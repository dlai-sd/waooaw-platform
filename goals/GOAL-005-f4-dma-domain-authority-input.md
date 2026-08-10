# GOAL-005 F4 DMA Domain-Authority Input

## Contribution Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-011 — Product Owner |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-011-06 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-10T14:04:48+00:00 |
| `authorization_id` | GOA-GOAL-005-INST-011-06 |
| `acceptance_record` | ACC-GOAL-005-INST-011-06 |
| Date | 2026-08-10 |
| Gate contribution | G-F4-09 — Product incorporation of DMA outcome, evidence, attribution, uncertainty, cadence, and attention semantics |
| Decision | CONTRIBUTED — ready for the separately authorized INST-003 business-semantics validation, then INST-005 adapter-conformance validation |
| Authority boundary | Product incorporation and provenance attestation only; no direct domain-authority testimony, business validation, adapter approval, architecture, interface, schema, implementation, provider activation, deployment, F5-F8, or self-review authority |

## 1. Authority And Provenance

For WC-034 F4, **Yogesh Khandge is the current DMA domain authority**. Founder direction recorded in `GEP-GOAL-005-INST-013-04` is: "Yogesh will do this. Sujay will come in picture once waooaw is operational."

**Sujay Khandge is deferred until WAOOAW is operational.** Sujay has zero current F4 contribution, review, approval, availability, or dependency. Any later Sujay participation requires a separately authorized operational-stage process and is not an entry condition, validation condition, or approval condition for this record or G-F4-09.

This record is an **institutional professional synthesis presented under Yogesh governance**. It is produced by INST-011 from approved repository DMA knowledge and the Founder direction above. It is **not direct Yogesh testimony**, does not quote Yogesh as the author of the professional content, and does not claim that Yogesh personally drafted, reviewed, or approved the synthesized content. Naming Yogesh as current domain authority establishes the governance route; it does not convert repository synthesis into personal testimony or personal content approval.

### 1.1 Approved Repository Sources

| Source | Incorporated authority |
|---|---|
| `goals/GOAL-005-execution-plan.md` — GEP-GOAL-005-INST-013-04, GOA-GOAL-005-INST-011-06, and ACC-GOAL-005-INST-011-06 | DMA selection, Yogesh authority, Sujay deferral, Order 4 sequence, required evidence, and exclusions |
| `architecture/reference/agents/digital-marketing-agent.md` v3.1 | Approved DMA vocabulary, acquisition, enquiry-to-booking, conversion, analytics, attribution, paid-advertising, compliance, authority, evidence, limitation, and review practices; lifecycle status remains gate-pass with Founder approval through v3.0 and no customer proof |
| `goals/GOAL-005-D06-dma-domain-authority-synthesis.md` | Controlled institutional DMA synthesis: customer-goal configuration, baseline/measure/evidence expectations, honest attribution, two-month strategic review, constraints, and professional posture |
| `goals/GOAL-005-D06-product-attestation.md` — CR-GOAL-005-INST-011-03 | Product attestation that D-06 is institutional synthesis rather than personal testimony; goal/baseline/measure/evidence/cadence configuration and truthful evidence classes |
| `architecture/reference/billing/billing-profiles/dma-billing-profile.md` | Founder-authorized DMA billing profile, segregated customer ad spend, spend ceiling, pass-through treatment, and skill activation constraints |
| `architecture/reference/billing/dma-bundle-definitions.md` | Approved bundle and trial meanings; live ad spend is separate customer-funded actual, while trial campaigns are simulated with zero real spend; open pricing choices are not incorporated as F4 policy |
| `architecture/reference/agents/gaps/digital-marketing-agent-domain-gaps.md` | Current outcome-evidence maturity: enquiry-to-booking attribution and normalized performance evidence are not operational or customer-proven; provider and campaign dependencies require truthful unavailable treatment |
| `goals/GOAL-005-f4-business-contribution.md` — CR-GOAL-005-INST-003-04 | Generic business distinction among plan, work, result, technical metric, evidence, forecast, and actual; domain validation remains separate |
| `architecture/reference/product/f4-relationship-workspace-release-contract.md` — CR-GOAL-005-INST-011-05 | Product Results composition, truthful states, mandatory customer actions, DMA selection, and prohibition on DMA-specific generic-workspace fields |
| `architecture/reference/components/relationship-workspace-solution-contract.md` — CR-GOAL-005-INST-005-05 | Conceptual `RelationshipOutcomeAdapterV1` contribution fields and BP ownership of public incorporation and attention ordering |
| `architecture/reference/data/relationship-workspace-data-contract.md` — CR-GOAL-005-INST-006-04 | Provenance, freshness, evidence-state, correction, binding, outcome-versus-technical-metric, and domain-adapter semantics |
| `architecture/reference/security/relationship-workspace-security-contract.md` — CR-GOAL-005-INST-007-05 | Relationship/goal binding, service and customer authority, sensitive evidence, unavailable-state, and fail-closed command constraints |

No external source, personal interview, new commercial policy, runtime observation, provider response, deployment evidence, or customer result is asserted by this record.

## 2. F4-Specific DMA Customer-Outcome Vocabulary

DMA uses the customer's professional vocabulary. The neutral term **customer visit outcome** resolves to the approved business-domain term, such as appointment, booking, reservation, session, consultation, meeting, viewing, order, enrolment, or another domain-approved equivalent. F4 must not label every business outcome as a lead, patient, appointment, or booking when that term is wrong for the selected customer's domain.

| DMA customer-outcome concept | F4 meaning | Not sufficient as the outcome |
|---|---|---|
| **Acquired qualified enquiry** | A new customer contact within the agreed campaign and review boundary that expresses relevant service intent, is not classified as spam, and satisfies the customer-confirmed qualification meaning for the selected business. The qualification basis and source must be visible. | Reach, impression, profile view, click, message delivery, unclassified contact, or raw enquiry count without the agreed qualification basis |
| **Confirmed customer visit outcome** | A customer visit outcome confirmed by an authoritative booking or business record, or explicitly identified as customer-confirmed when no integrated authoritative source exists. Cancellation, no-show, duplicate, test, and unconfirmed request meanings remain distinct. | Booking-page view, button click, availability check, form submission, chat handoff, proposed slot, or appointment creation attempt |
| **Enquiry-to-visit conversion** | The relationship between an eligible qualified-enquiry cohort and confirmed customer visit outcomes for the same declared period and qualification rules. Cohort, exclusions, and evidence completeness must remain visible. | DM response speed, WhatsApp handoff, CTA click rate, form completion, or work completion by itself |
| **Acquisition outcome** | The customer-approved acquisition goal assessed through qualified enquiries, confirmed customer visit outcomes, or another domain-approved acquired-customer event over a declared review period. | Content volume, campaign launch, channel availability, audience reach, engagement, or provider-reported conversion alone |
| **Spend efficiency** | Customer-funded, WBE-authoritative actual ad spend assessed against attributable qualified enquiries, confirmed customer visit outcomes, or attributable business value when that value is authoritatively available. It may be expressed in customer language such as cost per qualified enquiry, cost per confirmed booking, or evidenced return from ad spend. | Budget, wallet balance, forecast, provider cost, management fee, allowance use, click cost, or platform/runtime resource consumption substituted for customer outcome |
| **Retention or repeat outcome** | A domain-approved repeat visit, reactivation, retention, renewal, or customer-lifetime outcome supported by the selected customer's business records and consent boundaries. | Reminder sent, review request sent, lifecycle message delivered, or segmentation work completed |
| **Campaign outcome** | The declared customer business goal for an approved campaign, assessed through one or more approved measures, evidence, review period, and attribution limits. | Campaign status, creative approval, publication, content-calendar adherence, or provider delivery health |

**Business outcome, work completion, and technical/ad-platform metric remain separate.** A campaign can be launched, content can be published, messages can be delivered, and systems can operate correctly while qualified enquiries, bookings, or spend efficiency remain unchanged, unavailable, or attribution unknown. Conversely, an observed business change is not attributed to DMA merely because DMA work completed during the same period.

Technical and ad-platform measures such as latency, retries, provider success, delivery state, reach, impressions, plays, saves, clicks, click-through rate, queue state, model use, token use, and API consumption may support diagnosis or explain evidence limits. They never occupy the business-outcome field and never establish customer value by themselves.

## 3. Baseline And Measure Semantics

### 3.1 Baseline

A DMA outcome baseline is the customer-confirmed or authoritatively observed starting meaning against which the declared customer goal will be reviewed. It names:

- the outcome definition and customer-domain vocabulary;
- the observation period and any seasonality or material business context;
- the source, source status, completeness, and confirmation basis;
- included and excluded channels, campaigns, locations, services, customer cohorts, and event states;
- the applicable qualification, deduplication, cancellation, no-show, and attribution rules; and
- the time from which a plan or material strategy change is assessed.

Historical data may supply a baseline only when its meaning is compatible with the current measure and its validity is known. A new customer, disconnected source, changed qualification rule, changed booking process, material campaign change, or incompatible historical period may require a new baseline or a bounded observation period.

Missing historical evidence is **Baseline needed**, not zero. A customer estimate remains **customer-stated baseline** until confirmed by an authoritative source. A benchmark may provide context but is not the customer's baseline. A target is not a baseline, and this record sets no numeric target or threshold for any customer.

### 3.2 Measure

Every selected measure must define its customer-language label, counted event, unit, period, cohort, inclusions, exclusions, source, evidence status, attribution rule, validity, and accountable owner. The customer goal supplies the target or decision threshold through separately governed configuration; this record supplies no default number.

The minimum supported measure families are:

1. **Qualified-enquiry acquisition:** distinct qualified enquiries under the agreed qualification and deduplication meaning.
2. **Confirmed customer visit outcomes:** distinct authoritative confirmed appointments, bookings, reservations, sessions, consultations, meetings, viewings, orders, enrolments, or the selected domain equivalent.
3. **Enquiry-to-visit conversion:** confirmed customer visit outcomes assessed against the eligible qualified-enquiry cohort under one compatible period and rule set.
4. **Spend efficiency:** WBE-authoritative actual ad spend assessed against attributable qualified enquiries, confirmed customer visit outcomes, or attributable business value when that value is available and permitted.
5. **Retention and lifecycle:** repeat, reactivated, retained, renewed, or lifetime-value outcomes where approved customer records and consent support the measure.

Measures may be quantitative or a bounded qualitative assessment when the approved domain contract permits it. A qualitative assessment must still identify method, evidence, uncertainty, and limitation; it cannot disguise missing data as success.

## 4. Evidence Sources And Status

| Evidence source | Permitted outcome use | Required qualification or limit |
|---|---|---|
| Customer booking, scheduling, CRM, order, enrolment, or equivalent authoritative business record | Confirm customer visit outcomes, cancellations, no-shows, repeat outcomes, and eligible cohorts | Connection, source ownership, event meaning, consent, completeness, duplicates, and freshness must be known |
| `booking-mcp` or approved domain-equivalent projection | Confirm customer visit outcomes and source attribution when supplied by the authoritative system | Creation attempt is not confirmation; source attribution may be absent; provider integration is not currently customer-proven |
| GA4 multi-channel funnel and source/medium evidence with disciplined campaign tags | Support first-touch, last-touch, and journey correlation | Requires compatible tagging, connected analytics, consent, event configuration, and no material path outside observation |
| Approved platform analytics for Instagram, Facebook, Google Business Profile, WhatsApp, email, Search Console, and advertising | Support channel touchpoints, enquiries, calls, clicks, campaign observations, and diagnostic measures | Platform-reported events are not automatically qualified enquiries, bookings, revenue, or causal attribution |
| WBE commercial projection | Supply authoritative actual ad spend, commercial validity, and correction state for spend-efficiency assessment | Budget, wallet, allowance, forecast, management fee, and provider/platform cost remain distinct from actual customer ad spend |
| Customer-confirmed record or statement | Supply a provisional baseline, offline outcome, correction, or missing-source context | Label as customer-confirmed or customer-stated; do not present as independently observed or provider-confirmed |
| Public business and competitor evidence | Supply market, seasonality, or constraint context | Does not prove this customer's acquisition, conversion, booking, revenue, or spend outcome |
| CE-confirmed constitutional evidence | Prove a proposal, approval, authority decision, action, limitation disclosure, or evidence transition occurred | Does not by itself prove the intended customer business outcome occurred |
| PR work and provider receipts | Prove execution facts and support reconciliation | Work or transport completion is not a customer outcome and cannot manufacture attribution |

Every evidence reference retains `PENDING`, `RECORDED`, `UNAVAILABLE`, `DISPUTED`, or `SUPERSEDED` meaning as applicable. A pending recording attempt, local state, provider transport response, customer command receipt, or correlation identifier is not recorded evidence. Correction adds source-owned lineage and does not erase prior evidence.

The current institutional evidence status must remain explicit: DMA v3.1 has Activation Gate evidence, Founder approval is recorded through v3.0, and there is no recorded customer activation or customer-proof evidence. Enquiry-to-booking attribution, provider execution, and normalized cross-channel outcome evidence are specified but not operationally proven. F4 therefore presents the contract and truthful unavailable states; it must not present repository examples, simulation values, or specification targets as observed customer outcomes.

## 5. Attribution Basis, Limits, And Uncertainty

### 5.1 Attribution Basis

An outcome contribution may use only a disclosed basis supported by the available evidence:

- **direct source attribution:** the authoritative visit or business record supplies a compatible campaign or source reference;
- **tagged journey attribution:** approved campaign tags and connected analytics link an observed touchpoint path to the confirmed outcome;
- **first-touch or last-touch attribution:** the report explicitly states which rule is being used and does not present it as the whole causal journey;
- **multi-touch correlation:** the report identifies the observed sequence and method without converting correlation into sole-cause certainty; or
- **customer-confirmed attribution:** the customer confirms the source or influence, and the result is labelled accordingly rather than independently observed.

Spend efficiency uses the same eligible outcome and attribution basis as the underlying result and only WBE-authoritative actual ad spend for the matching scope and period. Organic and paid contributions, management fee, subscription charge, allowance, forecast, and customer ad spend remain distinct.

### 5.2 Attribution Limits

The result must identify material limits, including where applicable:

- missing, inconsistent, or removed campaign tags;
- disconnected analytics, channel, booking, CRM, or WBE evidence;
- offline calls, walk-ins, referrals, repeat customers, or cross-device journeys not reliably linked;
- platform self-reporting, modelled conversions, duplicate events, spam, cancellations, no-shows, or changed qualification rules;
- customer actions, seasonality, price, availability, reputation, service quality, competitor activity, economic conditions, or other influences outside DMA control;
- incomplete review periods, delayed conversions, small or changing cohorts, stale source data, or incompatible source versions; and
- consent, minimisation, sector, platform, or professional restrictions that prevent collection or use.

Attribution does not equal causation. The strongest supported statement may be that DMA **contributed to**, **was associated with**, or **cannot currently be linked to** an outcome. Absolute or exclusive causation is not claimed unless an approved evidence method can establish it.

### 5.3 Truthful Uncertainty And Unavailable States

Use **Attribution unknown** when the institution cannot establish a supported link between DMA work and the observed outcome. Do not replace it with organic, no impact, zero, unchanged, failure, or success.

Use **Outcome unavailable** when the authoritative business outcome source or compatible owner contract is absent, unsupported, denied, or unreachable. Use **Evidence pending** while authoritative recording or reconciliation remains incomplete. Use **Stale** when evidence has exceeded declared validity or predates a material change. Use **Disputed** when an authorized party challenges the evidence, measure, or attribution. Use **Baseline needed** when no fit baseline exists. Use **Review period open** when the declared period has not completed and no approved interim assessment applies.

Unavailable attribution blocks an attributable-success claim, not honest display of separately authoritative work, spend, or observed business facts. A result can therefore state that work completed, actual spend is known, confirmed bookings are known, and DMA attribution remains unknown.

## 6. Review Cadence And Freshness

- **Operational outcome digest:** monthly, using the DMA-approved narrative of what happened, what was learned, what was tried, what changes next, and at most one customer decision request. It distinguishes incomplete, partial, and unavailable evidence.
- **Strategic performance review:** every two months, meaning six reviews per year, as attested in D-06. It assesses the customer goal against baseline and current measure, achievements, misses, uncertainty, learning, and one prioritized recommendation.
- **Material exception review:** when an approved material candidate in Section 7 arises. A material exception may require attention before the next scheduled review but does not change the strategic cadence or silently reset the baseline.
- **Customer-requested review:** permitted when the customer challenges evidence, attribution, baseline, goal, constraint, or material change.

Each contribution declares source production time, observation period, last authoritative confirmation, declared validity, source version, and correction lineage. Information is current only for the purpose and period declared by its owner. A browser refresh does not make evidence fresh. A historical fact can remain true while being stale for current attribution, assurance, forecast, or success assessment.

Where an approved source supplies no validity window, the contribution says validity is **not declared** and does not infer indefinite freshness. Material changes to campaign objective, audience, channel connection, booking process, qualification rule, budget, offer, operating capacity, compliance status, or evidence method require review of baseline and measure compatibility before comparison continues.

## 7. Material DMA Attention Candidates

DMA and owner sources may contribute a candidate; BP alone determines public qualification and authoritative order. No candidate carries an adapter-local rank or changes the generic **Needs your attention** contract.

| Candidate | Material customer consequence | Permitted customer action |
|---|---|---|
| Baseline missing, incompatible, disputed, or materially changed | Outcome cannot be judged honestly against the current goal | **Confirm baseline**, correct evidence, or review a proposed new observation period |
| Attribution unknown or materially incomplete for a reported acquisition, conversion, or spend result | The customer cannot safely treat the result as DMA-caused or use it for a consequential budget/goal decision | **Review evidence**, **Challenge attribution**, acknowledge the limitation, or defer the decision |
| Outcome evidence unavailable, stale, partial, or under reconciliation | Success, failure, or current state cannot be confirmed | Reconnect or provide an approved source, review the known facts, or await reconciliation |
| Declared acquisition, conversion, retention, or campaign outcome is materially at risk or missed at its approved review point | Current work may not deliver the customer goal and continued activity may waste time or money | Review the diagnosis and options, change the goal or plan through governed commands, change pacing, pause affected work, or take no action with the known consequence |
| Paid advertising has a completed miss review while customer-funded spend continues | Financial exposure continues without evidenced return | Review spend and attribution, change pacing, pause affected work, or review a separately governed plan change |
| WBE reports an approaching or reached ad-spend boundary, exhausted funding, changed forecast, or unknown commercial outcome | Campaign activity may pause, degrade, or remain commercially unresolved according to owner-approved policy | Review usage/forecast, change pacing, pause affected work, or use only an owner-approved funding action; no purchase or increase is invented here |
| Campaign, channel, booking source, analytics source, or provider dependency is suspended, disconnected, unsupported, or unavailable | Work or outcome evidence cannot proceed as represented | Reconnect, supply approved evidence, choose an available bounded alternative, or pause affected work |
| Campaign approval, budget choice, audience change, tracking consent, booking/enquiry data collection, or another customer-controlled dependency is required | Work is blocked or its lawful/evidenced outcome boundary would change | Approve or reject the exact subject, confirm the distinct boundary where required, provide information, or decline |
| Domain, sector, consent, platform, or advertising constraint blocks or materially changes the campaign | Publishing or targeting may be unlawful, misleading, unsafe, or outside authority | Review the constraint, correct the claim or evidence, narrow scope, reject the work, or seek the appropriate professional review |
| A material negative review, complaint, safety concern, or prohibited claim requires business-owner response | Reputation, customer safety, or compliance may be harmed by delay or autonomous response | Review evidence and take or approve the owner-required response; DMA does not improvise regulated advice |

Informational delivery, content volume, ordinary engagement changes, routine provider telemetry, or technical alerts do not qualify unless an accountable owner translates them into a material customer consequence and valid action.

## 8. Campaign And Business Constraints

Every F4 DMA result is interpreted within the constraints that governed the relevant work:

- customer-approved goal, measure, review period, campaign brief, audience, budget, authority, and Decision Space;
- applicable domain vocabulary and domain compliance rules, including prohibited claims and consent requirements;
- channel and provider connection, supported capability, account standing, and data availability;
- customer operating capacity, service availability, booking process, location, seasonality, offer, and other confirmed business context;
- explicit approval before campaign launch, material budget change, new audience, retargeting, tracking installation, or governed data collection where required;
- customer-funded ad-spend segregation, WBE-authoritative actuals, approved financial ceiling, and no spend beyond authority;
- no guaranteed marketing, acquisition, booking, revenue, or return outcome; and
- no paid-advertising result during a demonstration where the approved trial uses a simulated campaign and zero real spend.

A constraint explains the conditions under which an outcome was pursued or could be measured. It does not excuse fabricated success, convert work into value, or authorize a workaround. A missing required connection, consent, approval, authority, evidence source, or commercial policy produces blocked or unavailable treatment.

## 9. Conceptual RelationshipOutcomeAdapter Mapping

This mapping demonstrates compatibility with the approved conceptual `RelationshipOutcomeAdapterV1`. It does not define an endpoint, transport, payload, wire schema, persistence schema, generated type, or implementation.

| Conceptual adapter field | DMA contribution |
|---|---|
| Adapter version | Supported DMA adapter contract major/minor supplied by the later owning adapter record; this Product record selects no concrete version |
| Accountable domain owner | DMA professional/domain owner governed for F4 by Yogesh Khandge; provenance states this is institutional synthesis, not Yogesh testimony |
| Tenant, relationship, and goal/review binding | One authenticated tenant, one selected Employment Relationship, and one declared DMA goal or review context; no cross-relationship outcome |
| Domain outcome identity and customer label | One approved concept from Section 2 expressed in the selected customer's DVE vocabulary |
| Baseline definition and version | Section 3.1 meaning, source, period, rule set, evidence status, and correction lineage; `Baseline needed` when absent |
| Measure definition and version | Section 3.2 event, unit, cohort, period, inclusions/exclusions, source, attribution rule, and accountable owner |
| Review period and observation time | Monthly operational or two-month strategic period, plus the actual observation window and any material exception context |
| Observed assessment | Authoritative observed value or approved bounded qualitative assessment; unavailable when evidence does not support one |
| Evidence references and states | Section 4 sources with pending, recorded, unavailable, disputed, or superseded meaning and BP-mediated references only |
| Attribution basis and limits | Section 5 disclosed direct, tagged, first/last-touch, multi-touch, or customer-confirmed basis plus material limitations |
| Uncertainty, excluded influences, and missing inputs | Section 5.2 limits and Section 5.3 truthful states; no guessed zero, success, failure, or causation |
| Outcome state and material change | Baseline needed, measuring/review period open, improving, unchanged, declining, achieved, not achieved, attribution unknown, disputed, stale, or unavailable only when supported by the later owner contract |
| Optional attention candidate | One Section 7 candidate with reason, consequence, valid customer action, validity, and source-relative identity; no public rank or order |
| Production, confirmation, validity, and source version | Section 6 freshness package, including undeclared validity and correction lineage |

BP validates adapter ownership, relationship/goal binding, supported version, evidence-reference form, completeness, provenance, and freshness. BP alone decides public Result incorporation, customer-visible state, available commands, attention qualification, and authoritative order. DMA cannot grant authority, approve work, change lifecycle, calculate WBE truth, record constitutional evidence, or expose a browser endpoint through this contribution.

## 10. G-F4-09 Product Evidence Map

| G-F4-09 Product evidence requirement | Evidence in this record |
|---|---|
| Named DMA authority and provenance | Section 1 names Yogesh, defers Sujay, and distinguishes institutional synthesis from testimony or personal approval |
| F4 customer-outcome vocabulary | Section 2 defines acquisition, qualified enquiry, confirmed visit, conversion, spend efficiency, retention, and campaign outcomes in domain-aware language |
| Baselines and measures | Section 3 defines baseline fitness, missing-baseline treatment, measure families, periods, cohorts, and no default numeric target |
| Evidence sources and status | Section 4 defines source roles, evidence-state meanings, and the current no-customer-proof boundary |
| Attribution limits and uncertainty | Section 5 defines permitted bases, causal limits, excluded influences, and truthful unknown/unavailable treatment |
| Review cadence and freshness | Section 6 defines monthly operational digest, two-month strategic review, material/customer-requested review, validity, and stale treatment |
| Material attention candidates and actions | Section 7 defines bounded candidates, consequences, and customer actions without rank or browser priority |
| Campaign and business constraints | Section 8 defines approval, authority, budget, domain, consent, provider, evidence, and trial constraints |
| Generic adapter compatibility input | Section 9 maps DMA meanings to conceptual `RelationshipOutcomeAdapterV1` fields without defining architecture or schema |
| Generic workspace neutrality | Sections 2 and 9 keep DMA vocabulary and rules in the domain contribution; no DMA field is added to the generic Relationship Workspace |

**Product contribution decision:** CR-GOAL-005-INST-011-06 supplies the authorized INST-011 evidence contribution to G-F4-09. It does not close G-F4-09 by itself. Under Amendment 3 Order 4, the separately accepted INST-003 context must next validate these meanings as customer business outcomes, and only after that publication may the separately accepted INST-005 context validate conceptual adapter conformance. Independent G-F4-11 review remains later and separate.

## 11. Explicit Exclusions

This record does not:

- claim direct Yogesh testimony, personal authorship, personal review, personal content approval, or new Founder testimony;
- create any Sujay contribution, review, approval, availability, or dependency;
- invent a numeric target, benchmark, attribution window, conversion promise, commercial policy, price, fee, allowance, budget consequence, or customer segment;
- modify the generic Relationship Workspace or add a DMA-specific field, command, rule, rank, or schema to it;
- define implementation, component placement, endpoint, path, API, OpenAPI, wire schema, database schema, migration, generated client, provider activation, source, test, build, deployment, or runtime behavior;
- represent a specification, simulation, provider metric, repository test, Activation Gate, work completion, or technical health as a live customer outcome;
- authorize campaign execution, spending, provider access, implementation, deployment, F5-F8, self-review, merge, or release; or
- resolve F4-POL-01 through F4-POL-06 or any other Founder-routed commercial, rights, lifecycle, assurance, export, or unavailable-state policy.

G-F4-12 implementation and G-F4-13 deployment remain blocked and require their own later constitutional authorization.