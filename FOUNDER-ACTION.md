# FOUNDER ACTION CHECKLIST

**Owner:** Yogesh Khandge (Founder)
**Last Updated:** 2026-07-23
**Purpose:** Single source of truth for every action only Yogesh can take.
No AI agent can complete any item on this list.
Items are in strict execution priority order — top item unblocks the most.

---

## How to use this

Work top to bottom. Each item tells you exactly:
- What to click / where to go
- What credential or key you will produce
- Where to store it
- What milestone it unblocks

Move the Status from `⬜ PENDING` → `✅ DONE` when complete.

---

## TIER 0 — Autonomous Sprint Start (blocks ALL code execution)

These 5 items must be done before the first autonomous GitHub Actions sprint can fire.
They are configuration, not external approvals. Each takes < 60 minutes.

| # | Action | Exact steps | What you produce | Where it goes | Unblocks | Time | Status |
|---|---|---|---|---|---|---|---|
| **T0-1** | **Anthropic API Key** (Claude Sonnet 4.6 autonomous execution) | Used personal Anthropic account (yogesh personal) — $25 credits already available. Created key `waooaw-dev-sprint`. Key stored in **Azure Key Vault** as `ANTHROPIC-API-KEY` (not GitHub Secret — ADR-014 OIDC pattern). | Stored in `waooaw-dev-kv` → `ANTHROPIC-API-KEY` | Azure Key Vault → fetched at runtime by workflow via OIDC | Autonomous sprint agent can use Claude Sonnet 4.6 | Done | ✅ DONE 2026-07-23 |
| **T0-2** | **Azure Service Principal** (Terraform + CI/CD deployment) | ✅ Completed 2026-07-23. Used OIDC (no client secret stored). App Registration: `waooaw-platform-sp`. Federated credentials for `main` branch + PRs. Contributor role granted on subscription. Key Vault access granted. | Tenant: `0471534c-1bbe-40ab-ae65-3f721b62582c` · Subscription: `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84` · Client ID: `ccd13909-d004-4340-aa26-990a00bed9c0` | GitHub Variables (not Secrets): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_KEYVAULT_NAME` — all set | Terraform apply (M1), CI/CD, blue-green deploy, Key Vault secret fetch | Done | ✅ DONE 2026-07-23 |
| **T0-3** | **Flip platform_phase to IMPLEMENTATION** | ✅ Authorized 2026-07-23 18:00 IST. Yogesh said: "Yogesh authorizes IB-009 Sprint 011 implementation". Flags flipped: `platform_phase=IMPLEMENTATION`, `autonomous_halt=false`. Sprint dispatch triggered. | Committed to PROJECT_STATE.md | GitHub | WC-011 execution begins | Done | ✅ DONE 2026-07-23 |
| **T0-4** | **GitHub App for autonomous PR review** (FA-023) | ✅ Completed 2026-07-23. App: `waooaw-reviewer`. App ID: `4372447`. Installation ID: `148479218`. Private key generated and stored in Key Vault. | All three stored in `waooaw-dev-kv`: `GH-APP-ID`, `GH-APP-INSTALLATION-ID`, `GH-APP-PRIVATE-KEY` | Azure Key Vault → fetched at runtime by review job via OIDC | Autonomous reviewer can post binding Grade A/F review (C-065 SDLC separation) | Done | ✅ DONE 2026-07-23 |
| **T0-5** | **Codecov token** (C-076 90% coverage gate) | ✅ Completed 2026-07-23. Signed in via GitHub, added `dlai-sd/waooaw-platform`, copied token. | Stored in `waooaw-dev-kv` → `CODECOV-TOKEN` | Azure Key Vault → fetched at runtime by CI | PRs blocked if coverage drops below 90% (C-076) | Done | ✅ DONE 2026-07-23 |

---

## TIER 1 — External Credentials (long lead times — start in parallel with TIER 0)

| # | FA | Action | What you produce | Where it goes | Unblocks | Lead time | Status |
|---|---|---|---|---|---|---|---|
| **T1-1** | FA-002 | **Meta Business Manager verification** — go to [business.facebook.com](https://business.facebook.com) → Create Business account under "DLAI Satellite Data (OPC) Pvt Ltd" → Submit verification: upload GST certificate (27AAKCD8188R1ZH) + CIN (U62090PN2024OPC230499) → Submit | Meta Business Manager ID (numeric) | Noted in this file, Status → DONE | FA-009 (WABA), FA-010 (Meta Business Partner), FA-018 (Facebook App), DMA Instagram posting, WhatsApp for all agents | **2–4 weeks (start TODAY)** | ⬜ PENDING |
| **T1-2** | FA-021 | **GCP Vertex AI service account key** — go to [console.cloud.google.com](https://console.cloud.google.com) → Create project `waooaw-platform` → Enable Vertex AI API → IAM → Create service account: `waooaw-vertex-sa` with role `Vertex AI User` → Keys → Add Key → JSON → download | SA key JSON file | 1. Azure Portal → Key Vault (dev) → Secrets → `GOOGLE_VERTEX_SA_KEY` → upload JSON content · 2. GitHub Secrets → `GCP_SA_KEY` → paste JSON | AI Runtime real Gemini 2.0 Flash inference (Sprint 015) — without this, agents run Ollama LOCAL only | 2 hours | ✅ DONE — 2026-07-24 (GOOGLE-VERTEX-SA-KEY confirmed in waooaw-dev-kv) |
| **T1-3** | FA-022 | **Sarvam AI API key** — go to [sarvam.ai](https://www.sarvam.ai) → Create account → API Keys → Create key named `waooaw-agricultural` | `SARVAM_API_KEY = sarvam-...` | Azure Key Vault (dev) → `SARVAM_API_KEY` · GitHub Secrets → `SARVAM_API_KEY` | Agricultural agent Grade A Marathi/Hindi advisory (C-042 Vocabulary Mandate compliance, PSE-R02 override) | 1 hour | ✅ DONE — 2026-07-24 (SARVAM-API-KEY confirmed in waooaw-dev-kv) |
| **T1-4** | FA-003 | **Azure OpenAI resource (UAE North)** — Azure Portal → Create resource → Azure OpenAI → Region: **UAE North** (not US East) → Deploy models: `gpt-4o` and `gpt-4o-mini` → copy endpoint + key | `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_KEY` | GitHub Secrets (both names above) | LLM fallback chain when Gemini circuit-breaker fires (ADR-029 PSE-R08) | 1 hour | ⬜ PENDING |
| **T1-5** | FA-005 | **Trading ESCALATION_DECISION acknowledgment** — reply "I acknowledge TRADING/EXECUTION/ESCALATION_DECISION is a BREAKING constitutional boundary and authorize Trading agent implementation" in the relevant GitHub Issue or in this chat | Written acknowledgment | Noted in this file + GitHub Issue | Trading Agent implementation sprint (WC-013b Trading track) unblocked | **5 min** | ⬜ PENDING |

---

## TIER 2 — Pilot Launch Prerequisites (needed before first customer, < 2 week lead time)

| # | FA | Action | What you produce | Where it goes | Unblocks | Lead time | Status |
|---|---|---|---|---|---|---|---|
| **T2-1** | FA-009 | **WAOOAW WABA** — after FA-002 is verified: [business.facebook.com](https://business.facebook.com) → WhatsApp → Add phone number → register WAOOAW dedicated WABA number (not your personal number) | WABA Phone Number ID + WABA Access Token | GitHub Secrets: `WHATSAPP_PHONE_NUMBER_ID` + `WHATSAPP_ACCESS_TOKEN` | Agricultural WhatsApp delivery, DMA WhatsApp campaigns, customer onboarding via WhatsApp | 1–2 weeks after FA-002 | ⬜ PENDING (blocked on FA-002) |
| **T2-2** | FA-018 | **Facebook App** — after FA-002: [developers.facebook.com](https://developers.facebook.com) → Create App → Business → name: `WAOOAW Platform` → Add Facebook Login product → copy App ID + App Secret | `FACEBOOK_APP_ID` + `FACEBOOK_APP_SECRET` | GitHub Secrets: both | Portal "Continue with Facebook" login (Keycloak IDP), rural Indian users | 2 hours after FA-002 | ⬜ PENDING (blocked on FA-002) |
| **T2-3** | FA-019 | **Apple Developer Account** — [developer.apple.com](https://developer.apple.com) → Enroll → Individual → ₹8,700/year · After enrollment: Certificates → Sign In with Apple Service ID → create `com.waooaw.signin` → download P8 key | P8 private key file + Key ID + Team ID | GitHub Secrets: `APPLE_P8_KEY`, `APPLE_KEY_ID`, `APPLE_TEAM_ID` | Portal "Continue with Apple" (iPhone users — Dr. Mehta, Meera) | 1–2 days | ⬜ PENDING |
| **T2-4** | FA-020 | **MSG91 DLT SMS registration** — go to [msg91.com](https://msg91.com) → Create account → DLT Registration → Register under DLAI Satellite Data with TRAI → create template: "Your WAOOAW OTP is {#var#}. Valid for 10 minutes." | DLT Template ID + MSG91 Auth Key | GitHub Secrets: `MSG91_AUTH_KEY` + `MSG91_DLT_TEMPLATE_ID` | SMS OTP fallback for rural users when WhatsApp OTP fails | 2–3 days (TRAI approval) | ⬜ PENDING |
| **T2-5** | FA-011 | **Zerodha Kite Connect developer account** — go to [kite.trade/developer](https://kite.trade/developer) → Create app → ₹2,000/month subscription → copy API Key + API Secret | `ZERODHA_API_KEY` + `ZERODHA_API_SECRET` | GitHub Secrets: both | Trading Agent live broker integration | 1 day | ⬜ PENDING |
| **T2-6** | — | **Razorpay live mode** — Razorpay Dashboard → Settings → Switch to Live mode → complete KYC (GSTIN 27AAKCD8188R1ZH + bank account) → copy Live Key ID + Key Secret | `RAZORPAY_KEY_ID` + `RAZORPAY_KEY_SECRET` (live, not test) | GitHub Secrets: both (replace existing test values) | First real customer payment (Milestone M18) | 1–2 days (KYC verification) | ⬜ PENDING |

---

## TIER 3 — Post-Pilot / Scale (before 50 customers)

| # | FA | Action | Unblocks | Lead time | Status |
|---|---|---|---|---|---|
| **T3-1** | FA-006 | Google Ads MCC — [ads.google.com/home/tools/manager-accounts](https://ads.google.com/home/tools/manager-accounts) → Create Manager Account → 15 min self-serve | DMA Skill 11 Google Ads management | Same day | ⬜ PENDING |
| **T3-2** | FA-007 | Create WAOOAW Instagram + LinkedIn + Facebook Page + Google Business Profile accounts | Skill 14 WAOOAW institutional self-marketing (FR-005 stat gate: 50+ customers) | 1 day | ⬜ PENDING |
| **T3-3** | FA-010 | Meta Business Partner status — apply after FA-002 verified + 90 days activity | DMA centralized ad account management (ADR-026 agency model) | 1–3 weeks after FA-002 | ⬜ PENDING |
| **T3-4** | FA-001 | Cloudflare account + add waooaw.com → enable proxy for `_next/static/**` | CDN — faster portal load | 30 min | ⬜ PENDING |
| **T3-5** | FA-012 | Kling AI API key (klingai.com) → GitHub Secret: `KLING_AI_API_KEY` | DMA Skill 8 Photo-to-Video Reels (~$10/month) | 30 min | ⬜ PENDING |
| **T3-6** | FA-013 | HeyGen API key (heygen.com) → GitHub Secret: `HEYGEN_API_KEY` | DMA Skill 8 Digital Twin avatar (~$29/month) | 30 min | ⬜ PENDING |
| **T3-7** | FA-014 | ElevenLabs API key (elevenlabs.io) → GitHub Secret: `ELEVENLABS_API_KEY` | DMA Skill 8 voice synthesis (~$5/month) | 30 min | ⬜ PENDING |
| **T3-8** | FA-015 | Runway ML API key (runwayml.com) → GitHub Secret: `RUNWAYML_API_KEY` | DMA Skill 8 generative brand video (~$15/month) | 30 min | ⬜ PENDING |
| **T3-9** | FA-016 | X (Twitter) API v2 Basic — $100/month. **Decision required:** worth it before 50 customers? | DMA X/Twitter posting | 1 day | ⬜ DECISION NEEDED |

---

## Summary — Current Status (2026-07-23)

```
COMPLETED TODAY (2026-07-23):
  ✅ T0-1  Anthropic API key in Key Vault (personal account, $25 credits)
  ✅ T0-2  Azure account + resource group + Key Vault + App Registration + OIDC
  ✅ T0-4  GitHub App waooaw-reviewer (App ID: 4372447, Installation: 148479218)
  ✅ T0-5  Codecov token in Key Vault
  ✅       GitHub Variables: AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID, AZURE_KEYVAULT_NAME
  ✅       Sprint Dashboard: Issue #7 live — monitor at github.com/dlai-sd/waooaw-platform/issues/7

ONE REMAINING ACTION TO START CODING:
  ⬜ T0-3  Say: 'Yogesh authorizes IB-009 Sprint 011 implementation' → sprint fires in ≤6 hours

NEXT 48 HOURS (do in parallel with waiting for sprint to fire):
  ⬜ T1-1  Submit Meta BM verification  → 30 min → START TODAY (2-4 week clock)
  ⬜ T1-2  GCP Vertex AI SA key        → 2 hours → Real Gemini inference (Sprint 015)
  ⬜ T1-3  Sarvam AI API key           → 1 hour  → Agricultural Grade A
  ⬜ T1-4  Azure OpenAI UAE North      → 1 hour  → LLM fallback chain
  ⬜ T1-5  Trading ESCALATION ack      → 5 min   → Trading sprint unblocked

AFTER META BM VERIFIES (2-4 weeks):
  ⬜ T2-1  WABA registration
  ⬜ T2-2  Facebook App
  ⬜ T2-5  Zerodha Kite Connect
  ⬜ T2-6  Razorpay live mode
```

---

## Cost Reference (per session budget tracking, C-077)

| Budget item | Monthly ceiling | Expected spend |
|---|---|---|
| Anthropic API (Claude Sonnet 4.6) | ₹2,940 (set as $35 limit in console) | ₹150–₹600 during active sprints |
| GitHub Copilot Business (1 user) | ₹1,596 | ₹1,596 fixed |
| Azure dev infrastructure (C-067) | ₹10,000 | ₹6,000–₹8,000 |
| Azure QA infrastructure (C-067) | ₹10,000 | ₹6,000–₹8,000 |
| Total dev tooling (C-077 scope) | **₹5,000** | **₹1,746–₹2,196** |
