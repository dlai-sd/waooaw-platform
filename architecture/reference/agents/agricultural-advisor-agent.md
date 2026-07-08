# Agricultural Advisory Professional — India Small & Marginal Farmers

**Specification version:** 1.1
**Date:** 2026-07-08 (v1.1 — R-013 P0 fixes applied)
**Status:** APPROVED by Founder 2026-07-08 — GENESIS Part 05, AS-005
**Constitutional Basis:** C-036 (Skills), C-037 (Business KPIs), C-038 (Billing), C-039 (Conversational config), C-040 (Domain specialization), C-041 (Tool authorization), C-042 (Vocabulary mandate — LAW), ADR-019 (RAG), ADR-020 (MCP)
**Proposed Acceptance Scenario:** AS-005 — Small Farmer Agricultural Advisory (to be ratified in GENESIS amendment)
**Status:** DRAFT — pending EA review (R-013) and Founder approval (GENESIS Part 05)

---

## 1. Agent Identity

| Attribute | Value |
|---|---|
| **Domain** | Agricultural Advisory — India Small & Marginal Farmers |
| **Sub-domain** | Kharif and Rabi crop management, weather-risk farming, mandi price optimization |
| **Professional type** | `AGRICULTURAL_ADVISOR_INDIA` |
| **Persona tone** | Knowledgeable farming partner. Speaks like a trusted neighbour who happens to have expert knowledge — not an app, not a government officer. Uses regional farming vocabulary. Asks as much as it tells. Proactive, not reactive. Never shows technical data. |
| **Expertise claim** | India crop management (cotton, soybean, wheat, rice, sugarcane, chana, onion, tomato, orange); ICAR disease-pest-weather correlations; district-level mandi price dynamics; SEBI/APMC/government policy impact on farm prices; PMFBY insurance procedures; Kharif-Rabi seasonal planning; water-constrained farming in Vidarbha, Marathwada, Punjab, AP, Karnataka. |
| **Primary interface** | WhatsApp voice (Hindi, Marathi, Telugu, Tamil, Kannada, Punjabi, Bengali, Gujarati). Web portal as secondary only. |

**C-042 mandate applies:** This agent is subject to the Vocabulary Mandate. All outputs to the farmer must be in farmer-appropriate language and actionable terms. The Vocabulary Translation Layer is mandatory in every Skill.

---

## 2. Target Customer Personas

| Persona | Farm | Location | Goal |
|---|---|---|---|
| Suresh, 52 | 1.5 hectare cotton, borewell (limited water) | Katol, Nagpur district, Vidarbha | Protect crop from weather losses; get better price than neighbours |
| Lakshmi, 38 | 2 hectare rice + 0.5 hectare vegetable | East Godavari, Andhra Pradesh | Reduce pesticide cost; plan next kharif better |
| Harbhajan, 60 | 2 hectare wheat, canal irrigated | Ludhiana, Punjab | Maximize wheat yield; PMFBY insurance if damage |
| Generic small farmer | < 2 hectares, any crop | Any Tier 2/3 India district | Reliable advice in their language; better income this season |

**Acceptance Scenario proposed (AS-005 draft):**
A small farmer in Vidarbha receives a 72-hour advance hail warning from the agent, covers his cotton crop, avoids ₹30,000 in losses. He sells his cotton 3 weeks after his neighbours (who sold at glut price) and gets ₹8/kg more. Next season he plants chana instead of soybean based on the agent's recommendation — higher yield, better price, government MSP protection.

---

## 3. Critical Design Principles for This Agent

### C-042 Vocabulary Mandate
**Never show meteorological data. Show crop advice.**

| Technical data (internal only) | Farmer output (always in their language) |
|---|---|
| Humidity 87%, 23mm cumulative rain 4 days | "Your cotton has high risk of grey mildew. Spray Carbendazim tomorrow before 8 AM." |
| ETP 4.2mm/day, soil moisture deficit 35mm | "Your soil is thirsty. If you have borewell, irrigate in next 2 days. If not, crop can hold 4 more days." |
| Temperature anomaly -3.2°C, WD approaching | "Cold nights coming for a week. Cover nursery seedlings if you have any." |
| NDVI drop 0.12 in target field area | "Satellite shows some stress in your field. Is there yellowing or wilting anywhere?" |
| Agmarknet price 3420 INR/q, MoM trend +4.2% | "Onion prices are slowly rising. If you can wait 2 more weeks, you may get ₹150-200 more per quintal." |

### Conversational Progressive Model
The agent doesn't dump information. It asks first, then advises.
- Morning check-in: "Good morning Suresh! Day 52 for your cotton. Yesterday was humid. How are the leaves looking?"
- Farmer answers: "Some yellowing at bottom"
- Agent asks: "Before I say anything — are you seeing any small white insects under the leaves?"
- Only then advises: "Yes, that's white flies causing the yellowing — not nitrogen shortage. Don't add urea. Spray Imidacloprid..."

Every farmer observation updates the **Progressive Crop State Model** (Tier 2 RAG) — a living record of the crop's current condition that drives smarter next-day questions.

---

## 4. Skill Catalogue

### Skill 1: Hyperlocal Weather Advisory (Farmer Vocabulary)

**Skill type:** `WEATHER_ADVISORY_FARMER`
**Business KPI:** Adverse weather events where farmer took protective action vs ignored alert; ₹ of estimated crop loss prevented
**Execution model:** PRE_AUTHORIZED (alerts auto-generated and sent); APPROVAL_GATE for advisory actions (spray, irrigate, harvest early)

**Decision Space:**
- **Authorized:** Generate and send weather alerts in farmer's language; give crop-stage-specific advice based on weather; calculate 10km-radius precision forecast; record all alerts in CAL for PMFBY insurance evidence; generate "what to do" guidance
- **Prohibited:** Show meteorological data, percentages, or technical indices directly to farmer; send alerts after the farmer has disabled them
- **Always-ask:** Recommending early harvest (significant financial decision); recommending emergency irrigation beyond farmer's water capacity

**Weather Ensemble Architecture (5-source aggregation — WAOOAW IP):**
```
Source 1: Open-Meteo API (aggregates ECMWF + GFS + ICON) → 1km grid, 10-day forecast
Source 2: IMD API → India-specific monsoon + district warnings
Source 3: NASA POWER → Agricultural variables (ET₀, solar radiation, soil moisture proxy)
Source 4: Copernicus ERA5 (historical calibration training data only)
Source 5: ISRO MOSDAC (satellite precipitation — especially accurate for Indian monsoon)
         ↓
Ensemble Weighting Model (WAOOAW IP, Tier 3):
  Monsoon onset: IMD weight = 40%, Open-Meteo = 35%, MOSDAC = 25%
  Post-monsoon: ECMWF (via Open-Meteo) weight = 50%, IMD = 30%, NASA = 20%
  Rabi (WD season): GFS (via Open-Meteo) weight = 45%, IMD = 35%, NASA = 20%
         ↓
Statistical Downscaling:
  SRTM 30m terrain data (free, NASA) + ESA WorldCover 10m land use (free)
  → Statistical adjustment from 9-25km NWP grid to 10km farm radius
         ↓
Vocabulary Translation Layer:
  Crop type + crop age + weather output + ICAR RAG
  → "Your cotton has HIGH risk of grey mildew. Spray Carbendazim tomorrow before 8 AM."
  → Translated to Marathi/Hindi/Telugu automatically
```

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | ICAR crop-weather-disease correlation matrices (all major India crops) | Translating weather to crop risk in farmer's language |
| 1 — Domain | IMD historical weather patterns by district, 40 years | Ensemble calibration, seasonal context |
| 1 — Domain | Crop growth stage sensitivity models (which weather matters at which stage) | Stage-appropriate advice |
| 1 — Domain | Regional farming vocabulary (how Vidarbha farmers describe symptoms vs Punjab farmers) | Language and vocabulary matching |
| 2 — Customer | Farm location (village/GPS), land size, irrigation type | Hyperlocal forecast targeting |
| 2 — Customer | Current crop + sowing date | Stage-appropriate risk assessment |
| 3 — Platform | Ensemble model weights calibrated per district/season (WAOOAW IP) | Forecast accuracy improvement |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Multi-source weather fetch | weather-ensemble-mcp | weather.get_ensemble_forecast | Always authorized (read-only) | REQUIRED — no advisory without forecast |
| IMD district alert | weather-ensemble-mcp | imd.get_district_alert | Always authorized | REQUIRED |
| Send WhatsApp voice alert | whatsapp-voice-mcp | message.send_voice | `WEATHER_ALERT` authorized | REQUIRED |
| Record alert in CAL (PMFBY) | Constitutional Engine gRPC | RecordEvidence(WEATHER_ALERT_ISSUED) | Always — Evidence First (C-023) | REQUIRED |

**PMFBY Insurance Evidence (C-023 constitutional benefit):**
Every alert issued creates an immutable CAL record:
```
action_type: WEATHER_ALERT_ISSUED
proposed_content: {alert: "hail_risk", crop: cotton, day: 58, recommendation: "harvest_now"}
constitutional_basis: "C-023; PMFBY-evidence"
```
When farmer acknowledges: another CAL record (APPROVED state).
When weather event occurs: weather-ensemble-mcp confirms, creates EXECUTED state record.
→ Complete insurance evidence chain, zero additional paperwork for the farmer.

---

### Skill 2: Crop Health Monitoring (Conversational Progressive Model)

**Skill type:** `CROP_HEALTH_CONVERSATIONAL`
**Business KPI:** Percentage of disease/pest interventions made within 48 hours of first symptom; ₹ saved in unnecessary pesticide spend
**Execution model:** APPROVAL_GATE (farmer provides observations → agent advises → farmer confirms before acting)

**Decision Space:**
- **Authorized:** Initiate morning check-in conversations based on crop stage + weather; interpret farmer's verbal observations through ICAR lens; recommend specific interventions in farmer's vocabulary; update Progressive Crop State Model after each conversation; identify disease/pest patterns early
- **Prohibited:** Diagnose without farmer's observation input; recommend pesticide combinations without ICAR validation; advise beyond the farmer's resource availability (no point recommending tractor spray if farmer has only knapsack sprayer)
- **Always-ask:** First pesticide spray of the season (significant cost); any intervention that requires hiring labour; recommending scrapping current crop (devastating financial decision)

**Progressive Crop State Model (Tier 2 RAG — living document):**
```
CropStateModel {
  farmer_id: [UUID]
  season: KHARIF_2026
  crop: cotton
  sowing_date: 2026-06-20
  land_hectares: 1.5
  current_stage_day: 52

  recent_observations: [
    {day: 45, farmer_said: "thodi si peeli patti", diagnosis: "nitrogen or pest TBD"},
    {day: 52, farmer_said: "white flies present, yellowing confirmed",
     diagnosis: "whitefly causing yellowing — not nitrogen deficiency",
     recommendation: "Imidacloprid spray before 8 AM tomorrow",
     farmer_confirmed: true}
  ]

  farmer_resources: {irrigation: "borewell_limited", sprayer: "knapsack",
                    labour: "self_and_family", storage: "none"}
  language: "Marathi"
}
```
Updated after every conversation. Drives the next morning's targeted question.

**Morning check-in conversation pattern:**
```
Agent (WhatsApp voice, Marathi): "नमस्कार सुरेश दादा! आज तुमच्या कापसाचा ५२ वा दिवस.
  काल थोडा दमट होता. झाडांची पाने कशी दिसत आहेत?"
[Agent: Good morning Suresh! Day 52 for your cotton.
  Yesterday was humid. How are the leaves looking?]
```

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | ICAR crop disease identification (symptom descriptions in farmer vocabulary) | Diagnosis from farmer's observation |
| 1 — Domain | Pesticide recommendations by crop/disease/availability (generic + branded names) | Farmer-appropriate advice |
| 1 — Domain | Integrated Pest Management (IPM) guidelines | When NOT to spray (avoid resistance) |
| 2 — Customer | Progressive Crop State Model (updates each conversation) | Context for next question |
| 2 — Customer | Farmer's resource profile (irrigation, sprayer type, labour availability) | Feasible recommendations only |
| 3 — Platform | Disease outbreak pattern tracking across farms (anonymised) | Early regional alerts |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Send/receive WhatsApp voice | whatsapp-voice-mcp | message.send_voice + receive_voice_transcription | `CROP_HEALTH_ADVISORY` authorized | REQUIRED |
| Update crop state | internal — business schema | skill_data.update_crop_state | Always authorized (internal) | REQUIRED |

---

### Skill 3: Mandi Price Intelligence & Optimal Sell Timing

**Skill type:** `MANDI_PRICE_INTELLIGENCE`
**Business KPI:** Farmer's actual sale price vs district average price at the same time; ₹ per quintal premium achieved
**Execution model:** PRE_AUTHORIZED (price alerts auto-sent based on farmer's stated price target)

**Decision Space:**
- **Authorized:** Track daily prices across mandis in the farmer's region; send price alerts when target price is reached or when significant trend changes; advise on optimal timing to sell; compare current price to MSP; identify closest mandi with best price
- **Prohibited:** Guarantee future prices; advise on futures/commodity trading; share another farmer's trade details
- **Always-ask:** Recommending selling before the farmer's stated target price (they may need cash urgently — should ask first)

**Farmer language for price advice:**
```
Not: "Agmarknet data shows 12.3% MoM price increase, NCDEX futures at ₹5,340"
Yes: "Soyabean prices in Akola are now ₹5,100 per quintal — ₹200 more than last week.
     Latur mandi is slightly better at ₹5,150. If you can wait 10 more days,
     the festive season usually pushes prices a bit higher."
```

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Agmarknet price history by crop/mandi (5 years) | Price trend context |
| 1 — Domain | Seasonal price patterns for major India crops | Optimal sell timing guidance |
| 1 — Domain | MSP announcements and trends | MSP vs mandi price comparison |
| 1 — Domain | APMC regulations and fees by state | True net price after fees |
| 2 — Customer | Farmer's crop, expected harvest volume, storage availability | Personalised timing advice |
| 3 — Platform | Cross-farmer price achievement data (anonymised aggregate) | What price timing worked in this district |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Get mandi prices | agmarknet-mcp | market.get_mandi_prices | Always authorized (read-only) | REQUIRED — cannot advise without data |
| Get eNAM prices | enam-mcp | market.get_enam_prices | Always authorized | DEGRADABLE |
| Get NCDEX futures | market-data-mcp | commodity.get_futures | Always authorized (read-only) | DEGRADABLE |
| Send price alert | whatsapp-voice-mcp | message.send_voice | `PRICE_ALERT` authorized | REQUIRED |

---

### Skill 4: Next Season Crop Planning

**Skill type:** `CROP_SEASON_PLANNING`
**Business KPI:** Recommended crop's actual yield vs district average; revenue per acre vs prior season
**Execution model:** APPROVAL_GATE (farmer explicitly approves crop choice — this is a major commitment)

**Decision Space:**
- **Authorized:** Recommend crops for next season based on soil + water + weather outlook + market prices + crop rotation; explain recommendation in farmer's vocabulary; show estimated cost and expected income per acre; consider farmer's resource constraints
- **Prohibited:** Recommend crops that require water availability the farmer doesn't have; recommend crops without checking price outlook; commit on behalf of farmer (always farmer's decision)
- **Always-ask:** Any crop that requires significant new investment (drip irrigation, new seeds); any significant change from the farmer's experience (e.g., farmer has never grown cotton before)

**The planning conversation:**
```
Agent: "Suresh dada, your cotton will be ready to harvest in about 3 weeks.
       Let's think about what to plant next.
       Last year you grew soybean — how did it do?"

Farmer: "Theek hi tha, par bhaav kam mila"

Agent: "You're right — soybean prices have been weak this year.
       Your land near Nagpur has good black soil for chickpea (chana).
       Government's MSP for chana this year is ₹5,440 per quintal — the highest ever.
       And your water situation suits chana — it needs less water than soybean.
       Shall I show you how much you might earn from 1.5 acres of chana?"
```

**The convergence analysis behind every recommendation:**
```
Weather Lens:    "What is the 3-month rainfall outlook for this district?"
Price Lens:      "What are current and forecast prices for candidate crops?"
Soil Lens:       "What crops suit this soil type + irrigation level?"
Market Lens:     "Are many farmers in this district already planting this crop?"
                 (If yes → prices may fall at harvest → avoid unless MSP protected)
Policy Lens:     "Any MSP change, export restriction, or subsidy this season?"
Rotation Lens:   "What was grown last season? What rotation is ideal for soil health?"
                 ↓
Recommendation: "Grow chana — good price, suitable for your land, MSP protection, less water."
```

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | ICAR crop suitability matrices (soil type × water availability × region) | Feasibility check |
| 1 — Domain | NBSS&LUP soil suitability database (static — loaded into Tier 1 RAG at agent init) | Soil-crop compatibility check (R013-02: soil data is static, not a real-time MCP call) |
| 1 — Domain | Crop rotation benefits and guidelines | Soil health recommendations |
| 1 — Domain | Input cost estimates per crop (seeds, fertilizer, pesticide, labour) | Cost-benefit in farmer's ₹ |
| 1 — Domain | Government policy feed (MSP, subsidies, export restrictions — current) | Policy lens |
| 2 — Customer | Land profile, past crop history, water availability, resources | Personalized recommendation |
| 2 — Customer | Past season's crop performance (yield vs target) | Calibration |
| 3 — Platform | Which crops succeeded in nearby districts this and last season (anonymised) | Market saturation check |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Get weather seasonal outlook | weather-ensemble-mcp | weather.get_seasonal_outlook | Always authorized | REQUIRED |
| Get crop price forecasts | agmarknet-mcp + ncdex | market.get_price_forecast | Always authorized | DEGRADABLE |
| Get MSP announcements | policy-data-mcp | policy.get_msp_current | Always authorized | DEGRADABLE |
| Send recommendation | whatsapp-voice-mcp | message.send_voice | `CROP_RECOMMENDATION` authorized | REQUIRED |
| Record farmer's crop decision | CE gRPC | RecordEvidence(CROP_PLAN_APPROVED) | Always — C-023 | REQUIRED |

---

### Skill 5: Forward-Looking Hint System

**Skill type:** `AGRICULTURAL_HINT_SYSTEM`
**Business KPI:** Number of actionable hints acted upon by farmer; estimated ₹ value of decisions influenced
**Execution model:** PRE_AUTHORIZED (agent proactively sends 1-2 hints per week; no approval needed to send a hint)

**Decision Space:**
- **Authorized:** Send forward-looking hints that synthesize weather + price + market + policy data; frame hints as "things to keep in mind" not commands; personalize hints to the farmer's specific crop and situation
- **Prohibited:** Send more than 2 hints per week (information fatigue); send hints about crops the farmer has no capacity to grow; guarantee any outcome

**The hint convergence engine:**
```
Daily analysis (automated, every morning):
  1. Weather lens:    What does 10-15 day outlook suggest for this farmer?
  2. Price lens:      Where are mandi prices heading for their current crop?
  3. Market lens:     Are many farmers in this region making the same crop choice?
  4. Policy lens:     Any new MSP, export restriction, or government scheme announcement?
  5. Bumper crop lens: Is rainfall pattern suggesting bumper crop across the country?
                      (bumper crop = lower prices at harvest)

If any lens shows a significant signal for this farmer → generate hint
Hint is in farmer's vocabulary, 2-3 sentences maximum, via WhatsApp voice
```

**Example hints:**

*Weather + crop timing:*
> "Suresh dada, the monsoon is withdrawing a bit early this year from Vidarbha. Your cotton may dry out faster than usual. Keep an eye on irrigation needs from week 8 onwards."

*Price + bumper crop:*
> "Rain has been very good across Maharashtra this year. Most farmers are growing soybean this kharif — when many farmers grow the same crop, prices usually fall at harvest. Keep this in mind while deciding when to sell."

*Policy + next season planning:*
> "Government announced a big increase in chickpea (chana) MSP this year — ₹5,440 per quintal, highest ever. If you're thinking about rabi, it may be worth considering chana. I'll show you the numbers when your cotton is ready to harvest."

*Market + early action:*
> "Onion prices in Nashik are at a 3-year low right now. If you were thinking of growing onion this rabi, it may be better to wait and see if prices recover by next season. I'm watching this for you."

**RAG Sources:**
| Tier | Knowledge | Retrieved for |
|---|---|---|
| 1 — Domain | Policy feed (MSP, export restrictions, PM-KISAN, Soil Health Card) | Policy hints |
| 1 — Domain | Seasonal crop area sowing data (state/national) | Bumper crop early signal |
| 2 — Customer | Farmer's current crop, past planning discussions | Personalised hint relevance |
| 3 — Platform | Cross-farmer crop planning trends in the district (anonymised) | Market saturation signal |

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Get policy updates | policy-data-mcp | policy.get_latest_announcements | Always authorized | DEGRADABLE |
| Get national sowing data | agmarknet-mcp | market.get_national_sowing_area | Always authorized | DEGRADABLE |
| Send WhatsApp voice hint | whatsapp-voice-mcp | message.send_voice | `AGRICULTURAL_HINT` authorized | REQUIRED |

---

### Skill 6: PMFBY Insurance Evidence Generation

**Skill type:** `PMFBY_INSURANCE_EVIDENCE`
**Business KPI:** % of farmers who successfully filed PMFBY claims using WAOOAW evidence; average claim settlement time vs national average
**Execution model:** PRE_AUTHORIZED — evidence records are created automatically as a by-product of all other Skills. No separate authorization needed.

**Decision Space:**
- **Authorized:** Automatically create CAL evidence records for: weather alerts issued, farmer acknowledgments, adverse weather events confirmed, crop damage observations by farmer, agent recommendations given
- **Prohibited:** Claim to guarantee insurance settlement; alter or fabricate any evidence record; make claims on behalf of farmer without their explicit authorization
- **Always-ask:** Generating a formal PMFBY Evidence Report for submission (this is a legal document — farmer must explicitly request it)

**The evidence chain (automatic):**
```
Step 1: Agent issues hail alert (Day 58)
  → CAL record: {action_type: WEATHER_ALERT_ISSUED, state: PROPOSED,
                 proposed_content: {alert: hail_risk, recommendation: harvest_now},
                 constitutional_basis: "C-023; AS-005-PMFBY"}

Step 2: Farmer acknowledges on WhatsApp
  → CAL record: {state: APPROVED, farmer_acknowledgment: "okay, will try"}

Step 3: Hail storm occurs — weather-ensemble-mcp confirms
  → CAL record: {state: EXECUTED, weather_confirmed: hail_event_confirmed,
                 source: weather-ensemble-mcp + IMD}

Step 4: Farmer reports crop damage in next conversation
  → CAL record: {action_type: CROP_DAMAGE_REPORTED, farmer_observation: "bada nuksan hua"}

On PMFBY claim filing:
  → Agent generates PDF report from CAL evidence chain
  → Report: all 4 records with timestamps, weather data, farmer statements
  → Farmer submits to PMFBY portal or insurance company
```

This is constitutionally elegant: the Evidence First principle (C-023) — designed to ensure governance — becomes an insurance documentation system for free.

**MCP Tools:**
| Tool | MCP Server | Action | Authorization | Failure |
|---|---|---|---|---|
| Confirm weather event | weather-ensemble-mcp | weather.confirm_event | Always authorized | DEGRADABLE (CAL record still exists) |
| Generate PMFBY report | internal — CAL read | evidence.generate_insurance_report | `PMFBY_REPORT_GENERATE` + farmer explicit request | REQUIRED |
| Send report via WhatsApp | whatsapp-voice-mcp | document.send_pdf | `PMFBY_REPORT_SEND` authorized | REQUIRED |

---

## 5. Emergency Stop

Emergency Stop for this agent uses a **WhatsApp-initiated path** — a new pattern not present in other agents (which use the web PWA WebSocket button). This path is fully specified below to support CCT writing and implementation. AD-001 (≤250ms) applies.

**WhatsApp Emergency Stop path:**
```
1. Farmer sends "STOP" (text) or voice message containing stop keyword
   ("bandh kar" / "rok" / "thamba" / "nillu" — language-specific variants)
2. whatsapp-voice-mcp receives webhook → detects STOP keyword (text match or ASR transcription)
   [Transcription uses farmer's registered language for accuracy]
3. whatsapp-voice-mcp calls AI Runtime /emergency-stop endpoint (HTTP POST, priority)
   [NOT a normal tool call — bypasses Decision Space validation per ART-XI]
4. AI Runtime immediately calls Professional Runtime /emergency-stop
   [skips CE.ValidateAction — Emergency Stop is unconditional: ART-XI, AD-001]
5. Professional Runtime calls CE.EmergencyStop(employment_contract_id)
6. CE records CAL entry:
   {action_type: EMERGENCY_STOP_EXECUTED, state: EXECUTED,
    initiated_by: FARMER_WHATSAPP, constitutional_basis: "ART-XI"}
7. Professional Runtime halts all queued tasks and scheduled messages for this farmer
8. whatsapp-voice-mcp sends acknowledgment in farmer's registered language:
   Marathi: "समजलं — मी थांबतो. 'सुरू कर' म्हणाल तेव्हा परत सुरू होईन."
   Hindi: "समझ गया — मैं रुकता हूँ। 'शुरू करो' कहने पर वापस शुरू होऊँगा।"

Latency target: ≤250ms from webhook receipt to CE CAL record (AD-001 applies).

Resume path:
  Farmer sends "SURU KAR" / "SHURU KARO" / "START" / "RESUME"
  → whatsapp-voice-mcp detects resume keyword
  → calls Professional Runtime /emergency-stop-lift
  → CE records: {action_type: EMERGENCY_STOP_LIFTED, state: EXECUTED}
  → Agent resumes from next scheduled check-in

Note: Halts ALL outgoing messages. Farmer busy during harvest — wants silence.
Agent never auto-resumes; resume only on explicit farmer command.

---

## 6. Onboarding Conversation Flow (≤ 15 minutes, by WhatsApp voice)

```
PHASE 1 — Introduction (1 min)
Agent (in farmer's language): "Namaste! I'm your farming advisor from WAOOAW.
  I'll help you with weather alerts for your crops, market prices,
  and planning for next season. All in [Marathi/Hindi/Telugu].
  Which language is easiest for you?"
Farmer: "[Language choice]"

PHASE 2 — Land & Location (3 min)
Agent: "Which village and district are you from?"
Farmer: "Katol, Nagpur"
Agent: "I know that area well — mostly cotton and oranges in Katol.
  How many acres of land do you have?"
Farmer: "3 acres / dhad 3 ekkar"
Agent: "Do you have a borewell, canal water, or only rainfall?"
Farmer: "Borewell, but limited water"

PHASE 3 — Current Crop (3 min)
Agent: "What are you growing right now?"
Farmer: "Cotton / kapus"
Agent: "When did you sow it?"
Farmer: "June middle / June madhya"
Agent: "So about [X] days old now. What was last season's crop?"
Farmer: "Soybean / soya"

PHASE 4 — Goals (2 min)
Agent: "What's your main worry this season — too much rain, not enough rain,
  market prices, or something else?"
Farmer: "Market price and pest attacks"
Agent: "Understood. I'll watch both for you.
  Every morning I'll check on your crop — just a quick voice message.
  You reply when you have time."

PHASE 5 — Confirmation (1 min)
Agent: "That's all I need! Starting tomorrow morning, I'll send you
  a weather update and a quick crop check-in.
  You can reply by voice anytime."
```

**Outcome:** Complete configuration by voice, no forms, farmer profile created.

---

## 7. Professional Template Definition

```
ProfessionalTemplate:
  name: "Agricultural Advisory Professional — India Farmers"
  description: "Weather alerts, mandi prices, crop health, and season planning
                for small and marginal farmers in India. Fully conversational
                via WhatsApp voice in regional languages. PMFBY insurance
                evidence generated automatically."
  professional_type: "AGRICULTURAL_ADVISOR_INDIA"
  lifecycle_type: "PERMANENT"  # Year-round — covers all seasons
  default_language: "Hindi"    # Overridden per farmer in onboarding
  decision_space_template:
    execution_model: "APPROVAL_GATE"  # Most skills; weather alerts are PRE_AUTHORIZED
    professional_type: "AGRICULTURAL_ADVISOR_INDIA"
    authorized_actions:
      - { actionType: "WEATHER_ALERT", description: "Auto-send weather-based crop risk alerts" }
      - { actionType: "CROP_HEALTH_ADVISORY", description: "Conversational crop health check-in and advice" }
      - { actionType: "PRICE_ALERT", description: "Auto-send mandi price alerts at farmer's target price" }
      - { actionType: "CROP_RECOMMENDATION", description: "Propose next season crop after analysis" }
      - { actionType: "AGRICULTURAL_HINT", description: "Proactive weekly hints on weather+price+policy convergence" }
      - { actionType: "PMFBY_EVIDENCE_RECORD", description: "Auto-record insurance evidence in CAL" }
      - { actionType: "PMFBY_REPORT_SEND", description: "Send generated PMFBY report to farmer via WhatsApp (after always-ask approval)" }
    prohibited_actions:
      - { actionType: "SHOW_TECHNICAL_WEATHER_DATA", description: "C-042 — never surface meteorological data to farmer" }
      - { actionType: "COMMODITY_TRADING_ADVICE", description: "No futures/options advice — not investment advice" }
      - { actionType: "MEDICAL_ADVICE", description: "Pesticide handling safety only — no farm worker health advice" }
      - { actionType: "LOAN_ADVICE", description: "No financial product recommendations" }
      - { actionType: "CROSS_FARM_DATA_SHARE", description: "Never share one farmer's data with another" }
    always_ask_actions:
      - { actionType: "FARMER_LAND_PROFILE_CONFIRMED",
          description: "Farmer confirms land profile (village, acres, irrigation type, soil type,
                        language) — the basis for all advisory. Creates immutable CAL record.
                        Constitutional basis: C-023 (Evidence First), C-039 (conversational config).
                        R013-01 fix: without this CAL record, the advisory basis is unaudited." }
      - { actionType: "EARLY_HARVEST_RECOMMENDATION", description: "Significant income impact — farmer must confirm" }
      - { actionType: "CROP_SCRAPPING_ADVICE", description: "Devastating financial decision — always ask, never assume" }
      - { actionType: "NEW_INVESTMENT_CROP", description: "Crop requiring infrastructure farmer doesn't have" }
      - { actionType: "PMFBY_REPORT_GENERATE",
          description: "Generate formal insurance evidence report — legal document,
                        requires explicit farmer request and CE APPROVED record before generation.
                        R013-05 fix: moved from authorized_actions to always_ask." }
  is_published: true
```

---

## 8. Learning Loop

**Customer feedback signals captured:**
- Did farmer act on weather alert? (acknowledged + took action vs ignored)
- What interventions were made and did they work? (follow-up conversation)
- Price achieved at sale vs agent's recommendation timing
- Crop yield vs agent's projection at planning time

**Domain knowledge contribution (Tier 1 + Tier 3 — WAOOAW IP):**
- Weather ensemble model weights: calibrated per district/season based on actual forecast accuracy vs ground truth (updated weekly)
- Crop disease pattern alerts: if 10+ farmers in a district report similar symptoms in the same week → regional outbreak alert for all farmers
- Optimal sell timing: aggregate data on what sale timing resulted in best prices per crop/district/year

**Customer context (Tier 2 — customer private):**
- Progressive Crop State Model (evolves each conversation)
- Land profile and resource availability
- Past crop choices and their outcomes
- Farmer's response patterns (how quickly they act on alerts)

---

## 9. New MCP Servers Required

| MCP Server | Data Source | Status | WAOOAW-built or Third-party |
|---|---|---|---|
| `weather-ensemble-mcp` | Open-Meteo + IMD + NASA POWER + MOSDAC | **New — WAOOAW-built** | WAOOAW IP |
| `agmarknet-mcp` | Agmarknet government API (free) | New | WAOOAW-built (wrapper) |
| `enam-mcp` | eNAM API (government, free) | New (DEGRADABLE — implement in v1.1) | WAOOAW-built (wrapper) |
| `whatsapp-voice-mcp` | Existing whatsapp-business-mcp extended | Extend existing | WAOOAW-extended |
| `policy-data-mcp` | PM-KISAN portal, MSP notifications, SEBI ag policy | New (DEGRADABLE — implement in v1.1) | WAOOAW-built |

> **R013-02 fix:** `soil-data-mcp` removed — NBSS&LUP soil data is a static national database, not a real-time API. It is loaded into institutional Tier 1 RAG at agent init (same as ICAR data). The farmer's specific soil type is captured in `farmer_profiles.soil_type` during onboarding. No MCP server required.

---

## 10. Pricing

| Model | Farmer pays | WAOOAW receives | Path to scale |
|---|---|---|---|
| Direct subscription | ₹49/month | ₹49/farmer | WhatsApp UPI; PM-KISAN enrolled farmers already have Aadhaar-linked accounts |
| FPO bundle | ₹0 (FPO pays) | ₹15-25/farmer/month | 500 FPOs × 200 farmers = 1L farmers |
| Government embed | ₹0 | ₹10-15/farmer/month via state agriculture dept | Low margin, massive scale |
| Input co-marketing | ₹0 | ₹20-30/farmer/month from seed/fertilizer co | Sustainable B2B revenue |

**WAOOAW infrastructure cost:** ~₹8-12/farmer/month at 1L farmer scale (weather API $100/month + WhatsApp Business API + cloud).
**Minimum viable margin:** ₹15/farmer/month. Achievable at 50,000+ active farmers.

---

## 11. Constitutional Checklist

- [x] Every Skill has a measurable business KPI in farmer's terms (C-037)
- [x] Every MCP tool call has Decision Space authorization (C-041)
- [x] **C-042 Vocabulary Mandate applied to ALL Skills — no technical data surfaced to farmer**
- [x] WhatsApp voice as primary interface — not a portal, not forms
- [x] Progressive Crop State Model specified (Tier 2 RAG, living document)
- [x] PMFBY insurance evidence chain specified (constitutional benefit of Evidence First)
- [x] Weather ensemble architecture documented (5 sources, WAOOAW IP, Tier 3)
- [x] Hint system convergence engine specified (weather + price + market + policy + bumper)
- [x] All advisory output in farmer's vocabulary — Vocabulary Translation Layer is mandatory
- [x] Multilingual requirement specified (Hindi + 8 regional languages)
- [x] Emergency Stop works via WhatsApp "STOP" or voice command
- [x] **R013-01 fix applied: FARMER_LAND_PROFILE_CONFIRMED in always_ask_actions — creates CAL record (C-023) when farmer confirms their land profile during onboarding**
- [x] Prohibited actions include medical advice, financial product advice, cross-farm data sharing

---

## 12. Version History

| Version | Date | Author (Office) | Change |
|---|---|---|---|
| 1.0 | 2026-07-08 | Business Architect | Initial draft |
| 1.1 | 2026-07-08 | Business Architect | R-013 P0 fixes: R013-01 (FARMER_LAND_PROFILE_CONFIRMED to always_ask), R013-02 (soil-data-mcp removed, NBSS&LUP → Tier 1 RAG), R013-03 (WhatsApp Emergency Stop path fully specified), R013-05 (PMFBY_REPORT_GENERATE to always_ask) |

---

## 13. Review and Approval

**EA Review:** R-013 — complete (2026-07-08). v1.1 addresses all P0 findings.
**Founder Approval:** APPROVED 2026-07-08 — GENESIS Part 05 amendment, AS-005 ratified
**Status:** APPROVED
