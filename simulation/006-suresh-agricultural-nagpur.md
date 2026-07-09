# Simulation 006 — Suresh's Cotton Farm, Katol, Nagpur

**Type:** Full Lifecycle Simulation — Agricultural Advisor Agent (Farmer Friend)
**Status:** Active
**Purpose:** Validate the Agricultural Advisor lifecycle for a small Indian farmer. Surface gaps in WhatsApp-first onboarding, vocabulary mandate enforcement, seasonal billing, evidence chain for insurance, and multi-skill autonomous operation.
**Business:** Suresh Kendre, 52, 1.5 hectare cotton farm, borewell (limited water), Katol, Nagpur district, Vidarbha, Maharashtra.

---

## Phase 1 — Discovery (No Portal)

Suresh is not going to visit a website. He learned about "Farmer Friend" (the agent's marketed name) from his local agricultural extension officer who displayed a poster: "WhatsApp this number for free crop advice."

### [GAP-A001] Agricultural Agent Has No WhatsApp-Native Onboarding

The DMA and Trading agents both use the portal for registration. Suresh cannot and will not use a portal. His onboarding must be entirely WhatsApp-based (C-039 + AD-015 + C-042).

**What WhatsApp-native onboarding means:**
1. Suresh sends a WhatsApp message (voice or text) to the WAOOAW agricultural number
2. The agent identifies him as a new user (no registration exists)
3. The agent conducts the registration AND profiling entirely through WhatsApp conversation
4. There is NO web form, NO portal login, NO email

**The onboarding conversation (replacing the portal registration form):**
```
Agent (Marathi voice): "नमस्कार! मी शेतकरी मित्र आहे. 
आपलं नाव आणि गाव सांगाल का?"
[Hello! I am Farmer Friend. Can you tell me your name and village?]

Suresh: "सुरेश केंद्रे, काटोल, नागपूर"
[Suresh Kendre, Katol, Nagpur]

Agent: "सुरेश दादा, या वर्षी काय पिकवलं आहे?"
[Suresh, what are you growing this year?]
```

**Gap:** The `digital_marketing_profiles` table (which we used for DMA registration data) doesn't fit. The agricultural advisor needs a `farmer_profiles` table (which already exists in the SQL schema from v0.12.0). But the table doesn't have fields for:
- WhatsApp number (how the agent reaches the farmer)
- `whatsapp_opt_in` (TRAI compliance — same GAP-004 from DMA simulation)
- Primary language
- Registration via WhatsApp (not portal) flag

**Layer:** SQL (farmer_profiles table — check existing fields); ADR for WhatsApp-native onboarding flow; C-045 note: the onboarding prompts for agricultural advisor are C-042-constrained and in regional languages.

---

## Phase 2 — Profile Collection (WhatsApp Voice)

The agent conducts the onboarding over 3-4 WhatsApp voice exchanges over 2 days (Suresh doesn't have time for a 15-minute session — he answers between field visits).

### [GAP-A002] Onboarding Completeness Not Achievable in 15 Minutes for Farmers

AD-013 (Conversational Configuration Completeness) requires onboarding in ≤ 15 minutes. This was designed for DMA (Dr. Mehta on a lunch break). For farmers: the WhatsApp-native onboarding is distributed across multiple short conversations over 1-3 days. This is NOT a 15-minute session.

**Constitutional tension:** AD-013 HARD requires ≤ 15 minutes. C-042 (farmer vocabulary and WhatsApp voice primary) implies the farmer sets the pace. These conflict.

**Resolution:** AD-013 must be amended to say: "≤ 15 minutes of active conversation time, which may be distributed across multiple sessions for C-042-governed agents." The agricultural onboarding is constitutionally valid even if it takes 3 days — as long as total active conversation is ≤ 15 minutes.

**Layer:** architectural-drivers.md (AD-013 amendment for C-042 agents).

---

## Phase 3 — First Advisory (Weather Alert)

Day 1 of active engagement. 5:00 AM. weather-ensemble-mcp fetches forecast. ICAR risk analysis runs.

**Ensemble output:** Humidity will reach 87% Thursday-Friday. Grey mildew risk HIGH for cotton at Stage Day 52.

**FARMER_ALERT prompt executes:**
- Input: "Humidity 87%, grey mildew risk HIGH, cotton Day 52"
- Output (Marathi): "सुरेश दादा, गुरुवारी-शुक्रवारी पाऊस राहणार. कापसाला करपा रोगाचा धोका आहे. उद्या सकाळी 8 च्या आधी Carbendazim फवारणी करा."
- Evidence: CE.RecordEvidence(WEATHER_ALERT_ISSUED)

Suresh receives WhatsApp voice. He acts. Sprays Wednesday morning.

Thursday: Heavy dew, high humidity. Neighbouring farms show grey mildew on Day 55. Suresh's crop is clean.

### [GAP-A003] PMFBY Insurance Evidence Chain Requires Adverse Event Confirmation — How?

The CAL record shows: alert issued (Day 52) → farmer acknowledged (Day 52 evening). But for PMFBY insurance: the adverse weather event must also be CONFIRMED. The spec says "adverse_event_confirmed_at" — but who confirms it? 

Current spec: "weather-ensemble-mcp confirms." But:
- IMD issues district-level warnings, not farm-level confirmations
- The farmer can't "confirm" adverse weather in the CAL — he's not a database record
- PMFBY insurance companies accept IMD confirmation, not WAOOAW confirmation

**Gap:** The evidence chain for PMFBY insurance requires IMD district warning records that can be cross-referenced. The weather-ensemble-mcp needs to fetch and store the IMD warning that corresponds to the alert. Currently the `weather_alert_log.adverse_event_confirmed_at` has no mechanism to populate it from an authoritative source.

**Resolution:** When a weather alert is issued, weather-ensemble-mcp should also fetch and store the corresponding IMD district warning ID (if one exists). The adverse_event_confirmed_at is populated when the IMD warning ID becomes confirmed in the IMD database.

**Layer:** weather_alert_log (add imd_warning_id column); weather-ensemble-mcp (add imd.get_district_warning_id tool); agricultural-advisor-agent.md (Skill 1 — PMFBY evidence chain spec).

---

## Phase 4 — Crop Health Morning Check-In

Day 55. Agent sends morning check-in (MORNING_CHECKIN prompt):
"सुरेश दादा, आज कापसाचा ५५ वा दिवस. बुधवारी फवारणी केल्यामुळे झाडे बरी दिसत असतील. आज झाडांच्या पानांवर काही पांढरे डाग आहेत का?"

Suresh (voice, Marathi): "नाही, पाने हिरवी आहेत. पण काही झाडे थोडी वाकली आहेत."
[No, leaves are green. But some plants are bending/drooping a bit.]

Agent CROP_HEALTH reasoning: drooping could be stem borer, water stress, or wind damage.
Asks follow-up: "खाली बघाल का — देठाला छिद्र आहे का?"
[Can you look at the bottom — is there a hole in the stem?]

Suresh: "हो, एक-दोन झाडांवर आहे."
[Yes, on one-two plants there is.]

Agent: "देठ अळी सुरू झाली आहे. आजच संध्याकाळी Chlorpyrifos फवारा. जास्त पसरण्याआधी."
[Stem borer has started. Spray Chlorpyrifos this evening. Before it spreads.]

### [GAP-A004] Voice Transcription in Regional Languages — STT Service Not Specified

The agent receives Suresh's voice message as audio. The `whatsapp-voice-mcp.receive_voice_transcription` tool is specified but the underlying speech-to-text service for Marathi/Hindi/Telugu/Tamil is not specified. Options:
- Google Cloud Speech-to-Text (supports all India languages)
- Azure Cognitive Services Speech (supports all India languages)
- OpenAI Whisper (supports many languages, less accurate for regional)
- IndicSTT (open source, India-specific)

This is an ADR decision. The quality of Marathi STT significantly affects the quality of agent advice — if "Carbendazim" is misheard as "Carbon", the advice changes.

**Resolution needed:** ADR for STT service selection for C-042 agents. The STT must handle regional farming vocabulary (pesticide names, crop terms, measurement units like "bigha", "quintal").

**Layer:** New ADR-023 (STT for India Regional Languages); whatsapp-voice-mcp spec (add STT endpoint configuration); agricultural-advisor-agent.md (note STT quality dependency for C-042 compliance).

---

## Phase 5 — Mandi Price Advisory

Harvest arrives at Day 155. Suresh has ~12 quintals cotton. Agent monitors prices via agmarknet-mcp.

Agent SELL_TIMING reasoning:
- Current Akola price: ₹6,800/q
- 7-day trend: slowly rising
- Last season Suresh got: ₹6,200/q
- Harvest pressure: moderate (many farmers harvesting same week)
- Cash urgency: moderate (school fees due)

Agent (Marathi voice): "सुरेश दादा, आज अकोल्याला भाव ₹6,800 प्रति क्विंटल आहे. गेल्या वर्षीपेक्षा ₹600 जास्त. लातूरला थोडा जास्त ₹6,850 आहे. जर 10 दिवस थांबता आलं, तर सणासुदीमुळे भाव थोडा आणखी वाढेल. पण तुमची गरज असेल तर आत्ता विकणे चांगले."
[Today's price in Akola is ₹6,800/quintal — ₹600 more than last year. Latur is slightly better at ₹6,850. If you can wait 10 days, festive season may push prices higher. But if you need the money now, selling now is good.]

### [GAP-A005] No Price Alert Mechanism — Farmer Must Check Every Day

The current spec says "send price alerts when target price is reached." But:
1. How does the farmer set a target price? (Not in the onboarding flow or Decision Space)
2. If prices spike overnight, how does the agent alert Suresh at 5 AM?
3. Agmarknet prices are reported next-day (T+1), not real-time. What is the data latency?

**Layer:** Skill 3 Decision Space (add price_target as configurable parameter); WhatsApp notification for price thresholds; agmarknet-mcp data freshness documentation.

---

## Phase 6 — Billing (Unique Gap for Agricultural Agent)

### [GAP-A006] Monthly Billing Doesn't Fit Farming Seasons

Monthly billing at ₹999/month means:
- During kharif sowing season (June-October): high value — daily alerts, weekly check-ins
- During rabi season (November-March): moderate value — different crop advice
- Between seasons (April-May): very low value — planning only

Suresh doesn't think in months. He thinks in seasons. Monthly billing creates friction:
- Why am I paying in December when nothing is happening on my farm?
- The subscription will lapse during off-season even if he wants to resume

**Constitutional issue:** C-038 (pro-rata billing — LAW) covers month-level precision. But a seasonal billing model (e.g., Kharif subscription: ₹2,500 for June-October) doesn't fit the current billing schema.

**Resolution options:**
(a) Keep monthly billing, allow pause without friction for off-season months
(b) Create a seasonal subscription plan in `professional_templates`
(c) Create a "farmer calendar" billing mode: bills only during active crop months

**Constitutional implication:** None of these are straightforwardly covered by C-038. This requires a new institutional decision. The billing spec must explicitly address seasonal work patterns.

**Layer:** ADR for seasonal billing; professional_templates (add seasonal lifecycle type); PROJECT_STATE (raise as open architectural question for Founder decision).

---

## Phase 7 — PMFBY Claim Preparation

Suresh's cotton suffered 30% yield loss from hail (Week 8 of the season). The evidence chain exists:
- Day 52: WEATHER_ALERT_ISSUED (hail risk) → CAL record
- Day 52 evening: Farmer acknowledged → CAL record
- Day 54: Hail occurred → IMD district warning confirmed (weather_alert_log.adverse_event_confirmed_at updated)
- Day 54 afternoon: Suresh reported crop damage → CAL record (damage_observation)

### [GAP-A007] PMFBY Claim Report Format Not Specified

The spec says Skill 5 (PMFBY Insurance Evidence) "generates PMFBY claim report on farmer's explicit request." But:
- What format does the claim report take? (PMFBY portal accepts specific formats)
- Who does the farmer submit it to? (PMFBY requires submission to bank or insurance company within 72 hours of damage)
- Does the agent help with the submission? (Would require integrating with PMFBY portal API)
- Does the evidence chain in WAOOAW's CAL directly satisfy PMFBY requirements? (It might not — PMFBY has its own documentation requirements)

**Resolution:** The spec should clarify: the agent produces evidence documentation (CAL records + summary report) that the farmer can use as supporting documents for their PMFBY claim filed through the normal channel (bank, Krishi Vigyan Kendra). The agent does NOT integrate with PMFBY portal directly (too complex, regulated).

**Layer:** agricultural-advisor-agent.md Skill 5 (clarify scope); add PMFBY report prompt to prompt library.

---

## Phase 8 — Re-Hire (New Rabi Season)

October. Kharif complete. Suresh terminates the subscription. January. Rabi wheat is doing poorly. He returns.

### [GAP-A008] Farmer Re-Hire: Which Data Survives?

When Suresh re-hires:
- `farmer_profiles` table: should survive (C-003 — his profile is his identity)
- `agent_progressive_state` (Progressive Crop State Model): should survive for historical reference
- Prior PMFBY evidence records: must survive (immutable CAL records)
- Prior weather alerts: should survive (PMFBY evidence chain)
- Prior crop state for the terminated season: survives as historical record

BUT: the new employment contract starts fresh. The agent greets Suresh as "welcome back" not "welcome." The profile is pre-loaded. This is the same CD-003 pattern from the DMA simulation.

**Additional gap:** The `agent_progressive_state` table references `employment_contract_id`. When the old contract is terminated and a new one created, the prior crop state records belong to the old contract. The new agent cannot directly access them — it needs a join through `employment_contracts.previous_contract_id`.

**Resolution:** `agent_progressive_state` queries should look back through `previous_contract_id` chain for the same farmer. Similar to DMA's `digital_marketing_profiles` survives termination pattern.

**Layer:** data_retention_records (add agricultural data to retention scope); agent_progressive_state query pattern for re-hire; agricultural-advisor-agent.md (re-hire continuity section).

---

## Gap Register — Agricultural Advisor Agent

### P0 — Must resolve before any farmer can be onboarded

| ID | Gap | Resolution |
|---|---|---|
| GAP-A001 | No WhatsApp-native onboarding | Fully WhatsApp-based registration flow spec; farmer_profiles table update |
| GAP-A004 | STT for regional languages not specified | ADR-023 (STT for India Regional Languages) |
| GAP-A006 | Monthly billing doesn't fit farming seasons | Founder decision on seasonal billing; ADR for seasonal subscription model |

### P1 — Must resolve before production

| ID | Gap | Resolution |
|---|---|---|
| GAP-A002 | AD-013 (15 min) incompatible with distributed farmer onboarding | AD-013 amendment for C-042 agents |
| GAP-A003 | PMFBY adverse event confirmation has no IMD integration | weather_alert_log.imd_warning_id; weather-ensemble-mcp imd.get_district_warning |
| GAP-A005 | No price target mechanism for sell timing alerts | Price target in Decision Space; WhatsApp push alert on target reached |
| GAP-A007 | PMFBY claim report format/scope undefined | Clarify scope in spec; add PMFBY report prompt |

### P2

| ID | Gap | Resolution |
|---|---|---|
| GAP-A008 | Re-hire: prior crop state not accessible from new contract | previous_contract_id query pattern for agent_progressive_state |

---

## Constitutional Discoveries — Agricultural Advisor

### CD-A001 — C-042 Vocabulary Mandate Extends to Agent-to-Agent Communication

When the agricultural advisor agent communicates with the Platform Operations Agent (via agent_messages), should those messages also be in farmer-appropriate language? No — agent-to-agent communications are internal and not subject to C-042. C-042 applies ONLY to outputs that reach the farmer. This distinction is not explicit in C-042's text.

**Precedent candidate:** C-042 applies at the customer boundary — the interface between the agent and the customer. Internal agent communications, evidence records, and operational traces are exempt from C-042's vocabulary requirement. The technical data in these records is explicitly preserved for audit, PMFBY, and operational purposes.

### CD-A002 — Seasonal Employment Lifecycle Is Constitutionally Unaddressed

C-034 (employment lifecycle) defines EVALUATION → ACTIVE → SUSPENDED → TERMINATED. This model was designed for continuous professional engagements (digital marketing, trading). For seasonal agricultural advisory, a better model might be EVALUATION → ACTIVE(SEASON) → DORMANT(OFF_SEASON) → ACTIVE(SEASON). The DORMANT state would:
- Suspend billing (C-038 pro-rata)
- Preserve all data (CD-003)
- Auto-reactivate at next season start (customer-configured)

This needs a constitutional amendment to C-034 or a new claim.
