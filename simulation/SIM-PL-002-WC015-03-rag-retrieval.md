# SIM-PL-002 — WC015-03 RAG Retrieval pgvector Stub
**Date:** 2026-07-29
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC015-03 — RAG retrieval: pgvector similarity search stub (returns top-3 chunks)
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Implements vector similarity search against constitutional.knowledge_chunks (ADR-019).
Uses asyncpg + pgvector `<->` operator. Returns top-3 by cosine similarity.
Stub: returns hardcoded chunks if pgvector not populated yet (dev mode).
Stack: Python 3.12. Constitutional: C-059 (evidence), ADR-019 (RAG architecture).

## Subtask Decomposition
WC015-03a (llm, reasoning) — rag.py: pgvector SELECT top-3 + stub fallback → ruff → PASS
WC015-03b (llm, reasoning) — unit tests: mock asyncpg connection → ruff → PASS

## Dependency Graph
WC015-03a: depends_on=[WC015-01b]
WC015-03b: depends_on=[WC015-03a]

## Risk Assessment
- pgvector operator `<->`: asyncpg accepts raw SQL with `$1::vector` parameter — standard
- Stub mode: `if not chunks: return HARDCODED_CHUNKS` — simple guard
- Async DB session: `async with pool.acquire() as conn:` — established asyncpg pattern
- ruff violations handled by per-file-ignores + STACK_BEHAVIORAL_RULES

## Verdict

**VERDICT: ✅ PASS**
