# WAOOAW Goal Backlog Register

**Authority:** Goal Orchestrator (INST-013) — maintained per GEOM §G-2
**Last Updated:** 2026-07-30
**Status:** Living document — updated at each Goal registration or session close

---

## Purpose

This register is the single view of all Goals in the WAOOAW ecosystem —
formalized Goals (numbered, with Understanding Records), backlog Goals
(identified, not yet formalized), and closed Goals (evidence committed to
Constitutional Audit Ledger).

A Goal enters this register when the Founder articulates a desired outcome.
A Goal receives a number when the Goal Orchestrator produces a Goal
Understanding Record and the Founder acknowledges the Execution Plan.

---

## Formalized Goals

| Goal ID | Statement | Status | Sprint(s) | Closed |
|---|---|---|---|---|
| GOAL-001 | Semantic Brain Transformation — transform WAOOAW into a Goal-driven semantic brain capable of outcome-based dialogue and execution | CLOSED | — | 2026-07-27 |
| GOAL-002 | Universal AI Execution Layer — implement MagicLLM + GoalExecutor as the universal AI intelligence substrate for all autonomous sprint execution | CLOSED | — | 2026-07-27 |
| GOAL-003 | PTR Dynamic Knowledge Asset — replace static JSON context with a live, multi-stack Prompt Template Repository assembled from source files | CLOSED | — | 2026-07-27 |
| GOAL-004 | WAOOAW Billing Engine | **SPEC COMPLETE** — implementation WBE-S1→WBE-S8 awaiting Founder authorization | WBE-S1→WBE-S8 (est.) | — |

---

## Backlog — Identified, Not Yet Formalized

Backlog Goals are outcomes the Founder has articulated and the Goal Orchestrator
has captured in exploratory discussion. They do not yet have a Goal Understanding
Record. They carry no sequence number until formalized.

---

### GOAL-AGENCY — Multi-Tier Agency and Reseller Billing Extension

**Registrant:** Yogesh Khandge (Founder)
**Registered:** 2026-07-30
**Prerequisite:** GOAL-004 (Billing Engine core must exist before agency models are layered on)

**Desired Outcome:**
Enable WAOOAW to serve digital marketing agencies and resellers under four
billing models, each with its own money flow, margin structure, and customer
identity arrangement — without requiring code changes to the core Billing Engine.

**Business Aspiration:**
WAOOAW's DMA agent today serves individual business owners directly. The next
commercial frontier is onboarding agencies who manage 10–50 SMB clients each.
One agency relationship = 50 customers without direct sales effort. The platform
must support four distinct agency configurations:

```
Model A — Agency WITH own wallet, clients WITHOUT own ad account
  Agency deposits lump sum. WAOOAW runs campaigns on MBM for each client.
  Agency earns by marking up WAOOAW's subscription + management fees.
  WAOOAW revenue: subscription + 10% ad management fee per client.
  Complexity: per-child sub-wallet quotas, concentration risk management.

Model B — Agency WITH own wallet, clients WITH own ad account
  Agency pays WAOOAW subscription. Client's own Meta/Google card pays ad spend.
  WAOOAW earns subscription only — no management fee (money never routed).
  Revenue model: possibly add per-campaign flat fee to compensate for lost mgmt fee.

Model C — Agency WITHOUT own wallet, clients WITHOUT own ad account
  Three sub-models:
    C-1 Referral: Client pays WAOOAW directly. WAOOAW pays agency 15% commission.
    C-2 White-label: Agency resells under own brand at bulk/reseller rate.
    C-3 Revenue share: WAOOAW shares management fee split with agency.
  Complexity: white-label identity, GST invoice routing, commission payout system.

Model D — Agency WITHOUT own wallet, clients WITH own ad account
  Pure reseller / partner program.
  Agency earns partner commission. WAOOAW services client at reseller rate.
  Highest-scale model — lowest per-customer revenue, zero WAOOAW sales cost.
```

**Key Design Decisions Needed Before Formalization:**
1. Which models are in scope for GOAL-AGENCY MVP vs future iterations?
2. White-label identity: is the end client's Employment Contract with WAOOAW or the reseller? (Constitutional + legal implication — Ojal review required)
3. Commission payout architecture: monthly bank transfer? TDS implications?
4. Minimum commitment for agencies: quarterly or annual? (concentration risk mitigation)
5. Partner dashboard scope: what billing data does the agency see about their clients?

**Key Operational Scenarios Identified:**
- Agency wallet drained by one high-velocity child client (Scenario 16 — velocity anomaly)
- Agency/reseller churn: single event removes 50 clients (concentration risk)
- White-label client who wants to move to WAOOAW direct (portability question)
- Per-child spending quota enforcement in agency shared wallet
- Commission payout reconciliation at month end
- GST invoice routing: WAOOAW invoices agency; agency invoices clients separately
- Reseller pricing table: three price tiers for the same bundle (direct / agency / reseller)

**Margin Map (explored in brainstorming):**
```
Model A (VMP3):    ~₹1,663/client/month WAOOAW margin (83%)
Model B (VMP4):    ~₹749/client/month WAOOAW margin (75%) — least attractive
Model C white-label: ~₹1,464/client/month (81%) + zero sales cost
Model D reseller:  ~₹1,464/client/month (81%) + zero sales cost
Direct customer:   ~₹2,163/client/month (86%)
```

**The Franchise Analogy:**
WAOOAW = franchisor. Agency = franchisee type depends on model:
- Model A = master franchisee (holds the float, manages the outlets)
- Model B = management contractor (runs outlets, client owns the shop)
- Model C = private-label retailer (buys wholesale, sells under own brand)
- Model D = regional distributor (finds customers, earns referral)

**Constitutional Implications (flagged for CA review at formalization):**
- Employment Contract identity under white-label (who is the employer?)
- C-048 Non-Exploitation enforcement when agent operates under reseller brand
- C-049 Honest Limitation when customer thinks they are on "DigitalFirst AI Platform"
- TDS and GST compliance on commission payouts (Ojal — legal review)
- Concentration risk: single agency default = mass customer impact

**Inputs Required at Formalization:**
- GOAL-004 completed (Billing Engine, Thread Catalog, Agent Billing Profiles exist)
- Founder decision on white-label identity (legal review first)
- Ojal sign-off on constitutional obligations under white-label
- Legal counsel input on commission structure and TDS treatment

**Estimated Scope:** Large — deserves its own multi-sprint Goal with CA review before
EA begins architecture. Not suitable for single sprint delivery.

---

## Backlog Grooming Notes

```
2026-07-30 (Goal Orchestrator — INST-013):
  GOAL-AGENCY registered from Founder brainstorming session.
  Prerequisite dependency on GOAL-004 confirmed.
  Constitutional review flags raised for formalization.
  Founder to decide on scope boundaries before this Goal is formalized.

  GOAL-004 objectives confirmed by Founder. Goal Understanding Record produced.
  10 Success Criteria confirmed. Spec phase deliverables D-01 through D-10 specified.
  GO Authorizations issued to INST-002, INST-003, INST-004, INST-005, INST-006,
  INST-013, INST-010. GOAL-004 status: PLANNED — awaiting spec phase execution.
  Full Goal document: goals/GOAL-004-waooaw-billing-engine.md
```

---

*Archive: All closed Goal evidence is in `goals/GOAL-00N-*.md` + `goals/goal_register.jsonl`*
*This register is updated by Goal Orchestrator at each session close.*
