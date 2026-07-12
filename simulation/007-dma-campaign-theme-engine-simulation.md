# Simulation 007 — DMA Campaign Theme Engine: Dr. Mehta's October Campaign

**Type:** User Simulation — Digital Marketing Agent v2.5 (Campaign Theme Engine, SIR, SCR, Platform Intelligence)
**Status:** Active
**Purpose:** Validate the new C-055 Campaign Theme Engine, SIR routing, Synthetic Content Reviewer, and Platform Intelligence against a real DMA customer lifecycle. Surface constitutional gaps in the campaign model. This simulation builds on Simulation 001 (Dr. Mehta's discovery and onboarding).
**Persona:** Dr. Priya Mehta, dental clinic, Viman Nagar, Pune. Month 4 of DMA engagement.

---

## Context

Dr. Mehta has been using the DMA agent for 4 months (POST_APPROVAL mode). Approval rate: 94%. The agent has proposed upgrading her to CAMPAIGN_APPROVAL mode. She has agreed.

This simulation covers the first full Campaign Theme Engine execution.

---

## Phase 1 — Platform Intelligence Research

### What should happen

Before the Campaign Brief is proposed, the agent runs Platform Intelligence Research:
- Research Dr. Mehta's competitors' platform activity
- Assess which platforms reach Viman Nagar dental patients
- Recommend a platform mix with evidence

### What actually happens in the simulation

DMA agent: "Dr. Mehta, before I design your October campaign, I'd like to understand where your patients spend time online. Let me research your area."

Agent runs `DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH` prompt with:
- `business_domain: DENTAL_CLINIC`
- `locality: VIMAN_NAGAR_PUNE`
- `competitor_list: [Dantavilas Dental, SmileCare Clinic, White Pearl Dental]`

MCP calls:
- `meta-ad-library-mcp: ads.search_active` → Dantavilas: 3 active Instagram ads. SmileCare: 0 paid. White Pearl: 1 old Facebook campaign.
- `social-profile-mcp: profile.get_public_data` → Dantavilas: 2,340 Instagram followers posting 4x/week. White Pearl: 870 followers.
- Tier 1 RAG: healthcare India platform benchmarks → Instagram primary for 25-45 dental patients in Pune. YouTube significantly growing for patient education content. GBP drives 40% of "dentist near me" conversions.

Platform Intelligence output:
```
INSTAGRAM: ACTIVE — primary patient discovery channel; competitors active; Dr. Mehta already at 1,100 followers
YOUTUBE_SHORT: ACTIVE — education content builds trust; patients research "is root canal painful?" pre-booking; no local competitors active (first-mover opportunity)
GBP: ACTIVE — mandatory; "dentist near me" intent channel
WHATSAPP: ACTIVE — 80 opted-in patients; retention + reactivation
FACEBOOK: ADVISORY — declining relevance for this demographic; maintain presence, don't invest heavily
LINKEDIN: NOT_RELEVANT — patients don't book dentists via LinkedIn
```

### [GAP-D001] Platform Intelligence: No Fallback for Zero Competitor Data

Dantavilas and SmileCare have Instagram presence. But what if `social-profile-mcp` returns 0 results for all competitors? Dr. Mehta's competitors might not exist as searchable public pages if they don't have official Facebook business pages.

**Gap:** Platform Intelligence Research has no documented fallback when competitor research returns no data. The prompt will receive empty competitor arrays, and the quality of the platform recommendation will degrade to generic domain benchmarks only. The customer should be informed when competitor data is unavailable.

**Resolution:**
- `DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH` prompt output schema must include `competitor_data_available: bool` and `fallback_basis: "DOMAIN_BENCHMARKS"` when no competitor data is found.
- The agent must disclose to the customer: "I couldn't find your competitors' public profiles — my recommendation is based on what works for dental clinics in your city, not your specific competitors."
- C-002 (Evidence First — trust through observable evidence): if the recommendation is based on benchmarks not competitors, the evidence record must state this.

**Layer:** DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH prompt schema; Platform Intelligence section of DMA Skill 2 spec.

---

## Phase 2 — Campaign Brief Proposal

Agent proposes: **"Dental Preventive Care Series — October 2026"**

```
Master Theme:  "Prevention isn't a luxury — it's the smartest ₹500 you'll spend"
Window:        October 1–31, 2026
Target Outcome: +15 preventive checkup bookings
Target Patient: Working professional, 28-45, Viman Nagar, hasn't visited in >1 year; 
                anxious about: cost + pain + time
Platform Mix:  Instagram (2 posts/week + 3 stories/week)
               YouTube Short (1 per 2 weeks)
               GBP (1 post/week)
               WhatsApp (1 broadcast/week to opted-in list)
Weekly Themes:
  Week 1: "Prevention is cheaper than cure"       — cost anxiety hook
  Week 2: "What actually happens at a checkup"    — demystify, reduce fear
  Week 3: "Meet our team — the faces you'll see"  — trust and human connection
  Week 4: "October special + conversion CTA"      — book now
```

Dr. Mehta reviews via portal. She approves. `content_campaigns.status = CUSTOMER_APPROVED`.

### What happens next (should be automatic):

The agent generates the Weekly Theme Cascade:
- Week 1 sub-theme entry → `campaign_weekly_themes` record
- Week 2 sub-theme entry → `campaign_weekly_themes` record
- Week 3 sub-theme entry → `campaign_weekly_themes` record
- Week 4 sub-theme entry → `campaign_weekly_themes` record

### [GAP-D002] Campaign Brief Approval UX Not Specified in Spec

The campaign brief is proposed by the agent and must be approved by the customer. But HOW does the customer approve it?

**Current spec gap:** `content_campaigns.status` transitions from DRAFT → CUSTOMER_APPROVED. But the spec does not define:
1. What the customer sees in the portal for campaign approval (is it a special page? a card? an inline approval?)
2. What the approval action is (a button? a WhatsApp reply "Approve"? a signed evidence record?)
3. Can the customer request changes before approving? If yes, what's the iteration flow?
4. What happens if the customer ignores the proposed campaign for 7 days?

**Constitutional requirement:** Campaign approval is a governance event (C-003 — authority is licensed through explicit customer action). The approval must create a CE.RecordEvidence record with the campaign_id and the customer's explicit authorization. A "soft" approval (no response = approval) is constitutionally invalid.

**Resolution:**
- Portal shows Campaign Brief card with "Approve this Campaign" and "Request Changes" buttons
- Each creates a CE evidence record: `CAMPAIGN_APPROVED` or `CAMPAIGN_CHANGE_REQUESTED`
- If no response in 7 days: campaign remains DRAFT; agent sends ONE reminder. No auto-approval.
- "Request Changes" flow: customer adds a note → agent revises brief → re-proposes → same approval gate

**Layer:** DMA agent spec (add campaign approval UX specification); business-capabilities.md (11.7 update); a new BP endpoint: `POST /api/v1/campaigns/{id}/approve`.

---

## Phase 3 — Platform Content Variant Generation (Week 1)

Week 1 begins October 1. The agent generates content variants for "Prevention is cheaper than cure."

### INSTAGRAM_POST variant

`DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT` prompt runs with:
- `platform: INSTAGRAM_POST`
- `weekly_theme: {sub_theme: "Prevention is cheaper than cure", narrative_hook: "₹500 checkup vs ₹15,000 root canal"}`
- `brand_voice_embedding: [Dr. Mehta's Creative Fingerprint]`

Output:
```json
{
  "caption": "Your dentist isn't trying to scare you. They're trying to save you ₹14,500.\n\nA preventive checkup at our Viman Nagar clinic = ₹500.\nWaiting until it hurts = root canal + crown = ₹15,000+\n\nYour smile is worth 30 minutes. Book yours today → link in bio 🦷\n\n#VImanNagar #DentistPune #PreventiveCare #DentalHealth #PuneDentist",
  "image_prompt": "Clean flat-lay: a ₹500 note vs a detailed illustration of a root canal treatment. Warm cream background. Brand colours (teal + white). Dr. Mehta's clinic aesthetic. No stock photo feel. Infographic style. Text overlay: '₹500 now or ₹15,000 later?'",
  "cta": "Book a checkup → link in bio",
  "alt_text": "Comparison showing ₹500 preventive checkup vs ₹15,000 root canal cost"
}
```

### SCR Pipeline runs

**Check 1 (Theme Fidelity):** "Prevention is cheaper than cure" + narrative_hook embedding vs content embedding = 0.87 ✓ PASS
**Check 2 (Brand Voice):** Voice embedding similarity = 0.82 ✓ PASS
**Check 3 (Compliance):** Scans for violations:
  - "₹15,000" claim: Is this a guaranteed price? → Rule check: claims about competitor costs without disclosure = VIOLATION of healthcare advertising guidelines
  - MCI (Medical Council of India) Advertising Guidelines: dental clinics cannot make comparative price claims that imply competitors charge more
  - Flag: COMPLIANCE_VIOLATION

**SCR Check 3 fires ROUTE_TO_CUSTOMER.**

Agent to Dr. Mehta (portal notification): "I need your input before I can post Week 1's Instagram content. The price comparison (₹500 vs ₹15,000) may violate healthcare advertising guidelines — I can't confirm competitor charges. Options: (a) Remove the price comparison entirely; (b) Change to 'your own costs' framing ('A preventive checkup costs ₹500. A root canal can cost 10-30x more'); (c) Add a disclaimer. What would you prefer?"

Dr. Mehta: "Option (b) — our own costs, no comparison."

Agent regenerates. SCR reruns. Check 3: PASS (no comparative claims). Auto-posts.

### [GAP-D003] SCR Healthcare Compliance Rule Set Is a Stub

The SCR Check 3 (Compliance) is specified as "rule-based check against known prohibitions (RAG Tier 1: advertising standards)." But:
- The MCI advertising guidelines for dental clinics are 127 pages
- They cover: prohibited claims, testimonial rules, before/after image rules, pricing claims, competitive comparisons, guarantee language
- The current RAG Tier 1 content is not specified at rule level — it says "Healthcare marketing regulation guidelines India" as a generic Tier 1 RAG source

**Gap:** Without specific, structured compliance rules, the SCR Check 3 for healthcare agents will either:
(a) Miss violations (LLM doesn't know the specific MCI rule)
(b) Over-trigger (LLM is too conservative and blocks legitimate content)
Both outcomes destroy the value of the CAMPAIGN_AUTO mode.

**Resolution:**
- Create a structured compliance rule set for DIGITAL_MARKETING_HEALTHCARE: `knowledge/compliance/healthcare-advertising-rules-india.md`
- Rules must be machine-readable (structured: Rule ID, Prohibited pattern, Allowed pattern, Source citation)
- SCR Check 3 uses RAG retrieval against this structured set + rule-based pattern matching
- Rules cover: comparative claims, guarantee language, before/after images (C-052 context), testimonials, medical procedure descriptions
- This becomes a mandatory Tier 1 RAG source for the DMA agent

**Layer:** New file: `knowledge/compliance/healthcare-advertising-rules-india.md`; DMA Skill 2 RAG Sources (add compliance ruleset); SCR Check 3 specification (add structured rule lookup before LLM check).

---

## Phase 4 — YouTube Short Generation (Audio + Visual)

Week 2: "What actually happens at a checkup." Agent generates YouTube Short variant.

`DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT` runs with `platform: YOUTUBE_SHORT`.

Output includes `audio_script`:
```
"I know what you're thinking. Dental visits are painful. [pause]
They don't have to be.
I'm Dr. Priya Mehta from Viman Nagar, and I want to show you what actually happens
when you sit in my chair. [B-roll: clinic interior, friendly face]
Step 1: We talk. I listen to what's been bothering you.
Step 2: A gentle examination. No surprises. I explain everything as I go.
Step 3: We make a plan together. You decide what happens next.
A checkup takes 30 minutes. Once a year. That's it.
Come see us. Link in description."
[Outro: Dr. Mehta smiling, clinic name + address overlay]
```

### [GAP-D004] Audio Generation Service Not Specified for Video Content

The YOUTUBE_SHORT variant has a `voice_script` field. Generating a YouTube Short requires:
- Text-to-Speech for Dr. Mehta's voice (or the spec says "Dr. Mehta records voice" — but this is not specified)
- Video composition: voice + B-roll + text overlays + music
- `video-generation-mcp` is specified but the underlying service (Runway ML, Kling, Sora) is not selected (Founder decision pending, noted in Skill Dependency Register)

**The deeper gap:** The `audio_script` is generated correctly by the AI. But the pipeline from audio_script → actual audio file is undefined:

Option A: Dr. Mehta records herself using the script (agent sends the script; she records and uploads)
Option B: AI TTS generates a voice that sounds like Dr. Mehta (requires voice cloning — legal complexity)
Option C: Generic professional TTS voice reads the script (less personal but immediately viable)

**Constitutional note:** Using a voice clone of Dr. Mehta without explicit, documented consent is a constitutional violation of C-003 (authority licensed) and C-048 (information non-exploitation). The spec must declare this as an always-ask action type.

**Resolution:**
- YOUTUBE_SHORT execution mode for Phase 1 (MVI): `audio_mode: CUSTOMER_RECORDS` — agent sends script to customer, customer records voice, uploads via portal, agent composes the video
- YOUTUBE_SHORT execution mode for Phase 2: `audio_mode: AI_VOICE_WITH_CONSENT` — always-ask action: customer must confirm voice consent and approve the AI-generated voice sample before use
- `YOUTUBE_SHORT_VOICE_CONSENT_CONFIRMED` added as an always-ask action type

**Layer:** DMA agent spec Skill 8 (Video Content) — add YouTube Short audio mode declaration; always-ask action for voice consent; `video-generation-mcp` spec clarification.

---

## Phase 5 — Weekly Digest

Monday, October 8. Agent sends first Weekly Campaign Digest.

Dr. Mehta receives on portal + WhatsApp:

```
📊 Week 1 Campaign Digest — "Dental Preventive Care Series"

This week:
• Instagram post (₹500 vs root canal) — 89 likes, 12 saves, 3 DMs about bookings ✓
• 3 Instagram stories — 240 views, 18 link taps ✓
• GBP post — 45 views, 8 website clicks ✓
• WhatsApp broadcast — 80 sent, 12 replies (5 asked about appointment) ✓

Your campaign target: +15 preventive bookings in October
Week 1 results: 6 people showed strong intent (DM + WhatsApp query)
Campaign health: ON TRACK 🟢

Week 2 preview: "What actually happens at a checkup"
Content planned: Instagram post + story + YouTube Short + GBP + WhatsApp

Anything you'd like to change? Reply here or in the portal.
```

### [GAP-D005] Weekly Digest Has No Attribution Gap — "Showed Intent" Is Not "Booked"

The digest says "6 people showed strong intent." But Dr. Mehta's KPI is "+15 preventive BOOKINGS." The gap between intent (DM, WhatsApp query) and actual booking is:

- Patients must message Dr. Mehta's personal WhatsApp or call the clinic
- There is no booking system integration in the current spec (no booking-mcp, no clinic management system integration)
- The agent cannot know if a patient who DM'd on Instagram actually booked an appointment
- The actual KPI (appointment bookings) is not measurable from the agent's perspective

**This is the most critical gap in the DMA agent's business model.** The agent can measure content metrics (engagement, clicks) but NOT the actual business outcome (bookings). The monthly KPI assessment will always be an estimate.

**Constitutional implication:** C-037 (Business KPI primacy — every skill must have a measurable KPI). If the KPI (appointment bookings) is not measurable, C-037 is violated at the agent level.

**Resolution options:**
(a) Integrate with clinic management software (Dentistry software APIs — e.g., Carestream, Dentrix) for actual booking data → requires new MCP: `clinic-management-mcp`
(b) Track "intent signals" as a proxy KPI and be transparent: "I track signals, not bookings — you confirm in our monthly review"
(c) Provide Dr. Mehta a simple weekly "booking count" input: "How many new patients cited Instagram/social this week?" → manual signal feeding into the agent's KPI model

**Option (b) or (c) for MVI.** Option (a) for Phase 2+.

**The honest limitation disclosure (C-049):** The agent must declare this at onboarding: "I can measure content performance with high accuracy. I cannot directly measure appointment bookings unless you connect your clinic management system. I'll use engagement signals and your weekly input to estimate."

**Layer:** DMA agent spec — add KPI measurement gap declaration (C-049 honest limitation); update Skill 9 (Performance Analytics) to include proxy KPI model and manual input mechanism; add clinic-management-mcp as Phase 2 dependency.

---

## Phase 6 — Skill Intent Router (SIR) in Action

Dr. Mehta sends a message mid-campaign:
"I want to run a Diwali campaign AND also I want to know how last month's Google ads performed AND I noticed a competitor launched something big on Instagram today."

SIR receives this message. Three intents identified:

1. `CAMPAIGN_CREATION` → primary: `CONTENT_STRATEGY` (Diwali campaign brief)
2. `PERFORMANCE_QUERY` → primary: `PERFORMANCE_ANALYTICS` (Google Ads last month)
3. `COMPETITOR_ALERT` → primary: `COMPETITIVE_INTELLIGENCE`

SIR Layer 4 (Collaboration Orchestration): determines sequence:
- Step 1: `COMPETITIVE_INTELLIGENCE` — fetch competitor Instagram activity (HIGH urgency, Signal Intelligence already has this via SIL competitor feed)
- Step 2: `PERFORMANCE_ANALYTICS` — fetch last month Google Ads data
- Step 3: `CONTENT_STRATEGY` — propose Diwali campaign brief (AFTER knowing performance context + competitive landscape)

Agent assembles one coherent response:

"Dr. Mehta, three things:
**1. About that competitor:** SmileCare just launched a paid campaign with 'Free Dental Consultation' offer. This is the first time they've used paid ads. I've noted it.

**2. Last month's Google Ads:** ₹3,200 spent → 47 clicks → estimated 6-8 enquiries. Cost per enquiry: ~₹450. This is on the lower end for dental ads in Pune — good performance.

**3. Diwali campaign:** Given SmileCare's new offer, I'd recommend making Diwali different from generic discounting. Proposal: 'Smile for Diwali — Gift yourself a healthy smile'. Shall I draft the full campaign brief?"

### [GAP-D006] SIR Multi-Skill Response Creates Single Combined Evidence Record — Unclear Attribution

When the SIR orchestrates 3 skills for one message:
- COMPETITIVE_INTELLIGENCE runs → evidence record #1
- PERFORMANCE_ANALYTICS runs → evidence record #2
- CONTENT_STRATEGY drafts brief → evidence record #3

But the final customer-visible response is ONE message. The evidence chain shows 3 separate skill actions. However:
- The billing attribution (which UsageUnit type gets charged?) is unclear for the combined response
- The customer approval (she approved her portfolio of skills, not "SIR multi-skill queries") — does the combined query need explicit authorization?

**Gap:** The SIR orchestration model does not specify:
1. UsageUnit billing for multi-skill responses (do we charge 3 separate units or 1 combined unit?)
2. Evidence record linkage (how do the 3 evidence records know they were part of one customer request?)
3. The combined response's `combined_approval` flag — if COMPETITIVE_INTELLIGENCE is PRE_AUTHORIZED but CONTENT_STRATEGY requires APPROVAL_GATE, what happens?

**Resolution:**
- Add `parent_request_id UUID` to `institutional.agent_evidence_records` table — all evidence records for a single SIR multi-skill response share the same `parent_request_id`
- UsageUnit billing: charge the HIGHEST-cost unit type used in the response (charge once, not N times)
- If any contributing skill requires APPROVAL_GATE: the combined response requires approval for that skill's contribution only; other PRE_AUTHORIZED contributions are included in the response immediately

**Layer:** `institutional.agent_evidence_records` (add `parent_request_id`); C-054 claim (add billing attribution clarification); SIR specification in ai-runtime.md (add combined billing + approval logic).

---

## Gap Register — DMA Simulation 007

### P0 — Must resolve before CAMPAIGN_AUTO mode goes live

| ID | Gap | Resolution |
|---|---|---|
| GAP-D002 | Campaign approval UX not specified — no constitutional approval mechanism | Portal Campaign Brief card with explicit Approve/Request Changes buttons; CE evidence record per approval |
| GAP-D003 | SCR Check 3 healthcare compliance rule set is a stub — LLM cannot reliably check MCI rules | Create structured healthcare compliance rule set; add to Tier 1 RAG; SCR Check 3 uses rule lookup |
| GAP-D005 | Appointment booking KPI not measurable from agent — violates C-037 | C-049 honest limitation disclosure at onboarding; proxy KPI model; manual booking input mechanism |

### P1 — Must resolve before production

| ID | Gap | Resolution |
|---|---|---|
| GAP-D001 | Platform Intelligence: no fallback for zero competitor data | Add competitor_data_available flag + fallback disclosure to customer |
| GAP-D004 | YouTube Short audio generation service not specified; voice cloning requires consent | Declare audio_mode (CUSTOMER_RECORDS vs AI_VOICE); add YOUTUBE_SHORT_VOICE_CONSENT as always-ask |
| GAP-D006 | SIR multi-skill evidence record attribution unclear | parent_request_id in evidence records; combined billing policy |

---

## Constitutional Discoveries — DMA v2.5

### CD-D001 — Campaign Approval Is a New Class of Constitutional Event

Campaign approval (customer approving a 4-week, multi-platform, multi-content campaign brief) is qualitatively different from approving a single post. It is a pre-authorization that covers N future content pieces. This type of pre-authorization is not currently defined in the Constitutional framework — C-003 (authority is licensed) and C-044 (Synthetic Approval) both handle different patterns.

**Precedent:** A new evidence action_type `CAMPAIGN_BRIEF_APPROVED` is needed. This event is the constitutional basis for all subsequent CAMPAIGN_APPROVAL and CAMPAIGN_AUTO mode content publishing within the campaign window.

### CD-D002 — SCR Is a New Form of Constitutional Compliance Infrastructure

The SCR (Synthetic Content Reviewer) is the first WAOOAW system where the institution reviews its own outputs before they reach the customer. This is a new constitutional pattern: AI checks AI. The evidence record for every SCR run (both PASS and FAIL) must be preserved as an institutional compliance artifact — not just a transactional log. If a customer ever challenges a piece of published content, the SCR record proves the institution's diligence check was performed.
