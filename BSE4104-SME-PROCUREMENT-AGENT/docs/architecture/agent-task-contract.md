# Week 5 Agent Task Contract

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep)
**Week:** 5 — Bounded Agent Loop
**Owners:** Ashaba Ahebwa Mable (sections 1, 2, 5, 6, 7) · Tendo Caisey (sections 3, 4, 8)
**Status:** Draft, all sections written. Mable's sections were checked against the Week 5 code on 12 Oct 2026. Sections 3, 4 and 8 were drafted from the code on 12 Oct 2026 because Tendo's text was not in the repository; Tendo reviewed them against the code on 16 Oct 2026 and accepted them, with two wording changes (the section 3 introduction and the section 4 `reorder_result` row). Items needing agreement from both are listed in section 9.

This contract is what the Week 5 agent loop is built and tested against. "Implement the bounded agent loop" codes it, "Stop-condition and allow-list tests" test it, and the three execution traces demonstrate it. Where this contract and the code disagree, the code is wrong until the contract is changed by agreement.

Sources: `project-definition.md` §8 and §11, `project-charter.md` (bounded agency and stop conditions), `ai-boundary-matrix.md`, `user-stories.md` (US-05 to US-09, US-11, US-12), `tool-catalogue.md`.

---

## 1. Goal (Mable)

**Take one flagged stock item from the reorder signal to a requisition in `PENDING_APPROVAL`, awaiting a human approver.**

The agent does not reach that state by itself. Two steps belong to the officer (`project-definition.md` §11, US-05 criterion 3, US-07):

| Step | Done by | Result |
|---|---|---|
| 1. Confirm the item is below its reorder level and get the suggested quantity | Agent → `check_reorder_levels` | Item and quantity in case state |
| 2. Retrieve the policy rules that apply | Agent → `lookup_policy` | Quotation minimum and approval threshold, with sources |
| 3. Compare quotations and get the recommended supplier and blocking flags | Agent → `compare_quotations` | Ranked comparison in case state |
| **Hand-off H1** | Agent stops | Officer sees the recommendation and flags |
| 4. Confirm the recommended supplier | **Officer** | Confirmed supplier recorded with officer ID |
| 5. Create the draft requisition | Agent → `create_requisition_draft` | Requisition in `DRAFT` |
| **Hand-off H2** | Agent stops | Officer sees the draft |
| 6. Submit for approval | **Officer**, through the state machine | Requisition in `PENDING_APPROVAL` |

**The goal is met** when the requisition is in `PENDING_APPROVAL`, the submission is in the audit log with the officer's ID and a timestamp, and the trace shows every agent step.

**Scope.** One stock item per case. If no item is below its reorder level, the case ends at step 1 with nothing to do (stop condition S5).

**What the agent never does.** It never confirms a supplier, submits, approves, rejects or queries. Approval, rejection and query belong to the approver after the goal is met and are outside the agent loop.

**Built (12 Oct).** `run_agent` in `src/agent/loop.py` follows this table. Run 1 does steps 1–3 and stops at H1 (`SUPPLIER_CONFIRMATION_REQUIRED`). The officer confirms with `confirm_supplier()` (step 4), and run 2 resumes from the saved state, does step 5 and stops at H2 (`READY_FOR_HUMAN_APPROVAL`). Step 6 is `submit_for_approval` in the state machine. Checked end to end with the real tools on 12 Oct (INV-003, 460 pieces, quotation date pinned to 27 Aug): run 1 used 4 tool calls and stopped at H1, and run 2 used 1 and stopped at H2.

## 2. Maximum iterations (Mable)

**Proposed limit: 6 tool calls per agent run, with at most 1 retry per failed tool call. The retry counts towards the 6.**

| Basis | Detail |
|---|---|
| Unit counted | One **tool call** dispatched by the router, allowed or blocked. The charter defines the limit as "tool-call iterations". |
| Happy path | Run 1 (steps 1–3) needs 4 calls: reorder check, 2 policy lookups (quotation minimum, approval threshold), comparison. Run 2 (step 5) needs 1: the draft. |
| Headroom | 6 leaves room for one retry (`MAX_TOOL_RETRIES=1`, US-11 criterion 2) without allowing a second loop over the same work. |
| Resuming after a hand-off | A resumed run starts a new count of 6. The case state carries over; the counter does not. Built: `run_agent(state=...)`. |
| Model-call budget | Each tool call needs a model turn, so one full case uses about 7–9 Gemini requests. The free tier allows 20 a day, about two full cases. `run_agent` currently uses a rule-based planner and makes no model calls, so this budget applies once a model planner is connected. |
| Configuration | `.env.example` sets `MAX_AGENT_ITERATIONS=6` and `MAX_TOOL_RETRIES=1`; `src.agent.loop.run_agent` reads these values and allows explicit caller overrides. |

`run_agent` counts each router-dispatched call, including blocked calls and retries, in the preserved `iteration_count`. It retries `TOOL_ARGUMENT_ERROR`, `TOOL_EXECUTION_ERROR` and `TOOL_OUTPUT_INVALID` once by default, then hands off with the error and next action outstanding. The retry counter resets after a successful call, so the limit is one retry per failed call, as specified. This enforcement applies to `run_agent`; the earlier model-facing `run_bounded_tool_agent` remains a separate entry point. Tests: `tests/agent/test_stop_conditions_and_allowlist.py` (iteration limit, never-stopping planner, limit read from the environment).

The charter and project definition still say "[PLACEHOLDER: proposed 6]", and there is no Week 2 sign-off for it in the repository. Once Tendo agrees, this section is the sign-off, and both placeholders are replaced with 6.

## 3. Approved tools (Tendo; reviewed 16 Oct 2026)

The allow-list is the four tools in `TOOL_REGISTRY` (`src/agent/tools_router.py`). Their input and output contracts are in `tool-catalogue.md`. This section adds when the loop may call each one. All four are deterministic. In `run_agent` the rule-based planner (`default_plan`) chooses the next call; in `run_bounded_tool_agent` the model proposes it. In both loops the router validates the arguments and the output.

| Order | Tool | The planner may call it when | It adds to the case state | Side effects |
|---|---|---|---|---|
| 1 | `check_reorder_levels` | An item ID is known and there is no reorder result yet. | `reorder_result` | None (read-only) |
| 2 | `lookup_policy` | The item needs reordering, the quantity is known, and a rule in `POLICY_TOPICS` has no evidence yet. Called once per topic: the quotation minimum and the approval threshold. | `policy_evidence[topic]` | Appends the retrieval to `evidence/traces/retrieval.jsonl` (Week 3 log) |
| 3 | `compare_quotations` | Both policy rules were found and there is no comparison yet. Judged on the case's `as_of_date` | `comparison_result` (with `informational_flags`), `blocking_flags` | None. The router attaches any confirmed supplier preference as `supplier_preference_hint` after ranking |
| 4 | `create_requisition_draft` | The comparison has a recommendation and no blocking flags, an officer has confirmed that exact supplier at H1, a preparing officer ID is known, and no draft exists yet. | `draft_id` | Writes one `DRAFT` row to `data/requisitions.csv` and a `REQUISITION_DRAFT_CREATED` audit event, both recording the confirming officer |

Preconditions the router enforces for the draft, whatever the planner asks for: it recomputes the comparison and refuses the draft if there are blocking flags (`POLICY_BLOCKING_FLAGS`), if the requested supplier differs from the computed one (`MODEL_VALUE_MISMATCH`), or if no officer confirmation for that supplier is passed (`SUPPLIER_NOT_CONFIRMED`). The confirmation is passed by code from the case state. It is not in any tool schema, so the model cannot supply it.

Not tools: `confirm_supplier` (officer, step 4), `record_supplier_preference` (officer, memory), and every state-machine transition (`submit_for_approval`, `approve`, `reject`, `query`, `halt`). Any other tool name is blocked with `TOOL_NOT_ALLOWED` (stop S3).

## 4. State fields (Tendo; reviewed 16 Oct 2026)

The case state is the dictionary built by `initial_case_state()` in `src/agent/loop.py`. Every stop returns it unchanged, and `run_agent(state=...)` accepts it back to resume. The model sets none of these fields directly: a model planner can only propose a tool call or a hand-off.

| Field | Content | Set by |
|---|---|---|
| `item` | `{"item_id": ...}`, or `None` if no item was identified | Person (case input), or code when a description matches exactly one item |
| `item_description`, `item_candidates` | The officer's free-text description, and the matching items when it matches more than one | Person (description); code (`match_items`) |
| `quantity`, `unit` | Requested quantity in base units, and its unit | Person (case input, or when resuming after `QUANTITY_CONFIRMATION_REQUIRED`) |
| `preparing_officer_id` | The officer preparing the requisition | Person (case input) |
| `as_of_date` | Date quotation validity is judged on; `None` means today. Kept across a resume and passed by code to the comparison and the draft pre-check, never a tool argument | Person (case input; evaluations and demos) |
| `reorder_result` | Output of `check_reorder_levels`; added when that tool returns, not in the initial state | Code (tool result) |
| `policy_evidence` | One `lookup_policy` result per topic: status, section, rule text, source | Code (tool result) |
| `comparison_result` | Output of `compare_quotations`, including the recommended supplier and any preference hint | Code (tool result) |
| `blocking_flags` | Blocking flags from the comparison, without duplicates | Code (tool result) |
| `confirmed_supplier` | `supplier_id`, `confirmed_by`, `confirmed_at`, recorded at H1 | Person, through `confirm_supplier()` |
| `draft_id` | Requisition ID of the created `DRAFT` | Code (tool result) |
| `iteration_count` | Tool calls in this run, including blocked calls and retries. Reset to 0 when a run resumes | Code (loop) |
| `retry_count`, `pending_retry` | Retries used for the current failed call, and the call to repeat | Code (loop) |
| `last_error` | Message of the last failed tool call, cleared on success | Code (loop) |
| `tool_history` | Every call in every run of the case: tool, arguments, ok, error | Code (loop) |
| `stop_reason`, `outstanding` | Why the run stopped and the next step, in words | Code (loop and planner rules) |

## 5. Stop conditions (Mable)

The agent halts on any of the following, preserves the case state and hands off (section 6). Codes are used in traces and tests.

**Planned stops: the workflow needs the officer**

| Code | Condition | Source |
|---|---|---|
| H1 | A comparison with no blocking flags has produced a recommended supplier. The officer must confirm it before any draft is created. | US-05 criterion 3, US-07 criterion 1, matrix rows 5 and 10 |
| H2 | A `DRAFT` has been created. The officer must submit it. | US-07 criterion 2, project definition §11 |

**Failure stops: the agent cannot safely continue**

| Code | Condition | Source |
|---|---|---|
| S1 | **Iteration limit.** The sixth tool call has completed and the goal step is not done. | US-11 criterion 1, charter |
| S2 | **Tool failed twice.** A tool returned `TOOL_EXECUTION_ERROR` or `TOOL_OUTPUT_INVALID`, was retried once, and failed again. | US-11 criterion 2, matrix row 18 |
| S3 | **Disallowed request.** The model requested a tool outside the allow-list (`TOOL_NOT_ALLOWED`). The call is blocked and logged, and the run stops instead of letting the model try another route. | US-11 criterion 3, charter |
| S4 | **Policy override needed.** The comparison returned blocking flags (`POLICY_BLOCKING_FLAGS`), for example too few valid quotations or an expired quotation. Only a person can resolve or override a rule. A quotation from an excluded supplier is an informational flag, not a stop: it is already left out of the count and the ranking (agreed 12 Oct, section 9 item 11). | US-06, US-07 criterion 3, project definition §11 |
| S5 | **Required input missing or nothing to do.** The item is unknown or ambiguous, the quantity or unit is missing, or no item is below its reorder level. | Matrix rows 1 and 15, charter |
| S6 | **Policy not found.** `lookup_policy` returned `no_evidence` for a rule the case needs (quotation minimum or approval threshold). | US-10, matrix row 17 |
| S7 | **Model disagrees with computed value.** The router returned `MODEL_VALUE_MISMATCH`, so the model asked for a draft with a supplier other than the computed recommendation. | Principle 1, US-05 criterion 1 |
| S8 | **Model unavailable or unusable.** The model API failed after its own retry (for example quota or 503), or returned no usable response. | Matrix row 18 |

**Not a stop:** `TOOL_ARGUMENT_ERROR` on the first attempt. The error goes back to the model, which may correct its arguments once. That correction is the retry; a second argument error is S2.

**Retry rule.** Only S2 and the argument-error case above allow a retry, and only one. S3 to S7 are never retried, because retrying them would mean the agent working around a control.

**Codes in the code (12 Oct).** Both loops record a descriptive `stop_reason` and, beside it, the contract code from this table (`contract_code` in every result, trace stop line and `AGENT_RUN_STOPPED` audit event; mapping in `src/agent/stop_codes.py`, section 9 item 8).

| Contract code | `stop_reason` | Built? |
|---|---|---|
| H1 | `SUPPLIER_CONFIRMATION_REQUIRED`; `SUPPLIER_NOT_CONFIRMED` when the model asks for a draft | Yes (Traces 1, 1b, 3B and 3C; tests) |
| H2 | `READY_FOR_HUMAN_APPROVAL` | Yes (Traces 1 and 1b; tests) |
| S1 | `ITERATION_LIMIT_REACHED`; `MAX_TOOL_ROUNDS_EXCEEDED` (model loop) | Yes (tests) |
| S2 | `TOOL_FAILED_AFTER_RETRY` | Yes (Trace 3A) |
| S3 | `TOOL_NOT_ALLOWED` | Yes; the run stops and is not retried (tests) |
| S4 | `POLICY_BLOCKING_FLAGS`, `NO_RECOMMENDED_SUPPLIER` | Yes (Trace 1c) |
| S5 | `AMBIGUOUS_ITEM`, `ITEM_NOT_FOUND`, `REORDER_STATUS_UNASSESSABLE`, `MISSING_QUANTITY`, `QUANTITY_CONFIRMATION_REQUIRED`, `MISSING_PREPARING_OFFICER`, `NO_REORDER_REQUIRED` | Yes (Trace 2). `NO_REORDER_REQUIRED` ends with status `stopped`, not `handoff`, because there is nothing to hand off |
| S6 | `POLICY_NOT_FOUND` | Yes (tests) |
| S7 | `MODEL_VALUE_MISMATCH` | Yes, in the router; the rule-based planner cannot trigger it |
| S8 | `MODEL_UNAVAILABLE`, `MODEL_NO_CANDIDATES` (model loop); `INVALID_PLAN_ACTION` (unusable planner output) | Yes (tests) |

Retries differ by loop, as this section intends: in `run_bounded_tool_agent` a failed call goes back to the model, which may correct it once; `run_agent`'s rule-based planner cannot correct arguments, so it replays the same call once.

## 6. Hand-off conditions (Mable)

Every stop, planned or failure, ends with the same hand-off package. Its purpose is that the officer can understand what happened and resume or abandon the case without starting again (US-11 criterion 1, US-12).

| Item in the hand-off | Content |
|---|---|
| Stop code and reason | One of H1, H2, S1–S8, with a plain-language sentence, e.g. "Stopped: QUO-1001 has expired, so fewer than 2 valid quotations remain (policy §2)." |
| What was completed | The steps from section 1 that finished, with their results. |
| What is outstanding | The next step and who must do it: officer, approver or a retry later. |
| Case state | All state fields from section 4 at the moment of the stop, unchanged and saved so the case can resume. |
| Evidence | Tool-call trace (`evidence/traces/tool-calls.jsonl`) for the run, plus policy sources and the comparison. |
| Officer's options | Resume, after confirming the supplier, supplying missing input or resolving a flag. Or abandon, with a reason. |

**Rules for every hand-off**
- The stop and its reason are written to the trace and the audit log. The agent never conceals a failure (matrix row 18).
- Partial state is kept, never discarded or recomputed by the model on resume (success criterion 8).
- The model may write the reason sentence, but the stop code, completed steps and state come from code.
- After a hand-off the agent does nothing further until a person acts.

**Built (12 Oct).** Every `run_agent` stop returns `status`, `reason` (the `stop_reason`), `contract_code`, `message`, `outstanding` (the next step, in words), the full case `state`, the in-memory `trace`, `state_before_last_step` and a `run_id`. Each run appends its tool calls and an `agent_stop` line to `evidence/traces/tool-calls.jsonl`, and an `AGENT_RUN_STOPPED` event to `evidence/traces/audit-log.jsonl`. The officer resumes by passing the saved state back to `run_agent(state=...)`, and abandons with `halt()` in the state machine. Tests confirm the state is kept unchanged on an iteration-limit halt, a hand-off, a missing item, a blocked tool and an exhausted retry. An ambiguous item description lists the candidate items in the hand-off and keeps them in the state (Trace 2). `run_bounded_tool_agent` returns the same package fields (`stop_reason`, `contract_code`, `message`, `outstanding`, trace) and writes an `agent_stop` line. "What was completed" is read from `tool_history` and the trace rather than a separate list.

## 7. Prohibited actions (Mable)

Restated from the brief and the AI boundary matrix. "Status" records whether the control exists in code (checked 12 Oct 2026).

| Prohibited action | Matrix row | How it is prevented | Status |
|---|---|---|---|
| **Purchase**: issuing a purchase order or committing funds | 11, 12 | No purchasing or payment capability exists anywhere in the system (ABS). | Holds: no such tool or code path |
| **Supplier contact** through any channel | 10, Principle 3 | No email, messaging or network channel to a supplier exists (ABS). The only outbound connections are to the Gemini API and, on first use, the Hugging Face download of the embedding model. | Holds |
| **Approval**: approving, rejecting or querying a requisition | 8, 13, 14 | The state machine has no `DRAFT` → `APPROVED` path, approval requires an approver ID, and `requisition_store` is not a model tool (FSM, ALLOW). | **Holds.** No path into `APPROVED` except `approve()` from `PENDING_APPROVAL`. Since 12 Oct approve, reject and query also refuse anyone whose role in `data/users.csv` is not approver, and the person who prepared the requisition; the requisition store logs refused attempts (US-09) |
| **Memory write without confirmation** | 19 | Any durable preference is written only after explicit human confirmation, recorded with the confirming identity and timestamp (CODE, LOG). | **Holds.** `src/memory/supplier_preferences.py`: `record_supplier_preference` refuses unless `confirmed=True` and a confirmer ID is given, and stores the confirmer and a UTC timestamp. It is not a model tool (`tests/memory/test_supplier_preferences.py`). The router attaches the stored preference to the comparison result as a hint after ranking, and `compare_quotations` does not read memory; no test checks this yet |
| Confirming the supplier or submitting on the officer's behalf | 5, 10 | Hand-offs H1 and H2; the draft tool requires a confirmed supplier. | **Holds.** The loop stops at H1, only `confirm_supplier()` (an officer action, not a tool) records a confirmation, and the router refuses a draft without one (`SUPPLIER_NOT_CONFIRMED`). The loop has no submit step and stops at H2 |
| Using a model-produced figure | 4, Principle 1 | Figures come only from deterministic tools; the router refuses a supplier that differs from the computed one. | Holds for the supplier; full numeral check planned for Week 8 |
| Calling a tool outside the allow-list | 9 | Router allow-list (ALLOW); the run then stops (S3). | **Holds in both loops**: the call is blocked before execution and the run stops without retry (tests) |

## 8. Enforcement mapping (Tendo; reviewed 16 Oct 2026)

Where each stop condition and prohibited action is enforced, and the test that shows it. Paths are under `src/` and `tests/`.

**Stop conditions**

| Code | Enforced in | Test | Status |
|---|---|---|---|
| H1 | `agent/loop.py` `default_plan` (stops after the comparison); `agent/tools_router.py` `dispatch_tool` (refuses an unconfirmed draft) | `test_agent_loop.py` (plan-and-observe, supplier confirmation); `test_week4_gap_fixes.py` (draft without confirmation) | Built |
| H2 | `agent/loop.py` `default_plan` | `test_agent_loop.py` (plan-and-observe) | Built |
| S1 | `agent/loop.py` `_run_loop` and `agent/tools_router.py` `_run_tool_loop`, limit from `MAX_AGENT_ITERATIONS` | `agent/test_stop_conditions_and_allowlist.py` `IterationLimitTests`; `test_agent_integration.py` `ModelLoopControlTests` | Built |
| S2 | Both loops, `stop_codes.RETRYABLE_TOOL_ERRORS`, `MAX_TOOL_RETRIES` | `test_agent_loop.py` (retry tests); `test_stop_conditions_and_allowlist.py` (retry exhausted); `ModelLoopControlTests` | Built |
| S3 | `agent/tools_router.py` allow-list; both loops stop on a non-retryable error | `test_stop_conditions_and_allowlist.py` `AllowListTests`; `test_agent_integration.py` | Built |
| S4 | `agent/loop.py` `default_plan`; router refuses a draft with flags | `test_stop_conditions_and_allowlist.py` (hand-off halt); `test_week4_gap_fixes.py` | Built |
| S5 | `agent/loop.py` `default_plan`, `match_items` | `test_agent_loop.py` (ambiguous item, `ItemDescriptionTests`, resume) | Built |
| S6 | `agent/loop.py` `default_plan` (`POLICY_TOPICS`) | `test_agent_loop.py` `PolicyStepTests` | Built |
| S7 | `agent/tools_router.py` `check_model_vs_computed` | `test_week4_gap_fixes.py` (supplier different from computed) | Built in the router |
| S8 | `agent/tools_router.py` `_run_tool_loop` (`MODEL_UNAVAILABLE`, `MODEL_NO_CANDIDATES`); `agent/loop.py` (`INVALID_PLAN_ACTION`) | `ModelLoopControlTests` (model failure) | Built |
| Hand-off package | `agent/loop.py` `run_agent`, `_persist_run`, `_resumable_state` | `test_agent_loop.py` `PersistenceTests`, `ResumeTests`; `test_stop_conditions_and_allowlist.py` `StatePreservedAfterHaltTests` | Built |

**Prohibited actions**

| Action | Enforced in | Test | Status |
|---|---|---|---|
| Purchase, supplier contact | Absence: no such tool or code path | `test_stop_conditions_and_allowlist.py` (`issue_purchase_order`, `make_payment`, `send_supplier_email` blocked) | Holds |
| Approval | `workflow/state_machine.py` (`_check_approver`); roles from `workflow/users.py`; not in `TOOL_REGISTRY` | `test_stop_conditions_and_allowlist.py` (`approve_requisition` blocked); `workflow/test_state_machine.py` `AuthorizationRoleTests`; `test_week4_gap_fixes.py` (refused and logged) | Holds |
| Memory write without confirmation | `memory/supplier_preferences.py` | `memory/test_supplier_preferences.py` | Holds |
| Confirming the supplier for the officer | `agent/loop.py` `confirm_supplier`; `agent/tools_router.py` (`SUPPLIER_NOT_CONFIRMED`) | `test_agent_loop.py` `SupplierConfirmationTests`; `test_week4_gap_fixes.py` | Holds |
| Model-produced figure | `agent/tools_router.py` `check_model_vs_computed` | `test_week4_gap_fixes.py` | Holds for the supplier; numerals in Week 8 |

## 9. Decisions and gaps for Tendo to confirm

1. **Iteration limit of 6 tool calls, 1 retry** (section 2). Agree, then remove the placeholders in `project-charter.md` and `project-definition.md`.
2. ~~**The model-facing loop still counts rounds, not tool calls.**~~ Built 12 Oct: `run_bounded_tool_agent` counts tool calls against `MAX_AGENT_ITERATIONS` (S1); the round limit stays as a second bound.
3. ~~**Hand-off H1 is missing.**~~ Built 12 Oct: `default_plan` stops at H1, `confirm_supplier()` records the officer, and the router refuses a draft without that confirmation. Through `run_bounded_tool_agent` a draft is now always refused, because the model cannot supply the confirmation.
4. ~~**A blocked tool request does not stop the model-facing run.**~~ Built 12 Oct: it stops at S3 and the model is not asked again.
5. ~~**The model-facing loop has no retry logic or hand-off package.**~~ Built 12 Oct: one correction per failing tool, then S2; any other refusal stops; model failures stop at S8; every stop returns the hand-off fields and is written to the trace.
6. ~~**Role check for approval** (US-09).~~ Built 12 Oct: roles come from `data/users.csv` (synthetic accounts), and the state machine refuses non-approvers and self-approval. Isaac still owns the state-machine review and should check this change.

Added on 12 Oct after checking the merged Week 5 code and traces (`evidence/traces/week5/README.md`, findings 1–9):

7. ~~**`lookup_policy` is never called.**~~ Built 12 Oct: step 2 looks up the quotation minimum and the approval threshold, and stops with `POLICY_NOT_FOUND` (S6) when either has no evidence.
8. ~~**Stop codes.**~~ Built 12 Oct: both kept. The descriptive `stop_reason` stays (it says which case), and every stop also carries its contract code (`src/agent/stop_codes.py`).
9. ~~**`run_agent` cannot resume.**~~ Built 12 Oct: `run_agent(state=...)`.
10. ~~**Stops are not persisted.**~~ Built 12 Oct: tool trace and audit log. The `expectedFailure` marker was removed.
11. ~~**An already-excluded quotation blocks the whole case.**~~ Decided 12 Oct: `EXCLUDED_SUPPLIER` is an informational flag (`informational_flags` in the comparison). The quotation is still not counted or ranked, and too few remaining valid quotations still block. The reference cement case now reaches a draft (Trace 1b).
12. ~~**Quotation data is stale.**~~ Decided 12 Oct: keep the synthetic data and set the date explicitly. `run_agent(as_of_date=...)` is a person-set case input passed by code to the comparison and the draft pre-check (section 4). On the real clock every case still stops at S4 (Trace 1c), which is correct.
13. ~~**The Week 5 traces predate items 3, 7, 9 and 10.**~~ Regenerated 12 Oct: Trace 1 shows H1, the officer's confirmation and a resume to H2; Trace 3 phase B resumes from phase A's saved state; every trace lists its persisted audit events.
14. **Open: quotation coverage.** Only 4 of the 15 inventory items (INV-001, 003, 005, 006) have any quotation, so most reorder signals stop at S4 or `NO_RECOMMENDED_SUPPLIER`. Adding synthetic quotations changes the shared data set used by the Week 3 evaluation, so it is left for the Week 7 evaluation planning.
