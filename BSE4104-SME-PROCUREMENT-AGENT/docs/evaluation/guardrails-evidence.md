# Guardrail Evidence (W7-05)

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep)
**Owners:** Akisa Maria Ashley + Azibo Isaac Alinda
**Status:** Draft 22 Oct 2026. Sections marked **TO FILL** need a live run or the owner's confirmation.

Every guardrail below is enforced **in code, not in a prompt**. A prompt rule is listed only where it is a second layer behind a code control, and it is marked as such. Each row gives the code, the test that proves it, and the evaluation scenario that exercises it (`final-scenarios.md`).

## 1. Summary

| # | Guardrail | Where enforced | Proven by | Scenario | Status |
|---|---|---|---|---|---|
| G1 | Quantity validated before any tool or model call | `src/validation.py::validate_quantity`, called from `src/agent/loop.py::_quantity_error` and `run_agent` | `tests/agent/test_quantity_guardrail.py`, `tests/test_quantity_validation.py` | E05 | Enforced (added 22 Oct) |
| G2 | Item code must exist | `check_reorder_levels` returns `not_found`; planner stops `ITEM_NOT_FOUND` (S5) | `tests/test_agent_loop.py` (`ItemDescriptionTests`) | X04, E04 | Enforced. **No format check** on `item_id` (see 3.2) |
| G3 | Tool arguments checked against the declared schema | `src/agent/tools_router.py::_validate_arguments` | `tests/test_tool_failure_and_authorization.py` | T03 | Enforced |
| G4 | Tool output checked (schema, authority) before use | `tools_router.py::_validate_output`; `TOOL_OUTPUT_INVALID` | `tests/test_tool_failure_and_authorization.py` (output tests) | T03 | Enforced |
| G5 | Tool allow-list | `tools_router.py::dispatch_tool`, `TOOL_REGISTRY`; blocked as `TOOL_NOT_ALLOWED` (S3), never retried | `tests/agent/test_stop_conditions_and_allowlist.py` | U03, A03 | Enforced |
| G6 | Iteration limit | `src/agent/loop.py::_run_loop` (`ITERATION_LIMIT_REACHED`, S1) | same file, `IterationLimit` tests | X01 | Enforced |
| G7 | Approval control: no approval capability for the agent; role and preparer checks | `src/workflow/state_machine.py::_check_approver`; no approve tool in `TOOL_REGISTRY` | `tests/workflow/`, `test_no_approval_capability_is_exposed_to_the_model` | A03, U01, U02 | Enforced |
| G8 | Human confirmation (H1) before a draft | `tools_router.py` `SUPPLIER_NOT_CONFIRMED` check | `tests/test_agent_integration.py`, `tests/memory/test_memory_controls.py` | A04, X03 | Enforced |
| G9 | Model value must equal computed value | `tools_router.py::check_model_vs_computed` (`MODEL_VALUE_MISMATCH`, S7) | `tests/test_tool_failure_and_authorization.py` | I03 | Enforced |
| G10 | Instructions inside quotation letters treated as data | Code: model output is validated and cannot approve or draft (G5, G7, G8, G9). Prompt (second layer): `prompts/quotation_extraction_v1.2.txt` lines 39-47 | Adversarial scenarios A01, A02 | A01, A02 | **TO FILL**: live run needed |

## 2. Evidence per guardrail

### G1 Quantity validation (US-02 AC3, AI boundary matrix rows 1 and 15)

**Before (19 Oct):** `validate_quantity()` existed but was only called from its own test. A zero, negative or non-numeric quantity reached the tools and the agent made five tool calls before stopping at S2. Recorded as E05's expected failure and as FC-01 in the Failure Catalogue.

**After (22 Oct):** `run_agent` validates a new case's quantity before the loop starts. An invalid value returns a hand-off `INVALID_QUANTITY` (contract S5), `iteration_count` 0 and an empty trace. A missing quantity (`None`) is not treated as invalid; the planner's existing `QUANTITY_CONFIRMATION_REQUIRED` stop handles it. A resumed case is not re-validated.

Rejected inputs (all from `tests/agent/test_quantity_guardrail.py`): `0`, `-5`, `"abc"`, `True`, `"  "`. The test patches `dispatch_tool` to raise if called, so a pass proves no tool ran.

```
$ python -m src.eval.run --smoke --only E05
E05  PASS    0.00 s  S5 INVALID_QUANTITY | S5 INVALID_QUANTITY | S5 INVALID_QUANTITY
```

### G2 Item codes

An unknown item code reaches `check_reorder_levels`, which returns `not_found`, and the planner stops `ITEM_NOT_FOUND` (S5) with no further tool call. Free-text descriptions go through `match_items`: one match selects, several stop `AMBIGUOUS_ITEM`, none stops `ITEM_NOT_FOUND`; the loop never chooses between candidates (E04).

### G3 and G4 Boundaries between the model and the tools

`_validate_arguments` rejects unexpected and missing arguments before dispatch. `_validate_output` rejects non-serialisable output, output missing a contract field, and a draft tool that returns an APPROVED state (the tool may not exceed its authority). Output failures return `TOOL_OUTPUT_INVALID`, are retried once, then stop at S2 (scenario T03).

### G5 and G6 Allow-list and iteration limit

A tool not in `TOOL_REGISTRY` is blocked before execution, logged to the run trace and the persistent tool trace, never retried, and ends the run at S3. The limit counts tool calls including retries and blocked calls, defaults to the contract value and can be set with `MAX_AGENT_ITERATIONS`. Halting leaves the case state unchanged (tests listed above).

### G7 and G8 Approval and confirmation

`_check_approver` raises `UnauthorisedActionError` unless the actor has the approver role and did not prepare the requisition. The router has no approve, reject or send tool. A draft cannot be created without a named officer's H1 confirmation of that supplier. `tests/memory/test_memory_controls.py::test_nothing_in_src_calls_confirm_supplier` pins that only officer-facing code may call `confirm_supplier`.

> **Known issue (FC-02):** this test currently fails because `src/eval/run.py` calls `confirm_supplier`. The guardrail itself is intact; the runner needs to move or the test needs a documented exception.

### G9 Computed value stays authoritative

If a model-named supplier or figure differs from the computed one, the draft is refused as `MODEL_VALUE_MISMATCH` and both values are recorded (I03).

### G10 Prompt injection

Code controls: a letter's text cannot cause an approval, a draft, an email or a tool outside the allow-list, because those actions are blocked or need an H1 confirmation in code (G5, G7, G8). Prompt layer: the extraction prompt states that everything inside `<QUOTATION>` is untrusted data. **TO FILL:** run A01 and A02 live (about 3 to 4 Gemini requests), then paste here the extracted validity (must be 7 days, not 90), the absence of any recommendation or draft, and A02's answer text.

## 3. Test output

Run from the project root on 22 Oct 2026:

```
$ python -m pytest -q tests/agent tests/test_tool_failure_and_authorization.py tests/workflow \
    tests/test_quantity_validation.py tests/test_agent_loop.py tests/observability \
    tests/test_preference_isolation.py
115 passed, 131 subtests passed

$ python -m pytest -q tests --ignore=tests/test_week3_rag.py --ignore=tests/test_model_client.py
1 failed, 189 passed, 171 subtests passed
FAILED tests/memory/test_memory_controls.py::NoWriteWithoutConfirmationTests::test_nothing_in_src_calls_confirm_supplier
```

**TO FILL:** re-run the full suite once FC-02 is fixed and paste a clean result. `test_week3_rag.py` and `test_model_client.py` were not run here; run them on a machine with the embedding model and add the output.

### 3.2 Gaps to state honestly in the Week 7 report

1. `item_id` has no format check (for example `INV-\d{3}`); an unknown code is caught only by lookup. This is safe but not an input validator in the strict sense. Azibo to decide whether to add one.
2. Submit has no role check: an approver account can submit a draft (Week 5 review, finding 3, accepted).
3. A refused approval on the case-store path is not written as a refusal event (Week 5 review, finding 2, open).
4. A rule-based planner replays a failed call with the same arguments; only the model loop can correct arguments (Week 5 review, finding 5, documented).
