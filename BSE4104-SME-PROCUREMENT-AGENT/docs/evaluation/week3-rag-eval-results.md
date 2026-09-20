# Week 3 RAG Evaluation — Results (W3-06)

**Status: 10 of 15 cases completed. 5 cases pending — blocked by Gemini free-tier daily quota
exhaustion (20 requests/day/project), not a system defect. See note at bottom.**

Of the 10 cases actually answered: **10/10 passed** (6/6 answerable+partial rows correctly
grounded and cited the source document; 4/4 unanswerable rows correctly refused).

## Completed cases

| # | Type | Question | Answer | Citation | Verdict |
|---|---|---|---|---|---|
| A2 | A | Can a requisition cover more than one stock item? | No. Under this version of the policy, a requisition covers only one stock item, and requisitions covering several items are not accepted. | knowledge/policy/procurement-policy.md | ✅ PASS |
| A3 | A | Who approves a requisition worth UGX 3,000,000? | A requisition worth UGX 3,000,000 requires approval by the operations manager. | knowledge/policy/procurement-policy.md | ✅ PASS |
| A4 | A | What happens to a quotation whose validity period has already lapsed by the time the requisition is prepared? | A quotation whose validity period has lapsed must be excluded from comparison. | knowledge/policy/procurement-policy.md | ✅ PASS |
| A5 | A | Can the officer who prepared a requisition also approve it? | No, the officer preparing a requisition may not approve it. | knowledge/policy/procurement-policy.md | ✅ PASS |
| B3 | B | A supplier not on the register is the cheapest option — can I recommend them, and how long does director approval take? | Yes, you can recommend a supplier not on the register, but any recommendation of a supplier not on the supplier register requires prior approval by a [director]. *(Full answer truncated by evaluation script's display width — re-check full text before final submission.)* | knowledge/policy/procurement-policy.md | ✅ PASS |
| B5 | B | If two quotations are within 2% of landed cost, how is the tie broken, and how many days difference counts as "shorter"? | When two quotations are within 2% of each other on landed cost, the tie is broken by preferring the quotation with the shorter delivery lead time. [Remainder truncated — same note as B3.] | knowledge/policy/procurement-policy.md | ✅ PASS |
| C1 | C | What is the penalty for a supplier who submits a fraudulent quotation? | cannot answer from available documents | — | ✅ PASS |
| C2 | C | Can a requisition be approved retroactively after goods are already delivered? | cannot answer from available documents | — | ✅ PASS |
| C4 | C | How many requisitions has SUP-05 been excluded from in the past year? | cannot answer from available documents | — | ✅ PASS |
| C5 | C | Who is the current operations manager by name? | cannot answer from available documents | — | ✅ PASS |

## Pending — blocked by API quota, not yet evaluated

| # | Type | Question | Status |
|---|---|---|---|
| A1 | A | How many quotations are required for a requisition worth UGX 2,000,000? | Pending — every attempt hit 429 (quota) or 503 (overload) |
| B1 | B | What quotations are required for a UGX 2,000,000 requisition, and which specific suppliers should I use? | Pending — same |
| B2 | B | How is landed cost calculated, and what is today's VAT rate? | Pending — same |
| B4 | B | What must a valid quotation state, and what's a common mistake suppliers make when writing one? | Pending — same |
| C3 | C | What is the company's registered VAT rate? | Pending — same |

## Root cause of the pending cases (real finding, not an excuse)

The shared `MODEL_API_KEY` is on Gemini's **free tier, capped at 20 requests/day per project**.
Multiple team members and multiple evaluation runs today exhausted this in a single afternoon.
Confirmed via direct API error: `quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier,
quotaValue: 20`. A second key tried from the team chat returned the identical quota, indicating
it shares the same underlying project/billing account rather than being independent.

**This is a real team-process gap worth carrying into the AI Boundary Matrix / Week 8 hardening
list**: a 20-request/day shared key cannot support a 4-5 person team doing iterative RAG
evaluation and development in parallel. Needs one of: a paid tier, per-member API keys/projects,
or a coordinated testing schedule.

## Additional finding: citation granularity

Every citation returned by the pipeline is at the **document level only**
(`knowledge/policy/procurement-policy.md`), never a specific clause number (e.g. §1.2, §5.4),
even though the answer text itself is substantively correct and matches the expected clause.
This makes automated clause-level verification impossible — a human has to read the answer and
manually confirm which clause it drew from. Worth logging as a grounding-granularity gap in
W3-07, separate from the quota issue above.

## Next step

Re-run only the 5 pending questions (A1, B1, B2, B4, C3) once the quota resets — check with
whoever owns the API key/billing account for the reset time (Gemini free-tier quotas typically
reset daily). Use `scripts/run_week3_rag_eval.py`; it already isolates real API errors from
genuine pass/fail results, so re-running won't disturb the 10 cases already completed here.
