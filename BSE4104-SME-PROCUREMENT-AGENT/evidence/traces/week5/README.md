# Week 5 execution traces (W5-04)

Owner: Akisa Maria Ashley (Quality/Security Lead). These are recordings of the real bounded
loop (`src/agent/loop.py`, `run_agent`) run against the Week 5 Agent Task Contract
(`docs/architecture/agent-task-contract.md`). Stop codes (H2, S4, S5, S2) are the
contract's (H1, H2, S2, S4, S5).

| File | What it shows | Outcome | Contract |
|---|---|---|---|
| `trace-1-happy-path.json` | Reorder signal to a DRAFT requisition awaiting a human (INV-003, 460 pieces). Run 1 stops at H1, the officer confirms SUP-03, run 2 resumes from the saved state | Run 1 `SUPPLIER_CONFIRMATION_REQUIRED` after 4 calls; run 2 `READY_FOR_HUMAN_APPROVAL` after 1 | H1, H2 |
| `trace-1b-reference-case-excluded-supplier.json` | The design's cement reference case (INV-001, 10,000 kg). QUO-1004 from excluded SUP-05 is reported as informational and left out of the ranking; the officer confirms SUP-01 | Run 1 `SUPPLIER_CONFIRMATION_REQUIRED` after 4 calls; run 2 `READY_FOR_HUMAN_APPROVAL` after 1 | H1, H2 |
| `trace-1c-real-clock-stale-quotations.json` | Trace 1's inputs on the real clock | `POLICY_BLOCKING_FLAGS` after 4 calls | S4 |
| `trace-2-ambiguous-item.json` | "Portland cement" matches two items; none is chosen | `AMBIGUOUS_ITEM`, 0 tool calls | S5 |
| `trace-3-tool-failure-recovery.json` | A: outage, one retry, safe hand-off. B: tool returns, resume from A's saved state. B2: officer confirms, resume to the draft. C: one failure, retry succeeds | A `TOOL_FAILED_AFTER_RETRY` (2 calls); B and C reach H1; B2 reaches `READY_FOR_HUMAN_APPROVAL` | S2, H1, H2 |

Every trace also lists the audit events its runs persisted (`AGENT_RUN_STOPPED` for each stop, and `REQUISITION_DRAFT_CREATED` with the confirming officer). Event ids and timestamps are left out so a re-run does not change them.

**Regenerated 12 Oct 2026** after the loop gaps in findings 4–7 were closed (contract section 9, items 3, 7, 9 and 10), and again after findings 1 and 3 were resolved. The first version showed 3 tool calls, no H1, and the reference case stopping at S4.

Traces 1b and 1c are extra: 1b is the case the final demo rehearses, and 1c shows why
every other trace sets an as-of date.

## How they were produced

`python -m scripts.generate_week5_traces` from the project root. It can be re-run at any
time: no model is called (the loop's default planner is rule-based, so no API quota is
used; `lookup_policy` runs the local Week 3 retriever). Requisition drafts, the loop's tool
trace and all audit events go to a temporary folder rather than `data/requisitions.csv`,
`tool-calls.jsonl` or `audit-log.jsonl`, `lookup_policy`'s retrieval log is switched off,
and the only files written are the ones here. Re-running changes only the generation
timestamps and the officer's `confirmed_at` time in the saved states.

Three things are simulated, and each trace says so in its `environment` block:

- **The as-of date.** Traces 1, 1b, 2 and 3 pass `run_agent(as_of_date=...)`, the
  person-set case input the router uses for quotation validity (no patching). Trace 1c
  uses the real clock.
- **The outage in Trace 3** is a mock that raises `ConnectionError`.
- **The ambiguity in Trace 2.** Matching the text "Portland cement" to its two candidates is
  done by the generator, not by `run_agent`, which receives `item_id=None`.

## Findings

Each is backed by the trace named. Findings 1 and 3–7 were resolved on 12 Oct 2026 and
are kept here, struck through, as the record of what the first traces showed. The rest
are open; the owners decide.

1. ~~**The reference case cannot reach a draft** (Trace 1b).~~ Resolved by decision:
   `EXCLUDED_SUPPLIER` is now an informational flag. The exclusion is still enforced (the
   quotation is not counted or ranked, and the draft tool refuses an excluded supplier),
   and too few remaining valid quotations still block. Trace 1b now reaches a draft.
2. **The quotation data is stale on the real clock** (Trace 1c). The quotations are dated
   20-28 Aug with 7-30 days of validity: 0 of 10 are valid today. Decided: keep the data
   and set an as-of date (finding 3), so this is now expected behaviour rather than a
   blocker. Still open: only 4 of the 15 inventory items have any quotation, which limits
   the Week 7 evaluation set.
3. ~~**The router cannot take an as-of date** (Trace 1c).~~ Resolved:
   `run_agent(as_of_date=...)` is kept in the case state and passed by code to the
   comparison and the draft pre-check. It is not a tool argument, so the model cannot
   choose a date that makes an expired quotation valid.
4. ~~**No hand-off H1** (Trace 1).~~ Fixed: run 1 of Trace 1 stops at H1 and the draft
   needs the officer's confirmation.
5. ~~**`lookup_policy` is never called** (Trace 1).~~ Fixed: every run that gets past the
   quantity check makes two policy lookups (quotation minimum, approval threshold).
6. ~~**`run_agent` cannot resume** (Trace 3, phase B).~~ Fixed: phase B now resumes from
   phase A's saved state with `run_agent(state=...)`.
7. ~~**A blocked or failed call is logged in memory only.**~~ Fixed: every run writes its
   tool calls and stop to the tool trace and the audit log; the `expectedFailure` marker
   was removed.
8. **The ambiguity hand-off does not list the candidates** (Trace 2), and the description
   matching sits outside the loop.
9. **No role check on approval** (`tests/workflow/test_state_machine.py`). Carried from
   Week 4; contract section 9, item 6.

## AI use

The tests and the generator were drafted with AI assistance (AI Engineering Log, entry 5).
The trace files are the unedited output of the real loop.
