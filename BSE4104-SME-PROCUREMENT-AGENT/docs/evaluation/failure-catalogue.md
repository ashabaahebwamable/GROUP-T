# Failure Catalogue with Remediation and Re-test (W7-06)

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep)
**Owner:** Akisa Maria Ashley
**Status:** Draft 22 Oct 2026. Every entry is a failure observed in this system, with the evidence named. Entries marked **TO FILL** need a PR link or a re-test result before they count as remediated.

A failure is remediated only when there is a fix (PR link) **and** a re-test result. Open failures are listed as open.

## Summary

|ID|Area|Failure|Found|Status|
|-|-|-|-|-|
|FC-01|Agent loop|Invalid quantity not rejected before tools run|19 Oct (E05)|Fixed, re-tested; [PR #16](https://github.com/ashabaahebwamable/GROUP-T/pull/16)|
|FC-02|Tools / safety|Evaluation runner calls a human-only action from `src/`|22 Oct (test suite)|Fixed, re-tested; [PR #16](https://github.com/ashabaahebwamable/GROUP-T/pull/16)|
|FC-03|Observability|Evaluation runner wrote to the real trace log|22 Oct (smoke run)|Fixed, re-tested; [PR #17](https://github.com/ashabaahebwamable/GROUP-T/pull/17)|
|FC-04|Retrieval|Citations name the file, not the clause|24 Sep (W3)|**Open** (proposed in Week 3, not built as of 22 Oct)|
|FC-05|Retrieval|Similarity threshold does not separate answerable from unanswerable|24 Sep (W3)|**Open** (proposed in Week 3, not built as of 22 Oct)|
|FC-06|Retrieval|Structured lookups bypass the threshold (fixed score 1.0)|24 Sep (W3)|**Open** (still in code)|
|FC-07|Agent loop / workflow|"Preparer may not approve" check skipped on the case-store path|12 Oct (W5 review)|Fixed, tested; [commit d9615ff](https://github.com/ashabaahebwamable/GROUP-T/commit/d9615ff1f4a643b06df9814db212902de186166a)|
|FC-08|Model client|Immediate retries exhausted the daily Gemini quota|Sep (W3)|Fixed, tested; [commit 56d5bf0](https://github.com/ashabaahebwamable/GROUP-T/commit/56d5bf033e608e7fcbf32d5c54ff406e71bd05b1)|

## FC-01 Invalid quantity not rejected before tools run

* **Symptom:** INV-001 with quantity `0`, `-5` or `"abc"`: the agent made five tool calls and ended at S2 instead of refusing the input (US-02 AC3, scenario E05).
* **Root cause:** `src/validation.py::validate_quantity` was written in Week 2 and unit-tested, but nothing in `src/` called it. The control existed only on paper (AI boundary matrix rows 1 and 15).
* **Fix:** `run_agent` now validates a supplied quantity after creating/restoring case state and before the planner loop; invalid input stops with `INVALID_QUANTITY` (S5), zero tool calls. The validator also rejects non-finite quantities and values too large to convert safely. Files: `src/agent/loop.py`, `src/validation.py`, `src/agent/stop_codes.py`, `docs/architecture/agent-task-contract.md`. PR: https://github.com/ashabaahebwamable/GROUP-T/pull/16
* **Re-test:** `tests/agent/test_quantity_guardrail.py` covers invalid new and resumed cases (including a no-tool-call assertion); `tests/test_quantity_validation.py` covers zero, negative, non-numeric, boolean, NaN, infinity and oversized integer values. E05 smoke: PASS; focused quantity/agent/workflow suite: 94 passed, 129 subtests passed; full suite: 203 passed, 173 subtests passed.

## FC-02 Evaluation runner calls a human-only action from `src/`

* **Symptom:** `tests/memory/test_memory_controls.py::test_nothing_in_src_calls_confirm_supplier` fails with `{'src/eval/run.py': {'confirm'}} != {}`.
* **Root cause:** the runner (N01, N02, N03, X03 resume cases) calls `confirm_supplier` to simulate the officer, and it lives under `src/`. The test enforces that only officer-facing application code may confirm a supplier, so that nothing the agent can reach can confirm on a person's behalf (criteria 2.6, item 3).
* **Fix:** moved the evaluation runner and its simulated officer action to `scripts/eval_runner.py`; `src/eval/run.py` remains a compatibility CLI entry point without calling the human action. The source-scan safety test remains unchanged. PR: https://github.com/ashabaahebwamable/GROUP-T/pull/16
* **Re-test:** `tests/memory/test_memory_controls.py::NoWriteWithoutConfirmationTests::test_nothing_in_src_calls_confirm_supplier` passes in the full suite: 203 passed, 173 subtests passed. `python -m src.eval.run --check` also passes through the compatibility CLI.
* **Status:** Fixed and re-tested locally; PR CI must pass before merge.

## FC-03 Evaluation runner wrote to the real trace log

* **Symptom:** after `python -m src.eval.run --smoke --only E05`, the untracked file `evidence/traces/observability.jsonl` appeared with 4 records. `criteria.md` section 4 requires evidence logs to be unchanged after a run.
* **Root cause:** `Sandbox` redirected the tool trace, audit log, requisitions and preferences, but not the structured request traces. `loop.py`, `tools_router.py` and `rag/answer.py` each fall back to `DEFAULT_TRACE_PATH`.
* **Fix:** `Sandbox` now patches `DEFAULT_TRACE_PATH` in those three modules to a file in the temporary folder (`src/eval/run.py`). PR: https://github.com/ashabaahebwamable/GROUP-T/pull/17
* **Re-test:** the smoke run of E05 and T01 passes and `git status` shows no new file under `evidence/`. The full-suite run also leaves no such file.

## FC-04 Citations name the file, not the clause

* **Symptom:** every answered question in the W3-06 run cited only `knowledge/policy/procurement-policy.md`, never the clause used. A reviewer must re-check each answer against the policy.
* **Root cause:** policy chunks carry `metadata.section`, but `src/rag/retrieve.py::_source_id` builds the ID from the file path only, and `answer_query` validates citations at that level. Source: `docs/evaluation/week3-retrieval-failures.md`, Failure 1.
* **Fix:** not applied. `_source_id` in `src/rag/retrieve.py` still builds the ID from the file path only (checked on `main`, 22 Oct). Proposed in Week 3: include the section in the evidence ID. **PR: TO FILL**
* **Re-test:** re-run the 15 Week 3 questions after the fix and compare. **TO FILL**
* **Status:** Open.

## FC-05 Similarity threshold does not separate answerable from unanswerable

* **Symptom:** only 1 of 5 unanswerable questions was refused by the 0.35 gate. C1 (fraud penalty) scored 0.51, higher than answerable A2 (0.48); C1 to C3 were refused only because the model obeyed the prompt.
* **Root cause:** MiniLM scores on a small single-domain corpus fall in a narrow band; no one threshold separates the two groups. Refusal rested on a prompt rule, the weaker control in the AI boundary matrix. Source: Week 3 failure log, Failure 2.
* **Fix:** not applied. `DEFAULT_THRESHOLD` is still 0.35 in `src/rag/retrieve.py` and there is no post-check (checked on `main`, 22 Oct). Proposed in Week 3: calibrate the threshold, add a deterministic post-check that an answer's numbers appear in a cited chunk, later a re-ranker. **PR: TO FILL**
* **Re-test:** X05 and X06 in the final run show whether refusals still rest on the prompt alone. **TO FILL** with their results.
* **Status:** Open.

## FC-06 Structured lookups bypass the threshold

* **Symptom:** C4 (SUP-05 exclusion history) retrieved the one supplier row with score 1.00. The row has no history, so it cannot answer; only the model's refusal stopped a wrong answer.
* **Root cause:** `src/rag/retrieve.py` line 78 still gives any structured result a default score of `1.0`, so a question containing an `INV-`, `SUP-`, `QUO-` or `REQ-` ID always passes the gate. Confirmed in the current code on 22 Oct.
* **Fix:** not yet applied. Options in the Week 3 log: check that the record's fields cover the question's intent, or pass structured results through the semantic threshold. **PR: TO FILL**
* **Re-test:** C4 must be refused by the deterministic gate before the model is called. **TO FILL**
* **Status:** Open.

## FC-07 "Preparer may not approve" check skipped on the case-store path

* **Symptom:** the case store did not record who prepared a case, so US-09's "preparer may not decide" check was not applied on that path (Week 5 change review, finding 1).
* **Root cause:** `src/workflow/case_store.py` stored no preparer; only the CSV requisition store was covered.
* **Fix:** the actor of the submit event is treated as the preparer (12 Oct). Pushed directly to `main` by Ashaba Ahebwa Mable with no pull request, so the commit is the evidence: https://github.com/ashabaahebwamable/GROUP-T/commit/d9615ff1f4a643b06df9814db212902de186166a
* **Re-test:** `tests/workflow/test_case_store.py::test_officer_and_submitter_cannot_approve_a_case` passed in the CI run on PR #16 (22 Oct); full suite 194 passed.

## FC-08 Immediate retries exhausted the daily Gemini quota

* **Symptom:** during the W3-06 run, failing calls each used up to three of the 20 free-tier daily requests and exhausted the quota mid-run.
* **Root cause:** `src/model_client.py` retried 429 and 503 errors three times with no pause.
* **Fix:** 5xx now backs off 5 s then 15 s; 429 is not retried (Week 3 failure log, 27 Sep). Pushed directly to `main` by Ashaba Ahebwa Mable with no pull request, so the commit is the evidence: https://github.com/ashabaahebwamable/GROUP-T/commit/56d5bf033e608e7fcbf32d5c54ff406e71bd05b1
* **Re-test:** CI run on PR #16: tests/test_model_client.py, 4 passed.

## Failures from this evaluation run

**TO FILL** after the full run: add one entry per FAIL in `final-results.md` (symptom, root cause, fix, PR, re-test). Expected candidates: any model-backed scenario that invents a figure, and any scenario whose runner result Ashley overrides on review.

### T02 — Retry succeeds, but policy blocks continuation

**Observed result:** FAIL. The tool failed once, was retried successfully, but the agent stopped at `S4 POLICY_BLOCKING_FLAGS` instead of reaching H1.

**Investigation:** The scenario uses the evaluation date `2026-09-01`. The quotation involved may have expired on that date, which could explain the policy block.

**Disposition:** Keep T02 as a failure pending review of the scenario's date, quotation validity, and expected outcome. Do not mark it as passed or change the expected result merely to achieve a higher pass rate.