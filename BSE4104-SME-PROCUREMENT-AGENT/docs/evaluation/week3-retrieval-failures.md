# Week 3 Retrieval/Grounding Failure Log (W3-07)

Per the brief: at least three retrieval/grounding failures, with cause and candidate fix for
each. This log only records failures actually observed from real model output — no guessed or
hypothetical entries, per the Quality/Security Lead standard of evidence for this project.

**Status: 1 of 3 confirmed. 2 slots pending the 5 questions still blocked by API quota
(see week3-rag-eval-results.md) — to be completed once those run.**

---

## Failure 1 (CONFIRMED): Citation granularity is document-level only

**What happened:** Across every answered question in the W3-06 evaluation (A2-A5, B3, B5), the
system's `citations` field returned only the source file path
(`knowledge/policy/procurement-policy.md`), never the specific clause number the answer actually
drew from — even though the answer text itself correctly matched a specific clause (e.g. A5's
answer matches §5.4 exactly).

**Cause:** The retrieval/chunking layer (`src/retrieval/`) appears to index and return whole
documents (or chunks) without preserving clause-level identifiers in the citation metadata
returned to `answer_query()`.

**Why it matters:** A human reviewer currently has to read every answer and manually cross-check
it against the policy document to confirm which clause was actually used — the system's own
citation doesn't do this verification work for them. This weakens exactly the auditability that
citations are meant to provide (AI Boundary Matrix Row 17 — grounding is the point of the
retrieval layer).

**Candidate fix:** Carry clause/section identifiers through the chunking step so each retrieved
chunk's metadata includes its source clause number, not just its file path, and surface that in
the `citations` field `answer_query()` returns.

---

## Failure 2 (PENDING — re-test tomorrow)

**Target question:** B2 — "How is landed cost calculated, and what is today's VAT rate?"

**What we're checking for:** The VAT rate does not exist anywhere in the corpus. A correct
answer explains the landed-cost formula (grounded) and explicitly refuses or flags that no VAT
rate is stated (per policy 2.4-style refusal behaviour) — it must NOT invent a plausible-sounding
percentage. If it does state a specific number, that is a hallucination and this section will be
filled in with the exact quote, cause, and fix.

## Failure 3 (PENDING — re-test tomorrow)

**Target question:** C3 — "What is the company's registered VAT rate?"

**What we're checking for:** Same trap as above from the unanswerable side — this question has
no basis in the corpus at all. It should trigger a full refusal (`cannot answer from available
documents`), matching what C1, C2, C4, C5 already did correctly. If it instead states a VAT
figure, that's a second confirmed hallucination and will be documented with cause and fix here.

---

## Next step

Run A1, B1, B2, B4, C3 once the API quota resets (`scripts/run_week3_rag_eval.py`). Update
Failures 2 and 3 above with the real answers. If both come back clean (correctly grounded /
correctly refused), replace them with whatever real failure the fuller run does surface — do not
leave fabricated content in this file to hit a count of three.
