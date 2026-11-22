# CB-021 — WC-134 ADR-046 Cloud Workload Credentials For Professional Runtime

**Office:** Platform IT Expert (INST-010)
**Work Contract:** WC-134
**State:** OPEN — PARTIALLY MITIGATED on Demo only (2026-11-16, Founder-accepted interim exception, expires 2026-12-16); cloud issuance, private-key delivery, the PR mTLS listener and the BP link remain undesigned

## Blocking condition

Professional Runtime health requires `relationship_workload_auth`, which is built from the ADR-046
workload credential bundle at `WAOOAW_WORKLOAD_CREDENTIALS` (manifest, BP delegation certificate,
per-workload certificates). Before WC-134 the check required only `bp_service_jwt_secret`. No Terraform,
Key Vault asset, volume mount or listener configuration provisions the bundle for Demo, UAT or Production,
and the WC-134 contract states that "listener/configuration deployment remains unqualified".
`ca-demo-professional-runtime--0000102` therefore reports `degraded` (HTTP 503) and fails activation,
and BP-to-PR conversation Start, Cancel and stream cannot be authorized. ADR-046 forbids a plaintext or
legacy-secret fallback, so governed conversation generation stays `UNAVAILABLE`.

## Evidence

- Demo forward-fix of Environment Deployment run `43150585543` (release `e69dd3a0`): 11 of 12 applications
  ready; `ca-demo-professional-runtime` `ActivationFailed`, `/health` 503 for the full probe window.
- PR `main.py` `health()` and `relationship_workspace.configure_relationship_workspace()` at `e69dd3a0`;
  the same check at `8cf1e38b` read only `bp_service_jwt_secret`.
- The Container App has none of `WAOOAW_WORKLOAD_CREDENTIALS`, `AIR_EMPLOYMENT_BASE_URL` or a credential volume.
- ADR-046 section 4.1: cloud certificates and delegation keys are per-environment Key Vault assets.

## Needed to unblock

Accepted design and an authorized Work Contract for per-environment ADR-046 issuance (root, intermediate,
workload certificates, BP delegation key) in Key Vault, managed-identity access, mounts for BP and PR,
the PR mTLS listener configuration, rotation and expiry alerting, and a Demo qualification proving BP to PR
Start/Cancel/stream. Until then Demo serves everything that does not need PR conversation generation.

## Demo forward-fix record

Environment Deployment run `43150585543` (release `e69dd3a0`, PR #594) failed after the Demo database reset
succeeded. The CLI log tail is capped at 300 records and the indented provisioner result reached 324
(106 init files), so `jq` received truncated JSON. The Azure job itself had `Succeeded`: the four databases were
reset, the init chain applied and the ownership handoff verified. The workflow now rebuilds the result from
Log Analytics when the tail is not complete JSON, and a regression test runs the step with a result larger than
the cap.

By Founder direction the remaining steps were replayed out of band on Demo only, from the same signed release
tuple and run evidence, by a temporary job in the private runner environment as `id-waooaw-demo-deployment`.
This departs from the single `deploy.yaml` mutation path (ADR-047) and carries no GitHub attestation of its own.
Terraform applies had zero destroys; the Keycloak and Temporal migrations, the Billing migration and the Temporal
qualification passed; 11 of 12 applications became ready. The old-revision retirement step was skipped
deliberately to keep Professional Runtime's last healthy revision as rollback. The temporary job and workspace
blob were removed; two `.pre-forward-fix-20261116` Terraform state backups remain for Founder disposition.

WhatsApp webhook ingress, TLS, guest registration and deterministic replies are served; governed conversation
generation remains `UNAVAILABLE` and fails closed. Live Meta delivery has not been exercised and needs Founder
acceptance.

## Interim mitigation (Demo only, Founder-accepted 2026-11-16)

Professional Runtime health needs only the public ADR-046 trust material: `manifest.json` and Business
Platform's `delegation-cert.pem`. Those two public files were generated with
`scripts/bootstrap_workload_identity.py` in a throwaway Docker container, using a temporary registry copy that set
the `ci` slot to Demo's trust domain (`demo.waooaw.internal`) and a 720-hour leaf lifetime; the manifest's
`environment` field was then set to `demo`. All private keys and the throwaway root were shredded and never left
that container. PR's own `WorkloadAuth.from_credentials` loaded exactly those two files.

The two files were written to Key Vault `kv-waooaw-demo` by a temporary in-network job as secrets
`workload-identity-manifest` and `workload-identity-bp-delegation-cert`, read by PR's identity only
(`Key Vault Secrets User`, secret scope). Terraform now owns the wiring: two Key Vault secret references, a Container
Apps `Secret` volume at `/mnt/workload-trust`, `WAOOAW_WORKLOAD_CREDENTIALS=/tmp/workload-identity`, and an entrypoint
that rebuilds the directory tree the loader reads because Container Apps mounts secrets flat. The two role assignments
created by hand are adopted by `import` blocks in `environments/demo/workload/main.tf`; remove them after the first
successful deploy. A real Demo `terraform plan` showed 2 imports, 12 in-place changes and 0 destroys, plan policy PASS.

Result: `ca-demo-professional-runtime--0000103` is ready; the in-network verification job passes for all 7 services and
all 12 applications are ready; superseded revisions were retired.

### Accepted ADR-046 exceptions (Demo only)

| Exception | ADR-046 requirement | Expiry / closure |
|---|---|---|
| Hand-made trust root and certificates | Issuance from the approved registry, not a manual ceremony | Certificate not-after `2026-12-16T08:40:19Z`; replaced by the designed issuer |
| 30-day leaf lifetime | 2-hour leaf lifetime for Demo | Same |

### What is NOT delivered

- PR reports healthy because it can verify BP-signed envelopes. BP has no workload credentials, so it does not sign them;
  BP's gateways stay unconfigured and governed conversation generation remains `UNAVAILABLE`.
- No private key is delivered to any workload. The PR mTLS listener (`private_server.py`, port 5443) is not started by
  the image, which runs only `uvicorn main:app` on 5003, and nothing exposes port 5443.
- No cloud issuance, renewal, revocation or compromise runbook exists. An architect-owned Azure deployment design for
  these is required before the full capability, UAT or Production.
- After 2026-12-16 the manifest and delegation certificate expire; PR's loader does not check expiry, but the
  exception must be closed or renewed by then.

## Enterprise Architect disposition (2026-11-22, Founder-requested focused session)

**Office:** INST-004 Enterprise Architect. **Status of the design:** PROPOSED - FOUNDER APPROVAL PENDING; Part A of ADR-046 Section 12 restates accepted text and is already in force.

- **The design gap in "Needed to unblock" is answered.** [ADR-046 Section 12](../adr/ADR-046-workload-identity-and-service-authentication.md) (Amendment 1) and [workload-identity-cloud-issuance-contract.md](../architecture/reference/security/workload-identity-cloud-issuance-contract.md) define Key Vault custody, scheduled issuance, 24-hour leaves renewed at 8 hours, in-process reload, private listener exposure, alerting, revocation and ordered implementation slices. No earlier Azure-issued-identity design existed; the contract section 1.1 records the evidence.
- **Pricing admin cannot use a shared token.** The Platform IT Expert's withdrawal of the ops-token path is confirmed: only the signed delegated envelope can carry actor, role and Founder step-up (ADR-046 12.1 items 1-2).
- **Exception handling.** The Demo interim exception expiring 2026-12-16T08:40:19Z stays as recorded until closed. It must be retired by Slice 5 no later than 2026-12-09; if not, the Platform IT Expert records a dated extension request here before 2026-12-09. Closure requires the deletion of the two interim Key Vault secrets, credential source `keyvault` in BP, PR and WBE, and a Founder-session `GET /admin/pricing` returning 200 through BP to WBE (ADR-046 12.3).
- **Newly recorded gap.** Verifiers do not check chain, validity or key usage of the BP delegation certificate (`relationship_workspace.py` in WBE and PR); Slice 2 closes this.
- **Next state.** Blocker stays OPEN until the Founder approves Amendment 1 and a Work Contract for Slices 1-5 is authorized; then it moves to PARTIALLY MITIGATED until Slice 5 evidence closes it. The Enterprise Architect did not change implementation, infrastructure or any existing Work Contract.
