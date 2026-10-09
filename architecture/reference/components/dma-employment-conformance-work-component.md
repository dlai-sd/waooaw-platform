# DMA Package A Employment Conformance Work Component

## Record Control

| Field | Value |
|---|---|
| Authoring office | Chief Solution Architect (INST-005) |
| Status | FOUNDER ACCEPTED - WC-116 IMPLEMENTATION AUTHORIZED 2026-10-09 - ACTIVATION UNAUTHORIZED |
| Version | `1.0.0-candidate.1` |
| Parent requirement | `architecture/reference/components/dma-onboarding-and-autonomous-operation-enterprise-requirements.md` |
| Generic interface baseline | WC-115 Conversational Employment Protocol; domain-adapter contract `1.0.0-candidate.2` |
| Product boundary | DMA Release 1; `professionalVersion: 1.0.0`; specification revision `3.1`; Skills 0/1/2 only |
| Delivery package | Package A - DMA employment conformance |
| Implementing office | Platform IT Expert (INST-010), authorized for the current session by the Founder on 2026-10-09 |
| Authority boundary | Package A implementation and local qualification only. No activation, deployment, provider connection, publication, spend, or customer traffic is authorized. |

## 1. Decision Summary

Package A makes the admitted DMA Release 1 image conform to the existing WC-115 employment interface
without changing WC-115, adding a DMA branch to a platform component, or making any DMA capability
available to customers.

The package supplies DMA-owned meanings for the six existing generic domain-adapter operations:

1. `getEmploymentInterfaceManifest`;
2. `getInductionRequirementSet`;
3. `validatePlanCandidate`;
4. `classifyMaterialChange`;
5. `evaluateDependencyIsolation`; and
6. `getPerformanceAssessment`.

Business Platform remains the public facade and relationship composer. Constitutional Engine remains
the constitutional decision and evidence owner. WBE remains the commercial and Skill-eligibility
owner. Professional Runtime remains the admitted execution, cancellation, reconciliation, and Stop
owner. AIR remains proposal-only. The DMA adapter interprets DMA domain meaning only.

Package A is disabled by default. Conformance evidence, compatibility PASS, admission, and
`activationEligible=true` are evidence and never activation, deployment, or customer-traffic
authority.

## 2. Scope And Exclusions

### 2.1 Included

- canonical identity and version mapping for DMA Release 1 Skills 0/1/2;
- one digest-bound `EmploymentInterfaceManifestV1`;
- one versioned DMA induction requirement set;
- DMA plan validation and material-change classification;
- dependency isolation for Package A dependencies and work;
- separate customer-outcome and DMA-performance interpretation;
- the enterprise-required ten-dimension, 1-10 maturity assessment;
- Package A trial/hire projections through WC-115 `INDUCTION`, `PLANNING`, and `OPERATIONS`;
- DMA, Trading, and Tutor generic-contract conformance fixtures;
- source-consolidation tasks needed to remove conflicting active DMA meanings;
- Docker-only qualification, default-off rollout, rollback, and Founder handoff.

### 2.2 Excluded

- external content publication or scheduling;
- authenticated social, advertising, analytics, CRM, booking, or search-provider mutation;
- advertising spend, wallet funding, audience upload, lead contact, or lifecycle messaging;
- Skills other than 0/1/2 becoming available;
- provider selection, cloud mutation, deployment, DNS, secrets, Production, or customer traffic;
- a new public command, WC-115 phase, generic schema field, deployable, database, or authority owner;
- implementation of Package B1, B2, C, D, or E;
- activation or correction of institutional-only Skill 14;
- rewriting historical evidence or silently rebinding an existing relationship to a new manifest.

### 2.3 Deferred Package Trace

| Enterprise capability | Package A treatment | Owning later package |
|---|---|---|
| Digital Strategy And Marketing Intelligence | Profile, maturity, priorities, and Package A planning only | Package D adds later search/lifecycle strategy depth |
| Content, Creative And Social Media | Strategy, campaign brief, and non-published calendar only | B1 creates content; B2 publishes and measures |
| Paid Media And Campaign Management | Customer-facing planned/unavailable projection only | Package C |
| Marketing Performance And Improvement | Package A assessment meanings only; no live-channel result claim | B2/C/D by activated capability |
| WhatsApp Customer Interface | Same BP owner operations and command semantics; no DMA channel branch | Channel activation remains separately governed |
| Lead Management And Customer Growth | Planned/unavailable projection only | Package C and D |
| Search And Digital Discoverability | Public evidence may inform maturity; no change action | Package D |
| Client, Location And Reputation Operations | Account-mode and primary-location limitation only | Package D/E |

Package A preserves all eight customer-facing buckets in the catalogue projection, but exposes only
the exact qualified Skills 0/1/2 subset as candidate capability. A deferred bucket must state
`PLANNED` or `UNAVAILABLE` with its missing package and must never be advertised as ready.

## 3. Controlling Inputs And Conflict Resolution

### 3.1 Precedence

For Package A, implementers apply the following order:

1. this component's parent enterprise requirements;
2. WC-115 and its accepted generic solution/OpenAPI contracts;
3. the accepted DMA image/instance concept;
4. this work component;
5. the canonical DMA agent specification, prompts, dependency register, billing records, fixtures,
   and admission records after the reconciliations required below.

An implementer must stop rather than choose between conflicting active meanings.

### 3.2 Mandatory Gap Bridges

| Gap | Controlling resolution | Required closure before runtime implementation |
|---|---|---|
| DMA Skill 1 specifies a 1-7 maturity score while the enterprise requirement mandates 1-10 across ten dimensions | The enterprise 1-10 contract controls Package A | Amend the canonical DMA Skill 1 section and every active prompt/fixture/reference to the 1-10 contract; archive or mark the 1-7 model non-normative |
| Current skill numbers contain gaps and collisions | Numbers are migration aliases only | Use the stable semantic IDs in Section 4; no public or durable identity uses `Skill 0`, `Skill 1`, or `Skill 2` alone |
| Dependency register describes an older DMA version and duplicates behavior | It owns dependencies only | Retain dependency inventory, remove normative skill behavior, and reference stable IDs/versions |
| Existing release baseline qualifies exact-seven runtime behavior but WC115-R024/R025/R026 remain Founder-reserved | Existing execution qualification does not provide employment semantics | Implement and qualify the six operations without changing generic WC-115 contracts |
| Exact admitted OCI digest is environment/admission evidence rather than architecture text | A tag or placeholder cannot satisfy compatibility | Resolve the current admitted digest from the accepted admission record at implementation preflight; mismatch or absence stops |
| DMA v3.1 gate-pass exceeds the recorded Founder approval through v3.0 | Gate-pass is not current-version product approval | Package A may reconcile specification meaning but cannot claim v3.1 activation or customer availability |

### 3.3 Canonical Source Disposition

| Record | Package A disposition |
|---|---|
| `architecture/reference/agents/digital-marketing-agent.md` | Sole human-readable DMA behavior authority after 1-10 scoring and stable-ID reconciliation |
| Digest-bound DMA employment manifest | Sole runtime availability and employment-semantics authority for one admitted DMA version |
| `architecture/reference/prompts/digital-marketing-agent-prompts.md` | Prompt content only; references stable IDs and cannot define availability |
| `architecture/reference/skill-dependency-register.md` | Dependency inventory only; references stable IDs and cannot define behavior |
| DMA billing profile/bundles | Commercial references only; WBE remains authority |
| `architecture/dma-agent-image-concept.md` | Image/version/instance/admission model; no duplicate skill behavior |
| Test fixtures | Test inputs and expected outcomes only; never normative authority |
| Historical catalogues | Archive or mark non-normative after proving no live consumer depends on them |

Admission and build gates must reject two active records that disagree on identity, version,
availability, inputs, side effects, mode, dependencies, or authority.

## 4. Package A Identity And Compatibility Tuple

### 4.1 Stable Skill Coordinates

| Migration alias | Stable skill ID | Skill contract version | Package A availability |
|---|---|---:|---|
| Skill 0 | `CUSTOMER_PROFILING` | `1.0.0` | Qualified candidate for trial and hire after all Package A gates |
| Skill 1 | `MARKET_RESEARCH_AND_MATURITY` | `1.0.0` | Qualified candidate for trial and hire after all Package A gates |
| Skill 2 | `CONTENT_STRATEGY_AND_CALENDAR` | `1.0.0` | Qualified candidate for trial and hire after all Package A gates |

The versions above identify the first stable employment-semantics contracts. They do not change
`professionalVersion`, specification revision, product release, or OCI identity.

### 4.2 Required Compatibility Tuple

One Package A candidate binds all of:

```text
professionalTypeId   = DIGITAL_MARKETING_LOCAL_SERVICE
professionalVersion  = 1.0.0
specificationRevision = 3.1 or an explicitly Founder-approved successor
manifestVersion      = 1.0.0
adapterVersion       = 1.0.0
wc115ProtocolVersion = 1.0-candidate
ociDigest            = sha256:<exact admitted digest>
sourceCommit          = <exact 40-character implementation commit>
evidenceDigest        = sha256:<exact qualification envelope digest>
```

`professionalTypeId` must use the exact current admission-catalogue value if that accepted record
differs from the display form above. Such a difference is reconciled in the manifest mapping; the
Platform IT Expert must not rename an admitted identity. Every tuple member is verified independently.
A reconciliation commit or digest must not invent a specification-revision suffix or silently advance
revision `3.1`; a revision change requires its existing agent-lifecycle and Founder approval path.
A display label, tag, compatibility result, or specification revision cannot substitute for another
member.

Compatibility fails closed for a missing value, placeholder digest, unsupported mandatory major,
mixed mandatory majors, stale evidence, identity mismatch, or unresolved active-source conflict.

## 5. Employment Interface Manifest

The manifest implements the existing `EmploymentInterfaceManifestV1` unchanged.

### 5.1 Governance References

Each reference carries `{contractRef, contractVersion, contractDigest}`:

| Manifest field | Required reference |
|---|---|
| `agentSpecification` | Reconciled canonical DMA specification revision and digest |
| `promptPolicy` | DMA prompt catalogue revision and digest after stable-ID/scoring reconciliation |
| `toolProfile` | Package A tool/dependency profile that permits only public/read-only or internal owner routes |
| `decisionConsequenceMap` | Current admitted DMA DCM revision and digest |

Mutable branches, latest tags, unresolved file paths, or missing digests are invalid.

### 5.2 Induction Manifest Values

| Field | Required value |
|---|---|
| `requirementSetVersion` | `1.0.0` |
| `mandatoryContext` | `ACCOUNT_MODE`, `BUSINESS_IDENTITY`, `BUSINESS_DOMAIN`, `PRIMARY_LOCATION`, `PROSPECTIVE_CUSTOMERS`, `THREE_MONTH_ASPIRATION`, `EMPLOYMENT_MODE`, `SELECTED_OUTCOMES` |
| `optionalContext` | `WEBSITE_URL`, `CURRENT_CHANNELS`, `KNOWN_COMPETITORS`, `CURRENT_ENQUIRY_BASELINE`, `TEAM_SIZE`, `CURRENT_AD_SPEND`, `BIGGEST_MARKETING_PAIN`, `PREFERRED_LANGUAGE`, `CONTENT_INPUTS` |
| `dependencyTypes` | `CUSTOMER_CONFIRMATION`, `PUBLIC_OBSERVATION`, `READ_ONLY_CONNECTION`, `CUSTOMER_OWNED_OUTCOME_SOURCE`, `PLATFORM_OWNER_RECORD`, `ADMITTED_CONTRACT` |
| `readinessRules` | Exact rules in Sections 6 and 7; no prose-only or hidden rule |
| `domainSummaryAdapter` | Immutable Package A induction-summary contract reference |

### 5.3 Planning Manifest Values

| Field | Required values |
|---|---|
| `supportedGoalTypes` | `UNDERSTAND_CURRENT_POSITION`, `PRIORITIZE_MARKETING_IMPROVEMENTS`, `PLAN_CONTENT_AND_CAMPAIGNS` |
| `milestoneTypes` | `PROFILE_CONFIRMED`, `MATURITY_ASSESSMENT_REVIEWED`, `PRIORITIES_CONFIRMED`, `CAMPAIGN_BRIEF_ACCEPTED`, `CONTENT_CALENDAR_ACCEPTED` |
| `calendarConstraints` | IANA zone and local/instant/fold/tzdb semantics from WC-115; no publication date is executable authority; reschedule tolerance must be explicit in the accepted plan |
| `materialChangeRules` | Section 10 closed rules |
| `performanceMeasureTypes` | `PROFILE_COVERAGE`, `MATURITY_EVIDENCE_COVERAGE`, `PRIORITY_ACTION_PROGRESS`, `PLAN_REVIEW_TIMELINESS`, `CALENDAR_READINESS` |
| `planAdapter` | Immutable Package A planning contract reference |

### 5.4 Operations Manifest Values

| Field | Required values |
|---|---|
| `operatingCycleTypes` | `UNDERSTAND_OBSERVE_ASSESS_PLAN`, `REASSESS_AND_CORRECT` |
| `workItemTypes` | `PROFILE_CONFIRMATION`, `PUBLIC_PRESENCE_OBSERVATION`, `MATURITY_DIMENSION_SCORING`, `MATURITY_REPORT`, `PRIORITY_RECOMMENDATION`, `CAMPAIGN_BRIEF`, `CONTENT_CALENDAR` |
| `reassessmentTriggers` | material account connection; material business change; accepted review cadence; customer request; disputed evidence/score; stale mandatory evidence |
| `outcomeAdapter` | Immutable Package A outcome contract reference |
| `billingProfile` | Existing WBE-owned DMA Package A billing-profile reference and digest |
| `degradationProfile` | Immutable Package A degradation contract in Section 13 |
| `shorterMissedReviewThreshold` | Omit; generic two-period threshold remains controlling |

### 5.5 Conformance Scenarios

The manifest contains PASS scenarios only after executable evidence exists for:

- complete Package A trial induction and planning;
- complete Package A hire induction and planning;
- optional-input deferral with bounded isolation;
- insufficient maturity evidence producing in-progress rather than a score;
- disputed fact producing a successor assessment;
- dependency loss with bounded unaffected work;
- dependency isolation `UNKNOWN` failing closed;
- stale or incompatible manifest rejection;
- cross-tenant and cross-relationship rejection;
- Trading and Tutor fixtures passing the unchanged generic schema.

Each scenario binds the exact protocol and manifest versions, evidence reference, result, validation
time, and limitations. Before qualification, the candidate manifest must not fabricate PASS entries.

### 5.6 Customer-Facing Catalogue Projection

The BP-owned projection uses the eight enterprise capability labels and ordinary customer language.
For each bucket it shows selected outcome, exact current availability
(`TRIAL_AVAILABLE`, `HIRE_AVAILABLE`, `DEGRADED`, `UNAVAILABLE`, or `PLANNED`), missing input or
package, limitations, and next action. Internal numeric skill labels, adapter operations, manifests,
and component names are not primary customer vocabulary.

Only these Package A projections may become candidate-available after qualification:

- current position and priorities from `CUSTOMER_PROFILING` and
  `MARKET_RESEARCH_AND_MATURITY`;
- a non-published strategy, campaign brief, and calendar from
  `CONTENT_STRATEGY_AND_CALENDAR`.

Every other bucket remains `PLANNED` or `UNAVAILABLE`. Documentation, a manifest declaration, or a
conformance PASS cannot by itself make a bucket available.

## 6. Induction Requirement Contract

Every requirement uses the unchanged `DomainRequirementV1` envelope.

| Requirement ref | Label | Mandatory | Confirmation class | Affected skills | Completion and deferral rule |
|---|---|---:|---|---|---|
| `DMA-IND-001` | Employment mode | Yes | `CUSTOMER` | All Package A | Exact `TRIAL` or `HIRE`; no silent conversion |
| `DMA-IND-002` | Selected business outcomes | Yes | `CUSTOMER` | All selected | Customer language mapped to stable skills; selection grants no authority |
| `DMA-IND-003` | Account mode | Yes | `CUSTOMER` | `CUSTOMER_PROFILING` | One of `SINGLE_UNIT`, `MULTI_UNIT_OWNED`, `FRANCHISE`, `RESELLER`; unsupported mode limitations remain explicit |
| `DMA-IND-004` | Business identity | Yes | `CUSTOMER` | All Package A | Business and owner identity confirmed; registration data is not re-asked without conflict |
| `DMA-IND-005` | Business domain | Yes | `CUSTOMER` | All Package A | Inference remains proposed until confirmation |
| `DMA-IND-006` | Primary location | Yes | `CUSTOMER` | All Package A | Location and applicable service area confirmed |
| `DMA-IND-007` | Prospective customers | Yes | `CUSTOMER` | All Package A | Customer audience described in customer vocabulary |
| `DMA-IND-008` | Three-month aspiration | Yes | `CUSTOMER` | All Package A | Outcome desired; no guaranteed result or invented target |
| `DMA-IND-009` | Website URL | No | `AUTHORITY_SOURCE` | `MARKET_RESEARCH_AND_MATURITY` | Deferral allowed; website dimensions may remain unavailable |
| `DMA-IND-010` | Current channels | No | `CUSTOMER` | `MARKET_RESEARCH_AND_MATURITY`, `CONTENT_STRATEGY_AND_CALENDAR` | Deferral identifies affected observations/planning |
| `DMA-IND-011` | Public-observation scope and notice | Conditional | `OWNER_BOUND_ASSUMPTION` | `MARKET_RESEARCH_AND_MATURITY` | Required when Skill 1 is selected; declares permitted public sources, observation time, terms/access limits, and customer-visible notice without treating the employment agreement as blanket consent |
| `DMA-IND-012` | Read-only connected-account consent | No | `CUSTOMER` | `MARKET_RESEARCH_AND_MATURITY` | Separate, scoped, revocable; no setup or mutation |
| `DMA-IND-013` | Known competitors | No | `CUSTOMER` | `MARKET_RESEARCH_AND_MATURITY` | Named report display requires customer confirmation |
| `DMA-IND-014` | Brand and approved claims | Conditional | `CUSTOMER` | `CONTENT_STRATEGY_AND_CALENDAR` | Required when Skill 2 is selected; missing input pauses Skill 2 only |
| `DMA-IND-015` | Content assets and rights | No | `CUSTOMER` | `CONTENT_STRATEGY_AND_CALENDAR` | Missing assets narrow the plan; no likeness/voice/asset use without rights |
| `DMA-IND-016` | Language and communication preference | No | `CUSTOMER` | All Package A | Default presentation may use relationship language; no fact inferred from language |
| `DMA-IND-017` | Measurement and outcome sources | No | `AUTHORITY_SOURCE` | Assessment and performance | Missing sources disclose attribution limits |

Mandatory requirements cannot be deferred. Optional requirements may be deferred only when
`evaluateDependencyIsolation` proves the affected scope and the response names every paused or
limited skill. `UNKNOWN` is not proof.

`DomainRequirementV1.mandatory` is always a boolean in a resolved relationship requirement set.
Rows marked `Conditional` resolve to `true` exactly when their affected skill is selected and to
`false` otherwise. The adapter must not serialize the word `Conditional` or any third state.

## 7. Induction And Readiness Rules

### 7.1 Phase Readiness

| State | Package A rule |
|---|---|
| Induction incomplete | Any mandatory requirement missing, unconfirmed, stale, conflicted, or incompatible |
| Induction partial | Mandatory profile inputs confirmed; optional inputs deferred with proven bounded impact |
| Induction ready | All mandatory requirements confirmed, exact manifest current, deferred scope explicit, and no unresolved mandatory blocker |
| Skill 0 ready | `DMA-IND-001` through `DMA-IND-008` current and confirmed |
| Skill 1 preliminary | Business name and primary location confirmed; public-observation scope and notice current |
| Skill 1 reportable | At least seven maturity dimensions have sufficient evidence |
| Skill 2 ready to plan | Confirmed profile, selected planning outcome, brand/claim inputs, and current maturity/priorities or an explicit customer-approved no-assessment limitation |

Readiness is domain evidence only. BP composes authoritative readiness with CE, WBE, relationship,
manifest, admission, and other owner state.

### 7.2 Trial And Hire

Trial may produce a confirmed profile, maturity assessment, recommendations, sample campaign brief,
and non-published content calendar. Trial cannot publish, spend, contact leads, mutate provider
accounts, or inherit hire authority.

Hire may perform only admitted Package A behavior. It still requires exact entitlement, readiness,
current authority, confirmed inputs, and constitutional validation. Package A grants no external
side-effect capability in hire mode.

## 8. Maturity Assessment Contract

### 8.1 Scale And Dimensions

The assessment uses the enterprise-required customer-facing 1-10 scale:

1. Not Visible Online
2. Basic Online Listing
3. Online Presence Established
4. Regularly Active Online
5. Building Customer Engagement
6. Generating Leads Online
7. Converting Leads Into Customers
8. Growing Through Digital Marketing
9. Achieving Predictable Digital Growth
10. Leading The Market Digitally

The ten equally weighted dimensions are:

`BUSINESS_DIRECTION`, `ONLINE_PRESENCE`, `SEARCH_VISIBILITY`, `CONTENT_CONSISTENCY`,
`CUSTOMER_ENGAGEMENT`, `LEAD_HANDLING`, `CUSTOMER_RETENTION`, `MEASUREMENT`,
`IMPROVEMENT_DISCIPLINE`, and `GOVERNANCE_AND_TRUST`.

### 8.2 Dimension Result

Each dimension result contains:

- stable dimension ID and assessment version;
- score 1-10 or `NOT_ENOUGH_INFORMATION`;
- evidence references with source class;
- observation time and purpose-relative freshness;
- confidence;
- explanation in customer language;
- limitations and missing inputs;
- whether the fact is verified observation, customer-confirmed, public observation, or professional
  inference; and
- correction lineage when superseding a prior result.

### 8.3 Overall Calculation

1. Score dimensions independently.
2. Compute the arithmetic mean of scored dimensions only.
3. Retain one decimal place for audit.
4. Display the nearest whole-number maturity level.
5. Publish an overall score only when at least seven dimensions are scored.
6. Always publish evidence coverage as `scored dimensions / 10`.
7. If fewer than seven are scored, return `MATURITY_ASSESSMENT_IN_PROGRESS` and the missing evidence.
8. No hidden weights, industry benchmark adjustment, provider grade, or missing-as-zero behavior.
9. A correction creates a successor assessment and preserves the predecessor and reason.

Benchmarks may be shown only when their licensed source, date, method, cohort, confidence, and
limitations are explicit. A benchmark never changes the customer's score.

## 9. Plan Contract

### 9.1 Valid Package A Plan

A plan is `VALID` only when it:

- binds the exact relationship, manifest, requirement set, plan, and source versions;
- uses one supported Package A goal type;
- references only admitted stable skill coordinates;
- maps milestones to selected outcomes and confirmed/deferred induction facts;
- identifies required inputs, dependencies, customer decisions, measures, limitations, and owners;
- contains no external publication, spend, provider mutation, or unavailable skill;
- distinguishes recommendation, draft, customer decision, and authoritative owner state;
- uses complete WC-115 calendar semantics where calendar commitments exist; and
- does not claim maturity, performance, attribution, readiness, or success beyond evidence.

`PARTIAL` means a useful bounded plan exists but named optional work is deferred. `INVALID` means a
closed rule is violated. `UNKNOWN` means current domain meaning cannot be established and fails
closed.

### 9.2 Package A Plan Content

| Plan area | Required content |
|---|---|
| Profile | Confirmed facts, proposed facts, missing facts, source and version |
| Assessment | Assessment version, dimension results, overall/coverage state, evidence and limitations |
| Priorities | Evidence-linked recommended actions ordered by customer outcome, not internal skill number |
| Campaign brief | Theme, customer outcome, audience, window, approved channels, claims, constraints, measures and approval state |
| Calendar | Bounded 30-day plan; local time, IANA zone, instant/fold/tzdb where committed; no execution authority |
| Review | Review period, expected evidence, reassessment trigger and customer-safe next action |

## 10. Material Change Rules

The adapter returns `MATERIAL` for any change to:

- selected customer outcome or three-month aspiration;
- maturity baseline, scoring method, evidence-coverage basis, or disputed material fact;
- target or customer-visible success measure;
- Package A skill set or stable skill version;
- trial/hire mode;
- customer, primary location, account mode, or relationship scope;
- authority, approval, consent, credential, or provider-connection boundary;
- budget or commercial eligibility input;
- campaign theme, audience, channel mix, calendar window, or approved claim after plan acceptance;
- evidence/measurement source when it changes result meaning; or
- any protected WC-115 category.

`NON_MATERIAL` is limited to a change that preserves outcome, baseline, target, authority, skill set,
consent, evidence meaning, and accepted calendar tolerance. It still creates the owner-prescribed
successor record. Unclear classification is `UNKNOWN`, `renewedAgreementRequired=true`, and affected
work stays paused.

The response identifies only affected stable skills and work references. It never changes the plan,
accepts the change, waives confirmation, or resumes work.

## 11. Dependency Graph And Isolation

### 11.1 Dependency Classes

| Dependency | Directly affected work | Safely independent work |
|---|---|---|
| Confirmed profile fact/revision | Every result derived from that fact | Unrelated confirmed facts |
| Public web/search/social observation | Corresponding maturity dimensions and recommendations | Profile confirmation; dimensions with independent evidence |
| Read-only connected account | Corresponding channel dimensions | Public observations and other channel dimensions |
| Customer brand/claim inputs | Campaign brief/calendar using them | Profile and maturity assessment |
| Manifest/admission/adapter compatibility | All Package A operations | No Package A consequential operation |
| WBE eligibility | Funded consequential work | Protected read, Stop, and constitutional paths |
| CE availability | Governed writes and success | Safe reads; Stop remains independent |
| Evidence source freshness | Dependent score, claim, plan measure, or performance result | Results with separately current sources |

### 11.2 Isolation Algorithm Contract

`evaluateDependencyIsolation`:

1. verifies relationship, manifest, dependency, and candidate affected-skill identities;
2. resolves the dependency through the immutable Package A dependency graph;
3. returns `PROVEN_BOUNDED` only when every transitive dependent skill/work reference is identified
   and every claimed unaffected item has no path to the dependency;
4. returns `NOT_BOUNDED` when the dependency reaches additional work or a shared mandatory gate; and
5. returns `UNKNOWN` for missing graph nodes, version mismatch, stale graph/evidence, unresolved
   active-source conflict, or insufficient proof.

No caller-supplied affected list is trusted as complete. The adapter compares it with its own
digest-bound graph. `UNKNOWN` and `NOT_BOUNDED` pause all potentially dependent work.

## 12. Performance And Outcome Interpretation

`getPerformanceAssessment` reports two separate meanings:

### 12.1 Customer Outcome

For Package A, customer outcomes are limited to:

- confirmed profile coverage and resolved information gaps;
- maturity-assessment evidence coverage and supported maturity movement;
- completed priority actions;
- accepted campaign brief/calendar readiness; and
- supported customer decisions and next actions.

Activity, invocation success, tool receipt, report generation, calendar creation, spend, reach,
clicks, or provider acceptance is not automatically a customer outcome.

### 12.2 DMA Professional Performance

Professional performance may assess:

- timeliness against an accepted review or plan commitment;
- completeness against the Package A contract;
- evidence citation and limitation quality;
- correction/reconciliation completion;
- adherence to current authority and accepted plan; and
- whether required reassessment or corrective proposal was produced.

`outcomeState` and `agentPerformanceState` are independently derived. A strong professional process
can coexist with an unknown or missed business outcome; an observed customer outcome cannot erase a
professional failure. Attribution basis, confidence, evidence, limitations, and disputed/stale state
remain explicit. Two missed review periods require diagnosis and a corrective proposal.

## 13. Failure And Degraded-Mode Matrix

| Condition | Safe adapter result | Customer-safe treatment | Prohibited |
|---|---|---|---|
| Exact manifest absent/mismatch | `404`, `409`, or `DOMAIN_EMPLOYMENT_VERSION_UNSUPPORTED` as defined by WC-115 | Capability unavailable; no readiness | Best-effort manifest |
| Optional public source unavailable | Partial assessment with affected dimensions `NOT_ENOUGH_INFORMATION` | Name missing source and coverage | Missing-as-low score |
| Fewer than seven dimensions scored | Assessment in progress | Show coverage and required evidence | Publish overall score |
| Required owner/source unavailable | `DOMAIN_EMPLOYMENT_UNAVAILABLE` | Pending/unavailable with next action | Success-shaped fallback |
| Stale evidence | Dependent result stale/unknown | Request refresh | Reuse for authority or achieved claim |
| Conflicting customer/public fact | Disputed; successor requires correction | Ask customer to resolve | Silently choose |
| Unsupported account mode behavior | Preserve account mode; limit to supported primary-location scope | Honest limitation | Claim multi-location availability |
| Dependency isolation unknown | `UNKNOWN` | Pause potentially affected work | Continue guessed-unaffected work |
| Timeout or possible commit | WC-115 `OUTCOME_UNKNOWN` reconciliation | Pending reconciliation | Blind retry |
| CE unavailable | No governed success/write | Safe reads only; Stop independent | Local authorization |
| WBE stale/ineligible | Consequential work blocked | Commercial attention state | Adapter eligibility calculation |
| Stop | Halt active Package A work and suppress late result | Stopped/reconciliation state | Resume without fresh authority |

## 14. Command-To-Owner Matrix

The existing WC-115 commands are reused unchanged.

| Command | DMA adapter obligation | Other owner sequence | Adapter prohibition |
|---|---|---|---|
| `CONFIRM_INDUCTION_ITEM` | Resolve exact requirement and affected skills | CE validation/evidence, then BP append | Mark confirmation itself |
| `DEFER_INDUCTION_ITEM` | Verify optionality and exact bounded impact | CE validates deferral, then BP append | Defer mandatory requirement |
| `APPLY_CANDIDATE_PATCH` | Run the operation selected by BP-owned patch type | CE validates digest, then BP appends owner state | Select destination or mutate BP |
| `SUBMIT_PLAN_FOR_REVIEW` | Validate exact plan candidate | CE evidence, then BP review transition | Accept plan |
| `ACCEPT_PLAN_VERSION` | Revalidate exact plan and manifest | WBE eligibility, CE evidence, BP agreement | Grant entitlement or authority |
| `ACKNOWLEDGE_MATERIAL_CHANGE` | Classify, then validate successor plan when present | WBE when required, CE evidence, BP relock | Resume affected work |
| `RESCHEDULE_WITHIN_TOLERANCE` | Validate complete calendar commitment and tolerance | CE evidence, BP successor plan | Invent tolerance |
| `REQUEST_REASSESSMENT` | Return exact performance/assessment meaning; classify protected change | CE records request, BP pending transition | Control running work |
| `ACKNOWLEDGE_CORRECTIVE_PROPOSAL` | Verify proposal reference and evidence | CE evidence, BP acknowledgement | Claim correction succeeded |

The adapter never calls CE, WBE, AIR, or a public BP command. It returns domain meaning to BP or the
accepted private caller. WC-115 owner order, idempotency, reconciliation, and error rules remain
unchanged.

## 15. Data And Authority Map

| Record or fact | Owner | Adapter access | Required binding |
|---|---|---|---|
| Employment relationship, mode, selected outcomes | BP | Read delegated context | tenant + relationship + expected version |
| Confirmed profile and corrections | BP | Interpret supplied version | tenant + relationship + immutable revision |
| Manifest and dependency graph | Admitted DMA artifact/admission record | Read local digest-bound contract | professional type/version + manifest/digest |
| Assessment proposal and dimension results | DMA invocation result until accepted | Produce proposed result | relationship + profile revision + evidence refs |
| Authoritative customer assessment projection | BP | None to mutate | relationship + accepted assessment version |
| Plan and material-change state | BP | Validate immutable candidate | relationship + plan version |
| Commercial eligibility | WBE | No direct access or calculation | BP-owned owner step |
| Constitutional decision/evidence | CE | Reference only | action instance + evidence references |
| Invocation/result lineage | PR | Return typed result | relationship + instance + invocation + image digest |
| Provider/customer credentials | oauth-vault | No Package A credential access | Not applicable |

The adapter has no durable customer store, reusable credential, cross-relationship lookup, public
endpoint, or authority cache. Payload minimization follows the selected operation. Telemetry contains
opaque correlation and version identities, never profile, evidence, prompt, or assessment content.

## 16. Interaction Sequences

### 16.1 Manifest And Induction

1. BP supplies server-derived relationship context and exact admitted tuple.
2. Adapter verifies service assertion, audience, purpose, tenant/relationship delegation, and tuple.
3. Adapter resolves the digest-bound manifest; mismatch fails closed.
4. Adapter returns the exact induction requirement set.
5. BP composes customer-visible requirements and records decisions through existing commands.
6. Adapter never records completion or readiness.

### 16.2 Maturity Assessment

1. Confirmed profile and permitted evidence references identify the assessment inputs.
2. DMA distinguishes customer-confirmed, public, read-only, owner-source, and inferred evidence.
3. Each dimension is scored or marked `NOT_ENOUGH_INFORMATION`.
4. Overall score is produced only at coverage >=7/10.
5. Result includes evidence, freshness, confidence, limitations, coverage, and next action.
6. BP records customer review/correction; correction creates a successor version.

### 16.3 Plan Acceptance

1. BP reserves `SUBMIT_PLAN_FOR_REVIEW`.
2. Adapter validates the exact plan and manifest.
3. Invalid/partial/unknown result blocks or limits the owner sequence.
4. CE records submission before BP appends review state.
5. Acceptance repeats exact validation, includes WBE eligibility, CE evidence, and BP append.
6. Adapter never interprets submission or acceptance as execution authority.

### 16.4 Dependency Loss

1. BP supplies the changed dependency and candidate affected skills.
2. Adapter verifies against the digest-bound transitive graph.
3. `PROVEN_BOUNDED` names all dependent skills/work; unrelated work may remain eligible after other
   owners agree.
4. `NOT_BOUNDED` or `UNKNOWN` pauses potentially dependent work.
5. Recovery requires current evidence and a new assessment; no cached success.

### 16.5 Stop And Late Result

1. Existing Stop path halts the PR-managed invocation independently.
2. Adapter cancellation prevents new work and marks any late result non-admissible.
3. PR reconciles invocation state.
4. BP projects stopped/unknown state; CE evidence remains append-only.
5. Resume requires fresh authority and a new permitted invocation, never continuation by the adapter.

### 16.6 Web And WhatsApp Channel Reuse

Web and WhatsApp invoke the same BP owner operations and the same closed WC-115 command family.
Channel adapters may render or deliver differently but cannot duplicate induction, scoring, plan,
materiality, readiness, authority, idempotency, evidence, correction, Stop, or failure logic. A
decision initiated on one channel appears in the same relationship version on the other.

Duplicate, delayed, reordered, or retried WhatsApp messages reuse the original BP command identity
and cannot duplicate assessment, plan acceptance, publication, spend, or customer communication.
When assurance or sensitive detail is unsafe for WhatsApp, BP returns a secure handoff rather than
weakening the operation. Package A adds no WhatsApp endpoint and does not activate that channel.

## 17. Security, Privacy, Operability And Cost

- Accept only the caller/audience/purpose/delegation tuple already approved for the generic adapter.
- Derive tenant and relationship from trusted service assertions; payload identity is comparison only.
- Return indistinguishable not-found behavior for absent, inaccessible, and cross-tenant resources.
- Reject stale, revoked, cached, partial, or weaker assurance before domain evaluation.
- Permit only public/read-only evidence acquisition for Skill 1; no direct Internet route from the DMA
  image and no customer credential in Package A.
- Keep PII, business profile content, evidence content, prompts, and assessment text out of logs,
  traces, metrics, and errors.
- Emit structured spans for operation, stable skill IDs, manifest/adapter/protocol versions,
  decision state, freshness class, latency, retry/reconciliation state, and safe error code.
- Metrics use bounded labels; never tenant, relationship, customer, URL, evidence, or prompt values.
- Reuse existing SLO and Stop contracts. No new infrastructure target is introduced.
- WBE owns all cost/usage truth. Package A reports observed usage through existing runtime paths and
  never calculates price or entitlement.

## 18. Error And Idempotency Contract

The generic `DomainEmploymentProblemV1` vocabulary is unchanged:

`DOMAIN_EMPLOYMENT_INVALID`, `DOMAIN_EMPLOYMENT_UNAUTHORIZED`, `DOMAIN_EMPLOYMENT_NOT_FOUND`,
`DOMAIN_EMPLOYMENT_CONFLICT`, `DOMAIN_EMPLOYMENT_UNAVAILABLE`, and
`DOMAIN_EMPLOYMENT_VERSION_UNSUPPORTED`.

No free-form protected diagnostics enter public responses. Mutating semantic assessments use the
WC-115 idempotency key derived from the BP command and closed owner operation. Same identity and same
canonical payload digest replays the immutable assessment. Same identity with a different digest
conflicts before evaluation. Timeout or disconnect reconciles the original operation; it is not
submitted under a new key.

## 19. Acceptance And Fitness Contract

### 19.1 Positive

- exact manifest and requirement set for DMA Release 1;
- trial and hire induction through unchanged generic schemas;
- 7/10 evidence coverage produces the correct one-decimal mean and nearest customer level;
- 10/10 coverage with mixed evidence classes preserves provenance;
- valid Package A plan and non-material reschedule;
- bounded optional-input deferral;
- separate customer outcome and professional performance;
- successor assessment after customer correction.

### 19.2 Negative

- old 1-7 scoring input cannot become a Package A result;
- numeric skill aliases cannot become durable identity;
- fewer than seven dimensions cannot produce an overall score;
- missing evidence cannot become score 1 or success;
- trial cannot publish, spend, contact leads, or mutate accounts;
- adapter cannot accept a plan, grant readiness, calculate WBE eligibility, or record CE evidence;
- unknown/stale/mixed-major manifest and dependency evidence fail closed;
- changed idempotency payload conflicts with zero repeated semantic work;
- cross-tenant, cross-relationship, cross-instance, and wrong-purpose calls are indistinguishable
  denials;
- Stop suppresses late success and does not affect an unrelated customer instance.

### 19.3 Generic-Conformance Guard

The same generated domain-adapter types and provider/consumer suite must execute DMA, Trading, and
Tutor fixtures. Tests fail if a platform schema, public command, owner state, or generated client
contains a DMA-only field or branch.

### 19.4 Exact Oracles

| Oracle | Pass condition |
|---|---|
| Manifest | Closed schema; exact tuple; immutable refs/digests; no placeholder; default-off |
| Induction | Every requirement ID unique; mandatory/optional and affected skills exact |
| Scoring | Equal weights; >=7 threshold; one-decimal audit; nearest level; coverage always shown |
| Materiality | Every protected change material; ambiguity `UNKNOWN`; affected work fenced |
| Isolation | Transitive graph proof; `UNKNOWN` fail-closed; unrelated work only after proof |
| Performance | Outcome and professional state independently derived with evidence/limitations |
| Security | Wrong tenant/relationship/purpose/assurance denied before domain logic |
| Reconciliation | Same operation once-logical across replay, timeout, and restart |
| Stop | Existing constitutional SLO and independence pass; late result not admitted |
| Rollback | Candidate disabled; prior protocol remains; history/evidence preserved |

All authoritative validation runs through repository-owned Docker runners under C-080.

## 20. Rollout And Rollback

### 20.1 Rollout

1. reconcile canonical source conflicts;
2. freeze stable IDs, manifest, requirement set, dependency graph, and adapter semantics;
3. implement owner-local DMA semantics behind the existing default-off candidate gate;
4. pass owner unit and contract tests;
5. pass DMA/Trading/Tutor generic conformance;
6. pass negative, outage, duplicate, isolation, security, accessibility, Stop, and rollback suites;
7. bind the exact image/manifest/adapter/protocol/digest tuple;
8. run exact-candidate Docker qualification and complete the evidence ledger;
9. submit for Founder review.

The sequence ends before activation, deployment, provider access, or customer traffic.

### 20.2 Rollback

Rollback disables the Package A candidate gate, fences new candidate commands by the existing
rollback epoch, reconciles in-flight work under WC-115, preserves append-only plans/evidence/results,
and serves the prior protocol behavior. It never rewrites a customer relationship, manifest binding,
assessment, or constitutional record. Founder authority controls any runtime rollback action.

## 21. Implementation Work Components

| Component | Dependency | Exact output | Exit oracle |
|---|---|---|---|
| DMA-A00 Baseline | None | Exact origin, admitted tuple, controlling digests, current-session implementation authority | No missing/placeholder/mismatched input |
| DMA-A01 Canonical reconciliation | A00 | 1-10 Skill 1, stable ID references, dependency/prompt/billing/fixture dispositions | One active human skill authority; conflict scan PASS |
| DMA-A02 Manifest package | A01 | Digest-bound manifest, governance refs, Package A dependency graph | Closed-schema and tuple tests PASS |
| DMA-A03 Induction semantics | A02 | Requirement set and exact requirement resolution | Mandatory/optional/deferral contract tests PASS |
| DMA-A04 Planning semantics | A03 | Plan validation and material-change classification | Complete valid/partial/invalid/unknown matrix PASS |
| DMA-A05 Isolation semantics | A02 | Transitive dependency isolation | Proven/not-bounded/unknown and stale-graph tests PASS |
| DMA-A06 Assessment semantics | A03 | 1-10 maturity and separate performance/outcome interpretation | Calculation, coverage, correction, attribution tests PASS |
| DMA-A07 Adapter integration | A04-A06 | Six operations on existing generic adapter boundary | Provider/consumer and generated-client tests PASS |
| DMA-A08 Generic conformance | A07 | DMA, Trading, Tutor fixtures against unchanged generic schemas | No profession-specific platform contract PASS |
| DMA-A09 Journey and safety | A08 | Trial/hire, outage, duplicate, tenancy, Stop, rollback journeys | Full named acceptance portfolio PASS |
| DMA-A10 Qualification | A09 | Frozen candidate, immutable evidence, completed ledger | Dependency-complete Docker qualification PASS |
| DMA-A11 Handoff | A10 | Exact-head author review and prepared PR | Founder-ready remote-head precheck PASS |

No component may start while a dependency is incomplete. A failed exit oracle blocks all dependents.

## 22. Implementation-Readiness Test

Package A is implementation-ready only when the implementer can answer all of the following from
accepted records without invention:

- exact admitted identity and immutable digest;
- stable skill IDs and versions;
- exact manifest values and immutable references;
- every induction requirement and deferral consequence;
- every scoring dimension, formula, threshold, correction, and limitation;
- valid/partial/invalid/unknown plan rules;
- material and non-material boundary;
- transitive dependency/isolation behavior;
- outcome/performance separation;
- owner sequence and prohibited calls for every command;
- identity, authorization, idempotency, timeout, retry, reconciliation, and errors;
- security, privacy, telemetry, cost, Stop, rollout, rollback, and test oracles.

If any answer is missing, contradictory, or requires a provider/technology/authority decision, the
Platform IT Expert stops. Implementation discretion is limited to internal code organization that
does not alter these externally observable contracts.

## 23. Stops

Stop and return to the Chief Solution Architect, Enterprise Architect, or Founder as applicable if:

- another active DMA skill authority would remain;
- the 1-7 maturity model cannot be removed from active Package A meaning;
- the exact admitted image/manifest tuple cannot be established;
- a generic WC-115 schema or command must change;
- a new platform owner, public endpoint, phase, deployable, database, or authority is required;
- provider selection, credential access, publication, spend, lead contact, activation, deployment,
  or customer traffic becomes necessary;
- stable identity, consent, scoring, materiality, dependency, owner, or evidence meaning is ambiguous;
- DMA-specific behavior would enter BP, CE, WBE, PR, AIR, Web, Trading, or Tutor contracts;
- a candidate is advertised before exact conformance, qualification, admission, and separate
  activation authority;
- tests cannot prove cross-tenant/relationship/instance isolation or independent Stop; or
- any acceptance oracle would rely on prose review rather than executable evidence.

## 24. Enterprise Deliverable Trace

| Enterprise deliverable | Package A closure |
|---:|---|
| 1. Eight buckets and staged order | Sections 2.3, 5.6, and 20 preserve all buckets and vertical sequence |
| 2. Canonical consolidation | Sections 3.2 and 3.3 define conflict resolution, deletion/archive, and single authorities |
| 3. Stable taxonomy and manifest | Sections 4 and 5 define IDs, versions, aliases, tuple, and manifest |
| 4. WC-115 behavior mapping | Sections 7, 14, and 16 map phases, commands, operations, owners, and evidence |
| 5. Trial/hire state | Section 7.2 fixes modes and prohibits silent progression |
| 6. Inputs, accounts, credentials, approvals, missing input | Sections 6, 7, 11, 13, 15, and 17 define exact treatment |
| 7. Explainable maturity scoring | Section 8 fixes dimensions, formula, threshold, evidence, confidence, correction, and versioning |
| 8. Web/WhatsApp reuse | Section 16.6 requires one BP operation/state model and secure handoff |
| 9. Lead/lifecycle model | Explicitly deferred to Package C/D in Section 2.3; Package A cannot contact leads |
| 10. Search/discoverability | Public evidence is assessment-only; action is deferred to Package D |
| 11. Paid media/first-party audience | Planned/unavailable only; all activation, consent, spend, and lead work is deferred to Package C |
| 12. Image/manifest/admission/instance | Sections 4, 5, 15, 19, and 20 define the compatibility and rollout model |
| 13. Failure, degradation, stale data, correction, dispute | Sections 8, 11, 13, 16, and 18 define safe behavior |
| 14. Observability, privacy, security, cost, rollback, Stop | Sections 13, 16.5, 17, 19, and 20 define executable obligations |
| 15. Dependency-impact map | Sections 11, 14, and 15 preserve BP, PR, CE, AIR, WBE, oauth-vault, adapter, channel, owner, and provider boundaries |
| 16. Executable fitness and acceptance | Section 19 covers positive, negative, outage, duplicate, retry, tenancy, relationship, version, mode, and side-effect cases |
| 17. Platform IT Expert Work Contract | `work-contracts/WC-116-dma-employment-conformance.md` provides dependency-ordered atomic delivery |
| 18. Exact canonical-record updates | Sections 3.2 and 3.3 plus WC116-01 name every owning record and duplicate-removal action |
| 19. Customer catalogue and maturity projections | Sections 5.6 and 8 use enterprise vocabulary and hide numeric skill labels |

Package A intentionally closes only the first solution package required by enterprise Section 20.4.
Rows deferred to later packages are bounded exclusions, not omissions or implementation discretion.

## 25. Chief Solution Architect Handoff

The Platform IT Expert receives a bounded Package A: reconcile the canonical DMA sources, implement
the six existing adapter operations for the admitted Skills 0/1/2 tuple, prove the enterprise 1-10
maturity contract and generic WC-115 conformance, keep the candidate disabled, and stop before any
activation, deployment, provider access, external side effect, spend, or customer traffic.

No product, authority, consent, scoring, schema, provider, ownership, or availability decision is
delegated to implementation.
