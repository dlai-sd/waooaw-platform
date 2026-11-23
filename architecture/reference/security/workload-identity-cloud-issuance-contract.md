# ADR-046 Cloud Workload Credential Issuance Contract And Implementation Brief

**Status:** PROPOSED - FOUNDER APPROVAL PENDING (implements ADR-046 Amendment 1, which is also pending; Part A clarifications are already in force)
**Date:** 2026-11-22
**Owner:** INST-004 Enterprise Architect (design); INST-010 Platform IT Expert (implementation, after a Work Contract is authorized)
**Closes:** blocker CB-021 (design gap); IB-147 (BP to WBE credential)
**Authority:** [ADR-046 Section 12](../../../adr/ADR-046-workload-identity-and-service-authentication.md); preserves ADR-007, ADR-014, ADR-034, ADR-045, ADR-047
**Constitutional basis:** C-031 (decision needs an ADR), C-059 (traceability), C-065 (author is not approver), C-067 (cost and revision preservation)

This is the single place where the next session finds what is decided, what is true today, and the ordered work. It adds no implementation. If this file and the ADR disagree, the ADR wins.

## 1. Evidence Review

### 1.1 Is there a prior "Azure-provided identity" decision?

Part of one. The records are:

| Record | What it actually decides | Does it deliver the capability? |
|---|---|---|
| ADR-046 line 53 and 119 (accepted 2026-08-10) | Cloud trust is a per-environment private root and intermediate under that environment's Key Vault, delivered by managed identity; "Azure custody and automated issuance replace the ephemeral harness" | No. It states the intent and the custody. It does not name an issuer, a renewal job, a delivery or reload mechanism, or a listener exposure. |
| `goals/GOAL-005-f4-workload-identity-contribution.md` line 32 | Same intent as a contribution item | No |
| ADR-007 (2026-07-07) | Container Apps managed peer-to-peer mTLS, "certificates rotated automatically", for CE gRPC routes only | No. It is not enabled in any `infrastructure/terraform/**` file (no `mutual_tls`), exposes no per-workload SPIFFE identity to the application, and does not cover BP to WBE or PR. This is the most probable origin of the belief that Azure already provides it. |
| `azure-deployment-topology.md` line 968; PR #510 "Bind Demo Azure managed certificates" | Azure Container Apps managed certificates (Azure holds keys and renews) for public domains `cp.`, `api.`, `auth.demo` | No. These are public ingress TLS certificates, not workload identity. |
| CB-021 (2026-11-16) and `PROJECT_STATE.md` line 151 | State that issuance, private-key delivery, the listener and the BP link are "undesigned" and the cloud issuance design is open | Confirms the gap |
| Last 25 merged PRs (#590-#614) | Contain only PR #596 "Give Demo Professional Runtime public ADR-046 trust material (interim)" and unrelated work | No issuance, renewal or delivery implementation exists |

Conclusion: the decision that exists is "Azure Key Vault custody plus managed identity plus automated issuance". The automated issuance design and its implementation were never produced. Nothing was agreed or built that Azure issues workload certificates on its own, and Azure has no managed private-CA service that does.

### 1.2 Facts supplied for this review

| # | Claim | Verdict | Evidence and correction |
|---|---|---|---|
| 1 | Services use shared secrets in Key Vault; BP calls WBE with `X-Ops-Token`; Demo BP has no `BillingEngine__*` | TRUE | `modules/workload/main.tf:627-634`; `src/business-platform/Program.cs:269-281`. The ops-token path is pre-F4 and outside ADR-046's governed set (ADR-046 Section 3.2 table), so Part A item 3 freezes it. Wiring it on Demo is a separate Work Contract and is not required for pricing. |
| 2 | Pricing admin was built only for ADR-046; shared token cannot prove actor, role or step-up; the Platform IT Expert's withdrawal is correct | TRUE, CONFIRMED | `AuthenticatedPricingAdminGateway.cs` signs the 60-second envelope; `src/billing-engine/pricing_admin.py:285-330` requires the mTLS peer certificate and the Bearer envelope and derives role and step-up purpose only from the verified envelope. A shared token is a bearer secret with no actor claim, so any ops-token path would let anyone holding the secret assert the Founder step-up. ADR-046 Section 3.3 and Section 8 and CB-021 forbid it. The reasoning holds; the ops-token route is rejected permanently (ADR-046 12.1 item 1-2). |
| 3 | Program.cs registers Unconfigured gateways; nothing in Terraform wires `WAOOAW_WORKLOAD_CREDENTIALS` for BP or Billing; Demo shows 503 | TRUE | `Program.cs:226-240, 255-265, 392`; `main.tf:574` sets it for Professional Runtime on Demo only. |
| 4 | Only Demo PR has interim public trust material; no private key delivered; listeners exist but are not run or exposed | TRUE | `main.tf:651-667`; `src/billing-engine/private_server.py:14-24` (port 5444), `src/billing-engine/Dockerfile:34-35` and `src/professional-runtime/Dockerfile:23-24` run only `uvicorn`. The `azurerm_container_app` ingress supports one `target_port` (`main.tf:1520-1522`) and the provider lacks additional port mappings, so exposure needs an `azapi` overlay. |
| 5 | Verifiers enforce certificate validity | PARTLY TRUE | Only the mTLS peer certificate is checked for validity (`src/billing-engine/workload_identity.py:89`, `src/professional-runtime/workload_identity.py:117`). The BP delegation certificate is read as a bare public key with no chain, validity or key-usage check (`src/billing-engine/relationship_workspace.py:90-112`, `src/professional-runtime/relationship_workspace.py:359`). This is an ADR-046 Section 3.3 and 4.2 conformance gap, and it is why PR "ignores" the delegation cert expiry. Because the delegation public key is a single static value, a 24-hour delegation certificate cannot rotate until verifiers accept a set of keys and validate chain and validity. |
| 6 | Credentials load once; Container Apps refresh behavior unverified | TRUE | `WorkloadIdentityClient.Load`, `relationship_workspace.py` `from_credentials`, private listeners read files at start. Microsoft documents that a changed Key Vault reference restarts revisions that use it as an environment variable and does not promise in-place refresh of mounted secret files; ADR-014 line 82 describes read "at startup". Design therefore must not depend on platform refresh. |
| 7 | Static bundle fails closed on 2026-12-16 | TRUE for peer certificates, with a nuance | PR and WBE reject an expired peer leaf; the PR/WBE delegation public key is never expired by the loader. Once BP receives a private bundle, every BP leaf has a not-after. A 30-day static leaf means a calendar-date outage; the design rejects any static credential. |

### 1.3 Additional contradictions and gaps found

1. **Trust-domain text.** ADR-046 Section 3.1 says `spiffe://waooaw.<environment>/workload/<name>`; the registry (`infrastructure/workload-identity/registry.yaml` lines 6-20), the verifiers and Demo configuration use `<env>.waooaw.internal`. Resolved by ADR-046 12.2 D8.
2. **Lifetime policy.** The registry sets cloud leaves to 2, 2 and 1 hours, far below the 24-hour maximum. With no renewal automation this is an outage by design, and with a one-hour production leaf a 40-minute issuer fault stops production. Resolved by D3 (24 hours, renew at 8).
3. **Delegation-key identity.** The manifest carries one `delegation_key_id` per workload; rotation needs a set of valid keys with overlap (D4).
4. **ADR-INDEX omitted ADR-046** (and ADR-048). ADR-046 is now listed; ADR-048's omission is a pre-existing, unrelated gap left unchanged.
5. **ADR-014 says secrets are read at startup.** Rotating credentials need runtime reads; ADR-046 12.2 D4 defines this as the approved delivery for workload identity material only and does not change ADR-014 for other secrets.
6. **Allow decisions are not logged for pricing.** WBE logs `service_auth decision=allow` only for projection (`relationship_workspace.py:659`); pricing routes log only denials. The qualification needs positive evidence.
7. **ADR-046 Section 7.2 leaves legacy routes unclassified.** Resolved by Part A item 3.
8. **WBE readiness.** If WBE became unready on missing workload credentials, every non-F4 billing route would fail with it. The brief keeps readiness behavior as implemented and requires BP never to become unready on credential state (ADR-046 Section 5.3).

## 2. Design Decision

Chosen: **Key Vault custody of non-exportable root and intermediate keys, a scheduled issuer pair of Container Apps Jobs, 24-hour leaves renewed at 8 hours, in-process reload by managed-identity read from Key Vault, private mTLS listeners exposed as internal additional ports.** The authoritative statement is ADR-046 12.2; this section records the evaluation.

| Candidate | Result | Reason |
|---|---|---|
| (1) Key Vault keys + scheduled issuer jobs | **CHOSEN** | Matches ADR-046 Section 3.1, 4.1 and 4.2 exactly; no always-on component; uses the managed identity, Key Vault, Container Apps Job and Log Analytics the platform already runs; one issuance library for dev, CI and cloud. Azure provides custody, signing, identity, scheduling and monitoring; the only repo-owned part is the short script that assembles certificates, because Azure has no managed private CA for short-lived SPIFFE-SAN workload certificates. |
| (2) Key Vault certificates with auto-rotation | Rejected for issuance, used for nothing | Validity is in months; integrated issuers are public CAs, and a self-issued certificate is self-signed, so three services would have to re-pin on every rotation; cannot give a private chain or 24-hour leaves. |
| (3) Entra/managed-identity tokens instead of mTLS | Rejected now; escape hatch | Needs an ADR-046 amendment of Sections 3, 3.1, 3.2 and 8. The envelope could still carry actor, role and step-up if BP signs it with a Key Vault key, so the pricing authority is not lost, but parity with development and CI is lost, the credential becomes a bearer token, and Entra app registrations and app-role grants lie outside deployment authority. Recorded as the ADR-010 escape hatch. |
| (4) Existing repo mechanisms | Partly reused | `scripts/bootstrap_workload_identity.py` already generates root, intermediate and leaf with registry validation, delegation certificate key usage and fingerprints for dev and CI, and `infrastructure/workload-identity/registry.yaml` is the identity source. Neither runs in the cloud, handles Key Vault signing, renewal or revocation. The design refactors them into one library. ADR-047 runner infrastructure has no certificate function (ADR-047 line 125) and is not used for trust. ACA peer-to-peer mTLS (ADR-007) is not enabled and gives no URI SAN. |

### 2.1 What the Founder gets

Azure provides: managed identity for every workload and job, Key Vault custody and signing, scheduling, alerting. Nothing is stored or issued by a new WAOOAW store or service. The remaining repo-owned part is one script and its tests, running as two scheduled jobs. It never stops on a calendar date because renewal is automatic and monitored: a workload has at least 16 hours of validity after every healthy renewal and can ride through an issuer outage of that length before failing closed.

## 3. Operating Design

```
Key Vault (per environment)
  keys: wid-root (non-exportable EC P-256, rotation policy), wid-intermediate (same)
  secrets: wid-trust-bundle (public, signed, versioned)
           wid-bundle-business-platform | -billing-engine | -professional-runtime (private, one reader each)
Container Apps Jobs (workload environment)
  ca-rotator  daily   -> root key sign -> intermediate cert; root cert; trust bundle
  leaf-issuer 30 min  -> intermediate key sign -> leaf + delegation certs -> bundle secrets; trust bundle update
Workloads (BP, WBE, PR)
  managed identity -> read own bundle + trust bundle every 5 min -> verify -> atomic in-memory swap
  WBE :5444 / PR :5443 mutual-TLS listener, internal additional TCP port; BP client uses current leaf per new connection
```

1. **Keys and secrets.** Keys are created by Terraform as key resources (public part only in state) with rotation policy. Bundle secrets are created by Terraform with an `UNISSUED` sentinel and `ignore_changes` on the value; workloads treat the sentinel as no credential (`UNAVAILABLE`), and deployment verification fails if it is still present. Roles: workloads get `Key Vault Secrets User` at secret scope for their own bundle and the trust bundle only; `leaf-issuer` gets `Crypto User` on the intermediate key and write on the three bundle secrets and the trust bundle; `ca-rotator` gets `Crypto User` on the root key and write on the trust bundle. No vault-wide `Secrets Officer` (use secret-scope assignments, or an ABAC name-prefix condition on `wid-` if the platform supports it at implementation time).
2. **Signing.** The script builds each to-be-signed certificate with `cryptography`, signs the digest through the Key Vault sign operation (ES256, convert the raw signature to DER) and assembles the signed certificate. Tests verify the result with an ordinary X.509 chain verification.
3. **Publish-then-activate.** New delegation certificates enter the signed trust bundle first; the BP bundle carries `activate_after` at least ten minutes later so every verifier has refreshed. Old delegation keys stay verifiable until their own expiry.
4. **Reload.** Verifiers (WBE, PR) replace single-key construction with a key set built from the trust bundle and validate chain, validity, key usage and revocation at load and for each envelope. The mTLS listener reloads the server certificate chain for new handshakes. BP's client rebuilds its handler for new connections when the bundle changes. No restart, no revision change.
5. **Failure.** Startup and runtime follow ADR-046 Section 5.1. Key Vault outage keeps the last verified bundle until its not-after, then `SERVICE_IDENTITY_UNAVAILABLE`. BP stays ready; its owner gateways report `UNAVAILABLE`.
6. **Exposure.** Second listener in the same container, supervised; internal additional TCP port mapping through an `azapi` overlay; BP reaches `BillingEngine__RelationshipWorkspaceBaseUrl` and `ProfessionalRuntime__RelationshipWorkspaceBaseUrl` on those ports; the existing client validates the server's exact URI SAN, not its host name.
7. **Monitoring.** ADR-046 12.2 D6. Alert recipients and runbook are owned by Platform Operations (`environment-readiness-and-data-continuity.md` line 365). A renewal that has not happened by 12 hours remaining is a warning, by 4 hours is critical.
8. **Revocation.** ADR-046 12.2 D7. One manually triggered job execution; effect within five minutes.
9. **Demo scale-to-zero.** Start or deploy runs `leaf-issuer` once and waits for success before owner-gateway verification; workloads read on boot with background retry.
10. **Cost.** Two short jobs, about 50 executions a day per environment. Include the incremental estimate in the Terraform plan evidence for C-067 and FA-052.

## 4. Implementation Brief For The Platform IT Expert

Authorize one Work Contract (suggested WC-147) per the ordinary process. Slices are ordered. **Founder direction 2026-11-22: slices 0 to 6 ship as one pull request with one commit per slice; Slice 7 stays separate (see Section 8).** No slice may be started before the Founder approves ADR-046 Amendment 1, except Slice 0; merging the single pull request is that approval. Slice 0 result (Demo, 2026-11-22): (a) an additional internal TCP port reaches workload TLS with client certificate end to end (TLS 1.3, the server saw the client certificate and the client pinned the server certificate; ARM `additionalPortMappings` accepted); (b) the pinned `azure-cli` job image bundles `cryptography` 44.0.1 and `yaml` under `/usr/lib64/az/lib/python3.12/site-packages` (run the issuer with `PYTHONPATH` set to it) and `az login --identity` works in a job; (c) a job with a managed identity reaches the private vault (RBAC refusal, not a network refusal); Key Vault public access is disabled and reached through the private endpoint, so the vault is not reachable from outside the environment network. Not yet proven: the Key Vault `sign` call itself (proven in the Slice 3 Demo job run). Each slice below is a commit, not a separate pull request. Docker-only validation applies. Any change under `infrastructure/terraform/phase2/modules/workload/` or `src/professional-runtime/` requires the pre-PR runtime lifecycle gate: run `scripts/prepare_pr_body.py` (it invokes `scripts/run_goal006_runtime_lifecycle_gate.sh <evidence.json>`) at the exact head and include the evidence block in the PR body.

**Slice 0 - Spikes (no merge).** In Demo, prove and record: (a) an internal additional TCP port on a Container App is reachable from another app by `ca-demo-<app>:<port>` with TLS passed through to the workload; (b) the pinned `azure-cli` job image can run the issuance script (`cryptography`, `az keyvault key sign --algorithm ES256 --digest`, `az keyvault secret set`) under a job managed identity; (c) a workload container can read a Key Vault secret with its managed identity (precedent: `web` uses `AZURE_KEY_VAULT_URL`); (d) the Python and .NET services can add the read with the Azure SDK or with the identity endpoint and Key Vault REST without breaking ADR-045 image policy. If (a) or (b) fails, stop and return to the Enterprise Architect; do not substitute another design.

**Slice 1 - Issuance library, issuer script, registry 1.1.** Files: `scripts/bootstrap_workload_identity.py` (extract the issuance into a library with a signer interface: local ephemeral key, Key Vault sign), a new issuer script under `scripts/` with modes `ca`, `leaf`, `revoke`, `status`, `infrastructure/workload-identity/registry.yaml` (`policy_version: "1.1"`, cloud `leaf_lifetime_hours: 24`, add the link-probe route grant for BP to WBE and PR), `tests/constitutional/test_adr046_pki_bootstrap.py` (extend). Acceptance: dev and CI output remains behavior-compatible with today's tests; a fake Key Vault signer produces a chain that verifies; renew at 8 hours, 24-hour maximum, 90-day intermediate and one-year root with seven-day dual trust; revocation list and suspension; sentinel and rollback rejection; no key material in logs. No src/ changes.

**Slice 2 - Verifier and loader hardening with hot reload (src).** Files: `src/billing-engine/{workload_identity,relationship_workspace,private_server,mtls_protocol,main}.py`, `src/professional-runtime/{workload_identity,relationship_workspace,private_server,main}.py`, `src/business-platform/Services/{WorkloadIdentityClient,AuthenticatedPricingAdminGateway}.cs`, `src/business-platform/Program.cs`. Add a credential source abstraction (directory for dev and CI, Key Vault for cloud, selected by configuration; absent configuration changes nothing), a trust bundle consumer, delegation key sets with chain, validity and key-usage checks, in-process swap, rollback rejection, credential-state health and metric, a registered link-probe operation (GET, no actor, answers peer class and bundle version), and a positive `service_auth decision=allow` log for pricing operations. Acceptance: all ADR-046 Section 10 negative tests still pass; expired or not-yet-valid delegation certificates are rejected; hot reload with no restart in tests; BP stays ready with UNAVAILABLE gateways; no change to Emergency Stop.

**Slice 3 - Terraform custody, identities and jobs (Demo only first).** Files: `infrastructure/terraform/phase2/modules/workload/*.tf`, `environments/demo/workload/main.tf`. Add keys with rotation policy, per-workload and per-job identities and secret-scope roles, the `UNISSUED` secrets, `ca-rotator` and `leaf-issuer` scheduled jobs (digest-pinned image, script and registry digests in plan evidence), alerts per ADR-046 D6 following `whatsapp-monitoring.tf`, a deployment step that runs `ca-rotator` then `leaf-issuer` once and requires success before activation. Acceptance: plan shows zero destroys and no key material in state or logs; plan policy PASS; roles are least privilege; runtime lifecycle gate evidence at the exact head; the jobs run in Demo and the bundles show not-after 24 hours and renewal at 8 hours on the next run.

**Slice 4 - Listener exposure and wiring (Demo).** Files: `src/billing-engine/Dockerfile`, `src/professional-runtime/Dockerfile` (single supervised entrypoint running public and private listeners), `modules/workload/main.tf` (`azapi` additional internal TCP mappings for 5444 and 5443, `WAOOAW_WORKLOAD_*` source settings, `BillingEngine__RelationshipWorkspaceBaseUrl`, `ProfessionalRuntime__RelationshipWorkspaceBaseUrl` for BP, remove the PR entrypoint copy workaround and `/mnt/workload-trust`). Acceptance: BP link probe returns 200 for both owners; plaintext, wrong-SAN and wrong-environment connections are refused; the private ports are not externally reachable; revision preservation (C-067) honored; runtime lifecycle gate evidence.

**Slice 5 - Demo cutover and qualification (must reach Demo by 2026-12-09).** Delete the two interim Key Vault secrets and the hand-made import blocks after the first successful deploy, update CB-021 with closure. Acceptance:
- BP, PR and WBE report credential source `keyvault` with at least 16 hours remaining.
- BP exposes coarse owner-link state (READY or UNAVAILABLE per owner, no identifiers) and a deployment verification step fails the deployment when any owner gateway is `Unconfigured` or the link probe is not 200, or when an authenticated BP probe through the real gateway returns 401 or 503. Extend the existing deployment verification job and `scripts/goal006_verify_deployment.sh`; the failure must be visible in the workflow summary, not only logs.
- Live qualification: a Founder-role Demo session performs `GET /admin/pricing`; the response is 200 and shows live margin, with matching BP and WBE correlation identifiers and a WBE `decision=allow` log line. The same call with a missing step-up or a shared ops token is refused with no fallback. The evidence is attached to CB-021.
- Simulated issuer outage test in Demo (suspend the job for 4 hours): warning alert fires; apps continue; resume and confirm renewal.

**Slice 6 - UAT and Production.** Reuse the same module through environment configuration. Production activation follows the existing Founder activation gates. Repeat Slice 5 acceptance per environment. Different trust bundles and keys per environment (ADR-046 Section 3.1).

**Slice 7 (separate Work Contract, not required for pricing).** Wire `BillingEngine__BaseUrl` and `BillingEngine__OpsAuthToken` on Demo BP for the legacy trial/subscription routes under ADR-046 12.1 item 3, or migrate them to Section 7.2.

## 5. Drift Guards For The Next Session

Do not: add an ops-token, shared-secret or header-based path to pricing or any governed route; generate certificates by hand or ship a static bundle; extend the CB-021 exception; introduce a new certificate store, always-on issuer, service mesh or new image in the release tuple; rely on Container Apps secret-volume refresh; make BP unready on credential state; change the trust-domain form. If something here cannot work, stop and return to the Enterprise Architect with the Slice 0 evidence.

## 6. Proposals For The Founder (not constitutional edits)

Proposed claim text for the Founder to approve or reject (no claim file has been created or edited): "Any credential that expires on a fixed date in a deployed environment must have an automated, monitored renewal path with an alert before the renewal margin is exhausted; a calendar expiry must never be the cause of an outage." Basis: ADR-046 Section 4.2 and 5.2 already require the behaviour for workload identity; a claim would make it universal.

## 7. Traceability

ADR-046 Sections 3.1, 3.3, 4.1, 4.2, 5.1, 5.2, 5.3, 7.2, 8, 12; ADR-007; ADR-014; ADR-034; ADR-045; ADR-047; CB-021; WC-134; WC-136; WC-144; `infrastructure/workload-identity/registry.yaml`; `scripts/bootstrap_workload_identity.py`; `modules/workload/main.tf`.

## 8. Delivery Interface (binding for all slices; Founder-directed single PR, 2026-11-22)

The Founder directed that slices 0 to 6 ship as one pull request (commits per slice) and that Demo, UAT and Production use the same mechanism, differing only by environment parameters. Slice 7 stays separate. All components below must agree on this interface.

**Key Vault objects (per environment vault, all names prefixed `wid-`).**

| Object | Kind | Content | Writer | Readers |
|---|---|---|---|---|
| `wid-root` | key (EC P-256, non-exportable, Terraform-created) | root CA key | none (sign only) | `ca-rotator` (sign, create version) |
| `wid-intermediate` | key (same) | intermediate CA key | `ca-rotator` (create version) | `ca-rotator` (create version), `leaf-issuer` (sign) |
| `wid-ca-state` | secret, JSON | `{schema_version:"1.1", bundle_version:int, root_pem, root_key_kid, intermediate_pem, intermediate_key_kid, previous_root_pem|null, previous_root_until|null}`; public material and key versions only | `ca-rotator` | `leaf-issuer` |
| `wid-trust-bundle` | secret, JSON | see below, public only | `ca-rotator`, `leaf-issuer`, `revoke` | every workload |
| `wid-bundle-<workload>` | secret, JSON | see below, private | `leaf-issuer` | only that workload |

Terraform creates the two keys and the secrets with the value `UNISSUED` and `ignore_changes` on the value. A workload treats a value that is not valid JSON of the right schema, including `UNISSUED`, as "no credential yet".

**`wid-trust-bundle` JSON.** `{schema_version:"1.1", bundle_version:int, environment, trust_domain, generated_at, root_pem, intermediate_pem, ca_bundle_pem (root, intermediate, and previous_root while dual-trust), revoked_serials:[decimal strings], revoked_identity_uris:[...], manifest:{schema_version:"1.0", policy_version:"1.1", environment, trust_domain, workloads:{<name>:{identity_uri, audience, tls_certificate_sha256, tls_serial, not_before, not_after, delegation_certificates:[{key_id, certificate_pem, not_before, not_after, activate_after}], delegation_key_id (the active one)}}, route_grants:[...registry...]}, signature}`. `signature` is base64 of an ES256 (DER) signature by the intermediate key over the UTF-8 canonical JSON (sorted keys, no whitespace, ASCII) of the bundle with the `signature` member removed; a consumer verifies it with the bundle's own `intermediate_pem` after checking that certificate chains to the bundle's `root_pem`. `bundle_version` is monotonic (UTC epoch seconds of generation, raised by 1 if not greater than the previous). Consumers reject a lower version than the last accepted one.

**`wid-bundle-<workload>` JSON.** `{schema_version:"1.1", bundle_version:int, environment, workload, identity_uri, generated_at, not_after (the leaf not_after, ISO-8601 UTC), tls_key_pem, tls_cert_pem (leaf then intermediate), delegation_key_pem|null, delegation_cert_pem|null, delegation_key_id|null, delegation_activate_after|null}`. A delegation signer must not sign before `delegation_activate_after`; the certificate must already be in the trust bundle manifest (publish-then-activate, 10 minutes).

**Environment variables (service side).** `WAOOAW_WID_SOURCE` = `directory` (default; existing `WAOOAW_WORKLOAD_CREDENTIALS` behavior unchanged for development, CI and tests) or `keyvault`. For `keyvault`: `WAOOAW_WID_VAULT_URL` (for example `https://kv-waooaw-demo.vault.azure.net`), `WAOOAW_WID_WORKLOAD` (`business-platform`, `billing-engine` or `professional-runtime`), `WAOOAW_WID_MANAGED_IDENTITY_CLIENT_ID` (the user-assigned identity client id), `WAOOAW_WID_REFRESH_SECONDS` (default 300, minimum 30), `WAOOAW_WID_TRUST_DOMAIN` (expected trust domain, exact match required). Key Vault is read over its REST API with a managed-identity token from `IDENTITY_ENDPOINT` and `IDENTITY_HEADER` (resource `https://vault.azure.net`, API version `7.4`), as `WhatsAppProviderSecrets.cs` already does for the WhatsApp provider; no new SDK dependency may be added if the REST call suffices. The vault host must be taken from `WAOOAW_WID_VAULT_URL`, never hard-coded to one environment, and must end in `.vault.azure.net`.

**Issuer job environment.** `WID_ENVIRONMENT` (`demo`, `uat`, `prod`), `WID_VAULT_URL`, `WID_MANAGED_IDENTITY_CLIENT_ID`, `WID_WORKLOADS` (comma list, default `business-platform,billing-engine,professional-runtime`), `WID_REGISTRY_PATH`. Command line `issue.py {ca|leaf|revoke|status}`.

**Behavior rules.** Renew the leaf when its age is at least 8 hours, issue 24-hour leaves (registry `policy_version: "1.1"`), publish delegation certificates and the trust bundle before the bundle that activates them, sign only with Key Vault keys (`POST {key kid}/sign`, `ES256`, base64url SHA-256 digest; raw R||S converted to DER) in cloud and with local ephemeral keys in development and CI through the same library, never log key material, never write a CA private key anywhere.

**Link probe.** Registry operation `probeServiceLink` (GET, contract major 1) at route `/internal/v1/service-link` on the WBE and PR private listeners, granted to the `business-platform` caller. It requires no actor and answers `{status:"ok", peer_identity_uri, bundle_version, remaining_seconds}`, where `peer_identity_uri` is the identity of the caller taken from its client certificate (for the Business Platform probe, the Business Platform's own identity URI, never the owner's).

**BP owner-link state.** BP reports, without becoming unready, per owner gateway (`billing`, `professional-runtime`) one of `READY`, `UNAVAILABLE` or `UNCONFIGURED` in a non-gating field of its existing health detail, and probes the link with the probe route above (cached, refreshed with the credentials). A link is `READY` only when the owner answers `status:"ok"` and echoes BP's own identity URI. While any link is `UNAVAILABLE`, BP re-probes at the 30-second minimum interval instead of the credential refresh interval. The WBE and PR private ports do not wake a scaled-to-zero replica, so both keep one warm replica (`billing_min_replicas`, `pr_min_replicas`), as the AI runtime does.

## 9. Implementation Record (Platform IT Expert, IB-147 single PR)

Design status: ADR-046 Amendment 1 and this contract were approved and merged with PR #615. Where this section differs from Sections 3 to 5, this section is what was implemented; the Enterprise Architect should fold it into the contract at the next review.

| Topic | Implemented behavior | Reason |
|---|---|---|
| Key versions | `ca-rotator` creates new `wid-root` and `wid-intermediate` key versions explicitly (`create_key_version`) when the CA lifetime policy requires it. No Key Vault rotation policy is configured. | The issuer must publish the new public certificate in the same step; a policy-created version would be signed by nothing. |
| Job roles | `ca-rotator` holds `Key Vault Crypto User` and `Key Vault Crypto Officer` on both `wid-root` and `wid-intermediate` (it signs and creates versions), plus `Secrets Officer` on `wid-ca-state` and `wid-trust-bundle`. `leaf-issuer` holds `Crypto User` on `wid-intermediate`, `Secrets User` on `wid-ca-state`, and `Secrets Officer` on `wid-trust-bundle` and the three `wid-bundle-*` secrets. No vault-wide role. | Crypto Officer manages keys but cannot sign. |
| Leaf extensions | `subjectAltName` and `extendedKeyUsage` are non-critical; `basicConstraints` and `keyUsage` stay critical. | Standards-compliant verifiers reject a critical SAN when the subject is non-empty and reject a critical EKU on the leaf chain. |
| Issuer console contract | The jobs print `wid_issuer mode=<m> result=ok|failed`, `wid_status workload=<w> remaining_seconds=<n> bundle_version=<n>` and `wid_status ca intermediate_days=<n> root_days=<n>`. The Azure alerts parse exactly these lines. | Alerts must not depend on free-form output. |
| Deployment gate | `scripts/goal006_wid_gate.py`, a step in `environment-deployment.yaml`, starts `ca-rotator` then `leaf-issuer`, requires `Succeeded`, then requires BP `/health/detail` to report `credential_source=keyvault`, `credential_state=READY` and `READY` links to `billing` and `professional-runtime`. | Terraform success does not prove signing or pickup. |
| Interim Demo objects | The hand-made trust secrets, their role assignments and import blocks are kept in this PR. | The plan policy rejects deletions and replacements in workload plans. A follow-up PR removes them after the issuer is proven in Demo, by 2026-12-09. |
| Private listeners | Billing (5444) and Professional Runtime (5443) get an internal-only additional TCP port through an `azapi` PATCH; azurerm 4.14 cannot express it. | Internal mTLS must not share the public ingress. |
| Alerts | `wid-issuer-failed`, `wid-leaf-issuer-silent`, `wid-credential-warning` (under 12 h), `wid-credential-critical` (under 4 h) and `wid-ca-expiry` (under 14 days). | ADR-046 D6. |

Not yet proven at the time of writing (recorded in CB-021 when measured): Key Vault `sign` from a job in Demo, key-level RBAC allowing new key versions, the `azapi` PATCH against the existing public ingress of Professional Runtime, and the monthly cost.

**WC-149 addition.** The AI runtime becomes a fourth cloud workload (`wid-bundle-ai-runtime` slot, `WID_WORKLOADS` in the cloud stacks lists it, registry grants whose caller and target are both issued workloads are published in the trust bundle, so the earlier AI runtime grants are published for the first time). It gets an internal-only mutual-TLS listener on 5444 and one warm replica (`air_min_replicas`, default 1), because an additional TCP port does not wake a scaled-to-zero replica. Business Platform reaches it at `ProviderProbe__BaseUrl`. The worst-case trust bundle with four workloads, overlapping delegations and dual trust is under the 25 KiB secret limit with a small margin; `tests/constitutional/test_wid_issuer.py` asserts it, and the next grant or workload must raise the limit question first.
