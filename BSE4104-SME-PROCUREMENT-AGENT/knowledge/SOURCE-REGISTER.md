# Corpus Source Register

> Required by the BSE4104 brief: provenance for every item in the controlled corpus.
> **Every item below is synthetic and team-authored.** No client, supplier, price or record
> from any production or commercial system appears in this project.

## Records

| File | Items | Origin | Authored by | Date | Notes |
|---|---|---|---|---|---|
| `records/inventory.csv` | 15 of a target ~150 SKUs | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | Ugandan building-materials categories; base and pack units deliberately differ |
| `records/suppliers.csv` | 6 suppliers | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | Includes one excluded supplier for the policy test |
| `records/quotations.csv` | 10 quotations | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | Deliberately inconsistent unit, VAT and delivery conventions |
| `records/requisitions.csv` | 1 example row | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | Schema demonstration only |

## Documents

| File | Type | Origin | Authored by | Date | Purpose in the corpus |
|---|---|---|---|---|---|
| `policy/procurement-policy.md` | Policy | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | Primary retrieval target for grounded policy questions |
| `quotations/QUO-1001-nakawa-cement.md` | Quotation letter | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | VAT-inclusive, delivery included — the true cheapest |
| `quotations/QUO-1002-kireka-cement.md` | Quotation letter | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | VAT-exclusive with separate delivery — the apparent cheapest |
| `quotations/QUO-1003-ntinda-cement.md` | Quotation letter | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | Quoted per tonne against a per-kg base unit |
| `quotations/QUO-1005-bweyogerere-rebar.md` | Quotation letter | Synthetic, team-authored | [PLACEHOLDER] | [PLACEHOLDER] | Seven-day validity, lapsed — exclusion test |

## Public material cited but NOT ingested

| Source | Use |
|---|---|
| Standard Ugandan VAT rate (18%) | Realism of tax arithmetic in the synthetic policy and quotations |
| General public-procurement principles (multiple-quotation practice, approval thresholds) | Shape of the synthetic policy document |

These are referenced for realism only. No text is copied into the corpus and no external document is retrieved by the system.

## Outstanding

- [ ] Expand inventory to ~150 SKUs **[owner: PLACEHOLDER]**
- [ ] Expand to 25-40 corpus documents and equivalent records
- [ ] Add remaining quotation letters, including one omitting its unit of measure entirely
