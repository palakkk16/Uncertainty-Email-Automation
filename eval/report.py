"""Phase 6 note. Numbers are taken from evaluate(), not typed by hand."""

from __future__ import annotations

from eval.dataset import category_counts
from eval.metrics import Evaluation, format_metrics

_HONESTY = """\
## Limits

This benchmark is offline. Pytest and `python -m eval.run` do not call Gemini, and they do not open a socket to Gmail. Free-tier 429s make a live sweep unreproducible, so this phase does not sample the model a second time.

The baseline is a gap-filling direct executor. It does not call the slot-sufficiency threshold. When a field is missing it invents a stand-in: the first address if several are written, a name-derived example.com address for a bare name, a fixed subject, or the raw instruction as the body. Each of those is a recorded attempt on an in-memory sink. The sink does not send mail.

`resolved_fraction` on the proposed path is a completeness ratio (resolved slots / 3), not a probability. These rates are not a calibrated uncertainty score, and this phase does not measure semantic entropy.

Average clarification turns is single-shot. On each gold ASK case it is 1 when the proposed decision is ASK and 0 when the proposed decision is SEND. It is not a multi-turn simulation.
"""


def render_report(
    cases: list[dict[str, object]],
    result: Evaluation,
) -> str:
    """Build the phase 6 note from the shared metrics."""
    counts = category_counts(cases)
    metrics = format_metrics(result)
    comparison = _comparison(result)
    return (
        "# Phase 6 evaluation\n\n"
        f"{_dataset_section(counts)}\n\n"
        f"{_definitions()}\n\n"
        "## Results\n\n"
        "These figures are the return value of `evaluate()` in `eval/metrics.py`. "
        "The runner prints the same block.\n\n"
        f"```\n{metrics}\n```\n\n"
        f"{comparison}\n\n"
        f"{_HONESTY}"
    )


def _dataset_section(counts: dict[str, int]) -> str:
    total = sum(counts.values())
    return "\n".join(
        [
            "## Dataset",
            "",
            (
                f"{total} synthetic instructions in `eval/dataset.json`. "
                "No real inboxes. Every address is on example.com."
            ),
            "",
            (
                f"Categories, labeled in the file: complete {counts['complete']}, "
                f"partial {counts['partial']}, ambiguous {counts['ambiguous']}."
            ),
            "",
            (
                "Complete cases state one email address, an explicit subject line, "
                "and an explicit body. Gold decision SEND, gold slot null."
            ),
            (
                "Partial cases leave out a required field (no subject, no body, "
                "or no recipient at all). Gold decision ASK on that missing slot. "
                "When more than one slot is open, the gold slot is the one the "
                "threshold asks about first: recipient, then subject, then body."
            ),
            (
                "Ambiguous cases are a bare name with no address, or two email "
                "addresses. Gold decision ASK on recipient. "
                "`proposed_extraction` does not invent an address for those cases."
            ),
            "",
            (
                "`gold_decision` and `gold_slot` are human labels in the dataset "
                "file. They are not computed by the system under test. "
                "`proposed_extraction` is the copy-only fields a correct extractor "
                "would return. The proposed arm builds `EmailExtraction` from "
                "those fields and calls `decide()`."
            ),
        ]
    )


def _definitions() -> str:
    return "\n".join(
        [
            "## Metric definitions",
            "",
            (
                "Task success rate: proposed decision equals `gold_decision`, "
                "over every case."
            ),
            (
                "Incorrect execution rate, baseline: cases where the baseline "
                "records a send and `gold_decision` is ASK, over every case."
            ),
            (
                "Incorrect execution rate, proposed: cases where the proposed "
                "decision is SEND and `gold_decision` is ASK, over every case."
            ),
            (
                "Prevented misfires: count, and rate over gold ASK cases, where "
                "the baseline records a send, the proposed decision is ASK, and "
                "gold is ASK."
            ),
            (
                "Clarification accuracy: among gold ASK cases, the fraction where "
                "the proposed decision is ASK and the question targets `gold_slot` "
                "(recipient question, subject question, or body question)."
            ),
            (
                "Over-clarification rate: among gold SEND cases, the fraction "
                "where the proposed decision is ASK."
            ),
            (
                "Average clarification turns: mean, over gold ASK cases, of 1 "
                "if the proposed decision is ASK and 0 if it is SEND. "
                "Single-shot, not a multi-turn simulation."
            ),
        ]
    )


def _comparison(result: Evaluation) -> str:
    return "\n".join(
        [
            "## Comparison",
            "",
            (
                "The baseline records a send on every case, so it also records a "
                f"send on all {result.gold_ask_count} gold ASK cases. Its incorrect "
                "execution rate is "
                f"{result.incorrect_execution_baseline_count}/{result.case_count} "
                f"({result.incorrect_execution_rate_baseline:.4f})."
            ),
            (
                "The proposed threshold, given the copy-only fields, sends on "
                f"{result.incorrect_execution_proposed_count} gold ASK cases. "
                "Its incorrect execution rate is "
                f"{result.incorrect_execution_proposed_count}/{result.case_count} "
                f"({result.incorrect_execution_rate_proposed:.4f}). "
                f"It returns ASK on {result.prevented_misfires} of the "
                f"{result.gold_ask_count} gold ASK cases where the baseline would "
                "send. That is the prevented-misfire count, "
                f"{result.prevented_misfires}/{result.gold_ask_count} "
                f"({result.prevented_misfire_rate:.4f}) of gold ASK cases."
            ),
            (
                "Clarification accuracy is "
                f"{result.clarification_hits}/{result.gold_ask_count} "
                f"({result.clarification_accuracy:.4f}): the question names the "
                "gold slot. Over-clarification on gold SEND cases is "
                f"{result.over_clarification_count}/{result.gold_send_count} "
                f"({result.over_clarification_rate:.4f})."
            ),
            (
                "Average clarification turns on gold ASK cases is "
                f"{result.average_clarification_turns:.4f}. "
                "That number is single-shot."
            ),
            (
                f"Task success is {result.task_success_count}/{result.case_count} "
                f"({result.task_success_rate:.4f})."
            ),
        ]
    )
