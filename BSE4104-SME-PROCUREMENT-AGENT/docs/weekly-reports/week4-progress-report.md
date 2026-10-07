# Week 4 Progress Report — Tools and Function Calling

## Objective

Week 4 moved the agent from answering questions to **requesting actions through controlled tools**. The goal was a small set of declared tools that the model can ask for, a router that decides whether each request may run, and deterministic code that does every calculation and state change. The model still does not make decisions: it cannot select a supplier, approve a requisition, contact a supplier or commit money. The only side effect any tool has is a simulated one, a requisition saved as `DRAFT`.

## What was built

**Tool catalogue (W4-01).** `docs/architecture/tool-catalogue.md` defines four approved tools, each with a purpose, input and output JSON schema, who may call it, its side effect, validation rules and failure behaviour:

| Tool | Role | Side effect |
|---|---|---|
| `check_reorder_levels` | Current application data: reads live stock from `inventory.csv` | None |
| `lookup_policy` | Policy retrieval from the controlled corpus | None |
| `compare_quotations` | Deterministic landed-cost comparison | None |
| `create_requisition_draft` | Creates a `DRAFT` requisition and an audit event | Simulated |

The catalogue states that no tool may approve, purchase, award a supplier or pay. Only a human approver can move a requisition beyond `DRAFT`.

**Deterministic tools (W4-02).** `src/tools/procurement.py` implements the tools. Stock checks, landed cost, quotation validity, supplier exclusion, the minimum-quotation rule and the approval level are all computed in code using `Decimal`, not by the model. `create_requisition_draft` writes a `DRAFT` row to `data/requisitions.csv` and appends an event to `evidence/traces/audit-log.jsonl`. `lookup_policy` (`src/tools/policy.py`) reuses the Week 3 retriever.

**Function-calling router (W4-03).** `src/agent/tools_router.py` registers the four schemas with Gemini 3.6 Flash and is the only component that executes a tool. It:
- blocks any tool not on the allow-list with `TOOL_NOT_ALLOWED`, without running it;
- checks arguments against the schema before dispatch (`TOOL_ARGUMENT_ERROR`) and returns `TOOL_EXECUTION_ERROR` when a tool fails, instead of crashing;
- checks tool output before the model sees it (`TOOL_OUTPUT_INVALID`, naming the failing field);
- recomputes the quotation comparison before creating any draft, refuses on blocking flags, and checks the model's supplier against the computed one;
- stops after two model/tool rounds with `MAX_TOOL_ROUNDS_EXCEEDED`;
- appends every call, allowed or blocked, to `evidence/traces/tool-calls.jsonl`.

**Approval state machine (W4-05).** `src/workflow/state_machine.py` models `DRAFT → PENDING_APPROVAL → APPROVED / REJECTED / QUERIED`. No function moves a requisition from `DRAFT` straight to `APPROVED`, submission is refused while policy blocking flags are unresolved, and approval needs a recorded approver ID. `src/workflow/requisition_store.py` applies these transitions to the saved requisitions and records each one in the audit log. It is not a model tool, so autonomous approval is impossible because the code path does not exist, not just because a rule forbids it.

**Architecture.** `docs/architecture/week4-architecture.md` was rechecked against the code on 7 Oct 2026 and now shows every component as built. `week4-architecture.png` was regenerated from its Mermaid source on the same day, so the diagram and the text match the code. Tendo's original diagram is kept in the repository history.

**Demo (W4-07).** `scripts/demo_week4.py` runs the full tool chain: a reorder check flags INV-001, quotations for it are compared, and a requisition draft is created from the result. The run was recorded in `evidence/demo/week4/w4-07-tool-demo.mp4`.

## Testing (W4-04 and W4-05)

The test suite (`python -m pytest`) runs **87 tests and 10 subtests, and all pass** (run on 7 Oct 2026). CI passes on `main` (`evidence/screenshots/week4/w4-ci-run.png`).

`tests/test_tool_failure_and_authorization.py` covers the four required failure cases:

| Scenario | Result |
|---|---|
| Missing parameter | Clear `TOOL_ARGUMENT_ERROR`, no crash |
| Unauthorized request (attempted approval) | Blocked with `TOOL_NOT_ALLOWED` and traced; no approval tool is exposed to the model |
| Unavailable service | Mocked outage returns `TOOL_EXECUTION_ERROR` and does not hang |
| Unexpected tool response | Rejected with `TOOL_OUTPUT_INVALID`, naming the failing field. A draft reported in any state other than `DRAFT` is also rejected |

`tests/workflow/test_state_machine.py` has 12 tests, including the required attempted illegal `DRAFT → APPROVED` transition. It also covers every other illegal transition, refusal while blocking flags are unresolved, and empty or missing approver IDs. The raw run log is in `evidence/traces/week4/w4-04-w4-05-test-run.md`.

`tests/test_week4_gap_fixes.py` (16 tests) and two new output-validation tests in the W4-04 file cover the fixes listed in the next section.

## Gaps found and fixed

Checking the code against the tool catalogue on 27 Sep and 7 Oct found eight gaps. All eight were fixed on 7 Oct, each with tests:

| # | Gap | Fix |
|---|---|---|
| 1 | `lookup_policy` took a case value instead of a topic and never read the policy | New `lookup_policy(topic)` on the Week 3 retriever and threshold. Returns section, rule and source, or the Week 3 refusal. Live check: "approval thresholds" → §5, "how many quotations are required" → §2, "office party budget" → refused |
| 2 | The model-vs-computed check existed but was never called | Run on every draft request: the model's supplier must match the computed recommendation (`MODEL_VALUE_MISMATCH`). Results are returned as `model_checks` |
| 3 | Tool traces were kept only in memory | Every call is appended to `evidence/traces/tool-calls.jsonl` with a run ID |
| 4 | Tool output was not validated | Output must be JSON-serializable and contain its contract fields (`TOOL_OUTPUT_INVALID`). Akisa's W4-04 test was rewritten from documenting the gap to asserting the rejection |
| 5 | Blocking flags never reached the draft tool | The router recomputes the comparison and refuses with `POLICY_BLOCKING_FLAGS`. Live check: a draft for INV-001 today is refused because every quotation has expired |
| 6 | Drafts were written into the RAG corpus | Drafts now go to `data/requisitions.csv`; demo draft `REQ-2026-0002` was moved there |
| 7 | State machine was not connected to stored requisitions | `requisition_store.py` loads, transitions, saves and audits; human-only |
| 8 | Policy §3.4 lead-time tie-break was not implemented | Within 2% on landed cost, the shorter lead time is now preferred |

The catalogue also asked whether an item exactly at its reorder level should be flagged. US-01 says it should not, which is what the code does, so the catalogue was corrected.

## Still open

- **End-to-end Gemini run.** `scripts/run_week4_agent.py` sends four scenarios (reorder check, policy lookup, compare-and-draft, approval attempt) through the full agent and saves the result to `evidence/traces/week4/w4-live-agent-run.json`, with every tool call in `evidence/traces/tool-calls.jsonl`. It was run twice on 7 Oct. Every request failed on Google's side: first with `503 UNAVAILABLE` ("high demand"), then with `429 RESOURCE_EXHAUSTED` once the free tier's 20 daily requests were used. The tools themselves were checked live without the model (see gaps 1 and 5), and the agent loop is covered by mocked tests. The script will be rerun when the quota resets, and the output will be added as evidence.
- **Owner review of the state machine (planned for Week 5).** It was drafted with AI assistance while Isaac's machine was unavailable (AI Engineering Log, entry 3). Isaac will review and take ownership of it, together with `requisition_store.py`, as part of his Week 5 work. Until then it is accepted provisionally.

## Individual contributions (from repository history)

| Member | Week 4 contribution |
|---|---|
| Tendo Caisey (AI Engineering Lead) | Tool catalogue and schemas (W4-01, with Mable); function-calling router with allow-list, error handling, bounded loop and tracing (W4-03); Week 4 architecture diagram; Week 4 AI engineering log entry |
| Azibo Isaac Alinda | Deterministic procurement tools: reorder check, quotation comparison, policy rules and requisition draft (W4-02) |
| Akisa Maria Ashley (Quality/Security Lead) | Failure and authorization tests, including the output-validation gap (W4-04); approval state machine and its 12 tests (W4-05); test evidence and AI log entry 3 |
| Wakinya Esau John (DevOps/Documentation Lead) | Tool demo script and recording (W4-07); Week 4 evidence screenshots for CI, PRs and ClickUp; removed duplicate demo rows; reviewed and merged PRs #3 and #4 (W4-08) |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Refined the tool catalogue against the code and marked each gap (W4-01, with Tendo); Week 4 architecture text version; fixed the eight gaps above (`lookup_policy`, router checks, trace file, draft location, requisition store, §3.4 tie-break) with 18 tests; live agent runner `scripts/run_week4_agent.py`; regenerated the Week 4 architecture diagram; removed the misplaced duplicate `state_machine.py`; this report |

## Next steps (Week 5 candidates)

- Rerun `scripts/run_week4_agent.py` once the Gemini quota resets and commit the trace as evidence.
- Isaac to review and take ownership of `state_machine.py` and `requisition_store.py` (his Week 5 task).
- Carry over from Week 3: section-level citations, threshold calibration, and stopping structured lookups from bypassing the threshold.

## Conclusion

Week 4 delivered a tool-using agent with four declared tools, a router that blocks anything not on the allow-list and checks both what goes into a tool and what comes out, deterministic calculations, and a simulated-only side effect. A draft is created only when the router's own recomputation shows no blocking flags and agrees with the model's supplier. An approval state machine, reachable only by a person, makes autonomous approval impossible by design. All eight gaps found while checking the code against the catalogue were fixed with tests, and all 87 tests pass. What remains is the end-to-end Gemini run, blocked by the API quota on 7 Oct, and Isaac's review of the state machine, scheduled for Week 5.
