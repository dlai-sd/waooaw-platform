# Architectural Drivers

**Produced by:** Chief Business Architect (Sprint 002 + v0.11.0 update)
**Date:** 2026-07-07 (updated 2026-07-08)
**Constitutional Basis:** Ratified Claims C-001 through C-035, GENESIS Part 01

---

## Reading this Document

Architectural Drivers are non-negotiable constraints that shape every significant engineering decision. They are not goals or aspirations — they are boundaries. An architecture that violates a driver is constitutionally non-compliant, not merely suboptimal.

Each driver states:
- **What it requires** — the measurable constraint
- **Why it exists** — the constitutional claim or GENESIS source
- **What it constrains** — the capabilities and architectural decisions it shapes
- **Hard or Soft** — Hard = constitutional floor, cannot be traded. Soft = important target, may be balanced against cost.

---

## AD-001 — Emergency Stop Latency

**Requirement:** End-to-end round-trip latency from customer-issued Emergency Stop command to confirmed halt of all active professional operations must not exceed **250ms** in Pre-Authorized Action Space (PAAS) execution contexts.

**Type:** HARD — Constitutional Floor. Cannot be traded for performance, cost, or any other consideration.

**Constitutional Basis:** C-001 (human override is absolute and architecturally guaranteed), C-024 (≤250ms architectural guarantee), C-019 (empirical: deterministic latency is what makes PAAS constitutionally valid), C-020 (absolute time guarantee required)

**Capabilities Constrained:** 2.4 (Exercise Emergency Stop), 3.2 (Execute Pre-Authorized Work)

**Architectural consequence:** Emergency Stop requires a dedicated, pre-warmed persistent connection (WebSocket). Cannot use HTTP request-response. Cannot share a connection with other traffic. The connection must be established at session start and maintained for the session duration.

---

## AD-002 — Evidence First Enforcement

**Requirement:** The Constitutional Engine must write the evidence record to the Constitutional Audit Ledger as an atomic, durable operation **before** returning a success response to any calling service. No action that requires constitutional evidence may succeed if the evidence write fails.

**Type:** HARD — Constitutional Floor derived from the First Law.

**Constitutional Basis:** C-002 (First Law — trust earned through observable evidence), C-023 (Evidence First architectural implication), C-007 (ledger immutability — evidence must persist)

**Capabilities Constrained:** 2.2 (Approve Actions), 2.3 (Confirm Scope Boundary), 3.1 (Execute Approval-Gate), 3.2 (Execute Pre-Authorized), 6.3 (Record Constitutional Evidence)

**Architectural consequence:** The Constitutional Engine must be called synchronously (not asynchronously) before any approval, execution, or authority event returns success. gRPC is the protocol (ADR-001). The calling service must treat a Constitutional Engine timeout as a failure, not a success.

---

## AD-003 — Audit Ledger Immutability

**Requirement:** No record in the Constitutional Audit Ledger may be modified or deleted after it is written. The ledger is append-only. This applies at the database layer — not merely at the application layer.

**Type:** HARD — Constitutional Floor.

**Constitutional Basis:** C-007 (no evidence deleted or modified — Constitutional Floor), C-027 (append-only at database level)

**Capabilities Constrained:** 6.3 (Record Constitutional Evidence), 2.6 (Audit Evidence Ledger)

**Architectural consequence:** The application service account for the Constitutional Engine must have INSERT and SELECT permissions on the constitutional schema — not UPDATE or DELETE. Database-level enforcement (triggers or permission restriction) is required. EF Core migrations must never include UPDATE or DELETE on the constitutional schema.

---

## AD-004 — Multi-Tenant Data Isolation

**Requirement:** No customer's data must be accessible to any other customer under any circumstances, at any layer of the platform, including the database layer.

**Type:** HARD — Constitutional Floor derived from Three-Ledger model.

**Constitutional Basis:** C-005 (Three-Ledger Model — ledgers owned by different stakeholders, never merged), C-026 (isolation enforced at database level), C-006 (Doctrine of Institutional Independence)

**Capabilities Constrained:** All capabilities in all domains. Isolation is a cross-cutting concern.

**Architectural consequence:** Row-Level Security policies on every tenant-scoped table in PostgreSQL, enforced via `SET LOCAL app.tenant_id` on every database session. `tenant_id` from JWT is the isolation anchor propagated through every layer.

---

## AD-005 — PAAS Execution Latency

**Requirement:** Total latency from PAAS execution trigger to evidence-recorded completion must support the 250ms Emergency Stop window. The PAAS execution path — including in-memory Decision Space validation — must complete in under 50ms to leave the remaining budget for network, Emergency Stop detection, and evidence recording.

**Type:** HARD — derives from AD-001.

**Constitutional Basis:** C-025 (PAAS is a first-class execution model requiring zero network calls in hot path), C-024 (≤250ms guarantee), C-018 (PAAS model required for millisecond-scale professions)

**Capabilities Constrained:** 3.2 (Execute Pre-Authorized Work)

**Architectural consequence:** PAAS execution hot path must have zero external network calls. Decision Space parameters are loaded into memory at session start. Validation is in-memory only. This is why session-affinity is required (ADR-005) — the in-memory state cannot be shared across replicas without introducing network calls.

**PAAS latency budget (approximate allocation for 250ms Constitutional Floor):**

| Segment | Budget | Notes |
|---|---|---|
| PAAS execution hot path (in-memory validation + AI inference) | <50ms | Zero network calls |
| Constitutional Engine evidence recording (gRPC + DB write) | <80ms | Synchronous, local network |
| Emergency Stop detection + SignalR routing | <50ms | Pre-warmed connection |
| Halt command processing + confirmation | <50ms | In-memory |
| Safety margin | ~20ms | |
| **Total** | **≤250ms** | **Constitutional Floor** |

Any architectural change that shifts the budget of one segment must be evaluated against this table to confirm the 250ms guarantee is still achievable.

---

## AD-006 — Cost Constraint (Non-Production Environments)

**Requirement:** Each non-production environment (dev, QA, demo, UAT) must not exceed **INR 10,000/month** in total cloud infrastructure cost.

**Type:** SOFT (for production) / HARD (for non-production per GENESIS mandate).

**Constitutional Basis:** GENESIS Part 01 — Cost Constraint ("INR 10,000/month per non-production environment is an Architectural Driver, not a guideline")

**Capabilities Constrained:** 6.1 through 6.5 (all platform operations) — this driver governs the infrastructure design for those capabilities

**Architectural consequence:** Scale-to-zero is required for all non-production services. No always-on QA infrastructure. Container Apps consumption model. Self-hosted Temporal in dev/QA (shared PostgreSQL). No API gateway at MVI. Dev/QA environments sized at minimum viable specifications.

---

## AD-007 — Runtime Universality

**Requirement:** All three Minimum Viable Institution professional scenarios (dental marketing, beauty artist, NIFTY trading) must execute on a single Professional Runtime codebase with zero runtime code changes. Professional differentiation is through Decision Space configuration only.

**Type:** HARD — GENESIS mandate, directly quoted as the Runtime Universality Test.

**Constitutional Basis:** C-035 (Runtime Universality — LAW), C-030 (Decision Space is the architectural primitive)

**Capabilities Constrained:** 1.3 (Define Decision Space), 3.1 (Execute Approval-Gate Work), 3.2 (Execute Pre-Authorized Work), 3.3 (Manage Creative Standard Profile)

**Architectural consequence:** The Professional Runtime must be completely generic. All professional-type-specific behavior — what actions are allowed, what approval flows apply, whether PAAS or approval-gate model is used — is expressed through the Decision Space configuration object, not through code. A `if professionalType == TRADING` conditional in the runtime is a constitutional violation of this driver.

---

## AD-008 — Constitutional Auditability

**Requirement:** Every permission decision, authority grant, authority restriction, scope-boundary crossing, and Emergency Stop event must produce a traceable record in the Constitutional Audit Ledger, naming the specific constitutional claim, precedent, or policy that authorized or denied the decision.

**Type:** HARD — Constitutional Floor.

**Constitutional Basis:** C-028 (Proposed state is a first-class enum), C-029 (scope-boundary confirmation is a distinct record type), Constitution Article XI ("no permission decision may be made without traceable constitutional justification")

**Capabilities Constrained:** 2.1–2.4 (all governance capabilities), 4.2–4.3 (authority expansion and restriction), 6.3 (Record Constitutional Evidence)

**Architectural consequence:** Two distinct audit record types must exist: `ActionApproval` (standard approval within scope) and `ScopeBoundaryConfirmation` (approval at or beyond scope limit, with explicit boundary name and customer acknowledgment). A single approval record type with a flag is constitutionally insufficient.

---

## AD-009 — Security by Design

**Requirement:** All Constitutional Floors — human override, evidence immutability, permission traceability, authority licensing — must be enforced architecturally, not by application-layer convention. Security controls must be implemented at the lowest feasible layer.

**Type:** HARD — Constitutional Floor.

**Constitutional Basis:** C-001, C-007, C-008, Constitution Article IX (Constitutional Floors cannot be disabled by configuration or commercial pressure)

**Capabilities Constrained:** 2.4 (Emergency Stop), 6.1 (Authenticate), 6.2 (Isolate Tenant), 6.3 (Record Evidence)

**Architectural consequence:** JWT validation enforced in API middleware — not in individual endpoint handlers. RLS at database layer — not only application layer. Ledger append-only at database permission level — not only convention. Emergency Stop on dedicated WebSocket — not HTTP polling.

---

## AD-010 — Observability by Default

**Requirement:** Every constitutional event must emit structured telemetry automatically — without requiring manual instrumentation per feature. Constitutional compliance must be measurable from observability data alone.

**Type:** SOFT — derives from the First Law (trust through observable evidence applied to the platform itself).

**Constitutional Basis:** C-002 (First Law — the platform must be as observable as the professionals it governs), ADR-009 (OpenTelemetry constitutional spans defined: `constitutional.evidence.recorded`, `constitutional.authority.validated`, `constitutional.emergency_stop`, etc.)

**Capabilities Constrained:** 6.4 (Observe Platform Health and Constitutional Compliance)

**Architectural consequence:** OTel SDK in all four services. Constitutional spans emitted automatically from the Constitutional Engine on every constitutional event. PAAS latency histogram with P99 alert threshold at 200ms (before the 250ms Constitutional Floor is breached).

---

## AD-011 — Creative Standard Integrity

**Requirement:** For creative professional engagements, the Creative Standard Profile must be enforced as a constitutional document — deviations must be flagged, modifications must follow a governed amendment process, and the calibration period must be treated as a provisionally-standard state.

**Type:** HARD — Amendment A-005.

**Constitutional Basis:** C-016 (Amendment A-005 — Creative Standard Profile is a constitutional document), C-011 (scope-boundary confirmation applies to Creative Standard deviations)

**Capabilities Constrained:** 1.5 (Onboard Professional), 3.3 (Manage Creative Standard Profile), 2.3 (Confirm Scope-Boundary Crossings)

**Architectural consequence:** The Decision Space object for creative professions must include a `CreativeStandardProfile` field treated with constitutional authority. Content proposed against a Creative Standard must be validated against it before entering the standard approval flow. Creative Standard amendments must produce `ScopeBoundaryConfirmation` audit records.

---

## AD-012 — Business KPI Primacy in Performance Architecture (v0.8.0)

**Requirement:** Every performance monitoring interface, every performance data model, and every performance-related agent decision must surface the customer's stated business KPIs as the primary metric. Technical metrics (engagement rate, content quality score, execution count) are supporting evidence only and must never be surfaced as the headline performance indicator.

**Type:** HARD — derives from C-037 (LAW: performance = business outcomes).

**Constitutional Basis:** C-037 (business outcomes are the constitutional measure of professional performance — LAW); GENESIS "Business Outcome First" principle

**Capabilities Constrained:** 2.7 (Monitor Skill KPIs), 3.4 (Self-Improve), 4.1 (Assess Performance), 4.5 (Set Skill Goals)

**Architectural consequence:** The `skill_performance_records` table must carry both `business_kpi_value` (e.g., appointments_this_week) and `technical_metric_value` (e.g., engagement_rate) but the API and UI must always lead with the business KPI. The performance monitoring component in Business Platform must refuse to present technical metrics as a substitute for business KPIs.

---

## AD-013 — Conversational Configuration Completeness (v0.8.0, amended v0.21.0)

**Requirement:** The agent configuration flow — credential provision, goal setting, scheduling, Decision Space definition — must be completable through natural language conversation in under 15 minutes of active conversation time for a first-time customer, with no prior technical knowledge required.

**Amendment (v0.21.0 — GAP-A002, Simulation 006):** For C-042-governed agents (agricultural advisory, any agent where the customer has limited digital literacy), the 15-minute limit applies to TOTAL ACTIVE CONVERSATION TIME, which may be distributed across multiple short sessions over 1-3 days. A WhatsApp voice onboarding that occurs across 4 exchanges of ~3 minutes each is constitutionally valid. The constraint is the total conversation burden, not the calendar duration.

**Type:** HARD — derives from C-039 (conversational configuration is a constitutional obligation).

**Constitutional Basis:** C-039 (conversational configuration — CONFIRMED); C-042 (Vocabulary Mandate — farmers cannot sustain 15-minute uninterrupted sessions); GENESIS "The customer never manages prompts"

**Capabilities Constrained:** 1.7 (Configure via Conversation), 1.8 (Trial Enrollment), 4.5 (Set Skill Goals), 10.x (all Agricultural Advisory capabilities)

**Architectural consequence:** A Conversational Configuration Engine component must exist in AI Runtime. It must be capable of deriving a complete, valid Decision Space from natural language input. The resulting Decision Space must be presented back to the customer in business terms for confirmation before being committed.

---

## AD-014 — Pro-Rata Billing Precision (v0.8.0)

**Requirement:** Billing events must be calculated with minute-level precision. A pause, resume, or termination at any point in the billing cycle must result in a billing event that reflects the exact duration used — never rounded up to the nearest day, week, or month.

**Type:** HARD — derives from C-038 (LAW: pro-rata billing is a constitutional right).

**Constitutional Basis:** C-038 (pro-rata billing — LAW); ART-IX (right to terminate immediately without penalty)

**Capabilities Constrained:** 5.4 (Pause Skill), 5.5 (Resume Skill), 9.1 (Subscription Lifecycle), 9.2 (Transparent Billing)

**Architectural consequence:** The Subscription Manager must record billing events as timestamped ledger entries. Each pause/resume/terminate produces an immutable billing event with the exact timestamp. Pro-rata calculation is performed at billing period end over the event ledger. No scheduled jobs — event-driven billing only.

---

## AD-015 — Multilingual Voice Interface for C-042 Agents (v0.11.0)

**Requirement:** Any agent whose constitutional basis includes C-042 (Vocabulary Mandate) must deliver its primary customer interface via natural-language voice input/output in the dominant regional language(s) of the target customer population. Text/form interfaces are permitted only as secondary channels. The voice pipeline must not require the customer to type or use a smartphone app beyond WhatsApp.

**Type:** HARD — derives directly from C-042 (LAW). C-042 mandates that no technical data shall reach a low-literacy customer. A text-only or form-only interface is itself a form of technical data exposure (requiring literacy the customer may not have).

**Constitutional Basis:** C-042 (Vocabulary Mandate — LAW); C-039 (conversational interface — CONFIRMED); AS-005 (small and marginal farmer primary channel is WhatsApp voice)

**Capabilities Constrained:** 10.1, 10.2, 10.3, 10.4, 10.5, 10.6 — all Domain 10 capabilities; and any future agent with C-042 in its constitutional basis

**Architectural Consequence:** The AI Runtime's Vocabulary Translation Layer (see component spec) must:
1. Accept voice input via WhatsApp Business API Audio → speech-to-text (regional language)
2. Route through the agent's decision logic with full C-042 vocabulary enforcement
3. Render the response as audio via text-to-speech in the same regional language
4. Record the input transcript, decision chain, and output text (not audio) in the Constitutional Audit Ledger

The voice pipeline latency budget is ≤5 seconds end-to-end for standard advisory responses. Alert delivery (10.1) may be push-only (agent initiates) — no customer voice input required.

---

## Architectural Drivers Summary (v0.11.0)

| ID | Driver | Type | Primary Constraint |
|---|---|---|---|
| AD-001 | Emergency Stop Latency ≤250ms | HARD | PAAS execution, Emergency Stop capability |
| AD-002 | Evidence First Enforcement | HARD | All execution and governance capabilities |
| AD-003 | Audit Ledger Immutability | HARD | Constitutional evidence recording |
| AD-004 | Multi-Tenant Data Isolation | HARD | All capabilities (cross-cutting) |
| AD-005 | PAAS Execution Latency <50ms hot path | HARD | Pre-Authorized Work execution |
| AD-006 | Cost ≤INR 10k/month per non-prod env | HARD (non-prod) | All platform operations |
| AD-007 | Runtime Universality — one codebase | HARD | Professional execution, Decision Space |
| AD-008 | Constitutional Auditability | HARD | All governance capabilities |
| AD-009 | Security by Design | HARD | Authentication, isolation, evidence |
| AD-010 | Observability by Default | SOFT | Platform health and compliance |
| AD-011 | Creative Standard Integrity | HARD (creative prof.) | Creative professional capabilities |
| **AD-012** | **Business KPI Primacy** | **HARD** | **Performance monitoring, self-improvement** |
| **AD-013** | **Conversational Config Completeness (<15 min)** | **HARD** | **Configuration and onboarding** |
| **AD-014** | **Pro-Rata Billing Precision (minute-level)** | **HARD** | **Subscription lifecycle, billing** |
| **AD-015** | **Multilingual Voice Interface (C-042 agents)** | **HARD** | **Agricultural advisory, any C-042 agent** |
| **AD-016** | **Paid Advertising Budget Hard Cap** | **HARD** | **Digital Marketing Agent, any agent managing third-party spend** |

---

## AD-016 — Paid Advertising Budget Hard Cap (v0.14.0)

**Requirement:** When a Digital Professional manages financial spend on a third-party platform (paid advertising, marketplace budget, procurement), the customer-approved monthly budget ceiling must be enforced at the tool call layer — architecturally preventing spend beyond the approved limit regardless of system state, optimisation logic, or failure mode.

**Type:** HARD — derives from C-043 (LAW). Overspend is a constitutional violation equivalent to unauthorized action execution. Prompt-level instructions to "stay within budget" are insufficient — the enforcement must be structural.

**Constitutional Basis:** C-043 (Financial Spend Authority Ceiling — LAW); C-003 (Second Law — authority is licensed; spend authority is bounded at hire time); C-041 (every spend-incurring tool call requires CE.ValidateAction with budget_remaining as a parameter)

**Capabilities Constrained:** 11.5 (Paid Digital Advertising) — and any future capability involving agent-managed financial expenditure

**Architectural Consequence:** The AI Runtime's MCP client must, before any tool call that incurs financial spend:
1. Retrieve current approved_monthly_budget and current_month_spend from CE state
2. Calculate: would this call exceed approved_monthly_budget?
3. If YES → reject the tool call, raise BUDGET_CEILING_REACHED event, notify customer via approval request — do not attempt the spend call
4. Record the budget check result in the Constitutional Audit Ledger (Evidence First)
5. Only proceed with the spend tool call after confirming remaining_budget > 0 AND CE.ValidateAction returns PERMIT

Note: This driver requires CE.ValidateAction to carry budget state as a first-class parameter for spend-type tool calls. This is an extension to the CE ValidateAction interface beyond the standard Decision Space check.

---

## AD-017 — Synthetic Approval Confidence Gate (v0.16.0)

**Requirement:** Before generating a Synthetic Approval for any skill action, the AI Runtime must verify that: (a) the skill's approval mode is configured as `SYNTHETIC_APPROVAL`; (b) the computed confidence score meets or exceeds the customer-configured threshold; (c) the prior approved-action history count meets or exceeds the minimum history threshold; (d) the action type is within the skill's synthetic-eligible action classes. If any condition is not met, the skill must fall back to `EXCEPTION_APPROVAL` or `CUSTOMER_APPROVAL` mode for that action.

**Type:** HARD — derives from C-044 (LAW). A Synthetic Approval generated below the confidence threshold is constitutionally invalid. It cannot be corrected post-hoc — a sub-threshold synthetic approval is equivalent to an unauthorized action execution under C-003.

**Constitutional Basis:** C-044 (Synthetic Approval — LAW); C-002 (trust through evidence — confidence below threshold means insufficient evidence); C-003 (Second Law — unauthorized action is a constitutional violation)

**Capabilities Constrained:** All skills in SYNTHETIC_APPROVAL mode across any agent type. This is a platform-wide driver, not specific to the Digital Marketing Agent.

**Architectural Consequence:** The AI Runtime's Synthetic Approval Pipeline must:
1. Retrieve the skill's `approval_mode`, `synthetic_approval_confidence_threshold`, and `synthetic_approval_min_history` from skill runtime configuration
2. Query prior approval history for this action type: count and approval rate
3. Compute similarity score between proposed action and corpus of prior approved actions (vector similarity via pgvector)
4. If count < min_history OR similarity < threshold → REJECT synthetic approval → downgrade to EXCEPTION_APPROVAL for this action → customer approval request raised
5. If count ≥ min_history AND similarity ≥ threshold → generate SYNTHETIC_APPROVAL evidence record → CE.ValidateAction(SYNTHETIC_APPROVAL, confidence) → execute → notify customer
6. The confidence score and basis (list of prior approval IDs used for inference) are recorded in the evidence record — non-negotiable

**Override window:** Each synthetically approved action has a customer-configured retrospective override window (default: 24 hours for content actions, 1 hour for financial actions). Expired overrides are sealed in the CAL.

---

## AD-018 — Prompt Versioning and Constitutional Alignment (v0.20.0)

**Requirement:** Every prompt used by an AI model in the platform must carry a version identifier, a constitutional basis citation, and a review record. Prompt changes that alter decision-making behaviour must not be deployed without the same governance process as a Decision Space amendment. The AI Runtime must refuse to execute a prompt version that is not in the approved prompt registry.

**Type:** HARD — derives from C-045 (LAW). Ungoverned prompts produce ungoverned agent behaviour, which is constitutionally equivalent to an unauthorized Decision Space change.

**Constitutional Basis:** C-045 (Prompt as Constitutional Artifact — LAW); C-036 (Skills are constitutional units); DP-003 (Configuration over Code)

**Capabilities Constrained:** All skills in all agents — any skill that invokes an LLM inference

**Architectural Consequence:**
1. The AI Runtime maintains a Prompt Registry table (`agent_prompt_versions`) with: prompt_id, version, skill_type, pipeline_step, constitutional_basis, approved_by, approved_at, is_active
2. At runtime, before any LLM call, the AI Runtime looks up the active prompt version for (skill_type, pipeline_step)
3. If no approved prompt exists for that combination → AI Runtime returns INFERENCE_BLOCKED (not a graceful degradation — missing approved prompt is a constitutional gap)
4. Prompt content is stored in the Prompt Library (`architecture/reference/prompts/`) with constitutional basis per prompt
5. Developer cannot change a prompt by editing a file — they must create a new version, get it reviewed, and mark it active in the registry

---

## AD-019 — Agent-Driven Orchestration (v0.20.0)

**Requirement:** Digital Professional agents must drive their own execution cycle through a reasoning loop. Temporal workflows provide durability guarantees for agent decisions, not decision logic. Code schedulers (cron, Temporal schedules) may wake an agent, but the agent determines what to do upon waking. The agent's reasoning output is the primary workflow input; the workflow is the execution substrate, not the decision engine.

**Type:** HARD — derives from C-047 (LAW). An agent whose actions are determined by a workflow scheduler is not a professional — it is a script. The constitutional claim that agents exercise professional judgment (C-036) requires that judgment to be genuinely exercised, not pre-scripted.

**Constitutional Basis:** C-047 (Agent-Driven Execution Loop — LAW); C-036 (Skills as constitutional units); C-030 (Decision Space as architectural primitive — the agent reads it, not the scheduler)

**Capabilities Constrained:** All skill execution capabilities (3.1, 3.2, all Domain 11 skills) — and all Platform Operations capabilities (Domain 12)

**Architectural Consequence:**
1. Every agent execution cycle begins with an LLM reasoning call: "Given my context and Decision Space, what is the most appropriate action for me to take right now?"
2. The reasoning output is a structured plan (action_type, parameters, constitutional_basis, confidence) — not a generic completion
3. The Temporal workflow executes the plan produced by the agent's reasoning
4. Temporal does NOT decide what the agent does — it only ensures durability of the agent's decision
5. The reasoning call and its output are recorded as a Reasoning Trace (see agent-reasoning-trace.md)
6. CE.ValidateAction is called on the agent's proposed action BEFORE Temporal activity execution — the agent reasons, CE validates, Temporal executes

---

## AD-020 — STT for India Regional Languages (v0.21.0 — C-042, GAP-A004)

**Requirement:** Any agent subject to C-042 (Vocabulary Mandate) that accepts voice input must use a Speech-to-Text service capable of accurately transcribing India regional languages — including domain-specific agricultural vocabulary (pesticide names, crop terms, measurement units). The STT service must be configurable per agent deployment and must be validated for accuracy on domain vocabulary before activation.

**Type:** HARD — derives from C-042 (LAW). A STT service that mishears "Carbendazim" as "Carbon" produces wrong agricultural advice. STT accuracy is a prerequisite for C-042 vocabulary compliance, not an implementation detail.

**Constitutional Basis:** C-042 (Vocabulary Mandate); C-039 (conversational interface); AD-015 (Multilingual Voice Interface)

**Capabilities Constrained:** All agricultural advisory capabilities (Domain 10); any future C-042-governed agent using voice input

**Architectural Consequence:**
1. The whatsapp-voice-mcp implements STT via a configurable provider (Google Cloud Speech / Azure Cognitive Services / IndicSTT — per ADR-023 when written)
2. Domain vocabulary validation: before deployment, the STT is tested against a domain vocabulary checklist (50+ crop names, pesticide names, measurement units in target language)
3. Misrecognition fallback: if STT confidence is below 0.75, the agent asks for clarification in farmer's language before acting on the transcription
4. STT output is stored as-is in the evidence record alongside the original audio reference — for audit and PMFBY purposes
