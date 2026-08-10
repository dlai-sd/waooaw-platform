# WC-034 F4 Relationship Workspace Data Contract

## Attestation

| Field | Value |
|---|---|
| Institution | INST-006 — Data Architect |
| Goal | GOAL-005 |
| Work Contract | WC-034 F4 |
| Contribution ID | CR-GOAL-005-INST-006-03 |
| Date | 2026-08-10 |
| Status | COMPLETE |
| Contribution boundary | Canonical data semantics, provenance, logical flow, correction, retention, and isolation for the F4 Relationship Workspace; no endpoint, wire schema, database schema, migration, implementation, provider activation, deployment, or F5-F8 decision |

## 1. Purpose And Governing Boundary

This contract defines how F4 preserves the meaning and origin of relationship, plan, work, result, usage, budget, attention, rights, and evidence information for one selected Employment Relationship at a time. It refines the owner boundaries in `architecture/reference/components/relationship-workspace.md` without changing them.

The Business Platform (BP) owns the public relationship-governance projection. The WAOOAW Billing Engine (WBE) remains the sole authority for allowance and commercial actuals, budgets, forecasts, thresholds, assumptions, and consequences. The Constitutional Engine (CE) and constitutional evidence stores remain the authority for constitutional validation and recorded constitutional evidence. Professional Runtime (PR) supplies execution facts. Professional and domain owners supply outcome semantics through the generic domain adapter role. The web application presents the BP projection and never becomes a source of relationship truth.

This is a conceptual and logical data contract. It does not prescribe tables, columns, indexes, migrations, storage engines, endpoint paths, payload shapes, or generated-client types.

## 2. Canonical Data Principles

1. **Meaning follows authority.** A projection may compose authoritative meanings, but composition does not transfer source ownership.
2. **Provenance travels with meaning.** A value without accountable source, version, binding, production time, and validity meaning is not fit for consequential display or action.
3. **Tenant and relationship are joint boundaries.** Tenant authority comes from authenticated server context. Relationship authority is resolved independently for the selected Employment Relationship. Neither binding alone is sufficient.
4. **Actual, forecast, allowance, budget, and threshold are distinct facts.** No one may be substituted for another, even when they share a unit.
5. **Business outcomes and technical metrics are distinct.** Technical operation may support or qualify an outcome but cannot manufacture customer value.
6. **Pending and recorded evidence are distinct.** Recorded evidence exists only after confirmation by the authoritative evidence owner.
7. **Correction preserves history.** A corrected public meaning supersedes an earlier meaning; it does not erase or rewrite prior constitutional evidence.
8. **Unknown, stale, unavailable, disputed, and superseded are first-class states.** None may be collapsed into empty, zero, false, current, failed, or successful.
9. **Ordering is authoritative data.** Needs-your-attention qualification, authoritative ordering sequence, and stable ties are BP relationship-governance truth, not presentation logic. The public contract exposes no rank or score, and web presents BP's supplied order exactly without ranking.
10. **Minimisation precedes convenience.** The public projection carries only the information required for the selected relationship and customer purpose.

## 3. Canonical Provenance

Every F4 projection and every consequential item must carry enough conceptual provenance to establish the following meanings. Concrete representation belongs to the Solution Architect and owning service contracts.

| Provenance concept | Canonical meaning |
|---|---|
| Accountable source owner | The domain institution or service accountable for the meaning: BP relationship governance, WBE commercial truth, CE/evidence authority, PR execution truth, or a named professional/domain owner. |
| Source subject | The source-owned fact, projection, event, evidence record, or outcome assessment from which the public meaning was derived. |
| Source version | The immutable or monotonically advancing source-relative version that identifies the exact authoritative meaning used. A presentation revision is not a source version. |
| Contract version | The supported semantic contract under which the source meaning was interpreted. It identifies compatibility, not recency. |
| Produced time | When the source owner produced or confirmed the meaning. |
| Observed time | When the underlying usage, work, metric, outcome, or condition occurred or was observed. It may differ from produced time. |
| Last authoritative confirmation | The latest time the accountable source confirmed that the meaning remained authoritative. A transport receipt or browser refresh is not confirmation. |
| Declared validity | The source-owned time or condition through which the meaning may be treated as current. Absence of declared validity does not imply indefinite validity. |
| Freshness state | Current, stale, unknown, or unavailable according to Section 7. Freshness is evaluated against source-owned validity and material version changes, not browser age alone. |
| Tenant binding | The authenticated tenant to which the source meaning belongs. It is derived from trusted server context and never supplied as customer-selected authority. |
| Relationship binding | The single Employment Relationship to which the meaning belongs. A tenant-wide fact must be explicitly scoped before it can enter a relationship projection. |
| Goal or subject binding | The goal, work item, approval, evidence subject, budget period, or other source-owned subject to which the meaning applies. |
| Source-relative identity | A stable identity within the accountable source that supports reconciliation and correction without allowing another domain to assume ownership. |
| Source-relative sequence | The authoritative sequence used for ordered relationship information. It is data, not a presentation hint. |
| Correction lineage | The prior meaning corrected or superseded, the accountable correcting source, correction reason category, and effective time. |
| Evidence relationship | Whether evidence is pending, recorded, unavailable, disputed, or superseded, plus an authority-owned reference suitable for BP-mediated access when permitted. |

### 3.1 Source Version Semantics

A source version identifies a source owner's exact authoritative statement. Versions are compared only within the same source owner, source subject, tenant, and relationship binding. BP must not compare or merge unrelated WBE, PR, CE, or domain-adapter versions into a synthetic global version.

The BP public projection has its own relationship-projection version for conflict detection and reconciliation. That version records the composition BP authorized; it does not replace the included source versions. A new BP projection version may contain an unchanged WBE source version, and a new WBE version may require a new BP projection before it is customer-current.

An unsupported contract version makes the affected contribution **unavailable**, not unknown and not silently coercible. A newer source version does not retroactively alter the meaning of an earlier projection or evidence record.

### 3.2 Freshness Semantics

Freshness is source-relative and purpose-relative. Information is current only when:

- its accountable source and exact source version are known;
- its tenant, relationship, and subject bindings match the selected context;
- its declared validity has not expired;
- no known material source-version change invalidates it; and
- it is permitted for the intended use, such as display, ordering, assurance, approval, actual reporting, or forecasting.

Information can remain historically true while stale for a current decision. Stale information must not support fresh assurance, a new approval, a changed attention order, a current forecast, an actual balance claim, or an achieved-outcome claim.

### 3.3 Opaque Cursor Semantics

An incremental-read or reconciliation cursor is an opaque observation token issued by the authoritative projection owner. It means only: continue or reconcile the same authorized projection from an owner-defined position.

A cursor:

- is bound to the authenticated tenant, selected relationship, projection family, and compatible contract version;
- grants no authority and proves no access entitlement;
- exposes no interpretable rank, timestamp, database key, tenant identifier, or commercial value;
- cannot be transferred across relationships, tenants, users, projection families, or incompatible versions;
- cannot be used to infer absence, completion, freshness, or success;
- becomes unusable when its owner cannot safely reconcile it, at which point a complete separately authorized projection is required; and
- never permits the web application to merge old and new relationship contexts.

Cursor rejection is not an empty result. It is an explicit reconciliation condition whose public treatment is conflict, stale, or unavailable according to the owning contract.

## 4. Stable Ordering And Ties

BP relationship governance owns Needs-your-attention qualification and ordering. Each qualifying item has an authoritative source-relative sequence within the selected relationship projection. Equal-priority items retain their BP-provided relative sequence across refresh, pagination, reconnect, and device until BP changes the sequence or an item ceases to qualify.

Stable ties mean:

- equal authoritative priority does not authorize a secondary sort;
- time, label, state, technical severity, local activity, viewport, locale, or arrival order cannot break a tie unless BP has already incorporated that rule into its authoritative sequence;
- WBE and domain adapters may contribute candidate attention facts, but only BP can qualify and place them in the public order;
- a correction that does not change authoritative sequence preserves the prior relative position;
- a sequence change produces a new BP relationship-projection version with accountable provenance; and
- an incomplete page or cursor segment cannot be locally re-ranked to appear complete.

The web presents the supplied order exactly. It may visually group only when the owner-approved contract states that grouping preserves the authoritative sequence and does not hide a qualifying item.

## 5. Commercial And Consumption Semantics

| Concept | Canonical meaning | Required provenance | Must not mean |
|---|---|---|---|
| Actual | An authoritative observation of usage, allowance movement, charge, payment, or other commercial fact that has occurred for a named period and subject. WBE owns usage and commercial actuals. | WBE source/version, observed and produced times, period, unit, relationship/subject binding, confirmation and correction status. | Forecast, reservation, pending charge, provider cost, token count, browser estimate, or budget. |
| Forecast | A bounded forward-looking estimate produced by an accountable owner from named assumptions, validity, uncertainty, period, and range. WBE owns allowance and commercial forecasts. | WBE source/version, forecast production time, forecast period, range, assumptions, uncertainty, validity, and supersession state. | Actual use, guaranteed outcome, approved spend, available allowance, or authority to act. |
| Allowance | A customer-understandable entitlement or quantity available under agreed terms for a named period and scope. It is not money unless the owning contract explicitly defines a monetary allowance. | WBE source/version, allowance definition/version, unit, period, scope, actual consumed, remaining amount, renewal/adjustment status, and validity. | Tokens, provider cost, budget, forecast, wallet implementation detail, or unrestricted authority. |
| Budget | A governed financial ceiling or licensed spending boundary for a named owner, scope, period, and consequence. | WBE source/version, currency, agreed ceiling, effective period, authority owner, scope, actual financial position, and change provenance. | Allowance, price, actual charge, forecast, available cash, or permission beyond the stated scope. |
| Threshold | An owner-defined boundary evaluated against one named actual, allowance, budget, or forecast meaning, with a typed consequence. WBE owns commercial and allowance thresholds. | WBE source/version, threshold definition/version, basis, comparison subject, evaluation time, state, consequence, and validity. | Browser-derived warning, rank, predicted breach without a forecast, or automatic authority change. |

Actuals are corrected by a new source-owned actual that identifies what it corrects. Forecasts are normally superseded, not corrected as though they had been actuals. A forecast becomes **actual now available** only by linking to a separately authoritative actual; the forecast itself never changes category.

Threshold state must identify whether it was evaluated from an actual or forecast basis. A forecast threshold is a forward-looking warning; it is not an actual breach. Crossing a budget or allowance threshold does not itself grant, revoke, or expand authority unless a separately approved governance rule produces that consequence.

## 6. Results And Evidence Semantics

### 6.1 Business Outcome Versus Technical Metric

| Meaning | Business outcome | Technical metric |
|---|---|---|
| Question answered | Did the customer's declared business goal change within the agreed period and attribution boundary? | Did an enabling system, model, provider, queue, delivery path, or execution process operate? |
| Required context | Goal, baseline, measure, period, observed value or bounded assessment, evidence, attribution basis and limits, accountable domain owner. | Metric definition/version, system scope, observation window, unit, source, and operational interpretation. |
| Examples | Appointments, qualified enquiries, booking rate, revenue, cost per acquired customer, crop loss prevented, price premium, risk-managed return. | Latency, delivery status, execution duration, retry count, provider success, queue depth, model use, token consumption. |
| Public role | Primary customer-value meaning when evidence and attribution support it. | Supporting diagnostic or limitation context only. |
| Prohibited conversion | None; it remains unknown or disputed when attribution is insufficient. | It cannot be relabelled, scored, or aggregated into business success without an approved domain outcome contract. |

A business outcome must retain the provenance of the domain adapter contribution and the evidence used by BP to authorize the public Result. BP owns the public Result composition, but it does not invent a baseline, measure, attribution rule, or domain interpretation.

A completed work item or deliverable is not a business outcome. A positive technical metric is not a business outcome. An outcome may remain unchanged, declining, not achieved, attribution unknown, or disputed even when all work and technical systems completed successfully.

### 6.2 Pending And Recorded Evidence

**Pending evidence** means an evidence obligation or recording attempt is known, but the authoritative evidence owner has not confirmed a durable record. Pending evidence may identify the intended subject, accountable producer, expected evidence class, and correlation suitable for reconciliation. It must not expose a fabricated evidence identifier or imply constitutional completion.

**Recorded evidence** means the authoritative evidence owner confirmed a durable evidence record and supplied an authority-owned reference, recording time, evidence state, subject binding, and constitutional basis appropriate to the public projection. Transport acceptance, PR completion, BP command acceptance, a local outbox entry, or an optimistic browser state is not recorded evidence.

The public transition is one-way in historical fact: pending may be followed by recorded, unavailable, or a reconciled failure. If recorded evidence is later challenged or corrected, the original record remains recorded and is additionally marked disputed or superseded in the public interpretation. It is never rewritten as though it had not existed.

## 7. Truth And Availability States

| State | Canonical meaning | Public consequence | Recovery or lineage requirement |
|---|---|---|---|
| Current | The exact source/version is authoritative, valid for the intended use, correctly bound, and not contradicted by a known material change. | May be displayed and used only for the purposes authorized by its owner contract. | Preserve source/version and last confirmation. |
| Unknown | The authoritative owner, state, effect, attribution, value, or reconciliation outcome cannot presently be determined. | Name the unknown meaning; withhold consequential success and any action that depends on it. Unknown is not zero, empty, false, or failed. | Identify the accountable recovery owner and next valid reconciliation action when one exists. |
| Stale | Previously authoritative information exceeded its validity or predates a material change. | Show when it was current and what use is prohibited; never silently display it as current. | Obtain a fresh source version or complete projection. |
| Unavailable | The owning contract, compatible version, authority, evidence payload, or operating source is absent, denied, unsupported, erased, or not reachable. | Show unavailable or blocked; do not substitute another source or improvised command. | Name the owner or dependency without exposing private topology or another relationship. |
| Disputed | An authorized party challenges accuracy, completeness, attribution, interpretation, or evidence sufficiency, and the dispute is unresolved. | Preserve the underlying fact and visibly qualify the affected public claim; do not present disputed success as settled. | Link the dispute to the exact source version/evidence and later resolution without overwriting either. |
| Superseded | A later accountable source version replaces the earlier meaning for current use. The earlier meaning remains historically valid for its recorded context. | Present the later meaning as current and the earlier meaning as historical when authorized; never merge them. | Preserve predecessor/successor lineage, reason category, accountable source, and effective time. |

These states are orthogonal to loading, empty, and error. Loading means the current authoritative state has not yet been obtained. Empty means the authoritative view has no qualifying item. Error means a request did not receive an authoritative outcome. None determines whether an existing value is unknown, stale, unavailable, disputed, or superseded.

## 8. Correction, Supersession, And Append-Only Evidence

Corrections follow the authority of the corrected meaning:

1. The accountable source issues a new source version or correction fact bound to the same tenant, relationship, and subject.
2. The correction identifies the prior source-relative identity/version and a non-sensitive reason category.
3. BP validates ownership, binding, compatibility, and evidence implications before producing a new relationship-projection version.
4. The public projection marks the earlier meaning superseded and uses the corrected meaning prospectively.
5. If the correction itself is constitutionally consequential, CE records a new evidence event before BP presents governed success.

Constitutional evidence is append-only. A correction, dispute, withdrawal, erasure event, or supersession creates additional evidence or lineage; it never updates, deletes, or disguises an earlier evidence record. Business projections may change their current interpretation, but must retain enough lineage to explain which source version and evidence supported each prior consequential state.

Payload correction and payload erasure are distinct from proof correction. Erasable customer payload may be replaced, invalidated, minimised, or purged under approved policy. The constitutional proof that a proposal, decision, action, correction, dispute, or erasure occurred remains append-only, with sensitive payload excluded or represented by a non-reconstructive reference/hash where approved.

## 9. BP Projection Of WBE Truth

WBE remains the sole authority for allowance and billing actuals, remaining allowance, budgets, ceilings, forecasts, assumptions, thresholds, and commercial consequences. BP composes WBE-authored meanings into the relationship projection; it does not replicate a second commercial ledger or recalculate commercial truth.

The logical flow is:

1. BP requests or receives a WBE-owned projection for the authenticated tenant and selected relationship or explicitly approved commercial subject.
2. WBE supplies the authoritative meaning with its source version, contract version, bindings, period, units, production/observation times, validity, assumptions, and correction status.
3. BP validates tenant/relationship applicability, supported contract version, and completeness.
4. BP relays the WBE meaning in customer language inside a new BP relationship-projection version while retaining WBE ownership and provenance.
5. Web presents only the BP projection and never calls WBE or calculates commercial meaning.

BP may retain only the minimum WBE reference/version and transient projection material needed for authorized composition, delivery, reconciliation, and dispute support. Any temporarily retained WBE value remains a non-authoritative copy of the exact WBE-authored version, inherits WBE validity and retention limits, and becomes stale when WBE says it is stale. It cannot be rebased, aggregated, rounded into a different consequence, combined with provider telemetry, or carried forward as current after WBE is unavailable.

BP must not:

- derive allowance use from messages, tokens, provider calls, work items, or conversation events;
- derive actual spend from budget, forecast, price, reservation, or provider cost;
- calculate remaining allowance, threshold state, forecast range, commercial consequence, tax, price, or margin;
- replace unavailable WBE truth with a last-known value presented as current;
- treat successful transport to or from WBE as a successful commercial outcome; or
- persist WBE values as independently mutable BP commercial truth.

## 10. Domain Adapter Provenance

A professional/domain adapter contributes outcome semantics for one declared goal or review context. It is a provenance-preserving input to BP, not a public source and not a new authority.

Every contribution must identify conceptually:

- accountable professional/domain owner and adapter contract version;
- authenticated tenant, selected relationship, and goal/review-context binding;
- domain outcome identity and customer-language label;
- baseline definition/version, measure definition/version, review period, and observation time;
- observed value or bounded qualitative assessment with unit and method where applicable;
- evidence references and whether each is pending, recorded, unavailable, disputed, or superseded;
- attribution basis, attribution limits, uncertainty, excluded influences, and unavailable inputs;
- outcome state and material change meaning;
- candidate attention reason, required customer action, consequence, validity window, and source-relative identity; and
- source production time, last confirmation, declared validity, source version, and correction lineage.

BP validates ownership, relationship/goal binding, supported version, evidence-reference legitimacy, and completeness before incorporating the contribution. BP owns the resulting public Result and all attention qualification and ordering. The adapter cannot grant authority, approve work, alter scope or lifecycle, define customer rights, calculate WBE truth, record constitutional evidence, or apply an adapter-local rank to the public order.

Domain-specific raw payload, credentials, prompts, model traces, provider telemetry, and unrelated customer data do not enter the generic relationship projection. Technical metrics may accompany an outcome only as clearly labelled supporting or limiting context.

## 11. Cross-Relationship Isolation

Every projection, item, source version, cursor, sequence, command expectation, draft handoff, evidence reference, WBE meaning, and adapter contribution is bound to one authenticated tenant and one selected Employment Relationship before public use.

Relationship switching is a context replacement, not a filter over a shared client-side collection. It requires a complete separately authorized BP projection. The prior relationship contributes no drafts, links, cursor, ordering state, authority, lifecycle, rights, budget, allowance, forecast, threshold, work, evidence, result, cached item truth, optimistic state, or pending command to the new context.

The following are prohibited:

- tenant or relationship authority derived from request content, browser storage, route text alone, cursor contents, or a source-domain claim;
- tenant-wide aggregation silently treated as relationship truth;
- joining evidence, WBE, PR, or adapter contributions by customer identity without an authorized relationship binding;
- reusing a cursor, source-relative identity, item key, or idempotency intent across relationships;
- displaying stale content from the prior relationship while the new context loads;
- merging same-labelled goals, work, outcomes, budgets, or evidence across relationships; and
- leaking the existence, count, identity, or state of another relationship through errors, empty states, ordering gaps, timing, or continuation behavior.

An item that cannot prove both bindings is unavailable to the public projection. It is not repaired by inference.

## 12. Retention And Data Minimisation

Retention follows data purpose and owner; it does not follow the longest-lived projection that has referenced the data.

| Data class | Minimisation rule | Retention rule |
|---|---|---|
| Constitutional evidence and correction lineage | Keep the minimum immutable proof needed to establish subject, actor/authority, state, basis, time, binding, and lineage. Do not place unnecessary customer payload in the ledger. | Append-only under constitutional retention. Erasure or correction adds proof; it does not delete prior proof. |
| BP relationship projection | Include only meanings required for the selected relationship, current view, available commands, reconciliation, rights, and evidence access. | Retain according to relationship-governance purpose and approved lifecycle policy; superseded projections are not retained as a second source of truth beyond audit/reconciliation need. |
| WBE projection material in BP | Keep only exact source provenance and the minimum transient WBE-authored values needed for composition and reconciliation. | Inherit WBE validity and owner-approved retention; never outlive usefulness as an authoritative display or become a BP commercial ledger. |
| Domain outcome contribution | Include approved measure, interpretation, attribution, uncertainty, and evidence references; exclude raw domain payload unless separately authorized and necessary. | Retain according to the goal review, dispute, and evidence purpose; superseded contribution versions remain only as required for lineage. |
| Technical metrics | Include only metrics necessary to explain reliability, limitation, uncertainty, or a blocked outcome. Aggregate or redact where individual detail is unnecessary. | Use the shortest operationally and legally sufficient period; do not retain merely to imply long-term customer value. |
| Erasable payload | Keep customer content or sensitive values outside immutable proof and reference them only when authorized. | Correct, invalidate, or purge under approved DPDPA policy while preserving non-reconstructive proof of governed events. |
| Cursor and client reconciliation state | Keep no interpretable business content and no reusable authority. | Short-lived and purpose-bound; discard on relationship switch, logout, incompatible version, expiry, or completed reconciliation. |

No public projection includes provider credentials, raw prompts, private reasoning, constitutional deliberation, unrelated tenant data, unrelated relationship data, or technical detail that is unnecessary for the customer meaning. Evidence export has its own assurance and sensitivity controls; eligibility for display does not imply eligibility for export.

## 13. Logical Data Flows

### 13.1 Relationship Projection Read

1. Authenticated server context establishes tenant and actor.
2. BP authorizes access to the selected Employment Relationship.
3. BP obtains BP-owned governance truth and valid contributions from WBE, PR, CE/evidence readers, and approved domain adapters.
4. Each contribution is checked for owner, source/contract version, tenant/relationship/subject binding, freshness, evidence state, and correction lineage.
5. BP qualifies and orders Needs-your-attention items and produces one relationship-projection version.
6. Web presents the BP projection without ranking, recalculation, cross-relationship merging, or private-service access.

### 13.2 Consequential Command And Evidence

1. Web submits an approved BP command against the selected relationship and expected BP projection version.
2. BP validates actor, tenant, relationship, subject, authority, scope, lifecycle, assurance, and source-version expectations.
3. Owning domains determine their authoritative outcomes; WBE alone determines commercial outcomes.
4. CE validates and records constitutional evidence where required.
5. BP presents success only after authoritative owner confirmation and Evidence First obligations are satisfied.
6. Partial or uncertain completion remains unresolved, pending, unknown, stale, unavailable, or disputed as applicable and is reconciled without blind overwrite.

### 13.3 Correction Or Dispute

1. The authorized correction/dispute is bound to the exact source version or evidence subject.
2. The accountable source records a new correction, dispute, or resolution fact.
3. CE receives additional evidence when constitutionally required; prior evidence remains unchanged.
4. BP produces a new relationship-projection version with explicit lineage and public qualification.
5. Web replaces the current interpretation without erasing authorized historical context or carrying it to another relationship.

## 14. G-F4-04 Closure Mapping

| G-F4-04 requirement | Contract section | Completion evidence |
|---|---|---|
| Canonical provenance | Sections 2 and 3 | Accountable owner, source subject/version, contract version, times, validity, bindings, identity, sequence, correction, and evidence meanings defined. |
| Freshness | Sections 3.2 and 7 | Current, stale, unknown, and unavailable use rules defined without browser inference. |
| Ordering and stable ties | Section 4 | BP-owned qualification, exact sequence, tie stability, and prohibited secondary sorting defined. |
| Actual, forecast, allowance, budget, and threshold | Section 5 | Categories, required provenance, prohibited substitutions, and correction rules defined. |
| Business outcome and technical metric | Section 6.1 | Customer-value and operational meanings separated with adapter accountability and attribution limits. |
| Pending and recorded evidence | Section 6.2 | Evidence First transition and authoritative confirmation boundary defined. |
| Tenant and relationship binding | Sections 3 and 11 | Joint binding and complete context replacement on relationship switch defined. |
| Unknown, stale, unavailable, disputed, superseded | Section 7 | First-class meanings, public consequences, and recovery/lineage defined. |
| Correction and append-only evidence | Section 8 | Source-owned correction, BP supersession, immutable evidence, dispute, and erasure separation defined. |
| BP projection of WBE truth | Section 9 | Relay/composition without replication, recalculation, independent mutation, or stale substitution defined. |
| Domain adapter provenance | Section 10 | Required lineage, evidence, attribution, compatibility, and prohibited authority defined. |
| Retention and minimisation | Section 12 | Purpose/owner-based retention classes and minimisation rules defined. |

**G-F4-04 data-semantics contribution result:** SATISFIED by `CR-GOAL-005-INST-006-03`, subject to the independent review required by G-F4-11. This contribution does not close G-F4-03, G-F4-05 through G-F4-13, implementation, release, deployment, or customer proof.

## 15. Acceptance Evidence Mapping

| Acceptance ID | Data obligation | Required acceptance evidence |
|---|---|---|
| UX-CONV-06 | Plan, Work, Deliverable, and Decision items retain owner, state, effect, evidence status, source version, and relationship binding without collapsing intended work, completed work, and outcome. | Sample every included consequential item type across current, pending, stale, unknown, disputed, and superseded conditions; verify all meanings and actions trace to the authoritative source and no technical metric appears as business effect. |
| UX-CONV-07 | Projection, cursor, item, draft handoff, WBE meaning, adapter contribution, evidence reference, and command expectation remain tenant-and-relationship bound. | Switch between at least two relationships in one tenant and between authorized/unauthorized tenant contexts; verify complete context replacement and zero carry-over or observable leakage of drafts, links, cursors, sequence, work, authority, budget, evidence, or results. |
| UX-CONV-08 | Needs-your-attention uses BP-supplied qualification, sequence, and stable ties. | Repeat full and cursor-based reads across refresh, reconnect, pagination, locale, viewport, and device; verify the exact BP sequence, stable equal-priority ties, and zero browser secondary sort or adapter/WBE ranking. |
| CCT-UX-BOUNDARY-01 | Scope-boundary confirmation is a separately identified, version-bound, Evidence First event and cannot be represented by an ordinary approval. | Verify the boundary subject, expected BP/source versions, typed acknowledgement, CE-recorded evidence, correction lineage, and no ordinary-approval substitution or cross-relationship replay. |
| CCT-UX-RIGHTS-01 | Rights, scope, authority, lifecycle, evidence access, and Emergency Stop retain independent authoritative meanings for the selected relationship. | Verify each included lifecycle state, including stale/unavailable source contributions, without hiding rights or deriving authority from capability, commercial state, or cached projection data. |
| CCT-UX-EF-01 | Pending evidence never appears as recorded; recorded requires authoritative evidence confirmation; disputes and corrections append lineage. | Exercise pending-to-recorded, pending-to-unavailable, recorded-to-disputed, and recorded-to-superseded scenarios; verify zero fabricated record IDs, zero optimistic success, and preservation of prior evidence. |
| UX-SHELL-06 | Missing owner contract, unsupported version, unavailable source, or unbound contribution remains unavailable or blocked. | Remove or invalidate each source class in turn; verify no BP/web fallback calculation, private service route, stale-as-current substitution, cross-relationship inference, or fabricated success. |

Acceptance evidence must identify the tested source/contract versions and fixture or environment provenance. Static contract checks, fixture-backed behavior, live integration, deployment evidence, and customer proof must be labelled distinctly and must not be represented as one another.

## 16. Review And Authorization Boundary

This contribution is complete within INST-006 Decision Space. It requires independent Solution Architect and Constitutional Analyst review as assigned by the INST-006 charter and the integrated C-065-compliant F4 review defined by G-F4-11.

No section authorizes a concrete database schema, migration, endpoint, wire contract, generated client, application code, test implementation, provider activation, autonomous-runner dispatch, release, or deployment. Any owner contract absent from the approved F4 package remains blocked or unavailable; downstream work may not invent a default.

## 17. Basis

- `goals/GOAL-005-f4-business-contribution.md` — CR-GOAL-005-INST-003-03
- `architecture/reference/components/relationship-workspace.md` — CR-GOAL-005-INST-004-07
- `architecture/reference/data/ledger-design.md` — three-ledger separation and immutable constitutional evidence
- `architecture/reference/data/evidence-schema.md` — Evidence First and append-only evidence-state lineage
- ADR-003 — authenticated tenant authority and tenant isolation
- ADR-011 — non-destructive constitutional evidence evolution
- C-005, C-007, C-023, C-026 through C-030, C-034, C-036 through C-044, C-048, C-049, C-051, C-056, C-063, C-083 through C-085, C-088 through C-091, and C-099