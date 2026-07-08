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
