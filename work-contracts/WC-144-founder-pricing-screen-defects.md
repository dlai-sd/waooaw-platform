# WC-144 - Founder Pricing Screen Defects And Honest Unavailable State

## Record Control

| Field | Value |
|---|---|
| Work Contract | WC-144 |
| Authoring office | Platform IT Expert (INST-010), under Founder assignment in the current conversation (lightweight record; the Founder may re-assign the number or office) |
| Initiative | IB-144 |
| Founder assignment | Current conversation: "fix defects you see on this screen" for `/admin/pricing`, "UI need to follow existing styling", and "ensure we have reusable api which will be used by whatsapp interface and on mobile app" |
| Status | IMPLEMENTED - FOUNDER REVIEW PENDING. Evidence is in the PR body at the exact head |
| Baseline | `origin/main` `d33956fa` |
| Related contracts | WC-134 and CB-021 (Business Platform to Billing workload credentials, the cause of the unavailable state); ADR-046 |
| Requirement ledger | [WC-144-requirements.yaml](./WC-144-requirements.yaml) |
| Constitutional basis | C-059, C-063 |

## Problem And Evidence

The Founder reported defects on `cp.demo.waooaw.com/admin/pricing` in three screenshots:

1. The eight section links render as a bulleted vertical list.
2. The heading rule is shorter than the cards below it.
3. The error is bare small red text.
4. Three Safety-control forms repeat the same hint sentence, and the Safety controls and Export and import cards touch each other.
5. Inputs, selects, the file input and the textarea use browser styling and inconsistent widths; the Export button stretches while the Import fields do not.

Separately, the page shows "Live margin could not be loaded". Demo logs show the web app logging `web.admin.pricing.live_margin_failed` with HTTP 503 and Business Platform logging `PricingAdminOwnerUnavailableException: The authenticated WBE pricing owner is not configured.` The Demo `ca-demo-business-platform` app has no `WAOOAW_WORKLOAD_CREDENTIALS` and no `BillingEngine__*` settings, so `UnconfiguredPricingAdminGateway` answers every pricing call. This is the open CB-021 gap and is not a screen defect.

## Authority And Scope

### In scope

1. Pricing screens use the existing portal tokens and button styles: a wrapping tab bar, a full-width heading rule, themed form controls, and sub-cards in a responsive grid, in both light and dark themes.
2. The live margin error is a bordered alert using `--color-error`; on HTTP 503 it states that the pricing service is not connected in this environment, instead of leaving the cause unknown.
3. Each Safety-control form carries its own hint.

### Out of scope (each needs its own Work Contract)

- Provisioning the Business Platform to Billing workload credential and URL, which is what makes margin and every other pricing call work on Demo (CB-021, ADR-046; Terraform under `modules/workload/` also needs the runtime lifecycle gate).
- The Founder-managed provider and credential registry with Test, Confirm and save, versioned Key Vault secret, rollback and live use without redeploy. It depends on the Business Platform to Billing channel.
- The payer (funder) model for LLM and API cost, agency and channel-partner billing, and tax invoice breakups. The scan found the data model and GST tables exist but no end-to-end payer flow.
- Reusable API principle for those later contracts: one channel-neutral, versioned, OpenAPI-described Business Platform API consumed by the web app, WhatsApp and any later mobile app. This contract changes no API; the existing pricing administration API is already that surface and the web app only consumes it.

## Canonical Requirement Index

Each row is one normative obligation. The ledger `WC-144-requirements.yaml` binds to this file's complete SHA-256 digest; any edit of this file after the ledger is written requires a new digest.

| ID | Obligation |
|---|---|
| WC144-R001 | The pricing page frame renders its section links as a wrapping tab bar using `primary-command` for the current page and `secondary-link` for the others, with `aria-current` preserved |
| WC144-R002 | A failed live margin load renders an alert; when the failure status is 503 it also says the pricing service is not connected in this environment |
| WC144-R003 | Each of the three Safety-control forms shows its own hint, and every hint still states that the action takes effect now |
| WC144-R004 | Pricing form controls, sub-card grid, heading rule and error alert are styled only with existing design tokens, scoped to `.pricing-admin`, and no type size is changed |
| WC144-R005 | No API contract, generated client or Business Platform code changes; the root cause of the 503 is recorded and not hidden |

## Implementation Record

Evidence at the exact head (commands and results) is in the PR body. The layout was also rendered with the real stylesheet in a headless browser in light, dark and mobile widths and inspected by the author; the screenshots are not committed.
