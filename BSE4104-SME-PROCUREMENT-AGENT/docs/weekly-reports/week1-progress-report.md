# Week 1 Progress Report

> Reconciliation draft prepared 8 September 2026 from the repository state. Items
> requiring team or ClickUp confirmation are recorded as pending, not claimed as complete.

|                 |                                                                                                          |
| --------------- | -------------------------------------------------------------------------------------------------------- |
| Group / project | Group identifier pending confirmation — SME Procurement-Preparation Agent (working name: ReqPrep)        |
| Course          | BSE4104 Emerging Trends in Software Engineering                                                          |
| Week            | Week 1 — Problem Framing and AI-Native Requirements                                                      |
| Week ending     | 4 September 2026                                                                                         |
| Members         | Azibo Isaac Alinda — individual Week 1 repository work; remaining members and roles pending confirmation |
| Repository      | https://github.com/ashabaahebwamable/GROUP-T                                                             |
| ClickUp board   | Pending: board URL and task activity were not available in the repository                                |

## 1. Work completed against weekly objectives

The brief's Week 1 objectives are: select one feasible use case, define users and success criteria, justify AI use, and set the boundaries of the agent.

| Objective                                      | Status                                      | Artefact                                     | Note                                                                    |
| ---------------------------------------------- | ------------------------------------------- | -------------------------------------------- | ----------------------------------------------------------------------- |
| Use case selected                              | Complete locally; team confirmation pending | `docs/requirements/project-definition.md`    | SME procurement-preparation agent                                       |
| Single primary workflow defined                | Complete                                    | `project-charter.md` §7                      | Reorder signal to approved requisition, one item per case               |
| Project Charter (2-3 pages)                    | Draft complete; team review pending         | `docs/requirements/project-charter.md`       | Contains scope, AI boundary, workflow, assumptions and success criteria |
| 8-12 user stories with acceptance criteria     | Complete locally; team review pending       | `docs/requirements/user-stories.md`          | 12 stories with Given/When/Then criteria and test methods               |
| AI Boundary Matrix                             | Complete locally; team review pending       | `docs/requirements/ai-boundary-matrix.md`    | 20 activity rows with enforcement mechanisms                            |
| Initial architecture / context diagram         | Source complete; rendered PNG pending       | `docs/architecture/week1-context-diagram.md` | ASCII and Mermaid versions are committed                                |
| GitHub repository created                      | Complete                                    | https://github.com/ashabaahebwamable/GROUP-T | `main` is synchronized with `origin/main`                               |
| ClickUp project created, Week 1 tasks assigned | Not verified                                | Pending board URL                            | Must be confirmed before submission                                     |
| Synthetic data design and initial corpus       | Initial slice complete; expansion pending   | `docs/requirements/synthetic-data-design.md` | 15 inventory rows, 6 suppliers, 10 quotations and 4 quotation letters   |
| Manual baseline measured                       | Not completed                               | `docs/evaluation/week1-manual-baseline.md`   | Three cases still need timed manual measurement                         |

## 2. Key engineering decisions and why

State each decision, the alternative rejected, and the reason. Suggested content, to be confirmed or replaced by what the team actually decided:

1. **One stock item per requisition.** Multi-line requisitions would introduce split supplier award, which falls outside the safety boundary, and would multiply the evaluation scenario count.
2. **No model-produced figure is used by the system.** All monetary arithmetic is recomputed in code; discrepancies are logged. The alternative of allowing the model to compute totals was rejected for financial-safety reasons.
3. **Quotation letters in text form are included in the corpus**, not structured records alone, because extraction from varying prose supplies a meaningful AI task and supports later grounding tests.
4. **Optical character recognition is excluded.** It would add a separate failure source and is outside the capacity of the eight-week project.
5. **All data is synthetic and team-authored.** This satisfies the brief's data-access constraint and permits deliberate mis-ranking, missing-field and expired-quotation test cases.

## 3. Failures, challenges and current response

Record what actually went wrong. This section is assessed; an empty one is not credible.

| Challenge                                                                                                         | Response                                                                                             | Status                     |
| ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------- |
| Work began before all group and ClickUp details were available                                                    | Completed the repository-based Week 1 artefacts and recorded unknown administrative facts as pending | Open for team confirmation |
| Evidence corpus is intentionally smaller than the final target and one missing-unit quotation remains outstanding | Kept the initial slice bounded and listed the expansion and missing-field case as Week 2 work        | Carried forward            |

Known open items at the close of Week 1:

- Iteration limit for the bounded agent remains a proposed 6 tool-call maximum and requires team confirmation.
- Success-criteria thresholds remain proposed and require team confirmation.
- Corpus expansion from the initial 21 items/documents to the 25-40 target remains outstanding.
- The rendered architecture PNG, manual baseline, ClickUp evidence, and individual member allocations remain outstanding.

## 4. GitHub evidence

| Item              | Reference                                                                   |
| ----------------- | --------------------------------------------------------------------------- |
| Repository URL    | https://github.com/ashabaahebwamable/GROUP-T                                |
| First commit      | `8f619c2` — 7 September 2026, 13:00 +0300                                   |
| Commits this week | 1 verified commit in the local history                                      |
| Contributors      | Azibo Isaac Alinda — 1 commit; additional contributors pending confirmation |
| Folder structure  | Per brief §5                                                                |
| Secret handling   | `.env` excluded via `.gitignore`; `.env.example` contains placeholders only |

## 5. ClickUp evidence

| Item                                   | Reference                        |
| -------------------------------------- | -------------------------------- |
| Board URL                              | Pending confirmation             |
| Week 1 tasks created                   | Not verified from the repository |
| Tasks complete / in progress / blocked | Not verified from the repository |
| Members joined                         | Not verified from the repository |
| Tasks linked to repository evidence    | Not verified from the repository |

## 6. Individual contribution summary

Each member completes their own row and their own paragraph. The brief requires that every student be able to explain the work they submit.

| Member             | Role                                        | Tasks owned                  | Artefacts authored                                                                                                           | Commits |
| ------------------ | ------------------------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------- |
| Azibo Isaac Alinda | Project / Requirements and repository setup | T1.1, T1.3-T1.8, T1.11 draft | Charter, definition, stories, boundary matrix, architecture source, synthetic-data design, repository README and this report | 1       |

**Azibo Isaac Alinda:** I bounded the system to one stock item per requisition and kept supplier confirmation and approval as separate human gates. This avoids split supplier award and prevents a model recommendation from becoming an unauthorised purchasing decision. Remaining members must add their own rows and contribution paragraphs before submission.

## 7. Declared use of AI tools

Per brief §6. Full detail in `docs/ai-engineering-log.md`.

| Tool / model                   | Used for                                                                                      | Reviewed by                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| GitHub Copilot / AI assistance | Drafting and reviewing requirements, boundaries, architecture wording and this reconciliation | Azibo Isaac Alinda; review and final acceptance remain the student's responsibility |

## 8. Plan for Week 2

Week 2 focus per the brief: build the smallest useful model-backed capability and establish a tested baseline before adding retrieval or agency.

| Planned task                                                             | Owner                                          | Target                                                             |
| ------------------------------------------------------------------------ | ---------------------------------------------- | ------------------------------------------------------------------ |
| Select the model; document capability, cost, latency, privacy and access | Team member to be assigned                     | Model Selection Note, 1 page                                       |
| Integrate the model into the application                                 | Application / Integration owner to be assigned | Working baseline interaction                                       |
| Write Prompt Specification v1.0                                          | AI Engineering owner to be assigned            | Role, task, context, constraints, output format, failure behaviour |
| Build the 10-case prompt evaluation table                                | Quality owner to be assigned                   | Expected vs actual recorded                                        |
| Version at least two meaningful prompt iterations                        | AI Engineering owner to be assigned            | `prompts/` with history                                            |
| Close the open items in §3                                               | Whole team after roles are confirmed           | Iteration limit, thresholds and evidence gaps agreed               |

**Carried forward:** quotation field extraction remains the proposed first model-backed capability because it is the narrowest slice with clear AI value and feeds every later week. The team should confirm this at the Week 2 kickoff.
