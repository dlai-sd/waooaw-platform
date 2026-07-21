# Suresh-on-Portal — UX Gap Discovery Walkthrough

**Version:** 1.0
**Date:** 2026-07-18
**Status:** COMPLETE — gaps identified, resolutions specified
**Simulation type:** End-to-end portal journey — Discovery → Registration → Trial → First Session → Refer a Friend
**Reference persona:** Suresh, 52, cotton farmer, Katol, Nagpur district, Vidarbha, Maharashtra
**Companion document:** `architecture/reference/ux/constitutional-ux-vocabulary.md`
**Constitutional Basis:** C-039 (Conversational Config), C-042 (Vocabulary Mandate — LAW), C-001 (Human Override), C-063 (Data Minimisation), C-023 (Evidence First), ADR-008 (Keycloak Identity Broker), ADR-022 (Razorpay), ADR-023 (Phone-as-Identity)

---

## Suresh's Profile (Simulation Context)

| Attribute | Value |
|---|---|
| Age | 52 |
| Location | Katol, Nagpur district, Vidarbha, Maharashtra |
| Farm | 1.5 hectare cotton, borewell (limited water) |
| Language | Marathi primary, Hindi secondary. No English. |
| Device | Android mid-range phone (₹12,000). Jio SIM. |
| Accounts | Google (Gmail — because Android). WhatsApp. Facebook (casual). No Apple ID. |
| Digital literacy | Can use WhatsApp voice messages fluently. Manages UPI payments. Does NOT browse websites regularly. |
| Previous experience | Has used government agriculture apps but found them confusing. |
| WhatsApp number | Primary identity per ADR-023 |

**Design constraint:** Suresh must be able to complete the full registration and trial activation using only his thumb on a 6-inch Android screen, in Marathi, in under 5 minutes.

---

## PART A — Discovery & Landing

---

### A-1 — How Suresh Discovers WAOOAW

Suresh sees a Facebook ad in Marathi (Skill 14 — WAOOAW self-marketing):

> *"तुमची कापूस शेती सुरक्षित करा. AI तज्ञ मदतनीस फक्त ₹200/महिना."*
> ("Protect your cotton farm. AI expert advisor at just ₹200/month.")

He taps the ad → lands on WAOOAW home page.

---

### A-2 — Home Page (First 3 Seconds)

**What Suresh sees:** A page in English.

**[GAP-REG-001] Language not auto-detected before page render**

Suresh's Facebook is set to Marathi. His Android is set to Marathi. He arrives on an English page. His instinct: close the tab.

**Resolution:**
```
Priority sequence for language detection:
1. OAuth provider locale (if arriving from social ad with UTM)
2. Browser `Accept-Language` header (Android: mr-IN, hi-IN)
3. IP geolocation → map to state → suggest regional language
4. Default to Hindi if Marathi not available, English as last resort

Implementation:
- Next.js middleware: read Accept-Language header on first request
- If language detected ≠ English: show a language confirmation banner
  "हे मराठीत पाहायचे आहे?" (Want to see this in Marathi?) [हो] [No]
- After confirmation: persist to localStorage, redirect with locale prefix
- Language selector always visible in header — Suresh can correct manually
```

**Keycloak impact:** When Suresh initiates OAuth, pass `ui_locales=mr` in the authorization request so the Keycloak login page also renders in Marathi.

---

### A-3 — Home Page (After Marathi Loads)

Suresh sees the home page in Marathi. He reads:

> *"तुमचा व्यवसाय साठी एक तज्ञ, सर्व tools नाही."*
> ("A professional for your business, not just tools.")

Hero input:
> *"तुमचा व्यवसाय काय आहे?"* ("What does your business do?")

Cycling examples:
- "मी नागपूरमध्ये कापूस पिकवतो" ("I grow cotton in Nagpur")
- "माझी डेंटल क्लिनिक आहे" ("I have a dental clinic")
- "मी F&O trading करतो" ("I trade F&O")

Suresh types in Marathi voice (Android Marathi keyboard voice input):
> *"मी कापूस शेती करतो, नागपूर जिल्हा"* ("I do cotton farming, Nagpur district")

WoW Concierge responds (Marathi):
> *"नागपूर जिल्ह्यातील कापूस शेतकऱ्यांसाठी WaooaW Expert Agricultural Advisor उपलब्ध आहे — हवामान सतर्कता, मंडी भाव, आणि पीक सल्ला मराठीत, WhatsApp वर.
> तुमच्या शेतासाठी काय करेल ते पाहायचे आहे का?"*

**UX requirement met:** C-042 — no technical terms. "WaooaW Expert Agricultural Advisor" not "AI Agricultural Agent v2.7".

---

## PART B — Registration & Login

---

### B-1 — Registration Entry Point

After 3 WoW Concierge exchanges, Suresh taps:

> [**मोफत वापरून पहा — 7 दिवस**] ("Try free — 7 days")

**Registration screen design for Suresh:**

```
┌──────────────────────────────────────────┐
│  WaooaW Expert Agricultural Advisor         │
│  7 दिवस मोफत. कार्ड आवश्यक नाही.          │
│  (7 days free. No card needed.)          │
│                                          │
│  [G] Google ने सुरू करा                  │
│      (Continue with Google)              │
│                                          │
│  [f] Facebook ने सुरू करा               │
│      (Continue with Facebook)            │
│                                          │
│  [📱] WhatsApp / फोन नंबरने सुरू करा    │
│       (Continue with WhatsApp/Phone)     │
│                                          │
│  ──────── किंवा ────────                  │
│                                          │
│  [🍎] Apple ने सुरू करा                  │
│       (Continue with Apple)              │
│                                          │
│  नोंदणी करून तुम्ही आमच्या               │
│  Terms आणि Privacy Policy ला             │
│  सहमत आहात.                              │
└──────────────────────────────────────────┘
```

**Provider priority for Suresh:** Google first (Android default account), then Phone/WhatsApp (most natural for rural India), then Facebook, then Apple (least likely for Suresh but required for Meera/Dr. Mehta on iPhone).

---

### B-2 — OAuth Provider Specifications

#### Provider 1 — Google OAuth (Primary for Suresh)

**Architecture:** Via Keycloak (ADR-008 — already configured).

```
Suresh taps [Continue with Google]
  ↓
Business Platform → /api/v1/auth/social/google
  → Keycloak authorization_endpoint with:
    - client_id: waooaw-platform
    - scope: openid profile email
    - ui_locales: mr               ← Marathi Keycloak page
    - prompt: select_account       ← Show account picker (Suresh may have multiple)
  ↓
Keycloak → Google accounts.google.com
  ↓
Suresh selects his Gmail account (one tap — already logged in on Android)
  ↓
Google → Keycloak (id_token with: sub, name, email, picture, locale)
  ↓
Keycloak → WAOOAW (Keycloak JWT with claims)
  ↓
Business Platform: upsert organisation record, issue session
```

**Data from Google OAuth:**
| Field | Available | Used for |
|---|---|---|
| `sub` (Google ID) | ✓ | Keycloak external ID mapping |
| `name` | ✓ | Pre-fill display name |
| `email` | ✓ | Account communication (NOT primary identity for agricultural) |
| `picture` | ✓ | Default avatar (requires C-063 disclosure — see GAP-REG-008) |
| `locale` | ✓ | Confirm language selection (mr-IN = confirm Marathi) |
| Phone number | ✗ | Not available from Google OAuth |
| Farm details | ✗ | Collected conversationally by agent |

**[GAP-REG-008] Google profile picture — C-063 disclosure required**

Google provides a profile picture URL. Convenient as default avatar. But C-063 (Data Minimisation) requires disclosure when storing data not strictly necessary.

**Resolution:**
```
After Google OAuth completes, show one-tap opt-in:
"Google ने तुमचा फोटो दिला आहे. वापरायचा का?"
("Google provided your photo. Use it?")
[हो, वापरा]  [नको, उभे राहू द्या]

If "No": use initials-based avatar (S for Suresh) — never the Google photo
Data disclosed: "Profile picture stored for identification only. Delete anytime in Settings."
```

---

#### Provider 2 — Facebook Login

**Architecture:** Add Facebook as Keycloak social IDP.

```
Keycloak configuration (waooaw-realm.json addition):
{
  "alias": "facebook",
  "displayName": "Continue with Facebook",
  "providerId": "facebook",
  "enabled": true,
  "config": {
    "clientId": "${FACEBOOK_APP_ID}",
    "clientSecret": "${FACEBOOK_APP_SECRET}",
    "defaultScope": "public_profile,email"
  }
}
```

**Founder action required:** Create WAOOAW Facebook App in Meta Business Manager. App ID and Secret → GitHub Secrets (`FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`).

**Data from Facebook OAuth:** name, email (if user has email attached to FB), profile picture, locale.

**[GAP-REG-009] Facebook email not always available**

Many Indian Facebook users (especially older, rural) did not register with email — they used phone number. Facebook OAuth will return an empty `email` claim for these users.

**Resolution:**
```
After Facebook OAuth: if email is null:
  → ask for phone number only (for WhatsApp agent delivery):
  "WhatsApp वर सल्ला पाठवण्यासाठी तुमचा फोन नंबर द्या:"
  [Phone input + OTP verification via WhatsApp]
  
This phone number becomes the agricultural agent's primary channel identifier (ADR-023).
```

---

#### Provider 3 — Phone / WhatsApp OTP (Critical for Rural India)

This is the most important login path for Suresh — he may not want to link any social account. His WhatsApp number IS his identity (ADR-023).

**Architecture:** Keycloak custom authenticator SPI — Phone OTP.

```
Flow:
Suresh taps [Continue with WhatsApp/Phone]
  ↓
Phone number input screen (Marathi):
  "तुमचा WhatsApp नंबर टाका:" (+91 __________)
  ↓
Business Platform → /api/v1/auth/otp/send
  → First attempt: WhatsApp OTP via WABA (Meta Business API)
    Message: "WAOOAW: तुमचा OTP आहे: 847291. 10 मिनिटांत वापरा."
  → If WABA unavailable: fallback to SMS OTP via MSG91
  ↓
OTP entry screen (6 digits, auto-read on Android — SMS Retriever API)
  ↓
Business Platform → /api/v1/auth/otp/verify
  → On success: Keycloak creates/updates user, issues JWT
```

**OTP delivery specifications:**
| Channel | Provider | Template | Fallback |
|---|---|---|---|
| WhatsApp | WABA (Meta Business API) | `otp_verification` template — pre-approved | SMS |
| SMS | MSG91 (India-specific, DLT compliant) | "WAOOAW OTP: {otp}. Valid 10 min. -WAOOAW" | None |

**[GAP-REG-010] OTP in field with poor connectivity**

Suresh is at his farm. Jio 4G drops to 2G. WhatsApp OTP takes 3 minutes to arrive. Screen has timed out.

**Resolution:**
```
OTP screen requirements:
  - Countdown timer: 10:00 (10 minute validity — longer than standard 5 min for rural India)
  - "दुसरा OTP पाठवा" (Resend) button: appears after 60 seconds, not 30
  - After 2 failed WhatsApp OTP attempts: auto-offer SMS:
    "WhatsApp वर OTP आला नाही? SMS वर पाठवूया?"
    [SMS वर पाठवा]
  - Android SMS Retriever API: auto-fill OTP if SMS is received (no manual copy-paste)
  - Screen timeout: extend to 15 minutes on this screen only (standard is 5 minutes)
```

**[GAP-REG-007] Duplicate phone number**

If Suresh's son already registered with this number:

```
Error message (Marathi — not a code):
"हा नंबर आधीच नोंदणीकृत आहे.
 तुम्ही याआधी वापरला आहे का?"

Options:
[हो, माझे खाते उघडा]  ← OTP re-verification → login to existing account
[नाही, मदत हवी आहे]   ← Opens support chat (Grievance Officer contact)

Never: "Error 409 — Conflict: phone_number_already_registered"
```

---

#### Provider 4 — Apple Sign In (SIWA)

**Primary users:** Dr. Mehta, Meera (iPhone users). Not Suresh.

**Architecture:** Add Apple as Keycloak social IDP (Phase 1 — moved from Phase 3 per ADR-008 original plan).

```
Keycloak configuration (waooaw-realm.json addition):
{
  "alias": "apple",
  "displayName": "Continue with Apple",
  "providerId": "apple",
  "enabled": true,
  "config": {
    "clientId": "${APPLE_SERVICE_ID}",      ← Apple Services ID (not App ID)
    "teamId": "${APPLE_TEAM_ID}",
    "keyId": "${APPLE_KEY_ID}",
    "privateKey": "${APPLE_PRIVATE_KEY}"    ← P8 key from Apple Developer portal
  }
}
```

**[GAP-REG-011] Apple Developer account required — Founder action**

Apple Sign In requires:
1. Apple Developer account (₹8,700/year or $99/year)
2. App ID with Sign In with Apple capability
3. Services ID for web OAuth flow
4. P8 private key from developer portal

**Founder action P0:** Create Apple Developer account and generate SIWA credentials before launch.

**Apple-specific behaviour:** Apple allows users to hide their email (generates a relay address). The platform must handle `privaterelay.appleid.com` email addresses gracefully — they cannot be used for email communication. Must ask for phone number instead for notification delivery.

---

### B-3 — Minimum Mandatory Registration Fields

**Constitutional basis:** C-063 (Data Minimisation — only collect what is necessary).

After any OAuth provider completes, Suresh sees a 2-step completion screen (if fields are missing from OAuth):

**Step 1 — The one thing we need (if not from OAuth):**
```
"WaooaW Expert Agricultural Advisor तुमच्याशी WhatsApp वर बोलेल.
 तुमचा WhatsApp नंबर काय आहे?"

[+91 __________]

ℹ "हा नंबर फक्त तुमच्या WaooaW Expert साठी वापरला जाईल."
  ("This number is used only for your WaooaW Expert.")
```

**Complete minimum field set:**

| Field | Required | Source | Notes |
|---|---|---|---|
| Display name | ✓ | OAuth (pre-filled) or text input | 1 field. Not "first name + last name" |
| Phone number | ✓ for agricultural | OAuth (not available) or OTP flow | WhatsApp agent delivery (ADR-023) |
| Language preference | ✓ | Auto-detected (confirm only) | One tap to confirm, not a form |
| Email | ✗ | OAuth optional | Not required at registration. Collected if customer wants email invoices. |
| Farm details | ✗ | Collected by agent | "What crop do you grow?" is the FIRST message from the agent, not a registration field |
| Address | ✗ | Collected by agent | |
| GST number | ✗ | Collected by billing system at first payment | |

**[GAP-REG-003] Current OpenAPI spec requires more fields**

The existing Business Platform OpenAPI (`POST /api/v1/employment/contracts`) expects `organisation_name`, `primary_contact_name`, `primary_contact_email` as required fields.

**Resolution:**
```
Amend POST /api/v1/employment/contracts:
  - organisation_name:        OPTIONAL at registration (default to display_name + "'s Farm")
  - primary_contact_email:    OPTIONAL (nullable — many agricultural customers have no email)
  - primary_contact_phone:    REQUIRED for agricultural/tutoring agents (ADR-023 basis)
  - language_preference:      NEW required field (mr/hi/en/ta/te/kn/gu/bn/ml/pa/ur)

Progressive completion:
  The Business Platform allows "incomplete" organisation records.
  Missing fields are flagged as `profile_completion_status: PARTIAL`.
  The agent's first conversation fills these in.
  A ≥80% profile completeness is required before the agent begins billing (C-037 — Business KPI).
```

**Registration completes in:** 2 taps (Google OAuth) → phone OTP → language confirm = 3 screens, < 2 minutes for Suresh.

---

## PART C — Post-Registration: First Portal Experience

---

### C-1 — Welcome State (Suresh's Dashboard, First Visit)

```
┌──────────────────────────────────────────┐
│ WAOOAW           [⏹ सुरू करा] [सुरेश ▾] │
│                                          │
│ सुप्रभात, सुरेश! 🌅                      │
│                                          │
│ ┌────────────────────────────────────┐   │
│ │  WaooaW Expert Agricultural Advisor   │   │
│ │  तुमची 7 दिवसांची मोफत चाचणी     │   │
│ │  सुरू आहे.                        │   │
│ │                                    │   │
│ │  पहिली गोष्ट: तुमच्या शेताबद्दल  │   │
│ │  सांगा.                           │   │
│ │                                    │   │
│ │  [WhatsApp वर बोला →]             │   │
│ │  [Portal वर चॅट करा →]           │   │
│ └────────────────────────────────────┘   │
└──────────────────────────────────────────┘
```

**[GAP-REG-012] Suresh's primary channel is WhatsApp, not the portal**

The portal is for monitoring. Suresh's actual conversation with the agent is on WhatsApp (ADR-023). The portal welcome screen must make this immediately clear — and make "Start on WhatsApp" the primary CTA.

**Resolution:**
```
Two CTAs, clearly prioritized:
Primary:   [WhatsApp वर बोला →]    ← Opens WA deep link: wa.me/[WABA_number]
Secondary: [Portal वर चॅट करा →]  ← Web portal conversation (same agent, different channel)

The WhatsApp link pre-loads a conversation opener:
"नमस्कार! मी सुरेश, नागपूर जिल्ह्यातून. WaooaW Expert Agricultural Advisor वापरायचा आहे."
(Agent recognises the number from registration — no need to re-introduce)
```

---

### C-2 — Agent Onboarding Conversation (First 3 Messages)

Suresh taps "WhatsApp वर बोला" → WhatsApp opens with the pre-composed message.

Agent receives the message, identifies Suresh from phone number, sees `profile_completion_status: PARTIAL`.

**Agent opens (Marathi voice message + text):**
> *"नमस्ते सुरेश! मी तुमचा WaooaW Expert Agricultural Advisor. तुम्ही कापूस पिकवता हे मला कळले. या हंगामात किती एकर कापूस आहे?"*
> ("Hello Suresh! I'm your WaooaW Expert Agricultural Advisor. I understand you grow cotton. How many acres of cotton this season?")

This is **conversational profile completion** (C-039) — the first question fills in `farm_area_hectares`. The customer experiences a helpful conversation, not a form.

**[GAP-REG-013] WhatsApp → Portal sync latency**

Suresh has a conversation on WhatsApp. He then opens the portal. The portal must show the WhatsApp conversation history. But WhatsApp webhook events and portal real-time updates need to be in sync.

**Resolution:**
```
All agent conversations (regardless of channel) stored in:
  professional.agent_sessions (existing table)
  professional.agent_messages (new table — channel-agnostic message log)

Portal Activity Feed reads from agent_messages — shows same conversation in portal timeline.
Sync: near-real-time via SignalR (ADR-004) push to portal.
WhatsApp conversation is the source of truth; portal is a mirror.
```

---

## PART D — Refer a Friend

---

### D-1 — Suresh's Referral Scenario

After 10 days on the platform, Suresh's WaooaW Expert correctly predicted a hail storm 72 hours in advance. Suresh tells his farming group on WhatsApp. Harbhajan (Punjab wheat farmer) asks: *"कुठे मिळेल?"* ("Where can I get it?")

Suresh taps the Refer a Friend option in My Profile.

---

### D-2 — Referral Program Design

**Reward model:**

| Party | Reward | When | Condition |
|---|---|---|---|
| Referrer (Suresh) | 1 month free subscription credit | When referred customer completes first paid month | Referrer must be an active subscriber |
| Referred (Harbhajan) | Extended trial: 14 days instead of 7 | At registration | No condition |
| Cap | 12 referral credits per year per customer | — | Prevents abuse |

**[GAP-REF-001] No referral mechanism exists in any current spec**

This is a new functional area. Full specification below.

---

### D-3 — Referral API Specification (New)

**New database table:**
```sql
-- Schema: business
CREATE TABLE referrals (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id       UUID NOT NULL REFERENCES business.organisations(id),  -- referrer
    referral_code         TEXT NOT NULL UNIQUE,                                  -- e.g., "SURESH-KT47"
    referred_org_id       UUID REFERENCES business.organisations(id),            -- filled on conversion
    status                TEXT NOT NULL DEFAULT 'PENDING',                       -- PENDING | CONVERTED | CREDITED | EXPIRED
    trial_extended_days   INT NOT NULL DEFAULT 14,
    credit_amount_paise   INT NOT NULL DEFAULT 0,                                -- filled when credit calculated
    referred_at           TIMESTAMPTZ,
    converted_at          TIMESTAMPTZ,
    credited_at           TIMESTAMPTZ,
    expires_at            TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '90 days',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- RLS: referrer can see their own referrals only
-- CREDIT_AMOUNT calculated at conversion: 1 month of referred customer's plan price
```

**New API endpoints (Business Platform — OpenAPI addition):**

```yaml
# GET /api/v1/referrals/my-code
# Returns the authenticated customer's referral code and stats
responses:
  200:
    referral_code: "SURESH-KT47"
    referral_link: "https://waooaw.com/r/SURESH-KT47"
    whatsapp_share_text: "मी WAOOAW वापरतो — AI Agricultural Advisor फक्त ₹200/महिना! मोफत 14 दिवस वापरून पहा: https://waooaw.com/r/SURESH-KT47"
    stats:
      total_referred: 3
      converted: 1
      credits_earned_months: 1
      credits_available_months: 1

# POST /api/v1/referrals/apply
# Called at registration when ?ref=SURESH-KT47 is present in the URL
body:
  referral_code: "SURESH-KT47"
responses:
  200:
    trial_days_extended: 14    # instead of default 7
    message: "14 दिवसांची मोफत चाचणी मिळाली (सुरेश च्या शिफारसीमुळे)"

# GET /api/v1/referrals/stats
# Full referral history for the authenticated customer
responses:
  200:
    referrals: [...]
    total_credits_earned: 1
    credits_redeemed: 0
    credits_available: 1
    next_credit_triggers: "Harbhajan completes first paid month"
```

**Referral code format:** `[NAME]-[4-character alphanumeric]`
- Generated at registration
- Human-readable (Suresh can share verbally — "SURESH-KT47")
- Unique across platform

**Razorpay credit integration:**
```
When referred customer completes first paid month:
  1. Calculate referrer's credit = referred customer's Month 1 plan amount (₹200 for agricultural)
  2. Apply as Razorpay subscription coupon to referrer's next renewal:
     POST https://api.razorpay.com/v1/coupons
     { "code": "REF-{referral_id}", "type": "flat", "value": 200 }
  3. Add coupon to referrer's subscription:
     PATCH /api/v1/subscriptions/{referrer_subscription_id}/coupon
  4. Record evidence: CE.RecordEvidence(type: REFERRAL_CREDIT_APPLIED)
  5. Notify referrer via WhatsApp:
     "सुरेश, तुमच्या मित्राने पहिला महिना पूर्ण केला! 
      पुढच्या महिन्याचे ₹200 मोफत आहे. 🎉"
```

---

### D-4 — Share Interface Design

```
┌──────────────────────────────────────────┐
│  मित्रांना सांगा                         │
│  (Tell your friends)                     │
│                                          │
│  तुमचा कोड: SURESH-KT47                  │
│                                          │
│  [📋 कॉपी करा]  लिंक: waooaw.com/r/...  │
│                                          │
│  ──────── शेअर करा ────────              │
│                                          │
│  [🟢 WhatsApp वर पाठवा]   ← PRIMARY     │
│  [📘 Facebook वर पाठवा]                  │
│  [📤 इतर apps]                           │
│                                          │
│  तुम्हाला: एक महिना मोफत               │
│  मित्राला: 14 दिवस मोफत चाचणी          │
│                                          │
│  3 मित्रांना सांगितले | 1 ने subscribe  │
│  केले | 1 महिना credit मिळाला           │
└──────────────────────────────────────────┘
```

**WhatsApp share implementation:**
```javascript
const whatsappShareUrl = `https://wa.me/?text=${encodeURIComponent(
  `मी WAOOAW वापरतो — AI Agricultural Advisor फक्त ₹200/महिना!\n` +
  `मोफत 14 दिवस वापरून पहा (माझ्या शिफारसीने): https://waooaw.com/r/SURESH-KT47`
)}`;
```

The WhatsApp share button opens the device's WhatsApp directly with the pre-composed Marathi message. Suresh taps once → selects Harbhajan from his contacts → sends. No copy-paste required.

---

## PART E — Portal Dashboard (Logged-In State)

---

### E-1 — Suresh's Daily Dashboard

Suresh opens the portal at 7 AM to check on his cotton. He sees:

```
┌────────────────────────────────────────────┐
│ WAOOAW     [⏹ Active]      [सुरेश ▾]       │
│                                            │
│ सुप्रभात, सुरेश!  शनिवार, 18 जुलै 2026    │
│                                            │
│ ┌── WaooaW Expert Agricultural Advisor ─────┐ │
│ │  सक्रिय आहे (6:30 पासून)              │ │
│ │                                        │ │
│ │  आज:                                   │ │
│ │  ✓ 6:30 AM — IMD अहवाल तपासला         │ │
│ │    काळजी नाही — हवामान ठीक             │ │
│ │  ✓ 8:15 AM — नागपूर मंडी भाव:        │ │
│ │    कापूस ₹7,200/क्विंटल               │ │
│ │    (3 दिवस थांबा — भाव वाढेल)        │ │
│ │  ⚡ 11:00 — गारपिटीचा धोका: कमी       │ │
│ │                                        │ │
│ │  [WhatsApp वर बोला]  [पूर्ण इतिहास]  │ │
│ └────────────────────────────────────────┘ │
│                                            │
│ [+ नवीन WaooaW Expert जोडा]                  │
└────────────────────────────────────────────┘
```

**"Curious, Engaged, Informed" model in action:**
- **Engaged:** Activity feed shows what the agent did before Suresh woke up. He doesn't need to ask.
- **Curious:** "नवीन WaooaW Expert जोडा" (Add new WaooaW Expert) — surfaces other agent types
- **Informed:** Platform insight card (dismissable, once/week):
  > *"तुमचा WaooaW Expert फक्त तुमच्यासाठी काम करतो. इतर कुठल्याही शेताची माहिती त्याला नाही."*
  > ("Your WaooaW Expert works only for you. It has no information about any other farm.")
  This builds the constitutional trust story for Suresh without technical language.

---

### E-2 — Emergency Stop (Active Session View)

The Emergency Stop pill [⏹ Active] is always visible when an agent session is active.

```
Suresh presses [⏹ Active]:

┌────────────────────────────────────────────┐
│                                            │
│  ⏹ थांबवा                                  │
│  STOP NOW                                  │
│                                            │
│  WaooaW Expert Agricultural Advisor थांबेल.  │
│  सर्व काम 250ms मध्ये थांबेल.             │
│                                            │
│  [हो, थांबवा]     [रद्द करा]              │
│                                            │
└────────────────────────────────────────────┘

After confirmation:
"तुमच्या WaooaW Expert ने काम थांबवले आहे (7:23 AM)
 तुम्ही सांगाल तेव्हा पुन्हा सुरू करेल."
[पुन्हा सुरू करा]
```

C-001 compliance: confirmed — 2 taps maximum from any screen to Emergency Stop.

---

## PART F — Settings & Preferences

---

### F-1 — Settings Screen (Logged-In)

```
┌────────────────────────────────────────────┐
│  सेटिंग्ज                                  │
│                                            │
│  खाते                                      │
│  ├── भाषा: मराठी                    [›]   │
│  ├── थीम: सिस्टम (Light)            [›]   │
│  ├── नोटिफिकेशन्स                   [›]   │
│  └── माझा WhatsApp नंबर: +91-9876…  [›]   │
│                                            │
│  सदस्यता                                   │
│  ├── Agricultural Advisor — ₹200/महिना     │
│  │   चाचणी संपते: 25 जुलै 2026            │
│  └── Payment माहिती जोडा               [›] │
│                                            │
│  WaooaW Expert Scope                          │
│  └── WaooaW Expert काय करू शकतो?         [›] │
│                                            │
│  मदत                                       │
│  ├── प्रश्न विचारा (WoW Concierge)    [›]  │
│  └── Grievance Officer शी संपर्क करा  [›] │
│                                            │
│  [लॉग आउट]                                 │
└────────────────────────────────────────────┘
```

**[GAP-SET-001] Payment method collection timing**

Suresh is on a trial. He sees "Payment माहिती जोडा" (Add payment info). If he ignores this and the trial ends on Day 7, the agent pauses. He's now in the fields — he gets a WhatsApp message saying his agent paused. He wants to pay but he's not near a portal.

**Resolution — WhatsApp payment activation:**
```
Day 5 WhatsApp message from agent:
"सुरेश, तुमची मोफत चाचणी 2 दिवसांत संपेल.
 पुढे सुरू ठेवायचे असेल तर:
 [Pay Now →]  (Razorpay UPI link — opens in WhatsApp browser)
 
 ₹200/महिना. UPI, card, net banking."

The payment link (Razorpay Payment Link API) works inside WhatsApp browser.
Suresh pays via UPI (PhonePe/GPay) — one tap, no portal needed.
On payment success → Razorpay webhook → agent automatically resumes.
```

This preserves the WhatsApp-primary experience for rural customers.

---

## PART G — Gap Summary & Resolution Register

---

### Complete GAP Register (This Walkthrough)

| GAP ID | Description | Severity | Resolution |
|---|---|---|---|
| GAP-REG-001 | Language not auto-detected before page render | HIGH | Browser locale detection + `Accept-Language` header → auto-switch with 1-tap confirm |
| GAP-REG-002 | WhatsApp OTP not specced as portal login path | HIGH | Keycloak custom authenticator SPI; WABA OTP + MSG91 SMS fallback |
| GAP-REG-003 | OpenAPI contract requires too many registration fields | HIGH | Amend `POST /api/v1/employment/contracts` — make all fields except phone+name optional |
| GAP-REG-007 | Duplicate phone number — no clear error path | MEDIUM | Plain-language Marathi error + 2 resolution options (login vs. support) |
| GAP-REG-008 | Google profile picture — C-063 disclosure missing | MEDIUM | One-tap opt-in after OAuth with clear data disclosure |
| GAP-REG-009 | Facebook OAuth — email not always available for rural Indian users | MEDIUM | Post-FB OAuth phone number collection + WhatsApp OTP |
| GAP-REG-010 | OTP expiry too short for poor connectivity | MEDIUM | Extend to 10 minutes; 60s resend delay; WhatsApp→SMS auto-fallback after 2 fails |
| GAP-REG-011 | Apple Developer account not created — SIWA blocked | HIGH | Founder action P0 (before launch for iPhone users) |
| GAP-REG-012 | Portal welcome screen doesn't prioritize WhatsApp for agricultural | HIGH | WhatsApp CTA primary, portal chat secondary on welcome screen |
| GAP-REG-013 | WhatsApp ↔ Portal conversation sync not specced | HIGH | `professional.agent_messages` table (channel-agnostic); SignalR push to portal |
| GAP-REF-001 | No referral mechanism in any current spec | MEDIUM | Full referral API spec + `business.referrals` table + Razorpay coupon integration |
| GAP-SET-001 | Trial-to-paid conversion requires portal visit — blocks rural customers | HIGH | Razorpay Payment Link via WhatsApp (Day 5 nudge) — pays without opening portal |

---

## PART H — Complete API & Integration Specification

---

### H-1 — Authentication APIs

**New endpoints (Business Platform):**

```yaml
POST /api/v1/auth/otp/send
  body:
    phone: "+919876543210"
    channel: "whatsapp" | "sms"
  responses:
    200: { request_id: "uuid", expires_in: 600, channel_used: "whatsapp" }
    429: { retry_after: 60 }  # rate limited

POST /api/v1/auth/otp/verify
  body:
    phone: "+919876543210"
    otp: "847291"
    request_id: "uuid"
  responses:
    200: { access_token: "...", refresh_token: "...", is_new_user: true }
    400: { error: "invalid_otp", attempts_remaining: 2 }
    410: { error: "otp_expired" }

GET /api/v1/auth/social/{provider}/connect
  # provider: google | facebook | apple
  # Redirects to Keycloak authorization_endpoint
  # Query params forwarded: ui_locales, referral_code, agent_type

POST /api/v1/auth/social/{provider}/callback
  # Keycloak → this endpoint after successful OAuth
  # Creates/updates organisation record
  # Returns: access_token, refresh_token, is_new_user, profile_completion_status
```

**Keycloak realm additions required (`waooaw-realm.json`):**

| IDP | Status | Founder action needed |
|---|---|---|
| Google | ✓ Already configured | None |
| Facebook | Needs addition | Create WAOOAW Facebook App (`FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET`) |
| Apple | Needs addition | Create Apple Developer account; generate Service ID + P8 key |
| Phone OTP | Needs custom SPI | Developer: implement `PhoneOTPAuthenticator` Keycloak SPI |

---

### H-2 — Registration & Profile APIs

**Amended endpoints:**

```yaml
POST /api/v1/registration/start
  # Called after any successful OAuth or OTP verification
  body:
    display_name: "Suresh"               # required
    phone: "+919876543210"               # required for agricultural/tutoring
    language_preference: "mr"            # required
    agent_type: "AGRICULTURAL_ADVISOR_INDIA"  # from pre-registration selection
    referral_code: "SURESH-KT47"        # optional — extends trial if valid
    profile_picture_consent: true       # optional — C-063
  responses:
    201:
      organisation_id: "uuid"
      trial_end_date: "2026-07-25"
      trial_days: 14                    # 14 if referral applied, else 7
      whatsapp_agent_number: "+91-WAOOAW-WABA"
      portal_onboarding_url: "/dashboard"

PUT /api/v1/profile
  # Supports both structured JSON and natural language update (NLP processed by AI Runtime)
  body:
    display_name: "Suresh Patil"
    language_preference: "mr"
    notification_preferences:
      whatsapp: true
      push: false
      email: false
```

---

### H-3 — Referral APIs (New — full specification)

```yaml
GET /api/v1/referrals/my-code
  # Authenticated. Creates referral code if one doesn't exist.
  responses:
    200:
      referral_code: "SURESH-KT47"
      referral_link: "https://waooaw.com/r/SURESH-KT47"
      whatsapp_share_text: "..."     # pre-composed Marathi message
      facebook_share_text: "..."    # pre-composed Marathi message
      stats:
        total_referred: 3
        converted_to_paid: 1
        credits_earned_months: 1
        credits_available_months: 1
        credits_redeemed_months: 0

POST /api/v1/referrals/apply
  # Called at registration with referral code
  body:
    referral_code: "SURESH-KT47"
  responses:
    200:
      trial_extension_days: 7      # adds to base 7 = 14 days total
      message_mr: "14 दिवसांची मोफत चाचणी मिळाली"
    404: { error: "referral_code_not_found" }
    410: { error: "referral_code_expired" }

POST /api/v1/referrals/credit  (internal — called by billing webhook)
  # Triggered by Razorpay webhook: referred customer's first subscription payment confirmed
  body:
    referred_organisation_id: "uuid"
    razorpay_payment_id: "pay_xxx"
  # Creates Razorpay coupon → applies to referrer's next renewal → notifies referrer via WhatsApp
```

---

### H-4 — Trial Management APIs

```yaml
GET /api/v1/trials/status
  responses:
    200:
      trial_active: true
      trial_end_date: "2026-07-25"
      days_remaining: 7
      nudge_sent_day5: false

POST /api/v1/trials/convert
  # Manual conversion (from portal Settings)
  body:
    plan_id: "plan_agricultural_advisor"
    payment_method: "razorpay_subscription"
  responses:
    200:
      subscription_id: "sub_xxx"
      razorpay_subscription_url: "https://rzp.io/..."  # payment link
      
# WhatsApp payment path (Day 5 nudge):
POST /api/v1/payments/whatsapp-link  (internal)
  # Called by trial expiry scheduler on Day 5
  body:
    organisation_id: "uuid"
    plan_id: "plan_agricultural_advisor"
  # Generates Razorpay Payment Link → sends via WABA to customer's WhatsApp
```

---

### H-5 — Third-Party Integrations Summary

| Integration | Purpose | Provider | Credentials needed |
|---|---|---|---|
| Google OAuth | Social login | Keycloak (existing) | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — already in secrets |
| Facebook Login | Social login | Meta / Keycloak | `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET` — **Founder action** |
| Apple Sign In | Social login (iPhone users) | Apple / Keycloak | `APPLE_TEAM_ID`, `APPLE_SERVICE_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY` — **Founder action** |
| WhatsApp OTP | Phone-based portal login | WABA (existing WABA account) | Uses existing `WABA_PHONE_NUMBER_ID` — no new credential |
| SMS OTP fallback | OTP fallback for poor WhatsApp delivery | MSG91 | `MSG91_AUTH_KEY`, `MSG91_SENDER_ID`, DLT template ID — **Founder action** |
| Razorpay Subscriptions | Trial-to-paid, referral credits | Razorpay (existing ADR-022) | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` — already specced |
| Razorpay Payment Links | WhatsApp-based payment for rural customers | Razorpay | Same as above |

---

## PART I — Open Items Before UI Sprint Begins

| Item | Owner | Priority |
|---|---|---|
| Amend Business Platform OpenAPI — relax required registration fields | Enterprise Architect | P0 |
| Add Facebook IDP to `waooaw-realm.json` | Developer | P0 |
| Add Apple IDP to `waooaw-realm.json` | Developer (after Founder creates account) | P0 |
| Implement Keycloak Phone OTP custom authenticator SPI | Developer | P0 |
| Create `business.referrals` table + migration | Developer | P1 |
| Implement referral API endpoints | Developer | P1 |
| Implement `professional.agent_messages` table (channel-agnostic) | Developer | P1 |
| Razorpay Payment Link generation + WhatsApp delivery | Developer | P1 |
| MSG91 DLT template registration (mandatory for India SMS) | Founder | P1 |
| Create WAOOAW Facebook App in Meta Business Manager | Founder | P0 |
| Create Apple Developer account + SIWA Service ID | Founder | P0 |
| CCT-UX-01: RTL layout integrity test | Enterprise Architect | P0 before UI sprint |
| CCT-UX-02: Phone OTP flow under 2G conditions | Developer | P1 |
| CCT-UX-03: Referral credit — Razorpay coupon applied correctly | Developer | P1 |
| Marathi language translations — all 11 vocabulary items | **AI task — WAOOAW AI translates its own strings. No Founder or human translator involved.** See `constitutional-ux-vocabulary.md` Section 1.4 for translation standard. | P0 before launch |
