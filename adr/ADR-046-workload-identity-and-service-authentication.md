# ADR-046: Workload Identity and Service Authentication

**Status:** ACCEPTED - R-066 conditions satisfied; R-067 approved with no conditions
**Date:** 2026-08-10
**Decision owner:** INST-004 - Enterprise Architect
**Goal / Work Contract:** GOAL-005 / WC-034 F4, Amendment 4 Order 1
**Authorization:** [GOA-GOAL-005-INST-004-09](../goals/GOAL-005-execution-plan.md#goa-goal-005-inst-004-09), accepted by [ACC-GOAL-005-INST-004-09](../goals/GOAL-005-execution-plan.md#acc-goal-005-inst-004-09)
**Contribution evidence:** [CR-GOAL-005-INST-004-10](../goals/GOAL-005-f4-workload-identity-contribution.md)
**Learning evidence:** [LR-GOAL-005-INST-004-06](../goals/GOAL-005-f4-workload-identity-learning.md)
**R-066 repair evidence:** [CR-GOAL-005-INST-004-11](../goals/GOAL-005-f4-workload-identity-repair-contribution.md) and [LR-GOAL-005-INST-004-07](../goals/GOAL-005-f4-workload-identity-repair-learning.md)
**Independent review evidence:** [R-066](../reviews/R-066-wc034-f4-adr046-business-review.md) and [R-067](../reviews/R-067-wc034-f4-adr046-constitutional-review.md)
**Constitutional basis:** C-001, C-002, C-003, C-005, C-006, C-008, C-023, C-026, C-031, C-032, C-063, C-065, C-083, C-084, C-085; capabilities 6.1-6.4; AD-002, AD-004, AD-008, AD-009, AD-010; DP-001, DP-002, DP-006, DP-007, DP-010
**Accepted decisions preserved:** [ADR-007](ADR-007-grpc-mtls-certificates.md), [ADR-014](ADR-014-secret-management.md), ADR-001, ADR-003, ADR-004, ADR-009, ADR-010, ADR-018, ADR-031, and ADR-034

## 1. Status And Decision Boundary

This ADR is Accepted. INST-003 approved it through R-066 subject to two conditions, INST-004 repaired both conditions prospectively, and fresh INST-002 approved the repaired decision through R-067 with no conditions. INST-013 recorded the resulting status mechanically and did not author, repair, or independently accept the decision.

This decision governs workload identity and mutual service authentication for:

- Business Platform (BP) to WAOOAW Billing Engine (WBE);
- BP to Professional Runtime (PR); and
- BP to an approved professional/domain adapter implementing the generic Relationship Workspace adapter role.

It does not create a new deployable component, public endpoint, ledger surface, provider connection, or browser credential. BP remains the sole ordinary public F4 facade and public relationship-governance projection owner. WBE remains the commercial-truth authority. PR remains the professional-execution-truth authority. Constitutional Engine (CE) remains the constitutional validation, authority-licensing, and constitutional-evidence authority. Professional/domain adapters remain private semantic contributors. Web has no direct access to WBE, PR, CE, adapters, providers, or ledgers.

BP-to-CE and PR-to-CE remain governed by accepted ADR-007. This ADR neither silently amends ADR-007's route scope nor represents ADR-007's plain development transport as sufficient for the new F4 routes. A future proposal to bring older CE routes to the parity model below requires separately authorized ADR reconciliation.

This ADR does not resolve F4-POL-01 through F4-POL-06, close executable G-F4-10, authorize canonical OpenAPI changes or generated clients, authorize implementation or provider activation, authorize deployment, or expand into F5-F8.

## 2. Context

The approved F4 architecture requires BP to compose private WBE, PR, CE/evidence, and professional/domain truths into one relationship-bound public projection. R-064 condition EA-F4-01 found that accepted ADRs do not define workload identity and mutual authentication for BP-to-WBE, BP-to-PR, or BP-to-domain-adapter traffic across development, CI, and cloud.

ADR-007 authenticates selected CE gRPC routes with managed cloud mTLS but explicitly permits plain gRPC on the development Docker network. ADR-014 defines where secrets are stored; it does not make a secret an identity or choose a service-authentication protocol. Network location, a shared secret, a caller-provided header, or possession of a relationship identifier cannot prove which workload made a request or whether that workload may invoke the target operation for the stated audience.

F4 therefore requires one environment-parity architecture that authenticates both peers, binds the caller to an explicit target audience and route policy, carries narrowly delegated BP context without treating that context as authority by itself, and fails closed without placing CE on the authentication path.

## 3. Decision

Every governed route in this ADR uses mutually authenticated TLS in development, CI, and cloud. Each workload receives a unique asymmetric identity from an environment-scoped trust root. Identity is expressed as an exact SPIFFE-style URI SAN, not a certificate Common Name pattern. The same identity, audience, route-policy, delegated-context, expiry, and failure semantics apply in every environment.

BP sends a short-lived, asymmetrically signed delegated-context envelope on each authenticated call. The target accepts the envelope only after it authenticates BP from the mTLS peer certificate, verifies that the envelope issuer is the same authenticated BP workload, verifies its own exact audience and requested operation, and rebinds every delegated claim to its own authorized relationship or resource context. The envelope is context, not an independent bearer authority.

### 3.1 Trust Domains And Workload Identities

Each environment has a cryptographically separate trust domain and root:

| Environment | Trust root and issuance source | Leaf handling | Permitted difference |
|---|---|---|---|
| Development | An ephemeral local root and intermediate generated by the approved bootstrap harness for one developer environment | Harness issues distinct BP, WBE, PR, and selected-adapter certificates; keys live only in restricted ephemeral files or memory and expire within 24 hours | Root is local and ephemeral; identity and policy semantics are identical to cloud |
| CI | A new ephemeral root and intermediate generated inside each isolated CI run by the approved test harness | Per-run workload certificates expire at run end and no later than two hours after issuance; keys and root are destroyed with the runner | Root lifetime is tied to one run; no repository or GitHub shared secret is a trust root |
| Cloud | A separate private root and intermediate for each environment, with certificate source and access controlled through that environment's Azure Key Vault under ADR-014 | Per-workload certificates are delivered only to the named workload through managed identity and approved Container Apps certificate/secret references; private key material is never committed or shared | Azure custody and automated issuance replace the ephemeral harness; protocol and authorization semantics do not change |

Trust domains use the form `spiffe://waooaw.<environment>/workload/<workload-name>`. The initial exact identities are:

- `.../workload/business-platform`;
- `.../workload/billing-engine`;
- `.../workload/professional-runtime`; and
- `.../workload/domain-adapter/<approved-adapter-id>`.

The environment label and trust bundle must match the target environment exactly. No root, intermediate, leaf, signing key, or identity is shared across development, CI, QA, UAT, or production. Wildcard URI SANs, DNS-only workload identity, generic certificate-CN matching, and substring or regular-expression trust-domain acceptance are prohibited.

### 3.2 Protocol, Transport, And Peer Authorization

- REST traffic uses HTTPS; gRPC uses HTTP/2 over TLS. TLS 1.3 is preferred and TLS 1.2 is the minimum permitted version.
- Both caller and target present certificates chaining to the environment's approved trust bundle.
- The target validates chain, validity, key usage, revocation state, exact URI SAN, exact trust domain, exact intended server audience, and route authorization before reading protected request content.
- BP validates the target's exact URI SAN and service audience. A certificate valid for PR cannot authenticate WBE or an adapter.
- Plain HTTP, plaintext gRPC, opportunistic TLS, trust-on-first-use, and an authentication-disabled development or CI mode are prohibited.
- Certificate possession authenticates a workload identity only. An allowlisted policy must also authorize that exact caller identity for the exact target audience, method/route family, operation, and supported contract major.

Initial audiences are logical, environment-independent identifiers:

| Target | Exact audience | Initially permitted caller |
|---|---|---|
| WBE | `urn:waooaw:service:billing-engine` | BP only for approved Relationship Workspace commercial projection and command families |
| PR | `urn:waooaw:service:professional-runtime` | BP only for approved Relationship Workspace execution projection and control families |
| Domain adapter | `urn:waooaw:service:domain-adapter:<approved-adapter-id>` | BP only for approved adapter projection, goal-validation, and command-reconciliation families |

An adapter identity and audience are registered explicitly. A generic "any domain adapter" audience or route grant is prohibited. A workload cannot use its certificate to call another private owner, query a ledger, impersonate BP, or obtain tenant-wide access.

### 3.3 Signed Delegated-Context Envelope

For each call BP creates a canonical, versioned envelope containing only:

- envelope schema version and signing-key identifier;
- issuer workload URI, exact target audience, target operation and route/method binding;
- authenticated actor subject and effective role derived by BP from the validated customer session, never copied from a caller-provided authority header;
- server-derived tenant identifier and independently authorized Employment Relationship identifier;
- declared purpose, subject/resource reference, and applicable scope, authority, lifecycle, assurance, evidence, owner-projection, and contract versions;
- command or read identity, idempotency key where applicable, canonical request-body digest, and expected source versions;
- issued-at, not-before, expiry, unique envelope ID, and correlation/trace identifier.

BP signs the canonical envelope with a workload-specific asymmetric delegation key whose certificate chains to the same environment trust domain and whose key usage is separate from ordinary TLS server use. Envelopes expire no more than 60 seconds after issuance. The target validates the signature and exact canonicalization rules before using any claim.

The target must then rebind the envelope to the authenticated connection and target-owned truth:

1. the envelope issuer URI must equal the mTLS caller URI exactly;
2. the audience, operation, method/route, body digest, envelope version, and contract major must match the received call;
3. the tenant and relationship must be authorized by the target's own relationship/resource mapping for the requested owner operation;
4. actor, role, purpose, scope, authority, lifecycle, assurance, and expected versions must be sufficient for that operation under target policy; and
5. any target-owned resource, commercial, execution, or domain state must independently match before access or mutation.

The envelope is not a customer token, capability token, approval, scope-boundary confirmation, CE permit, evidence record, or proof that an operation succeeded. It cannot create tenant, relationship, role, authority, billing, execution, domain, or constitutional truth. Caller-provided `tenant`, `relationship`, actor, role, purpose, operation, version, or similar headers never override BP-derived context and are not accepted as authority.

### 3.4 Authentication Is Not Constitutional Authorization

Service authentication is decided locally from the verified certificate, trust bundle, audience, route policy, envelope signature, and target rebinding. CE must not be called to authenticate a workload, validate a TLS connection, issue a certificate, or validate the delegated envelope. Requiring CE for authentication would create a circular dependency and could couple ordinary private transport, recovery, and Emergency Stop to CE availability.

After service authentication succeeds, the owning business operation still invokes CE when its approved constitutional flow requires `ValidateAction`, authority licensing, or `RecordEvidence`. ADR-031 fail-safe behavior and DP-001 Evidence First continue to apply. Successful mTLS or envelope validation never substitutes for CE authorization or evidence.

## 4. Credential Lifecycle

### 4.1 Issuance And Storage

- Issuance requires an approved workload registry entry containing exact trust domain, URI SAN, audiences, route grants, key usages, owner, and environment.
- Development and CI certificates are generated only by the approved bootstrap/test harness. A developer does not manually mint, export, exchange, or retrieve identity material from a password manager.
- Cloud certificates and delegation keys are environment-specific Key Vault assets under ADR-014. Managed identity controls which workload may receive or use each asset. No application-wide credential bundle exists.
- Private keys are non-shared and non-exportable where the platform supports in-place use. If a runtime requires key material, it is delivered only to that workload through a restricted memory-backed or platform certificate mount, never through source, images, logs, command arguments, general `.env` values, or reusable GitHub secrets.
- TLS and delegation signing use distinct key usages and preferably distinct leaf keys. A database password, HMAC value, API key, Keycloak client secret, GitHub secret, or developer credential cannot stand in for workload identity.

### 4.2 Rotation, Expiry, And Revocation

- Workload leaf certificates and delegation certificates have a maximum 24-hour lifetime in development and cloud and a maximum two-hour lifetime in CI.
- Renewal begins before two-thirds of the leaf lifetime. Old and new leaves may overlap only for the bounded renewal window and must carry the same registered identity and policy.
- Environment roots have a maximum one-year lifetime; intermediates have a maximum 90-day lifetime. Root rotation uses a maximum seven-day dual-trust window with an explicit old-root removal time. Trust is never broadened across environments during rotation.
- Targets consume signed, versioned trust bundles and route policies. An expired, unavailable, rolled-back, unknown, or unverifiable bundle fails closed.
- Revocation identifies both certificate serial and workload URI. Targets reject revoked credentials before expiry. Short leaf lifetime reduces exposure but does not replace revocation.

### 4.3 Compromise Response

On suspected compromise, the accountable platform/security owner must:

1. disable issuance and route grants for the workload identity;
2. revoke affected serials and delegation signing keys in the environment trust distribution;
3. fail closed at every target until a fresh trusted identity is issued;
4. rotate the workload's TLS and delegation credentials and, when CA compromise is possible, rotate the intermediate or root;
5. invalidate outstanding envelope IDs and reject envelopes signed by the compromised key even if unexpired;
6. preserve privacy-safe audit and observability evidence, identify affected correlations and owner operations, and reconcile idempotent outcomes; and
7. keep Emergency Stop independently reachable and keep affected F4 families `UNAVAILABLE` or `BLOCKED` until trust is restored.

No bypass credential, shared emergency secret, plaintext fallback, or temporarily trusted CN is permitted during recovery.

## 5. Failure, Privacy, Observability, And Stop

### 5.1 Fail-Closed Outcomes

The target rejects the call before protected lookup or mutation when certificate, trust domain, identity, audience, route, envelope, signature, expiry, replay, tenant, relationship, purpose, operation, body digest, policy, or version validation fails. Missing identity material makes the target unready and the dependent F4 family `UNAVAILABLE` or `BLOCKED`; it never enables anonymous service traffic.

Internal failures use stable classes such as `SERVICE_AUTHENTICATION_FAILED`, `SERVICE_AUTHORIZATION_DENIED`, `DELEGATED_CONTEXT_INVALID`, `DELEGATED_CONTEXT_EXPIRED`, `DELEGATED_CONTEXT_REPLAYED`, and `SERVICE_IDENTITY_UNAVAILABLE`. Responses include only a correlation identifier and retry/reconciliation safety where appropriate. They do not disclose whether a tenant, relationship, resource, workload registration, route grant, certificate serial, or private target exists. BP translates owner failures into the approved privacy-safe public RFC 9457 contract.

### 5.2 Observability

Each service emits structured OpenTelemetry events for certificate validation result, authenticated caller identity class, audience, policy version, envelope version, operation class, allow/deny reason class, credential age, rotation state, replay decision, latency, and correlation. Raw certificates, private keys, signatures, actor IDs, tenant IDs, relationship IDs, acknowledgement text, evidence payloads, and owner data are excluded from logs and metric labels. Security audit access remains environment-scoped under ADR-014.

Repeated denial, expired credentials, trust-bundle rollback, unexpected identity/audience pairs, replay attempts, rotation failure, or cross-tenant/relationship mismatch must alert the accountable operator without weakening the deny result.

### 5.3 Emergency Stop Independence

ADR-004 and ADR-018 continue to govern the dedicated Emergency Stop path. F4 service authentication must not route Stop through a workspace command, WBE, a domain adapter, workspace refresh, delegated-envelope issuance, or CE authentication. Credential rotation or failure on a governed F4 owner route cannot delay or disable Stop. PR and CE continue the accepted Stop and CE-unavailability behavior; this ADR adds no ordinary F4 dependency to that path.

## 6. Least Privilege, Confused Deputy, Replay, And Isolation

- Policy is default-deny and grants one caller, target audience, operation family, and contract major at a time. Reads do not imply commands; projection access does not imply ledger access; adapter access does not imply provider access.
- The target rejects an envelope for another audience, operation, route, body, adapter, tenant, relationship, purpose, or version even when its signature is valid. This prevents BP from becoming an unconstrained confused deputy and prevents a compromised downstream workload from replaying BP context elsewhere.
- Every envelope ID is single-use at the target until expiry. Replay state is scoped by caller identity, audience, envelope ID, operation, tenant, relationship, and request digest.
- For an idempotent retry, the client creates a fresh envelope and reuses the approved idempotency key. The target or owning service may return only the already recorded outcome when caller, tenant, relationship, operation, canonical request hash, and initial expected versions all match. It must not repeat the semantic mutation.
- A changed request under the same idempotency key is a conflict. An unknown outcome is reconciled by command identity before retry. Authentication success cannot convert `PARTIAL`, `UNKNOWN`, `BLOCKED`, `REJECTED`, or `UNAVAILABLE` into success.
- Cross-tenant, cross-relationship, wrong-role, wrong-adapter, wrong-audience, and inaccessible-resource requests are denied before protected existence disclosure and cause zero owner mutation, CE evidence claim, or public success.

## 7. Compatibility And Migration

### 7.1 Contract Impact

- BP public OpenAPI and generated web clients receive no workload credential, private audience, internal host, delegated envelope, tenant authority header, or private route. Browser behavior is unchanged.
- BP-to-WBE, BP-to-PR, and BP-to-adapter internal contracts gain a common versioned authentication profile and envelope schema. Their business payload and source ownership do not move.
- WBE retains actual, allowance, ceiling, forecast, threshold, pacing, commercial-consequence, and distinct `BLOCKED` truth. Authentication does not authorize BP to recompute or mutate WBE truth.
- PR retains execution truth and existing CE-governed execution behavior. Authentication does not transfer public governance or relationship authority to PR.
- Domain adapters retain domain outcome semantics only and require explicit identity/audience registration per adapter. No generic adapter credential is permitted.
- CE contracts are unchanged. BP-to-CE and PR-to-CE remain under ADR-007, and CE is not made an authentication dependency.

### 7.2 Migration Sequence

Future separately authorized implementation must migrate each route in this order:

1. publish the approved workload registry, exact URI SANs, audiences, operation grants, envelope schema, and trust-policy version;
2. issue distinct environment credentials and validate trust distribution without enabling F4 traffic;
3. configure targets to expose only the mutually authenticated listener and to reject plaintext and unknown identities;
4. validate BP against the exact target identity and run negative identity, audience, route, replay, tenant, and relationship checks;
5. enable the owner route only after parity evidence passes in development and CI, then in the separately authorized cloud environment; and
6. remove superseded listeners, credentials, trust entries, and temporary migration state before F4 activation.

There is no dual-mode plaintext fallback. If an existing route cannot cut over atomically, the dependent F4 capability remains `UNAVAILABLE` or `BLOCKED` until a separately approved migration design provides authenticated continuity. Existing F3 behavior is not silently changed by F4; any shared BP-to-PR transport migration must demonstrate backward compatibility and preserve existing contract outcomes before F4 is enabled.

Before each planned cutover, and for every credential incident, the migration or incident record must enumerate each affected F4 read or command family and any affected shared F3 BP-to-PR route. For every enumerated family or route it must name the accountable business owner, the planned or observed impact window, the customer-language `UNAVAILABLE`, `BLOCKED`, or unknown consequence, the status of customer rights and the independently governed Emergency Stop, and the privacy-safe support correlation and escalation path. It must preserve pending customer intent and every unknown outcome by command identity and owner version, then reconcile them without assuming that request acceptance or transport loss means either failure or success.

Restoration is owner-by-owner and family-by-family. The accountable WBE, PR, domain, BP, and, where applicable, CE owner must confirm its own authoritative state and consequence before BP republishes availability. Post-restoration evidence must prove that reconciliation exposed no duplicate mutation, cross-relationship state, lost customer decision, false success, or stale authority. Certificate validity, listener readiness, successful mTLS or envelope validation, request acceptance, technical completion, and evidence recording are necessary signals where applicable but are never sufficient restoration criteria. A family or shared F3 route remains `UNAVAILABLE`, `BLOCKED`, or honestly unknown until business-state reconciliation satisfies these criteria.

## 8. Alternatives Considered And Rejected

| Alternative | Decision and reason |
|---|---|
| Shared HMAC secret in development or CI, even if cloud uses certificates | Rejected. It changes the identity and compromise model by environment, cannot prove a unique asymmetric workload, encourages broad secret sharing, and makes parity evidence false. |
| Caller-provided tenant, relationship, actor, role, purpose, or operation headers as authority | Rejected. Callers can forge them. BP must derive context from authenticated server state, sign it, and targets must rebind it to authenticated BP and owner truth. |
| Plain HTTP or plaintext gRPC on an isolated development/CI network | Rejected for these routes. Network location is not workload identity, bypasses certificate/audience/replay tests, and repeats the gap identified in EA-F4-01. |
| Generic certificate-CN, wildcard SAN, DNS suffix, or pattern matching | Rejected. It authorizes unintended workloads and audiences. Exact environment trust domain, URI SAN, audience, route, operation, and contract policy are required. |
| CE call required to authenticate every service request | Rejected. Authentication is a local transport and policy concern; making CE a trust oracle creates circular dependency, couples availability, and risks Stop and fail-safe behavior. CE remains required only for constitutional operations that already require it. |
| Developer password manager or manual certificate ceremony as trust root | Rejected. Human handling is non-reproducible, unauditable as environment identity, and unsuitable for CI. The approved bootstrap/test harness and cloud issuance path are the only issuers. |
| Long-lived API keys, Keycloak client secrets, or OAuth client-credentials tokens as service identity | Rejected. They are bearer secrets, do not provide mutual transport authentication, and weaken route/audience binding and compromise containment. |
| One cross-environment root or one shared workload certificate | Rejected. Compromise crosses environment and workload boundaries and violates ADR-014 environment isolation. |
| Service mesh or new identity control-plane service | Rejected for this decision. The required properties are met with existing workload runtimes, approved harnesses, asymmetric PKI, and Key Vault; a new deployable component is not justified or authorized. |
| Trusting the signed delegated envelope without mTLS rebinding | Rejected. It turns context into a bearer token and permits replay or confused-deputy use from another workload. |

## 9. Consequences And Tradeoffs

### Benefits

- Development, CI, and cloud exercise the same authentication and authorization semantics.
- Every target knows the exact calling workload and intended audience before protected lookup.
- Tenant and relationship context remains server-derived, relationship-bound, purpose-limited, and independently revalidated.
- Compromise is contained by environment, workload, audience, operation, short lifetime, and revocation.
- CE remains authoritative for constitutional decisions without becoming an authentication availability dependency.
- BP public-facade, WBE commercial-truth, PR execution-truth, CE authority, private-adapter, browser, and ledger boundaries remain unchanged.

### Costs And Risks

- Local bootstrap and CI require deterministic CA/certificate generation and expiry handling.
- Cloud operation requires certificate issuance, trust-bundle distribution, renewal, revocation, and compromise runbooks using Key Vault-controlled assets.
- Targets require bounded replay state and exact canonical envelope verification.
- Short-lived credentials can make services unavailable when rotation fails. This is intentional fail-closed behavior and requires observable renewal margins.
- ADR-007 retains a different development rule for its existing CE routes. That known inconsistency is disclosed and cannot be repaired under this authorization.

## 10. Future Executable Evidence Obligations

No executable evidence is produced by this ADR. A later separately authorized implementation contribution must provide, at minimum:

1. deterministic bootstrap/test-harness evidence that fresh dev and CI roots issue unique short-lived BP, WBE, PR, and adapter certificates with exact URI SANs and no shared secret;
2. cloud configuration evidence for environment-separated private CA/certificates, Key Vault custody, managed-identity access, non-shared delivery, rotation, revocation, and audit access, without activating an unauthorized provider or deployment;
3. positive mTLS and exact server-identity tests for every authorized caller-target pair in development, CI, and the separately authorized cloud environment;
4. negative tests for plaintext, untrusted root, expired/not-yet-valid/revoked certificate, wrong environment, wrong URI SAN, CN-only identity, wildcard/pattern identity, wrong audience, wrong route, wrong operation, wrong contract major, and unregistered adapter;
5. envelope conformance tests for canonical signing, issuer-to-mTLS binding, target audience, method/route, body digest, actor source, tenant and relationship rebinding, purpose, operation, versions, 60-second expiry, key usage, and privacy minimisation;
6. confused-deputy tests proving that valid BP context cannot be used against another service, adapter, tenant, relationship, operation, body, purpose, or version;
7. replay and idempotency tests proving single-use envelope IDs, fresh envelopes for safe retries, same-hash prior-outcome replay, changed-hash conflict, unknown-outcome reconciliation, and zero duplicate mutation;
8. cross-tenant, cross-relationship, wrong-role, inaccessible-resource, and protected-existence tests with privacy-safe errors and zero WBE, PR, adapter, BP, CE, or ledger mutation;
9. issuance, renewal, overlap, expiry, trust-bundle rollback, revocation, workload-key compromise, intermediate/root rotation, and recovery tests, including fail-closed behavior when trust state is unavailable;
10. CE-unavailability evidence proving that service authentication remains locally decidable, governed writes still follow ADR-031 and Evidence First, and no CE call is made for TLS or envelope authentication;
11. Emergency Stop evidence proving that owner-route failure, credential expiry, rotation, revocation, WBE outage, adapter outage, or delegated-envelope failure does not delay or disable the dedicated Stop path;
12. OpenTelemetry and privacy scans proving useful identity/audience/policy/rotation/replay signals while excluding keys, certificates, signatures, actor, tenant, relationship, acknowledgement, evidence payload, private topology, and high-cardinality protected identifiers;
13. compatibility evidence proving unchanged BP public/generated-client surfaces, preserved WBE `BLOCKED`, preserved PR and CE behavior, explicit adapter registration, no browser/private-ledger access, and no plaintext fallback listener; and
14. a parity matrix demonstrating identical trust-domain, URI SAN, audience, route, envelope, authorization, expiry, error, replay, and isolation semantics across development, CI, and cloud, with only the approved root custody and issuance differences.

### 10.1 End-To-End Business-Operation Matrix

The future executable evidence package must include one row for every enabled BP-to-WBE, BP-to-PR, and BP-to-domain-adapter read family and command family; grouping is permitted only when the grouped operations have identical owners, constitutional obligations, state transitions, consequences, and public translations. Each row must identify the relationship-bound operation, accountable owner, read or command classification, expected business state and consequence, and executable proofs for all of the following links:

| Required proof link | Minimum executable proof |
|---|---|
| Authenticated transport | BP and the exact target mutually authenticate, and the envelope is bound to the correct audience, route, operation, relationship, purpose, body, and contract version. |
| Correct owner receipt | The designated WBE, PR, or registered domain adapter receives the request under its owner correlation and confirms that no other owner or BP substitute handled its truth. |
| Constitutional step where applicable | Every required CE authorization, authority-licensing, and Evidence First operation is confirmed in order; a non-applicable CE step is justified by the approved owner contract rather than omitted silently. |
| Owner-confirmed business state and consequence | The owner returns or records its authoritative state, source version, business consequence, and unresolved state; technical acceptance or completion is not used as a proxy. |
| BP public translation | BP preserves the owner meaning, including `UNAVAILABLE`, `BLOCKED`, `UNKNOWN`, `PARTIAL`, `REJECTED`, stale, disputed, or attribution-limited outcomes, through the privacy-safe public contract without recomputation or optimistic upgrade. |
| Final customer-visible state | The generated-client/browser path displays the same relationship, business state, consequence, rights or next action, and support-safe correlation in customer language. |

For every applicable matrix row, negative and partial cases must interrupt each link independently and prove the resulting owner and customer state. In particular, successful mTLS or envelope validation, request acceptance, technical completion, or constitutional evidence recording alone must never be presented or persisted as completed work, available authority, actual or available commercial truth, or an achieved business outcome. The matrix must prove zero false success when a later owner, CE, BP translation, or customer-visible step is denied, unavailable, partial, unknown, stale, disputed, or fails reconciliation.

### 10.2 Migration And Credential-Incident Evidence Matrix

The future package must also include planned-migration and credential-incident rows for every affected F4 family and any shared F3 BP-to-PR route. Each row must prove:

1. the accountable business owner and planned or observed impact window;
2. the customer-language `UNAVAILABLE`, `BLOCKED`, or unknown consequence, including which intended work, decision, commercial fact, or result is affected;
3. the continuing status of customer rights and the independently governed Emergency Stop;
4. durable preservation of pending customer intent and unknown outcomes by command identity, followed by owner-authoritative reconciliation before retry or completion;
5. a privacy-safe correlation exposed through BP and an accountable support-escalation path that does not reveal private topology, identity material, tenant, relationship, or owner data;
6. owner-by-owner restoration criteria for WBE commercial truth, PR execution truth, domain outcome truth, BP governance/public truth, and required CE authority/evidence state; and
7. post-restoration proof of no duplicate mutation, cross-relationship state, lost customer decision, false success, or stale authority.

Executable recovery must keep each family or route unavailable, blocked, or honestly unknown until those business states reconcile. Listener readiness, certificate renewal, successful authentication, request health, technical completion, or evidence presence alone cannot restore availability. Tests must include interrupted cutover, expiry, revocation, rotation failure, compromised TLS or delegation credentials, lost response after owner receipt, and partial multi-owner recovery, with restoration occurring independently only for families whose complete business-state criteria pass.

Static specification, fixture, integration, browser, deployment, and customer-proof evidence must retain their existing provenance labels and must not be conflated. Passing this future evidence would satisfy only the authorized implementation gate named by a later amendment; it would not resolve F4 policy defaults, authorize deployment, or prove customer outcomes.

## 11. Review And Acceptance Required

Order 2 requires an independent INST-003 review of capability coverage, operational continuity, customer-rights effects, and business-driver alignment. Order 3 requires a fresh INST-002 review of constitutional and claim traceability. Each review must publish its own authorized Contribution and Learning Records, state an explicit decision and exact conditions, and remain independent of this authoring context.

Until both reviews approve and every condition is satisfied, ADR-046 remains **PROPOSED** and EA-F4-01 remains open. No self-approval is claimed.