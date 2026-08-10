# WC-034 F4 Relationship Workspace Security Contract

## Attestation

| Field | Value |
|---|---|
| Institution | INST-007 — Security Architect |
| Goal | GOAL-005 |
| Work Contract | WC-034 F4 |
| Contribution ID | CR-GOAL-005-INST-007-04 |
| Date | 2026-08-10 |
| Status | COMPLETE |
| Contribution boundary | F4 authorization and assurance controls only; no product policy, endpoint path, wire schema, data schema, implementation, provider activation, deployment, or F5-F8 decision |

## 1. Decision Summary

The Relationship Workspace is a Business Platform (BP) public projection for one authenticated actor and one authorized Employment Relationship at a time. The browser authenticates to BP only. BP authorizes every read and command from authoritative tenant membership, relationship membership, role, lifecycle, scope, authority, and current-version state; possession of an identifier, cursor, link, acknowledgement, assurance proof, or idempotency key grants no authority.

The WAOOAW Billing Engine (WBE), Professional Runtime (PR), Constitutional Engine (CE), professional/domain adapters, Constitutional Audit Ledger, Customer Evidence Ledger, and billing ledgers are private boundaries. Browser access to any of them is denied by network policy, service authentication, and application authorization. BP mediates every permitted projection and command. CE remains the constitutional validation and evidence authority, WBE remains the commercial-truth authority, PR remains an internal execution-truth supplier, and domain adapters remain internal semantic suppliers.

This contract closes the security architecture contribution for `G-F4-05`. It defines minimum controls and fail-closed conditions. Where the business contribution or an owning institution has not selected materiality, role entitlement, stronger-factor, recipient, redaction, retention, or commercial policy, this contract routes the decision and does not create a default.

## 2. Security Invariants

1. Tenant authority comes only from a valid Keycloak-brokered server session under ADR-003 and ADR-008. A tenant identifier from a URL, body, header other than the authenticated server context, browser store, cursor, or internal payload is never authority.
2. Relationship access is resolved authoritatively on every request. Relationship membership, role entitlement, lifecycle, scope, and authority are not inferred from tenant membership, a JWT role alone, conversation history, a prior projection, or possession of an opaque identifier.
3. Every consequential command is bound to the authenticated actor subject, tenant, Employment Relationship, effective role, command family, subject, purpose, expected authoritative versions, assurance event, acknowledgement event when required, and idempotency intent.
4. Authorization is evaluated before existence, state, step-up, conflict, or validation detail is disclosed. An inaccessible tenant, relationship, item, export, acknowledgement, or command is indistinguishable from a non-existent one to the caller.
5. A command denied for assurance, acknowledgement, role, version, lifecycle, scope, authority, or service-identity failure performs no governed mutation and creates no customer-visible success. Required denial evidence is recorded without exposing protected facts.
6. Evidence First applies before BP presents governed success. Pending, accepted-for-processing, transport success, or internal service success is not recorded constitutional success.
7. Emergency Stop is outside ordinary C1-C5 step-up. It remains directly reachable and is never delayed by acknowledgement, assurance freshness, rate limiting, export controls, commercial state, lifecycle state, or an unavailable F4 projection.
8. Browser state is presentation state only. It never becomes relationship truth, authority, assurance, acknowledgement, ordering, evidence, billing truth, or a durable governance record.

## 3. Consequence-Class Assurance Controls

F4 reuses the approved Identity Boundary assurance vocabulary. `AAL2_ACCOUNT` is the minimum routine authenticated account assurance. `AAL3_FRESH` is the approved fresh portal assurance and includes every server-required factor. Token refresh alone does not satisfy freshness. The current Identity Boundary definition of `AAL3_FRESH` controls unless an authorized owner approves a different requirement for a named F4 command.

The server evaluates assurance at command receipt and again immediately before commit when an orchestration or delay could cross the approved freshness window. Assurance is invalidated for the command when the actor, tenant, relationship, role, command, subject, purpose, safe return target, or required factor differs; when authentication is revoked; or when a bound authoritative version changes materially.

| Class | Minimum authorization and assurance control | Typed acknowledgement control | Fail-closed conditions |
|---|---|---|---|
| **C1 — Reversible operational control** | Pause requires a current authenticated relationship role licensed to pause and must remain directly exercisable. Resume requires at least current `AAL2_ACCOUNT`; `AAL3_FRESH` is required when prior assurance is stale or when scope, authority, budget, risk, lifecycle, professional identity, scheduled consequence, or another owner-declared material condition changed while paused. | Not required unless the approved owner classifies a named resume consequence as material. | Deny resume when the prior and current consequence cannot be compared, a required owner projection is stale or unavailable, or the actor no longer holds the effective role. Pause and Emergency Stop are not withheld because resume assurance is unavailable. |
| **C2 — Governed decision** | The actor must hold the current decision-owner role for the exact subject and relationship. `AAL3_FRESH` is mandatory before approval enables an external, financial, legal, safety, irreversible, or owner-classified material effect. Other C2 decisions require at least current `AAL2_ACCOUNT`. | Required for owner-classified material approval. Required for rejection only when the approved owner determines that rejection causes irreversible loss, cancellation, or a material deadline consequence. | Deny on expired subject, changed consequence, changed dependency, changed decision owner, stale projection, or unresolved materiality. No ordinary approval grants scope or authority. |
| **C3 — Scope-boundary decision** | `AAL3_FRESH` is always required from the licensed boundary owner for the exact named boundary, exclusions, relationship, affected parties, duration, and downstream action. | Always required as a distinct scope-boundary acknowledgement. An approval acknowledgement cannot be reused. | Deny when boundary, exclusions, duration, scope version, authority version, lifecycle version, or consequence changed after assurance or acknowledgement. Unresolved boundary ownership is a denial, not an implied owner. |
| **C4 — Evidence custody action** | Relationship-scoped inspection requires at least current `AAL2_ACCOUNT` and an evidence-readable role. `AAL3_FRESH` is required for export to another party, sensitive export, materially incomplete export, or any stricter owner-approved sensitivity class. | Required for export to another party, sensitive export, or materially incomplete export. Routine authorized inspection does not require it. | Deny when sensitivity, completeness, period, recipient, purpose, redaction policy, evidence authorization, relationship binding, or export authority is unknown, stale, or unsupported. |
| **C5 — Authority change** | `AAL3_FRESH` is always required from the current licensed authority owner for grant, expansion, narrowing, suspension, revocation, expiry change, or restoration. Authority state is re-read immediately before commit. | Required for grant, expansion, restoration, and every owner-classified materially consequential narrowing or revocation. | Deny on changed authority owner, scope, duration, ceiling, stop condition, affected work, lifecycle consequence, or authority version. Capability, trust, prior approval, or relationship ownership never substitutes for licensed authority. |

The table fixes security floors, not product composition. A stronger assurance requirement may be selected through the authorized policy path. A weaker requirement may not be selected where this table requires `AAL3_FRESH` or a typed acknowledgement.

## 4. Typed Acknowledgement Enforcement

A typed acknowledgement is a server-issued, single-use challenge for one consequence. It is not a checkbox, generic confirmation button, copied approval, reusable consent, client-authored statement, or acceptance hidden in terms.

Before accepting it, BP must verify that:

- the actor types the exact server-presented confirmation phrase or equivalent approved accessible challenge for the displayed consequence;
- the challenge is bound to actor subject, tenant, relationship, effective role, command family, command subject, purpose, consequence class, consequence-policy identifier and version, and the authoritative versions named in Section 6;
- the displayed subject, boundary or authority, exclusions, duration, recipient, sensitivity, financial or lifecycle effect, and reversibility facts match the facts being committed;
- the challenge is unexpired, unused, issued after the latest material version, and paired with the assurance level required for that command;
- accessibility support changes only the input method, not the explicitness or semantic content of the acknowledgement; and
- CE records the correct distinct constitutional event before success, including a distinct scope-boundary event for C3.

The browser may preserve only non-secret draft intent during step-up. It must not preserve the typed phrase, assurance proof, recipient proof, export locator, or completed acknowledgement. After step-up, BP reauthorizes and revalidates the bound command; successful authentication alone does not execute it.

## 5. Authorization And Privacy-Safe Failure

### 5.1 Authorization order

BP evaluates F4 requests in this order:

1. validate the Keycloak issuer, signature, audience, expiry, actor subject, and authenticated tenant context;
2. resolve current tenant membership and the selected Employment Relationship without trusting caller-supplied ownership;
3. resolve the actor's effective relationship role and licensed command entitlement;
4. validate lifecycle, scope, authority, item ownership, and current versions;
5. determine consequence class, assurance, acknowledgement, and owning-service requirements;
6. invoke only the authorized internal service for the bound purpose; and
7. require authoritative outcome and CE evidence before presenting governed success.

Authentication establishes an actor; tenant membership establishes no relationship command by itself; relationship membership establishes no decision-owner or authority-owner entitlement by itself; capability establishes no authority.

### 5.2 Anti-enumeration

- Unauthenticated failure is generic and reveals no tenant, relationship, account, role, item, evidence, export, or service fact.
- After authentication, non-existence and lack of tenant, relationship, role, item, evidence, or export access use the same public status family, stable privacy-safe code family, response shape, headers, and timing envelope. INST-005 owns the concrete public error contract.
- Step-up, version conflict, lifecycle conflict, export sensitivity, and acknowledgement detail are returned only after resource authorization. They must not become existence or role oracles.
- Lists, counts, pagination, cursors, stable attention order, search, masked values, export size, filenames, and timing reveal only resources already authorized for the selected relationship.
- Correlation support uses an opaque public correlation identifier. Stack traces, internal service names, ledger keys, policy internals, factor details, tenant identifiers, other relationship identifiers, recipient identity, and redaction rationale are not exposed in public errors.
- Authorization denials and suspicious enumeration attempts emit security telemetry containing minimum pseudonymous routing context, never protected payload content.

## 6. Tenant, Relationship, Role, And Version Binding

Every F4 read, cursor, continuation, draft handoff, acknowledgement, assurance intent, export, download grant, and command is scoped to one tenant and one Employment Relationship. Every consequential command additionally binds:

- authenticated actor subject and authentication session;
- effective relationship role and the authoritative role-assignment version;
- exact command family, subject identity, purpose, and consequence class;
- relationship, plan or work subject, scope, authority, lifecycle, assurance-policy, and consequence-policy versions that affect authorization;
- WBE projection version for a commercial consequence, evidence projection version for an evidence consequence, and domain contribution version for a domain consequence, when applicable;
- expected authoritative version used for conflict detection; and
- request hash plus idempotency key.

A cursor, acknowledgement, intent, or export grant presented under another tenant, relationship, actor, role, purpose, or version is denied without revealing which binding failed. Relationship switching invalidates in-memory drafts, links, cursors, attention state, selected actions, assurance intents, acknowledgement challenges, export grants, and optimistic state from the prior relationship. A separately authorized complete projection is required.

## 7. Approval, Boundary, Authority, And Lifecycle Controls

Ordinary approval and scope-boundary confirmation are separate command and evidence families. Approval authorizes only the named next step for the current subject and versions. It cannot add included work, affected parties, relationship reach, authority reach, duration, ceiling, or a new lifecycle entitlement. Any such change is C3, C5, or both and requires its own assurance, acknowledgement, validation, and evidence.

Authority and lifecycle commands must:

- verify the actor is the current licensed owner of that exact change, not merely an `OWNER`-labelled tenant member;
- show and bind the effective time, affected work, scheduled-work effect, scope, authority, financial/allowance consequence supplied by WBE, evidence consequence, stop condition, and re-entry or termination consequence supplied by approved owners;
- fail closed when any required owner projection is unknown, stale, conflicting, unavailable, or changes before commit;
- never derive a completed lifecycle or authority state from transport acceptance, local optimism, PR state, or WBE state alone; and
- preserve Emergency Stop and evidence access according to constitutional rights even when ordinary activity is paused, suspended, terminated, commercially constrained, or under reconciliation.

Unknown product policy for renewal, termination, billing, evidence retention, authority materiality, or re-entry is represented as blocked and routed under Section 13. Security architecture does not select the commercial or customer-rights outcome.

## 8. Evidence Inspection And Export Protection

BP Evidence Reader is the only public evidence mediator. The browser never receives a CE, ledger, object-store, or database credential and never constructs a ledger query.

Before inspection or export, BP authorizes the actor, tenant, relationship, role, evidence subject, period, purpose, completeness, sensitivity, and permitted operation. Export adds these controls:

1. classify every included item under the approved data classification and compute the highest resulting sensitivity;
2. resolve the intended recipient and purpose from an approved recipient policy; self, another relationship participant, steward, regulator, support actor, and external third party are not interchangeable;
3. prove recipient authorization before generation and again before retrieval; possession of a link is insufficient;
4. apply the owner-approved redaction and field-minimisation policy before release, while preserving an export manifest that states period, sources, completeness, omissions, redactions, supersession status, and authoritative or partial meaning;
5. require C4 assurance and acknowledgement according to Section 3, after sensitivity, recipient, completeness, and limitations are known;
6. issue only a short-lived, audience-bound, actor-bound, tenant-bound, relationship-bound, single-purpose retrieval grant; no bearer public URL or durable share link;
7. encrypt export material in transit and at rest, isolate it from public caches and shared temporary storage, and expire generated material under the approved retention policy; and
8. record request, authorization, generation, retrieval, expiry, denial, and redaction evidence without placing export content in constitutional or operational telemetry.

If sensitivity, recipient eligibility, redaction, legal basis, completeness, or retention policy is missing, export is unavailable. The platform does not infer consent, downgrade sensitivity, silently omit protected material, or produce an unlabelled partial export.

## 9. Browser, Cache, Service Worker, Telemetry, And URL Controls

Authenticated F4 projections, commands, evidence, exports, assurance responses, and errors use non-cacheable private response policy. Shared caches and CDN storage are prohibited. The web application must not persist F4 payloads, relationship truth, typed acknowledgements, assurance proofs, evidence content, export grants, or recipient details in `localStorage`, `sessionStorage`, IndexedDB, the Cache API, or other durable browser storage.

The service worker may cache only approved static assets. It must bypass F4 navigation, authenticated HTML/RSC payloads, API reads, command responses, evidence, exports, step-up, acknowledgements, errors, and redirects. Offline presentation may show an honest unavailable state or a non-sensitive shell; it may not replay cached relationship truth as current, queue a consequential F4 command, or claim that a command succeeded.

On sign-out, account switch, tenant switch, relationship switch, role loss, session expiry, or authorization failure, protected in-memory state and back/forward-restorable content are cleared or made unusable before the next context renders. Browser history must not restore actionable prior-relationship state.

URLs, referrers, page titles, analytics events, and client logs must not contain tenant identifiers, evidence content or ledger keys, typed phrases, assurance or acknowledgement tokens, idempotency keys, recipient identity, export locators, commercial details, goals, results, or work content. Any route identifier authorized by the Solution contract must be opaque and remains non-authoritative. Referrer policy must prevent protected path disclosure to third parties.

Telemetry records operation class, outcome class, latency, approved pseudonymous correlation, service identity, policy version, and security signal only. It excludes JWTs, cookies, personal data, relationship content, evidence content, goals, result values, forecasts, budget values, typed acknowledgements, assurance proofs, recipient data, export content, and raw tenant or relationship identifiers. Security analytics cannot become a shadow relationship or evidence store.

## 10. Confused-Deputy And Service Authentication Controls

Every internal F4 call authenticates both the calling workload and the delegated customer purpose. Network location alone is insufficient.

| Route | Required service control | Delegation and authorization control |
|---|---|---|
| Web/browser to BP | Keycloak-brokered customer session; same-origin server boundary where approved | BP derives tenant and actor from the server session and resolves relationship/role authority; browser-supplied tenant or role is ignored |
| BP to WBE | Mutually authenticated workload identity under ADR-007/ADR-014-equivalent service policy; WBE accepts the approved BP identity only for F4 customer projection/command purposes | Delegation is bound to actor, tenant, relationship, purpose, commercial subject, expected WBE version, and least-privilege operation; WBE reauthorizes the relationship-commercial binding and returns no unrelated tenant data |
| BP to CE | Approved authenticated gRPC boundary; CE independently validates caller identity and delegated actor/tenant context | CE validates the exact constitutional action, relationship, scope/authority versions, consequence class, and evidence type; BP cannot request a broader event than the customer command |
| BP to PR | Mutually authenticated BP and PR workload identities; PR exposes only the approved internal execution projection/control contract with no public route | Delegated customer purpose binds actor, tenant, relationship, professional, work item, execution/control subject, expected source version, and least-privilege operation; PR independently authorizes the BP caller, audience, relationship binding, purpose, version, and requested operation and returns no unrelated execution data |
| BP to professional/domain adapter | Mutually authenticated BP and allowlisted adapter workload identities for a registered professional/domain and supported contract version; the adapter contract has no public route | Delegated customer purpose binds actor, tenant, relationship, goal/review context, accountable domain owner, validation/projection subject, evidence references, expected source version, and least-privilege operation; the adapter independently authorizes the BP caller, audience, relationship/goal binding, purpose, version, and requested operation and returns no unrelated relationship data |

BP must not forward a customer bearer token as sufficient service authorization to WBE, PR, or a domain adapter. Internal recipients verify the calling service identity, intended audience, permitted operation, and delegated context independently. A compromised or over-privileged service is denied when it requests another tenant, relationship, role, purpose, version, or operation.

Separately approved event delivery from PR or a professional/domain adapter to BP may coexist under its own authenticated, authorized, versioned contract, but it is not the F4 execution projection/control or domain projection/validation contract and does not reverse the BP-initiated directions above.

## 11. Replay, Idempotency, And Concurrency Protection

Every F4 mutation and export request uses a client-generated idempotency key interpreted only inside the authenticated actor, tenant, relationship, command family, command subject, purpose, and request-hash binding. Reusing a key with a different binding or payload is a conflict and executes nothing. Replaying the same binding returns the same authoritative terminal or unresolved outcome without repeating the effect.

Acknowledgement challenges, assurance intents, recipient proofs, and retrieval grants are single-use and purpose-bound. Their replay after completion returns the already-authoritative outcome or a privacy-safe denial; it never creates another decision, authority change, lifecycle transition, export, or evidence event.

Commands carry expected authoritative versions. BP and each owning service reject stale versions before mutation. Multi-owner operations use an orchestrated idempotent outcome with durable reconciliation ownership. A timeout or lost response remains unresolved until authoritative reconciliation; retry does not assume failure and transport acceptance does not assume success.

Rate limiting and abuse controls apply per authenticated actor and tenant without creating cross-tenant timing or capacity oracles. They never apply to Emergency Stop and must not turn repeated denial into authorization.

## 12. Adversarial Acceptance And Traceability

| Security acceptance | Required adversarial proof | F4 mapping |
|---|---|---|
| **SEC-F4-01 — Cross-tenant isolation** | Tenant A substitutes Tenant B relationship, item, cursor, version, acknowledgement, assurance intent, idempotency key, evidence reference, export, or retrieval grant across every read and command family. All attempts produce privacy-indistinguishable denial, zero protected fields/counts/timing distinctions, zero mutation, zero export, and no success evidence. | `G-F4-05`, UX-CONV-07, CCT-UX-RIGHTS-01, CCT-UX-EF-01 |
| **SEC-F4-02 — Cross-relationship isolation** | Two relationships in one tenant are exercised by an actor authorized for only one or for different roles in each. Substitution and relationship switching carry over zero drafts, links, attention state, authority, budget, evidence, acknowledgement, assurance, export, cursor, or idempotency outcome. | `G-F4-05`, UX-CONV-07, UX-CONV-08 |
| **SEC-F4-03 — Role and consequence enforcement** | Viewer, routine manager, decision owner, boundary owner, and authority owner attempts cover C1-C5; stale JWT roles and changed authoritative assignments are included. Only the currently licensed role succeeds, and required `AAL3_FRESH` and typed acknowledgement cannot be bypassed or reused. | `G-F4-05`, CCT-UX-BOUNDARY-01, CCT-UX-RIGHTS-01 |
| **SEC-F4-04 — Approval/boundary separation** | An approval token, acknowledgement, endpoint intent, or idempotency result is replayed against a scope-boundary or authority command and vice versa. Every mismatch is denied; CE records the distinct event type only after valid completion. | CCT-UX-BOUNDARY-01, CCT-UX-EF-01 |
| **SEC-F4-05 — Version and replay resistance** | Scope, authority, lifecycle, role, plan/work subject, WBE consequence, evidence completeness, recipient, or policy changes between display, step-up, acknowledgement, and commit. Stale commands fail closed; same-key retries never duplicate effects; uncertain outcomes reconcile without fabricated success. | UX-CONV-06, CCT-UX-EF-01, UX-SHELL-06 |
| **SEC-F4-06 — Private-boundary denial** | Browser-originated requests target PR, WBE, CE, domain adapters, Constitutional Audit Ledger, Customer Evidence Ledger, billing ledgers, internal DNS names, and guessed public routes. Network and application controls deny all paths; no CORS, redirect, generated client, error, or credential exposes a private surface. | `G-F4-05`, UX-SHELL-06 |
| **SEC-F4-07 — Confused-deputy resistance** | Authenticated WBE, PR, and domain-adapter callers alter delegated tenant, relationship, actor, purpose, audience, subject, or version, and attempt operations outside their registered role. The recipient independently denies each attempt with no cross-context data or mutation. | `G-F4-05`, UX-CONV-07, CCT-UX-EF-01 |
| **SEC-F4-08 — Export containment** | Recipient, sensitivity, period, completeness, redaction, relationship, actor, retrieval grant, and expiry are tampered with or replayed. Unauthorized generation/retrieval is denied; caches, URLs, telemetry, and service workers contain no export material or grant. | `G-F4-05`, CCT-UX-RIGHTS-01, UX-SHELL-06 |
| **SEC-F4-09 — Browser privacy** | Refresh, offline mode, back/forward navigation, service-worker update, sign-out, account/tenant/relationship switch, analytics capture, and error reporting are inspected. No protected payload is served from cache, restored into another context, placed in a URL/referrer, or emitted to telemetry. | `G-F4-05`, UX-CONV-07, UX-SHELL-06 |
| **SEC-F4-10 — Stop independence** | Step-up, acknowledgement, rate limit, stale projection, WBE/PR/domain outage, export generation, and blocked lifecycle states are active while Emergency Stop is exercised. Stop remains reachable and no F4 control adds delay or denial. | CCT-UX-RIGHTS-01 |

The integrated F4 acceptance package must also preserve UX-CONV-06 structured owner/state/effect/action semantics, exact BP ordering for UX-CONV-08, and honest unavailable behavior for UX-SHELL-06. Security tests do not authorize implementation or claim customer proof.

## 13. Routed Owner Decisions And Dependencies

| Routed owner | Decision required | Security treatment until approved |
|---|---|---|
| INST-002 — Constitutional Analyst | Validate whether any named F4 action requires acknowledgement beyond the C1-C5 minimum and whether any constitutional floor requires stronger assurance. | Apply this contract's minimum; block the disputed named action rather than weaken or invent policy. |
| INST-005 — Solution Architect | Define concrete public/internal operations, privacy-safe error contracts, delegation envelopes, version fields, idempotency behavior, and generated-client exclusion of private surfaces. | No private route, improvised operation, or implementation inference. |
| INST-006 — Data Architect | Define authoritative version, freshness, correction/supersession, sensitivity, recipient, completeness, redaction, retention, and export-manifest semantics. | Unknown or unsupported semantics make the affected consequence or export unavailable. |
| INST-011 — Product Owner | Select mandatory first-release commands, owner-declared C2 materiality, C1 material resume cases, customer acknowledgement presentation, omission behavior, and policy questions requiring Founder choice. | Do not display an unowned action or choose a materiality default. |
| BP owner | Accept authoritative relationship/role authorization, acknowledgement, orchestration, evidence-reader, anti-enumeration, and security-telemetry responsibilities. | F4 public command/read remains blocked without the owner-approved contract. |
| WBE owner | Define authorized BP caller role, delegated commercial purpose, commercial version/freshness, command reconciliation, and privacy-minimised projection. | Usage/budget command or consequence remains unavailable; BP does not recompute it. |
| Professional/domain owners | Define adapter service identity, relationship/goal authorization, evidence-reference permissions, supported version, and domain sensitivity. | Results contribution remains unavailable; BP does not infer domain meaning. |
| Registrant/Founder through INST-013 | Resolve choices that change customer rights, authority ownership, commercial/lifecycle consequences, acceptable recipients, retention, release composition, or implementation/deployment authority. | Explicitly blocked; no downstream default or architecture contribution substitutes for authorization. |

## 14. Gate Statement

`G-F4-05 — Security assurance` is **SATISFIED** by `CR-GOAL-005-INST-007-04` for architecture integration: C1-C5 assurance floors, typed acknowledgement, tenant/relationship/role/version authorization, anti-enumeration, evidence export, browser privacy, replay/idempotency, confused-deputy, service authentication, direct-access denial, and adversarial acceptance are explicit.

This does not close `G-F4-03`, `G-F4-04`, `G-F4-06` through `G-F4-13`, or any owner-routed policy question. It does not authorize endpoints, schemas, generated clients, implementation, autonomous execution, provider activation, deployment, F5-F8 work, or self-review. Missing owner decisions remain blocked or unavailable exactly as identified above.

## 15. Basis

- `goals/GOAL-005-f4-business-contribution.md` — CR-GOAL-005-INST-003-03
- `architecture/reference/components/relationship-workspace.md` — CR-GOAL-005-INST-004-07
- `architecture/reference/components/identity-boundary.md` — approved assurance vocabulary and step-up mechanism
- `architecture/reference/security/security-architecture.md` and `architecture/reference/security/threat-model.md`
- ADR-003, ADR-007, ADR-008, and ADR-014
- AD-001 through AD-004 and AD-008 through AD-010
- Constitution Articles IX and X