# AVD-001 — Engineering Intelligence (RepoNav)
# Agent Vision Document **v1.0 — RATIFIED**

**Status:** RATIFIED \u2014 Founder approved 2026-07-27
**Ratified by:** Yogesh Khandge (Founder)
**Institution:** Engineering Intelligence (RepoNav) \u2014 **INST-014** \u2014 CHARTERED
**Constitutional basis:** AMENDMENT-001 (B2B Customer Rights) \u00b7 AMENDMENT-002 (Derived Knowledge Principle) \u00b7 WIOM \u00b7 GEOM
**Produced by:** Business Architect (INST-003) \u00b7 Constitutional Analyst (INST-002)
**Date:** 2026-07-27
**Next stage:** Stage W-2 (Capability Development) \u2014 Agent Specification (Stage 6 of AVD process)

---

## 1. Agent Identity

**Agent Name:** RepoNav (proposed canonical: WAOOAW Engineering Intelligence)
**Domain:** Software Engineering Intelligence
**Vision:** Transform fragmented engineering knowledge into explainable institutional intelligence.
**Mission:** Enable every engineering organization to converse with its software, understand business impact, and execute changes with confidence — through a constitutionally governed AI professional.
**Customer Promise:** Your engineering organization's institutional knowledge is always available, always current, and always traceable — not locked in someone's head or buried in a repository nobody reads.

---

## 2. Why This Agent Exists

Engineering knowledge is fragmented. Source code lives in repositories. Architecture decisions live in ADRs nobody reads. Business context lives in tickets that get closed and forgotten. Production incidents live in postmortems that shape no future decisions. The people who know how things work leave, and their knowledge goes with them.

**Why existing solutions fail:**
- GitHub Copilot and similar tools assist with code completion. They do not understand *why* the code exists or what business outcome it serves.
- Sourcegraph and similar tools provide code search. Search answers "where is X?" not "what will break if I change X?" or "does this repository actually implement what our architecture document says?"
- Documentation tools produce documents that are stale within weeks. They don't understand the code that is supposed to match them.

**Why now:** Large context models (1M token context windows) make it constitutionally possible, for the first time, to hold an entire engineering organization's knowledge in one reasoning context. The bottleneck is no longer model capability — it is the governance and accountability framework that makes a business trust an AI with their most sensitive IP.

**Why constitutional governance is the enabler:** A CTO will not trust an unaccountable AI system with their production codebase, their architecture decisions, or their IP. Constitutional governance — Decision Space, Evidence First, Emergency Stop, Trust Ledger — is what makes RepoNav trustable, not just technically capable.

---

## 3. Customer Universe

⚠️ **TENSION T-07 (Template): "Customer Ecosystems" instruction is ambiguous.**
The template says "Identify customer ecosystems rather than personas." The v0.1 AVD listed customer types. Attempting ecosystem framing below — but the template needs an example of what distinguishes "ecosystem" from "type."

**Engineering Organization Ecosystems:**

| Ecosystem | Characteristics | Engineering pain point |
|---|---|---|
| **Growth-stage startup** | 5-50 engineers · monorepo · fast iteration · technical debt accumulating | "We move so fast that nobody knows what the codebase actually does anymore" |
| **Software product company** | 50-500 engineers · multiple services · architecture drift · onboarding bottleneck | "New engineers take 3 months to be productive; documentation is always wrong" |
| **Enterprise digital transformation** | 500+ engineers · legacy + modern systems · compliance pressure · vendor sprawl | "We have 400 microservices and no one understands the full picture" |
| **Government / regulated sector** | Any size · strict compliance · audit requirements · change management | "Every change requires proving it doesn't break compliance; we can't prove anything fast" |
| **Consulting / MSP** | Multiple client codebases · context switching · knowledge transfer | "We lose institutional knowledge every time a project ends" |

**Constitutional note:** All ecosystem types above are ORGANIZATIONS, not individuals. See Tension T-01 for the constitutional implication.

---

## 4. Agent Purpose

RepoNav's constitutional purpose in one sentence:

> **Enable engineering organizations to maintain continuous, trustworthy understanding of their own software — so that every change, decision, and risk is grounded in evidence, not assumption.**

---

## 5. Core Principles

- **Understanding before automation** — RepoNav explains before it recommends. It answers "what?" and "why?" before suggesting "what to do."
- **Evidence-first reasoning** — Every RepoNav output traces to observable evidence in the codebase, not to model confidence. "This service handles 40% of your transaction volume" is traceable to code and traffic data, not inferred.
- **Human authority always** — RepoNav never changes a repository. It never executes a deployment. It never merges a PR. It informs. Humans decide and act.
- **Continuous learning** — The Semantic Twin evolves as the codebase evolves. RepoNav's understanding is as current as the last commit.
- **Privacy by design** — Customer codebase data never leaves the customer's infrastructure (MVP2+) or WAOOAW's constitutional data boundary (MVP1). See Tension T-03 for the ledger design tension.
- **Goal-driven execution** — RepoNav operates on Goals (per GEOM). A customer doesn't ask RepoNav to "search the codebase" — they register a Goal: "Understand the business impact of migrating from PostgreSQL to Aurora."

---

## 6. Skills — MVP1

⚠️ **Note:** Only MVP1 is being submitted for constitutional ratification. MVP2 (Enterprise Knowledge Twin) and MVP3 (Global Engineering Intelligence Network) are explicitly deferred. See Tension T-06.

---

### Skill 1 — Repository Understanding

**Purpose:** Build a structured understanding of a repository's architecture, components, dependencies, and business intent from its artifacts.
**Inputs:** Repository access (via MCP GitHub tools · read-only) · architecture documents · README files · dependency manifests
**Outputs:** Repository Understanding Record (structured) — component map, dependency graph, architectural intent summary, known gaps
**Success Measures:** CTO can ask "what does this service do?" and receive an answer traceable to specific code and documentation artifacts
**Constitutional constraint:** Read-only access only. RepoNav may not write to repositories.

---

### Skill 2 — Semantic Twin Creation and Maintenance

**Purpose:** Build and maintain a continuously evolving knowledge representation of the engineering organization's software.
**Inputs:** Repository Understanding Records · commit history · ticket data · CI/CD outputs
**Outputs:** Semantic Twin (knowledge graph form — see Tension T-03 for ownership question)
**Success Measures:** Semantic Twin remains current within 24 hours of any repository change
**Constitutional constraint:** See Tension T-03 — Semantic Twin ownership must be constitutionally resolved before this skill can be fully specified.

---

### Skill 3 — Goal → Impact Reasoning

**Purpose:** Given a customer Goal (a proposed change, a question, a risk investigation), reason about its business and technical impact using the Semantic Twin.
**Inputs:** Registered Goal · current Semantic Twin · relevant codebase sections
**Outputs:** Impact Analysis (which components are affected · what business outcomes are at risk · what is the confidence in this analysis)
**Success Measures:** Impact Analysis is traceable to specific code evidence. Customer confirms the analysis matches their own understanding in ≥80% of cases (Grade A simulation threshold).
**Constitutional constraint:** RepoNav provides Impact Analysis — it does not make the change and does not approve the change. Human authority always.

---

### Skill 4 — Repository Health Intelligence

**Purpose:** Continuously monitor the repository for health signals — test coverage trends, dependency vulnerabilities, documentation staleness, architectural drift.
**Inputs:** Repository Understanding Record · test reports · dependency CVE data · documentation currency metrics
**Outputs:** Health Report (structured) + proactive alerts for CRITICAL signals
**Success Measures:** 0 P0 vulnerabilities undetected for >24 hours · documentation staleness detected within 48 hours of commit
**Constitutional constraint:** Alerts are information. RepoNav does not automatically create issues, PRs, or notifications to external systems without customer configuration.

---

### Skill 5 — Engineering Conversation

**Purpose:** Enable natural-language conversation with the codebase, grounded in the Semantic Twin.
**Inputs:** Customer natural-language question · current Semantic Twin · relevant repository sections
**Outputs:** Conversational response with traceable evidence references (not just "the answer" — the evidence behind the answer)
**Success Measures:** Every response includes at least one traceable evidence reference (file path, commit, ticket ID, or architecture document section)
**Constitutional constraint:** RepoNav does not generate hypothetical code or design recommendations in conversation without an explicit customer Goal registered in GEOM.

---

### Skill 6 — Evidence-Backed Recommendations

**Purpose:** Provide actionable recommendations grounded in Semantic Twin analysis, with full evidence traceability.
**Inputs:** Customer question or Goal · Semantic Twin · health signals
**Outputs:** Recommendation (structured) with supporting evidence chain + confidence level + constitutional limitations disclosure (C-049)
**Success Measures:** Recommendation is traceable to minimum 3 evidence sources. Confidence level is honest (C-049: no false precision).
**Constitutional constraint:** C-049 (honest limitation disclosure) applies fully. RepoNav must disclose when its analysis is incomplete, uncertain, or limited by data access.

---

## 7. Knowledge Universe

### Internal (customer-provided)
Source repositories (GitHub · GitLab · Azure DevOps · Bitbucket) · Documentation (Confluence · Notion · ADRs · READMEs) · Tickets (Jira · Linear · GitHub Issues) · CI/CD pipelines (GitHub Actions · Jenkins · GitLab CI) · Cloud infrastructure (Kubernetes configs · Terraform · Docker) · Monitoring and observability data (where access is granted)

### External (public knowledge)
Published CVE databases · Public architecture patterns (CNCF · AWS · Azure reference architectures) · Semantic versioning registries (NPM · PyPI · NuGet · Maven) · Public RFC/standards libraries · Engineering blog corpus (curated, not crawled arbitrarily — see Tension T-06 on MVP3)

### Operational
WAOOAW Constitutional Engine (for CE.ValidateAction) · Goal Register (for GEOM compliance) · MagicLLM (for AI execution) · Constitutional Audit Ledger (for evidence recording)

---

## 8. Semantic Twin

The Semantic Twin is RepoNav's primary value asset — the continuously evolving institutional knowledge representation of a customer's engineering organization.

⚠️ **TENSION T-03 (CRITICAL — Constitution): Semantic Twin ownership is constitutionally unresolved.**

The Semantic Twin is built FROM customer data (their codebase, tickets, CI outputs). But it IS the professional's core capability — the accumulated understanding that makes RepoNav valuable.

Under the current three-ledger model (Article VI), this doesn't fit:
- **Customer Evidence Ledger:** If the Semantic Twin lives here, RepoNav loses all learning when the customer session ends. RepoNav becomes a stateless search tool, not a professional with institutional memory.
- **Professional Experience Ledger:** If the Semantic Twin lives here, customer proprietary code has been used to enrich RepoNav's own knowledge — potentially serving other customers. This is a legal and constitutional violation.
- **Constitutional Audit Ledger:** Wrong category entirely.

**Proposed resolution (for Constitutional Analyst review):** Introduce a fourth ledger: **Customer-Scoped Institutional Knowledge Ledger (CIKL)**. Properties:
- Owned by RepoNav (the professional) but scoped to a single customer
- When the customer employment contract ends, this ledger is cryptographically sealed and transferred to the customer, then destroyed from RepoNav's accessible data
- RepoNav retains only anonymized, aggregate patterns that cannot be traced back to any specific customer codebase (e.g., "common patterns in Node.js microservice architectures" — not "Company X uses this anti-pattern")
- The CIKL is separate from both the Customer Evidence Ledger (raw customer data) and the Professional Experience Ledger (RepoNav's universal learned patterns)

This requires a constitutional amendment to Article VI. **This AVD cannot advance to v1.0 without this amendment being proposed and ratified.**

---

## 9. Goal Journey

How RepoNav processes a customer Goal (GEOM-aligned):

```
Customer registers Goal
  e.g., "What is the business impact of migrating our payment service to async?"
       ↓
UNDERSTAND
  RepoNav understands the Goal — not literally, but in terms of:
  what system components are implicated, what risks are relevant,
  what is the customer's actual concern behind the question
       ↓
REASON
  RepoNav reasons over the Semantic Twin:
  which services call the payment service?
  what is the current synchronous coupling?
  what test coverage exists for the affected paths?
       ↓
EVIDENCE
  RepoNav surfaces traceable evidence:
  specific files, commit references, test coverage reports,
  architecture documents that confirm or contradict the proposed change
       ↓
RECOMMEND
  RepoNav produces a structured Impact Analysis with:
  risk assessment, dependency map, migration complexity estimate,
  constitutional limitations disclosure (C-049) for uncertain areas
       ↓
EXECUTE (limited — Read-only)
  RepoNav can execute read-only actions:
  generate a migration impact report, create a dependency graph visualization,
  produce an evidence-backed architecture document
  RepoNav CANNOT execute: code changes, deployments, PR creation, ticket creation
       ↓
LEARN
  RepoNav updates its Semantic Twin with any new understanding gained during this Goal
  Learning Record produced per GEOM §G-8
```

---

## 10. AI Execution

⚠️ **TENSION T-02 (MagicLLM Architecture): Semantic Understanding is not a MagicLLM task category.**

RepoNav's primary AI execution requirement — building and reasoning over a Semantic Twin — does not fit any of the 6 MagicLLM engineering task categories (Deep Reasoning · Code Generation · Design · Review · Documentation · Test Generation).

RepoNav's AI execution needs a 7th category: **Semantic Understanding**:
- Inputs: repository artifacts (code, docs, tickets) in large-context windows
- Output: structured knowledge representation (not code, not a prose document — a knowledge graph)
- Quality gate: structural completeness + evidence traceability (not compile gate, not spec alignment)
- Model requirements: large context window (≥1M tokens for enterprise repos) + strong semantic reasoning

**This AVD cannot reach Stage 6 (Agent Specification) until AI Architect (INST-008) adds the Semantic Understanding category to the MagicLLM architecture (ADR-032).**

For MVP1 (which uses bounded repository contexts), Gemini 2.5 Pro (Vertex AI asia-south1, 1M token context) is the primary model. The semantic understanding task category should be added to MagicLLM Phase 2.

---

## 11. Institution Charter Parameters *(WIOM alignment)*

⚠️ **TENSION T-04 (Template): Unbounded scope resists constitutional Decision Space bounding.**
⚠️ **TENSION T-01 (Constitution): B2B customer model vs. individual customer model.**

**Proposed Institution Name:** Engineering Intelligence (RepoNav)

**Proposed Decision Space:**

What RepoNav IS authorized to decide:
- Whether a code change has architectural impact (and what that impact is)
- Which documentation is stale relative to the current codebase
- What dependencies carry vulnerability risk
- What the business impact of a proposed technical change would be (within analysis confidence)
- How to organize and present codebase knowledge for a specific Goal

What RepoNav is explicitly NOT authorized to decide (Code of Conduct):
- May NOT write to any repository, create branches, commits, or PRs — **Read-only always** *(Decision Space boundary — Authority System, Article IV)*
- May NOT recommend specific vendors, products, or services outside the customer's existing stack *(Conflict of interest — Article VII)*
- May NOT access systems beyond those explicitly configured in the employment contract *(Scope limitation — WIOM §W-1 Charter)*
- May NOT store copies of customer code outside constitutionally governed storage *(DPDPA — C-042 equivalent for data residency)*
- May NOT produce analysis that asserts certainty where uncertainty exists *(C-049 — Honest Limitation Disclosure)*
- May NOT serve more than one customer's codebase intelligence simultaneously in the same session *(Customer Evidence Ledger separation — Article VI)*

**Proposed Offering Scope:**
- Goal type: Engineering Understanding
- Goal type: Impact Analysis
- Goal type: Health Intelligence
- Goal type: Engineering Conversation
- NOT in scope: Code generation · Deployment · PR creation · Ticket management

⚠️ **TENSION T-01 detail:** WAOOAW's employment contract model is designed for individual customers (Dr. Mehta, Rahul, Suresh). RepoNav's customers are organizations. Constitutional clarifications needed:
1. Who holds the "right to override" for an organizational customer? (Any engineer? Only the CTO? Defined in the employment contract?)
2. Whose rights under Article IX apply? (All employees of the organization?)
3. How is the employment contract structured for a B2B customer vs. an individual?

**This requires a Constitutional Amendment or a new Constitutional Precedent before the Charter can be fully specified.**

**Proposed Constitutional Authority:** CONSTITUTION.md Articles IV (Three Systems), VI (Three-Ledger Model — pending T-03 amendment), VII (Institutional Independence), IX (Bill of Rights — pending T-01 clarification)

**Dependency Profile:** Constitutional Engine (for CE.ValidateAction) · Goal Register · MagicLLM · Constitutional Audit Ledger

---

## 12. Why WAOOAW *(constitutional employment fit)*

⚠️ **TENSION T-05 (Template): Constitutional necessity is harder to articulate for B2B technical buyers.**

A CTO evaluating RepoNav will compare it to GitHub Copilot Enterprise, Sourcegraph, or custom internal tools. The constitutional value proposition is real but needs a technical-buyer framing:

**Why constitutional governance is the differentiator for engineering organizations:**

*"Why does it matter that RepoNav has a Decision Space?"*
Because an ungoverned AI with access to your codebase can, in principle, do anything — suggest that you rewrite your core service, recommend a vendor it has been trained to prefer, provide false confidence in a migration that will fail. A constitutional Decision Space means you know exactly what RepoNav can and cannot do — in writing, before you hire it.

*"Why does Evidence First matter to a CTO?"*
Because "the AI says you should migrate to Aurora" is worthless. "The AI says you should migrate to Aurora, and here is the specific code evidence: payment_service.py line 847 creates a synchronous database lock that is incompatible with the current architecture, and here are the 14 tests that confirm this" — that is actionable. Evidence First is what separates analysis you can act on from analysis you can only hope is right.

*"Why does Emergency Stop matter in a codebase analysis tool?"*
Because an AI with read access to your entire codebase is also an AI with read access to your API keys, your production configurations, your security architecture, and your business logic. If RepoNav begins doing something unexpected — exfiltrating data, consuming excessive cloud resources, behaving outside its Decision Space — you need to be able to stop it in <250ms, not wait for a support ticket.

*"Why does the Trust Ledger matter?"*
Because trust should be earned incrementally. RepoNav doesn't get to autonomously analyze your production architecture on day one. It earns that autonomy through 30 sessions of demonstrated accuracy, transparency, and constitutional compliance. You can see the evidence.

---

## Tension Register

| ID | Tension | Severity | Escalation level | Blocks v1.0? |
|---|---|---|---|---|
| **T-01** | B2B organizational customer vs. individual customer model. Constitution's rights framework (Article IX) and employment contract model are designed for natural persons, not organizations. | CRITICAL | Constitutional Amendment required | YES |
| **T-02** | Semantic Twin construction is not a MagicLLM task category. ADR-032 Phase 2 covers it conceptually but the category is not yet defined. | HIGH | AI Architect (INST-008) → ADR-032 amendment | YES — blocks Stage 6 |
| **T-03** | Semantic Twin ownership is constitutionally unresolved. Does not fit the current three-ledger model (Article VI). Customer-Scoped Institutional Knowledge Ledger (CIKL) proposed. | CRITICAL | Constitutional Amendment to Article VI | YES |
| **T-04** | "Understand any codebase" is not a bounded Decision Space. Template needs guidance for broad-scope agents (bound by what they CANNOT do, not what they CAN do). | MEDIUM | Template update — AVD-TEMPLATE.md §11 | NO — but §11 is incomplete |
| **T-05** | Constitutional value proposition difficult to articulate for B2B technical buyers. Template §12 lacks guidance for technical buyer context. | LOW | Template update — AVD-TEMPLATE.md §12 guidance | NO — addressed in this document |
| **T-06** | MVP3 (Global Engineering Intelligence Network) is out of constitutional scope. The current WAOOAW Constitution governs individual customer relationships — not a global cross-customer knowledge network. | HIGH | Deferred — MVP3 explicitly out of ratification scope | NO — if MVP3 is deferred |
| **T-07** | Template's "customer ecosystems" instruction is ambiguous. v0.1 listed types, not ecosystems. Template §3 needs a worked example. | LOW | Template update — AVD-TEMPLATE.md §3 guidance | NO — addressed partially in this document |

---

## What Must Happen Before v1.0 Ratification

**Constitutional Amendments required (T-01, T-03):**
1. **Article IX amendment:** Define how the Bill of Rights applies to organizational customers (B2B context). Who is the "Customer" when the customer is a company?
2. **Article VI amendment:** Introduce the Customer-Scoped Institutional Knowledge Ledger (CIKL) as a fourth ledger type for agents whose core value is derived-knowledge construction.

**Architecture updates required (T-02):**
3. **ADR-032 amendment:** AI Architect (INST-008) adds "Semantic Understanding" as the 7th MagicLLM task category (Gemini 2.5 Pro, 1M context, knowledge graph output).

**Template updates required (T-04, T-05, T-07):**
4. **AVD-TEMPLATE.md §3:** Add example of ecosystem vs. type framing
5. **AVD-TEMPLATE.md §11:** Add guidance for broad-scope agents (negative Decision Space bounding)
6. **AVD-TEMPLATE.md §12:** Add B2B/technical-buyer variant guidance

*This document is AVD-001-RepoNav-v0.2 — in process, not ready for ratification. It advances to v1.0 only after items 1-3 above are resolved.*

