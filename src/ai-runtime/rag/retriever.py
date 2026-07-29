# Implements: architecture/reference/components/ai-runtime.md §0 Provider Abstraction Layer,§1 LLM Gateway
# constitutional_basis: C-023, C-059, C-063
from __future__ import annotations

import asyncio
import logging
from typing import Any

import asyncpg
from pgvector.asyncpg import register_vector
from transformers import pipeline as hf_pipeline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Embedding model — AI4Bharat IndicBERT loaded once at module level (LOCAL tier, ₹0)
# ⛔ DO NOT 'pip install ai4bharat' — model loaded via HuggingFace transformers
# ⛔ DO NOT log raw embeddings — C-063 data minimisation
# ---------------------------------------------------------------------------
_INDIC_BERT_MODEL = "ai4bharat/indic-bert"
_embed_pipeline: Any | None = None


def _get_embed_pipeline() -> Any:
    """Lazy-load IndicBERT feature-extraction pipeline (once per process)."""
    global _embed_pipeline
    if _embed_pipeline is None:
        logger.info("Loading IndicBERT pipeline from HuggingFace: %s", _INDIC_BERT_MODEL)
        _embed_pipeline = hf_pipeline("feature-extraction", model=_INDIC_BERT_MODEL)
    return _embed_pipeline


def _embed_text(text: str) -> list[float]:
    """
    Produce a mean-pooled embedding vector for *text* using IndicBERT.

    The pipeline returns shape (1, seq_len, hidden_dim).  We mean-pool over
    the sequence dimension to produce a single (hidden_dim,) vector.

    C-063: the raw embedding is never logged or returned to callers.
    """
    pipe = _get_embed_pipeline()
    # shape: list[list[list[float]]] → [1][seq_len][hidden_dim]
    output: list[list[list[float]]] = pipe(text)
    token_vectors = output[0]  # shape: [seq_len][hidden_dim]
    hidden_dim = len(token_vectors[0])
    pooled = [
        sum(token_vectors[t][d] for t in range(len(token_vectors))) / len(token_vectors)
        for d in range(hidden_dim)
    ]
    return pooled


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

async def retrieve_chunks(
    query: str,
    dsn: str,
    top_k: int = 3,
) -> list[str]:
    """
    Return the top-*k* content chunks from ``professional.agent_prompts``
    whose ``embedding`` column is nearest to the IndicBERT embedding of *query*
    (cosine / L2 via pgvector ``<=>`` operator).

    Args:
        query:  The user query or context string to embed and search against.
        dsn:    asyncpg-compatible PostgreSQL DSN (injected by caller — never
                hard-coded here; C-063: DSN must not be logged).
        top_k:  Number of chunks to return (default 3 per spec).

    Returns:
        List[str] of up to *top_k* content strings, ordered by similarity
        (most similar first).  Never includes raw embeddings.

    Raises:
        asyncio.CancelledError:  propagated immediately — never swallowed.
        asyncpg.PostgresError:   propagated after logging — caller decides retry.
        ValueError:              if *query* is empty or embedding fails.
    """
    if not query or not query.strip():
        raise ValueError("retrieve_chunks: query must be a non-empty string")

    # Embed in a thread so we do not block the event loop (IndicBERT is synchronous)
    try:
        embedding: list[float] = await asyncio.get_event_loop().run_in_executor(
            None, _embed_text, query
        )
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as exc:
        logger.error(
            "IndicBERT embedding failed",
            exc_info=True,
            extra={"context": "retrieve_chunks.embed"},
        )
        raise ValueError("Embedding generation failed") from exc

    # pgvector expects a plain Python list; asyncpg codec handles serialisation
    conn: asyncpg.Connection | None = None
    try:
        conn = await asyncpg.connect(dsn)
        await register_vector(conn)

        rows: list[asyncpg.Record] = await conn.fetch(
            # C-063: only SELECT content — never SELECT embedding
            "SELECT content "
            "FROM professional.agent_prompts "
            "ORDER BY embedding <=> $1 "
            "LIMIT $2",
            embedding,
            top_k,
        )
        chunks: list[str] = [row["content"] for row in rows]
        logger.info(
            "RAG retrieval returned %d chunk(s) for query (length=%d chars)",
            len(chunks),
            len(query),
        )
        return chunks

    except asyncio.CancelledError:
        raise
    except asyncpg.PostgresError:
        logger.error(
            "pgvector retrieval query failed",
            exc_info=True,
            extra={"context": "retrieve_chunks.query"},
        )
        raise
    finally:
        if conn is not None:
            try:
                await conn.close()
            except asyncpg.PostgresError:
                logger.error(
                    "Failed to close asyncpg connection",
                    exc_info=True,
                    extra={"context": "retrieve_chunks.close"},
                )