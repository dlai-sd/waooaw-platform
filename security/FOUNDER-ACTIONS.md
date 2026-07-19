# WAOOAW Platform — Founder Action List

**Last Updated:** 2026-07-19
**Purpose:** Tracks all actions that require the Founder's direct involvement. No AI agent can complete these.

---

## Format

| ID | Action | Priority | Dependency | Effort | Status |
|---|---|---|---|---|---|
| FA-NNN | What to do | P0/P1/P2 | What it unlocks | Time estimate | PENDING / DONE |

---

## P0 — Before Any Live Customer

| ID | Action | What it unlocks | Effort | Status |
|---|---|---|---|---|
| **FA-001** | Create Cloudflare account + add waooaw.com domain + enable proxy mode for static assets (`_next/static/**`, `*.js`, `*.css`) | CDN — O-02 optimization; faster portal load for all users | 30 minutes | PENDING |
| **FA-002** | Meta Business Manager verification (upload business documents) | DMA Skill 11 (paid advertising agency model — ADR-026); WhatsApp Business API (WABA) | 2-4 weeks lead time | PENDING |
| **FA-003** | Create Azure OpenAI resource in **UAE North** region (not US East) + deploy gpt-4o and gpt-4o-mini models | **Fallback LLM** (ADR-029 fallback chain) — primary LLM is now Google Vertex AI (FA-021). Azure UAE North is circuit-breaker fallback only | 1 hour | PENDING |
| **FA-004** | ~~Designate Grievance Officer~~ — **DONE (partial):** Yogesh Khandge designated (yogesh.khandge@dlaisd.com). Remaining: set up grievance page on portal + ensure 30-day response SLA is documented in Privacy Policy | DPDPA compliance before commercial launch | 30 minutes | PARTIAL |
| **FA-005** | TRADING/EXECUTION/ESCALATION_DECISION — acknowledge that this is a BREAKING constitutional boundary before any trading agent goes live | Trading IB-009 implementation unblocked | Immediate | PENDING |
| **FA-006** | Google Ads MCC (My Client Center) account setup | DMA Skill 11 Google Ads management (ADR-026) | 1 day (self-serve) | PENDING |
| **FA-007** | Create WAOOAW Instagram + LinkedIn + Facebook + GBP accounts | Skill 14 (WAOOAW institutional self-marketing, FR-005) | 1 day | PENDING |
| **FA-021** | **Create GCP project + enable Vertex AI API + create Service Account key** — (1) console.cloud.google.com → New project: `waooaw-platform`. (2) APIs & Services → Enable `Vertex AI API`. (3) IAM → Service Accounts → create `waooaw-ai-runtime` with role `Vertex AI User`. (4) Keys → Create JSON key → download. (5) Add JSON content to Azure Key Vault secret `google-vertex-sa-key`; add project ID to `google-vertex-project-id`. | **Primary LLM for ALL agents** (ADR-029): Gemini 2.0 Flash (MID_TIER) + Gemini 2.5 Pro (FRONTIER + steward sessions) via Mumbai region (asia-south1). **DPDPA primary position. ~40% cost saving vs Azure-only plan.** | 2 hours (self-serve — free GCP tier sufficient to start) | **PENDING — DO FIRST** |
| **FA-022** | **Register at sarvam.ai + subscribe to Saaras API + add key to Key Vault** — (1) sarvam.ai → Sign up. (2) Subscribe to Saaras API plan (~₹0.05/call). (3) Copy API key → add to Azure Key Vault secret `sarvam-api-key`. | **Agricultural agent C-042 compliance** (ADR-029): Sarvam Saaras is the MID_TIER provider for Hindi/Marathi/Telugu/Punjabi/Kannada advisory. Without this, Suresh gets Gemini (Grade B regional language). With this, Grade A guaranteed for Vidarbha dialect and rural India vocabulary. | 1 hour (self-serve) | **PENDING — BEFORE AGRICULTURAL LAUNCH** |

## P1 — Before 50 Customers

| ID | Action | What it unlocks | Effort | Status |
|---|---|---|---|---|
| **FA-008** | Change PostgreSQL Flexible Server for **dev + QA** from `Standard_D2s_v3` → `Burstable B2s` in Azure portal | O-08: saves ₹2,000–4,000/month on dev/QA database | 15 minutes | PENDING |
| **FA-009** | WAOOAW WABA (WhatsApp Business Account) — apply after Meta BM is verified (FA-002) | DMA Skill 7 WhatsApp campaigns for customers | 1-2 weeks after FA-002 | PENDING |
| **FA-010** | Meta Business Partner status application — after FA-002 | DMA Skill 11 centralized ad account management (ADR-026) | 1-3 weeks after FA-002 | PENDING |
| **FA-011** | Zerodha Kite Connect developer account (₹2,000/month) | Trading Agent live broker integration | 1 day | PENDING |
| **FA-018** | Create **WAOOAW Facebook App** in Meta Business Manager (App ID + Secret → GitHub Secrets) | Portal social login: "Continue with Facebook" (Keycloak IDP); required for Suresh + rural Indian users who use FB not Google | 2 hours (after FA-002 Meta BM verified) | PENDING |
| **FA-019** | Create **Apple Developer account** (₹8,700/year) + generate SIWA Service ID + P8 private key | Portal social login: "Continue with Apple" for Dr. Mehta, Meera, and all iPhone users | 1 day (Apple review can take 24-48h) | PENDING |
| **FA-020** | Register **MSG91 DLT templates** (India TRAI Distributed Ledger Technology — mandatory for transactional SMS) + create MSG91 account | SMS OTP fallback when WhatsApp OTP fails (rural connectivity backup) | 2-3 days (DLT registration with TRAI) | PENDING |

## P1 — Video API Keys (₹~4,900/month total when activated)

| ID | Action | What it unlocks | Monthly cost | Status |
|---|---|---|---|---|
| **FA-012** | KLING_AI_API_KEY (Kling AI account) | DMA Skill 8 Track 1: Photo-to-Video Reels | ~$10 | PENDING |
| **FA-013** | HEYGEN_API_KEY (HeyGen account) | DMA Skill 8 Track 2: Digital Twin avatar | ~$29 | PENDING |
| **FA-014** | ELEVENLABS_API_KEY (ElevenLabs account) | DMA Skill 8 voice + Digital Twin audio | ~$5 | PENDING |
| **FA-015** | RUNWAYML_API_KEY (Runway ML account) | DMA Skill 8 Track 3: Generative brand video | ~$15 | PENDING |

## P2 — Decision Required

| ID | Action | What it unlocks | Decision needed | Status |
|---|---|---|---|---|
| **FA-016** | X (Twitter) API v2 Basic — $100/month | DMA X/Twitter posting capability | Is this worth $100/month before 50 customers? | PENDING |
| **FA-017** | LinkedIn Company Page for WAOOAW | Skill 14 LinkedIn presence; FA-007 completes this | Part of FA-007 | PENDING |

---

## Completed Actions

*(Move items here when done)*

---

## Notes

- **FA-002 (Meta BM) is the critical path item** — FA-009, FA-010, FA-018 all depend on it. Start immediately.
- **FA-021 (GCP Vertex AI) is now the primary LLM action** (ADR-029) — 2 hours, self-serve. Unlocks Gemini 2.0 Flash (MID_TIER) + Gemini 2.5 Pro (FRONTIER) as primary providers for ALL agents. 40% cost saving vs Azure-only. Do alongside FA-003 (Azure remains fallback).
- **FA-022 (Sarvam AI) is required before Agricultural launch** — 1 hour, self-serve. Without it, Agricultural agent uses Gemini (good but not Grade A for Marathi/Vidarbha dialect). With it, Grade A guaranteed.
- **FA-003 (Azure OpenAI UAE North)** still needed — it's the fallback chain for when Gemini has rate limits or outage. Do after FA-021.
- **FA-005 (Trading ESCALATION_DECISION)** is a 5-minute acknowledgment that unlocks the entire trading implementation sprint.
- **FA-018 (Facebook App)** depends on FA-002 (Meta BM verified). Do both together.
- **FA-019 (Apple Developer)** has no dependencies — can be done immediately. Unlocks Apple Sign In for Dr. Mehta + Meera (iPhone users).
- **FA-020 (MSG91 DLT)** has no dependencies — can be done immediately. Takes 2-3 days for TRAI approval. Unlocks SMS OTP fallback for rural users.
- All video API keys (FA-012 through FA-015) can wait until after the first 10 customers — no customer needs video in month 1.
- **Logo + brand colors** — Founder to provide directly. Unblocks brand color token population in `constitutional-ux-vocabulary.md`.
