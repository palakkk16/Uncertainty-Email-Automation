"""Print Phase 6 metrics and write docs/phase-6-evaluation.md.

Run from the project root: python -m eval.run
This command does not call Gemini and does not send mail.
"""

from __future__ import annotations

from pathlib import Path

from eval.dataset import load_dataset
from eval.metrics import evaluate, format_metrics
from eval.report import render_report

_DOC = Path(__file__).resolve().parents[1] / "docs" / "phase-6-evaluation.md"


def main() -> None:
    """Score the dataset once, print the metrics, and write the note."""
    cases = load_dataset()
    result = evaluate(cases)
    print(format_metrics(result))
    _DOC.write_text(render_report(cases, result))
    print(f"wrote {_DOC}")


if __name__ == "__main__":
    main()
