# WC-034 F4 Relationship Workspace

## Attestation

| Field | Value |
|---|---|
| Institution | INST-004 — Enterprise Architect |
| Goal | GOAL-005 |
| Work Contract | WC-034 F4 |
| Contribution ID | CR-GOAL-005-INST-004-07 |
| Date | 2026-08-10 |
| Status | COMPLETE |
| Contribution boundary | Reference architecture and owner assignment only; no endpoint path, wire schema, implementation, deployment, provider activation, or F5-F8 decision |

## 1. Decision Summary

F4 extends the existing authenticated customer experience with one governed Relationship Workspace for one selected Employment Relationship at a time. It introduces no new deployable component. The existing Business Platform (BP) is the sole public customer-facing relationship facade and the authoritative relationship governance projection. The web application presents only BP-owned public projections and sends customer commands only through approved BP contracts.

The WAOOAW Billing Engine (WBE) remains authoritative for billing and allowance actuals, ceilings, forecasts, thresholds, assumptions, and commercial consequences. BP consumes an internal WBE projection and incorporates it into the public relationship projection without recalculating, ranking, or recreating billing truth.

The Constitutional Engine (CE) remains the sole constitutional validation and constitutional-evidence authority. Professional Runtime (PR) remains an internal supplier of professional execution truth. Professional and domain adapters supply domain outcome semantics to BP without becoming public customer facades. The web application never directly accesses PR, WBE, CE, the Constitutional Audit Ledger, the Customer Evidence Ledger, or any billing ledger, and never ranks or aggregates relationship truth locally.

This structure derives from capabilities 2.1-2.7, 4.1-4.5, 5.1-5.5, 6.2-6.5, and 9.1-9.2; C-001 through C-005, C-007, C-010, C-011, C-023, C-026, C-030, C-034, C-036 through C-044, C-048, C-049, C-051, C-056, C-063, C-065, C-083 through C-085, and C-088 through C-091; and AD-002, AD-004, AD-007, AD-008, AD-012, and AD-014.

## 2. Scope And Structural Boundaries

F4 includes the conceptual ownership and composition of relationship context, Plan, Needs your attention, Work, Results, Usage & budget, Rights & control, and their governed customer commands. The workspace preserves the distinction between capability, authority, intended work, completed work, business outcome, forecast, actual, and evidence.

F4 excludes application code, database design, deployment topology, concrete API operations, endpoint paths, wire schemas, generated clients, provider work, new platform services, F5 omnichannel continuity, F6 voice or attachments, F7 Founder administration, and F8 integrated release closure. It does not change the dedicated Emergency Stop architecture.

An absent owner-approved contract is represented as unavailable or blocked. Neither BP nor web may compensate with inferred data, local defaults, technical telemetry, mock success, or a private service connection.

## 3. Authority And Ownership Matrix

| Concern | Authoritative owner | BP public responsibility | Explicitly prohibited |
|---|---|---|---|
| Selected relationship context | BP Employment Relationship domain | Project authorized professional identity, lifecycle, current-goal reference, rights availability, source currency, and relationship binding | Web-selected tenant authority; relationship truth inferred from conversation, contract, payment, or local cache |
| Plan | BP relationship-governance domain | Project proposed/agreed plan, goals, intended work, dependencies, timing, review points, owners, effects, and available commands | Browser plan assembly; plan treated as approval, authority, completed work, or result |
| Goals | BP relationship-governance domain, informed by professional/domain semantics | Project baseline, measure, review period, attribution boundary, state, owner, and governed commands | PR or web mutating public goal truth directly |
| Work | BP relationship-governance domain; PR supplies internal execution facts | Project proposed, approved, scheduled, active, paused, blocked, completed, cancelled, failed, or outcome-unknown work with accountable owner and evidence status | PR events exposed as customer truth before BP validation; completed work relabelled as outcome |
| Deliverables | BP relationship-governance domain; professional/domain owner supplies deliverable meaning | Project purpose, limitations, review state, owner, evidence state, and available commands | Web inferring acceptance from download, preview, or transport state |
| Results | BP relationship-governance projection using professional/domain adapter contributions | Project evidence-backed business outcomes, baselines, periods, measures, attribution limits, uncertainty, and review actions | Technical/runtime metrics presented as business success; web or BP manufacturing domain outcome meaning |
| Needs your attention | BP relationship-governance domain | Supply the complete qualifying list, authoritative order, stable tie sequence, reasons, consequences, due meaning, and commands | Web ranking, scoring, filtering into authority, secondary sorting, personalization, or cross-relationship aggregation |
| Approvals and scope-boundary confirmations | BP command facade; CE validates and records constitutional evidence | Present distinct subjects, consequences, expiry, assurance need, and authoritative outcome | Ordinary approval silently changing scope; web or BP bypassing CE validation/evidence |
| Scope, authority, lifecycle, and rights | BP Employment Relationship and governance domains; CE governs constitutional validity | Project current versions, effective state, available rights, typed consequences, and commands | Capability treated as authority; optimistic lifecycle mutation; rights hidden by commercial or degraded state |
| Evidence reads and exports | CE/evidence stores remain evidence authorities; BP Evidence Reader is the only public projection | Authorize tenant/relationship/role scope; project evidence status and permitted payload references; mediate export | Direct web ledger access; pending evidence shown as recorded; exports outside assurance and sensitivity policy |
| Usage & budget actuals | WBE | Relay WBE-owned allowance use, remaining allowance, financial actuals, period, and commercial consequence through BP | BP recomputation; technical token/provider cost substituted for customer allowance or spend |
| Ceilings, forecasts, thresholds, and commercial consequences | WBE | Relay WBE-owned ceiling, forecast range, assumptions, validity, threshold state, and typed consequence through BP | BP or web forecasting, threshold calculation, price inference, ranking, or consequence invention |
| Professional execution truth | PR | Accept internal facts, validate correlation and supported versions, then project only BP-owned customer meanings | Public PR ingress or PR ownership of relationship governance |
| Domain outcome semantics | Professional/domain owner through a generic adapter contract | Compose approved domain measures and interpretations into BP Results and attention candidates | DMA-specific logic in the generic workspace; adapter control of public ordering or constitutional authority |
| Presentation and interaction | Web application | Present generated BP public projections and commands for one authorized relationship | Direct PR/WBE/CE/ledger access; truth aggregation, authority decisions, ranking, or durable governance state |

## 4. Conceptual Relationship Read Model

The public F4 read model is one BP-owned, relationship-bound projection. This section defines semantic responsibilities, not a wire schema.

The projection contains:

- relationship context: professional identity, lifecycle state, current goal context, rights/control availability, and currency meaning;
- Plan: goals, intended and priority work, dependencies, review points, timing, owners, effects, and state;
- Needs your attention: qualifying customer-action items in authoritative server order with stable ties;
- Work: activities, deliverables, approvals, schedules, owners, states, effects, available actions, and evidence status;
- Results: business outcome measures, baselines, review periods, evidence support, attribution limits, uncertainty, and accountable domain source;
- Usage & budget: allowance and financial actuals, remaining allowance, ceilings, forecast ranges, assumptions, thresholds, validity, and consequences supplied by WBE;
- Rights & control: current scope, authority, lifecycle controls, rights, approval/boundary distinctions, evidence access/export, and Emergency Stop reachability.

Every projection and consequential item carries conceptual provenance sufficient to establish:

- the accountable source domain and source projection version;
- source observation or production time, declared validity, freshness status, and last authoritative confirmation;
- an opaque continuation/reconciliation cursor where incremental reading applies;
- authenticated tenant binding and Employment Relationship binding;
- item identity and source-relative sequence sufficient to preserve stable ties;
- the authority, scope, lifecycle, assurance, evidence, and WBE projection versions relevant to the displayed meaning;
- whether the meaning is current, stale, unknown, unavailable, pending, disputed, or superseded.

Tenant identity is derived from the authenticated server context and is never accepted as customer-provided authority. Cursors are opaque observations bound to tenant and relationship; they grant no access and cannot authorize a command. Relationship switching obtains a complete separately authorized projection and carries no drafts, links, authority, budget, evidence, ordering state, or cached item truth across relationships.

### Stable Ordering

BP owns qualification and ordering for Needs your attention. Equal-priority items retain their BP-provided relative sequence across refresh, pagination, device, and reconnect until BP changes the sequence or an item stops qualifying. Web presents that sequence exactly. Source-domain candidates, including WBE threshold consequences and domain outcome review needs, do not enter the public list until BP accepts them into the relationship projection with an accountable reason and action.

### Unknown, Stale, And Unavailable

- **Unknown** means BP cannot determine the authoritative owner, state, effect, attribution, or outcome. The unknown field is named, consequential success is withheld, and an accountable recovery action is supplied where one exists.
- **Stale** means previously authoritative information exceeded declared validity or predates a material version change. BP states when it was current and excludes it from fresh assurance, approval, ordering changes, forecasts, actuals, and success claims until refreshed.
- **Unavailable** means an owning contract or authority is absent, denied, or not operating. BP exposes the capability as unavailable or blocked without substituting another source. Web preserves that meaning and does not offer an improvised command.

Loading, empty, error, pending, and disputed remain distinct from unknown, stale, and unavailable. No cached, optimistic, transport-success, PR-processing, or pending-evidence state becomes current relationship truth without authoritative BP confirmation.

## 5. Command Responsibilities

Web issues only commands present in an approved generated BP client and displays commands only when the BP projection declares them available. Every consequential command is bound to the authenticated actor, tenant, relationship, subject, expected authoritative version, declared purpose, and idempotency intent. A stale expectation causes reconciliation or an explicit conflict; it never causes blind overwrite.

| Command family | Responsibility chain | Required outcome discipline |
|---|---|---|
| Plan and goal review/change | Web requests; BP authorizes and owns relationship mutation; professional/domain owner may prepare semantics; CE validates when authority, boundary, or constitutional evidence is implicated | Proposed remains distinct from agreed; changed assumptions and affected work are explicit |
| Approval or rejection | Web requests; BP verifies subject, owner, expiry, consequence, assurance, and current version; CE validates and records before governed success | Approval grants only the stated next step and never silently expands scope or authority |
| Scope-boundary confirmation | Web requests a distinct command; BP enforces current assurance and typed acknowledgement; CE validates and records the distinct constitutional event | Never represented by or collapsed into ordinary approval |
| Pause, resume, renew, or terminate | Web requests; BP owns lifecycle transition and typed relationship consequence; WBE supplies commercial consequence; CE validates and records where required | No optimistic final state; actual lifecycle and billing effects remain independently authoritative |
| Authority grant, constraint, suspension, revocation, or restoration | Web requests; BP verifies licensed authority owner and current versions; CE is constitutional validation/evidence authority | Fresh assurance and typed acknowledgement follow the approved consequence policy |
| Evidence inspection or export | Web requests; BP Evidence Reader authorizes scope and mediates CE/evidence access; Security policy determines assurance and export protection | Export completeness, sensitivity, recipient/use, redaction, and limitations remain explicit |
| Budget, allowance, pacing, or commercial choice | Web requests through BP; WBE validates commercial state and owns resulting actual/forecast/consequence; BP owns public relationship effect; CE validates authority where applicable | BP does not calculate billing truth; command success waits for authoritative owning outcomes and evidence obligations |

Commands that can affect both relationship governance and WBE truth use an orchestrated, idempotent outcome. Partial or uncertain completion is exposed as unresolved with reconciliation ownership; BP must not report success from transport acceptance alone. Evidence First applies before a constitutionally governed success is presented.

## 6. Generic Domain Results Adapter

F4 defines one generic internal contribution role for professional/domain owners. It is not a new deployable component and does not introduce F5 continuity. An adapter contributes domain semantics to BP for one tenant-bound Employment Relationship and one declared goal or review context.

The adapter contribution describes, conceptually:

- domain outcome identity and customer-language label;
- accountable professional/domain owner;
- baseline, measure, review period, observed value or bounded qualitative assessment;
- evidence references available for BP-mediated reading;
- attribution basis, limits, uncertainty, and unavailable inputs;
- outcome state and material change meaning;
- candidate attention reason, required customer action, consequence, and validity window;
- adapter contract version and source freshness.

BP validates adapter ownership, relationship/goal binding, supported version, evidence references, and completeness before incorporating the contribution. BP owns the resulting public Results projection and all public attention qualification and ordering. The adapter cannot grant authority, approve work, change lifecycle, define rights, record constitutional evidence, calculate WBE truth, or expose itself to web.

The architecture is domain-neutral. No DMA outcome, campaign, channel, advertising, agricultural, trading, tutoring, or other profession-specific field or rule belongs in the generic workspace contract. Each professional/domain owner defines its outcome vocabulary and evidence semantics under its own approved contract while conforming to this adapter role.

## 7. Institutional Assignments

| Assignee | Exact F4 contribution |
|---|---|
| INST-005 — Solution Architect | Define the concrete BP public and BP-to-WBE/PR/domain internal API contracts, interaction sequencing, supported versions, errors, idempotency behavior, command conflict/reconciliation behavior, and generated-client boundary. Own endpoint paths and wire schemas. Confirm no browser-private-service route exists. |
| INST-006 — Data Architect | Define canonical data semantics and provenance for actual, forecast, allowance, budget, threshold, business outcome, technical metric, pending/recorded evidence, source/version/freshness/cursor, stable sequence, tenant/relationship binding, unknown, stale, unavailable, retention, and correction/supersession. Preserve ledger separation. |
| INST-007 — Security Architect | Define fresh-assurance thresholds, typed-acknowledgement enforcement, relationship/role authorization, anti-enumeration, export sensitivity/recipient protections, cache and telemetry limits, confused-deputy controls, and direct-service/ledger denial tests for each consequence class. |
| INST-011 — Product Owner | Confirm minimum F4 release composition, mandatory item and command families, customer labels, omission rules, consequence disclosures, domain-neutral acceptance scenarios, and which unresolved customer-rights or commercial choices require Founder policy through INST-013. |
| BP owner | Own the relationship-governance aggregate and public projection; define Plan, goals, work, deliverables, approvals, schedule, scope, authority, lifecycle, rights, evidence-reader, Results composition, ordered attention, commands, and internal consumer contracts. |
| WBE owner | Define the internal authoritative projection and command outcomes for allowance/billing actuals, remaining allowance, ceilings, forecasts, assumptions, thresholds, validity, pacing choices, and commercial consequences. Supply compatibility and freshness rules; prohibit BP recomputation. |
| Professional/domain owners | Define domain-specific outcome vocabulary, baselines, measures, review periods, evidence sources, attribution limits, uncertainty, material attention candidates, and adapter compatibility without owning public ordering or customer authority. |

Independent review must preserve C-065. INST-004 does not independently review this contribution. Solution, Product, Data, and Security contributions are authored in their respective Decision Spaces, and the complete F4 package receives the fresh independent reviewer context required by the approved plan before implementation selection.

Any unresolved policy decision concerning customer rights, authority, consequence classes, commercial treatment, release composition, or acceptable uncertainty is routed to INST-013 for Goal-level orchestration and Registrant/Founder resolution. No downstream owner may invent a default while that decision is unresolved.

## 8. Dependency And Authorization Gates

| Gate | Required evidence | Owner | State after this contribution |
|---|---|---|---|
| G-F4-01 — Business input | Approved F4 business meanings, stable ordering, consequence classes, truthful states, and acceptance semantics | INST-003 | SATISFIED — CR-GOAL-005-INST-003-03 |
| G-F4-02 — Enterprise Architecture ownership | Public/internal authority, projection boundaries, conceptual read/command responsibilities, domain adapter, assignments, exclusions, and ADR impact are explicit | INST-004 | SATISFIED — CR-GOAL-005-INST-004-07 |
| G-F4-03 — Solution API contracts | Concrete BP public and internal owner contracts define reads, commands, errors, idempotency, reconciliation, versions, and no private browser route | INST-005 with BP/WBE/professional owners | BLOCKED pending contribution |
| G-F4-04 — Data semantics | Canonical provenance, freshness, ordering, actual/forecast/outcome/evidence meanings, bindings, correction, retention, and unavailable-state semantics are approved | INST-006 | BLOCKED pending contribution |
| G-F4-05 — Security assurance | Consequence assurance, authorization, export, cache, telemetry, anti-enumeration, cross-tenant, and direct-access controls are approved | INST-007 | BLOCKED pending contribution |
| G-F4-06 — Product release composition | Mandatory first-release views, item/command families, labels, omission behavior, and policy escalations are approved | INST-011 | BLOCKED pending contribution |
| G-F4-07 — BP owner contract | BP accepts sole public facade and relationship-governance projection ownership, including stable attention ordering and command authority | BP owner | BLOCKED pending owner-approved contract |
| G-F4-08 — WBE owner contract | WBE supplies the internal authoritative actual/ceiling/forecast/threshold/consequence projection and compatibility rules | WBE owner | BLOCKED pending owner-approved contract |
| G-F4-09 — Domain-owner contracts | Selected professional/domain owners supply adapter-conformant outcome semantics and evidence/attribution rules | Professional/domain owners | BLOCKED pending selected-release contracts |
| G-F4-10 — Generated-client compatibility | Approved BP public F4 contract validates and generates the web client without manual patches or private PR/WBE/CE/ledger surfaces | INST-005 and BP owner | BLOCKED until G-F4-03 and G-F4-07 close |
| G-F4-11 — Independent reviews | Solution, Product, Data, and Security contributions and the integrated package receive C-065-compliant independent review in the fresh reviewer context defined by plan | Assigned independent reviewers through INST-013 | BLOCKED pending G-F4-03 through G-F4-10 |
| G-F4-12 — Implementation authorization | A separate current-session authorization names the approved F4 package, bounded implementation scope, acceptance evidence, and INST-010 assignment | Registrant/Founder through INST-013 | BLOCKED; architecture completion is not implementation authority |
| G-F4-13 — Deployment authorization | Separate release/deployment review and authorization identifies environment, evidence, rollback, and deployment confirmer | Authorized release/deployment authorities | BLOCKED; no deployment authority in F4 architecture |

Gates close in dependency order. A later gate cannot treat an earlier blocked contribution as an implementation assumption. F5-F8 do not enter or close through this table.

## 9. ADR Impact Assessment

No new architectural decision is made by F4 and no existing ADR requires amendment at this stage:

- ADR-001 continues to keep CE internal and authoritative for constitutional validation/evidence interaction.
- ADR-002 continues to assign concrete REST contract and generated-client work to spec-first Solution Architecture.
- ADR-003 continues tenant derivation and isolation requirements.
- ADR-017 continues the existing web application boundary.
- ADR-034 continues WBE authority for billing, allowance, forecast, threshold, and commercial truth.
- Existing BP, PR, CE, WBE, and web responsibilities are refined as logical projection ownership; no deployable component or technology is introduced.

If INST-005, INST-006, INST-007, INST-011, BP, WBE, or a professional/domain owner discovers that F4 requires a significant decision not covered by an accepted ADR, that need is a blocker routed through INST-013 to the authorized ADR-owning process. This contribution does not author, reserve, or imply the missing decision.

## 10. Acceptance Trace

| Acceptance ID | Architecture obligation | Owning proof contribution |
|---|---|---|
| UX-CONV-06 | BP-owned Action, Plan, Deliverable, and Decision meanings expose owner, state, effect, evidence status, and only authoritative available commands | INST-005 contract; BP owner; INST-011 composition |
| UX-CONV-07 | Every projection, cursor, command, draft handoff, and item is tenant/relationship-bound; switching obtains a complete separately authorized context with zero carry-over | INST-005 contract; INST-006 semantics; INST-007 assurance |
| UX-CONV-08 | BP supplies only qualifying Needs your attention items in exact authoritative order with stable ties; web performs zero ranking or secondary sorting | BP owner contract; INST-006 ordering semantics; INST-011 release composition |
| CCT-UX-BOUNDARY-01 | Scope-boundary confirmation is a distinct BP command with current assurance, named boundary/consequence, typed acknowledgement, and CE evidence | INST-005 contract; INST-007 assurance; BP/CE owners |
| CCT-UX-RIGHTS-01 | BP projection keeps rights, scope, authority, lifecycle, evidence access, and Emergency Stop reachable in customer language for each included state | BP owner; INST-011 composition; INST-007 assurance |
| CCT-UX-EF-01 | Pending and recorded evidence are distinct; recorded appears only after authoritative CE confirmation projected by BP | INST-005 interaction contract; INST-006 evidence semantics; BP/CE owners |
| UX-SHELL-06 | Missing or blocked owner contracts produce unavailable/blocked public meanings and no improvised private or successful path | All contributing owners; integrated independent review |

F4 architecture acceptance requires zero browser-derived ordering, zero BP recreation of WBE truth, zero direct web access to PR/WBE/CE/ledgers, zero domain-specific hardcoding in the generic workspace, zero cross-relationship leakage, and zero fabricated success. These architecture criteria do not claim executable acceptance, implementation completion, release, deployment, or customer proof.

## 11. Controlling Inputs

- `goals/GOAL-005-f4-business-contribution.md` — CR-GOAL-005-INST-003-03
- `work-contracts/WC-034-goal005-webportal-founder-admin.md` — F4 component boundary
- `architecture/reference/ux/hybrid-application-shell.md` — public facade, web, and service ownership boundaries
- `architecture/reference/ux/wc-034-implementation-decomposition.md` — F4 scope, dependencies, exclusions, and acceptance identifiers
- `goals/GOAL-005-D01-product-outcome-input.md` — approved release-wide product outcome and durable relationship boundary
- `knowledge/business-capabilities.md`, `knowledge/architectural-drivers.md`, and `knowledge/design-principles.md` — capability and constraint derivation