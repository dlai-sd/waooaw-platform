# Skill Dependency Register

**Purpose:** Pre-simulation and pre-implementation checklist. Lists every Skill of every approved agent with its external dependencies, credential requirements, infrastructure needs, and Founder action items. Use this before any simulation run or IB-009 implementation sprint.

**Last Updated:** 2026-07-12 (v0.37.0)
**Constitutional Basis:** C-041 (tool calls governed by Decision Space); ADR-014 (secret management); ADR-020 (MCP integration pattern); ADR-021 (OAuth vault); ADR-023 (WhatsApp Phone Identity)

---

## Status Legend

| Symbol | Meaning |
|---|---|
| ✅ | Available — mocked in docker-compose OR documented as real credential |
| ⚠️ | Partial — exists in architecture but needs configuration or credential before live use |
| 🔴 | Founder action required — cannot proceed without external arrangement |
| 📋 | Design complete — no external dependency (platform-internal) |

---

## Agent 1: Digital Marketing Agent (DMA) v2.4

**Professional Type:** `DIGITAL_MARKETING_HEALTHCARE`
**Entry Channel:** Portal (web PWA)
**Credential Model:** OAuth via oauth-vault service (ADR-021)

### Skill 0 — Customer Profiling & Market Research

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `web-search-mcp` | External API (generic web search) | ✅ docker-compose stub | None — provider selection (SerpAPI/Brave) needs `.env` config before live |
| `google-places-mcp` | Google Places API | ⚠️ stub only | Google Cloud project + Places API key → GitHub Secret `GOOGLE_PLACES_API_KEY` |
| `social-profile-mcp` | Public social data | ✅ docker-compose stub | None for public data; rate limits vary by provider |
| `meta-ad-library-mcp` | Meta Ad Library API (public) | ✅ docker-compose stub | None — public API, no auth required |
| `web-scan-mcp` | Website signal scanning | ✅ docker-compose stub | None |
| `customer-profile-mcp` | Internal — Business Platform DB | 📋 internal | None |

### Skill 1 — Digital Maturity Report

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| Same MCPs as Skill 0 | — | See above | See above |

### Skills 2–3 — Content Strategy & Calendar / Content Creation

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `scheduling-mcp` | Internal scheduling service | ✅ docker-compose stub | None — internal |
| `image-generation-mcp` | AI image generation (DALL-E / Stable Diffusion) | ⚠️ stub only | **Provider decision + API key** → GitHub Secret `IMAGE_GENERATION_API_KEY`. OpenAI DALL-E 3 or Stability AI. Monthly cost estimate: ~₹2,000–₹8,000/month at MVI volume. |

### Skill 4 — Instagram Marketing

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `instagram-mcp` | Meta Graph API (Instagram Business) | ⚠️ oauth-vault configured | 🔴 **Meta Business Verification required.** App must be reviewed and approved for `instagram_basic`, `instagram_content_publish`, `pages_read_engagement` scopes. Requires: business documents, website, privacy policy. **Lead time: 2–4 weeks.** |
| Customer Instagram OAuth | Per-customer OAuth token | ⚠️ depends on Meta app | 🔴 Requires Meta app approval above first |
| `platform-analytics-mcp` | Internal analytics aggregator | ✅ docker-compose stub | None |

### Skill 5 — Facebook Presence Management

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `facebook-mcp` | Meta Graph API (Pages) | ⚠️ oauth-vault | 🔴 **Same Meta Business Verification as Skill 4** — same app, additional scopes: `pages_manage_posts`, `pages_manage_engagement` |
| Customer Facebook Page OAuth | Per-customer token | ⚠️ oauth-vault | 🔴 Requires Meta app approval |

### Skill 6 — Google Business Profile

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `google-business-mcp` | Google My Business API | ⚠️ stub only | 🔴 **Google Cloud project + My Business API enabled + OAuth consent screen verified.** Requires Google Business verification for the app. Lead time: 1–2 weeks. |
| Customer GBP OAuth | Per-customer token | ⚠️ oauth-vault | 🔴 Requires Google app above |

### Skill 7 — WhatsApp Business Engagement

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `whatsapp-business-mcp` | Meta WhatsApp Business API | ⚠️ stub only | 🔴 **WAOOAW WhatsApp Business Account (WABA) required.** Meta Business Manager → WhatsApp Business API → WABA number. Lead time: 1–2 weeks. **Cost: ~$0.005/message (BSP fees vary).** |
| Customer WABA credentials | Per-customer credential | ⚠️ oauth-vault | 🔴 Each DMA customer needs their own WABA. WAOOAW must guide them through Meta WABA verification. |
| HSM templates | Meta pre-approval | ⚠️ template design needed | 🔴 Each broadcast template requires Meta review. Lead time: 1–7 days per template. |

### Skill 8 — Video & Visual Content Creation

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `video-generation-mcp` | AI video generation — **DECIDED v0.48.0: Three-Track Architecture** | ⚠️ stub only | **Provider decision made. Four separate MCPs now specified:** |
| `image-to-video-mcp` | Kling AI 2.0 — Track 1 Photo-to-Video | ⚠️ stub only | 🔴 **KLING_AI_API_KEY required.** Self-serve at klingai.com. Approx $10/month for DMA MVI volume (~₹840/month). |
| `avatar-generation-mcp` | HeyGen 2.0 — Track 2 Digital Twin avatar | ⚠️ stub only | 🔴 **HEYGEN_API_KEY required.** Self-serve at heygen.com. Creator plan $29/month (~₹2,430). Covers 3 min avatar video/month — sufficient for MVI. |
| `voice-clone-mcp` | ElevenLabs Turbo v2 — Track 2 voice cloning | ⚠️ stub only | 🔴 **ELEVENLABS_API_KEY required.** Self-serve at elevenlabs.io. Starter plan $5/month (~₹420). 30,000 chars/month, voice cloning included. |
| `text-to-video-mcp` | Runway ML Gen-3 Alpha — Track 3 generative brand video | ⚠️ stub only | 🔴 **RUNWAYML_API_KEY required.** Self-serve at runwayml.com. Standard plan $15/month (~₹1,260). 625 credits = ~100 seconds of generated video. |

### Skill 9 — Performance Analytics

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `platform-analytics-mcp` | Internal | 📋 internal | None |

### Skills 10–11 — Local SEO + Paid Advertising

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `seo-mcp` | SEO data provider (Ahrefs / Semrush API) | ⚠️ stub only | 🔴 **Semrush or Ahrefs API access.** Semrush API: ~$100/month minimum. Ahrefs API: ~$82/month. Founder decision on provider. |
| `google-search-console-mcp` | Google Search Console API | ⚠️ stub only | 🔴 Same Google Cloud project as GBP. Additional OAuth scope: `webmasters.readonly`. Customer must verify their site in GSC. |
| `meta-ads-mcp` | Meta Ads API | ⚠️ oauth-vault | 🔴 **Meta Ads API access requires Meta Business Verification (same as Skill 4/5) + Ads API access level.** Standard Access requires volume justification. |
| `google-ads-mcp` | Google Ads API | ⚠️ stub only | 🔴 **Google Ads API developer token required.** Must apply via Google Ads manager account. Lead time: 1–2 weeks. Customer must link their Ads account. |

### Skills 12–13 — Conversion Optimisation + Competitive Intelligence

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `web-optimisation-mcp` | A/B testing (VWO / Optimizely API) | ⚠️ stub only | 🔴 **Provider decision.** VWO API: ~₹7,000/month minimum. Customer must install testing JS snippet. |
| `meta-ad-library-mcp` | Public Meta Ad Library | ✅ stub | None (public API) |

---

## Agent 2: Trading Agent v1.7

**Professional Type:** `TRADING_FO_CRYPTO`
**Entry Channel:** Portal (web PWA) — PAAS session
**Credential Model:** Broker API via oauth-vault (ADR-021)

### Skill 1 — SESSION_PREP (Pre-session analysis)

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `market-data-mcp` | NSE/BSE market data (Upstox / Zerodha / Angel One data API) | ⚠️ stub only | 🔴 **Broker data API subscription.** Upstox: free tier available (delayed). Real-time: ₹500–₹2,000/month. Founder decision on data provider tier. |
| `news-sentiment-mcp` | Financial news + sentiment (MoneyControl / Economic Times API) | ⚠️ stub only | 🔴 **No free public API for Indian financial news sentiment.** Options: web scraping (risk) or Refinitiv/Bloomberg (expensive). Founder decision needed. |

### Skill 2 — TRADE_SETUP (Intraday F&O strategy)

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `broker-api-mcp` | Broker order management (Zerodha Kite / Upstox v2) | ⚠️ oauth-vault | 🔴 **SEBI-registered broker API agreement required.** Zerodha Kite Connect: ₹2,000/month per developer account + customer must link their Zerodha account. **BREAKING PROMPT NOTE (acknowledged required): TRADING/EXECUTION/ESCALATION_DECISION is BREAKING type — Founder must explicitly acknowledge this prompt before Trading agent implementation begins.** |
| Customer broker OAuth token | Per-customer token | ⚠️ oauth-vault | 🔴 Customer connects their broker account via ADR-021 OAuth flow |

### Skill 3 — LOSS_LIMIT_ALERT (Risk management)

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `broker-api-mcp` (read positions) | Same as Skill 2 | ⚠️ | See Skill 2 |

### Skill 4 — SESSION_REPORT

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| Internal CAL + reasoning traces | 📋 internal | 📋 | None |

### Skill 5 — Crypto Advisory (if TRADING_FO_CRYPTO tier)

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `crypto-mcp` | CoinGecko API (read-only pricing) | ✅ stub — CoinGecko free tier | None for read-only. **Advisory only — no custody, no exchange connection.** |

### Trading Agent — Specific Founder Actions

| Item | Priority | Action |
|---|---|---|
| TRADING/EXECUTION/ESCALATION_DECISION prompt acknowledgment | **P0 — BLOCKING** | Founder must read the BREAKING prompt and explicitly acknowledge before any Trading IB-009 sprint begins |
| Broker API partner agreement (Zerodha Kite Connect) | P1 | Apply at developers.kite.trade — ₹2,000/month developer account |
| SEBI compliance review of PAAS model | P1 | Confirm PAAS advisory model does not require PMS registration |

---

## Agent 3: Agricultural Advisor v2.6

**Professional Type:** `AGRICULTURAL_ADVISOR_INDIA`
**Entry Channel:** WhatsApp (Phone Identity — ADR-023)
**Credential Model:** Phone Identity Service (port 8137); no OAuth per-customer

### Skill 1 — Weather Advisory

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `weather-ensemble-mcp` (Open-Meteo) | Open-Meteo API (free tier) | ✅ free API, no key required | None for Open-Meteo (free, no key). IMD district alerts need verification. |
| `weather-ensemble-mcp` (IMD district alerts) | India Meteorological Department | ⚠️ stub only | 🔴 **IMD API access.** IMD has a developer portal (mausam.imd.gov.in). Free but requires registration and API key → GitHub Secret `IMD_API_KEY`. |

### Skill 2 — Crop Health Monitoring

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `whatsapp-voice-mcp` | Meta WhatsApp Cloud API | ⚠️ depends on WABA | 🔴 **WAOOAW WABA number required** (same Meta Business Verification as DMA). Agricultural agent uses WAOOAW's own WABA (not customer's). Single WABA for all farmers. |
| TRAI opt-in compliance | Regulatory | ⚠️ architecture done | None — opt-in implemented in Phone Identity Service (ADR-023). But farmer UX onboarding flow needs testing. |
| ICAR crop disease database | Tier 1 RAG | ⚠️ content needed | 🔴 **ICAR database content licensing.** ICAR publications are public domain but structured database content (crop-disease matrices) may require ICAR collaboration. Founder decision: build from public ICAR PDFs vs. formal partnership. |

### Skill 3 — Mandi Price Intelligence

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| `agmarknet-mcp` | Agmarknet API (data.gov.in) | ✅ free public API — `api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070` | None — free public API. Needs `DATA_GOV_IN_API_KEY` (free registration). |
| `enam-mcp` | eNAM API | ⚠️ stub only | 🔴 **eNAM (National Agriculture Market) API registration required.** Free but requires trader/aggregator registration. Founder decision on entity type for registration. |

### Skill 4 — Crop Planning

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| NBSS&LUP soil data | Tier 1 RAG (static) | ⚠️ content loading needed | 🔴 **NBSS&LUP dataset access.** National Bureau of Soil Survey data is published but bulk access requires inquiry. Founder to initiate contact or use publicly available district-level summaries. |
| Government policy feed (MSP, subsidies) | Tier 1 RAG | ⚠️ content loading needed | 🔴 **Content pipeline for MSP updates.** `data.gov.in` has MSP data. Needs automated ingestion pipeline. Platform Engineering action, not Founder. |

### Skill 5 — Forward-Looking Hint System

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| All signal feeds (SIL Section 4.13) | See SIL above | See above | See above |

### Skill 6 — PMFBY Insurance Evidence

| Dependency | Type | Status | Founder Action Required |
|---|---|---|---|
| CAL evidence records | Internal | 📋 internal | None — fully internal |
| PMFBY digital claim portal integration | Optional | ⚠️ not yet designed | 🔴 **PMFBY portal API availability.** PMFBY has a portal but no published developer API. Founder inquiry to Ministry of Agriculture for data sharing agreement. **Low priority for MVI — evidence documents generated for farmer; manual upload to PMFBY portal.** |

### Agricultural Agent — WhatsApp WABA Items

| Item | Priority | Action |
|---|---|---|
| WAOOAW WABA number and Meta Business Verification | **P0 — blocks all 3 agents** | Single Meta Business Manager account covers DMA + Agricultural. Apply once. Lead time: 2–4 weeks. |
| 3 HSM templates for billing (UPI AutoPay mandate) | P1 | Templates designed in ADR-023. Requires WABA first, then Meta template submission. Lead time: 1–7 days each. |
| ADR-023 extension for WhatsApp Voice STT service | P1 | STT provider selection pending (Google Speech-to-Text vs. Azure Speech vs. Bhashini). ADR required before implementation. |
| Meta pre-approval for PROACTIVE_ALERT HSM templates (Section 4.13) | P1 | 3 templates declared in agent spec. Submit after WABA setup. |
| Bhashini API for regional language STT/TTS (optional — improves Marathi quality) | P2 | Bhashini is free (MeitY). Registration at bhashini.gov.in. `BHASHINI_API_KEY` → GitHub Secret. |

---

## Platform-Wide Dependency Summary

### Founder Action Required (P0 — Before Any Simulation or Implementation)

| # | Item | Agents Blocked | Lead Time | Cost |
|---|---|---|---|---|
| 1 | **Meta Business Manager verification** (covers Instagram, Facebook, WhatsApp, Ad Library) | DMA + Agricultural | 2–4 weeks | Free |
| 2 | **WAOOAW WhatsApp Business Account (WABA) number** | DMA + Agricultural | 1–2 weeks after #1 | $0.005/message |
| 3 | **TRADING/EXECUTION/ESCALATION_DECISION prompt acknowledgment** | Trading | Immediate — one sentence | None |
| 4 | **Meta Business Partner status** (required for multi-client ad management via WAOOAW MBM — ADR-026) | DMA Skill 11 Paid Advertising | 1–3 weeks after Meta BM verification (#1) | Free |
| 5 | **Google Ads Manager account (MCC)** + billing profile setup | DMA Skill 11 Paid Advertising | 1 day (Google self-serve) | Free to create; ad spend billed monthly |

### Founder Action Required (P1 — Before Live Deployment)

| # | Item | Agents | Cost |
|---|---|---|---|
| 6 | Zerodha Kite Connect developer API account | Trading | ₹2,000/month |
| 7 | IMD API key (free registration) | Agricultural | Free |
| 8 | eNAM registration for agmarknet-mcp | Agricultural | Free |
| 9 | Google Cloud project for Places + GBP + Search Console | DMA | ~₹0 (free tiers cover MVI) |
| 10 | ICAR content strategy decision (public PDFs vs. formal partnership) | Agricultural | Partnership: negotiation needed |
| 11 | NBSS&LUP soil data access | Agricultural | Free (public domain) |
| 12 | SEBI compliance review of PAAS advisory model | Trading | Legal cost (one-time) |
| **13** | **Video generation API keys — 4 self-serve signups (v0.48.0):** Kling AI (klingai.com ~$10/mo), HeyGen (heygen.com $29/mo), ElevenLabs (elevenlabs.io $5/mo), Runway ML (runwayml.com $15/mo) | **DMA Skill 8 — Three-Track Video** | **~$59/month (~₹5,000/month) total platform cost. Self-serve, no lead time.** |

### Platform Engineering Actions (Not Founder — Before Simulation)

| # | Item | Owner |
|---|---|---|
| A | Mock all stubs with realistic test data for docker-compose simulation | Runtime Professional |
| B | `data.gov.in` API key (free) + agmarknet-mcp realistic price data | Runtime Professional |
| C | MSP data ingestion pipeline from data.gov.in | Runtime Professional |
| D | Open-Meteo integration test (no key needed — free public API) | Runtime Professional |
| E | `waooaw-ads-manager` stub service in docker-compose (returns mock sub-account IDs) | Runtime Professional |

---

## DMA Skill 11 — Paid Advertising Dependency Detail (ADR-026 Model)

### WAOOAW_MANAGED Connection (Default — ADR-026)

| Dependency | Status | Founder Action | Cost |
|---|---|---|---|
| WAOOAW Meta Business Manager | ⚠️ Requires Meta BM verification (P0 item #1) | P0 — Founder submits for verification | Free |
| Meta Business Partner status | 🔴 Requires additional Meta review after BM verification | P0 item #4 above | Free |
| `WAOOAW_META_SYSTEM_USER_ACCESS_TOKEN` | 🔴 Created inside Meta BM after Partner status | Added to Azure Key Vault | Free |
| `waooaw-ads-manager` service | ⚠️ Spec complete; needs implementation | IB-009 implementation sprint | Dev cost |
| Google Ads Manager (MCC) account | 🔴 Founder creates MCC account | P0 item #5 above | Free |
| `WAOOAW_GOOGLE_ADS_MCC_DEVELOPER_TOKEN` | 🔴 Issued after MCC creation (Google review: 1-2 weeks) | Added to Azure Key Vault | Free |
| Ad Spend Wallet Razorpay flow | ⚠️ New payment type (AD_SPEND_TOPUP) — needs implementation | IB-009 implementation sprint | Razorpay 2% + GST on each topup |

### CUSTOMER_OWNED Connection (Alternative — PENDING_FOUNDER_AUTHORIZATION)

| Dependency | Status | Note |
|---|---|---|
| Per-customer Meta BM OAuth | 🔴 PENDING_FOUNDER_AUTHORIZATION | Declared in spec. Not built. Same as original ADR-021 model. |
| Per-customer Google Ads OAuth | 🔴 PENDING_FOUNDER_AUTHORIZATION | Declared in spec. Not built. |

---

## GitHub Secrets Required (Full Inventory)

| Secret Name | Service | Required For | Status |
|---|---|---|---|
| `META_APP_ID` | Meta Graph API | DMA (Instagram, Facebook, WhatsApp), Agricultural (WhatsApp) | 🔴 Needs Meta Business Verification |
| `META_APP_SECRET` | Meta Graph API | Same | 🔴 |
| `WAOOAW_META_SYSTEM_USER_ACCESS_TOKEN` | WAOOAW MBM (ADR-026) | DMA Skill 11 — centralized ad management | 🔴 Needs Meta Business Partner status |
| `WAOOAW_GOOGLE_ADS_MCC_DEVELOPER_TOKEN` | WAOOAW Google MCC (ADR-026) | DMA Skill 11 — centralized ad management | 🔴 Needs Google MCC + developer token approval |
| `GOOGLE_PLACES_API_KEY` | Google Places | DMA Skill 0 | 🔴 Needs Google Cloud project |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth | DMA (GBP, Search Console) | 🔴 |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth | Same | 🔴 |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads API | DMA Skill 11 | 🔴 Needs application |
| `ZERODHA_API_KEY` | Kite Connect | Trading | 🔴 Needs developer account |
| `ZERODHA_API_SECRET` | Kite Connect | Trading | 🔴 |
| `IMD_API_KEY` | IMD Weather | Agricultural | 🔴 Free, needs registration |
| `DATA_GOV_IN_API_KEY` | Agmarknet / data.gov.in | Agricultural | ⚠️ Free — register at data.gov.in |
| `IMAGE_GENERATION_API_KEY` | DALL-E or Stability AI | DMA Skill 3 static images | 🔴 Provider decision pending (separate from video MCPs) |
| `KLING_AI_API_KEY` | Kling AI 2.0 | DMA Skill 8 Track 1 — Photo-to-Video | 🔴 Self-serve at klingai.com. ~$10/month. |
| `HEYGEN_API_KEY` | HeyGen 2.0 | DMA Skill 8 Track 2 — Digital Twin avatar | 🔴 Self-serve at heygen.com. $29/month (Creator plan). |
| `ELEVENLABS_API_KEY` | ElevenLabs Turbo v2 | DMA Skill 8 Track 2 — Voice cloning | 🔴 Self-serve at elevenlabs.io. $5/month (Starter plan). |
| `RUNWAYML_API_KEY` | Runway ML Gen-3 Alpha | DMA Skill 8 Track 3 — Generative brand video | 🔴 Self-serve at runwayml.com. $15/month (Standard plan). |
| `SEO_API_KEY` | Semrush or Ahrefs | DMA Skill 10 | 🔴 Provider decision pending |
| `BHASHINI_API_KEY` | Bhashini STT/TTS | Agricultural (optional) | ⚠️ Free — bhashini.gov.in |
| `AZURE_KEY_VAULT_URL` | Azure Key Vault (ADR-014) | All agents (cloud env) | ⚠️ Azure subscription required |
| `TEMPORAL_CLOUD_CLIENT_CERT` | Temporal Cloud mTLS | All agents (prod) | 🔴 Temporal Cloud account |
| `TEMPORAL_CLOUD_CLIENT_KEY` | Temporal Cloud mTLS | All agents (prod) | 🔴 |
| `RAZORPAY_KEY_ID` | Razorpay (ADR-022) | All agents billing | 🔴 Razorpay production account |
| `RAZORPAY_KEY_SECRET` | Razorpay | All agents billing | 🔴 |

**For simulation runs (docker-compose):** Only `DATA_GOV_IN_API_KEY` (free) and `IMD_API_KEY` (free) are needed for realistic data. All other MCPs run with mocked responses from docker-compose stubs. No paid credentials required for simulation.
