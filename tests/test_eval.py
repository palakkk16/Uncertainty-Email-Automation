"""Offline evaluation of the threshold against a gap-filling baseline.

These tests do not call Gemini and do not send mail. Gold labels are read
from eval/dataset.json.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

from app.baseline.direct import ASSUMED_SUBJECT, MemorySink, execute
from eval.dataset import category_counts, load_dataset
from eval.metrics import evaluate, format_metrics, propose
from eval.run import main

_ROOT = Path(__file__).resolve().parents[1]
_FORBIDDEN = (
    "googleapiclient",
    "googleapiclient.discovery",
    "scripts.gmail_send_test",
    "gmail_send_test",
    "google.generativeai",
    "vertexai",
)


def test_dataset_has_all_three_categories_and_example_addresses() -> None:
    cases = load_dataset()
    counts = category_counts(cases)

    assert set(counts) == {"complete", "partial", "ambiguous"}
    assert all(count > 0 for count in counts.values())
    assert max(counts.values()) - min(counts.values()) <= 1
    assert 16 <= len(cases) <= 20
    emails = _addresses_in_dataset()
    assert emails
    assert all(address.endswith("@example.com") for address in emails)


def test_human_labels_follow_the_category_definitions() -> None:
    for case in load_dataset():
        if case["category"] == "complete":
            assert case["gold_decision"] == "SEND"
            assert case["gold_slot"] is None
        elif case["category"] == "partial":
            assert case["gold_decision"] == "ASK"
            assert case["gold_slot"] in {"recipient", "subject", "body"}
        else:
            assert case["category"] == "ambiguous"
            assert case["gold_decision"] == "ASK"
            assert case["gold_slot"] == "recipient"
        _assert_copy_only(case)


def test_baseline_always_records_a_send_and_never_imports_mail() -> None:
    for case in load_dataset():
        sink = MemorySink()
        attempt = execute(str(case["instruction"]), sink)

        assert len(sink.attempts) == 1
        assert sink.attempts[0] == attempt
        assert attempt["recipient"]
        assert attempt["subject"]
        assert attempt["body"]

    _assert_mail_sender_not_imported()
    source = _package_source(_ROOT / "app" / "baseline")
    assert "decide(" not in source
    assert "ASK" not in source


def test_complete_case_proposed_sends_and_baseline_sends() -> None:
    case = _case("complete-lab-meeting")
    decision = propose(case)
    sink = MemorySink()
    attempt = execute(str(case["instruction"]), sink)

    assert decision.decision == "SEND"
    assert decision.clarification is None
    assert len(sink.attempts) == 1
    assert attempt["recipient"] == "rahul@example.com"
    assert attempt["subject"] == "Lab meeting"
    assert attempt["body"] == "Tomorrow at 10 AM"


def test_rahul_bare_name_asks_and_baseline_invents_an_address() -> None:
    case = _case("ambiguous-rahul")
    decision = propose(case)
    sink = MemorySink()
    attempt = execute(str(case["instruction"]), sink)

    assert case["instruction"] == "Email Rahul about tomorrow"
    assert decision.decision == "ASK"
    assert decision.clarification is not None
    assert "Rahul" in decision.clarification
    assert attempt["recipient"] == "rahul@example.com"
    assert attempt["recipient"] not in str(case["instruction"])
    assert attempt["recipient"].endswith("@example.com")
    assert len(sink.attempts) == 1


def test_two_addresses_proposed_asks_and_baseline_still_sends() -> None:
    case = _case("ambiguous-two-addresses")
    decision = propose(case)
    sink = MemorySink()
    attempt = execute(str(case["instruction"]), sink)

    assert decision.decision == "ASK"
    assert decision.clarification is not None
    assert "rahul@example.com" in decision.clarification
    assert "priya@example.com" in decision.clarification
    assert len(sink.attempts) == 1
    assert attempt["recipient"] == "rahul@example.com"
    assert case["proposed_extraction"]["recipient"] is None


def test_missing_subject_uses_the_fixed_assumption_and_asks_subject() -> None:
    case = _case("partial-missing-subject")
    decision = propose(case)
    sink = MemorySink()
    attempt = execute(str(case["instruction"]), sink)

    assert decision.decision == "ASK"
    assert decision.clarification is not None
    assert "subject" in decision.clarification.lower()
    assert attempt["subject"] == ASSUMED_SUBJECT
    assert attempt["body"] == "Tomorrow at 10 AM"


def test_metrics_match_independent_counts_and_the_written_note() -> None:
    cases = load_dataset()
    result = evaluate(cases)
    recounted = _recount(result.outcomes)

    assert result.task_success_count == recounted["task_success"]
    assert result.task_success_rate == recounted["task_success"] / len(cases)
    assert result.incorrect_execution_baseline_count == recounted["baseline_bad"]
    assert result.incorrect_execution_proposed_count == recounted["proposed_bad"]
    assert result.prevented_misfires == recounted["prevented"]
    assert result.clarification_hits == recounted["clarification_hits"]
    assert result.over_clarification_count == recounted["over"]
    assert result.gold_ask_count == recounted["ask"]
    assert result.average_clarification_turns == recounted["turns"] / recounted["ask"]
    assert result.task_success_count == len(cases)
    assert result.incorrect_execution_proposed_count == 0
    assert result.prevented_misfires == result.gold_ask_count

    main()
    note = (_ROOT / "docs" / "phase-6-evaluation.md").read_text()
    assert format_metrics(result) in note
    for phrase in (
        "offline",
        "semantic entropy",
        "Gmail",
        "Gemini",
        "single-shot",
        "gap-filling",
        "in-memory",
    ):
        assert phrase in note


def test_eval_code_does_not_import_the_mail_sender() -> None:
    for root in (_ROOT / "eval", _ROOT / "app" / "baseline"):
        for path in root.rglob("*.py"):
            imported = _imported_modules(path)
            for name in imported:
                for forbidden in _FORBIDDEN:
                    assert forbidden not in name

    _assert_mail_sender_not_imported()


def _case(case_id: str) -> dict[str, object]:
    for case in load_dataset():
        if case["id"] == case_id:
            return case
    raise AssertionError(f"missing case {case_id}")


def _assert_copy_only(case: dict[str, object]) -> None:
    instruction = str(case["instruction"])
    extraction = case["proposed_extraction"]
    assert isinstance(extraction, dict)
    for key in ("recipient", "subject", "body", "recipient_mention"):
        value = extraction[key]
        if isinstance(value, str):
            assert value in instruction
    recipient = extraction["recipient"]
    if case["category"] == "ambiguous":
        assert recipient is None


def _addresses_in_dataset() -> list[str]:
    import re

    text = (_ROOT / "eval" / "dataset.json").read_text()
    return re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text)


def _recount(outcomes: tuple) -> dict[str, int]:
    ask = [item for item in outcomes if item.gold_decision == "ASK"]
    send = [item for item in outcomes if item.gold_decision == "SEND"]
    turns = sum(1 if item.proposed_decision == "ASK" else 0 for item in ask)
    return {
        "task_success": sum(
            item.proposed_decision == item.gold_decision for item in outcomes
        ),
        "baseline_bad": sum(
            item.baseline_sent and item.gold_decision == "ASK" for item in outcomes
        ),
        "proposed_bad": sum(
            item.proposed_decision == "SEND" and item.gold_decision == "ASK"
            for item in outcomes
        ),
        "prevented": sum(
            item.baseline_sent and item.proposed_decision == "ASK" for item in ask
        ),
        "clarification_hits": sum(
            item.proposed_decision == "ASK" and item.proposed_slot == item.gold_slot
            for item in ask
        ),
        "over": sum(item.proposed_decision == "ASK" for item in send),
        "ask": len(ask),
        "turns": turns,
    }


def _package_source(root: Path) -> str:
    return "\n".join(path.read_text() for path in root.rglob("*.py"))


def _imported_modules(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.append(node.module)
            found.extend(f"{node.module}.{alias.name}" for alias in node.names)
    return found


def _assert_mail_sender_not_imported() -> None:
    assert "googleapiclient" not in sys.modules
    assert "googleapiclient.discovery" not in sys.modules
    loaded = [name for name in sys.modules if "gmail_send_test" in name]
    assert loaded == []
