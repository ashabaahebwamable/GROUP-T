# Traces index — GROUP-T ReqPrep

Cross-week index of RAG and agent execution traces. Maintained by the DevOps/Documentation
Lead (Wakinya Esau John) as part of W5-06. Each week's own folder may have a more detailed
README; this file is the entry point across all of them.

| Week | Folder | What it covers | Detail |
|------|--------|-----------------|--------|
| 3 | `week3/` | RAG retrieval traces: two normal policy queries, one genuine refusal (query outside the corpus, zero chunks retrieved) | — |
| 4 | `week4/` | W4-04/W4-05 test run notes (tool dispatch, state machine) | `week4/w4-04-w4-05-test-run.md` |
| 5 | `week5/` | Full agent loop traces against the Week 5 Agent Task Contract: happy path, reference case, stale-quotation real-clock run, ambiguous item, and tool-failure recovery. Includes a findings list (9 open issues) for the team to action. | `week5/README.md` |

Two files at this level, `audit-log.jsonl` and `retrieval.jsonl`, are live logs the system
writes to directly rather than curated evidence — see each week's folder for the specific
entries pulled out as evidence.

## Adding a new week
1. Create `weekN/` under this folder.
2. Add the trace files.
3. If there's more than one or two traces, add a short `weekN/README.md` explaining what
   each file shows (see `week5/README.md` for the fullest example).
4. Add a row to the table above.
5. Update the Traces column in `evidence/README.md`.
