# Week 5 change review (12 Oct 2026)

**Reviewer:** Ashaba Ahebwa Mable (Project/Requirements Lead), with AI assistance (AI Engineering Log, entry 7).
**Why this review exists:** on 12 Oct the files below were changed to close the Week 5 contract gaps, and their owners could not be reached that day. This is an independent review by someone other than the owners. **It does not replace the owners' review:** each owner should read their section, confirm or object, and add their name and date in the last column.

## What was checked

For every changed file: the diff since `84fdda2` was read against the agent task contract and US-09; each claimed behaviour was traced to a test; the full suite was run (144 pass, 17 subtests); the loop was run end to end on real tools for INV-001, INV-003 and INV-010; and the trace generator, the demo and the tests were checked to write nothing into `data/` or the evidence logs.

## Findings

| # | File | Finding | Action |
|---|---|---|---|
| 1 | `src/workflow/case_store.py` | The case store does not record who prepared a case, so the US-09 "preparer may not approve" check was skipped on this path (the CSV requisition store was covered) | **Fixed:** the actor of the submit event is treated as the preparer. Test `test_officer_and_submitter_cannot_approve_a_case` |
| 2 | `src/workflow/case_store.py` | A refused approval raises but is not written to the case-event table; only the CSV requisition store logs refusals (`REQUISITION_ACTION_REFUSED`) | Open, minor. The case store is the resume model; decide in Week 6 whether it also needs a refusal event |
| 3 | `src/workflow/requisition_store.py` | Submit has no role check: an approver account could submit a draft | Accepted. The contract and US-07 only require that the agent cannot submit; flag if the team wants submit restricted to officers |
| 4 | `src/agent/tools_router.py` | `_limit_from_env` duplicates `loop._read_positive_int` | Accepted: importing from `loop` would be circular. Both read the same variables and defaults |
| 5 | `src/agent/loop.py` | `run_agent`'s rule-based planner replays a failed call with the same arguments, so an argument error can only fail again | Accepted and documented in contract section 5; only the model loop can correct arguments |

No other defects were found. Behaviours confirmed by test: H1 stop and router refusal of unconfirmed drafts; S6 policy stop; resume with a fresh iteration count and retry allowance; persisted stops with contract codes; S1/S2/S3/S8 in the model loop; candidate listing for ambiguous items; officer and self-approval refused and logged.

## Owner confirmation

| Area | Files | Owner | Confirmed (name, date) |
|---|---|---|---|
| Bounded loop | `src/agent/loop.py`, `tests/test_agent_loop.py` | Azibo Isaac Alinda | |
| State machine, stores, role check | `src/workflow/state_machine.py`, `requisition_store.py`, `case_store.py`, `users.py`, `data/users.csv`, `tests/workflow/` | Azibo Isaac Alinda | |
| Router and model loop | `src/agent/tools_router.py`, `src/agent/stop_codes.py`, `tests/test_agent_integration.py` | Tendo Caisey | |
| Stop-condition tests, traces, generator | `tests/agent/test_stop_conditions_and_allowlist.py`, `scripts/generate_week5_traces.py`, `evidence/traces/week5/` | Akisa Maria Ashley | |
| Synthetic quotations QUO-1011 to 1027 | `knowledge/records/quotations.csv` | Azibo Isaac Alinda (data author) | |
