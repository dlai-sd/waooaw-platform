# SIM-PL-002 — WC015-05 Unit Tests ≥90% + PSE Routing Tests
**Date:** 2026-07-29
**Author:** Platform IT Expert (Architecture hat)
**Task:** WC015-05 — Unit tests ≥90% for PSE + RAG + dispatch, mock Ollama + pgvector
**Simulation type:** Dependency Graph Task Decomposition (IB-021)

## Context
Comprehensive test suite covering PSE 4-tier routing decisions, RAG similarity
search (mocked pgvector), Ollama dispatch (mocked httpx), and prompt guard.
Target: ≥90% coverage per C-076.
Stack: Python 3.12 pytest + pytest-asyncio. Constitutional: C-076 (test coverage).

## Subtask Decomposition
WC015-05a (llm, reasoning) — test_pse.py: PSE routing table + tier selection tests → ruff → PASS
WC015-05b (llm, reasoning) — test_dispatch.py + test_rag.py: mock AsyncMock suite → ruff → PASS

## Dependency Graph
WC015-05a: depends_on=[WC015-01b, WC015-02a, WC015-03a]
WC015-05b: depends_on=[WC015-05a]

## Risk Assessment
- Same mock pattern as WC014-03b (test_sessions.py) — proven approach
- pytest-asyncio: `@pytest.mark.asyncio` + `async def test_*` — established
- per-file-ignores: tests/** has LOG015, G004, S, ANN suppressed
- ruff --unsafe-fixes: F841 auto-renamed; B018 caught by STACK_BEHAVIORAL_RULES
- AsyncMock for httpx: `unittest.mock.patch("httpx.AsyncClient.post")` — standard
- sys.path.insert for hyphenated ai-runtime dir: STACK_BEHAVIORAL_RULES covers this

## Verdict

**VERDICT: ✅ PASS**
