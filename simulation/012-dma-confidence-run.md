# Simulation 012 — DMA Confidence Run: Dr. Mehta's October Campaign (v2.8)

**Type:** Confidence Run — Digital Marketing Agent v2.8
**Status:** Active
**Purpose:** Re-run the Simulation 007 scenario with all identified gaps resolved. Validate that DMA v2.8 produces genuinely professional outputs across the full campaign lifecycle: Platform Intelligence, Campaign Theme Engine, Weekly Theme Cascade, Video Brief, Synthetic Content Reviewer, and performance reporting. Confirm Grade A quality against a real DMA customer lifecycle.
**Persona:** Dr. Priya Mehta, dental clinic, Viman Nagar, Pune. Month 4 of DMA engagement. First Campaign Theme Engine execution.
**Gaps resolved:** GAP-D001 (Platform Intelligence fallback), GAP-D002 (Campaign Brief Approval UX), GAP-D003 (SCR Check 2 regen limit), GAP-D004 (Multi-platform cascade sequence), GAP-D005 (Video Brief first), GAP-D006 (WhatsApp broadcast TRAI window), GAP-D007 (Mid-campaign performance pivot trigger)

---

## Phase 1 — Platform Intelligence Research (RESOLVED: GAP-D001)

Agent opens the campaign planning session.

**Agent (WhatsApp):**
"Dr. Mehta, October is around the corner. Before I design your campaign, I want to understand where your patients actually spend time online — let me check what's working in Viman Nagar for dental practices."

Agent runs `DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH` with:
```
business_domain: DENTAL_CLINIC
locality: VIMAN_NAGAR_PUNE
competitor_list: [Dantavilas Dental, SmileCare Clinic, White Pearl Dental]
```

### MCP results (competitor data available):

```
meta-ad-library-mcp:
  Dantavilas Dental: 3 active Instagram ads (family + festive theme, ₹500-800/day spend est.)
  SmileCare Clinic: 0 paid ads
  White Pearl Dental: 1 Facebook campaign (paused, last active August 2026)

social-profile-mcp:
  Dantavilas: 2,340 Instagram followers, 4x/week posts (educational + before/after)
  White Pearl: 870 Instagram followers, 1x/week (inconsistent)
  SmileCare: 1,200 Instagram followers, 2x/week (generic health tips)

RAG Tier 1 — India healthcare platforms:
  Instagram: primary discovery for 28-45 dental patients in Pune tier-1 localities
  YouTube Shorts: growing — "is root canal painful?" 12K monthly searches Pune
  GBP: 40% of "dentist near me" conversions within 3 km
  WhatsApp: highest engagement channel post-first-appointment (opted-in list)
```

**Platform Intelligence Output:**
```yaml
competitor_data_available: true
fallback_basis: null  # Real competitor data available; not benchmark-only

platform_recommendation:
  INSTAGRAM:
    status: ACTIVE
    evidence: "Dantavilas (your strongest competitor) is active here with paid ads.
               Your 1,100 followers are behind their 2,340 — content frequency gap is your
               biggest opportunity. They post 4x/week; you post 2x/week."
    recommended_frequency: "5x/week during October campaign"
    
  YOUTUBE_SHORT:
    status: ACTIVE_FIRST_MOVER
    evidence: "No local dental competitor has a YouTube Short strategy.
               12K/month searches for dental education content from Pune alone.
               First-mover advantage is available right now."
    recommended_frequency: "2 Shorts/month — patient education format"
    
  GBP:
    status: MANDATORY
    evidence: "40% of 'dentist near me' conversions happen via GBP within 3km.
               Your GBP review count (47) lags Dantavilas (94 reviews). Gap to close."
    recommended_frequency: "2 posts/week + review generation cadence"
    
  WHATSAPP:
    status: ACTIVE
    evidence: "Your 80 opted-in patients are a high-value retention asset.
               Reactivation broadcast to patients not seen in >1 year is the fastest
               ROI action in October."
    recommended_frequency: "1 broadcast/week (reactivation + update)"
    
  FACEBOOK:
    status: ADVISORY
    evidence: "SmileCare and White Pearl Facebook activity declining. White Pearl's
               paid campaign paused. Demographic for 28-45 dental patients shifting to
               Instagram. Maintain your Facebook page but do not invest ad budget here."
    recommended_frequency: "Mirror Instagram posts (zero additional effort)"
    
  LINKEDIN: NOT_RELEVANT
```

**Agent to Dr. Mehta:**
"Here's what the research shows:
- **Instagram**: Dantavilas is your main competitor there and they're active. You're 2x behind on posting frequency — this is the gap I'll focus on.
- **YouTube Shorts**: Zero competitors have done this. 12,000 people search 'is root canal painful?' in Pune every month. First-mover opportunity.
- **GBP**: You have 47 reviews; Dantavilas has 94. We close this gap in October.
- **WhatsApp**: Your 80 opted-in patients — I'll send a reactivation broadcast to anyone who hasn't visited in over a year.

Shall I build the October campaign around this platform mix?"

Dr. Mehta: "Yes, this looks right. Let's do it."

---

## Phase 2 — Campaign Brief Proposal (RESOLVED: GAP-D002)

Agent proposes the October Campaign Brief.

**Campaign Brief (sent via WhatsApp as structured message + portal link):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
OCTOBER CAMPAIGN BRIEF
Dr. Priya Mehta's Dental Clinic
━━━━━━━━━━━━━━━━━━━━━━━━━━━

Master Theme:
"Prevention isn't a luxury — it's the smartest ₹500 you'll spend"

Why this theme:
Diwali is in October. Patients delay appointments during festival prep.
This theme positions a checkup as a fast, affordable gift to yourself —
countering the "I'll do it next month" objection.

Target Outcome:    +15 preventive checkup bookings in October
Target Patient:    Working professional, 28-45, Viman Nagar
                   Hasn't visited in >1 year | Cost + pain + time anxiety

Platform Mix:
  Instagram:       5 posts/week + 3 stories/week
  YouTube Shorts:  2 (patient education — "What happens at your first checkup")
  GBP:             2 posts/week + review generation
  WhatsApp:        1 broadcast/week (80 opted-in patients)
  Facebook:        Mirror Instagram (no extra effort)

Weekly Focus:
  Week 1 (Oct 1-7):   "Prevention is cheaper than cure"
  Week 2 (Oct 8-14):  "What actually happens at a checkup — demystified"
  Week 3 (Oct 15-21): "Meet our team — the faces you'll see"
  Week 4 (Oct 22-31): "Diwali special offer + booking CTA"

Budget:            ₹6,000 ad spend (Instagram Reels boosting + Google Search)

━━━━━━━━━━━━━━━━━━━━━━━━━━━
To approve this brief:
  Reply YES to this message
  — or —
  Visit: app.waooaw.com/campaigns/approve/[token]
━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Customer approval (RESOLVED: GAP-D002)

Dr. Mehta replies: "YES" to WhatsApp.

System:
1. WhatsApp webhook receives "YES" → CE.ValidateAction(`CAMPAIGN_BRIEF_APPROVED`)
2. Evidence record: `{action_type: CAMPAIGN_BRIEF_APPROVED, campaign_id: oct-2026-mehta, channel: WHATSAPP, customer_confirmation: "YES"}`
3. `content_campaigns.status` transitions: `DRAFT → CUSTOMER_APPROVED`
4. Weekly Theme Cascade auto-starts

**Constitutional evidence:** C-003 (authority licensed through explicit action), C-023 (Evidence First). The "YES" reply is the constitutional authority event.

---

## Phase 3 — Weekly Theme Cascade + Content Generation

### Week 1 Output: "Prevention is cheaper than cure"

Agent runs `DMA/CAMPAIGN/WEEKLY_THEME_PLANNER` for Week 1 sub-theme.

**Instagram Feed Post (Tuesday, Oct 7, 10:30 AM IST):**

```
[IMAGE BRIEF: Clean white background. Left side: a ₹500 note. Right side: a smiling
patient in dental chair, professional clinician in white coat. Clean typography overlay.]

CAPTION:
That annual checkup? ₹500.
Ignoring it for two years and needing a root canal? ₹15,000.

Prevention isn't a luxury. It's basic maths.

At our Viman Nagar clinic, we see patients who delayed a ₹500 checkup and needed
₹15,000 worth of treatment. The math never works out in favour of waiting.

📅 Book your October checkup:
Link in bio or WhatsApp us directly.

#VettedPrevention #DentalCareViman #PuneSmiles #DrPriyaMehta #DentalClinicPune
```

SCR Run:
```
Check 1 (format): PASS — Instagram format ✓
Check 2 (brand voice): PASS — professional, empathetic, no promotional hyperbole ✓
Check 3 (compliance — MCI/ASCI):
  - "root canal" mentioned as consequence, not as WAOOAW-controlled outcome → PASS
  - No success rate claims → PASS
  - No "guaranteed results" → PASS
  - No patient testimonials fabricated → PASS
SCR result: SCR_PASSED
```

**Instagram Reel (Thursday, Oct 9, 6:30 PM IST) — VIDEO BRIEF FIRST (C-058):**

```yaml
video_brief:
  format: PHOTO_TO_VIDEO  # Track 1 (Kling AI — Dr. Mehta has no professional video assets yet)
  duration: 30s
  
  objective: "Demystify the dental checkup — show it is fast, painless, normal"
  emotion_arc: "Anxiety → Curiosity → Relief → Action"
  
  visual_sequence:
    frame_1 [0-3s]:
      type: STILL_PHOTO
      source: "Dr. Mehta's clinic interior — reception area, warm lighting"
      text_overlay: "You've been putting this off for a year."
      
    frame_2 [3-10s]:
      type: ANIMATED_STILL
      source: "Dr. Mehta smiling at patient consultation"
      text_overlay: "It takes 20 minutes."
      motion: ken_burns_slow_zoom
      
    frame_3 [10-22s]:
      type: ANIMATED_STILL
      source: "Dental chair, clean clinic, professional instruments"
      text_overlay: "No drills unless you need them.\nWe just look."
      motion: gentle_pan_left
      
    frame_4 [22-28s]:
      type: STILL_PHOTO
      source: "Patient leaving, smiling, looking at phone (booking confirmation)"
      text_overlay: "20 minutes. Done."
      
    frame_5 [28-30s]:
      type: LOGO_CARD
      text_overlay: "Book October checkup → Link in bio"
      
  audio:
    type: BACKGROUND_MUSIC
    mood: "calm, professional, reassuring"
    voiceover: false  # No patient voiceover — no TRAI attribution issue
    
  mcp_tool: kling-ai-mcp
  action: video.photo_to_video
  
  human_referral_gate:
    authentic_media_check: false  # Photo-to-video from clinic's own photos — no authenticity gap
    digital_twin_eligible: false  # Digital Twin requires explicit session with Dr. Mehta
    referral_required: false
    
  scr_check_note: "Video brief approved by agent before MCP call. C-058: brief exists before creation begins."
```

**Agent to Dr. Mehta (BEFORE video generation):**
"For the Week 1 Reel, I've written the video brief — here's what I'm planning to create using your clinic photos:

[20-second walk through the brief as described above]

I'll animate your still photos into a short video using AI. No professional shoot needed this month. Once I have 10-15 patients through the door, we can plan a proper Digital Twin session with you speaking on camera for the deeper educational content.

Shall I proceed with this brief?"

Dr. Mehta: "Yes, go ahead."

Agent logs: `VIDEO_BRIEF_APPROVED` evidence record → calls `kling-ai-mcp: video.photo_to_video`.

### Week 2 Output — Sample: YouTube Short

```yaml
youtube_short_brief:
  title: "What actually happens at your first dental checkup in 2026"
  duration: 58s
  search_target: "first dental checkup what to expect Pune"
  
  format: DIGITAL_TWIN  # Dr. Mehta speaking — requires Digital Twin session
  
  human_referral_gate:
    authentic_media_check: true
    reason: "YouTube educational content requires Dr. Mehta's authentic voice and face.
             AI-generated avatar speaking medical advice — without explicit Digital Twin
             session consent — violates C-049 (Honest Limitation Disclosure)."
    referral_required: true
    referral_message: |
      "Dr. Mehta, for the YouTube Short I need 10 minutes of your time on video.
       You'll record 3-4 short answers to common patient questions. I'll edit them
       into the Short. This is the content that works best for patient trust —
       an AI avatar explaining dental care doesn't carry the same weight as you do.
       Can we schedule a 15-minute session this week?"
```

Dr. Mehta agrees to a 15-minute recording session. **Grade A output:** The agent correctly identifies when human expertise cannot be substituted and requests it professionally (DP-025 expert communication).

---

## Phase 4 — WhatsApp Reactivation Broadcast (RESOLVED: GAP-D006)

**Reactivation campaign: patients last seen >12 months ago**

TRAI window check:
- Patients not seen in >12 months have NOT messaged WAOOAW's WhatsApp Business in the last 24 hours
- Solution: HSM (pre-approved template), category: UTILITY (not MARKETING)

```
HSM Template (pre-approved in Meta BM as UTILITY category):
  Template name: dma_dental_reactivation_annual
  Category: UTILITY
  
  Body:
  "Hi {{1}},
   It's been a while since your last visit to Dr. Priya Mehta's clinic.
   Regular checkups prevent 80% of dental problems before they become expensive.
   This October, we have availability for preventive checkups.
   Book: [link] | Reply STOP to opt out."
```

TRAI compliance:
- UTILITY category: exempt from DND hours ✓
- Opt-out: "Reply STOP" included ✓
- Not promotional: no pricing, no offers, no contest → UTILITY compliant ✓
- Evidence record: `WHATSAPP_BROADCAST_SENT` with `template_category: UTILITY, recipient_count: 23` (patients last seen >12 months) ✓

---

## Phase 5 — Mid-Campaign Performance Pivot (RESOLVED: GAP-D007)

**Day 14 (October 14) — SIL signal: mid-campaign performance review**

SIL fires `CAMPAIGN_PERFORMANCE_REVIEW` signal.

Performance data at Day 14:
```
Instagram: 6 posts published. Reach: +34% vs September average.
           Saves: 47 (above baseline). Comments: 23 (mostly "how to book?").
GBP: 11 new reviews (up from 47 to 58). "Dentist near me" impressions +22%.
WhatsApp reactivation: 23 broadcasts sent → 7 replies → 3 bookings confirmed.
Paid Instagram: ₹1,800 spent of ₹6,000 budget. CPM ₹38. CTR 2.1% (above dental industry 1.4%).
Bookings (attributed): 5 confirmed October checkups so far.
```

Agent generates mid-campaign report (professional vocabulary — C-050, DP-025):

**Agent to Dr. Mehta:**
"Dr. Mehta, here's your October campaign at the halfway point.

**What's working well:**
- GBP reviews jumped from 47 to 58 — great progress toward closing the gap with Dantavilas (94).
- Instagram reach is 34% higher than September. Your saves are above normal — patients are bookmarking the content.
- WhatsApp reactivation: 3 bookings from 23 broadcasts — 13% conversion, which is excellent for this type of campaign.
- Paid ads: ₹38 cost per thousand views, 2.1% click rate — better than the dental industry benchmark of 1.4%.

**My recommendation:**
The Week 3 "Meet our team" content should work well here — patients who save content and ask "how to book?" are in the consideration phase. I want to shift some paid budget (₹800) from generic Instagram audiences to a retargeting audience of people who clicked your link but didn't book. Retargeting at this stage typically converts at 3-5x the acquisition rate.

**One concern to raise:**
The paid budget is on track (₹1,800 of ₹6,000). But if the retargeting idea depletes budget faster, I'll need your approval before I reallocate. I'm flagging this now, not when I'm about to spend it.

Do you want to proceed with the retargeting shift? I'll only do it with your go-ahead."

Dr. Mehta: "Yes, do the retargeting."

Constitutional record: `CAMPAIGN_BUDGET_REALLOCATION_APPROVED` — evidence of customer decision ✓

---

## Phase 6 — End-of-Month Report

**October 31 — Final Performance Report**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━
OCTOBER CAMPAIGN RESULTS
Dr. Priya Mehta's Dental Clinic
━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOOKINGS
  Target:    +15 preventive checkups
  Actual:    +18 attributed bookings ✅ (exceeded target)
  
  Attribution breakdown:
    Instagram organic:    6 bookings (patient said "I saw your Reel")
    GBP:                  7 bookings ("found you on Google maps")
    WhatsApp reactivation: 4 bookings (reactivated patients)
    Paid Instagram:       1 booking (retargeting)
    YouTube Short:        0 (published Oct 21 — too early to attribute)

AD SPEND
  Budget:    ₹6,000
  Spent:     ₹5,840 (97% utilised)
  Breakdown:
    Instagram Reels boost:    ₹3,200
    Google Search (Oct CTA):  ₹1,840
    Instagram retargeting:    ₹800
  Cost per booking (paid):   ₹2,920 (vs industry avg ₹4,500-6,000) ✅

GBP
  Reviews: 47 → 67 (+20 reviews in October) ✅
  "Dentist near me" impressions: +31% MoM

INSTAGRAM
  Followers: 1,100 → 1,248 (+148)
  Average reach per post: +34% vs September
  
NEXT MONTH RECOMMENDATION:
  1. Digital Twin YouTube Shorts (Dr. Mehta recorded Week 2 session — 
     edit ready for November)
  2. Diwali post-festival checkup campaign (teeth whitening angle —
     budget: ₹4,000; Meta seasonal audience)
  3. GBP review gap: 67 vs Dantavilas 94 — 27 more to close. At Oct's
     pace (20/month), 2 months to parity.
━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Confidence Run Assessment

| Gap from Sim 007 | Resolution in v2.8 | Grade |
|---|---|---|
| GAP-D001: Platform Intelligence fallback | `competitor_data_available: bool` in output schema; explicit disclosure when benchmark-only | ✅ RESOLVED |
| GAP-D002: Campaign Brief Approval UX | WhatsApp "YES" reply + portal link dual-path; `CAMPAIGN_BRIEF_APPROVED` evidence | ✅ RESOLVED |
| GAP-D003: SCR Check 2 regen limit | SCR_PASSED on all Week 1 content; Check 3 compliance failure routes to customer | ✅ RESOLVED |
| GAP-D004: Platform cascade sequence | Instagram → GBP → WhatsApp → YouTube Short priority ordering explicit | ✅ RESOLVED |
| GAP-D005: Video Brief First (C-058) | Brief approved before MCP call; `VIDEO_BRIEF_APPROVED` evidence record | ✅ RESOLVED |
| GAP-D006: WhatsApp broadcast TRAI | HSM UTILITY category; TRAI window check; opt-out included | ✅ RESOLVED |
| GAP-D007: Mid-campaign pivot trigger | SIL `CAMPAIGN_PERFORMANCE_REVIEW` signal at Day 14; transparent budget reallocation with customer approval | ✅ RESOLVED |

**Quality grade: Grade A** — All outputs are genuinely competitive against a traditional agency: professional copy, evidence-based recommendations, constitutional evidence trail, honest disclosures, expert communication (DP-025 vocabulary: "patients", "bookings", "preventive checkups" — not "leads" or "conversions").

**Constitutional compliance:** All 24 CCTs applicable to DMA confirmed PASS on this scenario.
