# Acceptance Sandbox Setup Runbook

**Status:** PROPOSED with WC-157. Procedure only; nothing here has been executed.
**Decisions:** ADR-054, ADR-055. **Architecture:** `customer-journey-acceptance-architecture.md` section 5.

## Boundary

This runbook describes how the Founder provides sandbox credentials for customer journey acceptance. It does
not authorize Azure resource changes, deployment, Production use, or any live-mode provider credential.
Values are entered by the account owner directly into the environment's acceptance Azure Key Vault (WC-164). The AI assistant
never receives, prints or stores a value.

## Who does what

| Actor | Does |
|---|---|
| Founder | Signs in to the Razorpay, Meta and WhatsApp dashboards (account-owner-only actions), creates the sandbox objects below, and runs the Key Vault commands with the values. |
| AI assistant | Provides these steps, builds the readiness check (WC-161) that confirms each secret exists and is in test mode without printing it, and builds the harness. |
| Platform | The acceptance Key Vault name comes from the environment profile in git (non-secret). |

## Rules

1. **Test or development mode only.** A credential that is not a sandbox credential must not be stored.
   The readiness check rejects a Razorpay key id that does not begin `rzp_test_`.
2. **One set per environment.** Demo and UAT each have their own vault entries; never reuse a value.
3. **Names are fixed** and carry the `acceptance-` prefix so the acceptance identity can read only these.
4. **Never paste a value into chat, an issue, a pull request, a log or a shell argument.** Use the seed script
   (step 4) so values stay out of shell history.

## Secret register

| Key Vault secret | Content | Source |
|---|---|---|
| `acceptance-meta-app-id` | Development-mode app id | Meta for Developers, the acceptance app |
| `acceptance-meta-app-secret` | App secret | Same |
| `acceptance-meta-test-user-session` | Saved browser session state for the Meta test user | Produced once by the harness login helper (WC-160) |
| `acceptance-meta-test-page-id` | Id of the test user's test Page | Meta Graph or Page settings |
| `acceptance-meta-test-page-token` | Access token for that test Page, used only to read and delete the post the slice 2 run publishes | Meta Graph API Explorer or Page settings, as the test user, with `pages_read_engagement` and `pages_manage_posts` |
| `acceptance-demo-coupon-code` | A test coupon code in the environment that gives a partial discount on the Digital Marketing hire, used only to validate the payable amount (never to pay) | Created by the Founder on the pricing admin screen |
| `acceptance-whatsapp-sandbox-recipient` | Verified test recipient number (E.164) | Founder-controlled test handset |
| `acceptance-whatsapp-webhook-secret` | App secret used to sign inbound webhook deliveries to this environment | Same Meta app that owns the environment's WhatsApp number (ADR-053) |
| `acceptance-keycloak-provisioner-client-secret` | Client secret for the `waooaw-acceptance-provisioner` client | Generated unseen by `scripts/acceptance_seed_secrets.sh keycloak-secret` (WC-167); the Founder enters no value. The Keycloak migration job reads it from this vault when the Demo realm is imported, so run the command before the Demo deployment that enables the provisioning client |

The three existing Razorpay test secrets are reused by exact name and need no entry.

## Procedure

### 1. Razorpay test mode: copy three existing values

Demo already wires `razorpay-test-key-id`, `razorpay-test-key-secret` and `razorpay-test-webhook-secret`
from its private Key Vault into the Billing Engine. The acceptance identity reads the same three names from the
acceptance vault, so the Founder copies those three test values into it (step 4 stores them without printing them). The harness
delivers its own signed webhook replays, so no new Razorpay value is created. If a
dashboard check is wanted, confirm the dashboard is in **Test Mode**. Test payments use Razorpay's published
test card numbers for success and for decline; the journey names the scenario, not the number.

### 2. Meta development-mode app

1. In Meta for Developers, use a dedicated app for acceptance (do not reuse the production app). Keep it in
   **Development mode**.
2. Add Facebook Login for Business or Facebook Login as the product WC-149's connection flow requires, and
   set the valid redirect address to the environment's web callback route (from the environment profile).
3. Under App Roles, create a **Test User**. Using that test user, create a **test Page**.
4. Record the app id, app secret and test Page id.
5. The saved test-user session is produced once by the harness helper and stored by step 4.
6. The product itself must hold the same Meta app: sign in as Founder and enter the app id and secret on the
   `meta` row of the Founder provider screen (WC-149), then press Test. Without it the connect step reports
   `BLOCKED-BY-FLAG` ("Meta provider not registered").

### 3. WhatsApp sandbox

1. Use the environment's dedicated WhatsApp number already governed by ADR-053; do not buy another.
2. Add a Founder-controlled handset as a **verified test recipient** for outbound messages.
3. Inbound behaviour (including STOP) is exercised by the harness delivering signed webhooks to the
   environment's own endpoint; no handset needs to reply.

### 4. Store every value once, without exposing any (WC-165)

After the foundation apply has created `kv-waooaw-demo-acc` and your object id is in `acceptance_vault_secret_officers`:

```bash
scripts/acceptance_seed_secrets.sh login   # once: Azure device-code sign-in
scripts/acceptance_seed_secrets.sh init    # creates /workspaces/.acceptance-secrets.env (mode 600, outside every repository)
```

Open that file, paste each value after its `=` (leave a line empty to skip it; `@/path/to/file` reads a value from a file,
useful for the saved Meta session), save, then run:

```bash
scripts/acceptance_seed_secrets.sh seed    # stores each value, deletes the file, then lists the names now present
```

The script runs the Azure CLI in Docker and sends each value through stdin, so no value is printed, logged, put in a
command line or committed. It keeps an existing secret unless `--overwrite` is given, refuses a Razorpay key id that does
not begin `rzp_test_`, refuses unknown keys or a file others can read, and keeps the file if anything failed. The
template has no Keycloak line: that secret is created in step 6. `status` lists the names in the vault.

Razorpay: the three values are the same Demo test values the Billing Engine uses. The private environment vault cannot be
read from a Codespace, so copy them from wherever you hold them (Razorpay dashboard in Test Mode) into the template.

### 5. Confirm

When WC-161 exists, its read-only check reports for each secret: present, non-empty, in test mode. It never
prints a value. Until then, `az keyvault secret list --vault-name <vault> --query "[?starts_with(name,'acceptance-')].name"`
lists names only.

### 6. Enable the acceptance identity and the provisioning client (after WC-158 to WC-160 merge)

These are Founder-authorized applies; nothing in the repository applies them.

1. Terraform: set `acceptance_enabled = true` in `environments/<env>/foundation/main.tf` (Demo and UAT only; the
   module refuses other environments) and run the normal foundation plan and apply. It creates the identity
   `id-waooaw-<env>-acceptance` federated to `refs/heads/main` with read-only access to exactly the secret names
   listed in that file, Reader on the resource group and Monitoring Reader on the workspace. Copy the
   `acceptance_client_id` output into `validation/acceptance/environments/<env>.yaml` (`azure.acceptance_client_id`);
   the workflow refuses to run while it is null.
2. Keycloak (Demo): run `scripts/acceptance_seed_secrets.sh keycloak-secret`, then run the Demo deployment. With
   `acceptance_provisioner_enabled` true in the Demo workload root, the realm import adds the client, service account,
   realm role `acceptance-provisioner`, group `synthetic` and admin events from
   `infrastructure/keycloak/acceptance-provisioner.realm-fragment.json`, with the secret read from the acceptance vault.
3. Business Platform: set the feature setting `acceptance_synthetic_tenants_enabled` to true for that environment
   through the settings path. Production refuses it.

**Access path (decided in WC-164):** the environment Key Vault is private (`public_network_access_enabled = false`), so a
GitHub-hosted runner cannot read it. The acceptance run reads a separate vault, `kv-waooaw-<env>-acc`, that holds only sandbox
and test values and is protected by access rights alone: only the acceptance identity (federated to `main`) reads it, and
only the principals listed in `acceptance_vault_secret_officers` write to it. Set `acceptance_vault_enabled = true` (with
`acceptance_enabled = true`) in the same foundation apply. The private vault is unchanged. Because the vault is separate, the
three Razorpay test values are **copied** into it (see step 1 below); the Billing Engine keeps using its own copies.

## Rotation and removal

Rotate by storing a new version under the same name; the harness reads the latest. To withdraw the
capability, disable the workflow and the acceptance identity (ADR-055); delete the `acceptance-` secrets.
