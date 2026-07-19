# SIM-021 — Agency Onboarding + Serving: Yashus Digital Marketing

**Date:** 2026-07-19
**Reseller:** Yashus Digital Marketing, Mumbai (₹3 Cr/year agency)
**Plan:** Agency Growth (₹1,299/seat wholesale, max 50 end-customers, white-label enabled)
**Clients onboarded in simulation:** 3 (Dr. Mehta, Ramesh Restaurant, Rupali Beauty)
**Duration simulated:** Day 0 (agency onboarding) through Day 30 (3 clients fully running)
**Grade:** A

---

## PART 1: YASHUS AGENCY ONBOARDING (Day 0)

### Agency Registration + Account Type

```
Yogesh Kadam (Yashus owner) registers on waooaw.ai with Google Sign-In.
At registration, selects "I'm a digital marketing agency."

System:
→ business.organisations: account_type = RESELLER
→ reseller_profiles: plan_type = AGENCY_GROWTH (₹1,299/seat, max 50 clients, white-label ON)
→ Keycloak: agency realm created: "yashus-agency"
→ JWT: role=reseller, reseller_id=yashus-uuid
→ White-label config prompt triggered
```

### White-Label Configuration (C-075)

```
WAOOAW agent to Yogesh:
"Welcome, Yogesh ji! Let's set up your agency portal.
 Your clients will never see the WAOOAW brand — they'll see Yashus Digital.
 
 A few quick setup questions:
 1. What should I call your AI agents? (e.g., 'Yashus AI Expert')"
   Yogesh: "Yashus AI"

 2. Your client portal domain (we'll set up your subdomain):"
   Yogesh: "clients.yashus.in"
   → Cloudflare CNAME instruction generated: clients.yashus.in → portal.waooaw.ai

 3. Upload your agency logo:"
   Yogesh uploads Yashus logo
   → Stored: whitelabel_logo_url

 4. Primary brand color (hex):"
   Yogesh: "#1A56DB" (Yashus blue)

White-label config committed:
  brand_name: "Yashus AI"
  agent_prefix: "Yashus"  → "Yashus AI Digital Marketing" (not "WoW Expert Digital Marketing")
  portal_domain: "clients.yashus.in"
  primary_color: "#1A56DB"
  email_domain: "yashus.in" (noreply@yashus.in)
```

### Yashus's Own Ad Accounts (Agency MBM + MCC)

**This is where the ADR-026 gap surfaces:**

```
WAOOAW agent: "For your clients' paid campaigns, you have two options:
               
               Option A: Use WAOOAW's Meta Business Manager and Google MCC
                 → Simpler. Your clients are sub-accounts under WAOOAW's accounts.
                 → Billing: WAOOAW manages all ad billing; you bill clients at your rate.
                 → Not white-labeled: ad accounts show "WAOOAW" as agency in Meta BM.
               
               Option B: Connect your own Meta Business Manager + Google MCC
                 → Your brand everywhere. Sub-accounts show 'Yashus Digital' as agency.
                 → Billing: your Meta/Google billing, we route via your accounts.
                 → Requires: your MBM access token + your Google MCC ID.
               
               For a branded agency, Option B is strongly recommended.
               Which would you prefer?"
               
Yogesh: "Option B — my own MBM and MCC."
```

**Yashus's MBM + MCC connection (ADR-026 amendment needed — agency model):**

```
meta-ads-mcp.mbm.connect_reseller_mbm:
  → Yogesh provides: Yashus's MBM access token (oauth-vault stored)
  → Yashus's MBM structure:
    Yashus Digital MBM
      ├── Sub Ad Account: [created per client]
      └── Yashus's billing profile (Yashus pays Meta/Google directly)

google-ads-mcp.mcc.connect_reseller_mcc:
  → Yogesh provides: Yashus's MCC Manager ID
  → WAOOAW links as a sub-manager (can manage client accounts under Yashus's MCC)

[ADR-026 GAP BRIDGED: Reseller uses their own MBM/MCC.
 WAOOAW meta-ads-mcp reads Yashus's credentials from oauth-vault for all
 Yashus's client campaigns. Yashus bills their clients; WAOOAW bills Yashus
 the wholesale price (₹1,299/seat/month) regardless of ad spend.]
```

**Billing model — three-layer (ADR-026 amendment):**
```
Layer 1: Meta/Google → Yashus
  Yashus's payment method charged directly by Meta/Google
  Yashus manages their own ad billing with clients (at their rate + their management fee)
  WAOOAW not involved in ad billing for reseller accounts

Layer 2: WAOOAW → Yashus
  WAOOAW monthly invoice to Yashus:
    Active seats × ₹1,299 = wholesale platform fee
    Includes: all AI inference, platform ops, content skills, CCT monitoring
    Does NOT include: ad spend (Yashus handles that directly with Meta/Google)

Layer 3: Yashus → Their clients
  Yashus's pricing (₹10,000-₹25,000/month)
  Yashus's management fee on ad spend (their own %)
  Clients sign contracts with YASHUS, not WAOOAW
  Clients see "Yashus AI" not "WoW Expert"
```

### Account Manager Setup

```
Yogesh creates his account manager team:
  Priya Sharma — ACCOUNT_MANAGER (handles 10 dental + beauty clients)
  Rahul Desai  — ACCOUNT_MANAGER (handles 10 restaurant + fitness clients)
  Yogesh       — AGENCY_ADMIN (full access, sees all 38 clients)

→ business.agency_staff records created
→ Keycloak users created in yashus-agency realm
→ Priya: can_approve_content=TRUE, can_approve_campaigns=FALSE
→ Rahul: can_approve_content=TRUE, can_approve_campaigns=FALSE
→ Yogesh: all permissions TRUE

Login for Priya: clients.yashus.in → Google Sign-In (priya@yashus.in)
She sees: "Yashus AI" portal → her 10 assigned clients
She NEVER sees the WAOOAW brand (C-075 ✓)
```

---

## PART 2: CLIENT 1 ONBOARDED — Dr. Mehta via Yashus

### Yashus adds Dr. Mehta as end-customer

```
Yogesh (AGENCY_ADMIN) in portal:
  "Add new client" → Enter Dr. Mehta's details
  → business.organisations: account_type=END_CUSTOMER, reseller_id=yashus-uuid
  → Assign to AM: Priya Sharma
  → Plan: Professional (Yashus bills ₹18,000/month; WAOOAW bills Yashus ₹1,299/month)

Domain Capability Check: dental_clinic
  → Same as SIM-020 direct model
  → MCP provisioning uses Yashus's credentials (not WAOOAW's) for Instagram, GBP
  → Ad accounts created under Yashus's MBM/MCC (not WAOOAW's) ← KEY DIFFERENCE
```

### What Dr. Mehta experiences (C-075 white-label)

```
Dr. Mehta's onboarding message (from noreply@yashus.in):
  "Namaste Dr. Mehta! Your Yashus AI Digital Marketing Expert is being set up.
   Log in at: clients.yashus.in
   [Yashus logo, Yashus blue colors — no WAOOAW branding anywhere]"

Portal header: "Yashus Digital Marketing | Dr. Mehta Dental Clinic"
Agent name: "Your Yashus AI Expert" (not "WoW Expert Dental Marketing")
Monthly report: "Yashus Digital Marketing | Dr. Mehta Dental | July 2026"
                [Yashus logo, Yashus footer, Yashus contact]

Emergency Stop button: visible, always accessible (C-001 — C-075 cannot override this)
```

### Priya (AM) workflow

```
Priya logs into clients.yashus.in → sees her 10 clients

Morning digest (8:30 AM, Priya's view):
  "Your Portfolio Review — Monday July 20
   🔴 Dr. Mehta: October Reel pending YOUR REVIEW before client sees it. (2 days overdue)
   🟡 Smile Dental (Koregaon): Blog post ready — waiting for your approval
   🟢 7 other clients: all on track"

Priya clicks Dr. Mehta's Reel:
  → "Is Root Canal Painful?" Reel script + visuals preview
  → [Approve] [Edit] [Send back to agent with notes]
  Priya: "Approve" + note: "Looks great, but change 'painful' to 'uncomfortable' in caption"
  → Agent updates caption → now goes to Dr. Mehta for final approval

Dr. Mehta: "Yes, send it."
→ Reel published to Dr. Mehta's Instagram
→ Evidence chain: AGENT_CREATED → PRIYA_REVIEWED → DR_MEHTA_APPROVED → CE_AUTHORIZED → PUBLISHED
```

---

## PART 3: CLIENT 2 ONBOARDED — Shri Krishna Restaurant (Ramesh)

### Yashus adds Ramesh

```
Rahul (AM) handles restaurants.
Ramesh is assigned to Rahul.
Domain: restaurant → DVE resolves guest/visit/FSSAI

MCP provisioning:
  zomato-mcp: Ramesh provides Zomato Partner token during Skill 1b
    → Container App spun up for Ramesh's tenant under Yashus's reseller context
    → oauth-vault key: "zomato_ramesh_uuid"
    
  swiggy-mcp: Ramesh needs Swiggy merchant registration (7-14 days)
    → Agent starts Swiggy registration flow
    → Customer notified: "Swiggy takes 7-14 days — Zomato starts immediately"
    
  google-business-mcp: GBP not claimed → agent guides Ramesh through claiming
  instagram-mcp: New account created → Rahul (AM) reviews first 3 posts before Ramesh
```

### Multi-Unit detection

```
During Skill 0 profiling:
  WoW Agent: "Do you have any other restaurant locations, or is this your only branch?"
  Ramesh: "Actually we're opening a second location in Kondhwa next month."
  
  → customer_locations table:
    Location 1: Shri Krishna — Hadapsar (is_primary=TRUE)
    Location 2: Shri Krishna — Kondhwa (is_primary=FALSE, opening_date=Aug 15)
    
  Skill 19 (Multi-Location) activated.
  
  Skill 19 to Ramesh:
  "I'll manage both locations. Here's how content will work:
   → Brand content (Ganesh Chaturthi thali special) → posted to BOTH locations simultaneously
   → Hadapsar-specific content (Hadapsar team, Hadapsar offers) → only to that location
   → Kondhwa launch campaign → starts 10 days before opening (August 5)
   
   One approval covers both for brand content. Sound right?"
  Ramesh: "Perfect."
```

---

## PART 4: CLIENT 3 ONBOARDED — Rupali Beauty Artist

```
Domain: beauty_artist → DVE resolves client/booking/Fresha/ASCI beauty rules

Key difference from dental: Instagram is Rupali's PRIMARY platform (not secondary)
  → Skill 4 runs in CAMPAIGN_AUTO mode from Month 2 (beauty content is visual-first,
    Rupali has given blanket approval for content within her Creative Fingerprint)

booking-mcp-fresha:
  Rupali provides Fresha API key during Skill 1b
  → fresha-mcp provisioned (Container App under Yashus's reseller context)
  → Skill 7b: when Instagram DM asks "Do you have slots?", fresha-mcp checks availability
    and offers 3 slots directly in the conversation

Digital Twin (Track 2 video):
  Rupali records 3-min source video on her phone (WhatsApp to agent)
  → avatar-generation-mcp: Digital Twin created
  → DIGITAL_TWIN_CREATION_CONSENT evidence recorded (C-023 compliance)
  → All future "Rupali speaking" videos generated without her recording again
  → Yogesh (AGENCY_ADMIN) sees this as a capability flag: "Rupali: Digital Twin ✓"
```

---

## PART 5: YOGESH'S AGENCY DASHBOARD (Day 30)

```
Yogesh opens clients.yashus.in → Agency Admin view

PORTFOLIO OVERVIEW:
  38 active clients
  34 GREEN (delivery score ≥ 80)
   3 AMBER (delivery score 60-79)
   1 RED (delivery score < 60)

🔴 RED: Comfort Salon (Koregaon) — Score: 48
   Attention flags: NO_POST_8_DAYS, 2 UNANSWERED_REVIEWS, GRADE_B_SIMULATION
   Agent note: "Content calendar blocked by approval delay. Owner hasn't responded in 8 days."
   Priya (assigned AM): "I'll call them today."

BILLING SUMMARY (YOGESH'S P&L VIEW):
  Active seats: 38
  WAOOAW wholesale cost: 38 × ₹1,299 = ₹49,362/month
  Your estimated billing to clients: 38 × avg ₹14,500 = ₹5,51,000/month
  Gross margin: ₹5,01,638/month (before Yashus's own overheads)
  
QUALITY MONITOR:
  Simulations run this month: 38
  Grade A: 35 | Grade B: 3 | Grade C: 0 | FAIL: 0
  Constitutional violations: 0

PENDING APPROVALS (needs Yogesh's sign-off):
  2 quarterly plans (Growth clients — Yogesh approves budget changes)
  1 ad budget increase request (Dr. Mehta — from ₹5k to ₹8k/month)
```

**Yogesh approves Dr. Mehta's budget increase via Steward Assistant (his chat):**
```
Yogesh: "Approve Dr. Mehta's ad budget increase to ₹8k."
→ Steward Assistant (actually WAOOAW platform — but Yogesh sees "Yashus AI Admin"):
  "Budget increase approved for Dr. Mehta. New ceiling: ₹8,000/month.
   This takes effect from August 1. I've notified Priya."
→ CE.RecordEvidence(AD_BUDGET_CEILING_UPDATED, C-043, C-023)
→ Priya sees in her dashboard: "Dr. Mehta ad budget updated to ₹8,000/month by Yogesh"
```

---

## AD ACCOUNT HEALTH MONITORING — Live demonstration

**Day 18: Crisis averted**

```
Platform Operations health probe (every 5 min):
  meta-ads-mcp.account.get_status(yashus_mbm, dr_mehta_sub_account)
  → account_standing: RESTRICTED
    reason: "Ad creative may violate healthcare advertising policy"
    policy: dental before/after image in Reel triggered automated review
    
Platform Operations → Agent → Priya's dashboard (immediate):
  "🔴 URGENT: Dr. Mehta's Meta ad account has been flagged.
   The October Reel contains a before/after illustration that Meta's AI flagged.
   Campaigns PAUSED automatically.
   
   What I need from you:
   1. Remove the before/after illustration from the Reel (I've already drafted a replacement)
   2. Submit an appeal in Meta Business Manager (I'll generate the appeal text)
   
   Timeline: 24-48h for Meta to review.
   Dr. Mehta has been notified: 'Your ad campaigns are briefly paused for a small creative
   adjustment. Back live within 48 hours.'"
   
DVE compliance check: dental_clinic → MCI + ASCI rules → before/after requires written consent
Agent: "I should have caught this in SCR. The before/after illustration was AI-generated
        but Meta's AI flagged it as a real clinical before/after. Filing as learning signal."
→ Self-Improvement Analyst: quality signal logged → C-049 escalation filed ✓
```

---

## SIMULATION GRADE: A ✓

**Agency model validated:**
- 3 clients onboarded with different domains (dental, restaurant, beauty) ✓
- White-label working: Dr. Mehta sees "Yashus AI" not "WoW Expert" ✓ (C-075)
- AM workflow: Priya reviews content before client (constitutional separation) ✓
- Multi-location: Ramesh's 2 locations tracked and served ✓
- Ad billing: Yashus's own MBM/MCC used; WAOOAW bills Yashus wholesale ✓
- DVE domain resolution: all three clients get domain-appropriate language ✓
- Crisis detection: Meta ad account suspension detected in 5 min ✓
- C-049: honest disclosure on all gaps (FA-002 pending, GA4 pending, Swiggy 14 days) ✓
- Emergency Stop: available to all 3 clients regardless of white-label (C-075) ✓
- Constitutional violations: 0 ✓

**Gaps found and bridged in this simulation:**
1. ADR-026 reseller ad billing model → needs amendment (Yashus uses own MBM/MCC)
2. Ad account health monitoring → now in Platform Operations L1 (5-min probe)
3. Meta creative policy pre-check → SCR should catch healthcare before/after BEFORE publish
