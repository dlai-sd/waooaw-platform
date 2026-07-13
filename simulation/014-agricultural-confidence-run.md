# Simulation 014 — Agricultural Confidence Run: Suresh's Multi-Signal Night (v2.6)

**Type:** Confidence Run — Agricultural Advisor v2.6
**Status:** Active
**Purpose:** Re-run the Simulation 009 scenario with all identified gaps resolved. Validate that the Agricultural Advisor v2.6 handles simultaneous multi-signal alerting (CRITICAL + HIGH + HIGH), TRAI DND hours compliance, multi-signal bundling, PMFBY evidence chain, and advisory-grade crop protection recommendations in Marathi.
**Persona:** Suresh Kendre, cotton farmer, Katol, Nagpur. Day 71 of Kharif 2026. Cotton in boll formation — maximum hail vulnerability.
**Gaps resolved:** GAP-A009 (TRAI DND — CRITICAL signal delivery method: UTILITY HSM), GAP-A010 (multi-signal bundling rules), GAP-A011 (PMFBY evidence chain — customer reply creates insurance record), GAP-A012 (voice vs text for CRITICAL alerts in Marathi)

---

## Context: Multi-Signal Bundling Rules (Now In Spec)

Added to agricultural-advisor-agent.md Section 4.13 (Signal Intelligence Layer):

```yaml
multi_signal_bundling_rules:
  CRITICAL:
    delivery: IMMEDIATE_SOLO
    bundling: NEVER  # Critical signals are always delivered alone
    trai_window: OVERRIDE  # CRITICAL overrides DND via UTILITY HSM category
    
  HIGH:
    within_15_min_of_CRITICAL: HOLD_2_HOURS_THEN_BUNDLE
    multiple_HIGH_within_15_min: BUNDLE_INTO_ONE_ADVISORY
    delivery_window: "If held past 9 PM, deliver at 6 AM — before first field activity"
    trai_window: RESPECT  # HIGH signals respect DND unless customer has opted into 24hr alerts
    
  ADVISORY:
    delivery: BUNDLE_WITH_NEXT_SCHEDULED_COMMUNICATION
    trai_window: SCHEDULED_WINDOW_ONLY
```

---

## Phase 1 — Three Signals at 11:00 PM

**Wednesday, 11:00 PM — Day 71 of Kharif 2026**

### Signal arrival order (within 5 minutes):

| Time | Signal | Type | Materiality | Action per bundling rules |
|---|---|---|---|---|
| 11:00 PM | `WEATHER_HAIL_RISK` — Katol district, 72% probability 6-9 AM Thursday | CRITICAL | 0.94 | IMMEDIATE_SOLO |
| 11:03 PM | `DISTRICT_PEST_OUTBREAK` — pink bollworm at Day 68-72 stage in 7 farms | HIGH | 0.76 | HOLD (within 15 min of CRITICAL) |
| 11:05 PM | `PRICE_RAPID_DROP` — cotton ₹7,100 → ₹6,680 in 2 days | HIGH | 0.71 | HOLD + BUNDLE with pest alert |

SIL bundling decision log:
```yaml
bundle_session_id: BSID-2026-07-71
  signal_1:
    type: WEATHER_HAIL_RISK
    decision: IMMEDIATE_SOLO
    reason: CRITICAL — no bundling permitted
    
  signal_2:
    type: DISTRICT_PEST_OUTBREAK
    decision: HOLD_FOR_BUNDLE
    hold_until: "6:00 AM Thursday (before field activity window; within TRAI window)"
    bundle_trigger: arrival within 15 minutes of CRITICAL signal
    
  signal_3:
    type: PRICE_RAPID_DROP
    decision: HOLD_FOR_BUNDLE
    hold_until: "6:00 AM Thursday (same bundle as signal_2)"
    bundle_trigger: multiple HIGH signals within 15 minutes
```

---

## Phase 2 — CRITICAL Hail Alert Delivery (11:02 PM)

### TRAI compliance resolution (GAP-A009):

```yaml
hsm_template_selection:
  signal: WEATHER_HAIL_RISK
  urgency: CRITICAL
  trai_time: "11:00 PM — within DND hours (9 PM – 9 AM)"
  
  template_selected: agri_critical_weather_alert_v2
  template_category: UTILITY  # Not MARKETING — critical advisory is exempt from DND
  meta_approval_status: APPROVED (pre-approved in Meta Business Manager)
  
  constitutional_basis: "C-001 (Human Override — CRITICAL crop protection alert);
                         C-053 (Signal Sensing Obligation — CRITICAL signals are 
                         UTILITY messages, not promotional content)"
```

### Alert sent via WhatsApp Voice + Text (CRITICAL format, Marathi):

**Voice message (Marathi, delivered 11:02 PM):**
> "सुरेश दादा, लगेच उठा. उद्या सकाळी ६ ते ९ वाजेपर्यंत काटोल भागात ७२ टक्के गारपीट होण्याची शक्यता आहे. तुमचा कापूस ७१ व्या दिवशी आहे — बोंड फुटण्याच्या अवस्थेत गारपीट सर्वात जास्त नुकसान करते. आत्ता शक्य असल्यास झाडांवर जाळी टाका. नसल्यास उद्या पहाटे ५ वाजता उठा आणि फांद्या बांधा. PMFBY साठी या संदेशाला 'हो' उत्तर द्या — हे विमा दाव्यासाठी नोंदवले जाईल."

**Translation:** "Suresh, wake up now. 72% hail probability for Katol district tomorrow morning 6-9 AM. Your cotton is at Day 71 — boll formation stage is the most vulnerable to hail. If possible, cover plants with netting now. If not, wake up at 5 AM tomorrow and tie the branches. For PMFBY insurance claim, reply 'हो' (yes) to this message — it will be recorded."

**Text message (same time, for record + easier reply):**
```
🚨 गारपीट इशारा — काटोल
उद्या पहाटे 6-9: गारपीट 72%
कापूस Day 71 — जास्त धोका

आत्ता: जाळी टाका
5 AM: उठा, फांद्या बांधा

PMFBY साठी: 'हो' reply करा ⬇️
```

Evidence record created (C-023):
```yaml
action_type: PROACTIVE_SIGNAL_ALERT
signal: WEATHER_HAIL_RISK
urgency_class: CRITICAL
hsm_template_category: UTILITY
trai_window_status: "OUTSIDE_WINDOW — CRITICAL_OVERRIDE_UTILITY"
delivery_method: [VOICE, TEXT]
delivery_timestamp: "2026-07-TK-23:02:18 IST"
customer_notified: true
bundling_decision: IMMEDIATE_SOLO
```

---

## Phase 3 — Suresh Replies "हो" (PMFBY Evidence Chain) — RESOLVED: GAP-A011

**11:07 PM — Suresh replies "हो"**

System:
1. WhatsApp webhook receives "हो" → maps to `PMFBY_CLAIM_ACKNOWLEDGMENT`
2. Evidence record: `{action_type: PMFBY_SIGNAL_ACKNOWLEDGMENT, signal_id: BSID-2026-07-71, customer_reply: "हो", timestamp: 23:07:33 IST, organisation_id: suresh_kendre}`
3. `pmfby_claim_evidence` table records: `weather_alert_delivered: true`, `customer_acknowledged: true`, `acknowledgment_channel: WHATSAPP`, `hail_probability: 72%`, `crop_stage: BOLL_FORMATION_DAY_71`

**Agent reply (11:08 PM):**
"नोंदवले. उद्या जर गारपीट झाली, तर हा संदेश आणि तुमचे उत्तर PMFBY दाव्यासाठी वापरता येईल. सकाळी ९ वाजल्यानंतर मी परिस्थितीचे मूल्यांकन करेन."

**Translation:** "Recorded. If hail occurs tomorrow, this message and your reply can be used for your PMFBY claim. I'll assess the situation after 9 AM."

**Constitutional basis:** C-023 (Evidence First — customer acknowledgment is a constitutional event for insurance chain), C-007 (Audit Ledger Immutability — PMFBY evidence cannot be altered after the fact) ✓

---

## Phase 4 — Bundled Morning Advisory (6:03 AM Thursday)

Signals 2 + 3 (pest outbreak + price drop) held since 11 PM, now delivered as a single bundled advisory.

**Agent (WhatsApp, 6:03 AM — Marathi text + voice):**

```
सुरेश दादा, आजच्या दोन महत्त्वाच्या गोष्टी:

🐛 कापूस अळी (गुलाबी बोंडअळी):
काटोल तालुक्यात ७ शेतांवर गुलाबी बोंडअळी दिसली
(Day 68-72 — तुमच्याच अवस्थेत).
आज सकाळी तुमच्या शेतावर एक नजर टाका:
- बोंडांवर छोटे छिद्रे दिसतात का?
- आतून गुलाबी अळी दिसते का?
जर दिसले: लगेच मला कळवा — मी फवारणी सल्ला देतो.

💰 कापसाचे भाव:
अकोला बाजारात भाव: ₹७,१०० → ₹६,६८० (२ दिवसांत ₹४२० घसरले)
तुमचा लक्ष्य भाव: ₹६,५०० — अजून ₹१८० बफर आहे.
सध्या विक्री नको. अजून ८-१२ दिवस वाट पाहणे योग्य.
पाऊस आणि बाजार स्थिरावला की भाव परत येऊ शकतो.

गारपीट स्थिती: आत्ता पहाटे ६ वाजले — अजून संधी आहे.
```

**Translation:**
"Suresh, two important things today:

🐛 Pink Bollworm: 7 farms in Katol district reported it at Day 68-72 (your stage). Check your field this morning: are there small holes in bolls? Pink larvae inside? If yes, contact me immediately — I'll advise on spraying.

💰 Cotton Prices: Akola market dropped ₹420 in 2 days (₹7,100 → ₹6,680). Your target: ₹6,500 — still ₹180 buffer. Don't sell yet. Wait 8-12 more days. Prices may recover once rains settle and market stabilises.

Hail situation: It's 6 AM now — still time to act."

Constitutional compliance: C-048 (Non-Exploitation — three WhatsApp messages at 11 PM is exploitative; bundling HIGH signals is the respectful approach) ✓

---

## Phase 5 — Post-Hail Assessment (9:15 AM)

Hail occurred from 6:45 AM to 7:50 AM (within predicted window). Suresh assesses damage.

**Suresh (WhatsApp, 9:20 AM):** "गारपीट झाली. बरीच बोंडे पडली. क्लेम कसा करायचा?"
**Translation:** "Hail happened. Many bolls fell. How do I file the claim?"

**Agent:**
"सुरेश दादा, मी PMFBY प्रक्रिया सुरू करतो.

कालची सगळी माहिती नोंदवलेली आहे:
✓ गारपीट इशारा पाठवला (रात्री ११:०२)
✓ तुम्ही पुष्टी दिली (रात्री ११:०७)
✓ हवामान डेटा: ७२% संभाव्यता, प्रत्यक्ष घटना ०६:४५-०७:५०

आता तुम्हाला करायचे आहे:
१. आज दुपारी: नुकसानीची फोटो काढा (सर्व बाजूंनी)
२. शेजारच्या शेतकऱ्यांना विचारा — ते साक्षीदार होतात
३. विमा कंपनीला ७२ तासांत कळवा (हे मी मदत करतो)

फोटो इथे पाठवा — मी तुमचा क्लेम फॉर्म भरायला मदत करतो."

**Translation:** "Suresh, I'm starting the PMFBY process. All evidence is recorded: ✓ Alert sent (11:02 PM), ✓ You confirmed (11:07 PM), ✓ Weather data: 72% probability, actual event 6:45-7:50 AM. Now: take photos today, ask neighbors as witnesses, notify insurance company within 72 hours (I'll help). Send photos here — I'll help fill your claim form."

Evidence chain complete:
- `PROACTIVE_SIGNAL_ALERT` (11:02 PM) ✓
- `PMFBY_SIGNAL_ACKNOWLEDGMENT` (11:07 PM) ✓
- `WEATHER_EVENT_CONFIRMED` (9:15 AM) ✓
- `PMFBY_CLAIM_INITIATED` (9:22 AM) → links all three records ✓

**Constitutional basis:** C-007 (Audit Ledger Immutability — each event is an immutable CAL record linked by `pmfby_chain_id`), C-023 (Evidence First — each step has a constitutional record) ✓

---

## Confidence Run Assessment

| Gap from Sim 009 | Resolution in v2.6 | Grade |
|---|---|---|
| GAP-A009: TRAI DND for CRITICAL signals | HSM UTILITY category approved in Meta BM; CRITICAL = DND override via utility message | ✅ RESOLVED |
| GAP-A010: Simultaneous multi-signal bombardment | Bundling rules: CRITICAL alone, HIGH bundled after 2 hours or at 6 AM | ✅ RESOLVED |
| GAP-A011: PMFBY evidence chain | "हो" reply creates `PMFBY_SIGNAL_ACKNOWLEDGMENT` record; full chain linked by `pmfby_chain_id` | ✅ RESOLVED |
| GAP-A012: Voice vs text delivery | Voice message (Marathi) for CRITICAL; text for confirmability/reply; both for HIGH bundled | ✅ RESOLVED |

**Quality grade: Grade A** — The agent operates as a professional agricultural advisor: proactive CRITICAL alert in the farmer's language at the right moment, respectful bundling that doesn't overwhelm, insurance evidence chain that actually helps the farmer (not just records for WAOOAW), honest price advice ("don't sell yet — ₹180 buffer").

**Constitutional highlight:** The "हो" reply → PMFBY evidence chain is the most important constitutional feature of this simulation. An agricultural advisor who tells a farmer about hail risk but doesn't help them claim insurance afterwards is incomplete. C-023 (Evidence First) + C-007 (Audit Ledger Immutability) together create an insurance evidence trail the farmer can actually use.
