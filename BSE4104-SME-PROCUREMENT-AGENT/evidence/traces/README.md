# Traces index — GROUP-T ReqPrep

Cross-week index of RAG and agent execution traces. Maintained by the DevOps/Documentation
Lead (Wakinya Esau John) as part of W5-06. Each week's own folder may have a more detailed
README; this file is the entry point across all of them.

| Week | Folder | What it covers | Detail |
|------|--------|-----------------|--------|
| 3 | `week3/` | RAG retrieval traces: two normal policy queries, one genuine refusal (query outside the corpus, zero chunks retrieved) | — |
| 4 | `week4/` | W4-04/W4-05 test run notes (tool dispatch, state machine) | `week4/w4-04-w4-05-test-run.md` |
| 5 | `week5/` | Full agent loop traces against the Week 5 Agent Task Contract: happy path, reference case, stale-quotation real-clock run, ambiguous item, and tool-failure recovery. Includes a findings list (9 issues; 8 resolved on 12 Oct, quotation coverage still open for Week 7). | `week5/README.md` |
| 7 | `week7/` | Structured observability records for a policy-grounded answer, no-evidence refusal, agent hand-off, ambiguous item and tool failure. | `week7/README.md` |

The files at this level (`audit-log.jsonl`, `retrieval.jsonl`, `tool-calls.jsonl` and
`observability.jsonl`) are live logs the system writes to directly rather than curated
evidence — see each week's folder for the specific entries pulled out as evidence.

## Adding a new week
1. Create `weekN/` under this folder.
2. Add the trace files.
3. If there's more than one or two traces, add a short `weekN/README.md` explaining what
   each file shows (see `week5/README.md` for the fullest example).
4. Add a row to the table above.
5. Update the Traces column in `evidence/README.md`.

## Inspecting a Week 7 run

Request traces are appended as JSONL to `evidence/traces/observability.jsonl`. Export
any run to a readable JSON document from the project root:

```powershell
python -m src.observability export <run-id> --output evidence/traces/exported-run.json
```

Use `--log <path>` to inspect a different JSONL file. Each record contains model and
prompt metadata, retrieved evidence, tool calls and results, latency, errors and the
final outcome. The bounded deterministic planner records that it did not call a model.
