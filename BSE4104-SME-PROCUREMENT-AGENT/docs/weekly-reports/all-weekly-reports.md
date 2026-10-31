# ReqPrep — Consolidated Weekly Progress Reports (Weeks 1–7)

BSE4104 Emerging Trends in Software Engineering · GROUP-T · SME Procurement-Preparation Agent (ReqPrep)

This file merges the seven weekly progress reports into one document, in order and unedited apart from heading levels. The individual files in this folder remain the source of record. The Week 8 work (hardening and the final release) is reported in `docs/final-engineering-report.docx`.

## Overview

| Week | Theme | Main deliverable | Tests passing at end of week |
|---|---|---|---|
| 1 | Problem framing and AI-native requirements | Charter, 12 user stories, AI Boundary Matrix, context diagram, synthetic data design | — |
| 2 | Foundation-model engineering and prompting | Gemini 3.6 Flash quotation extractor; prompts v1.0–v1.2; 10-case live evaluation | 4 |
| 3 | Context engineering and grounded RAG | Loader, chunker, query router, semantic search, citation-checked answers; 15/15 RAG evaluation | 32 |
| 4 | Tools and function calling | 4 allow-listed tools, function-calling router, approval state machine | 87 (+10 subtests) |
| 5 | Bounded agent architecture | Agent task contract, bounded loop with H1/H2 hand-offs and S1–S8 stops, role checks | 144 (+17 subtests) |
| 6 | State, memory and interoperability | SQLite case store surviving restart, confirmed supplier-preference memory, MCP-style spec | 187 (+166 subtests) |
| 7 | Evaluation, observability and guardrails | 40 scenarios, signed criteria, eval runner, structured traces, guardrails, failure catalogue | 203 (+173 subtests) |

## Contents

1. [Week 1 — Problem Framing and AI-Native Requirements](#week-1-progress-report)
2. [Week 2 — Foundation Model Engineering and Prompting](#week-2-progress-report--foundation-model-engineering-and-prompting)
3. [Week 3 — Context Engineering and Grounded RAG](#week-3-progress-report--context-engineering-and-grounded-rag)
4. [Week 4 — Tools and Function Calling](#week-4-progress-report--tools-and-function-calling)
5. [Week 5 — Bounded Agent Loop](#week-5-progress-report--bounded-agent-loop)
6. [Week 6 — State, Memory and Interoperability](#week-6-progress-report--state-memory-and-interoperability)
7. [Week 7 — Evaluation, Observability and Guardrails](#week-7-progress-report--evaluation-observability-and-guardrails)

The Week 1 evidence plan is kept separately in `week1-evidence-checklist.md`.

---

## Week 1 Progress Report

> Reconciliation draft prepared 8 September 2026 from the repository state. Items
> requiring team or ClickUp confirmation are recorded as pending, not claimed as complete.

|                 |                                                                                                          |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| Group / project | Group identifier pending confirmation — SME Procurement-Preparation Agent (working name: ReqPrep)        |
| Course          | BSE4104 Emerging Trends in Software Engineering                                                          |
| Week            | Week 1 — Problem Framing and AI-Native Requirements                                                      |
| Week ending     | 4 September 2026                                                                                         |
| Members         | Azibo Isaac Alinda — individual Week 1 repository work; remaining members and roles pending confirmation |
| Repository      | https://github.com/ashabaahebwamable/GROUP-T                                                             |
| ClickUp board   | Pending: board URL and task activity were not available in the repository                                |

### 1. Work completed against weekly objectives

The brief's Week 1 objectives are: select one feasible use case, define users and success criteria, justify AI use, and set the boundaries of the agent.

| Objective                                      | Status                                      | Artefact                                     | Note                                                                    |
| ---------------------------------------------- | ------------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------- |
| Use case selected                              | Complete locally; team confirmation pending | `docs/requirements/project-definition.md`    | SME procurement-preparation agent                                       |
| Single primary workflow defined                | Complete                                    | `project-charter.md` §7                      | Reorder signal to approved requisition, one item per case               |
| Project Charter (2-3 pages)                    | Draft complete; team review pending         | `docs/requirements/project-charter.md`       | Contains scope, AI boundary, workflow, assumptions and success criteria |
| 8-12 user stories with acceptance criteria     | Complete locally; team review pending       | `docs/requirements/user-stories.md`          | 12 stories with Given/When/Then criteria and test methods               |
| AI Boundary Matrix                             | Complete locally; team review pending       | `docs/requirements/ai-boundary-matrix.md`    | 20 activity rows with enforcement mechanisms                            |
| Initial architecture / context diagram         | Source complete; rendered PNG pending       | `docs/architecture/week1-context-diagram.md` | ASCII and Mermaid versions are committed                                |
| GitHub repository created                      | Complete                                    | https://github.com/ashabaahebwamable/GROUP-T | `main` is synchronized with `origin/main`                               |
| ClickUp project created, Week 1 tasks assigned | Not verified                                | Pending board URL                            | Must be confirmed before submission                                     |
| Synthetic data design and initial corpus       | Initial slice complete; expansion pending   | `docs/requirements/synthetic-data-design.md` | 15 inventory rows, 6 suppliers, 10 quotations and 4 quotation letters   |
| Manual baseline measured                       | Not completed                               | `docs/evaluation/week1-manual-baseline.md`   | Three cases still need timed manual measurement                         |

### 2. Key engineering decisions and why

State each decision, the alternative rejected, and the reason. Suggested content, to be confirmed or replaced by what the team actually decided:

1. **One stock item per requisition.** Multi-line requisitions would introduce split supplier award, which falls outside the safety boundary, and would multiply the evaluation scenario count.
2. **No model-produced figure is used by the system.** All monetary arithmetic is recomputed in code; discrepancies are logged. The alternative of allowing the model to compute totals was rejected for financial-safety reasons.
3. **Quotation letters in text form are included in the corpus**, not structured records alone, because extraction from varying prose supplies a meaningful AI task and supports later grounding tests.
4. **Optical character recognition is excluded.** It would add a separate failure source and is outside the capacity of the eight-week project.
5. **All data is synthetic and team-authored.** This satisfies the brief's data-access constraint and permits deliberate mis-ranking, missing-field and expired-quotation test cases.

### 3. Failures, challenges and current response

Record what actually went wrong. This section is assessed; an empty one is not credible.

| Challenge                                                                                                         | Response                                                                                             | Status                     |
| ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------- |
| Work began before all group and ClickUp details were available                                                    | Completed the repository-based Week 1 artefacts and recorded unknown administrative facts as pending | Open for team confirmation |
| Evidence corpus is intentionally smaller than the final target and one missing-unit quotation remains outstanding | Kept the initial slice bounded and listed the expansion and missing-field case as Week 2 work        | Carried forward            |

Known open items at the close of Week 1:

- Iteration limit for the bounded agent remains a proposed 6 tool-call maximum and requires team confirmation.
- Success-criteria thresholds remain proposed and require team confirmation.
- Corpus expansion from the initial 21 items/documents to the 25-40 target remains outstanding.
- The rendered architecture PNG, manual baseline, ClickUp evidence, and individual member allocations remain outstanding.

### 4. GitHub evidence

| Item              | Reference                                                                   |
| ----------------- | --------------------------------------------------------------------------- |
| Repository URL    | https://github.com/ashabaahebwamable/GROUP-T                                |
| First commit      | `8f619c2` — 7 September 2026, 13:00 +0300                                   |
| Commits this week | 1 verified commit in the local history                                      |
| Contributors      | Azibo Isaac Alinda — 1 commit; additional contributors pending confirmation |
| Folder structure  | Per brief §5                                                                |
| Secret handling   | `.env` excluded via `.gitignore`; `.env.example` contains placeholders only |

### 5. ClickUp evidence

| Item                                   | Reference                        |
| -------------------------------------- | -------------------------------- |
| Board URL                              | Pending confirmation             |
| Week 1 tasks created                   | Not verified from the repository |
| Tasks complete / in progress / blocked | Not verified from the repository |
| Members joined                         | Not verified from the repository |
| Tasks linked to repository evidence    | Not verified from the repository |

### 6. Individual contribution summary

Each member completes their own row and their own paragraph. The brief requires that every student be able to explain the work they submit.

| Member             | Role                                        | Tasks owned                  | Artefacts authored                                                                                                           | Commits |
| ------------------ | ------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------- |
| Azibo Isaac Alinda | Project / Requirements and repository setup | T1.1, T1.3-T1.8, T1.11 draft | Charter, definition, stories, boundary matrix, architecture source, synthetic-data design, repository README and this report | 1       |

**Azibo Isaac Alinda:** I bounded the system to one stock item per requisition and kept supplier confirmation and approval as separate human gates. This avoids split supplier award and prevents a model recommendation from becoming an unauthorised purchasing decision. Remaining members must add their own rows and contribution paragraphs before submission.

### 7. Declared use of AI tools

Per brief §6. Full detail in `docs/ai-engineering-log.md`.

| Tool / model                   | Used for                                                                                      | Reviewed by                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| GitHub Copilot / AI assistance | Drafting and reviewing requirements, boundaries, architecture wording and this reconciliation | Azibo Isaac Alinda; review and final acceptance remain the student's responsibility |

### 8. Plan for Week 2

Week 2 focus per the brief: build the smallest useful model-backed capability and establish a tested baseline before adding retrieval or agency.

| Planned task                                                             | Owner                                          | Target                                                             |
| ------------------------------------------------------------------------ | ---------------------------------------------- | ------------------------------------------------------------------ |
| Select the model; document capability, cost, latency, privacy and access | Team member to be assigned                     | Model Selection Note, 1 page                                       |
| Integrate the model into the application                                 | Application / Integration owner to be assigned | Working baseline interaction                                       |
| Write Prompt Specification v1.0                                          | AI Engineering owner to be assigned            | Role, task, context, constraints, output format, failure behaviour |
| Build the 10-case prompt evaluation table                                | Quality owner to be assigned                   | Expected vs actual recorded                                        |
| Version at least two meaningful prompt iterations                        | AI Engineering owner to be assigned            | `prompts/` with history                                            |
| Close the open items in §3                                               | Whole team after roles are confirmed           | Iteration limit, thresholds and evidence gaps agreed               |

**Carried forward:** quotation field extraction remains the proposed first model-backed capability because it is the narrowest slice with clear AI value and feeds every later week. The team should confirm this at the Week 2 kickoff.

---

## Week 2 Progress Report — Foundation Model Engineering and Prompting

### Objective

The Week 2 task focused on delivering the smallest useful model-backed capability: a quotation-extraction baseline that can convert supplier quotation text into a structured JSON object without turning the system into an autonomous purchasing agent. This work established the first evidence-backed model interaction pattern for the ProcurePrep workflow, before later stages add retrieval, tools, and agency.

### Model selection

The repository adopts Google Gemini 3.6 Flash as the baseline model for this phase. This choice balances affordability, prompt responsiveness, and the ability to handle short structured extraction tasks without a paid subscription. The project later uses the model only with synthetic procurement data, because the free-tier arrangement carries privacy constraints and synthetic-only rules are necessary for the capstone environment.

The model selection note documents the capability, cost, latency, access and privacy considerations. These constraints are not abstract concerns; they directly shape the bounded use of the model. The model is used for evidence extraction, not supplier selection or purchase decision-making.

### Baseline implementation

The week-2 baseline was implemented in the source layer as a deterministic extraction workflow wrapped by a Gemini API client. The main extraction logic is in `src/quotation_extractor.py`, and the application-level model call is in `src/model_client.py`.

The extractor is intentionally narrow. It accepts raw quotation text, preserves fields explicitly stated in the text, and flags gaps or ambiguity instead of inventing values. This is consistent with the project principle that no model-produced figure is trusted without deterministic validation.

The model client adds the actual integration path: when a valid `MODEL_API_KEY` is present, a prompt is sent to the Gemini endpoint, the JSON response is parsed, and the result is validated. This is the minimum working interaction path for the project baseline.

### Prompt evolution

Three prompt versions are now recorded in the prompt folder:

- `v1.0`: baseline extraction task with explicit constraints and failure handling.
- `v1.1`: evidence-first revision that emphasized explicit trust boundaries and JSON output contract.
- `v1.2`: final tightened schema with explicit rules for missing information, conflicting prices, non-quotation input and instruction contamination.

The prompt history demonstrates iterative improvement rather than a single take. Each version tightened the specification around uncertainty handling and output safety, which is critical in a procurement domain where a model must not silently guess or make a decision.

### Evaluation approach

A 10-case evaluation matrix was created and recorded in `docs/evaluation/week2-prompt-test-cases.md`. The cases cover:

- complete valid quotations;
- missing currency and missing item prices;
- ambiguous delivery terms;
- prompt injection inside quotation text;
- multiple items;
- empty input;
- non-quotation text;
- conflicting price values; and
- missing currency.

This coverage is intentionally designed to test failure modes that are common in real quotation handling. The evaluation checks whether the model or extractor states facts only when they are present, preserves values literally, and explains uncertainty without hallucinating.

### Verification evidence

The repository includes both a deterministic extractor baseline and a live Gemini validation path. The live path was successfully exercised with a valid API key using the supported model name `gemini-3.6-flash`.

The real model-run output was saved to:

`evidence/live-evaluation/gemini-week2-live-results.json`

The live run covered the same 10-case quotation matrix and produced actual model outputs, including uncertainty notes for ambiguous delivery, unsupported values, prompt-injection content, and conflicting totals.

The repository also includes a parser-only unit test suite:

`python -m unittest discover -s tests -v`

Result: 4 tests ran and all passed.

This confirms two things: the deterministic code still behaves as expected, and the live Gemini interaction also works when the API is configured and the supported model name is used.

### Conclusion

Week 2 delivered the required foundation-model engineering baseline: model selection, prompt versioning, real model interaction, and live evaluation evidence. The project now has a working model-backed quotation-extraction path using Gemini 3.6 Flash, with detailed output captured for the same 10-case evaluation matrix.

---

## Week 3 Progress Report — Context Engineering and Grounded RAG

### Objective

Week 3 extended the Week 2 baseline from extracting single quotations to **grounded question answering over the controlled procurement corpus**. The goal was a retrieval-augmented pipeline that answers policy questions only from team-authored documents, cites its sources and refuses when the corpus does not support an answer (US-10). The model is still used for evidence, not for decisions, it does not select suppliers or approve requisitions.

### What was built

**Corpus completion.** The two missing trap documents identified in the Quality/Security review were added. `QUO-1004` is a quotation from the excluded supplier SUP-05, with the lowest headline rate. `QUO-1006` gives a quantity with no defined unit of measure. The corpus now holds 7 documents (1 policy and 6 quotation letters) and 32 structured records. Provenance is recorded in `knowledge/SOURCE-REGISTER.md`, which is kept out of the evidence the model sees (see below).

**Loading and chunking.** `src/ingestion/loader.py` loads every Markdown and CSV file under `knowledge/` and tags each one with its type (policy, quotation, supplier, inventory, requisition). `src/ingestion/chunker.py` splits the policy by section heading, keeping the section name in the chunk metadata. Quotation letters stay whole, and each CSV row is its own chunk. `src/rag/ingest.py` also builds an idempotent SQLite index of the same corpus with line ranges, available for inspection. The live retriever does not use it yet.

**Retrieval.** `src/retrieval/query_router.py` sends questions that contain a record ID (`INV-`, `SUP-`, `QUO-`, `REQ-`) to structured lookup, and everything else to semantic search. Semantic search uses `all-MiniLM-L6-v2` embeddings computed locally in memory. `src/rag/retrieve.py` applies a **0.35 similarity threshold**: if nothing scores above it, the system returns the fixed refusal `cannot answer from available documents` without calling the model. Every query is logged to `evidence/traces/retrieval.jsonl`.

**Grounded answering.** `src/rag/answer.py` builds the context with `DOC_ID` labels, calls Gemini 3.6 Flash with the versioned prompt `prompts/policy-qa/v1.0.md`, and then **checks every returned citation against the documents actually retrieved**. Any citation the model makes up is removed, and an answer left with no valid citation becomes a refusal (see `tests/test_week3_rag.py`).

**Architecture.** The pipeline is documented in `docs/architecture/week3-rag-diagram.md` and the matching `.png`. The retrieval-stack decision is recorded in `docs/ai-engineering-log.md` (entry 1, 19 Sep 2026).

### Evaluation (W3-06)

A 15-question set was written against the actual policy text: 5 answerable, 5 partially answerable and 5 deliberately unanswerable (`docs/evaluation/week3-rag-eval.md`). Each question lists the file and clause it should cite, what a correct answer must contain, and what it must refuse. The set was run with `scripts/run_week3_rag_eval.py` against the live pipeline: 11 questions on 24 Sep 2026, and the remaining 4 (B2, B5, C3, C4) on 27 Sep 2026 after Gemini free-tier limits blocked them.

| Group | Scored | Passed | Notes |
|---|---|---|---|
| A: answerable | 5/5 | 5 | Correct fact, cites `procurement-policy.md` |
| B: partially answerable | 5/5 | 5 | Each answered the grounded part **and** stated what the documents don't cover (e.g. B3: "The provided documents do not state how long director approval takes."). B2 did not state a VAT rate |
| C: unanswerable | 5/5 | 5 | All refused with the exact refusal string and no citations |
| **Total** | **15/15** | **15** | Groundedness 100%, refusal accuracy 100% (5/5) |

Results are in `docs/evaluation/week3-rag-eval-results.md`. The runner checks citations and refusals automatically. The B-row requirement to refuse the out-of-scope part was checked by hand against the full answer text in `week3-rag-eval-cache.json`.

The unit test suite (`python -m unittest discover -s tests`) runs 32 tests, and all pass.

### Retrieval and grounding failures (W3-07)

Three failures were confirmed from the run's model output and retrieval traces. Full evidence and candidate fixes are in `docs/evaluation/week3-retrieval-failures.md`.

1. **Citations are document-level only.** Answers match the correct clause (for example, A5 matches §5.4), but `citations` returns only `procurement-policy.md`. The chunker already stores the section; it is dropped between retrieval and citation. Candidate fix: carry the section into the evidence ID.
2. **The threshold does not separate answerable from unanswerable questions.** The 0.35 gate refused only C5. C1–C3 passed it with irrelevant chunks scoring 0.40–0.51, and were refused only because the model followed the prompt (C3 was re-confirmed on 27 Sep). Scores overlap: unanswerable C1 (0.51) outscored answerable A2 (0.48). Candidate fix: calibrate the threshold on the evaluation set, and add a deterministic check that the answer is supported by a cited chunk.
3. **Structured lookups bypass the threshold.** C4 mentions `SUP-05`, so it was routed to structured lookup and given a fixed score of 1.0, even though the supplier row cannot answer a question about history. The model refused, but the gate did not. Candidate fix: check that the record's fields can answer the question, rather than using a fixed score.

**Fixed during the week:**
- **Provenance file loaded as evidence.** `SOURCE-REGISTER.md` mentions an 18% VAT rate deliberately absent from the policy. It was not retrieved in the run, but it is now excluded from loading, with a test.
- **Retry logic used up the quota.** `src/model_client.py` retried 429/503 errors three times with no pause. It now backs off before retrying server errors and does not retry quota errors, with tests.
- **Evaluation runner.** Refusal accuracy now counts only C questions that actually ran, and cached notes no longer repeat on every re-run.

### Individual contributions (from repository history)

| Member | Week 3 contribution |
|---|---|
| Azibo Isaac Alinda | Idempotent SQLite ingestion (`src/rag/ingest.py`); grounded RAG workflow (`retrieve.py`, `answer.py`, prompt v1.0, tests, architecture diagram, AI log entry) |
| Tendo Caisey | Loader and chunker, query router, semantic search and structured lookup (`src/ingestion/`, `src/retrieval/`); first RAG architecture diagram; reviewer of the retrieval-stack decision |
| Akisa Maria Ashley (Quality/Security Lead) | Trap documents QUO-1004 and QUO-1006; source-register update; first draft of the 15-question set; evaluation runner; retrieval-failure log; CI workflow and validation tests |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Refined the evaluation set with file and clause citations, required refusals and a scoring rubric; ran the full evaluation and analysed the retrieval traces; confirmed failures 2 and 3; fixed source-register exclusion, API retry backoff and evaluation metrics; this report |

### Next steps (Week 4 candidates)

- Carry the policy section into citations (failure 1).
- Calibrate the threshold on the evaluation set and add a deterministic answer-support check (failure 2).
- Stop structured lookups from bypassing the threshold (failure 3).

### Conclusion

Week 3 delivered a working, traceable RAG pipeline over the synthetic corpus, with a refusal threshold, citation validation, retrieval traces and a 15-case evaluation. All 15 questions were either grounded and cited, or correctly refused. The evaluation also showed where the deterministic controls are weaker than designed: the similarity threshold and the structured route leave refusal of out-of-scope questions to the model, and citations stop at the document level. Each has a candidate fix for the next iteration.

---

## Week 4 Progress Report — Tools and Function Calling

### Objective

Week 4 moved the agent from answering questions to **requesting actions through controlled tools**. The goal was a small set of declared tools that the model can ask for, a router that decides whether each request may run, and deterministic code that does every calculation and state change. The model still does not make decisions: it cannot select a supplier, approve a requisition, contact a supplier or commit money. The only side effect any tool has is a simulated one, a requisition saved as `DRAFT`.

### What was built

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

### Testing (W4-04 and W4-05)

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

### Gaps found and fixed

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

### Still open

- **End-to-end Gemini run.** `scripts/run_week4_agent.py` sends four scenarios (reorder check, policy lookup, compare-and-draft, approval attempt) through the full agent and saves the result to `evidence/traces/week4/w4-live-agent-run.json`, with every tool call in `evidence/traces/tool-calls.jsonl`. It was run twice on 7 Oct. Every request failed on Google's side: first with `503 UNAVAILABLE` ("high demand"), then with `429 RESOURCE_EXHAUSTED` once the free tier's 20 daily requests were used. The tools themselves were checked live without the model (see gaps 1 and 5), and the agent loop is covered by mocked tests. The script will be rerun when the quota resets, and the output will be added as evidence.
- **Owner review of the state machine (planned for Week 5).** It was drafted with AI assistance while Isaac's machine was unavailable (AI Engineering Log, entry 3). Isaac will review and take ownership of it, together with `requisition_store.py`, as part of his Week 5 work. Until then it is accepted provisionally.

### Individual contributions (from repository history)

| Member | Week 4 contribution |
|---|---|
| Tendo Caisey (AI Engineering Lead) | Tool catalogue and schemas (W4-01, with Mable); function-calling router with allow-list, error handling, bounded loop and tracing (W4-03); Week 4 architecture diagram; Week 4 AI engineering log entry |
| Azibo Isaac Alinda | Deterministic procurement tools: reorder check, quotation comparison, policy rules and requisition draft (W4-02) |
| Akisa Maria Ashley (Quality/Security Lead) | Failure and authorization tests, including the output-validation gap (W4-04); approval state machine and its 12 tests (W4-05); test evidence and AI log entry 3 |
| Wakinya Esau John (DevOps/Documentation Lead) | Tool demo script and recording (W4-07); Week 4 evidence screenshots for CI, PRs and ClickUp; removed duplicate demo rows; reviewed and merged PRs #3 and #4 (W4-08) |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Refined the tool catalogue against the code and marked each gap (W4-01, with Tendo); Week 4 architecture text version; fixed the eight gaps above (`lookup_policy`, router checks, trace file, draft location, requisition store, §3.4 tie-break) with 18 tests; live agent runner `scripts/run_week4_agent.py`; regenerated the Week 4 architecture diagram; removed the misplaced duplicate `state_machine.py`; this report |

### Next steps (Week 5 candidates)

- Rerun `scripts/run_week4_agent.py` once the Gemini quota resets and commit the trace as evidence.
- Isaac to review and take ownership of `state_machine.py` and `requisition_store.py` (his Week 5 task).
- Carry over from Week 3: section-level citations, threshold calibration, and stopping structured lookups from bypassing the threshold.

### Conclusion

Week 4 delivered a tool-using agent with four declared tools, a router that blocks anything not on the allow-list and checks both what goes into a tool and what comes out, deterministic calculations, and a simulated-only side effect. A draft is created only when the router's own recomputation shows no blocking flags and agrees with the model's supplier. An approval state machine, reachable only by a person, makes autonomous approval impossible by design. All eight gaps found while checking the code against the catalogue were fixed with tests, and all 87 tests pass. What remains is the end-to-end Gemini run, blocked by the API quota on 7 Oct, and Isaac's review of the state machine, scheduled for Week 5.

---

## Week 5 Progress Report — Bounded Agent Loop

### Objective

Week 5 turned the Week 4 tools into a **bounded agent**: a loop that takes one flagged stock item from the reorder signal to a requisition draft awaiting a human, and stops safely whenever it cannot or must not continue. The limits on the agent are written down first, in an agent task contract, and the loop, tests and traces are checked against it. The agent still makes no decisions that belong to people: it never confirms a supplier, submits, approves, purchases or contacts a supplier.

### What was built

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

### Testing (W5-05)

The test suite (`python -m pytest`) runs **144 tests and 17 subtests, and all pass** (12 Oct 2026). There are no expected failures left: the one that documented unsaved stops was removed once stops were persisted.

| Requirement | Tests |
|---|---|
| Iteration limit reached → halt with outstanding steps listed (S1) | `tests/agent/test_stop_conditions_and_allowlist.py` `IterationLimitTests`; `tests/test_agent_integration.py` `ModelLoopControlTests` |
| Tool outside the allow-list → blocked before execution, logged, run stops (S3) | `AllowListTests` (approval, supplier email, purchase order, payment); model-loop test |
| Case state after a halt equals the state before it | `StatePreservedAfterHaltTests` (limit, hand-off, missing item, blocked tool, exhausted retry) |
| H1, resume, policy lookup (S6), persisted stops, item matching | `tests/test_agent_loop.py` |
| Officer cannot approve; preparer cannot approve; refusal logged | `tests/workflow/test_state_machine.py` `AuthorizationRoleTests`; `tests/test_week4_gap_fixes.py` |

The test fixture `tests/conftest.py` sends every test run's trace and audit writes to a temporary folder, so running the tests never changes the evidence files.

### Execution traces (W5-04)

Five traces in `evidence/traces/week5/` are the unedited output of the real loop, produced by `python -m scripts.generate_week5_traces`. No model is called; `lookup_policy` uses the real local retriever. Each trace records the contract code of every stop and the audit events it wrote.

| Trace | Outcome |
|---|---|
| 1 Happy path (INV-003, 460 pieces) | Run 1: 4 calls, H1. Officer confirms SUP-03. Run 2: 1 call, draft, H2 |
| 1b Reference cement case (INV-001, 10,000 kg) | QUO-1004 from excluded SUP-05 reported as informational and left out of the ranking; H1, confirm SUP-01, draft, H2 |
| 1c Trace 1 on today's date | S4: every synthetic quotation has expired |
| 2 "Portland cement" | S5: matches INV-001 and INV-002; both listed, neither chosen, no tool called |
| 3 Induced tool failure | A: outage, one retry, S2. B: resume from A's saved state to H1; B2: confirm, draft, H2. C: one failure, retry succeeds, H1 |

### Gaps found and fixed

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

### Still open

- **Tendo's review of contract sections 3, 4 and 8.** They were drafted from the code on 12 Oct because his text was not in the repository. He needs to accept or replace them, and to agree the iteration limit of 6, after which the placeholders in `project-charter.md` and `project-definition.md` are replaced.
- **Owner confirmation of the 12 Oct changes.** Because the owners could not be reached, an independent review was done and recorded in `docs/reviews/week5-change-review.md`. It found one defect, now fixed (the case store skipped the self-approval check), and four minor points. Isaac's review of the bounded loop and state-machine changes is now recorded in that file, dated 2026-10-15. Tendo and Ashley remain pending on their areas. No record of Isaac's review of the Week 4 state machine is in the repository yet.
- **Week 3 evaluation after the quotation additions.** Seventeen synthetic quotations (QUO-1011 to QUO-1027) were added so that seven of the nine below-reorder items can reach a draft. Retrieval for the 15 Week 3 questions was compared before and after without the model: 11 are identical, and B1, B4, C1 and C3 differ only in lower-ranked quotation rows. All four were rerun on Gemini (B1 on 12 Oct; B4, C1 and C3 on 13 Oct, after the 12 Oct quota ran out) and all still pass, including the C3 refusal, so the additions did not change the Week 3 results (`evidence/traces/week3/week3-recheck-after-quotation-additions.json`). **Resolved.**
- **Live Gemini run: done (12 Oct).** All four `scripts/run_week4_agent.py` scenarios completed on real Gemini (`evidence/traces/week4/w4-live-agent-run.json`, calls in `evidence/traces/tool-calls.jsonl`): the reorder check and policy lookup answered from the tools; the compare-and-draft scenario compared the quotations and correctly did not draft, because all have expired on today's date; the approval request was refused with a reference to policy §5 and no tool call. Two scenarios first stopped with `MODEL_UNAVAILABLE` (S8) on Google 503 errors, which the new model-loop stop handled cleanly, and were rerun.
- **Demo video.** `scripts/demo_week5.py` was run and its output saved as `evidence/demo/week5/w5-demo-transcript.txt`; a screen recording, like Week 4's, still needs a person.

### Individual contributions (from repository history)

| Member | Week 5 contribution |
|---|---|
| Tendo Caisey (AI Engineering Lead) | Week 5 architecture diagram and first version of the orchestrator in `loop.py` (8 Oct). Contract sections 3, 4 and 8 are assigned to him and awaiting his review |
| Azibo Isaac Alinda | Bounded agent loop `run_agent`: planner, observe step, iteration limit, retry and hand-off package, with tests (9 Oct) |
| Akisa Maria Ashley (Quality/Security Lead) | Stop-condition and allow-list tests (W5-05); trace generator and the first five traces with nine findings (W5-04); SQLite case store, state model and confirmed supplier-preference memory with tests; AI log entry 5 |
| Wakinya Esau John (DevOps/Documentation Lead) | Week 5 evidence: CI, PR and ClickUp screenshots, evidence index and traces README (W5-06, PR #5, merged by jewesau) |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Agent task contract sections 1, 2, 5, 6 and 7 and the draft of 3, 4 and 8 (W5-01); checked the merged code against it and fixed the ten gaps above with tests; the two data decisions; regenerated traces; `scripts/demo_week5.py`; AI log entry 6; this report |

### Next steps (Week 6)

- Tendo to review contract sections 3, 4 and 8 and the iteration limit; replace the charter and project-definition placeholders.
- Isaac and Ashley to review the 12 Oct changes to their files.
- US-12 (memory): connect the confirmed supplier preference to the officer's H1 confirmation, with its own confirmation step.
- Plan Week 7 evaluation data, including quotation coverage.

### Conclusion

Week 5 delivered a bounded agent that follows a written contract: six tool calls at most, one retry, ten coded stop conditions, a hand-off package on every stop, and two points where it waits for the officer. Both loops stop on a blocked tool instead of trying another route, every stop is saved to the trace and audit log, and a stopped case resumes without repeating work. Approval is now restricted to approver accounts and cannot be made by the person who prepared the requisition. All 144 tests pass and five traces show the behaviour on real tools, including the project's reference case reaching a draft, and seven of the nine items below reorder level can now reach a draft. The Week 4 live scenarios now also run end to end on real Gemini. What remains is the owners' confirmation of this week's changes and Tendo's review of his contract sections.

---

## Week 6 Progress Report — State, Memory and Interoperability

### Objective

Week 6 gave the agent a **durable state** and one **justified memory**. A workflow case now survives an application restart with its evidence intact, and an officer's confirmed choice of supplier can be shown again the next time the same item is reordered. The memory is deliberately weak: it is written only after a person confirms, it is a hint that never changes the computed ranking, it expires, and the model never sees who confirmed it. The week also specified one tool as an MCP-style interface, so its contract can be understood outside this codebase.

### What was built

**State model and persistence (W6-01).** `src/workflow/case_store.py` stores each workflow case in SQLite (`data/application_state.sqlite3`, git-ignored) with its item, quotations, comparison, flags, state and decisions, and records every transition as an event in the same transaction. `docs/architecture/state-model.md` has the state diagram and transition table:

| From | Action | To | Condition |
|---|---|---|---|
| — | create | `OPEN` | unique case ID |
| `OPEN` | start draft | `DRAFT` | — |
| `DRAFT` | submit | `PENDING_APPROVAL` | no unresolved blocking flags |
| `PENDING_APPROVAL` | approve / reject / query | `APPROVED` / `REJECTED` / `QUERIED` | registered approver who did not submit the case; reject and query need a reason |
| `OPEN`, `DRAFT`, `PENDING_APPROVAL` | halt | `HALTED` | a reason |
| any terminal state | anything | — | refused |

On restart `get_case` rebuilds a case exactly as recorded and `list_resumable_cases` offers only `OPEN`, `DRAFT` and `PENDING_APPROVAL` cases (US-12 AC1–2).

**Supplier-preference memory (W6-02).** `src/memory/supplier_preferences.py` stores one fact per confirmation: item, supplier, the confirming officer's ID and a UTC timestamp.
- **Written only after explicit human confirmation.** When an officer confirms the recommended supplier at hand-off H1 (`confirm_supplier`), the preference is recorded with their identity (US-12 AC3). The writer refuses anything but a literal `confirmed=True` and a registered officer or approver; it is not a model tool.
- **Shown as a hint, never a ranking input.** The router attaches the latest preference for the same item to the comparison result as `supplier_preference_hint`; the comparison function never reads memory. Tests show a remembered supplier cannot be promoted, made eligible if excluded, or used to clear a blocking flag.
- **Model prompt.** The `compare_quotations` tool description tells the model to surface the hint as information, distinguish it from the computed recommendation, and leave the decision to people.

**Memory design and data handling (W6-03).** `docs/architecture/memory-design-note.md` sets out what is stored and why, who can read it, retention and deletion, what reaches the model, and every other kind of data the system keeps. The rules are implemented, not just described:

| Rule | Implementation |
|---|---|
| Retention 12 months | Older preferences are never shown; `purge_expired_preferences()` deletes them and logs it |
| Deletion | `delete_supplier_preferences()`: approver only; every deletion and refused attempt goes to the audit log |
| Read access | `list_supplier_preferences()`: officer and approver roles only |
| Data sent to the model | The supplier only; the officer's ID and time are removed before anything reaches Gemini |

The security review (section 8) checked for personal data, secrets and access control. A stand-in review on 13 Oct found and fixed one gap (an unregistered ID could be recorded as confirmer); Ashley then repeated all three checks independently, including scanning every commit for keys and 20 deliberate bad-input attempts, and added three findings (below).

**MCP-style interface (W6-04).** `docs/architecture/mcp-interface-spec.md` specifies `compare_quotations` as an MCP-style tool: capability, input and output contracts, preference handling, permissions and side effects, validation and errors, and the security boundary. It states plainly that no MCP server has been deployed; the optional external integration was not attempted.

### Testing (W6-05)

The suite (`python -m pytest`) runs **187 tests and 166 subtests, and all pass** (19 Oct 2026). A shared fixture keeps every test off the real database and evidence logs.

| Card requirement | Tests |
|---|---|
| No preference write without confirmation | `tests/memory/test_memory_controls.py` `NoWriteWithoutConfirmationTests`, `ConfirmationWritePathTests`; `tests/memory/test_supplier_preferences.py` |
| Restored values identical to those recorded before restart | `tests/workflow/test_state_transitions_and_restart.py` `RestartTests`: every field of every case after a real restart, awkward values unchanged, restoring is read-only, the event history is unbroken |
| Every legal and illegal state transition | `TransitionMatrixTests`: every state against every action, terminal states, no action can jump to a state; plus condition tests for reasons, approver role and separation of duties |
| Memory never changes the ranking | `MemoryNeverChangesTheRankingTests`; `tests/test_preference_does_not_change_ranking.py` |
| Retention, deletion and access rules | `DataHandlingTests` in `test_supplier_preferences.py` |

### Demonstration (W6-06)

`evidence/demo/week6/w6-06-restart-resume-and-preference-flow.mp4`, recorded with `scripts/demo_week6.py`, shows the INV-003 case stopping at H1, the officer confirming SUP-03, the case resuming from its saved state to a draft at H2, and the stored preference being read back as a hint.

Two limits of the demonstration, stated so the recording is not over-read:
- Both runs happen in one program. The agent's own case state is passed between runs in memory; it is not yet saved to the W6-01 case store, so an agent run cannot be resumed after the application is closed. Restart of the case store itself is proven by the `RestartTests` above.
- The script writes the preference with a direct call rather than through `confirm_supplier`, which now does it automatically; the effect is the same.

Running the script also added a demonstration draft, `REQ-2026-0004`, to `data/requisitions.csv`.

### Findings carried forward

| # | Finding | Source | Proposed action |
|---|---|---|---|
| 1 | Identity is asserted, not authenticated: there is no login, so anyone who supplies an approver's ID is treated as one | Memory note §8 (Ashley) | Week 8 hardening; state it in memory note §4 |
| 2 | Logged free text has no size limit (a 200,000-character reason added 200 KB to the audit log) | Memory note §8 (Ashley) | Cap actor ID and reason length |
| 3 | The purge of expired preferences is not scheduled | Memory note §7 | Call it at application start |
| 4 | No retention rule for cases, requisitions or the audit log | Memory note §6–7 | Team decision |
| 5 | The agent loop does not save its state to the case store | W6-06 demonstration | Connect `run_agent` stops to `case_store` so a run survives a restart |
| 6 | Two synthetic account IDs are based on team members' names | Memory note §8 | Use generic IDs in the Week 7 data |

### Still open

- **Owner confirmations from Week 5.** Ashley's row in `docs/reviews/week5-change-review.md` is still blank. Isaac's two rows were recorded on 15 Oct in a commit by Ashley; Isaac should confirm them himself.
- **Demonstration draft.** Decide whether `REQ-2026-0004` stays in `data/requisitions.csv` or is removed, as the Week 4 demonstration rows were.

### Individual contributions (from repository history)

| Member | Week 6 contribution |
|---|---|
| Tendo Caisey (AI Engineering Lead) | MCP-style interface specification and its wording correction (W6-04); model prompt for the preference hint (W6-02); ranking test proving a preference never changes the recommendation (W6-02); test isolation for the preferences database; Week 5 sign-off of contract sections 3, 4 and 8, the iteration limit, and the updated W5-02 diagram |
| Azibo Isaac Alinda | Owner of W6-01 and W6-02; review of the bounded loop and state-machine changes recorded on 15 Oct |
| Akisa Maria Ashley (Quality/Security Lead) | SQLite case store, state model and supplier-preference memory (W6-01, W6-02); connected the preference write to the officer's confirmation; memory and state tests, including every transition and a real restart (W6-05); independent security review of the memory note (W6-03 §8) |
| Wakinya Esau John (DevOps/Documentation Lead) | Restart-and-resume and preference demonstration with `scripts/demo_week6.py` (W6-06); Week 6 screenshots (W6-07); Week 5 demo video |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Memory design and data handling note and the retention, deletion, access and model-data code it describes (W6-03); stand-in security review; merged and aligned Tendo's W6-04 work; kept the demo and trace generator off the real database; Week 3 recheck after the quotation additions; this report |

### Next steps (Week 7)

- Connect agent-run stops to the case store, so a case can be resumed after the application restarts (finding 5).
- Prepare the Week 7 evaluation set: the seven items that now reach a draft, the S4 cases (INV-003 lapsed quotation, INV-006 too few quotations), the two policy 3.4 tie-breaks, and generic account IDs.
- Schedule the preference purge and cap logged text length (findings 2 and 3).
- Close the Week 5 owner confirmations.

### Conclusion

Week 6 delivered persistence that survives a restart exactly, and a memory that is useful without being trusted: confirmed by a person, shown as a hint, never used in ranking, kept for twelve months, deletable only by an approver, and never sent to the model with anyone's identity. Every legal and illegal state transition is tested, as are the memory controls, and all 187 tests pass. The `compare_quotations` contract is now documented as an MCP-style interface. What remains for Week 7 is connecting agent runs to the case store and preparing the evaluation set.

---

## Week 7 Progress Report — Evaluation, Observability and Guardrails

### Objective

Week 7 set out to show, with evidence, that ReqPrep is reliable, grounded, inspectable and safe: a fixed scenario set judged against thresholds agreed before running, structured traces for every request, guardrails proven in code, and a catalogue of real failures with their fixes.

### What was delivered

| Task | Evidence | Status |
|---|---|---|
| W7-01 Scenario set | `docs/evaluation/final-scenarios.md`: 40 scenarios (10 normal, 6 edge, 4 incorrect information, 4 adversarial, 3 tool failure, 3 unauthorized, 10 for full user-story coverage), each with input, expected outcome, pass criteria and user story; 4 synthetic test letters outside the knowledge corpus | Done |
| W7-02 Criteria | `docs/evaluation/criteria.md`: task completion, groundedness, tool-selection accuracy, instruction following, latency, safety violations (target 0); signed by Mable (19 Oct) and Tendo (21 Oct) **before** the first run | Done |
| W7-03 Runner and results | `scripts/eval_runner.py` (also `python -m src.eval.run`); run `20261023T020535Z` in `evidence/eval/`; `docs/evaluation/final-results.md` | **Partly done** (see below) |
| W7-04 Observability | `src/observability/`: one structured record per request (model, prompt version, retrieved chunks, tool calls and results, latency, errors, outcome); `python -m src.observability export <run-id>`; 5 traces in `evidence/traces/week7/` | Done |
| W7-05 Guardrails | `docs/evaluation/guardrails-evidence.md`: 10 guardrails with code references, tests and status | Done, except G10 (prompt injection) awaiting live evidence |
| W7-06 Failure Catalogue | `docs/evaluation/failure-catalogue.md`: 8 genuine failures since Week 3 with symptom, root cause, fix and re-test | Done (5 fixed, 3 open) |
| W7-07 Evidence | `evidence/screenshots/week7/`: evaluation run, trace viewer, CI (including a green run after the FC-02 fix), PR list, ClickUp | Done |

### Evaluation results so far

The runner executed the 26 scenarios that need no model call; the 14 others are not yet automated.

| Measure | Result | Threshold |
|---|---|---|
| Safety violations | **0** | 0 |
| Task completion (automated) | **25 / 26** | ≥ 90% overall |
| — normal / edge / unauthorized / additional | 7/7, 5/5, 3/3, 7/7 | — |
| — tool failure | 2/3 (T02, see below) | — |
| Tool selection, rule-based agent | **8 / 8** exact | 100% |
| Latency p50 / p95, no model call | 0.04 s / 0.11 s | p95 ≤ 5 s |

**T02 is a scenario error, not a system failure.** The scenario did not state a date, so the runner used 1 Sep, when INV-003's quotation QUO-1005 has lapsed. The trace shows the retry worked (failure, successful retry, case continued) and the case then stopped correctly at S4. The scenario should use 27 Aug, as N02 does. Because results have been seen, the correction will be recorded in `criteria.md` section 7 before T02 is re-run.

**Not yet evaluated.** The 13 Gemini-backed scenarios (policy Q&A, extraction, model agent), including **all four adversarial scenarios A01–A04**, and X07. The criteria require 100% in the adversarial category and full groundedness, so **the evaluation cannot be declared passed yet**. The automatic outcomes also still need the reviewer's verdict in `final-results.md`, which the criteria make the deciding judgement.

### Failures found and fixed this week

| # | Failure | Fix |
|---|---|---|
| FC-01 | A zero, negative or non-numeric quantity ran five tool calls before stopping (US-02 AC3, scenario E05) | `src/validation.py` rejects it before any tool runs (`INVALID_QUANTITY`, S5), on new and resumed cases; PR #16; E05 now passes |
| FC-02 | The evaluation runner, inside `src/`, confirmed suppliers on the officer's behalf and broke the guard test | Runner moved to `scripts/`; the guard test is unchanged and passes |
| FC-03 | An evaluation smoke run wrote into the real trace log | Runner traces isolated in a temporary folder; PR #17 |

Still open from Week 3: citations name the file, not the clause (FC-04); the similarity threshold does not separate answerable from unanswerable questions (FC-05); structured lookups bypass the threshold (FC-06).

### Known gaps

- **Prompt injection (G10)** is mitigated by code — no approval tool, allow-listed tools, H1 confirmation before any draft — but not yet shown to hold at the model. A01 and A02 provide that evidence.
- `item_id` has no format check (unknown codes are caught by lookup only); submit has no role check; a refused approval on the case-store path is not logged; tool argument types are not validated against the schema.

### Testing

`python -m pytest`: **203 tests and 173 subtests pass** (23 Oct), including the new quantity-guardrail and observability tests; CI is green on `main`.

### Contributions (from repository history)

| Member | Week 7 |
|---|---|
| Tendo Caisey | Evaluation runner and its second batch of scenarios; recorded the run; signed the criteria |
| Akisa Maria Ashley | Observability and trace export (W7-04); quantity guardrail (FC-01); moved the runner out of `src/` (FC-02); guardrails evidence (W7-05); Failure Catalogue (W7-06) |
| Azibo Isaac Alinda | Reviewed and merged the quantity-guardrail and evidence pull requests (#16, #19) |
| Wakinya Esau John | Week 7 screenshots, including the evaluation run, trace viewer and green CI (W7-07) |
| Ashaba Ahebwa Mable | Scenario set and test letters (W7-01); criteria and thresholds (W7-02); this report |

### Next steps

1. Correct T02's date (recorded in `criteria.md` §7) and re-run it.
2. Run the 13 Gemini-backed scenarios over two days (about 17 requests; free-tier limit 20 a day), adversarial first, and paste A01/A02 into guardrail G10.
3. Automate or run X07 by hand.
4. Reviewer verdicts for all 40 scenarios in `final-results.md`, then a final pass/fail against the thresholds.
