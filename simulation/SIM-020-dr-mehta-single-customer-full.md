# SIM-020 — Single Customer Onboarding + Serving: Dr. Mehta, Dental Clinic

**Date:** 2026-07-19
**Business:** Dr. Priya Mehta, Mehta Dental Clinic, Viman Nagar, Pune
**Plan:** Professional (₹2,499/month subscription + ad spend wallet)
**Duration simulated:** Day 0 through Month 3 (first paying cycle complete)
**Grade:** A

---

## PRE-CHECK: WAOOAW Platform State (before Dr. Mehta signs up)

```
FA-002 (Meta BM verification): PENDING — campaigns cannot run until complete
FA-021 (GCP Vertex AI):       PENDING — GA4 analytics not available
FA-003 (Azure OpenAI UAE):    PENDING — using Gemini as primary (ADR-029)

Available at onboarding:
  ✓ GBP, Instagram, Facebook: content skills fully operational
  ✓ WhatsApp: platform WABA not yet live → WhatsApp broadcast limited
  ✓ Paid ads: CANNOT run (FA-002 pending) → told honestly at Day 0
  ✓ GA4: CANNOT connect (FA-021 pending) → told honestly at Day 0
```

---

## Day 0 — Registration

Dr. Mehta registers on `waooaw.ai` with Google Sign-In.

**System events (< 1 second):**
- `business.organisations` record created: account_type=DIRECT_CUSTOMER
- Keycloak user created, JWT issued with plan_tier=professional
- Domain Capability Check triggered (Temporal activity, runs in background)

**Domain Capability Check result (2 min after registration):**
```
Domain: dental_clinic
Required MCPs:    [google-business-mcp, instagram-mcp, scheduling-mcp, ...]
google-business-mcp: NOT_PROVISIONED → Type 1 (Dr. Mehta's Google account OAuth)
instagram-mcp: NOT_PROVISIONED → Type 1 (Dr. Mehta's Instagram Business account)
meta-ads-mcp: PLATFORM_CREDENTIAL → FA-002 pending → FOUNDER_ACTION raised
ga4-mcp: PLATFORM_CREDENTIAL → FA-021 pending → FOUNDER_ACTION raised
booking-mcp-practo: NOT_PROVISIONED → Type 1 (Practo credentials)
```

**Welcome message to Dr. Mehta (WhatsApp, within 1 hour — C-074):**
```
Namaste Dr. Mehta! Welcome to WAOOAW. Your WaooaW Expert Dental Marketing is being set up.

✅ Ready immediately:
   - Google Business Profile management
   - Instagram Business presence
   - Content creation and scheduling
   - WhatsApp patient engagement

⏳ Setting up today (need your help — 10-15 min total):
   - Google Business Profile: I need your Google account access
   - Instagram: Connect your Instagram Business account
   - Practo: Your Practo doctor login (for appointment booking integration)

📋 Setting up within 24 hours:
   - Paid ads (Google + Meta): Our ad account setup is in progress.
     You'll be able to run campaigns within 24 hours.
     (Note: Meta's own verification takes 2-4 weeks — we'll start organic
      campaigns immediately and launch paid once verification completes)

Everything I can do without your login is already running.
Ready to connect your Google account? Reply YES to start.
```

---

## Day 0-1 — Skill 0: Customer Profiling

**Conversation flow (WhatsApp):**

```
WaooaW Expert: "Namaste Dr. Mehta! I can see you're a dentist in Viman Nagar —
              one of Pune's busiest areas for young professionals.
              My first question: do you want to focus on getting new patients,
              or on keeping existing patients coming back, or both?"

Dr. Mehta: "Both, but mainly new patients right now. We just moved to a bigger clinic."

WaooaW Expert: "New space — exciting! How many new patients per month would make
              you feel this is working?"

Dr. Mehta: "20 would be great. We currently get about 8-10 from walk-ins."

WaooaW Expert: "Got it — double your current new patient flow. That's a clear target.
              One more question: who is your typical new patient? Working professional?
              Family? Students from the nearby colleges?"

Dr. Mehta: "Mostly working professionals 25-45. Near Magarpatta."
```

**Profile built (confirmed at 6 exchanges):**
```
business_domain: dental_clinic
owner_name: Dr. Priya Mehta (BDS, 8 years practice)
business_name: Mehta Dental Clinic
location: Viman Nagar, Pune (near Magarpatta IT Park)
target_customers: Working professionals 25-45, Magarpatta/Viman Nagar area
current_new_patients_month: 8-10
aspiration: +20 new patients/month
dental_focus: general dentistry, cosmetic, implants
DVE domain: dental_clinic → patient, appointment, etc.
```

---

## Day 1-2 — Skill 1: Maturity Score

**Research run in parallel (PRE_AUTHORIZED, no interaction needed):**

MCP calls:
```
google-places-mcp.place.get_details("Mehta Dental Clinic Viman Nagar Pune")
  → GBP claimed: YES
  → Last post: 2 months ago
  → Reviews: 23 total, avg 4.3 stars
  → Response rate: 30% (low)
  → Booking link: NOT SET

social-profile-mcp.profile.get_public_data("instagram: @mehtadental")
  → Account type: Personal (not Business) ← P0 gap
  → Followers: 234
  → Last post: 3 months ago
  → Engagement rate: 0.8% (below 2% baseline)

meta-ad-library-mcp.ads.search_active("Mehta Dental Viman Nagar")
  → No active ads
  
web-scan-mcp.tracking.check_pixels("mehta-dental.in")
  → Meta Pixel: NOT INSTALLED
  → Google Tag: NOT INSTALLED
  → GA4: NOT CONNECTED
```

**Maturity Score: 3/7 — Occasional Activity**

**Report delivered to Dr. Mehta:**
```
Dr. Mehta, here's your digital marketing picture:

SCORE: 3/7 — "Occasional Activity"
The average dental clinic in your city tier is 3.8. Top 20% are 5.5.

Your 3 most impactful gaps right now:
  1. Instagram is a Personal account (not Business) → you can't run ads or see analytics.
     Fix: 5 minutes to switch. I'll guide you.
  2. Your GBP has no booking link → patients who find you on Google can't book.
     Fix: Connect Practo/Calendly. 15 minutes.
  3. No Meta Pixel on your website → when patients visit, we can't retarget them.
     Fix: 3-line code snippet your web developer installs. Or I'll create the instructions.

What this means for your goal:
  At Score 3, you're getting 8-10 new patients via walk-ins and referrals.
  At Score 5, you'll be getting 20+ via digital channels.
  I can get you to Score 5 in 30 days. Let's start with the 3 gaps above.
```

---

## Day 2-3 — Skill 1b: Platform Account Setup

### A. Google Business Profile — MCP provisioning

**Credential collection (Type 1):**
```
WaooaW Expert: "Let's connect your Google Business Profile. I need 'manage' access
              to your GBP so I can post updates and respond to reviews.
              
              Steps (3 min):
              1. Go to business.google.com
              2. Select your clinic
              3. Users → Add → type: noreply@waooaw.ai
              4. Role: Manager
              5. Send
              
              I'll get the access within 2 minutes of you sending it."

Dr. Mehta: (grants access)

→ google-business-mcp provisioned (Container App spun up, customer_mcp_status = RUNNING)
→ CE.RecordEvidence(MCP_PROVISIONED, "google-business-mcp", C-074)
→ DR. MEHTA: "✓ Google Business Profile connected! I can now manage your GBP."
```

**Immediate GBP improvements made:**
```
gbp.update_description: "Multi-specialty dental clinic in Viman Nagar, Pune. 
  Root canal, implants, cosmetic dentistry, braces. 8+ years of trusted care.
  Near Magarpatta IT Park. Open Mon-Sat 10 AM – 8 PM. Book online."
  → Keywords injected: dentist viman nagar, dental clinic near magarpatta

gbp.set_booking_link("https://calendly.com/mehtadental") [after Practo setup]

gbp.seed_qa: 15 Q&A pairs seeded:
  "Do you handle dental emergencies?" → "Yes, call +91-XXXX. Same-day slots available."
  "How much is a root canal?" → "₹8,000 – ₹15,000 depending on tooth location."
  [... 13 more]
  
CE.RecordEvidence(GBP_UPDATED, constitutional_basis="C-023,C-073")
```

### B. Instagram Business Account — MCP provisioning

```
WaooaW Expert: "Your Instagram account is currently Personal — let's switch it to Business.
              This gives us analytics and the ability to run ads later.
              
              Settings → Account → Switch to Professional Account → Business → Dentist"

Dr. Mehta: (switches account)

→ instagram-mcp: OAuth flow initiated
  Dr. Mehta grants: Instagram content publish, read insights, manage comments
→ instagram-mcp provisioned (Container App)
→ First actions:
  instagram.update_bio: "Dr. Priya Mehta BDS | Viman Nagar, Pune | 
                         Root Canal ✓ Implants ✓ Cosmetic Dentistry ✓
                         📍 Near Magarpatta | 📞 Book: [link]"
  instagram.generate_highlight_covers: Services, Reviews, Team, FAQ (4 covers)
  → image-generation-mcp called for branded covers
```

### C. Ad Account Setup — Critical Gap Bridge

**Current state: FA-002 (Meta BM) PENDING**

```
WaooaW Expert: "For paid ads on Facebook and Instagram, our Meta Business Manager
              is being verified by Meta (standard 2-4 week process).
              
              While we wait, I'll do two things:
              1. Set up your Facebook Page access so we're ready to go the day verification completes
              2. Start all your organic campaigns now (Instagram posts, GBP updates, WhatsApp)
              
              The good news: you don't need to do anything for the ad setup.
              I'll send you a notification when we're ready to launch your first paid campaign."

[FA-002 pending notification auto-sent to Sujay via Steward Assistant:
 "Dr. Mehta (dental_clinic) wants paid ads. FA-002 still pending.
  Organic campaigns started. Paid campaigns on hold.
  Customer notified. ETA: 2-4 weeks (Meta's timeline)."]
```

**Meta Page Access (preparation while FA-002 pending):**
```
waooaw-ads-manager.mbm.generate_page_access_request:
  → Generates a Partner Request link for Dr. Mehta's Facebook Page
  → "Grant WAOOAW Advertise on Behalf Of access to your Facebook Page"
  → Dr. Mehta clicks → approves
  → Page access stored in meta-ads-mcp configuration
  → When FA-002 completes → campaigns launch immediately (no further action needed)
```

**Google Ads + LSA Setup (parallel, no Meta BM dependency):**
```
WaooaW Expert: "Good news — Google Ads doesn't need the same verification.
              I can launch Google campaigns this week.
              
              I'll create your Google Ads account under our Manager Account.
              You'll get read-only access to see your campaigns anytime.
              
              To track conversions (bookings from ads), I also need your website address
              to add Google Tag. Can your web developer add a 3-line code snippet?"

google-ads-mcp.mcc.create_client_account:
  customer_id: dr-mehta-uuid
  account_name: "Mehta Dental Clinic — Viman Nagar"
  currency: INR
  time_zone: "Asia/Kolkata"
  → client account created under WAOOAW MCC
  → CE.RecordEvidence(GOOGLE_ADS_ACCOUNT_CREATED, C-023, C-073)

google-ads-mcp.account.grant_read_access:
  → Dr. Mehta's Google account gets view access to her campaigns
  → She can see what's running without being able to change it

For LSA (Google Local Services Ads — pay per lead):
  → Agent provides step-by-step: submit dental license + PCPNDT certificate to Google
  → Once verified: LSA appears at top of "dentist near me" searches
  → Billing: Google charges per verified patient call/message (₹300-500/lead)
  → LSA uses separate Google account, not connected to regular Google Ads
  → Estimated setup: 7-14 days (Google's verification)
```

**Conversion Tracking — Critical for attribution (GA4 gap noted):**
```
WaooaW Expert: "To know which posts and ads are actually bringing patients to your
              website, I need Google Analytics and Meta Pixel on your site.
              
              Your web developer needs to add these two snippets (< 5 min):
              
              1. META PIXEL:
              [code snippet auto-generated by meta-ads-mcp]
              
              2. GOOGLE TAG:
              [code snippet auto-generated by google-ads-mcp]
              
              3. GOOGLE ANALYTICS 4:
              [GA4 setup instructions — note: requires FA-021 for WAOOAW to READ the data]
              
              Even if you can't install now, I'll track everything I can via direct
              Instagram and GBP metrics. Attribution improves once these are installed."

[NOTE: GA4 data reading requires FA-021 (GCP credentials) — gap logged in customer_mcp_status]
```

### D. Ad Spend Wallet Creation

```
WaooaW Expert: "To run paid ads, you'll fund an Ad Spend Wallet.
              You decide how much to put in (minimum ₹2,000/month for Meta to optimize).
              I recommend ₹5,000/month to start — enough to test 2 campaigns.
              
              Your billing has two parts:
              Part 1: ₹2,499/month subscription (platform + content management)
              Part 2: Ad spend + 10% management fee (only what you actually spend)
              
              Example if you spend ₹5,000 on ads:
              Meta ad spend:        ₹3,500
              Google ad spend:      ₹1,500
              Management fee (10%): ₹   500
              Sub-total:            ₹5,500
              GST (18%):            ₹   990
              Total Invoice 2:      ₹6,490
              
              The 10% management fee is the industry standard for ad management.
              You can see every rupee spent on every campaign in your dashboard.
              Shall I set up your wallet with ₹5,000?"
```

**Razorpay flow:**
```
razorpay-mcp.wallet.create:
  customer_id: dr-mehta-uuid
  initial_topup: ₹5,000 (customer-entered amount)
  
→ Razorpay payment link generated → sent to Dr. Mehta via WhatsApp
→ Dr. Mehta pays via UPI
→ razorpay-mcp.webhook.payment_captured → wallet credited
→ CE.RecordEvidence(AD_SPEND_WALLET_FUNDED, amount=5000, constitutional_basis="C-056,C-038,C-023")
→ Invoice 1 (subscription): immediately generated via pdf-generation-mcp
→ Invoice 2 (ad spend): generated monthly after campaign run
```

---

## Day 3-5 — Skill 2: Campaign Strategy

```
Campaign Brief (agent proposes, Dr. Mehta approves):

  master_theme:    "Pain-Free Dentistry for Busy Professionals"
  target_outcome:  "+20 new patient appointments in Month 1"
  target_audience: Working professionals 25-45, Viman Nagar/Magarpatta
  platform_mix:    [INSTAGRAM, GOOGLE_BUSINESS, WHATSAPP, GOOGLE_ADS (paid)]
  content_cadence: Instagram: 3 posts/week + 5 stories; GBP: 2 posts/week
  paid_campaigns:  Google Search (pending LSA setup) + Meta (pending FA-002)
  
  Week 1: "We moved to a bigger space" — launch announcement
  Week 2: "Pain-free treatment" — anxiety relief hook
  Week 3: "Meet Dr. Mehta" — humanizing
  Week 4: "First-visit offer" — conversion CTA
  
Dr. Mehta: "Looks great. Go ahead."
CE.RecordEvidence(CAMPAIGN_BRIEF_APPROVED, campaign_id=..., constitutional_basis="C-055,C-023")
```

---

## Weeks 1-4 — Campaign Execution

### Content Publishing (Skill 4 — Instagram)

**Week 1, Day 1 — First Reel:**
```
Brief: "New Clinic Launch — Pain-Free Dentistry"
Hook: "We upgraded our clinic so you never dread the dentist again 🦷"

Execution flow:
1. video-generation-mcp.video.generate_from_brief → 30s Reel (Track 3 generative)
2. SCR runs: domain compliance check → dental_clinic → MCI rules applied ✓
   No clinical claims. No before/after. Compliant ✓
3. Dr. Mehta preview via WhatsApp: "Here's your first Reel. Does it sound like you?"
4. Dr. Mehta: "Yes! Love it."
5. CE.RecordEvidence(CONTENT_APPROVED, reel_id=...) → C-023 BEFORE publish
6. instagram-mcp.reel.publish → posted
7. scheduling-mcp.calendar.schedule_post → future posts queued

Evidence chain:
  CONTENT_BRIEF_CREATED → BRIEF_QUALITY_REVIEWED → CUSTOMER_APPROVED →
  CE_VALIDATION_AUTHORIZED (C-041) → CONTENT_PUBLISHED
```

### GBP Management (Skill 6)

```
Week 1: First GBP "What's New" post
  "Mehta Dental Clinic has a new home in Viman Nagar! Bigger space, same trusted care.
   Book your appointment: [calendly link]"
  → google-business-mcp.post.create_update → published

Week 2: New patient review detected (4 stars, "Good dentist")
  → google-business-mcp.review.list_unreplied → 1 unread
  → DVE resolved review response template: 
    "Thank you for visiting us! We're glad you had a positive experience. 
     Looking forward to seeing you again. 🙏 — Dr. Mehta's Team"
  → APPROVAL_GATE: "Here's my suggested response. Send?"
  → Dr. Mehta: "Yes"
  → google-business-mcp.review.respond → published
  → CE.RecordEvidence(REVIEW_RESPONDED, constitutional_basis="C-023")
```

### Paid Advertising (Skill 11 — starts Week 3 when Google Ads live)

```
Google Search Campaign — Live (no FA-002 dependency):
  Campaign type: Performance Max
  Asset group:
    Headlines: "Trusted Dentist in Viman Nagar" / "Pain-Free Root Canal in Pune" / ...
    Descriptions: "Near Magarpatta IT Park. Book today." / ...
    Images: from content_assets library (Instagram posts repurposed)
  Budget: ₹2,500/month (of the ₹5,000 wallet — split: ₹2,500 Google + ₹2,500 Meta later)
  
Week 3 — First campaign debit:
  google-ads-mcp.campaign.get_report: ₹450 spent, 3 patient calls attributed
  razorpay-mcp.wallet.debit: ₹450 + ₹45 management fee = ₹495
  → CE.ValidateAction: C-043 check (₹5,000 ceiling, ₹495 debit → authorized)
  → CE.RecordEvidence(AD_SPEND_CHARGED, amount=495, constitutional_basis="C-056,C-043,C-023")

Ad Account Health Monitoring (GAP BRIDGED — new in this session):
  Platform Operations health probe (every 5 min):
    meta-ads-mcp.account.get_status → account_standing: ACTIVE ✓
    google-ads-mcp.account.get_status → account_standing: ACTIVE ✓
  → No issues. Dr. Mehta sees nothing (clean operation).
```

---

## Month 1 — Results and Evidence

**Skill 9 — Monthly Report (auto-generated, white-label PDF):**

```
MEHTA DENTAL CLINIC — Digital Marketing Report — July 2026
Prepared by: WAOOAW Digital Marketing Professional

HEADLINE RESULT: 14 new patient enquiries attributed to digital channels

Instagram: 28 posts published | 3,400 reach | 89 profile visits | 12 WhatsApp clicks
GBP: 2,100 views | 34 calls | 8 direction requests | 5 new reviews (avg 4.6 stars)
Google Ads (PMax): ₹1,850 spent | 11 patient calls | ₹168 CPL
Meta Ads: NOT LIVE (Meta BM verification in progress — ETA 2-3 weeks)

REVIEW PROGRESS: 23 → 28 total reviews (+5). All 5 responded within 24h.

NEXT MONTH PLAN:
  - Meta paid campaigns launch (once BM verified)
  - Increase to 4 posts/week on Instagram (engagement trend positive)
  - Launch GBP photo campaign (currently 8 photos — target: 20)
  
CONSTITUTIONAL COMPLIANCE: 0 violations. All actions evidence-backed.
```

---

## Month 1-3 — Trust Building and Lifecycle

**Skill 16 — Customer Lifecycle (DVE: dental_clinic):**

```
Patient "Anita" books via Google Ads call → appointment confirmed via Practo booking-mcp
→ 24h later: TOUCH 1
  "How are you feeling after your cleaning, Anita ji? Any discomfort? 🙏"
  Anita: "Great! Very professional."
  → TOUCH 2 triggered:
  "Glad to hear it! A quick Google review helps other patients find us: [link]"
  Anita leaves 5-star review → GBP rating: 4.3 → 4.5

At Day 60: TOUCH 4 (6-month checkup reminder) set for Month 7.
```

**Trust Ledger (end of Month 3):**
```
sessions_completed: 47 (47 distinct patient-facing interactions)
c048_violations: 0
c049_escalations: 2 (both honest — "Meta pixel not installed, can't track website conversions")
grade_a_simulations: 3 (monthly simulation runs all Grade A)
customer_satisfaction_signals: 8 (positive patient responses + review milestone)
computed_trust_score: 0.91
authorized_autonomy_tier: 1 → READY FOR TIER 0 at Month 4 (30 sessions, trust ≥ 0.90)
```

---

## Month 3 — Quarterly Review (Skill 21)

```
Q1 SCORECARD:
  Target: +20 new patients/month → Achieved: +14 Month 1, +17 Month 2, +21 Month 3 ✅
  Target: 4.5+ GBP rating → Achieved: 4.7 ✅
  Meta Ads: LAUNCHED Month 2 (FA-002 verified) → 8 leads in first month at ₹290 CPL

Q2 PLAN PROPOSED:
  Campaign theme: "Back to School Dental Health" (Aug-Sep)
  Ad budget: ₹7,000/month (increase from ₹5,000 — proven 4.1x ROAS)
  New: Instagram Collab with "Pune Dental Professionals" association
  New: Launch Skill 14 (Reputation Management) — Practo reviews need attention (3.9 rating)

Dr. Mehta: "Approved! This is better than I expected in 3 months."
```

**SIMULATION GRADE: A ✓**
All constitutional instincts verified. 0 violations. Trust score 0.91. ₹168 CPL Month 1 → ₹97 CPL Month 3 (learning curve).
