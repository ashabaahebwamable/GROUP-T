# Week 6 Progress Report — State, Memory and Interoperability

## Objective

Week 6 gave the agent a **durable state** and one **justified memory**. A workflow case now survives an application restart with its evidence intact, and an officer's confirmed choice of supplier can be shown again the next time the same item is reordered. The memory is deliberately weak: it is written only after a person confirms, it is a hint that never changes the computed ranking, it expires, and the model never sees who confirmed it. The week also specified one tool as an MCP-style interface, so its contract can be understood outside this codebase.

## What was built

**State model and persistence (W6-01).** `src/workflow/case_store.py` stores each workflow case in SQLite (`data/application_state.sqlite3`, git-ignored) with its item, quotations, comparison, flags, state and decisions, and records every transition as an event in the same transaction. `docs/architecture/state-model.md` has the state diagram and transition table:

| From | Action | To | Condition |
|---|---|---|---|
| — | create | `OPEN` | unique case ID |
| `OPEN` | start draft | `DRAFT` | — |
| `DRAFT` | submit | `PENDING_APPROVAL` | no unresolved blocking flags |
| `PENDING_APPROVAL` | approve / reject / query | `APPROVED` / `REJECTED` / `QUERIED` | registered approver who did not submit the case; reject and query need a reason |
| `OPEN`, `DRAFT`, `PENDING_APPROVAL` | halt | `HALTED` | a reason |
| any terminal state | anything | — | refused |

On restart `get_case` rebuilds a case exactly as recorded and `list_resumable_cases` offers only `OPEN`, `DRAFT` and `PENDING_APPROVAL` cases (US-12 AC1–2).

**Supplier-preference memory (W6-02).** `src/memory/supplier_preferences.py` stores one fact per confirmation: item, supplier, the confirming officer's ID and a UTC timestamp.
- **Written only after explicit human confirmation.** When an officer confirms the recommended supplier at hand-off H1 (`confirm_supplier`), the preference is recorded with their identity (US-12 AC3). The writer refuses anything but a literal `confirmed=True` and a registered officer or approver; it is not a model tool.
- **Shown as a hint, never a ranking input.** The router attaches the latest preference for the same item to the comparison result as `supplier_preference_hint`; the comparison function never reads memory. Tests show a remembered supplier cannot be promoted, made eligible if excluded, or used to clear a blocking flag.
- **Model prompt.** The `compare_quotations` tool description tells the model to surface the hint as information, distinguish it from the computed recommendation, and leave the decision to people.

**Memory design and data handling (W6-03).** `docs/architecture/memory-design-note.md` sets out what is stored and why, who can read it, retention and deletion, what reaches the model, and every other kind of data the system keeps. The rules are implemented, not just described:

| Rule | Implementation |
|---|---|
| Retention 12 months | Older preferences are never shown; `purge_expired_preferences()` deletes them and logs it |
| Deletion | `delete_supplier_preferences()`: approver only; every deletion and refused attempt goes to the audit log |
| Read access | `list_supplier_preferences()`: officer and approver roles only |
| Data sent to the model | The supplier only; the officer's ID and time are removed before anything reaches Gemini |

The security review (section 8) checked for personal data, secrets and access control. A stand-in review on 13 Oct found and fixed one gap (an unregistered ID could be recorded as confirmer); Ashley then repeated all three checks independently, including scanning every commit for keys and 20 deliberate bad-input attempts, and added three findings (below).

**MCP-style interface (W6-04).** `docs/architecture/mcp-interface-spec.md` specifies `compare_quotations` as an MCP-style tool: capability, input and output contracts, preference handling, permissions and side effects, validation and errors, and the security boundary. It states plainly that no MCP server has been deployed; the optional external integration was not attempted.

## Testing (W6-05)

The suite (`python -m pytest`) runs **187 tests and 166 subtests, and all pass** (19 Oct 2026). A shared fixture keeps every test off the real database and evidence logs.

| Card requirement | Tests |
|---|---|
| No preference write without confirmation | `tests/memory/test_memory_controls.py` `NoWriteWithoutConfirmationTests`, `ConfirmationWritePathTests`; `tests/memory/test_supplier_preferences.py` |
| Restored values identical to those recorded before restart | `tests/workflow/test_state_transitions_and_restart.py` `RestartTests`: every field of every case after a real restart, awkward values unchanged, restoring is read-only, the event history is unbroken |
| Every legal and illegal state transition | `TransitionMatrixTests`: every state against every action, terminal states, no action can jump to a state; plus condition tests for reasons, approver role and separation of duties |
| Memory never changes the ranking | `MemoryNeverChangesTheRankingTests`; `tests/test_preference_does_not_change_ranking.py` |
| Retention, deletion and access rules | `DataHandlingTests` in `test_supplier_preferences.py` |

## Demonstration (W6-06)

`evidence/demo/week6/w6-06-restart-resume-and-preference-flow.mp4`, recorded with `scripts/demo_week6.py`, shows the INV-003 case stopping at H1, the officer confirming SUP-03, the case resuming from its saved state to a draft at H2, and the stored preference being read back as a hint.

Two limits of the demonstration, stated so the recording is not over-read:
- Both runs happen in one program. The agent's own case state is passed between runs in memory; it is not yet saved to the W6-01 case store, so an agent run cannot be resumed after the application is closed. Restart of the case store itself is proven by the `RestartTests` above.
- The script writes the preference with a direct call rather than through `confirm_supplier`, which now does it automatically; the effect is the same.

Running the script also added a demonstration draft, `REQ-2026-0004`, to `data/requisitions.csv`.

## Findings carried forward

| # | Finding | Source | Proposed action |
|---|---|---|---|
| 1 | Identity is asserted, not authenticated: there is no login, so anyone who supplies an approver's ID is treated as one | Memory note §8 (Ashley) | Week 8 hardening; state it in memory note §4 |
| 2 | Logged free text has no size limit (a 200,000-character reason added 200 KB to the audit log) | Memory note §8 (Ashley) | Cap actor ID and reason length |
| 3 | The purge of expired preferences is not scheduled | Memory note §7 | Call it at application start |
| 4 | No retention rule for cases, requisitions or the audit log | Memory note §6–7 | Team decision |
| 5 | The agent loop does not save its state to the case store | W6-06 demonstration | Connect `run_agent` stops to `case_store` so a run survives a restart |
| 6 | Two synthetic account IDs are based on team members' names | Memory note §8 | Use generic IDs in the Week 7 data |

## Still open

- **Owner confirmations from Week 5.** Ashley's row in `docs/reviews/week5-change-review.md` is still blank. Isaac's two rows were recorded on 15 Oct in a commit by Ashley; Isaac should confirm them himself.
- **Demonstration draft.** Decide whether `REQ-2026-0004` stays in `data/requisitions.csv` or is removed, as the Week 4 demonstration rows were.

## Individual contributions (from repository history)

| Member | Week 6 contribution |
|---|---|
| Tendo Caisey (AI Engineering Lead) | MCP-style interface specification and its wording correction (W6-04); model prompt for the preference hint (W6-02); ranking test proving a preference never changes the recommendation (W6-02); test isolation for the preferences database; Week 5 sign-off of contract sections 3, 4 and 8, the iteration limit, and the updated W5-02 diagram |
| Azibo Isaac Alinda | Owner of W6-01 and W6-02; review of the bounded loop and state-machine changes recorded on 15 Oct |
| Akisa Maria Ashley (Quality/Security Lead) | SQLite case store, state model and supplier-preference memory (W6-01, W6-02); connected the preference write to the officer's confirmation; memory and state tests, including every transition and a real restart (W6-05); independent security review of the memory note (W6-03 §8) |
| Wakinya Esau John (DevOps/Documentation Lead) | Restart-and-resume and preference demonstration with `scripts/demo_week6.py` (W6-06); Week 6 screenshots (W6-07); Week 5 demo video |
| Ashaba Ahebwa Mable (Project/Requirements Lead) | Memory design and data handling note and the retention, deletion, access and model-data code it describes (W6-03); stand-in security review; merged and aligned Tendo's W6-04 work; kept the demo and trace generator off the real database; Week 3 recheck after the quotation additions; this report |

## Next steps (Week 7)

- Connect agent-run stops to the case store, so a case can be resumed after the application restarts (finding 5).
- Prepare the Week 7 evaluation set: the seven items that now reach a draft, the S4 cases (INV-003 lapsed quotation, INV-006 too few quotations), the two policy 3.4 tie-breaks, and generic account IDs.
- Schedule the preference purge and cap logged text length (findings 2 and 3).
- Close the Week 5 owner confirmations.

## Conclusion

Week 6 delivered persistence that survives a restart exactly, and a memory that is useful without being trusted: confirmed by a person, shown as a hint, never used in ranking, kept for twelve months, deletable only by an approver, and never sent to the model with anyone's identity. Every legal and illegal state transition is tested, as are the memory controls, and all 187 tests pass. The `compare_quotations` contract is now documented as an MCP-style interface. What remains for Week 7 is connecting agent runs to the case store and preparing the evaluation set.
