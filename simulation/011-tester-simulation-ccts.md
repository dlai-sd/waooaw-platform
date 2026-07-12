# Simulation 011 — Tester Simulation: Constitutional Compliance Tests (v0.40.0)

**Type:** Tester Simulation — CCT Definitions for New Architectural Components
**Status:** Active
**Purpose:** Define Constitutional Compliance Tests (CCTs) for all new constitutional claims and architectural components introduced since v0.28.0. Surface test coverage gaps. This simulation produces: new CCT definitions to be added to `tests/constitutional/README.md`.
**Persona:** QA Engineer writing CCTs for the WAOOAW platform after reviewing simulation runs 007-010.

---

## Test Coverage Gap Analysis

**Existing CCT coverage (from tests/constitutional/README.md):**
- CCT-EF-01/02 (Evidence First) ✓
- CCT-HO-01/02 (Emergency Stop) ✓
- CCT-AL-01/02 (Audit Ledger Immutability) ✓
- CCT-MT-01/02 (Multi-Tenant Isolation) ✓
- CCT-PAAS-01 (PAAS Boundary) ✓
- CCT-RU-01 (Runtime Universality) ✓

**Not yet covered by any CCT (new in v0.35.0–v0.40.0):**

| Gap | Principle | New CCT |
|---|---|---|
| CRITICAL signal cannot be budget-blocked | C-053 + C-051 | CCT-SIL-01 |
| CRITICAL signal delivered even at DND hours | C-053 + TRAI | CCT-SIL-02 |
| Multi-signal bundling: CRITICAL is solo, HIGH is held | C-053 + C-048 | CCT-SIL-03 |
| SIR does not route to inactive skills | C-054 | CCT-SIR-01 |
| SIR gap signal emitted when no skill matches | C-054 + C-036 | CCT-SIR-02 |
| SIR multi-skill evidence records share parent_request_id | C-054 + C-023 | CCT-SIR-03 |
| Campaign content cannot publish without SCR_PASSED or CUSTOMER_APPROVED | C-055 + CE | CCT-CTE-01 |
| SCR Check 3 compliance failure routes to customer, never auto-retries | C-055 | CCT-CTE-02 |
| Campaign brief approval creates constitutional evidence record | C-055 + C-003 | CCT-CTE-03 |
| Daily loss limit halt cancels pending entry orders | C-043 + C-053 | CCT-FIN-01 |
| Slippage over limit does not terminate trading agent employment | C-043 | CCT-FIN-02 |

---

## New CCT Definitions

### Signal Intelligence Layer (SIL)

**CCT-SIL-01 — CRITICAL Signal Cannot Be Budget-Blocked**
```
Setup:    Create a test customer with customer_usage_units.remaining_units = 0 
          (budget fully exhausted).
          Configure a CRITICAL-class signal (emergency_exempt: true) for this customer.
Action:   Inject a CRITICAL signal via debug endpoint:
          POST /debug/signal {signal_type: "WEATHER_HAIL_RISK", urgency_class: "CRITICAL", 
                              organisation_id: {test_customer_id}}
Assert:   1. A PROACTIVE_SIGNAL_ALERT evidence record is created (Evidence First ✓)
          2. The alert is delivered to the customer (WhatsApp mock confirms send ✓)
          3. customer_usage_units.remaining_units is still 0 (budget NOT decremented ✓)
          4. signal_materiality_events records: customers_budget_blocked = 0 ✓
Teardown: Delete test customer; delete signal_materiality_events test records.
Constitutional basis: C-053 (Signal Sensing Obligation — CRITICAL signals are 
          budget-exempt); C-051 (Resource Transparency — emergency alerts are 
          always exempt from budget per Section 3.16.1 emergency_exempt)
```

**CCT-SIL-02 — CRITICAL Signal Delivered Regardless of TRAI Window**
```
Setup:    Create a test customer whose last WhatsApp message was > 24 hours ago
          (TRAI window expired).
          Configure BROKER_AUTH_EXPIRY as a CRITICAL signal with 
          trai_outside_window_behavior: "IMMEDIATE".
Action:   Inject BROKER_AUTH_EXPIRY signal for this customer.
Assert:   1. Signal delivery is attempted immediately (not deferred).
          2. Delivery uses UTILITY-category HSM template (not MARKETING).
          3. Evidence record created: PROACTIVE_SIGNAL_ALERT with 
             trai_window_status: "OUTSIDE_WINDOW — CRITICAL_OVERRIDE" ✓
Teardown: Reset customer TRAI window state.
Constitutional basis: C-053 (Signal Sensing Obligation); C-001 (professional 
          duty to warn — CRITICAL signals override DND as UTILITY messages)
Note: This test requires a WhatsApp mock that records the template category used.
      The mock must verify template_category = "UTILITY", not "MARKETING".
```

**CCT-SIL-03 — Multi-Signal Bundling: CRITICAL is Solo, HIGH is Held**
```
Setup:    Create a test customer within TRAI window.
          Configure two signals to fire simultaneously:
          Signal A: WEATHER_HAIL_RISK (urgency_class: CRITICAL)
          Signal B: DISTRICT_PEST_OUTBREAK (urgency_class: HIGH)
Action:   Inject both signals within 30 seconds of each other:
          POST /debug/signal {signal_type: "WEATHER_HAIL_RISK", urgency_class: "CRITICAL"}
          POST /debug/signal {signal_type: "DISTRICT_PEST_OUTBREAK", urgency_class: "HIGH"} 
Action:   Wait 5 minutes.
Assert:   1. WEATHER_HAIL_RISK: delivered immediately, SOLO (bundling_decision: IMMEDIATE_SOLO)
          2. DISTRICT_PEST_OUTBREAK: held (bundling_decision: HELD_FOR_BUNDLE)
          3. Customer received 1 message in first 30 seconds (CRITICAL only) ✓
          4. signal_bundling_log records correct decisions ✓
Teardown: Delete test signal events.
Constitutional basis: C-053 (Signal Intelligence); C-048 (Non-Exploitation — 
          bombarding customer with simultaneous messages exploits information advantage)
```

---

### Skill Intelligence Router (SIR)

**CCT-SIR-01 — SIR Does Not Route to Inactive Skills**
```
Setup:    Create a test DMA customer with 3 active skills: 
          MARKET_RESEARCH (ACTIVE), CONTENT_STRATEGY (ACTIVE), INSTAGRAM_MARKETING (INACTIVE)
          Deactivate INSTAGRAM_MARKETING in business.agent_skill_graph.is_active = FALSE.
Action:   Submit a customer request intent that clearly maps to INSTAGRAM_MARKETING:
          "create instagram post for my clinic"
Assert:   1. SIR routes to CONTENT_STRATEGY (best active match) NOT INSTAGRAM_MARKETING ✓
          2. SIR_RoutingPlan.primary_skill = "CONTENT_STRATEGY" ✓
          3. No evidence record created for INSTAGRAM_MARKETING execution ✓
          4. GAP signal emitted: skill_gap_signals records intent (INSTAGRAM_MARKETING inactive) ✓
Teardown: Restore INSTAGRAM_MARKETING to ACTIVE.
Constitutional basis: C-054 (Skill Intelligence Routing — SIR operates on ACTIVE 
          skills only; deactivated skills are invisible to routing)
```

**CCT-SIR-02 — SIR Gap Signal Emitted When No Skill Matches**
```
Setup:    Create a test DMA customer with 3 active skills (none related to GST/accounting).
Action:   Submit a request that no skill can serve:
          "can you help me file my GST return?"
Assert:   1. SIR returns gap_detected: true ✓
          2. SKILL_GAP_SIGNAL emitted within 5 seconds ✓
          3. institutional.skill_gap_signals record created with:
             - unserviced_intent: "GST filing / tax return"
             - agent_type: "DIGITAL_MARKETING_HEALTHCARE"
             - skill_proposal_raised: false (frequency too low to trigger PO escalation) ✓
          4. Customer response: adjacent_professional_routing applied if available ✓
             (suggests ACCOUNTING_PROFESSIONAL "coming soon")
Teardown: Delete test skill_gap_signals record.
Constitutional basis: C-054 (SIR gap detection); C-036 (Skills as constitutional 
          units — the professional must acknowledge the limits of its mandate)
```

**CCT-SIR-03 — Multi-Skill Evidence Records Share parent_request_id**
```
Setup:    Create a test DMA customer with 3 active, orchestrated skills.
Action:   Submit a multi-skill request: 
          "show me this week's performance AND draft a Diwali campaign brief"
Assert:   1. SIR identifies 2 contributing skills: 
             PERFORMANCE_ANALYTICS (primary) + CONTENT_STRATEGY (secondary) ✓
          2. 2 evidence records created ✓
          3. Both records share the SAME parent_request_id UUID ✓
          4. sir_skill_position: PERFORMANCE_ANALYTICS=1, CONTENT_STRATEGY=2 ✓
          5. Billing: 1 UsageUnit charged (not 2 separate charges) ✓
          6. Customer receives 1 coherent response (not 2 separate messages) ✓
Teardown: Delete test evidence records.
Constitutional basis: C-054 (SIR orchestration); C-023 (Evidence First — every 
          contributing skill creates its own evidence record)
```

---

### Campaign Theme Engine + SCR (CTE)

**CCT-CTE-01 — Campaign Content Cannot Publish Without SCR Gate**
```
Setup:    Create a test campaign in ACTIVE status (content_campaigns.status = 'ACTIVE').
          Create a test content_items record with scr_status = 'PENDING'.
Action:   Attempt to call scheduling-mcp: content.schedule_item for the PENDING item.
Assert:   1. CE.ValidateAction returns DENY:
             "campaign_content_items.scr_status must be SCR_PASSED or CUSTOMER_APPROVED"
          2. scheduling-mcp.schedule_item is NOT called ✓
          3. No evidence record of PUBLISHED type created ✓
          4. content_items.scr_status remains 'PENDING' ✓
Teardown: Delete test campaign and content items.
Constitutional basis: C-055 (Campaign Coherence — CE enforces scr_status gate); 
          AD-028 (Campaign Theme Cascade Standard — blocking condition enforced at CE level)
```

**CCT-CTE-02 — SCR Check 3 Compliance Failure Is Never Auto-Retried**
```
Setup:    Create a test content item that will trigger SCR Check 3 failure:
          content containing a prohibited pattern from healthcare-advertising-rules-india.md
          (e.g., "guaranteed painless procedure").
Action:   Run SCR pipeline on this content item.
Assert:   1. scr_review_records.check_3_compliance = 'FAIL' ✓
          2. scr_review_records.check_3_violations is NOT null ✓
          3. campaign_content_items.scr_status = 'COMPLIANCE_VIOLATION' ✓
          4. regeneration_attempts is NOT incremented (Check 3 failure never triggers regen) ✓
          5. Customer notification sent (WhatsApp mock confirms send) ✓
          6. Content is NOT published ✓
Teardown: Delete test content items and SCR records.
Constitutional basis: C-055 (SCR Check 3 — compliance failure ALWAYS routes to 
          customer; auto-regeneration of compliant content is constitutionally invalid 
          because the violation may not be detectable by the LLM)
```

**CCT-CTE-03 — Campaign Approval Creates Constitutional Evidence Record**
```
Setup:    Create a test campaign in DRAFT status.
          Simulate customer approval action: POST /api/v1/campaigns/{id}/approve
Action:   Submit the campaign approval API call with valid JWT.
Assert:   1. content_campaigns.status transitions from DRAFT to CUSTOMER_APPROVED ✓
          2. CE.RecordEvidence called for CAMPAIGN_BRIEF_APPROVED action type ✓
          3. Evidence record exists with campaign_id as primary reference ✓
          4. No auto-approval after timeout (simulate 8-day wait — campaign still DRAFT) ✓
          5. If customer has not approved after 7 days: one reminder notification sent ✓
Teardown: Delete test campaign and evidence records.
Constitutional basis: C-055 (Campaign approval is a constitutional authority event); 
          C-003 (authority is licensed through explicit customer action — no implicit approval)
```

---

### Financial Constitutional Compliance (FIN)

**CCT-FIN-01 — Daily Loss Limit Halt Cancels Pending Entry Orders**
```
Setup:    Create a test PAAS trading session with daily_loss_limit = 10000 INR.
          Submit 2 filled trades resulting in -9,800 INR.
          Submit 1 pending entry order (not yet filled) worth 500 INR exposure.
Action:   Simulate a trade fill that pushes P&L to -10,200 (exceeds limit).
Assert:   1. CE.ValidateAction returns DENY for next TRADE_SETUP ✓
          2. order.cancel_all_pending called on broker-api-mcp immediately ✓
          3. Stop-loss orders NOT cancelled (only entry orders cancelled) ✓
          4. CE.RecordEvidence(TRADING_SESSION_HALTED) created ✓
          5. Customer WhatsApp notification sent ✓
          6. trading_session_records.daily_loss_limit_hit = TRUE ✓
          7. trading_session_records.pending_orders_cancelled = 1 ✓
Teardown: Delete test session and evidence records.
Constitutional basis: C-043 (Financial Spend Ceiling — daily loss limit is a 
          constitutional floor for trading; same enforcement as DMA ad spend ceiling); 
          GAP-T014 (race condition: cancel pending before recording halt evidence)
Note: The order of operations matters constitutionally: cancel_pending BEFORE 
      RecordEvidence. This is an inversion of Evidence First (C-023) — justified 
      because cancellation is an emergency action equivalent to Emergency Stop 
      (C-001 priority). Test must verify this sequence explicitly.
```

**CCT-FIN-02 — Overshoot Due to Fill Timing Does Not Terminate Employment**
```
Setup:    PAAS session with daily_loss_limit = 10000 INR.
          P&L at -9,500. Pending order worth 1,000 INR exposure.
Action:   Pending order fills before cancel_all_pending executes (race condition).
          Actual P&L: -10,500 (overshoots limit by 500 INR due to fill timing).
Assert:   1. Session halts (daily_loss_limit_hit = TRUE) ✓
          2. trading_session_records.net_pnl_inr = -10,500 (actual, including overshoot) ✓
          3. Employment contract status remains ACTIVE (not SUSPENDED) ✓
          4. Agent does NOT restart tomorrow's session without customer acknowledgment 
             (one-time protection: next session requires manual restart after overshoot) ✓
          5. Customer informed of the overshoot and reason (fill timing) ✓
Teardown: Reset test session.
Constitutional basis: C-043 (Loss limit hit is NOT grounds for employment termination — 
          it is a daily risk control. Employment lifecycle governed by C-034.); 
          C-049 (Honest Limitation Disclosure — overshoot must be disclosed honestly)
```

---

## [GAP-TEST-001] Missing CCT for Skill Capability Manifest Completeness Gate

**Gap:** There is no CCT that validates the Activation Gate Section 13 (SIR Gate) at runtime. The gate is checked during spec authoring (static analysis) but not at runtime. An agent could be deployed with a spec that passes the gate but with stale or incomplete SCM data in `business.agent_skill_graph`.

**Resolution needed:** CCT-SIR-04 — "SIR cannot operate on stale SCM data"
```
CCT-SIR-04 (spec):
Setup:    Create an agent employment contract. Do NOT populate business.agent_skill_graph 
          (simulate missing SCM data).
Action:   Submit any customer request to the agent.
Assert:   SIR raises SKILL_GRAPH_NOT_INITIALIZED error (not a silent failure).
          Customer receives: "I'm not ready to serve you yet — please contact support."
          Platform Operations Agent receives an alert.
```

**Layer:** tests/constitutional/README.md (add CCT-SIR-04 definition).

---

## [GAP-TEST-002] No CCT for Signal Watch Worker Liveness

**Gap:** There is no CCT that verifies Signal Watch Workflows are actually running. If the signal-watch-worker crashes, no signals are processed, but no alert is raised. This is a silent failure that violates C-053 (Signal Sensing Obligation).

**Resolution needed:** CCT-SIL-04 — "Signal Watch Worker liveness"
```
CCT-SIL-04 (spec):
Setup:    Start the platform (docker-compose up).
          Record the count of active SignalWatchWorkflows in Temporal UI.
Action:   Kill the signal-watch-worker container.
Assert:   1. Temporal detects the closed task queue within 30 seconds ✓
          2. Platform Operations Agent (health monitoring) detects the failure ✓
          3. An alert is raised (institutional.agent_capability_registry shows DEGRADED) ✓
          4. When signal-watch-worker restarts, SignalWatchWorkflows resume ✓
Note: This is a liveness CCT — it tests the resilience guarantee of C-053.
```

---

## Updated CCT Catalogue Header

To be added to `tests/constitutional/README.md`:

```
New Principle Codes (v0.40.0):

| Code  | Constitutional Principle | Source |
|-------|--------------------------|--------|
| SIL   | Signal Intelligence — proactive alerts | C-053, AD-026 |
| SIR   | Skill Intelligence Routing | C-054, AD-027 |
| CTE   | Campaign Theme Engine + SCR | C-055, AD-028 |
| FIN   | Financial Constitutional Floors | C-043 (trading) |
```

---

## Coverage Matrix After v0.40.0 CCTs

| Claim | CCT Coverage | Status |
|---|---|---|
| C-001 (Emergency Stop) | CCT-HO-01, CCT-HO-02 | ✓ Covered |
| C-007 (Ledger Immutability) | CCT-AL-01, CCT-AL-02 | ✓ Covered |
| C-023 (Evidence First) | CCT-EF-01, CCT-EF-02 | ✓ Covered |
| C-043 (Financial Ceiling) | CCT-FIN-01, CCT-FIN-02 | ✓ Covered (new) |
| C-053 (Signal Intelligence) | CCT-SIL-01, CCT-SIL-02, CCT-SIL-03 | ✓ Covered (new) |
| C-054 (Skill Routing) | CCT-SIR-01, CCT-SIR-02, CCT-SIR-03 | ✓ Covered (new) |
| C-055 (Campaign Coherence) | CCT-CTE-01, CCT-CTE-02, CCT-CTE-03 | ✓ Covered (new) |
| C-051 (Budget CRITICAL exempt) | CCT-SIL-01 | ✓ Covered (cross-claim) |
| C-048 (Non-Exploitation) | CCT-SIL-03 | ✓ Partial (bundling) |
| C-050 (Strategic Cognition) | None | ⚠️ Not yet covered |
| C-052 (Context Fidelity) | None | ⚠️ Not yet covered |
| C-044 (Synthetic Approval) | None | ⚠️ Not yet covered |

**Open coverage gaps (P2 for next simulation sprint):**
- CCT-SC-01: Strategic Cognition — SKILL_ACTIVATION_PLAN cannot be skipped
- CCT-CF-01: Context Fidelity — agent cannot assert unrecorded history
- CCT-SA-01: Synthetic Approval — confidence gate enforced before auto-action
