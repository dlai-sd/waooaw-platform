# WC-137 - Platform Access And Environment Feature Settings

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-137 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-138 |
| Founder assignment | Current conversation: "i want waooaw customer to have access to new features we added in 604 including ui and different roles"; scope additions: WhatsApp consent-first greeting flow; authorization to include the WhatsApp STOP acknowledgement and `WALLET_AUTHORITY=WALLET` |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `99cd8471` (WC-136 merged) |
| Related contracts | WC-123 identity; WC-124 private configuration; WC-134 WhatsApp; WC-135 visitor conversation; WC-136 workbench and pricing console |
| Requirement ledger | [WC-137-requirements.yaml](./WC-137-requirements.yaml) |
| Standing policy | [PLATFORM-SETTINGS-AND-ACCESS-POLICY](../standards/PLATFORM-SETTINGS-AND-ACCESS-POLICY.md) - the rules every later agent follows |
| Constitutional basis | C-001, C-009, C-023, C-036, C-059, C-063, C-088; ADR-046 |

## Authority And Scope

### In scope

1. Per-environment feature settings (data, not code), merged from a repository file under the private deployment blob.
2. Platform roles: stored grants, Founder-from-configuration root of trust, Access Request and Founder approval with step-up.
3. Fixes found by real-stack proof: staff routes reachable for web tokens; JwtBearer claim mapping for `sub`, `email`, `acr`, `amr`.
4. Keycloak step-up (OTP, `acr` 2) in the realm.
5. Web: request-access page, Founder approvals page, role-gated layouts and pricing console.
6. WhatsApp Demo flow: consent first, then menu, then agent card.
7. Demo values: workbench on, wallet authority `WALLET`, trial binding `RECORD`, STOP acknowledgement on, Founder named.

### Out of scope (each needs separate Founder authorization)

- Any UAT or Production value (both settings files are `{}`).
- Editing the private Demo blob, or any bypass of its private network (WC-124).
- Real-phone WhatsApp acceptance, proactive sends, the logo image.
- Fixing `IdentityController.HasLifecycleStepUp` and `AgentAdmissionsController.HasStepUp` (same claim-mapping gap; recorded in the policy as A7).
- Deployment, approval and merge.

## Rollout And Runbook

1. Merge, then the Founder runs the Demo deployment. Every Demo apply recreates the databases and re-imports the Keycloak realm; running Keycloak replicas restart afterwards. Founder grants are re-asserted from configuration at business-platform start.
2. Founder first sign-in: open the approvals page, enrol OTP when asked (two passes the first time), then approve pending admin requests.
3. To turn a flag on or off in an environment: edit that environment's settings file (or the private blob through the deployment path) in a Founder-authorized PR. Never edit code.
4. UAT and Production adopt a value only when the Founder authorizes it in a PR. Images are the same across environments.
5. The Key Vault signing key was renewed to 2027-02-19 under IB-137; renew again before then.

## Founder Authorization (quoted)

> "Not in this PR: the WhatsApp STOP acknowledgement stays off (needs the privacy check), `WALLET_AUTHORITY=WALLET` stays Founder-gated, and I won't touch UAT or Prod values. - include this acknowledgement in pr and here is my authorization"

Reading applied by the implementer: the authorization covers **Demo only**. UAT and Production are untouched. If the Founder meant more, it is a data-only change to the settings files.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-137-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC137-R001 | Feature settings are per-environment data validated before Terraform and delivered to the workload without code changes |
| WC137-R002 | A repository settings file per environment is merged under the private blob, the blob wins key by key, the file is closed to `feature_settings` and `platform_access`, and UAT and Production stay empty |
| WC137-R003 | Roles come only from stored grants and the Founder configuration; the Founder grant is re-asserted at every start and survives reset and fresh deploy |
| WC137-R004 | Admins register by Access Request; approval needs a different Founder with step-up; abuse controls (verified email, justification, one pending, daily limit) apply |
| WC137-R005 | Staff routes are reachable with a web token and refuse tokens that claim their own roles |
| WC137-R006 | Claims mapped by JwtBearer (`sub`, `email`, `acr`, `amr`) are recognised for roles and step-up |
| WC137-R007 | The Keycloak realm issues an OTP step-up (`acr` 2) and it is proven against the Demo realm |
| WC137-R008 | The web shows request-access and Founder approvals and gates staff layouts and the pricing console by role |
| WC137-R009 | The WhatsApp Demo flow is consent first, then menu, then agent card, with a versioned consent notice and flag-gated STOP acknowledgement |
| WC137-R010 | The standing policy is published and routed from the agent entry point |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. Real-stack proof: 41 of 41 checks passed against a compose stack with real Keycloak tokens (customer, Founder from configuration, admin registration, approval with real step-up, revoke, restart and wiped-grants re-assertion). Not provable locally: a real-phone WhatsApp test.
