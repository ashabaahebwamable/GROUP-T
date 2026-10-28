# SME Procurement-Preparation Agent (working name: ReqPrep)

**BSE4104 Emerging Trends in Software Engineering — 8-Week AI-Native & Agentic Engineering Capstone**
Makerere University · College of Computing and Information Sciences · Department of Networks
Course convener: Dr Kamulegeya Grace B (PhD)

Group: **GROUP T** · Members: Azibo Isaac Alinda, Tendo Caisey, Akisa Maria Ashley, Ashaba Aheebwa Mable, Wakinya Esau John · Academic year 2026/2027

---

## What this system does

ReqPrep assists a small-business stores officer in preparing a **single-item purchase requisition**. It checks stock against reorder levels, reads the commercial terms out of supplier quotations, converts them to a comparable basis, applies the procurement rules, and produces a draft requisition with a recommended supplier and written justification. It then stops for human confirmation and approval.

## What this system does not do

It issues no purchase order, contacts no supplier, and moves no money. There is no supplier channel, no payment interface and no purchase-order capability in the codebase — these are **absent capabilities, not disabled features**. Supplier award, purchasing, payment and autonomous financial commitment are outside scope, per the brief's safety boundary for this use case.

## Division of responsibility

| Layer                      | Responsibility                                                                                                                                                                                                             |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **AI**                     | Extraction of commercial terms from quotation text; detection and escalation of ambiguity; grounded policy explanation with citations; drafting the requisition narrative; proposing the next step within the bounded loop |
| **Deterministic software** | All monetary and unit arithmetic; every policy rule; authorisation; schema validation; the requisition state machine; the audit log; the tool allow-list and iteration limit                                               |
| **Human**                  | Confirming the recommended supplier; approving, rejecting or querying every requisition, at every value; authorising any policy override or durable memory write                                                           |

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
    week1-progress-report.md               Week 1 deliverable — progress report (reconciliation draft)
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

## Setup and reproducible runs

### Requirements

- Python **3.12 or newer** (CI uses 3.12; the tests also pass on 3.13).
- Git, for cloning the repository.
- Internet access for the first installation and first retrieval run: `sentence-transformers` downloads the local embedding model when needed. Retrieval runs locally after that. Model-backed features additionally require a Gemini API key.

 Clone the repository and move into the project folder, then create and activate a virtual environment and install the dependencies:

```powershell
   git clone https://github.com/ashabaahebwamable/GROUP-T.git
   cd GROUP-T\BSE4104-SME-PROCUREMENT-AGENT
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
```

If PowerShell blocks activation, either allow scripts for the current terminal according to your organization's policy, or call the environment's interpreter directly as `.\.venv\Scripts\python.exe` in the commands below. On macOS/Linux, use `python3 -m venv .venv`, `source .venv/bin/activate`, and then the same `python -m pip ...` commands.

On Windows, clone into a short path such as `C:\dev\`. Some evidence files have long names, and in a deeply nested folder the clone fails with `Filename too long` because of Windows' 260-character path limit. If you must use a long path, run `git config --global core.longpaths true` before cloning.

### Run the deterministic demo

```powershell
python -m scripts.demo_week5
```

This follows the reference cement case through the officer confirmation and draft hand-off. By default, writes go to a temporary directory and are discarded. It does not call Gemini, but the first run may download the local embedding model. Do **not** use `--persist` for a rehearsal unless you intend to modify local data and evidence files.
The first run can look frozen for about two minutes while the embedding model loads. Don't press anything. Once the model has been downloaded, you can set `$env:HF_HUB_OFFLINE = "1"` before running to stop network retry messages. Don't set it on a first run, because it blocks the download.

### Run tests and check evaluation wiring

```powershell
python -m pytest tests/ -v
python -m src.eval.run --check
```

The test dependencies, including `pytest`, are listed in `requirements.txt`. CI installs `pytest` separately as well; this is redundant but ensures its test command is available. The evaluation check verifies the scenario document against the runner; it does not execute the evaluation.

The full evaluation is deliberately gated: both owners must sign `docs/evaluation/criteria.md` section 6 before it is run. That agreement was recorded on 19 and 21 October 2026, before the recorded full run. To repeat the run, use `python -m src.eval.run`; model-backed scenarios need `MODEL_API_KEY`, internet access and available Gemini quota, and the batching rules are in section 4 of that document. Check `python -m src.eval.run --help` for the supported options. Evaluation results and traces are evidence; review them before treating automated outcomes as final.
### Model configuration and secrets

The tests and deterministic demo do not need a Gemini API key. To run a model-backed script locally, copy `.env.example` to `.env` and set `MODEL_API_KEY` (and, if needed, `MODEL_NAME` and `MODEL_PROVIDER`) to values you obtained yourself. `.env` is excluded by `.gitignore` and **must never be committed**. No key, token or password belongs in this repository, in any file, at any time. Never put credentials in a command, screenshot, log or evidence artifact.

## Project timeline

| Week | Focus                                      | Status      |
| ---- | ------------------------------------------ | ----------- |
| 1    | Problem framing and AI-native requirements | Complete    |
| 2    | Foundation-model engineering and prompting | Complete    |
| 3    | Context engineering and RAG                | Complete    |
| 4    | Tools and function calling                 | Complete    |
| 5    | Agent architecture and bounded autonomy    | Complete    |
| 6    | Memory, state and interoperability         | Complete    |
| 7    | Evaluation, observability and guardrails   | In progress |
| 8    | Hardening and final release                | In progress |

## AI use declaration

AI assistance was used in preparing this project and is declared per assignment brief §6. Material AI-assisted decisions and generated artefacts are recorded in `docs/ai-engineering-log.md`. Every team member remains accountable for the correctness, security and behaviour of all work submitted.
