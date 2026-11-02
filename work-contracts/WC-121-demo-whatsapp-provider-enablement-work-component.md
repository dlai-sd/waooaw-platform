# WC-121 Demo WhatsApp Provider Enablement Work Component

## 0. Record Control

| Field | Value |
|---|---|
| Work component | WC121-C09 - Demo WhatsApp Provider Enablement |
| Version | 0.1.0-candidate.4 |
| Status | SESSION IMPLEMENTATION AND DEMO SCOPE AUTHORIZED - EXACT INPUTS AND QUALIFICATION PENDING |
| Parent Work Contract | `work-contracts/WC-121-customer-engagement-workspace-implementation.md` |
| Controlling component | WC-121 Section 6.9, CEW-WC-09 - Live Demo Provider and Deployment |
| Upstream transport Work Contract | `work-contracts/WC-120-conversation-engine-whatsapp-implementation.md` |
| Solution input | `architecture/reference/components/customer-engagement-workspace-solution-contract.md` |
| WhatsApp solution input | `architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md` |
| Environment input | `infrastructure/conversation-whatsapp/demo.json` |
| Environment schema | `infrastructure/conversation-whatsapp/environment.schema.json` |
| Implementation office | Platform IT Expert |
| Source baseline | `origin/main` at `6166da3fb516c78143207ac6d4bc9af7c1652c2c` |
| Result | PLANNING AMENDED; S01-S16 REQUIRE CURRENT-CANDIDATE EVIDENCE AND APPLICABLE PROTECTED INPUTS |

This work component decomposes already accepted WC-120 and WC-121 boundaries into executable
Platform IT stories. It makes no new architecture decision and does not authorize source changes,
provider access, credential use, Azure or DNS mutation, deployment, external traffic, activation,
PR approval, or merge.

**2026-11-02 current-session amendment:** The Founder explicitly authorized implementation and
inclusion of Demo provider enablement, deployment and activation in WC-120, then confirmed
`implementation_authorization=true` and a separate latest-main worktree. WC-120 Section 12 is the
owning scope/impact/grouped-plan amendment, based on
`a497cb2f2669d7da90dcb37611badffc4c6953ea`. It supersedes the earlier blanket non-authorization
above and in Section 8 for this assignment, but does not supply missing exact provider/cloud
identities, protected credentials, recipient/window/spend, qualified tuple or activation inputs.
Each Section 3 gate must still be recorded and checked independently before its action.
PR approval/merge and UAT/Production mutation remain excluded. Existing S01-S16 are the required
Demo stories; do not create a duplicate story chain or infer completion from historical evidence.

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
3. For Demo, designate the existing Business Platform managed identity as the WhatsApp provider
   runtime principal. The entire BP application, revisions and processes sharing that identity
   form the trusted boundary; logical adapter naming provides no intra-BP security isolation.
   Keep deployment/configurator and independent verifier principals separate.
4. Grant exact-secret read only on the separate approved provider-binding, verification-token,
   App Secret and outbound-authority references required by enabled flows. Describe the existing
   `Key Vault Secrets User` role accurately, including associated metadata access; it is not a
   custom literal-get-only role. Exclude broader inherited access and enforce version, purpose,
   environment, revocation and expiry in runtime controls.
5. Deny provider-secret access to Keycloak, Web, other runtime principals, UAT, Production and
   unrelated workloads. Do not reuse Facebook-login credentials. Do not grant media credentials
   to BP: provider media retrieval remains disabled unless the accepted distinct scanner boundary
   and its environment-bound identity and safety proofs exist.
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
5. Authenticate independently deployed callers and enforce the accepted audience, purpose,
   operation, environment and delegated-context checks. In-process adapter-to-BP calls preserve
   authorization context but are not an independently authenticated workload boundary.
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

- New deployable, ingress owner, public facade, cross-duty runtime/configurator/verifier identity
  sharing, credentials shared with another workload, or health probe with an external effect.
  The explicitly designated Demo BP/provider-runtime identity is permitted; no intra-BP isolation
  is claimed.

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

For this session, the authorization amendment in Record Control and Section 10 supersedes the
historical blanket prohibition for the bounded WC-120/Demo assignment. The independent exact-input
checks in Section 3 and all story acceptance/stop predicates remain controlling.

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

## 10. Current-Session Impact And Founder Configuration Intake

### 10.1 Complete Protected-Action Story Inventory

Baseline: `a497cb2f2669d7da90dcb37611badffc4c6953ea`, branch
`ib/120/whatsapp-demo-implementation`. All statuses below are inspection findings, not test results.
The grouped execution order, WC-120 requirement mapping, validation timing, evidence identity and
rollback boundary are in WC-120 Section 12.4.

| Story | Existing surface / baseline observation | Required delta, direct evidence and dependency |
|---|---|---|
| S01 | Existing WC-120/WC-121 contracts, ledgers and source/owner records | Freeze current exact digests and independent action inputs; contract intake passes but image and protected inputs remain pending. No implementation under S01. |
| S02 | Demo manifest has only `DEMO_SUFFIX_3575` and protected reference placeholders | Verify dedicated app/WABA/sender/billing and a distinct authorized recipient through the protected operator path; never infer live ownership from a manifest. Requires S01. |
| S03 | Environment schema and BP `Wc120ConversationOptions`/`WhatsAppJourneyOptions` exist | Close the production binding schema, unknown/wrong-environment/expiry/revocation controls and protected resolver mapping; fixtures do not supply credentials. Requires S01-S02. |
| S04 | `infrastructure/environment-readiness/secret-catalog.json` has no WhatsApp entries; Demo manifest already names five references | Add exact purpose-separated catalog/consumer/rotation records and deterministic rendering; prove zero UAT/Production configuration delta and no values. Requires S03. |
| S05 | Existing private environment provisioning path and versioned Key Vault pattern | Bind approved no-echo entry, metadata/expiry/rotation/revocation and non-resurrection tests; do not place secrets in CLI arguments, Terraform or chat. Requires S04 and exact credential authority. |
| S06 | Existing Demo OIDC/private runner and workload identity controls | Apply the bounded Security-owned BP/provider-runtime reconciliation in Section 10.4; prove exact secret/principal/purpose denial and absence of broader inherited grants. Requires S04 and exact environment inputs. |
| S07 | BP owns webhook and outbox; standalone legacy `src/phone-identity-service/Program.cs` also exists; BP DI selects `DisabledWhatsAppProviderAdapter` | Reuse BP ownership and existing release members, complete real transport/runtime scheduling without a new deployable, and prove startup/raw-byte/authentication and cross-workload/cross-duty secret isolation. Requires S03-S06; the full BP process is the declared provider-runtime trust boundary. |
| S08 | `callbackHostReference` is `whatsapp-demo.<approved-domain>`; existing protected Demo deployment path | Supply exact approved callback DNS/TLS/route and ingress owner, restrict challenge/POST paths and raw bytes; Portal host is not a fallback. Requires S07 and exact cloud/DNS scope. |
| S09 | Existing `WhatsAppJourneyController.Verify()` is gated with POST acceptance | Separate authorized GET challenge readiness from disabled business POST/dispatch; register exact Meta URL/subscription only after protected inputs and ingress qualify. Requires S05/S08. |
| S10 | Existing outbox consent/window/template eligibility, opaque recipient/payload references | Complete real provider credential/template/recipient binding, enqueue/send-time authority/spend/expiry checks and timeout reconciliation; no temporary token or blind resend. Requires S02-S06. |
| S11 | Default-off Demo manifest and signed exact-seven release path exist | Bind release/config/catalog/policy/provider/authority versions and capability state; credential presence cannot activate. Prove expiry/revocation/Stop and same-image parity. Requires S04/S07/S10. |
| S12 | `.github/workflows/deploy.yaml`, reusable deployment/verification and phase2 Terraform | Use existing immutable promotion/private runner and independently verify zero-traffic readiness; no rebuild during deployment. Requires S08/S11, exact qualified image and cloud scope. |
| S16 | Existing WC-123 opaque-session/current-membership code; current main includes logout correction #573 | Requalify exact Web image for direct/intercepted Google/Facebook Login/Register, Logout/Switch, membership and visual/accessibility oracles; old failure text is historical, not current failure evidence. Requires S01/S11/S12. |
| S13 | Existing canonical conversation, webhook, outbox and Stop test surfaces | Live challenge/template/reply/cross-channel/Stop/alerts/replay/rollback acceptance is still required; emulator and source inspection cannot pass it. Requires S09-S12/S16 plus exact recipient/window/spend. |
| S14 | Four default-off manifest switches and activation sentinel exist | Implement exact-tuple activation/expiry enforcement at effect boundaries; prove deactivation/revocation and no automatic reactivation. Requires S13 and complete bounded activation inputs. |
| S15 | Existing outbox, claim/tombstone, Stop and recovery/rollback surfaces | Rehearse fence/reconcile/revoke/retain/erase sequence and zero UAT/Production delta; full resource deletion needs its exact scope and accepted lifecycle decisions. Requires S13-S14 for live rehearsal. |

### 10.2 Founder Inputs And Where To Configure Them

Supply only readiness status and protected references in chat. Complete telephone identities,
provider IDs bound to telephone identity, tokens, App Secret, verify token, OTPs, payloads and
customer content must stay in the approved private configuration channel. A reference is not
proof that a secret exists, is current, or is readable by its intended principal.

| Founder/operator input | Official configuration location | Safe handoff |
|---|---|---|
| Dedicated Demo Meta business portfolio and WhatsApp app; App ID and App Secret | [Meta App Dashboard](https://developers.facebook.com/apps/) - select the app, its WhatsApp use case and app settings | Confirm dedicated ownership/status; provision protected binding metadata and `whatsapp-app-secret`, not values in chat. Keep separate from Facebook-login credentials. |
| WABA, Phone Number ID, sender/display-name verification and selected supported API version | App WhatsApp API Setup; [WhatsApp Manager](https://business.facebook.com/wa/manage/); [official setup guide](https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started) | Resolve identities only through `whatsapp-provider-binding`; confirm the suffix-safe sender label. Do not purchase or migrate a number under general scope authority. |
| Demo-only system user, assigned app/WABA assets and least-privilege messaging/media permissions | [Meta Business Settings](https://business.facebook.com/settings/) - Users, System users and assigned assets | Provision `whatsapp-outbound-authority` and separately scoped `whatsapp-media-authority`; no temporary Getting Started token or personal token. Operator performs MFA/OTP steps privately. |
| Consenting distinct Demo recipient, approved scenario and purpose | WhatsApp API Setup/recipient settings and the approved private consent/configuration channel | Provide only an opaque recipient/consent reference and readiness status. Do not assume sender can message itself. |
| Approved template name, category, locale, variables/version and billing readiness | WhatsApp Manager - Message templates and account payment settings | Provide non-sensitive approved template metadata/policy reference; runtime still validates the current approval and consent. Initial Product locale remains `en-IN`. |
| Final callback hostname/domain ownership and DNS/TLS scope | Approved DNS provider and [Azure Portal](https://portal.azure.com/) for the existing Demo ingress | Confirm the exact approved hostname and cloud scope through protected configuration; implementation derives the final route from the accepted BP API. Do not register a placeholder or the Portal catch-all. |
| Webhook callback URL, verify token and message subscriptions | Meta app WhatsApp Configuration; [official webhook guide](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview) | Operator enters the generated `whatsapp-verify-token` privately after exact ingress/challenge qualification. Subscription success does not activate POST acceptance or dispatch. |
| Five versioned canonical Demo secret references | Existing private-network no-echo provisioning path for `kv-waooaw-demo`; [Azure Key Vault documentation](https://learn.microsoft.com/azure/key-vault/secrets/about-secrets) | `whatsapp-provider-binding`, `whatsapp-verify-token`, `whatsapp-app-secret`, `whatsapp-outbound-authority`, `whatsapp-media-authority`; no portal/public-network bypass or broad vault grant. |
| Exact Demo subscription/resource group, DNS zone, identities and rollback target | Existing protected environment configuration and approved deployment pipeline | Supply/confirm opaque configuration and authority references; no UAT/Production grant or mutation. |
| Live UTC start/expiry, maximum spend, message/rate ceiling, recipient set, incident owner and alert destination | Founder decision bound to the exact qualified release/configuration/catalog and previous compatible tuple | Record non-sensitive limits and opaque references; reject absent, expired, wrong-tuple or revoked authority at dispatch, receipt and activation. Image digests are bound after qualification, not guessed now. |
| Demo recovery and lifecycle/consent policy acceptance | WC-120 Sections 2.3/3.3 and accepted Data/Legal records | Explicit material-risk decision on Demo RPO 24h/RTO 8h and applicable policy references; do not infer Legal decisions or UAT/Production acceptance. |

The implementation office will generate the verify token and validate the safe provisioning
mechanism; the Founder does not need to invent or paste it. Real account creation, MFA, business
verification, number registration and template approval may require the authorized human operator
and provider processing time.

### 10.3 Current Stop And Resume Conditions

No live provider/cloud query or mutation has been performed under this amendment.
Current-session implementation and bounded Demo scope are authorized, but protected execution
waits for the exact inputs above, verified credential controls, current exact-image qualification
and independent deployed-authentication proof. Do not claim S01-S16 completion, live Meta acceptance
or go-live merely because source code, fixtures, secret references or an earlier deployment exist.

Continue compatible repository work using Section 10.4's S06/S07 clarification; stop on a proposed
stronger isolation claim that the existing topology cannot enforce. UAT/Production remain untouched. After all repository implementation
and test sources are complete, run the consolidated Docker qualification required by WC-120
Section 12.4, perform author review, and prepare the exact-head PR using the existing template and
mandatory preparation gates. No PR is represented as tested or merge-ready before those checks pass.
The canonical deployment accepts a matching trusted-main control/release SHA only. Submit the
engineering-qualified PR first, wait for Founder merge and trusted release publication, then execute
S12-S15 and retain their live evidence here. No pre-merge branch deployment or self-merge is
authorized, and pending live stories must remain explicit in the implementation PR.

### 10.4 Focused Technical Dispositions And Shared API Invariant

On 2026-11-02 the Founder authorized focused help from specialized WAOOAW offices rather than
delegating engineering decisions back to the Founder. Platform Architect assessed the existing BP
workload mapping and recommended the smallest explicit whole-BP runtime boundary instead of a new
deployable. Security Architect returned a bounded conditional acceptance within existing security
owner controls: accepted enterprise architecture Sections 13.6/identity controls already place the
logical adapter under BP and separate runtime, scanner and configurator duties; ADR-053 separates
those duties, not processes within BP.

The corrected S06/S07 wording above records that technical reconciliation, not a new independent
review, proven effective cloud permission, Founder risk exception or deployment approval. The
Security-owned mandatory conditions remain: exact-secret read and no broad inherited grant;
separate environment/duty identities; raw-byte authentication; fail-closed authorization and
privacy-safe evidence; just-in-time secret use with at most five-minute memory lifetime; bounded
rotation overlap; immediate emergency revocation; and no rollback resurrection. If compromise of
ordinary BP code must be unable to read the adapter's credentials, this topology cannot provide
that guarantee and work stops for a separately authorized architecture change.

The Founder also explicitly confirmed API reuse across WhatsApp, Customer Portal Web and a possible
future Mobile application. All clients use the same channel-neutral BP conversation and command
semantics, canonical history, identity/relationship authority, idempotency and evidence. WhatsApp
webhooks/provider transport are adapters to those owners, not another business API or conversation
engine. Web and future Mobile consume the generated shared public contract; server-only callback
and provider credentials must never be exposed in a client bundle. This assignment does not create
a Mobile application.

### 10.5 Current Implementation Authoring Checkpoint - Not Acceptance Evidence

The current isolated implementation branch contains the following source changes. These are
authored changes, **not cloud permission proof, provider acceptance, deployment,
activation or completed-story claims**. Section 10.6 records subsequent engineering test execution.

- GET challenge verification has its own default-off switch, exact query-key/multiplicity and
  UTF-8 byte limits. The asynchronous route reads only the pinned verification secret. POST
  acceptance remains independently gated and requires the exact JSON media type and raw bytes.
- The BP provider runtime has fresh, purpose-separated Key Vault reads through its workload
  identity. Binding, verification, App Secret and outbound reads are distinct; media is never
  requested. Versions, enabled/not-before/expiry metadata, response size, duplicate JSON members,
  exact vault/secret identity and the closed binding document are checked. Outbound credentials
  carry a five-minute maximum usable lifetime. Neither protected HTTP logging nor provider spans
  may contain values; incoming verification URLs are excluded from callback tracing.
- `provider-binding.schema.json` describes the private binding value, not a checked-in fixture.
  Its recipient digest must name an already admitted canonical contact/channel binding. A
  verified Meta sender is matched to the protected telephone binding and that existing opaque
  identity; rotating the App Secret does not recalculate identities or create contacts. The
  production provider path rejects the legacy synthetic envelope and does not mint legacy
  channel-specific tenant tokens. Legacy service callers retain their existing key-based path.
- The cloud adapter reads the existing canonical conversation message and matching outbox
  record. It does not create another message store or public business API. Approved, versioned,
  body-only templates project the exact canonical text into bounded numbered parameters;
  unsupported layouts, missing projections and approval mismatches deny rather than alter
  content. Templates with other components require their own admitted projection.
- HTTP success records `PROVIDER_ACCEPTED` delivery evidence, **not** `DELIVERED`. The outbox
  remains `UNRESOLVED` while awaiting verified delivery evidence. Reconciliation never sends.
  Opaque outbox correlation plus a durable reservation can recover a lost HTTP response or an
  early status callback without treating unknown submission as permission to resend.
- The hosted worker derives its single Demo tenant from current activation authority; the
  existing interceptor supplies transaction-local tenant context for synchronous and
  asynchronous database operations. No owner, global tenant scan or `BYPASSRLS` path is added.
- Activation checks match Demo, release/configuration/catalog/rollback digests, independent
  activation/traffic/consent references, recipient, time window, incident and alert references.
  Expiry is exclusive and is rechecked immediately before egress. Revocation and tuple drift
  fence effects. Authority metadata does not prove that alerts or dependencies are healthy;
  their exact-candidate evidence must still qualify before configuration is admitted.
- Migration `61-wc120-whatsapp-traffic-reservations.sql` adds tenant-isolated, append-only runtime
  reservations. Serializable transactions bound message count, a rolling one-minute rate and
  conservative reserved spend. Reservations are not refunded after an ambiguous outcome.
  The per-message ceiling still requires accepted provider pricing/billing evidence; this is
  not a claim that configured numbers can constrain an unknown provider invoice.
- The five canonical catalog entries declare independent provider/media readiness gates.
  WC-091 baseline configuration readiness still requires every pre-existing baseline secret
  and cannot stand in for WhatsApp readiness. Disabled media is not provisioned merely to make
  the Portal ready. Unknown gates or moving baseline secrets into an optional gate fail closed.

Authored regression selectors are `WhatsAppCapabilityGateTests`, `WhatsAppDemoProviderTests`,
the existing `WhatsAppJourneyServiceTests`/`WhatsAppOutboxWorkerTests`, and the added WC-091
pipeline tests. They cover boundary shapes, purpose-separated reads, expiry/revocation, exact
recipient/tuple denial, canonical projections, unknown outcomes, callback correlation and
baseline-readiness independence. In-memory tests do not establish PostgreSQL serializability,
effective RLS or distributed limits; the subsequent real PostgreSQL test is recorded below.

Registration-only protected deployment configuration, exact four-secret RBAC scopes, BP managed
identity selection, dedicated callback-host routing and the existing managed-certificate binding
path are now wired. The frozen provider configuration cannot enable business callbacks, dispatch
or activation. Adding the hostname does not prove DNS, TLS or effective cloud permissions.

Remaining engineering work includes admitted lifecycle/activation input wiring, catalog-owned consolidated
qualification and evidence binding, privacy/coverage/lint/build/browser/recovery closure, and
exact-head author review/PR publication. S09 and S12-S15 additionally retain the exact protected
inputs and trusted-main sequencing in Section 10.3. All production defaults remain off; no live
provider or cloud mutation has been performed.

### 10.6 Consolidated Engineering Execution Checkpoint - Not Release Or Live Acceptance

These runs exercised the isolated, uncommitted candidate based on main
`a497cb2f2669d7da90dcb37611badffc4c6953ea`. They are diagnostic engineering results, not
exact-commit catalog attestations or completed-story declarations. Commands below ran in the
repository's Docker runners, with the worktree explicitly mounted. No host Python tests or
per-story Docker campaigns were used.

| Executed command / boundary | Observed result |
|---|---|
| `csharpier check src/business-platform tests/business-platform.Tests/ConversationWhatsAppFitness` | PASS, 134 files |
| `sh scripts/validation_control/run_wc120_dotnet_test.sh -warnaserror --settings tests/coverage.runsettings --collect:"XPlat Code Coverage" --results-directory /workspace/test-results/whatsapp/coverage --logger "console;verbosity=minimal"` | PASS, 1,192 tests, zero failures/skips; 90.41% line and 80.09% branch coverage |
| `PYTHONPATH="$PWD:$PWD/scripts" pytest -q tests/pipeline tests/contract --junitxml=test-results/whatsapp/pipeline-contracts.xml` | NOT PASS: 2,176 passed; six failures also reproduced against untouched main |
| `sh scripts/validation_control/run_wc123_session_contract.sh` | PASS after full init-chain startup, session concurrency, restart and sanitized restore |
| `sh scripts/validation_control/run_web_test_gate.sh` | PASS, TypeScript, ESLint, 719 tests and enforced coverage thresholds; three pre-existing skipped tests remain disclosed |
| `pnpm exec playwright test tests/e2e/wc120-product-state-accessibility.spec.ts --workers=2 --retries=0 --output=/workspace/test-results/whatsapp/browser-results --reporter=line` | PASS, 15 scenarios across all five projects, no retries/skips; includes axe checks |
| Terraform 1.9.8 `fmt`, `init -backend=false -input=false`, and `validate -no-color` for Demo workload, with AzureRM 4.14.0 | PASS; no plan/apply or cloud proof |
| `ruff check` on affected Python implementation/tests | PASS |
| `actionlint -color -shellcheck= .github/workflows/environment-deployment.yaml` in `rhysd/actionlint:1.7.7` | PASS; shellcheck disabled explicitly, not claimed |
| `git diff --check` | PASS |

The real PostgreSQL test executes the actual budget service with 24 competing reservations,
serializable transactions, the runtime principal and tenant interceptor. It verifies count/spend
ceilings, immutable authority within an activation reference, absent/cross-tenant isolation,
denied runtime mutation and repeat migration application. Serialization losers produce an
explicit pre-egress denial. This does not substitute for distributed cloud permission or billing proof.
The adapter also reuses the owner's current consent/binding/window/template eligibility check
after protected reads, immediately before egress; opt-out/window-change regressions dispatch zero.

Qualification uncovered and repaired stale catalog/bootstrap/render bindings and migration-tail
expectations. Migration 61 now acquires/releases only its bounded owner prerequisite. The browser
fixture was missing the current required engagement-progress route; restoring that synthetic route
exposed WebKit contrast failures in the progress buttons. Scoped theme-aware colours fixed the
failure without excluding nodes or weakening axe assertions.

The first full .NET attempt encountered Temporal SDK binary-download contention. Its official
test-server dependency was fetched through the SDK's own metadata endpoint, then copied to the
container's executable temporary cache; no tests were disabled and no automatic retry was enabled. The fetched
test-server is 1.40.0, SHA-256
`19defb9f7318c7cf249518b3642a735efb79876c2b6918afe312336476b796a5`.
This additional dependency identity must be incorporated into authoritative runner/evidence
qualification rather than treating an ad-hoc cached-binary mount as immutable catalog proof.

All six remaining pipeline/contract failures were reproduced in a temporary `git archive HEAD`
baseline, before changing any baseline files:

- Two `test_auth_preview.py` assertions: scaling-source formatting and obsolete password-reference count.
- `test_prepare_pr_body.py`: an expected shared PostgreSQL path is not selected.
- `test_wc123_impact_manifest.py`: a pre-existing accepted-source digest mismatch.
- `test_wc123_session_readiness.py`: pre-existing missing rotation metadata.
- `test_agent_admission_schema.py`: a pre-existing DMA content digest mismatch.

They are not waived, edited into apparent success or classified as passing. Unrelated repairs,
exact-head publication, complete CE-FIT/recovery evidence and protected lifecycle/go-live inputs
remain unresolved; **no PR-ready, released, deployed or active status is claimed**.

### 10.7 Authorized prerequisite repairs and expanded validation (2026-11-02)

Following Section 10.6, the Founder explicitly authorized the six prerequisite repairs with
regressions. The two obsolete Terraform assertions now parse HCL: Web has zero replicas before
application activation and the configured single-replica target afterwards; both Temporal secret
owners use the exact Key Vault credential and managed identity, without inline secret values.
The actual validation policy now explicitly selects the BP precheck for its owned migration
paths, including both `029_identity.sql` and migration 61, even when a global trigger bypasses
component classification. The PR wrapper is unchanged.

The Web database catalog entry now makes its existing 90-day rotation class explicit, with
120-day expiry, zero password overlap for the single database login, and retirement blocked until
replacement uptake and old connection draining. Its regression distinguishes the
`web_session_app` database principal from the Web secret consumer. Demo/UAT projections and the
bootstrap catalog hash were regenerated. This metadata repair is not evidence that private
rotation, retirement or compromise rehearsals have occurred.

Five stale WC-123 source hashes and the DMA fixture's constitutional-DNA hash now match their
actual sources. The historical AUTH-WC-01 candidate remains unchanged; refreshed content bindings
are maintenance, not a new institutional acceptance. No agent profession, skill or version
coordinate was changed. Ruff also corrected formatting and made the touched schema-version
test's regular expression literal rather than wildcard matching.

Docker execution, using the existing full-runner recipe from this qualification campaign:

```bash
PYTHONPATH="$PWD:$PWD/scripts" pytest -q tests/pipeline tests/contract
```

Result: **PASS, 2,182 passed, zero failures**. Diagnostic log:
`test-results/whatsapp/prerequisite-pipeline-closure.log`.

```bash
PYTHONPATH="$PWD:$PWD/scripts" pytest -q tests/pipeline/test_auth_preview.py tests/pipeline/test_prepare_pr_body.py tests/pipeline/test_wc123_impact_manifest.py tests/pipeline/test_wc123_session_readiness.py tests/contract/test_agent_admission_schema.py tests/validation_control
```

Result: **500 passed, six failures**. All original prerequisite regressions pass; the additional
failures are in the broader validation-control inventory:

- `test_catalog_contract.py`: full-runner inventory and Docker-socket inventory omit the existing
  `wc123:session-contract` gate.
- `test_gate_equivalence.py`: existing catalog mode and Founder-approval flags disagree with the
  authoritative baseline.
- `test_runner_supply.py`: existing persistent-state runner dependency, reusable-plan runner-use,
  and quality-job dependency assertions disagree with current workflows.

Each of these exact six selectors also fails against a fresh archive of untouched
`a497cb2f2669d7da90dcb37611badffc4c6953ea`; no changes to those tests or workflows were made.
They are not waived. Disposition must preserve accepted validation strength and runner trust;
changing an approval flag to make an assertion pass is not approval. Further out-of-scope
repairs require Founder direction. Relevant Ruff checks pass. The full pipeline's nine appended
synthetic institutional records and generated test source were removed precisely, preserving the
original records. Activation wiring, exact-head qualification, complete author review and the
protected live gates from Section 10.6 remain open; no PR-ready or live-readiness claim follows.

### 10.8 Additional validation-control repairs authorized and verified (2026-11-02)

The Founder subsequently authorized investigation and narrow repair of the six additional
failures, preserving validation strength, runner trust and approval boundaries.

- Runner and socket inventories now include the existing nested-Docker
  `wc123:session-contract` gate; its existing classification and executable plan remain enforced.
- The frozen gate baseline now matches the selective-enforcement state already accepted by the
  Founder in merged PR #513 (`a0af1604`, merged by `dlai-sd` on 2026-10-15). The actual catalog's
  mode and approval flags were not changed. Its existing activation evidence is
  `validation/evidence/wc121-selective-validation-activation.json`, SHA-256
  `33cc214af699408d73abdb3c9f58d046697c9a93c54589f9dff6933a21279fcb`.
  New negative regressions deny changed mode, removed approval, or reduced main/release inventory.
- Planning and supply assertions now reflect Founder-merged PR #514 (`54050dfb`, merged by
  `dlai-sd` on 2026-10-15): hash-pinned host planning precedes selected runner supply. Tests retain
  the exact installer, dependency-manifest evidence, non-circular planning and output contracts.
  Host test execution is still prohibited.
- The persistent-state CI job now depends on runner supply and consumes its verified immutable
  Python image before all three existing test commands. `--no-build --pull never` prevents
  consumer-side build or image replacement. No test selector, blocking job or failure evidence
  was removed. Regressions prove the runner is selected even for empty/documentation/Web-only
  changes and the job has no selective gate-skipping condition.
- The consumer-build assertion distinguishes the `build` subcommand from the protective
  `--no-build` option; positive and negative examples preserve actual build detection.

GitHub CLI authentication was unavailable. The existing GitHub integration confirmed both merged
PRs and Founder merge identity; no credential lookup, token extraction, new approval or push was
performed.

Final Docker regression command:

```bash
PYTHONPATH="$PWD:$PWD/scripts" pytest -q tests/validation_control tests/pipeline tests/contract
```

Result: **PASS, 2,618 passed, zero failures**. Diagnostic log:
`test-results/whatsapp/validation-control-prerequisite-closure.log`.
Affected Python files pass Ruff and formatting; `actionlint -color -shellcheck=`
passes both affected workflows, with shellcheck explicitly not claimed. Only synthetic records
and test source generated by these local runs were removed; original institutional records remain
unchanged. This closes both authorized prerequisite groups, not the remaining WhatsApp
activation-input, complete CE-FIT/privacy/recovery, immutable exact-head qualification, author
review, publication or protected live gates.

### 10.9 Immutable Temporal Dependency And Canonical Projection Checkpoint (2026-11-02)

The .NET and full Docker validation images now bake in the official Temporal test server
`1.40.0` instead of allowing the SDK to download a mutable dependency at test execution.
Both verify archive SHA-256
`524465a96274831e004326f6e2f2a5f3ef9aaed72c2069cf16c1d64b8b1ec3ca`
and executable SHA-256
`19defb9f7318c7cf249518b3642a735efb79876c2b6918afe312336476b796a5`.
The shared test helper verifies the fixed `/opt/temporal-test-server` file before selecting
SDK `ExistingPath`; missing or modified binaries fail without execution or download fallback.
All three existing time-skipping call sites use that helper. Both images built successfully;
the local full image ID is
`sha256:0d785a6687921f8c6ce23f518d188763e474e467a946637b4aa7cda7dc6bf551`.
This local build is not a trusted published runner manifest or an exact-head qualification receipt.

Direct author checks reproduced and repaired two tightly coupled adapter defects:

- A known pre-send capability denial now records internal `NOT_SENT` and a blocked outbox,
  not a false provider rejection. Previously unknown submissions remain `UNKNOWN` and are
  reconciled without resending; actual provider rejection retains its existing meaning.
- Provider projection now deserializes the existing canonical `ConversationTextBlockV1`
  with unmapped members prohibited and rejects duplicate properties, wrong schema, non-TEXT
  blocks, missing type and media/unknown fields before protected reads, reservation or egress.
  Five new negative cases reproduced the prior attempted HTTP path and now prove zero sends
  and zero reservations. No parallel conversation DTO, history, business API or engine was added.

WhatsApp still enters the existing `ConversationService.SendAsync`; outbound work reads the
existing canonical messages and conversation outbox. Customer Portal Web and future Mobile
retain the same conversation contract, authorization, idempotency, history and evidence.
`NOT_SENT` is internal provider-observation evidence, not a new public message-state enum.

Executed Docker validation:

```bash
sh scripts/validation_control/run_wc120_dotnet_test.sh -warnaserror \
  --settings tests/coverage.runsettings --collect:"XPlat Code Coverage" \
  --results-directory /workspace/test-results/whatsapp/canonical-guard-coverage \
  --logger "console;verbosity=minimal"
PYTHONPATH="$PWD:$PWD/scripts" pytest -q tests/validation_control tests/pipeline tests/contract
PYTHONPATH="$PWD:$PWD/scripts" pytest -q \
  tests/validation_control/test_catalog_contract.py \
  tests/validation_control/test_runner_contracts.py \
  tests/validation_control/test_runner_supply.py \
  tests/validation_control/test_gate_equivalence.py
```

Results: **PASS, BP 1,202 passed, zero failures/skips; coverage 90.45% lines / 80.17%
branches**. Full Python closure: **2,619 passed**. Subsequent runner/catalog/supply/equivalence
selector closure: **134 passed**, including a new regression proving the added tests occur in
the qualification plan and actual release tests lane. The `quality:scripts` and release test
selectors now execute these relevant prerequisite regressions rather than merely collecting
them during an ad hoc local run.

CSharpier checked 136 affected source/test files; affected Python Ruff/format checks pass.
The rebuilt full runner does not contain actionlint; that attempted invocation failed visibly.
The existing pinned `rhysd/actionlint:1.7.7` image then passed
`-color -shellcheck= .github/workflows/ci.yaml`; shellcheck is not claimed.
`sh -n scripts/run_release_qualification.sh` passes. Only the exact synthetic institutional
records and `src/test/File.cs` generated by the broad Python suite were removed.

These are dirty-candidate diagnostic results, not release, deployment or provider acceptance.
Admitted activation input/authority wiring, the complete CE-FIT/privacy/recovery closure,
clean exact-head evidence, final author review, commits and the Founder-review PR remain.
Protected Meta values, trusted-main deployment, separate bounded traffic authority and
activation evidence are still absent; all production provider defaults remain off.

### 10.10 Protected Activation Preparation And Author Qualification Repairs (2026-11-02)

The Founder directed continued engineering and PR creation, with actual Meta configuration
information to follow the PR. No protected values are required to qualify the inactive source
candidate. Live S09/S12-S15 acceptance remains pending those inputs and the trusted-main release.

`scripts/wc120_whatsapp_activation.py` is a separate protected-operator preparation entry point.
It is not invoked by ordinary deployment and does not approve evidence or mutate Azure. It
requires the exact bundle digest from an independent Founder decision; deriving a digest from
one's own document is not authorization. The approved bundle must contain:

- Schema `waooaw.demo-whatsapp-activation/v1`, the registration configuration digest, and the
  existing `WhatsAppActivationAuthority` fields, with distinct activation/traffic references,
  exact release/catalog/rollback digests, canonical tenant, admitted recipient, UTC window,
  positive bounded count/rate and six-decimal conservative spend/cost limits.
- `binding_digests`: `AppBindingDigest`, `WabaBindingDigest`, `RecipientBindingDigest`.
  The last is the existing provider sender Phone Number ID digest, not a new recipient identity.
  The authority's recipient digest separately names the canonical consenting contact binding.
- `policies`: the current `PolicyVersion`, `InstitutionalPolicyVersion`,
  `InteractionPolicyVersion` and `ChannelRenderingPolicyVersion`.
- One to sixteen approved BODY-only template projections using existing
  `Name`, `Version`, `Locale`, `Category`, `Body` fields, with no duplicate identity.
- `prerequisites`: independently accepted qualification, zero-traffic deployment, provider
  registration, credential-scope, consent, Stop, alert, rollback and pricing receipts. Each
  includes its opaque reference, exact digest and expiry covering the whole activation window.

The runtime configuration digest binds the registration configuration, provider account/sender
digests, current policy versions and complete template inventory using the preparer's deterministic
sorted JSON representation. A changed policy/template or pinned secret version therefore cannot
reuse the old configuration tuple. The preparer reuses the registration validator and recomputes
the current catalog binding. It emits only existing BP runtime configuration keys, never tokens,
App Secret, telephone values or raw provider IDs. Output is mode `0600`, create-only; denials do
not echo private input. The operator invocation, only after independent exact approval, is:

```bash
python scripts/wc120_whatsapp_activation.py \
  --bundle PRIVATE_APPROVED_BUNDLE \
  --approved-digest EXACT_DIGEST_FROM_FOUNDER_DECISION \
  --deployment-inputs PRIVATE_REGISTERED_TFVARS \
  --output PRIVATE_CREATE_ONLY_RUNTIME_SETTINGS
```

The protected deployment/configurator must independently verify the referenced receipts,
current nonrevocation, alert/Stop health, effective cloud/provider permissions and the exact
target revision before admitting these settings. References and a digest are not cryptographic
proof that those external facts are true. This tool neither introduces a signer trust anchor
nor grants a new identity permission. The admitted settings require a separately authorized
same-image revision/configuration change; the normal Terraform registration path still forces
callback acceptance, dispatch and provider availability off. At expiry/revocation runtime gates
fence effects. Late callbacks and unresolved work remain quarantined for authorized reconciliation;
they are never implicitly accepted or blindly resent after authority closes. Live revocation,
rollback and teardown evidence is still mandatory and is not claimed from this preparer.

Author review reproduced a runtime gate accepting the same record as both activation and traffic
authority (`ACTIVE` instead of `BLOCKED`); the runtime and preparation path now both reject this.
The final BP Docker regression remains **1,202 passed, zero skips**, including the negative;
measured coverage is **90.48% lines / 80.17% branches**.

Author review also found that the existing WC-120 qualification helper synthesized a test count
from exit status, overwrote three .NET selectors with browser output, and asserted a release
qualification waiver without reading an authority record. Those validation defects are corrected:

- Actual TRX/JUnit counters are required; zero executed tests, hidden failures or skips cannot
  qualify. Browser support retains separate reports alongside primary .NET selectors.
- Exact source commit, actual report counters, runner image identity and artifact hashes are
  revalidated before the candidate manifest. Required missing inputs and stale/failed summaries
  fail closed. Migration 61 is included in the schema binding.
- Runner image IDs are frozen before execution; consumers use `--pull never` against those
  already inspected local images. Section 10.11 records the actual Compose CLI correction.
  Separate release qualification is explicitly pending, with no invented Founder waiver.
- The bounded XML report parser rejects DTDs before entity declarations; UTF-8/UTF-16 negative
  tests prove rejection. The local Ruff S314 annotation documents this tested custom target
  rather than adding an unnecessary XML dependency.

Final expanded Docker closure:
`PYTHONPATH="$PWD:$PWD/scripts" pytest -q tests/validation_control tests/pipeline tests/contract`
passes **2,689 tests**, followed by scripts Ruff and affected-file formatting. New activation and
evidence regressions are wired into the actual release tests lane and protected by its selector
regression. This remains diagnostic evidence until the clean commit is qualified. No live provider
configuration, credential use, cloud mutation, deployment or activation is claimed.

### 10.11 Signed Milestone And Actual Compose Consumer Verification (2026-11-02)

Signed implementation milestone `43ccfed9` passed all seven staged prechecks and C-059.
The first hook run correctly rejected two files formatted differently by the authoritative
Python runner; that runner formatted only those files and 125 related regressions passed.
The approved local environment supplied GitHub authentication and signing without credential
printing, copying or persistence. No login/device flow, reviewer identity or unsigned-commit
exception was used.

The first clean-candidate qualification attempt exposed an introduced command defect:
Compose `run` supports `--pull never` but not `--no-build`. The qualifier and three persistent-state
CI commands now omit the unsupported flag. No consumer build is introduced: the supply action
verifies an existing immutable image, the qualifier freezes inspected local image IDs, pulls
are forbidden, and no `--build` option or consumer `build` subcommand is permitted. The earlier
Section 10.8 source-only assertion of `--no-build` is superseded by this runtime observation.

Actual proof: the pinned .NET image executed `dotnet --version` through the corrected Compose
command; both persistent-state negative tests executed through the corrected real consumer
syntax and passed. Runner-supply, qualification-evidence and catalog-selector regressions pass
119 tests; affected Ruff/format, pinned actionlint and Bash syntax checks pass. Clean-candidate
qualification is retried after this correction. No unsuccessful selector is represented as
passing, and no cloud/provider action or live acceptance is claimed.

### 10.12 Meta Setup, Vault Intake, And Deployment Status (2026-11-02)

**Current status: ENGINEERING MERGED; META SETUP PARTIAL; DEPLOYMENT FAILED;
WHATSAPP NOT ACTIVATED.** This checkpoint supersedes earlier pending-PR statements, not
the independent provider, traffic, activation, authentication or rollback gates.

PR [#574](https://github.com/dlai-sd/waooaw-platform/pull/574) merged as
`b8c563b2adff73affb7344309245af9d688af293`. Before merge, exact source candidate
`8bb63679a3aa2a79f5dff8eff11010d0653a3ec5` passed all 16 primary CE-FIT selectors
without failures/skips, 15 separately retained browser cases, 96 targeted BP tests, 14
recovery/contract tests, the complete BP suite (1,202 passed, zero skips), complete contract
suite (32 passed), and Web (719 passed, three existing skips). Final browser repetition
passed 15 cases. The BP image built; the independent real-container lifecycle gate passed
`503 -> 200 -> 503 -> 200`. All seven exact-head prechecks and mandatory PR preparation
passed. This evidence does not establish a successful deployment or live Meta acceptance.

#### Meta operator progress

The following are Founder-reported dashboard observations, not independently authenticated
Graph API verification. Raw telephone numbers, secrets, OTPs, recipient identity and protected
provider-binding values are deliberately not copied into this record.

| Setup item | Recorded status |
|---|---|
| Messaging application | Existing `WAOOAW Messaging Service`; Founder reports Published. `WAOOAW Customer Login` was not selected for messaging access. |
| Public legal settings | Privacy `https://cp.demo.waooaw.com/privacy`, terms `https://cp.demo.waooaw.com/terms`, deletion instructions `https://cp.demo.waooaw.com/data-deletion` are publicly reachable. App domain `cp.demo.waooaw.com` was added; Founder reports settings saved. The earlier suggested privacy fragment was invalid and is not the deletion URL. |
| Real sender | Existing business account and registered sender identified separately from Meta's test account; Manager reports Connected and shows the business display name. Founder explicitly confirmed this sender is dedicated to WAOOAW Demo. |
| System user | `WAOOAW Demo Integration`, Employee access, created. Refresh confirmed two assigned assets; the earlier empty list was stale. |
| App asset permission | `WAOOAW Messaging Service`: Partial access, Develop app / View insights / Test app shown by Meta. No Manage app assignment requested. |
| WhatsApp asset permission | Dedicated business WhatsApp account: Phone numbers (view only) and Messages. No Everything or number-management assignment requested. |
| Messaging token | Founder confirmed `whatsapp_business_messaging` selected. A 60-day expiry was recommended but not independently confirmed. Token generation was paused; no token value was received, stored or tested by this session. |
| Webhook | Callback URL, private verify token, event subscription and account subscription remain pending. No client-certificate option was enabled by this session. |
| Other gates | Business-verification result, billing readiness and approved-template inventory are not yet verified. Voice/media/scanner authority remains disabled and unprovisioned. |

Meta's label "Production setup" means a real business sender rather than its test sender.
It is not WAOOAW Production-environment authority. Publishing the Meta app alone does not
activate WAOOAW, admit recipients, grant traffic, or prove webhook delivery.

#### Remaining protected inputs and source locations

| Input / evidence | Source / next requirement |
|---|---|
| Exact app, WABA and Phone Number IDs | Existing Messaging Service / WhatsApp production setup and [WhatsApp Manager](https://business.facebook.com/latest/whatsapp_manager/phone_numbers/). Values already shown by the Founder must be transferred into the protected binding, not confused with the test account. |
| Supported Graph API version | Confirm against the app's API setup and accepted provider configuration; do not infer it from unrelated Meta integrations. |
| System-user messaging token | [Business Settings: System users](https://business.facebook.com/settings/system-users). Generate only after approved no-echo vault intake is available; confirm expiry and the selected app/account/scope. Store under `whatsapp-outbound-authority`, separately from App Secret and verify token. |
| App Secret | Messaging Service, App settings / Basic; protected intake into `whatsapp-app-secret`, never chat, screenshots, source, PR body or command arguments. |
| Verify token and callback | Private operator-held verification token into `whatsapp-verify-token`; exact dedicated Demo callback DNS/TLS and GET challenge must be deployed and verified before subscription. Do not substitute the Customer Portal URL as the callback. |
| Provider binding | Closed document in `WhatsAppProviderBinding`: Demo environment, binding version, app/WABA/sender IDs, API version, consenting recipient and digest, authority reference, validity window. Store under `whatsapp-provider-binding`. |
| Templates and traffic authority | Approved BODY-only templates with locale/category/version, consenting canonical recipient, separate activation and traffic decisions, exact time window, count/rate/spend/cost bounds, Stop/alerts, pricing, rollback and teardown receipts. |
| Secret admission | Exact enabled versions, validity/expiry metadata, proper workload scopes and current nonrevocation; no placeholder or media token to satisfy ordinary deployment. |

#### Existing reusable Key Vault uploader: reuse decision and limits

Located the existing unchanged uploader
[`scripts/wc091_secret_provision.py`](../scripts/wc091_secret_provision.py), backed by
[`secret-catalog.json`](../infrastructure/environment-readiness/secret-catalog.json).
It takes a catalog logical ID, `--environment demo`, and an approved `FA-` authorization
identifier. It checks version metadata first, preserves an existing version without reading
its value, accepts a missing external secret through `getpass`, and sends the REST body on
stdin (`--body @/dev/stdin`), not in process arguments. It prints only logical ID, version
and CREATED/PRESERVED status. No replacement uploader or batch utility was created.

**Reuse decision:** reuse this uploader unchanged for initial upload of missing catalog
entries through the authorized private operator path. It is not a complete WhatsApp admission
or rotation utility: existing versions are preserved, JSON binding semantics are not validated,
and PUT supplies only `value`, not expiry/not-before attributes. The WhatsApp runtime explicitly
requires an enabled, unexpired `exp` attribute. Therefore an approved metadata-setting and
validation step is still required before version pinning/activation; running the uploader
alone is insufficient. No claim of end-to-end provisioning or live use is made.

Executed existing uploader regressions in the Docker runner:

```text
PYTHONPATH=/workspace:/workspace/scripts pytest -q \
  tests/pipeline/test_wc091_environment_readiness.py::test_secret_provisioning_preserves_existing_version_without_reading_value \
  tests/pipeline/test_wc091_environment_readiness.py::test_external_secret_value_uses_stdin_body_not_command_arguments \
  tests/pipeline/test_wc091_environment_readiness.py::test_az_secret_body_is_read_from_stdin
PASS: 3 tests; mocked transport, not live vault writes.
```

Read-only Azure CLI inspection confirmed `kv-waooaw-demo`, RBAC enabled and public network
access Disabled. The current CLI identity's metadata lookup returned `ForbiddenByRbac`
(`secrets/readMetadata/action`, assignment not found). This proves an RBAC blocker; it does
not prove that a subsequently authorized identity has a working private network path.
No role grant, network bypass, secret upload, token generation or credential rotation was
performed. Next operator step is to identify the approved provisioning identity/private
execution path, not enable public access or grant the runtime broad vault administration.

#### Failed deployment evidence and proposed repair (not implemented)

[Environment Deployment run 41482319765, job 125405558629](https://github.com/dlai-sd/waooaw-platform/actions/runs/41482319765/job/125405558629)
used merged commit `b8c563b2adff73affb7344309245af9d688af293`.

| Finding | Evidence | Proposed correction |
|---|---|---|
| Primary: optional WhatsApp secrets become unconditional deployment prerequisites | Step 26, Check credential inventory, failed at 16:38:48 UTC: `Required external credential whatsapp-provider-binding is missing`. `required_external_credentials` selects every Demo `external-operator` / `founder-key-vault-admin` entry without considering capability admission. Reproducing the selector with web sessions disabled includes all five WhatsApp entries, including the deliberately unprovisioned media authority. | Select conditional secrets using typed effective capability/configuration authority, not human-readable `requiredWhen` prose. Disabled WhatsApp must not block an ordinary deployment. Registration/callback/outbound gates must each fail closed on their admitted required versions; media stays absent unless its separate scanner boundary is admitted. Preserve unrelated required credential checks. Add enabled/disabled/missing/media-negative execution regressions. |
| Secondary: finalizer assumes a provisioner exists after earlier failure | Create and Run WC-124 database provisioner (steps 32/33) were skipped after inventory failure. Step 36 still ran because its condition is `always()`, foundation success and `handoff_required`; it failed at 16:38:49 UTC with ResourceNotFound for `job-demo-wc124-db-provisioner`. | Bind handoff to actual provisioner availability and recorded authority/transition progress. Do not run a job-dependent finalizer before creation; preserve terminal revocation/zero-authority checks whenever privileges were actually acquired, including partial failures. Add the pre-creation-failure regression rather than suppressing cleanup errors. |

The ordinary credential gate regression is introduced by this delivery's catalog integration,
not caused by the Founder delaying token generation. Fabricated secrets or enabling media would
hide the defect and violate the default-off contract. The local CLI RBAC denial is a separate
operator-intake blocker: the private deployment runner reached a specific SecretNotFound result.
Independent deployment verification was skipped; no successful new workload deployment, Demo
activation, webhook subscription or external traffic is claimed. Implementation repair and a
new controlled deployment remain proposed, not executed in this documentation checkpoint.
