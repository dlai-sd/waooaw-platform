# ADR-019: RAG Architecture — Domain Knowledge and Customer Context Retrieval

**Status:** Accepted
**Date:** 2026-07-08
**Roles Applied:** AI Architect (retrieval architecture) + Data Architect (storage) + Enterprise Architect (data classification)
**Constitutional Basis:** C-040 (domain specialization — LAW); FR-003 (agent learning is WAOOAW IP, customer data is private); AD-012 (business KPI primacy — RAG must retrieve KPI-relevant domain knowledge, not generic content)

---

## Context

Every Digital Professional on WAOOAW must be constitutionally domain-specialized (C-040). A dental marketing agent must know dental marketing patterns for India; a beauty artist agent must know beauty industry trends. This knowledge must be retrieved at inference time, not embedded in the model weights — for two reasons:

1. Domain knowledge changes (algorithm updates, seasonal trends, regulatory changes) and must be updateable without retraining
2. Customer-specific context (brand voice, prior approved content) is private to each customer and cannot be in shared model weights

The question is: how is retrieval architecture organized, what stores are used, and where is each type of knowledge stored?

---

## Decision

**Three-tier RAG architecture: Domain Store → Customer Context Store → Platform Intelligence Store. Each tier has distinct ownership (FR-003), storage technology, and update cadence.**

### Tier 1 — Domain Knowledge Store (WAOOAW IP, shared)

**What:** Industry-level knowledge applicable to all agents of the same professional type.
- Dental marketing: Indian dental patient demographics, content performance benchmarks, seasonal appointment patterns, healthcare marketing regulations (India)
- Beauty: beauty industry trends, platform aesthetic standards, seasonal booking patterns
- Trading: technical analysis patterns, SEBI regulations, FO/Crypto market microstructure

**Storage:** PostgreSQL `institutional` schema + pgvector for semantic search (ADR decision for dedicated vector DB deferred to when volume warrants — see below)

**Update cadence:** Weekly automated refresh from curated sources + Founder-approved manual curation
**Ownership:** WAOOAW IP (FR-003) — never exposed to customers or competitors
**Access:** AI Runtime only — read-only at inference time

### Tier 2 — Customer Context Store (Customer Private, per-tenant)

**What:** Per-customer knowledge built from the customer's specific engagement.
- Brand voice embeddings (Dr. Mehta's aesthetic, Sana's style)
- Historical approved content embeddings
- Customer preference signals (what they approved vs rejected)
- Business goal context

**Storage:** `professional.creative_standard_embeddings` (already specified, pgvector)
**Update cadence:** Real-time — updated after every customer approval/rejection signal
**Ownership:** Customer private (C-005) — RLS enforced at DB level
**Access:** AI Runtime — isolated per customer via `tenant_id`

### Tier 3 — Platform Intelligence Store (WAOOAW IP, aggregate-derived)

**What:** Cross-customer aggregate patterns — what works for dental clinics in Pune on Instagram, what posting times generate most engagement for beauty artists in Mumbai. Derived from anonymized, aggregated signals from Tier 2 across all customers. No individual customer is identifiable.

**Storage:** Separate pgvector index in `institutional` schema, populated by a batch aggregation pipeline
**Update cadence:** Daily batch aggregation job
**Ownership:** WAOOAW IP (FR-003) — the most valuable WAOOAW asset
**Access:** AI Runtime — read-only, informing inference quality

---

## RAG Pipeline at Inference Time

```
Inference request arrives (e.g., "create this week's Instagram post for Dr. Mehta")
        ↓
1. Retrieve from Tier 1 (Domain):
   Query: "dental marketing Instagram best practices India 2026"
   Returns: top-5 relevant domain knowledge chunks
        ↓
2. Retrieve from Tier 2 (Customer):
   Query: "Dr. Mehta brand voice previous posts aesthetic"
   Returns: 3 most similar approved posts + brand voice embedding
        ↓
3. Retrieve from Tier 3 (Platform Intelligence):
   Query: "dental clinic Instagram posts Pune high engagement"
   Returns: aggregate performance patterns for this segment
        ↓
4. Construct context-rich prompt:
   [Domain knowledge] + [Customer context] + [Platform patterns] + [Task instruction]
        ↓
5. LLM generates content
        ↓
6. Creative Standard Enforcer validates against customer's style profile (Tier 2)
        ↓
7. Returns proposed content to Professional Runtime
```

---

## Storage Technology Decision

**MVI decision:** pgvector in the existing PostgreSQL instance (institutional schema).

**Rationale:** At MVI scale (tens of customers, hundreds of agent interactions), pgvector within PostgreSQL is sufficient. It avoids adding a new infrastructure component (no Pinecone, no Weaviate, no Qdrant at MVI).

**Future decision trigger:** When the `institutional` schema's pgvector index grows beyond 1M vectors OR when cross-account retrieval latency exceeds 100ms P95 — then evaluate a dedicated vector database (ADR-019-addendum).

---

## Amendment 1 — Chunking Specification (2026-07-23, audit GAP-CH10-01)

**Authority:** Audit finding GAP-CH10-01 — production RAG chunking was unspecified. This amendment defines the mandatory chunking strategy for all tiers.

### Mandatory Chunking Strategy

All documents ingested into Tier 1 (Domain Knowledge) and Tier 3 (Platform Intelligence) must be chunked using the following specification. This is not a recommendation — it is the enforced standard for all ingestion pipelines.

| Parameter | Value | Rationale |
|---|---|---|
| Chunk size | 512 tokens | Balances semantic coherence vs retrieval precision. Validated against DMA, Trading, and Agricultural domain corpora. |
| Chunk overlap | 50 tokens | Preserves context across chunk boundaries without inflating index size. |
| Boundary enforcement | Sentence boundary aware | Never split at mid-sentence. Use `spaCy` sentence tokenizer (multilingual model `xx_sent_ud_sm`) before chunking. |
| Language handling | Multilingual — sentence tokenizer handles Hindi, Marathi, Tamil, Telugu, Kannada | Required for Agricultural agent (C-042) domain knowledge in regional languages. |
| Maximum chunk tokens | 512 (hard limit) | If a sentence exceeds 512 tokens alone (rare), it is split at the 512-token boundary as an exception. |
| Minimum chunk tokens | 50 | Chunks below 50 tokens are merged with the adjacent chunk. Prevents low-signal micro-chunks. |

### Chunk Metadata (mandatory on every chunk)

Every chunk stored in pgvector must carry the following metadata alongside the embedding:

```python
@dataclass
class ChunkMetadata:
    source_document_id: str          # e.g., "dental_marketing_india_v3"
    source_document_version: str     # semantic version — allows stale chunk detection
    source_section: str              # e.g., "Section 4: Instagram Content Strategy"
    chunk_index: int                 # position within source document (0-based)
    chunk_token_count: int           # actual token count (not nominal 512)
    language: str                    # ISO 639-1 code: "en", "hi", "mr", "ta", etc.
    domain: str                      # "dental_marketing", "trading", "agricultural", etc.
    tier: int                        # 1 (Domain) | 3 (Platform Intelligence)
    created_at: datetime
    # Tier 2 (Customer Context) chunks also carry:
    tenant_id: Optional[str]         # UUID — RLS anchor; None for Tier 1/3 (shared)
    contract_id: Optional[str]       # UUID — links to employment contract
```

### Source Attribution in Reasoning Traces

Every chunk retrieved during inference must be logged in the `context_summary` JSONB of the `agent_reasoning_traces` table. This closes the black-box gap — the trace records not just what action was taken, but what knowledge justified it.

```json
{
  "tier1_chunks": [
    {
      "source_document_id": "dental_marketing_india_v3",
      "source_section": "Section 4: Instagram Content Strategy",
      "chunk_index": 12,
      "similarity_score": 0.91,
      "token_count": 487
    }
  ],
  "tier2_chunks": [
    {
      "source_document_id": "dr_mehta_brand_voice_v4",
      "chunk_index": 3,
      "similarity_score": 0.88,
      "token_count": 312
    }
  ],
  "tier3_chunks": [...],
  "total_context_tokens": 1247
}
```

---

## Amendment 2 — Per-Inference Token Budget (2026-07-23, audit GAP-CH10-02)

**Authority:** Audit finding GAP-CH10-02 — no per-inference RAG token budget specified for production agents.

### Production RAG Context Budget per Agent Type

Every agent type has a defined maximum token budget for RAG context (Tier 1 + Tier 2 + Tier 3 combined). This budget is enforced at the AI Runtime RAG pipeline stage — retrieval stops when the budget is reached, not when top-K chunks are exhausted.

**Budget enforcement principle:** Quality over quantity. Fewer highly-relevant chunks are better than many loosely-relevant chunks within the same budget.

| Agent Type | Skill Context | Tier 1 Budget | Tier 2 Budget | Tier 3 Budget | Total RAG Budget |
|---|---|---|---|---|---|
| Digital Marketing Agent | Skill 2 (Content) | 1,500 tok | 1,000 tok | 500 tok | 3,000 tok |
| Digital Marketing Agent | Skill 1 (Market Research) | 2,000 tok | 500 tok | 1,000 tok | 3,500 tok |
| Trading Agent | All skills | 1,000 tok (pre-warmed) | 800 tok | 200 tok | 2,000 tok |
| Agricultural Agent | Advisory | 1,500 tok | 600 tok | 400 tok | 2,500 tok |
| Private Tutor Agent | All skills | 1,500 tok | 1,000 tok | 500 tok | 3,000 tok |
| Self-Improvement Analyst | All skills | 2,000 tok | 0 tok | 1,500 tok | 3,500 tok |
| Platform IT Expert | All skills | 2,500 tok | 0 tok | 500 tok | 3,000 tok |
| Platform Operations | All skills | 1,000 tok | 0 tok | 500 tok | 1,500 tok |

**Overflow behavior:** If the budget is reached before top-K chunks are exhausted, the retrieval stops. The `context_summary.budget_reached` flag is set to `true` in the reasoning trace. The Self-Improvement Analyst monitors budget_reached frequency — if > 20% of traces for an agent type hit the budget, it triggers a domain knowledge curation review.

**Trading Agent special case:** Tier 1 chunks for Trading are pre-warmed at PAAS session start (zero retrieval latency in the hot path). The 1,000-token Tier 1 budget is loaded once and held in the PAAS session state for the session duration.

---

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Dedicated vector database (Pinecone, Weaviate) at MVI | Adds infrastructure complexity and cost. AD-006 cost constraint. pgvector sufficient for MVI scale. |
| All knowledge in model weights (fine-tuning) | Cannot be updated without retraining. Customer context cannot be in shared weights (privacy). Violates C-040 (domain knowledge must be current). |
| No RAG (pure prompt injection) | Context window limits prevent adequate domain knowledge. No persistent learning. Violates C-040. |

---

## Consequences

**Benefits:**
- Domain knowledge updateable without model changes
- Customer context is isolated per tenant (RLS enforced)
- WAOOAW IP (Tier 1 + 3) never mixed with customer data
- Inference quality improves continuously as Tier 3 accumulates aggregate patterns

**Trade-offs:**
- Retrieval adds ~20-50ms to inference latency (acceptable within PAAS budget for non-trading agents; for trading agent, retrieval is pre-warmed at session start)
- pgvector requires indexing maintenance (`REINDEX` periodically as embeddings grow)

---

## Amendment 3 — Autonomous RSA-Triggered Domain Store Refresh (2026-07-24)

**Authority:** C-069 Amendment 1 (2026-07-24) — Level 0 knowledge gap pattern defined by
Reasoning Sprint Analyst spec (architecture/reference/agents/reasoning-sprint-analyst-agent.md v1.3)

**The gap this amendment closes:** ADR-019 specified weekly automated refresh for Tier 1 and
real-time updates for Tier 2. Neither covered on-demand autonomous refresh triggered by detected
knowledge gaps during agent execution.

**Decision:** A fourth refresh trigger is added for Tier 1:

**Trigger 4 — RSA Knowledge Gap Refresh (autonomous, no human approval)**
- **When:** Reasoning Sprint Analyst or Self-Improvement Analyst detects that Tier 1 lacks data
  needed for an existing skill (agent escalated, CCT failed, or C-049 escalation cluster)
- **What:** RSA constructs the missing knowledge payload using LLM synthesis + authoritative sources
- **How:** Calls the Domain Store ingest API directly — same pipeline as weekly refresh, different trigger
- **Validation:** The ingest pipeline validates factual consistency before accepting the payload
- **Exception:** Legal/regulatory data (SEBI, medical guidelines) requires domain curator review before ingest
- **Customer visibility:** Zero. The next agent session has the knowledge. No notification.

**Constitutional basis:** C-069 (platform must improve without waiting for humans), C-070
Instinct 3 (autonomous trust-based execution), C-048 (not exploiting customer unawareness).
