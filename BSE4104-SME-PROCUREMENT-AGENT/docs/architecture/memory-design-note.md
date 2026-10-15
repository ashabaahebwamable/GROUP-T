# Memory Design and Data Handling Note

**Project:** BSE4104 SME Procurement Preparation Agent (ReqPrep)
**Week:** 6 — State and Memory (W6-03)
**Owners:** Ashaba Ahebwa Mable (sections 1–7) · Akisa Maria Ashley (section 8, security review)
**Status:** Sections 1–7 written and checked against the code on 13 Oct 2026. Section 8 security review carried out on 13 Oct as a stand-in while Ashley was unreachable; awaiting her confirmation.
**Sources:** `user-stories.md` US-12, `ai-boundary-matrix.md` row 19, `model-selection-note.md` §5, `state-model.md`, `src/memory/supplier_preferences.py`.

---

## 1. The memory use case

ReqPrep keeps one kind of durable memory: **a supplier preference for an item, confirmed by a person.** When an officer has confirmed a supplier for an item, that choice can be shown again the next time the same item is reordered, so the officer does not have to remember it.

It is a **hint, not an input**. The quotation comparison never reads it, so it cannot change the eligibility, the landed cost or the ranking (AI Boundary Matrix row 19: "using an unconfirmed preference to influence a recommendation" is prohibited, and here even a confirmed one does not influence it). The officer sees it next to the computed recommendation and decides.

Everything else the system saves is **case state or evidence**, not memory: it records what happened in a case, and is covered in section 6.

## 2. What is stored

One SQLite table, `supplier_preferences`, in `data/application_state.sqlite3` (git-ignored; the same file as the case store).

| Field | Example | Why it is needed |
|---|---|---|
| `preference_id` | 1 | Row key; the latest row per item wins |
| `item_id` | INV-001 | The item the preference applies to |
| `supplier_id` | SUP-01 | The supplier the officer confirmed |
| `confirmed_by` | OFFICER-1 | Who confirmed it (US-12 AC3; matrix row 19, LOG) |
| `confirmed_at` | 2026-10-12T10:00:00+00:00 | When, in UTC; also drives retention |

Nothing else is stored: no prices, no quotation text, no supplier contact details, no free text typed by the officer, and nothing the model produced.

**Personal data.** `confirmed_by` is a staff account ID, which identifies a person. It is the only personal data in the table, and it is required by US-12 AC3. In this project every account is synthetic (`data/users.csv`), so no real person's data is held.

## 3. How a preference is written

`record_supplier_preference(item_id, supplier_id, confirmed=True, confirmer_id=...)` is the only write path.

- It refuses unless `confirmed` is exactly `True` and the confirmer ID is non-empty; a refused call writes nothing (`PreferenceConfirmationRequiredError`).
- The confirmer must be a registered officer or approver in `data/users.csv`; anyone else is refused (`PreferenceAccessDeniedError`). Added after the section 8 review.
- It is **not a model tool**: it is not in `TOOL_REGISTRY`, so the model cannot write memory. The model may at most suggest that a preference is worth remembering (matrix row 19).
- The officer confirmation at hand-off H1 now calls `record_supplier_preference(...)` immediately after the confirmed supplier is accepted, so the durable preference is written only after explicit human confirmation and not as a model action.

## 4. Who can read it

| Reader | How | Rule |
|---|---|---|
| The officer working a case | The router adds the latest unexpired preference to the comparison result as `supplier_preference_hint`; the hand-off message shows it with who confirmed it and when | Shown only for the same item |
| An officer or approver looking at all preferences | `list_supplier_preferences(reader_id=...)` | Role checked against `data/users.csv`; anyone else gets `PreferenceAccessDeniedError` |
| The Gemini model (model-driven loop only) | The comparison result sent back to the model | **Supplier only.** `model_safe_hint` removes `confirmed_by` and `confirmed_at` before anything is sent, so no personal data reaches the free-tier API (`model-selection-note.md` §5) |
| The rule-based loop (`run_agent`) | Case state | Never sent anywhere |

**Limit of these controls.** The role checks apply to the application's functions. Anyone with direct access to the SQLite file on the machine can read it; protecting the file itself (operating-system permissions, disk encryption) is outside this prototype and is listed as a Week 8 hardening item.

## 5. Retention and deletion

| Rule | Implementation |
|---|---|
| **Retention: 12 months** from `confirmed_at` | `RETENTION_DAYS = 365`. An older preference is never shown or listed |
| Expired rows are removed | `purge_expired_preferences()` deletes them and logs one `PREFERENCES_PURGED` event (actor `system`, row count). It is meant to run on a schedule or at application start; **it is not yet called automatically** |
| A newer confirmation supersedes an older one | Only the latest row per item is shown; older rows remain until they expire or are deleted |
| Deletion on request (supplier relationship ended, wrong entry) | `delete_supplier_preferences(item_id, deleted_by=..., reason=...)`: **approver only**, removes every row for the item, and writes `PREFERENCE_DELETED` with who, why and how many rows |
| Refused deletion | An officer or unknown user gets `PreferenceAccessDeniedError`, and the attempt is logged as `PREFERENCE_DELETE_REFUSED` |

Why 12 months: long enough to help with items reordered a few times a year, short enough that a supplier choice made under old prices or terms does not keep reappearing. Quotations themselves expire in 7–30 days, so the preference only ever points to a supplier, never to a price.

The audit log is append-only and is not deleted with the preference: the record that a preference existed and was removed is the evidence that the rules were followed (matrix row 20).

## 6. Other data the system keeps

These are not memory, but they are stored and the same questions apply.

| Data | Where | Contents | Personal data | Retention today |
|---|---|---|---|---|
| Workflow cases | `data/application_state.sqlite3` (`workflow_cases`, `workflow_case_events`) | Item, quotations, comparison, flags, state, decisions | Decision-maker and actor IDs | Kept; no rule yet |
| Requisitions | `data/requisitions.csv` | Draft and decided requisitions | `created_by`, `decided_by` | Kept (procurement record) |
| Audit log | `evidence/traces/audit-log.jsonl` | Every state change, stop, refusal and preference deletion | Actor IDs | Kept; append-only by design |
| Tool-call trace | `evidence/traces/tool-calls.jsonl` | Each tool call and stop, **including the prompt text** | Whatever an officer types in a prompt | Kept |
| Retrieval trace | `evidence/traces/retrieval.jsonl` | Policy questions and retrieved chunks | Whatever is typed in a question | Kept |
| Officer accounts | `data/users.csv` | User ID, display name, role | Synthetic accounts only | Kept |

Two points follow:

- The trace files store prompt text verbatim. With synthetic scenarios that is harmless, and it is the evidence the course requires. A real deployment would need a rule for them (shorter retention, or not storing free text), and they should not be committed to a repository.
- No retention rule exists yet for cases, requisitions or the audit log. For a procurement system these are usually kept for a fixed audit period; choosing it is a decision for the team and is listed in section 7.

## 7. Open items

1. **Schedule the purge:** call `purge_expired_preferences()` at application start or on a timer.
2. **Retention for case and evidence data** (section 6): team decision.
3. **File-level protection** of `data/application_state.sqlite3`: Week 8 hardening.

## 8. Security review (Akisa Maria Ashley)

**Performed on 13 Oct 2026 by Ashaba Ahebwa Mable, with AI assistance (AI Engineering Log, entry 9), because Ashley could not be reached.** This is a stand-in review, not Ashley's: she owns this section and should repeat or confirm the checks below and sign at the end.

| Check | What was done | Result |
|---|---|---|
| **No personal data beyond what US-12 requires** | Read the `supplier_preferences` schema and every place a preference is written or read; confirmed by test that the confirming officer's ID and time are removed before the comparison result is sent to Gemini (`test_preference_hint_reaches_the_model_without_officer_identity`). The application database does not exist in the repository (`data/*.sqlite3` is git-ignored) | **Pass.** Only the confirmer's account ID is personal data, and US-12 AC3 requires it. **Low finding:** two synthetic account IDs are based on real team members' names (`ESAU-JOHN` in `data/users.csv` and `data/requisitions.csv`; `officer-ashley` in `data/users.csv` and the Week 5 traces). No other details of them are stored. Recommendation: use generic IDs (`OFFICER-2`, `OFFICER-3`) when the Week 7 evaluation data is prepared; not changed now because the Week 4 and Week 5 evidence refer to them |
| **No secrets in stored data or evidence** | Scanned every tracked file and the full git history for Google API key patterns and for the project's actual key; checked that no `.env` file was ever committed; scanned tracked files for other key, token and password patterns; looked at the three Week 5 screenshots | **Pass.** No key, token or password in any tracked file or past commit; `.env` is git-ignored and was never committed; the logs committed on 12 Oct contain no key. Screenshots show no secret values (browser tab titles mention an SSH-keys settings page and a GitLab host name, but no key is visible) |
| **Preference access limited to officer and approver roles** | Traced every function that writes, reads, lists or deletes a preference and checked its role rule against `data/users.csv` | **Pass after one fix.** Listing (officer/approver) and deletion (approver) were role-checked, but **any non-empty ID, even an unregistered one, could be recorded as the confirmer**. Fixed: `record_supplier_preference` now requires a registered officer or approver (`test_unregistered_confirmer_cannot_write_a_preference`). Accepted: the hint shown inside a case has no separate reader check, because it is shown only to the officer working that case; direct access to the database file is outside the application (section 4) |

Stand-in reviewer: Ashaba Ahebwa Mable, 13 Oct 2026

Confirmation by Akisa Maria Ashley, 13 Oct 2026, with AI assistance (AI Engineering Log, entry 10).

## 9. Tests

`tests/memory/test_supplier_preferences.py` (12 tests) and `tests/test_agent_integration.py`:

| Rule | Test |
|---|---|
| No write without confirmation | `test_preference_cannot_be_written_without_confirmation`, `test_empty_confirmer_is_rejected_without_persisting` |
| Identity and timestamp recorded | `test_confirmed_preference_is_durable_and_has_identity_and_timestamp` |
| Shown only for the same item; latest wins | `test_preference_is_retrieved_only_for_matching_item`, `test_latest_confirmation_is_returned` |
| Not shown after 12 months | `test_preference_is_not_shown_after_the_retention_period` |
| Purge removes only expired rows, logged | `test_purge_removes_only_expired_rows_and_is_logged` |
| Approver deletes, logged; officer refused, logged | `test_approver_can_delete_and_the_deletion_is_logged`, `test_officer_cannot_delete_and_the_attempt_is_logged` |
| Only officers and approvers can list | `test_only_officers_and_approvers_can_list_preferences` |
| Only a registered officer or approver can be the confirmer | `test_unregistered_confirmer_cannot_write_a_preference` |
| No officer identity sent to the model | `test_hint_sent_to_the_model_has_no_officer_identity_or_time`, `test_preference_hint_reaches_the_model_without_officer_identity` |

Not yet tested: that the computed ranking is identical with and without a stored preference (W6-05).
