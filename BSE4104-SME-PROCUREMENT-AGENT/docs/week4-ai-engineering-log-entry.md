# AI Engineering Log — Week 4 Entry

**Project:** BSE4104 SME Procurement Preparation Agent  
**Engineer:** Tendo Caisey — AI Engineering Lead  
**Week:** 4 — Tools and Function Calling  
**Period:** 21–25 September 2026

## 1. AI-assisted artefacts and decisions

### W4-01 — Tool catalogue and schemas
AI assistance was used to structure and refine the Week 4 tool catalogue and explicit tool contracts. The resulting catalogue defines four approved model-facing capabilities:

- `check_reorder_levels`
- `lookup_policy`
- `compare_quotations`
- `create_requisition_draft`

The design keeps validation, business rules, calculations, state changes and side effects in deterministic application code rather than delegating them to the model.

### W4-03 — Function-calling orchestration
AI assistance was used to implement and debug `src/agent/tools_router.py`.

The router:
- registers Gemini-compatible tool schemas;
- maps model function calls to approved Python functions;
- enforces an explicit tool allow-list;
- blocks and traces unauthorized tool requests;
- captures successful and failed tool executions as structured trace events;
- compares model-produced figures with deterministic computed values;
- treats the deterministic computed value as authoritative;
- bounds the number of model/tool rounds;
- returns deterministic tool results to the model without granting autonomous purchasing or approval authority.

A compatibility issue was encountered during live integration around the function-response conversation role. The implementation was adjusted so the model's returned content is preserved and the function response is supplied using the supported conversation structure.

Another implementation issue occurred because existing router tests expected `dispatch_tool()` to return both a result and a trace. The router was revised to preserve that contract while retaining the required trace information.

## 2. Verification

The complete local test suite was run after the Week 4 router changes.

Result:

`49 passed, 10 subtests passed`

The passing suite includes:
- agent integration tests;
- model-client tests;
- deterministic procurement-tool tests;
- quantity validation tests;
- tool-router tests;
- Week 2 baseline tests; and
- Week 3 RAG tests.

## 3. Engineering judgement and controls

The main design decision was to keep the model in the decision/orchestration role while keeping procurement calculations and policy enforcement deterministic.

In particular:
- the model does not calculate authoritative landed cost;
- the model cannot call tools outside the allow-list;
- creating a requisition is limited to a DRAFT/simulated side effect;
- human approval remains the boundary for higher-impact procurement action;
- tool failures are returned as structured errors rather than silently ignored;
- tool execution is traceable for evaluation and debugging.

## 4. AI-generated code ownership

AI-generated suggestions were reviewed against the project requirements, existing interfaces and automated tests. Changes were corrected where they conflicted with the established router/test contract or Gemini tool-calling requirements.

The final implementation was tested locally before acceptance into the project branch.

## 5. Evidence / artefacts

- `src/agent/tools_router.py`
- `docs/architecture/tool-catalogue.md`
- `docs/architecture/week4-architecture.png`
- Week 4 test run: `49 passed, 10 subtests passed`
