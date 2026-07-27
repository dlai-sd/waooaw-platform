# Constitutional Amendment 002 — Derived Knowledge Principle

**Classification:** Constitutional Amendment — extends CONSTITUTION.md Article VI
**Status:** RATIFIED
**Ratified by:** Yogesh Khandge (Founder)
**Ratification date:** 2026-07-27
**Proposed by:** Constitutional Analyst (INST-002) — GOAL-001 Phase 5 (2026-07-27)
**Triggered by:** RepoNav AVD onboarding — Tension T-03
**Constitutional basis:** CONSTITUTION.md Article VI (Three-Ledger Model) · Article VII (Doctrine of Institutional Independence) · Article II (First Law — trust through evidence)
**Amends:** CONSTITUTION.md Article VI — extends, does not modify

---

## Constitutional Discovery That Triggered This Amendment

During the RepoNav AVD onboarding (Tension T-03), a constitutional gap was found in the Three-Ledger Model (Article VI):

Article VI defines three ledgers: Professional Experience Ledger (owned by the Professional), Customer Evidence Ledger (owned by the Customer), and Constitutional Audit Ledger (owned by the Platform).

RepoNav's core capability — the Semantic Twin — is built FROM customer data (their codebase, tickets, architecture documents) but IS the professional's accumulated understanding that makes the agent more valuable over time. This does not fit cleanly into any existing ledger:

| If Semantic Twin lives in... | Problem |
|---|---|
| Customer Evidence Ledger | RepoNav loses all understanding when a session ends. Every conversation starts from zero. The professional cannot accumulate expertise from working with a customer. RepoNav becomes a stateless search tool, not a governed professional. |
| Professional Experience Ledger | Customer proprietary code has been used to enrich the professional's knowledge — potentially serving other customers. This is both a legal violation and an Article VII violation (the professional benefits from evidence it was not authorized to use across contexts). |
| Constitutional Audit Ledger | Categorically wrong. This ledger contains constitutional events, not professional knowledge. |

**The root tension:** Human professionals face the same situation. A consulting engineer who works with a company's codebase for 3 years develops deep expertise — their Professional Experience Ledger is enriched by that work. But they would not retain a copy of the company's source code after the engagement ends. The knowledge is theirs; the raw material is not.

WAOOAW's Constitution has not yet defined this distinction for digital professionals. This amendment establishes it.

---

## Amendment Text

### A002.1 — The Derived Knowledge Principle

When a Digital Professional's core function involves building understanding from customer data (rather than executing tasks against customer data), the following principle governs:

**The Derived Knowledge Principle:**
> *A digital professional may retain derived professional knowledge from customer engagements in its Professional Experience Ledger. The professional may NOT retain raw customer data beyond the scope of the active engagement. The line between derived knowledge and raw customer data is defined by this amendment.*

This principle resolves the Semantic Twin ownership question: derived knowledge → Professional Experience Ledger. Raw customer data → Customer Evidence Ledger, not to persist beyond engagement.

### A002.2 — Definitions

**Raw Customer Data:** Any artifact, content, or record that originated from the customer's domain and can be attributed to that specific customer. Includes: source code, configuration files, proprietary documentation, ticket content, employee-identifying information, customer business logic, API keys or secrets.

**Derived Professional Knowledge:** Understanding, patterns, structures, and insights produced by the Professional through analysis of raw customer data that:
1. Does NOT contain any raw customer data (no verbatim content, no identifiable customer IP)
2. Could not be used to reconstruct the raw customer data
3. Represents general professional expertise applicable beyond this specific customer engagement

**Semantic Twin:** A structured knowledge representation of an engineering system built by an Engineering Intelligence Professional (such as RepoNav). A Semantic Twin is classified as:
- **Customer-scoped Semantic Twin:** The portion of the Semantic Twin that is specific to one customer's architecture, naming conventions, and implementation details. This is Raw Customer Data and belongs in the Customer Evidence Ledger.
- **Professional-scope derived knowledge:** General architectural patterns, common anti-patterns, language/framework insights, and cross-industry structural knowledge derived from customer work but not traceable back to any specific customer. This belongs in the Professional Experience Ledger.

### A002.3 — Data Lifecycle for Knowledge-Deriving Professionals

For Digital Professionals whose primary function is knowledge derivation from customer data (e.g., Engineering Intelligence agents), the following data lifecycle applies:

| Data type | Where it lives | Retention on contract end |
|---|---|---|
| Raw customer data (code, tickets, configs) | Customer Evidence Ledger | Transferred to Customer via portability provision. Purged from WAOOAW systems within contractual retention period. |
| Customer-scoped Semantic Twin | Customer Evidence Ledger | Same as above — transferred and purged. |
| Professional-scope derived knowledge (anonymized patterns) | Professional Experience Ledger | Retained by Professional. Cannot be used in a form traceable to the originating customer. |
| Constitutional Audit Records | Constitutional Audit Ledger | Immutable. Retained permanently. |

**Anonymization standard for Professional-scope derived knowledge:**
Derived knowledge is considered sufficiently anonymized when:
- No specific customer's name, domain, or identifying characteristics appear in the record
- The knowledge cannot be used to reconstruct any specific customer's system
- The knowledge takes the form of general patterns, statistical observations, or professional expertise rather than specific system descriptions

### A002.4 — Constitutional Constraint on Knowledge Transfer

A Digital Professional may NOT:
- Use customer-specific derived knowledge from Customer A to serve Customer B without Customer A's explicit consent
- Share raw customer data or customer-scoped Semantic Twin data with any other customer or third party
- Retain raw customer data after the contractual retention period, regardless of its potential professional value
- Claim that generalized derived knowledge is proprietary IP that cannot be used for other customers — the Professional Experience Ledger is the professional's, and general expertise derived from work is constitutionally theirs

### A002.5 — Customer's Right to Semantic Twin Portability

Upon contract termination, the Organizational Customer (or individual Customer) has the right to receive a portable export of their customer-scoped Semantic Twin. This is part of the Customer Evidence Ledger portability right under Article IX.

The customer-scoped Semantic Twin export must:
- Be in a documented, machine-readable format
- Include the full knowledge structure that was built from their data
- Be delivered within 30 days of contract termination request

### A002.6 — Audit Trail for Knowledge Classification

Every entry in a knowledge-deriving Professional's Professional Experience Ledger that was derived from a customer engagement must include a metadata record:

```
derivation_source:    [engagement type — not customer identity]
derivation_timestamp: [when knowledge was derived]
anonymization_confirmed: true
customer_traceable:   false
```

The Constitutional Analyst (INST-002) is responsible for auditing compliance with this classification during periodic constitutional review cycles.

---

## What This Amendment Enables

With this amendment ratified:
1. RepoNav's Semantic Twin has a constitutionally defined ownership model
2. Knowledge-deriving agents can accumulate professional expertise across customer engagements without violating customer IP
3. The line between "what the agent learns from you" and "what the agent keeps about you" is constitutionally defined
4. Future agents with similar knowledge-derivation functions (Legal Intelligence, Financial Intelligence, Healthcare Intelligence) have a constitutional framework

## What This Amendment Does NOT Change

- The Three-Ledger Model (Article VI) is extended, not modified
- Customer Evidence Ledger ownership and immutability are unchanged
- Professional Experience Ledger portability is unchanged
- Constitutional Audit Ledger properties are unchanged
- Article VII (Institutional Independence) is unchanged — the professional derives knowledge from evidence; it does not evaluate evidence on behalf of the customer

---

*Proposed by Constitutional Analyst (INST-002) — GOAL-001 Phase 5*
*Pending Founder ratification. Not governing until ratified.*
*Upon ratification, this document becomes a constitutional chapter and its content governs all knowledge-deriving Digital Professionals.*
