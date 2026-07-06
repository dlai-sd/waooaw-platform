# Constitutional Precedents Register

**Authority:** Derived from The Constitution of WAOOAW

**Status:** Active — Updated as Constitutional Discovery cases are conducted

**Owned by:** Founder (deliberation and ratification)

**Classification:** Binding on all Architecture Decision Records

---

## How This Register Works

Constitutional Precedents are durable interpretations of the Constitution, established through the Constitutional Discovery process and ratified by the Founder.

Every Architecture Decision Record must cite the Constitutional Precedents it implements.

A precedent cannot contradict the Constitution. It interprets it.

A precedent cannot be revoked by engineering convenience. It can only be superseded by a new precedent or a constitutional amendment, both requiring Founder deliberation.

---

## Precedent Classification

**CP — Constitutional Precedent**

Durable interpretation binding on architecture.

**CD — Constitutional Discovery**

A discovery made during a case that has been reviewed but does not rise to a full precedent. Recorded for traceability.

---

## Precedents

---

### CP-001 — Pre-Employment Rights Visibility

**Source:** Simulation 001 — Dr. Mehta Dental Clinic

**Constitution Articles:** Article IX (Bill of Rights), Article IX (Customer Rights), Article XIV (Constitutional Chain)

**Discovery:** The Constitution grants Customer Rights from the moment of hiring. But customers evaluate and exercise judgment about those rights *before* hiring. A customer who cannot see the authority boundaries, override rights, and termination rights during evaluation cannot give informed constitutional consent at the moment of hiring.

**Precedent:** Constitutional rights that govern an employment relationship must be made visible to prospective customers before the Employment Contract is formed. Pre-employment rights visibility is a constitutional obligation, not a product feature.

**Architectural consequence:** The hiring and evaluation flow must present Constitutional Floors and Customer Rights before the customer reaches the contract signing step. This is not optional UX. It is constitutionally required.

---

### CP-002 — Shadow Authority as Earned Evidence

**Source:** Simulation 001 — Dr. Mehta Dental Clinic

**Constitution Articles:** Article III (The Second Law), Article XIII (The Continuous Trust Cycle), Article VI (Three-Ledger Model)

**Discovery:** A customer, without any platform mechanism, invented a shadow authority trial — asking the professional to demonstrate what it *would* have done before granting authority to act. This behavior is constitutionally correct: it applies the Second Law precisely. Authority earned through demonstrated judgment. But the institution had no formal support for this pattern.

**Precedent:** A "Proposed Action" evidence state must exist as a first-class institutional concept. A digital professional must be capable of demonstrating intended behavior before being licensed to execute it. This shadow mode produces evidence that the customer can evaluate before granting authority expansion. Authority is never assumed from capability. It is earned through demonstrated behavior under observation.

**Architectural consequence:** Evidence states must formally include: `Proposed` (shadow demonstration), `Awaiting Approval`, `Approved`, `Rejected`, `Executed`. The `Proposed` state is the shadow authority trial mechanism. Architecture must support this natively, not as a workaround.

---

### CP-003 — Scope-Boundary Confirmation

**Source:** Simulation 001 — Dr. Mehta Dental Clinic

**Constitution Articles:** Article IX (Customer Rights — right to transparency), Article X (Professional Duties — must be transparent about every decision), Article VII (Doctrine of Institutional Independence)

**Discovery:** A customer approved an out-of-scope action (a pricing post) without fully understanding the constitutional implications of that approval. The professional correctly escalated by requesting explicit confirmation. However, the escalation was initiated by the professional's constitutional duty, not by a platform mechanism. Without that duty, the approval would have been recorded and executed without informed consent.

**Precedent:** When a professional is asked to act at or beyond the boundary of its licensed scope, simple approval is not sufficient. The platform must surface a scope-boundary confirmation request that explicitly states the boundary being crossed and obtains acknowledgment from the customer. The constitutional record must show that the customer understood they were approving a scope-boundary action, not merely that they approved.

**Architectural consequence:** Scope-boundary triggers must produce a mandatory confirmation flow, distinct from a standard approval flow. The confirmation must name the boundary being crossed. Standard approval without boundary acknowledgment is not constitutionally valid for out-of-scope actions.

---

## Constitutional Discoveries (Not Yet Precedents)

The following discoveries were made but have not been elevated to full precedents. They are recorded for institutional traceability.

---

### CD-004 — Renewal as Governed Re-consent

**Source:** Simulation 001 — Month 3

**Observation:** The customer renewed the Employment Contract after reviewing evidence. This renewal was constitutionally clean. However, the renewal was presented as a contract renewal, not as a re-consent event. The distinction matters: renewal is a commercial event; re-consent is a constitutional one. The customer should be explicitly renewing constitutional consent — including reviewing authority levels — not merely continuing a subscription.

**Status:** Under deliberation. May rise to CP-004.

---

### CD-005 — Embodiment Change Notification Standard

**Source:** Case 001 — Month 6

**Observation:** When the professional's underlying model changed, the platform notified the customer. The customer accepted. The constitutional observation was that consent was not required for an embodiment change that preserved the profession and responsibilities. But the notification content was not constitutionally specified. What must be communicated? What must not be implied? What constitutional assurances must the notification make?

**Status:** Under deliberation. May rise to CP-005.

---

## Case 002 Discoveries

---

### CD-006 — Creative Identity as Protected Customer Right

**Source:** Case 002 — Sana Mirza, Beauty Artist

**Constitution Articles:** Article IX (Bill of Rights), Article V (Identity and Embodiment)

**Observation:** The Constitution does not explicitly name creative identity as a customer right. For sole-proprietor creative businesses, the customer's personal aesthetic IS the service. A professional operating in this context must be constitutionally bounded by the customer's creative identity, not merely by capability limits. The Creative Standard Profile functions as a constitutional document — it defines the boundary of professional authority.

**Status:** Under deliberation. Likely rises to CP-006. May require constitutional amendment.

---

### CD-007 — Concurrent Engagement Protocol

**Source:** Case 002 — Week 3

**Constitution Articles:** Article VI (Three-Ledger Model), Article IX (Customer Rights)

**Observation:** When both customer and professional are actively engaged on the same channel, there is no constitutional protocol governing scheduling priority, duplication prevention, or evidence classification. The professional improvised a graceful resolution. But improvisation is not constitution. The Employment Contract must define concurrent engagement rules explicitly.

**Status:** Under deliberation. Architectural implications significant for content scheduling design.

---

### CD-008 — Third-Party Data in Customer Archives

**Source:** Case 002 — Week 5

**Constitution Articles:** Article VI (Three-Ledger Model), Article VII (Doctrine of Institutional Independence), Article IX (Customer Rights)

**Observation:** Professional onboarding involves accessing historical customer content that may contain identifiable third-party individuals who did not consent to processing by an autonomous digital professional. The three-ledger model addresses customer data ownership but does not address third-party data rights embedded within customer archives. This is a privacy gap with genuine constitutional and potentially regulatory implications.

**Status:** Under deliberation. May require constitutional amendment. Escalated to Founder as potentially the most significant discovery in Case 002.

---

### CD-009 — Creative Standard Calibration Period

**Source:** Case 002 — Month 2

**Constitution Articles:** Article IX (Customer Rights — right to transparency), Article X (Professional Duties)

**Observation:** A creative standard approved at Week 1 is a hypothesis, not fully informed consent. The customer cannot know what they do not know about their own creative voice until they see it imperfectly reproduced. Corrections during the early engagement period do not constitute rejection of work — they constitute refinement of an inherently provisional standard. The institution needs a formal calibration period where the Creative Standard Profile is explicitly provisional and amendments are expected, not exceptional.

**Status:** Under deliberation. Likely rises to CP-009.

---

### CD-010 — Split Authority Mode

**Source:** Case 002 — Month 3 Renewal

**Constitution Articles:** Article III (Second Law), Article IV (Three Systems)

**Observation:** The current authority model treats professional actions as complete units — the professional produces and distributes content. Some customers require split authority: the customer retains creative production while delegating operational distribution to the professional. This Customer-Created, Professional-Distributed mode is not currently supported in the Employment Contract or authority model.

**Status:** Under deliberation. Architectural implications for authority model design.

---

### CD-011 — Suspension vs Termination

**Source:** Case 002 — Month 6

**Constitution Articles:** Article V (Identity and Embodiment), Article VI (Three-Ledger Model), Article IX (Customer Rights — data portability)

**Observation:** Non-renewal is not termination. Seasonal businesses require the ability to pause employment without losing accumulated institutional memory — the Creative Standard Profile, vocabulary record, aesthetic calibration, evidence history. Requiring full re-onboarding on seasonal return destroys the Trust Cycle's compounding value. The Employment Contract lifecycle must support a Suspended state distinct from Terminated.

**Status:** Under deliberation. Likely rises to CP-011. Critical for seasonal business models.

---

## Precedent Index

| ID | Title | Source | Status |
|---|---|---|---|
| CP-001 | Pre-Employment Rights Visibility | Case 001 | Ratified |
| CP-002 | Shadow Authority as Earned Evidence | Case 001 | Ratified |
| CP-003 | Scope-Boundary Confirmation (Mandatory) | Case 001, re-affirmed Case 002 | Ratified |
| CD-004 | Renewal as Governed Re-consent | Case 001 | Under deliberation |
| CD-005 | Embodiment Change Notification Standard | Case 001 | Under deliberation |
| CD-006 | Creative Identity as Protected Customer Right | Case 002 | Under deliberation |
| CD-007 | Concurrent Engagement Protocol | Case 002 | Under deliberation |
| CD-008 | Third-Party Data in Customer Archives | Case 002 | Under deliberation |
| CD-009 | Creative Standard Calibration Period | Case 002 | Under deliberation |
| CD-010 | Split Authority Mode | Case 002 | Under deliberation |
| CD-011 | Suspension vs Termination | Case 002 | Under deliberation |

---

*This register is updated after every Constitutional Discovery case.*

*Precedents are ratified by the Founder. Discoveries are recorded by the Chief Engineer.*
