# WAOOAW Platform — Founder Action List

**Last Updated:** 2026-08-12
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
| **FA-005** | TRADING/EXECUTION/ESCALATION_DECISION — acknowledge that this is a BREAKING constitutional boundary before any trading agent goes live | Trading IB-009 implementation unblocked | Immediate | ✅ DONE 2026-07-23 — Yogesh Khandge: *"I acknowledge that TRADING/EXECUTION/ESCALATION_DECISION is a BREAKING constitutional boundary and authorize Trading agent implementation."* |
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

| **FA-026** | GOAL-PLATFORM-REGISTRY Implementation Authorization — Founder authorized blueprint-first upgrade: Component Manifests, EA Skeletons, Gap Scanner, Blueprint Assurance, DB registry tables for all 5 platform services. | 2026-07-30 — Yogesh Khandge | ✅ DONE |
| **FA-027** | GOAL-004 WBE Implementation Authorization — Founder authorized Wallet & Billing Engine implementation (WBE-S1 through WBE-S8 = WC-025 through WC-032). Pricing decisions (D-05 §7) remain open but do NOT block implementation. WBE will not go live with real customers until pricing authorization is recorded separately. | 2026-07-30 — Yogesh Khandge | ✅ DONE |
| **FA-029** | WC-042 = WBE-S7 Authorization — Founder authorized Single Onboarding Payment + Renewal Saga sprint. Implementation decision: all Razorpay configuration via env vars (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_PLAN_ID_{tier}). Lower environments (WAOOAW_ENVIRONMENT=demo\|uat) use 100% discount coupons DEMOWAOOAW/UATWAOOAW to bypass live payment. Production plan IDs to be injected at deploy time. Extends FA-027 coverage to WC-042 (WBE-S7 renumbered from original WC-031 to WC-042 due to sprint sequencing changes). | 2026-08-07 — Yogesh Khandge | ✅ DONE |
| **FA-030** | WC-057 implementation authorization — Founder stated `Authorize implementation of WC-057`. Google OAuth provider configuration is deferred to sprint-end acceptance; local Keycloak authentication and the WC-057 implementation may proceed without it. This authorization does not include WC-058 through WC-060. | 2026-08-08 — Yogesh Khandge | ✅ DONE |
| **FA-031** | WC-034 Phase B implementation authorization — after approving and merging PR #239, Founder stated `239 pr is approved. now record my approval for implementation`. This authorizes INST-010 to implement only WC-034 Phase B components whose local entry criteria pass. Execution remains gated on completion of the FA-032-approved Platform IT Expert Skill 16 Type 1 update, activation gate, and independent EA review, plus approved service contracts for the selected component. It does not authorize deferred attachments, voice, F5/WC-060 continuity and notification behavior, global priority aggregation, public Concierge, WC-058 through WC-060, or deployment. | 2026-08-09 — Yogesh Khandge | ✅ DONE |
| **FA-032** | Platform IT Expert Skill 16 proposal approval — Founder stated `I approve the Platform IT Expert Skill 16 proposal, Next.js Conversational Experience Engineering, with recommendation APPROVE_FOR_SPEC. Authorize the Section 15 Type 1 agent update and activation-gate review. This does not itself authorize application implementation.` This authorizes the Business Architect and agent-spec author to execute only the `NEW_SKILL` Type 1 lifecycle in GitHub Issue #241, followed by independent EA review and the activation gate. It does not activate Skill 16, amend the ratified agent spec by itself, adopt a dependency, or authorize application-source changes. | 2026-08-09 — Yogesh Khandge | ✅ DONE |
| **FA-033** | Platform IT Expert v1.2 and Skill 16 activation — after R-049 independently approved the corrected 16-section technical gate, Founder stated `I approve Platform IT Expert v1.2 and activate Skill 16 — Next.js Conversational Experience Engineering.` This activates the ratified internal capability. It introduces no dependency or deployment authority. WC-034 execution remains limited to FA-031 and each selected component's local entry criteria. | 2026-08-09 — Yogesh Khandge | ✅ DONE |
| **FA-034** | WC-034 Phase B execution release — after PR #244 merged and FA-033 activated Platform IT Expert v1.2 Skill 16, Founder confirmed `WC-034 Phase B execution is now unblocked.` This releases INST-010 to begin F1 and any later WC-034 component whose local entry criteria pass. It does not waive service-contract, API, security, acceptance, independent-review, or C-076 gates; authorize deferred attachments, voice, F5/WC-060 continuity, global priority aggregation, public Concierge, WC-058 through WC-060; or authorize deployment. | 2026-08-09 — Yogesh Khandge | ✅ DONE |
| **FA-035** | WC-034 F2 customer identity policy — Founder approves one `Continue with Google`, `Continue with Facebook`, `Continue with Apple`, and email-fallback experience for new and returning customers. Registration asks only for missing minimum information and requires confirmed email before account completion. Mobile verification is progressive: it must not block basic account entry or exploration, but is required before hiring, WhatsApp connection, payment, recovery activation, sensitive account changes, or another server-classified consequential action. Provider subjects, not email alone, identify login bindings; separate login methods may reconnect to one WAOOAW account only after proof of control, without automatic email-only linking, duplicate creation, or account-existence disclosure. Facebook login requests only basic login information and remains isolated from pages, advertisements, posts, contacts, business activity, and DMA Business OAuth. All three providers are designed now and activated independently only after provider setup and customer-safety evidence: Facebook remains gated by FA-002/FA-018 and Apple by FA-019. Customers may add or remove login methods while retaining at least one usable login or recovery path. This action authorizes product-policy and F2 contract updates only; it does not authorize implementation, provider activation, deployment, or merge. ADR-008 reconciliation remains an INST-004 architecture handoff. | 2026-08-09 — Yogesh Khandge | ✅ DONE |
| **FA-036** | WC-034 F4 current-session implementation authorization — after INST-013 asked exactly `This would begin writing implementation code. Do you authorize this for the current session?`, Founder replied `yes please`. This satisfies the mandatory session implementation gate for the dependency-ordered F4 scope in proposed GEP-GOAL-005-INST-013-06. It does not satisfy the separate exact Registrant acknowledgement, decide `F4-POL-01` through `F4-POL-06`, issue a GOA, authorize deployment or provider activation, enter F5-F8, approve a PR, authorize merge, or weaken ADR-046. | 2026-08-11 — Yogesh Khandge | ✅ DONE |
| **FA-037** | WC-034 F5 / WC-060 contract unification decision — after receiving three paths, Founder selected Option 3 with `ok follow option 3, update required work component documents for suitable changes as you sense.` WC-060 becomes the sole implementation Work Contract for WC-034 F5; its dependency chain, security/data/replay/evidence/Stop semantics, adversarial CCTs, independent reviews, and proportional F8 gate remain mandatory. No duplicate F5 implementation contract follows WC-060. This action authorizes contract and architecture reconciliation only; it does not authorize WC-060 implementation, deployment, provider activation, F6-F8 feature work, PR approval, or merge. | 2026-08-11 — Yogesh Khandge | ✅ DONE |
| **FA-038** | WC-058 current-session implementation authorization — Founder stated exactly `Authorize implementation of WC-058`. This satisfies the separate Founder implementation-consent gate for WC-058 after WC-057 closure. GEOM routing remains mandatory: fresh CA readiness and exact Registrant acknowledgement of GEP-GOAL-005-INST-013-07 must precede GOA-GOAL-005-INST-010-04 issuance and later ACC-GOAL-005-INST-010-04. This action does not authorize provider activation or credentials, WC-059 or WC-060, deployment, production/customer proof, PR approval, merge, or self-review. | 2026-08-11 — Yogesh Khandge | ✅ DONE |
| **FA-040** | WC-059 current-session implementation authorization — Founder stated exactly `Authorize implementation of WC-059` and required confirmation that the Work Contract is genuinely groomed before implementation. This satisfies the separate Founder implementation-consent gate after WC-058 closure. Grooming confirms D-07/R-046, WC-042/WC-043, D-03/D-06, and all required owner/security/data contracts are complete; occupied migration sequence 21 is preserved by the implementation filename `21b-ae01-contract-activation.sql`. GEOM routing remains mandatory: fresh CA readiness and exact Registrant acknowledgement of GEP-GOAL-005-INST-013-08 must precede GOA-GOAL-005-INST-010-05 issuance and later ACC-GOAL-005-INST-010-05. This action does not authorize live Razorpay/provider credentials, provider activation, WC-060, deployment, production/customer proof, PR approval, merge, or self-review. | 2026-08-11 — Yogesh Khandge | ✅ DONE |
| **FA-041** | WC-060 current-session implementation authorization — Founder stated exactly `Authorize implementation of WC-060`. This satisfies Amendment 9's separate implementation-consent gate after R-086 and ACK-GOAL-005-INST-001-09. GEOM routing remains mandatory: GOA-GOAL-005-INST-010-06 must be issued before later ACC-GOAL-005-INST-010-06, and no implementation task may begin before acceptance. This action does not authorize provider activation, deployment, F6-F8 feature implementation, PR merge, self-review, or self-merge. | 2026-08-12 — Yogesh Khandge | ✅ DONE |

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

| **FA-28** | Provider anthropic runway 5.0d - replenishment required | P0 | C-077 procurement runway | 1 hour | OPEN |