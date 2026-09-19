# Week 3 RAG Architecture

```mermaid
flowchart LR
    A[Controlled knowledge corpus] --> B[Ingest and normalize]
    B --> C[Chunk documents]
    C --> D[Index locally\nMiniLM embeddings + SQLite FTS5]
    Q[User query] --> E[retrieve(query, k)]
    D --> E
    E --> T{Best score >= 0.35?}
    T -- No --> R[Refusal: cannot answer from available documents]
    T -- Yes --> F[Build context with DOC_ID, metadata, score]
    F --> M[Policy QA model prompt v1.0]
    M --> V[Validate citations against retrieved DOC_IDs]
    V --> O[Cited grounded answer]
    E -. every query .-> L[evidence/traces/retrieval.jsonl]
```
