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
