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
|FC-03|Observability|Evaluation runner wrote to the real trace log|22 Oct (smoke run)|Fixed, re-tested; [PR #21](https://github.com/ashabaahebwamable/GROUP-T/pull/21)|
|FC-04|Retrieval|Citations name the file, not the clause|24 Sep (W3)|**Open** (proposed in Week 3, not built as of 22 Oct)|
|FC-05|Retrieval|Similarity threshold does not separate answerable from unanswerable|24 Sep (W3)|**Open** (proposed in Week 3, not built as of 22 Oct)|
|FC-06|Retrieval|Structured lookups bypass the threshold (fixed score 1.0)|24 Sep (W3)|**Open** (still in code)|
|FC-07|Agent loop / workflow|"Preparer may not approve" check skipped on the case-store path|12 Oct (W5 review)|Fixed, tested; [commit d9615ff](https://github.com/ashabaahebwamable/GROUP-T/commit/d9615ff1f4a643b06df9814db212902de186166a)|
|FC-08|Model client|Immediate retries exhausted the daily Gemini quota|Sep (W3)|Fixed, tested; [commit 56d5bf0](https://github.com/ashabaahebwamable/GROUP-T/commit/56d5bf033e608e7fcbf32d5c54ff406e71bd05b1)|
|FC-09|Evaluation scenario|T02: scenario date leaves INV-003 with two valid quotations, so the case cannot reach H1|25 Oct (final run)|Fixed, re-tested on a dirty tree; [PR #27](https://github.com/ashabaahebwamable/GROUP-T/pull/27)|
|FC-10|Workflow / authorisation|A submitter could approve their own case by padding their ID with spaces|27 Oct (D-05 test work)|Fixed, tested; [PR #28](https://github.com/ashabaahebwamable/GROUP-T/pull/28)|
|FC-11|Extraction (model)|N10: the model dropped "exclusive of VAT" and the separate transport charge|28 Oct (live Gemini run)|**Open** (fix not yet made)|
|FC-12|Extraction (model)|E02: the model accepted "each" as the unit instead of reporting it missing|29 Oct (live Gemini run)|**Open** (fix not yet made)|

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
* **Fix:** the runner's `Sandbox` now patches `DEFAULT_TRACE_PATH` in the modules that use it to a file in the temporary folder (`scripts/eval_runner.py`). It reached `main` in PR #21 (23 Oct, Caisey's runner), which already contained the same change, so the separate PR #17 was closed unmerged. PR: https://github.com/ashabaahebwamable/GROUP-T/pull/21
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

### FC-11 Extraction drops the VAT status and a separate transport charge (scenario N10)

- **Symptom:** live Gemini extraction of `QUO-1002` returned the correct supplier, quantity, unit, price, total, validity, lead time and terms. It omitted that prices are exclusive of VAT and that transport is charged separately at UGX 180,000, and left `missing_fields` and `uncertainty_notes` empty. (Three other checks also failed, but only because the model returned correct values as strings such as `"29,500"`; that is a checker strictness issue, not a model error.)
- **Root cause:** the v1.2 extraction schema has no field for VAT treatment or a separate delivery charge, and the prompt does not require the model to record them as notes when the letter states them, so cost-relevant facts were dropped silently. Policy 3.1 compares quotations on landed cost, so these facts change the result.
- **Fix (proposed, not yet made):** add VAT-treatment and delivery-charge fields to the schema, or require an uncertainty note when a letter states either, and make the numeric checks accept formatted strings. **PR: TO FILL**
- **Re-test:** re-run N10 live (one request) and compare with the letter. **TO FILL**
- **Evidence:** `evidence/eval/live-gemini/20261028T181848Z/N10-result.json`. **Status:** Open.

### FC-12 Extraction accepts "each" as the unit instead of reporting it missing (scenario E02)

- **Symptom:** for `QUO-1006`, which states 200 "each" with no unit of measure, the model returned unit `each` and left `missing_fields` empty. Policy 2.4 says a quotation with no unit of measure is incomplete; the scenario requires the unit to be null and listed as missing. (The supplier-name check also failed on letter case only, which is a checker artefact.)
- **Root cause:** the prompt does not tell the model that a non-unit word such as "each" does not count as a unit of measure, so it took the word literally.
- **Fix (proposed, not yet made):** add that instruction to the prompt and re-run. **PR: TO FILL**
- **Re-test:** re-run E02 live (one request); the unit must be null and listed in `missing_fields`. **TO FILL**
- **Evidence:** `evidence/eval/live-gemini/20261029T-E02/E02-result.json`. **Status:** Open.

## Failures from this evaluation run

One entry per failure found. All 40 scenarios now have a result; FC-11 and FC-12 come from the live runs, and the final record should be repeated on a committed tree.

### FC-09 (scenario T02): retry succeeds, but the scenario's date blocks continuation

- **Symptom:** the tool failed once and was retried successfully, but the agent stopped at `S4 POLICY_BLOCKING_FLAGS` instead of reaching H1 (final run `20261023T020535Z`, trace `4808c040`).
- **Root cause (verified 25 Oct):** the runner evaluates T02 at `as_of_date` 2026-09-01. At that date QUO-1005 (dated 2026-08-20, valid 7 days) has expired, so INV-003 has two valid quotations. `compare_quotations` returns `EXPIRED_OR_INVALID_QUOTATION:QUO-1005` and `MINIMUM_VALID_QUOTATIONS_NOT_MET:required=3:found=2`, so S4 is the correct outcome. Scenario X10 uses the same item and date and expects exactly this. At 2026-08-27 the same call has no blocking flags (scenario N02). The agent and the retry mechanism behaved correctly; the scenario's setup contradicts X10.
- **Fix:** T02 now runs at `as_of_date` 2026-08-27, recorded with this reason in `criteria.md` section 7 (26 Oct). The expected result is unchanged. PR: https://github.com/ashabaahebwamable/GROUP-T/pull/27
- **Re-test:** run `20261026T163427Z`: T02 PASS, with one simulated failure, one retry, then `H1 SUPPLIER_CONFIRMATION_REQUIRED` (27 of 27 automated scenarios passed). That run was made on a working tree that was not clean, so it must be repeated on a committed tree for the final record.
- **Status:** Fixed. Open item: re-run on a clean tree.

### FC-10 A submitter could approve their own case by padding their ID with spaces

- **Symptom:** after submitting a case as `DIRECTOR-1`, approving it as `"DIRECTOR-1 "` or `" DIRECTOR-1"` was not refused, and the case became APPROVED. Reproduced on the case store (the production path) and on the state machine; lower-case variants also passed the state machine when the role was supplied (US-09, guardrail G7).
- **Root cause:** `_check_approver` in `src/workflow/state_machine.py` compared `approver_id == requisition.created_by` on raw strings. The case store trims IDs for its role lookup, so a padded ID still received the approver role, and the owner check then failed to match. The gap existed before commit `d74db42`, which normalises stored values but not the comparison.
- **Fix:** IDs are compared trimmed and case-insensitively (5 lines in `state_machine.py`). PR: https://github.com/ashabaahebwamable/GROUP-T/pull/28
- **Re-test:** `tests/workflow/test_input_normalisation.py`, 15 tests. Padded and lower-case variants of the preparer's ID are refused for approve, reject and query, and a padded ID is refused on the case store; a different approver with spaces around their ID is still allowed and recorded without them. Before the fix the two bypass tests fail; after it all 15 pass. Full suite 209 passed; CI green on PR #28.
- **Found by:** writing the tests that defect D-05 asked for. Mable merged the fix on 27 Oct.
- **Status:** Fixed.
