"""Request and response models for POST /chat.

The bounds exist so a blank or huge instruction fails before Gemini is
called. Extraction fields stay null when the instruction does not state them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

# After trimming. A longer instruction is rejected rather than truncated,
# because truncation could drop the part extraction would need.
_MAX_MESSAGE_LENGTH = 4000


class ChatRequest(BaseModel):
    """User instruction. Content is interpreted only by the extraction call."""

    message: str

    @field_validator("message")
    @classmethod
    def strip_and_bound(cls, value: str) -> str:
        """Require 1–4000 characters after trimming.

        Whitespace-only text is the same failure as an empty instruction:
        there is nothing to extract, and Gemini must not be called.
        """
        stripped = value.strip()
        if len(stripped) < 1:
            raise ValueError(
                "message must be at least 1 character after trimming whitespace"
            )
        if len(stripped) > _MAX_MESSAGE_LENGTH:
            raise ValueError(
                "message must be at most 4000 characters after trimming whitespace"
            )
        return stripped


class EmailExtraction(BaseModel):
    """Fields copied from the instruction. No confidence score.

    Strict mode keeps a number or object from being coerced into a string.
    Coercion would invent a field the user did not write.
    `recipient_mention` is a person's name copied from the instruction, or
    null. It is not an email address.
    """

    model_config = ConfigDict(strict=True)

    recipient: str | None = None
    subject: str | None = None
    body: str | None = None
    recipient_mention: str | None = None


class SlotAssessment(BaseModel):
    """Inspectable slot-sufficiency threshold.

    `resolved_fraction` is the number of resolved required slots divided
    by 3. It is a completeness ratio, not a probability.
    """

    model_config = ConfigDict(strict=True)

    method: Literal["slot_sufficiency_threshold"]
    recipient: Literal["resolved", "missing", "bare_name", "ambiguous"]
    subject: Literal["resolved", "missing"]
    body: Literal["resolved", "missing"]
    resolved_fraction: float


class ChatResponse(BaseModel):
    """ASK or SEND from the slot-sufficiency threshold.

    The language model does not choose `decision`. Python does, after
    copy-only extraction. SEND does not send mail.
    """

    reply: str
    phase: Literal["decision_layer"]
    decision: Literal["ASK", "SEND"]
    clarification: str | None
    extraction: EmailExtraction
    assessment: SlotAssessment
