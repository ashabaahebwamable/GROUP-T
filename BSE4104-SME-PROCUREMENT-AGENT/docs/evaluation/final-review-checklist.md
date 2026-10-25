# Final Review Checklist (W8-01)

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep)
**Coordinator:** Ashaba Ahebwa Mable. **Area leads:** requirements (Mable), app, integration and state (Isaac), prompts, RAG and agent (Caisey), tests and security (Ashley), docs and deploy (Esau).
**Status:** Draft 2026-10-25, checked against `main` at commit `38a97e2`. The traceability table and the tests and security section were prepared from the repository with Claude's help and are to be confirmed by the area lead. Other leads add their sections.

## 1. Traceability: user story to tests to evaluation scenario

Evaluation status is from run `20261023T020535Z` (`docs/evaluation/final-results.md`: 26 of 40 scenarios automated, 25 PASS, 1 FAIL, 14 not run). Unit and integration tests: 194 pass on `main`.

| User story | Automated tests (under `tests/`) | Evaluation scenarios | Gap |
|---|---|---|---|
| US-01 Reorder visibility | test_procurement_tools.py (reorder check) | PASS: E01, E06, N07 | None |
| US-02 Opening a case | test_agent_loop.py (item description), test_quantity_validation.py, agent/test_quantity_guardrail.py | PASS: E04, E05, X04 | None |
| US-03 Reading quotations | test_week2_baseline.py (extraction prompt matrix and schema) | PASS: T03; not run: A01, E02, I01, I02, I04, N10 | Only the tool-failure scenario ran; extraction scenarios not run |
| US-04 Comparable pricing | test_procurement_tools.py (units, tax, delivery), test_week4_gap_fixes.py (lead-time tie-break) | PASS: E03, I03, N01, N03, N05, N06; not run: I01, I02 | Some model-backed scenarios not run |
| US-05 Justified recommendation | test_tools_router.py (model value vs computed), test_preference_does_not_change_ranking.py | PASS: E03, I03, N01, N02, N03; not run: A02, A04 | A02 and A04 (model-backed) not run |
| US-06 Policy flags | test_procurement_tools.py (policy check flags), test_week4_gap_fixes.py (policy lookup) | PASS: N01, N02, N04, X10 | None |
| US-07 Draft and submit | test_week4_gap_fixes.py (draft pre-check, requisition store), workflow/test_state_machine.py, workflow/test_case_store.py | PASS: N01, N02, X08, X09; not run: A04 | Some model-backed scenarios not run |
| US-08 Approving with evidence | workflow/test_state_machine.py (approve, reject, query), workflow/test_state_transitions_and_restart.py | not run: X07 | **No scenario has been run** |
| US-09 Authorisation | workflow/test_state_machine.py (roles), test_tool_failure_and_authorization.py, workflow/test_case_store.py | PASS: U01, U02; not run: A03 | Some model-backed scenarios not run |
| US-10 Honest refusal | test_week3_rag.py (refusal without evidence), test_week4_gap_fixes.py (refuses below threshold) | not run: A02, N08, N09, X05, X06 | **No scenario has been run** |
| US-11 Safe stop | agent/test_stop_conditions_and_allowlist.py, test_agent_loop.py, test_agent_integration.py | PASS: T01, T03, U03, X01; FAIL: T02 | T02 failed: scenario defect, see D-01 |
| US-12 Resuming a case | workflow/test_state_transitions_and_restart.py (restart), memory/test_memory_controls.py | PASS: X02, X03 | None |

**Findings from the trace**

1. Every one of the 12 user stories has at least one evaluation scenario and at least one automated test file.
2. Only `US-02`, `US-09` and `US-12` are cited by ID inside the test files. The test column above was built by hand from test names; adding the story ID to each test's docstring would make the link checkable.
3. **US-08 and US-10 have no executed scenario.** US-08's only scenario, X07, needs no model and should be automated first. US-10's scenarios (N08, N09, A02, X05, X06) all need the model.
4. US-03 (reading quotations) is evidenced only by T03. Its extraction scenarios (N10, E02, I01, I02, I04, A01) are model-backed and not yet run.

## 2. Tests and security review (Ashley)

| Check | Result | Evidence |
|---|---|---|
| Full test suite on `main` | 194 passed, 0 failed (173 subtests), run 2026-10-25; `test_week3_rag.py` and `test_model_client.py` pass in CI | pytest output; CI run on PR #16 |
| Safety rule: nothing in `src/` can call `confirm_supplier` | Enforced by `test_nothing_in_src_calls_confirm_supplier`; the runner now lives in `scripts/` | PR #16 |
| Guardrails enforced in code, not prompts | G1 to G9 enforced in code with tests; G10 (prompt injection) mitigated by code but not yet shown at the model | `docs/evaluation/guardrails-evidence.md` |
| Automatic safety violations in the full run | 0 | `final-results.md` |
| Secrets in git history | None found. Five patterns scanned over all 162 commits on all branches (Google API key, `MODEL_API_KEY` with a value, `sk-` keys, GitHub tokens, private key blocks); `.env` was never tracked; `.env` is in `.gitignore`; `.env.example` holds placeholders only | Scan run 2026-10-25. This is a pattern search, not a dedicated scanner. |
| Authentication | Not implemented: identity is asserted, so anyone supplying an approver's ID is treated as one | Known limitation L-04 |
| Evaluation logs unchanged by a run | Yes: `Repository files changed during the run: none` | `final-results.md` |
| Run made on a committed tree | **No**: run recorded `working tree not clean` | D-04 |

## 3. Defects and gaps to log in ClickUp

| ID | Finding | Severity | Owner | Verify (Ashley) |
|---|---|---|---|---|
| D-01 | T02 fails: its date (2026-09-01) leaves INV-003 with two valid quotations, so S4 is correct. Scenario defect; correct the date to 2026-08-27 and record it in `criteria.md` section 7 | Medium | Caisey | Re-run T02 |
| D-02 | 14 scenarios not run, including all four adversarial ones (A01 to A04). Prompt-injection resistance (G10) has no model-level evidence | **Critical** | Caisey | Re-run and review |
| D-03 | X07 (US-08) needs no model and is not automated, so US-08 has no executed scenario | High | Caisey | Re-run |
| D-04 | Results were recorded on a dirty working tree | Medium | Caisey | Re-run on a committed tree |
| D-05 | Commit `d74db42` is titled "integration tests" but changes production code (input normalisation in `state_machine.py` and `case_store.py`) and adds no tests. It is not in the AI log | Medium | Ashley, Isaac | Add tests (for example an approver ID with surrounding spaces) and an AI log entry if AI helped |
| D-06 | Retrieval failures FC-04, FC-05, FC-06 are open (clause-level citations, uncalibrated threshold, structured-lookup bypass) | Medium | Isaac, Caisey | Fix, or document as limitation L-06 |
| D-07 | `item_id` has no format check; unknown codes are caught only by lookup | Low | Isaac | Document, or add |

**Critical defects** are those that prevent a claim in the final report from being evidenced. Only D-02 is critical today.

## 4. Sign-off

| Area | Lead | Reviewed (date) | Notes |
|---|---|---|---|
| Requirements | Mable | | |
| App, integration, state | Isaac | | |
| Prompts, RAG, agent | Caisey | | |
| Tests and security | Ashley | | |
| Docs and deploy | Esau | | |
