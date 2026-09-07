# User Stories and Acceptance Criteria

> Week 1 deliverable, BSE4104. Twelve stories covering the single primary workflow
> defined in `project-charter.md` §7. Parts 3 and 4 of the Week 1 request are combined
> here so that each story sits next to its own criteria.

## How to read this document

- **User story** — one sentence in the form *As a [role], I want [capability], so that [benefit]*. The role is always one of the two charter roles: stores officer or approver.
- **Acceptance criteria** — binary checks in Given / When / Then form. Each is observable by someone other than the author.
- **Performed by** — whether the capability is AI, deterministic software, or split. This column carries the brief's learning outcome on where AI adds value and where deterministic software stays in control.
- **Priority** — Must (the demonstration fails without it), Should (matters, survives a slip), Could (first to be dropped).
- **Test method** — the mechanism that will verify it, linking Week 1 to the Week 8 evaluation set.

---

## US-01 — Reorder visibility

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want to see which stock items have fallen below their reorder level, so that I begin replenishment before a shortage becomes an emergency. |
| Performed by | Deterministic software entirely; no model involvement |
| Priority | Must |
| Test method | Automated unit tests over a fixture inventory, including the boundary case where stock equals the reorder level |
| Workflow stage | 1 |

**Acceptance criteria**

1. **Given** an inventory register, **when** the reorder check runs, **then** every item whose current stock is below its reorder level is listed, and no item at or above its reorder level appears.
2. **Given** a flagged item, **when** it is listed, **then** a suggested reorder quantity computed in code is displayed alongside it.
3. **Given** an item with no reorder level recorded, **when** the check runs, **then** the item is reported as unassessable rather than omitted silently.

## US-02 — Opening a case

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want to open a requisition case by stating what I need in my own words, so that I do not have to look up stock codes before starting. |
| Performed by | AI interprets the free text; deterministic software validates item code, quantity and case creation |
| Priority | Must |
| Test method | Automated tests for validation rules; evaluation scenarios for the ambiguity path |
| Workflow stage | 2 |

**Acceptance criteria**

1. **Given** the input "need to reorder cement, about 200 bags", **when** the case is opened, **then** a candidate item, quantity and unit are proposed for the officer's confirmation.
2. **Given** an item description matching more than one inventory record, **when** the case is opened, **then** the system asks which item is meant and selects none itself.
3. **Given** a quantity that is zero, negative or non-numeric, **when** it is submitted, **then** the case is rejected with the reason stated, before any model call is made.
4. **Given** an item description matching no inventory record, **when** the case is opened, **then** the system reports that the item is unknown and does not create a case.

## US-03 — Reading quotations

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want the commercial terms read out of each quotation automatically, so that I do not retype supplier figures by hand. |
| Performed by | AI extracts; deterministic software validates the schema and stores the record |
| Priority | Must |
| Test method | Field-level accuracy measured across the corpus quotation letters; automated schema-rejection tests |
| Workflow stage | 3 |

**Acceptance criteria**

1. **Given** a quotation letter in text form, **when** it is processed, **then** supplier, item, quantity, unit, unit price, tax treatment, delivery terms and validity date are extracted into the canonical quotation record.
2. **Given** a quotation that omits its unit of measure, **when** it is processed, **then** the missing field is reported and the officer is asked to supply it, with no default assumed.
3. **Given** an extracted record, **when** it is stored, **then** it passes schema validation, and any record failing validation is rejected with the failing field named.

## US-04 — Comparable pricing

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want all quotations expressed on one comparable cost basis, so that I do not choose a supplier that only appears to be cheapest. |
| Performed by | Deterministic software entirely (charter Principle 1) |
| Priority | Must |
| Test method | Automated unit tests per conversion rule, plus the reference mis-ranking case in the evaluation set |
| Workflow stage | 4 |

**Acceptance criteria**

1. **Given** quotations stated in different units of measure, **when** they are compared, **then** all are converted to landed cost per base unit and the ranking reflects the converted values.
2. **Given** one tax-inclusive and one tax-exclusive quotation, **when** they are compared, **then** tax is applied uniformly and no pre-tax figure is used in the ranking.
3. **Given** a quotation with delivery priced separately, **when** it is compared, **then** the delivery charge is included in landed cost.
4. **Given** the comparison output, **when** it is inspected, **then** every figure shown was computed in code, and any model-stated figure differing from the computed value is recorded as a logged discrepancy.

## US-05 — Justified recommendation

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want a recommended supplier with the reasoning written out, so that I can defend the choice to my approver. |
| Performed by | Deterministic ranking; AI writes the explanatory narrative |
| Priority | Must |
| Test method | Automated check that the recommended supplier equals rank one; manual review of the narrative against the comparison table for each scenario |
| Workflow stage | 5 |

**Acceptance criteria**

1. **Given** a ranked comparison, **when** the recommendation is produced, **then** the recommended supplier is the top-ranked quotation as ordered in code, and not a separate model selection.
2. **Given** a recommendation, **when** it is displayed, **then** the stated reasons refer only to figures present in the comparison table.
3. **Given** a recommendation, **when** it is displayed, **then** it is marked as requiring officer confirmation and is never presented as a decision taken.

## US-06 — Policy flags

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want applicable procurement rules checked automatically, so that a requisition does not reach my approver with a rule already broken. |
| Performed by | Deterministic software entirely — rules as code, not prompt instructions |
| Priority | Must |
| Test method | One automated test per rule, each with a passing and a failing fixture |
| Workflow stage | 4 |

**Acceptance criteria**

1. **Given** fewer valid quotations than the policy minimum, **when** the case is assembled, **then** a flag is raised naming the rule.
2. **Given** a quotation from an excluded supplier, **when** it is processed, **then** it is flagged and excluded from the recommendation.
3. **Given** a quotation past its validity date, **when** it is compared, **then** it is flagged and excluded from the ranking.
4. **Given** a case value above the approval threshold, **when** it is assembled, **then** the applicable approval level is stated.

## US-07 — Draft and submit

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want the requisition drafted from the case evidence and submitted for approval, so that I do not prepare the document from scratch. |
| Performed by | AI drafts the narrative; deterministic software creates the record, enforces the state transition and writes the audit log |
| Priority | Must |
| Test method | Automated state-machine tests, including an attempted illegal transition |
| Workflow stage | 5, 6 |

**Acceptance criteria**

1. **Given** a confirmed supplier, **when** the draft is created, **then** it is created in state DRAFT with a system-assigned requisition number.
2. **Given** a draft, **when** the officer submits it, **then** it moves to PENDING_APPROVAL and the transition is written to the audit log with the officer's identity and a timestamp.
3. **Given** a draft with an unresolved blocking flag, **when** the officer submits it, **then** submission is refused and the blocking flag is stated.

## US-08 — Approving with evidence

| Field | Value |
|---|---|
| Role | Approver |
| Story | As an approver, I want to see the full comparison and any flags next to the recommendation, so that I am approving on evidence rather than rubber-stamping. |
| Performed by | Deterministic software; AI contributes only a case summary |
| Priority | Must |
| Test method | Manual demonstration with screenshot; automated test confirming no path exists from PENDING_APPROVAL to APPROVED without a recorded human decision |
| Workflow stage | 7 |

**Acceptance criteria**

1. **Given** a submitted requisition, **when** the approver opens it, **then** the ranked comparison, the policy flags and the citations are displayed together with the recommendation.
2. **Given** a submitted requisition, **when** the approver decides, **then** approve, reject and query are all available, and the outcome is written to the audit log with identity and timestamp.
3. **Given** a requisition of any value, **when** it is submitted, **then** it remains in PENDING_APPROVAL until a human decision is recorded.

## US-09 — Authorisation

| Field | Value |
|---|---|
| Role | Stores officer / approver |
| Story | As an approver, I want approval restricted to approver accounts, so that a requisition cannot be approved by the person who prepared it. |
| Performed by | Deterministic software entirely |
| Priority | Must |
| Test method | Authorisation tests using a non-approver account; code review recorded in the Week 8 hardening evidence |
| Workflow stage | 7 |

**Acceptance criteria**

1. **Given** an officer account, **when** an approval is attempted, **then** it is refused and the attempt is logged.
2. **Given** a direct request to move a requisition from DRAFT to APPROVED, **when** it is submitted, **then** it is refused as an illegal state transition.
3. **Given** the codebase, **when** it is reviewed, **then** no automatic approval path exists at any value.

## US-10 — Honest refusal

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want to be told when the policy documents do not cover my question, so that I do not act on an invented answer. |
| Performed by | Deterministic retrieval and scoping; AI decides use and refusal |
| Priority | Must |
| Test method | The 15-case retrieval evaluation set: answerable, partially answerable and deliberately unanswerable |
| Workflow stage | 3 |

**Acceptance criteria**

1. **Given** a question answerable from the corpus, **when** it is asked, **then** the answer cites the documents relied upon.
2. **Given** a question the corpus does not address, **when** it is asked, **then** the system states that it cannot answer from available documents and cites nothing.
3. **Given** a partially answerable question, **when** it is asked, **then** the covered part is answered with citations and the uncovered part is explicitly identified as uncovered.

## US-11 — Safe stop

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want the system to stop and hand the case back to me when it cannot proceed, so that it does not loop or guess. |
| Performed by | Deterministic enforcement of limits and the allow-list; AI recognises the outstanding need at hand-off |
| Priority | Must |
| Test method | Execution traces including one induced failure and recovery (Week 5 deliverable) |
| Workflow stage | 3-5 |

**Acceptance criteria**

1. **Given** the iteration limit is reached, **when** the agent is running, **then** it halts, states what remains outstanding, and preserves the case state.
2. **Given** a tool that fails repeatedly, **when** it is called, **then** the agent retries once and then hands off rather than continuing.
3. **Given** a proposed action outside the approved tool list, **when** the agent proposes it, **then** the call is blocked before execution and logged.

## US-12 — Resuming a case

| Field | Value |
|---|---|
| Role | Stores officer |
| Story | As a stores officer, I want to reopen an unfinished case and continue where I stopped, so that an interrupted requisition is not started again. |
| Performed by | Deterministic persistence and state reconstruction; criterion 3 enforces charter Principle 2 on memory |
| Priority | Should |
| Test method | Restart-and-resume demonstration; automated test confirming no preference write occurs without confirmation |
| Workflow stage | 8 |

**Acceptance criteria**

1. **Given** an open case, **when** the officer returns after the application restarts, **then** the item, quotations, comparison and flags are restored from persistence.
2. **Given** a restored case, **when** it is displayed, **then** the restored values are identical to those recorded before the interruption.
3. **Given** a durable supplier preference, **when** it is written, **then** it is written only after explicit human confirmation and is recorded with the identity of whoever confirmed it.

---

## Review against BSE4104 requirements

| Check | Status |
|---|---|
| 8-12 testable stories | 12 |
| Criteria testable, no unmeasurable adjectives | Every criterion binary and observable |
| Traces to the single primary workflow | Workflow stage recorded per story; US-01 to US-09 cover stages 1-7, US-10 to US-12 cover boundary behaviour within the same workflow |
| AI and deterministic responsibilities distinguished | Stated per story; five wholly deterministic, none wholly AI |
| Both charter roles represented | Officer in nine, approver in two, one shared |
| Safety boundaries covered | Authorisation US-09, refusal US-10, stop conditions and allow-list US-11, memory confirmation US-12 |
| No features outside approved scope | Every story maps to one of the four approved tools and the two human gates |
| Feasible within 8 weeks | US-01 to US-04 Weeks 2-4; US-05 to US-09 Weeks 4-5; US-10 Week 3; US-11 Week 5; US-12 Week 6 |
| Nothing automatically purchases | No story creates a purchase order, contacts a supplier or moves money |

**Known weakness, declared.** Eleven of twelve stories are priority Must, because nine are the workflow spine and the remainder are safety boundaries required by the brief's minimum evidence table. If a more discriminating priority spread is wanted, the defensible downgrades are US-02 criterion 1 (free-text entry could be replaced by selection from a list) and US-12. **[PLACEHOLDER: group decision required.]**
