# Week 3 RAG Evaluation — 15-Case Question Set (DRAFT — pending Mable's review)

Owner: Ashaba Ahebwa Mable (questions) + Akisa Maria Ashley (execution). This file is the
**question set** deliverable for W3-06. Drafted against the actual `procurement-policy.md` so
every expected citation is real, not invented — Mable, please sanity-check wording and add/swap
anything before we run it.

Each row will be filled in during execution with: the system's actual answer, whether it cited
the expected clause, and pass/fail against US-10 ("Policy answers come from the controlled corpus
with citations, or the system refuses").

## A. Answerable (5) — a single policy clause fully answers the question

| # | Question | Expected citation |
|---|---|---|
| A1 | How many quotations are required for a requisition worth UGX 2,000,000? | §2.1 — three valid quotations (≥ UGX 1,000,000) |
| A2 | Can a requisition cover more than one stock item? | §1.2 — no, one item per requisition |
| A3 | Who approves a requisition worth UGX 3,000,000? | §5.1 — the operations manager (≤ UGX 5,000,000) |
| A4 | What happens to a quotation whose validity period has already lapsed by the time the requisition is prepared? | §2.3 — it must be excluded from comparison |
| A5 | Can the officer who prepared a requisition also approve it? | §5.4 — no |

## B. Partially answerable (5) — policy covers part of the question; the rest is out of scope or needs another source

| # | Question | Expected citation | What's out of scope |
|---|---|---|---|
| B1 | What quotations are required for a UGX 2,000,000 requisition, and which specific suppliers should I use? | §2.1 (quotation count) | Naming specific suppliers is a supplier-register lookup, not a policy question — system should answer the count and say supplier selection needs the supplier register/comparison, not guess names |
| B2 | How is landed cost calculated, and what is today's VAT rate? | §3.1 (landed cost components) | The actual VAT percentage is not stated in this policy document — system should answer the formula and refuse to state a VAT rate not present in the corpus |
| B3 | A supplier not on the register is the cheapest option — can I recommend them, and how long does director approval take? | §4.3 (requires director approval) | Approval turnaround time isn't a policy fact — should refuse that part |
| B4 | What must a valid quotation state, and what's a common mistake suppliers make when writing one? | §2.4 (required fields) | "Common mistakes" is commentary, not policy — should not fabricate an answer here |
| B5 | If two quotations are within 2% of landed cost, how is the tie broken, and how many days difference counts as "shorter"? | §3.4 (shorter lead time preferred) | Policy does not define a threshold for "shorter" — system should refuse to invent a number |

## C. Deliberately unanswerable (5) — no basis in the corpus; system must refuse, not guess

| # | Question | Why it's unanswerable |
|---|---|---|
| C1 | What is the penalty for a supplier who submits a fraudulent quotation? | Policy has no fraud/penalty clause at all |
| C2 | Can a requisition be approved retroactively after goods are already delivered? | Not addressed anywhere in the policy |
| C3 | What is the company's registered VAT rate? | Never stated in any corpus document |
| C4 | How many requisitions has SUP-05 been excluded from in the past year? | Requires historical data the corpus doesn't contain (register is a point-in-time snapshot) |
| C5 | Who is the current operations manager by name? | No named individuals appear in the policy or supplier register |

## Execution notes (fill in once run against the pipeline)

- Pass criteria (US-10): answer must cite the correct clause/document for A and B rows, and must explicitly refuse (not guess) for the out-of-scope part of B rows and for all C rows.
- Record: actual answer text, citation given (or absence of one), pass/fail, and one-line note on failure mode if any.
