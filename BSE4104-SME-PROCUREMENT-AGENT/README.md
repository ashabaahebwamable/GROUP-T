# SME Procurement-Preparation Agent (working name: ReqPrep)

**BSE4104 Emerging Trends in Software Engineering — 8-Week AI-Native & Agentic Engineering Capstone**
Makerere University · College of Computing and Information Sciences · Department of Networks
Course convener: Dr Kamulegeya Grace B (PhD)

Group: **[PLACEHOLDER]** · Members: **[PLACEHOLDER]** · Academic year 2026/2027

---

## What this system does

ReqPrep assists a small-business stores officer in preparing a **single-item purchase requisition**. It checks stock against reorder levels, reads the commercial terms out of supplier quotations, converts them to a comparable basis, applies the procurement rules, and produces a draft requisition with a recommended supplier and written justification. It then stops for human confirmation and approval.

## What this system does not do

It issues no purchase order, contacts no supplier, and moves no money. There is no supplier channel, no payment interface and no purchase-order capability in the codebase — these are **absent capabilities, not disabled features**. Supplier award, purchasing, payment and autonomous financial commitment are outside scope, per the brief's safety boundary for this use case.

## Division of responsibility

| Layer | Responsibility |
|---|---|
| **AI** | Extraction of commercial terms from quotation text; detection and escalation of ambiguity; grounded policy explanation with citations; drafting the requisition narrative; proposing the next step within the bounded loop |
| **Deterministic software** | All monetary and unit arithmetic; every policy rule; authorisation; schema validation; the requisition state machine; the audit log; the tool allow-list and iteration limit |
| **Human** | Confirming the recommended supplier; approving, rejecting or querying every requisition, at every value; authorising any policy override or durable memory write |

Two governing principles: **no model-produced figure is used by the system**, and **no automatic approval path exists at any value**.

## Data

All data is **synthetic and team-authored**. No client name, supplier identity, price or record from any production or commercial system is used. Provenance: `knowledge/SOURCE-REGISTER.md`.

## Repository layout

```
README.md                                  this file
docs/
  requirements/
    project-definition.md                  Part 1 — compact project definition
    project-charter.md                     Week 1 deliverable — Project Charter
    user-stories.md                        Week 1 deliverable — 12 stories + acceptance criteria
    ai-boundary-matrix.md                  Week 1 deliverable — full AI Boundary Matrix
    synthetic-data-design.md               data schemas and designed inconsistencies
  architecture/
    week1-context-diagram.md               Week 1 deliverable — architecture + Mermaid source
  weekly-reports/
    week1-progress-report.md               Week 1 deliverable — progress report (template)
    week1-evidence-checklist.md            evidence plan
  evaluation/
    week1-manual-baseline.md               manual baseline (template)
  project-management/
    clickup-week1.md                       ClickUp structure and Week 1 tasks
  ai-engineering-log.md                    required AI use log
prompts/                                   versioned prompts (Week 2 onward)
knowledge/
  SOURCE-REGISTER.md                       corpus provenance
  policy/procurement-policy.md             synthetic procurement policy
  quotations/                              synthetic quotation letters
  records/                                 synthetic inventory, suppliers, quotations, requisitions
src/                                       application source (Week 2 onward)
tests/                                     tests (Week 2 onward)
evidence/
  traces/                                  execution traces (Week 5 onward)
  screenshots/                             evidence screenshots
  demo/                                    demonstration recordings
.env.example                               placeholder configuration — never contains real keys
```

## Configuration and secrets

Copy `.env.example` to `.env` and fill in your own values. `.env` is excluded by `.gitignore` and **must never be committed**. No key, token or password belongs in this repository, in any file, at any time.

## Project timeline

| Week | Focus | Status |
|---|---|---|
| 1 | Problem framing and AI-native requirements | In progress |
| 2 | Foundation-model engineering and prompting | Not started |
| 3 | Context engineering and RAG | Not started |
| 4 | Tools and function calling | Not started |
| 5 | Agent architecture and bounded autonomy | Not started |
| 6 | Memory, state and interoperability | Not started |
| 7 | Evaluation, observability and guardrails | Not started |
| 8 | Hardening and final release | Not started |

## AI use declaration

AI assistance was used in preparing this project and is declared per assignment brief §6. Material AI-assisted decisions and generated artefacts are recorded in `docs/ai-engineering-log.md`. Every team member remains accountable for the correctness, security and behaviour of all work submitted.
