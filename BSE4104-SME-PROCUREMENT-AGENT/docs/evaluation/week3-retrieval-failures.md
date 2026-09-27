# Week 3 Retrieval/Grounding Failure Log (W3-07)

Per the brief: at least three retrieval/grounding failures, with cause and candidate fix for
each. This log only records failures actually observed from the real system: model output from
the W3-06 run, or the retrieval traces that same run wrote to `evidence/traces/retrieval.jsonl`.
There are no guessed or hypothetical entries, per the Quality/Security Lead standard of evidence
for this project.

**Status: 3 of 3 confirmed** (evaluation runs of 24 Sep 2026 and 27 Sep 2026; traces in
`evidence/traces/retrieval.jsonl`). All 15 W3-06 questions have now been scored.

---

## Failure 1: Citation granularity is document-level only

**What happened:** Across every answered question in the W3-06 evaluation (A1–A5, B1, B3, B4), the
system's `citations` field returned only the source file path
(`knowledge/policy/procurement-policy.md`), never the specific clause the answer actually drew from.
The answer text itself matched a specific clause each time (e.g. A5's answer matches §5.4 exactly).

**Cause:** The retriever *does* know the section. Policy chunks are split by heading in
`src/ingestion/chunker.py` and carry `metadata.section` (e.g. `5. Approval thresholds`, visible in
the trace). But `src/rag/retrieve.py` builds `source_id` from the file path alone, and
`answer_query()` validates and returns citations at that level. The section is dropped between
retrieval and citation.

**Why it matters:** A human reviewer has to read every answer and cross-check it against the
policy to confirm which clause was used, so the citation doesn't do that verification work
for them. This weakens the auditability that citations are meant to provide (AI Boundary Matrix
Row 17: grounding is the point of the retrieval layer).

**Candidate fix:** Include the section in the evidence ID given to the model (e.g.
`policy/procurement-policy.md#5. Approval thresholds`), validate citations against those IDs, and
return them in `citations`.

---

## Failure 2: The 0.35 threshold does not separate answerable from unanswerable questions

**What happened:** The design relies on the similarity threshold to refuse out-of-corpus questions
before the model is called (`week3-rag-diagram.md`: *Best score >= 0.35? No → Refusal*). In the
run, that gate refused only **one** of the five unanswerable questions (C5, no chunks). The rest
all passed it with irrelevant evidence:

| Question | Top retrieved chunk | Score | Relevant? |
|---|---|---|---|
| C1 fraud penalty | policy §2 Quotation requirement | 0.51 | No |
| C2 retroactive approval | policy §1 Requisition requirement | 0.49 | Adjacent, not answering |
| C3 company VAT rate | `quotations.csv` row | 0.40 | No |
| C4 SUP-05 exclusion history | `suppliers.csv` row | 1.00 | See Failure 3 |

C1, C2 and C3 were refused only because the model obeyed prompt rule 3. The deterministic gate
did not catch them. The 27 Sep re-run of C3 retrieved the same chunks with the same scores.

**Cause:** MiniLM similarity scores for this small, single-domain corpus fall in a narrow band.
Every question mentions procurement vocabulary, so every chunk looks "somewhat similar". The ranges
overlap: unanswerable C1 scored **0.51**, higher than answerable A2 (0.48) and A4 (0.47). No single
threshold value can separate them.

**Why it matters:** Refusal for out-of-scope questions currently depends on the prompt, which the
AI Boundary Matrix treats as the weaker, prompt-only control. One model that is less obedient
(or one injected instruction) and C1–C3 get plausible but ungrounded answers.

**Candidate fix:** (a) Calibrate the threshold on the 15-question set and report the overlap,
rather than keeping 0.35 as a fixed value. (b) Add a deterministic post-check: release an answer
only if its key terms or numbers appear in a cited chunk. (c) Longer term, add a re-ranker or a
relevance check before the model call.

---

## Failure 3: Structured-lookup results bypass the threshold entirely

**What happened:** C4 ("How many requisitions has SUP-05 been excluded from in the past year?")
contains a record ID, so `QueryRouter` sent it to structured lookup. The single result, the
`suppliers.csv` row for SUP-05, reached the model with a score of **1.00**. The row says only
`excluded pending supplier review` and has no history, so it cannot answer the question.

**Cause:** `src/rag/retrieve.py` assigns a default score of `1.0` to any structured result
(`score = ... 1.0 if route == "structured"`). Any question that mentions an `INV-`, `SUP-`,
`QUO-` or `REQ-` ID therefore always passes the threshold, whatever it actually asks.

**Why it matters:** An exact record match shows the record *exists*, not that it *answers the
question*. For questions like C4 the refusal again depends entirely on the model. In the 27 Sep run the
model did refuse C4 (`cannot answer from available documents`), but only the prompt stopped it.

**Candidate fix:** Treat an ID match as "relevant record found" and still apply a check that the
question's intent is covered by the record's fields (e.g. no date/history field → refuse
"history" or "how many times" questions), or pass structured results through the same
semantic threshold instead of a fixed 1.0.

---

## Watch item: VAT rate (B2, C3)

**Risk:** `knowledge/SOURCE-REGISTER.md` was being loaded as evidence. It mentions
"Standard Ugandan VAT rate (18%)", a figure deliberately kept out of the policy.
**Observed:** In the 24 Sep traces the register was *not* retrieved for B2 or C3, so no leak
occurred.
**Action taken:** The register is now excluded from loading in `src/ingestion/loader.py` and
`src/rag/ingest.py` (test: `test_source_register_is_not_loaded_as_evidence`).
**Result (27 Sep re-run):** No leak. B2 explained landed cost and said "The provided evidence does
not contain information regarding today's VAT rate". C3 refused. Neither stated a VAT percentage.
**Closed.**

## Operational issue found during the run (not a retrieval failure)

`src/model_client.py` retried 429/503 errors three times with no pause, so each failing call used
up to three of the 20 free-tier daily requests and exhausted the quota mid-run. **Fixed:** 5xx now
backs off 5 s then 15 s, and 429 is not retried (tests in `tests/test_model_client.py`).

## Next step

The candidate fixes for failures 1–3 are proposed for Week 4. Re-run the same 15 questions after
each fix, so the before and after can be compared.
