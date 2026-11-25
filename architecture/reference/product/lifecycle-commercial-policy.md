# Lifecycle Commercial Policy (settles OP-LIFECYCLE-COMM-01)

**Decided by:** the Founder, 2026-11-25, in the WC-172 build session (D1 to D5 accepted as proposed).
**Implemented by:** `src/billing-engine/payment/lifecycle_policy.py`, `payment/lifecycle.py`, `payment/price_protection.py`,
`invoicing/` and the migration `infrastructure/postgres/init/99zzzzzzzz-wc172-01-lifecycle-tax-and-money.sql` (WC-172).
**Controlling documents:** [agent-employment-experience-contract.md](./agent-employment-experience-contract.md) (AEEC-06 to AEEC-09),
[ADR-022](../../../adr/ADR-022-payment-processing-razorpay-india.md) (Amendment 1.4, C-090), C-038, C-088, C-090.

Every rule below is a tested code path. A rule the Founder has not decided is not in this file.

## Rules

| Id | Situation | Rule | Where it is enforced |
|---|---|---|---|
| D1 | Pause | The unused days of the pause are **credited to the next invoice**, never refunded to the card. One pause lasts at most **30 days**, then the paused components come back. Emergency Stop never bills and is not a pause | `paused_fee_credit_paise`, `pause_window_end`, `LifecycleService._pause`, `resume_expired_pauses`; the credit is a `FEE_CREDIT` billing adjustment that `renew_paid` applies, oldest first, and a credit note records |
| D2 | Terminate | The customer may terminate on any day. **Service ends at the paid period end** with no mid-period refund, except a **documented service failure** (cited by its evidence id), which ends service now and refunds the unused fee pro rata. The evidence export stays downloadable for **90 days** after service ends. Nothing is deleted | `service_ends_at`, `export_available_until`, `LifecycleService._terminate`, `finalize_terminations`; a terminating relationship cannot renew (`RELATIONSHIP_TERMINATING`) |
| D3 | Renewal price | The **locked price renews unchanged**. A catalogue price change reaches an existing hire only after **30 days' notice and the customer's acknowledgement** (ADR-022 Amendment 1.4, C-090); otherwise the old price continues | `PriceProtection.notify`, `acknowledge`, `applicable_version`, `require_change_allowed`; `LifecycleService._renewal_terms` |
| D4 | Amend | An **upgrade is charged pro rata at once**; a **downgrade takes effect at the next period**. Each is evidenced by an invoice line or a credit note | `upgrade_fee_difference_paise`, `LifecycleService._change_package` (reads the POLICY `upgrade_timing` and `downgrade_timing`; `decisions_match` states the Founder's values) |
| D5 | Payer and funder | The **payer is the signed-in account holder**. A **funder** (another account) is allowed only with the funder's own acceptance and a billing profile (C-088). The invoice names the payer. A charge with no known payer is refused | `TaxDocumentService.issue_for_payment` (`PAYER_UNKNOWN`, `FUNDER_NOT_ACCEPTED`), tables `billing_profiles`, `funder_acceptances` |

## Rules this policy adds so the books are provable

| Rule | Where |
|---|---|
| Every captured payment has one GST tax invoice and every refund or credit one credit note, numbered without gaps per series and financial year (`WAOOAW/2026-27/000042`, `WAOOAW/CN/2026-27/000042`), with the exact paise split and the place of supply | `invoicing/service.py`, `invoicing/tax.py` |
| A document is immutable; a correction is a credit note followed by a new invoice | database trigger `tax_documents_immutable` |
| A hire created before the quote lock has no period and is refused at renewal; it is never silently migrated, and the customer is asked to accept again | `LifecycleService.renew_paid` (`NO_ACTIVE_PERIOD`) |
| A failed renewal payment follows the saga with the POLICY `payment_grace_days`; after the grace the relationship is suspended and its credit lapses | `record_payment_failure`, `suspend_expired_grace` |

## What is not decided here

| Item | Owner |
|---|---|
| WAOOAW's registered address, SAC confirmation and invoice series start (D6) and the tax professional's confirmation | Founder |
| How a customer asks for a service-failure termination (today an operator cites the evidence id) | Founder, a later iteration |
| Customer screens for credit and export dates | Business Platform and web, a later iteration |
