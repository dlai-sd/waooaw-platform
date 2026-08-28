# GOAL-006 Cloud Platform Finalization Evidence

## Record Control

| Field | Value |
|---|---|
| Baseline | `10d7525ccca6fa0d7daa437da7e4630fb94bbeae` |
| Branch | `fix/goal006-cloud-platform-finalization` |
| Authority | WC-076; FA-052; Founder current-session Demo/UAT implementation and Azure CLI proof authorization on 2026-08-28 |
| Status | DEMO ACCEPTED; UAT DEPLOYED AND VERIFIED; PRODUCTION CODE-PREPARED / PLAN-ONLY PREREQUISITES PENDING |

## Local And Offline Qualification

| Check | Result |
|---|---|
| Failing contract baseline | PASS - seven finalization contracts failed before implementation |
| Focused Keycloak/output/trust contracts | PASS |
| GOAL-006 focused regression | PASS - 181/181 after canonical trust restoration |
| Full pipeline regression | PASS - 1275/1275 |
| Actionlint | PASS - GOAL-006 deployment workflows |
| Terraform 1.9.8 formatting | PASS |
| Terraform roots | PASS - Demo/UAT/Production foundation and workload, 6/6 |
| Patch whitespace | PASS |

Python contracts ran with the repository Python environment. Terraform formatting and validation
ran with `hashicorp/terraform:1.9.8`.

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
| UAT runner resources | ACTIVE and proven through private broker, runner, and cleanup executions |
| UAT managed environment | Public (`internal=false`), `Succeeded`, static IP `135.13.181.135` |
| UAT active executions | Zero broker, runner, or cleanup executions after qualification |
| OIDC subjects | Exact Demo, UAT, and Production GitHub Environment subjects exist |
| GitHub Environments | Demo and UAT deployment/verification environments exist; Production deployment/verification environments are absent |

The Founder directed that the Terraform state account must not be public. Azure CLI disabled public
network access on `waooawp3tfstate2ed118`; immediate verification confirmed default deny, zero IP
rules and the existing approved Demo private endpoint. No state content was read.

## Remaining Boundaries

The shared Terraform state account has no declarative owner in the authorized Terraform roots or
runner Deployment Stack; those surfaces reference it as an existing resource. Public access is now
disabled as directed, but durable infrastructure-as-code ownership remains deferred engineering debt.

Production GitHub deployment and verification environments are absent. Creating protected
Production environments remains a prerequisite for any Production plan. Production foundation code
now declares a public managed environment before first creation, and Production workload code omits
the Demo Founder CIDR restriction; no Production plan or apply was run. Production runner activation
remains prohibited and its blueprint is `INACTIVE`.

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
| UAT public foundation migration | PASS - empty private Container Apps environment replaced once with explicit Founder authorization; final environment `cae-waooaw-uat` is public, `Succeeded`, and reusable; strict no-delete policy restored afterward |
| UAT initial workload | PASS - run `33160684332` deployed all eight apps and cleaned private execution resources; independent verification correctly failed on Keycloak HTTP 500 |
| Keycloak RCA | CONFIRMED - in-memory H2 initialized/imported successfully, then presented an empty schema in the same JVM; revision lacked application readiness gating |
| Keycloak correction | PASS - `dev-file` backing store plus OIDC startup/readiness probes; revision `ca-uat-keycloak--0000001` is healthy and latest-ready; public OIDC discovery returns HTTP 200 |
| Output-chain RCA | CONFIRMED - UAT root omitted `web_url`; `echo "web_url=$(terraform output ...)"` masked Terraform failure and emitted an empty reusable-workflow output |
| Output-chain correction | PASS - all workload roots forward `module.workload.web_url`; workflow captures and asserts a non-empty value before publishing it |
| Final UAT qualification | PASS - run `33177257822` at SHA `40fe8131de635860ec86b8171e315ab607061d36`; authorize, resolve, broker, apply, cleanup, and independent verification all succeeded |
| UAT functional verification | PASS - execution `job-uat-deployment-verification-rcxumkt`; OIDC HTTP 200 on attempt 1, Web and Business Platform HTTP 200 on attempt 2, Constitutional Engine `SERVING` |
| UAT serving revisions | PASS - all eight apps report `Succeeded` and latest revision equals latest-ready; internal services remain internal and customer-facing services use public ingress |
| UAT public endpoints | PASS - Web HTTP 200; identity-edge OIDC HTTP 200 with UAT issuer |
| Production | CODE-PREPARED / NOT RUN - public-at-creation foundation and no CIDR restriction; protected environments and plan prerequisites remain pending; apply prohibited |
| Temporary trust cleanup | PASS - exact-branch wrapper removed; reusable deployment and verification trust only `deploy.yaml@refs/heads/main` and immutable `release_sha` checkouts |

RCA: `https://api.ipify.org` was initially queried from Codespace, so the deployed `/32` represented
automation egress instead of the Founder's review browser. The canonical dispatch input now requires
the address to be obtained in the Founder review browser and explicitly rejects Codespace or runner
egress as the source. Focused workflow contracts passed 74/74 and actionlint passed after the change.

The reusable workflow labels are environment-derived. Deployment uses the selected environment and
verification uses `${{ inputs.environment }}-verification`. The temporary exact-branch wrapper used
for UAT qualification is absent from the final branch.