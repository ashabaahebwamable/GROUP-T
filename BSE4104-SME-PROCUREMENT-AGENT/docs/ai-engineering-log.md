# AI Engineering Log

> Required by BSE4104 §6: *AI-generated work is permitted and expected. Unexplained work is not.*
> This log records material AI-assisted decisions and generated artefacts.
> **Do not backfill it.** An entry written days later, from memory, is worth little and is usually detectable.

## How to use this log

Add an entry when AI assistance materially shaped a decision or produced an artefact that entered the repository. Routine autocomplete does not need an entry; a generated document, a design decision taken on AI advice, or generated code accepted into a branch does.

Each entry must record how the output was **reviewed**, what was **changed**, and why it was **accepted or rejected**. The review columns are the point of the log — they are what distinguishes owned work from pasted work.

## Log

| # | Date | AI tool / model | Purpose | Prompt or task (summary) | Output produced | How we reviewed it | Changes we made | Accepted / rejected and why | Evidence link | Team member |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | | | | | | | | | | |
| 2 | | | | | | | | | | |
| 3 | | | | | | | | | | |
| 4 | | | | | | | | | | |
| 5 | | | | | | | | | | |

## Declared tools

| Tool / model | Version or access | Used for | Notes |
|---|---|---|---|
| [INSERT] | [INSERT] | [INSERT] | |

---

## EXAMPLES — illustrative only

**The three rows below are EXAMPLES showing the expected level of detail. They are NOT records of work done by this team. Delete this whole section before submission.**

| # | Date | AI tool / model | Purpose | Prompt or task (summary) | Output produced | How we reviewed it | Changes we made | Accepted / rejected and why | Evidence link | Team member |
|---|---|---|---|---|---|---|---|---|---|---|
| E1 | *[example date]* | *[example assistant]* | Draft the AI Boundary Matrix structure | Asked for a matrix covering reasoning, retrieval, validation, authorisation, tool use, purchasing, payment, approval and failure handling | A 20-row matrix with an enforcement-mechanism column | Two members read every row against the brief's safety boundary for this use case and checked each row against a user story | Added the enforcement-strength scale; rewrote the purchasing and payment rows to state the capability is absent rather than restricted | Accepted with changes — the structure was sound but the original wording implied disabled features rather than absent ones, which understated the control | *[commit link]* | *[example member]* |
| E2 | *[example date]* | *[example assistant]* | Generate synthetic quotation letters | Asked for four letters with deliberately inconsistent unit, VAT and delivery conventions | Four markdown letters | Recomputed every landed cost by hand and confirmed the intended mis-ranking actually occurs; checked no real business name was used | Corrected one rate that made two quotations tie, which would have removed the trap; added the synthetic-document header to each file | Accepted with changes | *[commit link]* | *[example member]* |
| E3 | *[example date]* | *[example assistant]* | Suggest an approach to multi-line requisitions | Asked whether to support several line items per requisition | A design allowing per-line supplier selection | Checked against the brief's safety boundary and our own scope section | None — the approach was not adopted | **Rejected.** Per-line supplier selection amounts to split award, which is outside the safety boundary, and it would multiply the evaluation scenario count beyond eight weeks | *[decision recorded in charter §9]* | *[example member]* |

A rejection entry like E3 is worth more than three acceptances. It demonstrates that the team evaluated AI output rather than absorbing it.
