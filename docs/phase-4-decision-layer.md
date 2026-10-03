# Phase 4 — Python ASK vs SEND threshold

`POST /chat` still makes one Gemini API call. That call only copies text. Python then decides `ASK` or `SEND`. The model is not asked which to choose, and it is not asked for a confidence score.

This is a decision threshold on field constraints. It is not a calibrated probability, not semantic entropy, and not information gain. Those remain open. `resolved_fraction` is a completeness ratio: the number of resolved required slots divided by 3. `bare_name` and `ambiguous` are not resolved, so they do not increase the ratio.

A `SEND` decision does not call Gmail. `scripts/gmail_send_test.py` is still the only mail sender. The API does not import it.

## Threshold

Required slots: `recipient`, `subject`, `body`.

| Slot | `resolved` | Otherwise |
| --- | --- | --- |
| recipient | The extraction contains exactly one email address, and that address occurs in the instruction. The instruction does not contain a second address. | `ambiguous` when more than one email address is present. `bare_name` when the instruction names a person and no email address is present. `missing` when none of those hold. |
| subject | `extraction.subject` is a non-empty string contained in the instruction. | `missing` |
| body | Same rule as subject. | `missing` |

`SEND` only when all three slots are `resolved`. `clarification` is null. `reply` is `The decision is SEND. No email was sent.`

`ASK` otherwise. Exactly one question, in this order: recipient (`ambiguous`, then `bare_name`, then `missing`), then subject, then body. `reply` and `clarification` are that question.

A bare name is accepted only when it occurs in the instruction. The extractor may copy it as `recipient_mention`. If that copy is missing, a deterministic span check looks for name tokens immediately after an email verb (`Email Rahul about tomorrow` yields Rahul). The span uses a closed word list. It is not a person-name model. No email address is invented.

## Response

`POST /chat` with every slot resolved:

```json
{
  "reply": "The decision is SEND. No email was sent.",
  "phase": "decision_layer",
  "decision": "SEND",
  "clarification": null,
  "extraction": {
    "recipient": "rahul@example.com",
    "subject": "Lab meeting",
    "body": "Tomorrow at 10 AM",
    "recipient_mention": null
  },
  "assessment": {
    "method": "slot_sufficiency_threshold",
    "recipient": "resolved",
    "subject": "resolved",
    "body": "resolved",
    "resolved_fraction": 1.0
  }
}
```

`POST /chat` with `{"message": "Email Rahul about tomorrow"}`:

```json
{
  "reply": "What is Rahul's email address?",
  "phase": "decision_layer",
  "decision": "ASK",
  "clarification": "What is Rahul's email address?",
  "extraction": {
    "recipient": null,
    "subject": null,
    "body": null,
    "recipient_mention": "Rahul"
  },
  "assessment": {
    "method": "slot_sufficiency_threshold",
    "recipient": "bare_name",
    "subject": "missing",
    "body": "missing",
    "resolved_fraction": 0.0
  }
}
```

`decision` is `ASK` or `SEND`. It is not null. `phase` is `decision_layer`.

`assessment.method` is always `slot_sufficiency_threshold`. Subject and body are only `resolved` or `missing`. Recipient may also be `bare_name` or `ambiguous`.

Empty or whitespace-only `message` is still **422** and does not call Gemini. A missing Gemini key is still **503**. A Gemini client error with HTTP status 429 is **429**, with a fixed detail and no exception text. Any other Gemini failure or unparseable JSON is still **502**. None of those responses send mail.

## What this phase does not do

- No semantic entropy, sampling, or information-gain choice of the question
- No LLM self-reported confidence, and no use of model token probabilities
- No claim that `resolved_fraction` is a calibrated uncertainty
- No Gmail send, and no import of `scripts/gmail_send_test.py` from the API
- No new paid service and no new dependency

The decision function lives in `app/decision/` and can be unit-tested without Gemini.
