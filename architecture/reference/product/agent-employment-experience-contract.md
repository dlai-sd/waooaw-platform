# Agent Employment Experience Contract — Skeleton

**Status:** SKELETON — REQUIRES FOCUSED DERIVATION AND RATIFICATION
**Version:** 0.1-draft
**Program:** GOAL-005
**Work Contract:** WC-052
**Purpose:** Define the invariant customer-facing relationship shared by every WAOOAW professional across WhatsApp, web, mobile, and future supported channels.

> This is not ADR-035's Platform-Agent Contract. ADR-035 governs machine signals between platform services and agents. Agent Base Spec v1.0 governs common agent behavior. This contract governs what a customer may consistently expect from the employment relationship.

## 1. Contract Boundaries

| Contract | Governs | Does not govern |
|---|---|---|
| Agent Employment Experience Contract | Customer journey, rights, relationship state, channel continuity, employment transitions | Domain skill behavior or service-to-agent signal schemas |
| Agent Base Spec | Behavior every agent inherits | Customer-channel composition and employment UX |
| Platform-Agent Contract | Versioned platform signals consumed by agents | Customer-facing journey semantics |
| Agent domain specification | Professional expertise, skills, Decision Consequence Map, domain vocabulary | Generic employment platform behavior |

## 2. Normative Subjects — To Groom

| Clause | Subject | Constitutional basis | Minimum question to resolve | Target gate |
|---|---|---|---|---|
| AEEC-01 | Identity and participants | C-005, C-026, C-034 | Which identifiers and roles remain stable across channels and employment changes? | Foundation |
| AEEC-02 | Pre-employment visibility | C-009, C-012 | Which rights, limits, skills, authority, evidence, and price information precede trial or hire? | Foundation |
| AEEC-03 | Relationship states | C-034, C-038 | What are the legal transitions among prospect, evaluation, trial, active, suspended, and terminated? | Foundation |
| AEEC-04 | Conversation continuity | C-006, C-026, C-035, C-039 | What state is channel-neutral, who owns it, and how is a channel handoff authenticated? | Foundation |
| AEEC-05 | Conversational configuration | C-030, C-039 | What minimum context forms a valid proposed Decision Space in business language? | Foundation |
| AEEC-06 | Trial and demonstration | C-001, C-038, C-049, C-088 | Which rights apply, what data persists, and what must be disclosed before conversion? | Foundation |
| AEEC-07 | Contract formation | C-009, C-030, C-034 | What explicit consent forms employment, and which facts become immutable evidence? | Foundation |
| AEEC-08 | Billing activation | C-023, C-038, C-088, C-090 | Which transition permits charging, and how are retries and idempotency exposed? | Wave 1 |
| AEEC-09 | Evidence visibility | C-002, C-005, C-007, C-037, C-051 | Which decisions, actions, outcomes, limitations, and charges must the customer see? | Wave 1 |
| AEEC-10 | Human Override | C-001, C-024 | How is Emergency Stop continuously reachable and how is its scope expressed? | Foundation |
| AEEC-11 | Alerts and approvals | C-010, C-011, C-029, C-053 | How are materiality, channel choice, deduplication, expiry, and escalation governed? | Wave 2/3 |
| AEEC-12 | Performance and review | C-002, C-003, C-037 | How do business outcomes lead every review while technical metrics remain evidence? | Wave 2/3 |
| AEEC-13 | Lifecycle controls | C-007, C-034, C-038 | What occurs on amend, pause, resume, renew, terminate, and export? | Wave 3 |
| AEEC-14 | Multi-agent boundaries | C-004, C-005, C-026 | How do identity, authority, evidence, budget, stop scope, and handoffs remain independent? | Wave 4 |
| AEEC-15 | Version protection | C-008, C-032, C-094 | What customer notice or consent is required for security, behavioral, and capability changes? | Wave 5 |
| AEEC-16 | Organizational delegation | C-001, C-003, C-041, C-043, C-099 | How are outcome plans, cross-agent dependencies, budgets, and stop conditions contracted? | Wave 6 |

## 3. Cross-Channel Invariants — Candidate Set

These candidates require ratification before becoming normative:

1. One employment relationship has one durable identity across all channels.
2. A channel changes presentation, not rights, authority, evidence, billing, or relationship state.
3. The customer can always discover current authority, active work, material evidence, cost state, and Emergency Stop.
4. A channel handoff requires authenticated continuity and cannot silently merge people, tenants, or conversations.
5. A trial carries constitutional rights from its first consequential interaction.
6. Hire is an explicit evidenced transition; conversation alone cannot silently create a paid relationship.
7. Domain vocabulary may specialize presentation but cannot weaken common rights or hide limitations.
8. Loss of a channel must not destroy the relationship or authorize work that was not previously authorized.

## 4. Required Contract Artifacts — Grooming Outputs

| Artifact | Purpose |
|---|---|
| Relationship state model | Define states, legal transitions, idempotency, and terminal behavior |
| Participant and identity model | Define customer, payer, guardian, operator, steward, agent, and organization roles |
| Channel-neutral conversation envelope | Carry relationship, participant, employment, context, and evidence correlation identifiers |
| Rights and disclosure schedule | Define information visible before trial, hire, amendment, and renewal |
| Consent and contract evidence model | Define which customer decisions become durable constitutional evidence |
| Lifecycle command contract | Define configure, hire, amend, pause, resume, renew, terminate, export, and stop semantics |
| Experience conformance suite | Verify equivalent rights and transitions across supported channels |

## 5. Ratification Exit Criteria

- Every Foundation clause has an approved normative statement and traceability source.
- State and identity models have no ambiguous owner or transition.
- ADR-035 and Agent Base Spec references are explicit and non-duplicative.
- At least one WhatsApp-to-web handoff scenario validates channel invariance.
- At least one trial-to-hire scenario validates consent, billing, evidence, and idempotency.
- Business Architect confirms capability coverage.
- Constitutional Analyst confirms rights and claim traceability.
