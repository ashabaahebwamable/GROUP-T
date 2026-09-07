# AI Boundary Matrix

> Week 1 deliverable, BSE4104. Full version; a condensed form appears in
> `project-charter.md` §14. This document is the authority where the two differ.

## Purpose

The brief requires students to justify where AI adds value and where deterministic software or human decision-making must remain in control. This matrix is that justification in auditable form. It exists for three reasons:

1. **Safety.** A financial workflow must not commit an SME to a purchase on the strength of a probabilistic output. Naming each prohibited action, and the mechanism that prevents it, converts an intention into a control.
2. **Explainability.** When a decision is questioned, the matrix identifies which component produced which part of the output, so the answer is traceable rather than speculative.
3. **Testability.** Every row implies a test. The rows below map directly onto the user stories and the 30-scenario evaluation set.

## Governing principles

**Principle 1.** No figure produced by the model is used by the system. Where a model-stated figure disagrees with the code-computed value, the computed value prevails and the discrepancy is logged.

**Principle 2.** The implementation contains no automatic approval path at any value, so autonomous approval is impossible rather than merely prohibited.

**Principle 3.** The system has no channel to any supplier and no payment capability of any kind. Purchasing and payment are therefore not restricted features but absent ones.

## Enforcement mechanisms

The final column of each row names how the boundary is enforced. Strength descends in this order, and boundaries enforced by prompt instruction alone are flagged for hardening in Week 8.

| Code | Mechanism | Strength |
|---|---|---|
| ABS | Capability absent from the system | Strongest — cannot be violated |
| ALLOW | Tool allow-list check before execution | Strong |
| ROLE | Role and authorisation check | Strong |
| FSM | State-machine transition validation | Strong |
| CODE | Rule or computation implemented in code | Strong |
| SCHEMA | Input/output schema validation | Moderate |
| LIMIT | Iteration or retry limit | Moderate |
| LOG | Audit log and cross-check (detective, not preventive) | Moderate |
| PROMPT | Prompt instruction only | Weak — declared, to be hardened |

---

## The matrix

| # | System activity | AI may do | Deterministic software must do | Human approval required | AI prohibited from doing | Reason | Enforcement |
|---|---|---|---|---|---|---|---|
| 1 | Inventory interpretation | Interpret a free-text item description into a candidate stock item; ask which item is meant when several match | Resolve the item code against the register; reject unknown codes; validate quantity type and sign | None | Creating or amending an inventory record; inventing a stock item that is not in the register | Inventory is the system of record for every downstream computation; a fabricated item would corrupt the whole case | SCHEMA, CODE |
| 2 | Reorder reasoning | Explain in words why an item appears in the reorder list | Compare current stock with the reorder level; compute the suggested quantity | None | Deciding that an item needs reordering; altering a reorder level | The decision is a threshold comparison with a single correct answer, so a probabilistic component adds risk without adding value | CODE |
| 3 | Quotation extraction | Read supplier, item, quantity, unit, unit price, tax treatment, delivery terms and validity from quotation text; report fields it cannot find | Validate the extracted record against the canonical schema; reject records with missing mandatory fields | None | Filling a missing field with a default or an inferred value | Extraction over varying prose is where AI genuinely adds value, but an invented unit or tax treatment would silently corrupt the comparison | SCHEMA, PROMPT |
| 4 | Quotation comparison | Explain the comparison in prose; describe why one quotation ranks above another | Convert units; apply tax; add delivery; compute landed cost per base unit; sort the results | None | Producing, estimating or restating any monetary figure that the system then uses; ordering the ranking itself | Arithmetic has one correct answer and is the basis of a financial recommendation; Principle 1 applies | CODE, LOG |
| 5 | Recommendation generation | Write the justification narrative for the top-ranked quotation; state the trade-offs | Determine rank order; set the recommended supplier to rank one; attach flags and citations | Officer confirms the recommendation before it proceeds | Recommending a supplier other than the code-determined rank one; presenting a recommendation as a decision | Keeps selection auditable and prevents the narrative from diverging from the computed evidence | CODE, PROMPT |
| 6 | Requisition drafting | Draft the requisition narrative and justification text | Create the record, assign the requisition number, set state DRAFT, write the audit entry | None for creating a draft (it commits nothing) | Setting a requisition state; assigning a requisition number; writing to the audit log | A draft is reversible and low-risk; state and identity are integrity-critical and belong in code | FSM, CODE |
| 7 | Validation | Point out to the user that something appears missing or inconsistent | Enforce every rule: minimum quotations, thresholds, excluded suppliers, quotation validity, schema conformance | None | Judging a case compliant; waiving, softening or reinterpreting a rule | Rules must give the same answer every time and be inspectable by an auditor | CODE, SCHEMA |
| 8 | Authorisation | Nothing | Verify identity and role on every action; refuse and log unauthorised attempts | The action itself, where the matrix requires it | Evaluating whether a user is permitted to act; approving anything | Authorisation is a security control and cannot rest on a probabilistic component | ROLE |
| 9 | Tool use | Propose which allow-listed tool to call next and with what arguments | Check the tool against the allow-list, validate arguments against schema, execute, return the result | None for read-only and draft tools | Calling a tool not on the allow-list; executing code; browsing the web; constructing new capabilities | Bounded agency requires that the set of possible actions be fixed and known in advance | ALLOW, SCHEMA |
| 10 | Supplier selection and award | Explain the merits of each supplier | Rank quotations and present the comparison | Officer confirms the supplier for the draft | Awarding business to a supplier; treating the officer's confirmation as an award | Award is a commercial commitment and is outside project scope entirely | ABS, PROMPT |
| 11 | Purchasing | Nothing | Nothing — the capability does not exist | Not applicable | Issuing a purchase order; committing funds; creating any instruction to buy | Prohibited by the brief's safety boundary for this use case; no purchase-order capability is implemented at all | ABS |
| 12 | Payment | Nothing | Nothing — the capability does not exist | Not applicable | Initiating, scheduling or simulating any payment | Prohibited by the brief; the system holds no payment interface, credential or channel | ABS |
| 13 | Approval | Summarise the case for the approver | Enforce role, validate the state transition, record the decision with identity and timestamp | Approver decision on every requisition, at every value | Approving a requisition; recommending that approval be automatic; inferring approval from silence or inactivity | Approval is the control that makes the whole workflow safe; Principle 2 applies | ROLE, FSM |
| 14 | Rejection and query | Draft the wording of a rejection or query note for the human to review | Record the outcome and the reason; move the requisition to the correct state | Approver decision | Rejecting or querying a requisition on its own initiative | Rejection has commercial consequences for the case and must be attributable to a person | ROLE, FSM |
| 15 | Missing information | Identify the specific field that is missing and ask the user for it | Block progression while a mandatory field is absent; record what was requested | Human supplies the value | Guessing, defaulting or inferring a missing commercial term | A guessed unit or tax treatment produces a confidently wrong recommendation, the most dangerous failure mode in this workflow | SCHEMA, PROMPT |
| 16 | Conflicting quotation data | Report the conflict and describe the alternatives | Detect the conflict deterministically where it is detectable (duplicate quotations, contradictory totals, quantity mismatch); block ranking of an unresolved conflict | Human resolves the conflict | Choosing which conflicting figure to believe | Resolving a conflict is a commercial judgement with financial consequence | CODE, PROMPT |
| 17 | Unsupported requests | State that the corpus does not support an answer, and cite nothing | Scope retrieval to the approved corpus; return provenance with every retrieved passage | None | Answering from general knowledge; presenting an uncited assertion as policy | Grounding is the point of the retrieval layer; an ungrounded policy claim could cause a real rule to be breached | PROMPT, LOG |
| 18 | Failure handling | Recognise that a step did not succeed and state what remains outstanding | Enforce the iteration limit and single retry; halt; preserve partial state; write the failure to the log | Human resumes or abandons the case | Retrying indefinitely; substituting an alternative action for the failed one; concealing a failure | Unbounded retry is the classic agent failure mode and produces cost, latency and silent incorrectness | LIMIT, LOG |
| 19 | Persistent memory | Suggest that a preference might be worth remembering | Write the preference only on explicit confirmation, with the confirming identity and timestamp | Human confirms every durable preference write | Writing a durable preference on its own initiative; using an unconfirmed preference to influence a recommendation | Memory that silently shapes later recommendations moves the decision away from the human without anyone noticing | CODE, LOG |
| 20 | Audit and evidence | Summarise the case history in words for a human reader | Write the immutable audit trail; timestamp and attribute every state change | None | Editing, deleting or rewriting an audit entry | The audit trail is the evidence that the boundaries above were respected, so it cannot be model-writable | CODE |

---

## Check against the brief's stated safety boundary

The brief's safety boundary for this use case is: *no real purchasing, payment, supplier award or autonomous financial commitment.*

| Brief prohibition | Matrix rows | How it is prevented |
|---|---|---|
| Real purchasing | 10, 11 | No purchase-order capability exists (ABS) |
| Payment | 12 | No payment interface, credential or channel exists (ABS) |
| Supplier award | 5, 10 | Officer confirmation produces a draft only; award is out of scope (ABS, PROMPT) |
| Autonomous financial commitment | 4, 5, 11, 12, 13 | No model figure is used (Principle 1); no auto-approval path exists (Principle 2); approval is role-gated (ROLE, FSM) |

## Boundaries currently enforced by prompt instruction alone

Declared honestly, per the brief's expectation that students own the limitations of their own system. These are the Week 8 hardening candidates:

- Row 3 — no defaulting of a missing extracted field. Partially mitigated by schema validation, which catches absence but not a plausible invented value.
- Row 5 — narrative confined to figures present in the comparison table.
- Row 15 — no guessing of missing commercial terms.
- Row 16 — no selection between conflicting figures.
- Row 17 — no answering from general knowledge.

**Planned hardening [OPTIONAL for Week 1, required by Week 8]:** a post-generation validator that checks every numeral appearing in model narrative against the code-computed comparison record, and flags any numeral not present in it.
