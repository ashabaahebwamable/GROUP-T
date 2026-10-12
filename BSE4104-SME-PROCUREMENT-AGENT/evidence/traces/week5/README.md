# Week 5 execution traces (W5-04)

Owner: Akisa Maria Ashley (Quality/Security Lead). These are recordings of the real bounded
loop (`src/agent/loop.py`, `run_agent`) run against the Week 5 Agent Task Contract
(`docs/architecture/agent-task-contract.md`). Stop codes (H2, S4, S5, S2) are the
contract's.

| File | What it shows | Outcome | Contract |
|---|---|---|---|
| `trace-1-happy-path.json` | Reorder signal to a DRAFT requisition awaiting a human (INV-003, 460 pieces). Run 1 stops at H1, the officer confirms SUP-03, run 2 resumes from the saved state | Run 1 `SUPPLIER_CONFIRMATION_REQUIRED` after 4 calls; run 2 `READY_FOR_HUMAN_APPROVAL` after 1 | H1, H2 |
| `trace-1b-reference-case-excluded-supplier.json` | The design's cement reference case (INV-001, 10,000 kg) | `POLICY_BLOCKING_FLAGS` after 4 calls | S4 |
| `trace-1c-real-clock-stale-quotations.json` | Trace 1's inputs on the real clock | `POLICY_BLOCKING_FLAGS` after 4 calls | S4 |
| `trace-2-ambiguous-item.json` | "Portland cement" matches two items; none is chosen | `AMBIGUOUS_ITEM`, 0 tool calls | S5 |
| `trace-3-tool-failure-recovery.json` | A: outage, one retry, safe hand-off. B: tool returns, resume from A's saved state. B2: officer confirms, resume to the draft. C: one failure, retry succeeds | A `TOOL_FAILED_AFTER_RETRY` (2 calls); B and C reach H1; B2 reaches `READY_FOR_HUMAN_APPROVAL` | S2, H1, H2 |

Every trace also lists the audit events its runs persisted (`AGENT_RUN_STOPPED` for each stop, and `REQUISITION_DRAFT_CREATED` with the confirming officer). Event ids and timestamps are left out so a re-run does not change them.

**Regenerated 12 Oct 2026** after the loop gaps in findings 4–7 were closed (contract section 9, items 3, 7, 9 and 10). The earlier version showed 3 tool calls and no H1.

Traces 1b and 1c are extra. They exist because the happy path only works under conditions
that the findings below explain.

## How they were produced

`python -m scripts.generate_week5_traces` from the project root. It can be re-run at any
time: no model is called (the loop's default planner is rule-based, so no API quota is
used; `lookup_policy` runs the local Week 3 retriever). Requisition drafts, the loop's tool
trace and all audit events go to a temporary folder rather than `data/requisitions.csv`,
`tool-calls.jsonl` or `audit-log.jsonl`, `lookup_policy`'s retrieval log is switched off,
and the only files written are the ones here. Re-running changes only the generation
timestamps and the officer's `confirmed_at` time in the saved states.

Three things are simulated, and each trace says so in its `environment` block:

- **The clock.** Traces 1, 1b and 3 pin the date given to `compare_quotations`. Trace 1c
  uses the real clock.
- **The outage in Trace 3** is a mock that raises `ConnectionError`.
- **The ambiguity in Trace 2.** Matching the text "Portland cement" to its two candidates is
  done by the generator, not by `run_agent`, which receives `item_id=None`.

## Findings

Each is backed by the trace named. Findings 4–7 were fixed on 12 Oct 2026 and are kept
here, struck through, as the record of what the first traces showed. The rest are open;
the owners decide.

1. **The reference case cannot reach a draft** (Trace 1b). `compare_quotations` correctly
   leaves the excluded supplier's quotation (QUO-1004) out of the ranking and still
   recommends SUP-01, which is what policy 4.1 and US-06 AC2 describe. But it also lists
   `EXCLUDED_SUPPLIER:SUP-05:QUO-1004` as a *blocking* flag, and the contract (S4) treats
   that as a stop. Neither policy 4.1 nor US-06 AC2 says it should block the whole
   requisition. The demo script `scripts/demo_week4.py` gets a draft for INV-001 only by
   passing `policy_flags=()` by hand. **Decision needed:** make an already-excluded
   quotation informational, or change the reference case and the final demo.
2. **The quotation data has gone stale** (Trace 1c). The quotations are dated 20-28 Aug
   with 7-30 days of validity: 0 of 10 are valid today, 10 of 10 on 27 Aug. Only 4 of the 15
   inventory items have any quotation. Searching every date from 15 Aug to 13 Oct, the
   only flag-free case is INV-003 on or before 27 Aug. The Week 7 evaluation set will need
   refreshed dates or more quoted items.
3. **The router cannot take an as-of date** (Trace 1c). Its draft pre-check calls
   `compare_quotations` with no date, so a caller cannot pin the clock through it.
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
