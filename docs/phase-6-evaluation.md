# Phase 6 evaluation

## Dataset

18 synthetic instructions in `eval/dataset.json`. No real inboxes. Every address is on example.com.

Categories, labeled in the file: complete 6, partial 6, ambiguous 6.

Complete cases state one email address, an explicit subject line, and an explicit body. Gold decision SEND, gold slot null.
Partial cases leave out a required field (no subject, no body, or no recipient at all). Gold decision ASK on that missing slot. When more than one slot is open, the gold slot is the one the threshold asks about first: recipient, then subject, then body.
Ambiguous cases are a bare name with no address, or two email addresses. Gold decision ASK on recipient. `proposed_extraction` does not invent an address for those cases.

`gold_decision` and `gold_slot` are human labels in the dataset file. They are not computed by the system under test. `proposed_extraction` is the copy-only fields a correct extractor would return. The proposed arm builds `EmailExtraction` from those fields and calls `decide()`.

## Metric definitions

Task success rate: proposed decision equals `gold_decision`, over every case.
Incorrect execution rate, baseline: cases where the baseline records a send and `gold_decision` is ASK, over every case.
Incorrect execution rate, proposed: cases where the proposed decision is SEND and `gold_decision` is ASK, over every case.
Prevented misfires: count, and rate over gold ASK cases, where the baseline records a send, the proposed decision is ASK, and gold is ASK.
Clarification accuracy: among gold ASK cases, the fraction where the proposed decision is ASK and the question targets `gold_slot` (recipient question, subject question, or body question).
Over-clarification rate: among gold SEND cases, the fraction where the proposed decision is ASK.
Average clarification turns: mean, over gold ASK cases, of 1 if the proposed decision is ASK and 0 if it is SEND. Single-shot, not a multi-turn simulation.

## Results

These figures are the return value of `evaluate()` in `eval/metrics.py`. The runner prints the same block.

```
cases: 18
task_success: 18/18 (1.0000)
incorrect_execution_baseline: 12/18 (0.6667)
incorrect_execution_proposed: 0/18 (0.0000)
prevented_misfires: 12/12 (1.0000)
clarification_accuracy: 12/12 (1.0000)
over_clarification: 0/6 (0.0000)
average_clarification_turns: 1.0000
```

## Comparison

The baseline records a send on every case, so it also records a send on all 12 gold ASK cases. Its incorrect execution rate is 12/18 (0.6667).
The proposed threshold, given the copy-only fields, sends on 0 gold ASK cases. Its incorrect execution rate is 0/18 (0.0000). It returns ASK on 12 of the 12 gold ASK cases where the baseline would send. That is the prevented-misfire count, 12/12 (1.0000) of gold ASK cases.
Clarification accuracy is 12/12 (1.0000): the question names the gold slot. Over-clarification on gold SEND cases is 0/6 (0.0000).
Average clarification turns on gold ASK cases is 1.0000. That number is single-shot.
Task success is 18/18 (1.0000).

## Limits

This benchmark is offline. Pytest and `python -m eval.run` do not call Gemini, and they do not open a socket to Gmail. Free-tier 429s make a live sweep unreproducible, so this phase does not sample the model a second time.

The baseline is a gap-filling direct executor. It does not call the slot-sufficiency threshold. When a field is missing it invents a stand-in: the first address if several are written, a name-derived example.com address for a bare name, a fixed subject, or the raw instruction as the body. Each of those is a recorded attempt on an in-memory sink. The sink does not send mail.

`resolved_fraction` on the proposed path is a completeness ratio (resolved slots / 3), not a probability. These rates are not a calibrated uncertainty score, and this phase does not measure semantic entropy.

Average clarification turns is single-shot. On each gold ASK case it is 1 when the proposed decision is ASK and 0 when the proposed decision is SEND. It is not a multi-turn simulation.
