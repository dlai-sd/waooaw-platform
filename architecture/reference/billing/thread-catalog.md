# Thread Catalog — WAOOAW Platform Provider Cost Reference

**Authority:** Chief Business Architect (INST-003) — GOAL-004 D-06
**Constitutional Basis:** C-091 (Thread Catalog Sovereignty)
**Status:** APPROVED — 2026-07-30
**Founder Authorization Required:** Yes — per C-091, all entries require Founder Action before activation
**Review Frequency:** Quarterly or on provider price change (whichever comes first)
**FX Baseline:** USD/INR = 87.00 (2026-07-30 RBI reference rate + 5% FX buffer)

---

## How to Read This Catalog

Each thread has three cost layers:
- **Raw cost**: what WAOOAW actually pays the provider (pre-markup)
- **Markup components**: FX buffer + operational overhead + risk premium
- **Marked-up cost**: what WBE uses in bundle cost floor calculations

All amounts in INR paise (1 paise = ₹0.01). Marked-up cost = raw × (1 + total_markup_pct).

---

## Platform Threads (shared across all agents)

### LLM Threads

| thread_id | Provider | Model | Unit | Raw cost (INR paise) | FX buffer % | Ops overhead % | Risk premium % | Total markup % | Marked-up cost (paise) |
|---|---|---|---|---|---|---|---|---|---|
| `llm_local` | Self-hosted (Ollama) | llama3.2-3b / AI4Bharat IndicBERT | Per message classified | 0 | 0% | 0% | 0% | 0% | 0 |
| `llm_mid_gemini` | Google Vertex AI | Gemini 2.0 Flash | Per 1K tokens (in+out) | 2 | 5% | 8% | 3% | 16% | 3 |
| `llm_mid_sarvam` | Sarvam AI | Saaras | Per 1K tokens | 2 | 0% | 8% | 5% | 13% | 3 |
| `llm_frontier_gemini` | Google Vertex AI | Gemini 2.5 Pro | Per 1K tokens (in+out) | 18 | 5% | 8% | 3% | 16% | 21 |
| `llm_frontier_gpt4o` | Azure OpenAI UAE | GPT-4o | Per 1K tokens | 22 | 0% | 8% | 5% | 13% | 25 |

**Notes:**
- `llm_local` is zero-cost (self-hosted). Included in catalog for completeness; not included in bundle cost floor calculations.
- `llm_mid_sarvam` is the preferred MID_TIER provider for Indian-language messages (PSE-R02, ADR-029). Bundle cost floors use `llm_mid_gemini` as the standard rate; Sarvam is same price so no floor adjustment needed.
- `llm_frontier_gpt4o` is the fallback (circuit-breaker only, ADR-029). Bundle cost floors use `llm_frontier_gemini` as primary.
- Token count for bundle ration purposes: each "LLM call" counted as 2,000 tokens average for MID_TIER; 6,000 tokens average for FRONTIER (based on observed usage in WC-012 through WC-015 sessions).

### WhatsApp Thread

| thread_id | Provider | Unit | Raw cost (paise) | FX buffer | Ops overhead | Risk premium | Total markup | Marked-up cost |
|---|---|---|---|---|---|---|---|---|
| `whatsapp_window` | Exotel / 360Dialog (BSP) | Per 24-hour conversation window | 60 | 0% | 17% | 0% | 17% | 70 |

**Notes:**
- WhatsApp BSP charges are INR-billed — no FX buffer needed.
- One "window" = one 24-hour conversation session initiated by customer message. Multiple messages in same window = one charge.
- Risk premium 0% — BSP pricing is predictable.
- The 17% ops overhead covers: webhook infrastructure, HMAC validation, message routing (ADR-023).

### Infrastructure Thread (Shared Overhead)

| thread_id | Component | Unit | Monthly cost per customer | Markup | Monthly marked-up per customer |
|---|---|---|---|---|---|
| `infra_share` | Azure Container Apps + PostgreSQL + Redis + Keycloak | Per active customer/month (amortised) | 15,000 paise (₹150) | 20% (admin overhead) | 18,000 paise (₹180) |

**Notes:**
- Infrastructure share is a fixed monthly amount per active customer (not per-request).
- Derived from: total Azure dev infrastructure cost ÷ projected active customer count.
- At 10 customers: ₹180/customer. At 100 customers: ₹50/customer (economies of scale — review quarterly).
- Current baseline assumes 10-customer pilot. Recalculate at 25-customer milestone.

---

## DMA-Specific Threads

| thread_id | Provider | Unit | Raw cost (paise) | FX buffer | Ops overhead | Risk premium | Total markup | Marked-up cost |
|---|---|---|---|---|---|---|---|---|
| `video_kling_clip` | Kling AI (FA-012) | Per 5-second video clip | 1,500 | 5% | 5% | 5% | 15% | 1,725 |
| `video_heygen_minute` | HeyGen (FA-013) | Per minute of avatar video | 1,250 | 5% | 5% | 5% | 15% | 1,438 |
| `video_heygen_monthly` | HeyGen (FA-013) | Monthly platform subscription (1 seat) | 250,000 | 5% | 5% | 0% | 10% | 275,000 |
| `voice_elevenlabs_monthly` | ElevenLabs (FA-014) | Monthly subscription (Starter — 30K chars) | 50,000 | 5% | 5% | 0% | 10% | 55,000 |
| `video_runway_credit` | Runway ML (FA-015) | Per generation credit (~5 second clip) | 2,500 | 5% | 5% | 5% | 15% | 2,875 |
| `image_gen_per_image` | Kling AI / Stable Diffusion | Per image | 200 | 5% | 5% | 5% | 15% | 230 |

**Notes:**
- Video generation providers (FA-012 through FA-015): all pending Founder Actions for account setup. Cost data from publicly listed pricing, FX at 87.00.
- `video_heygen_monthly` and `voice_elevenlabs_monthly` are platform subscriptions — amortised across all customers using video/voice in that period. If 10 DMA Runner customers use video this month, HeyGen subscription cost = ₹2,750 ÷ 10 = ₹275/customer.
- `video_kling_clip` is the primary video thread for social media Reels (Starter/Runner bundles). Each clip = 1 bundle ration unit.
- `video_runway_credit` is for premium video quality (Winner bundle / top-up only).

### DMA Ad Spend Threads

| thread_id | Provider | Unit | Treatment |
|---|---|---|---|
| `ad_spend_meta` | Meta Ads (WAOOAW MBM) | INR paise (pass-through) | NOT in cost floor — customer's money, not WAOOAW's cost |
| `ad_spend_google` | Google Ads (WAOOAW MCC) | INR paise (pass-through) | NOT in cost floor — customer's money, not WAOOAW's cost |
| `ad_mgmt_fee_meta` | WAOOAW management fee | 10% of gross Meta spend | Revenue item — not a cost |
| `ad_mgmt_fee_google` | WAOOAW management fee | 10% of gross Google spend | Revenue item — not a cost |

**Notes:** Ad spend is ALWAYS customer's money (C-056). It is NOT a WAOOAW cost and does NOT appear in the bundle cost floor. The management fee is WAOOAW revenue, not a cost. These entries exist in the Thread Catalog for completeness and transparency reporting only.

---

## Trading-Specific Threads

| thread_id | Provider | Unit | Raw cost (paise) | Markup | Marked-up |
|---|---|---|---|---|---|
| `market_data_zerodha` | Zerodha Kite Connect (FA-011) | Monthly subscription (₹2,000 + GST) | 200,000 | 10% | 220,000 |
| `market_data_zerodha_call` | Zerodha Kite Connect | Per API call (amortised at 10K calls/month) | 20 | 10% | 22 |
| `charting_per_chart` | TradingView / in-house | Per chart render | 50 | 15% | 58 |

---

## Agricultural Advisor-Specific Threads

| thread_id | Provider | Unit | Raw cost (paise) | Markup | Marked-up |
|---|---|---|---|---|---|
| `climate_data_imd` | India Meteorological Dept (free API) | Per call | 0 | 0% | 0 |
| `crop_prices_agmarknet` | Agmarknet (free govt. portal) | Per query | 0 | 0% | 0 |
| `scheme_data_pm_kisan` | PM-KISAN / NABARD (free) | Per query | 0 | 0% | 0 |
| `soil_data_icar` | ICAR (free govt. portal) | Per query | 0 | 0% | 0 |

**Notes:** The Agricultural Advisor agent has zero agent-specific thread cost — all data sources are free government portals. This makes it the highest-margin agent at any bundle tier. The entire cost for Agricultural customers is platform threads (LLM + WhatsApp + infrastructure).

---

## Private Tutor-Specific Threads

| thread_id | Provider | Unit | Raw cost (paise) | Markup | Marked-up |
|---|---|---|---|---|---|
| `syllabus_cbse` | CBSE (public data, scrape/maintain) | Monthly maintenance cost (amortised) | 500 | 10% | 550 |
| `syllabus_state_boards` | State board portals (public) | Monthly maintenance (amortised) | 1,000 | 10% | 1,100 |
| `image_whiteboard` | In-house / Stable Diffusion | Per whiteboard diagram render | 200 | 15% | 230 |

---

## Thread Catalog Version History

| Version | Date | Change | Authorized By |
|---|---|---|---|
| v1.0 | 2026-07-30 | Initial Thread Catalog — GOAL-004 D-06 | Yogesh Khandge (Founder) |
