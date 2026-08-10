# GOAL-005 F4 Relationship Workspace — Business Contribution

## Attestation

| Field | Value |
|---|---|
| Institution | INST-003 — Business Architect |
| Goal | GOAL-005 |
| Contribution ID | CR-GOAL-005-INST-003-03 |
| Date | 2026-08-10 |
| Contribution status | COMPLETE |
| Contribution boundary | Business semantics for WC-034 F4 Relationship Workspace; no architecture, interface, schema, implementation, provider activation, or deployment decision |

## Customer Outcome And Release Boundary

F4 gives a customer one truthful relationship workspace for understanding what their employed professional plans to do, what needs a customer decision, what work is under way, what business results are evidenced, how allowances and budget are expected to change, and which rights and controls remain available. The customer can act in business language without interpreting models, tokens, queues, traces, provider telemetry, or other technical abstractions.

F4 begins from an existing authenticated employment relationship and the completed conversation foundation. It does not create a relationship, perform provider work, or claim cross-channel continuity. Its release boundary is the governed customer understanding and control of one selected relationship at a time.

The workspace must preserve five business distinctions:

1. Capability is what the professional can do; it is not authority to act.
2. A proposal or plan is not completed work.
3. Completed work is not automatically a business outcome.
4. A forecast is not actual usage, spend, or result.
5. Recorded evidence supports a claim but does not manufacture success.

## Business Vocabulary

| Customer label | Business meaning | Required distinction |
|---|---|---|
| **Plan** | The current agreed or proposed path from customer goals to intended work, including owner, state, expected effect, timing, dependencies, authority needs, and review point. | A plan describes intended work. Proposed plan content is not approved authority or completed work. |
| **Priority Work** | The subset of work whose business importance, timing, dependency, risk, or customer consequence makes it prominent within the relationship. | Priority is authoritative relationship information, not a browser inference from visual activity or technical telemetry. |
| **Needs your attention** | An authoritative ordered list of items for which a customer decision, acknowledgement, information, boundary confirmation, funding choice, or other customer action is required or materially time-sensitive. | Attention means a customer response is needed or a material consequence must be understood. It does not mean the professional or browser merely considers an item interesting. |
| **Work** | Proposed, approved, scheduled, active, paused, blocked, completed, cancelled, or failed professional activity attributable to the selected relationship and its declared goals. | Work state describes activity, not customer value. Every item names its owner, state, effect, available action, and evidence status. |
| **Results** | Evidence-backed changes assessed against declared business outcomes, baselines, measures, review periods, and attribution limits. | Results prioritize customer outcomes such as appointments, enquiries, revenue, cost, quality, or risk reduction. Technical/runtime metrics may support diagnosis but are not presented as business success. |
| **Usage & budget** | Customer-understandable actual allowance consumption, remaining allowance, agreed financial ceiling, forecast range, forecast assumptions, review period, and consequences of approaching or crossing a boundary. | Allowance is not currency, forecast is not actual use, and neither tokens nor provider cost substitutes for customer vocabulary. |
| **Rights & control** | Reachable statements of customer rights, current scope and authority, lifecycle controls, approval and boundary obligations, evidence access, and unconditional Emergency Stop. | Capability, trust, authority, lifecycle, and evidence remain independently understandable. Rights remain visible before and after consequential decisions. |

### Customer Outcomes Versus Technical Metrics

Customer-visible business outcomes answer whether the hired professional improved the customer's declared goal within an agreed period and with stated evidence and attribution limits. Examples include appointment growth, qualified enquiries, booking rate, revenue improvement, cost per acquired customer, crop loss prevented, price premium, or risk-managed return.

Technical/runtime metrics answer whether an enabling system operated, for example request latency, message delivery, execution duration, model use, provider success rate, retry count, queue depth, or token consumption. They may explain reliability, uncertainty, or a blocked result, but they must not be relabelled as customer value. A healthy runtime with no evidenced business improvement is not a successful business outcome; a business outcome whose attribution is unknown must remain unknown.

## Authoritative Needs-Your-Attention Ordering

The ordered list is supplied by the authoritative relationship owner. The browser displays that order exactly and must not calculate, improve, personalize, or silently re-rank it.

An item qualifies only when the authoritative relationship state says at least one of the following is true:

- the customer must approve, reject, confirm a scope boundary, acknowledge a typed consequence, or provide a required decision;
- work is blocked on customer information, authority, funding, scheduling, or another customer-controlled dependency;
- a material deadline, review point, expiry, allowance threshold, budget boundary, rights impact, or lifecycle consequence requires customer awareness or action;
- a result, forecast, or failure contains material uncertainty or changed assumptions that the customer must review;
- the customer must respond to a safety, compliance, evidence, or authority exception.

Informational updates with no required or materially time-sensitive customer response do not qualify. Technical alerts qualify only after an accountable business owner has translated them into a customer consequence and required action.

For ties, the authoritative order remains stable across refreshes: items with equal authoritative priority retain their server-provided relative sequence until the relationship owner changes that sequence or the items cease to qualify. The browser must not add a secondary sort by timestamp, label, state, perceived urgency, local activity, or any other derived signal.

Browser-derived ranking is prohibited because it would create unlicensed prioritization, could vary between devices or sessions, obscure the accountable owner, and present an unevidenced recommendation as authoritative relationship judgment.

## Owner, State, Effect, And Action Semantics

Every consequential relationship item must answer four customer questions: **Who is accountable? What is true now? What changes or could change? What may I do next?** Where no action is available, the item must say so and explain the business reason.

| Concept | Owner | State semantics | Effect semantics | Customer action semantics |
|---|---|---|---|---|
| Plan | Customer outcome owner for acceptance; professional for preparation and maintenance | Proposed, agreed, active, needs review, superseded, completed, cancelled | Intended work, dependencies, expected outcome, timing, authority and budget assumptions | Review, agree, request change, confirm boundary, pause, or cancel when entitled |
| Goal | Customer-designated business outcome owner | Draft, active, at risk, achieved, not achieved, replaced, retired | Defines the outcome, baseline, measure, review period, and attribution boundary against which work is judged | Define, confirm, amend, replace, or retire within contract boundaries |
| Work | Named professional or delegated accountable role | Proposed, approved, scheduled, active, paused, blocked, completed, cancelled, failed, outcome unknown | States what activity occurred or is intended and its expected or observed consequence | Approve, reject, pause, resume, provide input, review evidence, or take no action as explicitly stated |
| Deliverable | Professional for production; customer or named reviewer for acceptance where required | Planned, in preparation, ready for review, accepted, rejected, revised, withdrawn | Identifies the usable output, intended purpose, limitations, and downstream consequence | Review, accept, reject with reason, request revision, export evidence, or confirm a boundary |
| Approval | Customer or other explicitly licensed decision owner | Required, pending, approved, rejected, expired, withdrawn | Grants or denies the stated next step only; approval does not silently expand scope or authority | Approve or reject after seeing subject, scope, consequence, expiry, and evidence |
| Schedule | Owner accountable for the scheduled commitment | Proposed, confirmed, due, delayed, missed, completed, cancelled | Shows when work or review is expected and the consequence of change or delay | Confirm, reschedule, pause, cancel, or acknowledge a material change where permitted |
| Business outcome | Customer-designated outcome owner; professional accountable for evidence and honest attribution | Baseline needed, measuring, improving, unchanged, declining, achieved, not achieved, attribution unknown | States customer value against the agreed baseline, period, measure, evidence, and limitations | Confirm baseline, inspect evidence, challenge attribution, amend the goal, or agree next action |
| Allowance | Customer for use choices within agreed terms; accountable commercial owner for definition | Available, approaching threshold, exhausted, renewed, adjusted, unavailable, unknown | Explains what customer-understandable quantity remains and what work changes at a boundary | Continue, reduce activity, change pacing, purchase an approved addition, or accept disclosed degradation |
| Forecast | Named professional or commercial owner accountable for assumptions | Current, changed, stale, withdrawn, actual now available | Expresses a range, period, assumptions, uncertainty, and likely budget or allowance consequence; never an actual charge | Review assumptions, change pacing or scope, approve a separately governed choice, or await actuals |
| Budget | Customer or licensed budget owner | Proposed, agreed, available, approaching ceiling, ceiling reached, suspended, changed | Defines the financial limit and consequence of approaching or reaching it; never grants broader work authority | Set or lower a ceiling, request an increase through governed change, pause affected work, or review actuals |
| Rights | Customer; WAOOAW remains accountable for faithful disclosure | Available, exercised, temporarily constrained with reason, restored; never silently absent | Explains protections, review, evidence access, pause/termination consequences, and Emergency Stop | Exercise the right, inspect its consequence, obtain evidence, or escalate a failure to honor it |
| Scope | Customer for granted boundary; professional accountable for staying within it | Proposed, confirmed, active, change proposed, exceeded, expired, withdrawn | Defines included and excluded work, affected relationship, duration, and consequence of change | Confirm the boundary distinctly from approval, reject change, narrow scope, or initiate governed amendment |
| Authority | Customer or other constitutionally licensed authority owner | Not granted, proposed, granted, constrained, suspended, expired, revoked | Defines which decisions or actions may occur, for which scope, duration, ceiling, and stop condition | Grant, constrain, suspend, revoke, or decline authority through a governed acknowledgement |
| Lifecycle | Customer relationship owner under agreed employment terms | Evaluation, Active, Suspended, Terminated | Determines whether professional activity may occur and states billing, schedule, evidence, and re-entry consequences | Activate where entitled, pause, resume, renew, or terminate after seeing the typed consequence |
| Evidence | Accountable producer of the underlying statement or action; institution preserves the record | Pending, recorded, unavailable, incomplete, disputed, superseded by later evidence | Supports what was proposed, decided, done, or observed; does not erase earlier evidence or guarantee an outcome | Inspect, export, dispute, request clarification, or acknowledge an evidence limitation |

Unknown is not a substitute for any named state. If the authoritative state is unavailable or conflicting, the workspace says **unknown**, withholds consequential success claims, and identifies the next accountable recovery or review action.

## Consequence Classes

| Class | Applies to | Required business disclosure | Fresh assurance or typed acknowledgement |
|---|---|---|---|
| C1 — Reversible operational control | Pause; resume with unchanged, current scope, authority, budget, and assurance | Affected relationship/work, immediate effect, scheduled-work effect, billing or allowance effect, and what remains preserved | Pause must remain directly exercisable. Resume needs fresh assurance when prior assurance is stale or scope, authority, budget, risk, or material conditions changed while paused. |
| C2 — Governed decision | Approval or rejection of a plan, work item, deliverable, schedule, or proposal | Exact subject, owner, current state, approved or rejected effect, downstream dependency, expiry, reversibility, and evidence consequence | Fresh assurance is required before an approval enables consequential external, financial, legal, safety, or irreversible effect. Typed acknowledgement is required when the owner-defined consequence class says the decision is material; rejection requires it when rejection causes an irreversible loss, cancellation, or material deadline consequence. |
| C3 — Scope-boundary decision | Confirmation or rejection of included/excluded work, relationship reach, authority reach, duration, or affected parties | Boundary being confirmed, exclusions, affected relationship, duration, downstream action, and distinction from ordinary approval | Always requires a distinct typed acknowledgement and current assurance. A normal approval cannot stand in for scope-boundary confirmation. |
| C4 — Evidence custody action | Evidence inspection and export | Evidence subject, period, completeness, sensitivity, intended recipient or use, redaction/limitation, and whether the export is authoritative or partial | Routine inspection does not require typed acknowledgement. Export to another party, export of sensitive material, or export with material incompleteness requires fresh assurance and typed acknowledgement of scope and consequence. |
| C5 — Authority change | Grant, expansion, narrowing, suspension, revocation, expiry, or restoration of authority | Exact authority, scope, owner, duration, financial ceiling, affected work, stop condition, effective time, and lifecycle consequence | Always requires fresh assurance. Grant, expansion, restoration, or any materially consequential narrowing/revocation requires a typed acknowledgement by the licensed authority owner. |

These classes identify the business assurance obligation only. The owning assurance, security, constitutional, and solution institutions must define the valid mechanism without weakening the stated customer meaning.

## Truthful System Meanings

| Condition | Business meaning | Required treatment |
|---|---|---|
| Empty | The authoritative relationship has no qualifying item for this view, or no item exists yet. | Name which meaning applies. Do not imply work, success, or failure. Offer only valid next actions. |
| Loading | The current authoritative relationship state has not yet been obtained. | Preserve context, identify that status is pending, and do not show prior or placeholder content as current. |
| Error | The authoritative state could not be obtained or a requested action did not receive authoritative confirmation. | State that success is unconfirmed, preserve the customer's intent where safe, provide correlation or recovery support, and do not fabricate completion. |
| Unknown | The institution cannot currently determine the authoritative business state, effect, owner, or attribution. | Label the unknown field, explain the customer consequence, withhold consequential action where required, and route recovery to the accountable owner. |
| Stale | Previously authoritative information is older than its declared validity or known to precede a material change. | Show when it was current, identify what may have changed, do not use it for fresh assurance, ordering, approval, forecast, or success, and request authoritative refresh. |

No optimistic display, local browser state, cached content, technical success signal, pending evidence, or unconfirmed request may be presented as completed work, recorded evidence, accepted decision, available authority, actual spend, or achieved business outcome.

## Minimum F4 Release Composition

The minimum F4 release contains, for one selected relationship at a time:

- a relationship context that identifies the professional, lifecycle state, current goal, and whether information is current;
- **Plan**, including proposed/agreed status, owners, intended effects, dependencies, timing, and review actions;
- authoritative **Needs your attention** in server-provided stable order, with reason, consequence, due meaning, and customer action;
- **Work**, with owner, business state, expected or observed effect, available action, and evidence status;
- **Results**, separating work outputs from evidence-backed business outcomes and naming baselines, periods, measures, attribution limits, and unknowns;
- **Usage & budget**, separating actual allowance use, remaining allowance, financial ceiling, forecasts, assumptions, thresholds, and consequences in customer language;
- **Rights & control**, including scope, authority, lifecycle actions, evidence access/export, approval and boundary distinctions, and reachable Emergency Stop;
- honest empty, loading, error, unknown, and stale meanings across every included view.

The minimum release explicitly defers:

- F5 omnichannel continuity, cross-channel notifications, and continuity claims;
- F6 voice interaction, transcription, attachments, and their consent or retention choices;
- F7 Founder administration;
- provider connection or activation and consequential provider work;
- deployment to any environment;
- browser-derived priority ranking, personalization, or local reordering;
- multi-relationship aggregation that merges authority, budget, evidence, drafts, or item links;
- any F8 closure claim beyond the focused F4 acceptance evidence.

## Measurable Success And Acceptance Mapping

| Acceptance ID | F4 business acceptance | Measurable proof |
|---|---|---|
| UX-CONV-06 | Structured Plan, Work, Deliverable, and Decision items expose owner, state, effect, evidence status, and valid customer actions. | Every sampled consequential item answers all four customer questions; keyboard-operable action availability matches the authoritative state; zero item types use technical status as business effect. |
| UX-CONV-07 | Changing the selected professional changes the complete relationship context without crossing drafts, links, authority, budget, evidence, or work. | In every switch scenario, 100% of displayed and actionable items belong to the selected relationship; zero cross-relationship carry-over is observed. |
| UX-CONV-08 | Needs your attention displays only qualifying authoritative items in the exact supplied order with stable ties. | Repeated refresh and device checks preserve the supplied sequence; zero browser-calculated ranks, secondary sorts, or pre-contract fabricated destinations exist. |
| CCT-UX-BOUNDARY-01 | Scope-boundary confirmation names the boundary and consequence and remains distinct from normal approval. | Every boundary scenario requires a separate typed acknowledgement; zero ordinary approvals silently confirm or expand scope. |
| CCT-UX-RIGHTS-01 | Rights, current scope and authority, lifecycle state, evidence access, and Emergency Stop are reachable in customer language. | All named rights/control meanings are reachable for each included lifecycle state; zero technical vocabulary is required to understand or exercise them. |
| CCT-UX-EF-01 | Pending evidence precedes recorded evidence, and recorded status appears only after authoritative confirmation. | Every tested evidence transition shows pending before recorded; zero pending, failed, unknown, stale, or merely technical-success states display recorded success. |
| UX-SHELL-06 | An absent capability contract means unavailable or blocked, never privately improvised or presented as successful. | Every absent/deferred F4 dependency produces an honest unavailable or blocked meaning; zero fabricated success paths or unowned capability claims appear. |

F4 succeeds when a customer can correctly answer, without technical assistance: what is planned, what needs me now and why, what work is actually happening, what result is evidenced, what allowance or budget consequence is approaching, what authority exists, what rights I can exercise, and what remains unknown. Acceptance requires zero fabricated success, zero browser-derived ordering, and zero cross-relationship leakage in the evaluated scenarios.

## Routed Owner Questions And Dependencies

These are unresolved owner decisions or dependencies. This contribution does not invent their answers.

| Routed to | Question or dependency | Why F4 needs it |
|---|---|---|
| INST-002 — Constitutional Analyst | Which F4 decisions require typed acknowledgement beyond the minimum classes named here, and what current assurance conditions satisfy each class? | Business semantics identify consequence; constitutional assurance must validate the obligation. |
| INST-004 — Enterprise Architect | Which authoritative domain owns the complete ordered Needs-your-attention projection, stable tie sequence, relationship context, and freshness meaning without shifting judgment to the browser? | F4 requires one accountable source of ordering and state. |
| INST-005 — Solution Architect | How do the approved owners expose the required business meanings and blocked/unavailable states while preserving one selected relationship and no browser-created authority? | Component and interaction placement are outside INST-003 Decision Space. |
| INST-006 — Data Architect | What canonical meanings and provenance distinguish actuals, forecasts, allowances, budgets, business outcomes, technical metrics, pending evidence, recorded evidence, unknown, and stale? | F4 must not collapse semantically different facts. |
| INST-007 — Security Architect | What fresh-assurance thresholds and evidence-export protections apply by consequence class, sensitivity, recipient, authority change, and lifecycle state? | F4 names where assurance is required but does not choose its mechanism. |
| INST-011 — Product Owner | Which F4 item types and customer actions are mandatory for the first release, what customer-language labels resolve remaining ambiguity, and which consequence disclosures require Founder policy? | Product composition and unresolved policy prioritization remain Product Owner decisions. |
| Business Platform owner | Supply authoritative plan, goal, work, deliverable, approval, schedule, lifecycle, scope, authority, rights, evidence, and ordered-attention business contracts. | F4 cannot derive relationship truth or priority in the browser. |
| Billing owner | Supply customer-language allowance actuals, remaining allowance, budgets, thresholds, forecasts, assumptions, validity, and consequence semantics. | F4 cannot infer consumption, financial state, or forecasts from technical usage. |
| Professional/domain owner | Define domain-specific business outcomes, baselines, measures, evidence sources, attribution limits, material attention reasons, and review cadence. | Generic F4 semantics cannot manufacture domain success criteria. |
| Registrant / Founder through INST-013 | Resolve any owner-routed policy choice that changes customer rights, commercial consequences, authority, release composition, or implementation authorization. | Architecture contribution authority does not authorize policy invention or implementation. |

Until these owner contracts and decisions are approved, affected F4 capabilities remain explicitly blocked or unavailable. Their absence must not be compensated for by browser logic, technical metrics, inferred authority, or invented defaults.

## Basis

This contribution derives from the approved GOAL-005 customer outcome and AE-03 relationship-workplace stories, WC-034 F4 scope and acceptance identifiers, the INST-003 D-01 employment capability vocabulary, Founder Vision business-outcome primacy, and ratified claims including C-001 through C-004, C-007, C-009 through C-011, C-023, C-028 through C-030, C-034, C-036 through C-044, C-048, C-049, C-051, C-056, C-063, C-083 through C-085, C-088 through C-091, and C-099.