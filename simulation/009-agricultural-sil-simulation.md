# Simulation 009 — Agricultural Advisor: SIL Proactive Alerts + Multi-Signal Day

**Type:** User Simulation — Agricultural Advisor v2.6 (SIL Weather + Price Alerts, TRAI Boundary, Multi-Signal Handling)
**Status:** Active
**Purpose:** Validate C-053 Signal Intelligence Layer for the agricultural agent under real-world stress conditions: simultaneous signals, TRAI DND hours, multi-language voice delivery, and the PMFBY insurance evidence chain. Extends Simulation 006 (Suresh's Cotton Farm).
**Persona:** Suresh Kendre, cotton farmer, Katol, Nagpur. Day 71 of the Kharif 2026 season. Cotton is in boll formation stage — the most critical weather window.

---

## Phase 1 — The Multi-Signal Day (Wednesday 11 PM)

It is 11:00 PM. Suresh is asleep. Three signals fire simultaneously.

### Signal 1: WEATHER_HAIL_RISK (C-053)

Weather-ensemble-mcp data: Hail probability 72% for Katol district, Thursday morning 6-9 AM. Cotton at Day 71 (boll formation — maximum hail vulnerability).

Materiality: 0.94 → URGENCY_CLASS: CRITICAL
`emergency_exempt: true`

SIL: Should alert Suresh immediately. It is 11:00 PM.

### Signal 2: DISTRICT_PEST_OUTBREAK (C-053)

Tier 3 RAG (anonymous aggregate): 7 cotton farms in Katol district reported pink bollworm on Day 68-72. Risk window for Suresh: HIGH (same stage, same district).

Materiality: 0.76 → URGENCY_CLASS: HIGH
TRAI window: Suresh last messaged WAOOAW at 7:30 PM (3.5 hours ago — within 24-hour window).

### Signal 3: PRICE_RAPID_DROP (C-053)

Agmarknet data: Cotton prices in Akola fell ₹420/q in 2 days (from ₹7,100 to ₹6,680). Suresh's harvest is 12 days away. His stated price target: ₹6,500/q.

Materiality: 0.71 → URGENCY_CLASS: HIGH
Note: Price target not yet crossed (₹6,680 > ₹6,500), but rapid decline is an advisory signal.

---

### [GAP-A009] CRITICAL Signal at 11 PM — TRAI DND Hours Conflict

Signal 1 (hail risk) is CRITICAL → `emergency_exempt: true`. The spec says IMMEDIATE delivery regardless of TRAI window, regardless of budget.

But TRAI's DND (Do Not Disturb) regulations in India prohibit promotional messages between **9 PM and 9 AM**. The hail risk alert is not a promotional message — it is an emergency advisory. But TRAI's regulations distinguish between:
- Transactional messages: exempt from DND (OTP, booking confirmations, emergency alerts)
- Service messages: partially exempt with pre-approval
- Promotional messages: subject to DND

**The gap:** The spec declares CRITICAL signals are `emergency_exempt: true` (bypassing budget). But it does not explicitly state that CRITICAL signals are exempt from TRAI DND hours. The two exemptions (budget and DND) are separate.

**Constitutional resolution:**
- C-001 (Human Override) + C-053 (Signal Sensing Obligation) together create a constitutional obligation that overrides TRAI DND for CRITICAL signals affecting life/livelihood
- CRITICAL signal delivery method at DND hours: **HSM pre-approved template** (Meta WhatsApp has a "utility" message category that is exempt from DND when pre-approved)
- The hail alert HSM template must be categorized as "UTILITY" (not "MARKETING") in Meta Business Manager
- The distinction: promotional messages inform the customer about WAOOAW services; CRITICAL agricultural alerts warn the customer about imminent crop loss — these are clearly UTILITY messages

**Layer:** SIL specification — add DND exemption for CRITICAL signals; HSM templates for agricultural agent — change category from "MARKETING" to "UTILITY" for CRITICAL signal templates; agricultural-advisor-agent.md Section 4.13 (WEATHER_HAIL_RISK `trai_outside_window_behavior: "IMMEDIATE"` is correct — but should add `hsm_category: UTILITY`).

---

### [GAP-A010] Simultaneous Multi-Signal Alert — No Bundling or Sequencing Rule

At 11:00 PM, all three signals fire within 5 minutes. The SIL would, by default, send three separate WhatsApp messages to Suresh:
1. 11:00 PM: Hail risk alert (CRITICAL)
2. 11:03 PM: Pest outbreak alert (HIGH)
3. 11:05 PM: Price drop alert (HIGH)

Three WhatsApp messages at 11 PM — even for emergency agricultural content — is overwhelming and likely to cause the farmer to disengage from future alerts. The value of CRITICAL alerts degrades when they arrive with two other messages.

**Gap:** No bundling or sequencing rule exists for simultaneous signals. The SIL sends each signal independently.

**Resolution:**
```
Multi-signal bundling rules (per signal session):
1. CRITICAL signals: send immediately, solo — no bundling with any other signal
2. HIGH signals within 15 minutes of a CRITICAL signal: hold for 2 hours, then bundle
3. Multiple HIGH signals within 15 minutes of each other: bundle into one advisory
4. ADVISORY signals: always bundle with next scheduled communication
```

Result for Suresh: 11:00 PM hail alert (CRITICAL, solo). 1:00 AM: bundled message (if TRAI allows) or held until 6:00 AM (before hail risk window opens): pest outbreak + price trend combined.

**The combined 6 AM message:**
"सुरेश दादा, आजच्या गुजारे बद्दल दोन गोष्टी:
1. कापूस अळी: काटोल तालुक्यात 7 शेतांवर दिसली. तुमची झाडे तपासा.
2. भाव: अकोल्याला दोन दिवसांत ₹420 घसरले. अजून ₹180 बफर आहे. घाई नको."

**Layer:** SIL specification (add multi-signal bundling rules); agent-execution-loop.md (SignalWatchWorkflow — add signal queue with bundling logic); agricultural-advisor-agent.md Section 4.13 (add `bundling_rule` per signal type).

---

## Phase 2 — CRITICAL Hail Alert Delivery (11:02 PM)

Alert delivered via WhatsApp Voice (CRITICAL, immediate):

"सुरेश दादा, आत्ता उठा — उद्या सकाळी 6 ते 9 वाजेपर्यंत गारपीट होण्याची 72% शक्यता आहे. कापूस 71 व्या दिवशी आहे — गारपीट सर्वात जास्त नुकसान करते. 

काय करायचे: आत्ता शक्य असल्यास झाडांवर जाळी टाका. नसल्यास उद्या सकाळी 5 वाजता उठा आणि फांद्या बांधा.

PMFBY साठी: या संदेशाला 'हो' reply करा — हे तुमच्या विमा दाव्यासाठी record होईल."
[Suresh, wake up now — 72% hail probability 6-9 AM tomorrow. Cotton at Day 71 — maximum vulnerability.
Do: cover plants with net if possible. Otherwise: wake at 5 AM, tie branches.
For PMFBY: reply 'yes' to this message — it will be recorded for your insurance claim.]

Suresh receives the message. He wakes up. Replies "हो" (Yes).

CE.RecordEvidence:
- `action_type: WEATHER_ALERT_ISSUED`
- `materiality_score: 0.94`
- `signal_source: weather-ensemble-mcp`
- `farmer_acknowledged: true`
- `acknowledged_at: 2026-09-30T23:17:00+05:30`
- `constitutional_basis: C-053; C-023; C-001`

### [GAP-A011] PMFBY Evidence Chain: IMD Confirmation Still Not Automated

The hail alert was issued at 11 PM. The hail event occurs at 7:30 AM (confirmed by Suresh's field report at 8 AM). The IMD district warning for Nagpur was issued at 10:45 PM (15 minutes before the SIL alert).

**Gap:** The `weather_alert_log.imd_warning_id` column (needed since GAP-A003 in Simulation 006) still has no automated population mechanism. The `weather-ensemble-mcp` fetches hail probability data but does NOT fetch the corresponding IMD district warning ID.

**To complete the PMFBY evidence chain, the IMD warning ID must be stored.** Without it, the insurance company has no authoritative third-party confirmation that aligns with the WAOOAW alert.

**Resolution:**
- `weather-ensemble-mcp` tool: `imd.get_district_warning(district, date_range)` — added to MCP catalogue
- When HAIL_RISK or WEATHER_HEAVY_RAIN signal fires: immediately fetch IMD warning ID for the district
- Store `imd_warning_id` in the `weather_alert_log` table (add column)
- If no IMD warning exists at time of alert (our forecast preceded IMD): check again at 6 AM; if IMD issues a subsequent warning, retroactively update `imd_warning_id`

**Layer:** `weather_alert_log` SQL table (add `imd_warning_id` column, `imd_warning_fetched_at`); weather-ensemble-mcp spec (add `imd.get_district_warning` tool); agricultural-advisor-agent.md Skill 1 (PMFBY evidence chain — add IMD confirmation step).

---

## Phase 3 — Morning After (6:00 AM)

Suresh checks his field at 6:30 AM. Hail hit. Some boll damage — estimated 20-25% yield loss.

Suresh messages: "गारपीट झाली, माझ्या कापसाला 25% नुकसान झाले"
[Hail happened, 25% damage to my cotton]

SIR receives. Intent: CROP_DAMAGE_REPORT → primary skill: `PMFBY_INSURANCE_EVIDENCE`

Agent:
"सुरेश दादा, नुकसान झाल्याचं आम्हाला माहित आहे. तुमचा Insurance चा record तयार आहे:
- काल रात्री 11:02 वाजता Alert गेला ✓
- तुम्ही 11:17 ला 'हो' सांगितलं ✓
- हवामान विभागाचा नागपूर Districtचा Warning: WRN-2026-09-30-NGP-HAI ✓

आता 72 तासांत तुमच्या Bank किंवा PMFBY helplineला (1800-180-1551) सांगा.
मी तुमच्यासाठी एक Report बनवतो — Print करा आणि न्या."

### [GAP-A012] PMFBY Report Generation Not Implemented

The agent says it will generate a PMFBY report. But:
1. The `AGRI/SKILL/PMFBY_REPORT_GENERATE` prompt is listed in the prompt catalogue but its output format is not specified
2. The report must include: CAL evidence records, farmer profile, crop details, weather data, IMD warning reference, in a format acceptable to PMFBY officers
3. The report needs to be sent to Suresh in a format he can use: either a PDF (requires `pdf-generation-mcp`) or a WhatsApp voice summary (simpler)

**Gap:** PMFBY report output format and delivery mechanism not specified.

**Resolution:**
- PMFBY report format: PDF with structured sections (Farmer Profile, Crop Details, Alert Record, IMD Reference, Evidence Chain)
- Delivery: PDF sent via `whatsapp-voice-mcp: document.send_pdf` to farmer's WhatsApp
- Additionally: verbal summary via WhatsApp voice in Marathi
- `pdf-generation-mcp` already exists in containers.md — connect it for PMFBY reports
- PMFBY report prompt output schema: specify required sections and PMFBY-compatible format

**Layer:** agricultural-advisor-agent.md Skill 6 (PMFBY — add report format spec); `AGRI/SKILL/PMFBY_REPORT_GENERATE` prompt (add output schema with PDF section structure); add `pdf-generation-mcp` to Agricultural agent's MCP tool list.

---

## Phase 4 — Price Target Mechanism

Two weeks later. Harvest complete. Suresh has 12 quintals. Current Akola price: ₹6,720. His SIL price target (configured during onboarding): ₹6,500 (already crossed).

Wait — why hasn't the price alert fired if ₹6,720 > ₹6,500?

### [GAP-A013] Price Target Is Referenced in SIL But Not Captured in Decision Space or Farmer Profile

The SIL Section 4.13 references `farmer.stated_price_target` as a relevance dimension. But:
- `farmer_profiles` table does not have a `stated_price_target` column
- The onboarding conversation for Agricultural agent (Section 6.3) does not ask for price target
- `stated_price_target` is referenced in the spec but has no database home

**Gap:** The price target that drives the SIL `PRICE_TARGET_CROSSED` signal is an orphaned reference — it exists in the SIL spec but is not stored anywhere.

**Resolution:**
- Add `stated_price_target_inr_per_quintal NUMERIC(8,2)` column to `business.farmer_profiles`
- Add price target question to the WhatsApp onboarding conversation: "तुम्हाला किती भाव मिळाला की विकायचा विचार कराल? (किमान किंमत)" [What price would make you consider selling? (minimum price)]
- The SIL `PRICE_TARGET_CROSSED` materiality classifier reads from `farmer_profiles.stated_price_target_inr_per_quintal`
- Price target is updateable (farmer can change it via WhatsApp: "माझा भाव target ₹7,000 कर" → agent updates)

**Layer:** `business.farmer_profiles` SQL (add price_target column); agricultural-advisor-agent.md onboarding (add price target question); agricultural-advisor-agent.md Skill 3 (confirm price target is persisted to profile); RLS (no change — farmer_profiles already tenant-scoped).

---

## Gap Register — Agricultural Simulation 009

### P0 — Must resolve before any proactive signal delivery

| ID | Gap | Resolution |
|---|---|---|
| GAP-A009 | CRITICAL signals at DND hours — TRAI DND exemption not declared | Declare CRITICAL=UTILITY message category; HSM templates must be UTILITY category |
| GAP-A010 | Simultaneous signals — no bundling or sequencing rule | Add multi-signal bundling rules to SIL specification |
| GAP-A013 | Price target not stored in farmer_profiles — SIL reference is orphaned | Add stated_price_target column to farmer_profiles; add to onboarding conversation |

### P1 — Before production

| ID | Gap | Resolution |
|---|---|---|
| GAP-A011 | IMD warning ID not automatically fetched for PMFBY chain | Add imd_warning_id to weather_alert_log; weather-ensemble-mcp imd.get_district_warning tool |
| GAP-A012 | PMFBY report format and delivery not specified | Specify report format + PDF delivery via whatsapp-voice-mcp; add pdf-generation-mcp to agricultural MCP list |

---

## Constitutional Discoveries — Agricultural Advisor

### CD-A003 — UTILITY vs MARKETING: A Constitutional Distinction for Proactive Communication

C-053 (Signal Sensing Obligation) requires proactive alerts for CRITICAL signals. WhatsApp's HSM template system has categories: MARKETING, UTILITY, AUTHENTICATION. CRITICAL agricultural alerts are UTILITY, not MARKETING. This distinction matters for:
1. TRAI DND compliance (UTILITY is exempt from DND hours)
2. Meta WhatsApp template approval (UTILITY templates have fewer restrictions)
3. Constitutional integrity (a CRITICAL crop loss warning is a service obligation, not a marketing message)

The AGENT-AUTHORING-GUIDE Section 3.18 should specify: "Every signal type with `emergency_exempt: true` or `urgency_class: CRITICAL` must declare `whatsapp_template_category: UTILITY`. An agent that sends a CRITICAL signal under a MARKETING template has misclassified a constitutional obligation as a commercial message."

### CD-A004 — Multi-Signal Bundling Is a Constitutional Obligation (C-048)

Sending three simultaneous WhatsApp messages to a sleeping farmer at 11 PM (even if justified individually) crosses C-048 (Information Non-Exploitation). The agent has an information advantage — it knows all three signals fired simultaneously. Using that advantage to bombard the farmer with three messages rather than one intelligently bundled message is an exploitation of the information asymmetry. The agent should use its knowledge of ALL active signals to communicate more intelligently than sending each signal independently.
