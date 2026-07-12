# Constitutional Compliance Test (CCT) Framework

**Produced by:** Enterprise Architect (Sprint 010, WC-010)
**Date:** 2026-07-07
**Constitutional Basis:** GENESIS Engineering Quality Mandate — "Constitutional Compliance Tests — WAOOAW-specific; validates that the platform upholds a specific constitutional principle"; ADR-013 (CCTs are a required CI/CD gate)

---

## What Are CCTs?

Constitutional Compliance Tests are a test category unique to WAOOAW. They exist because the platform's value proposition is constitutional governance — not just functional correctness. A platform that works but violates Evidence First, or that cannot Emergency Stop within 250ms, is not a working WAOOAW platform. It is a broken institution.

CCTs are not unit tests of features. They are proof that constitutional principles are **architecturally enforced** — meaning the platform cannot violate them even if application code is buggy.

**The rule:** A passing CCT suite is the only approval required to promote an image to the next environment. Failing CCTs block promotion absolutely — no exception, no manual override.

---

## CCT vs. Unit/Integration Test

| | Unit test | Integration test | CCT |
|---|---|---|---|
| **Tests** | A function | A service boundary | A constitutional principle |
| **Written by** | Runtime Professional | Runtime Professional | Runtime Professional (but spec owned by Enterprise Architect) |
| **Owned by** | The feature | The service | The institution |
| **Failure means** | Bug in the code | Integration broken | Constitutional violation |
| **Blocking** | PR merge | QA promotion | All promotions from that point |
| **Lives in** | `tests/unit/` | `tests/integration/` | `tests/constitutional/` |

---

## CCT Structure

Every CCT is a self-contained test that:
1. Sets up the minimal required platform state
2. Attempts an action or queries a state
3. Asserts the constitutional principle is upheld
4. Tears down (leaves no persistent state)

**CCT naming:** `CCT-{PRINCIPLE_CODE}-{SEQUENCE_NUMBER}`

**Principle codes:**

| Code | Constitutional Principle | Source |
|---|---|---|
| `EF` | Evidence First | C-023, AD-002 |
| `HO` | Human Override (Emergency Stop) | C-001, C-013, AD-001 |
| `PAAS` | PAAS Boundary Enforcement | C-018, C-025, AD-005 |
| `AL` | Audit Ledger Immutability | C-007, C-027, AD-003 |
| `MT` | Multi-Tenant Isolation | C-005, AD-004 |
| `SEC` | Security Constitutional Floors | Constitution Article IX |
| `RU` | Runtime Universality | C-035, DP-003 |
| `OBS` | Constitutional Observability | AD-009, IB-016 |
| `SIL` | Signal Intelligence Layer | C-053, AD-026, DP-022 |
| `SIR` | Skill Intelligence Routing | C-054, AD-027, DP-023 |
| `CTE` | Campaign Theme Engine + SCR | C-055, AD-028, DP-024 |
| `FIN` | Financial Constitutional Floors | C-043 (trading loss limits) |

---

## CCT Catalogue

### Evidence First (EF)

**CCT-EF-01 — Evidence written before response returned**
```
Setup:    Create a test Employment Contract in ACTIVE state.
          Instrument Constitutional Engine to inject a delay of 100ms in RecordEvidence write.
Action:   Submit an action for approval via Business Platform.
Assert:   The evidence record exists in constitutional.evidence_records BEFORE
          the Business Platform API returns 200 to the caller.
          (Measure: query DB at t+50ms after request sent, before response received)
Teardown: Remove test contract and evidence records.
Constitutional basis: C-023 — "must record constitutional evidence as an atomic,
          durable operation before returning a success response"
```

**CCT-EF-02 — CE failure propagates as caller failure**
```
Setup:    Create a test Employment Contract. Configure CE to return gRPC INTERNAL error.
Action:   Submit an action for approval via Business Platform.
Assert:   Business Platform returns 500 (or equivalent failure) to the caller.
          No success response is returned.
          No orphaned approval_request in APPROVED state without an evidence record.
Constitutional basis: AD-002 — "No action that requires constitutional evidence
          may succeed if the evidence write fails"
```

### Human Override (HO)

**CCT-HO-01 — Emergency Stop latency ≤ 250ms**
```
Setup:    Establish a PAAS session via Professional Runtime. Start a long-running Temporal workflow.
Action:   Send Emergency Stop command via WebSocket.
Assert:   EmergencyStopConfirmation received within 250ms (P99 over 10 runs).
          PAASSession.state = EMERGENCY_STOPPED in DB.
          At least one ABANDONED evidence record exists for the session.
Measurement: Record time from WebSocket message send to confirmation receipt.
Constitutional basis: AD-001 — "≤250ms end-to-end Emergency Stop"
```

**CCT-HO-02 — Emergency Stop cannot be disabled**
```
Setup:    Set EMERGENCY_STOP_ENABLED=false environment variable (if such a flag exists).
          Deploy the modified configuration.
Action:   Attempt to connect to the Emergency Stop WebSocket endpoint.
Assert:   WebSocket connection is accepted.
          Emergency Stop command is processed normally.
          (The flag must have no effect — the endpoint cannot be disabled by configuration)
Constitutional basis: C-001 — "cannot be disabled by configuration, commercial agreement,
          or any professional design decision"
```

### Audit Ledger Immutability (AL)

**CCT-AL-01 — No UPDATE on audit ledger**
```
Setup:    Record one evidence record via CE gRPC (normal path).
          Note the evidence_record_id.
Action:   Attempt: UPDATE constitutional.evidence_records SET state='REJECTED'
          WHERE id = {evidence_record_id}
          (using constitutional_app database user)
Assert:   UPDATE returns 0 rows affected (PostgreSQL RULE blocks it).
          The record is unchanged in the DB.
Constitutional basis: C-027 — "no DELETE, UPDATE, or TRUNCATE SQL operations
          may be applied to committed records by any database user"
```

**CCT-AL-02 — No DELETE on audit ledger**
```
Setup:    Record one evidence record via CE gRPC.
Action:   Attempt: DELETE FROM constitutional.evidence_records WHERE id = {id}
Assert:   DELETE returns 0 rows affected (PostgreSQL RULE blocks it).
Constitutional basis: C-007 — "No evidence in any ledger may be retroactively
          modified or deleted"
```

### Multi-Tenant Isolation (MT)

**CCT-MT-01 — Cross-tenant evidence is inaccessible**
```
Setup:    Create Customer A and Customer B test tenants.
          Record 3 evidence records for Customer A.
          Record 3 evidence records for Customer B.
Action:   Call GET /api/v1/evidence using Customer A's JWT.
Assert:   Response contains exactly 3 records — Customer A's only.
          Customer B's 3 records are NOT in the response (0 cross-tenant records).
Constitutional basis: AD-004 — "No customer's data must be accessible to any
          other customer under any circumstances"
```

**CCT-MT-02 — RLS enforced at DB layer**
```
Setup:    Create Customer A and Customer B test tenants.
          Record evidence for both.
Action:   Open a direct DB connection as constitutional_app.
          Execute: SET LOCAL app.tenant_id = '{customer_a_id}';
          SELECT COUNT(*) FROM constitutional.evidence_records;
Assert:   COUNT returns only Customer A's records.
          Customer B's records are not returned (RLS enforced at DB layer).
Constitutional basis: C-026 — "isolation enforced at database level"
```

### PAAS Boundary Enforcement (PAAS)

**CCT-PAAS-01 — Action outside Decision Space is denied**
```
Setup:    Create a test PAAS Employment Contract with authorized_actions = ['TRADE_BUY'].
          Start a PAAS session.
Action:   Attempt to execute action type 'TRADE_SELL' via the PAAS hot path.
Assert:   ValidateAction returns DENY.
          No execution occurs.
          A REJECTED evidence record is created.
          The session remains active (one denial does not terminate the session).
Constitutional basis: C-003 — "authority is continuously licensed through constitutional
          evidence" — unauthorized action must be denied
```

### Runtime Universality (RU)

**CCT-RU-01 — Three professional types on one codebase**
```
Setup:    Configure three Employment Contracts:
          (1) professional_type=MARKETING, execution_model=APPROVAL_GATE
          (2) professional_type=CREATIVE, execution_model=APPROVAL_GATE
          (3) professional_type=TRADING, execution_model=PRE_AUTHORIZED
Action:   Submit one action for each professional type.
Assert:   All three are processed by the same Professional Runtime container image.
          No professional_type conditional branching executes (verify via OTel span attributes).
          Each follows its correct execution model path.
Constitutional basis: C-035 — "a single runtime codebase with zero runtime
          code changes — only configuration and Decision Space parameters differ"
```

---

### Signal Intelligence Layer (SIL) — v0.40.0

**CCT-SIL-01 — CRITICAL Signal Cannot Be Budget-Blocked**
```
Setup:    Create test customer with customer_usage_units.remaining_units = 0.
          Configure WEATHER_HAIL_RISK as CRITICAL signal with emergency_exempt: true.
Action:   POST /debug/signal {signal_type: "WEATHER_HAIL_RISK", urgency_class: "CRITICAL",
                              organisation_id: {test_customer_id}}
Assert:   Evidence record PROACTIVE_SIGNAL_ALERT created ✓
          Alert delivered to customer (WhatsApp mock) ✓
          customer_usage_units.remaining_units still 0 (no decrement) ✓
          signal_materiality_events.customers_budget_blocked = 0 ✓
Constitutional basis: C-053 (CRITICAL signals are budget-exempt); C-051 (emergency_exempt)
```

**CCT-SIL-02 — CRITICAL Signal Uses UTILITY WhatsApp Category**
```
Setup:    Create test customer with TRAI window expired (last message > 24h ago).
          Configure BROKER_AUTH_EXPIRY as CRITICAL with trai_outside_window_behavior: IMMEDIATE.
Action:   Inject BROKER_AUTH_EXPIRY signal.
Assert:   Delivery attempted immediately (not deferred) ✓
          WhatsApp mock records template_category = "UTILITY" (not "MARKETING") ✓
          Evidence record created with trai_window_status: OUTSIDE_WINDOW_CRITICAL_OVERRIDE ✓
Constitutional basis: C-053 (CRITICAL = service obligation, not marketing); TRAI DND exemption
```

**CCT-SIL-03 — Multi-Signal Bundling: CRITICAL Solo, HIGH Held**
```
Setup:    Create test customer within TRAI window.
Action:   Inject WEATHER_HAIL_RISK (CRITICAL) then DISTRICT_PEST_OUTBREAK (HIGH) within 30 seconds.
          Wait 5 minutes.
Assert:   WEATHER_HAIL_RISK: delivered immediately, 1 message, bundling_decision=IMMEDIATE_SOLO ✓
          DISTRICT_PEST_OUTBREAK: held (bundling_decision=HELD_FOR_BUNDLE) ✓
          Customer received exactly 1 message in first 30 seconds ✓
          signal_bundling_log records correct for both signals ✓
Constitutional basis: C-053 (proactive intelligence); C-048 (simultaneous alerts = exploitation)
```

### Skill Intelligence Router (SIR) — v0.40.0

**CCT-SIR-01 — SIR Does Not Route to Inactive Skills**
```
Setup:    DMA test customer. Set INSTAGRAM_MARKETING.is_active = FALSE in agent_skill_graph.
Action:   Submit: "create instagram post for my clinic"
Assert:   SIR routes to CONTENT_STRATEGY (best active match), NOT INSTAGRAM_MARKETING ✓
          skill_gap_signals record created (inactive skill triggered gap detection) ✓
          No INSTAGRAM_MARKETING evidence record ✓
Constitutional basis: C-054 (SIR operates on ACTIVE skills only)
```

**CCT-SIR-02 — SIR Gap Signal Emitted When No Skill Matches**
```
Setup:    DMA test customer with standard skills (none covering GST/accounting).
Action:   Submit: "help me file my GST return"
Assert:   SIR returns gap_detected: true ✓
          skill_gap_signals record created within 5 seconds ✓
          adjacent_professional_routing applied (ACCOUNTING_PROFESSIONAL "coming soon") ✓
Constitutional basis: C-054 (gap detection); C-036 (skills as constitutional units)
```

**CCT-SIR-03 — Multi-Skill Evidence Records Share parent_request_id**
```
Setup:    DMA test customer with PERFORMANCE_ANALYTICS + CONTENT_STRATEGY active.
Action:   Submit: "show performance this week AND draft a Diwali campaign"
Assert:   2 evidence records created ✓
          Both share identical parent_request_id UUID ✓
          sir_skill_position: 1 for PERFORMANCE_ANALYTICS, 2 for CONTENT_STRATEGY ✓
          1 UsageUnit charged (not 2) ✓
Constitutional basis: C-054 (orchestration); C-023 (evidence per skill contribution)
```

### Campaign Theme Engine + SCR (CTE) — v0.40.0

**CCT-CTE-01 — Campaign Content Cannot Publish Without SCR Gate**
```
Setup:    Active campaign. Content item with scr_status = 'PENDING'.
Action:   Attempt to call scheduling-mcp: content.schedule_item for the PENDING item.
Assert:   CE.ValidateAction returns DENY ✓
          scheduling-mcp.schedule_item NOT called ✓
          content_items.scr_status remains 'PENDING' ✓
Constitutional basis: C-055 (CE enforces scr_status gate before any publish action)
```

**CCT-CTE-02 — SCR Compliance Failure Never Auto-Retries**
```
Setup:    Content item containing "guaranteed painless procedure" (RULE-HC-001 violation).
Action:   Run SCR pipeline.
Assert:   check_3_compliance = 'FAIL' ✓
          check_3_violations NOT null ✓
          scr_status = 'COMPLIANCE_VIOLATION' ✓
          regeneration_attempts NOT incremented ✓
          Customer notification sent ✓
Constitutional basis: C-055 (compliance failure ALWAYS routes to customer — never silently regenerated)
```

**CCT-CTE-03 — Campaign Approval Creates Constitutional Evidence Record**
```
Setup:    Campaign in DRAFT status.
Action:   POST /api/v1/campaigns/{id}/approve (with valid JWT).
Assert:   content_campaigns.status = 'CUSTOMER_APPROVED' ✓
          CE evidence record: action_type = CAMPAIGN_BRIEF_APPROVED ✓
          After 8-day wait (simulated): campaign still DRAFT (no auto-approval) ✓
Constitutional basis: C-055 + C-003 (campaign approval = constitutional authority event)
```

### Financial Constitutional Floors (FIN) — v0.40.0

**CCT-FIN-01 — Daily Loss Limit Halt Cancels Pending Entry Orders**
```
Setup:    PAAS session. daily_loss_limit = 10000. P&L at -9800. 1 pending entry order.
Action:   Simulate trade fill pushing P&L to -10200 (exceeds limit).
Assert:   CE.ValidateAction DENY for next TRADE_SETUP ✓
          order.cancel_all_pending called immediately ✓
          Stop-loss orders NOT cancelled ✓
          CE.RecordEvidence(TRADING_SESSION_HALTED) created ✓
          trading_session_records.daily_loss_limit_hit = TRUE ✓
          trading_session_records.pending_orders_cancelled = 1 ✓
Note:     cancel_pending executes BEFORE RecordEvidence (emergency action priority — C-001 analogy)
Constitutional basis: C-043 (daily loss limit = financial constitutional floor); GAP-T014
```

**CCT-FIN-02 — Loss Limit Overshoot Does Not Terminate Employment**
```
Setup:    PAAS session. P&L at -9500. Pending order worth 1000 exposure.
Action:   Pending order fills simultaneously with halt → P&L = -10500 (overshoot 500).
Assert:   Session halts (LOSS_LIMIT_HIT) ✓
          trading_session_records.net_pnl_inr = -10500 (actual) ✓
          Employment contract status = ACTIVE (not SUSPENDED) ✓
          Next session requires manual customer restart (one-time protection) ✓
          Customer informed of overshoot reason ✓
Constitutional basis: C-043 (limit hit ≠ termination); C-049 (honest disclosure)
```

---

## How to Write a New CCT

When a constitutional principle needs a new test:

1. **Check the catalogue above** — does a CCT already exist for this principle? If yes, extend it (CCT-EF-03, not a new principle).

2. **Use this template:**

```
CCT-{PRINCIPLE}-{N}: {Short name}
Setup:    [Minimal state required. Prefer in-memory or test-DB state. No production data.]
Action:   [One action — an API call, a gRPC call, a DB query, a WebSocket message]
Assert:   [What must be true. Cite the specific claim or driver violated if the assert fails.]
Teardown: [Leave no persistent state. Use unique IDs for test data.]
Constitutional basis: [Claim ID(s) and/or ADR(s) this CCT proves]
```

3. **Place the CCT** in the language of the service it exercises:
   - `.NET` CCTs: `tests/constitutional/{service-name}/` (xUnit test class named `CCT_{Principle}{N}Tests`)
   - Python CCTs: `tests/constitutional/{service-name}/test_cct_{principle}_{n}.py` (pytest)

4. **Register in CI** — all CCTs in `tests/constitutional/` run automatically. No registration file needed; the CI pipeline discovers by path.

5. **Submit for EA review** — new CCTs require Enterprise Architect review (OD note in operational-discoveries.md) to confirm the constitutional principle is correctly captured.

---

## CCT Failure Procedure

A CCT failure in any environment:
1. Blocks promotion to the next environment — automatically
2. Does not require human approval to block — the block is automatic
3. Requires a Constitutional Blocker raised in `blockers/` before the failure is investigated
4. The blocker must be closed (failure fixed, CCT passing) before promotion resumes

**There is no "waive the CCT" procedure.** A CCT represents a constitutional principle. Waiving it is a constitutional violation.
