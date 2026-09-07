# ClickUp Structure and Week 1 Tasks

> Week 1 deliverable support, BSE4104. The brief requires ClickUp throughout the project,
> with weekly tasks, assigned owners, recorded deadlines, and important tasks linked to
> repository evidence. This document is the plan; the board itself is the evidence.

## Structure

| Level | Name |
|---|---|
| Workspace | `BSE4104 [PLACEHOLDER: group identifier]` |
| Space | `SME Procurement-Preparation Agent` |
| Folder | `Week 01 - Problem Framing and AI-Native Requirements` |
| Lists | `Deliverables`, `Setup`, `Evidence` |

Create one folder per week (`Week 02 …` through `Week 08 …`) so the board mirrors the brief's timeline. Do not create additional spaces; a single space keeps the whole project auditable in one view.

**Statuses:** `To Do` → `In Progress` → `In Review` → `Blocked` → `Complete`

`In Review` matters: the brief requires that AI-generated artefacts be reviewed before acceptance, and a review status is where that review becomes visible.

**Priorities:** Urgent / High / Normal / Low. Reserve Urgent for items that block another member's work.

**Custom fields to add (all four are worth the two minutes):**

| Field | Type | Purpose |
|---|---|---|
| `Deliverable` | text | The artefact this task produces |
| `GitHub path` | text or URL | Where the artefact lives in the repository |
| `Evidence` | text | What proves completion |
| `AI-assisted` | checkbox | Flags tasks needing an AI Engineering Log entry |

## Week 1 tasks

Deadlines assume the Week 1 window of 31 August to 4 September 2026. Owners are placeholders until roles are assigned.

### T1.1 — Project definition
- **Description:** Agree use case, single primary workflow, primary user, and the scope and out-of-scope lists.
- **Owner:** Project / Requirements Lead **[PLACEHOLDER]** · **Priority:** Urgent · **Due:** 1 Sep
- **Deliverable:** `docs/requirements/project-definition.md`
- **Acceptance:** One workflow only; both scope lists present; safety exclusions separated from capacity exclusions.
- **Evidence:** Committed file; ClickUp task marked Complete with the commit linked.

### T1.2 — Manual baseline measurement
- **Description:** Work three requisition cases by hand. Record elapsed time, arithmetic errors, and any policy rule missed.
- **Owner:** **[PLACEHOLDER]** · **Priority:** High · **Due:** 2 Sep
- **Deliverable:** `docs/evaluation/week1-manual-baseline.md`
- **Acceptance:** Three cases recorded with times and observed errors; method stated.
- **Evidence:** Committed file; photograph or scan of the working in `evidence/screenshots/`.
- **Note:** Not named in the brief as a deliverable, but it is what makes success criterion 9 measurable. **[OPTIONAL by the brief, recommended.]**

### T1.3 — Project Charter
- **Description:** Write the 2-3 page charter covering all fifteen required sections.
- **Owner:** Project / Requirements Lead **[PLACEHOLDER]** · **Priority:** Urgent · **Due:** 3 Sep
- **Deliverable:** `docs/requirements/project-charter.md`
- **Acceptance:** 2-3 pages; AI and deterministic responsibilities separated; assumptions and constraints present; success criteria measurable.
- **Evidence:** Committed file; review comment from a second member recorded on the task.

### T1.4 — User stories and acceptance criteria
- **Description:** Produce 8-12 testable stories with Given/When/Then criteria.
- **Owner:** Quality / Security Lead **[PLACEHOLDER]** · **Priority:** Urgent · **Due:** 3 Sep
- **Deliverable:** `docs/requirements/user-stories.md`
- **Acceptance:** 8-12 stories; every criterion binary; each story mapped to a workflow stage and a test method.
- **Evidence:** Committed file; ClickUp checklist of the twelve story IDs.

### T1.5 — AI Boundary Matrix
- **Description:** Complete the matrix across all required activity categories, including the enforcement mechanism per row.
- **Owner:** AI Engineering Lead **[PLACEHOLDER]** · **Priority:** Urgent · **Due:** 3 Sep
- **Deliverable:** `docs/requirements/ai-boundary-matrix.md`
- **Acceptance:** All brief-named categories covered; prohibited actions listed; every row names an enforcement mechanism; prompt-only boundaries declared.
- **Evidence:** Committed file.

### T1.6 — Architecture and context diagram
- **Description:** Produce the initial architecture with component types, plus a rendered image.
- **Owner:** Application / Integration Lead **[PLACEHOLDER]** · **Priority:** High · **Due:** 4 Sep
- **Deliverable:** `docs/architecture/week1-context-diagram.md` and `.png`
- **Acceptance:** Every component labelled AI, deterministic, data or human; model shown without direct tool or data access; human gate present.
- **Evidence:** Committed file and image; screenshot of the rendered diagram.

### T1.7 — Synthetic data design and initial corpus
- **Description:** Define the three schemas and author the first corpus slice with the deliberate inconsistencies.
- **Owner:** AI Engineering Lead **[PLACEHOLDER]** · **Priority:** High · **Due:** 4 Sep
- **Deliverable:** `docs/requirements/synthetic-data-design.md`, `knowledge/**`, `knowledge/SOURCE-REGISTER.md`
- **Acceptance:** Three schemas documented; every trap present in the data or listed as outstanding; source register complete; synthetic declaration stated.
- **Evidence:** Committed files.

### T1.8 — GitHub repository setup
- **Description:** Create the repository using the brief's structure, add README and `.env.example`, make the first commit.
- **Owner:** DevOps / Documentation Lead **[PLACEHOLDER]** · **Priority:** Urgent · **Due:** 1 Sep
- **Deliverable:** The repository
- **Acceptance:** All folders present; `.gitignore` excludes `.env`; no secret committed; every member has push access.
- **Evidence:** Screenshot of the repository root and of the contributors list.

### T1.9 — ClickUp setup
- **Description:** Create workspace, space, folder, lists, statuses, custom fields; invite all members.
- **Owner:** DevOps / Documentation Lead **[PLACEHOLDER]** · **Priority:** Urgent · **Due:** 1 Sep
- **Deliverable:** The board
- **Acceptance:** All Week 1 tasks created with owners and due dates; all members joined.
- **Evidence:** Screenshot of the board in list view showing owners and dates.

### T1.10 — Evidence collection
- **Description:** Gather and file all Week 1 evidence per the evidence checklist.
- **Owner:** Quality / Security Lead **[PLACEHOLDER]** · **Priority:** Normal · **Due:** 4 Sep
- **Deliverable:** `evidence/screenshots/**`
- **Acceptance:** Every checklist row satisfied; no credential or personal data visible in any screenshot.
- **Evidence:** The filed screenshots themselves.

### T1.11 — Week 1 progress report
- **Description:** Write the 1-2 page report using only work actually completed.
- **Owner:** Project / Requirements Lead **[PLACEHOLDER]** · **Priority:** High · **Due:** 4 Sep
- **Deliverable:** `docs/weekly-reports/week1-progress-report.md`
- **Acceptance:** All eight sections present; individual contributions named; no placeholder left unfilled at submission.
- **Evidence:** Committed file; MUELE submission receipt.

### T1.12 — Final Week 1 review
- **Description:** Check the full submission against the brief's Week 1 deliverable list; fix gaps.
- **Owner:** Whole team **[PLACEHOLDER]** · **Priority:** High · **Due:** 4 Sep
- **Deliverable:** Review notes appended to the progress report
- **Acceptance:** Every brief-listed deliverable accounted for; each member able to explain each artefact.
- **Evidence:** Review notes; ClickUp tasks all Complete or explicitly Blocked with a reason.

## Notes on honest use of the board

- Move a task to Complete when it is done, not when it is planned. A board completed retroactively in one sitting is visible in the activity log and reads badly.
- Every task with `AI-assisted` checked needs a corresponding AI Engineering Log entry.
- Individual accountability is assessed, so avoid assigning tasks to the whole group except T1.12.
