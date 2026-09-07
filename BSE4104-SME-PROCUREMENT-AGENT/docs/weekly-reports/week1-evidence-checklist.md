# Week 1 Evidence Checklist

> Week 1 deliverable support, BSE4104. Primary evidence is GitHub + ClickUp + MUELE.
> The purpose of evidence is to show that work was *done*, not merely that a document exists.

## Rule that applies to every screenshot

**Never visible:** API keys, tokens, passwords, `.env` contents, personal telephone numbers, home addresses, any real client or supplier data, private messages.
**Always visible:** the browser URL or repository path, a timestamp or commit reference where the platform shows one, and the name of the member whose work it is.

---

## 1. Project Charter

| | |
|---|---|
| Proves completion | Committed file with a commit history showing more than one revision, plus a review comment from a second member |
| Stored at | `docs/requirements/project-charter.md` |
| ClickUp | T1.3 marked Complete, commit URL in the `GitHub path` field |
| Screenshot | The GitHub commit history for the file, showing at least two commits by at least two members |
| Visible | File path, commit messages, author names, dates |
| Not visible | Nothing sensitive; charter content is safe to show |
| Weak evidence to avoid | A screenshot of the document itself. It proves a file exists, not that the team produced it |

## 2. User stories

| | |
|---|---|
| Proves completion | Committed file, and the story IDs reproduced as a ClickUp checklist so stories become trackable work |
| Stored at | `docs/requirements/user-stories.md` |
| ClickUp | T1.4 Complete with a twelve-item checklist (US-01 … US-12) |
| Screenshot | The ClickUp checklist alongside the committed file |
| Visible | Story IDs, owner, due date |

## 3. Acceptance criteria

| | |
|---|---|
| Proves completion | Criteria present in the same file, in Given/When/Then form, with a named test method per story |
| Stored at | `docs/requirements/user-stories.md` (same file — criteria belong with their story) |
| ClickUp | Covered by T1.4 |
| Screenshot | One story shown in full, criteria included, as a representative sample |
| Note | Do not split criteria into a separate document; separation is how stories and criteria drift apart |

## 4. AI Boundary Matrix

| | |
|---|---|
| Proves completion | Committed file covering every activity category the brief names, with an enforcement mechanism per row |
| Stored at | `docs/requirements/ai-boundary-matrix.md` |
| ClickUp | T1.5 Complete |
| Screenshot | The rendered table on GitHub, showing the prohibited-actions section |
| Strong addition | A short note in the task recording one boundary the team argued about and how it was resolved. Disagreement recorded is evidence of engineering judgement |

## 5. Architecture / context diagram

| | |
|---|---|
| Proves completion | Both the markdown source and a rendered image |
| Stored at | `docs/architecture/week1-context-diagram.md`, image at `docs/architecture/week1-context-diagram.png` |
| ClickUp | T1.6 Complete |
| Screenshot | The rendered diagram, and the GitHub-rendered Mermaid block |
| Visible | Component type labels (AI / deterministic / data / human) |

## 6. GitHub repository

| | |
|---|---|
| Proves completion | Repository with the brief's folder structure, a first commit, and commits from every member |
| Stored at | The repository itself |
| ClickUp | T1.8 Complete |
| Screenshots | (a) repository root showing all folders; (b) the Insights → Contributors page showing commits per member; (c) the `.gitignore` showing `.env` excluded |
| Visible | Repository name, folder list, contributor names and commit counts |
| Not visible | Any file containing a real key. Confirm `.env` is absent from the repository before screenshotting |
| Why contributors matters | Individual accountability is assessed. One member committing everything is a marked weakness even if the work was shared |

## 7. ClickUp board

| | |
|---|---|
| Proves completion | Board with all Week 1 tasks, each with an owner, a due date and a current status |
| ClickUp | The board itself |
| Screenshots | (a) list view showing owners, dates and statuses; (b) one task opened, showing description, acceptance criteria and the GitHub link; (c) the members list |
| Visible | Task names, assignee names, dates |
| Weak evidence to avoid | A board where every task is Complete with the same timestamp |

## 8. Synthetic data design

| | |
|---|---|
| Proves completion | Schema document plus the actual corpus files, plus the source register |
| Stored at | `docs/requirements/synthetic-data-design.md`, `knowledge/**`, `knowledge/SOURCE-REGISTER.md` |
| ClickUp | T1.7 Complete |
| Screenshot | The reference mis-ranking table from the design document, and the `knowledge/` tree on GitHub |
| Visible | The synthetic declaration |
| Not visible | Any real supplier name or price. If a synthetic name resembles a real business, note in the register that the resemblance is coincidental |

## 9. Week 1 progress report

| | |
|---|---|
| Proves completion | Committed file with all eight sections, plus the MUELE submission |
| Stored at | `docs/weekly-reports/week1-progress-report.md` |
| ClickUp | T1.11 Complete |
| Screenshots | The committed file, and the MUELE submission confirmation |
| Visible | Week ending date, group identifier, named contributions |
| Not visible | Student numbers if your group prefers to omit them **[OPTIONAL]** |
| Requirement | No unfilled placeholder may remain at submission |

## 10. Individual contribution evidence

The most commonly neglected item, and the one that carries individual marks.

| | |
|---|---|
| Proves completion | Three independent traces per member: commits authored, ClickUp tasks owned and completed, and a named contribution section in the progress report |
| Stored at | GitHub history, ClickUp board, progress report §7 |
| Screenshots | Contributors page; ClickUp filtered by assignee, one screenshot per member |
| Visible | Member name, task list, commit count |
| Strong addition | Each member adds one paragraph to the progress report explaining a decision *they* made and why — the brief requires every student to be able to explain their submitted work |
| Warning | Do not reconstruct commit history retroactively to balance contributions. It is visible in timestamps and it is academically dishonest |
