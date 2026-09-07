# Project Charter

**ReqPrep — A Bounded Agentic Assistant for Purchase Requisition Preparation in Ugandan SMEs**

| | |
|---|---|
| Course | BSE4104 Emerging Trends in Software Engineering |
| Institution | Makerere University, CoCIS, School of Computing and Informatics Technology, Department of Networks |
| Course convener | Dr Kamulegeya Grace B (PhD) |
| Selected use case | SME procurement-preparation agent (Brief, Section 3) |
| Document | Week 1 deliverable — Project Charter v1.1 |
| Date | [PLACEHOLDER] |
| Group | [PLACEHOLDER: group identifier] |

*Sections marked **[ASSUMPTION]** or containing **[PLACEHOLDER]** are not yet agreed commitments and require team confirmation before submission.*

---

## 1. Problem statement

Small and medium-sized buyers in Uganda — building contractors, hardware retailers and comparable firms — conduct procurement using paper records, informal messaging and a single spreadsheet. Three failures recur. Reordering is reactive: a shortage is discovered when an item is needed rather than when stock crosses a threshold, converting routine replenishment into emergency purchasing. Supplier quotations are not comparable as received, because suppliers quote in different units of measure, treat value-added tax inconsistently, and price delivery separately or not at all. Finally, the resulting requisition is prepared from scratch and carries no record of why a particular supplier was chosen, so approval is granted without supporting evidence.

The cost is measurable in staff time per requisition, in price leakage on rushed purchases, and in the absence of an audit trail for approved spending.

## 2. Target user

**Primary user — the stores or procurement officer.** A single individual at a firm of approximately 20 to 80 staff, operating one site with an inventory of roughly 150 stock-keeping units and working relationships with six to ten suppliers. The officer transacts in Ugandan shillings, has moderate computer proficiency, and prepares requisitions for approval by a superior.

**Secondary user — the approver.** An operations manager or director who interacts with the system only to approve, reject or query a submitted requisition: a read operation followed by a single decision.

**Explicit non-users.** Suppliers, finance and payment functions, and external auditors are not users of this system. Excluding suppliers is deliberate: because the system has no channel to a supplier, no purchasing commitment can originate from it by construction rather than by policy alone.

## 3. Current pain point

In current practice the officer identifies a shortage, requests quotations through informal channels, and receives them in inconsistent formats. Comparison is performed by eye under time pressure, requiring mental conversion between units and inference about tax treatment. Applicable procurement rules — a minimum-quotation requirement, approval thresholds, preferred and excluded suppliers — are held informally rather than consulted. The requisition is then typed manually and the justification for supplier selection is not recorded.

A manual baseline is being established in Week 1: three sample cases worked by hand, recording elapsed time, arithmetic errors and unapplied policy rules. **[PLACEHOLDER: baseline results to be inserted once measured.]** These measurements are the comparison point for the Week 8 evaluation.

## 4. Proposed solution

ReqPrep assists the procurement officer in preparing a single-item purchase requisition. The officer opens a case for one stock item and supplies the quotations received. The system retrieves the applicable procurement policy from a controlled document corpus, extracts the commercial terms from each quotation, normalises them to a common basis, produces a ranked comparison with a recommended supplier and written justification, and prepares a draft requisition. It then stops. Supplier confirmation is performed by the officer and approval by the approver; the system performs neither.

The workflow is a traceable multi-step sequence executed through approved tools. The conversational element is a means of interacting with that workflow rather than the product itself, in accordance with the brief's requirement that a proposal must not be only a chatbot.

## 5. Why AI adds value

Artificial intelligence is applied to four tasks in which input variability defeats a rule-based approach. This section exists to justify the use of AI rather than to assert it.

1. **Extraction of commercial terms from quotation text.** Suppliers state unit of measure, tax treatment, delivery terms and validity in prose that varies by supplier and by document. Field extraction therefore cannot be reliably pattern-matched, and a regular-expression approach fails on the first supplier who phrases a term differently.
2. **Detection and escalation of ambiguity.** Where a quotation omits its unit, or a requested item matches several inventory records, the correct behaviour is a clarifying question rather than an assumption. Recognising which cases are under-determined is a judgement over unstructured input.
3. **Grounded explanation of policy.** Determining whether a rule applies to a given case requires locating relevant passages in the corpus, applying them to case particulars, and declining to answer where the corpus provides no basis.
4. **Selection of the next step within the bounded workflow.** Establishing what information remains outstanding and which approved tool to invoke next is a planning task over incomplete state.

No value is claimed for arithmetic, rule enforcement, authorisation or record-keeping, all of which are deterministic responsibilities.

## 6. Deterministic software responsibilities

Deterministic software retains control of every consequential operation:

- Reorder evaluation: comparison of stock level against reorder level and computation of suggested quantity.
- All monetary and unit arithmetic, recomputed in code from extracted fields: unit conversion, tax, delivery, landed cost per base unit and totals.
- Policy enforcement as code: minimum-quotation rule, approval-threshold routing, excluded-supplier check, quotation-validity check.
- Authorisation and role verification.
- Schema validation of every tool input and output.
- The requisition state machine, permitting only DRAFT → PENDING_APPROVAL → APPROVED | REJECTED | QUERIED.
- Requisition numbering, the immutable audit log, the iteration limit, the tool allow-list and retrieval scoping.

**Principle 1.** No figure produced by the model is used by the system. Where a model-stated figure disagrees with the code-computed value, the computed value prevails and the discrepancy is written to the log.

**Principle 2.** The implementation contains no automatic approval path at any value. Autonomous approval is therefore impossible rather than merely prohibited.

## 7. Primary workflow

One end-to-end workflow: **reorder signal to approved requisition, for a single stock item.**

| Stage | What happens | Performed by |
|---|---|---|
| 1. Reorder check | Stock level compared against reorder level; suggested quantity computed | Deterministic |
| 2. Case input | Item and quantity captured and validated; ambiguous item names raised as questions | Deterministic capture and validation; AI interpretation of free text |
| 3. Evidence gathering | Applicable policy retrieved from the corpus; commercial terms extracted from quotations | Deterministic retrieval and indexing; AI selection and extraction |
| 4. Normalise and compare | Quotations converted to landed cost per base unit and ranked; policy flags raised | Deterministic |
| 5. Draft requisition | Recommended supplier presented with justification and citations; draft record created | AI narrative; deterministic record creation |
| 6. Officer confirmation | Supplier confirmed and requisition submitted | Human |
| 7. Approval decision | Requisition approved, rejected or queried | Human |
| 8. Outcome | Approved requisition retained with its evidence trail; case state persisted | Deterministic |

**Bounded agency.** The agent operates within a fixed maximum of **[PLACEHOLDER: proposed 6]** tool-call iterations, may invoke only allow-listed tools, and hands off to the human with partial state intact when a limit is reached, a required input is unavailable, or a tool fails repeatedly.

## 8. Project scope

| Dimension | Commitment |
|---|---|
| Organisation | One firm, one site, Ugandan shillings only, goods only |
| Requisition | One stock item per requisition |
| Inventory | Approximately 150 stock-keeping units |
| Suppliers | Six to ten |
| Quotations | Three to five per case |
| Corpus | 25 to 40 documents and equivalent records |
| Tools | Four: `check_stock_levels`, `compare_quotations`, `create_requisition_draft`, `submit_for_approval` |
| Agency | One bounded agent loop |
| Memory | Two justified mechanisms: the case file, and human-confirmed supplier preference |
| Evaluation | 30 final scenarios spanning normal, edge, failure and adversarial cases |

Accepted quotation formats are structured records together with quotation letters in text form. Optical character recognition of scanned or photographed quotations is excluded.

## 9. Out of scope

**Excluded for capacity.** Multi-line requisitions; optical character recognition of scanned quotations; supplier performance scoring over time; prediction of reorder levels or demand; goods-received reconciliation, stock takes and write-offs; multiple sites, currencies or foreign-exchange handling; production authentication, multi-tenancy and integration with any external enterprise or accounting system; automatic solicitation of quotations; electronic mail, calendar or messaging integrations; a general-purpose procurement question-answering surface alongside the workflow.

**Excluded on safety grounds.** Issuing a purchase order or committing funds; payment of any kind, including simulated payment; contact with a supplier through any channel; autonomous supplier award; automatic approval at any value; use of any model-generated monetary figure by the system; persistent-memory writes capable of influencing later recommendations without human confirmation; open-ended tool use, code execution or web browsing; use of any real client, supplier or price data from any production system.

Two exclusions merit particular vigilance because a plausible-looking implementation could violate them while appearing compliant: the use of model-computed monetary values, and unconfirmed writes to persistent memory.

## 10. Data and corpus

All data is authored by the team and synthetic. The corpus comprises an inventory register with units of measure, reorder levels and supplier lead times; a supplier register with terms and preferred or excluded status; structured quotation records; quotation letters in text form, deliberately inconsistent in unit, tax treatment and delivery terms; and a team-authored procurement policy specifying approval thresholds, the minimum-quotation rule, preferred-supplier rules and the quotation-validity window.

Publicly available material — the standard value-added tax rate and general public-procurement principles — is cited for realism but not ingested. A source register recording the provenance of every corpus item is maintained at `knowledge/SOURCE-REGISTER.md`.

**Data declaration.** No client name, supplier identity, price or record originating from any production or commercial system is used in this project. The deliberate inconsistency of the synthetic quotation letters is a design requirement, since it supplies the adversarial cases against which the system is evaluated.

Corpus authoring owner: **[PLACEHOLDER: name]**; completion date: **[PLACEHOLDER: date]**.

## 11. Assumptions [ASSUMPTION]

| Assumption | Consequence if false |
|---|---|
| Reorder levels already exist in the inventory register and are approximately correct | The reorder signal carries no meaning and all cases must be initiated manually |
| Each quotation identifies its supplier and the item quoted | Extraction cannot proceed and the quotation must be rejected as incomplete |
| The procurement policy is internally consistent and current | Conflicting rules cannot be resolved by retrieval and require human interpretation |
| The officer can supply the correct unit of measure when asked | Ambiguous cases stall at the clarification step |
| An approver is available within the working period of a case | Requisitions accumulate in PENDING_APPROVAL and the end-to-end demonstration cannot complete |
| Quotations are received in text or structured form | Cases arriving only as photographs fall outside the accepted input formats |

## 12. Constraints

- **Schedule.** Eight weeks, 31 August to 23 October 2026, with presentations on 27, 29 and 30 October 2026.
- **Team.** [PLACEHOLDER: number] members with approximately [PLACEHOLDER: hours] hours per member per week available alongside concurrent coursework.
- **Model access.** [PLACEHOLDER: model, to be selected in Week 2]. No funded interface budget, so model choice is constrained to a free or low-cost tier, and a documented fallback is required in the event of rate or cost limits.
- **Data.** Synthetic and team-authored data only. No confidential, personal or restricted data may be transmitted to an external model service.
- **Evidence.** All work must be evidenced through GitHub, ClickUp and MUELE, with individual accountability for identifiable weekly tasks.
- **Infrastructure.** Local development with reproducible configuration. Connectivity and power availability must be assumed unreliable for demonstration purposes, requiring a rehearsed offline or recorded fallback.

## 13. Success criteria [PLACEHOLDER thresholds]

| # | Criterion | Threshold | Measurement |
|---|---|---|---|
| 1 | Safety boundary violations | Zero | Audit log review across all 30 evaluation scenarios |
| 2 | Overall scenario pass rate | ≥ [80]% | Week 8 execution of the 30-scenario set |
| 3 | Adversarial subset pass rate | ≥ [70]%, with every failure documented and root-caused | Adversarial cases within the same set |
| 4 | Monetary figures used by the system | 100% code-computed; every model–code discrepancy logged | Cross-check log |
| 5 | Grounded answers carrying a corpus citation | ≥ 90% | Manual review of retrieval-based responses |
| 6 | Unanswerable questions correctly declined | ≥ [80]% | Unanswerable subset of the 15-case retrieval evaluation |
| 7 | Correct handling of the reference mis-ranking case | Pass | The case in which the nominally cheapest quotation is not the lowest landed cost |
| 8 | Case resumption after restart | Pass | State reconstructed from persistence, not re-derived by the model |
| 9 | Preparation time against manual baseline | Improvement demonstrated | Comparison with Week 1 baseline measurements |

A refusal or a clarifying question is recorded as a pass where the alternative would have been an unsupported answer.

## 14. AI safety and control boundaries

The full AI Boundary Matrix is maintained at `ai-boundary-matrix.md`. Condensed form:

| AI may | Deterministic software must | Human approval required |
|---|---|---|
| Extract commercial terms from quotation text | Compute all monetary and unit values | Confirmation of the recommended supplier |
| Raise clarifying questions on ambiguity | Enforce policy rules and thresholds | Submission of a requisition for approval |
| Explain policy with citations, or decline | Verify role and authorisation | Approval, rejection or query of a requisition |
| Draft the requisition narrative | Govern state transitions and audit logging | Any override of a policy rule, with recorded reason |
| Select the next tool within the allow-list | Enforce the allow-list and iteration limit | Any write of a durable preference to memory |

**Prohibited actions.** Issuing a purchase order; any payment; contact with a supplier; autonomous supplier award; automatic approval; use of a model-generated monetary value; unconfirmed memory writes; tool use outside the allow-list; code execution or web browsing.

**Stop conditions.** The iteration limit is reached; a required input is unavailable; a tool fails after one retry; a policy override is required; a request falls outside the allow-list. In each case the agent halts and hands off with partial state preserved.

**Enforcement.** For each boundary, the enforcement mechanism — allow-list, role check, state machine, schema validation or prompt instruction — is recorded in the full matrix. Boundaries enforced by prompt instruction alone are identified as such and are candidates for hardening in Week 8.

## 15. Team and accountability

| Role | Member |
|---|---|
| Project / Requirements Lead | [PLACEHOLDER] |
| Application / Integration Lead | [PLACEHOLDER] |
| AI Engineering Lead | [PLACEHOLDER] |
| Quality / Security Lead | [PLACEHOLDER] |
| DevOps / Documentation Lead (five-member groups) | [PLACEHOLDER] |

Roles may rotate. Each member owns identifiable weekly tasks recorded in ClickUp and linked to repository evidence, and each member must be able to explain the system's major design decisions and observed failures. Use of AI tools in design, implementation, testing and documentation is declared in the AI Engineering Log at `../ai-engineering-log.md`.
