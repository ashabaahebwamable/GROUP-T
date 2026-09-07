# Week 1 Progress Report

> **TEMPLATE.** Every `[INSERT …]` marker must be replaced with what the team actually did.
> Nothing in this file is a record of completed work until a member fills it in.
> Target length 1-2 pages.

| | |
|---|---|
| Group / project | [INSERT GROUP IDENTIFIER] — SME Procurement-Preparation Agent (working name: ReqPrep) |
| Course | BSE4104 Emerging Trends in Software Engineering |
| Week | Week 1 — Problem Framing and AI-Native Requirements |
| Week ending | 4 September 2026 |
| Members | [INSERT MEMBER NAMES AND ROLES] |
| Repository | [INSERT ACTUAL GITHUB REPOSITORY URL] |
| ClickUp board | [INSERT ACTUAL CLICKUP LINK] |

## 1. Work completed against weekly objectives

The brief's Week 1 objectives are: select one feasible use case, define users and success criteria, justify AI use, and set the boundaries of the agent.

| Objective | Status | Artefact | Note |
|---|---|---|---|
| Use case selected | [INSERT STATUS] | `docs/requirements/project-definition.md` | SME procurement-preparation agent |
| Single primary workflow defined | [INSERT STATUS] | `project-charter.md` §7 | Reorder signal to approved requisition, one item per case |
| Project Charter (2-3 pages) | [INSERT STATUS] | `docs/requirements/project-charter.md` | |
| 8-12 user stories with acceptance criteria | [INSERT STATUS] | `docs/requirements/user-stories.md` | [INSERT NUMBER] stories |
| AI Boundary Matrix | [INSERT STATUS] | `docs/requirements/ai-boundary-matrix.md` | |
| Initial architecture / context diagram | [INSERT STATUS] | `docs/architecture/week1-context-diagram.md` | |
| GitHub repository created | [INSERT STATUS] | [INSERT URL] | |
| ClickUp project created, Week 1 tasks assigned | [INSERT STATUS] | [INSERT URL] | |
| Synthetic data design and initial corpus | [INSERT STATUS] | `docs/requirements/synthetic-data-design.md` | [OPTIONAL by the brief in Week 1; brought forward] |
| Manual baseline measured | [INSERT STATUS] | `docs/evaluation/week1-manual-baseline.md` | [INSERT ACTUAL RESULT OR "not completed"] |

## 2. Key engineering decisions and why

State each decision, the alternative rejected, and the reason. Suggested content, to be confirmed or replaced by what the team actually decided:

1. **One stock item per requisition.** Multi-line requisitions would introduce split supplier award, which falls outside the safety boundary, and would multiply the evaluation scenario count. [CONFIRM OR REPLACE]
2. **No model-produced figure is used by the system.** All monetary arithmetic is recomputed in code; discrepancies are logged. Rejected alternative: allowing the model to compute totals for speed. [CONFIRM OR REPLACE]
3. **Quotation letters in text form included in the corpus**, not structured records alone. Reason: Week 3 requires genuine retrieval and grounding, and extraction from varying prose is where AI adds value. [CONFIRM OR REPLACE]
4. **Optical character recognition excluded.** Realistic but would consume roughly two weeks and its errors would be indistinguishable from agent failures in evaluation. [CONFIRM OR REPLACE]
5. [INSERT ANY FURTHER DECISION THE TEAM ACTUALLY MADE]

## 3. Failures, challenges and current response

Record what actually went wrong. This section is assessed; an empty one is not credible.

| Challenge | Response | Status |
|---|---|---|
| [INSERT ACTUAL CHALLENGE] | [INSERT RESPONSE] | [INSERT STATUS] |
| [INSERT ACTUAL CHALLENGE] | [INSERT RESPONSE] | [INSERT STATUS] |

Known open items at the close of Week 1:
- Iteration limit for the bounded agent not yet fixed [INSERT DECISION OR CONFIRM STILL OPEN]
- Success criteria thresholds not yet agreed [INSERT DECISION OR CONFIRM STILL OPEN]
- Corpus expansion from [INSERT NUMBER] to 25-40 items outstanding
- [INSERT ANY OTHER OPEN ITEM]

## 4. GitHub evidence

| Item | Reference |
|---|---|
| Repository URL | [INSERT ACTUAL GITHUB REPOSITORY URL] |
| First commit | [INSERT ACTUAL COMMIT HASH AND DATE] |
| Commits this week | [INSERT NUMBER] |
| Contributors | [INSERT MEMBER NAMES WITH COMMIT COUNTS] |
| Folder structure | Per brief §5 |
| Secret handling | `.env` excluded via `.gitignore`; `.env.example` contains placeholders only |

## 5. ClickUp evidence

| Item | Reference |
|---|---|
| Board URL | [INSERT ACTUAL CLICKUP LINK] |
| Week 1 tasks created | [INSERT NUMBER] |
| Tasks complete / in progress / blocked | [INSERT COUNTS] |
| Members joined | [INSERT NUMBER OF MEMBERS] |
| Tasks linked to repository evidence | [INSERT NUMBER] |

## 6. Individual contribution summary

Each member completes their own row and their own paragraph. The brief requires that every student be able to explain the work they submit.

| Member | Role | Tasks owned | Artefacts authored | Commits |
|---|---|---|---|---|
| [INSERT NAME] | [INSERT ROLE] | [INSERT TASK IDS] | [INSERT FILES] | [INSERT NUMBER] |
| [INSERT NAME] | [INSERT ROLE] | [INSERT TASK IDS] | [INSERT FILES] | [INSERT NUMBER] |
| [INSERT NAME] | [INSERT ROLE] | [INSERT TASK IDS] | [INSERT FILES] | [INSERT NUMBER] |
| [INSERT NAME] | [INSERT ROLE] | [INSERT TASK IDS] | [INSERT FILES] | [INSERT NUMBER] |

**[INSERT NAME]:** [INSERT ONE PARAGRAPH: a decision you personally made this week and why]

## 7. Declared use of AI tools

Per brief §6. Full detail in `docs/ai-engineering-log.md`.

| Tool / model | Used for | Reviewed by |
|---|---|---|
| [INSERT TOOL] | [INSERT PURPOSE] | [INSERT MEMBER] |

## 8. Plan for Week 2

Week 2 focus per the brief: build the smallest useful model-backed capability and establish a tested baseline before adding retrieval or agency.

| Planned task | Owner | Target |
|---|---|---|
| Select the model; document capability, cost, latency, privacy and access | [INSERT NAME] | Model Selection Note, 1 page |
| Integrate the model into the application | [INSERT NAME] | Working baseline interaction |
| Write Prompt Specification v1.0 | [INSERT NAME] | Role, task, context, constraints, output format, failure behaviour |
| Build the 10-case prompt evaluation table | [INSERT NAME] | Expected vs actual recorded |
| Version at least two meaningful prompt iterations | [INSERT NAME] | `prompts/` with history |
| Close the open items in §3 | [INSERT NAME] | Iteration limit and thresholds agreed |

**Carried forward:** the first model-backed capability will be quotation field extraction, since it is the narrowest slice with real AI value and it feeds every later week. [CONFIRM OR REPLACE]
