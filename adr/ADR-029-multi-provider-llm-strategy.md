# ADR-029 — Multi-Provider LLM Strategy with Conscious Provider Selection

**Status:** ACCEPTED
**Date:** 2026-07-19
**Deciders:** Enterprise Architect, Founder (Yogesh Khandge)
**Constitutional Basis:** C-051 (Resource Transparency), C-042 (Vocabulary Mandate — regional language fidelity), C-069 (Platform Self-Improvement — platform must use performance data to improve its own choices), ADR-024 (Token Economy), ADR-028 (Steward/Customer tier separation)

---

## Context

ADR-024 defined a four-layer token economy routing messages to LOCAL / MID_TIER / FRONTIER. ADR-028 added steward vs customer separation. Both ADRs implicitly assumed Azure OpenAI as the sole provider. The 2026-07-19 LLM API analysis identified four gaps in the single-provider assumption:

1. **DPDPA gap**: Azure UAE North is acceptable but Google Cloud Mumbai (`asia-south1`) gives stronger India data residency — data does not leave India.
2. **Regional language fidelity**: GPT-4o-mini underperforms on Hindi/Marathi/Telugu/Punjabi relative to Gemini 2.0 Flash and Sarvam AI for the Agricultural agent (C-042 Vocabulary Mandate).
3. **Cost**: Gemini 2.0 Flash (MID_TIER) and Gemini 2.5 Pro (FRONTIER) are 35-40% cheaper than GPT-4o-mini and GPT-4o at the same quality level, with better multilingual capability.
4. **Static routing is constitutionally insufficient**: C-069 requires the platform to improve itself using observed evidence. A platform that never adjusts its LLM provider choice based on performance data violates this obligation.

---

## Decision

### Decision 1: Provider Registry (replacing single-provider assumption)

A **Provider Registry** replaces the implicit `AZURE_OPENAI_*` environment variables. Each tier has a **primary provider** and an ordered **fallback chain**. The AI Runtime reads the active provider configuration at startup; provider switching does not require redeployment — only Key Vault updates.

```
LOCAL tier:
  primary:   ollama/llama3.2-3b            (self-hosted, ₹0, classification gate)
  secondary: ollama/ai4bharat-indic-bert    (self-hosted, ₹0, Indian language tasks)
  no fallback — LOCAL outage → queue, then ZERO_COST template

MID_TIER:
  primary:   google/gemini-2.0-flash        (Vertex AI asia-south1, Mumbai)
  secondary: sarvam/saaras                  (India-hosted, Agricultural agent override)
  fallback:  azure/gpt-4o-mini              (UAE North, circuit-breaker only)

FRONTIER:
  primary:   google/gemini-2.5-pro          (Vertex AI asia-south1, Mumbai)
  fallback:  azure/gpt-4o                   (UAE North, circuit-breaker only)
  never:     grok, claude-anthropic-direct, openai-direct  (DPDPA gap — US-only)
```

### Decision 2: Provider Selection Engine (conscious selection — C-069)

The AI Runtime hosts a **Provider Selection Engine** (PSE) that runs before every LLM dispatch. The PSE applies two layers in order:

#### Layer A — Rule Engine (deterministic, evaluated first, never skipped)

Rules are statically configured and run in priority order. A rule DENY removes a provider from the eligible set for that request.

| Rule ID | Condition | Effect |
|---|---|---|
| **PSE-R01** | Customer data contains PII AND provider has no India/UAE DPA | DENY provider |
| **PSE-R02** | `message_language` IN {hi, mr, te, ta, kn, pa, bn, gu} AND tier=MID_TIER | PREFER sarvam/saaras, then google/gemini-2.0-flash |
| **PSE-R03** | `plan_tier=essential` | DENY all FRONTIER providers |
| **PSE-R04** | `role=steward` | FORCE FRONTIER tier, FORCE primary provider (no fallback to non-FRONTIER) |
| **PSE-R05** | `record_type=CONSTITUTIONAL_DECISION` | FORCE FRONTIER + FORCE primary |
| **PSE-R06** | Provider's Key Vault secret is empty or expired | DENY provider |
| **PSE-R07** | Provider rate-limit response received in last 60s | DENY provider for 120s (circuit-breaker) |
| **PSE-R08** | Provider P99 latency > tier SLA (MID_TIER >2s, FRONTIER >8s) in last 10 min | SKIP provider, try next |

#### Layer B — Performance Engine (evidence-based ranking — C-069)

After rules filter eligible providers, the PSE ranks them by composite score computed from `institutional.provider_performance`:

```
composite_score = (success_rate × 0.50)
               + ((1 - normalised_latency_p99) × 0.25)
               + ((1 - normalised_cost_per_call) × 0.15)
               + (c049_escalation_rate_inverse × 0.10)
```

Where:
- `success_rate` = calls completed / calls attempted in last 1h window
- `normalised_latency_p99` = provider_p99 / tier_sla_ms (0.0 to 1.0)
- `normalised_cost_per_call` = provider_cost / max_tier_cost
- `c049_escalation_rate_inverse` = 1 - (c049_escalations_this_provider / total_calls)

Highest composite_score wins. In case of tie, prefer the DPDPA-primary provider (India-region first).

#### Layer C — Dispatch + Outcome Recording

After selection, the PSE:
1. Dispatches to the selected provider
2. Measures actual latency and outcome (success / rate-limit / error / timeout)
3. Writes to `institutional.provider_performance` (see ADR-029 schema section)
4. If dispatch fails → move to next in fallback chain → record fallback event
5. If all providers exhausted → C-049 escalation to customer + evidence record

### Decision 3: Agricultural Agent Sarvam Override

For the Agricultural agent, Sarvam AI is the MID_TIER **default** (not just preferred) when language is in the Indian regional set. This is a constitutional decision: C-042 Vocabulary Mandate requires regional fidelity as a LAW. Using a model demonstrably inferior for Hindi/Marathi violates C-042. Sarvam AI's MID_TIER PSE-R02 override is therefore constitutionally mandated, not just cost-optimal.

### Decision 4: AI4Bharat for LOCAL Tier Indian Language Classification

AI4Bharat IndicBERT and IndicNLP models run self-hosted via Ollama for:
- Message language detection (replaces locale header detection — more accurate for code-switched text like "bhaiya weather kya hai aaj ka")
- Agricultural skill C-042 vocabulary compliance check (does output use farmer-appropriate terms?)
- LOCAL classification gate for Indian-language inputs

Cost: ₹0 (open-source, self-hosted). DPDPA: best possible (on-premise).

### Decision 5: Provider Performance Visibility for Sujay via Steward Assistant

The Steward Assistant surfaces provider performance weekly to Sujay:
*"This week: Gemini 2.0 Flash success rate 99.2%, avg 87ms. Sarvam Saaras 98.7%, avg 103ms. Azure fallback was used 12 times (Gemini rate limit at 14:00 Tuesday). No DPDPA events."*

This closes the feedback loop: Sujay can instruct a provider change via chat, which triggers a Key Vault update (Tier 1 authorization).

---

## Provider Cost Summary (per ADR-029 decision)

| Tier | Provider | Cost/call (est.) | Data residency | Regional language |
|---|---|---|---|---|
| LOCAL | Ollama/Llama 3.2 3B | ₹0 | On-premise ✓✓ | Weak |
| LOCAL | Ollama/AI4Bharat IndicBERT | ₹0 | On-premise ✓✓ | ✓✓✓ India-specific |
| MID_TIER | Gemini 2.0 Flash (Mumbai) | ~₹0.07 | India ✓✓✓ | ✓✓ |
| MID_TIER | Sarvam Saaras (India) | ~₹0.05 | India ✓✓✓ | ✓✓✓ |
| MID_TIER fallback | Azure GPT-4o-mini (UAE) | ~₹0.12 | UAE ✓ | Good |
| FRONTIER | Gemini 2.5 Pro (Mumbai) | ~₹0.45 | India ✓✓✓ | ✓✓✓ |
| FRONTIER fallback | Azure GPT-4o (UAE) | ~₹0.75 | UAE ✓ | Good |

**Net cost saving at 1,000 customers vs. original single-provider plan: ~₹5,100/month (-40%)**

---

## New Environment Variables (Key Vault secrets — Founder Actions)

| Secret name | Value | Tier | Founder action |
|---|---|---|---|
| `GOOGLE_VERTEX_PROJECT_ID` | GCP project ID | MID + FRONTIER | FA-021: Create GCP project, enable Vertex AI API |
| `GOOGLE_VERTEX_REGION` | `asia-south1` | MID + FRONTIER | Set with FA-021 |
| `GOOGLE_VERTEX_SA_KEY` | Service account JSON key | MID + FRONTIER | FA-021 |
| `SARVAM_API_KEY` | Sarvam AI API key | MID (Agricultural) | FA-022: Register at sarvam.ai |
| `STEWARD_FRONTIER_MODEL` | `gemini-2.5-pro` | FRONTIER | Updated from gpt-4o |
| `MID_TIER_MODEL_PRIMARY` | `gemini-2.0-flash` | MID_TIER | Updated |
| `MID_TIER_MODEL_AGRI` | `sarvam-saaras-1.0` | MID_TIER (Agricultural) | FA-022 |
| `OLLAMA_INDIC_MODEL` | `ai4bharat/indic-bert` | LOCAL | Pulled in docker-compose |

All secrets stored in Azure Key Vault, read via `secretref:` pattern (ADR-014). Never in `.env` files or container images.

---

## Consequences

### Positive
- 40% AI inference cost reduction at scale
- DPDPA strongest-possible position (India-region primary for all LLM calls)
- C-042 Agricultural compliance improved: Sarvam/AI4Bharat for Indian regional languages
- Platform actively improves provider selection using evidence (C-069 compliant)
- Provider failures handled gracefully via fallback chain — no single point of failure
- Sujay can see provider performance via Steward Assistant — no blind spots

### Negative
- Two new GCP credentials to manage (Vertex AI service account)
- Sarvam AI is a smaller provider — SLA less robust than Azure/Google (mitigated by Azure fallback)
- AI4Bharat models require Ollama GPU for production quality (CPU-only is slower for embeddings)

### Neutral
- AZURE_OPENAI_* env vars retained for fallback — no migration cost for existing CI/CD
- Provider Selection Engine adds ~5ms to every LLM dispatch path (within ADR-024 budget — LOCAL classification gate absorbs this in the 100ms budget)

---

## Amendments to Existing ADRs

- **ADR-024:** Layer 2 (Model Tier Dispatch) gains a `provider` dimension alongside `tier`. The `minimum_model_tier` field in `professional.agent_prompts` is joined by `preferred_provider` (nullable — null means PSE chooses).
- **ADR-028:** `STEWARD_FRONTIER_MODEL` env var updated to `gemini-2.5-pro`. Fallback to `azure/gpt-4o` if Gemini unavailable.
- **ADR-009:** `institutional.provider_performance` table added to observability scope — provider metrics flow through OTel alongside infrastructure metrics.

---

## Founder Actions Required (new)

| ID | Action | Lead time | Blocks |
|---|---|---|---|
| **FA-021** | Create GCP project, enable Vertex AI API, create service account with `aiplatform.user` role, download SA key JSON | 2 hours | MID_TIER primary, FRONTIER primary |
| **FA-022** | Register at sarvam.ai, subscribe to Saaras API, get API key | 1 hour | Agricultural MID_TIER override |

---

## Amendment 2 (WC-149): Hosted model binding

**Status:** PROPOSED - FOUNDER APPROVAL PENDING (the Founder approved the approach in conversation; approval is recorded by merging the pull request that carries this amendment; the Enterprise Architect office is not invoked)
**Date:** 2026-11-22
**Work Contract:** [WC-149](../work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md), requirement WC149-R006
**Constitutional basis:** C-051 (Resource Transparency), C-059, C-063; ADR-042 (provider registry), ADR-046 (workload identity)
**Scope:** Decisions 1 to 5 above are unchanged. This amendment only defines how a hosted (MID_TIER or FRONTIER) model is identified when a governed inference binding names it.

### A2.1 Why

A governed inference binding identifies a model by a weight digest and a tokenizer digest. A hosted model has no weights or tokenizer files the platform can hash, so those digests cannot be computed. Without a rule, either hosted models could not be bound at all, or a placeholder hash would imply a verification that did not happen.

### A2.2 Decision

1. **Identity.** A hosted-model inference binding identifies the model by three values: `provider`, the pinned model identifier (for example the exact model name sent in the request) and `tokenizerFamily`. It does not claim weight or tokenizer bytes.
2. **Digest fields.** The binding's existing model and tokenizer digest fields hold the same value: the SHA-256 of the canonical JSON (sorted keys, no whitespace, UTF-8) of `{provider, model, tokenizerFamily}`. A change to any of the three values therefore changes the digest and requires a new binding.
3. **Provider-reported model as evidence.** On every call the adapter records the model name the provider returned as per-call evidence. A mismatch with the pinned identifier is evidence of provider alias drift. It is recorded and surfaced; it is not a blocking failure, because providers move aliases without notice and a blocking rule would stop service for a change the platform cannot prevent.
4. **Rates.** Input and output rates are set by the Founder and bound by `rate_digest`, as for any binding. The adapter never infers a rate from provider output.
5. **Endpoints.** A hosted binding endpoint must be on an allowlist of provider hosts: `api.sarvam.ai`, `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com`. A binding naming any other host is not admitted. Adding a host needs an amendment.
6. **Keys.** The provider key comes from the provider registry (WC-148) at call time, pinned to the active credential version. A key is never part of the binding, its digests or its evidence.
7. **Unchanged.** Ollama LOCAL bindings keep their weight and tokenizer digest rules. The Provider Selection Engine layers, the Sarvam agricultural override and the fallback chain of Decision 1 are unchanged.

### A2.3 Not decided here

This amendment does not select any provider or plan tier for any customer or agent, does not set any rate, and does not publish a binding. Publishing a binding and its approval evidence remains a separate Founder-approved act under WC-134.

### A2.4 Consequences

- Hosted adapters can be admitted to the governed generation binding without fabricated weight digests.
- Provider alias drift becomes visible in evidence instead of silent.
- The host allowlist bounds where a bound key can be sent, so a mistaken or malicious endpoint cannot receive a provider key.
- A pinned model that a provider retires fails at the provider and falls back through the existing chain; the platform does not substitute another model silently.
