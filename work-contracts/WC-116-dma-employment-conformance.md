# WC-116 - DMA Package A Employment Conformance Implementation

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Implementing office | Platform IT Expert (INST-010) |
| Status | IMPLEMENTATION SPECIFICATION COMPLETE - FOUNDER ACCEPTANCE AND CURRENT-SESSION IMPLEMENTATION AUTHORIZATION REQUIRED |
| Parent enterprise requirement | `architecture/reference/components/dma-onboarding-and-autonomous-operation-enterprise-requirements.md` |
| Controlling work component | `architecture/reference/components/dma-employment-conformance-work-component.md` `1.0.0-candidate.1` |
| Generic baseline | WC-115; domain-adapter OpenAPI `1.0.0-candidate.2` |
| Delivery unit | One bounded Package A implementation PR |
| Constitutional basis | C-001, C-023, C-026, C-035, C-041, C-049, C-059, C-063, C-065, C-066, C-070, C-071, C-079, C-080, C-094; ADR-049; ADR-051 |
| Activation authority | None |
| Deployment authority | None |

## 1. Objective

Implement Package A so DMA Release 1 supplies exact employment semantics for WC115-R024, R025, and
R026 through the unchanged generic WC-115 domain-adapter contract. The implementation must reconcile
the active DMA source conflicts, bind an exact immutable manifest, implement all six domain-adapter
operations for Skills 0/1/2, and prove conformance without inventing product, authority, consent,
scoring, provider, schema, or ownership decisions.

This contract does not authorize runnable implementation by itself. Before changing `src/`, tests,
generated artifacts, migrations, build outputs, or executable configuration, the Platform IT Expert
must ask:

> This would begin writing implementation code. Do you authorize WC-116 implementation for the current session?

Only an explicit current-session Founder confirmation opens implementation.

## 2. Authorized Outcome

After separate authorization, WC-116 may:

- reconcile the canonical DMA specification and dependent active references to the Package A stable
  IDs and enterprise 1-10 maturity contract;
- implement DMA-specific semantics behind the existing generic adapter boundary;
- add the digest-bound DMA manifest, requirement set, dependency graph, conformance fixtures, and
  direct tests needed by Package A;
- use existing BP/PR generated clients only where WC-115 already assigns ownership;
- add Docker-only validation evidence and the WC-116 requirement ledger; and
- prepare a disabled-by-default exact-head PR for Founder review.

## 3. Invariants And Exclusions

1. BP remains the public facade and relationship/state owner.
2. The adapter owns domain interpretation only.
3. WC-115 schemas, operations, commands, phases, owner order, errors, and generated-client ownership
   remain unchanged.
4. The enterprise ten-dimension 1-10 maturity contract controls; no runtime selection between 1-7 and
   1-10 is permitted.
5. Stable semantic skill IDs are durable identity; numeric labels are migration aliases only.
6. `UNKNOWN`, stale, partial, disputed, unavailable, and blocked never become ready or success.
7. Trial and hire remain separate and neither grants external side-effect authority.
8. WBE, CE, PR, AIR, oauth-vault, and admission authorities remain unchanged.
9. Emergency Stop remains independent and late results after Stop are not admitted.
10. Candidate behavior stays default-off.

Excluded: activation, deployment, provider login/mutation, publication, advertising spend, lead
contact, customer traffic, Package B-E, new shared platform contracts, new deployables/databases,
unrelated refactors, dependency upgrades, PR approval, and merge.

## 4. Required Inputs And Preconditions

| Order | Input | Required state |
|---:|---|---|
| 0 | Fresh `origin/main`, process controls, office card | Current and digest-valid |
| 1 | Parent enterprise requirements | Merged; status ready for Solution Architect |
| 2 | Controlling Package A work component | Founder accepted; version/digest pinned |
| 3 | WC-115 solution, implementation, OpenAPI, and ledger | Merged; R024-R026 remain the only agent-specific reserved scope |
| 4 | DMA agent specification, prompt catalogue, dependency register, billing profile, image concept, admission record | Present; conflicts inventoried |
| 5 | Exact admitted DMA Release 1 tuple | Professional, manifest, adapter, protocol, OCI, source, and evidence identities available without placeholders |
| 6 | `work-contracts/WC-116-requirements.yaml` | Contract digest matches; Docker ledger validation PASS |
| 7 | Current-session Founder implementation authorization | Explicitly recorded before any runnable change |

Failure of any precondition stops implementation. The implementer may not substitute a tag, display
label, fixture, stale evidence, or inferred value.

## 5. Permitted Surfaces

Only dependency-complete changes directly required by WC116 requirements are allowed:

| Purpose | Permitted surface |
|---|---|
| Canonical DMA behavior | `architecture/reference/agents/digital-marketing-agent.md` |
| Prompt references | `architecture/reference/prompts/digital-marketing-agent-prompts.md` |
| Dependency references | `architecture/reference/skill-dependency-register.md` |
| Image/manifest reference repair | `architecture/dma-agent-image-concept.md` and owning admission/catalogue records |
| DMA adapter implementation | `src/agent-adapters/digital_marketing/**` |
| Shared adapter runtime only when required by unchanged generic contract | `src/agent-adapters/runtime_contract/**` |
| DMA adapter tests | `tests/agent-adapters/**` and existing DMA adapter fixture surfaces |
| Generic conformance fixtures | Existing DMA, Trading, and Tutor contract-fixture surfaces |
| Validation evidence | `validation/evidence/wc116/**` |
| Contract/ledger | This WC and `work-contracts/WC-116-requirements.yaml` |

The Package A-owned artifacts use these exact paths unless an already-accepted repository manifest
owns the same artifact at a single different canonical path. Any such conflict is a stop; the
implementer does not create a second copy.

| Artifact | Exact Package A path |
|---|---|
| Employment manifest | `src/agent-adapters/digital_marketing/contracts/employment-interface-manifest.v1.json` |
| Induction requirements | `src/agent-adapters/digital_marketing/contracts/induction-requirements.v1.json` |
| Dependency graph | `src/agent-adapters/digital_marketing/contracts/dependency-graph.v1.json` |
| Degradation profile | `src/agent-adapters/digital_marketing/contracts/degradation-profile.v1.json` |
| Adapter semantics | `src/agent-adapters/digital_marketing/employment.py` |
| Direct Package A tests | `tests/agent-adapters/test_dma_employment_conformance.py` |
| Cross-profession fixtures | `tests/fixtures/conversational-employment/agents/` |

Changes to BP, PR, CE, WBE, AIR, Web, infrastructure, workflows, generic OpenAPI, or databases are
prohibited unless a concrete mismatch proves WC-115 was not implemented as accepted. Such a mismatch
is a stop and requires a separately authorized repair, not scope expansion inside WC-116.

## 6. Delivery Components

### WC116-00 - Bind Baseline And Authority

**Inputs:** Section 4.

**Actions:**

1. Verify exact origin and accepted controlling digests.
2. Verify WC-115 generic operations and R024-R026 reserved state.
3. Resolve the admitted DMA type/version/image tuple from authoritative records.
4. Record current-session Founder implementation authority.
5. Run the WC-116 ledger and changed-surface preflight in Docker.

**Output:** immutable baseline evidence.

**Exit:** no placeholder, conflict, missing digest, stale authority, or unapproved input.

### WC116-01 - Reconcile Canonical DMA Sources

**Dependency:** WC116-00.

**Actions:**

1. Replace the active Skill 1 1-7 maturity model with the enterprise ten-dimension 1-10 model.
2. Add stable IDs and versions for Skills 0/1/2; retain numbers only as aliases.
3. Update active prompt references to stable IDs and 1-10 semantics without changing prompt
   authority.
4. Reduce the dependency register to dependency ownership and stable references.
5. Align billing, image, admission, and active fixtures to references rather than duplicate behavior.
6. Archive or mark obsolete duplicate catalogues non-normative after proving no live consumer.
7. Preserve all eight enterprise capability buckets in the customer catalogue while keeping every
   non-Package-A bucket explicitly planned or unavailable.

**Outputs:** one human-readable skill authority and a conflict/disposition inventory.

**Tests:** active-source uniqueness, stable-ID reference, obsolete-score, and duplicate-behavior scans.

**Exit:** no active 1-7 Package A score, collision, phantom Skill 3, or duplicate normative meaning.

### WC116-02 - Create Exact Manifest And Dependency Graph

**Dependency:** WC116-01.

**Actions:**

1. Create manifest version `1.0.0` using the unchanged generic schema.
2. Bind immutable governance references and digests.
3. Declare exact induction, planning, operations, and scenario fields from the work component.
4. Bind stable skills, dependencies, modes, side effects, evidence, cost/usage references, and
   degraded behavior.
5. Create the digest-bound transitive dependency graph.
6. Refuse PASS scenario entries until their evidence exists.

**Outputs:** manifest, dependency graph, deterministic digest/build binding.

**Tests:** schema closure, deterministic serialization/digest, exact tuple, missing/stale/mixed-major,
and placeholder rejection.

**Exit:** manifest and graph tests PASS with candidate still unavailable/default-off.

### WC116-03 - Implement Manifest And Induction Operations

**Dependency:** WC116-02.

**Actions:**

1. Implement `getEmploymentInterfaceManifest`.
2. Implement `getInductionRequirementSet` with DMA-IND-001 through DMA-IND-017.
3. Verify service assertion, purpose, server-derived tenant/relationship, and exact tuple before
   resolving domain meaning.
4. Preserve mandatory/optional, confirmation class, stable skill impact, and deferral rules.
5. Return only generic WC-115 envelopes and closed errors.
6. Resolve conditional requirements to the schema's boolean `mandatory` value from selected skills.

**Tests:** complete/partial induction, mandatory deferral denial, optional bounded deferral,
wrong-purpose, cross-tenant/relationship, stale manifest, and not-found equivalence.

**Exit:** WC115-R024 agent-specific semantics PASS.

### WC116-04 - Implement Plan Validation

**Dependency:** WC116-03.

**Actions:**

1. Implement `validatePlanCandidate`.
2. Validate exact versions, supported goals/milestones/skills, confirmed/deferred inputs, calendar
   semantics, evidence/limitations, and Package A side-effect exclusions.
3. Return only `VALID`, `PARTIAL`, `INVALID`, or `UNKNOWN`.
4. Keep plan acceptance and owner mutation outside the adapter.

**Tests:** complete valid matrix, partial/deferred matrix, prohibited-skill/side-effect invalids,
stale/mismatch unknowns, and idempotent replay/conflict.

**Exit:** every closed plan rule has a direct executable oracle.

### WC116-05 - Implement Material Change Classification

**Dependency:** WC116-04.

**Actions:**

1. Implement `classifyMaterialChange`.
2. Apply every protected and DMA-specific material category in the work component.
3. Return exact affected stable skill/work references.
4. Require renewed agreement for `MATERIAL` and `UNKNOWN`.
5. Never mutate, accept, relock, or resume work.

**Tests:** one positive and one negative boundary per material category, ambiguous unknown, bounded
non-material tolerance, and zero owner mutation.

**Exit:** WC115-R025 semantics PASS for plan and material change.

### WC116-06 - Implement Dependency Isolation

**Dependency:** WC116-02.

**Actions:**

1. Implement `evaluateDependencyIsolation`.
2. Resolve transitive impact from the adapter-owned digest-bound graph.
3. Compare rather than trust caller candidate impacts.
4. Return `PROVEN_BOUNDED`, `NOT_BOUNDED`, or `UNKNOWN`.
5. Fail closed on graph/version/evidence uncertainty.

**Tests:** each dependency class, transitive impact, shared gate, incomplete caller list, stale graph,
unknown node, unrelated skill continuation, and cross-customer isolation.

**Exit:** no unrelated work continues without proof and no dependent work continues on `UNKNOWN`.

### WC116-07 - Implement Maturity And Performance Assessment

**Dependency:** WC116-03.

**Actions:**

1. Implement the ten dimension result contract and exact equal-weight calculation.
2. Enforce the 7/10 publication threshold and evidence-coverage display.
3. Preserve evidence class, freshness, confidence, limitations, disputes, and successor corrections.
4. Implement `getPerformanceAssessment`.
5. Derive customer outcome and DMA professional performance independently.
6. Require diagnosis/corrective proposal after two missed review periods.

**Tests:** 0-6/10 in-progress, 7-10/10 scoring, rounding, no hidden weight, missing-as-unknown,
benchmark non-influence, correction lineage, stale/disputed evidence, attribution limitation,
outcome/performance divergence, and old 1-7 rejection.

**Exit:** WC115-R026 assessment semantics PASS.

### WC116-08 - Integrate Six Operations

**Dependencies:** WC116-04 through WC116-07.

**Actions:**

1. Wire all operations through the existing runtime contract.
2. Preserve WC-115 generated-client ownership, errors, idempotency, timeout, retry, and reconciliation.
3. Emit privacy-safe structured telemetry.
4. Enforce no durable customer store, public endpoint, credential, or authority cache in the adapter.

**Tests:** provider/consumer contract, deterministic regeneration where applicable, operation identity,
timeout/possible-outcome, restart/replay, error closure, log/trace/metric redaction.

**Exit:** exact generic OpenAPI contract passes with no handwritten duplicate DTO.

### WC116-09 - Prove Generic Conformance And Journeys

**Dependency:** WC116-08.

**Actions:**

1. Run DMA, Trading, and Tutor fixtures through unchanged generic schemas.
2. Execute trial and hire induction/planning/operations journeys.
3. Execute outage, stale, duplicate, replay, cross-tenant, cross-relationship, cross-instance,
   mixed-major, Stop, late-result, correction, rollback, and accessibility/customer-state journeys.
4. Prove two customers share one admitted DMA artifact without state or Stop crossover.
5. Prove Web and WhatsApp reuse the same BP operations, relationship versions, idempotency, customer
   states, secure handoff, and Stop semantics without a DMA-specific channel branch.

**Exit:** all positive and negative Package A oracles PASS; no generic contract contains DMA fields.

### WC116-10 - Freeze And Qualify

**Dependency:** WC116-09.

**Actions:**

1. Freeze exact candidate identity.
2. Run dependency-complete repository Docker qualification.
3. Bind evidence to image, manifest, adapter, protocol, source, environment, command, and result.
4. Complete `WC-116-requirements.yaml`.
5. Verify candidate remains default-off with no activation/deployment input.

**Exit:** every requirement PASS on one immutable candidate.

### WC116-11 - Author Review And Founder Handoff

**Dependency:** WC116-10.

**Actions:**

1. Re-read the complete diff against the enterprise requirements, work component, WC-115, and this WC.
2. Review correctness, scope, authority, failure behavior, security, privacy, tests, rollout,
   rollback, and downstream effects.
3. Repair every finding and rerun affected Docker checks.
4. Push final commit, bind author review to the exact 40-character remote head, and prepare the PR
   body with `scripts/prepare_pr_body.py`.

**Exit:** author review PASS, exact remote-head precheck PASS, PR open for Founder review.

## 7. Canonical Requirement Index

| Requirement | Normative outcome |
|---|---|
| WC116-R001 | Implementation starts only from accepted inputs, exact digests, valid ledger, and explicit current-session authority. |
| WC116-R002 | Scope remains Package A Skills 0/1/2 and the six unchanged adapter operations. |
| WC116-R003 | Active DMA sources contain one canonical skill authority and no conflicting 1-7 maturity contract. |
| WC116-R004 | Stable skill IDs/versions replace numeric labels as durable identity. |
| WC116-R005 | Manifest binds the exact professional, adapter, protocol, OCI, source, and evidence tuple without placeholders. |
| WC116-R006 | Manifest governance, induction, planning, operations, dependency, and conformance declarations are complete and digest-bound. |
| WC116-R007 | Induction implements DMA-IND-001 through DMA-IND-017 with exact mandatory, confirmation, impact, and deferral semantics. |
| WC116-R008 | Plan validation returns only valid, partial, invalid, or unknown from the closed Package A rules and never accepts a plan. |
| WC116-R009 | Material-change classification covers every protected/DMA category, identifies bounded impact, and never mutates or resumes work. |
| WC116-R010 | Dependency isolation uses a transitive digest-bound graph, distrusts caller completeness, and fails closed on unknown. |
| WC116-R011 | Maturity uses ten equal dimensions, 1-10 scores, >=7 publication coverage, one-decimal audit, nearest display, and successor correction. |
| WC116-R012 | Missing evidence remains unavailable and cannot become a low score, hidden weight, unsupported benchmark, or success. |
| WC116-R013 | Customer outcomes and DMA professional performance remain separate, evidence-based, and limitation-aware. |
| WC116-R014 | All six operations conform to the unchanged generic OpenAPI with closed errors and no duplicate DTO or public adapter route. |
| WC116-R015 | Tenant, relationship, instance, purpose, assurance, version, and idempotency boundaries fail closed before domain logic. |
| WC116-R016 | Timeout, disconnect, duplicate, replay, restart, and late-result paths reconcile once-logically without blind retry. |
| WC116-R017 | WBE, CE, BP, PR, AIR, oauth-vault, admission, and Stop authorities remain unchanged. |
| WC116-R018 | Trial/hire remain separate; neither permits publication, spend, provider mutation, lead contact, activation, deployment, or traffic. |
| WC116-R019 | DMA, Trading, and Tutor pass one unchanged generic contract and no platform schema or branch is DMA-specific. |
| WC116-R020 | Two customer instances remain isolated while sharing one exact admitted artifact; Stop does not cross instances. |
| WC116-R021 | Privacy-safe telemetry, PII minimization, public/read-only acquisition, and closed diagnostics pass. |
| WC116-R022 | Candidate remains disabled by default and rollback preserves prior behavior, append-only history, and evidence. |
| WC116-R023 | Every requirement has immutable, exact-candidate Docker evidence in the WC-116 ledger. |
| WC116-R024 | Complete author review repairs all findings and binds PASS to the exact remote head. |
| WC116-R025 | PR handoff contains no self-approval, merge, activation, deployment, provider access, or customer-traffic action. |

## 8. Validation

All authoritative commands run in repository-owned Docker runners. The implementation plan must use
the validation catalogue to select focused gates and end with the dependency-complete qualification
command applicable at execution time.

At minimum:

```bash
docker compose run --rm test-runner \
  python scripts/validate_requirement_ledger.py \
  --ledger work-contracts/WC-116-requirements.yaml \
  --contract work-contracts/WC-116-dma-employment-conformance.md
```

Required evidence families:

- contract/schema and deterministic digest;
- owner-local unit tests;
- generated provider/consumer contract tests;
- maturity calculation/property tests;
- generic DMA/Trading/Tutor conformance;
- trial/hire journey tests;
- negative authority/tenancy/version/idempotency tests;
- outage/reconciliation/Stop/rollback tests;
- privacy, security, observability, accessibility, and constitutional gates;
- final exact-candidate Docker qualification.

No host Python, Node, .NET, virtual environment, ad hoc image, or prose-only PASS is authoritative.

## 9. Definition Of Done

- [ ] All Section 4 preconditions pass.
- [ ] Every WC116 requirement has direct immutable evidence.
- [ ] Canonical source conflicts are removed or archived as non-normative.
- [ ] The six generic adapter operations implement the exact Package A semantics.
- [ ] The enterprise 1-10 maturity contract passes all calculation and negative tests.
- [ ] DMA, Trading, and Tutor pass unchanged generic contracts.
- [ ] Security, privacy, isolation, replay, failure, Stop, rollback, and customer-safe-state tests pass.
- [ ] Candidate remains default-off and no excluded action occurred.
- [ ] Author review is PASS on the exact remote head.
- [ ] Prepared PR is open for Founder review; the author has not approved or merged it.

## 10. Stops

Stop immediately for any condition in the controlling work component Section 23, or when:

- implementation would touch a prohibited surface;
- a requirement lacks a direct executable oracle;
- a current-session Founder implementation authorization is absent;
- the ledger digest or evidence identity does not match;
- a failed focused gate is proposed to be skipped or threshold-reduced;
- a source conflict would be hidden by runtime branching;
- a provider, infrastructure, data-schema, or generic-protocol decision is needed; or
- final qualification cannot run in an approved Docker runner.

Record the blocker; do not compensate, infer, widen scope, or continue dependent work.

## 11. Rollback

Before candidate freeze, revert only WC-116-owned changes to the last executable milestone. After
freeze, any repair creates a new candidate and reruns affected dependency closure. Runtime rollback
is Founder-controlled: disable the existing candidate gate, fence new candidate work, reconcile
in-flight operations, retain append-only history/evidence, and preserve prior protocol behavior.

## 12. Author Review Record

Status: PASS for the architecture package authored by the Chief Solution Architect. The later
implementation author review remains a separate WC116-11 obligation bound to its exact remote head.

The review must verify:

- every enterprise requirement in Sections 1-20 is preserved or explicitly excluded by Package A;
- WC115-R024/R025/R026 and all six operations are fully specified;
- implementation has no unresolved product, scoring, consent, provider, schema, or ownership choice;
- dependencies, states, errors, retries, reconciliation, security, observability, tests, rollout,
  rollback, exclusions, and stops are complete; and
- no implementation or activation authority is implied by architecture acceptance.

### 12.1 Findings And Repairs

| Finding | Repair |
|---|---|
| Compatibility tuple invented a reconciled specification-revision suffix | Preserved revision `3.1` or an explicitly Founder-approved successor; prohibited silent revision advance |
| Conditional induction requirements did not map deterministically to the generic boolean field | Defined selected-skill resolution to exact `true`/`false` values |
| Public observation was framed as customer permission rather than scoped, terms-compliant evidence acquisition | Recast as an owner-bound public-observation scope and customer-visible notice |
| Package A did not explicitly preserve all eight customer-facing capability buckets and later-package disposition | Added customer catalogue and deferred-package trace with non-Package-A states fixed to planned/unavailable |
| Web/WhatsApp reuse and concrete artifact ownership were insufficiently explicit | Added channel-reuse acceptance and exact Package A artifact paths with duplicate-path stop |

### 12.2 Architecture Author Review Result

The complete work component, Work Contract, and requirement ledger were re-read against the parent
enterprise requirements, WC-115, the DMA image/instance concept, the canonical Skills 0/1/2
specification, the Solution Architect professional standard, and the Package A acceptance boundary.
After the repairs above, the package has no unresolved scope, authority, identity, scoring, consent,
interface, state, failure, security, privacy, operability, test, rollout, rollback, or handoff gap.

**Result: PASS - Founder review remains required; implementation remains unauthorized.**
