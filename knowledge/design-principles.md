# Design Principles

**Produced by:** Chief Business Architect (Sprint 002 + v0.8.0 update)
**Date:** 2026-07-07 (updated 2026-07-08)
**Constitutional Basis:** Ratified Claims C-001 through C-039

---

## Reading this Document

Design Principles are engineering directives derived from constitutional claims. Every significant implementation decision must be evaluable against these principles.

A principle has three parts:
- **Directive** — what the engineering organization must do (or must not do)
- **Constitutional Basis** — the claim(s) from which it derives
- **Enforcement** — how compliance is verified

Principles are listed in order of constitutional priority — Constitutional Floor principles first.

---

## DP-001 — Evidence First

**Directive:** Record constitutional evidence before returning success. Never return a success response for an action that requires constitutional evidence if the evidence write has not been confirmed durable.

**Why:** Trust is earned through observable evidence (C-002, First Law). Evidence that is not recorded before the action succeeds can be lost if the system fails between action completion and evidence write. Lost evidence is a trust void — it cannot be recovered.

**Constitutional Basis:** C-002 (First Law), C-023 (Evidence First architectural implication), C-007 (ledger immutability)

**Enforcement:**
- The Constitutional Engine is called synchronously via gRPC before any approval, execution, or authority event returns success
- The calling service treats a Constitutional Engine timeout as a failure — the action did not succeed
- Constitutional Compliance Tests (CCTs) verify this in every environment before promotion
- Operational Discovery: any code path that returns success before Constitutional Engine confirmation is a constitutional violation, not a bug

---

## DP-002 — Human Override is Unconditional

**Directive:** The Emergency Stop path must never be degraded, rate-limited, queued, or made asynchronous. It is the last architectural guarantee of constitutional governance.

**Why:** Human override of any digital professional is absolute and architecturally guaranteed (C-001, Constitutional Floor). "Architecturally guaranteed" means the guarantee exists at the infrastructure layer, not the application layer.

**Constitutional Basis:** C-001 (human override absolute), C-024 (≤250ms architectural guarantee), C-019 (deterministic latency makes PAAS constitutional)

**Enforcement:**
- Emergency Stop uses a dedicated pre-warmed WebSocket connection (ADR-004, Azure SignalR)
- Emergency Stop path has no shared queue with regular API traffic
- Constitutional Compliance Tests measure Emergency Stop round-trip latency in every environment — P99 > 200ms triggers an alert before the 250ms Constitutional Floor is breached
- Any infrastructure change that would share the Emergency Stop connection with other traffic requires Founder approval

---

## DP-003 — Configuration over Code

**Directive:** Professional-type differences must be expressed through configuration and Decision Space parameters. No conditional logic of the form `if professionalType == X` may exist in the Professional Runtime.

**Why:** All three MVI professional scenarios must run on one runtime codebase with zero code changes (C-035, Runtime Universality Test). The Decision Space object is the mechanism through which all professional-type behavior is expressed (C-030).

**Constitutional Basis:** C-035 (Runtime Universality — LAW), C-030 (Decision Space as architectural primitive)

**Enforcement:**
- Runtime Universality Test is a gate: "A dental marketing professional, a beauty artist professional, and a trading professional must all execute on the same codebase with only their Decision Space configuration differing"
- Code review rejects any `professionalType` conditional in Professional Runtime or AI Runtime
- This principle does NOT prevent professional-type-specific configuration files — it prevents runtime branching

---

## DP-004 — Decision Space is the Primitive

**Directive:** Design all employment, authority, approval, and execution models around the Decision Space object as the central first-class concept. Employment is the delegation of a Decision Space. Authority is the license to occupy it. Capability is the ability to exercise judgment within it.

**Why:** ECI-001 (ratified as working assumption C-030) is the constitutional primitive from which all other models derive. Designing around a different primitive (e.g., role-based permissions, feature flags) would produce a system that cannot faithfully embody the constitutional model.

**Constitutional Basis:** C-030 (Decision Space as architectural primitive — ratified working assumption), C-014 (shadow authority is a natural behavior — implies Decision Space has observable boundaries), C-018 (PAAS is a geometric property of Decision Space)

**Enforcement:**
- The Decision Space object must be independently inspectable, versionable, and auditable in the domain model
- The Decision Space must be the configuration object customers interact with at hiring — not a derived consequence of role assignment
- Any change to a customer's Decision Space must produce a Constitutional Audit Ledger record

---

## DP-005 — Append-Only for Truth

**Directive:** Constitutional and evidence records grow forward in time, never backward. No UPDATE or DELETE operation may be applied to the Constitutional Audit Ledger or the Customer Evidence Ledger by any actor, including database administrators, under normal operations.

**Why:** No evidence in any ledger may be retroactively modified or deleted (C-007, Constitutional Floor). This protection must be enforced at the database layer, not the application layer (C-027).

**Constitutional Basis:** C-007 (ledger immutability), C-027 (append-only at database level)

**Enforcement:**
- The application service account for the Constitutional Engine has INSERT + SELECT permissions — no UPDATE or DELETE on the constitutional schema
- EF Core migrations on the constitutional schema must be reviewed against the prohibited SQL operations list (ADR-011)
- When business logic requires "correcting" a previous evidence record, the correct pattern is to append a correction record, not modify the original

---

## DP-006 — Security by Design

**Directive:** Implement Constitutional Floors at the lowest feasible architectural layer. Application-layer enforcement is always secondary to infrastructure-layer enforcement for constitutional requirements.

**Why:** Constitutional Floors cannot be disabled by configuration, commercial pressure, or application bugs (Constitution Article XI). An application-layer-only enforcement can be bypassed by a sufficiently sophisticated bug or misconfiguration. Infrastructure-layer enforcement cannot.

**Constitutional Basis:** C-001 (human override absolute), C-007 (immutability), C-004 (three systems independent — cannot be conflated at application layer), C-006 (Institutional Independence), C-009 (AD-009)

**Enforcement:**
- JWT validation in API middleware — not in individual handlers
- Row-Level Security in PostgreSQL — not only in repository queries
- Ledger immutability at database permission level — not only in EF Core model
- mTLS between services — not only application-layer authentication
- Emergency Stop on dedicated WebSocket — not HTTP polling

---

## DP-007 — Tenant Isolation by Default

**Directive:** Multi-tenant isolation must be enforced at the database layer as the primary mechanism. Application-layer isolation is a secondary defense, not the primary one. Every database query must operate within the tenant boundary established by the authenticated JWT.

**Why:** The Three-Ledger Model requires that no stakeholder may access another's ledger without explicit constitutional authorization (C-005). Application-layer-only isolation can be bypassed (C-026). The tenant_id from the JWT is the isolation anchor.

**Constitutional Basis:** C-005 (Three-Ledger Model), C-026 (database-level enforcement), C-006 (Institutional Independence)

**Enforcement:**
- PostgreSQL RLS policies on every tenant-scoped table using `SET LOCAL app.tenant_id`
- Every API request extracts tenant_id from JWT and propagates it through gRPC metadata into DB session
- Constitutional Compliance Tests include a cross-tenant isolation test: a request authenticated as Tenant A must receive a 403 or empty response for any Tenant B resource
- No shared database credentials between tenants at any layer

---

## DP-008 — Authority is Earned, Not Assumed

**Directive:** Digital professionals begin at the minimum authority level configured in the Employment Contract. Authority expands only through evidence-demonstrated competence in governed assessments. No professional begins with authority granted by capability alone.

**Why:** Authority is never granted by confidence — it is continuously licensed through constitutional evidence (C-003, Second Law). Maximum capability does not confer authority (C-004, Three Systems independent).

**Constitutional Basis:** C-003 (Second Law), C-004 (Capability ≠ Authority), C-009 (CP-001 — authority level must be visible at evaluation)

**Enforcement:**
- The Employment Contract stores the initial authority level — not derived from the professional profile
- Authority expansion requires an explicit governance event recorded in the Constitutional Audit Ledger
- The UI must display the current authority level at all times during active employment
- Authority cannot be expanded silently by the platform — it requires a customer governance action

---

## DP-009 — API First

**Directive:** Interfaces are defined and reviewed before implementations begin. The OpenAPI specification is the source of truth for external APIs. The gRPC `.proto` file is the source of truth for internal APIs. Implementations must conform to the specification — specifications are never generated from code.

**Why:** The Constitutional Chain requires that architecture precedes implementation (C-008, C-032). An API specification is architecture — defining it after implementation inverts the chain.

**Constitutional Basis:** C-008 (Constitutional Chain), C-031 (significant decisions require ADRs — API design is a significant decision), C-032 (implementation may not create architecture), ADR-002 (spec-first OpenAPI strategy)

**Enforcement:**
- Pull requests adding new endpoints must include the OpenAPI spec update first
- CI pipeline validates implementation responses against the spec (schemathesis, ADR-002)
- `.proto` files are version-controlled in `architecture/reference/proto/` (ADR-001)
- Code review rejects implementations where the spec was not written first

---

## DP-010 — Observability by Default

**Directive:** Every constitutional event must emit structured telemetry automatically as part of the event processing — not as an optional logging step added after the fact. Constitutional compliance must be measurable from observability data without additional instrumentation.

**Why:** Trust is earned through observable evidence (C-002). The platform that governs digital professionals must itself be observable. The institution cannot claim its professionals are trustworthy if the platform governing them cannot be observed.

**Constitutional Basis:** C-002 (First Law — observable evidence), ADR-009 (constitutional spans: `constitutional.evidence.recorded`, `constitutional.authority.validated`, `constitutional.emergency_stop`, `constitutional.ai.inference`)

**Enforcement:**
- Constitutional Engine emits a constitutional span for every evidence record, authority validation, authority violation, and Emergency Stop event
- PAAS latency histogram `paas.execution.latency_ms` P99 alert at 200ms (50ms before Constitutional Floor)
- OTel SDK integrated in all four services from day one — not added when needed
- Constitutional Compliance Tests validate that constitutional spans appear in traces for every governed event

---

## DP-011 — Business Outcome First in Every Interface (v0.8.0)

**Directive:** Every customer-facing interface — configuration, monitoring, reporting, billing — must present business outcomes as the primary language. Technical metrics, system identifiers, and operational state are secondary context. If a customer must think in technical terms to use WAOOAW, the interface has failed.

**Why:** GENESIS establishes that the customer hires business capability, not technology. An interface that presents `authorized_actions[0].actionType = INSTAGRAM_POST` requires the customer to think technically. An interface that says "the agent is allowed to post on Instagram" delivers the same information in business language. C-039 mandates conversational configuration precisely because form-based technical interfaces violate this principle.

**Constitutional Basis:** C-039 (conversational configuration — CONFIRMED); C-037 (business KPIs as primary performance measure — LAW); GENESIS "Business Outcome First"

**Enforcement:**
- All customer-facing API fields use business vocabulary (not enum codes) in human-readable form
- UI/UX review must validate that no customer-facing screen requires technical literacy
- Performance dashboards must lead with business KPIs; technical metrics are accessible but not primary
- Agent onboarding conversational flow is tested with actual business owners (dentist, beauty artist, trader), not engineers

---

## DP-012 — Skill Granularity in Governance (v0.8.0)

**Directive:** Every governance mechanism — Evidence First, Emergency Stop, authority licensing, billing — must operate at the Skill level, not only at the agent level. A customer who pauses a single Skill must not cause the entire agent to halt.

**Why:** C-036 establishes that Skills are independently governable constitutional units. If the governance infrastructure only operates at the agent level, C-036 is architecturally unenforceable. A dental marketing agent with four skills (Instagram, Facebook, Google Business, WhatsApp) must allow the customer to pause only Instagram without affecting the others.

**Constitutional Basis:** C-036 (Skills as independently governable units — LAW); C-038 (pro-rata billing at Skill level — LAW)

**Enforcement:**
- The `professional_skills` table has its own lifecycle state (ACTIVE, PAUSED, TERMINATED)
- Billing events are generated per-Skill, not per-agent
- Emergency Stop at agent level halts all Skills; but Skill-level pause only halts that Skill
- The capability-to-container map must show Skill-level capabilities mapped to their owning containers

---

## DP-013 — Vocabulary Translation Layer for C-042 Agents (v0.11.0)

**Directive:** Any agent whose constitutional basis includes C-042 (Vocabulary Mandate) must implement a Vocabulary Translation Layer inside the AI Runtime — a mandatory processing stage that intercepts every outbound response and enforces the translation from technical/data vocabulary to the customer's occupational vocabulary. This layer is not optional and cannot be bypassed.

**Why:** C-042 is a LAW with no qualification. An agent that can "sometimes" emit technical data to a low-literacy customer is not C-042-compliant — it is unconstitutional. The Vocabulary Translation Layer makes compliance structural: it is architecturally impossible for a C-042 agent to emit a raw humidity percentage, a mandi index, or a rupee price in isolation, because the layer intercepts the response before it reaches the customer and enforces translation.

**Constitutional Basis:** C-042 (Vocabulary Mandate — LAW); C-039 (conversational interface — CONFIRMED); AD-015 (Multilingual Voice Interface requirement)

**Enforcement:**
- The Vocabulary Translation Layer is a discrete module in the AI Runtime, not a prompt instruction
- It is activated by agent configuration: `vocabulary_mandate: true` in the agent's decision space config
- Input: the agent's raw LLM response (which may contain technical data for internal use)
- Output: a translated response in the customer's registered language and occupational vocabulary
- The layer must validate that no technical data pattern (numeric index, %, ppm, meteorological codes) appears in the output
- The layer logs both the raw and translated responses in the Constitutional Audit Ledger (for compliance verification)
- Failure to translate must result in a refusal to deliver the response and an internal alert — never a raw data leak

---

## Design Principles Summary (v0.11.0)

| ID | Principle | Type | Constitutional Floor? |
|---|---|---|---|
| DP-001 | Evidence First | Engineering mandate | Yes — First Law |
| DP-002 | Human Override is Unconditional | Engineering mandate | Yes — Article XI |
| DP-003 | Configuration over Code | Engineering mandate | Yes — Runtime Universality |
| DP-004 | Decision Space is the Primitive | Design directive | No — working assumption |
| DP-005 | Append-Only for Truth | Engineering mandate | Yes — Article XI |
| DP-006 | Security by Design | Engineering mandate | Yes — Article XI |
| DP-007 | Tenant Isolation by Default | Engineering mandate | Yes — Article VI |
| DP-008 | Authority is Earned, Not Assumed | Design directive | No — Second Law consequence |
| DP-009 | API First | Engineering process | No — Constitutional Chain consequence |
| DP-010 | Observability by Default | Engineering mandate | No — First Law consequence |
| **DP-011** | **Business Outcome First in Every Interface** | Engineering mandate | No — GENESIS mandate |
| **DP-012** | **Skill Granularity in Governance** | Engineering mandate | Yes — C-036 LAW |
| **DP-013** | **Vocabulary Translation Layer for C-042 Agents** | Engineering mandate | Yes — C-042 LAW |
| **DP-014** | **Maturity-Driven Skill Activation** | Engineering mandate | No — domain design pattern |

---

## DP-014 — Maturity-Driven Skill Activation (v0.14.0)

**Directive:** For multi-skill agents that serve customers across a wide spectrum of readiness levels, skills must be activated progressively based on the customer's assessed maturity — not all at once at engagement start. An intelligence phase (profile + assessment) must always precede execution skill activation. Execution skills are gated by the customer's current maturity score and the phase bundle they have selected.

**Why:** Activating all available skills on a Score 1 customer (no digital footprint) produces waste and confusion — the customer cannot use advanced skills (CRO, competitive intelligence) when they have no traffic to convert and no competitors to monitor. Conversely, withholding execution from a Score 6 customer creates opportunity loss. The maturity assessment is the mechanism that makes skill activation relevant rather than generic.

**Constitutional Basis:** C-036 (Skills are independently governable — activation is per-Skill, not per-agent); C-037 (Business KPI primacy — activating skills the customer cannot benefit from wastes their budget and fails their KPIs); AD-013 (Conversational Config Completeness — the profile and assessment must complete within the onboarding time constraint)

**Enforcement:**
- The Customer Profiling skill (Skill 0) must complete before any execution skill is activated
- The Market Research skill (Skill 1) must produce a Maturity Score before the Phase Bundle is confirmed
- Phase Bundle selection (Curtain Raiser / Growth Engine / Maturity Phase) is a customer decision, not an agent decision — the agent recommends, the customer confirms
- Decision Space authorization entries for Phase 2 and Phase 3 skills include a `phase_prerequisite` constraint: CE.ValidateAction returns DENY for a Phase 2 skill invocation if the customer's active bundle is Curtain Raiser
- Skill upgrade (bundle change) requires a new customer authorization event — the same process as any Decision Space expansion (C-003 Second Law)

---

## DP-015 — Synthetic Approval as Learned Delegation (v0.16.0)

**Directive:** A skill operating in SYNTHETIC_APPROVAL mode must generate its approval from a learned, evidence-backed preference model — not from heuristics, defaults, or untrained inference. The skill's approval authority is earned through demonstrated correctness, not assumed at activation. The transition from CUSTOMER_APPROVAL to SYNTHETIC_APPROVAL must be gradual, auditable, and customer-controlled at every step.

**Why:** The alternative — an AI that simply executes without approval — is constitutionally invalid (C-003). The other alternative — requesting approval for every action forever — makes the agent unusable for high-volume professional work. Synthetic Approval is the constitutionally sound middle path: authority delegation backed by evidence, revocable at any time, transparent in every record.

**Constitutional Basis:** C-044 (Synthetic Approval — LAW); C-002 (trust earned through evidence); C-001 (human override unconditional); AD-017 (confidence gate)

**Enforcement:**
- Approval mode is a skill-level configuration field, not an agent-level setting — each skill earns synthetic authority independently
- Mode upgrade (CUSTOMER → EXCEPTION → SYNTHETIC) is a Decision Space amendment requiring a customer authorization event (C-003) — the skill may propose, never self-activate
- Every synthetically approved action produces an evidence record with: approval type = SYNTHETIC, confidence score, basis approval IDs, customer notification timestamp, override deadline
- Customer notification is mandatory before or at execution — not after the override window closes
- The skill's monthly API budget includes a specific allocation for synthetic approval inference (vector similarity computation + LLM confidence scoring) — this is not free
- Self-governance: if the customer overrides more than 10% of synthetic approvals in any 30-day period, the skill must automatically propose downgrading to EXCEPTION_APPROVAL mode

---

## DP-016 — Prompt-First Execution (v0.20.0)

**Directive:** Before writing any code that invokes an LLM, the prompt for that invocation must exist in the Prompt Library as an approved, versioned document. Code that calls an AI model without a documented, approved prompt is constitutionally ungoverned and must be rejected in code review.

**Why:** The prompt is the mechanism by which constitutional constraints, domain knowledge, and decision criteria are expressed to the AI model. If the prompt is not governed, the agent's behaviour is not governed, regardless of how well-specified the surrounding code is. A perfectly implemented pipeline with an undocumented prompt is constitutionally incomplete.

**Constitutional Basis:** C-045 (Prompt as Constitutional Artifact); AD-018 (Prompt Versioning); DP-003 (Configuration over Code)

**Enforcement:**
- The Prompt Library (`architecture/reference/prompts/`) is a required deliverable before any implementation sprint that includes LLM calls
- Every prompt document includes: prompt_id, version, skill_type, pipeline_step, system_context, constitutional_constraints, output_schema, failure_handling, approval record
- The AI Runtime's prompt loader reads from the `agent_prompt_versions` table at startup — hardcoded prompt strings in code are a constitutional violation
- Pull requests that add LLM calls without a corresponding Prompt Library entry are automatically flagged in code review

---

## DP-017 — Autonomous Platform Operations (v0.20.0)

**Directive:** The platform must govern its own operations through constitutional agents — not through undocumented human interventions. Every platform operation that can affect a customer engagement (billing, contract state, skill suspension, agent restart) must be performed by a constitutionally governed agent with an evidence record, a Decision Space, and customer notification rights where applicable.

**Why:** The platform's credibility depends on consistent governance. A platform that governs customer-facing agents constitutionally but operates its own infrastructure through undocumented human procedures is institutionally inconsistent. Customers cannot trust an institution that does not apply its own governance framework to itself.

**Constitutional Basis:** C-046 (Platform Operations under Constitutional Governance — LAW); C-002 (trust through evidence); C-001 (human override unconditional — applies to platform operations affecting customers)

**Enforcement:**
- The Platform Operations Agent (see platform-operations-agent.md) is the only agent authorised to perform platform operations that affect customer engagements
- Human engineers may perform infrastructure operations (restart a crashed container, restore a database) but may NOT perform customer-affecting operations (cancel a contract, suspend a skill, modify billing) except via the Platform Operations Agent's override mechanism
- Every platform operation that modifies an employment contract, skill state, or billing record must generate a CE evidence record

---

## DP-018 — Agent Execution Primacy (v0.20.0)

**Directive:** The AI agent's reasoning output determines what action is taken. Infrastructure code (Temporal workflows, API handlers, cron schedules) provides the execution substrate — it does not determine the agent's actions. When implementing any agent execution cycle, the first question is: "What does the agent reason about here?" not "What should the code trigger here?"

**Why:** An agent whose actions are fully determined by code is a script, not a professional. The constitutional claim that Digital Professionals exercise judgment (C-036) requires that judgment to be genuinely exercised. The distinction matters architecturally: in a code-driven model, removing the AI makes the system slower but still functional. In an agent-driven model, removing the AI makes the system non-functional — the agent IS the decision logic.

**Constitutional Basis:** C-047 (Agent-Driven Execution Loop — LAW); C-036 (Skills as constitutional units); AD-019 (Agent-Driven Orchestration)

**Enforcement:**
- Every Temporal workflow activity that invokes an LLM must begin with the agent's reasoning call and treat its output as the workflow's primary input
- Code that determines agent actions through conditional logic (`if it's Monday, create content`) is a DP-018 violation — the agent should reason that Monday requires content, not be told
- The AI Execution Loop spec (architecture/reference/agent-execution-loop.md) defines the standard reasoning-first activity pattern that all agent implementations must follow

---

## DP-019 — Portfolio-First Cognition (v0.31.0)

**Directive:** When implementing any agent execution cycle that involves skill activation or performance evaluation, the agent must reason about its entire active skill portfolio before acting on any individual skill. A skill heartbeat that executes without consulting the agent's strategic state is a DP-019 violation. The strategic state (current plan, portfolio health, last assessment) must be loaded at the start of every execution cycle and updated when the plan changes.

**Why:** An agent that manages skills independently — each skill running on its own heartbeat without strategic coordination — is a collection of scripts pretending to be a professional. The constitutional claim of professional judgment (C-036) requires the agent to behave as a whole professional: someone who considers the customer's overall goal before deciding what to do next with any individual capability. This is the macro-level analogue of DP-018 (which governs micro-level reasoning before each action).

**Constitutional Basis:** C-050 (Strategic Cognition Obligation — LAW); C-036 (Skills as constitutional units); C-037 (Business KPI primacy); DP-018 (Agent Execution Primacy); AD-021 (Strategic Cognition Trigger Points)

**Enforcement:**
- Every agent's execution loop implementation must load `agent_strategic_state` (current plan + last assessment) before executing any skill heartbeat at a trigger-point interval
- A skill that modifies the agent's output (content, advice, trade, alert) and does NOT reference the current strategic plan violates DP-019
- The SKILL_ACTIVATION_PLAN and PERFORMANCE_ASSESSMENT prompts are the formal mechanism for updating strategic state — they are not optional analytics; they are the decision authority for skill orchestration
- The Activation Gate (Section 10 of AGENT-AUTHORING-GUIDE) is the governance mechanism that enforces this principle before any agent is activated

---

## DP-020 — Quality-Preserving Resource Economy (v0.32.0)

**Directive:** Every token spent by a WAOOAW agent must deliver proportionate customer value. Resource economy is not a compromise of quality — it is intelligent allocation of quality where it matters most. When implementing any LLM call or agent action, the first question is: “Does this action require frontier reasoning, or does it require reliable pattern execution?” Frontier models must be reserved for decisions where the reasoning quality difference is materially visible to the customer outcome. Routine execution (vocabulary translation, acknowledgment handling, template formatting) must use the minimum capable tier. Silently degrading quality at budget limit is prohibited (C-049). Spending frontier tokens on routine tasks when lower tiers are sufficient is wasteful (C-051 violation — poor resource stewardship).

**Why:** The cost structure of AI agents is the primary commercial risk for WAOOAW at scale. A platform that cannot control per-customer AI cost cannot price sustainably for the markets it serves (₹200/month farmers, ₹1,499/month SMEs). Quality-preserving resource economy is not an optimization — it is a commercial survival requirement. The principle exists so that implementation engineers default to the lowest viable tier for each task, not the highest available tier for simplicity.

**Constitutional Basis:** C-051 (Resource Transparency — LAW); C-048 (Non-Exploitation — over-spending on AI and passing cost to customers is an exploitation of the platform's information advantage); C-049 (Honest Limitation — budget limits must be disclosed, not silently managed through quality reduction); AD-022 (Model Tier Selection); AD-023 (Semantic Cache)

**Enforcement:**
- `minimum_model_tier` in `agent_prompt_versions` is the formal enforcement mechanism — every prompt call must read this field before dispatching to any LLM provider
- Message Classification Gate (Token Economy Layer) runs on LOCAL tier always — never a frontend call to frontier model
- Semantic cache lookup is mandatory before any LLM call for BEHAVIOURAL or lower tier prompts
- Pre-computation at off-peak hours (02:00–04:00 IST) is the preferred pattern for time-insensitive outbound messages
- The Usage Summary prompt runs on MID_TIER always — communicating budget status is BEHAVIOURAL quality, not BREAKING quality
- A PR that routes a PHRASING_ONLY prompt to FRONTIER is a DP-020 violation and requires EA justification

---
