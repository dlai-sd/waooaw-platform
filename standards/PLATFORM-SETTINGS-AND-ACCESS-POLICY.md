# Platform Settings And Access Policy

**Status:** Standing policy, introduced by WC-137 (IB-138). Founder-directed: *"update required constitutional components ... so next agent knows this as policies instead of drifting or inventing new approach."*
**Applies to:** every office and agent that changes feature flags, per-environment values, staff roles, platform sign-in, or the WhatsApp visitor flow.
**Authority:** this standard records decisions; it grants no deployment, UAT, Production, spend, approval or merge authority. A change to any rule below needs a Work Contract and Founder authorization. Do not replace a mechanism here with a new one.

## 1. Per-environment values are data, never code

| Rule | Detail |
|---|---|
| S1 | A value that differs by environment (demo, uat, prod) is **data**. Code never branches on the environment name and a flag is never flipped by editing code. |
| S2 | The same images are promoted demo → uat → prod. Behaviour differs only through settings data. |
| S3 | Settings live in two layers, merged by `scripts/goal006_deployment_inputs.py` (`merge_environment_settings`): **base** `infrastructure/platform-settings/<environment>.json` (git, non-secret) and **override** the private blob `deployment-config/<environment>/workload-configuration.json`. The blob wins key by key. |
| S4 | The settings file is closed to two groups: `feature_settings` and `platform_access`. Anything else is rejected before Terraform. Secrets and image digests never go in it. |
| S5 | Absent means off. UAT and Production files stay `{}` until the Founder authorizes values in a PR. Demo values were authorized for IB-138 only. |
| S6 | Adding a flag: add it default-off to the closed key list in `goal006_deployment_inputs.py`, the matching workload Terraform variable and `feature-settings.tf`, read it through configuration in the service, and add a test. No environment-name conditionals. |
| S7 | The private blob is reachable only from the private runner. Never bypass that (no account key, SAS, public-network toggle or ad hoc privileged job; WC-124). To change a blob value, use the deployment path. |
| S8 | Founder-gated values (for example `wallet_authority: WALLET`, WhatsApp STOP acknowledgement) change in UAT or Production only with Founder authorization quoted in the PR. |
| S9 | WC-170 activation switches follow S6: `employment_protocol_enabled` (default off), `employment_protocol_rollback_epoch` (whole number, default 0; it is never reused and raising it blocks in-flight employment commands with evidence and rewrites no history) and `web_conversation_enabled` (default off; it becomes the web `WC120_CONVERSATION_ENABLED` setting). Demo values were authorized for WC-170 only; the Founder-only read-back is `GET /api/v1/admin/employment/readiness`. |

## 2. Roles and access

| Rule | Detail |
|---|---|
| A1 | A role comes only from a stored grant (verified email or `sub`) or from the Founder configuration. A token never carries its own role: staff routes reject a token with a `waooaw_roles` claim. |
| A2 | **Founder identity is the root of trust.** It is `platform_access.founders` in the settings data, re-asserted at every business-platform start as a `BOOTSTRAP` grant, so it survives database reset, upgrade and fresh deploy. A Founder grant is not revocable through the API. Founder email is identity, not a credential: sign-in is still required. The grant is tied to the first verified sign-in identity (`subject`) that matches the configured email, and a different identity gets nothing. A configured `subject` is enforced from the first sign-in. A Founder entry may set `rebind_on_start: true` (Demo only; never with a `subject`): every start then releases the stored tie, records `FOUNDER_SUBJECT_RELEASED`, and the next verified sign-in with the configured email ties it again, so a redeploy that changes the sign-in identity never locks the Founder out. UAT and production stay strict. |
| A3 | **Admins register themselves; they never grant themselves.** Flow: verified-email Access Request → Founder approval **with step-up** (`acr` level 2 and `otp` in `amr`) → stored grant. Self-approval is refused, one pending request per person, a daily request limit applies, a justification is required. Revoke needs no step-up. |
| A4 | Login screens do not change. The role is resolved after sign-in (`GET /api/v1/platform/me/roles`, 15 s cache). |
| A5 | Staff routes (`StaffIdentityRoute`) skip tenant isolation; customer routes take their tenant from database membership. Do not reintroduce a tenant claim for staff. |
| A6 | ASP.NET JwtBearer maps inbound claims. Code that reads `sub`, `email`, `acr` or `amr` must accept the mapped long names as well (see `PlatformRoles`). Unit tests with raw claims do not catch this; prove it against a real token. |
| A7 | Known gap, not fixed here: `IdentityController.HasLifecycleStepUp` and `AgentAdmissionsController.HasStepUp` read raw `acr`/`amr`. Fix them with A6 before relying on them. |
| A8 | Google and Facebook brokered sign-ins cannot step up. A Founder's first approval needs OTP enrolment first. |

## 3. WhatsApp visitor flow (Demo number)

| Rule | Detail |
|---|---|
| W1 | Order is fixed: **consent first** (Yes / STOP), then the promise stack and agent menu, then one agent card with four actions. One decision per message. |
| W2 | Copy lives in `src/business-platform/Catalog/Visitor/waooaw-demo.v1.json` and shared `GuestCopy`; the web chat reuses the consent copy. Changing consent wording bumps `noticeVersion`, which forces re-consent. |
| W3 | No logo image is sent. Agent icons are emoji. Agents beyond Digital Marketing are "coming soon" until a contract says otherwise. |
| W4 | STOP before Yes ends the chat; "Hi" restarts it. The STOP acknowledgement is flag-gated (`whatsapp_stop_acknowledgement_enabled`). |

## 4. Evidence rules

- Validate in Docker only. Staff and sign-in changes need a real-stack proof (real Keycloak token), not only unit tests: `scripts/keycloak_stepup_proof.sh` for step-up.
- Key Vault signing keys expire; a deployment failing with an expired key is renewed, not worked around (IB-137 RCA; renewed to 2027-02-19).
