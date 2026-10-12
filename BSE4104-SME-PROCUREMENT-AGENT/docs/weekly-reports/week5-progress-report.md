# Week 5 Progress Report — Bounded Agent Loop

## Objective

Week 5 turned the Week 4 tools into a **bounded agent**: a loop that takes one flagged stock item from the reorder signal to a requisition draft awaiting a human, and stops safely whenever it cannot or must not continue. The limits on the agent are written down first, in an agent task contract, and the loop, tests and traces are checked against it. The agent still makes no decisions that belong to people: it never confirms a supplier, submits, approves, purchases or contacts a supplier.

## What was built

**Agent task contract (W5-01).** `docs/architecture/agent-task-contract.md` sets the goal, the four approved tools and when each may be called, the case-state fields and who sets them, the iteration limit (6 tool calls, 1 retry per failed call), ten stop conditions with codes, the hand-off package, the prohibited actions and where each rule is enforced. Its two officer hand-offs are:

| Code | When | Officer's action |
|---|---|---|
| H1 | After the comparison recommends a supplier | Confirm that supplier (`confirm_supplier`) |
| H2 | After the draft is created | Submit it through the state machine |

and its failure stops are S1 iteration limit, S2 tool failed after one retry, S3 tool not on the allow-list, S4 blocking policy flags, S5 missing or ambiguous input, S6 policy rule not found, S7 model disagrees with the computed value and S8 model unavailable.

**Bounded loop.** `src/agent/loop.py` (`run_agent`) runs Sense → Plan → Act → Observe with a rule-based planner:

1. `check_reorder_levels` confirms the item needs reordering;
2. `lookup_policy` retrieves the quotation minimum (policy §2) and the approval threshold (policy §5);
3. `compare_quotations` ranks the quotations by landed cost;
4. **H1**: the run stops until the officer confirms the recommended supplier;
5. a resumed run calls `create_requisition_draft`, and **H2** hands the draft to the officer.

Every tool call, including blocked calls and retries, counts towards the limit read from `MAX_AGENT_ITERATIONS`. A retryable failure is retried once (`MAX_TOOL_RETRIES`). Every stop returns the hand-off package (stop reason, contract code, message, outstanding step, full case state, trace) and is written to `evidence/traces/tool-calls.jsonl` and, as an `AGENT_RUN_STOPPED` event, to `evidence/traces/audit-log.jsonl`. A stopped case resumes from its saved state with `run_agent(state=...)`, without repeating finished steps. The router refuses a draft unless an officer's confirmation of that exact supplier is passed by code; the model cannot supply it.

The model-driven entry point, `run_bounded_tool_agent`, has the same controls: tool calls counted against the same limit, one correction per failing tool, and a stop (not a second attempt) on a blocked tool, a policy refusal, a missing confirmation or a model failure.

**Case state, persistence and memory.** `src/workflow/case_store.py` keeps workflow cases in SQLite with an event per transition, and `docs/architecture/state-model.md` documents the states (`OPEN`, `DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `QUERIED`, `HALTED`). `src/memory/supplier_preferences.py` stores a supplier preference only with explicit confirmation and the confirmer's identity; it is shown to the officer as a hint and never affects ranking.

**Authorisation (US-09).** Approve, reject and query now refuse anyone whose role in `data/users.csv` is not approver, and the person who prepared the requisition. The requisition store writes a `REQUISITION_ACTION_REFUSED` audit event for each refused attempt. The accounts in `data/users.csv` are synthetic.

**Architecture.** `docs/architecture/week5-agent-architecture.png` shows the orchestrator around the Week 4 router and tools.

**Demo.** `python -m scripts.demo_week5` runs the project's reference cement case ("Portland cement 32.5N", 10,000 kg) through H1, the officer's confirmation and a resume to H2. By default it writes only to a temporary folder, so it can be rehearsed before the final presentation.

## Testing (W5-05)

The test suite (`python -m pytest`) runs **144 tests and 17 subtests, and all pass** (12 Oct 2026). There are no expected failures left: the one that documented unsaved stops was removed once stops were persisted.

| Requirement | Tests |
|---|---|
| Iteration limit reached → halt with outstanding steps listed (S1) | `tests/agent/test_stop_conditions_and_allowlist.py` `IterationLimitTests`; `tests/test_agent_integration.py` `ModelLoopControlTests` |
| Tool outside the allow-list → blocked before execution, logged, run stops (S3) | `AllowListTests` (approval, supplier email, purchase order, payment); model-loop test |
| Case state after a halt equals the state before it | `StatePreservedAfterHaltTests` (limit, hand-off, missing item, blocked tool, exhausted retry) |
| H1, resume, policy lookup (S6), persisted stops, item matching | `tests/test_agent_loop.py` |
| Officer cannot approve; preparer cannot approve; refusal logged | `tests/workflow/test_state_machine.py` `AuthorizationRoleTests`; `tests/test_week4_gap_fixes.py` |

The test fixture `tests/conftest.py` sends every test run's trace and audit writes to a temporary folder, so running the tests never changes the evidence files.

## Execution traces (W5-04)

Five traces in `evidence/traces/week5/` are the unedited output of the real loop, produced by `python -m scripts.generate_week5_traces`. No model is called; `lookup_policy` uses the real local retriever. Each trace records the contract code of every stop and the audit events it wrote.

| Trace | Outcome |
|---|---|
| 1 Happy path (INV-003, 460 pieces) | Run 1: 4 calls, H1. Officer confirms SUP-03. Run 2: 1 call, draft, H2 |
| 1b Reference cement case (INV-001, 10,000 kg) | QUO-1004 from excluded SUP-05 reported as informational and left out of the ranking; H1, confirm SUP-01, draft, H2 |
| 1c Trace 1 on today's date | S4: every synthetic quotation has expired |
| 2 "Portland cement" | S5: matches INV-001 and INV-002; both listed, neither chosen, no tool called |
| 3 Induced tool failure | A: outage, one retry, S2. B: resume from A's saved state to H1; B2: confirm, draft, H2. C: one failure, retry succeeds, H1 |

## Gaps found and fixed

Checking the merged code against the contract on 12 Oct found these gaps; all were fixed with tests:

| # | Gap | Fix |
|---|---|---|
| 1 | No hand-off H1: drafts were created without officer confirmation | Loop stops at H1; `confirm_supplier()`; router refuses unconfirmed drafts (`SUPPLIER_NOT_CONFIRMED`) and records the confirming officer on the draft |
| 2 | `lookup_policy` never called; S6 impossible | Step 2 looks up both rules; `POLICY_NOT_FOUND` stops the case |
| 3 | A stopped case could not be resumed | `run_agent(state=...)`, with a new iteration count and retry allowance |
| 4 | Stops were not written to the trace or audit log | Every run is persisted |
| 5 | The model-driven loop counted rounds, kept going after a block and had no retry limit | Same controls as `run_agent` |
| 6 | Stop reasons did not use the contract's codes | Every stop also carries its contract code (`src/agent/stop_codes.py`) |
| 7 | Ambiguous item hand-off did not list the candidates | `run_agent(item_description=...)` matches inventory names and lists the candidates |
| 8 | No role check on approval (US-09) | Role registry and state-machine check; refusals logged |
| 9 | The reference cement case could not reach a draft: an already-excluded quotation was a blocking flag | **Decision:** `EXCLUDED_SUPPLIER` is informational; the quotation is still not counted or ranked, and too few valid quotations still block |
| 10 | Synthetic quotations have expired, and the date could not be set through the router | **Decision:** keep the data; `run_agent(as_of_date=...)` is a person-set case input passed by code, not a tool argument, so the model cannot choose a date that revalidates a quotation |

## Still open

- **Tendo's review of contract sections 3, 4 and 8.** They were drafted from the code on 12 Oct because his text was not in the repository. He needs to accept or replace them, and to agree the iteration limit of 6, after which the placeholders in `project-charter.md` and `project-definition.md` are replaced.
- **Owner confirmation of the 12 Oct changes.** Because the owners could not be reached, an independent review was done and recorded in `docs/reviews/week5-change-review.md`. It found one defect, now fixed (the case store skipped the self-approval check), and four minor points. The owners (Isaac, Tendo, Ashley) still need to confirm in that note's last table. No record of Isaac's review of the Week 4 state machine is in the repository yet.
- **Week 3 evaluation after the quotation additions.** Seventeen synthetic quotations (QUO-1011 to QUO-1027) were added so that seven of the nine below-reorder items can reach a draft. Retrieval for the 15 Week 3 questions was compared before and after without the model: 11 are identical, and B1, B4, C1 and C3 differ only in lower-ranked quotation rows. Those four need a Gemini rerun, C3 (a required refusal) in particular.
- **Live Gemini run.** Not run: no Gemini API key is configured on the machine used on 12 Oct. `scripts/run_week4_agent.py` (4 scenarios) and the four Week 3 questions above need about 15 requests, within the free tier's 20 a day. `run_agent` itself calls no model.
- **Demo video.** `scripts/demo_week5.py` was run and its output saved as `evidence/demo/week5/w5-demo-transcript.txt`; a screen recording, like Week 4's, still needs a person.

## Individual contributions (from repository history)

| Member | Week 5 contribution |
|---|---|
| Tendo Caisey (AI Engineering Lead) | Week 5 architecture diagram and first version of the orchestrator in `loop.py` (8 Oct). Contract sections 3, 4 and 8 are assigned to him and awaiting his review |
| Azibo Isaac Alinda | Bounded agent loop `run_agent`: planner, observe step, iteration limit, retry and hand-off package, with tests (9 Oct) |
| Akisa Maria Ashley (Quality/Security Lead) | Stop-condition and allow-list tests (W5-05); trace generator and the first five traces with nine findings (W5-04); SQLite case store, state model and confirmed supplier-preference memory with tests; AI log entry 5 |
| Wakinya Esau John (DevOps/Documentation Lead) | Week 5 evidence: CI, PR and ClickUp screenshots, evidence index and traces README (W5-06, PR #5, merged by jewesau) |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Agent task contract sections 1, 2, 5, 6 and 7 and the draft of 3, 4 and 8 (W5-01); checked the merged code against it and fixed the ten gaps above with tests; the two data decisions; regenerated traces; `scripts/demo_week5.py`; AI log entry 6; this report |

## Next steps (Week 6)

- Tendo to review contract sections 3, 4 and 8 and the iteration limit; replace the charter and project-definition placeholders.
- Isaac and Ashley to review the 12 Oct changes to their files.
- US-12 (memory): connect the confirmed supplier preference to the officer's H1 confirmation, with its own confirmation step.
- Rerun the live Gemini scenarios once the quota allows, now through the controls added to `run_bounded_tool_agent`.
- Plan Week 7 evaluation data, including quotation coverage.

## Conclusion

Week 5 delivered a bounded agent that follows a written contract: six tool calls at most, one retry, ten coded stop conditions, a hand-off package on every stop, and two points where it waits for the officer. Both loops stop on a blocked tool instead of trying another route, every stop is saved to the trace and audit log, and a stopped case resumes without repeating work. Approval is now restricted to approver accounts and cannot be made by the person who prepared the requisition. All 144 tests pass and five traces show the behaviour on real tools, including the project's reference case reaching a draft, and seven of the nine items below reorder level can now reach a draft. What remains is the owners' confirmation of this week's changes, Tendo's review of his contract sections, and a Gemini rerun once an API key is available.
