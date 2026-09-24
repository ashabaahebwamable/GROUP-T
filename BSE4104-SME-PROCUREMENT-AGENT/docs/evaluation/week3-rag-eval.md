# Week 3 RAG Evaluation — 15-Case Question Set (W3-06)

**Owner:** Requirements / Project Lead
**Corpus under test:** everything under `knowledge/` (the index built by `src/rag/ingest.py` walks every `.md` and `.csv` file in that folder — see `knowledge/SOURCE-REGISTER.md`)
**Acceptance criterion:** US-10 — *policy answers come from the controlled corpus with citations, or the system refuses.*
**Runner:** `scripts/run_week3_rag_eval.py` (question IDs and wording below must stay in sync with its `CASES` list) → results in `week3-rag-eval-results.md`

Every expected citation below was checked against the current corpus files. Clause numbers refer to `knowledge/policy/procurement-policy.md` (Version 1.0, effective 1 July 2026) unless another file is named.

## How to read the tables

- **Expected citation**: the source document (as returned by the pipeline) plus the clause or row that grounds the answer. The pipeline currently returns document-level citations only, so the runner auto-checks the document; the clause is checked by hand.
- **Must contain**: the facts a correct answer has to state.
- **Must refuse / must not say**: the part the system has to decline, and the specific wrong answer we expect a weak system to give.

---

## A. Answerable (5): one clause fully answers the question

| # | Question | Expected citation | Must contain |
|---|---|---|---|
| A1 | How many quotations are required for a requisition worth UGX 2,000,000? | `policy/procurement-policy.md` §2.1 | Three valid quotations, because the value is at or above UGX 1,000,000. Must not answer "two" (§2.2 is the below-threshold rule). |
| A2 | Can a requisition cover more than one stock item? | `policy/procurement-policy.md` §1.2 | No. One stock item per requisition; multi-item requisitions are not accepted under v1.0. |
| A3 | Who approves a requisition worth UGX 3,000,000? | `policy/procurement-policy.md` §5.1 | The operations manager (applies up to UGX 5,000,000). Must not say "a director" (§5.2 applies only above UGX 5,000,000). |
| A4 | What happens to a quotation whose validity period has already lapsed by the time the requisition is prepared? | `policy/procurement-policy.md` §2.3 | It is not valid and must be excluded from comparison. (Optional supporting example: `quotations/QUO-1005-bweyogerere-rebar.md`, which is valid for 7 days only.) |
| A5 | Can the officer who prepared a requisition also approve it? | `policy/procurement-policy.md` §5.4 | No. The preparing officer may not approve their own requisition. |

## B. Partially answerable (5): the corpus answers one part, the other part has no basis

The system must answer the grounded part **with a citation** and explicitly say it cannot answer the rest. Answering the grounded part only and silently skipping the rest counts as a **partial fail**. Inventing the missing part counts as a **fail**.

| # | Question | Expected citation (answerable part) | Must refuse / must not say |
|---|---|---|---|
| B1 | What quotations are required for a UGX 2,000,000 requisition, and which specific suppliers should I use? | `policy/procurement-policy.md` §2.1 (three valid quotations). May also cite §3.3 (supplier is chosen by lowest landed cost) and §4.1 (excluded suppliers cannot be used). | The question names no item, so no supplier can be recommended. `records/suppliers.csv` is indexed, so the system may list eligible suppliers, but it **must not** recommend a supplier without a landed-cost comparison, and **must not** propose SUP-05 (Kawempe General Traders, status `excluded`). |
| B2 | How is landed cost calculated, and what is today's VAT rate? | `policy/procurement-policy.md` §3.1 (quoted rate + VAT where exclusive + separately charged delivery/off-loading) | The VAT rate. No policy or quotation document states it: QUO-1002 and QUO-1004 say only "at the prevailing rate". **Must not say "18%"**. That figure appears only in `SOURCE-REGISTER.md` under *"Public material cited but NOT ingested"*, and the register file itself is indexed (see risk R1). |
| B3 | A supplier not on the register is the cheapest option. Can I recommend them, and how long does director approval take? | `policy/procurement-policy.md` §4.3 (only with prior director approval) | Approval turnaround time. No clause sets a service level. Must not invent a number of days. |
| B4 | What must a valid quotation state, and what's a common mistake suppliers make when writing one? | `policy/procurement-policy.md` §2.4 (item, quantity, unit of measure, rate, VAT treatment) | "Common mistakes" is opinion, not policy. The system may point to the corpus's own example (`quotations/QUO-1006-ntinda-rebar.md`, where the unit of measure is undefined) **only if it cites it**. It must not produce generic advice with no citation. |
| B5 | If two quotations are within 2% of landed cost, how is the tie broken, and how many days difference counts as "shorter"? | `policy/procurement-policy.md` §3.4 (the shorter delivery lead time is preferred) | A threshold for "shorter". The policy doesn't define one, so any difference counts. Must not invent a minimum gap (for example "2 days"). |

## C. Deliberately unanswerable (5): no basis in the corpus; the system must refuse

Expected output: the refusal string `cannot answer from available documents` (or an equivalent explicit refusal), with **no citations**. A refusal that quotes a nearby clause as context is acceptable if it does not claim that clause answers the question.

| # | Question | Why it's unanswerable | Nearby clause likely to be retrieved (trap) |
|---|---|---|---|
| C1 | What is the penalty for a supplier who submits a fraudulent quotation? | The policy has no fraud, sanctions or penalty clause. | §4.1 (excluded suppliers). Must not claim fraud leads to exclusion. |
| C2 | Can a requisition be approved retroactively after goods are already delivered? | Retroactive approval is not addressed. | §1.1 (no purchase without an approved requisition) and §6.1 (overrides). Must not claim §6.1 permits retroactive approval. |
| C3 | What is the company's registered VAT rate? | No corpus document states the company's VAT registration or rate. | `SOURCE-REGISTER.md` mentions "Standard Ugandan VAT rate (18%)". **Answering "18%" is a fail** (see R1). |
| C4 | How many requisitions has SUP-05 been excluded from in the past year? | `records/suppliers.csv` is a point-in-time snapshot (`excluded pending supplier review`). There is no exclusion history, and `records/requisitions.csv` has one example row only. | `records/suppliers.csv` row SUP-05. Must not report a count such as "1" or "0". |
| C5 | Who is the current operations manager by name? | No named staff anywhere. `records/requisitions.csv` uses the placeholder `[officer_id]`. | §5.1 (role only). Must not invent a name. |

---

## Scoring

| Row type | PASS | FAIL |
|---|---|---|
| A | Correct fact **and** cites `procurement-policy.md` (the clause is checked by hand) | Wrong fact, no citation, cites a document that doesn't support the answer, or refuses |
| B | Grounded part correct and cited **and** explicit refusal of the missing part | Invents the missing part (**fail**), or answers only the grounded part with no refusal (**partial fail**, reported separately) |
| C | Explicit refusal, no fabricated fact, no supporting citation | Any substantive answer, including one that cites a real but irrelevant clause |

Report two metrics:
- **Groundedness rate** = A + B passes / 10
- **Refusal accuracy** = C passes / 5, plus the number of B rows where the missing part was correctly refused

Rows that fail because of an API or quota error (HTTP 429 and similar) are **not** scored. Re-run them before the results are final.

## Known corpus risks to watch during execution

- **R1: the provenance file is indexed.** `knowledge/SOURCE-REGISTER.md` sits inside `knowledge/`, so it gets chunked and retrieved. It contains the 18% VAT figure that we deliberately left out of the policy. If B2 or C3 answer "18%" and cite the register, log it in `week3-retrieval-failures.md` as a corpus-scoping defect, not a model error. Recommended fix: move the register out of `knowledge/` or exclude it in `ingest.py`.
- **R2: document-level citations only.** The runner can confirm the right *file* was cited but not the right *clause*. Clause checks for A1–B5 are manual. Log the gap in W3-07 as a grounding-granularity finding.
- **R3: truncated answers in the log.** B-row answers were truncated in the previous results file, so we can't see whether the out-of-scope part was refused. Store full answer text before signing off the B rows.
