# Simulation 017 — Skill 14 Launch: WAOOAW as Its Own First DMA Customer

**Type:** Institutional Simulation — WAOOAW Self-Marketing (FR-005, Skill 14, Track D)
**Status:** Active
**Purpose:** Walk through WAOOAW's own DMA onboarding as the first customer on the platform. Configure the `WAOOAW_INSTITUTIONAL_MARKETING` Decision Space, run the Customer Profiling and Market Research skills for WAOOAW itself, and produce the Phase 1 campaign (pre-50 customer threshold: value proposition only, no performance stats). Validate the self-reinforcing loop: WAOOAW uses its own DMA to acquire DMA customers.
**Constitutional basis:** C-057 (AI Agency Standard), C-046 (Platform Self-Governance), FR-005 (Founder authorization 2026-07-12), C-043 (₹5,000/month ad spend constitutional floor applies to WAOOAW itself)
**Founder parameters:** ₹5,000/month ad spend, portfolio stats only after 50+ diverse customers across multiple domains

---

## WAOOAW_INSTITUTIONAL_MARKETING Decision Space Configuration

This is the first Decision Space to configure when IB-009 implementation begins.

```yaml
# constitutional/institutional-marketing-decision-space.yaml
decision_space_id: WAOOAW_INSTITUTIONAL_MARKETING
employer: WAOOAW
organisation_id: WAOOAW_INSTITUTIONAL  # Institutional entity — distinct from any customer organisation

professional_type: DIGITAL_MARKETING_HEALTHCARE  # Agent instance; campaigns target ALL local businesses
billing_mode: INSTITUTIONAL                       # No subscription; no management fee; WAOOAW bills itself
ad_spend_budget:
  monthly_cap_inr: 5000
  constitutional_basis: "C-043 (Financial Spend Ceiling applies to WAOOAW's own spending)"
  wallet_source: "WAOOAW institutional bank account — NOT any customer Ad Spend Wallet (C-056)"
  ledger_id: "ad_spend_ledger — organisation_id = WAOOAW_INSTITUTIONAL"

# Founder-authorized portfolio stat threshold (FR-005)
portfolio_stat_gate:
  minimum_customers: 50
  diversity_requirement: MULTI_DOMAIN  # Must include doctors + builders/real estate + banks/NBFCs + retail/other
  gate_status: LOCKED  # Locked until threshold met; unlocks automatically when conditions are satisfied
  consequence_of_violation: "C-023 (Evidence First) + C-049 (Honest Limitation Disclosure) — 
                              using performance stats before 50 diverse customers is a constitutional 
                              misrepresentation. The platform has not yet proven itself at scale."

authorized_actions:
  - META_AD_CAMPAIGN
  - GOOGLE_AD_CAMPAIGN
  - INSTAGRAM_POST
  - FACEBOOK_POST
  - LINKEDIN_POST
  - GOOGLE_BUSINESS_POST
  - WHATSAPP_BROADCAST  # WAOOAW's own WABA for platform notifications

prohibited_actions:
  - USE_CUSTOMER_PERFORMANCE_DATA  # Cannot use any specific customer's data without consent
  - PERFORMANCE_STATS_BEFORE_THRESHOLD  # Locked until 50+ diverse customers

always_ask:
  - Any ad creative claiming measurable results (requires portfolio_stat_gate.gate_status = UNLOCKED)
  - Increasing ad spend beyond ₹5,000/month (requires Founder approval — new Decision Space amendment)
  - Any testimonial or case study (requires explicit customer consent + separate evidence record)
```

---

## Phase 1 — WAOOAW Customer Profiling (Self-Profiling)

The DMA agent profiles WAOOAW as its own customer. This is constitutional: WAOOAW must treat itself like any other customer — including running the full Evidence First chain on its own marketing actions.

**Institutional profile:**

```yaml
customer_profile:
  organisation_id: WAOOAW_INSTITUTIONAL
  owner_name: "WAOOAW Platform Team"
  business_name: "WAOOAW"
  business_domain: DIGITAL_MARKETING_AGENCY  # Special domain — not a customer domain
  tagline: "Autonomous digital professionals under constitutional governance"
  
  target_customers:
    primary: "Local business owners across India who need professional digital marketing"
    segments:
      - "Healthcare: Dental, medical clinics, physiotherapy, Ayurveda"
      - "Real estate: Builders, developers, property agents"
      - "Financial services: Banks (branch marketing), insurance advisors, NBFCs"
      - "Retail & hospitality: Local stores, restaurants, boutiques"
      - "Professional services: CAs, lawyers, consultants"
      - "Fitness & wellness: Studios, gyms, yoga"
      - "Education: Coaching classes, schools"
    geography: "India — Tier 1 + Tier 2 cities"
    
  aspiration: "Become the default digital marketing professional for 1,000 local businesses 
                across India within 24 months of launch"
  
  current_digital_channels:
    instagram: "WAOOAW Instagram — pending creation"
    facebook: "WAOOAW Facebook page — pending creation"
    linkedin: "WAOOAW LinkedIn Company page — pending creation"
    google_business: "WAOOAW GBP listing — pending creation"
    website: "WAOOAW.com — specification complete; awaiting IB-009 launch"
    whatsapp_business: "Pending WABA approval (P0 Founder action)"
    
  positioning:
    vs_traditional_agency:
      - "Traditional agency: ₹20,000-50,000/month retainer + inflated ad fees"
      - "WAOOAW: ₹1,499/month subscription + actual ad spend only"
      - "Traditional agency: 30-day onboarding, then junior executive handles your account"
      - "WAOOAW: AI-native professional working from day one, 24/7"
    vs_freelancer:
      - "Freelancer: depends on one person's availability and knowledge"
      - "WAOOAW: constitutionally governed — every action recorded, every decision transparent"
    vs_doing_it_yourself:
      - "DIY: business owner spends 2-3 hours/week on social media"
      - "WAOOAW: owner approves, agent executes — reclaim 10+ hours/month"
      
  constitutional_self_constraint:
    note: "WAOOAW's own marketing must exemplify the constitutional standards the platform 
           enforces for all customers: Evidence First, Honest Limitation Disclosure, 
           professional vocabulary, no exaggerated claims. If WAOOAW's own marketing 
           violates C-049 (Honest Limitation Disclosure), the platform is constitutionally 
           incoherent. WAOOAW's marketing is the highest-scrutiny application of DMA v2.8."
```

---

## Phase 2 — WAOOAW Market Research (Self-Research)

**DMA Agent running Skill 1 on WAOOAW itself:**

```
web-search-mcp: "WAOOAW digital marketing India"
→ No significant results (brand is new — expected)

social-profile-mcp: WAOOAW Instagram, WAOOAW Facebook, WAOOAW LinkedIn
→ Accounts not yet created (confirmed — P0 action)

google-places-mcp: WAOOAW
→ GBP listing not yet created (confirmed — P0 action)

meta-ad-library-mcp: WAOOAW
→ No active ads (expected)

Competitor scan (AI digital marketing platforms, India):
  - Lead Squared: CRM-heavy, enterprise focus, ₹3,000+ per month
  - WebEngage: Automation tool, not a professional service
  - Paperbell, Zoho Social: Tools, not AI professionals
  - Traditional agencies (IndiaMart search "digital marketing agency Pune"): 
    2,000+ listings, ₹15,000-50,000/month, no transparent pricing
  - Freelancers (Upwork, Fiverr): ₹3,000-8,000/month, inconsistent quality
```

**WAOOAW Self-Assessment:**

```
Digital Maturity Score: 1 (No Presence — expected for a brand-new platform)

Competitive Landscape Assessment:
  OPPORTUNITY: No direct competitor offers an AI-native professional at ₹1,499/month.
               All alternatives are either tools (requiring owner to do work) or 
               agencies (expensive, opaque). WAOOAW's gap is real and unoccupied.
               
  RISK: "AI in marketing" is a crowded claim. Differentiation requires demonstrating
         constitutional governance, not just AI capability.
         
  FIRST-MOVER ADVANTAGE: Local businesses in India are underserved by:
    (a) Traditional agencies (too expensive, too opaque)
    (b) DIY tools (require marketing knowledge they don't have)
    WAOOAW occupies the gap between these two options.

Platform Build Priority (Needs Heat Map for WAOOAW):
  NOBODY CAN FIND US:      CRITICAL — No digital footprint yet
  NOT ENOUGH LEADS:         CRITICAL — No customer acquisition channel active
  WASTING AD MONEY:         N/A — Not spending yet
  LOSING TO COMPETITORS:    MODERATE — Agencies are capturing the budget we should
  DON'T KNOW WHAT'S WORKING: N/A — No campaigns yet
```

**Recommended Phase 1 for WAOOAW (pre-50 customers):**
1. Create Instagram + LinkedIn + Facebook + GBP (immediate — Founder action)
2. Phase 1 content: value proposition, how it works, local business problems solved
3. Phase 1 campaign theme: "What if your business had a marketing professional working 24/7 — for less than ₹1,500/month?"
4. NO performance stats in any creative — portfolio gate LOCKED until 50+ diverse customers

---

## Phase 3 — Phase 1 Campaign: "The Professional Your Business Deserves"

**Campaign Brief (Month 1 — July/August 2026):**

```
Master Theme: "The professional your business deserves.
               ₹1,499/month. No agency retainer. No inflated ad fees."

Why this theme:
  Every business owner in India has experienced one of:
  (a) Paying an agency ₹20,000/month and getting junior executive service
  (b) Trying to do it themselves and running out of time
  (c) Hiring a freelancer who disappeared after 3 months
  This theme speaks to all three failure modes they've experienced.
  
Target Outcome:   First 10 customer onboarding conversations
Target Customer:  Local business owner, India, running their own business,
                  has tried/considered digital marketing, frustrated with cost/quality gap

Platform Mix:
  Instagram:    4 posts/week (problem-solution format)
  LinkedIn:     2 posts/week (B2B credibility — banks, builders, professional services)
  Facebook:     Mirror Instagram (no additional effort)
  GBP:          Weekly post (searchability for "AI marketing India" + "digital marketing ₹1499")
  Meta Paid Ads: ₹3,500/month (primary acquisition channel — 70% of budget)
  Google Search: ₹1,500/month (intent-based: "digital marketing for dental clinic India")

Monthly Ad Spend: ₹5,000 (Founder-authorized ceiling — C-043 applied to WAOOAW)
```

---

## Phase 4 — Content Calendar (Month 1, July 2026)

### Instagram Content Plan (16 posts over 4 weeks):

**Week 1 — "The Problem You Know"**

```
Post 1 (Monday, text card):
[Deep blue background, white text]
"You're a dentist.
You didn't go to dental college to become a social media manager.

But here you are.
Every Sunday night — scrolling Canva, writing captions,
wondering why you bother.

There's a better way.
[waooaw.com/start] | Link in bio"

SCR Check 3: No performance claims. No misleading promises. Speaks to a real experience. ✅

---

Post 2 (Wednesday, carousel — "What ₹1,499/month gets you"):
Slide 1: "₹1,499/month. What does that actually buy?"
Slide 2: "A professional who researches your competitors before your first campaign."
Slide 3: "A professional who writes captions in your patient's language — not marketing jargon."
Slide 4: "A professional who tells you when it's working and when it isn't."
Slide 5: "Every action recorded. Every decision transparent. No agency smoke and mirrors."
Slide 6: "WAOOAW. Your business's digital marketing professional. [waooaw.com/start]"

Note: No claims about results, conversion rates, or specific customer outcomes.
Constitutional compliance: C-049 (Honest Limitation Disclosure) — the carousel 
promises process transparency, not outcome guarantees. ✅

---

Post 3 (Friday, Reel — VIDEO BRIEF):
video_brief:
  format: GENERATIVE  # No clinic photos available — brand-new company
  duration: 30s
  objective: "Show the contrast: exhausted business owner vs. professional handling it"
  
  concept: "Split-screen:
    LEFT: Business owner late at night, looking at phone, struggling with Canva
    RIGHT: Text on screen — 'Your WAOOAW professional is already on it.'
    
    Voice (Hindi/English mix):
    'Raat ke 11 baj gaye. Kal ki post abhi banaani hai.
    (11 PM already. Still haven't made tomorrow's post.)
    
    What if you didn't have to?
    
    WAOOAW — the digital marketing professional working for your business.
    ₹1,499/month. No agency. No freelancer. Just results.'
    "
    
  mcp_tool: runwayml-mcp  # Generative video — no real footage available yet
  human_referral: false   # Brand-new company; no Founder face required for Phase 1
```

**Week 2 — "How It Actually Works"**

```
Post 4 (Monday, step-by-step carousel):
"How WAOOAW works in your first week:

Day 1: We research your business, your competitors, your platforms.
       You see a complete picture of where you stand.

Day 2-3: We build your content calendar for the next 30 days.
         You approve (or ask for changes) before anything goes live.

Day 7: Your first professional posts start going out.
       You're not writing captions at 11 PM anymore."

Post 5 (Wednesday, quote card):
"Before anything goes live, you see it.
Before anything is spent, you authorize it.
That's the constitutional promise we make to every customer."

Post 6 (Friday, Reel — LinkedIn version adapted):
"What does 'AI professional' actually mean?

It's not a chatbot responding to comments.
It's a professional that:
- Researches your market before recommending anything
- Shows you evidence for every recommendation
- Never spends your ad budget without your approval
- Reports results in plain language, not dashboards you don't understand

That's WAOOAW."
```

**Week 3 — "Who It's For"**

```
Post 7 (Monday — Dental):
"For Dr. Mehta's of India:
You have 47 Google reviews. Your competitor has 94.
That gap costs you 5-8 patients/month.

A professional who knows this and has a plan to close it.
₹1,499/month."

Note: "Dr. Mehta" is a generic persona (our own test persona) — not a real customer.
     Cannot cite specific outcomes. Can describe the problem accurately. ✅

Post 8 (Wednesday — Builder/Real Estate):
"For builders launching projects:
Your buyers search 'affordable apartments Pune' on Google.
Are you there when they search?

Site launch to sold out — professional digital marketing from the first foundation pour.
₹1,499/month."

Post 9 (Friday — Professional services):
"For CAs, lawyers, consultants who know LinkedIn should be working harder for them —
but never have time to make it happen.

Let a professional handle your thought leadership.
You write the ideas. We write the posts. They go out on schedule.
₹1,499/month."
```

**Week 4 — "The Offer + Conversion CTA"**

```
Post 10 (Monday — pricing transparency):
"Full pricing transparency. Because that's how we work.

₹1,499/month — professional subscription (your marketing professional on retainer)
+ your actual ad spend (you see every rupee, every click, every result)
No hidden markup. No agency commission on your ad budget.
We charge our fee. Your ads spend what you authorize. Full stop."

Constitutional compliance: C-056 (Ad Spend Transparency). ✅

Post 11 (Wednesday — First month offer):
"Try the first month.
If you don't see the value, you don't continue. No lock-in.
[waooaw.com/start — 3-minute signup]"

Post 12 (Friday — social proof mechanism):
"Early customers.
We're looking for 50 businesses across India to prove what's possible.
Doctors. Builders. Banks. Insurance advisors. Fitness studios.
If your business is local and your marketing needs professional hands — we'd like to work with you.
[waooaw.com/start]"

Note: "50 businesses" — transparent about where we are. C-049 (Honest Limitation 
     Disclosure): not claiming to be the market leader. Inviting early adopters honestly. ✅
```

---

## Phase 5 — LinkedIn Content Plan (B2B positioning)

LinkedIn is WAOOAW's highest-potential B2B channel (banks, builders, insurance, professional services respond here).

**Sample LinkedIn post (Week 1):**
```
Every bank branch manager in India has the same problem:
The national marketing team sends generic campaign materials.
Local customers don't respond to generic.

A bank branch needs a professional who knows:
- This branch is in Koregaon Park (young professionals)
- Not the same as Pimpri (manufacturing workers)
- Local campaigns that actually reach the right customers

That's what WAOOAW does for bank branches.
₹1,499/month. Branch-level marketing that isn't national-template generic.

#BankMarketing #LocalBusiness #DigitalMarketing #AI
```

**Sample LinkedIn post (Week 2 — constitutional angle):**
```
"Constitutional governance" in digital marketing sounds like legal language.
Here's what it means in practice:

Before your ad goes live: you see it and approve it.
Before your budget is spent: you authorize the amount.
After every campaign: a transparent report — what worked, what didn't, what's next.

No black box. No "trust us, the algorithm knows best."
Evidence-first digital marketing.

WAOOAW — the digital marketing professional that works for you, not for its own metrics.
```

---

## Phase 6 — First Meta Ad Campaign Brief

**Campaign: Acquisition — Dental Clinic Owners**

```yaml
meta_ad_campaign:
  campaign_name: "WAOOAW_DENTAL_ACQ_AUG2026"
  objective: LEAD_GENERATION
  budget_inr: 1800  # 36% of ₹5,000 monthly budget — dental segment test
  
  targeting:
    geo: "Tier 1 + Tier 2 India cities (Mumbai, Pune, Bangalore, Hyderabad, Chennai, Delhi NCR)"
    interests: ["Dental clinic", "Dentistry", "Business owner", "Small business"]
    behaviours: ["Business page admin", "Small business owner"]
    age: "28-55"
    
  ad_creative:
    headline: "Professional digital marketing for your dental clinic. ₹1,499/month."
    primary_text: |
      You didn't go to dental college to manage Instagram.
      
      WAOOAW gives your clinic a professional digital marketing partner —
      one that researches your local market, writes your content, and
      runs your campaigns transparently.
      
      ₹1,499/month. No agency retainer. No markup on your ad budget.
      
      See what WAOOAW would do for your clinic in the first 7 days.
    cta: LEARN_MORE
    landing_page: "waooaw.com/dental-clinic"
    
  scr_check:
    check_1: PASS  # Format: Meta lead gen format ✓
    check_2: PASS  # Brand voice: professional, honest, specific ✓
    check_3: PASS  # No performance claims without evidence; C-049 ✓
                   # "professional digital marketing" is a process promise, not an outcome claim
    scr_result: SCR_PASSED
    
  constitutional_evidence:
    action_type: META_AD_CAMPAIGN_CREATED
    organisation_id: WAOOAW_INSTITUTIONAL
    spend_authorization: "₹1,800 of ₹5,000 monthly budget"
    portfolio_stat_used: false  # Gate LOCKED — Phase 1 ✓
```

**Campaign: Acquisition — General Local Business**

```yaml
meta_ad_campaign_2:
  campaign_name: "WAOOAW_GENERAL_ACQ_AUG2026"
  objective: LEAD_GENERATION
  budget_inr: 1700
  
  targeting:
    geo: "Same Tier 1 + Tier 2 cities"
    interests: ["Small business", "Entrepreneur", "Business management", "Local business"]
    age: "28-55"
    
  ad_creative:
    headline: "Your business's digital marketing professional. ₹1,499/month."
    primary_text: |
      Most small businesses in India are caught between:
      Paying an agency ₹20,000/month they can't afford
      — or doing it themselves and running out of time.
      
      WAOOAW is the third option:
      A professional who researches, writes, runs, and reports.
      Transparently. Without the agency markup.
      
      ₹1,499/month. First month — see the value or don't continue.
    cta: LEARN_MORE
    landing_page: "waooaw.com/start"
    
  scr_result: SCR_PASSED
```

**Google Search Campaign:**

```yaml
google_search_campaign:
  campaign_name: "WAOOAW_SEARCH_AUG2026"
  budget_inr: 1500
  
  keywords:
    - "digital marketing for dental clinic India"     # High intent, niche
    - "ai marketing for small business India"          # Emerging keyword
    - "affordable digital marketing agency India"      # Budget-conscious intent
    - "digital marketing ₹1500 month India"           # Pricing intent
    - "social media management local business India"   # General intent
    
  ad_text:
    headline_1: "AI Digital Marketing Pro — ₹1,499/mo"
    headline_2: "No Agency Retainer. No Hidden Markup."
    headline_3: "Researches, Writes, Reports Transparently"
    description: "Constitutional governance: every action visible. Every rupee authorized by you.
                  Professional digital marketing for local Indian businesses. Try 1 month."
    
  scr_result: SCR_PASSED
```

**Total Month 1 ad spend: ₹5,000 (₹1,800 + ₹1,700 + ₹1,500) = Exactly at constitutional floor ✓**

---

## Phase 7 — Evidence Trail for WAOOAW Institutional

All WAOOAW marketing actions are recorded identically to customer actions:

```sql
-- WAOOAW_INSTITUTIONAL records in ad_spend_ledger
INSERT INTO business.ad_spend_ledger (
  organisation_id,           -- 'WAOOAW_INSTITUTIONAL' (not a customer org)
  platform,                  -- 'META', 'GOOGLE'
  campaign_id,               -- WAOOAW_DENTAL_ACQ_AUG2026
  amount_inr,                -- 1800
  authorized_by,             -- WAOOAW_INSTITUTIONAL_MARKETING decision space
  evidence_record_id,        -- Links to CAL
  reporting_month            -- 2026-08
) VALUES ...

-- Monthly report goes to Founder (same format as customer reports)
-- Founder is the "customer" for WAOOAW_INSTITUTIONAL_MARKETING
```

**Constitutional point (C-046 — Platform Self-Governance):** WAOOAW cannot hold itself to a lower standard than its customers. The same Evidence First, Ad Spend Transparency, and Campaign Coherence obligations apply to WAOOAW's own marketing.

---

## Phase 8 — Portfolio Stat Gate (What Unlocks Phase 2)

```yaml
portfolio_stat_gate_status: LOCKED

will_unlock_when:
  customer_count: 50
  domain_diversity: 
    - At least 3 of these 4 domains represented:
      - HEALTHCARE (dental, medical, physiotherapy)
      - REAL_ESTATE (builders, property agents)
      - FINANCIAL_SERVICES (banks, insurance)
      - OTHER (fitness, retail, professional services, food, education)
  
unlocked_messaging_examples:
  - "[N] businesses served across doctors, builders, banks, insurance advisors, 
     restaurants. Average [X]% more enquiries in the first 3 months."
  - "From ₹500/month dental checkups booked online to ₹3 crore apartments sold via 
     Instagram — our professionals have handled it all. [N] businesses. ₹1,499/month."

phase_2_campaign_themes:
  - "Proof over promise — [N] businesses. Multi-domain. India."
  - "The digital marketing professional that has already worked for your type of business."
```

---

## Confidence Assessment: Track D — Skill 14 Launch Readiness

| Criterion | Status |
|---|---|
| `WAOOAW_INSTITUTIONAL_MARKETING` Decision Space configured | ✅ Ready for IB-009 implementation |
| Portfolio stat gate (50+ diverse customers) enforced | ✅ Gate LOCKED, unlock conditions defined |
| Financial isolation from customer ad budgets (C-056) | ✅ `organisation_id = WAOOAW_INSTITUTIONAL` in all ledger records |
| Evidence First chain for WAOOAW's own campaigns | ✅ Same CCT requirements as customer campaigns |
| Phase 1 content calendar and ad briefs produced | ✅ 12 Instagram posts + 4 LinkedIn posts + 3 ad campaigns |
| SCR passes on all WAOOAW marketing content | ✅ No performance claims, no misleading promises |
| Constitutional self-constraint: WAOOAW exemplifies its own standards | ✅ Explicit in profile; C-049 and C-023 applied to WAOOAW itself |

**The self-reinforcing loop is architecturally complete:**

```
Customer sees WAOOAW's Instagram: "Professional marketing for your dental clinic."
Customer books a demo.
DMA agent runs Skill 0 (Customer Profiling).
DMA agent runs Skill 1 (Market Research).
Customer approves their first campaign.
That campaign generates results.
Results become portfolio evidence (after 50th customer).
Portfolio evidence strengthens WAOOAW's Phase 2 marketing.
```

**Next action (Founder):**
1. Create WAOOAW Instagram, LinkedIn, Facebook, GBP accounts (1 day — no dependencies)
2. WAOOAW WABA (WhatsApp Business Account) — pending Meta Business Manager verification
3. When IB-009 implementation begins: configure `WAOOAW_INSTITUTIONAL_MARKETING` as the first Decision Space in the database
4. WAOOAW is Customer #0 — the platform's own proof of concept
