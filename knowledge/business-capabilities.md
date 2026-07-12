# Business Capability Map

**Produced by:** Chief Business Architect (Sprint 002 + v0.8.0 update)
**Date:** 2026-07-07 (updated 2026-07-08)
**Constitutional Basis:** GENESIS Part 01 (Acceptance Scenarios 001–004), Ratified Claims C-001 through C-039

---

## Reading this Map

Each capability is named in **Verb + Object** format.
Each capability cites the constitutional claim(s) or acceptance scenario(s) that demand it.
A capability exists because the institution must provide it — not because it would be useful to have.

**Capability trace codes:**
- `AS-001/002/003/004` = GENESIS Acceptance Scenario
- `C-NNN` = Ratified constitutional claim
- `ART-IX` = Constitution Article IX (Bill of Rights)

---

## Domain 1 — Hire Digital Professionals

*The institution must enable organizations to engage digital professionals under constitutional governance.*

---

### 1.1 Evaluate Professional Candidates

**Statement:** The institution must enable prospective customers to evaluate digital professional profiles — including authority boundaries, Constitutional Floors, and override rights — before forming an Employment Contract.

**Constitutional Basis:** C-009 (CP-001 — pre-employment rights visibility is a constitutional obligation); C-012 (empirical: Dr. Mehta's hiring was influenced by pre-contract rights display); AS-001, AS-002, AS-003

**Why this cannot be optional:** The Constitution grants Customer Rights from the moment of hiring. Informed consent at hiring requires rights to be visible before signing.

---

### 1.2 Configure Employment Terms

**Statement:** The institution must enable customers to configure the goals, budget constraints, review cadence, and initial authority level of a digital professional before the contract is formed.

**Constitutional Basis:** AS-001 (Dr. Mehta sets appointments goal, INR 5,000 budget, 30-day review requirement); AS-002 (Sana sets enquiry goal, platform limit); AS-003 (Rahul sets capital limit, daily loss limit, trading window); C-003 (authority licensing starts at hire)

---

### 1.3 Define Decision Space

**Statement:** The institution must enable customers to define the bounded space within which a digital professional is constitutionally authorized to exercise judgment — including what the professional may do, may not do, and must always ask before doing.

**Constitutional Basis:** C-030 (Decision Space is the architectural primitive); C-003 (authority is a license — the Decision Space IS the license boundary); C-011 (CP-003 — scope boundaries must be confirmed explicitly, therefore scope boundaries must be defined explicitly); AS-001, AS-002, AS-003

---

### 1.4 Form Employment Contract

**Statement:** The institution must produce a formal Employment Contract that records the agreed Decision Space, authority level, review cadence, override rights, and termination rights — signed by the customer.

**Constitutional Basis:** C-009 (CP-001 — Constitutional rights must be in the contract); C-034 (employment lifecycle — contract formation is the transition from Evaluation to Active); ART-IX (Customer Rights — right to know authority level of every hired professional)

---

### 1.5 Onboard Digital Professional

**Statement:** The institution must enable a digital professional to learn the customer's context — goals, prior work, brand vocabulary, and creative standards — before beginning active work.

**Constitutional Basis:** AS-001 (professional learns Dr. Mehta's patient demographics, existing channels); AS-002 (professional learns Sana's aesthetic voice — Creative Standard Profile); C-016 (Amendment A-005 — Creative Standard Profile is a constitutional document for creative professions); C-034 (Active state requires the professional to be ready to serve, not merely hired)

---

## Domain 2 — Govern Professional Work

*The institution must provide customers with continuous, constitutional oversight of professional activity.*

---

### 2.1 Review Proposed Actions

**Statement:** The institution must enable customers to review actions a digital professional proposes to take before authorizing execution — the shadow authority trial mechanism.

**Constitutional Basis:** C-010 (CP-002 — Proposed state is a first-class institutional concept); C-014 (shadow authority trial is natural customer behavior); C-013 (empirical: Dr. Mehta invented this independently); AS-001, AS-002

---

### 2.2 Approve or Reject Professional Actions

**Statement:** The institution must enable customers to approve or reject individual proposed actions, with the decision recorded in the Customer Evidence Ledger.

**Constitutional Basis:** C-010 (CP-002 — evidence states: Proposed → Awaiting Approval → Approved/Rejected → Executed); AS-001 (Dr. Mehta approves each post for 30 days); AS-002 (Sana approves captions before publishing); ART-IX (right to override any action)

---

### 2.3 Confirm Scope-Boundary Crossings

**Statement:** When a digital professional is asked to act at or beyond its licensed scope, the institution must present a distinct, explicit scope-boundary confirmation — not a standard approval — that names the boundary being crossed.

**Constitutional Basis:** C-011 (CP-003 — mandatory scope-boundary confirmation, constitutionally distinct from approval); C-028 (empirical: Dr. Mehta was asked about a pricing post, a boundary crossing); ART-IX (right to transparency)

---

### 2.4 Exercise Emergency Stop

**Statement:** The institution must enable customers to immediately halt all active and queued professional operations at any time, with a guaranteed end-to-end round-trip latency of ≤250ms in Pre-Authorized Action Space contexts.

**Constitutional Basis:** C-001 (human override is absolute and architecturally guaranteed); C-024 (≤250ms is the architectural guarantee for PAAS contexts); C-019 (empirical: deterministic latency is what makes PAAS constitutionally valid); AS-003 (Rahul must be able to halt trading at any moment)

**This capability is a Constitutional Floor. It may not be degraded for performance, cost, or any other reason.**

---

### 2.5 Monitor Professional Activity in Real Time

**Statement:** The institution must provide customers with real-time visibility into what their digital professional is doing — what has been proposed, approved, executed, and rejected — without requiring the customer to query a log.

**Constitutional Basis:** C-002 (trust earned through observable evidence — trust cannot be earned if evidence is not observable); ART-IX (right to full transparency of professional behavior); AS-001, AS-002, AS-003 (all acceptance scenarios include customer oversight dashboards)

---

### 2.6 Audit Evidence Ledger

**Statement:** The institution must enable customers to review a complete, immutable audit trail of all professional decisions and actions within their engagement, at any time.

**Constitutional Basis:** C-007 (no evidence deleted — the complete record always exists); C-005 (Customer Evidence Ledger owned by customer); ART-IX (right to audit Customer Evidence Ledger completely and at any time)

---

## Domain 3 — Execute Professional Services

*The institution must execute professional services in two constitutional modes.*

---

### 3.1 Execute Approval-Gate Work

**Statement:** The institution must support a professional execution model where each significant action is proposed, reviewed by the customer, and executed only after explicit approval — for professions where human review latency is acceptable.

**Constitutional Basis:** C-010 (CP-002 — evidence state machine); C-011 (CP-003 — scope-boundary confirmation); AS-001 (dental marketing — approvals meaningful within human timescales); AS-002 (beauty artist — customer reviews every caption)

---

### 3.2 Execute Pre-Authorized Work

**Statement:** The institution must support a professional execution model where the customer pre-defines a bounded Decision Space, the professional executes autonomously within that space at machine speed, and Emergency Stop provides the constitutional human override mechanism.

**Constitutional Basis:** C-018 (PAAS model is constitutionally correct for millisecond-scale professions); C-025 (PAAS is a first-class execution model); C-017 (empirical: standard approval model was constitutionally incoherent for trading); C-019 (empirical: Emergency Stop with deterministic latency makes PAAS constitutionally valid); AS-003 (Rahul's trading strategy requires machine-speed execution)

---

### 3.3 Manage Creative Standard Profile

**Statement:** For creative professions, the institution must maintain and enforce the customer's Creative Standard Profile as a constitutional document — including a governed calibration period, a governed amendment process, and enforcement on every professional action.

**Constitutional Basis:** C-016 (Amendment A-005 — Creative Standard Profile is a constitutional document); C-011 (scope-boundary confirmation applies to Creative Standard deviations); AS-002 (Sana's aesthetic voice is the service she sells)

---

## Domain 4 — Develop Professional Trust

*The institution must provide the mechanisms through which digital professionals earn expanded authority.*

---

### 4.1 Assess Professional Performance

**Statement:** The institution must enable customers to review KPI performance and professional behavior evidence at regular intervals, as the basis for authority expansion or restriction decisions.

**Constitutional Basis:** C-002 (trust earned through observable evidence — periodic assessment is the structured observation event); AS-001 (monthly KPI review); AS-002 (monthly performance review); AS-003 (daily performance review)

---

### 4.2 Expand Professional Authority

**Statement:** The institution must provide a governed process for expanding a digital professional's authority level — based on accumulated evidence of performance within the current authority level.

**Constitutional Basis:** C-003 (Second Law — authority is earned, not granted by confidence); C-002 (First Law — trust earned through evidence); ART-IX (customer right to know current authority level)

---

### 4.3 Restrict or Suspend Professional Authority

**Statement:** The institution must provide a governed process for restricting or suspending a digital professional's authority level — with evidence-based justification and the Right of Review for the professional.

**Constitutional Basis:** C-003 (authority license can be suspended); ART-IX (Platform right to suspend authority where evidence warrants); Article XII (Right of Review)

---

### 4.4 Renew Employment Contract

**Statement:** The institution must support contract renewal as a governed re-consent event — where the customer explicitly reviews authority levels, performance evidence, and constitutional rights before re-committing.

**Constitutional Basis:** AS-001, AS-002, AS-003 (all scenarios include renewal decisions); C-009 (CP-001 — rights must be visible at contract formation; same logic applies at renewal)

---

## Domain 5 — Close Professional Engagements

*The institution must provide constitutionally governed exits from employment relationships.*

---

### 5.1 Suspend Professional Employment

**Statement:** The institution must support temporary suspension of professional employment — pausing active work while preserving all accumulated evidence, Creative Standard Profiles, and relationship context — for later resumption.

**Constitutional Basis:** C-034 (Suspended state in employment lifecycle); AS-002 (Sana's business is seasonal — lean months require suspension not termination)

---

### 5.2 Terminate Professional Employment

**Statement:** The institution must support immediate, unconditional termination of a professional employment relationship at any time, with complete portability of the Customer Evidence Ledger.

**Constitutional Basis:** C-034 (Terminated state); ART-IX (Customer right to terminate any professional engagement immediately and without restriction); ART-IX (right to data portability)

---

### 5.3 Export Customer Evidence

**Statement:** Upon termination (or on demand), the institution must provide the customer with a complete, portable export of their Customer Evidence Ledger in a standard format.

**Constitutional Basis:** ART-IX (right to data portability); C-005 (Customer Evidence Ledger is owned by the customer); C-007 (immutability — export must be the complete record)

---

## Domain 6 — Operate the Platform

*The institution must operate the platform infrastructure that makes all other capabilities possible.*

---

### 6.1 Authenticate and Authorize Customers

**Statement:** The institution must authenticate every customer identity and authorize access to only their constitutionally permitted resources — across all access channels.

**Constitutional Basis:** C-006 (Doctrine of Institutional Independence — access must be authenticated to enforce the doctrine); C-026 (three-ledger separation at DB level requires authenticated identity); ART-IX (Customer rights are personal — they require authentication to enforce)

---

### 6.2 Isolate Tenant Data

**Statement:** The institution must guarantee that no customer's data is accessible to any other customer, at any layer of the platform — including the database layer.

**Constitutional Basis:** C-005 (Three-Ledger Model — ledgers must not be merged); C-026 (isolation enforced at DB level, not only application level); C-006 (Doctrine of Institutional Independence)

---

### 6.3 Record Constitutional Evidence

**Statement:** The institution must record a constitutional audit record for every permission decision, authority event, and constitutional boundary crossing — before returning success to the calling service.

**Constitutional Basis:** C-023 (Evidence First — Constitutional Engine records before returning success); C-027 (Constitutional Audit Ledger append-only); C-029 (scope-boundary crossing produces a distinct audit record type)

---

### 6.4 Observe Platform Health and Constitutional Compliance

**Statement:** The institution must provide operators with continuous, structured observability into both platform health (latency, errors, throughput) and constitutional compliance (Emergency Stop latency, PAAS boundary adherence, Evidence First enforcement).

**Constitutional Basis:** C-002 (trust earned through observable evidence — the institution must be as observable as the professionals it governs); ADR-009 (OpenTelemetry constitutional spans); C-024 (Emergency Stop latency is a Constitutional Floor — must be measured)

---

### 6.5 Bill Customers with Pro-Rata Precision

**Statement:** The institution must calculate and manage billing for professional engagements on a pro-rata basis — billing must stop at the moment of pause or termination, and resume at the moment of restart, with no minimum periods or penalties.

**Constitutional Basis:** C-038 (billing is the financial implementation of the customer's constitutional right to pause and terminate — C-038 LAW); AS-001 (INR 8,000–12,000/month constraint); AS-002 (INR 6,000–10,000/month constraint); ART-IX (right to terminate immediately without penalty)

---

## Domain 1 — Additional Capabilities (v0.8.0)

---

### 1.6 Browse Agent and Skill Catalogue

**Statement:** The institution must enable prospective customers to browse available Digital Professionals, their Skill catalogues, domain specializations, ratings, and prior customer feedback — before committing to a trial or subscription.

**Constitutional Basis:** C-009 (CP-001 — rights visibility before hiring); C-039 (conversational configuration must be discoverable naturally); AS-001 (Dr. Mehta chooses a dental-specialized marketing agent, not a generic one)

---

### 1.7 Configure Agent via Conversation

**Statement:** The institution must enable customers to configure an agent's goals, credentials, schedule, and Decision Space through natural language dialogue — the agent asks questions, the customer answers in business terms, and the agent derives its own constitutional configuration.

**Constitutional Basis:** C-039 (conversational configuration is a constitutional obligation); C-030 (Decision Space is configured by the customer — the configuration mechanism must not require technical literacy); AS-001 (Dr. Mehta says "post 3 times a week on Instagram and Facebook" not "authorized_actions[0].platform=INSTAGRAM")

---

### 1.8 Enroll in Trial Engagement

**Statement:** The institution must enable customers to begin a time-limited trial engagement (7 days) with full constitutional employment rights — Emergency Stop, Evidence First, data portability — and no billing commitment during the trial period.

**Constitutional Basis:** FR-002 (trial = full constitutional employment); C-038 (no billing during trial); C-001 (Emergency Stop from day one of trial); ART-IX (data portability from day one of trial)

---

## Domain 2 — Additional Capabilities (v0.8.0)

---

### 2.7 Monitor Skill Performance Against Business KPIs

**Statement:** The institution must enable customers to review each Skill's performance against its stated business KPIs — appointments booked, enquiries generated, risk-adjusted return — not against internal technical metrics.

**Constitutional Basis:** C-037 (performance is business outcomes, not technical metrics — C-037 LAW); C-036 (each Skill has its own performance evidence); AS-001 (appointment growth as KPI); AS-002 (booking rate as KPI); AS-003 (daily return, Sharpe ratio as KPIs)

---

## Domain 3 — Additional Capabilities (v0.8.0)

---

### 3.4 Self-Improve Skill Performance

**Statement:** The institution must enable each Skill to improve its own performance over time using feedback from prior execution — approved actions, rejected actions, customer corrections — within the bounds of WAOOAW's institutional learning model (FR-003).

**Constitutional Basis:** C-037 (failure to improve toward business KPIs is a constitutional obligation breach); FR-003 (learning that improves the Skill uses the customer's evidence as input but the derived model is WAOOAW IP); C-002 (trust earned through evidence — improvement is evidence of earned trust)

---

## Domain 4 — Additional Capabilities (v0.8.0)

---

### 4.5 Set and Update Skill Goals

**Statement:** The institution must enable customers to define, review, and update the specific business goals and scheduling parameters for each individual Skill — independently of other Skills in the same engagement.

**Constitutional Basis:** C-036 (each Skill has its own configuration and performance targets); C-039 (goal-setting must be achievable through conversation); AS-001 (Dr. Mehta sets frequency and goals per platform separately)

---

### 4.6 Earn Synthetic Approval Authority Through Preference Learning

**Statement:** The institution must enable a skill to progress from requiring explicit customer approval for every action to generating synthetic approvals from its learned preference model — as a structured, evidence-backed, customer-controlled escalation that activates only after demonstrated alignment, and that the customer can revoke at any time.

**Constitutional Basis:** C-044 (Synthetic Approval — LAW); C-002 (trust earned through evidence — synthetic authority is earned, not assumed); C-001 (human override unconditional — customer retains retrospective override throughout); C-003 (mode upgrade is a Decision Space amendment requiring customer authorization event); DP-015 (Synthetic Approval as learned delegation)

---

## Domain 5 — Additional Capabilities (v0.8.0)

---

### 5.4 Pause Individual Skill (Pro-Rata Billing)

**Statement:** The institution must enable customers to pause a single Skill within a professional engagement without suspending other Skills — with billing for the paused Skill stopping pro-rata from the moment of pause.

**Constitutional Basis:** C-036 (Skills are independently governable); C-038 (pro-rata billing on pause — C-038 LAW); AS-002 (Sana pauses Instagram in slow months without terminating the whole engagement)

---

### 5.5 Resume Paused Skill

**Statement:** The institution must enable customers to resume a previously paused Skill, restoring all prior configuration, Creative Standard Profile, and performance history — billing resumes pro-rata from the moment of resumption.

**Constitutional Basis:** C-036 (Skill identity and learning persist through pause — a paused Skill is not a terminated Skill); C-038 (billing resumes from moment of resumption)

---

## Domain 9 — Commercial and Marketplace (v0.8.0 — MVI-partial)

*The institution must enable sustainable commercial operations and marketplace discovery.*

---

### 9.1 Manage Subscription Lifecycle

**Statement:** The institution must enable customers to start, pause, resume, and terminate subscriptions — with automatic pro-rata billing at each lifecycle event.

**Constitutional Basis:** C-038 (pro-rata billing — C-038 LAW); C-034 (employment lifecycle governs the subscription lifecycle — they are the same event)

---

### 9.2 Provide Transparent Billing

**Statement:** The institution must provide customers with a complete, itemised, real-time view of their current and projected billing — per Skill, per agent, with pro-rata calculations visible.

**Constitutional Basis:** C-038 (billing transparency is the commercial expression of constitutional rights); ART-IX (right to information about costs of professional engagement)

---

---

## Domain 10 — Agricultural Advisory (v0.11.0 — AS-005)

*The institution must enable small and marginal farmers in India to receive expert agricultural advisory through their existing channels (WhatsApp voice) in their own language.*

*C-042 Vocabulary Mandate applies to all Domain 10 capabilities: no technical data is surfaced to the farmer. All outputs are actionable instructions in farmer's occupational vocabulary.*

---

### 10.1 Receive Hyperlocal Crop Weather Alerts

**Statement:** The institution must deliver weather-based crop risk alerts to the farmer in their language and vocabulary — not meteorological data — with 72-hour advance warning for adverse events, calibrated to the farmer's specific crop type, growth stage, and 10km farm radius.

**Constitutional Basis:** C-040 (domain specialization — agent must know crop-weather correlations, not just weather); C-042 (vocabulary mandate — never show humidity percentages, always show crop action); AS-005 (farmer receives actionable weather advisory); C-023 (every alert recorded in CAL for PMFBY evidence)

---

### 10.2 Monitor Crop Health via Conversational Check-in

**Statement:** The institution must enable the agent to proactively ask the farmer about their crop's current condition, interpret farmer observations through domain knowledge, and advise on interventions — maintaining a living Progressive Crop State Model across all conversations.

**Constitutional Basis:** C-039 (conversational interface is the primary interaction model — C-039 CONFIRMED); C-042 (vocabulary mandate); C-040 (domain specialization — agent must know crop disease symptoms from farmer's descriptions); AS-005

---

### 10.3 Get Mandi Price Intelligence and Sell Timing

**Statement:** The institution must inform farmers of current and trending mandi prices across their region, compare against MSP, and advise on optimal sell timing — in farmer's vocabulary (rupees per quintal, not indices).

**Constitutional Basis:** C-037 (business KPI primary — farmer's income, not price index data); C-042 (vocabulary mandate); AS-005 (farmer achieves better price than district average)

---

### 10.4 Plan Next Season Crop

**Statement:** The institution must recommend the optimal crop for the farmer's next season based on the convergence of weather outlook, mandi price trends, soil type, water availability, market saturation, government policy, and crop rotation — presenting the recommendation in farmer vocabulary with estimated income.

**Constitutional Basis:** C-039 (conversational planning — farmer approves crop choice); C-037 (business outcome: income per acre vs prior season); C-040 (domain knowledge required: soil-crop compatibility, ICAR data); AS-005

---

### 10.5 Receive Agricultural Hints

**Statement:** The institution must proactively share 1–2 forward-looking agricultural insights per week — synthesizing weather, price, market saturation, government policy, and bumper crop signals — framed as "things to keep in mind" in the farmer's language.

**Constitutional Basis:** C-040 (domain specialization — hints require multi-source agricultural intelligence); C-042 (vocabulary mandate); AS-005 (farmer makes better seasonal decisions with forward-looking context)

---

### 10.6 Generate PMFBY Insurance Evidence

**Statement:** The institution must automatically generate an insurance evidence chain in the Constitutional Audit Ledger — alert issued, farmer acknowledged, adverse weather confirmed — and produce a PMFBY claim report on the farmer's explicit request.

**Constitutional Basis:** C-023 (Evidence First — every alert and acknowledgment creates a CAL record); C-007 (immutability — evidence records cannot be altered); ART-IX (farmer's right to their own evidence records); AS-005 (PMFBY claim documentation)

---

## Domain 11 — Digital Marketing Professional (v0.14.0 — AS-001, AS-002)

*The institution must enable dental clinics, beauty artists, and other local service businesses in India to engage a digital marketing professional who builds their digital presence, drives customer acquisition, and improves their digital marketing maturity over time.*

*Phase bundles (Curtain Raiser / Growth Engine / Maturity Phase) gate capability activation based on the customer's Digital Marketing Maturity Score. Capabilities 11.1–11.2 are always active; 11.3–11.6 are phase-gated.*

---

### 11.1 Profile Customer and Identify Marketing Needs

**Statement:** The institution must enable the Digital Marketing Professional to conduct an AI-native consultative profiling conversation with a new customer — starting from the minimum registration data — to build a complete Customer Profile that identifies which of the 8 customer need states (visibility, leads, conversion, efficiency, competition, consistency, trust, clarity) are active, latent, or not applicable.

**Constitutional Basis:** C-039 (conversational configuration — profile completable through conversation in ≤ 15 minutes); C-036 (every Skill is independently governable — profile drives skill activation); AS-001 (Dr. Mehta's goals and context must be understood before any action is taken); AS-002 (Sana's aesthetic and brand must be captured at intake)

---

### 11.2 Assess Digital Marketing Maturity and Deliver Report

**Statement:** The institution must enable the Digital Marketing Professional to independently research a customer's digital presence using publicly available data, calculate a Digital Marketing Maturity Score (1–7) against a fixed scale with industry and geography benchmarks, and produce a Digital Marketing Maturity Report with a recommended Phase Bundle and 3-month plan — delivered once at engagement start and refreshed every 6 months.

**Constitutional Basis:** C-037 (business KPI primacy — maturity score is the primary outcome metric for this agent); C-040 (domain specialization — maturity assessment requires deep knowledge of digital marketing signals); C-041 (research tools must be authorized in Decision Space; all research must be public-data-only); C-043 (research cannot access authenticated external systems without explicit authorization); AS-001, AS-002

---

### 11.3 Execute Social Media and Content Marketing (Phase 1 — Curtain Raiser)

**Statement:** The institution must enable the Digital Marketing Professional to create and publish approved content across Instagram, Facebook, Google Business Profile, WhatsApp Business, and video channels — building a consistent digital presence that makes the customer discoverable and trustworthy to their target patients or clients.

**Constitutional Basis:** C-036 (each social platform is a separately configurable Skill); C-037 (KPI: consistent posting rate, Google Business views, follower growth); C-041 (each publishing action requires Decision Space authorization); AS-001 (Dr. Mehta's Instagram/WhatsApp/Google presence); AS-002 (Sana's Instagram portfolio and booking enquiries)

---

### 11.4 Improve Local Search Visibility and Reputation (Phase 2 — Growth Engine)

**Statement:** The institution must enable the Digital Marketing Professional to audit and improve the customer's local SEO signals — Google Business Profile optimisation, on-page SEO, keyword targeting, citation consistency — and manage online reputation through review response management, driving more patients or clients to discover the customer via search.

**Constitutional Basis:** C-037 (KPI: search impressions, local pack appearances, review rating); C-040 (domain specialization — local SEO for healthcare/beauty India requires specific knowledge); C-041 (website changes require explicit authorization per change); AS-001, AS-002

---

### 11.5 Run Paid Digital Advertising Within Approved Budget (Phase 2 — Growth Engine)

**Statement:** The institution must enable the Digital Marketing Professional to plan, launch, and optimise paid advertising campaigns on Meta (Facebook/Instagram Ads) and Google Ads — within the customer's explicitly approved monthly budget ceiling, which is a Constitutional Floor equivalent per C-043.

**Constitutional Basis:** C-043 (financial spend authority cap — budget ceiling is absolute); C-041 (PAID_AD_CAMPAIGN and PAID_AD_OPTIMISE require Decision Space authorization); C-037 (KPI: CPL, ROAS); AS-001 (dental clinic paid patient acquisition); AS-002 (beauty artist booking enquiry campaigns)

---

### 11.6 Optimise Digital Conversion and Monitor Competitors (Phase 3 — Maturity Phase)

**Statement:** The institution must enable the Digital Marketing Professional to analyse why website visitors or social media followers do not convert to bookings or enquiries — and recommend or execute approved landing page and funnel improvements — while monitoring the top 3 competitors' public digital activity and alerting the customer to significant competitive moves.

**Constitutional Basis:** C-037 (KPI: conversion rate, competitive gap score); C-041 (website changes and competitor monitoring require Decision Space authorization); C-040 (domain specialization — CRO for local healthcare India requires UX and funnel knowledge); competitive intelligence is customer-private (C-041: research tools are authorized but outputs may not be shared)

---

| Domain | Count | Capabilities |
|---|---|---|
| 1 — Hire | 8 | 1.1 Evaluate, 1.2 Configure, 1.3 Define Decision Space, 1.4 Form Contract, 1.5 Onboard, 1.6 Browse Catalogue, 1.7 Configure via Conversation, 1.8 Trial Enrollment |
| 2 — Govern | 7 | 2.1 Review Proposed, 2.2 Approve/Reject, 2.3 Confirm Boundary, 2.4 Emergency Stop, 2.5 Monitor, 2.6 Audit, 2.7 Monitor Skill KPIs |
| 3 — Execute | 4 | 3.1 Approval-Gate, 3.2 Pre-Authorized (PAAS), 3.3 Creative Standard, 3.4 Self-Improve |
| 4 — Develop | 5 | 4.1 Assess, 4.2 Expand Authority, 4.3 Restrict Authority, 4.4 Renew, 4.5 Set Skill Goals |
| 5 — Close | 5 | 5.1 Suspend, 5.2 Terminate, 5.3 Export Evidence, 5.4 Pause Skill, 5.5 Resume Skill |
| 6 — Operate | 5 | 6.1 Authenticate, 6.2 Isolate Tenant, 6.3 Record Evidence, 6.4 Observe, 6.5 Bill Pro-Rata |
| 7 — Customer Portal | 8 | (IB-014 design frame) |
| 8 — CS Agents | 6 | (IB-015 / FR-001 design frame) |
| 9 — Commercial | 2 | 9.1 Subscription Lifecycle, 9.2 Transparent Billing |
| **10 — Agricultural Advisory** | **6** | **10.1 Weather Alerts, 10.2 Crop Health Monitor, 10.3 Price Intelligence, 10.4 Crop Planning, 10.5 Hints, 10.6 PMFBY Evidence** |
| **Total** | **56+** | |

---

## Capabilities Not in Scope (MVI)

| Capability | Deferred to | Reason |
|---|---|---|
| Appeal Constitutional Decision | Epoch 5 | Requires functioning Constitutional Oversight mechanism |
| Certify Professional Identity Continuity | Epoch 6 | Requires multiple embodiment changes to observe |
| Enable Third-Party Integrations | Epoch 6 | Requires stable API and developer programme |
| Operate Professional Marketplace (public) | Epoch 7 | Requires sufficient professional inventory |
| Agent Teams — self-organizing | Post-MVI Enterprise | FR-004 — IB-018 |

---

## Domain 12 — Platform Operations (v0.20.0 — C-046)

*The institution must govern its own operations through constitutional agents. Every platform operation that affects a customer engagement must be performed by a constitutionally governed Platform Operations Agent with defined authority, evidence-recorded actions, and customer notification rights.*

---

### 12.1 Monitor Agent and Skill Health (L1)

**Statement:** The institution must continuously monitor the health of every active agent skill engagement — tracking inference quality, constitutional compliance rate, goal progress, API budget consumption, and delivery channel reliability — and autonomously resolve routine anomalies within the Platform Operations Agent's authorized action space.

**Constitutional Basis:** C-046 (Platform under constitutional governance); C-037 (KPI primacy — health monitoring exists to protect KPI achievement); AD-019 (agent-driven orchestration — health monitoring is itself an agent reasoning cycle)

---

### 12.2 Respond to Platform Incidents (L2)

**Statement:** The institution must respond to platform anomalies — degraded CE performance, failed Temporal workflows, payment processing failures, OAuth token expiry — through a constitutionally governed incident resolution cycle that diagnoses, proposes resolution, obtains required authorization, implements, and records evidence for every incident affecting a customer engagement.

**Constitutional Basis:** C-046; C-001 (customer override rights — customers must be notified of incidents affecting their engagements); C-023 (Evidence First — incident resolution is a constitutional action)

---

### 12.3 Audit Constitutional Compliance (L3)

**Statement:** The institution must periodically audit every active agent engagement against the constitutional corpus — verifying that Synthetic Approval confidence thresholds are being met, that evidence records are complete, that Decision Space boundaries have not drifted, and that prompt versions in use are approved. The audit produces a Constitutional Compliance Report delivered to the Founder and the relevant customer.

**Constitutional Basis:** C-046; C-044 (Synthetic Approval — requires confidence monitoring); C-045 (Prompt as Constitutional Artifact — requires prompt version audit); AD-008 (every permission decision must be auditable)

---

### 12.4 Generate Agent Reasoning Traces and Operational Intelligence

**Statement:** The institution must capture structured reasoning traces for every AI inference — recording the decision context, the reasoning chain, the constitutional basis invoked, the confidence score, and the outcome — in a queryable store that enables operational agents to detect patterns, quality degradations, and constitutional anomalies.

**Constitutional Basis:** C-046; C-047 (Agent-Driven Execution — the reasoning IS the primary output); AD-008 (constitutional auditability requires reasoning, not just outcome); C-002 (trust through evidence — reasoning traces are the deepest form of evidence)

---

### 12.5 Govern Prompt Lifecycle

**Statement:** The institution must manage the lifecycle of every AI prompt — versioning, review, approval, activation, and deprecation — ensuring that no unapproved prompt is ever executed by a production agent, and that every prompt change goes through the same governance process as a Decision Space amendment.

**Constitutional Basis:** C-045 (Prompt as Constitutional Artifact — LAW); AD-018 (Prompt Versioning); DP-016 (Prompt-First Execution)

---

### 12.6 Detect and Communicate Material Signals (Signal Intelligence Layer — v0.35.0)

**Statement:** The institution must continuously monitor external signal feeds (weather, market data, platform analytics, competitor activity) relevant to each active agent engagement, evaluate signal materiality against each customer's current state, and proactively communicate actionable alerts before the customer asks. CRITICAL-class signals (materiality ≥ 0.90) must be delivered regardless of customer budget balance. The institution may not possess a material signal affecting a customer's business outcome and withhold it.

**Constitutional Basis:** C-053 (Signal Sensing Obligation — LAW); C-001 (human override absolute — professional duty to warn before override is needed); C-048 (Information Non-Exploitation — possessing material information and not sharing it exploits information advantage against customer interests); AD-026 (Signal Watch Workflow Pattern); DP-022 (Proactive Intelligence Primacy)

---

### 12.7 Route Customer Requests to Correct Skill(s) (Skill Intelligence Router — v0.35.0)

**Statement:** The institution must ensure that every customer request or message directed at a multi-skill agent is intelligently routed to the correct active Skill(s) — using the Skill Capability Manifests of active skills to match customer intent at LOCAL-tier cost (≤10ms, ₹0). When a request spans multiple skills, the institution must orchestrate those skills in dependency order and present one coherent professional response. When no active skill can serve a request, the institution must emit a gap signal for the governance process.

**Constitutional Basis:** C-054 (Skill Intelligence Routing — LAW); C-036 (Skills as constitutional units — the professional deploys the right capability without being told which tool to use); C-050 (Strategic Cognition — SCM feeds the Skill Dependency Graph that C-050 reasons over); AD-027 (Skill Capability Manifest Standard); DP-023 (Skill Network Intelligence)
