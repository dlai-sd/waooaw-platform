# GOAL-006 Cloud Platform Finalization Evidence

## Record Control

| Field | Value |
|---|---|
| Baseline | `10d7525ccca6fa0d7daa437da7e4630fb94bbeae` |
| Branch | `fix/goal006-cloud-platform-finalization` |
| Authority | WC-076; FA-052; Founder current-session implementation, read-only Azure, temporary exact-branch trust, and Demo plan/apply authorization on 2026-08-28 |
| Status | DEMO ACCEPTED; UAT RUNNER ACTIVE; UAT WORKLOAD QUALIFICATION NEXT |

## Local And Offline Qualification

| Check | Result |
|---|---|
| Failing contract baseline | PASS - seven finalization contracts failed before implementation |
| Focused workflow contracts | PASS - 21/21 |
| Runner blueprint/bootstrap/deployment | PASS - 40/40 |
| GOAL-006 pipeline regression | PASS - 470/470 |
| Full pipeline regression | PASS - 1260/1260 at UAT runner qualification SHA `c3d6318d94adbee20c310f2f46c4d74b2ad289fb` |
| Actionlint 1.7.7 | PASS - eight delivery workflows |
| Terraform 1.9.8 formatting | PASS |
| Terraform roots | PASS - Demo/UAT/Production foundation and workload, 6/6 |
| Editor diagnostics | PASS - no findings in touched workflow, test, or runner-stack paths |
| Patch whitespace | PASS |

All Python tests ran through `docker compose run --rm test-runner`. No host Python test process or
virtual environment was used.

## Azure Read-Only Preflight

| Check | Observed result |
|---|---|
| Tenant | `0471534c-1bbe-40ab-ae65-3f721b62582c` |
| Subscription | `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84`, Enabled |
| Region | Central India |
| GOAL-006 monthly budget | INR 10,000 |
| Current monthly spend | INR 504.22 observed 2026-08-28 |
| Demo runner executions | Zero active runner, broker, cleanup, or reconciler executions |
| Demo runner Key Vault | Public network disabled; default deny; RBAC enabled |
| State account | Public network disabled; default deny; no IP rules; approved Demo private endpoint present |
| UAT/Production runner resources | Runner resource groups exist but contain no resources |
| OIDC subjects | Exact Demo, UAT, and Production GitHub Environment subjects exist |
| GitHub Environments | Demo and UAT deployment/verification environments exist; Production deployment/verification environments are absent |

The Founder directed that the Terraform state account must not be public. Azure CLI disabled public
network access on `waooawp3tfstate2ed118`; immediate verification confirmed default deny, zero IP
rules and the existing approved Demo private endpoint. No state content was read.

## Remaining Boundaries

The shared Terraform state account has no declarative owner in the authorized Terraform roots or
runner Deployment Stack; those surfaces reference it as an existing resource. Public access is now
disabled as directed, but durable infrastructure-as-code ownership remains deferred engineering debt.

Production GitHub deployment and verification environments are also absent. Creating protected
Production environments remains a prerequisite for the authorized Production plan-only stage.
Production runner activation remains prohibited and its blueprint is `INACTIVE`. UAT uses the
approved environment-federated bootstrap app for hosted control-plane operations and the generated,
verified cleanup managed identity for post-run cleanup.

## Live Evidence

| Evidence type | Status |
|---|---|
| Azure mutation | PASS - state account public network access disabled and private endpoint preserved |
| Demo plan | PASS - run `33145397876` at qualification SHA `7c7700d41104036e4810e1457404126022424eff`; runner, broker and cleanup succeeded |
| Initial Demo apply | BACKEND PASS / FOUNDER BROWSER FAIL - run `33146079390` deployed release SHA `10d7525ccca6fa0d7daa437da7e4630fb94bbeae`, but used Codespace egress `4.240.39.204/32`; the Founder browser at `49.36.49.189` received `RBAC: access denied` at Azure ingress |
| Corrective Demo apply | PASS - run `33147562517` at qualification SHA `9fe961219d609df01f1c9d9a5345b6052fa6f5bd`; Web, Business Platform and Professional Runtime now restrict ingress to Founder browser CIDR `49.36.49.189/32` |
| Exact-branch OIDC/private runner | PASS - plan and both apply runs traversed the private runner; zero runner, broker and cleanup executions remained active |
| Independent verification | PASS - exact-six, pinned dependencies, latest-ready revisions, internal HTTP/gRPC probes, URL and CIDR |
| Demo endpoint | ACCEPTED - Founder confirmed the corrected portal loaded at `https://ca-demo-web.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io` on 2026-08-28 |
| Demo ingress | PASS - Web, Business Platform and Professional Runtime restricted to `49.36.49.189/32`; private services remained internal |
| Functional verification | PASS - corrective execution `job-demo-deployment-verification-wri2jfa`; independent Web, Business Platform, identity discovery and Constitutional Engine probes succeeded |
| Serving revisions | PASS - all eight latest revisions matched latest-ready and received 100% of routed traffic; retained zero-traffic rollback revisions were not mutated |
| Exact-six digests | PASS - live Constitutional Engine, Business Platform, Professional Runtime, AI Runtime, Web and Billing Engine digests exactly matched the signed release manifest |
| Founder Demo acceptance | PASS - Founder explicitly accepted and approved the Demo application on 2026-08-28 after browser-path verification |
| UAT prerequisite reconciliation | PASS - dedicated Azure CLI what-if contained zero deletes; apply refreshed the current six-output custom-role contract and verified RBAC plus INR 10,000 budget |
| UAT runner preview | PASS - run `33149859100` at SHA `c3d6318d94adbee20c310f2f46c4d74b2ad289fb`; reviewed plan `sha256:6bcf94f36f1f77f550b5d6e5e51337e5a1aa801916b2c6d010415413991e9361` contained 36 creates, one resource-group ignore and one approved deferred same-environment evidence assignment, with zero deletes |
| UAT runner apply | PASS - run `33150103583`; deployment record `sha256:8f725ff1c009f8b99d277cf8a771a456ba21ce2d92c29580361dd8935ec7640d`; stack verified ACTIVE with 37 managed resources, `denyDelete`, detach-on-unmanage, private approved endpoints, private RBAC vault, immutable job images and zero active runner/broker/cleanup executions |
| UAT workload | NEXT - plan/apply the Demo-proven exact-six release using the UAT protected configuration boundary |
| Production | NOT AUTHORIZED - plan/apply not run |
| Temporary trust cleanup | PASS - qualification branch policies and cleanup federation removed after each run; Demo, Demo verification and cleanup identity trust only `main` |

RCA: `https://api.ipify.org` was initially queried from Codespace, so the deployed `/32` represented
automation egress instead of the Founder's review browser. The canonical dispatch input now requires
the address to be obtained in the Founder review browser and explicitly rejects Codespace or runner
egress as the source. Focused workflow contracts passed 74/74 and actionlint passed after the change.

The reusable workflow labels are environment-derived. The observed `Apply demo` job name is formed
from the selected execution and `${{ inputs.environment }}`; the `demo-verification` protected
environment is formed from `${{ inputs.environment }}-verification`. The temporary exact-branch
wrapper was intentionally Demo-only for pre-PR qualification and is absent from the restored branch.