# Simulation 004 — Kiran's Fitness Studio, Bangalore

**Type:** Full Lifecycle Simulation — End-to-End Platform Validation

**Status:** Active

**Purpose:** Validate the complete customer lifecycle from portal discovery through hire, trial, configuration, weekly execution, payment, pause, resume, termination, and re-hire. Surface all gaps at every layer — portal UX, identity, platform API, agent execution, billing, data retention, and constitution. Expose what a developer agent building IB-009 will hit.

**Business:** Kiran Desai, Owner, KD Fitness Studio, Koramangala, Bangalore

**Why this persona:** Fitness studio is not in the current agent spec target personas (Dental, Beauty). Kiran is moderately tech-savvy (uses apps, Instagram regularly). Monthly revenue ~₹2.5L. Monthly new member target: 20 (current: 8). Existing Instagram: 2,100 followers, posts 2x/month. WhatsApp: 180 active members group.

---

## The World Before WAOOAW

Kiran opened KD Fitness Studio in January 2024. Eighteen months in, the studio is profitable but not growing. The Koramangala market is competitive — five gyms and two yoga studios within 1.5 km. Kiran's differentiator is boutique: small batches, personal attention, no annual contracts.

He spends ₹4,000/month on Instagram boosted posts and gets roughly 8 new member inquiries. Of those, 5-6 convert. He knows this is poor but doesn't know why or what to change. He tried a digital marketing freelancer for two months — cost ₹12,000, got three posts. Gave up.

His constraints:
- Budget: ₹6,000–10,000/month for digital marketing
- Time: 15 minutes/week maximum
- Language preference: English for professional work; Hindi/Kannada comfortable
- Primary device: Samsung Galaxy (Android), uses WhatsApp constantly, opens laptop maybe twice/week

---

## Phase 1 — Portal Discovery

**Wednesday, 7:45 PM**

Kiran is at his studio after the evening batch. He opens Instagram on his phone to check a competitor's story. He notices a sponsored post from WAOOAW. The copy reads:

*"Your gym deserves a digital marketing professional, not a freelancer. Starting at ₹999/month."*

He taps. He is on the WAOOAW portal — on mobile.

### What the Portal Shows Him

The portal landing page has a section: **"What's your biggest challenge?"** — eight cards in his language:

- 🔍 Nobody can find my studio online
- 📞 I'm not getting enough enquiries
- 📅 I don't have time to post on social media
- ⭐ My Google reviews are not good
- 💸 I'm wasting money on ads
- ⚔️ Competitors are growing faster than me
- 🛒 People visit my profile but don't join
- 📊 I don't know what's working

He taps "📅 I don't have time to post on social media."

### [GAP-001] Fitness Studio Domain Not in Agent Spec

The portal should now show the Digital Marketing Agent specialised for fitness studios. The current agent spec covers Dental and Beauty personas only. When Kiran identifies as a fitness studio owner, the portal has nothing fitness-specific to show him — no domain-specific KPI benchmarks, no fitness-specific content examples, no persona match.

**Impact:** Portal either shows a generic DMA (poor first impression) or shows nothing (worse). The agent spec must be extended to include fitness studios as a third persona sub-domain.

**Layer:** Architecture → `digital-marketing-agent.md` persona table, Tier 1 RAG domain knowledge.

---

### The Skills Mind Map

Kiran taps "Explore the agent" and sees an interactive mind map. In the centre: "Digital Marketing Professional." Radiating out: 8 skills in customer language ("I post consistently for you", "I build your Google presence", "I run your ads", "I research your competition"). He can tap each skill to see what it does, what it costs, and what results it typically produces for fitness studios.

### [GAP-002] Skills Mind Map — No Portal Component Specification

The skills mind map is mentioned as the portal sales/marketing layer in Section 6 of the agent spec, but there is no frontend component specification anywhere. No Next.js component, no data model for how the portal renders the skills graph, no API endpoint that serves the skill catalogue to the portal.

**Impact:** Developer building IB-009 portal has no specification for this component. Will improvise — constitutional principles around customer-language presentation will be violated if improvised incorrectly.

**Layer:** Portal (web/) → IB-014 (Domain 7 Customer Self-Service Portal — not yet specified).

---

He reads the skills mind map for 4 minutes. He taps "What does a trial look like?" A modal appears:

*"Register free. We research your studio's digital presence and give you a full report — your Digital Marketing Score and a personalised plan. Takes 15 minutes. No credit card required."*

He taps **Try Free**.

---

## Phase 2 — Registration

### The Registration Flow

A form appears. Fields:

1. Your name
2. Studio name
3. Type of business (dropdown — he sees "Fitness Studio" ✓ — wait, does this exist?)
4. City/area
5. Who are your customers (short text)
6. What do you most want to improve (short text)

### [GAP-003] Fitness Studio Missing from Business Domain Dropdown

The registration form's business domain dropdown is not specified in any current spec. The Skill 0 Customer Profiling spec lists example domains (DENTAL_CLINIC, BEAUTY_ARTIST, FITNESS_STUDIO) but the dropdown population source — where these values come from and how the portal knows what to show — is not specified. If FITNESS_STUDIO is not in the dropdown, Kiran either selects "Other" (losing domain-specific intelligence) or abandons.

**Layer:** Portal data model → `digital_marketing_profiles.business_domain` ENUM needs to include FITNESS_STUDIO; `digital-marketing-agent.md` needs Fitness persona.

---

### [GAP-004] Phone Number Not in Registration Fields

The 6 mandatory registration fields do not include a phone number. But the platform must deliver the Maturity Report via WhatsApp, which requires the customer's phone number with +91 prefix. The report delivery flow will fail at the WhatsApp delivery step because there is no phone number stored.

**Impact:** Either the WhatsApp delivery silently fails (worst case — no notification to customer), or the profiling conversation has to ask for it (inconsistent with "registration covers it"), or there is a post-registration step that is not specified.

**Resolution needed:** Add `phone_number_whatsapp` as a registration field (mandatory for WhatsApp delivery). TRAI compliance requires explicit opt-in for WhatsApp messages — add `whatsapp_opt_in` boolean to registration.

**Layer:** `digital_marketing_profiles` table, registration form spec, TRAI compliance.

---

### [GAP-005] WhatsApp Opt-In Not in Registration — TRAI Constitutional Constraint

TRAI (Telecom Regulatory Authority of India) regulations require explicit consent before sending commercial messages via WhatsApp. The current spec's WhatsApp broadcast skill (Skill 7) notes TRAI compliance but only for broadcast to existing patients/clients. The Maturity Report delivery via WhatsApp is also a commercial message to a new user.

If WAOOAW sends the Maturity Report to Kiran's WhatsApp without his explicit opt-in, it is a TRAI violation.

**Constitutional implication:** C-036 (Skills are constitutionally governed) must include a TRAI compliance prerequisite for any WhatsApp delivery. The evidence record for the first WhatsApp delivery must include `whatsapp_opt_in: true` and the timestamp of opt-in.

**Layer:** Claims (potential new C-045 — India Communications Compliance), registration spec, evidence schema.

---

Kiran fills the form. He adds his phone number in the free-text "aspiration" field because the form doesn't ask for it. He submits.

He lands on: **"Welcome, Kiran. I'm researching your studio now. This takes a few minutes."**

A spinner. Then a chat interface opens.

---

## Phase 3 — Profiling Conversation

### The AI-Native Interview

**Agent:** "Hi Kiran! I can see you run KD Fitness Studio in Koramangala, Bangalore — and you want more members. Perfect. I have a few quick questions to understand your situation. This takes about 10 minutes. Ready?"

**Kiran:** "Yes"

**Agent:** "Great. Your studio is in Koramangala — do most of your members live or work in the immediate area, or do some come from further neighbourhoods like Indiranagar or HSR?"

**Kiran:** "Mostly Koramangala and Indiranagar. Some from HSR."

**Agent:** *(inferring geo-scope: ~3km radius)* "Understood. You mentioned wanting more members — roughly how many new members are you getting now per month, and what would 'good' look like for you?"

**Kiran:** "Now maybe 8. I'd like 20."

**Agent:** "That's a clear target. Are you currently spending anything on Instagram ads or Google ads?"

**Kiran:** "Yes Instagram. About ₹4,000 a month. Don't know if it's working."

**Agent:** *(marks: paid advertising active, ROI unclear, efficiency need ACTIVE)* "Got it — ₹4,000 on Instagram with unclear results. That's very common. One more thing: is there a specific gym or fitness studio nearby that you think is doing better than you digitally?"

**Kiran:** "Yes, FitZone Koramangala. Their Instagram is much better than mine. They got 8,000 followers."

**Agent:** *(marks: competitor identified, competition need ACTIVE)*

**Summary card appears:**
> Here's what I know so far:
> ✓ KD Fitness Studio — Fitness Studio in Koramangala, Bangalore
> ✓ Members: mostly 3km radius (Koramangala, Indiranagar, HSR)
> ✓ Goal: 8 → 20 new members/month
> ✓ Spending ₹4,000/month on Instagram ads — ROI unclear
> ✓ Competitor: FitZone Koramangala (8K Instagram followers)
> Does this look right?

**Kiran:** "Yes exactly"

**Agent:** "Perfect. I have enough to start. I'm now researching your studio's digital presence — takes 3-5 minutes. I'll come back with your Digital Marketing Score."

### [GAP-006] Profiling Conversation Runs in Portal — But Kiran is on Mobile

The profiling conversation is specified as a "chat interface." On mobile, this is a web chat. But Kiran's primary device is WhatsApp. If he closes the browser mid-conversation (notifications, a phone call), the conversation is lost.

**Gap:** No mechanism for resuming an incomplete profiling conversation. No session persistence across browser close. No option to conduct the profiling via WhatsApp instead of web chat.

**Constitutional implication:** C-039 (conversational configuration must be completable) — if the conversation cannot be resumed, C-039 is violated for mobile-primary users.

**Resolution:** The profiling conversation needs a resume token (link in SMS/WhatsApp) that lets the customer continue from the last confirmed exchange. Alternatively, a WhatsApp-native profiling flow as an option.

**Layer:** AI Runtime (Customer Profiling Pipeline), web portal session management, Customer Profile table (needs `profiling_session_id` and `last_exchange_index`).

---

## Phase 4 — Market Research Execution

### Background Research (3-5 minutes)

The Market Research Pipeline runs. It:
- Searches "KD Fitness Studio Koramangala Bangalore" via web-search-mcp
- Retrieves Google Business Profile data via google-places-mcp
- Scans @kdfitnesskoramangala on Instagram via social-profile-mcp (public)
- Checks Meta Ad Library for KD Fitness Studio (finds 2 active campaigns)
- Scans kd-fitness.in website (if exists) via web-scan-mcp

### [GAP-007] Temporal Workflow for Market Research Not Specified

The Market Research Pipeline runs for 3-5 minutes. This cannot be a synchronous HTTP request — it will timeout. It must be a background job. The platform uses Temporal for durable workflow orchestration (ADR-015). But there is no specification for a "Market Research Workflow" in Temporal. No workflow definition, no activity functions, no timeout configuration.

**Impact:** Developer agent building IB-009 has no specification for how to implement the 3-5 minute background research. Will likely implement as a synchronous call (wrong — times out) or an ad-hoc background thread (wrong — not durable, not observable).

**Layer:** Temporal workflow spec (missing), Professional Runtime → Temporal integration for intelligence skill workflows.

---

### [GAP-008] Market Research Result Has No Fitness Benchmark Data

The Maturity Score calculation uses Tier 3 platform intelligence (aggregate benchmarks by domain + city). For Fitness Studio in Bangalore, there is no existing Tier 3 data — this is a new domain not yet in the system.

**Impact:** The benchmark section of the Maturity Report ("Average fitness studio in Bangalore: Score X") cannot be populated. The agent must either display "benchmark not yet available for this domain" (acceptable) or fabricate a number (constitutional violation — C-002, First Law: claims must be evidential).

**Constitutional implication:** This is a First Law issue. The agent must NEVER display a benchmark it cannot evidence. The Maturity Report spec must include a fallback: if benchmark data is not available for domain+city, show national average OR display "benchmark being built — check back next month."

**Layer:** Claims (C-002 applies), Maturity Report spec, Tier 3 data population strategy.

---

## Phase 5 — Maturity Report Delivery

The research completes. Kiran's score: **3 / 7 — Occasional Activity**.

**Report generated:**
- Score: 3/7
- Axis scores: Footprint 3, Social 3, GBP 2, Paid 4, Content 2, Competitors 4, Analytics 2
- Needs Heat Map: Visibility (LATENT), Leads (ACTIVE), Consistency (ACTIVE), Trust (ACTIVE), Efficiency (ACTIVE), Competition (ACTIVE), Clarity (LATENT)
- Recommended bundle: **Curtain Raiser** (Score 1-3)

### Delivery: WhatsApp Voice

The platform attempts to deliver via WhatsApp voice (Kiran's preferred channel — Day 1).

### [GAP-009] WhatsApp Business API — Outbound Message to New User Requires Pre-Approved Template

WhatsApp Business API has a strict policy: businesses can only initiate conversations with users using pre-approved message templates (HSM — Highly Structured Messages). The Maturity Report is NOT a pre-approved template — it is a dynamically generated document. WhatsApp will reject the delivery.

**Resolution path:** WAOOAW must have pre-approved HSM templates for: (a) report ready notification ("Your Digital Marketing Report is ready — tap to view"), (b) then a link to the portal, with the full report accessible there. Voice summary can only be sent if the customer initiates the conversation first (or has an active conversation window from the last 24 hours).

**Constitutional implication:** The delivery guarantee in Section 3.14.3 (WhatsApp voice delivery Day 1) is architecturally unachievable for first-time customers due to WhatsApp Business API policy. The spec must be revised: first delivery is always portal + SMS/email with a link; WhatsApp delivery is established once the customer has initiated a conversation.

**Layer:** whatsapp-business-mcp (HSM template management), `digital_marketing_maturity_scores.report_pdf_url`, delivery sequence logic.

---

### [GAP-010] Report PDF Generation — No Document Generation Service Specified

The Maturity Report includes a PDF download. No PDF generation service is in the architecture — no container, no MCP server, no library specification. The portal can render HTML, but PDF generation requires a service (Puppeteer, wkhtmltopdf, or a PDF API).

**Layer:** containers.md (missing pdf-generation service), docker-compose (missing stub).

---

Kiran receives an SMS: "Your Digital Marketing Report for KD Fitness Studio is ready. View it at: [link]"

He taps the link on his phone. Portal opens. Score 3/7 displayed with the heat map and recommendations. He spends 6 minutes reading.

He taps **"Let me try the Curtain Raiser package."**

---

## Phase 6 — Trial Hiring Workflow

### Employment Contract Formation

The portal guides Kiran through:
1. Review recommended skills (Curtain Raiser: Skills 0-8)
2. Set goals per skill
3. Connect accounts

### [GAP-011] Trial Duration and Limitations Not Specified

The trial is referenced multiple times in the spec ("trial artifact," "trial experience") but never defined:
- How long does the trial last? (7 days? 14 days? Until first report?)
- What skills are active during trial? (All Curtain Raiser? Or limited?)
- What is the trial billing model? (Free? ₹0 but with usage cap?)
- What triggers trial-to-paid conversion?
- What happens if the trial expires without hire? (Data deleted? Preserved? For how long?)

**Constitutional implication:** C-034 (employment lifecycle) defines EVALUATION → ACTIVE → SUSPENDED → TERMINATED states. The "trial" is not a constitutional state — it is an EVALUATION state with a time limit. The trial expiry must trigger a constitutional lifecycle event (either ACTIVE if hired, or TERMINATED if not). This event must be recorded in evidence_records.

**Layer:** `employment_state` ENUM needs TRIAL or the spec must map trial to EVALUATION with a time-bounded policy, `employment_contracts` needs `trial_end_date`, C-034 needs a note on trial-to-paid transition.

---

### Setting Skill Goals

For each Curtain Raiser skill, Kiran is asked:
- **Content Strategy:** "How many posts per week on Instagram?" → Kiran: "3"
- **Google Business:** "Do you want me to respond to reviews?" → Kiran: "Yes"
- **WhatsApp:** "Do you want to send member updates to your WhatsApp group?" → Kiran: "Yes"

### [GAP-012] Platform Account Connection — OAuth Flow Not Specified

To execute skills, the agent must connect to Kiran's accounts:
- Instagram Business account (Meta Graph API — requires Facebook Login OAuth)
- Facebook Page (Meta Graph API)
- Google Business Profile (Google OAuth)
- WhatsApp Business (requires WhatsApp Business API account — not just a personal number)

**The spec says:** "Credential collection is guided, one platform at a time, via Keycloak-managed external credential vault."

**What is not specified:**
- How does the OAuth flow work? Who redirects to Meta/Google?
- Who stores the OAuth tokens? Keycloak? A separate secrets vault?
- How are refresh tokens managed? (Meta tokens expire, Google tokens expire)
- What happens if Kiran's Instagram account is a personal account, not a business account? (Required for API access — very common blocker)
- What happens when a token expires mid-campaign? (Ad pauses? Agent notifies customer?)

**This is a P0 implementation gap.** Without platform account connection, no social skills can execute. The credential vault is mentioned in ADR-014 (Secret Management) but the OAuth flow for external platforms is not in any ADR.

**Layer:** New ADR needed (ADR-021: External Platform OAuth and Token Management), containers.md (oauth-proxy-mcp?), Keycloak configuration.

---

### [GAP-013] WhatsApp Business API — Kiran Has a Personal WhatsApp, Not a Business Account

Kiran's WhatsApp number is his personal number. WhatsApp Business API requires a dedicated WhatsApp Business account, WABA (WhatsApp Business Account) approval from Meta, and a different phone number. It cannot use a personal WhatsApp number.

**Impact:** The WhatsApp Business Engagement skill (Skill 7) cannot execute for most small business customers in India who use personal WhatsApp numbers. This is a fundamental product gap for the India market.

**Resolution paths:** (a) WAOOAW provides a managed WhatsApp Business number on behalf of the customer (adds operational complexity) or (b) The skill is only activated when the customer has a verified WABA (limits market significantly) or (c) The skill uses a chatbot integration approach via third-party providers like Interakt/Wati (changes the architecture).

**Constitutional implication:** Capability 11.3 (WhatsApp engagement) will fail for the majority of India SME target customers. This must be addressed before WhatsApp skill is activated in the MVP.

**Layer:** `digital-marketing-agent.md` Skill 7 constraints, containers.md, new ADR for WhatsApp Business Account provisioning model.

---

Kiran completes the goal-setting for Content Strategy, Google Business (no WhatsApp — he selects "I'll set this up later"). The Employment Contract is shown:

- Professional: Digital Marketing Professional
- Bundle: Curtain Raiser (Trial — 14 days)
- Active skills: Content Strategy, Instagram, Facebook, Google Business, Video
- Trial period: 14 days from today
- Post-trial: ₹1,499/month (+ GST)
- Your override rights: listed

Kiran taps **"Start Trial".**

Evidence record created: `EMPLOYMENT_FORMED` — Employment Contract ID generated.

---

## Phase 7 — Agent Runs (Trial Period, Days 1-14)

### Day 1 — Content Strategy Skill Activates

The agent runs Skill 2 (Content Strategy). It produces a monthly content calendar:
- 12 posts for the next month (3/week × 4 weeks)
- Themes: Koramangala fitness lifestyle, member transformation stories (with consent), morning workout motivation, studio highlights

The calendar is presented to Kiran for approval in the portal.

### [GAP-014] Approval Notification — How Does Kiran Know He Has Something to Approve?

Kiran has just set up the trial and gone back to running his studio. The content calendar is ready in the portal. But how does Kiran know to go look at it? The spec says approval is required before any execution begins. But there is no specification for:
- How the agent notifies the customer that an approval is pending
- Which channel the approval notification goes to (WhatsApp text? Push? Email?)
- What happens if the customer doesn't respond within X days (does execution block forever?)
- Is there an approval timeout and auto-escalation?

**Constitutional implication:** The APPROVAL_GATE execution model says "customer approves before execution." If the customer is not notified, the evidence record for "AWAITING_APPROVAL" stays in that state indefinitely. The system has no self-resolving mechanism. This is a platform gap, not a skill gap.

**Layer:** Business Platform (approval request notification mechanism), push notification service (not in architecture), `approval_requests` table needs `notification_sent_at`, `reminder_sent_at`, `expires_at`.

---

### Day 3 — Kiran Approves Content Calendar

Kiran gets an email (the fallback channel since WhatsApp is not yet set up): "Your content calendar is ready for review." He opens the portal, approves 10 of 12 posts, requests one change. Agent updates and re-presents. Kiran approves. Calendar locked.

### Day 3-7 — Posts Execute

Agent publishes 3 posts. Each post:
1. Content created (image-generation-mcp → AI image)
2. Caption written
3. Presented to Kiran for approval (CUSTOMER_APPROVAL mode — trial period)
4. Kiran approves via portal
5. instagram-mcp.post.publish executed
6. Evidence record: EXECUTED

### [GAP-015] Image Generation Legal — AI Images for Fitness Content

The image-generation-mcp generates AI images for Instagram posts. For a fitness studio, content typically shows: people exercising, studio environment, equipment, transformations. AI-generated people in gym settings are legally ambiguous — some jurisdictions require disclosure that images are AI-generated. India does not have clear regulations yet but this will evolve.

**Constitutional implication:** The spec currently says "Prohibited: generate AI deepfakes of real people." But AI-generated generic fitness people (not real, but photorealistic) is in a grey zone. The constitutional constraint should be extended: "All AI-generated images must not create false impressions about actual people, actual results, or actual studio conditions."

**Layer:** `digital-marketing-agent.md` Skill 8 constitutional constraints.

---

### Day 10 — Analytics Skill Runs

Skill 9 (Performance Analytics) reads Instagram insights: 3 posts published, 847 impressions, 23 profile visits, 2 link-in-bio taps.

### [GAP-016] Analytics Platform Access — Google Analytics Not Connected

The analytics skill reads from Meta Insights and GBP Insights (configured). But Kiran's website (if any) runs Google Analytics 4. GA4 access requires OAuth connection to Kiran's Google account. The analytics skill spec says it reads from "all connected platforms" — but GA4 connection is not in the account connection flow. The trial never asked for Google account access.

**Layer:** OAuth connection flow (GAP-012 also), google-search-console-mcp, platform-analytics-mcp needs GA4 OAuth documentation.

---

### Day 14 — Trial Ends. Agent Presents Summary.

The trial period ends. Agent produces a trial summary:
- 6 posts published (all approved)
- 2,847 impressions from posts
- 18 profile visits
- Google Business: 3 new reviews responded to
- No new member sign-ups tracked (no tracking pixel — GAP-017)

**Kiran receives:** Email + Portal notification — "Your trial has ended. Here's what your digital marketing professional achieved. Continue for ₹1,499/month + GST?"

### [GAP-017] Conversion Tracking — No Mechanism to Track New Members from Digital

The agent's primary KPI for Kiran is "new member sign-ups." But the agent has no way to know if a new member came from a post, a Google Business profile visit, or a WhatsApp message. There is no tracking mechanism specified:
- No UTM parameters on the studio's website link
- No unique landing page for the agent's campaigns
- No integration with any gym management software (Mindbody, etc.)
- No "how did you hear about us" capture at membership sign-up

**Impact:** The primary KPI (new member sign-ups) is untracked. The agent can only report impressions and profile visits — not the business outcome. The Maturity Report promised "measurable ROI from digital" at Score 5+ but the infrastructure for measuring ROI does not exist.

**Constitutional implication:** C-037 (Business KPI primacy) requires the primary business outcome to be measurable. If it is not measurable, the agent cannot report against its constitutional obligation. This is a C-037 compliance failure.

**Layer:** Claims (C-037 — business KPI must be measurable or agent must surface this gap to customer), new capability needed: conversion tracking setup, UTM management.

---

## Phase 8 — Hire Decision and Payment (Razorpay)

Kiran taps **"Continue — ₹1,499/month".**

### [GAP-018] No Payment Processor in the Architecture

Razorpay India is not mentioned in any file in this repository:
- Not in containers.md
- Not in docker-compose.yml
- Not in any ADR
- Not in the data schema
- Not in the business-platform.openapi.yaml (presumably)

The `subscription_billing_events` table exists in the schema but has no payment processor integration defined. The billing model is described (pro-rata, per-skill) but there is no payment capture, payment confirmation, or subscription management mechanism.

**This is a P0 gap for any paid product.** Without payment processing, the product cannot generate revenue.

**Gaps within this gap:**
- Razorpay Subscription API (recurring billing) vs. Razorpay Payment Links (one-time)
- India GST: 18% GST must be added to ₹1,499 → actual charge is ₹1,769 (Kiran must see this)
- GST invoice: WAOOAW must issue a GST-compliant tax invoice (GSTIN, HSN code for SaaS services)
- Payment failure handling: what happens if payment fails? Employment suspended immediately? Grace period?
- Refund policy: what if Kiran cancels within 3 days?

**Layer:** New ADR (ADR-022: Payment Processing — Razorpay India), new container (razorpay-mcp or billing-service), `subscription_billing_events` needs payment_processor_reference, new tables for payment_transactions, gst_invoices.

---

### [GAP-019] GST Invoicing — India Legal Requirement

Indian B2B customers (businesses with GSTIN) can claim GST input credit on software subscriptions. WAOOAW must:
- Ask if customer has GSTIN (optional at registration, mandatory for invoice)
- Issue GST-compliant invoices monthly (HSN/SAC code for "Online Information and Database Access or Retrieval Services" — 9984)
- File GSTR-1 monthly reporting all B2C and B2B invoices

**Layer:** Registration form (add optional GSTIN field), billing schema (gst_invoices table), GST calculation in billing events.

---

Assume payment succeeds (Razorpay test mode). Employment state transitions from EVALUATION to ACTIVE.

Evidence record: `EMPLOYMENT_ACTIVATED` — employment contract, payment confirmed, billing start date.

---

## Phase 9 — Month 1-3 Paid Engagement

### Weeks 3-8 — Agent Running

The agent runs weekly:
- Monday: Content batch for the week proposed → Kiran approves (takes 5 min)
- Tuesday-Saturday: Posts published per schedule
- Every 2 weeks: WhatsApp member update (skipped — WhatsApp not connected)
- Monthly: Google Business optimization

### Week 4 — Agent Proposes Exception Approval Mode Upgrade

After 4 weeks and 12 posts with >90% approval rate (Kiran rejected 1 post out of 12), the agent surfaces:

> "You've approved 11 of 12 posts I've suggested. I can make this even smoother — instead of approving each post, approve the weekly content plan on Monday and I'll execute automatically. This saves you 3-4 tap-approvals per week. Want to try it?"

Kiran taps **"Yes."** Decision Space amendment created. Skill 4 (Instagram) upgrades to `EXCEPTION_APPROVAL` mode. Evidence record: `DECISION_SPACE_AMENDMENT` + `SKILL_APPROVAL_MODE_UPGRADE`.

### Month 2, Week 2 — Pace Check Triggered

Day 15 of Month 2. Instagram: 1,847 impressions, 12 profile visits. Pace < 60% of month target.

Agent self-correction: shifts posting time from 7 PM to 6:30 AM (test: morning workout audience). Logs to `skill_self_governance_log`.

Agent sends WhatsApp text (Kiran has now connected his personal WhatsApp number for notifications, opted in):

> "KD Fitness: I noticed your Instagram reach is below target for this month. I've shifted posting times to early morning to catch your audience before their workouts. Watching closely — will update you at month end."

### [GAP-020] Personal WhatsApp for Notifications vs. Business WhatsApp for Customer Broadcast

Two separate WhatsApp interactions exist:
- **WAOOAW → Kiran**: platform notifications (approval requests, reports, alerts) — can use Kiran's personal WhatsApp if he opts in
- **Agent → Kiran's members**: broadcast messages (member updates, offers) — requires Kiran's WhatsApp Business account

The spec conflates these two. The `whatsapp-business-mcp` is used for both. But they are different: personal WhatsApp notification delivery uses the WhatsApp Business API with Kiran as the recipient; member broadcast uses Kiran's own WABA account to reach his members.

**Layer:** `digital-marketing-agent.md` Skill 7 needs to distinguish platform notifications from customer-broadcast use cases. Two separate MCP authorization patterns.

---

### Month 3 — Synthetic Approval Mode Proposal

Month 3, week 1. Instagram Skill has now processed 24 posts in EXCEPTION_APPROVAL mode. Of the weekly batch approvals, Kiran has approved all 8 weekly plans without changes. Confidence on routine posts: 93%.

Agent surfaces:

> "You've approved all 8 weekly content plans without changing anything. I now know your preferences well enough to handle routine posts automatically. I'll still show you anything new or different — new themes, collaborations, anything that feels different from what you usually like. Want to try fully automatic? You can always review and undo anything within 24 hours."

Kiran taps **"Yes."** Synthetic Approval mode activated for Skill 4 (routine posts).

Evidence chain: Decision Space amendment → `synthetic_approval_records` begins populating.

---

## Phase 10 — Pause

### Month 4 — Kiran Pauses

Kiran is renovating his studio for 3 weeks. He doesn't want posts going out during renovation. He taps **"Pause agent"** in the portal.

### [GAP-021] Pause Granularity — Full Agent vs. Individual Skill

The pause option in the portal is not specified. Can Kiran:
(a) Pause the entire agent (all skills stop)
(b) Pause specific skills (stop Instagram/Facebook, keep Google Business running)
(c) Pause with a scheduled resume date

C-036 says "Skills are independently governable." C-038 says billing stops pro-rata from pause moment. This implies individual skill pause is constitutional. But the portal UX for this is not specified. If the portal only offers full-agent pause, C-036 is not fully served.

**Layer:** Business Platform (pause endpoint granularity), `employment_contracts` (pause at contract level or at skill level?), `subscription_billing_events` (which skills are paused?).

---

### What Happens to Running State on Pause

When Kiran pauses:
- **Scheduled posts:** 2 posts are scheduled for the next 3 days in instagram-mcp. Should they execute or be cancelled?
- **Active ad campaign:** Meta ad campaign is running. Should it pause immediately? (Yes — billing impact)
- **Competitor monitoring:** Should continue — it's read-only and doesn't cost customer money
- **A/B tests:** Any running A/B test should pause

### [GAP-022] Pause Execution — No Pause Handler Specified

There is no specification for what happens to each skill's in-flight work when a pause is triggered. The `dm_phase_bundle_subscriptions.deactivated_at` is set, but no workflow handles:
- Cancelling scheduled posts in scheduling-mcp
- Pausing Meta/Google ad campaigns via their APIs
- Suspending competitive monitoring cycles
- Preserving the A/B test state for later resumption

**Layer:** Business Platform (pause handler workflow in Temporal), `skill_self_governance_log` needs pause_reason, in-flight skill state handling per skill type.

---

Billing stops pro-rata. `subscription_billing_events` records pause with `paused_at` timestamp and calculates pro-rata credit.

---

## Phase 11 — Resume

3 weeks later. Kiran taps **"Resume agent".**

### [GAP-023] Resume Continuity — Synthetic Approval History Preserved?

When Kiran resumes, the Synthetic Approval Pipeline must re-check whether synthetic mode is still valid. Three weeks have passed. In that time:
- New Instagram algorithm changes may have affected what performs well
- The prior 24 approved posts are now 3 weeks old
- The confidence model may have drifted

Should the system: (a) resume synthetic approval as-before (same model), (b) reset to EXCEPTION_APPROVAL and rebuild, or (c) run a brief re-calibration check?

**Constitutional implication (C-044):** Synthetic Approval authority is "earned through demonstrated preference learning" — if the preference model is potentially stale, using it without recalibration may produce approvals the customer would not have given. The safest constitutional position: resume at EXCEPTION_APPROVAL mode; propose upgrade back to SYNTHETIC after 4-8 more approved actions.

**Layer:** `skill_runtime_configurations` — add `synthetic_model_last_calibrated` timestamp and `stale_after_days` parameter; resume handler checks model freshness.

---

## Phase 12 — Termination

Month 6. Kiran's studio has grown. He now wants a full-time human social media manager. He taps **"End hire".**

### [GAP-024] Termination Flow — Evidence Export and Data Retention

On termination:
- What evidence can Kiran take with him? The spec mentions "Export Customer Evidence" (Capability 5.3) but the export format, content, and delivery mechanism are not specified.
- What happens to Tier 2 RAG data (approved posts, brand voice embeddings, synthetic approval history)?
- What happens to the competitor snapshots?
- How long does WAOOAW retain Kiran's data after termination?

**India PDPB (Personal Data Protection Bill) implications:** WAOOAW must have a data retention policy and must delete personal data within a defined period after the customer requests deletion. No retention policy exists in any specification.

**Constitutional implication:** ART-IX (Customer Rights) — "right to their own evidence records." This implies customers can export all evidence at any time, including post-termination. The export capability must survive termination for a defined period.

**Layer:** New claim potentially needed for data retention, `employment_contracts.terminated_at`, retention policy document, export API specification.

---

### Billing Settlement on Termination

Final billing: pro-rata for last partial month. GST invoice issued. Razorpay refund if any credit exists.

Evidence record: `EMPLOYMENT_TERMINATED`

---

## Phase 13 — Return After 3 Months

### The Re-Hire Flow

Month 9. Kiran's human social media manager quit. Kiran returns to WAOOAW. He logs in with the same credentials (Keycloak — account preserved).

Portal greets him: "Welcome back, Kiran. KD Fitness Studio's last Digital Marketing Score was **4/7** (3 months ago). Want to pick up where you left off?"

### [GAP-025] Re-Hire Continuity Model — Constitutional and Data Design Gap

When Kiran re-hires, several questions arise:

**(a) Is a new Employment Contract formed, or is the old one resumed?**
C-034 (employment lifecycle) says TERMINATED → next hire is a new EVALUATION → ACTIVE cycle. A new Employment Contract must be formed. The old contract is permanently TERMINATED. But the customer's profile data (Tier 2 RAG — approved posts, brand voice, skill configurations) should be reusable.

**(b) Which data survives termination?**
- Customer profile: YES (registered user, profile persists)
- Maturity scores: YES (historical record, append-only)
- Approved post embeddings (Tier 2 RAG): should YES but spec is silent
- Synthetic approval history: should YES but policy not specified
- Skill runtime configurations: should YES (customer's choices should be remembered)
- Active ad campaigns: NO (terminated with contract)
- Evidence records: YES (immutable, CAL record)

**(c) What is the re-hire onboarding?**
If data survives, the agent should NOT run full Customer Profiling again — it already knows Kiran. But 3 months have passed — should a refresh Market Research be run? The 6-monthly refresh cadence says yes.

**Layer:** `employment_contracts` (previous_contract_id FK for continuity tracking), `digital_marketing_profiles` (survives termination — belongs to organisation, not contract), Tier 2 RAG retention policy, re-hire onboarding flow specification.

---

Kiran selects **"Resume my previous setup"** (re-hire with prior configuration).

New Employment Contract formed. Prior skill configurations loaded. Refresh Market Research runs (3 months since last assessment). New Maturity Report: Score **5/7** — Structured Activity (Kiran's human SM manager was actually doing some work). Recommendation: upgrade to Growth Engine bundle.

Kiran selects Growth Engine. Razorpay subscription updated to ₹2,499/month.

Agent activates new skills: Analytics (Skill 9), Local SEO (Skill 10), Paid Advertising (Skill 11).

---

## Gap Register

### P0 — Must resolve before IB-009 sprint begins

| ID | Gap | Layer | Resolution needed |
|---|---|---|---|
| GAP-012 | Platform OAuth flow not specified | ADR, containers.md | ADR-021: External Platform OAuth and Token Management |
| GAP-018 | No payment processor in architecture | ADR, containers.md, SQL | ADR-022: Razorpay India Integration |
| GAP-014 | Approval notification mechanism not specified | Business Platform, push notification | Notification service spec + push-notification container |
| GAP-007 | Market Research temporal workflow not specified | Temporal workflow | Market Research Temporal Workflow spec |

### P1 — Must resolve before any skill can execute for real customers

| ID | Gap | Layer | Resolution needed |
|---|---|---|---|
| GAP-004 | Phone number missing from registration fields | Registration form, SQL | Add phone_number_whatsapp + whatsapp_opt_in to registration |
| GAP-005 | TRAI WhatsApp opt-in not captured | Constitution, evidence schema | C-045 candidate (India Communications Compliance) |
| GAP-009 | WhatsApp Business API first-message restriction | whatsapp-business-mcp, delivery spec | Revise delivery sequence: portal/SMS first, WhatsApp after opt-in window |
| GAP-011 | Trial model not defined | employment_state ENUM, C-034, contract schema | Define trial as EVALUATION with time bound; add trial_end_date to contracts |
| GAP-013 | Personal WhatsApp vs WhatsApp Business API | Skill 7 spec, architecture | Resolve provisioning model; document WhatsApp Business account requirement |
| GAP-017 | Conversion tracking (primary KPI) not specified | C-037, new capability | UTM management, conversion tracking capability, or C-037 compliance gap disclosure |
| GAP-019 | GST invoicing not in billing architecture | SQL, billing spec | gst_invoices table, GSTIN field, SAC code, GSTR-1 reporting |
| GAP-022 | Pause execution handler not specified | Temporal workflow, Business Platform | Pause workflow: cancel scheduled posts, pause ads, suspend monitors |

### P2 — Must resolve before production launch

| ID | Gap | Layer | Resolution needed |
|---|---|---|---|
| GAP-001 | Fitness Studio not in agent spec personas | `digital-marketing-agent.md` | Add FITNESS_STUDIO as third persona sub-domain |
| GAP-002 | Skills mind map has no portal component spec | IB-014 (portal) | Skills catalogue API endpoint + frontend component spec |
| GAP-003 | Business domain dropdown not data-modelled | Registration form, SQL | Define business domain taxonomy as a platform-level enum/lookup |
| GAP-006 | Profiling conversation not resumable on mobile | AI Runtime, session management | Resume token, session persistence, WhatsApp-native profiling option |
| GAP-008 | No benchmark data for new domains | Tier 3 platform intelligence, Maturity Report | Fallback strategy: national average or "benchmark being built" |
| GAP-010 | PDF generation service not in architecture | containers.md | Add pdf-generation service (Puppeteer/Gotenberg stub) |
| GAP-015 | AI-generated image legal ambiguity | Skill 8 constitutional constraints | Add constraint: no AI images implying real results or real people |
| GAP-016 | GA4 not in account connection flow | OAuth flow, platform-analytics-mcp | Add Google Analytics OAuth to account connection step |
| GAP-020 | Platform notification vs. broadcast WhatsApp conflated | Skill 7 spec | Separate two use cases in spec with distinct authorization patterns |
| GAP-021 | Pause granularity (full vs. skill-level) not specified | Business Platform, C-036, portal | Define pause at skill level per C-036; portal UX for selective pause |
| GAP-023 | Synthetic approval model freshness on resume | skill_runtime_configurations | Add model freshness check on resume; policy for stale model |
| GAP-024 | Termination: evidence export, data retention policy | SQL, ART-IX, India PDPB | Data retention policy document, export API, deletion workflow |
| GAP-025 | Re-hire continuity model | SQL, C-034, Tier 2 RAG | Define which data survives termination; re-hire onboarding flow |

---

## Constitutional Discoveries

### CD-001 — Trial as EVALUATION with Constitutional Time Bound

The Constitution's EVALUATION state has no time limit. In commercial practice, trials are time-bounded. The resolution: EVALUATION may carry a `trial_end_date`; at expiry, if no ACTIVE transition has occurred, the system must create a TERMINATED evidence record automatically (no silent limbo states).

**Precedent candidate:** Every EVALUATION state must either transition to ACTIVE or terminate within a defined period. Silent EVALUATION is constitutionally invalid — it creates phantom authority that is neither active nor revoked.

---

### CD-002 — Primary KPI Must Be Measurable Before Agent Activation

C-037 says business KPI is primary. But for KPIs that require external tracking infrastructure (conversion tracking, attribution), the agent cannot fulfil its constitutional obligation if that infrastructure doesn't exist. The agent must surface this gap to the customer at employment formation — not discover it after 6 weeks of work.

**Precedent candidate:** If a skill's primary business KPI is not technically measurable with available data, the agent must disclose this at hiring and propose the tracking setup as the first action. It may not accept a KPI it cannot measure and then report proxy metrics as substitutes.

---

### CD-003 — Pause Creates a Preservation Obligation

When a customer pauses a professional engagement, the institution acquires a constitutional obligation to preserve the professional's accumulated knowledge (Tier 2 RAG, synthetic approval history, skill configurations) for a reasonable period. The Employment Contract pauses; the professional's identity and learning do not.

**Precedent candidate:** A paused engagement preserves all accumulated professional learning for the duration of the pause and a post-termination period. The institution may not delete Tier 2 customer-private data during a pause event.

---

### CD-004 — India Regulatory Compliance as a Constitutional Prerequisite

WAOOAW operates primarily in India. Three India-specific regulations create constitutional constraints not currently in any claim:
(a) TRAI: WhatsApp commercial messages require opt-in
(b) PDPB: Data retention and deletion obligations
(c) GST: Invoice and filing obligations for any business receiving payment

**Precedent candidate:** India-specific regulatory compliance (TRAI, PDPB, GST) is a Constitutional Floor for any agent serving India customers. Violating these regulations is equivalent to violating a Constitutional Floor — the institution cannot operate commercially without them.

**New claim candidate:** C-045 — India Regulatory Compliance Prerequisite.
