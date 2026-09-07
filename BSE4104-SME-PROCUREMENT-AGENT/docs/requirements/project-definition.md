# Part 1 — Final Project Definition

> Week 1 deliverable, BSE4104. Compact reference form. The prose version for
> submission is `project-charter.md`; the two must always agree.
> Items marked **[ASSUMPTION]**, **[PLACEHOLDER]** or **[OPTIONAL]** are labelled as such deliberately.

## 1. Project title

**ReqPrep — A Bounded Agentic Assistant for Purchase Requisition Preparation in Ugandan SMEs**
*(name subject to group confirmation)*

## 2. One-paragraph description

ReqPrep assists a small-business stores officer in preparing a single-item purchase requisition. It checks stock against reorder levels, reads the commercial terms out of supplier quotations, converts those quotations to a common comparable basis, checks the applicable procurement rules, and produces a draft requisition with a recommended supplier and written justification. It then stops. Supplier confirmation is performed by the officer and approval by a designated approver. The system issues no purchase order, contacts no supplier, and moves no money.

## 3. Problem statement

Small and medium buyers in Uganda run procurement on paper, informal messaging and one spreadsheet. Reordering is reactive, so shortages become emergency purchases. Quotations arrive in inconsistent units, with inconsistent tax treatment and delivery pricing, and are compared by eye under time pressure. The resulting requisition is typed from scratch and records no reason for the supplier chosen, so approval is granted without supporting evidence.

## 4. Target users

| Role | Who | What they do in the system |
|---|---|---|
| Primary | Stores / procurement officer at a firm of ~20-80 staff, one site, ~150 SKUs, 6-10 suppliers, transacting in UGX | Opens cases, supplies quotations, confirms supplier, submits for approval |
| Secondary | Approver (operations manager or director) | Reads the case, then approves, rejects or queries once |
| Non-users | Suppliers, finance/payments, external auditors | No access. Excluding suppliers means no purchasing commitment can originate from the system by construction |

## 5. Current procurement pain points

1. Reorder is discovered at point of need, not at threshold.
2. Quotations are not comparable as received (unit of measure, VAT treatment, delivery pricing, validity).
3. Comparison arithmetic is manual and error-prone under time pressure.
4. Procurement rules exist in a document nobody consults.
5. The supplier decision leaves no recorded justification, so approval is uninformed.
6. The requisition is retyped for every case.

## 6. Proposed solution

A bounded agentic assistant over one workflow, with four approved tools, a controlled document corpus, and two human decision gates. Not a chatbot: the conversational surface is a way of driving a traceable multi-step workflow, and the artefact produced is a draft requisition with its evidence trail.

## 7. Primary user

The stores / procurement officer. All other roles are secondary or excluded.

## 8. Primary end-to-end workflow

Reorder signal to approved requisition, **one stock item per case**.

| # | Stage | Performed by |
|---|---|---|
| 1 | Reorder check: current stock compared with reorder level; suggested quantity computed | Deterministic |
| 2 | Case opened: item and quantity captured and validated; ambiguity raised as a question | AI interprets free text; deterministic validation |
| 3 | Evidence gathered: policy retrieved from corpus; commercial terms extracted from quotations | Deterministic retrieval; AI extraction |
| 4 | Comparison: quotations normalised to landed cost per base unit, ranked; policy flags raised | Deterministic |
| 5 | Draft prepared: recommended supplier with written justification and citations; DRAFT record created | AI narrative; deterministic record |
| 6 | Officer confirms supplier and submits | Human |
| 7 | Approver approves, rejects or queries | Human |
| 8 | Decision recorded with full evidence trail; case state persisted | Deterministic |

Bounded agency: fixed maximum of **[PLACEHOLDER: proposed 6]** tool-call iterations, allow-listed tools only, hand-off with partial state preserved on any stop condition.

## 9. Why AI adds value

Four tasks where input variability defeats a rule-based approach:

1. **Extraction from quotation text** — suppliers state unit, tax treatment, delivery and validity in prose that varies per supplier and document, so fields cannot be reliably pattern-matched.
2. **Ambiguity detection and escalation** — recognising that a unit is missing or an item name matches several records, and asking rather than assuming.
3. **Grounded policy explanation** — locating relevant passages, applying them to the case, and declining where the corpus gives no basis.
4. **Next-step selection within the bounded loop** — planning over incomplete case state.

No AI value is claimed for arithmetic, rule enforcement, authorisation or record-keeping.

## 10. What deterministic software handles

Reorder arithmetic; all monetary and unit computation; policy rules as code; authorisation and role checks; schema validation of every tool input and output; the requisition state machine; requisition numbering; the immutable audit log; iteration limits; the tool allow-list; retrieval scoping.

**Principle 1.** No model-produced figure is used by the system. Where a model-stated figure differs from the code-computed value, the computed value prevails and the discrepancy is logged.
**Principle 2.** No automatic approval path exists at any value, so autonomous approval is impossible rather than merely prohibited.

## 11. What requires human approval

| Action | Gate |
|---|---|
| Read stock, quotations, policy | None (read-only, allow-listed) |
| Create or edit a draft requisition | None (logged) |
| Confirm the recommended supplier | Officer confirms; system never finalises |
| Submit for approval | Officer |
| Approve / reject / query | Approver only, at any value |
| Override a policy rule | Human, with recorded reason |
| Write a durable preference to memory | Human confirmation |

## 12. Explicitly out of scope

**Capacity:** multi-line requisitions; OCR of scanned or photographed quotations; supplier performance scoring; demand or reorder-point prediction; goods-received reconciliation, stock takes, write-offs; multi-site, multi-currency, FX; production authentication, multi-tenancy, ERP or accounting integration; automatic solicitation of quotations; email, calendar or messaging integration; a general-purpose procurement Q&A surface alongside the workflow.

**Safety:** issuing a purchase order or committing funds; payment of any kind, including simulated payment; contacting a supplier through any channel; autonomous supplier award; automatic approval at any value; use of any model-generated monetary figure; unconfirmed persistent-memory writes; open-ended tool use, code execution or web browsing; any real client, supplier or price data from any production system.

## 13. Available data

Team-authored synthetic data only — see `synthetic-data-design.md` and `../../knowledge/SOURCE-REGISTER.md`. Inventory register, supplier register, structured quotation records, quotation letters in text form, and a team-written procurement policy. Public material (standard VAT rate, general public-procurement principles) is cited for realism but not ingested.

**Declaration:** no client name, supplier identity, price or record from any production or commercial system is used in this project.

## 14. Assumptions **[ASSUMPTION — group confirmation required]**

| Assumption | Consequence if false |
|---|---|
| Reorder levels exist in the inventory register and are approximately correct | The reorder signal is meaningless; all cases must be opened manually |
| Each quotation identifies its supplier and the item quoted | Extraction cannot proceed; the quotation is rejected as incomplete |
| The procurement policy is internally consistent and current | Conflicting rules cannot be resolved by retrieval; human interpretation required |
| The officer can supply the correct unit of measure when asked | Ambiguous cases stall at the clarification step |
| An approver is available within the working period of a case | Requisitions accumulate in PENDING_APPROVAL; the end-to-end demo cannot complete |
| Quotations arrive as text or structured records | Photographed-only quotations fall outside accepted input formats |

## 15. Constraints

- **Schedule:** 8 weeks, 31 Aug - 23 Oct 2026; presentations 27, 29, 30 Oct 2026.
- **Team:** [PLACEHOLDER: number] members, ~[PLACEHOLDER: hours]h per member per week alongside concurrent coursework.
- **Model access:** [PLACEHOLDER: model, selected Week 2]. No funded budget, so a free or low-cost tier with a documented fallback for rate and cost limits.
- **Data:** synthetic, team-authored only. No confidential, personal or restricted data to any external model service.
- **Evidence:** GitHub + ClickUp + MUELE, with individual accountability for identifiable weekly tasks.
- **Infrastructure:** local development, reproducible configuration; connectivity and power must be assumed unreliable for the demonstration, so a rehearsed offline or recorded fallback is required.

## 16. Success criteria **[PLACEHOLDER thresholds require group agreement]**

| # | Criterion | Threshold | Measured by |
|---|---|---|---|
| 1 | Safety boundary violations | Zero | Audit log review across all 30 scenarios |
| 2 | Overall scenario pass rate | >= [80]% | Week 8 run of the 30-scenario set |
| 3 | Adversarial subset pass rate | >= [70]%, every failure root-caused | Adversarial cases in that set |
| 4 | Monetary figures used by the system | 100% code-computed; every model-code discrepancy logged | Cross-check log |
| 5 | Grounded answers carrying a citation | >= 90% | Manual review of retrieval responses |
| 6 | Unanswerable questions correctly declined | >= [80]% | Unanswerable subset of the 15-case RAG set |
| 7 | Reference mis-ranking case handled correctly | Pass | The case where the nominally cheapest quotation is not lowest landed cost |
| 8 | Case resumption after restart | Pass | State reconstructed from persistence, not re-derived by the model |
| 9 | Preparation time vs manual baseline | Improvement demonstrated | Comparison with the Week 1 baseline **[PLACEHOLDER: baseline not yet measured]** |

A refusal or clarifying question counts as a pass where the alternative would have been an unsupported answer.
