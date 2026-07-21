# WAOOAW Platform — Founder Action List

**Last Updated:** 2026-07-21
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
| **FA-003** | Create Azure OpenAI resource in **UAE North** region (not US East) + deploy gpt-4o and gpt-4o-mini models | Fallback LLM chain when Vertex AI circuit-breaker fires (ADR-029) | 1 hour | PENDING |
| **FA-004** | ~~Designate Grievance Officer~~ — **DONE (partial):** Yogesh Khandge designated (yogesh.khandge@dlaisd.com). Remaining: set up grievance page on portal + ensure 30-day response SLA is documented in Privacy Policy | DPDPA compliance before commercial launch | 30 minutes | PARTIAL |
| **FA-005** | TRADING/EXECUTION/ESCALATION_DECISION — acknowledge that this is a BREAKING constitutional boundary before any trading agent goes live | Trading IB-009 implementation unblocked | Immediate | PENDING |
| **FA-006** | Google Ads MCC (My Client Center) account setup | DMA Skill 11 Google Ads management (ADR-026) | 1 day (self-serve) | PENDING |
| **FA-007** | Create WAOOAW Instagram + LinkedIn + Facebook + GBP accounts | Skill 14 (WAOOAW institutional self-marketing, FR-005) | 1 day | PENDING |
| **FA-021** | Create GCP project → enable Vertex AI API → create service account with `aiplatform.user` role → download SA key JSON → store in Azure Key Vault as `GOOGLE_VERTEX_SA_KEY` | **AI Runtime integration tests + test/demo env only.** NOT required for Sprint 011–014 (infrastructure, CE, BP, PR — all use mocks/stubs). Required from Sprint 015 (AI Runtime) onward when integration tests hit real LLM providers. Without it, AI Runtime runs LOCAL tier only (Ollama); customer agents stub responses. | 2 hours | PENDING |
| **FA-022** | Register at sarvam.ai → subscribe to Saaras API → store API key in Azure Key Vault as `SARVAM_API_KEY` | Agricultural agent Grade A regional language (Hindi/Marathi/Telugu). PSE-R02 override requires Sarvam for C-042 Vocabulary Mandate compliance. | 1 hour | PENDING |
| **FA-023** | Create GitHub App for autonomous PR review (C-065 SDLC Separation enforcement): Go to `github.com/settings/apps/new` → set permissions: `pull_requests:write`, `contents:read` → install on `dlai-sd/waooaw-platform` → generate installation token → store as `REVIEW_APP_TOKEN` GitHub Secret | **Autonomous Sprint Agent full C-065 compliance.** Without this, the autonomous reviewer runs in advisory mode only (posts comment, cannot formally approve). CODEOWNERS merge gate remains — this just adds the autonomous review approval layer. | 30 minutes | PENDING |

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
- **FA-003 (UAE North OpenAI) takes 1 hour** and saves ~55% LLM latency from day one — do alongside IB-009 kickoff.
- **FA-005 (Trading ESCALATION_DECISION)** is a 5-minute acknowledgment that unlocks the entire trading implementation sprint.
- **FA-018 (Facebook App)** depends on FA-002 (Meta BM verified). Do both together.
- **FA-019 (Apple Developer)** has no dependencies — can be done immediately. Unlocks Apple Sign In for Dr. Mehta + Meera (iPhone users).
- **FA-020 (MSG91 DLT)** has no dependencies — can be done immediately. Takes 2-3 days for TRAI approval. Unlocks SMS OTP fallback for rural users.
- All video API keys (FA-012 through FA-015) can wait until after the first 10 customers — no customer needs video in month 1.
- **Logo + brand colors** — Founder to provide directly. Unblocks brand color token population in `constitutional-ux-vocabulary.md`.
