# WAOOAW Agent Vision Document (AVD)

> **Purpose:** The Agent Vision Document (AVD) is the canonical business and vision artifact used to design every WAOOAW Agent before implementation.

## 1. Agent Identity
- Agent Name
- Domain
- Vision Statement
- Mission
- Customer Promise

## 2. Why this Agent Exists
Describe the customer problem, why it exists, why existing solutions are insufficient, and why now.

## 3. Customer Universe
Identify customer ecosystems rather than personas.

**What is a customer ecosystem?** An ecosystem is a description of the customer’s operating context: their type, scale, goals, and the specific conditions that create demand for this agent. It goes beyond naming the customer type (e.g., “Startup”) to describe the environment in which the pain point exists.

**Example of type vs. ecosystem:**
- Type: “Startup”
- Ecosystem: “Growth-stage startup (5–50 engineers · fast iteration cadence · technical debt accumulating faster than documentation · engineering institutional knowledge at risk as team grows)”

For each ecosystem, describe:
- Scale and organizational characteristics
- The specific pain point that drives demand for this agent
- What the customer can accomplish with this agent that they cannot accomplish otherwise

**Organizational vs. individual customers:** If this agent’s customers are organizations (not individuals), note this explicitly. Organizational customers are governed by AMENDMENT-001 (B2B Customer Rights). The AVD §11 Charter Parameters must reflect the Authorized Representative model.

## 4. Agent Purpose
A single sentence defining the institutional purpose of the agent.

## 5. Core Principles
- Understanding before automation
- Evidence over assumptions
- Human authority
- Goal-driven execution
- Continuous learning
- Privacy by design

## 6. Skills
Each skill contains:
- Purpose
- Inputs
- Outputs
- Success Measures
- Configurations

## 7. Knowledge Universe
### Internal
Repositories, documentation, tickets, architecture.

### Operational
CI/CD, cloud, monitoring, security.

### External
Standards, public repositories, research, APIs, industry knowledge.

## 8. Semantic Twin
Describe what institutional knowledge the agent maintains and how it continuously evolves.

## 9. Goal Journey
```text
Goal
 ↓
Understand
 ↓
Reason
 ↓
Evidence
 ↓
Recommend
 ↓
Execute
 ↓
Learn
```

## 10. AI Execution
```text
Goal
 ↓
Context Builder
 ↓
Execution Contract
 ↓
AI Execution Layer
 ↓
Validation
 ↓
Evidence
 ↓
Learn
```

## 11. Institution Charter Parameters *(WIOM alignment — mandatory)*

This section is used by Constitutional Analyst (INST-002) to validate the proposed Institution Charter. It becomes the basis for the INST-NNN entry in the Institution Registry upon Founder ratification.

**Proposed Institution Name:** [Canonical name that will appear in Institution Registry]

**Proposed Decision Space (use NEGATIVE bounding for broad-scope agents):**

For agents with inherently broad scope (e.g., “understand any codebase”, “analyze any legal document”), the Decision Space is more clearly defined by what the agent may NOT do than by listing everything it CAN do. Use this format:

*What this agent IS constitutionally authorized to decide:*
[e.g., “Whether a proposed code change has architectural impact and what that impact is”]

*What this agent is explicitly PROHIBITED from deciding or doing (Code of Conduct):*
- May NOT: [explicit prohibition + constitutional source]
- May NOT: [next prohibition]

This negative-bounding approach is especially important for knowledge-deriving agents (AMENDMENT-002 applies) and agents with wide domain coverage.

**Proposed Offering Scope:** [What Goal types this agent may serve — expressed as customer outcome categories]

**Proposed Constitutional Authority:** [Which CONSTITUTION.md Articles and Amendments directly govern this agent]

**Dependency Profile:** [Which upstream Institutions must contribute before this agent acts in a Goal Journey]

**Customer type:** Individual (governed by Article IX directly) | Organizational (governed by AMENDMENT-001 — specify Authorized Representative model)

## 12. Why WAOOAW *(constitutional employment fit — mandatory)*

This section justifies why this agent requires constitutional governance and cannot be a simple LLM wrapper.

**For SME / consumer-facing agents** (Dr. Mehta, Rahul, Suresh model):
Answer: *“Why does this customer need to trust an AI with [their patients / their money / their crop decisions], and what constitutional protections make that trust possible?”*
- Emergency Stop protects against the agent doing something unexpected with real consequences
- Decision Space means the customer knows exactly what the agent will and will not do
- Evidence First means every recommendation is traceable — not just an AI’s opinion
- Trust Ledger means trust is earned incrementally, not assumed on day one

**For B2B / technical-buyer agents** (engineering organization, legal firm, financial institution model):
Answer: *“Why would a CTO, General Counsel, or CFO choose a constitutionally governed agent over an ungoverned AI tool with the same technical capability?”*
- Decision Space: the organization knows exactly what the agent can and cannot do — in a contract, not in a marketing claim
- Evidence First: every analysis is traceable to source evidence, not to model confidence — you can act on it
- Emergency Stop: any employee can halt the agent in <250ms — the organization retains control at all times
- Derived Knowledge Principle (AMENDMENT-002, if applicable): clear constitutional definition of what the agent learns from your data vs. what it retains

**What the customer receives that they cannot receive from an ungoverned AI:**
[The constitutional promise — what is guaranteed by the institution’s charter that no prompt-and-pray system can guarantee]
Learning
```

## 11. MVP Roadmap
- MVP1
- MVP2
- MVP3

## 12. Future Agent Opportunities
Describe adjacent agents and ecosystem expansion.

## 13. Commercial Model
Pricing, deployment models, marketplace offerings, services.

## 14. Why WAOOAW
Explain why this capability is delivered as a governed WAOOAW Agent rather than conventional software.

## 15. Success Metrics
Business outcomes, customer outcomes, institutional learning, and continuous improvement.
