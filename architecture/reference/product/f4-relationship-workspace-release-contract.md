# WC-034 F4 Relationship Workspace — First-Release Product Contract

## Attestation

| Field | Value |
|---|---|
| Institution | INST-011 — Product Owner |
| Goal | GOAL-005 |
| Work Contract | WC-034 F4 |
| Contribution ID | CR-GOAL-005-INST-011-04 |
| Date | 2026-08-10 |
| Status | COMPLETE |
| Gate contribution | G-F4-06 — Product release composition |
| Contribution boundary | Product scope, customer language, release composition, omission behavior, and acceptance only; no architecture, endpoint, wire schema, implementation, provider activation, deployment, or F5-F8 authority |

## 1. Product Decision

The first F4 release gives a customer one truthful workspace for one selected Employment Relationship at a time. It answers:

1. What is planned?
2. What needs me now, in what authoritative order, and why?
3. What work is proposed, under way, blocked, or complete?
4. What business result is evidenced, and what remains uncertain?
5. What allowance or budget consequence is approaching?
6. What authority exists, and which rights and controls can I exercise?

The release includes a relationship context plus six mandatory views: **Plan**, **Needs your attention**, **Work**, **Results**, **Usage & budget**, and **Rights & control**. A mandatory view is never silently removed. When its owner-approved contract or authoritative state is absent, the view remains reachable and says **Unavailable** or **Blocked**, identifies the business consequence, and offers only an owner-approved next action.

The workspace presents Business Platform (BP) public relationship projections and customer commands only. It does not infer relationship truth, ordering, authority, billing truth, business success, or command availability in the browser. It does not expose direct customer access to Professional Runtime (PR), the WAOOAW Billing Engine (WBE), the Constitutional Engine (CE), a ledger, a provider, or any internal service.

## 2. Selected Relationship Context

The first release operates on exactly one customer-authorized relationship. Before the six views, it must identify in customer language:

- the employed professional;
- the relationship lifecycle state;
- the current goal, or the truthful absence of one;
- whether the displayed information is current, stale, unknown, or partly unavailable;
- the time of last authoritative confirmation;
- the reachability of **Emergency Stop**.

Changing the selected professional means changing the complete relationship context. The release carries no draft, link, item, ordering state, authority, scope, budget, allowance, evidence, work, or result from the previous relationship. Until the replacement context is authoritatively obtained, the new selection is **Loading**; the prior relationship is not displayed as if it belonged to the new selection.

The first release provides no combined or cross-relationship workspace. It does not total budgets, merge attention lists, compare professionals, or establish a global priority.

## 3. Mandatory View Composition

### 3.1 Plan

**Customer purpose:** Understand the current proposed or agreed path from the relationship goal to intended work.

**Mandatory item families:**

- current goal, including owner, baseline status, measure, review period, and attribution boundary;
- current plan, including proposed/agreed state, owners, intended effect, timing, dependencies, assumptions, and review point;
- Priority Work identified by the authoritative relationship projection;
- plan dependencies requiring customer authority, information, funding, scheduling, or review.

**Mandatory first-release commands when declared available by the authoritative projection:**

- **Review plan**;
- **Agree to plan**;
- **Request a change**;
- **Confirm scope boundary**, as a distinct typed-acknowledgement command and never as ordinary approval;
- **Pause affected work** or **Cancel plan** when the customer's current rights permit it.

**Product rules:** A proposed plan is not approved authority, scheduled work, completed work, or a result. Priority Work is authoritative relationship information; the browser does not create, score, or reorder it. If no current plan exists, say **No plan has been proposed yet** or **No current plan applies**, whichever is authoritative, and show only a valid next action.

### 3.2 Needs Your Attention

**Customer purpose:** See only the matters requiring a customer response or materially time-sensitive awareness, in the order owned by the relationship.

**Mandatory item families:**

- approval or rejection required;
- scope-boundary confirmation required;
- customer information, decision, authority, funding, or scheduling dependency;
- allowance threshold or budget boundary requiring a customer choice or acknowledgement;
- material result, forecast, changed assumption, or attribution uncertainty requiring review;
- lifecycle, rights, safety, compliance, evidence, or authority exception requiring customer action.

**Mandatory item content:** reason for attention, accountable owner, current state, customer consequence, due meaning or **No stated deadline**, available action, and evidence status.

**Mandatory first-release commands when declared available by the authoritative projection:**

- **Review**;
- **Approve** or **Reject** the exact subject;
- **Confirm scope boundary** with distinct typed acknowledgement;
- **Provide information** or **Respond** through an approved relationship command;
- **Review assumptions**;
- **Change pacing** or **Pause affected work** for an authoritative allowance/budget consequence;
- **Review evidence** or **Acknowledge limitation** where policy permits.

**Product rules:** The view displays the complete qualifying list in the exact authoritative order and preserves stable ties. The browser performs no ranking, secondary sort, personalization, local urgency calculation, or cross-relationship aggregation. Informational updates without a required or materially time-sensitive customer response do not appear here. An empty view says **Nothing needs your attention right now** and does not imply that all work is complete or successful.

### 3.3 Work

**Customer purpose:** Understand professional activity without confusing activity with customer value.

**Mandatory item families:**

- work item;
- deliverable;
- approval or decision associated with work;
- schedule or review commitment.

Every consequential item exposes: accountable owner, business state, expected or observed effect, evidence status, and the valid next customer action or **No action available**, with a business reason.

**Mandatory first-release commands when declared available by the authoritative projection:**

- **Review work** or **Review deliverable**;
- **Approve** or **Reject** the exact next step;
- **Accept deliverable**, **Reject with reason**, or **Request revision**;
- **Pause work**, **Resume work**, or **Provide input**;
- **Review evidence**.

**Product rules:** Work uses customer states such as Proposed, Approved, Scheduled, Active, Paused, Blocked, Completed, Cancelled, Failed, and Outcome unknown. Transport, queue, retry, model, provider, token, or runtime states are not shown as the business effect. **Completed** means the activity completed; it does not mean the intended business outcome was achieved.

### 3.4 Results

**Customer purpose:** Judge evidenced customer value against declared goals without manufactured attribution.

**Mandatory item families:**

- business outcome measure;
- baseline or **Baseline needed**;
- review period;
- evidence support and evidence status;
- attribution basis, limits, and uncertainty;
- accountable outcome owner and valid review action.

**Mandatory first-release commands when declared available by the authoritative projection:**

- **Review evidence**;
- **Challenge attribution**;
- **Confirm baseline**;
- **Review result**;
- **Request goal change** through an approved command.

**Product rules:** Results prioritize domain-approved customer outcomes, not technical or runtime metrics. A completed deliverable is not automatically a result. A healthy runtime is not customer success. When attribution cannot be established, show **Attribution unknown** and withhold achieved/not-achieved claims that depend on it. If no result is measurable yet, state whether the baseline is missing, the review period is still open, evidence is pending, or the owner contract is unavailable.

### 3.5 Usage & Budget

**Customer purpose:** Understand actual allowance use, financial limits, forecasts, and the consequences of approaching a boundary.

**Mandatory item families:**

- actual customer-understandable allowance used and remaining;
- agreed financial ceiling and current authoritative actual, when applicable;
- threshold state and review period;
- forecast range, assumptions, uncertainty, validity, and accountable owner;
- typed commercial consequence of approaching or reaching a boundary.

**Mandatory first-release commands when declared available by the authoritative projection:**

- **Review usage**;
- **Review forecast assumptions**;
- **Change pacing**;
- **Pause affected work**;
- **Set or lower budget ceiling**;
- **Request budget increase** or **Purchase approved addition** only when a Founder-approved commercial policy and owner-approved command explicitly permit it.

**Product rules:** Allowance is not currency. Forecast is not actual usage or spend. Token consumption, provider cost, request count, latency, or execution time does not substitute for customer allowance or financial truth. BP and the browser do not calculate WBE-owned actuals, forecasts, thresholds, or consequences. When WBE truth is unavailable or stale, no previous value is presented as current and no purchase, increase, or pacing success is claimed.

### 3.6 Rights & Control

**Customer purpose:** Understand and exercise relationship rights without having to interpret capability, trust, or technical controls.

**Mandatory item families:**

- current scope, including inclusions, exclusions, duration, and state;
- current authority, including owner, reach, duration, ceiling, and stop condition;
- relationship lifecycle and typed consequence;
- approval and scope-boundary distinction;
- evidence inspection and export rights;
- pause, resume, renewal, and termination rights where the current lifecycle permits them;
- unconditional **Emergency Stop** reachability.

**Mandatory first-release commands when declared available by the authoritative projection:**

- **Review scope** and **Confirm scope boundary**;
- **Review authority**, **Constrain authority**, **Suspend authority**, or **Revoke authority**;
- **Pause relationship**, **Resume relationship**, **Renew relationship**, or **Terminate relationship**;
- **Review evidence** and **Export evidence**;
- **Emergency Stop**.

Grant, expansion, or restoration of authority is visible only when an approved authority policy and command make it available. A capability never implies authority. Emergency Stop remains reachable regardless of plan, work, billing, allowance, evidence, degraded-service, or lifecycle presentation state; this contract does not alter its dedicated behavior.

## 4. Customer Language Contract

The release uses these exact primary labels:

| Primary label | Required customer meaning |
|---|---|
| **Plan** | Intended work and its assumptions; not permission, completion, or success |
| **Priority Work** | Work made prominent by the authoritative relationship owner; not browser-ranked activity |
| **Needs your attention** | A response or materially time-sensitive understanding is required |
| **Work** | Professional activity and deliverables; not automatically customer value |
| **Results** | Evidence-backed customer outcomes with attribution limits |
| **Usage & budget** | Allowance actuals, financial boundaries, forecasts, and consequences kept distinct |
| **Rights & control** | Scope, authority, lifecycle, evidence rights, and Emergency Stop |

Customer-facing content must use the customer's domain and business outcome language. Internal service names, queue states, provider ranking, model names, tokens, traces, technical metrics, tenant identifiers, internal identifiers, and ledger implementation terms are omitted from ordinary customer meaning. A correlation reference may be provided for support after an error, but it is not presented as an explanation of the business state.

Consequential actions use explicit command labels such as **Approve plan**, **Reject deliverable**, **Confirm scope boundary**, **Pause affected work**, or **Revoke authority**. Generic labels such as **Submit**, **Continue**, **OK**, or **Confirm** do not stand alone where the subject or consequence matters.

## 5. Omission And Unavailability Rules

1. The six mandatory views and relationship context are always reachable for an authorized selected relationship.
2. An item family with no authoritative item is omitted from its list; the containing view shows a precise empty meaning when the whole view is empty.
3. A missing owner-approved contract, unsupported command, denied authority, or unavailable owner is not treated as an empty list. The affected family remains named as **Unavailable** or **Blocked** with the reason and business consequence that can be truthfully disclosed.
4. A command is shown only when the authoritative projection declares it available for the current actor, relationship, subject, state, and version. The browser does not invent disabled future commands.
5. When a mandatory right exists but its digital exercise is unavailable, the right remains visible with the approved alternate route or escalation. It is never silently omitted.
6. Evidence, usage, budget, result, or authority details that are restricted for the current actor are not hinted at through counts, labels, timing, or error differences.
7. A partially unavailable view identifies which facts remain authoritative and which do not. Available facts do not fill or imply unavailable facts.
8. No deferred capability is represented by a fabricated destination, mock value, optimistic success, local-only mutation, or private internal-service connection.

## 6. Truthful State Contract

| State | Required customer treatment | Prohibited treatment |
|---|---|---|
| **Loading** | Keep the selected relationship context identifiable, state that current information is being obtained, preserve safe customer intent, and prevent consequential action based on unresolved current state. | Showing a placeholder, cached value, or previous relationship as current. |
| **Empty** | State exactly what is absent: no item exists yet, or no item currently qualifies for this view. Offer only an authoritative valid next action. | Implying completion, success, failure, or unavailable capability. |
| **Error** | State that the authoritative view or command outcome could not be confirmed; say **Success not confirmed** for consequential commands; preserve intent where safe; provide retry, reconciliation, or support reference. | Optimistic success, duplicate blind submission, or technical transport acceptance shown as business completion. |
| **Unknown** | Name the unknown field, owner, effect, attribution, or state; explain the customer consequence; withhold dependent success claims and consequential commands; identify accountable recovery when available. | Replacing unknown with a guessed state, zero, no-change, success, or failure. |
| **Stale** | Say when the information was current and what may have changed; request authoritative refresh; exclude stale information from fresh assurance, ordering changes, approvals, forecasts, actuals, and success claims. | Quietly presenting old information as current or using it to authorize a decision. |
| **Unavailable / Blocked** | Name the affected capability or item family, distinguish absence of contract from temporary owner unavailability or denied authority, explain the business consequence, and show only an approved recovery route. | Improvising a command, using another source, or treating the capability as empty or successful. |
| **Pending evidence** | State that evidence has not yet received authoritative recorded confirmation. | Labelling the action evidenced, recorded, complete, or successful. |

These treatments apply independently within each mandatory view. One current section does not make another unknown or stale section current.

## 7. Consequence Disclosures

Before a consequential command, the customer sees the exact subject, accountable owner, current state, intended effect, affected relationship and work, downstream dependency, expiry or duration where applicable, reversibility, evidence consequence, and the consequence of declining or taking no action when known.

The first release applies these fixed product rules:

- ordinary approval never confirms or expands scope;
- scope-boundary confirmation always has its own command, current assurance requirement, named inclusions/exclusions, consequence, and typed acknowledgement;
- authority grant, expansion, restoration, and materially consequential narrowing or revocation require fresh assurance and typed acknowledgement under the approved policy;
- lifecycle commands disclose immediate work, schedule, evidence, allowance, billing, and re-entry consequences without claiming a WBE outcome before confirmation;
- evidence export discloses subject, period, completeness, sensitivity, intended recipient/use, redaction or limitation, and whether the export is authoritative or partial;
- uncertain or partial multi-owner command outcomes remain **Unresolved** until reconciled and do not display success.

## 8. Founder Policy Decisions Required

The Product Owner does not invent the following policies. INST-013 must route each unresolved choice to the Registrant/Founder and the accountable owner. Until resolved, the affected command or consequence remains **Blocked** or **Unavailable**.

| Policy ID | Founder decision required | First-release behavior until decision |
|---|---|---|
| F4-POL-01 | Which governed approvals and rejections, beyond scope and authority decisions, are materially consequential enough to require typed acknowledgement; include irreversible loss, cancellation, financial, legal, safety, and deadline classes. | Present the decision and consequence, but do not enable a materially consequential approval/rejection lacking an approved acknowledgement policy. |
| F4-POL-02 | Which evidence exports may be self-served by sensitivity, recipient, intended use, redaction, and material incompleteness; define any customer-visible restriction or alternate fulfillment route. | Permit ordinary evidence inspection; mark affected export unavailable with the approved escalation route once supplied. |
| F4-POL-03 | Commercial treatment at allowance thresholds and budget ceilings: whether work pauses, degrades, continues, or may use an approved paid addition; define purchase/increase eligibility and customer consequence. | Show authoritative actual, threshold, forecast, and known consequence; do not offer purchase/increase or invent degradation behavior. |
| F4-POL-04 | Which authority grants, expansions, restorations, constraints, suspensions, and revocations are customer self-service, and the typed consequences when affected work cannot be recovered. | Always show current authority and permit only owner-approved protective reduction commands; block grant/expansion/restoration without approved policy. |
| F4-POL-05 | Lifecycle commercial and re-entry policy for pause, resume, renewal, and termination, including billing/allowance treatment, scheduled work, retained evidence, and when fresh assurance is mandatory on resume. | Emergency Stop remains available; other lifecycle commands remain unavailable unless their complete typed consequence is owner-approved. |
| F4-POL-06 | What customer action remains permissible when a required owner projection is stale, unknown, partially unavailable, or has an unresolved multi-owner outcome. | Allow read-only review of facts still marked authoritative; withhold affected consequential commands and success claims. |

These are policy decisions, not permission to choose assurance mechanisms, API shapes, persistence, or implementation. Security, constitutional, solution, BP, WBE, and domain owners retain their assigned Decision Spaces.

## 9. Explicit Deferrals And Exclusions

The first F4 release defers or excludes:

- F5 omnichannel continuity, cross-channel notifications, and any continuity claim;
- F6 voice, transcription, attachments, and their consent or retention choices;
- F7 Founder administration;
- F8 integrated release closure beyond focused F4 evidence;
- multi-relationship aggregation, global attention, professional comparison, or merged budget/authority/evidence views;
- browser ranking, personalization, local reordering, or browser-created priority;
- provider connection, provider activation, consequential provider work, or provider/model choice display;
- deployment to any environment and any claim of customer proof;
- technical/runtime metrics as product success measures;
- direct customer or browser access to PR, WBE, CE, ledgers, providers, or other internal services;
- endpoint paths, wire schemas, generated clients, persistence, component design, and implementation.

## 10. Implementation-Ready Acceptance Scenarios

The scenarios below are normative product acceptance. They require owner-approved contracts and executable evidence before implementation can be accepted; this contribution itself does not authorize implementation.

### UX-CONV-06 — Structured Relationship Items

**Given** one authorized selected relationship containing Action/Decision, Plan, Work, and Deliverable items across available and unavailable command states, **when** the customer reviews each item by keyboard and pointer, **then** every consequential item shows owner, customer-language state, business effect, evidence status, and exactly the authoritative available commands or **No action available** with a reason.

**Exact acceptance:** 100% of sampled item types answer who owns it, what is true, what changes, and what the customer may do next; proposed plan is never shown as authority; completed work is never shown as a result without outcome evidence; no technical status is used as business effect; no unavailable command can be invoked.

### UX-CONV-07 — Selected Relationship Isolation

**Given** two authorized relationships with deliberately different drafts, links, plans, attention order, work, results, allowance, budget, authority, and evidence, **when** the customer switches from relationship A to relationship B during loaded, loading, stale, offline/reconnect, and error/retry conditions, **then** the complete workspace is rebound to B only after authoritative confirmation and no A state appears as B state.

**Exact acceptance:** zero cross-relationship carry-over in every mandatory view and action; zero command targets the prior relationship; prior content is not presented as current while B loads; returning to A obtains its separately authorized context rather than a merged browser state.

### UX-CONV-08 — Authoritative Attention Ordering

**Given** qualifying and non-qualifying items, including equal-priority ties, **when** Needs your attention is loaded, refreshed, paged or incrementally continued, reconnected, and viewed on supported desktop and mobile presentations, **then** only qualifying items appear in the exact authoritative sequence and tied items retain their supplied relative order.

**Exact acceptance:** zero browser ranking, scoring, timestamp sort, secondary sort, personalization, local reordering, or cross-relationship aggregation; informational-only items are absent; an empty list says **Nothing needs your attention right now** without claiming work completion or success.

### CCT-UX-BOUNDARY-01 — Scope Is Not Approval

**Given** an ordinary approval and a scope-boundary decision with named inclusions, exclusions, relationship, duration, authority effect, downstream action, and consequence, **when** the customer attempts each decision, **then** ordinary approval affects only its stated next step and scope confirmation requires a separate current-assurance flow and typed acknowledgement.

**Exact acceptance:** zero ordinary approvals confirm, enlarge, or silently alter scope; the typed acknowledgement names the boundary and consequence; stale or unknown scope/assurance blocks confirmation; success appears only after authoritative confirmation and required evidence.

### CCT-UX-RIGHTS-01 — Rights And Control Reachability

**Given** every included relationship lifecycle state and a degraded owner state, **when** the customer opens Rights & control using keyboard and supported mobile/desktop navigation, **then** current scope, authority, lifecycle, evidence access/export meaning, approval/boundary distinction, and Emergency Stop are reachable and understandable without technical vocabulary.

**Exact acceptance:** all mandatory rights/control families remain named; a digitally unavailable right supplies only an approved alternate route; no commercial, evidence, loading, error, stale, unknown, or degraded state hides Emergency Stop; capability is never presented as authority.

### CCT-UX-EF-01 — Evidence Status Honesty

**Given** pending, authoritatively recorded, failed, unknown, stale, disputed, incomplete, and unavailable evidence states, **when** a customer performs or reviews a governed action, **then** **Recorded** appears only after authoritative confirmation and all other states retain their distinct customer meaning and consequence.

**Exact acceptance:** every tested transition shows pending before recorded where recording is required; zero transport success, local state, PR processing, retry completion, or pending evidence is shown as recorded success; unconfirmed command outcome says **Success not confirmed** or **Unresolved** and offers reconciliation rather than blind success.

### UX-SHELL-06 — Honest Missing Capability

**Given** each missing, denied, deferred, unsupported, stale, or temporarily unavailable owner contract needed by F4, **when** the customer visits the affected mandatory view or attempts to locate its command, **then** the view remains reachable and identifies the affected family as **Unavailable** or **Blocked**, explains the truthful business consequence, and offers only an approved recovery action.

**Exact acceptance:** zero fabricated destination, placeholder actual, mock result, optimistic mutation, private internal-service path, or unowned capability claim; no F5-F8, provider activation, deployment, or technical-metric success is implied; mandatory rights are not silently omitted.

## 11. G-F4-06 Closure Map

| G-F4-06 requirement | Product decision in this contract | Closure evidence |
|---|---|---|
| Mandatory first-release views | Relationship context plus Plan, Needs your attention, Work, Results, Usage & budget, Rights & control | Sections 2 and 3 |
| Mandatory item families | Goal/plan/priority/dependency; attention reasons; work/deliverable/decision/schedule; business outcomes; allowance/budget/forecast; scope/authority/lifecycle/evidence/Stop | Section 3 |
| Mandatory command families | Plan review/change, approval/rejection, distinct boundary confirmation, work/deliverable control, results review, pacing/budget choices, rights/authority/lifecycle/evidence control | Section 3, subject to authoritative availability and Founder policy |
| Customer labels | Exact primary labels and consequence-specific command labels | Section 4 |
| Omission behavior | Mandatory views retained; truthful empty versus unavailable/blocked; rights never silently omitted; no invented commands | Section 5 |
| Truthful system states | Loading, empty, error, unknown, stale, unavailable/blocked, and pending evidence remain distinct | Section 6 |
| Consequence disclosures | Exact subject, owner, state, effect, relationship, dependencies, duration/expiry, reversibility, evidence, and decline/no-action consequence | Section 7 |
| Founder policy escalation | Six bounded rights, assurance, commercial, lifecycle, export, and uncertainty choices; no defaults invented | Section 8 |
| Domain-neutral acceptance | All seven F4 acceptance IDs have Given/When/Then scenarios and exact measurable acceptance | Section 10 |
| Scope preservation | No F5-F8, deployment, provider activation, browser ranking, technical-metric success, or direct internal-service access | Sections 1 and 9 |

**G-F4-06 decision:** SATISFIED by `CR-GOAL-005-INST-011-04`, subject to the integrated F4 package's independent review. This closes Product Owner release-composition ambiguity only. It does not close G-F4-03 through G-F4-05 or G-F4-07 through G-F4-13, approve owner contracts, authorize implementation, authorize deployment, or resolve the Founder policy decisions in Section 8.

## 12. Basis

- `goals/GOAL-005-f4-business-contribution.md` — CR-GOAL-005-INST-003-03
- `architecture/reference/components/relationship-workspace.md` — CR-GOAL-005-INST-004-07
- `work-contracts/WC-034-goal005-webportal-founder-admin.md` — F4 boundary and acceptance identifiers
- `constitution/INSTITUTIONAL_BACKLOG.md` — IB-014 customer self-service demand and constitutional portal constraints

## 13. Post-Authorization Re-Attestation

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-011-05 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-10T13:30:17+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-011-05 |
| `acceptance_id` | ACC-GOAL-005-INST-011-05 |
| Gate contribution | G-F4-06 — Product release composition and DMA first-release selection |
| Decision | RE-ATTESTED — SATISFIED within INST-011 Decision Space |

After accepting `GOA-GOAL-005-INST-011-05` at `2026-08-10T13:25:23+00:00`, INST-011 independently re-opened this candidate against `GEP-GOAL-005-INST-013-04` and R-062 / `CR-GOAL-005-INST-002-05`. INST-011 adopts Sections 1-12 without substantive amendment and confirms the Order 1 G-F4-06 product composition: one selected Employment Relationship context with the six mandatory first-release views **Plan**, **Needs your attention**, **Work**, **Results**, **Usage & budget**, and **Rights & control**; authoritative action availability and attention ordering; truthful empty, stale, unknown, blocked, unavailable, error, and pending-evidence states; the deferrals in Section 9; and the unresolved Founder policy escalations in Section 8.

INST-011 also confirms the Registrant's selection of **Digital Marketing Agent (DMA)** as the sole WC-034 F4 first-release profession. This selection does not import DMA-specific fields or professional judgment into the generic Relationship Workspace contract.

### Order 4 DMA Domain-Authority Evidence Requirement

Before Order 4 can incorporate DMA domain evidence or G-F4-09 can close, a governing record must name the DMA domain authority and provide attested provenance for evidence covering all of the following:

- F4-specific customer-outcome vocabulary;
- baselines and measures;
- authoritative evidence sources;
- attribution boundaries and limits;
- uncertainty treatment;
- review cadence; and
- material DMA attention candidates.

Yogesh Khandge is the named DMA domain authority for this F4 contribution. The Founder direction recorded on 2026-08-10 explicitly defers Sujay until WAOOAW is operational; Sujay has no current F4 contribution, review, approval, or availability dependency. Existing approved DMA knowledge and an F4-specific institutional professional synthesis may be incorporated with explicit provenance for Yogesh governance and review, but neither may be represented as direct Yogesh testimony. INST-011 must attest the evidence provenance, INST-003 must validate business-outcome semantics, and INST-005 must validate generic adapter conformance. Generic adapter conformance alone cannot close G-F4-09.

### Preserved Boundaries

The Section 8 policy escalations were resolved prospectively by `FPD-GOAL-005-F4-POL-01` through `FPD-GOAL-005-F4-POL-06` and are incorporated below. Those decisions grant no architecture, endpoint, API, wire-schema, canonical OpenAPI, generated-client, implementation, test, migration, build, provider-activation, deployment, F5-F8, self-review, or self-merge authority. G-F4-12 implementation acceptance and G-F4-13 deployment remain separately gated.

## 14. Amendment 5 Order 2 Acceptance Record

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-005 |
| `acceptance_id` | ACC-GOAL-005-INST-011-08 |
| `record_type` | Acceptance Record |
| `authorization_id` | GOA-GOAL-005-INST-011-08 |
| `accepted_at` | 2026-08-11T02:09:53+00:00 |
| Decision | ACCEPTED - incorporate Founder-selected F4 policy decisions prospectively into this product contract only |

## 15. Amendment 5 Order 2 Founder Decision Incorporation

### Contribution Record

| Field | Value |
|---|---|
| `institution_id` | INST-011 |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-011-08 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-11T02:09:53+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-011-08 |
| `acceptance_id` | ACC-GOAL-005-INST-011-08 |
| `acceptance_timestamp` | 2026-08-11T02:09:53+00:00 |
| contribution_scope | Record Founder selections `F4-POL-01` through `F4-POL-06` as first-release product policy and publish customer-visible treatment, enabled versus unavailable command families, release composition, fail-closed behavior, and incorporation dependencies |
| decision_boundary | Product incorporation only. No policy reinterpretation, architecture, API/schema design, mechanism selection, implementation, deployment, F5-F8, self-review, or merge authority. |

### Founder-selected first-release policy set (prospective)

| Policy | Founder decision record | Selected option | Product incorporation |
|---|---|---|---|
| `F4-POL-01` | `FPD-GOAL-005-F4-POL-01` | A | Typed acknowledgement is required for irreversible loss, cancellation, financial consequence, legal consequence, safety consequence, and deadline consequence classes. |
| `F4-POL-02` | `FPD-GOAL-005-F4-POL-02` | A | Self-service remains limited to the customer's own authorized evidence view/export routes already within approved sensitivity and recipient boundaries; all other exports use an alternate route. |
| `F4-POL-03` | `FPD-GOAL-005-F4-POL-03` | B | Read-only and non-consequential access continues while affected consequential work pauses at an allowance threshold or budget ceiling. |
| `F4-POL-04` | `FPD-GOAL-005-F4-POL-04` | A | Self-service permits protective reduction only; authority grant, expansion, and restoration remain non-self-service. |
| `F4-POL-05` | `FPD-GOAL-005-F4-POL-05` | B | Emergency Stop remains immediate; selected owner-approved pause/resume paths may be enabled with explicit consequence and re-entry treatment; renewal/termination remain closed. |
| `F4-POL-06` | `FPD-GOAL-005-F4-POL-06` | A | Read-only review of still-authoritative facts is permitted; affected consequential commands and success claims remain withheld while required owner state is unresolved. |

### Customer-visible treatment and release composition

1. Relationship context and the six mandatory views in Sections 2-3 remain the first-release composition with truthful state semantics in Section 6.
2. Consequential approvals/rejections in the selected material classes require typed acknowledgement; unresolved material-class eligibility remains blocked.
3. Evidence inspection remains available where already authorized; export families outside selected self-service bounds remain unavailable and use the approved alternate route.
4. At allowance/budget boundary conditions, read-only and non-consequential access may continue while affected consequential work remains paused unless and until owner-authoritative policy/command conditions are met.
5. Rights and control preserve protective reduction paths where owner-approved; self-service authority grant/expansion/restoration remains unavailable.
6. Emergency Stop remains independently reachable regardless of policy family state.
7. During stale, unknown, partial, unavailable, or unresolved owner state, still-authoritative read facts may remain visible while affected consequential commands and success claims remain withheld.

### Enabled versus still-unavailable command families

| Command family | Incorporation status under `A, A, B, A, B, A` |
|---|---|
| Material consequential approvals/rejections | Enabled only for selected classes with required typed acknowledgement; otherwise blocked. |
| Evidence inspection | Enabled where already authorized. |
| Self-service evidence export | Enabled only within selected self-service boundaries; other export families remain unavailable. |
| Commercial continuation at threshold/ceiling | Consequential continuation remains paused/blocked unless owner-authoritative conditions are satisfied. |
| Protective authority reduction | Enabled only where already owner-approved. |
| Authority grant/expansion/restoration | Remains unavailable (non-self-service). |
| Pause/resume lifecycle paths | May be enabled only for selected owner-approved paths with explicit consequence and re-entry treatment. |
| Renewal/termination lifecycle paths | Remains unavailable/closed. |
| Degraded-state consequential execution | Remains withheld while required owner state is unresolved. |
| Emergency Stop | Always enabled and independent. |

### Exact fail-closed behavior and dependencies

The fail-closed baseline in Section 8 remains mandatory and is now applied prospectively with the Founder selections above:

- no materially consequential approval/rejection executes without required typed acknowledgement;
- no out-of-bound self-service export executes;
- no unresolved consequential commercial continuation executes;
- no self-service authority grant, expansion, or restoration executes;
- no unresolved lifecycle renewal/termination executes;
- no affected consequential command or success claim executes under unresolved required owner state.

This incorporation depends on:

- Solution incorporation record `CR-GOAL-005-INST-005-11` for canonical owner/relationship-workspace specification alignment; and
- Security verification record `CR-GOAL-005-INST-007-07` for accepted floor preservation.

Until both dependencies are incorporated and no conflict is declared by their accountable offices, affected command families remain `BLOCKED` or `UNAVAILABLE` exactly as declared above.

## 16. Learning Record (GEOM G-05)

| field | value |
|---|---|
| institution_id | INST-011 |
| goal_id | GOAL-005 |
| record_id | LR-GOAL-005-INST-011-06 |
| record_type | Learning Record |
| improvement_signal | Recording Founder-selected policy options as a prospective, command-family matrix preserves customer-visible truth while preventing inferred defaults, architectural invention, and floor weakening. |
| constitutional_discovery | no |
| evolution_triggered | no |
| produced_at | 2026-08-11T02:09:53+00:00 |
