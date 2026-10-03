"""Shared ASK versus SEND metrics for pytest and the eval runner.

Rates come from one function. The runner prints those numbers and writes
them into the phase 6 note. Nothing here calls a language model.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.baseline.direct import MemorySink, execute
from app.decision import decide
from app.schemas.chat import EmailExtraction
from app.decision.sufficiency import Decision


@dataclass(frozen=True)
class CaseOutcome:
    """One case scored by the proposed threshold and the baseline sink."""

    case_id: str
    category: str
    gold_decision: str
    gold_slot: str | None
    proposed_decision: str
    proposed_slot: str | None
    proposed_question: str | None
    baseline_sent: bool
    baseline_recipient: str
    baseline_subject: str
    baseline_body: str


@dataclass(frozen=True)
class Evaluation:
    """Aggregate rates plus the per-case rows they were counted from."""

    outcomes: tuple[CaseOutcome, ...]
    task_success_count: int
    task_success_rate: float
    incorrect_execution_baseline_count: int
    incorrect_execution_rate_baseline: float
    incorrect_execution_proposed_count: int
    incorrect_execution_rate_proposed: float
    prevented_misfires: int
    prevented_misfire_rate: float
    clarification_hits: int
    clarification_accuracy: float
    over_clarification_count: int
    over_clarification_rate: float
    average_clarification_turns: float
    gold_ask_count: int
    gold_send_count: int

    @property
    def case_count(self) -> int:
        return len(self.outcomes)


def propose(case: dict[str, object]) -> Decision:
    """Score the case's copy-only fields with the real threshold."""
    extraction = EmailExtraction.model_validate(case["proposed_extraction"])
    return decide(str(case["instruction"]), extraction)


def slot_targeted_by_question(question: str | None) -> str | None:
    """Map a clarification question onto recipient, subject, or body."""
    if not question:
        return None
    lowered = question.lower()
    if "subject" in lowered:
        return "subject"
    if "body" in lowered:
        return "body"
    if "email address" in lowered:
        return "recipient"
    return None


def evaluate(cases: list[dict[str, object]]) -> Evaluation:
    """Score every case once and return the documented rates."""
    outcomes = tuple(_score_case(case) for case in cases)
    return _aggregate(outcomes)


def format_rate(value: float) -> str:
    """Fixed-width rate so the printout and the note share one spelling."""
    return f"{value:.4f}"


def format_metrics(result: Evaluation) -> str:
    """Plain metrics block. The note embeds this text unchanged."""
    total = result.case_count
    lines = [
        f"cases: {total}",
        f"task_success: {result.task_success_count}/{total} ({format_rate(result.task_success_rate)})",
        (
            "incorrect_execution_baseline: "
            f"{result.incorrect_execution_baseline_count}/{total} "
            f"({format_rate(result.incorrect_execution_rate_baseline)})"
        ),
        (
            "incorrect_execution_proposed: "
            f"{result.incorrect_execution_proposed_count}/{total} "
            f"({format_rate(result.incorrect_execution_rate_proposed)})"
        ),
        (
            "prevented_misfires: "
            f"{result.prevented_misfires}/{result.gold_ask_count} "
            f"({format_rate(result.prevented_misfire_rate)})"
        ),
        (
            "clarification_accuracy: "
            f"{result.clarification_hits}/{result.gold_ask_count} "
            f"({format_rate(result.clarification_accuracy)})"
        ),
        (
            "over_clarification: "
            f"{result.over_clarification_count}/{result.gold_send_count} "
            f"({format_rate(result.over_clarification_rate)})"
        ),
        (
            "average_clarification_turns: "
            f"{format_rate(result.average_clarification_turns)}"
        ),
    ]
    return "\n".join(lines)


def _score_case(case: dict[str, object]) -> CaseOutcome:
    decision = propose(case)
    sink = MemorySink()
    attempt = execute(str(case["instruction"]), sink)
    question = decision.clarification
    proposed_slot = (
        slot_targeted_by_question(question) if decision.decision == "ASK" else None
    )
    return CaseOutcome(
        case_id=str(case["id"]),
        category=str(case["category"]),
        gold_decision=str(case["gold_decision"]),
        gold_slot=case["gold_slot"] if isinstance(case["gold_slot"], str) else None,
        proposed_decision=decision.decision,
        proposed_slot=proposed_slot,
        proposed_question=question,
        baseline_sent=len(sink.attempts) == 1,
        baseline_recipient=attempt["recipient"],
        baseline_subject=attempt["subject"],
        baseline_body=attempt["body"],
    )


def _aggregate(outcomes: tuple[CaseOutcome, ...]) -> Evaluation:
    total = len(outcomes)
    ask = [item for item in outcomes if item.gold_decision == "ASK"]
    send = [item for item in outcomes if item.gold_decision == "SEND"]
    task_hits = sum(
        item.proposed_decision == item.gold_decision for item in outcomes
    )
    baseline_bad = sum(
        item.baseline_sent and item.gold_decision == "ASK" for item in outcomes
    )
    proposed_bad = sum(
        item.proposed_decision == "SEND" and item.gold_decision == "ASK"
        for item in outcomes
    )
    prevented = sum(
        item.baseline_sent and item.proposed_decision == "ASK" for item in ask
    )
    clarification_hits = sum(
        item.proposed_decision == "ASK" and item.proposed_slot == item.gold_slot
        for item in ask
    )
    over = sum(item.proposed_decision == "ASK" for item in send)
    turns = [
        1 if item.proposed_decision == "ASK" else 0 for item in ask
    ]
    average_turns = sum(turns) / len(turns) if turns else 0.0
    return Evaluation(
        outcomes=outcomes,
        task_success_count=task_hits,
        task_success_rate=_rate(task_hits, total),
        incorrect_execution_baseline_count=baseline_bad,
        incorrect_execution_rate_baseline=_rate(baseline_bad, total),
        incorrect_execution_proposed_count=proposed_bad,
        incorrect_execution_rate_proposed=_rate(proposed_bad, total),
        prevented_misfires=prevented,
        prevented_misfire_rate=_rate(prevented, len(ask)),
        clarification_hits=clarification_hits,
        clarification_accuracy=_rate(clarification_hits, len(ask)),
        over_clarification_count=over,
        over_clarification_rate=_rate(over, len(send)),
        average_clarification_turns=average_turns,
        gold_ask_count=len(ask),
        gold_send_count=len(send),
    )


def _rate(count: int, total: int) -> float:
    if total == 0:
        return 0.0
    return count / total
