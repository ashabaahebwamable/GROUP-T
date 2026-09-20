# Corpus Source Register

> Required by the BSE4104 brief: provenance for every item in the controlled corpus.
> **Every item below is synthetic and team-authored.** No client, supplier, price or record
> from any production or commercial system appears in this project.

## Records

| File                        | Items                     | Origin                    | Authored by                                     | Date                 | Notes                                                                           |
| ---------------------------- | ------------------------- | ------------------------- | ------------------------------------------------ | --------------------- | -------------------------------------------------------------------------------- |
| `records/inventory.csv`      | 15 of a target ~150 SKUs  | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | Ugandan building-materials categories; base and pack units deliberately differ  |
| `records/suppliers.csv`      | 6 suppliers                | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | Includes one excluded supplier (SUP-05) for the policy test                     |
| `records/quotations.csv`     | 10 quotations               | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | Deliberately inconsistent unit, VAT and delivery conventions                     |
| `records/requisitions.csv`   | 1 example row               | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | Schema demonstration only                                                         |

## Documents

| File                                        | Type              | Origin                    | Authored by                                     | Date                 | Purpose in the corpus                                          |
| --------------------------------------------- | ----------------- | -------------------------- | ------------------------------------------------ | --------------------- | ----------------------------------------------------------------- |
| `policy/procurement-policy.md`               | Policy            | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | Primary retrieval target for grounded policy questions. Contains the approval-threshold table (§5), the excluded-supplier rule (§4.1), unit-of-measure and quotation-completeness rules (§2.4, §3.2) — these are policy clauses, not separate documents, and are indexed as such |
| `quotations/QUO-1001-nakawa-cement.md`       | Quotation letter  | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | VAT-inclusive, delivery included — the true cheapest              |
| `quotations/QUO-1002-kireka-cement.md`       | Quotation letter  | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | VAT-exclusive with separate delivery — the apparent cheapest      |
| `quotations/QUO-1003-ntinda-cement.md`       | Quotation letter  | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | Quoted per tonne against a per-kg base unit                        |
| `quotations/QUO-1004-kawempe-cement.md`      | Quotation letter  | Synthetic, team-authored  | Akisa Maria Ashley (Quality/Security Lead)       | 2026-09-17            | Lowest headline rate, but supplier is excluded (SUP-05, policy 4.1) — the manual-selection trap |
| `quotations/QUO-1005-bweyogerere-rebar.md`   | Quotation letter  | Synthetic, team-authored  | Azibo Isaac Alinda (initial repository author)  | 2026-09-07 baseline  | Seven-day validity, lapsed — exclusion test                        |
| `quotations/QUO-1006-ntinda-rebar.md`        | Quotation letter  | Synthetic, team-authored  | Akisa Maria Ashley (Quality/Security Lead)       | 2026-09-17            | Quantity given without a defined unit of measure — refusal-to-default test (policy 2.4) |

## Public material cited but NOT ingested

| Source                                                                                     | Use                                                                |
| --------------------------------------------------------------------------------------------- | --------------------------------------------------------------------- |
| Standard Ugandan VAT rate (18%)                                                              | Realism of tax arithmetic in the synthetic policy and quotations   |
| General public-procurement principles (multiple-quotation practice, approval thresholds)   | Shape of the synthetic policy document                             |

These are referenced for realism only. No text is copied into the corpus and no external document is retrieved by the system.

## Corpus volume against the Week 3 target (10-50 documents or equivalent records)

- Documents: 1 policy + 6 quotation letters = **7 documents**
- Records: 15 inventory rows + 6 supplier rows + 10 quotation rows + 1 requisition row = **32 structured records**
- Combined, the corpus is within the required range once records are counted as equivalent items, as the brief allows. Structured records (CSV) carry most of the volume; free-text documents (policy + letters) carry most of the retrieval/grounding complexity, which is what Week 3's RAG evaluation actually exercises.

## Outstanding

- [ ] Expand inventory to ~150 SKUs (not blocking for Week 3 RAG evaluation; needed for later scale testing)
- [x] QUO-1004 (excluded-supplier trap) and QUO-1006 (missing-unit-of-measure trap) letters added 2026-09-17 to close the gap identified in Quality/Security Lead review — previously flagged as missing against the six traps described in `synthetic-data-design.pdf`
- [ ] Confirm with the team whether the approval-threshold table and excluded-supplier list should also exist as standalone documents for retrieval, or whether indexing them as clauses within `procurement-policy.md` and rows within `suppliers.csv` is sufficient for the RAG pipeline's chunking strategy (Quality/Security Lead recommendation: current approach is sufficient and avoids duplicating the source of truth — raise only if retrieval testing in W3-06 shows otherwise)
