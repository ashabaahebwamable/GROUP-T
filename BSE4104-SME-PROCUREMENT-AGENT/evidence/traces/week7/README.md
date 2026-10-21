# Week 7 request traces

Generated with `python -m scripts.generate_week7_traces`. These records are
representative outputs from the observability hooks in `src/observability/`, the
bounded agent loop and the RAG answer path. All RAG model/retriever responses in this
set are injected deterministic fixtures; no external model API is called.

| File | Scenario |
|---|---|
| `rag-grounded-answer.json` | One retrieved policy chunk, model answer and citation |
| `rag-no-evidence-refusal.json` | No chunks retrieved; safe refusal without a model call |
| `agent-handoff.json` | Bounded agent checks reorder status, policy and quotations, then pauses for officer confirmation |
| `ambiguous-item.json` | Multiple inventory matches, human hand-off and no tool calls |
| `tool-failure.json` | Inventory tool outage, recorded error and safe hand-off |

Every trace includes a unique run ID, request data, model/planner metadata, prompt
version, retrieved chunks, tool calls/results, latency, errors and final outcome. The
agent traces correctly identify the deterministic planner as making no model call.

To inspect a live run, use this command from the project root:

```powershell
python -m src.observability export <run-id> --output <file.json>
```

To regenerate this evidence, run the generator above; it redirects application logs
and requisition writes to a temporary directory.
