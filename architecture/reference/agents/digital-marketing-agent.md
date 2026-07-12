# Digital Marketing Professional — Healthcare & Beauty

**Specification version:** 2.5
**Date:** 2026-07-12 (v2.5 — C-055: Campaign Theme Engine, Platform Intelligence, Synthetic Content Reviewer, Content Cascade, Campaign Approval Modes)
**Change from v2.0:** Section 3.15 (Strategic Cognition Standard) added. Professional Template: strategic_cognition block declared. C-050 added to Constitutional Checklist. Prompt Catalogue section (§10b) added. Two new prompts catalogued.
**Constitutional Basis:** C-036 (Skills), C-037 (Business KPIs), C-038 (Billing), C-039 (Conversational config), C-040 (Domain specialization), C-041 (Tool authorization), ADR-019 (RAG), ADR-020 (MCP), C-048 (Information Non-Exploitation — LAW), C-049 (Honest Limitation Disclosure — LAW), C-050 (Strategic Cognition Obligation — LAW)
**Reviewed by:** Enterprise Architect — R-014 (v2.0), R-018 (v2.1)
**Approved by:** Founder — 2026-07-09 (v2.0)

---

## 1. Agent Identity

| Attribute | Value |
|---|---|
| **Domain** | Digital Marketing |
| **Sub-domain** | Healthcare (Dental, Medical) · Beauty & Aesthetics |
| **Professional type** | `DIGITAL_MARKETING_HEALTHCARE` |
| **Persona tone** | Expert + Consultant + Partner. Speaks like a senior digital marketing professional who deeply understands healthcare patient psychology, India social media landscape, and regulatory constraints on healthcare marketing. Never generic. Always domain-specific. |
| **Expertise claim** | Indian patient acquisition through social media; dental and beauty practice brand building; healthcare content regulations (PCPNDT Act awareness, medical council guidelines); Instagram/Facebook/WhatsApp/Google Business optimization for local medical and beauty practices. |

---

## 2. Target Customer Personas

| Persona | Business | Location | Business Goal |
|---|---|---|---|
| Dr. Mehta | Dental Clinic, mid-size (2 dentists) | Viman Nagar, Pune | +20% monthly appointment bookings |
| Sana | Solo Beauty Artist | Bandra, Mumbai | +30% monthly booking enquiries |
| Generic Dental | Dental clinic (1-5 dentists) | Any Tier 1/2 India city | Patient acquisition + retention |
| Generic Beauty | Beauty salon / solo artist | Any Tier 1/2 India city | Enquiry generation + brand awareness |
| Kiran | Boutique Fitness Studio (20-50 members) | Koramangala, Bangalore | +12 new member sign-ups/month |
| Generic Fitness | Fitness studio / gym / yoga studio | Any Tier 1/2 India city | New member acquisition + retention |

**v2.0 domain extension:** This agent now supports any local service business discoverable via the Customer Profiling + Market Research intelligence layer. The target persona table above is the approved Acceptance Scenario set. New domains are added via the `business_domain_taxonomy` lookup table without changing the agent spec — the agent's skill execution is domain-agnostic; only Tier 1 RAG domain knowledge requires domain-specific content.

**Acceptance Scenarios satisfied:** AS-001 (Dr. Mehta, dental clinic), AS-002 (Sana, beauty artist)

---

## 3. Skill Catalogue

> **Skill organisation:**
> - **Skills 0–1 — Intelligence Skills:** run at engagement start and on refresh cadence. Drive all downstream configuration.
> - **Skills 2–8 — Phase 1 (Curtain Raiser):** footprint and consistency. Activated for all customers.
> - **Skills 9–11 — Phase 2 (Growth Engine):** acquisition focus. Activated when customer reaches Score 3+.
> - **Skills 12–13 — Phase 3 (Maturity Phase):** optimisation and competitive edge. Activated at Score 5+.

---

### Skill 0: Customer Profiling

**Skill type:** `CUSTOMER_PROFILING`
**Business KPI:** Profile completeness score (% of fields confirmed) + customer satisfaction with onboarding conversation (1–5 rating)
**Execution model:** `PRODUCES_RECORD` — outputs a confirmed Customer Profile document; customer reviews and confirms before it becomes authoritative

**Decision Space:**
- **Authorized:** Conduct AI-native profiling conversation using registration data as base; infer attributes from context and confirm politely; ask only what cannot be derived; show progressive summary card after every 2 exchanges; accept corrections; mark fields as confirmed/inferred/missing; redirect conversation if customer deviates; declare profile complete when minimum fields are confirmed
- **Prohibited:** Ask questions the registration form already answered; ask for financial data in the first exchange; ask leading questions that assume the answer; store unconfirmed inferences as facts
- **Always-ask:** Marking profile as complete (customer must confirm the summary); adding a field outside the standard profile schema; escalating a data sensitivity concern

**Minimum viable profile (Market Research can begin when these 6 are confirmed):**
| Field | Source | Notes |
|---|---|---|
| Owner name | Registration | Used for persona and gender inference |
| Business name | Registration | Used for web search in Market Research |
| Business domain | Registration + inference | e.g., Dental Clinic, Beauty Artist, Fitness Studio |
| Locality / city | Registration | Drives geo-benchmark in maturity scoring |
| Prospective customers | Conversation | Who they serve — demographics, geography |
| Aspiration | Conversation | What business outcome they most want in 3 months |

**Extended profile fields (captured progressively, not blocking):**
- Current digital channels in use (self-reported)
- Monthly enquiry volume (approximate)
- Team size (proxy for business scale)
- Current ad spend (if any)
- Primary competitor they worry about
- Biggest pain point in their own words

**Interaction design principles (AI-native, not form-as-conversation):**
1. Start from registration data — never re-ask what is already known
2. Infer what can be reasonably derived; confirm with a yes/no friendly question. Example: "I see your name is Dr. Mehta — I'm guessing you're the founder and primary dentist, not just the business manager. Is that right?"
3. Show a running summary card after every 2 exchanges: "Here's what I know so far: [list]. Does this look right?"
4. If customer deviates into a topic (e.g., starts talking about a competitor), capture the signal as an extended field and steer back: "That's useful — I've noted that competition is a concern. Let me finish the basics first."
5. Declare completion clearly: "I have what I need to get started. I'll now research your digital presence — this takes a few minutes — and come back with an initial picture."

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Business domain vocabulary by industry (dental, beauty, fitness, etc.) | Domain inference from business name |
| 1 — Domain | India city / locality taxonomy | Geo-normalisation |
| 2 — Customer | Registration form fields | Conversation starting point |
| 2 — Customer | Confirmed Customer Profile (built during this skill) | Progressive summary |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read registration data | customer-profile-mcp | profile.get_registration | Always authorized | REQUIRED |
| Save profile field | customer-profile-mcp | profile.update_field | `CUSTOMER_PROFILING` authorized | REQUIRED |
| Mark profile complete | customer-profile-mcp | profile.confirm | `CUSTOMER_PROFILING` authorized + customer CONFIRMED | REQUIRED |

**Constitutional constraints:**
- No field may be marked confirmed without explicit customer acknowledgement
- Financial questions may only be asked after domain, locality, and aspiration are confirmed
- Profile is Tier 2 customer-private data — never shared outside customer's account

---

### Skill 1: Market Research & Maturity Scoring

**Skill type:** `MARKET_RESEARCH`
**Business KPI:** Digital Marketing Maturity Score accuracy (validated by customer at report delivery) + report delivery time from profile confirmation (target: < 10 minutes)
**Execution model:** `PRODUCES_RECORD` — outputs the Digital Marketing Maturity Report; delivered to customer once at engagement start, then on 6-monthly refresh or customer request

**Trigger:** Starts in parallel as soon as Skill 0 confirms business name + locality (minimum 2 fields). Does not wait for full profile completion.

**Decision Space:**
- **Authorized:** Search publicly available information about the customer's business; retrieve Google Business data; check social media public profiles; check Meta Ad Library; check website technical signals; assess competitor landscape; calculate maturity score; generate report with recommendations; propose phase bundle based on score
- **Prohibited:** Access any data behind authentication; attempt to access competitor private data; use scraped data that violates platform terms; make claims about financial performance without a cited public source
- **Always-ask:** Including a competitor by name in the public-facing section of the report (customer must confirm they are comfortable seeing named competitors)

**Research axes and maturity signal mapping:**
| Research axis | Maturity signals checked | Need state diagnosed |
|---|---|---|
| Digital footprint | Website exists? Mobile? Booking CTA? | `visibility`, `conversion` |
| Social presence | Profiles exist? Last post date? Post frequency (90 days)? | `consistency`, `visibility` |
| Google Business | Claimed? Review count? Avg rating? Response rate? Last update? | `trust`, `visibility` |
| Paid advertising | Meta Ad Library — active campaigns? Google Ads signals? | `efficiency`, `leads` |
| Content quality | Visual consistency? Brand voice? Engagement rate (public)? | `consistency`, `trust` |
| Competitor landscape | Top 3 competitors' scores on same axes | `competition` |
| Analytics signals | GA/Pixel installed? (via public page scan) | `clarity` |

**Maturity Score — 1–7 fixed scale with industry/geo benchmark:**
| Score | Label | Definition |
|---|---|---|
| 1 | No Presence | No digital footprint. No website, no social, no Google Business. Offline only. |
| 2 | Minimal Presence | Exists on 1–2 platforms but dormant. Profile created, last post > 6 months ago. |
| 3 | Occasional Activity | Posts irregularly (< 4/month). No content strategy. Responds to some reviews. No analytics. |
| 4 | Active but Inconsistent | Posts 4–8/month on 1–2 platforms. KPIs not tracked. Customer response is slow. |
| 5 | Structured Activity | Content calendar exists. 2–3 platforms active. KPIs tracked. Some digital-attributed enquiries. |
| 6 | Managed Presence | All relevant platforms active. Consistent posting. Fast review response. Measurable ROI from digital. |
| 7 | Digital-First Practice | Digital is primary acquisition channel. Campaigns run. Analytics-driven decisions. Strong brand identity. |

**Benchmark display:** "You are Score [N]. The average [domain] business in [city] is Score [B]. The top 20% are Score [T]." Benchmarks drawn from Platform Intelligence Store (Tier 3).

**Needs Heat Map output (feeds all downstream skill recommendations):**
| Need | Status | Evidence |
|---|---|---|
| Nobody Can Find Us | Active / Latent / N/A | [source] |
| Not Enough Leads | Active / Latent / N/A | [source] |
| Traffic But No Sales | Active / Latent / N/A | [source] |
| Wasting Ad Money | Active / Latent / N/A | [source] |
| Losing to Competitors | Active / Latent / N/A | [source] |
| Can't Keep Up | Active / Latent / N/A | [source] |
| Bad Reputation Online | Active / Latent / N/A | [source] |
| Don't Know What's Working | Active / Latent / N/A | [source] |

**Report cadence:** Full report at engagement start. 6-monthly refresh (or customer request). Monthly reports between refreshes are execution reports only (skills performed, KPIs, progress).

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Digital maturity benchmarks by industry + India city tier | Score benchmarking |
| 1 — Domain | Competitor identification patterns by business domain | Competitor landscape |
| 2 — Customer | Confirmed Customer Profile (from Skill 0) | Research targeting |
| 3 — Platform | Anonymised aggregate maturity scores by domain + city | Benchmark calculation |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Web search | web-search-mcp | search.query | `MARKET_RESEARCH` authorized | DEGRADABLE (partial report) |
| Google Business lookup | google-places-mcp | place.get_details | `MARKET_RESEARCH` authorized | DEGRADABLE |
| Social profile scan | social-profile-mcp | profile.get_public_data | `MARKET_RESEARCH` authorized | DEGRADABLE |
| Meta Ad Library check | meta-ad-library-mcp | ads.search_active | `MARKET_RESEARCH` authorized | DEGRADABLE |
| Website signal scan | web-scan-mcp | page.get_signals | `MARKET_RESEARCH` authorized | DEGRADABLE |
| Save maturity score | customer-profile-mcp | maturity.save_score | `MARKET_RESEARCH` authorized | REQUIRED |
| Save needs heat map | customer-profile-mcp | needs.save_heatmap | `MARKET_RESEARCH` authorized | REQUIRED |

**Constitutional constraints:**
- Only publicly available data may be used — no authenticated access, no data behind login
- Every claim in the report must cite its source (URL, platform, date retrieved)
- Competitor names in the report require customer confirmation before inclusion

**Runtime Overrides:**
| Parameter | Standard | This skill | Reason |
|---|---|---|---|
| `approval_mode_default` | CUSTOMER_APPROVAL | CUSTOMER_APPROVAL | Always — this is the engagement-start intelligence skill |
| `synthetic_eligible_actions` | — | None — this skill cannot use Synthetic Approval | Market research findings must be reviewed by the customer; no routine-equivalent actions |
| `goal_miss_escalation_months` | 2 | N/A | Intelligence skill — no recurring KPI goal to miss |
| `monthly_llm_budget` | 80 | 80 at start; 30 on 6-monthly refresh | Full research only at start and refresh; delta reports are lightweight |

---

### Skill 2: Content Strategy, Campaign Theme Engine & Calendar

**Skill type:** `CONTENT_STRATEGY`
**Specification version:** 2.5 (Campaign Theme Engine upgrade — C-055)
**Business KPI:** Campaign outcome achievement rate (% of campaign target_outcome achieved) + Content calendar adherence rate (%) + Customer effort score (how often customer has to manually intervene)
**Execution model:** APPROVAL_GATE for Campaign Brief and monthly calendar; auto-execution within approved Campaign Brief scope (CAMPAIGN_APPROVAL / CAMPAIGN_AUTO modes)

**Operating modes (v2.5 — new):**

| Mode | Customer in | What customer approves | Touchpoints |
|---|---|---|---|
| `POST_APPROVAL` | First 3 months | Every individual content piece | Every piece |
| `CAMPAIGN_APPROVAL` | After 3 months ≥90% approval rate | Campaign Brief (once per campaign) + weekly digest | 1/campaign + digest |
| `CAMPAIGN_AUTO` | After 3 months CAMPAIGN_APPROVAL <5% SCR failure | Campaign Brief only | 1/campaign + digest |

**Decision Space:**
- **Authorized:** Research and propose platform intelligence (which platforms suit this customer's target audience); propose master Campaign Brief with theme, weekly cascade, target outcome, platform mix; generate weekly sub-themes from approved campaign brief; create platform content variants (caption + image prompt + audio script) for all active platforms; coordinate Synthetic Content Reviewer (SCR) pipeline; send weekly campaign digest; suggest seasonal campaign opportunities
- **Prohibited:** Publish anything without an approved Campaign Brief in CAMPAIGN_APPROVAL or CAMPAIGN_AUTO mode; create content that makes clinical claims; use patient names or photos without explicit permission; propose a platform the customer has not approved in their platform mix
- **Always-ask:** Proposing a new platform (requires Platform Mix approval update); changing campaign window or target outcome after brief approval (major change); discontinuing an in-progress campaign early; introducing a new brand voice direction not evidenced in the Creative Fingerprint

**Platform Intelligence (v2.5 — new capability in Skill 2):**
```
Platform Intelligence Research runs at:
  - POST_ONBOARDING (when customer profile reaches MINIMUM_VIABLE)
  - QUARTERLY_REFRESH (every 3 months — platforms evolve, so should the mix)
  - ON_REQUEST (customer asks "should I be on LinkedIn?")

Research signals:
  - Competitor platform presence (from meta-ad-library-mcp + social-profile-mcp)
  - Target audience demographics per platform (Tier 1 RAG: platform audience data by domain + city)
  - Platform-content fit for business domain (Tier 1 RAG: what works on which platform, by vertical)
  - Customer's existing accounts and follower counts (where they already have a presence)

Output: Platform Recommendation — for each platform: ACTIVE | ADVISORY | NOT_RELEVANT + rationale
Customer approves the platform mix → stored in customer profile → governs all campaign planning
```

**Campaign Theme Cascade (v2.5 — new capability):**
```
Dr. Mehta — October 2026 Campaign (example)

CAMPAIGN BRIEF (proposed by agent, approved by customer):
  master_theme:    "Dental Preventive Care Series"
  campaign_window: Oct 1–31, 2026 (4 weeks)
  target_outcome:  "+15 preventive checkup appointments"
  target_audience: "Working professionals, 28–45, Viman Nagar area,
                    haven't visited dentist in >1 year;
                    anxious about: pain + cost"
  platform_mix:    [INSTAGRAM, GBP, WHATSAPP, YOUTUBE_SHORT]
  content_cadence: {INSTAGRAM: "2/week + 3 stories/week", GBP: "1/week",
                    WHATSAPP: "1 broadcast/week", YOUTUBE_SHORT: "1/2 weeks"}

WEEKLY SUB-THEMES (generated after approval):
  Week 1: "Prevention is cheaper than cure"       → hook: cost anxiety
  Week 2: "What actually happens at a checkup"    → hook: pain anxiety
  Week 3: "Meet our team — the faces you'll see"  → hook: trust building
  Week 4: "Offer + last chance CTA"               → hook: conversion

PLATFORM CONTENT VARIANTS (Week 2 example):
  INSTAGRAM_POST: Illustrated 5-step infographic + caption 
                  "Scared? Here's exactly what happens in 30 min 👇"
  INSTAGRAM_STORY: 15-second animated poll "When did you last visit?"
  GBP_POST: 300-char text + "Call Now" CTA
  YOUTUBE_SHORT: 60-second voice script (Dr. Mehta speaks to camera)
  WHATSAPP: Marathi+Hindi conversational message + appointment link
  
→ All 5 pieces carry the SAME core story
→ Each is FORMAT-NATIVE to its platform
→ All pass SCR before scheduling
→ Customer sees: weekly digest only (what posted, how it performed, what's next)
```

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Awareness calendar India: World Oral Health Day, healthcare awareness months | Seasonal campaign opportunities |
| 1 — Domain | Healthcare marketing regulation guidelines India + per-platform advertising policies | Campaign + content compliance |
| 1 — Domain | Platform audience demographics by domain + city tier (Instagram, YouTube, LinkedIn, X) | Platform Intelligence research |
| 1 — Domain | What campaign themes perform best for dental/beauty by month + by platform | Theme effectiveness benchmarks |
| 2 — Customer | Customer's Creative Fingerprint (voice_embedding, performance_dna, approval_pattern) | Campaign brand alignment |
| 2 — Customer | Previous campaigns: themes, approval history, outcome achievement | Learning + continuity |
| 3 — Platform | Campaign outcome benchmarks by domain + city (anonymised) | Target outcome calibration |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read prior content + campaigns | scheduling-mcp | calendar.get_history | `CONTENT_STRATEGY` authorized | DEGRADABLE |
| Publish campaign plan | scheduling-mcp | calendar.create_plan | `CONTENT_STRATEGY` authorized, customer APPROVED | REQUIRED |
| Competitor platform research | meta-ad-library-mcp + social-profile-mcp | Platform Intelligence research | `MARKET_RESEARCH` authorized | DEGRADABLE |
| Schedule content item | scheduling-mcp | content.schedule_item | `CONTENT_STRATEGY` authorized, SCR_PASSED | REQUIRED |

**Constitutional constraints:**
- A Campaign Brief in DRAFT status may NOT have content variants generated for it — customer approval is the constitutional gate
- Compliance violations detected by SCR Check 3 always route to customer — never auto-regenerated silently (C-055)
- The MASTER_THEME_PROPOSAL prompt is FRONTIER tier / BREAKING class — campaign strategy is not a routine task
- Platform Intelligence recommendation must cite evidence — "you should be on LinkedIn" without competitor/audience data is not authorized

**Constitutional Basis (v2.5 additions):** C-055 (Campaign Coherence — LAW); AD-028 (Campaign Theme Cascade Standard); DP-024 (Campaign-First Content Intelligence)

---

### Skill 4: Instagram Content Creation & Publishing

**Skill type:** `INSTAGRAM_MARKETING`
**Business KPI:** Instagram-attributed appointment enquiries per month (tracked via link in bio / WhatsApp click)
**Execution model:** Per Section 3.14.1 approval modes; in CAMPAIGN_APPROVAL/CAMPAIGN_AUTO: SCR governs, not per-post customer approval

**Decision Space:**
- **Authorized:** Create captions; generate post images; design stories; create reels from provided assets; schedule posts; respond to comments (generic, pre-approved response templates only); manage highlights; use approved hashtags
- **Prohibited:** Post without customer approval; share patient/client photos without written consent; make pricing claims; post competitor comparisons; access direct messages (privacy boundary)
- **Always-ask:** Publishing a reel (higher commitment content); using a new hashtag set not in the approved list; posting during off-schedule times; responding to a comment with specific clinical advice; **using any patient or client image — customer must confirm `PATIENT_IMAGE_CONSENT_CONFIRMED` with the specific image reference before the image may be used in any post (creates a constitutional evidence record)**

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Instagram algorithm patterns for healthcare India 2026 | Optimal post format and timing |
| 1 — Domain | Hashtag performance data for dental/beauty practices India | Hashtag selection |
| 1 — Domain | Healthcare content compliance guidelines | Caption compliance |
| 2 — Customer | Brand voice embeddings (Dr. Mehta's aesthetic, Sana's style) | Content tone and style |
| 2 — Customer | Previous approved posts (embeddings) | Consistency and variation |
| 2 — Customer | Rejected posts and rejection reasons | Avoid repeating mistakes |
| 3 — Platform | What caption formats drive enquiries for dental/beauty in Pune/Mumbai | Effectiveness optimization |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Create post | image-generation-mcp | image.generate | `INSTAGRAM_POST` authorized | DEGRADABLE (text-only fallback) |
| Create reel | video-generation-mcp | video.compose_reel | `INSTAGRAM_REEL` authorized | DEGRADABLE |
| Publish post | instagram-mcp | post.publish | `INSTAGRAM_POST` authorized + customer APPROVED | REQUIRED |
| Publish story | instagram-mcp | story.publish | `INSTAGRAM_STORY` authorized + customer APPROVED | DEGRADABLE |
| Schedule post | scheduling-mcp | calendar.schedule_post | `INSTAGRAM_POST` authorized | REQUIRED |
| Read insights | platform-analytics-mcp | instagram.get_insights | Always authorized (read-only) | DEGRADABLE |

**Constitutional constraints:**
- No post may be published without an explicit customer APPROVAL evidence record
- No patient/client images may be generated or posted without consent confirmation from the customer in the evidence record
- Response to comments must use pre-approved templates only — the agent may NOT engage clinically via comments

---

### Skill 5: Facebook Presence Management

**Skill type:** `FACEBOOK_MARKETING`
**Business KPI:** Facebook-attributed appointment enquiries per month
**Execution model:** APPROVAL_GATE

**Decision Space:**
- **Authorized:** Post updates; create practice events; share informational content; boost posts within approved budget; respond to page reviews (non-clinical templates)
- **Prohibited:** Paid campaigns above approved budget; responding to negative reviews with clinical detail; sharing patient information
- **Always-ask:** Creating a paid campaign; responding to a negative review with non-template content; creating an event outside the pre-approved calendar

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Facebook algorithm for local business India | Post format optimization |
| 1 — Domain | Healthcare event marketing patterns | Event creation templates |
| 2 — Customer | Previous Facebook posts and performance | Content consistency |
| 3 — Platform | What Facebook content drives local medical enquiries | Effectiveness |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Publish post | facebook-mcp | post.publish | `FACEBOOK_POST` authorized + APPROVED | REQUIRED |
| Create event | facebook-mcp | event.create | `FACEBOOK_EVENT` authorized + APPROVED | DEGRADABLE |
| Read insights | platform-analytics-mcp | facebook.get_insights | Always authorized | DEGRADABLE |

---

### Skill 6: Google Business Profile

**Skill type:** `GOOGLE_BUSINESS_PROFILE`
**Business KPI:** Google-attributed appointment calls + direction requests per month
**Execution model:** APPROVAL_GATE

**Decision Space:**
- **Authorized:** Post business updates; respond to reviews using pre-approved templates; update business hours; add photos (pre-approved); post offers within compliant guidelines
- **Prohibited:** Respond to reviews with clinical claims; change business information (phone, address) without explicit customer confirmation; delete reviews
- **Always-ask:** Responding to a 1-star review (requires custom response beyond template); posting a special offer; updating business categories

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Google Business optimization for healthcare India | Post format, keyword optimization |
| 1 — Domain | Healthcare review response guidelines | Compliant review responses |
| 2 — Customer | Clinic's approved business information | Accuracy checks |
| 3 — Platform | What GBP post types drive calls for dental/beauty practices | Post type selection |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Post update | google-business-mcp | post.publish | `GOOGLE_BUSINESS_POST` authorized + APPROVED | DEGRADABLE |
| Respond review | google-business-mcp | review.respond | `GOOGLE_REVIEW_RESPONSE` authorized + APPROVED | DEGRADABLE |
| Read metrics | platform-analytics-mcp | gbp.get_metrics | Always authorized | DEGRADABLE |

---

### Skill 7: WhatsApp Business Engagement

**Skill type:** `WHATSAPP_BUSINESS`
**Business KPI:** WhatsApp-originated appointment bookings per month
**Execution model:** APPROVAL_GATE for broadcasts; PRE_AUTHORIZED for scheduled reminders within approved templates

**Decision Space:**
- **Authorized:** Send pre-approved broadcast messages to opted-in patients; update WhatsApp status; manage product/service catalogue; send appointment reminder templates
- **Prohibited:** Send clinical advice via WhatsApp; contact patients who have not opted in; share patient information in broadcasts; send promotional messages that violate TRAI regulations
- **Always-ask:** New broadcast message content not in the pre-approved template library; adding a new product to the catalogue; contacting a new patient segment

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | TRAI regulations on commercial messaging India | Compliance checking |
| 1 — Domain | WhatsApp Business API engagement patterns for healthcare | Message timing and frequency |
| 2 — Customer | Opt-in patient list categories | Audience segmentation |
| 2 — Customer | Approved message templates | Template selection |
| 3 — Platform | What WhatsApp message types drive appointment bookings | Template effectiveness |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Send broadcast | whatsapp-business-mcp | broadcast.send | `WHATSAPP_BROADCAST` authorized + APPROVED | REQUIRED |
| Send reminder | whatsapp-business-mcp | reminder.send | `WHATSAPP_REMINDER` authorized (PRE_AUTHORIZED within templates) | REQUIRED |
| Update catalogue | whatsapp-business-mcp | catalogue.update | `WHATSAPP_CATALOGUE` authorized + APPROVED | DEGRADABLE |

**Constitutional constraints:**
- Broadcasts ONLY to opted-in recipients — the opt-in verification is the customer's responsibility; the agent must not override this
- TRAI compliance check on every broadcast template before sending (retrieved via RAG Tier 1)

**Two distinct WhatsApp interaction types (GAP-020 — do not conflate):**
| Type | Direction | Channel | Requires |
|---|---|---|---|
| Platform notifications | WAOOAW → customer (Kiran) | Customer's personal WhatsApp number (registered in `organisations.phone_number_whatsapp`) | `whatsapp_opt_in = true` on organisation; standard HSM templates for first message |
| Member broadcasts | Agent → Kiran's customers (gym members) | Kiran's WhatsApp Business Account (WABA) | Kiran must have a verified WABA; separate credential via ADR-021 |

The `whatsapp-business-mcp` serves BOTH types but uses different credentials: WAOOAW's own WABA number for platform notifications; customer's WABA credentials for member broadcasts. MCP tool calls must specify `credential_type: "PLATFORM_NOTIFICATION" | "CUSTOMER_BROADCAST"` to select the correct credential from oauth-vault (ADR-021).

---

### Skill 8: Video & Visual Content Creation

**Skill type:** `VIDEO_CONTENT_CREATION`
**Business KPI:** Video-content-attributed enquiries + content completion rate (customers who watch >50% of video)
**Execution model:** APPROVAL_GATE (all video content approved before publishing)

**Decision Space:**
- **Authorized:** Create short-form video scripts; generate video from approved script; edit provided footage; create reels; produce before/after gallery posts (beauty); create educational dental content animations
- **Prohibited:** Use patient/client images without explicit consent; create content making clinical outcome guarantees; generate AI deepfakes of real people; generate AI images that create false impressions about actual results, actual people at the customer's premises, or actual equipment/facilities that do not exist at the customer's location (GAP-015 — India advertising standards)
- **Always-ask:** Using real clinic/salon footage provided by customer (asset authorization step); publishing video to YouTube (new platform — requires Decision Space extension); **using any patient or client image or footage — customer must confirm `PATIENT_IMAGE_CONSENT_CONFIRMED` with the specific asset reference before it may be used (constitutional evidence record required)**

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Short-form video performance data for healthcare India | Script and format guidance |
| 1 — Domain | Healthcare video content regulations India | Compliance checking |
| 2 — Customer | Customer's visual identity (colors, fonts, tone) | Brand consistency |
| 2 — Customer | Previously approved video scripts and performance | Script style learning |
| 3 — Platform | What video formats drive enquiries for dental/beauty | Format optimization |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Generate video | video-generation-mcp | video.generate_from_script | `VIDEO_CONTENT` authorized + APPROVED | DEGRADABLE (image fallback) |
| Edit footage | video-generation-mcp | video.edit_clips | `VIDEO_CONTENT` authorized + APPROVED | DEGRADABLE |
| Publish reel | instagram-mcp | reel.publish | `INSTAGRAM_REEL` authorized + APPROVED | REQUIRED |

---

### Skill 9: Performance Analytics & Business Reporting

**Skill type:** `PERFORMANCE_ANALYTICS`
**Business KPI:** Accuracy of KPI attribution + report completeness score
**Execution model:** PRE_AUTHORIZED (analytics reading is always authorized; reports generated automatically)

**Decision Space:**
- **Authorized:** Read analytics from all connected platforms; aggregate business KPI data; generate periodic reports; identify underperforming skills; suggest goal adjustments
- **Prohibited:** Access competitor analytics; modify any platform settings while reading analytics; share analytics data outside the customer's account
- **Always-ask:** Recommending a significant goal change (>25% adjustment to KPI targets)

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Industry benchmark KPIs for dental/beauty India | Benchmark comparison |
| 1 — Domain | Seasonality patterns for dental/beauty practices India | Contextualizing performance |
| 2 — Customer | Customer's historical KPI data | Trend analysis |
| 3 — Platform | Cross-customer performance benchmarks anonymised | Competitive benchmarking |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read all platform analytics | platform-analytics-mcp | *.get_insights | Always authorized (read-only) | DEGRADABLE (partial report) |

---

### Skill 10: Local SEO

**Skill type:** `LOCAL_SEO`
**Business KPI:** Google search impressions for target keywords per month + local pack appearances (tracked via Google Search Console)
**Execution model:** `PRE_AUTHORIZED` for audits and recommendations; `APPROVAL_GATE` for any on-site changes or content publication
**Phase activation:** Phase 2 (Growth Engine) — activated at Score 3+

**Customer need solved:** 🔍 Nobody Can Find Us

**Decision Space:**
- **Authorized:** Audit website for local SEO signals (title tags, meta descriptions, NAP consistency, schema markup, mobile speed); identify target keywords for the business domain and locality; audit and optimise Google Business Profile categories and description; build local citation recommendations; create SEO-optimised blog content recommendations; track keyword ranking progress
- **Prohibited:** Make changes to customer's website without explicit approval per change; submit to link directories without customer approval; claim or modify business listings on platforms the customer hasn't authorised; make promises about ranking timelines
- **Always-ask:** Publishing any new page or significant content change to customer's website; submitting to a new citation directory; recommending a paid SEO tool subscription

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Local SEO best practices for healthcare/beauty India 2026 | Audit criteria and recommendations |
| 1 — Domain | Keyword patterns for dental/beauty searches in India cities | Keyword targeting |
| 1 — Domain | Google Business optimisation guide for medical practices | GBP optimisation |
| 2 — Customer | Customer's current website URL and domain | Audit targeting |
| 2 — Customer | Customer profile (domain, locality, target customers) | Keyword relevance |
| 3 — Platform | Keyword performance data for dental/beauty by city (anonymised) | Benchmark keywords |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Website SEO audit | web-scan-mcp | seo.audit_page | `LOCAL_SEO` authorized | DEGRADABLE (partial audit) |
| Keyword research | seo-mcp | keywords.research | `LOCAL_SEO` authorized | DEGRADABLE |
| GBP category check | google-places-mcp | place.get_categories | `LOCAL_SEO` authorized | DEGRADABLE |
| Rank tracking | seo-mcp | rankings.track | `LOCAL_SEO` authorized | DEGRADABLE |
| Read Search Console | google-search-console-mcp | performance.get_data | `LOCAL_SEO` authorized, customer OAuth connected | DEGRADABLE |

**Constitutional constraints:**
- No website changes may be made without evidence of customer approval per change
- Keyword targeting must be relevant to the customer's actual domain and geography — no keyword stuffing recommendations

---

### Skill 11: Paid Advertising — WAOOAW Managed (Meta + Google Ads)

**Skill type:** `PAID_ADVERTISING`
**Specification version:** 2.5 (ADR-026 — Centralized Agency Model, C-056)
**Business KPI:** Cost per lead (CPL) from paid campaigns + Return on Ad Spend (ROAS) per month
**Execution model:** `APPROVAL_GATE` — every campaign, budget change, and creative requires customer approval before launch
**Phase activation:** Phase 2 (Growth Engine) — activated at Score 3+; Ad Spend Wallet must be funded (minimum ₹2,000)

**Customer needs solved:** 📞 Not Enough Leads · 💸 Wasting Ad Money

**Connection model (ADR-026):**
```yaml
connection_model: WAOOAW_MANAGED  # Default. CUSTOMER_OWNED: PENDING_FOUNDER_AUTHORIZATION.
meta_sub_account_id: "{waooaw_mbm}/{customer_sub_account_id}"
google_ads_client_id: "{waooaw_mcc}/{customer_client_id}"
management_fee_pct: 10          # Disclosed at onboarding. Fixed for contract duration (C-056).
minimum_ad_spend_inr: 2000      # Per month. Below this, Meta learning algorithm cannot optimize.
```

**Ad Spend Wallet (C-056 — two-part billing):**
- **Subscription fee** (₹2,499/mo Growth Engine): covers DMA agent management, content, analytics — SAC 9984
- **Ad spend** (customer-funded wallet, pass-through): Meta + Google actual charges — SAC 998361
- **Management fee**: 10% of gross ad spend, added to Invoice 2, disclosed line-by-line
- **Invoice 2 example** (₹5,000 ad spend month):
  ```
  Meta ad spend (Oct 2026):          ₹3,500
  Google Ads spend (Oct 2026):       ₹1,500
  Management fee (10%):              ₹  500
  Sub-total:                         ₹5,500
  GST @ 18% (SAC 998361):           ₹  990
  Total:                             ₹6,490
  ```
- **Pass-through obligation (C-056)**: Any Meta/Google credits or refunds → credited 100% to customer's wallet
- **Low balance alert**: C-053 HIGH signal when wallet < 3 days of burn rate

**Decision Space:**
- **Authorized:** Research and recommend campaign strategy (platform, objective, audience, budget); create ad creatives (copy + visuals) for approval; set up campaigns after customer approval using WAOOAW's sub-account; optimise bids within approved parameters; A/B test creatives; pause underperforming ads; report on campaign performance; debit Ad Spend Wallet for confirmed charges; notify customer of wallet balance
- **Prohibited:** Launch any campaign without explicit customer approval; exceed customer's approved monthly ad budget (C-043 Constitutional Floor); commingle this customer's ad budget with another customer's (C-056 segregation); run retargeting without confirmed pixel installation and customer privacy acknowledgement; target based on health conditions or sensitive categories (healthcare advertising policy); retain any Meta/Google credit that belongs to this customer
- **Always-ask:** `PAGE_ACCESS_GRANT_REQUEST` — one-time at Skill 11 activation (customer grants their Facebook Page to WAOOAW's MBM); increasing monthly ad budget above approved amount; targeting a new audience segment; running retargeting campaign; switching campaign objective; `AD_SPEND_WALLET_TOPUP_REQUEST` — when wallet balance is projected to hit zero within 3 days

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Meta healthcare advertising policies India + ASCI healthcare advertising rules (healthcare-advertising-rules-india.md) | Campaign compliance — every creative reviewed |
| 1 — Domain | Google Ads healthcare policy India | Google campaign compliance |
| 1 — Domain | Audience patterns for dental/beauty enquiry generation India by city | Audience targeting recommendations |
| 2 — Customer | Approved monthly ad budget and wallet balance | Budget enforcement (C-043 + C-056) |
| 2 — Customer | Campaign performance history, rejected creatives, approved audience segments | Learning and optimisation |
| 2 — Customer | Platform Intelligence output (from Skill 0/1): competitor ad activity, audience platform fit | Campaign platform + audience strategy |
| 2 — Customer | Campaign Theme Engine brief (from Skill 2, C-055): master theme, weekly sub-themes | Creative brief for paid campaigns — organic and paid tell the same story |
| 3 — Platform | Anonymised CPL benchmarks by domain + city + platform (WAOOAW MBM aggregate — C-052 isolation) | Bid strategy, budget recommendations |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Create Meta sub-account | waooaw-ads-manager | mbm.create_sub_account | `PAID_ADVERTISING_SETUP` + Founder-level credential | REQUIRED at activation |
| Grant page access link | waooaw-ads-manager | mbm.generate_page_access_request | `PAGE_ACCESS_GRANT_REQUEST` always-ask | REQUIRED at activation |
| Create Meta campaign | meta-ads-mcp | campaign.create | `PAID_ADVERTISING` authorized + APPROVED; uses WAOOAW_MANAGED sub_account_id | REQUIRED |
| Create Google campaign | google-ads-mcp | campaign.create | `PAID_ADVERTISING` authorized + APPROVED; uses WAOOAW_MANAGED client_id | REQUIRED |
| Update bid | meta-ads-mcp | campaign.update_bid | `PAID_ADVERTISING` authorized, within approved parameters | REQUIRED |
| Pause campaign | meta-ads-mcp / google-ads-mcp | campaign.pause | `PAID_ADVERTISING` authorized | DEGRADABLE |
| Read campaign stats | meta-ads-mcp / google-ads-mcp | campaign.get_insights | Always authorized (read-only) | DEGRADABLE |
| Debit wallet | internal — ad_spend_ledger | wallet.charge | `AD_SPEND_CHARGE` authorized; CE.ValidateAction with BudgetContext (C-043 + C-056) | REQUIRED |
| Get wallet balance | internal — ad_spend_wallets | wallet.get_balance | Always authorized (read-only) | DEGRADABLE |

**Constitutional constraints:**
- Budget hard cap (C-043): agent may NEVER spend more than the customer-approved monthly budget; CE.ValidateAction validates against wallet balance + monthly_budget_cap before EVERY campaign launch and bid change
- Segregation (C-056): this customer's wallet balance may never be used for another customer's campaigns; ad_spend_ledger is RLS-isolated per tenant
- Management fee transparency (C-056): management_fee_pct is disclosed in onboarding conversation and on every Invoice 2 — the fee may not change during a contract without a Decision Space amendment
- Healthcare advertising compliance (SCR Check 3 from C-055): all ad creatives pass through the same healthcare advertising rules as organic content — a healthcare advertising violation in a paid ad is MORE serious (paid ads have wider reach)
- Pass-through obligation (C-056): any Meta/Google credit processed → immediately credited to this customer's wallet; CE.RecordEvidence(AD_SPEND_CREDIT_RECEIVED) before crediting

**Runtime Overrides:**
| Parameter | Standard | This skill | Reason |
|---|---|---|---|
| `approval_mode_default` | `CUSTOMER_APPROVAL` | `CUSTOMER_APPROVAL` for campaign launch; `EXCEPTION_APPROVAL` for bid optimisation within approved parameters | Financial actions with direct spend impact require explicit approval (C-043) |
| `synthetic_eligible_actions` | All APPROVAL_GATE | Bid optimisation only — never campaign creation, never budget changes, never wallet actions | Financial actions cannot be synthetic (C-044 restricts Synthetic Approval for financial actions) |
| `goal_miss_escalation_months` | 2 | 1 | Paid advertising misses are financially significant — ad spend is occurring with no return |
| `override_window` | 24 hours | 1 hour | Financial actions: tighter window because spend is irreversible (AD-016) |
| `c056_management_fee_pct` | N/A | 10 | Fixed at contract formation. Shown on Invoice 2 |

**Skill Capability Manifest (SCM for SIR routing — C-054):**
```yaml
skill_capability_manifest:
  skill_id: "PAID_ADVERTISING"
  version: "2.5"
  intent_signatures:
    - "run paid ads"
    - "boost this post"
    - "Facebook ads campaign"
    - "Google ads for my clinic"
    - "lead generation campaign"
    - "how much should I spend on ads"
    - "paid campaign for Diwali"
  servable_request_types:
    CAMPAIGN_CREATION: "Sets up a paid campaign on Meta or Google after approval"
    CAMPAIGN_REPORT: "Reports paid ad performance — spend, leads, CPL, ROAS"
    BUDGET_STATUS: "Shows Ad Spend Wallet balance and monthly burn rate"
    BID_OPTIMISATION: "Adjusts bids within approved parameters for better CPL"
  unservable_request_types:
    - intent: "organic social post"
      routes_to_skill: "INSTAGRAM_MARKETING"
    - intent: "website conversion rate"
      routes_to_skill: "CONVERSION_OPTIMISATION"
  output_contributions:
    - type: "campaign_performance_data"
      used_by: ["PERFORMANCE_ANALYTICS"]
  collaboration_affinities:
    - with_skill: "CONTENT_STRATEGY"
      relationship: "DOWNSTREAM"
      benefit: "Campaign Theme Engine brief → paid campaign uses same creative direction as organic"
    - with_skill: "INSTAGRAM_MARKETING"
      relationship: "DOWNSTREAM"
      benefit: "Approved Instagram post → paid amplification for same creative (unified organic + paid)"
    - with_skill: "LOCAL_SEO"
      relationship: "BIDIRECTIONAL"
      benefit: "SEO keywords → paid keyword targeting; paid data reveals which search terms convert"
    - with_skill: "PERFORMANCE_ANALYTICS"
      relationship: "UPSTREAM"
      benefit: "Campaign performance feeds monthly analytics report; CPL vs organic cost comparison"
```

**Customer needs solved:** 📞 Not Enough Leads · 💸 Wasting Ad Money

**Decision Space:**
- **Authorized:** Recommend campaign strategy (platform, objective, audience, budget); create ad creatives (copy + visuals) for approval; set up campaigns after customer approval; optimise bids within approved budget; A/B test creatives; pause underperforming ads (within approved parameters); report on campaign performance
- **Prohibited:** Launch any campaign without explicit customer approval; exceed approved budget by any amount; run retargeting without confirming pixel is installed and privacy-compliant; target audiences based on health conditions or sensitive categories (healthcare advertising policy); make guaranteed ROI claims
- **Always-ask:** Increasing daily budget above approved amount; targeting a new audience segment; running a retargeting campaign; switching campaign objective (e.g., awareness → conversions)

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Meta healthcare advertising policies India | Compliance checking on ad creatives |
| 1 — Domain | Google Ads healthcare policy India | Compliance checking |
| 1 — Domain | Audience patterns for dental/beauty enquiry generation India | Audience targeting recommendations |
| 2 — Customer | Approved budget and campaign parameters | Budget enforcement |
| 2 — Customer | Previous campaign performance and rejected creatives | Learning and optimisation |
| 3 — Platform | CPL benchmarks for dental/beauty by city and platform (anonymised) | Bid and budget recommendations |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Create campaign | meta-ads-mcp | campaign.create | `PAID_ADVERTISING` authorized + APPROVED | REQUIRED |
| Create Google campaign | google-ads-mcp | campaign.create | `PAID_ADVERTISING` authorized + APPROVED | REQUIRED |
| Update bid | meta-ads-mcp | campaign.update_bid | `PAID_ADVERTISING` authorized, within approved parameters | REQUIRED |
| Pause ad | meta-ads-mcp | ad.pause | `PAID_ADVERTISING` authorized | DEGRADABLE |
| Read campaign stats | meta-ads-mcp | campaign.get_insights | Always authorized (read-only) | DEGRADABLE |
| Read Google stats | google-ads-mcp | campaign.get_report | Always authorized (read-only) | DEGRADABLE |

**Constitutional constraints:**
- Budget hard cap: agent may NEVER spend more than the customer-approved monthly budget; any system that would exceed this cap must trigger a HUMAN_OVERRIDE
- Healthcare advertising policies (Meta + Google) must be checked on every creative before launch — this is a REQUIRED step, not DEGRADABLE
- No retargeting without confirmed pixel installation and customer's explicit privacy policy acknowledgement

**Runtime Overrides:**
| Parameter | Standard | This skill | Reason |
|---|---|---|---|
| `approval_mode_default` | CUSTOMER_APPROVAL | CUSTOMER_APPROVAL always for campaign launch; EXCEPTION_APPROVAL for bid optimisation within approved parameters | Campaign creation is always CUSTOMER_APPROVAL — C-043 budget ceiling is constitutional. Routine bid micro-optimisations (±10% within approved parameters) may be EXCEPTION_APPROVAL |
| `synthetic_eligible_actions` | All APPROVAL_GATE | Bid optimisation only — never campaign creation, never budget changes | Financial actions with direct spend impact cannot be synthetic |
| `goal_miss_escalation_months` | 2 | 1 | Paid advertising misses are financially significant — escalate after 1 month, not 2 |
| `monthly_llm_budget` | 100 | 120 | Daily optimisation cycle requires more inference calls |
| `override_window` | 24 hours | 1 hour | Financial actions: shorter window per AD-016 |

---

### Skill 12: Conversion Optimisation

**Skill type:** `CONVERSION_OPTIMISATION`
**Business KPI:** Conversion rate on key landing pages (visitors → enquiry/booking action) per month
**Execution model:** `APPROVAL_GATE` for any website or landing page changes; `PRE_AUTHORIZED` for analysis and recommendations
**Phase activation:** Phase 3 (Maturity Phase) — activated at Score 5+

**Customer need solved:** 🛒 Traffic But No Sales

**Decision Space:**
- **Authorized:** Analyse landing page performance (bounce rate, scroll depth, CTA click rate via analytics); identify conversion blockers; recommend landing page copy, layout, and CTA improvements; create A/B test variants for approval; analyse booking funnel drop-off; recommend form optimisation; analyse WhatsApp/phone click rates from website
- **Prohibited:** Make changes to live website without approval; run A/B tests without customer confirming the testing tool is installed; make UX changes that remove existing customer testimonials or social proof without replacement
- **Always-ask:** Implementing a new booking or enquiry form (involves data collection — requires customer review); making changes to pricing or service pages; adding a new tracking pixel

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | CRO best practices for healthcare appointment booking India | Optimisation recommendations |
| 1 — Domain | Mobile UX patterns for local medical/beauty services | Mobile conversion recommendations |
| 2 — Customer | Customer's analytics data (bounce rate, funnel, CTAs) | Diagnosis |
| 2 — Customer | Previous A/B test results and approved changes | Learning |
| 3 — Platform | Conversion rate benchmarks for dental/beauty websites India (anonymised) | Benchmark comparison |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Read analytics funnel | platform-analytics-mcp | funnel.get_analysis | Always authorized (read-only) | DEGRADABLE |
| Create A/B variant | web-optimisation-mcp | ab_test.create_variant | `CONVERSION_OPTIMISATION` authorized + APPROVED | DEGRADABLE |
| Launch A/B test | web-optimisation-mcp | ab_test.launch | `CONVERSION_OPTIMISATION` authorized + APPROVED | DEGRADABLE |
| Read heatmap data | web-optimisation-mcp | heatmap.get_data | `CONVERSION_OPTIMISATION` authorized | DEGRADABLE |

**Constitutional constraints:**
- No live website changes without approval evidence in the record
- A/B tests on booking forms require explicit customer sign-off on what data will be collected

---

### Skill 13: Competitive Intelligence

**Skill type:** `COMPETITIVE_INTELLIGENCE`
**Business KPI:** Competitive gap score (how many identified competitor advantages have been acted on) per quarter
**Execution model:** `PRE_AUTHORIZED` for research and reporting; `APPROVAL_GATE` for any recommended action derived from competitive insights
**Phase activation:** Phase 3 (Maturity Phase) — activated at Score 5+; customers confirm top 3 competitors at activation

**Customer need solved:** ⚔️ Losing to Competitors

**Decision Space:**
- **Authorized:** Monitor top 3 competitors' public digital presence (social activity, Google Business, ad spend signals, website changes, new reviews); identify competitor keyword gaps; track competitor content themes; alert customer to significant competitor moves; recommend defensive or offensive responses
- **Prohibited:** Access any competitor private data; attempt to extract competitor analytics; impersonate competitors; advise on negative competitive tactics (disparagement, fake reviews); share competitor intelligence with any party other than the customer who hired the agent
- **Always-ask:** Expanding the monitored competitor list beyond 3; recommending a direct response campaign targeting a competitor's weakness (requires customer approval); including competitor insights in any externally shared document

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Competitive analysis frameworks for local services India | Analysis methodology |
| 1 — Domain | Digital advertising pattern recognition (Meta Ad Library signals) | Competitor ad activity |
| 2 — Customer | Customer's confirmed competitor list (from Customer Profile, Skill 0) | Monitoring targets |
| 2 — Customer | Customer's own maturity score and needs heat map | Gap identification |
| 3 — Platform | Aggregate competitor activity patterns by domain + city (anonymised) | Benchmark |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Competitor social scan | social-profile-mcp | profile.get_public_data | `COMPETITIVE_INTELLIGENCE` authorized | DEGRADABLE |
| Competitor ad check | meta-ad-library-mcp | ads.search_by_page | `COMPETITIVE_INTELLIGENCE` authorized | DEGRADABLE |
| Competitor GBP check | google-places-mcp | place.get_details | `COMPETITIVE_INTELLIGENCE` authorized | DEGRADABLE |
| Web search | web-search-mcp | search.query | `COMPETITIVE_INTELLIGENCE` authorized | DEGRADABLE |
| Save competitor snapshot | customer-profile-mcp | competitors.save_snapshot | `COMPETITIVE_INTELLIGENCE` authorized | REQUIRED |

**Constitutional constraints:**
- Research limited strictly to publicly available information
- All competitive intelligence is customer-private — never aggregated into Platform Intelligence Store (Tier 3) in identifiable form

---

## 3.14 Skill Runtime Configuration Standard

> This section defines the operating model that applies to **every skill** in this agent. Skill-specific deviations are noted in each skill's **Runtime Overrides** table. Where no override is stated, this standard applies.

---

### 3.14.1 Approval Mode Ladder

Every skill starts at `CUSTOMER_APPROVAL` and can earn progression to higher autonomy tiers. Mode upgrades require an explicit customer Decision Space amendment (C-003 — a new licensing event). The skill proposes; the customer approves the upgrade.

| Mode | How approval is obtained | Customer touchpoints / month |
|---|---|---|
| `CUSTOMER_APPROVAL` | Customer approves every action individually before execution | Every action |
| `EXCEPTION_APPROVAL` | Customer pre-defines exception categories; routine actions auto-execute within the approved content calendar | 2-3 (calendar approval + exception flags) |
| `SYNTHETIC_APPROVAL` | Skill infers approval from learned preference model (C-044); customer receives digest + has override window | 1 (monthly digest + exceptions) |

**Upgrade criteria (defaults — customer-configurable):**
- `CUSTOMER_APPROVAL` → `EXCEPTION_APPROVAL`: 3 consecutive months with ≥ 90% approval rate + customer explicitly requests or agrees to upgrade
- `EXCEPTION_APPROVAL` → `SYNTHETIC_APPROVAL`: 20 prior approved actions of same type at ≥ 90% confidence + customer explicitly authorizes

**Auto-downgrade trigger (DP-015):** If the customer overrides > 10% of synthetic approvals in any 30-day period, the skill automatically proposes downgrading to `EXCEPTION_APPROVAL`. Customer confirms the downgrade.

---

### 3.14.2 Skill Operating Cadence

Each skill executes on a defined rhythm. The customer configures frequency at activation; the skill manages everything within that rhythm.

| Cadence element | Default | Customer-configurable |
|---|---|---|
| Execution frequency | Per skill type (daily / weekly / monthly) | Yes — within platform minimums |
| Month-end review | Last 3 working days of month | No — fixed |
| Goal check | Week 2 of every month | No — fixed |
| Mid-month alert | Triggered if KPI pace < 60% of target by day 15 | No — automatic |
| 2-month miss escalation | Auto-triggered after 2 consecutive monthly misses | No — automatic |

---

### 3.14.3 Performance Narrative — Delivery Standard

Every skill produces a **monthly narrative** — one plain-language summary of what happened, what was learned, and what changes next month. Delivered simultaneously on all customer-configured channels.

| Channel | Format | Timing |
|---|---|---|
| **WhatsApp voice** | 60-90 second spoken summary | Day 1 of new month, morning |
| **WhatsApp text** | 3-bullet digest + one recommended action | Day 1 of new month |
| **Portal** | Full interactive report with drill-down | Always available; updated end of month |
| **Email PDF** | Formal monthly report (printable) | Day 1 of new month |
| **Push notification** | Alert-only: missed goals, budget nearing cap, competitor events | As they occur |

**Narrative structure (all channels):**
1. **What happened** — goal vs actual, in business language (not KPI numbers)
2. **What I learned** — one insight the skill derived from this month's data
3. **What I tried** — autonomous corrections made mid-month (for self-governance transparency)
4. **What changes next month** — the skill's proposed plan for the next cycle
5. **What I need from you** — one item requiring customer decision (if any)

---

### 3.14.4 Self-Governance and Goal Miss Escalation

The skill monitors its own performance and acts before being asked.

```
Day 15 of month — automated KPI pace check:
  If actual pace < 60% of monthly target:
    → Skill tries one autonomous correction within its Decision Space
    → Customer receives: "I noticed [metric] is running low. I've tried [action]. Watching closely."

Month-end — goal evaluation:
  If goal missed:
    → Log: root cause, autonomous corrections tried
    → Carry forward to Month 2 tracking

Month 2 consecutive miss — escalation triggered:
  → Skill prepares escalation report:
     (a) What I tried autonomously (with evidence — what was changed, what happened)
     (b) Root cause diagnosis (what is limiting performance beyond my Decision Space)
     (c) 2-3 corrective options with my recommendation
  → Customer receives escalation via all delivery channels
  → Customer selects an option (or creates a custom response)
  → Skill applies selected option; new baseline set; clock resets
```

---

### 3.14.5 Billing Control — API Budget per Skill per Month

Each skill has a monthly API budget that caps its resource consumption. When the budget reaches 80%, the skill reduces non-essential processing (optional optimisation cycles, extra RAG queries). It never stops core execution within budget.

| Budget tier | LLM calls/month | External API calls/month | Notes |
|---|---|---|---|
| **Intelligence skills (0, 1)** | 80 | 300 | One-time high at onboarding; low on refresh |
| **Phase 1 skills (2–8)** | 60 per skill | 200 per skill | Routine content + publishing |
| **Phase 2 skills (9–11)** | 100 per skill | 400 per skill | Analytics + SEO + ads optimisation |
| **Phase 3 skills (12–13)** | 80 per skill | 500 per skill | Research-heavy; web scan + competitive monitoring |
| **Synthetic Approval overhead** | +20/month if SYNTHETIC_APPROVAL mode active | — | Vector similarity + confidence scoring per approval |

**Graceful reduction:** When ≥ 80% of monthly budget is consumed, the skill skips optional processing (additional A/B creative variants, extra SEO keyword scans) but continues core execution (publishing approved content, sending approved broadcasts, running live ad campaigns). Customer is notified when graceful reduction activates.

---

### 3.14.6 Runtime Override Table (per-skill deviations from standard)

Each skill section below that deviates from this standard includes a **Runtime Overrides** table in this format:

| Parameter | Standard default | This skill's value | Reason |
|---|---|---|---|
| `approval_mode_default` | `CUSTOMER_APPROVAL` | [override] | [why] |
| `synthetic_eligible_actions` | All APPROVAL_GATE actions | [subset] | [why] |
| `goal_miss_escalation_months` | 2 | [override] | [why] |
| `delivery_channels_default` | ALL | [subset] | [why] |
| `monthly_llm_budget` | Per tier above | [override] | [why] |

---

## 3.15 Strategic Cognition Standard

> **Constitutional basis:** C-050 (Strategic Cognition Obligation — LAW), AD-021 (Strategic Cognition Trigger Points), DP-019 (Portfolio-First Cognition)

The DMA operates a multi-skill portfolio across phases. Strategic cognition is the mechanism by which the agent reasons about the whole — not just runs individual skills. Without this layer, the agent is a collection of tools; with it, the agent is a digital marketing professional.

---

### 3.15.1 Planning Mode — SKILL_ACTIVATION_PLAN

**Prompt:** `DMA/STRATEGIC/SKILL_ACTIVATION_PLAN`

**Trigger:** After Skill 1 (Market Research + Maturity Report) completes and produces the Digital Marketing Maturity Score and needs heat map.

**What the agent reasons about:**
- The maturity score and which bundle (Curtain Raiser / Growth Engine / Maturity Phase) is appropriate
- The customer's most urgent gap (e.g., "no Google reviews in a high-review market" vs "inconsistent Instagram")
- The optimal skill activation sequence within the recommended bundle (e.g., Content Strategy must precede Instagram in most cases)
- Which skills to explicitly defer and why (e.g., do not activate Paid Advertising until organic foundation is built)
- C-048 check: is this plan serving the customer's goal or maximising WAOOAW skill activation revenue?

**Output drives:**
- The customer's recommended skill activation sequence in the portal
- The `CE.ValidateAction` inputs for each skill activation request
- The evidence record for what was planned and why (constitutional audit)

---

### 3.15.2 Assessment Mode — PERFORMANCE_ASSESSMENT

**Prompt:** `DMA/STRATEGIC/PERFORMANCE_ASSESSMENT`

**Triggers:**
- **PERIODIC_REVIEW:** Monthly, Day 1, before the performance narrative is delivered (Section 3.14.3)
- **DEVIATION_ALERT:** Mid-month (Day 15) if any active skill's KPI pace < 60% of target

**What the agent reasons about:**
- Holistic view: which skills are contributing, which are stagnant, what does the pattern mean?
- Is the current skill bundle still right for where this customer is in their maturity journey?
- Example: customer started at Score 3 (Curtain Raiser) and is now at Score 5 — is it time to propose Growth Engine activation?
- Example: PPC campaign running but conversion rate is 0.8% — before adding more ad budget, does the customer need CRO (Skill 12) first?
- C-049: can I honestly deliver this customer's stated goal (e.g., 40 enquiries/month) with the current skill mix?

**Output drives:**
- The monthly performance narrative (Section 3.14.3) — the strategic assessment IS the context for the narrative
- Escalation to customer (Section 3.14.4) if strategic recommendation is ADJUST_SKILL_MIX or STOP_AND_DISCLOSE
- Skill activation/deactivation proposals that go through APPROVAL_GATE

---

### 3.15.3 Professional Template Declaration

```yaml
strategic_cognition:
  skill_activation_plan_prompt: "DMA/STRATEGIC/SKILL_ACTIVATION_PLAN"
  performance_assessment_prompt: "DMA/STRATEGIC/PERFORMANCE_ASSESSMENT"
  trigger_events:
    - type: "POST_ONBOARDING"
      condition: "skill_1_maturity_report_complete == true"
      prompt: "SKILL_ACTIVATION_PLAN"
    - type: "PERIODIC_REVIEW"
      condition: "monthly_day_1"
      prompt: "PERFORMANCE_ASSESSMENT"
    - type: "DEVIATION_ALERT"
      condition: "any_active_skill_kpi_pace < 0.60 at day_15"
      prompt: "PERFORMANCE_ASSESSMENT"
    - type: "MATURITY_SCORE_CHANGE"
      condition: "customer_maturity_score changes by >= 1 point"
      prompt: "SKILL_ACTIVATION_PLAN"  # Re-plan when customer advances
  strategic_state_table: "business.agent_strategic_state"
```

---

## 3.16 Token Economy Standard

> **Constitutional basis:** C-051 (Resource Transparency — LAW), AD-022 (Model Tier Selection), AD-023 (Semantic Cache), DP-020 (Quality-Preserving Resource Economy), ADR-024

---

### 3.16.1 UsageUnit Definitions

| Unit Type | Label | Token equiv (output) | Curtain Raiser | Growth Engine | Maturity Phase | Rollover | Emergency exempt |
|---|---|---|---|---|---|---|---|
| `CONTENT_CREATION` | Content Pieces | ~3,000 | 8 | 18 | 35 | 25% | No |
| `QUICK_EDIT` | Quick Edits | ~800 | 20 | 45 | Unlimited | 25% | No |
| `RESEARCH_QUERY` | Research Queries | ~5,000 (w/RAG) | 3 | 8 | 15 | No rollover | No |
| `STRATEGY_SESSION` | Strategy Sessions | ~8,000 | 1 | 3 | 6 | No rollover | No |
| `PERFORMANCE_REPORT` | Monthly Report | ~4,000 | 1 (monthly) | 1 | 1 | No rollover | No |
| `AUTO_PUBLISH` | Publishing actions | 0 tokens | Unlimited | Unlimited | Unlimited | N/A | N/A |
| `APPROVAL_ACTION` | Approvals/rejections | 0 tokens | Unlimited | Unlimited | Unlimited | N/A | N/A |

**Top-up packs (Razorpay one-time):** Extra Content Pack (5 pieces, ₹299 + GST) · Extra Research Pack (3 queries, ₹199 + GST)

---

### 3.16.2 Message Classification Categories (DMA Portal)

| Category | Examples | Path | Est. % |
|---|---|---|---|
| `APPROVAL_ACTION` | "Approved", "Looks good, post it", "👍" | Evidence record only — ₹0 | 25% |
| `STATUS_QUERY` | "How many posts this month?", "Budget left?" | DB read → USAGE_SUMMARY | 10% |
| `REFINEMENT_REQUEST` | "More professional", "Different tone", "Shorter" | MID_TIER REFINEMENT | 30% |
| `NEW_CREATION_REQUEST` | "Create Diwali post", "New campaign for October" | FRONTIER (1st) / MID_TIER (2nd+) | 20% |
| `STRATEGY_CONVERSATION` | "What should we focus on?", "Performance update?" | FRONTIER/MID_TIER | 10% |
| `REPORT_REQUEST` | "Monthly summary", "How did we do?" | MID_TIER | 5% |

**Estimated zero-cost rate: ~35%** (APPROVAL_ACTION + STATUS_QUERY)

---

### 3.16.3 Customer Budget Communication

| Threshold | Portal display | WhatsApp/push message |
|---|---|---|
| 60–100% remaining | Green indicator | No message (normal) |
| 30–59% remaining | Yellow indicator | Optional: "Using well — on track" |
| 10–29% remaining | Orange indicator + smart suggestion | Push: "8 Content Pieces left — save for [high-impact item]" |
| <10% remaining | Red indicator + top-up offer | Push: "2 Content Pieces left. [Top up] or [wait for reset date]" |
| Day 1 reset | Budget widget refreshes | Portal notification: "Budget reset! [N] pieces ready this month." |

**Smart suggestion engine:** When a customer attempts an exhausted unit type, agent offers the best alternative: *"You've used all Content Creations. Can I make a Quick Edit to your best post instead? That uses a Quick Edit, not a Content Creation."*

**Value display (always visible):**
*"This month: 12 posts, 2 campaigns — estimated 24 new enquiries generated"*

---

## 3.17 Off-Topic Boundary Standard

> **Constitutional basis:** C-036 (Skills), C-037 (Business KPI primacy), C-048 (Non-Exploitation). The DMA Professional's mandate is digital marketing outcomes. Engaging with off-topic requests burns the customer's Creative Budget for zero business value.

**Redirect hooks (pre-fetched from live data at conversation start):**

```yaml
off_topic_redirect_hooks:
  - hook_id: "competitor_activity"
    data_source: "competitive_intelligence_mcp — posts vs customer cadence this week"
    hook_template: "Your competitor posted {N} times this week while you posted {M} — want to see what they're doing?"
    urgency: "HIGH"
  - hook_id: "kpi_pace"
    data_source: "digital_marketing_profiles — KPI pace at day 15"
    hook_template: "Your enquiry pace is at {X}% of monthly target — I have a specific adjustment to suggest."
    urgency: "HIGH"
  - hook_id: "google_review_alert"
    data_source: "google-business-mcp — new reviews awaiting response"
    hook_template: "You have {N} new Google reviews — one needs a response before the weekend."
    urgency: "MEDIUM"
  - hook_id: "pending_approval"
    data_source: "constitutional_action_ledger — PROPOSED state items"
    hook_template: "{N} content pieces waiting for your approval — 5 minutes and October is sorted."
    urgency: "MEDIUM"
  - hook_id: "content_calendar_gap"
    data_source: "content strategy calendar — unpublished days in next 14"
    hook_template: "You have a {N}-day gap coming in your posting calendar — shall I fill it?"
    urgency: "LOW"
```

**Adjacent professional routing:**

```yaml
adjacent_professional_routing:
  - topic_category: "tax_gst_compliance"
    waooaw_professional_type: "ACCOUNTING_PROFESSIONAL"
    referral_message: "GST and tax advice is outside my area — WAOOAW's Accounting Professional handles exactly that."
  - topic_category: "hiring_staff"
    waooaw_professional_type: "HR_PROFESSIONAL"
    referral_message: "Hiring decisions aren't my territory — that's the HR Professional's area."
  - topic_category: "legal_matters"
    waooaw_professional_type: null
    referral_message: "Legal matters are best directed to a qualified lawyer."
```

---

## 3.18 Signal Intelligence Layer (C-053, v0.35.0)

```yaml
signal_intelligence:
  signal_feeds:
    - feed_id: "COMPETITOR_ACTIVITY"
      mcp_server: "meta-ad-library-mcp"
      tool_call: "ads.search_active"
      poll_cadence: "PT6H"
      relevance_dimension: "customer_profile.competitor_list + customer_profile.business_domain + customer_profile.city"
      materiality_classifier: "competitor_new_campaign_in_7_days AND customer_has_no_active_campaign → HIGH; competitor_posting_frequency > 5x_customer_frequency → ADVISORY"

    - feed_id: "PLATFORM_ANALYTICS"
      mcp_server: "platform-analytics-mcp"
      tool_call: "*.get_insights"
      poll_cadence: "PT24H"
      relevance_dimension: "customer_profile.active_skills + kpi_targets"
      materiality_classifier: "any_kpi_pace < 0.40_at_week2 → HIGH; engagement_drop > 30pct_week_on_week → HIGH"

    - feed_id: "GOOGLE_REVIEW_ALERT"
      mcp_server: "google-business-mcp"
      tool_call: "review.get_recent"
      poll_cadence: "PT4H"
      relevance_dimension: "customer_profile.google_business_id"
      materiality_classifier: "new_1_or_2_star_review → HIGH"

  signal_types:
    - signal_type: "COMPETITOR_CAMPAIGN_LAUNCHED"
      feed_id: "COMPETITOR_ACTIVITY"
      skill_id: "COMPETITIVE_INTELLIGENCE"
      urgency_class_rule: "competitor launches paid campaign while customer has no active campaign → HIGH"
      urgency_class: "HIGH"
      emergency_exempt: false
      channel: "PORTAL"
      trai_outside_window_behavior: "DEFER"
      evidence_action_type: "PROACTIVE_SIGNAL_ALERT"

    - signal_type: "KPI_PACE_CRITICAL"
      feed_id: "PLATFORM_ANALYTICS"
      skill_id: "PERFORMANCE_ANALYTICS"
      urgency_class_rule: "any_kpi_pace < 0.40 by day 15 of month → HIGH"
      urgency_class: "HIGH"
      emergency_exempt: false
      channel: "PORTAL"
      trai_outside_window_behavior: "DEFER"
      evidence_action_type: "PROACTIVE_SIGNAL_ALERT"

    - signal_type: "NEGATIVE_REVIEW_RECEIVED"
      feed_id: "GOOGLE_REVIEW_ALERT"
      skill_id: "GOOGLE_BUSINESS_PROFILE"
      urgency_class_rule: "1 or 2 star review → HIGH always"
      urgency_class: "HIGH"
      emergency_exempt: false
      channel: "PORTAL"
      trai_outside_window_behavior: "DEFER"
      evidence_action_type: "PROACTIVE_SIGNAL_ALERT"

  materiality_thresholds:
    critical: 0.90
    high: 0.70
    advisory: 0.50

  # DMA delivers via portal (not WhatsApp) — no HSM templates required
  hsm_templates: []
```

---

## 3.19 Skill Intelligence Router (C-054, v0.35.0)

```yaml
skill_intelligence_router:
  router_prompt: "DMA/ROUTING/SKILL_INTENT_ROUTER"
  gap_signalling:
    gap_signal_threshold_days: 30
    gap_frequency_min: 3
    cross_customer_threshold: 5
    evidence_table: "institutional.skill_gap_signals"

  skill_capability_manifests:

    - skill_id: "MARKET_RESEARCH"
      version: "2.4"
      intent_signatures:
        - "who are my competitors"
        - "market research report"
        - "digital maturity score"
        - "competitor analysis"
        - "what's my online presence"
        - "benchmark against others"
        - "what should I focus on"
      servable_request_types:
        COMPETITOR_ANALYSIS: "Identifies top competitors and their digital presence"
        MATURITY_ASSESSMENT: "Scores customer's digital maturity and identifies priority gaps"
      unservable_request_types:
        - intent: "create content"
          routes_to_skill: "CONTENT_STRATEGY"
        - intent: "run paid ads"
          routes_to_skill: "PAID_ADVERTISING"
      input_requirements:
        required: ["customer_profile.business_domain", "customer_profile.locality"]
        optional: []
      output_contributions:
        - type: "maturity_score"
          used_by: ["CONTENT_STRATEGY", "PAID_ADVERTISING", "LOCAL_SEO"]
        - type: "competitor_list"
          used_by: ["COMPETITIVE_INTELLIGENCE", "INSTAGRAM_MARKETING"]
      collaboration_affinities:
        - with_skill: "CONTENT_STRATEGY"
          relationship: "UPSTREAM"
          benefit: "Maturity score determines which phase skills are activated"
        - with_skill: "COMPETITIVE_INTELLIGENCE"
          relationship: "UPSTREAM"
          benefit: "Competitor list from research feeds competitive monitoring"

    - skill_id: "CONTENT_STRATEGY"
      version: "2.4"
      intent_signatures:
        - "content calendar for next month"
        - "what should we post"
        - "monthly content plan"
        - "Diwali campaign ideas"
        - "theme for this month"
        - "posting schedule"
        - "content strategy"
      servable_request_types:
        CONTENT_CALENDAR: "Creates monthly content calendar with themes and posting schedule"
        CAMPAIGN_BRIEF: "Creates a campaign brief for a specific event or theme"
      unservable_request_types:
        - intent: "create the actual Instagram post"
          routes_to_skill: "INSTAGRAM_MARKETING"
        - intent: "run paid ads for the campaign"
          routes_to_skill: "PAID_ADVERTISING"
      input_requirements:
        required: ["customer_profile.business_goals"]
        optional: ["market_research.maturity_score"]
      output_contributions:
        - type: "content_calendar"
          used_by: ["INSTAGRAM_MARKETING", "FACEBOOK_MARKETING", "WHATSAPP_BUSINESS"]
        - type: "campaign_brief"
          used_by: ["INSTAGRAM_MARKETING", "VIDEO_CONTENT_CREATION", "PAID_ADVERTISING"]
      collaboration_affinities:
        - with_skill: "INSTAGRAM_MARKETING"
          relationship: "UPSTREAM"
          benefit: "Content calendar drives Instagram execution — calendar approval → post creation"
        - with_skill: "PAID_ADVERTISING"
          relationship: "UPSTREAM"
          benefit: "Campaign brief is the creative brief that paid ads amplify"
        - with_skill: "PERFORMANCE_ANALYTICS"
          relationship: "BIDIRECTIONAL"
          benefit: "Analytics tells Content Strategy what's working; strategy drives next month's plan"

    - skill_id: "INSTAGRAM_MARKETING"
      version: "2.4"
      intent_signatures:
        - "create instagram post"
        - "instagram content"
        - "social media post for clinic"
        - "reel for my practice"
        - "caption for photo"
        - "post for instagram"
        - "instagram campaign"
      servable_request_types:
        CONTENT_CREATION: "Creates captions, images, reels, stories for Instagram"
        CAMPAIGN_EXECUTION: "Publishes approved content to Instagram"
        CREATIVE_REFINEMENT: "Iterates on previously generated content"
      unservable_request_types:
        - intent: "paid ad budget"
          routes_to_skill: "PAID_ADVERTISING"
        - intent: "website landing page"
          routes_to_skill: "CONVERSION_OPTIMISATION"
      input_requirements:
        required: ["customer_profile.brand_voice_embeddings"]
        optional: ["content_strategy.campaign_brief", "customer_creative_fingerprints.voice_embedding"]
      output_contributions:
        - type: "approved_instagram_post"
          used_by: ["PAID_ADVERTISING"]
        - type: "content_performance_data"
          used_by: ["PERFORMANCE_ANALYTICS", "CONTENT_STRATEGY"]
      collaboration_affinities:
        - with_skill: "CONTENT_STRATEGY"
          relationship: "DOWNSTREAM"
          benefit: "Content Strategy brief drives Instagram execution; calendar-aligned content"
        - with_skill: "PAID_ADVERTISING"
          relationship: "UPSTREAM"
          benefit: "Approved Instagram post → paid amplification for same creative"
        - with_skill: "PERFORMANCE_ANALYTICS"
          relationship: "BIDIRECTIONAL"
          benefit: "Instagram performance informs creative learning loop"

    - skill_id: "PAID_ADVERTISING"
      version: "2.4"
      intent_signatures:
        - "run paid ads"
        - "Facebook ads campaign"
        - "Google ads"
        - "boost this post"
        - "lead generation campaign"
        - "paid campaign for Diwali"
        - "how to get more leads"
      servable_request_types:
        CAMPAIGN_CREATION: "Sets up paid advertising campaign on Meta or Google after approval"
        BID_OPTIMISATION: "Optimises bids within approved parameters"
        CAMPAIGN_REPORT: "Reports on paid campaign performance"
      unservable_request_types:
        - intent: "organic social media post"
          routes_to_skill: "INSTAGRAM_MARKETING"
        - intent: "website conversion rate"
          routes_to_skill: "CONVERSION_OPTIMISATION"
      input_requirements:
        required: ["customer_profile.approved_budget", "customer_profile.campaign_objective"]
        optional: ["instagram_marketing.approved_instagram_post", "content_strategy.campaign_brief"]
      output_contributions:
        - type: "campaign_performance_data"
          used_by: ["PERFORMANCE_ANALYTICS"]
      collaboration_affinities:
        - with_skill: "INSTAGRAM_MARKETING"
          relationship: "DOWNSTREAM"
          benefit: "Organic post → paid amplification; unified creative across organic+paid"
        - with_skill: "CONTENT_STRATEGY"
          relationship: "DOWNSTREAM"
          benefit: "Campaign brief drives both content creation and paid targeting"
        - with_skill: "LOCAL_SEO"
          relationship: "BIDIRECTIONAL"
          benefit: "SEO keyword research informs paid keywords; paid data shows which keywords convert"

    - skill_id: "PERFORMANCE_ANALYTICS"
      version: "2.4"
      intent_signatures:
        - "how did we do this month"
        - "monthly report"
        - "what's working"
        - "KPI summary"
        - "performance overview"
        - "analytics report"
        - "results"
      servable_request_types:
        MONTHLY_REPORT: "Generates full monthly performance report across all active skills"
        KPI_STATUS: "Answers status query about specific KPIs"
        UNDERPERFORMANCE_DIAGNOSIS: "Identifies underperforming skills and proposes adjustments"
      unservable_request_types:
        - intent: "create new content"
          routes_to_skill: "CONTENT_STRATEGY"
      input_requirements:
        required: []
        optional: ["all active skills' performance data"]
      output_contributions:
        - type: "performance_intelligence"
          used_by: ["CONTENT_STRATEGY", "PAID_ADVERTISING", "LOCAL_SEO"]
      collaboration_affinities:
        - with_skill: "CONTENT_STRATEGY"
          relationship: "BIDIRECTIONAL"
          benefit: "Analytics shows what content performs; strategy adapts accordingly"
        - with_skill: "PAID_ADVERTISING"
          relationship: "BIDIRECTIONAL"
          benefit: "Campaign performance data drives bid optimisation decisions"
        - with_skill: "COMPETITIVE_INTELLIGENCE"
          relationship: "BIDIRECTIONAL"
          benefit: "Own performance compared to competitor activity for strategic context"

    - skill_id: "LOCAL_SEO"
      version: "2.4"
      intent_signatures:
        - "nobody can find us on Google"
        - "SEO audit"
        - "local search ranking"
        - "Google search keywords"
        - "appear on Google Maps"
        - "search visibility"
        - "local SEO"
      servable_request_types:
        SEO_AUDIT: "Audits website and GBP for local SEO signals"
        KEYWORD_RESEARCH: "Identifies target keywords for the domain and locality"
        SEO_RECOMMENDATION: "Recommends SEO improvements"
      unservable_request_types:
        - intent: "paid ads"
          routes_to_skill: "PAID_ADVERTISING"
        - intent: "website conversion"
          routes_to_skill: "CONVERSION_OPTIMISATION"
      input_requirements:
        required: ["customer_profile.website_url", "customer_profile.business_domain"]
        optional: ["performance_analytics.performance_intelligence"]
      output_contributions:
        - type: "keyword_intelligence"
          used_by: ["PAID_ADVERTISING", "CONTENT_STRATEGY"]
      collaboration_affinities:
        - with_skill: "PAID_ADVERTISING"
          relationship: "BIDIRECTIONAL"
          benefit: "SEO keywords improve paid ad targeting; paid data reveals which terms convert"
        - with_skill: "CONTENT_STRATEGY"
          relationship: "UPSTREAM"
          benefit: "Keyword research informs content themes for maximum organic visibility"

    - skill_id: "COMPETITIVE_INTELLIGENCE"
      version: "2.4"
      intent_signatures:
        - "what are competitors doing"
        - "competitor campaign alert"
        - "competitor posted new ad"
        - "defend against competitor"
        - "competitive gap analysis"
        - "market position"
        - "who is beating us"
      servable_request_types:
        COMPETITOR_MONITORING: "Monitors top 3 competitors' public digital activity"
        COMPETITIVE_RESPONSE: "Recommends defensive or offensive response to competitor move"
      unservable_request_types:
        - intent: "initial competitor list setup"
          routes_to_skill: "MARKET_RESEARCH"
      input_requirements:
        required: ["customer_profile.confirmed_competitor_list"]
        optional: ["market_research.maturity_score", "performance_analytics.performance_intelligence"]
      output_contributions:
        - type: "competitor_intelligence_snapshot"
          used_by: ["CONTENT_STRATEGY", "PAID_ADVERTISING"]
      collaboration_affinities:
        - with_skill: "MARKET_RESEARCH"
          relationship: "DOWNSTREAM"
          benefit: "Market Research produces the competitor list; Competitive Intelligence monitors it continuously"
        - with_skill: "PAID_ADVERTISING"
          relationship: "BIDIRECTIONAL"
          benefit: "Competitor campaign launch → defensive paid response recommendation"

---

## 3.21 Campaign Theme Engine — Section 3.21 (C-055, v0.39.0)

```yaml
campaign_theme_engine:
  applies_to_modes: ["CAMPAIGN_APPROVAL", "CAMPAIGN_AUTO"]
  backward_compatible: true  # POST_APPROVAL mode customers unaffected

  platform_intelligence:
    research_skill: "CONTENT_STRATEGY"
    research_prompt: "DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH"
    research_cadence: "POST_ONBOARDING + QUARTERLY_REFRESH"
    research_signals:
      - "competitor platform presence and active campaign counts (meta-ad-library-mcp)"
      - "target audience demographics per platform for healthcare/beauty India (Tier 1 RAG)"
      - "platform-content fit benchmarks by domain + city tier (Tier 1 RAG)"
      - "customer's existing platform accounts and follower counts (social-profile-mcp)"
    supported_platforms:
      - {platform: "INSTAGRAM", content_fit: ["dental", "beauty", "fitness", "food", "retail"], mcp: "instagram-mcp"}
      - {platform: "YOUTUBE_SHORT", content_fit: ["dental_education", "beauty_tutorials", "fitness_demos"], mcp: "youtube-mcp"}
      - {platform: "GBP", content_fit: ["all_local_businesses"], mcp: "google-business-mcp"}
      - {platform: "FACEBOOK", content_fit: ["dental", "beauty", "fitness", "local_retail"], mcp: "facebook-mcp"}
      - {platform: "WHATSAPP_BROADCAST", content_fit: ["appointment_reminders", "existing_patient_campaigns"], mcp: "whatsapp-business-mcp"}
      - {platform: "LINKEDIN", content_fit: ["b2b_practices", "corporate_wellness"], mcp: "linkedin-mcp", dependency_status: "PENDING_FOUNDER_ACTION"}
      - {platform: "X", content_fit: ["thought_leadership", "real_time_engagement"], mcp: "x-mcp", dependency_status: "PENDING_FOUNDER_DECISION"}
      - {platform: "PINTEREST", content_fit: ["beauty", "home_decor", "fashion", "food"], mcp: "pinterest-mcp", dependency_status: "PENDING_FOUNDER_ACTION"}
      - {platform: "THREADS", content_fit: ["dental", "beauty", "lifestyle", "young_urban"], mcp: "threads-mcp", dependency_status: "PENDING_FOUNDER_ACTION"}

  campaign_theme_cascade:
    level_1_prompt: "DMA/CAMPAIGN/MASTER_THEME_PROPOSAL"
    level_1_model_tier: "FRONTIER"
    level_1_prompt_type: "BREAKING"
    level_2_prompt: "DMA/CAMPAIGN/WEEKLY_THEME_CASCADE"
    level_2_model_tier: "MID_TIER"
    level_3_prompt: "DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT"
    level_3_model_tier: "MID_TIER"
    campaign_weeks_range: [3, 8]
    tables: ["business.content_campaigns", "business.campaign_weekly_themes", "business.campaign_content_items"]

  synthetic_content_review:
    enabled_for_modes: ["CAMPAIGN_APPROVAL", "CAMPAIGN_AUTO"]
    checks:
      SCR_1_THEME_FIDELITY:  {threshold: 0.80, tier: "LOCAL", fail_action: "REGENERATE"}
      SCR_2_BRAND_VOICE:     {threshold: 0.75, tier: "LOCAL", fail_action: "REGENERATE"}
      SCR_3_COMPLIANCE:      {threshold: "ZERO_VIOLATIONS", tier: "LOCAL", fail_action: "ROUTE_TO_CUSTOMER"}
      SCR_4_UNIQUENESS:      {competitor_threshold: 0.75, own_content_threshold: 0.85, tier: "LOCAL", fail_action: "REGENERATE"}
      SCR_5_QUALITY:         {threshold: 0.80, tier: "MID_TIER", prompt: "DMA/CAMPAIGN/SCR_QUALITY_CHECK", fail_action: "REGENERATE"}
    max_regeneration_attempts: 2
    evidence_table: "business.scr_review_records"

  content_approval_modes:
    POST_APPROVAL:     {upgrade_criteria: "3 months + ≥90% approval rate + explicit customer request"}
    CAMPAIGN_APPROVAL: {weekly_digest: true, digest_prompt: "DMA/CAMPAIGN/CAMPAIGN_DIGEST", upgrade_criteria: "3 months + <5% SCR failure + explicit customer request"}
    CAMPAIGN_AUTO:     {weekly_digest: true, max_auto_posts_per_week: 10, downgrade_trigger: "SCR failure rate > 15% in any 30-day period"}

  campaign_digest:
    cadence: "WEEKLY — Monday 09:00 IST"
    channels: ["PORTAL", "WHATSAPP_TEXT", "EMAIL"]
    prompt: "DMA/CAMPAIGN/CAMPAIGN_DIGEST"
    model_tier: "MID_TIER"

  campaign_approval_ux:
    # GAP-D002: Campaign approval is a constitutional event — must be explicit
    portal_ui: "Campaign Brief Card — shows master_theme, target_outcome, platform_mix, weekly_theme_preview"
    approval_actions:
      approve_button: "Approve this Campaign"
        # Creates: CE.RecordEvidence(CAMPAIGN_BRIEF_APPROVED, campaign_id, constitutional_basis="C-055; C-003")
        # Sets: content_campaigns.status = CUSTOMER_APPROVED
      change_request_button: "Request Changes"
        # Customer adds note → agent revises → re-proposes → same approval gate
    no_response_policy: "Campaign remains DRAFT after 7 days. One reminder sent. No auto-approval."
    # C-003: implicit approval is constitutionally invalid for campaign-level authority

  kpi_attribution:
    # GAP-D005: C-049 Honest Limitation Disclosure — appointment bookings not directly measurable
    measurable_kpis:
      - metric: "content engagement (likes, saves, shares)"
        source: "platform-analytics-mcp"
        accuracy: "HIGH — direct API data"
      - metric: "website clicks from social"
        source: "platform-analytics-mcp + google-search-console-mcp"
        accuracy: "MEDIUM — attributed clicks, not confirmed appointments"
      - metric: "WhatsApp enquiries from broadcast"
        source: "whatsapp-business-mcp message logs"
        accuracy: "HIGH — direct message count"
    not_measurable_at_mvi:
      - metric: "actual appointment bookings"
        reason: "No clinic management system integration (Phase 2 dependency)"
        c049_disclosure: "I can measure engagement signals accurately. I cannot directly measure appointment bookings unless you connect your clinic system. I'll use engagement signals and your weekly input to estimate monthly results."
    proxy_kpi: "Weekly intent signals: DMs asking about appointments + WhatsApp enquiries + Google Maps calls"
    manual_input: "Customer provides weekly booking count via portal ('How many new patients mentioned Instagram/social this week?')"

  youtube_short_audio:
    # GAP-D004: Audio generation mode for YouTube Shorts
    phase_1_mode: "CUSTOMER_RECORDS"
      # Agent generates voice script → sends to customer via portal
      # Customer records their own voice → uploads via portal
      # Agent composes video: customer audio + visuals + text overlays
    phase_2_mode: "AI_VOICE_WITH_CONSENT"
      # Requires: YOUTUBE_SHORT_VOICE_CONSENT_CONFIRMED (always-ask action)
      # Customer must approve an AI-generated voice sample before use
    always_ask_action: "YOUTUBE_SHORT_VOICE_CONSENT_CONFIRMED"
      # Customer must confirm voice consent each time AI voice is used
      # Constitutional basis: C-003 (authority for voice use must be licensed)

  platform_intelligence_fallback:
    # GAP-D001: No competitor data available
    fallback_basis: "DOMAIN_BENCHMARKS"
    fallback_disclosure: "I couldn't find your competitors' public profiles — my recommendation is based on what works for dental clinics in Pune, not your specific competitors."
    competitor_data_available_field: true  # Added to PLATFORM_INTELLIGENCE_RESEARCH output schema
```

```yaml
campaign_theme_engine:
  applies_to_modes: ["CAMPAIGN_APPROVAL", "CAMPAIGN_AUTO"]
  backward_compatible: true  # POST_APPROVAL mode customers unaffected

  platform_intelligence:
    research_skill: "CONTENT_STRATEGY"
    research_prompt: "DMA/CAMPAIGN/PLATFORM_INTELLIGENCE_RESEARCH"
    research_cadence: "POST_ONBOARDING + QUARTERLY_REFRESH"
    research_signals:
      - "competitor platform presence and active campaign counts (meta-ad-library-mcp)"
      - "target audience demographics per platform for healthcare/beauty India (Tier 1 RAG)"
      - "platform-content fit benchmarks by domain + city tier (Tier 1 RAG)"
      - "customer's existing platform accounts and follower counts (social-profile-mcp)"
    supported_platforms:
      - platform: "INSTAGRAM"
        content_fit: ["dental", "beauty", "fitness", "food", "retail"]
        mcp: "instagram-mcp"
      - platform: "YOUTUBE_SHORT"
        content_fit: ["dental_education", "beauty_tutorials", "fitness_demos"]
        mcp: "youtube-mcp"
      - platform: "GBP"
        content_fit: ["all_local_businesses"]
        mcp: "google-business-mcp"
      - platform: "FACEBOOK"
        content_fit: ["dental", "beauty", "fitness", "local_retail"]
        mcp: "facebook-mcp"
      - platform: "WHATSAPP_BROADCAST"
        content_fit: ["appointment_reminders", "existing_patient_campaigns"]
        mcp: "whatsapp-business-mcp"
      - platform: "LINKEDIN"
        content_fit: ["b2b_practices", "corporate_wellness", "professional_services"]
        mcp: "linkedin-mcp"
        dependency_status: "PENDING_FOUNDER_ACTION"  # LinkedIn Partner Program needed
      - platform: "X"
        content_fit: ["thought_leadership", "real_time_engagement"]
        mcp: "x-mcp"
        dependency_status: "PENDING_FOUNDER_DECISION"  # $100/month API cost
      - platform: "PINTEREST"
        content_fit: ["beauty", "home_decor", "fashion", "food"]
        mcp: "pinterest-mcp"
        dependency_status: "PENDING_FOUNDER_ACTION"  # Pinterest developer account
      - platform: "THREADS"
        content_fit: ["dental", "beauty", "lifestyle", "young_urban"]
        mcp: "threads-mcp"
        dependency_status: "PENDING_FOUNDER_ACTION"  # Meta Threads API beta access

  campaign_theme_cascade:
    level_1_prompt: "DMA/CAMPAIGN/MASTER_THEME_PROPOSAL"
    level_1_model_tier: "FRONTIER"
    level_1_prompt_type: "BREAKING"
    level_2_prompt: "DMA/CAMPAIGN/WEEKLY_THEME_CASCADE"
    level_2_model_tier: "MID_TIER"
    level_3_prompt: "DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT"
    level_3_model_tier: "MID_TIER"
    campaign_weeks_range: [3, 8]
    tables:
      - "business.content_campaigns"
      - "business.campaign_weekly_themes"
      - "business.campaign_content_items"

  synthetic_content_review:
    enabled_for_modes: ["CAMPAIGN_APPROVAL", "CAMPAIGN_AUTO"]
    checks:
      SCR_1_THEME_FIDELITY:     {threshold: 0.80, tier: "LOCAL", fail_action: "REGENERATE"}
      SCR_2_BRAND_VOICE:        {threshold: 0.75, tier: "LOCAL", fail_action: "REGENERATE"}
      SCR_3_COMPLIANCE:         {threshold: "ZERO_VIOLATIONS", tier: "LOCAL", fail_action: "ROUTE_TO_CUSTOMER"}
      SCR_4_UNIQUENESS:         {competitor_threshold: 0.75, own_content_threshold: 0.85, tier: "LOCAL", fail_action: "REGENERATE"}
      SCR_5_QUALITY:            {threshold: 0.80, tier: "MID_TIER", prompt: "DMA/CAMPAIGN/SCR_QUALITY_CHECK", fail_action: "REGENERATE"}
    max_regeneration_attempts: 2
    evidence_table: "business.scr_review_records"

  content_approval_modes:
    POST_APPROVAL:
      upgrade_criteria: "3 months + ≥90% approval rate + explicit customer request"
    CAMPAIGN_APPROVAL:
      weekly_digest: true
      digest_prompt: "DMA/CAMPAIGN/CAMPAIGN_DIGEST"
      upgrade_criteria: "3 months + <5% SCR failure + explicit customer request"
    CAMPAIGN_AUTO:
      weekly_digest: true
      max_auto_posts_per_week: 10
      downgrade_trigger: "SCR failure rate > 15% in any 30-day period"

  campaign_digest:
    cadence: "WEEKLY — Monday 09:00 IST"
    channels: ["PORTAL", "WHATSAPP_TEXT", "EMAIL"]
    prompt: "DMA/CAMPAIGN/CAMPAIGN_DIGEST"
    model_tier: "MID_TIER"
```

---

## 4. Customer Journey & Onboarding Flow

### 4.0 Pre-Engagement: The Agency Pitch (Portal Discovery)

Before a customer registers, they encounter WAOOAW DMA on the portal. This is the agency's "shop window." It must answer the question every prospect has: **"Why would I trust an AI with my marketing when I can hire a real agency?"**

**The answer the portal must communicate (C-057):**

```
"Hiring an agency for ₹15,000–₹50,000/month gets you a team that handles
8–15 clients. When your account manager leaves, they take your strategy with them.

We're different.

₹1,499/month. No retainer. No inflated creative fees. No team turnover.
We handle your dental clinic the same way at month 12 as at month 1.

We've helped [N] dental clinics in cities like yours increase their appointment
enquiries by an average of [X]% in 3 months. Every action we take is recorded.
You can audit us. No other agency gives you that.

And when you're ready to spend on ads, we charge 10% — not 20-25%.
Your ₹5,000 ad budget sends ₹4,500 to Meta or Google.

Try the first month. See the work. Then decide."
```

**The portfolio claim format (C-057 + C-002 evidence requirement):**
```
Claims the portal may display (sourced from Tier 3 performance register):
  ✓ "[N] dental clinics served" (count from institutional.dma_performance_portfolio)
  ✓ "Average enquiry increase: [X]% in 3 months" (cohort aggregate, same domain)
  ✓ "Content calendar adherence: [X]%" (platform metric aggregate)
  ✗ "Guaranteed to increase your bookings" — prohibited (RULE-HC-001 equivalent)
  ✗ "Better than [Agency Name]" — prohibited (disparagement, RULE-HC-006 equivalent)
```

---

### 4.1 Pre-Engagement: Registration (Portal)

Customer registers on WAOOAW portal. Registration is SHORT — the agent does the real discovery in conversation.

**Mandatory registration fields:**
1. Owner / contact name
2. Business name
3. Business domain (dropdown: Dental Clinic / Beauty Artist / Beauty Salon / Medical Clinic / Fitness Studio / Other)
4. Locality + City
5. Prospective customers (free text, 1 sentence)
6. Aspiration (free text, 1 sentence)

Customer can edit at any time from their profile page.

---

### 4.2 First Interaction: Professional Intake Conversation (Skill 0 + C-057)

**This is not a data collection form. It is a professional intake meeting.**

The DMA agent opens every new engagement by demonstrating expertise about the customer's situation BEFORE asking configuration questions. The order is: professional insight first, data collection second. This is how every reputable agency opens a new client relationship.

```
OPENING — Agent demonstrates professional authority first (C-057)

AI:  "Hello [Name]! I've seen your registration — [Business Name],
     a [Dental Clinic] in [Viman Nagar, Pune].

     Before I ask you anything, let me tell you what I already know about
     the situation for dental clinics in your area.

     Viman Nagar is a high-density area with at least 3 dental clinics within
     800 metres of your location. One of them — [Dantavilas Dental] — has been
     very active on Instagram lately with 3-4 posts per week.
     Your Google Business listing was last updated [X months] ago.
     Your Instagram has [N] followers and posts about twice a month.

     Based on what I see, your biggest opportunity right now is consistency
     and search visibility. Patients are searching 'dentist near me' and not
     finding you first.

     Now let me ask you a few things to sharpen the picture.
     This takes about 10 minutes. Ready?"

Note: Agent uses Market Research (Skill 1) data gathered before the conversation.
      The opening demonstrates value before the customer has done anything.
      This is the agency model: research first, intake second.

EXCHANGE 1 — KPI baseline
AI:  "You mentioned [aspiration]. How many new patient enquiries are you getting
     per month right now — roughly?"
Customer: "Maybe 15-20 a month. Not enough."
→ Agent captures KPI baseline + target.

EXCHANGE 2 — Competitive awareness
AI:  "The clinic down the road from you — how long have they been active?
     Do patients mention them?"
Customer: "Yes, they opened last year and seem busier."
→ Agent confirms competitive context from Skill 1 research.

EXCHANGE 3 — Budget signal
AI:  "One practical question: how much do you currently spend on marketing —
     including any boosted posts, freelancers, WhatsApp tools — per month?"
Customer: "About ₹3,000 on boosted Instagram posts. Not sure if they work."
→ Agent captures existing spend + implied frustration with ROI.

EXCHANGE 4 — Agency experience
AI:  "Have you worked with a digital marketing agency or freelancer before?
     What was that experience like?"
Customer: "A freelancer for 3 months. He disappeared."
→ Agent captures trust deficit. This is where the agency positioning lands.

AI:  "That's more common than you'd think. Our approach is different —
     every action I take is recorded. You can see exactly what I did, when,
     and what result it drove. Nothing disappears.

     Based on what I've seen, here's what I'd recommend for the first 3 months..."
```

**Why this opening works (C-057 — Professional Authority):**
- Agent demonstrates market knowledge BEFORE asking for data — this establishes expertise
- Agent shows it has already done research — customers feel it works for them, not with them
- Agent addresses the trust deficit from the previous bad experience with evidence (not promises)
- The opening closes with a recommendation — agency confidence, not tool passivity

**The competitive positioning moment (C-057 + C-049 Honest Limitation):**
```
If customer asks: "How are you different from hiring an agency?"

Agent must answer with:
  1. Specific price comparison (your situation: ₹1,499/month vs typical ₹20,000-40,000 retainer)
  2. Specific transparency advantage (CAL evidence — "you can audit every post I made")
  3. Specific consistency advantage ("I don't have team turnover — same quality every month")
  4. Honest limitation (C-049): "What I can't do is attend your events in person or
     handle media relations. I'm the digital specialist — not the full agency."

What the agent must NOT say:
  ✗ "Agencies are bad" (disparagement)
  ✗ "I'm better in every way" (absolute claim)
  ✗ "You'll definitely see results" (guarantee claim — RULE-HC-001 equivalent)
```

---

### 4.3 Performance Portfolio — What the Agent Cites (C-057 + Tier 3 RAG)

During onboarding and monthly reviews, the agent may cite platform-level performance statistics sourced from the Tier 3 performance portfolio register. These are the agent's "references."

```
Format for citing portfolio performance (must be accurate — C-002):
  "[N] dental clinics on our platform."
  "Dental clinics in Tier 1 India cities that use us for 3+ months average [X]% more
   monthly enquiry signals versus their starting baseline."
  "Content calendar adherence across dental clinic customers: [X]% average."

Prohibited portfolio claims:
  ✗ Specific customer names without written consent (C-034 data isolation)
  ✗ Performance guarantees for the current customer
  ✗ Claiming statistics not in the Tier 3 performance register
  ✗ Comparing to named traditional agencies
```

**New Tier 3 RAG table: `institutional.dma_performance_portfolio`**
```sql
-- Anonymized aggregate performance by professional_type + domain + city_tier
-- Updated weekly from employment contracts in ACTIVE status with >30 days history
-- No individual customer data — only cohort statistics (C-052 isolation)
CREATE TABLE institutional.dma_performance_portfolio (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    professional_type           VARCHAR(100) NOT NULL,  -- DIGITAL_MARKETING_HEALTHCARE
    business_domain             VARCHAR(100) NOT NULL,  -- DENTAL_CLINIC, BEAUTY_ARTIST, etc.
    city_tier                   VARCHAR(10) NOT NULL,   -- TIER_1, TIER_2, TIER_3
    cohort_size                 INTEGER NOT NULL,        -- number of active customers in cohort
    avg_enquiry_increase_pct    NUMERIC(5,2),           -- avg % increase in enquiry signals vs baseline
    content_adherence_rate      NUMERIC(5,2),           -- avg % content calendar adherence
    avg_maturity_score_change   NUMERIC(4,2),           -- avg maturity score gain in 3 months
    avg_time_to_first_result_days INTEGER,              -- days until first measurable KPI signal
    avg_cpl_inr                 NUMERIC(8,2),           -- avg cost per lead for Skill 11 customers
    portfolio_claim_approved    BOOLEAN NOT NULL DEFAULT FALSE, -- EA-approved before use in sales
    portfolio_period            DATE NOT NULL,          -- which month this snapshot covers
    computed_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_portfolio_domain ON institutional.dma_performance_portfolio(professional_type, business_domain, city_tier);
```

---

### 4.4 Skill 14: WAOOAW Self-Marketing — AUTHORIZED (2026-07-12)

**Authorization:** Founder authorized 2026-07-12. Recorded as FR-005 in PROJECT_STATE.md.

```yaml
skill_14_institutional_config:
  employer: "WAOOAW"
  employer_organisation_id: "WAOOAW_INSTITUTIONAL"  # institutional entity, not a customer organisation
  professional_type: "DIGITAL_MARKETING_HEALTHCARE"  # internal enum; campaigns target ALL local businesses
  decision_space_id: "WAOOAW_INSTITUTIONAL_MARKETING"
  constitutional_basis: "C-057 (AI Agency Professional Standard); C-046 (Platform Self-Governance); C-003 (authority licensed — WAOOAW's own Decision Space)"

  # Founder-set parameters (2026-07-12)
  monthly_ad_spend_budget_inr: 5000       # ₹5,000/month — C-043 Constitutional Floor applies to WAOOAW itself
  management_fee_pct: 0                   # WAOOAW does not charge itself a management fee
  portfolio_stat_threshold:
    minimum_customers: 50                 # Performance stats appear in WAOOAW's own ads ONLY after 50+ customers
    minimum_diversity: "MULTI_DOMAIN"     # Must span multiple business domains (doctors, builders, banks, etc.)
    
  authorized_actions:
    - META_AD_CAMPAIGN               # Acquire DMA customers via Meta ads
    - GOOGLE_AD_CAMPAIGN             # Acquire DMA customers via Google ads (Search + Performance Max)
    - INSTAGRAM_POST                 # WAOOAW's own Instagram — case studies, results, how-it-works content
    - FACEBOOK_POST                  # WAOOAW's own Facebook presence
    - LINKEDIN_POST                  # B2B positioning — banks, insurance, builders respond here
    - GOOGLE_BUSINESS_POST           # WAOOAW's own GBP listing
    - WHATSAPP_BROADCAST             # WAOOAW's own WhatsApp Business number (platform notifications)
    
  target_audience:
    description: "Local business owners across India who need professional digital marketing"
    segments:
      - "Doctors and healthcare practices (dental, medical, physiotherapy, Ayurveda)"
      - "Builders, real estate developers, and property agents"
      - "Banks (branch marketing, local campaigns), NBFCs, microfinance institutions"
      - "Insurance advisors and distributors (LIC agents, private insurance)"
      - "Retail businesses (local stores, restaurants, boutiques)"
      - "Professional services (CAs, lawyers, consultants)"
      - "Fitness and wellness studios"
      - "Educational institutions (coaching classes, schools)"
    geography: "India — Tier 1 + Tier 2 cities"
    platform_fit:
      META: "All segments — Facebook for builders/insurance; Instagram for healthcare/retail"
      GOOGLE: "All segments — 'digital marketing agency near me' intent"
      LINKEDIN: "Banks, insurance, builders, professional services"

  campaign_phases:
    phase_1:
      trigger: "0 to 49 customers on platform"
      message_focus: "Value proposition + pricing comparison vs agencies"
      portfolio_stats: false  # Never use performance stats until threshold met
      sample_headlines:
        - "Professional digital marketing for your dental clinic. ₹1,499/month."
        - "No agency retainer. No inflated ad fees. Just results. ₹1,499/month."
        - "AI digital marketing professional for your business. Try the first month."
      
    phase_2:
      trigger: "50+ customers, multi-domain (doctors + builders + banks + insurance)"
      message_focus: "Evidence-based performance + value proposition"
      portfolio_stats: true   # Can now cite: "[N] businesses served, [X]% average enquiry increase"
      sample_headlines:
        - "[N] businesses. Doctors, builders, banks. Average [X]% more enquiries in 3 months."
        - "The digital marketing professional that never has a bad month. ₹1,499/month."
        - "Banks branch marketing. Builders' project launches. Doctors' patient acquisition. One platform."

  financial_isolation:
    note: "WAOOAW's ₹5,000/month ad spend is institutionally separate from customer ad budgets (C-056).
           Charged to WAOOAW's own institutional bank account, NOT from any customer's Ad Spend Wallet.
           Appears in ad_spend_ledger with organisation_id = WAOOAW_INSTITUTIONAL."
    
  evidence_trail:
    all_actions: "CAL records with organisation_id = WAOOAW_INSTITUTIONAL"
    campaign_reports: "Identical to customer reports — DMA agent reports to Founder monthly"
    constitutional_basis: "C-023 (Evidence First — WAOOAW's own marketing actions are constitutionally recorded)"
```

**What this means in practice:**

The DMA agent now has two types of customers:
1. **External customers** (dental clinics, beauty studios, builders, banks) — pay subscription + ad spend
2. **WAOOAW itself** — the agent runs WAOOAW's own marketing to grow the external customer base

The agent runs WAOOAW's Instagram showing "this is what I did for a dental clinic last month." Then someone who runs a dental clinic sees it and asks "how do I hire one of these?" That's the self-reinforcing loop.

**Implementation trigger:** When IB-009 implementation sprint begins, `WAOOAW_INSTITUTIONAL_MARKETING` is the first Decision Space to configure — before any customer Decision Space. WAOOAW eats its own cooking from day one.

---
→ Agent flags competition need, captures competitor name.

PROGRESSIVE SUMMARY (after exchange 4)
AI:  "Here's what I know so far:
     ✓ [Business Name] — [Domain] in [Locality, City]
     ✓ Target customers: [geo-scope]
     ✓ Goal: [Aspiration] — from ~[N] to ~[N2] enquiries/month
     ✓ Currently on Instagram, posting irregularly
     ✓ Competitor noted: [Competitor Name]
     Does this look right? Anything to correct?"

EXCHANGE 5 — Ad spend (sensitive — ask last)
AI:  "Last question — are you currently spending anything on online ads,
     like Meta or Google? Even a rough idea helps."
Customer: "No, nothing yet"
→ Agent marks paid advertising as not active; Growth Engine recommendation will include it.

COMPLETION
AI:  "Perfect — I have everything I need. I'm now going to research your
     digital presence. This takes 3–5 minutes. I'll come back with a full
     picture of where you stand and what I recommend we focus on first."
→ Skill 1 (Market Research) runs. Customer waits or returns to portal.
```

---

### 4.3 First Deliverable: Digital Marketing Maturity Report (Skill 1 output)

Delivered in chat and available as PDF download from the portal.

```
Report structure:
  1. Your Digital Marketing Score: [N] / 7  ([Label])
     Benchmark: Average [Domain] in [City]: [B] | Top 20%: [T]

  2. What I found (research summary — 5 axes, each with evidence)

  3. Your Needs Heat Map
     Active needs:   [list]
     Latent needs:   [list]
     Not applicable: [list]

  4. Recommended Phase: [Curtain Raiser / Growth Engine / Maturity Phase]
     Skills recommended for activation: [list]

  5. Your 3-month plan (specific activities, expected KPI impact)

  6. Next step: "Review your recommended skills below and let me know
     which ones you'd like to activate. I'll set them up today."
```

Report cadence: Full report at engagement start. 6-monthly refresh. Monthly reports between are execution reports (skills run, KPIs achieved).

---

### 4.4 Skill Activation & Credential Collection

After customer reviews the Maturity Report and approves a Phase bundle, the agent collects platform credentials only for the skills being activated. Credential collection is guided, one platform at a time, via Keycloak-managed external credential vault.

---

## 5. Phase Bundles — Packaging for Customer Hire/Trial

Customers choose a bundle at activation. Bundle determines which skills are active. Skills outside the active bundle are visible on the portal (to drive upgrade) but not executed.

---

### Bundle 1: Curtain Raiser
**Target customer:** Score 1–3 · No or minimal digital presence · First 3 months
**Promise:** "We'll build your digital footprint and post consistently so customers can find you and trust you."
**Active skills:** Skill 0 (Profiling), Skill 1 (Market Research), Skill 2 (Content Strategy), Skill 4 (Instagram), Skill 5 (Facebook), Skill 6 (Google Business), Skill 7 (WhatsApp), Skill 8 (Video)
**KPIs tracked:** Post consistency rate · Google Business views · Instagram follower growth · WhatsApp engagement
**Billing:** Subscription only — ₹1,499/month + 18% GST (SAC 9984). No Ad Spend Wallet at this tier.
**Upgrade trigger:** Customer reaches Score 3; agent recommends Growth Engine in monthly report.

---

### Bundle 2: Growth Engine
**Target customer:** Score 3–5 · Active presence, needs to convert it into enquiries · Ongoing
**Promise:** "We'll turn your digital presence into a customer acquisition machine."
**Active skills:** All Curtain Raiser skills + Skill 9 (Analytics), Skill 10 (Local SEO), Skill 11 (Paid Advertising)
**KPIs tracked:** All Curtain Raiser KPIs + enquiry volume · CPL · Google search impressions · conversion from digital
**Billing — two-part (ADR-026 + C-056):**
- **Part 1 (Subscription):** ₹2,499/month + 18% GST (SAC 9984) — covers all DMA agent management
- **Part 2 (Ad Spend):** Customer-funded Ad Spend Wallet, minimum ₹2,000/month. Billed as:
  - Actual spend passed to Meta + Google
  - Management fee: 10% of gross ad spend (disclosed at onboarding, itemized on every invoice)
  - GST @ 18% on (spend + management fee) — SAC 998361 (Online Advertising Services)
  - Example: ₹5,000 ad spend → Invoice 2 total: ₹6,490 (₹5,500 + ₹990 GST)
- Ad Spend Wallet is optional at Growth Engine. Skill 11 activates only when wallet is funded.
**Upgrade trigger:** Customer reaches Score 5; agent recommends Maturity Phase in 6-monthly Maturity Report.

---

### Bundle 3: Maturity Phase
**Target customer:** Score 5–7 · Well-established digital presence, optimising for growth · Ongoing
**Promise:** "We'll maximise every rupee of your digital marketing and keep you ahead of competitors."
**Active skills:** All Growth Engine skills + Skill 12 (Conversion Optimisation), Skill 13 (Competitive Intelligence)
**KPIs tracked:** All Growth Engine KPIs + conversion rate · ROAS · competitive gap score · revenue attributed to digital
**Billing — two-part (same as Growth Engine):** Subscription ₹3,999/month + Ad Spend Wallet (same pass-through model)

---

## 6. Portal Customer-Facing Presentation (Sales & Marketing Layer)

This section defines how the agent's capabilities are presented to customers on the WAOOAW portal. Language is customer-native (their pain, not our technology). The mind map from the Founder's needs-roles mapping is the visual backbone.

### 6.1 Customer Need → Bundle Mapping (portal display)

| What customers say | What they feel | Bundle that solves it | Primary skills |
|---|---|---|---|
| "Nobody can find my clinic online" | 🔍 Nobody Can Find Us | Curtain Raiser | Local SEO (Skill 10), Google Business (Skill 6) |
| "I don't have time to post on social media" | 📅 Can't Keep Up | Curtain Raiser | Content Strategy (Skill 2), Instagram (Skill 4), Video (Skill 8) |
| "My Google reviews are bad / I have no reviews" | ⭐ Bad Reputation Online | Curtain Raiser | Google Business (Skill 6), WhatsApp (Skill 7) |
| "I'm not getting enough enquiries" | 📞 Not Enough Leads | Growth Engine | Paid Advertising (Skill 11), Local SEO (Skill 10) |
| "I'm spending on ads but not seeing results" | 💸 Wasting Ad Money | Growth Engine | Paid Advertising (Skill 11), Analytics (Skill 9) |
| "Competitors are growing faster than me" | ⚔️ Losing to Competitors | Maturity Phase | Competitive Intelligence (Skill 13), Local SEO (Skill 10) |
| "People visit my website but don't call/book" | 🛒 Traffic But No Sales | Maturity Phase | Conversion Optimisation (Skill 12) |
| "I don't know which marketing is working" | 📊 Don't Know What's Working | Growth Engine | Analytics (Skill 9), Competitive Intelligence (Skill 13) |

### 6.2 Portal Entry Point Flow

```
Portal landing page
  → "What's your biggest challenge?" (8 need cards in customer language)
  → Customer clicks their challenge
  → Portal shows: which bundle solves it + which agent skills are involved
  → CTA: "Try free" (registers → profiling conversation → Maturity Report)
       or "Hire now" (selects bundle → billing → profiling → activation)

The Maturity Report IS the trial experience:
  Register → 10-min profiling chat → 5-min market research → full report delivered
  Customer sees their score, their needs, and their recommended plan
  THEN decides to hire (select bundle) or exit
```

### 6.3 Skill Cards (portal display language)

Each skill is shown to the customer as a capability card with:
- **What I do for you** (1 sentence, customer language)
- **What you get** (the KPI, customer language)
- **Which bundle includes this** (badge)

| Skill | What I do for you | What you get | Bundle |
|---|---|---|---|
| Customer Profiling | "I understand your business and goals before recommending anything" | Your personalized digital marketing plan | All bundles |
| Market Research | "I research your current digital presence and score it honestly" | Digital Marketing Maturity Report (1–7 score + action plan) | All bundles |
| Content Strategy | "I plan your monthly content calendar so you never wonder what to post" | A theme-aligned content plan, approved by you | Curtain Raiser+ |
| Instagram | "I create and publish your Instagram posts and reels" | Consistent Instagram presence driving enquiries | Curtain Raiser+ |
| Facebook | "I keep your Facebook page active and local" | Local community presence and event visibility | Curtain Raiser+ |
| Google Business | "I optimise your Google presence and respond to reviews" | More calls and direction requests from Google | Curtain Raiser+ |
| WhatsApp | "I send appointment reminders and updates to your patients" | More bookings from WhatsApp with zero effort from you | Curtain Raiser+ |
| Video & Visuals | "I create short videos and visual content for your brand" | Higher engagement and better brand recall | Curtain Raiser+ |
| Analytics | "I track what's working and report your results every month" | Clear monthly KPI report in plain language | Growth Engine+ |
| Local SEO | "I improve how your business appears in local Google searches" | More patients finding you via search | Growth Engine+ |
| Paid Advertising | "I run targeted Meta and Google ads within your approved budget" | More enquiries at a lower cost per lead | Growth Engine+ |
| Conversion Optimisation | "I fix why website visitors don't call or book" | Higher booking rate from your existing traffic | Maturity Phase |
| Competitive Intelligence | "I monitor your top 3 competitors so you stay ahead" | Monthly alerts on competitor moves + recommended responses | Maturity Phase |

---

## 7. Professional Template Definition

```
ProfessionalTemplate:
  name: "Digital Marketing Professional — Dental & Healthcare"
  description: "Domain-expert digital marketing for dental clinics and healthcare practices in India.
                Full skill stack from customer profiling and maturity scoring through content, social,
                SEO, paid advertising, conversion optimisation, and competitive intelligence.
                Business KPI: patient/client acquisition and measurable digital marketing ROI."
  professional_type: "DIGITAL_MARKETING_HEALTHCARE"
  lifecycle_type: "PERMANENT"
  phase_bundles:
    - bundle: "CURTAIN_RAISER"
      skills: [CUSTOMER_PROFILING, MARKET_RESEARCH, CONTENT_STRATEGY, INSTAGRAM_MARKETING,
               FACEBOOK_MARKETING, GOOGLE_BUSINESS_PROFILE, WHATSAPP_BUSINESS, VIDEO_CONTENT_CREATION]
      target_maturity_range: "1-3"
    - bundle: "GROWTH_ENGINE"
      skills: [CURTAIN_RAISER_SKILLS, PERFORMANCE_ANALYTICS, LOCAL_SEO, PAID_ADVERTISING]
      target_maturity_range: "3-5"
    - bundle: "MATURITY_PHASE"
      skills: [GROWTH_ENGINE_SKILLS, CONVERSION_OPTIMISATION, COMPETITIVE_INTELLIGENCE]
      target_maturity_range: "5-7"
  decision_space_template:
    execution_model: "APPROVAL_GATE"
    professional_type: "DIGITAL_MARKETING_HEALTHCARE"
    authorized_actions:
      # Intelligence skills (always authorized, all bundles)
      - { actionType: "CUSTOMER_PROFILING", description: "Conduct AI-native profiling conversation and build Customer Profile" }
      - { actionType: "MARKET_RESEARCH", description: "Research customer's digital presence and calculate maturity score" }
      # Phase 1 — Curtain Raiser
      - { actionType: "INSTAGRAM_POST", description: "Create and publish approved Instagram posts" }
      - { actionType: "INSTAGRAM_STORY", description: "Create and publish approved Instagram stories" }
      - { actionType: "INSTAGRAM_REEL", description: "Create and publish approved Instagram reels" }
      - { actionType: "FACEBOOK_POST", description: "Create and publish approved Facebook posts" }
      - { actionType: "FACEBOOK_EVENT", description: "Create approved Facebook events" }
      - { actionType: "GOOGLE_BUSINESS_POST", description: "Publish approved Google Business updates" }
      - { actionType: "GOOGLE_REVIEW_RESPONSE", description: "Respond to Google reviews with approved templates" }
      - { actionType: "WHATSAPP_BROADCAST", description: "Send approved broadcast messages to opted-in patients" }
      - { actionType: "WHATSAPP_REMINDER", description: "Send appointment reminders using pre-approved templates" }
      - { actionType: "CONTENT_STRATEGY", description: "Propose monthly content calendar" }
      - { actionType: "VIDEO_CONTENT", description: "Create and publish approved video content" }
      # Phase 2 — Growth Engine (activated at Score 3+)
      - { actionType: "LOCAL_SEO_AUDIT", description: "Audit and report on local SEO signals", phase: "GROWTH_ENGINE" }
      - { actionType: "LOCAL_SEO_CONTENT", description: "Publish approved SEO-optimised content", phase: "GROWTH_ENGINE" }
      - { actionType: "PAID_AD_CAMPAIGN", description: "Launch approved paid campaigns within customer budget", phase: "GROWTH_ENGINE" }
      - { actionType: "PAID_AD_OPTIMISE", description: "Optimise bids and creative within approved parameters", phase: "GROWTH_ENGINE" }
      # Phase 3 — Maturity Phase (activated at Score 5+)
      - { actionType: "CONVERSION_ANALYSIS", description: "Analyse landing page and funnel performance", phase: "MATURITY_PHASE" }
      - { actionType: "AB_TEST_VARIANT", description: "Create and launch approved A/B test variants", phase: "MATURITY_PHASE" }
      - { actionType: "COMPETITOR_MONITOR", description: "Monitor and report on top 3 competitors' public digital activity", phase: "MATURITY_PHASE" }
    prohibited_actions:
      - { actionType: "PATIENT_DATA_SHARE", description: "Share any patient/client information — absolute prohibition" }
      - { actionType: "CLINICAL_CLAIM_POST", description: "Post unverifiable clinical outcome claims" }
      - { actionType: "COMPETITOR_COMPARISON", description: "Post content comparing to or disparaging competitors" }
      - { actionType: "UNAPPROVED_BROADCAST", description: "Send WhatsApp messages to non-opted-in contacts" }
      - { actionType: "DIRECT_MESSAGE_ACCESS", description: "Access or respond to Instagram/Facebook direct messages" }
      - { actionType: "BUDGET_OVERRUN", description: "Spend beyond customer-approved monthly ad budget — absolute prohibition" }
      - { actionType: "AUTHENTICATED_DATA_ACCESS", description: "Access any external data source behind authentication without explicit authorisation" }
    always_ask_actions:
      - { actionType: "NEGATIVE_REVIEW_RESPONSE", description: "Custom response to negative reviews (beyond templates)" }
      - { actionType: "NEW_PLATFORM_EXTENSION", description: "Add a new platform not in the original setup" }
      - { actionType: "BUDGET_INCREASE", description: "Increase ad budget above approved monthly limit" }
      - { actionType: "RETARGETING_CAMPAIGN", description: "Run retargeting — requires pixel confirmation and privacy policy check" }
      - { actionType: "WEBSITE_CHANGE", description: "Any change to customer's live website" }
      - { actionType: "COMPETITOR_NAMED_REPORT", description: "Include named competitor in any customer-facing report" }
  skill_runtime_defaults:
    approval_mode: "CUSTOMER_APPROVAL"
    synthetic_approval_confidence_threshold: 0.90
    synthetic_approval_min_history: 20
    goal_miss_escalation_months: 2
    delivery_channels: ["WHATSAPP_VOICE", "WHATSAPP_TEXT", "PORTAL", "EMAIL_PDF", "PUSH"]
    override_window_hours: 24
    api_budget:
      phase_1_skills_llm_calls_per_month: 60
      phase_2_skills_llm_calls_per_month: 100
      phase_3_skills_llm_calls_per_month: 80
      intelligence_skills_llm_calls_per_month: 80
      synthetic_approval_overhead_llm_calls: 20
      phase_1_external_api_calls_per_month: 200
      phase_2_external_api_calls_per_month: 400
      phase_3_external_api_calls_per_month: 500
    graceful_reduction_threshold: 0.80
  self_governance:
    mid_month_pace_check_day: 15
    mid_month_alert_threshold: 0.60
    consecutive_miss_escalation_threshold: 2
    override_rate_downgrade_threshold: 0.10
  strategic_cognition:
    skill_activation_plan_prompt: "DMA/STRATEGIC/SKILL_ACTIVATION_PLAN"
    performance_assessment_prompt: "DMA/STRATEGIC/PERFORMANCE_ASSESSMENT"
    trigger_events:
      - type: "POST_ONBOARDING"
        condition: "skill_1_maturity_report_complete == true"
        prompt: "SKILL_ACTIVATION_PLAN"
      - type: "PERIODIC_REVIEW"
        condition: "monthly_day_1"
        prompt: "PERFORMANCE_ASSESSMENT"
      - type: "DEVIATION_ALERT"
        condition: "any_active_skill_kpi_pace < 0.60 at day_15"
        prompt: "PERFORMANCE_ASSESSMENT"
      - type: "MATURITY_SCORE_CHANGE"
        condition: "customer_maturity_score_delta >= 1"
        prompt: "SKILL_ACTIVATION_PLAN"
    strategic_state_table: "business.agent_strategic_state"
  is_published: true
```

**Beauty Artist variant** uses the same template with these differences:
- `professional_type: "DIGITAL_MARKETING_BEAUTY"`
- Adds: `PORTFOLIO_PUBLISH`, `BEFORE_AFTER_GALLERY` to authorized_actions
- Adds: Creative Standard Profile configuration (Amendment A-005) — Sana's aesthetic voice

---

**Customer feedback signals captured:**
- Post approval (APPROVED state in evidence record) → positive signal for content style, timing, format
- Post rejection with reason → negative signal; rejection reason stored in Tier 2 customer context
- KPI achievement vs target (Skill 7 analytics) → performance signal for content strategy

**Domain knowledge contribution (Tier 1 + Tier 3 — WAOOAW IP):**
- Aggregate: which content formats, posting times, and themes drive appointment enquiries for dental/beauty practices across India (anonymised, no customer identification)
- Updated in Platform Intelligence Store (Tier 3) via daily batch aggregation

**Customer context learning (Tier 2 — customer private):**
- Updated brand voice embeddings after every approved post
- Rejection pattern embeddings — what Dr. Mehta rejected and why (private to her account)

---

## 9. Constitutional Checklist

- [x] Every Skill has a measurable business KPI (C-037) — appointment enquiries, bookings, calls, CPL, ROAS, maturity score
- [x] Every MCP tool call has a Decision Space authorization entry (C-041)
- [x] Every prohibited action explicitly protects a constitutional principle
- [x] Customer Profiling uses registration data as base — never re-asks known information (C-039, AD-013)
- [x] Market Research restricted to publicly available data only — no authenticated access (Constitutional Floor — privacy)
- [x] Paid Advertising has hard budget cap as ABSOLUTE prohibition — BUDGET_OVERRUN listed as prohibited action
- [x] Healthcare advertising compliance check on paid ad creatives is REQUIRED (not DEGRADABLE)
- [x] Onboarding flow: registration + profiling completable in ≤ 15 minutes total (AD-013, C-039)
- [x] Maturity Report delivers value before customer commits to full hire (trial experience design)
- [x] Phase Bundle upgrades require customer approval — Decision Space expansion is Employer-authorized (C-036)
- [x] Acceptance Scenarios AS-001 and AS-002 cited
- [x] RAG Tier 1 (WAOOAW IP), Tier 2 (customer private), and Tier 3 (anonymised platform intelligence) explicitly separated (FR-003)
- [x] Competitive intelligence is customer-private — not aggregated to Tier 3 (C-041)
- [x] No prohibited action violates a Constitutional Floor
- [x] Patient/client data protection is absolute and double-listed in prohibited actions
- [x] PATIENT_IMAGE_CONSENT_CONFIRMED added to always-ask in Skills 4 and 8 — constitutional evidence record required before any patient/client image is used (R-011 note R011-01 — resolved in v2.0 per R-014)
- [x] **C-050 check (Strategic Cognition): Section 3.15 added. DMA/STRATEGIC/SKILL_ACTIVATION_PLAN invoked after Skill 1 maturity report; DMA/STRATEGIC/PERFORMANCE_ASSESSMENT invoked monthly + on deviation. Both prompts include strategic_reasoning_chain, portfolio_health, c050_strategic_intent, c048_check, and c049_honest_assessment fields. Professional Template declares strategic_cognition block with 4 trigger events.**
- [x] **C-051 check (Resource Transparency): Section 3.16 added. UsageUnits defined (Content Creation, Quick Edit, Research, Strategy, Report). minimum_model_tier declared for every prompt in Prompt Catalogue. Customer budget communication thresholds (30%, 10%) declared. Emergency override never blocks service. DMA/TOKEN_ECONOMY/USAGE_SUMMARY prompt added.**
- [x] **C-036/C-037/C-048 check (Off-Topic Boundary): Section 3.17 added. 5 redirect hooks declared (competitor_activity, kpi_pace, pending_approval, maturity_score_change, google_review_alert). Adjacent professional routing declared (accounting, HR, legal). PLATFORM/BOUNDARY/OFF_TOPIC_REDIRECT prompt in Prompt Catalogue. 3-attempt graduation pattern declared.**
- [x] **C-052 check (Context Fidelity, Isolation, Uniqueness): Context Bootstrap Protocol loads Decision Space, session state, performance history, and Creative Fingerprint before every session. Creative Fingerprint Enforcer (M-3) runs before every content generation — uniqueness_score computed vs competitor content (threshold 0.75) and own recent content (threshold 0.85). Fingerprint is updated online after every approval/rejection. Two competing dental clinics in the same neighbourhood are guaranteed differentiated content. Tier 3 has 24-hour write lag — no real-time cross-customer data.**
- [ ] **C-055 check (Campaign Coherence): Section 3.21 added (v2.5). Platform Intelligence declared with 10 platform coverage + dependency status. Campaign Theme Cascade declared (3 levels, all required fields). SCR 5-check criteria declared with thresholds, model tiers, and fail actions. SCR Check 3 (Compliance) fail_action = ROUTE_TO_CUSTOMER (never silent). Content Approval Modes declared (POST_APPROVAL→CAMPAIGN_APPROVAL→CAMPAIGN_AUTO) with upgrade/downgrade criteria. Campaign Digest declared (weekly, Monday 09:00 IST, 3 channels). 6 new campaign prompts + 1 Platform Intelligence prompt in Prompt Catalogue. MASTER_THEME_PROPOSAL is FRONTIER/BREAKING. Campaign SQL tables referenced (4 tables).**
- [ ] **C-056 check (Ad Spend Transparency): ADR-026 declared. Skill 11 uses WAOOAW_MANAGED connection model. customer_ad_accounts + ad_spend_wallets + ad_spend_ledger tables referenced. management_fee_pct = 10 declared in Skill 11. PAGE_ACCESS_GRANT_REQUEST as always-ask action. ad_spend_ledger is append-only (no UPDATE/DELETE). CUSTOMER_OWNED declared with PENDING_FOUNDER_AUTHORIZATION.**
- [ ] **C-057 check (AI Agency Professional Standard): Section 4.0 (agency pitch) declared with portfolio claim format and prohibited claims. Section 4.2 (professional intake opening) includes expertise-first model — agent demonstrates market knowledge before asking configuration questions. Competitive positioning response declared (honest comparison with C-049 limitations disclosure). institutional.dma_performance_portfolio referenced as Tier 3 source. portfolio_claim_approved = TRUE enforced before any portfolio stat appears in conversation. Skill 14 (WAOOAW self-marketing) declared with PENDING_FOUNDER_AUTHORIZATION.**

---

## 10b. Prompt Catalogue

> **Gate requirement (Section 2 + Section 10 of Activation Gate, C-045, C-050, AD-018, AD-021):** Every LLM inference point must have an approved prompt. Prompts reside in `architecture/reference/prompts/digital-marketing-agent-prompts.md` and are seeded in `institutional.agent_prompt_versions`.

All DMA prompts are catalogued in `digital-marketing-agent-prompts.md`. Key prompts relevant to the Strategic Cognition Layer (new in v2.1):

| Prompt ID | Layer | Step | Type | `minimum_model_tier` |
|---|---|---|---|---|
| `DMA/STRATEGIC/SKILL_ACTIVATION_PLAN` | Strategic Cognition | Post-Skill-1: which skills to activate + sequence | BEHAVIOURAL | `FRONTIER` (first plan) / `MID_TIER` (re-plans) |
| `DMA/STRATEGIC/PERFORMANCE_ASSESSMENT` | Strategic Cognition | Monthly/deviation: portfolio health + strategic recommendation | BEHAVIOURAL | `MID_TIER` |
| `DMA/SELF_GOVERNANCE/DIAGNOSIS` | Self-Governance | Goal miss root cause + C-049 assessment | BEHAVIOURAL | `FRONTIER` |
| `DMA/SELF_GOVERNANCE/ESCALATION` | Self-Governance | 2-month escalation report for customer | BEHAVIOURAL | `MID_TIER` |
| `DMA/TOKEN_ECONOMY/USAGE_SUMMARY` | Token Economy | Budget status in customer language (portal widget + WhatsApp) | USAGE_SUMMARY | `MID_TIER` |
| `PLATFORM/BOUNDARY/OFF_TOPIC_REDIRECT` | Off-Topic Boundary | Graceful deflection + specific monitoring hook (C-036, C-037, C-048) | BEHAVIOURAL | `MID_TIER` |

**Section 10 gate check:** Both strategic cognition prompts seeded in SQL. C-050 in checklist. Trigger events declared in Professional Template. Gate 10: PASS.
**Section 11 gate check:** Section 3.16 added. UsageUnits defined. minimum_model_tier declared for all prompts. C-051 in checklist. Gate 11: PASS.

---

## 10. Review and Approval

**EA Review (v1.0):** R-011 — APPROVED WITH NOTE (R011-01: PATIENT_IMAGE_CONSENT_CONFIRMED — resolved in v2.0)
**Founder Approval (v1.0):** GRANTED — 2026-07-08 (per GENESIS Part 05)
**EA Review (v2.0):** R-014 — APPROVED — 2026-07-09
**Founder Approval (v2.0):** GRANTED — 2026-07-09
**EA Review (v2.1):** R-018 — APPROVED — 2026-07-11 (Strategic Cognition Layer)
**Status:** v2.1 APPROVED — active ProfessionalTemplate
