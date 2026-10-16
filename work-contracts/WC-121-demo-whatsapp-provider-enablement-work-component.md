# WC-121 Demo WhatsApp Provider Enablement Work Component

## 0. Record Control

| Field | Value |
|---|---|
| Work component | WC121-C09 - Demo WhatsApp Provider Enablement |
| Version | 0.1.0-candidate.3 |
| Status | EXECUTION PLAN - S16 REOPENED - SELECTIVE VALIDATION ACTIVATED - PROTECTED ACTIONS UNAUTHORIZED |
| Parent Work Contract | `work-contracts/WC-121-customer-engagement-workspace-implementation.md` |
| Controlling component | WC-121 Section 6.9, CEW-WC-09 - Live Demo Provider and Deployment |
| Upstream transport Work Contract | `work-contracts/WC-120-conversation-engine-whatsapp-implementation.md` |
| Solution input | `architecture/reference/components/customer-engagement-workspace-solution-contract.md` |
| WhatsApp solution input | `architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md` |
| Environment input | `infrastructure/conversation-whatsapp/demo.json` |
| Environment schema | `infrastructure/conversation-whatsapp/environment.schema.json` |
| Implementation office | Platform IT Expert |
| Source baseline | `origin/main` at `6166da3fb516c78143207ac6d4bc9af7c1652c2c` |
| Result | S16 BLOCKED; S01-S15 PLANNED OR BLOCKED |

This work component decomposes already accepted WC-120 and WC-121 boundaries into executable
Platform IT stories. It makes no new architecture decision and does not authorize source changes,
provider access, credential use, Azure or DNS mutation, deployment, external traffic, activation,
PR approval, or merge.

If an implementation choice would add a deployable, ingress class, store, queue, public facade,
identity owner, provider trust model, or cross-environment path not already accepted by the
controlling inputs, work stops for an amended architecture decision.

## 1. Objective

Prepare and, only after each independent authority is recorded, enable the Demo WhatsApp provider
boundary so that the exact WC-121 qualified image can:

1. receive Meta callback challenges and signed events through the accepted environment-isolated
   adapter;
2. send approved template and service-window messages through least-privilege outbound authority;
3. preserve one canonical relationship, conversation, command, and evidence history across Portal
   and WhatsApp;
4. keep provider delivery distinct from processing, owner, evidence, commercial, and outcome truth;
5. resolve every protected value at runtime from Demo-only Azure Key Vault references; and
6. begin and remain `READY_INACTIVE` unless separately activated for a bounded recipient, window,
   spend limit, release/configuration digest, and rollback tuple.

## 2. Fixed Inputs And Non-Negotiable Configuration

The following names come from the controlling WC-120 Demo manifest and are not renamed by this
component:

| Purpose | Canonical Demo value or reference |
|---|---|
| Repository-safe telephone label | `DEMO_SUFFIX_3575` |
| Callback host reference | `whatsapp-demo.<approved-domain>` |
| Provider binding | `kv://kv-waooaw-demo/secrets/whatsapp-provider-binding` |
| Webhook verification token | `kv://kv-waooaw-demo/secrets/whatsapp-verify-token` |
| Meta App Secret | `kv://kv-waooaw-demo/secrets/whatsapp-app-secret` |
| Outbound provider authority | `kv://kv-waooaw-demo/secrets/whatsapp-outbound-authority` |
| Media retrieval authority | `kv://kv-waooaw-demo/secrets/whatsapp-media-authority` |
| Namespace | `conversation-whatsapp-demo` |
| Configuration version | `wc120-candidate-1` |
| Feature-flag version | `wc120-default-off-1` |
| Initial callback acceptance | `false` |
| Initial dispatch | `false` |
| Initial restore routing | `false` |
| Initial provider egress | `false` |
| Activation authority | `SEPARATE_FOUNDER_AUTHORITY_REQUIRED` |

Complete E.164 telephone values, Meta App Secret, access tokens, OTPs, provider payloads, consent
payloads, and customer content are prohibited from the repository, image, Terraform state, plans,
workflow inputs or outputs, logs, traces, screenshots, evidence, and PR text.

## 3. Independent Entry Gates

No story may treat one gate as satisfying another.

| Gate | Required evidence |
|---|---|
| Package acceptance | Founder acceptance of the exact WC-120/WC-121 source versions and digests |
| Implementation | Explicit current-session implementation authorization |
| Provider account | Authority to inspect or mutate the named Demo Meta app and WABA |
| Credential use | Authority to create, read, rotate, revoke, or use each named credential |
| Cloud mutation | Authority for the exact Demo subscription, resource group, Key Vault, identities, ingress, and DNS scope |
| Deployment | Authority to deploy the exact qualified image and configuration tuple |
| Authentication and authorization integrity | WC-123 provider-neutral session, current-membership authorization, and direct plus route-intercepted Login/Register browser journeys pass on the exact Web candidate |
| External traffic | Bounded sender, recipient allowlist, scenario, start, expiry, and spend |
| Activation | Separate authority bound to exact release/configuration/catalog digests |
| Approval and merge | Founder review, approval, and merge |

WC121-C09 remains blocked until WC-121 Section 2.3 is satisfied, including same-sender/recipient
feasibility or a distinct Founder-authorized Demo recipient.

## 4. Story Dependency Chain

| Story | Outcome | Depends on |
|---|---|---|
| WC121-C09-S01 | Freeze accepted baseline and authority ledger | None |
| WC121-C09-S02 | Inventory and verify isolated Meta Demo assets | S01 |
| WC121-C09-S03 | Freeze provider-binding and protected-reference schemas | S01-S02 |
| WC121-C09-S04 | Extend closed-world Demo configuration and secret catalog | S03 |
| WC121-C09-S05 | Provision secrets through a no-echo path | S04 |
| WC121-C09-S06 | Bind least-privilege OIDC and managed identities | S04 |
| WC121-C09-S07 | Map and package the accepted adapter workload | S03-S06 |
| WC121-C09-S08 | Provision stable Demo callback ingress, DNS, and TLS | S07 |
| WC121-C09-S09 | Configure and verify Meta callback subscription | S05, S08 |
| WC121-C09-S10 | Configure outbound authority, templates, and recipient allowlist | S02-S06 |
| WC121-C09-S11 | Bind immutable release and default-off capability state | S04, S07, S10 |
| WC121-C09-S12 | Deploy at zero traffic and qualify private readiness | S08, S11 |
| WC121-C09-S16 | Prove WC-123 authentication, authorization, and auth-presentation integrity | S01, S11-S12 |
| WC121-C09-S13 | Run bounded live inbound/outbound acceptance | S09-S12, S16 |
| WC121-C09-S14 | Activate with expiry or remain inactive | S13 |
| WC121-C09-S15 | Rehearse rollback, revoke authority, and complete Demo teardown | S13-S14 |

## 5. Detailed Stories

### WC121-C09-S01 - Baseline, Authority, And Impact Freeze

**Outcome:** Every later action is bound to accepted sources, exact digests, owners, paths, and
independent authority records.

**Implementation surfaces**

- WC-120 and WC-121 source records.
- Requirement ledgers and accepted specialist dispositions.
- Changed-path, owner, migration, generated-artifact, deployment, rollback, and recovery inventory.

**Tasks**

1. Record exact source blobs for WC-120, WC-121, both solution inputs, the channel-neutral API, the
   Demo WhatsApp manifest, its schema, and the exact image candidate.
2. Map `WC121-R011`, `WC121-R014`, `WC121-R016` through `WC121-R018`, `WC121-R020`, and
   `WC121-R021` to direct stories and evidence.
3. Identify the accepted existing workload that owns the adapter; prove the mapping adds no
   deployable, public facade, store, queue, release member, or cross-environment path.
4. Record every required provider, cloud, deployment, traffic, activation, rollback, incident,
   spend, data, recovery, and evidence owner.
5. Record all current blockers without converting an unknown or missing input into an assumption.

**Executable evidence**

- Docker-owned digest and path preflight.
- Closed-world changed-path scan.
- Requirement-to-story completeness check.
- Prohibited-topology-delta check.

**Definition of Done**

- Every source digest and owner is exact.
- Every protected action is independently represented.
- No implementation file or provider/cloud action occurs under this story.

**Stop**

- Missing acceptance, conflicting source, unapproved owner, unknown workload placement, or topology
  expansion.

### WC121-C09-S02 - Demo Meta Asset And Recipient Readiness

**Outcome:** A privacy-safe inventory proves that the Demo Meta Business, app, WABA, sender, and
recipient are isolated, owned, and eligible for the bounded scenario.

**Implementation surfaces**

- Meta Business and WhatsApp Manager under separately authorized operator access.
- Protected operator inventory; repository contains references and statuses only.

**Tasks**

1. Verify Meta Business ownership and business-verification status.
2. Create or identify the dedicated Demo Meta app and WABA under the accepted isolation model.
3. Verify the authorized telephone identity, display-name state, Phone Number ID, WABA ID, App ID,
   billing readiness, and supported Graph API version.
4. Resolve `DEMO_SUFFIX_3575` only inside protected configuration.
5. Close same-sender/recipient feasibility through binding Meta confirmation, an authorized bounded
   probe, or a distinct Founder-authorized Demo recipient.
6. Record only opaque references, suffix-safe labels, status, authority, and timestamps as evidence.

**Executable evidence**

- Environment-isolation inventory validation.
- Cross-environment ID/reference inequality check.
- Protected-value leakage scan.
- Recipient-boundary gate result.

**Definition of Done**

- Dedicated Demo ownership and isolation are proven.
- Sender and recipient feasibility is closed.
- No complete telephone identity or credential appears in evidence.

**Stop**

- Unverified ownership, shared unapproved app/WABA/number, unresolved recipient feasibility, missing
  billing boundary, or any protected-value disclosure.

### WC121-C09-S03 - Provider Binding And Protected Reference Contract

**Outcome:** Runtime consumers can validate a versioned Demo provider binding without interpreting
unstructured secrets or trusting provider payload identity.

**Implementation surfaces**

- Environment configuration schema and validator.
- Adapter configuration model.
- Redacted binding metadata and rotation contract.

**Tasks**

1. Define the implementation schema for the existing `whatsapp-provider-binding` reference using
   only fields required by the accepted design: environment, app reference, WABA reference,
   Phone Number ID reference, sender telephone reference, bounded recipient reference, supported
   API version, binding version, validity, and authority evidence reference.
2. Keep complete telephone identity and all provider credentials out of the schema instance exposed
   to repository tooling.
3. Reject missing, unknown, wrong-environment, expired, revoked, or superseded bindings.
4. Bind inbound account/phone identifiers and outbound sender selection to the same environment
   binding.
5. Version rotation and overlap without allowing rollback to revive revoked authority.

**Executable evidence**

- Schema positive and negative tests.
- Wrong-environment, unknown-key, expiry, revocation, and rollback non-resurrection tests.
- Seeded protected-value scan.

**Definition of Done**

- Consumers fail closed on every invalid binding.
- The binding grants no tenant, relationship, participant, command, or activation authority.

**Stop**

- The schema requires a new identity owner, authority model, provider trust decision, or repository
  storage of a protected value.

### WC121-C09-S04 - Closed-World Configuration And Secret Catalog

**Outcome:** The accepted Demo manifest and secret dependency catalog are the only deployment-time
sources for WhatsApp provider configuration.

**Implementation surfaces**

- `infrastructure/conversation-whatsapp/demo.json`.
- `infrastructure/conversation-whatsapp/environment.schema.json`.
- `infrastructure/environment-readiness/secret-catalog.json` and schema.
- Environment renderer and validation tests.

**Tasks**

1. Add catalog entries for the five canonical Demo Key Vault references without values.
2. Record purpose, source, consumers, environment, required condition, rotation class, validation,
   owner, principal, allowed operations, and compromise action for every entry.
3. Preserve distinct purposes for provider binding, verify token, App Secret, outbound authority,
   and media authority.
4. Bind manifest, catalog, configuration, feature-flag, policy, and release digests.
5. Reject unknown keys, wrong vault/environment, duplicate names, mutable references, missing
   consumers, or a complete telephone value.
6. Keep callback acceptance, dispatch, restore routing, and provider egress false.

**Executable evidence**

- Docker environment-manifest and secret-catalog schema validation.
- Digest-binding and wrong-environment negative tests.
- Repository, rendered-config, Terraform plan, workflow, and artifact secret scans.

**Definition of Done**

- Rendering is deterministic and contains references only.
- All activation flags remain false.
- UAT and Production manifests and bindings change by zero.

**Stop**

- Hand-written consumer mapping, value-bearing manifest, unbound digest, cross-environment
  reference, or secret-purpose reuse.

### WC121-C09-S05 - No-Echo Secret Provisioning And Rotation

**Outcome:** Each Demo WhatsApp secret is created or versioned in `kv-waooaw-demo` without entering
repository, state, plan, command arguments, logs, outputs, artifacts, or evidence.

**Implementation surfaces**

- Existing environment secret-provisioning path.
- Azure Key Vault metadata and versioning.
- Rotation and revocation runbook.

**Tasks**

1. Generate the webhook verify token with accepted entropy and length.
2. Ingest the Meta App Secret, provider binding, outbound authority, and media authority through an
   approved no-echo operator path.
3. Store each purpose as a distinct versioned Key Vault secret using canonical names.
4. Apply enabled, expiry, content-type/tag, owner, environment, and version metadata without
   exposing the value.
5. Define rotation overlap, immediate revocation, compromise response, and consumer restart/reload
   behavior.
6. Prove a revoked version cannot be selected by rollback or restore.

**Executable evidence**

- Key Vault metadata-only readiness record.
- No-value log/artifact scan.
- Version, expiry, disable, rotate, and revoked-version negative tests.

**Definition of Done**

- All references resolve for authorized consumers only.
- Evidence contains metadata and opaque version identifiers, never values.

**Stop**

- Secret value in CLI arguments, Terraform state, workflow output, evidence, or a shared
  cross-purpose credential.

### WC121-C09-S06 - OIDC, Managed Identity, And Least-Privilege RBAC

**Outcome:** GitHub deployment uses environment-bound OIDC, while runtime, media, configurator, and
verification duties use separate least-privilege identities.

**Implementation surfaces**

- Demo GitHub environment federation.
- Azure managed identities and Key Vault secret-level RBAC.
- Workload audience and caller allowlists.

**Tasks**

1. Use federated OIDC with no Azure client secret for the authorized Demo deployment identity.
2. Bind the federated subject to the exact repository, workflow/environment, and Demo scope.
3. Assign separate adapter runtime, media scanner, deployment/configurator, and independent
   verification identities.
4. Grant `get` only on exact secret resources required by each runtime consumer.
5. Prevent Keycloak, Web, BP, UAT, Production, and unrelated workloads from reading provider
   credentials.
6. Validate workload identity, audience, caller, operation, purpose, environment, and delegated
   customer context independently.

**Executable evidence**

- Azure plan and policy checks.
- Positive exact-principal secret access.
- Wrong principal, audience, operation, environment, and secret negatives.
- Proof that `meta-login-client-secret` is not a WhatsApp credential or consumer binding.

**Definition of Done**

- No long-lived Azure deployment credential exists.
- Cross-environment and cross-purpose access is denied.

**Stop**

- Broad vault access, shared runtime/deployment identity, wildcard federation, or reliance on
  network location as identity.

### WC121-C09-S07 - Accepted Adapter Workload Packaging

**Outcome:** The accepted WhatsApp adapter boundary is packaged inside the approved release topology
without adding an unauthorized service, public facade, or release-tuple member.

**Implementation surfaces**

- Existing adapter/Phone Identity implementation and nearest tests.
- Approved workload Terraform module and release manifest.
- Internal BP adapter contract.

**Tasks**

1. Reconcile the current `phone-identity-service` implementation with the accepted WC-120 logical
   adapter placement and WC-121 no-new-deployable rule.
2. Stop for architecture direction if the current exact-seven workload cannot host the accepted
   boundary without a new deployable.
3. Bind startup configuration to canonical references and fail closed on missing mandatory
   dependencies.
4. Preserve exact-raw-body callback verification before parsing or normalization.
5. Preserve independently authenticated adapter-to-BP calls with purpose and audience checks.
6. Add no direct provider-to-owner or client-to-provider business path.

**Executable evidence**

- Container build and startup tests.
- Topology/release-member comparison.
- Raw-body mutation, signature, wrong-audience, and dependency-unavailable tests.
- Image secret scan.

**Definition of Done**

- The exact accepted topology is unchanged.
- Liveness is process-local and readiness performs no provider effect.

**Stop**

- New deployable, ingress owner, public facade, shared workload credential, or health probe with an
  external effect.

### WC121-C09-S08 - Stable Demo Callback Ingress, DNS, And TLS

**Outcome:** Meta can reach one stable, environment-bound HTTPS callback route that terminates only
at the accepted adapter.

**Implementation surfaces**

- Approved Demo ingress, DNS, TLS, WAF/rate controls, and route policy.
- `whatsapp-demo.<approved-domain>` host reference.

**Tasks**

1. Resolve `<approved-domain>` only after exact DNS and cloud authority.
2. Provision the stable Demo hostname, certificate, ingress route, request-size limit, content-type
   allowlist, timeout, and abuse controls.
3. Route only the accepted GET challenge and POST callback methods/path to the adapter.
4. Preserve exact request bytes and the Meta signature header.
5. Reject wrong host, method, path, content type, encoding, and oversized body before owner work.
6. Keep callback acceptance false after infrastructure provisioning.

**Executable evidence**

- DNS/TLS and route-policy validation.
- Wrong-host/path/method/content tests.
- Raw-body preservation and maximum-body tests.
- Proof `cp.demo.waooaw.com` remains the Portal and is not silently reused as the callback edge.

**Definition of Done**

- Stable HTTPS ingress reaches the adapter at zero accepted callback traffic.
- No UAT/Production DNS or route changes occur.

**Stop**

- Raw IP, temporary URL, Portal catch-all routing, missing TLS, transformed body, unapproved DNS, or
  topology expansion.

### WC121-C09-S09 - Meta Callback Registration And Subscription

**Outcome:** Meta verifies the exact Demo callback and subscribes only the required event types.

**Implementation surfaces**

- Meta App Dashboard and WABA subscription under provider authority.
- GET challenge and POST callback configuration.

**Tasks**

1. Configure the final approved HTTPS callback URL.
2. Enter the exact `whatsapp-verify-token` value through the protected operator path.
3. Validate `hub.mode=subscribe`, constant-time token comparison, and exact challenge response.
4. Subscribe the WABA only to required message and status events.
5. Record provider API/schema version and subscription state.
6. Keep POST callback acceptance and business dispatch disabled after registration.

**Executable evidence**

- Valid and invalid challenge results.
- Wrong token, mode, host, and replay negatives.
- Redacted provider subscription receipt with opaque identifiers only.

**Definition of Done**

- Meta reports callback verification and required subscription success.
- Registration causes no accepted business command or outbound message.

**Stop**

- Challenge reflection, token disclosure, broad event subscription, wrong WABA/app, or callback
  traffic before separate authority.

### WC121-C09-S10 - Outbound Authority, Templates, And Recipient Allowlist

**Outcome:** Outbound messaging is limited to approved purposes, current consent/service-window
eligibility, approved templates, and the bounded Demo recipient set.

**Implementation surfaces**

- Meta system user and WABA assignments.
- Outbound provider client configuration.
- Template registry, consent policy, service-window policy, and recipient allowlist.

**Tasks**

1. Create or identify a Demo-only Meta system user and assign only required app/WABA assets.
2. Grant the minimum accepted messaging and management permissions.
3. Store the resulting credential as `whatsapp-outbound-authority`; do not use a temporary
   Getting Started token.
4. Register environment-specific templates and record category, locale, variables, version,
   purpose, opt-in basis, approval, and revocation.
5. Resolve the distinct authorized Demo recipient only from protected configuration.
6. Enforce recipient, purpose, consent, template, service-window, spend, rate, and expiry gates at
   queue and send time using trusted server time.
7. Keep dispatch and provider egress false.

**Executable evidence**

- Permission and asset-scope inspection.
- Template eligibility matrix.
- Wrong recipient, expired consent, closed window, revoked template, excess spend, and wrong
  environment negatives.
- Credential and telephone leakage scans.

**Definition of Done**

- Eligible outbound work can be formed but cannot leave WAOOAW while gates remain false.
- No unapproved recipient or template is selectable.

**Stop**

- Personal token, temporary token, broad business authority, unresolved recipient, missing consent,
  unapproved template, or unbounded spend.

### WC121-C09-S11 - Immutable Release And Capability-State Binding

**Outcome:** The WhatsApp capability state is bound to one qualified release/configuration/catalog
tuple and cannot become active from environment name or credential presence.

**Implementation surfaces**

- Release manifest and configuration/catalog digests.
- Capability-state record and authority evidence.
- Deployment verification inputs.

**Tasks**

1. Bind signed image digests, schema compatibility, provider-binding version, manifest digest,
   secret-catalog digest, policy digests, and rollback tuple.
2. Record required dependency IDs and authority evidence references.
3. Implement only `BLOCKED`, `UNAVAILABLE`, `READY_INACTIVE`, and `ACTIVE` effective states.
4. Make missing, stale, expired, revoked, mismatched, or Stop authority reduce state.
5. Require separate external-traffic and activation records before `ACTIVE`.
6. Prove the same image has identical route, component, command, schema, and lifecycle manifests
   under Demo-, UAT-, and Production-shaped configuration.

**Executable evidence**

- Tuple/digest verification.
- State transition table tests.
- Default-off, expiry, mismatch, revocation, Stop, and rollback negatives.
- Same-image manifest comparison.

**Definition of Done**

- Deployment inputs select `READY_INACTIVE` at most.
- Credential existence alone cannot create readiness or activation.

**Stop**

- Mutable image/tag, unbound configuration, environment-name branch, success-shaped fallback, or
  transitive authority.

### WC121-C09-S12 - Zero-Traffic Deployment And Private Qualification

**Outcome:** The exact qualified tuple is deployed with zero traffic and proves startup, private
dependencies, observability, and rollback readiness without provider effects.

**Implementation surfaces**

- Authorized Demo deployment workflow and private runner.
- Existing ACA environment, identities, Key Vault references, readiness, telemetry, and rollback.

**Tasks**

1. Verify subscription, resource group, environment, source authorization, tuple, and rollback
   target before mutation.
2. Deploy the exact Component 08 image without rebuild, retag, or image mutation.
3. Start the new revision at zero traffic.
4. Verify liveness, startup, traffic readiness, optional WhatsApp readiness, configuration digest,
   migration watermark, Stop, evidence writes, queue bounds, and telemetry.
5. Prove health/readiness sends no Meta traffic and performs no consequential command.
6. Retain failure evidence and cleanly revert the zero-traffic revision on failure.

**Executable evidence**

- Deployment plan/apply and independent verification records.
- Exact image/configuration/catalog digest match.
- Zero-traffic network observation.
- Startup/readiness failure matrix and rollback proof.

**Definition of Done**

- The revision is healthy and `READY_INACTIVE`.
- Callback acceptance, dispatch, and provider egress remain false.

**Stop**

- Digest mismatch, secret value in deployment evidence, foreign-environment reference, unbounded
  queue, missing alert/runbook, provider effect, or failed rollback.

### WC121-C09-S16 - WC-123 Authentication, Authorization, And Auth-Presentation Integrity

**Outcome:** WhatsApp live-provider work cannot advance while the shared Login/Register entry,
provider-neutral authentication ceremony, application session, current-membership authorization,
or customer-visible provider disclosure is broken or unqualified on the exact Web candidate.

**Status:** BLOCKED. The previously recorded candidate `cf48eea4b199da29da4b9c9490da229fa82b15ad`
is not an ancestor of PR #512's final head `d15bc4df72f1df7a3a32b4f8857216bfa84646d3`.
The deployed candidate also returned `ABUSE_LIMITER_UNAVAILABLE` before broker handoff because its
always-on authentication limiter runtime contract was absent from Demo.

**Completion evidence**

- Google and Facebook Login and Register preserve explicit provider intent and customer-safe
  disclosure before broker handoff.
- Register clears stale Keycloak SSO and resumes only the allowlisted Google or Facebook provider.
- Normal Logout returns Home; Account Switch clears the prior session and remains Login-bound.
- Business Platform resolves the verified issuer, subject, active membership, account, and tenant;
  canonical, issuer-qualified, and pre-issuer registration continuity cannot cross issuers or
  tenants.
- Focused authentication units pass `49/49`; WC-083, WC-094, and WC-099 browser journeys pass
  `24/24`; preview contracts pass `9/9`; the full Business Platform gate passes `1119/1119`;
  production builds, forced-RLS/grant checks, repository pre-commit, and C-059 pass.
- The Codespace preview evidence is retained as local evidence only. It does not satisfy Task 15,
  exact-head qualification, or deployed-environment readiness.

This status satisfies only S16. It does not authorize or claim S01-S15, Meta account inspection or
mutation, protected credential use, Azure/DNS/TLS mutation, deployment, callback subscription,
external traffic, live WhatsApp acceptance, capability activation, approval, or merge.

**Implementation surfaces**

- WC-123 exact accepted candidate, requirement ledger, impact manifest, and session-readiness gates.
- Direct `/login` and `/register` routes and route-intercepted `@authModal` compositions.
- Google and Facebook provider commands, disclosure, broker handoff, cancellation, session router,
  current-membership authorization, and browser tests.

**Tasks**

1. Bind the exact Web candidate to WC-123's one Web-BFF opaque session authority, stock-Keycloak
   credential authority, BP current-membership authorization, and typed post-authentication router.
2. Reproduce Login and Register both by direct navigation and by clicking their public-page
   launchers so the route-intercepted `AuthDialog` composition is exercised.
3. Delete the nested `<dialog className="provider-disclosure" open>` implementation, its global
   keydown/focus-trap code, and the viewport-overlay `.provider-disclosure` CSS. Do not patch the
   native border with another CSS override.
4. Render provider disclosure as a state inside the existing Login/Register card and, when route
   intercepted, inside the one existing `AuthDialog`. Cancel returns to provider selection;
   Continue launches the selected provider. There must never be two active dialog layers.
5. Delete stale disclosure selectors and rules that no longer own rendered markup. Keep only
   card-local content/action styling scoped to the accepted auth component.
6. Open Google and Facebook disclosures in every supported composition and prove exactly one
   coherent customer interaction layer: no viewport-spanning native dialog border, stacked modal
   ambiguity, obscured content, clipped command, background interaction, focus escape, or duplicate
   accessible dialog ownership.
7. Capture visual evidence while each disclosure is open, not only after cancellation. Assert
   disclosure and panel bounding boxes, viewport containment, computed border/background, stacking,
   scroll behavior, 200% zoom, 360px reflow, RTL, reduced motion, keyboard order, Escape, focus
   restoration, and screen-reader naming.
8. Prove Cancel starts no provider request and changes no session, registration, membership,
   tenant, relationship, or authorization state.
9. Prove Continue performs exactly one provider-neutral broker handoff; Login cannot create
   registration/onboarding, and Register cannot silently become Login or employment admission.
10. Wire and exercise the WC-123 typed post-authentication router in the production callback or
    accepted continuation path; a test-only unused router is not completion evidence.
11. After callback, prove the Web-BFF owns the opaque session, BP derives current membership, every
   protected operation reauthorizes current tenant/resource/action, and stale, removed, suspended,
   or role-reduced membership denies immediately.
12. Prove local Logout clears protected browser state, revokes the current Web session, broadcasts
    the session change, and ends the Keycloak session without depending on provider availability.
13. Prove Account Switch clears protected state, revokes the current Web session before broker
    launch, ends the Keycloak session, returns to provider/account selection, and never renders the
    prior account while revocation or provider selection is pending or failed.
14. Prove Facebook-login App ID/secret and identity-broker authority are purpose-separated from
   WhatsApp App Secret, provider binding, outbound authority, media authority, callback, and
   activation.
15. Run the journey against the exact deployed candidate and supported Chromium, Firefox, and WebKit
   matrix before WC121-C09-S13 receives external-traffic authority.

**Executable evidence**

- Static source assertions that the auth flow contains no nested provider `<dialog open>`, no
  `.provider-disclosure` viewport-overlay rule, and no obsolete disclosure focus trap.
- Playwright direct-route and public-launcher route-interception journeys for Login and Register.
- Open-disclosure screenshots for Google and Facebook at desktop, 360px, 200% zoom, RTL, and dark
  and light themes.
- Bounding-box, computed-style, focus-trap, background-inertness, Axe, and no-overflow assertions.
- Provider-request capture proving Cancel is inert and Continue launches exactly one expected
  broker path.
- Login-existing, Login-without-account, Register-new, Register-existing, Logout, Account Switch,
  cancel, provider-failure, session-revocation-failure, and stale-membership journeys.
- Session, current-membership, tenant/resource/action, stale-authority, and cross-tenant negatives.
- Secret-catalog and RBAC proof that Facebook login and WhatsApp authorities have no shared secret
  or unintended consumer.

**Definition of Done**

- Direct and route-intercepted Login/Register journeys have the same accepted meaning and a
  coherent, accessible visual composition.
- Google and Facebook disclosure, Cancel, Continue, callback, post-authentication routing, and
  current-membership authorization pass on the exact candidate.
- The old nested-dialog markup, overlay CSS, and manual nested-dialog focus trap are absent.
- Logout leaves the browser locally unauthenticated even during provider outage; Account Switch
  cannot start a new broker handoff until prior Web-session revocation is confirmed.
- No backend provider-readiness state silently alters visible controls.
- No Login action creates registration, onboarding, relationship, or employment state.
- Facebook login and WhatsApp credentials, identities, callbacks, and authorities remain
  purpose-separated.

**Stop**

- Nested-dialog visual corruption, missing open-state visual evidence, focus/background leakage,
  provider-specific application semantics, cancellation side effect, duplicate broker request,
  mixed session authority, claim-derived tenant/role authority, stale membership acceptance,
  cross-tenant access, or credential-purpose reuse.

### WC121-C09-S13 - Bounded Live Provider Acceptance

**Outcome:** One authorized Demo scenario proves callback, inbound, outbound, cross-channel,
evidence, observability, and rollback behavior without expanding recipient, time, spend, or purpose.

**Implementation surfaces**

- Exact deployed revision and configuration tuple.
- Meta callback, approved template, bounded recipient, BP/Conversation/owner/evidence paths.
- Alerting, incident, reconciliation, and rollback paths.

**Tasks**

1. Confirm provider-account, credential-use, external-traffic, recipient, window, spend, incident,
   and rollback authorities immediately before the test.
2. Enable provider egress and callback acceptance only for the approved window and tuple.
3. Verify valid challenge, exact raw-body signature, freshness, deduplication, account/phone
   binding, inbound text, and privacy-safe acknowledgement.
4. Send one approved template to the authorized recipient and process the reply.
5. Verify Portal-to-WhatsApp-to-Portal continuity with one relationship, conversation, command,
   owner outcome, and evidence history.
6. Verify delivery, processing, evidence, commercial, and outcome dimensions remain independent.
7. Exercise end-session, Stop, invalid signature, stale/replayed event, wrong recipient, provider
   failure, alert routing, reconciliation, and rollback.
8. Disable live gates at the approved expiry even if the test is incomplete.

**Executable evidence**

- Redacted provider receipts and opaque identifiers.
- Inbound/outbound, replay, failure, Stop, alert, and rollback results.
- Exact release/configuration/catalog digests.
- Proof of bounded recipient, window, spend, and deactivation.

**Definition of Done**

- The approved scenario passes without duplicate business effects or protected-value leakage.
- Provider delivery never substitutes for owner/evidence success.
- The capability returns to `READY_INACTIVE`.

**Stop**

- Authority mismatch/expiry, unexpected recipient, signature/freshness failure, duplicate effect,
  missing evidence, redaction failure, Stop failure, alert failure, or rollback uncertainty.

### WC121-C09-S14 - Explicit Activation And Automatic Expiry

**Outcome:** The Demo capability becomes active only through a separate decision bound to exact
scope and automatically returns inactive at expiry.

**Implementation surfaces**

- Capability-state record.
- Traffic switch and expiry controller.
- Incident, spend, alert, and rollback ownership.

**Tasks**

1. Require a separate Founder activation record naming environment, capability, release and
   configuration digests, audience, recipient set, start, expiry, spend, incident owner, and
   rollback tuple.
2. Revalidate every dependency, credential version, alert route, Stop state, and traffic decision.
3. Transition `READY_INACTIVE` to `ACTIVE` only after exact match.
4. Automatically disable callback acceptance, dispatch, and provider egress at expiry or revocation.
5. Prevent ordinary workflow, deployment success, credential presence, or prior acceptance from
   reactivating the capability.

**Executable evidence**

- Valid activation and every mismatch/expiry/revocation negative.
- Automatic and manual deactivation proof.
- No-effect reactivation attempts.

**Definition of Done**

- Activation is bounded, observable, reversible, and non-transitive.
- Expiry returns the capability to `READY_INACTIVE` or `BLOCKED`.

**Stop**

- Missing exact activation record, stale tuple, unavailable Stop, untested alerts, missing incident
  owner, or unbounded recipient/window/spend.

### WC121-C09-S15 - Rollback, Credential Revocation, And Demo Teardown

**Outcome:** Failure or planned teardown disables provider effects, reconciles uncertain work,
revokes temporary authority, disposes eligible data, and proves zero UAT/Production impact.

**Implementation surfaces**

- Callback/dispatch/egress gates.
- Outbox, provider claims, reconciliation, tombstones, evidence, payload/media lifecycle.
- Azure resources, Meta assets, Key Vault versions, DNS/ingress, and teardown evidence.

**Tasks**

1. Disable callback acceptance, dispatch, and provider egress before teardown or rollback.
2. Stop new leases and reconcile or quarantine every `DISPATCHING`, `UNRESOLVED`, retry, callback,
   media, and owner outcome.
3. Preserve required idempotency claims, tombstones, Stop latches, delivery observations, owner
   truth, and immutable evidence.
4. Revert traffic/configuration to the previous qualified compatible tuple without rebuilding or
   restoring revoked security state.
5. Revoke temporary Meta and Key Vault authority and prove consumers can no longer use it.
6. Remove provider bindings, templates, DNS/ingress, or temporary resources only under their own
   exact authority.
7. Erase eligible payloads and derivatives; retain only policy-required tombstones/evidence.
8. Prove UAT and Production identities, secrets, data, DNS, ingress, and activation changed by zero.

**Executable evidence**

- Pending, reconciled, quarantined, and held-work teardown matrix.
- Credential-revocation and non-resurrection proof.
- Data disposition and retained-evidence report.
- UAT/Production zero-diff check.

**Definition of Done**

- No provider effect remains enabled.
- No accepted owner effect or evidence is deleted or falsely represented as reversed.
- Residual retained state is explicit, policy-backed, and non-routable.

**Stop**

- Uncertain provider outcome, active retry, unresolved hold, missing revocation authority, attempted
  destructive rollback, evidence deletion, or any UAT/Production delta.

## 6. Story-Level Evidence Rules

Every story records:

1. exact source and candidate digests;
2. requirement IDs and authority references;
3. changed paths and owners;
4. exact Docker-owned commands and results;
5. image, schema, configuration, catalog, and policy digests where applicable;
6. redacted machine-readable evidence location;
7. residual risk and blocked obligations;
8. rollback or stop action; and
9. author-review result.

Passing repository or emulator evidence does not satisfy live Meta, Azure, DNS, deployment, traffic,
activation, approval, or merge gates.

## 7. Completion Criteria

This work component is complete only when:

1. S01 through S16 satisfy their direct completion criteria;
2. WC-121 Component 08 exact-image qualification remains valid for the deployed digest;
3. every WC-121 Section 2.3 gate is recorded separately;
4. the canonical five Key Vault references are versioned and purpose-separated;
5. the dedicated Demo callback host and route pass challenge and signed-event verification;
6. one bounded recipient scenario proves inbound, outbound, parity, Stop, alerts, reconciliation,
   rollback, and deactivation;
7. no complete telephone identity, credential, provider payload, or customer content appears in a
   prohibited surface;
8. capability state is `READY_INACTIVE` after acceptance unless a separate unexpired activation
   decision exists;
9. UAT and Production change by zero;
10. author review finds no unresolved material issue; and
11. the Founder receives the exact-head PR for review and merge.

## 8. Explicit Non-Authorization

This candidate does not authorize:

1. source or generated implementation work;
2. Meta account inspection or mutation;
3. credential creation, access, use, rotation, or revocation;
4. Azure, Key Vault, RBAC, ingress, DNS, TLS, or cloud mutation;
5. deployment or traffic switching;
6. callback registration or event subscription;
7. outbound or inbound external traffic;
8. capability activation;
9. PR approval; or
10. merge.

Each action begins only after its exact current authority and prerequisites are recorded.

## 9. PR Validation Efficiency Extension

This extension governs delivery efficiency for this component and later work that uses the same
validation controls. It does not weaken exact-head traceability, hosted independence, security
checks, author review, Founder review, or merge authority.

### 9.1 Practical Target

| Change class | Current approximate delay | Target | Saving |
|---|---:|---:|---:|
| Message-only rewrite, identical tree | **~13m 50s** | **~2 min** | **~11-12 min** |
| Documentation/checkpoint-only update | Often **7-10 min** hosted | **~2-3 min** | **~5-8 min** |
| Already-prechecked source tree | **~14 min** local and hosted | **~6-8 min** | **~6-8 min** |
| New Business Platform or Web runtime change | **~14 min** | **~9-11 min** | **~3-5 min** |

### 9.2 Evidence-Reuse Boundary

Content-dependent executable evidence may be reused only when all of the following remain exact:

1. Git tree identity or a verified non-intersecting input path set;
2. gate, command, and validation-catalog identity;
3. gate implementation, runner, environment, and service digests;
4. declared gate input digest and artifact digests; and
5. a successful, machine-readable source evidence record.

Commit-dependent controls are never carried by tree identity. C-059 commit and PR-body
traceability, C-065 exact-head author review, C-066 authorization, requirement-ledger validity,
secret detection, remote-head binding, and PR metadata attestation execute for the current
candidate.

### 9.3 Delivery Sequence

1. Persist local pre-commit and PR-preparation evidence in the shared Git common directory so all
   worktrees use one durable candidate cache.
2. Reuse identical-tree gate results across a staged synthetic commit, its resulting commit, and a
   message-only history rewrite.
3. Preserve per-gate invalidation so one changed input reruns only its affected gate and dependants.
4. Collect the required hosted Shadow samples and prove zero unresolved false negatives. Complete:
   20 successful Code Quality comparisons and 20 successful full-CI Test Champion campaigns were
   verified on 2026-10-15.
5. Activate focused hosted selection only after its catalog activation conditions and Founder
   authority are recorded. Authorized in the current session and bound to
   `validation/evidence/wc121-selective-validation-activation.json`.
6. Keep periodic and main-branch full-inventory qualification independent from PR fast paths.

### 9.4 Acceptance

- An identical-tree second candidate executes zero reusable content-dependent local gates.
- Corrupt, missing, mismatched, or non-verifiable evidence causes execution rather than reuse.
- A runtime, validation-control, runner, environment, or declared-input change invalidates its
  affected evidence.
- Exact-head and commit-dependent controls run on every candidate.
- Hosted selective execution remains blocked while its activation evidence is incomplete.

### 9.5 Hosted Runner Selection Before Supply

The authoritative validation plan must resolve the required runner identities before runner supply
begins. The plan executes in a lightweight control plane with a pinned Python version and
hash-pinned dependency manifest. It records the exact base, head, interpreter, and dependency
manifest digest used for selection.

Each consuming workflow passes only `required_runners` from the authoritative plan to the reusable
runner-supply workflow. Full-inventory behavior remains fail-closed for global, normative, unknown,
main-push, and scheduled changes.

Acceptance:

- A documentation-only candidate does not resolve or publish an unselected runner.
- A full-inventory candidate still supplies all five validation runners.
- No validation gate starts until every runner selected for that candidate has trusted immutable
  manifest evidence.
- The validation plan does not download or start the multi-language full runner merely to compute
  selection.
- Static preflight renders Compose and checks Dockerfiles only when their graph inputs change;
  workflow lint remains scoped to changed workflow files.
- Static workflow validation proves the plan-to-supply dependency direction in CI, Code Quality,
  Integration, and E2E workflows.

### 9.6 Long-Running Gate Optimization

Release qualification selects its exact lanes before runner supply. Planning-only dependency and
hosted-policy changes do not select deployment rehearsal, while unknown paths and changes to the
qualification selector, catalog, runner supply, or shared release execution remain fail-closed.
The lean Python runner provides the fixed host-orchestration identity; the full multi-stack runner
is supplied only for test, PostgreSQL, or simulator lanes, and the Azure runner only for the Azure
lane.

The Azure runner is an immutable digest-pinned Azure CLI image with Container Apps extension
`1.3.0b4` installed at build time. Runtime verification checks the installed extension version and
records durations for image/emulator readiness, extension readiness, positive deployment,
negative deployment, and cleanup evidence.

C# CodeQL uses supported buildless analysis while retaining the `security-and-quality` query
suite. Python and JavaScript CodeQL coverage remains unchanged.

Acceptance:

- `requirements-validation-plan.txt` and `scripts/validation_control/hosted_policy.py` do not
  select any release lane.
- Azure-only qualification does not supply or pull the full multi-stack runner.
- Mixed qualification consumes the independently attested full and Azure runner images.
- The prebuilt Azure image proves Container Apps extension `1.3.0b4` under the runtime user.
- C# CodeQL has `build-mode: none`, no autobuild step, and unchanged query coverage.
- Release evidence uploads are conditional on the lane that produces each artifact.
