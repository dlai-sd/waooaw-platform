# Goal Orchestrator — AI Intelligence Layer

**Classification:** Reference Architecture
**Status:** Proposed — Awaiting EA review + Founder acknowledgement
**Produced by:** AI Architect (INST-008) — GOAL-002 Phase A (2026-07-27)
**Constitutional Basis:** C-070 (Three Basic Instincts) · C-069 (Platform Self-Improvement) · GEOM §6 · GOAL-002
**Goal Reference:** GOAL-002 — Universal Constitutional AI Execution Layer
**Depends on:** MagicLLM architecture (architecture/reference/magic-llm/architecture.md) · GEOM (ratified) · WIOM (ratified)

---

## §0 — Why the Goal Orchestrator Needs Intelligence

A Goal Orchestrator without AI intelligence is a constitutional scheduler — it routes based on rules, monitors based on timers, and escalates based on failure counts. It cannot understand ambiguity, detect drift before it becomes a gate failure, consult domain knowledge mid-journey, or synthesize a decision brief that a Founder can act on in 30 seconds.

The Three Basic Instincts (C-070) demand more:

| Instinct | Without GO Intelligence | With GO Intelligence |
|---|---|---|
| **Follow Constitution** | Routes based on fixed rules | Routes based on constitutional reasoning — detects when a proposed routing would violate Article VII or GEOM §G-13 |
| **Improve Itself** | Static routing table | Learns from every Goal — routing quality improves as the institution accumulates evidence |
| **Autonomous + Trust-Based** | Escalates to Founder at the first uncertainty | Exhausts the Remediation Cascade before escalating — Founder sees only genuine decisions |

The Goal Orchestrator's AI Intelligence (GO-Intelligence) is what makes WAOOAW's Semantic Brain genuinely semantic. It is not a human-in-the-loop tool. It is an institution that reasons constitutionally.

---

## §1 — Architecture

GO-Intelligence is a set of **5 embedded intelligence invocation points** within the Goal Orchestrator. Each invocation uses MagicLLM (the Universal Constitutional AI Execution Layer) with a dedicated orchestration task category. Each invocation produces a constitutional evidence record. Each invocation is governed by the same constitutional principles as any other MagicLLM invocation.

```
GOAL REGISTERED (any format)
         │
         ▼
┌─────────────────────────────────────┐
│  POINT 1 — Goal Understanding       │
│  MagicLLM Task Cat. 9               │
│  Raw input → structured             │
│  Understanding Record               │
│  GEOM Stage G-2                     │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  POINT 2 — Routing Intelligence     │
│  MagicLLM Task Cat. 10              │
│  Goal + Registry + history →        │
│  optimal Institution selection      │
│  + Execution Plan                   │
│  GEOM Stage G-4                     │
└──────────────────┬──────────────────┘
                   │
                   ▼ (continuous during Journey)
┌─────────────────────────────────────┐
│  POINT 3 — Journey Monitor          │
│  MagicLLM Task Cat. 11              │
│  New Goal Register entries →        │
│  drift signals, SLA warnings,       │
│  early quality alerts               │
│  GEOM Stage G-5 (continuous)        │
└──────────────────┬──────────────────┘
                   │ (on Gate Fail)
                   ▼
┌─────────────────────────────────────┐
│  POINT 4 — Research Query           │
│  MagicLLM Task Cat. 12              │
│  Gap description + evidence →       │
│  industry knowledge synthesis       │
│  GEOM §10 Remediation L2            │
└──────────────────┬──────────────────┘
                   │ (on Founder Escalation)
                   ▼
┌─────────────────────────────────────┐
│  POINT 5 — Decision Synthesis       │
│  MagicLLM Task Cat. 13              │
│  Full evidence package →            │
│  3-option decision brief            │
│  for Founder                        │
│  GEOM §10 Founder Escalation        │
└─────────────────────────────────────┘
```

---

## §2 — The 5 Orchestration Task Categories (MagicLLM Cat. 9–13)

These extend MagicLLM's original 8 engineering categories. They are invoked exclusively by the Goal Orchestrator — not by Engineering Institutions.

---

### Category 9 — Goal Understanding

**Purpose:** Convert any raw Goal input (plain English, mind map transcript, raw notes, partially structured document) into a constitutionally complete Goal Understanding Record.

**Input:**
```
raw_input:        [any text — plain English, transcript, notes]
registrant:       [INST-NNN or Founder name]
context:          [any prior related Goals in the Register — for dependency detection]
```

**Process:**
1. Extract the business intent — what outcome does the registrant actually want?
2. Identify constitutional implications (which claims, articles, domains are affected)
3. Draft preliminary success criteria (to be confirmed by Registrant)
4. Detect conflicts or dependencies with active Goals
5. Identify what must be clarified before the Goal can proceed to Classification

**Output — Goal Understanding Record:**
```
record_type:        Goal Understanding Record
intent:             [structured business outcome statement]
success_criteria_draft: [SC-01 through SC-NN — draft, pending Registrant confirmation]
constitutional_implications: [claims/articles/amendments relevant]
clarification_needed: yes|no
clarifications:     [list of questions if yes]
related_goals:      [GOAL-NNN references if conflicts/dependencies detected]
```

**Model:** Gemini 2.5 Pro (Vertex AI asia-south1) — reasoning + large context
**Quality gate:** Constitutional Analyst (INST-002) reviews Understanding Records for constitutional accuracy before proceeding to Classification

---

### Category 10 — Routing Intelligence

**Purpose:** Select the optimal Institutions and sequence for a classified Goal, producing a Goal Execution Plan that reflects both constitutional requirements and historical performance evidence.

**Input:**
```
goal_classification:   [Scope · Nature · Risk · Urgency]
goal_understanding:    [Goal Understanding Record]
institution_registry:  [current OPERATIONAL Institutions + their Offering Scopes]
performance_history:   [institutional.goal_orchestrator_performance — per Institution/Goal-type metrics]
active_goals:          [current Institution capacity usage]
```

**Process:**
1. Filter Institutions by Offering Scope match (constitutional) — first pass
2. Filter by OPERATIONAL status — second pass
3. Score remaining Institutions by historical performance on similar Goal types
4. Determine optimal execution sequence (sequential/parallel/hybrid)
5. Define Evidence Specifications per Institution
6. Set Participation Windows based on historical completion times
7. Define Remediation Cascade parameters (which levels, max attempts, which Institutions at each level)

**Output — Routing Decision Record + Draft Execution Plan:**
```
record_type:         Routing Decision Record
selected_institutions: [INST-NNN list + sequence]
routing_rationale:   [why each Institution was selected, performance evidence cited]
execution_plan_draft: [Draft Execution Plan — reviewed by CA before issuance]
cascade_parameters:  {l1_max: 3, l2_max: 2, l3_max: 1}
```

**Model:** Gemini 2.0 Flash (fast, structured output, efficient)
**Self-improvement:** Every routing decision + outcome is recorded in `institutional.goal_orchestrator_performance`. Poor routing (Institutions miss SLA, require cascade) updates the Institution's performance score for this Goal type.

---

### Category 11 — Journey Monitor

**Purpose:** Continuously analyse new Goal Register entries during a Goal Journey to detect quality drift, SLA risk, and emerging misalignment with Goal success criteria — before a Gate failure occurs.

**Input (on each new Goal Register entry):**
```
new_record:         [the new Contribution Record, Learning Record, or Decision Record]
goal_register_state: [current state of this Goal's evidence]
success_criteria:   [SC-NNN list from Goal Understanding Record]
execution_plan:     [Evidence Specifications + Participation Windows]
```

**Process:**
1. Check if the new record advances the Goal toward its success criteria (or drifts away)
2. Check if the contributing Institution is within its Participation Window
3. Detect patterns: is the evidence chain maintaining constitutional traceability?
4. Generate early warning signals for GO attention before a Gate failure

**Output — Monitor Signal:**
```
record_type:       Monitor Signal
signal_type:       NOMINAL | SLA_WARNING | DRIFT_DETECTED | QUALITY_CONCERN
description:       [what was detected]
recommended_action: [GO action if non-NOMINAL: contact Institution / request status]
```

**Model:** Gemini Flash Lite (very fast, lightweight, continuous — invoked on every new entry)
**Constitutional principle:** Monitor signals are informational. The Goal Orchestrator acts on them based on its constitutional authority. Monitor signals do not appear in the Goal's main evidence chain — they are in the GO's operational log.

---

### Category 12 — Research Query

**Purpose:** Query external industry knowledge and synthesise domain-specific expert guidance in response to a specific Goal outcome gap. This is the Remediation Cascade Level 2 intelligence.

**Input:**
```
gap_description:    [exactly what outcome is not being met and why]
failure_evidence:   [L1 Attempt Records — what was tried]
goal_domain:        [domain classification from Goal Understanding Record]
technology_context: [current technology stack from Platform Type Registry]
```

**Process:**
1. Identify the most relevant external knowledge domains for this gap (standards bodies, RFCs, academic literature, CVE databases, public implementation patterns)
2. Formulate targeted research queries for each domain
3. Retrieve and synthesise findings relevant to the specific gap
4. Map findings to constitutional requirements (any finding that violates a claim is excluded)
5. Produce ranked recommendations with evidence citations

**Output — Research Record:**
```
record_type:        Research Record
gap_addressed:      [gap_description restated]
sources_queried:    [list of knowledge domains and specific sources]
findings:           [structured findings — per source, with evidence citations]
applicable_patterns: [implementation patterns directly applicable to the gap]
constitutional_screen: [findings excluded due to constitutional violations + rationale]
confidence:         [0-100% — how directly applicable is this research to the gap?]
recommendations:    [ranked list — most applicable pattern first]
```

**Model:** Gemini 2.5 Pro (1M context, deep reasoning, synthesis)
**Knowledge sources (default, configurable per Goal domain):**
- OWASP (security) · CNCF (cloud native) · ISO/IEC standards · SEBI/RBI regulations (finance) · HL7/FHIR (healthcare) · public GitHub patterns · academic paper abstracts · RFC libraries · CVE databases

---

### Category 13 — Decision Synthesis

**Purpose:** Synthesise the full evidence package from a failed Remediation Cascade into a concise, actionable decision brief for the Founder. The brief presents exactly 3 options with their constitutional implications.

**Input:**
```
goal_understanding:    [Goal Understanding Record]
l1_records:           [all L1 Attempt Records]
l2_research_record:   [Research Record from Level 2]
l3_redesign_record:   [Redesign Record from Level 3]
specific_gap:         [the precise unresolvable gap]
constitutional_context: [relevant claims, articles, amendments]
```

**Process:**
1. Identify the precise nature of the failure — technical? Constitutional? Scope mismatch?
2. Derive 3 resolution options (always: scope reduction, redesign, suspension)
3. For each option: state what it means for the Goal, the institution, and the customer
4. Compose the brief in language appropriate for the Founder (not technical jargon)
5. State clearly what the Founder's decision will authorize

**Output — Founder Decision Brief:**
```
record_type:        Founder Decision Brief
headline:           [one sentence: what the Founder must decide]
goal_summary:       [the Goal statement in 2 sentences]
what_was_tried:     [L1/L2/L3 summary — what the system attempted autonomously]
the_gap:            [the precise problem in plain language]
options:
  A: [scope reduction — what changes, what is lost, what is preserved]
  B: [architectural redesign — what new Goal would be spawned, estimated scope]
  C: [suspension — when to revisit, what conditions would unblock it]
constitutional_note: [which option best preserves constitutional integrity]
```

**Model:** Gemini 2.5 Pro (structured output, clear prose for non-technical reader)
**Delivery:** Steward Assistant routes to Founder via Steward interface (chat/WhatsApp). The brief is designed to be readable in under 2 minutes on a mobile device.

---

## §3 — Self-Improvement: How GO-Intelligence Gets Better

Every invocation of a GO-Intelligence category produces evidence that feeds the self-improvement loop (C-069):

| Performance signal | Recorded in | Used by |
|---|---|---|
| Routing decision quality (did selected Institutions deliver?) | `institutional.goal_orchestrator_performance` | Category 10 (Routing) — updates Institution scoring |
| Understanding accuracy (did draft SC match Founder intent?) | Same table | Category 9 — improves intent extraction |
| Monitor precision (did signals predict actual Gate failures?) | Same table | Category 11 — reduces false positives |
| Research relevance (did Research Record enable Level 2 success?) | Same table | Category 12 — improves source selection |
| Decision brief acceptance (did Founder choose option A/B/C without asking for more info?) | Same table | Category 13 — improves brief quality |

The Goal Orchestrator's routing, understanding, and research quality improve measurably after every Goal. The system earns autonomy through demonstrated performance — exactly as every Institution earns trust through its Trust Ledger.

---

## §4 — Constitutional Constraints

| Constraint | Source | Effect |
|---|---|---|
| All 5 invocations produce evidence records | C-059 | No GO-Intelligence decision is undocumented |
| GO Authorization not required for GO-Intelligence invocations | GEOM §6 — GO derives authority from GEOM ratification | GO-Intelligence is the authority mechanism, not subject to it |
| GO-Intelligence does not override Gate decisions | GEOM §10 | AI recommendations inform the GO; constitutional gates govern what proceeds |
| AUTONOMOUS_HALT stops all GO-Intelligence invocations | C-001 (Human Override) | Absolute |
| GO-Intelligence may not self-modify its routing rules | C-069 + WIOM §W-5 | Routing rule changes require Stage W-5 evolution pathway |
| Research findings that violate constitutional claims are excluded | Every claim is binding | Category 12 includes a constitutional screen step |

---

*Produced by AI Architect (INST-008) — GOAL-002 Phase A*
*For Enterprise Architect review (INST-004) and Founder acknowledgement.*
