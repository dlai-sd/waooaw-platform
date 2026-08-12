# Founder Proposal: Low-Risk Constitutional Fast Path

**Status:** FOUNDER-AUTHORIZED LOW-RISK TOOLING IMPLEMENTATION - no high-risk activation
**Date:** 2026-08-10
**Prepared by:** INST-013 orchestration context
**Decision owner:** Founder / Registrant
**Implementation status:** AUTHORIZED FOR CURRENT SESSION - deterministic low-risk tooling only
**Constitutional basis preserved:** C-006, C-008, C-031, C-032, C-051, C-065, C-071, C-077, C-083, C-084, C-085
**Existing mechanisms reused:** `knowledge/index.md`, ADR-019, `sprint-context/index.json`, `scripts/build_sprint_index.py`

---

## 1. Purpose

Reduce interactive institutional orchestration time and token consumption for low-risk work without weakening BOOTSTRAP, prospective authority, Institutional Decision Spaces, independent review, evidence provenance, implementation gates, Founder control, or deployment separation.

This proposal responds to observed interactive-session overhead: repeated full-file discovery, repeated BOOTSTRAP-adjacent reads after readiness, excessive subagent fan-out, non-persisting write attempts, and long uncompacted sessions. It does not classify constitutional or implementation work as low risk merely because the requested edit is small.

## 2. Non-Negotiable Boundary

The fast path begins only **after** each context completes the mandatory sequence:

1. read `constitution/BOOTSTRAP.md`;
2. read `README.md` and extract Epoch, Gate, Authorized Office, and Engineering Status;
3. read `constitution/PROJECT_STATE.md`;
4. declare READY or BLOCKED; and
5. occupy an authorized Office with a declared Decision Space and Constitutional Obligations.

The index, RAG, a context packet, memory, a prior conversation, or a previous context's READY declaration cannot replace these steps.

## 3. Applicability

### 3.1 Eligible Low-Risk Work

The fast path may route only work that is already within the occupied Office's current Decision Space and requires no new institutional authority:

| Eligible class | Examples | Required control |
|---|---|---|
| Retrieval and routing | Locate controlling claim, ADR, Work Contract, Office Knowledge Specification, or current record | Index/RAG result plus decisive source verification |
| Mechanical status inspection | Git/PR/check status, identifier availability, timestamp ordering, record presence | Deterministic command or structured API result |
| Formatting and consistency validation | Markdown links, G-10 field presence, whitespace, stale live-status wording | Deterministic validation; no semantic decision |
| Orchestration preparation | Build a bounded context manifest, group same-order authorized work, prepare a review handoff | No GOA issuance, Acceptance, review verdict, or implementation authorization inferred |
| Mechanical checkpointing | Record a result already decided by independently published evidence | Exact evidence links; no reinterpretation or self-approval |
| Documentation correction | Correct a live document that contradicts an already published accepted result | No historical record rewrite and no policy or architecture change |

Eligibility is fail-closed. If classification is uncertain, use the ordinary constitutional path.

### 3.2 Excluded High-Risk Work

The fast path must never perform, compress, combine, or bypass:

- BOOTSTRAP or Office occupancy;
- constitutional interpretation, amendment, discovery, or claim ratification;
- GOA issuance, Goal Acceptance, Registrant acknowledgement, or Participation Window creation;
- independent Business, Constitutional, Enterprise Architecture, security, legal, or deployment review;
- ADR authorship, repair, approval, acceptance, or silent amendment;
- immutable Contribution, Learning, Acceptance, Acknowledgement, review, blocker, or constitutional evidence rewriting;
- Decision Space reassignment or separation-of-duties relaxation;
- creation or modification of an agent spec, skill, prompt, MCP, hook, or always-on instruction;
- source, test, migration, OpenAPI, generated-client, build, infrastructure, provider, secret, deployment, or production change;
- policy defaults, customer rights, commercial truth, billing, financial computation, authority, identity, authentication, privacy, Emergency Stop, or Evidence First decisions;
- self-review, self-approval, self-merge, or substitution of RAG output for authoritative evidence; or
- any task classified as high risk by the Constitution, GEOM, an accepted ADR, the Work Contract, the Execution Plan, or the occupied Office.

## 4. Fast-Path Retrieval Model

### 4.1 Index First

After READY, read the existing pre-computed or task-specific context index before searching the repository. The context entry must identify:

- goal, Work Contract, phase, order, and task;
- occupied Office and its Office Knowledge Specification;
- controlling PROJECT_STATE checkpoint;
- exact source files and section anchors;
- relevant claims and ADRs;
- current GOA/Acceptance/evidence references, when already published;
- allowed and excluded files;
- required validations;
- model hint: `none`, `auto`, or `reasoning`; and
- source commit and generation timestamp.

### 4.2 RAG Second

Use RAG only to locate relevant evidence within the indexed boundary. Retrieval must be query-specific and budgeted. Each result must retain:

- source path;
- source section;
- source version or commit;
- retrieval timestamp;
- relevance score when available; and
- provenance class: authoritative source, accepted decision, immutable evidence, current checkpoint, or informative context.

RAG output is a locator, not authority. Before a decision or edit, verify the smallest decisive section in the authoritative source.

### 4.3 Context Budget

Reuse the existing sprint-context budget as the initial ceiling:

| Context class | Initial budget |
|---|---:|
| Mandatory BOOTSTRAP sequence | Outside fast-path budget; always loaded directly |
| Task context manifest | 500 tokens |
| Authoritative source excerpts | 3,000 tokens |
| Supporting accepted evidence | 1,000 tokens |
| Total post-BOOTSTRAP task context | 4,500 tokens |

If the task cannot be resolved within this budget, the context must state why and move to the ordinary path. It must not silently omit controlling evidence.

## 5. Low-Risk Execution Procedure

1. **Classify:** Confirm the task appears in Section 3.1 and no Section 3.2 exclusion applies.
2. **Route:** Load one task context manifest from the index.
3. **Retrieve:** Query RAG only inside the manifest's source boundary.
4. **Verify:** Read the smallest decisive authoritative sections directly.
5. **Hypothesize:** State one falsifiable local hypothesis and one cheap disconfirming check.
6. **Act once:** Make one bounded edit or perform one mechanical action.
7. **Validate immediately:** Run the narrowest deterministic check before more reading or editing.
8. **Checkpoint:** Record branch, commit, completed step, validation, remaining step, and exclusions.
9. **Escalate:** Stop and return to the ordinary path on ambiguity, failed authority, conflicting evidence, semantic review need, or scope expansion.

## 6. Context And Subagent Economy

### 6.1 One Context Per Real Contribution

Use an institutional subagent only when a distinct authorized contribution or independent review is constitutionally required. Do not create separate contexts for identifier lookup, clerical classification, formatting, persistence, checkpoint wording, PR composition, or mechanical closure when the occupied orchestrating Office already owns that action.

### 6.2 Bundle Within Existing Authority

When a valid GOA already authorizes several outputs in one Participation Window, dispatch them together with:

- exact allowed files;
- exact record IDs and timestamps;
- pinned source commit;
- required verdict or output fields;
- explicit exclusions; and
- file-existence, diagnostics, and diff validation requirements.

Bundling does not combine independent Offices, erase dependency order, or authorize repair after review.

### 6.3 Capability Preflight

Before dispatch, verify that the selected agent can perform the requested action. A read-only exploration agent must never receive a persistence task. A failed persistence attempt creates no institutional contribution and must not be cited as evidence.

## 7. Disconnect-Safe Tracking

Every working increment must be recoverable without conversation history.

### 7.1 Branch Rule

Use a dedicated branch for an approved fast-path proposal or later implementation. Do not mix it with product implementation work.

### 7.2 Checkpoint Rule

At each completed increment:

1. validate the exact changed files;
2. update the proposal's Work Status table;
3. commit with a conventional non-implementation message;
4. push the branch; and
5. leave unrelated local modifications unstaged.

### 7.3 Work Status

| Increment | Status | Evidence |
|---|---|---|
| Cost and latency observation | DONE | Interactive-session analysis completed 2026-08-10 |
| Low-risk boundary drafted | DONE | Sections 2 and 3 |
| Index/RAG retrieval design drafted | DONE | Sections 4 and 5 |
| Disconnect-safe workflow drafted | DONE | Section 7 |
| Founder review | DONE | Founder explicitly authorized implementation of the approved low-risk constitutional fast path for the 2026-08-10 session |
| Constitutional/Office classification | DONE FOR THIS SCOPE | Deterministic standalone tooling only; no skill, hook, agent lifecycle, authority, or semantic decision |
| Deterministic validator implementation | DONE | `scripts/constitutional_fast_path.py`; 15 focused tests and 24 CCT-PIPE-01 checks passed; documented CLI build/validate passed |
| Skill/hook/agent customization | NOT AUTHORIZED | Requires separately governed lifecycle |
| F4 implementation amendment | DEFERRED | Planned after break; separate scope and authority |
| WC-062 institutional handoff follow-up | DONE | Sections 10–12 distinguish material decisions from ministerial orchestration |
| Goal Orchestrator operating-model draft | DONE — PROPOSED | M0–M3 router, Contribution Envelope, accountable executor, and handoff budget drafted |
| Independent constitutional review | NOT STARTED | Required only after Founder selects the design for formalization |
| GEOM / ORGANIZATION activation | NOT AUTHORIZED | Ratified text remains unchanged until independent review and exact Founder ratification |

## 8. Success Measures For A Later Pilot

A separately approved pilot should measure, without relaxing quality:

| Measure | Baseline observed | Pilot target |
|---|---:|---:|
| Institutional subagent contexts per bounded phase | 71 in the analyzed long session | 8-12 |
| Repeated post-READY BOOTSTRAP reads | 145 transcript reads of BOOTSTRAP | One mandatory read per context; zero redundant rereads in the same context |
| PROJECT_STATE reads | 156 transcript reads | One mandatory read plus one source refresh only when checkpoint changes |
| Tool executions | 5,693 | Below 800 for a comparable bounded phase |
| Non-persisting write retries | Multiple | Zero |
| Main interactive session length | Long sessions up to 190 turns; no recorded compaction | New wave or compaction by 25-30 turns |

These are operational targets, not constitutional waivers. Missing a target does not justify bypassing evidence or review.

## 9. Founder Decision Record

On 2026-08-10 the Founder authorized implementation of the approved low-risk constitutional fast path for the current session. The authorization covers deterministic context-manifest tooling and its focused tests and documentation. It does not authorize F4 application implementation, a skill, hook, agent update, semantic authority, provider activation, deployment, or any Section 3.2 exclusion.

Any later expansion or activation beyond this bounded tooling requires the Founder to choose one of:

1. **Reject** - retain the ordinary path unchanged;
2. **Approve a documentation-only pilot** - use the procedure manually for eligible low-risk work, with no new tooling;
3. **Authorize formal classification** - route the proposal to the appropriate Offices to determine required governance artifacts; or
4. **Authorize a later tooling proposal** - separately govern any validator, context-index extension, skill, hook, or agent update.

The implemented tool remains a fail-closed routing aid. This record does not grant institutional authority, alter an Office Decision Space, or make its output authoritative evidence.

---

## 10. WC-062 Follow-Up — Institutional Handoff Finding

**Observation date:** 2026-08-12
**Observed by:** INST-013 Goal Orchestrator
**Status:** PROPOSED OPERATING-MODEL AMENDMENT — not yet ratified

WC-062 specification routing confirmed that the retrieval fast path is necessary but insufficient.
The package legitimately required Product, Solution, Data, Security, integrated EA, and independent
CA decisions. It did not legitimately require a new institutional hop for identifier checks,
timestamp correction, artifact persistence, hash verification, checkpoint wording, review-file
creation, or branch publication.

The session also exposed a second cost pattern: after a material canonical-contract omission was
found, fresh EA and CA verdicts were constitutionally necessary, but clerical defects inside their
draft outputs still had to be corrected and revalidated by the orchestrating context. Treating each
clerical correction as another institutional contribution would add cost without adding
independence or quality.

**Root finding:** GEOM correctly requires accountable authority for institutional decisions, but
its implementation is being over-read as requiring a separate agent context for every action.
Constitutional separation attaches to **material decisions and independent verdicts**, not to
ministerial movement of already authorized evidence.

## 11. Proposed Constitutional Materiality Router

Before creating a new institutional context, INST-013 classifies the requested action by the most
consequential effect it can produce. Classification is fail-closed: uncertainty moves upward.

| Class | Effect | Executor | New institutional context? | Examples |
|---|---|---|---|---|
| `M0 — Ministerial` | Cannot change meaning, authority, scope, risk, acceptance, or immutable evidence | Goal Orchestrator directly | No | Locate IDs; verify timestamps/hashes; persist an attributed verdict; update checkpoint wording; commit/push exact approved artifacts |
| `M1 — Bounded continuation` | Completes or repairs an already authorized contribution without changing its Decision Space, Evidence Specification, acceptance meaning, or package boundary | Existing accountable Institution under the same Contribution Envelope | No new GOA; normally no new context | Fix formatting or an unpublished clerical error; supply a missing field; rerun the same validation; answer a reviewer finding within the accepted scope |
| `M2 — Material contribution` | Creates or changes domain policy, contract behavior, architecture, data/security rules, acceptance meaning, or reviewed canonical bytes | Accountable owner Institution | Yes, one context for the complete contribution | Product decision; canonical API contract; retention policy; threat control; material post-review repair |
| `M3 — Protected decision` | Changes constitutional meaning, authority, Decision Space, immutable evidence, deployment/production state, or issues an independent verdict | Constitutionally designated independent Office or Founder | Yes; ordinary path | CA/EA/security/legal review; GOA/Acceptance; constitutional amendment; implementation authorization; PR approval/merge |

The router classifies the **effect**, not the apparent size of the edit. A one-line authority change
is `M3`; a hundred-line deterministic status reconciliation may remain `M0`.

### 11.1 Materiality Tests

An action is at least `M2` if any answer below is yes:

1. Does it choose or change customer-visible behavior, policy, contract semantics, risk controls,
	 acceptance meaning, or an owner Decision Space?
2. Does it alter canonical bytes already reviewed or relied upon by a later phase?
3. Could a reasonable independent reviewer reach a different substantive verdict because of it?
4. Does it add a new artifact family, component boundary, dependency, constitutional obligation,
	 or implementation scope?

An action is `M3` if it additionally changes authority, constitutional interpretation, immutable
evidence, independent approval, deployment/production state, or Founder-reserved action.

## 12. Goal Orchestrator Operating Model vNext

### 12.1 One Accountable Executor

Each authorized Work Contract or complete Work Component has one primary executor from entry to
delivery closure. INST-013 remains the single orchestration interface to the Registrant and does
not expose routine office-to-office traffic as separate user handoffs.

The primary executor:

- receives one complete Contribution Envelope rather than a sequence of micro-assignments;
- completes all in-scope work, validation, evidence, and non-material repair loops;
- retains continuity until the complete authorized delivery unit is ready for its protected gate;
- does not transfer accountability merely because another Office supplies a bounded input; and
- returns one consolidated result, blocker, or material decision request to INST-013.

For implementation, INST-010 is the primary executor for the complete authorized Work Contract or
Work Component. Internal task boundaries are checkpoints, not new institutional handoffs.

### 12.2 Goal Orchestrator As Execution Coordinator, Not Messenger

Without becoming a domain contributor, INST-013 owns the following ministerial execution work:

- build and pin the complete context/evidence package for each real contribution;
- issue one Contribution Envelope with exact scope, IDs, files, exclusions, and validations;
- group independent same-order contributions into one parallel wave;
- preserve attribution while persisting an independently authored record;
- run deterministic chronology, identifier, hash, presence, and formatting checks;
- correct unpublished clerical defects that do not alter the author's substantive decision;
- maintain the active checkpoint, branch, commits, push, and recovery state;
- route a reviewer finding directly to the accountable owner without an intermediate messenger
	context; and
- present one consolidated decision or acknowledgement request to the Registrant.

These actions are orchestration evidence, not domain contributions. INST-013 may not use this rule
to select policy, repair substantive owner decisions, alter a verdict, or self-review.

### 12.3 Contribution Envelope

A GO Authorization may contain one complete Contribution Envelope:

| Field | Requirement |
|---|---|
| Delivery unit | Complete Work Contract, Work Component, or constitutionally indivisible contribution |
| Material decisions | Exact decisions the Institution owns |
| Outputs | All expected artifacts and records, bundled |
| Continuation authority | In-scope repair and rerun permitted during the Participation Window |
| Material-change triggers | Conditions requiring a new amendment, owner decision, or downstream re-review |
| Validation | Deterministic checks plus any protected independent gate |
| Closure | One consolidated Contribution and Learning Record unless the contract requires atomic records |

An in-scope `M1` repair does not require a new GOA, Acceptance, or Participation Window. A repair
after publication is linked as a correction record under the same envelope. A material `M2` repair
invalidates only the downstream reviews that relied on the changed bytes; it does not restart
unaffected upstream contributions.

### 12.4 Review Economy

Independent review remains mandatory where the Constitution, Work Contract, risk class, or
Execution Plan requires it. Review is performed once against the complete fixed package, not once
per internal increment.

| Situation | Required route |
|---|---|
| Unpublished clerical defect | Primary executor or INST-013 corrects; same validation reruns |
| Reviewer finds in-scope owner defect | Direct return to owner under the active envelope; same reviewer confirms |
| Material canonical change after review | Re-run only reviews downstream of that changed artifact |
| New Decision Space, authority, constitutional, security, legal, or deployment decision | Ordinary independent path; no compression |
| Complete implementation component | One implementation evidence package, then required independent reviews in a single review wave |

No Office may review its own substantive contribution. Multiple protected reviewers may run in
parallel when their Decision Spaces are independent and the fixed package is identical.

### 12.5 Handoff Budget And Stop-Loss

Every Execution Plan declares a handoff budget before routing:

- one institutional context per real `M2` contribution;
- one context per required `M3` independent verdict;
- zero contexts for `M0` actions;
- normally zero additional contexts for `M1` continuation work; and
- one reserve context for a material repair per contribution before INST-013 must re-plan.

INST-013 records actual versus budgeted contexts, tool calls, elapsed time, and rework causes at
phase closure. Exceeding the budget does not waive quality; it triggers consolidation or explicit
re-planning before more contexts are dispatched.

## 13. Proposed Constitutional Text Changes

This design requires a narrow amendment to ratified GEOM and the INST-013 charter. It does not
change BOOTSTRAP, Decision Spaces, independent review, implementation authorization, Founder
control, or the self-participation prohibition.

### GEOM

Add a **Materiality and Contribution Envelope** rule under Stage G-4 and §6:

> A GO Authorization authorizes one complete Contribution Envelope. INST-013 must not issue a new
> authorization or create a new institutional context for ministerial orchestration or an in-scope
> bounded continuation. New routing is required only for a material contribution, protected
> decision, expired/reclaimed Participation Window, changed Decision Space, or changed package
> boundary. INST-013 may execute ministerial evidence handling while preserving producer
> attribution; such handling is not a contribution and creates no review authority.

### ORGANIZATION

Add to INST-013 Decision Space:

> Constitutional materiality classification; Contribution Envelope construction; deterministic
> evidence validation; attribution-preserving persistence; consolidated checkpointing; handoff
> budget enforcement; and direct repair routing to the accountable owner.

Add to INST-013 Constitutional Obligations:

> Ministerial authority may not change substantive meaning, policy, scope, acceptance, risk,
> immutable evidence, or an independent verdict. Uncertainty is classified upward and routed.

## 14. Adoption Path

Because this proposal changes the ratified institutional operating model and the powers of
INST-013, it is not eligible for self-activation through the low-risk fast path.

The smallest quality-preserving adoption path is:

1. Founder selects this design for formalization.
2. One independent Constitutional Analyst reviews the materiality boundaries, G-13 separation,
	 and compatibility with GEOM/WIOM and the Office Operating Protocol.
3. Founder ratifies the exact amendment text.
4. INST-013 applies the approved GEOM and ORGANIZATION edits mechanically in one commit.
5. Pilot on one specification Work Contract and one implementation Work Contract; compare actual
	 handoffs, cost, elapsed time, rework, and escaped defects with the Section 8 baseline.

No separate Business, Solution, Data, Security, or Enterprise Architecture contribution is needed
unless the CA identifies a concrete conflict in that Office's Decision Space. This is deliberately
one constitutional review, one Founder decision, and one mechanical activation step.