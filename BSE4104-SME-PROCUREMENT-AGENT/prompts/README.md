# Prompt Library

This folder stores the prompt versions used for the ProcurePrep quotation-extraction baseline.

| Version | File                            | Status                   | Notes                                                                   |
| ------- | ------------------------------- | ------------------------ | ----------------------------------------------------------------------- |
| v1.0    | `quotation_extraction_v1.0.txt` | Baseline                 | Defines role, task, constraints, JSON output and failure handling.      |
| v1.1    | `quotation_extraction_v1.1.txt` | Evidence-first iteration | Tightens trust boundaries, output contract and uncertainty handling.    |
| v1.2    | `quotation_extraction_v1.2.txt` | Final Week 2 revision    | Adds explicit schema, missing-field logging and contradiction handling. |

## Version history

1. v1.0 established the extraction task and safety rules.
2. v1.1 clarified the input trust boundary and rejected hallucinated procurement decisions.
3. v1.2 finalized the schema and explicit rules for missing values, ambiguities and contradictory prices.

The current project baseline uses the quotation-extraction workflow implemented in `src/quotation_extractor.py` and the model call interface in `src/model_client.py`.
