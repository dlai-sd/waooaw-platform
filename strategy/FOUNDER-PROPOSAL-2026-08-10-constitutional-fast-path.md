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