# Known Limitations (W8-02)

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep), release v1.0.0
**Status:** Draft 2026-10-25, written from the repository at commit `38a97e2`. A limitation is something the team chose not to build or could not finish. A defect is something that behaves against its requirement and is tracked in `docs/evaluation/failure-catalogue.md` and `docs/evaluation/final-review-checklist.md`. Remove or reword a row if the item is fixed before the tag.

| ID | Limitation | Effect on a user | Why it is left | Related |
|---|---|---|---|---|
| L-01 | One stock item per requisition | An order for several items needs several requisitions | Scope decision in the project definition | `docs/requirements/project-definition.md` |
| L-02 | Text quotations only; there is no OCR | Scanned or photographed quotations cannot be read | Out of scope for the module | US-03 |
| L-03 | Synthetic data only; quotation validity windows lapse | Results depend on an explicit `as_of_date`; the same request can pass or stop at S4 on different dates | No real procurement data available; the date makes runs reproducible | Scenarios T02, X10 |
| L-04 | Identity is asserted, not authenticated: there is no login | Anyone who supplies an approver's ID is treated as that approver | Authentication was outside the scope; role and preparer checks are enforced in code on the identity supplied | `docs/evaluation/guardrails-evidence.md`, G7 |
| L-05 | Prompt-injection resistance is not yet demonstrated at the model | Code controls (no approval tool, allow-list, human confirmation) hold, but A01 to A04 have not been run against the model | Model-backed scenarios share a 20-request daily quota and were not run in time. **Remove or update this row once A01 to A04 have run** | G10, defect D-02 |
| L-06 | Retrieval weaknesses: citations name the document and not the clause (FC-04); the similarity threshold is uncalibrated (FC-05); structured lookups bypass the threshold with a fixed score of 1.0 (FC-06) | Policy answers are harder to verify, and a question naming a record ID can reach the model with weak evidence, so refusal then rests on the prompt | Fixes were proposed in Week 3 and not built | FC-04, FC-05, FC-06 |
| L-07 | The agent loop does not save its own state to the case store, and there is no approver interface | An agent run cannot be resumed after the application closes; approvals are made through code or tests, not a screen | Persistence and a user interface were deferred; the case store and state machine are tested separately | US-12 |
| L-08 | Workflow gaps accepted in the Week 5 review: submit has no role check; a refused approval on the case-store path is not written as a refusal event; the rule-based planner replays a failed call with the same arguments | An approver account can submit a draft; some refusals are missing from the audit log | Judged low risk for the prototype | Week 5 change review, findings 2, 3 and 5 |
| L-09 | `item_id` has no format check | An unknown code is rejected only by lookup (`ITEM_NOT_FOUND`) | The behaviour is safe; a format check adds little | Guardrail G2, defect D-07 |
| L-10 | The model runs on a free tier limited to 20 requests a day | Model-backed evaluation and live demonstrations must be rationed | Cost | `docs/evaluation/week3-retrieval-failures.md` |
| L-11 | Evaluation coverage is 26 of 40 scenarios; the model-backed ones are not run | The report can claim results only for the 26 | See L-05 and L-10. **Remove this row once the run is complete** | `docs/evaluation/final-results.md` |
