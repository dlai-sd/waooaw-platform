# Razorpay Test Mode Runbook (Demo and UAT)

**Status:** WC-176 R015 to R018. Procedure and what the billing engine does with each Razorpay event.
**Owner of live KYC and live keys:** the Founder. Nothing here moves real money.

## Boundary

Demo and UAT use Razorpay **Test Mode** only. Live KYC, live keys and the switch to live payments stay with the
Founder; the billing engine refuses a charge in live mode unless the money gate is on (WC-172). The AI assistant never
receives, prints or stores a key or secret value, and never runs the check below with live credentials.

## Settings of each environment

| Setting | Where it lives | Value |
|---|---|---|
| `RAZORPAY_KEY_ID` | Key Vault secret `razorpay-test-key-id` | A key id beginning `rzp_test_` |
| `RAZORPAY_KEY_SECRET` | Key Vault secret `razorpay-test-key-secret` | Test Mode key secret |
| `RAZORPAY_WEBHOOK_SECRET` | Key Vault secret `razorpay-test-webhook-secret` | The secret typed in the Razorpay webhook form |
| `RAZORPAY_READINESS_STATE` | Terraform, billing engine environment | `READY_TEST` in Demo and UAT |
| `GST_LEGAL_NAME`, `GST_GSTIN`, `GST_ADDRESS`, `GST_STATE_CODE`, `GST_SAC_CODE`, `GST_RATE_PERCENT` | Terraform, billing engine environment (non-secret) | `DLAI Satellite Data (OPC) Pvt Ltd`, `27AAKCD8188R1ZH`, `C8, Everest Heights, Park Road, Viman Nagar, Pune 411014, Maharashtra, India`, `27`, `9984`, `18` |

`GST_SAC_CODE` is the default `9984`; the Founder's tax professional confirms it before real money. Production leaves
the GST settings unset until then, and with no identity the billing engine issues no invoice (a payment still succeeds
and the reconciliation reports it).

The three Razorpay values are already in the Demo vault. Values are entered by the account owner directly into the vault
(see [acceptance-sandbox-setup.md](./acceptance-sandbox-setup.md)), never in chat, a log or a command argument.

## Webhook registration (Razorpay dashboard, Test Mode)

1. Settings, Webhooks, Add new webhook.
2. URL: the environment's public API address followed by `/api/v1/payments/webhooks/razorpay`
   (Demo: `https://api.demo.waooaw.com/api/v1/payments/webhooks/razorpay`).
3. Secret: the value of `razorpay-test-webhook-secret`.
4. Events: `payment.captured`, `payment.failed`, `refund.processed`. Other events are acknowledged and ignored.

## What the billing engine does

| Event | Effect |
|---|---|
| `payment.captured` | The signature (HMAC-SHA256 of the raw body, constant-time comparison) is verified; the event id is recorded once; the capture is recorded durably as `RECEIVED` before anything else; then the same completion path the checkout confirmation uses runs (activation record, renewal, upgrade fee) and the capture becomes `COMPLETED`. The GST tax invoice (`WAOOAW/2026-27/000001`, next number per financial year, no gaps) is issued once per payment. A replay of the same event answers `replayed` and changes nothing. |
| `payment.failed` | Recorded. A failed renewal starts the policy grace period once. |
| `refund.processed` | Recorded; a full refund closes the capture as `REFUNDED`. The credit note comes from the lifecycle sweep. |

A webhook with no configured secret, or a bad signature, is refused with `INVALID_SIGNATURE` before anything is read.

## Nothing captured is lost: reconciliation

The billing engine runs the capture reconciliation every 15 minutes. To run it by hand inside the billing engine
container: `python -m payment.capture_reconciliation reconcile [--window-hours 48] [--stale-hours 24]`. It prints one
JSON report (`ingested`, `completed`, `invoiced`, `refund_due`, `unresolved`).

1. A payment Razorpay shows as captured that the webhook never delivered is recorded and completed.
2. A capture that failed to complete (browser closed, provider timeout) is completed again; the customer sees "we are
   completing your Hire" meanwhile.
3. A capture that can never complete (no customer, a conflicting order), or a hire payment with no completed Hire after
   `--stale-hours`, is marked `REFUND_DUE`. Refunds are issued by the Founder in the Razorpay dashboard or through the
   lifecycle refund path; `refund.processed` then closes the row. Rows in `REFUND_DUE` are the Founder's list to act on.

Recurring billing: the renewal sweep (every 15 minutes) opens one Razorpay order for each period ending within three
days, pays a renewal from pause credit without the provider when credit covers it, and starts the policy grace period
when a renewal is still unpaid at the period's end. Suspension follows the lifecycle sweep.

## Verify read-only before each run

```
docker compose --profile test-python run --rm \
  -e ACCEPTANCE_RAZORPAY_KEY_ID -e ACCEPTANCE_RAZORPAY_KEY_SECRET -e ACCEPTANCE_RAZORPAY_WEBHOOK_SECRET \
  -e GST_LEGAL_NAME -e GST_GSTIN -e GST_ADDRESS -e GST_STATE_CODE -e GST_SAC_CODE \
  test-runner-python python scripts/wc176_razorpay_readonly_check.py \
  --webhook-url https://api.demo.waooaw.com/api/v1/payments/webhooks/razorpay [--online]
```

The check reports `ok`, `fail` or `not-checked` for: a `rzp_test_` key id, the key and webhook secrets present, the
webhook address, the GST identity (GSTIN checksum) and, only with `--online`, one read-only GET of the payments list.
It prints no secret value and changes nothing at Razorpay. A `fail` stops the run; `not-checked` means that input was
not supplied. Run it before every Demo or UAT acceptance run and before the Founder's first live run.

## Founder's own steps (not done here)

Razorpay live KYC, live keys, the money gate for real money (WC-172), and the tax professional's confirmation of the SAC
code.
