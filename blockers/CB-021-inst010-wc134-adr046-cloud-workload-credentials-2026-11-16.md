# CB-021 — WC-134 ADR-046 Cloud Workload Credentials For Professional Runtime

**Office:** Platform IT Expert (INST-010)
**Work Contract:** WC-134
**State:** OPEN — Founder disposition recorded 2026-11-16: continue Demo with Professional Runtime unready (fail closed); provisioning deferred

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
