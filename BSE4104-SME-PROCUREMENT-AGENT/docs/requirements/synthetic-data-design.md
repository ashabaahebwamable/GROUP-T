# Synthetic Data Design

> Week 1 deliverable, BSE4104. **All data described here is synthetic and team-authored.**
> No client name, supplier identity, price or record from any production or commercial system
> is used anywhere in this project. Provenance is recorded in `../../knowledge/SOURCE-REGISTER.md`.

## Why synthetic data is the correct choice here

The brief requires data the team can obtain in Week 1 and forbids dependence on confidential databases. Synthetic data is not a compromise in this project: because the system's central difficulty is _inconsistency between quotations_, authoring the corpus is what lets the team place specific, known inconsistencies into it and then test whether the system handles them. A real corpus would be less useful, not more.

## 1. Inventory

`knowledge/records/inventory.csv` — 15 rows delivered, expanding to approximately 150.

| Field                        | Type                                 | Why it exists                                                                |
| ---------------------------- | ------------------------------------ | ---------------------------------------------------------------------------- |
| `item_id`                    | string                               | Stable key; the only way an item may be referenced                           |
| `item_name`                  | string                               | Human-readable; the target of free-text matching in US-02                    |
| `category`                   | string                               | Grouping for realistic supplier specialisation                               |
| `base_unit`                  | enum (kg, tonne, piece, litre, roll) | **The comparison basis.** All quotations are converted to this               |
| `pack_unit`                  | string                               | How the item is actually sold (50kg bag, 12m length)                         |
| `base_units_per_pack`        | number                               | The conversion factor; the field that makes unit-mismatch detection possible |
| `current_stock_base`         | number                               | Held in base units to avoid mixed-unit arithmetic                            |
| `reorder_level_base`         | number                               | Threshold for the reorder check (US-01)                                      |
| `target_stock_base`          | number                               | Basis of the suggested reorder quantity                                      |
| `supplier_lead_days_typical` | number                               | Tie-break input under policy clause 3.4                                      |
| `last_updated`               | date                                 | Staleness signal; supports an edge-case scenario                             |

Design note: stock and thresholds are stored in base units while suppliers quote in pack units. That single mismatch is the origin of the project's core problem, so it is built into the schema deliberately.

## 2. Supplier quotations

`knowledge/records/quotations.csv` — 10 structured records, plus quotation letters in text form under `knowledge/quotations/`.

| Field                                       | Type                        | Why it exists                                                                       |
| ------------------------------------------- | --------------------------- | ----------------------------------------------------------------------------------- |
| `quotation_id`                              | string                      | Key, and the citation handle in the comparison output                               |
| `supplier_id`                               | string                      | Joins to the supplier register for status checks                                    |
| `item_id`                                   | string                      | Joins to inventory for the conversion factor                                        |
| `quantity` / `quantity_unit`                | number / string             | As quoted, not as needed                                                            |
| `unit_price_ugx` / `price_unit`             | number / string             | **Rate and its unit kept together**, because a rate without its unit is meaningless |
| `vat_treatment`                             | enum (inclusive, exclusive) | The most common cause of a wrong comparison                                         |
| `delivery_charge_ugx` / `delivery_included` | number / boolean            | Landed cost cannot be computed without both                                         |
| `delivery_days`                             | number                      | Tie-break input                                                                     |
| `quotation_date` / `validity_days`          | date / number               | Together determine whether the quotation is still valid (policy 2.3)                |

## 3. Purchase requisitions

`knowledge/records/requisitions.csv` — schema with one example row.

| Field                                                    | Type   | Why it exists                                                                   |
| -------------------------------------------------------- | ------ | ------------------------------------------------------------------------------- |
| `requisition_id`                                         | string | System-assigned, never model-assigned (US-07)                                   |
| `case_id`                                                | string | Links the requisition to its case file and persisted state                      |
| `item_id`, `quantity_base`, `quantity_unit`              |        | The requirement, in base units                                                  |
| `recommended_supplier_id`                                | string | Set from rank one by code                                                       |
| `confirmed_supplier_id`                                  | string | **Separate field, empty until a human confirms.** The separation is the control |
| `landed_cost_per_base_unit_ugx`, `total_landed_cost_ugx` | number | Code-computed only (Principle 1)                                                |
| `justification_ref`                                      | string | Pointer to the stored narrative and citations, not the narrative itself         |
| `policy_flags`                                           | list   | Flags raised by the rule engine (US-06)                                         |
| `state`                                                  | enum   | DRAFT / PENDING_APPROVAL / APPROVED / REJECTED / QUERIED                        |
| `created_by`, `created_at`                               |        | Attribution                                                                     |
| `decided_by`, `decided_at`, `decision_reason`            |        | Approval attribution and any override reason                                    |

Design note: `recommended_supplier_id` and `confirmed_supplier_id` are deliberately two columns. A single "supplier" column would make it impossible to prove afterwards that a human made the choice.

## 4. Deliberate inconsistencies built into the data

The corpus is seeded with known traps. Each becomes an evaluation scenario in Week 7-8.

| Trap                                                | Where                              | What it tests                                               |
| --------------------------------------------------- | ---------------------------------- | ----------------------------------------------------------- |
| VAT-exclusive rate that looks cheapest              | QUO-1002                           | Uniform tax treatment (US-04 criterion 2)                   |
| Rate quoted per tonne against a per-kg base unit    | QUO-1003                           | Unit conversion (US-04 criterion 1)                         |
| Delivery charged separately                         | QUO-1002, QUO-1003, QUO-1005       | Delivery included in landed cost (US-04 criterion 3)        |
| Lapsed quotation (7-day validity, dated 20 Aug)     | QUO-1005                           | Validity exclusion (US-06 criterion 3, policy 2.3)          |
| Excluded supplier offering the lowest headline rate | QUO-1004 / SUP-05                  | Supplier status enforcement (US-06 criterion 2, policy 4.1) |
| Quotation omitting its unit of measure              | Outstanding Week 2 corpus addition | Refusal to default a missing field (US-03 criterion 2)      |

## 5. The reference mis-ranking case

The demonstration case: **10,000 kg of Portland cement 32.5N (INV-001)**, four quotations, VAT at 18%.

| Quotation         | Headline rate       | Landed cost per kg | Total     | Outcome                                                     |
| ----------------- | ------------------- | ------------------ | --------- | ----------------------------------------------------------- |
| QUO-1004 (SUP-05) | UGX 27,000 / bag    | 637.20             | 6,372,000 | **Excluded** — supplier status (policy 4.1)                 |
| QUO-1002 (SUP-02) | UGX 29,500 / bag    | 714.20             | 7,142,000 | Ranked last despite the lowest valid headline rate          |
| QUO-1003 (SUP-06) | UGX 590,000 / tonne | 711.20             | 7,112,000 | Second                                                      |
| QUO-1001 (SUP-01) | UGX 32,000 / bag    | **640.00**         | 6,400,000 | **Recommended** — highest headline rate, lowest landed cost |

Manual selection by headline rate picks the excluded supplier first, and the worst valid option second. The correct answer is the quotation that looks most expensive. **[ASSUMPTION: 18% VAT and these synthetic rates; figures verified arithmetically, not sourced from any market.]**

This single case is worth rehearsing for the final presentation, because it demonstrates the value of the system in one table.

## 6. Volume plan

| Asset                    | Week 1 | Target                                           |
| ------------------------ | ------ | ------------------------------------------------ |
| Inventory records        | 15     | ~150                                             |
| Suppliers                | 6      | 6-10                                             |
| Structured quotations    | 10     | 30-40                                            |
| Quotation letters (text) | 4      | 12-15                                            |
| Policy documents         | 1      | 2-3 (policy, threshold schedule, supplier terms) |
| **Total corpus items**   | **21** | **25-40 documents plus records**                 |

Week 1 delivers a working slice with the main ranking and policy traps represented. Expansion, including the missing-unit quotation, is a Week 2-3 task with an owner to be assigned after team roles are confirmed.
