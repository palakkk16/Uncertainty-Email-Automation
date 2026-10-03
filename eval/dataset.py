"""Load the human-labeled evaluation cases.

Gold fields are read from the file. This module does not call the
threshold and does not invent labels.
"""

from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_DATASET = _ROOT / "eval" / "dataset.json"
_CATEGORIES = frozenset({"complete", "partial", "ambiguous"})
_DECISIONS = frozenset({"ASK", "SEND"})
_SLOTS = frozenset({"recipient", "subject", "body"})
_EXTRACTION_KEYS = ("recipient", "subject", "body", "recipient_mention")


def load_dataset(path: Path | None = None) -> list[dict[str, object]]:
    """Return the synthetic cases. An empty or malformed file fails fast."""
    dataset_path = path or _DATASET
    payload = json.loads(dataset_path.read_text())
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{dataset_path} must contain a non-empty list")
    cases: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, item in enumerate(payload):
        case = _validate_case(item, index)
        case_id = str(case["id"])
        if case_id in seen:
            raise ValueError(f"duplicate case id {case_id}")
        seen.add(case_id)
        cases.append(case)
    return cases


def category_counts(cases: list[dict[str, object]]) -> dict[str, int]:
    """Count cases in each human category."""
    counts = {name: 0 for name in ("complete", "partial", "ambiguous")}
    for case in cases:
        counts[str(case["category"])] += 1
    return counts


def _validate_case(item: object, index: int) -> dict[str, object]:
    if not isinstance(item, dict):
        raise ValueError(f"case {index} must be an object")
    required = (
        "id",
        "category",
        "instruction",
        "gold_decision",
        "gold_slot",
        "proposed_extraction",
    )
    missing = [key for key in required if key not in item]
    if missing:
        raise ValueError(f"case {index} is missing {', '.join(missing)}")
    category = item["category"]
    decision = item["gold_decision"]
    slot = item["gold_slot"]
    if category not in _CATEGORIES:
        raise ValueError(f"case {item['id']} has unknown category {category}")
    if decision not in _DECISIONS:
        raise ValueError(f"case {item['id']} has unknown gold_decision")
    if decision == "SEND" and slot is not None:
        raise ValueError(f"case {item['id']} SEND cases use a null gold_slot")
    if decision == "ASK" and slot not in _SLOTS:
        raise ValueError(f"case {item['id']} ASK gold_slot must name one slot")
    extraction = item["proposed_extraction"]
    if not isinstance(extraction, dict):
        raise ValueError(f"case {item['id']} proposed_extraction must be an object")
    for key in _EXTRACTION_KEYS:
        if key not in extraction:
            raise ValueError(f"case {item['id']} extraction lacks {key}")
        value = extraction[key]
        if value is not None and not isinstance(value, str):
            raise ValueError(f"case {item['id']} extraction {key} must be str or null")
    return item
