# Week 3 Progress Report — Context Engineering and Grounded RAG

## Objective

Week 3 extended the Week 2 baseline from extracting single quotations to **grounded question answering over the controlled procurement corpus**. The goal was a retrieval-augmented pipeline that answers policy questions only from team-authored documents, cites its sources and refuses when the corpus does not support an answer (US-10). The model is still used for evidence, not for decisions, it does not select suppliers or approve requisitions.

## What was built

**Corpus completion.** The two missing trap documents identified in the Quality/Security review were added. `QUO-1004` is a quotation from the excluded supplier SUP-05, with the lowest headline rate. `QUO-1006` gives a quantity with no defined unit of measure. The corpus now holds 7 documents (1 policy and 6 quotation letters) and 32 structured records. Provenance is recorded in `knowledge/SOURCE-REGISTER.md`, which is kept out of the evidence the model sees (see below).

**Loading and chunking.** `src/ingestion/loader.py` loads every Markdown and CSV file under `knowledge/` and tags each one with its type (policy, quotation, supplier, inventory, requisition). `src/ingestion/chunker.py` splits the policy by section heading, keeping the section name in the chunk metadata. Quotation letters stay whole, and each CSV row is its own chunk. `src/rag/ingest.py` also builds an idempotent SQLite index of the same corpus with line ranges, available for inspection. The live retriever does not use it yet.

**Retrieval.** `src/retrieval/query_router.py` sends questions that contain a record ID (`INV-`, `SUP-`, `QUO-`, `REQ-`) to structured lookup, and everything else to semantic search. Semantic search uses `all-MiniLM-L6-v2` embeddings computed locally in memory. `src/rag/retrieve.py` applies a **0.35 similarity threshold**: if nothing scores above it, the system returns the fixed refusal `cannot answer from available documents` without calling the model. Every query is logged to `evidence/traces/retrieval.jsonl`.

**Grounded answering.** `src/rag/answer.py` builds the context with `DOC_ID` labels, calls Gemini 3.6 Flash with the versioned prompt `prompts/policy-qa/v1.0.md`, and then **checks every returned citation against the documents actually retrieved**. Any citation the model makes up is removed, and an answer left with no valid citation becomes a refusal (see `tests/test_week3_rag.py`).

**Architecture.** The pipeline is documented in `docs/architecture/week3-rag-diagram.md` and the matching `.png`. The retrieval-stack decision is recorded in `docs/ai-engineering-log.md` (entry 1, 19 Sep 2026).

## Evaluation (W3-06)

A 15-question set was written against the actual policy text: 5 answerable, 5 partially answerable and 5 deliberately unanswerable (`docs/evaluation/week3-rag-eval.md`). Each question lists the file and clause it should cite, what a correct answer must contain, and what it must refuse. The set was run with `scripts/run_week3_rag_eval.py` against the live pipeline: 11 questions on 24 Sep 2026, and the remaining 4 (B2, B5, C3, C4) on 27 Sep 2026 after Gemini free-tier limits blocked them.

| Group | Scored | Passed | Notes |
|---|---|---|---|
| A: answerable | 5/5 | 5 | Correct fact, cites `procurement-policy.md` |
| B: partially answerable | 5/5 | 5 | Each answered the grounded part **and** stated what the documents don't cover (e.g. B3: "The provided documents do not state how long director approval takes."). B2 did not state a VAT rate |
| C: unanswerable | 5/5 | 5 | All refused with the exact refusal string and no citations |
| **Total** | **15/15** | **15** | Groundedness 100%, refusal accuracy 100% (5/5) |

Results are in `docs/evaluation/week3-rag-eval-results.md`. The runner checks citations and refusals automatically. The B-row requirement to refuse the out-of-scope part was checked by hand against the full answer text in `week3-rag-eval-cache.json`.

The unit test suite (`python -m unittest discover -s tests`) runs 32 tests, and all pass.

## Retrieval and grounding failures (W3-07)

Three failures were confirmed from the run's model output and retrieval traces. Full evidence and candidate fixes are in `docs/evaluation/week3-retrieval-failures.md`.

1. **Citations are document-level only.** Answers match the correct clause (for example, A5 matches §5.4), but `citations` returns only `procurement-policy.md`. The chunker already stores the section; it is dropped between retrieval and citation. Candidate fix: carry the section into the evidence ID.
2. **The threshold does not separate answerable from unanswerable questions.** The 0.35 gate refused only C5. C1–C3 passed it with irrelevant chunks scoring 0.40–0.51, and were refused only because the model followed the prompt (C3 was re-confirmed on 27 Sep). Scores overlap: unanswerable C1 (0.51) outscored answerable A2 (0.48). Candidate fix: calibrate the threshold on the evaluation set, and add a deterministic check that the answer is supported by a cited chunk.
3. **Structured lookups bypass the threshold.** C4 mentions `SUP-05`, so it was routed to structured lookup and given a fixed score of 1.0, even though the supplier row cannot answer a question about history. The model refused, but the gate did not. Candidate fix: check that the record's fields can answer the question, rather than using a fixed score.

**Fixed during the week:**
- **Provenance file loaded as evidence.** `SOURCE-REGISTER.md` mentions an 18% VAT rate deliberately absent from the policy. It was not retrieved in the run, but it is now excluded from loading, with a test.
- **Retry logic used up the quota.** `src/model_client.py` retried 429/503 errors three times with no pause. It now backs off before retrying server errors and does not retry quota errors, with tests.
- **Evaluation runner.** Refusal accuracy now counts only C questions that actually ran, and cached notes no longer repeat on every re-run.

## Individual contributions (from repository history)

| Member | Week 3 contribution |
|---|---|
| Azibo Isaac Alinda | Idempotent SQLite ingestion (`src/rag/ingest.py`); grounded RAG workflow (`retrieve.py`, `answer.py`, prompt v1.0, tests, architecture diagram, AI log entry) |
| Tendo Caisey | Loader and chunker, query router, semantic search and structured lookup (`src/ingestion/`, `src/retrieval/`); first RAG architecture diagram; reviewer of the retrieval-stack decision |
| Akisa Maria Ashley (Quality/Security Lead) | Trap documents QUO-1004 and QUO-1006; source-register update; first draft of the 15-question set; evaluation runner; retrieval-failure log; CI workflow and validation tests |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Refined the evaluation set with file and clause citations, required refusals and a scoring rubric; ran the full evaluation and analysed the retrieval traces; confirmed failures 2 and 3; fixed source-register exclusion, API retry backoff and evaluation metrics; this report |

## Next steps (Week 4 candidates)

- Carry the policy section into citations (failure 1).
- Calibrate the threshold on the evaluation set and add a deterministic answer-support check (failure 2).
- Stop structured lookups from bypassing the threshold (failure 3).

## Conclusion

Week 3 delivered a working, traceable RAG pipeline over the synthetic corpus, with a refusal threshold, citation validation, retrieval traces and a 15-case evaluation. All 15 questions were either grounded and cited, or correctly refused. The evaluation also showed where the deterministic controls are weaker than designed: the similarity threshold and the structured route leave refusal of out-of-scope questions to the model, and citations stop at the document level. Each has a candidate fix for the next iteration.
