# WAOOAW Platform — Founder Action List

**Last Updated:** 2026-07-13
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
| **FA-003** | Create Azure OpenAI resource in **UAE North** region (not US East) + deploy gpt-4o and gpt-4o-mini models | O-10 LLM latency optimization: 180ms → 80ms for all LLM calls | 1 hour | PENDING |
| **FA-004** | Designate yourself as WAOOAW **Grievance Officer** (DPDPA India 2023 mandatory) + set up security@waooaw.com email | DPDPA compliance before commercial launch | 30 minutes | PENDING |
| **FA-005** | TRADING/EXECUTION/ESCALATION_DECISION — acknowledge that this is a BREAKING constitutional boundary before any trading agent goes live | Trading IB-009 implementation unblocked | Immediate | PENDING |
| **FA-006** | Google Ads MCC (My Client Center) account setup | DMA Skill 11 Google Ads management (ADR-026) | 1 day (self-serve) | PENDING |
| **FA-007** | Create WAOOAW Instagram + LinkedIn + Facebook + GBP accounts | Skill 14 (WAOOAW institutional self-marketing, FR-005) | 1 day | PENDING |

## P1 — Before 50 Customers

| ID | Action | What it unlocks | Effort | Status |
|---|---|---|---|---|
| **FA-008** | Change PostgreSQL Flexible Server for **dev + QA** from `Standard_D2s_v3` → `Burstable B2s` in Azure portal | O-08: saves ₹2,000–4,000/month on dev/QA database | 15 minutes | PENDING |
| **FA-009** | WAOOAW WABA (WhatsApp Business Account) — apply after Meta BM is verified (FA-002) | DMA Skill 7 WhatsApp campaigns for customers | 1-2 weeks after FA-002 | PENDING |
| **FA-010** | Meta Business Partner status application — after FA-002 | DMA Skill 11 centralized ad account management (ADR-026) | 1-3 weeks after FA-002 | PENDING |
| **FA-011** | Zerodha Kite Connect developer account (₹2,000/month) | Trading Agent live broker integration | 1 day | PENDING |

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

- **FA-002 (Meta BM) is the critical path item** — FA-009, FA-010 depend on it. Start immediately.
- **FA-003 (UAE North OpenAI) takes 1 hour** and saves ~55% LLM latency from day one — do alongside IB-009 kickoff.
- **FA-005 (Trading ESCALATION_DECISION)** is a 5-minute acknowledgment that unlocks the entire trading implementation sprint.
- All video API keys (FA-012 through FA-015) can wait until after the first 10 customers — no customer needs video in month 1.
