# ADR-023 — WhatsApp Phone-as-Identity for C-042 Agents

**Status:** Accepted
**Date:** 2026-07-09
**Author:** Enterprise Architect (Issue #1 — Agent Update: Agricultural Advisor WhatsApp Integration)
**Constitutional Basis:** C-039 (conversational interface — CONFIRMED); C-042 (Vocabulary Mandate — LAW); AD-004 (multi-tenant isolation — HARD); AD-015 (Multilingual Voice Interface); C-001 (human override unconditional); C-023 (Evidence First)

---

## Context

The Agricultural Advisor Agent (and any future C-042-governed agent) serves customers with limited digital literacy. Its primary interface is WhatsApp voice — not a web portal. This creates an identity problem:

WAOOAW's existing identity infrastructure uses **Keycloak OAuth 2.0** (browser-based). When Dr. Mehta or Rahul register, they visit a portal, authenticate with Keycloak, and receive a JWT that is passed with every API request. Row-Level Security on PostgreSQL trusts this JWT to isolate tenant data.

A farmer in rural Vidarbha will not:
- Open a browser
- Navigate to a registration form
- Create a username and password
- Complete an email verification flow

The farmer's interface is: **save a phone number, send a WhatsApp voice message, receive advice**.

The identity mechanism must match the interface. Keycloak is architecturally wrong for this use case.

---

## Decision

**The farmer's Meta-verified WhatsApp phone number IS the primary identity credential for C-042-governed agents.**

Meta verifies every WhatsApp account via OTP to the registered SIM. This verification is stronger than most self-service registrations (it's tied to a physical SIM card). WAOOAW accepts Meta's verification as authoritative for agricultural advisory customers.

The mechanism is the **Phone Identity Service** — a lightweight component that:
1. Receives the farmer's phone number from every inbound WhatsApp message
2. Maps it to the farmer's `organisation_id` (or creates one if first contact)
3. Issues a short-lived internal session token scoped to that `organisation_id`
4. This token propagates to all downstream services exactly as a Keycloak JWT does for portal users

The data isolation guarantee (AD-004, RLS) is identical for both paths. Only the identity source differs.

---

## The Phone Identity Service (phone-identity-service, port 8137)

This is NOT an MCP server — it is a platform service called by the Business Platform when processing WhatsApp webhooks. It is stateless beyond the DB lookup.

### Service Responsibilities

```
1. VALIDATE incoming WhatsApp webhook
   - Verify Meta HMAC signature (X-Hub-Signature-256 header)
   - Reject any request with invalid signature → 403 (never processed)
   - Prevent replay attacks: check message timestamp is within ±5 minutes
   - Deduplicate by WhatsApp message_id: Meta may retry failed webhooks with the same
     message_id. Store processed message_ids in phone_identity_sessions for 24 hours.
     If message_id already processed: return 200 OK (idempotent) without re-processing.
     This prevents: duplicate approvals, duplicate NPS scores, duplicate PMFBY acknowledgments.

2. IDENTIFY the sender
   - Extract `from` field (phone number in E.164 format: +919876543210)
   - Look up in farmer_profiles.phone_number_whatsapp
   
3a. KNOWN FARMER
   - Return: { organisation_id, farmer_profile_id, session_token, is_new: false }
   
3b. UNKNOWN FARMER (first contact — auto-registration)
   - Create minimal farmer_profiles row:
       { phone_number_whatsapp, whatsapp_opt_in: TRUE (consent given by messaging us),
         onboarding_channel: WHATSAPP, profile_status: INCOMPLETE }
   - Create organisations row with tenant_id
   - CE.RecordEvidence(FARMER_REGISTERED, action_type=WHATSAPP_AUTO_REGISTRATION)
   - Return: { organisation_id, farmer_profile_id, session_token, is_new: true }

4. ISSUE SESSION TOKEN
   - Generate: JWT signed with internal WAOOAW key (NOT Keycloak)
   - Claims: { sub: organisation_id, phone: phone_number, exp: NOW+30min, iss: "waooaw-phone-identity" }
   - This token is used internally to set app.tenant_id in DB sessions
   - Never sent to the farmer (internal use only)

5. LOG session
   - Insert into phone_identity_sessions table
```

### The 30-minute session window

Each farmer interaction is a conversation turn. The session token lives for 30 minutes — sufficient for a multi-exchange check-in conversation. If the farmer messages again after expiry, a new token is issued automatically. There is no "login" concept — every inbound message validates identity.

---

## WhatsApp Webhook Processing Flow (full sequence)

```
Meta webhook → WAOOAW Business Platform /api/v1/whatsapp/webhook
    ↓
1. Phone Identity Service: validate HMAC signature
   → Invalid: 403 FORBIDDEN (log, no further processing)
   → Valid: proceed
    ↓
2. Phone Identity Service: identify farmer
   → Known: get organisation_id + issue session token
   → Unknown: auto-register + issue session token
    ↓
3. Business Platform: set DB session variable
   SET LOCAL app.tenant_id = '{organisation_id}'
   (identical to JWT middleware for portal users — RLS activates)
    ↓
4. Business Platform: route to agent
   → Is farmer in active APPROVAL_GATE conversation? → route to pending approval
   → Is farmer starting fresh? → route to agent execution loop trigger
   → Is farmer in onboarding? → route to Customer Profiling pipeline
    ↓
5. AI Runtime: executes agent reasoning with session context
   (Tier 2 RAG, farmer profile, progressive crop state — all RLS-filtered)
    ↓
6. Response: via whatsapp-voice-mcp (TTS if voice, text if text)
    ↓
7. CE.RecordEvidence: every agent action recorded with farmer's organisation_id
```

---

## TRAI Compliance — Constitutional Prerequisite

India's TRAI regulations prohibit unsolicited commercial messages. This is constitutionally enforced:

**Opt-in mechanism (WhatsApp-native):**
- Any farmer who sends WAOOAW a WhatsApp message has opted in — the act of messaging is explicit consent
- `farmer_profiles.whatsapp_opt_in = TRUE` is set during auto-registration (step 3b above)
- WAOOAW may NOT proactively message a farmer who has never messaged WAOOAW first
- Broadcast campaigns to farmer lists (not via inbound) require separate opt-in evidence records

**New constitutional constraint added to agricultural-advisor-agent.md:**

> `TRAI_OPT_IN_REQUIRED` — ALWAYS-ASK: Before sending any business-initiated message (proactive weather alert, price advisory) to a farmer who has not previously messaged WAOOAW in the last 24 hours, verify `whatsapp_opt_in = TRUE` AND a user-initiated conversation exists in the last 24 hours (Meta's 24-hour service window). Outside this window: send HSM pre-approved template only.

---

## WhatsApp-Native Discovery and Registration Flow

### How a New Farmer Finds WAOOAW

Distribution channels (no portal required):
1. **QR code on physical poster** at Krishi Vigyan Kendra, bank branch, fertiliser shop → WhatsApp opens with pre-filled message
2. **Extension officer shares number** via word of mouth or poster
3. **WhatsApp Business Profile** — WAOOAW's profile is searchable in WhatsApp directory
4. **Click-to-WhatsApp from digital channels** (Kisan portal, government agriculture apps)

### First Contact Flow

```
Farmer scans QR code → WhatsApp opens with pre-filled text:
"नमस्कार, मला शेती सल्ला हवा आहे" [Hello, I want farming advice]
(Or simply sends any message — the QR poster instructs: "Send any message to start")

WAOOAW receives → Phone Identity Service → auto-registers → agent wakes

Agent (Marathi voice):
"नमस्कार! मी शेतकरी मित्र आहे — तुमचा शेती सल्लागार.
तुमचं नाव आणि कुठलं गाव ते सांगाल का?"
[Hello! I am Farmer Friend — your farming advisor.
What is your name and which village are you from?]
```

### The Complete WhatsApp Onboarding (distributed, ≤15 min total — AD-013 amended)

```
Message 1 (farmer): [any text or voice]
Agent: Greeting + name + village question (OPENING_MESSAGE prompt)

Message 2 (farmer): "Suresh Kendre, Katol, Nagpur"
Agent: Confirms name/location + asks crop question (INFERENCE_CONFIRM prompt)

Message 3 (farmer): "Cotton, just sowed 3 weeks ago"
Agent: Summary card (voice): "I know: Suresh, Katol Nagpur, cotton 21 days old.
I need 2 more things — what size land and do you have borewell or canal water?"

Message 4 (farmer): "1.5 acre, borewell but water is less"
Agent: Profile MINIMUM_VIABLE → triggers Market Research equivalent
(for agricultural advisor: first weather check + crop stage assessment)
Agent: "Your farm is registered. I'll send you a daily update on your cotton.
Start time: tomorrow morning 7 AM."
→ farmer_profiles.profile_status = MINIMUM_VIABLE
→ CE.RecordEvidence(FARMER_ONBOARDED)
→ Temporal: schedule first morning check-in
```

---

## Security Model

| Threat | Mitigation |
|---|---|
| Fake webhook (not from Meta) | HMAC-SHA256 signature validation on every request; invalid = 403, no processing |
| Replay attack | Message timestamp check: ±5 minutes from server time |
| Phone number spoofing | Cannot happen — Meta controls the `from` field; WAOOAW does not accept user-supplied phone numbers |
| Session token leakage | Tokens are internal-only; never sent to farmer; 30-minute expiry; stored in phone_identity_sessions |
| Impersonation (stolen SIM) | Same limitation as all phone-based identity — SIM ownership = identity. Acceptable for agricultural advisory (no financial transactions). For agents handling financial actions, additional identity verification would be required. |
| Cross-tenant data access | RLS enforces `app.tenant_id` = `organisation_id` on every query. Session token cannot be escalated. |

---

## Consequences

**New containers:** `phone-identity-service` (port 8137) — internal platform service, not exposed externally.

**New SQL table:** `phone_identity_sessions` — session tokens per phone number.

**Changes to agricultural-advisor-agent.md:**
- Constitutional basis adds: ADR-023
- Always-ask adds: `TRAI_OPT_IN_REQUIRED`
- Section 4 (Onboarding) replaced with WhatsApp-native flow
- All skills: add `phone-identity-service` as prerequisite tool (session token required before any MCP call)

**No change to Keycloak:** Portal users continue to use Keycloak. Phone identity is parallel, not replacement. Both produce scoped session tokens that RLS trusts.

**Future agents:** Any future C-042 agent (or any WhatsApp-first agent) reuses this ADR. The Phone Identity Service is not agricultural-specific — it handles any phone-number-identified agent interaction.

---

## Rejected Alternatives

**A — Keycloak with WhatsApp as external IdP:** Keycloak supports external identity providers but requires a redirect flow — the user must visit a URL in a browser. WhatsApp does not support browser redirects mid-conversation. Technically impossible for WhatsApp-native users.

**B — OTP-based registration (WAOOAW sends OTP via SMS):** Adds friction, cost (Twilio/Msg91 for OTP SMS), and regulatory complexity (DLT registration for transactional SMS India). The farmer's WhatsApp account is already OTP-verified by Meta — WAOOAW should trust that rather than re-verify.

**C — Store session in Redis:** Overkill for this use case. The DB lookup is fast (<5ms on an indexed phone number query), and the session token is short-lived. Redis adds operational complexity without meaningful performance gain at agricultural advisory scale.

---

## Tiered WhatsApp Session Security (v2 — 2026-07-13)

WhatsApp phone-as-identity is the industry standard for routine interactions (banks including HDFC, Axis, Kotak use it). However, high-risk financial and legal actions require an additional authentication factor — consistent with how Indian banks handle it (MPIN for transactions, portal redirect for high-risk changes).

### Action Risk Tiers

```yaml
TIER_1_LOW_RISK:
  examples:
    - Routine content approval (Instagram post, WhatsApp broadcast)
    - NPS score response
    - Crop monitoring check-in
    - Homework helper query (Private Tutor)
    - Informational queries
  auth_required: PHONE_NUMBER_IDENTITY  # ADR-023 current model — no change
  additional: none

TIER_2_MEDIUM_RISK:
  examples:
    - Seasonal crop plan confirmation (agricultural — major annual commitment)
    - PMFBY insurance acknowledgment (legal document trigger)
    - Campaign brief approval (monthly campaign — significant time commitment)
    - Homework assignment submission confirmation (tutor)
  auth_required: PHONE_NUMBER_IDENTITY
  additional: "Explicit confirmatory reply REQUIRED — agent waits for YES/CONFIRM before proceeding"
  pattern: "Reply YES to confirm [action summary]. Reply NO or ignore to cancel."
  evidence: Constitutional record with customer reply text (C-023)
  note: "The explicit YES reply IS the authorization event. Different from a casual message."

TIER_3_HIGH_RISK:
  examples:
    - Ad budget approval above ₹2,000 (financial commitment)
    - New campaign with significant spend (₹5,000+ monthly)
    - Agent Employment Contract change (subscription upgrade/downgrade)
    - Trading session authorization above daily loss threshold
  auth_required: PHONE_NUMBER_IDENTITY + MPIN_CHALLENGE
  mpin_mechanism:
    what: "4-digit MPIN set by customer during web portal onboarding"
    storage: "Bcrypt hashed in business.customer_security table — never in plain text"
    prompt: "To confirm ₹5,000 campaign budget: reply your 4-digit WAOOAW PIN"
    max_attempts: 3  # After 3 failures: lockout (see below)
    lockout_policy:
      duration: 30 minutes (per account, not per IP — IP-based lockout enables DoS)
      scope: PER_ACCOUNT (locks the specific customer's MPIN for 30 min)
      notification: "WhatsApp message + portal notification: 'Your WAOOAW PIN has been
                     temporarily locked after 3 incorrect attempts. It will unlock at [time],
                     or you can reset it immediately at waooaw.com/security'"
      security_event: MPIN_LOCKOUT logged to constitutional.audit_ledger (C-023)
                      includes: timestamp, organisation_id, ip_address_hash (not plain IP)
      after_lockout: "Action reverts to TIER_4 (portal deep-link) until MPIN is reset"
      fraud_detection: "3 lockouts in 24 hours → SECURITY_ALERT to platform operations"
    reset: "Via web portal only (Keycloak re-authentication required) — not via WhatsApp"
    storage: "Bcrypt hash (cost factor 12), stored in business.customer_security — never plaintext"
  note: "MPIN is not required for the full session — only for the specific high-risk action."

TIER_4_CRITICAL:
  examples:
    - Employment Contract creation (new hiring)
    - Emergency Stop reversal (restart after stop)
    - Bank account / payment details change
    - Account deletion
  auth_required: WEB_PORTAL_ONLY
  whatsapp_response: |
    "This action needs to be completed securely on the WAOOAW portal.
     Here's your secure link: [deep link with pre-filled session]
     The link expires in 15 minutes."
  note: "Some actions are too consequential for any messaging channel.
         This is consistent with how Indian banks redirect WhatsApp users 
         to NetBanking/app for NEFT transfers or mandate changes."
```

### MPIN Onboarding (Portal)

During web portal onboarding (PATH 1 — Keycloak OAuth), every customer is prompted to set a WhatsApp MPIN:

```
"For your security, set a 4-digit PIN for high-value approvals on WhatsApp.
 This PIN is required when approving budgets or major decisions via WhatsApp.
 
 [Set PIN] — optional but strongly recommended
 
 If you skip this, high-risk approvals will redirect to the portal instead."
```

A customer without an MPIN is not blocked — their Tier 3 actions fall back to TIER_4 (portal redirect) rather than MPIN challenge.

### JWT Implication (ADR-008 v2)

The `auth_path: WHATSAPP` claim in the session JWT carries a `mpin_verified: true/false` flag that the Constitutional Engine checks:

```
CE.ValidateAction receives:
  action: AD_BUDGET_APPROVE (₹8,000)
  session.auth_path: WHATSAPP
  session.mpin_verified: false
  
CE decision: DENY — "High-risk financial action requires MPIN verification on WhatsApp.
              Please reply your 4-digit PIN to proceed."
              
After MPIN reply:
  session.mpin_verified: true
  
CE decision: ALLOW — evidence recorded: BUDGET_APPROVED + mpin_verified: true
```

### Industry Standard Reference

| Bank | Low-risk (WhatsApp) | High-risk (WhatsApp) | Critical |
|---|---|---|---|
| HDFC | Phone number sufficient | OTP sent to registered mobile | NetBanking redirect |
| Axis | Phone number sufficient | MPIN | App redirect |
| Kotak | Phone number sufficient | OTP | NetBanking redirect |
| **WAOOAW** | Phone number sufficient | **MPIN (4-digit, portal-set)** | **Portal deep-link** |

WAOOAW's model is aligned with Indian banking practice and stricter than most non-financial apps.

