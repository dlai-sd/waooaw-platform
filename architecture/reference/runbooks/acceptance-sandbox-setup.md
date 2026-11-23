# Acceptance Sandbox Setup Runbook

**Status:** PROPOSED with WC-157. Procedure only; nothing here has been executed.
**Decisions:** ADR-054, ADR-055. **Architecture:** `customer-journey-acceptance-architecture.md` section 5.

## Boundary

This runbook describes how the Founder provides sandbox credentials for customer journey acceptance. It does
not authorize Azure resource changes, deployment, Production use, or any live-mode provider credential.
Values are entered by the account owner directly into the environment's Azure Key Vault. The AI assistant
never receives, prints or stores a value.

## Who does what

| Actor | Does |
|---|---|
| Founder | Signs in to the Razorpay, Meta and WhatsApp dashboards (account-owner-only actions), creates the sandbox objects below, and runs the Key Vault commands with the values. |
| AI assistant | Provides these steps, builds the readiness check (WC-161) that confirms each secret exists and is in test mode without printing it, and builds the harness. |
| Platform | Environment Key Vault name comes from the environment profile in git (non-secret). |

## Rules

1. **Test or development mode only.** A credential that is not a sandbox credential must not be stored.
   The readiness check rejects a Razorpay key id that does not begin `rzp_test_`.
2. **One set per environment.** Demo and UAT each have their own vault entries; never reuse a value.
3. **Names are fixed** and carry the `acceptance-` prefix so the acceptance identity can read only these.
4. **Never paste a value into chat, an issue, a pull request, a log or a shell argument.** Use the prompt
   method below so values stay out of shell history.

## Secret register

| Key Vault secret | Content | Source |
|---|---|---|
| `acceptance-razorpay-key-id` | Test key id | Razorpay dashboard, Test Mode, Account & Settings, API Keys |
| `acceptance-razorpay-key-secret` | Test key secret | Same |
| `acceptance-razorpay-webhook-secret` | Webhook signing secret for the environment's test webhook | Razorpay dashboard, Test Mode, Webhooks |
| `acceptance-meta-app-id` | Development-mode app id | Meta for Developers, the acceptance app |
| `acceptance-meta-app-secret` | App secret | Same |
| `acceptance-meta-test-user-session` | Saved browser session state for the Meta test user | Produced once by the harness login helper (WC-160) |
| `acceptance-meta-test-page-id` | Id of the test user's test Page | Meta Graph or Page settings |
| `acceptance-whatsapp-sandbox-recipient` | Verified test recipient number (E.164) | Founder-controlled test handset |
| `acceptance-whatsapp-webhook-secret` | App secret used to sign inbound webhook deliveries to this environment | Same Meta app that owns the environment's WhatsApp number (ADR-053) |
| `acceptance-keycloak-provisioner-client-secret` | Client secret for the group-limited provisioning client | Created with WC-159 |

## Procedure

### 1. Razorpay test mode

1. Sign in to the Razorpay dashboard and switch to **Test Mode**.
2. Generate a test API key pair. Record nothing outside the vault.
3. Create a test webhook pointing at the environment's payment callback address (from the environment
   profile), choose a signing secret, and subscribe to the payment and order events the product consumes.
4. Test payments use Razorpay's published test card numbers for success and for decline; the journey names
   the scenario, not the number.

### 2. Meta development-mode app

1. In Meta for Developers, use a dedicated app for acceptance (do not reuse the production app). Keep it in
   **Development mode**.
2. Add Facebook Login for Business or Facebook Login as the product WC-149's connection flow requires, and
   set the valid redirect address to the environment's web callback route (from the environment profile).
3. Under App Roles, create a **Test User**. Using that test user, create a **test Page**.
4. Record the app id, app secret and test Page id.
5. The saved test-user session is produced once by the harness helper and stored by the same prompt method.

### 3. WhatsApp sandbox

1. Use the environment's dedicated WhatsApp number already governed by ADR-053; do not buy another.
2. Add a Founder-controlled handset as a **verified test recipient** for outbound messages.
3. Inbound behaviour (including STOP) is exercised by the harness delivering signed webhooks to the
   environment's own endpoint; no handset needs to reply.

### 4. Store a value without exposing it

Run once per secret, replacing the vault name and secret name. The prompt hides the input and nothing is
written to shell history:

```bash
read -rs -p "Value for acceptance-razorpay-key-id: " v; echo
printf '%s' "$v" | az keyvault secret set \
  --vault-name "<environment key vault from the profile>" \
  --name acceptance-razorpay-key-id --file /dev/stdin --output none
unset v
```

### 5. Confirm

When WC-161 exists, its read-only check reports for each secret: present, non-empty, in test mode. It never
prints a value. Until then, `az keyvault secret list --vault-name <vault> --query "[?starts_with(name,'acceptance-')].name"`
lists names only.

## Rotation and removal

Rotate by storing a new version under the same name; the harness reads the latest. To withdraw the
capability, disable the workflow and the acceptance identity (ADR-055); delete the `acceptance-` secrets.
