# Guardrail Evidence (W7-05)

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep)
**Owners:** Akisa Maria Ashley + Azibo Isaac Alinda
**Status:** Draft 22 Oct 2026. Sections marked **TO FILL** need a live run or the owner's confirmation. Code references below were checked against the Week 7 agent loop and Week 4 approval state machine.

The table distinguishes implemented code controls from prompt-level mitigations and evidence still pending. A test proves only the behavior it exercises; it does not establish broader controls that the code does not implement.

## 1. Summary

| # | Guardrail | Where enforced | Proven by | Scenario | Status |
|---|---|---|---|---|---|
| G1 | Supplied quantity validated before the planner/tool loop, on new and resumed cases | `src/validation.py::validate_quantity`, called from `src/agent/loop.py::_quantity_error` before `_run_loop` | `tests/agent/test_quantity_guardrail.py`, `tests/test_quantity_validation.py` | E05 | Enforced in PR #16; updated cases include resumed, non-finite and oversized values |
| G2 | Item code must exist | `check_reorder_levels` returns `not_found`; planner stops `ITEM_NOT_FOUND` (S5) | `tests/test_agent_loop.py` (`ItemDescriptionTests`) | X04, E04 | Enforced. **No format check** on `item_id` (see 3.2) |
| G3 | Tool argument names are allow-listed and required values must be present | `src/agent/tools_router.py::_validate_arguments` | `tests/test_tool_failure_and_authorization.py` | T03 | Partial: does not validate argument value types against schema types |
| G4 | Tool outputs must be JSON-serializable, include required fields, and drafts must remain DRAFT | `src/agent/tools_router.py::_validate_output`; `TOOL_OUTPUT_INVALID` | `tests/test_tool_failure_and_authorization.py` (output tests) | T03 | Enforced for these structural and authority checks; general field types/semantics are not validated |
| G5 | Tool allow-list | `tools_router.py::dispatch_tool`, `TOOL_REGISTRY`; blocked as `TOOL_NOT_ALLOWED` (S3), never retried | `tests/agent/test_stop_conditions_and_allowlist.py` | U03, A03 | Enforced |
| G6 | Agent tool-call iteration limit | `src/agent/loop.py::_run_loop` (`ITERATION_LIMIT_REACHED`, S1) | `tests/agent/test_stop_conditions_and_allowlist.py` (`IterationLimitTests`) | X01 | Enforced; halt records stop metadata while preserving case progress |
| G7 | Agent has no approval tool; approve/reject/query decisions require an approver role and a non-preparer | `src/agent/tools_router.py::TOOL_REGISTRY`; `src/workflow/state_machine.py::_check_approver` | `tests/workflow/test_state_machine.py`, `tests/test_agent_integration.py` | A03, U01, U02 | Enforced for decision actions. `submit_for_approval` itself has no actor/role check (see 3.2) |
| G8 | Human confirmation of the computed supplier is required before draft creation | `src/agent/tools_router.py::dispatch_tool`, `SUPPLIER_NOT_CONFIRMED` | `tests/test_week4_gap_fixes.py::test_draft_without_officer_confirmation_is_refused`, `tests/test_agent_integration.py` | A04, X03 | Enforced; FC-02 is fixed by moving the evaluation runner outside `src/`, and the unchanged source-scan test passes |
| G9 | Draft supplier must match the deterministic computed recommendation | `src/agent/tools_router.py::_check_draft_against_comparison`, `check_model_vs_computed` (`MODEL_VALUE_MISMATCH`, S7) | `tests/test_week4_gap_fixes.py::test_supplier_different_from_computed_is_refused` | I03 | Enforced for supplier identity only; other model-provided figures are not checked by this draft pre-check |
| G10 | Quotation-letter instructions are treated as untrusted data | Prompt layer: `prompts/quotation_extraction_v1.2.txt` lines 39-47. Code controls limit available tools and require policy checks and human confirmation for drafts | Adversarial scenarios A01, A02 | A01, A02 | **TO FILL**: no live A01/A02 evidence yet; code controls mitigate impact but do not prove the model treats injected text as data |

## 2. Evidence per guardrail

### G1 Quantity validation (US-02 AC3, AI boundary matrix rows 1 and 15)

**Before (19 Oct):** `validate_quantity()` existed but was only called from its own test. A zero, negative or non-numeric quantity reached the tools and the agent made five tool calls before stopping at S2. Recorded as E05's expected failure and as FC-01 in the Failure Catalogue.

**After (22 Oct):** `run_agent` validates any supplied quantity after restoring/creating the case state and before entering the planner loop. An invalid value returns a hand-off `INVALID_QUANTITY` (contract S5), `iteration_count` 0 and an empty trace. A missing quantity (`None`) follows the planner's existing quantity-confirmation flow. The updated PR #16 branch also rejects non-finite values and validates resumed states.

Rejected inputs include `0`, `-5`, `"abc"`, `True`, whitespace, positive infinity and `"Infinity"`; a resumed state containing an invalid quantity is also covered. The guardrail test patches `dispatch_tool` to raise if called, so a pass proves no tool ran.

```
$ python -m src.eval.run --smoke --only E05
E05  PASS    0.00 s  S5 INVALID_QUANTITY | S5 INVALID_QUANTITY | S5 INVALID_QUANTITY
```

### G2 Item codes

An unknown item code reaches `check_reorder_levels`, which returns `not_found`, and the planner stops `ITEM_NOT_FOUND` (S5) with no further tool call. Free-text descriptions go through `match_items`: one match selects, several stop `AMBIGUOUS_ITEM`, none stops `ITEM_NOT_FOUND`; the loop never chooses between candidates (E04).

### G3 and G4 Boundaries between the model and the tools

`_validate_arguments` rejects unexpected argument names and missing required values before dispatch; it does not enforce each declared JSON type. `_validate_output` rejects non-serialisable output, output missing a required contract field, and a draft tool that returns an APPROVED state (the tool may not exceed its authority); it does not generally validate field types or all field semantics. Output failures return `TOOL_OUTPUT_INVALID`, are retried once, then stop at S2 (scenario T03).

### G5 and G6 Allow-list and iteration limit

A tool not in `TOOL_REGISTRY` is blocked before execution, logged to the run trace and the persistent tool trace, never retried, and ends the run at S3. The limit counts tool calls including retries and blocked calls, defaults to the contract value and can be set with `MAX_AGENT_ITERATIONS`. At a limit stop, the case's progress is preserved while stop reason/outstanding-action metadata is updated.

### G7 and G8 Approval and confirmation

`_check_approver` raises `UnauthorisedActionError` unless the actor has the approver role and did not prepare the requisition; it is used for approve, reject and query decisions. The router has no approve, reject or send tool. A draft cannot be created without a named officer's H1 confirmation of the computed supplier. The evaluation runner (including its simulated officer confirmation) lives in `scripts/eval_runner.py`; `src/eval/run.py` is only a compatibility CLI entry point. The unchanged source-scan test `tests/memory/test_memory_controls.py::NoWriteWithoutConfirmationTests::test_nothing_in_src_calls_confirm_supplier` passes.

> **FC-02 resolved in the PR #16 branch:** the evaluation harness was moved outside application source. The test remains strict and unchanged.

### G9 Computed value stays authoritative

Before draft creation, the router recomputes the quotation comparison and refuses a model-requested recommended supplier that differs from the computed supplier as `MODEL_VALUE_MISMATCH`; the check records both values. This draft pre-check does not compare arbitrary model-generated figures.

### G10 Prompt injection

The extraction prompt states that everything inside `<QUOTATION>` is untrusted data. Code controls constrain the consequences: tools are allow-listed, there is no agent approval tool, and draft creation requires deterministic checks plus H1 human confirmation. These controls mitigate impact but do not prove prompt-injection resistance or guarantee that the model follows the instruction. **TO FILL:** run A01 and A02 live (about 3 to 4 Gemini requests), then paste here the extracted validity (must be 7 days, not 90), the absence of any unauthorized recommendation or draft, and A02's answer text.

## 3. Test output

Run from the project root on 22 Oct 2026 against PR #16 head `0155f3e`:

```
$ python -m pytest tests -q
203 passed, 173 subtests passed

$ python -m src.eval.run --check
Scenarios in final-scenarios.md: 40
Automated in the runner: 12
Exit code: 0
```

**TO FILL:** PR CI must complete successfully. G10 also needs live A01/A02 results; automated scenario coverage does not include those adversarial prompts yet.

### 3.2 Gaps to state honestly in the Week 7 report

1. `item_id` has no format check (for example `INV-\d{3}`); an unknown code is caught only by lookup. This is safe but not an input validator in the strict sense. Azibo to decide whether to add one.
2. Submit has no role check: an approver account can submit a draft (Week 5 review, finding 3, accepted).
3. A refused approval on the case-store path is not written as a refusal event (Week 5 review, finding 2, open).
4. A rule-based planner replays a failed call with the same arguments; only the model loop can correct arguments (Week 5 review, finding 5, documented).
