# Week 5 Agent Task Contract

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep)
**Week:** 5 — Bounded Agent Loop
**Owners:** Ashaba Ahebwa Mable (sections 1, 2, 5, 6, 7) · Tendo Caisey (sections 3, 4, 8)
**Status:** Draft. Mable's sections are written and need Tendo's review. Tendo's sections are still to be written. Items needing agreement from both are listed in section 9.

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

## 2. Maximum iterations (Mable)

**Proposed limit: 6 tool calls per agent run, with at most 1 retry per failed tool call. The retry counts towards the 6.**

| Basis | Detail |
|---|---|
| Unit counted | One **tool call** dispatched by the router, allowed or blocked. The charter defines the limit as "tool-call iterations". |
| Happy path | Steps 1–3 and 5 need 4 to 5 calls: reorder check, 1 or 2 policy lookups (quotation minimum, approval threshold), comparison, draft. |
| Headroom | 6 leaves room for one retry (`MAX_TOOL_RETRIES=1`, US-11 criterion 2) without allowing a second loop over the same work. |
| Resuming after a hand-off | A resumed run starts a new count of 6. The case state carries over; the counter does not. |
| Model-call budget | Each tool call needs a model turn, so one full case uses about 7–9 Gemini requests. The free tier allows 20 a day, about two full cases. That is enough for the three Week 5 traces only if runs are planned. |
| Already configured | `.env.example` has `MAX_AGENT_ITERATIONS=6` and `MAX_TOOL_RETRIES=1`. Neither is read by the code yet (section 8). |

The charter and project definition still say "[PLACEHOLDER: proposed 6]", and there is no Week 2 sign-off for it in the repository. Once Tendo agrees, this section is the sign-off, and both placeholders are replaced with 6.

## 3. Approved tools (Tendo)

*To be written by Tendo.* For each of the four tools: when the agent may call it, its precondition, and what it adds to the case state. Contracts are in `tool-catalogue.md`; this section adds the order and preconditions for the loop. In particular, `create_requisition_draft` may be called only after hand-off H1 has recorded a confirmed supplier.

## 4. State fields (Tendo)

*To be written by Tendo.* The case state carried between steps and kept on every stop: item, quantity and unit, policy evidence, comparison result, blocking flags, confirmed supplier and confirming officer, draft ID, tool-call count, retry count, last error, stop reason. For each field, state whether it is set by code or by a person. The model sets none of them directly.

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
| S4 | **Policy override needed.** The comparison returned blocking flags (`POLICY_BLOCKING_FLAGS`), for example too few valid quotations, an expired quotation or an excluded supplier. Only a person can resolve or override a rule. | US-06, US-07 criterion 3, project definition §11 |
| S5 | **Required input missing or nothing to do.** The item is unknown or ambiguous, the quantity or unit is missing, or no item is below its reorder level. | Matrix rows 1 and 15, charter |
| S6 | **Policy not found.** `lookup_policy` returned `no_evidence` for a rule the case needs (quotation minimum or approval threshold). | US-10, matrix row 17 |
| S7 | **Model disagrees with computed value.** The router returned `MODEL_VALUE_MISMATCH`, so the model asked for a draft with a supplier other than the computed recommendation. | Principle 1, US-05 criterion 1 |
| S8 | **Model unavailable or unusable.** The model API failed after its own retry (for example quota or 503), or returned no usable response. | Matrix row 18 |

**Not a stop:** `TOOL_ARGUMENT_ERROR` on the first attempt. The error goes back to the model, which may correct its arguments once. That correction is the retry; a second argument error is S2.

**Retry rule.** Only S2 and the argument-error case above allow a retry, and only one. S3 to S7 are never retried, because retrying them would mean the agent working around a control.

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

## 7. Prohibited actions (Mable)

Restated from the brief and the AI boundary matrix. "Status" records whether the control exists in code today (7 Oct 2026).

| Prohibited action | Matrix row | How it is prevented | Status |
|---|---|---|---|
| **Purchase**: issuing a purchase order or committing funds | 11, 12 | No purchasing or payment capability exists anywhere in the system (ABS). | Holds: no such tool or code path |
| **Supplier contact** through any channel | 10, Principle 3 | No email, messaging or network channel to a supplier exists (ABS). The only outbound connections are to the Gemini API and, on first use, the Hugging Face download of the embedding model. | Holds |
| **Approval**: approving, rejecting or querying a requisition | 8, 13, 14 | The state machine has no `DRAFT` → `APPROVED` path, approval requires an approver ID, and `requisition_store` is not a model tool (FSM, ALLOW). | Holds. Role check (officer vs approver, US-09) not yet built |
| **Memory write without confirmation** | 19 | Any durable preference is written only after explicit human confirmation, recorded with the confirming identity and timestamp (CODE, LOG). | Holds by absence: no memory feature exists yet. Must be enforced when US-12 is built in Week 6 |
| Confirming the supplier or submitting on the officer's behalf | 5, 10 | Hand-offs H1 and H2; the draft tool requires a confirmed supplier. | **Not yet enforced**: the router creates drafts without officer confirmation (section 9) |
| Using a model-produced figure | 4, Principle 1 | Figures come only from deterministic tools; the router refuses a supplier that differs from the computed one. | Holds for the supplier; full numeral check planned for Week 8 |
| Calling a tool outside the allow-list | 9 | Router allow-list (ALLOW); the run then stops (S3). | Allow-list holds; stop-on-block to be built |

## 8. Enforcement mapping (Tendo)

*To be written by Tendo.* For each stop condition in section 5 and each prohibited action in section 7, name the code that enforces it and whether it exists yet. Known gaps from section 9 should appear here as build items for "Implement the bounded agent loop".

## 9. Decisions and gaps for Tendo to confirm

1. **Iteration limit of 6 tool calls, 1 retry** (section 2). Agree, then remove the placeholders in `project-charter.md` and `project-definition.md`.
2. **The loop counts model rounds, not tool calls.** `run_bounded_tool_agent` uses `max_tool_rounds=2`, and one round can contain several tool calls. It needs to count tool calls and read `MAX_AGENT_ITERATIONS` and `MAX_TOOL_RETRIES` from the environment.
3. **Hand-off H1 is missing.** The router will create a draft without an officer-confirmed supplier. `create_requisition_draft` should require a confirmed-supplier record from H1.
4. **A blocked tool request does not stop the run** (S3). Today the error is returned to the model and the loop continues.
5. **No retry logic and no hand-off package.** Errors go back to the model with no retry count, and the result has no stop code or saved case state.
6. **Role check for approval** (US-09) is not built. This sits with Isaac's state-machine review.
