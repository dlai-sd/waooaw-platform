# Go-Live Checklist - Taking Real Money (WC-172 Epic G, R015 to R017)

**Status of this document:** the author prepares and maintains it; **only the Founder may mark a row `DONE`** after he has
seen the evidence. No pull request, deployment or ledger row grants permission to take real money. Real money stays off
in every environment until the Founder records written go-live approval (row G-23) and the capped rehearsal (row G-24)
has been read back.

**Rules this list enforces:** live Razorpay keys are entered by the Founder into the production vault and are never read,
printed or seeded by the author or by a GitHub-hosted runner (`tests/pipeline/test_wc172_money_and_identity_guards.py`
proves no hosted workflow job reads a production vault). The real-money gate (`real_money_enabled`) is off by default,
can be turned on only in production, in LIVE mode, by the Founder's step-up action, and can be turned off at once
(`payment.money_gate`, `wbeSetMoneyGate`).

Status values: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`. A row marked `DONE` names its evidence.

| Id | Prerequisite | Owner | Status | Evidence |
|---|---|---|---|---|
| G-01 | GST identity supplied: legal name, GSTIN, registered address, state, SAC, invoice series start (decision D6) | Founder | IN_PROGRESS | GSTIN 27AAKCD8188R1ZH is recorded in AGENT-ENTRY; address, SAC confirmation and series start are still to be given; set as `GST_*` settings per environment |
| G-02 | Tax professional confirms the invoice and credit note format, numbering and SAC | Founder | NOT_STARTED | pending |
| G-03 | Production vault `kv-waooaw-prod` exists, is private, and is unreachable from a GitHub-hosted runner | Platform IT Expert | NOT_STARTED | reviewed Terraform plan; the hosted-runner guard test |
| G-04 | Production managed identities and role assignments reviewed (no shared tokens carry authority) | Platform IT Expert | NOT_STARTED | pending |
| G-05 | ADR-046 cloud workload credentials qualified on UAT and on production; Demo interim certificate exception retired or extended in writing before 2026-12-16 | Platform IT Expert | NOT_STARTED | CB-021 closure evidence |
| G-06 | `BP_SERVICE_JWT_SECRET`, `PR_SERVICE_JWT_SECRET` and `OPS_AUTH_TOKEN` removed from governed routes in every environment | Platform IT Expert | IN_PROGRESS | `test_the_remaining_uses_of_the_shared_tokens_are_exactly_the_recorded_ones` enumerates what is left |
| G-07 | Razorpay live account verified (KYC complete) and live webhook registered | Founder | NOT_STARTED | pending |
| G-08 | Live Razorpay keys entered into the production vault by the Founder only | Founder | NOT_STARTED | the Founder's confirmation; the author never sees a key |
| G-09 | Production starts in LIVE mode with the real-money gate closed; a test key is refused at startup | Platform IT Expert | IN_PROGRESS | `payment.money_mode` startup guard and its tests; production read-back pending |
| G-10 | Meta production app, Business Verification and Advanced Access (App Review) | Founder | NOT_STARTED | submission and result dates entered by the Founder |
| G-11 | WhatsApp production number registered and utility template approved | Founder | NOT_STARTED | WhatsApp Manager screenshot |
| G-12 | Decision D7 recorded: closed beta of named customers added as app Testers until App Review passes | Founder | DONE | Founder, 2026-11-25: option A |
| G-13 | GitHub environment protections and reviewer lists for UAT and production | Founder | NOT_STARTED | repository settings read-back |
| G-14 | Rollback and freeze plan written and rehearsed | Platform IT Expert | NOT_STARTED | pending |
| G-15 | Monitoring and paging for payments, reconciliation discrepancies and the real-money gate | Platform IT Expert | NOT_STARTED | pending |
| G-16 | UAT provisioned from reviewed Terraform with the Founder's approval; CB-018, CB-019, CB-020 closed or owned | Platform IT Expert | NOT_STARTED | the Founder's apply approval and Environment Deployment runs |
| G-17 | Demo to UAT configuration promotion exercised | Platform IT Expert | NOT_STARTED | deployment run |
| G-18 | Release qualification passes on UAT | Platform IT Expert | NOT_STARTED | deployment run |
| G-19 | UAT journey (discover, hire, pay in test mode, connect, work, alert, pause, resume, amend, renew, terminate, export, invoice, credit note, reconcile) with one calibration report and an owner for every NOT-WITNESSED or FAIL item | Platform IT Expert | NOT_STARTED | calibration report |
| G-20 | Reconciliation clean on UAT for 7 consecutive days | Platform IT Expert | NOT_STARTED | discrepancy list read-back |
| G-21 | Founder step-up proven: the gate refuses to open without it and in any non-production environment | Platform IT Expert | IN_PROGRESS | `test_only_a_step_up_in_production_can_turn_real_money_on_and_off_needs_none`; Demo read-back pending |
| G-22 | Evidence owner verification and route grants answer on Demo: a forged spend evidence id is refused, an unlisted caller is refused | Platform IT Expert | NOT_STARTED | Demo read-back |
| G-23 | **Founder's written go-live approval** | Founder | NOT_STARTED | the Founder's written words |
| G-24 | Capped rehearsal: the Founder's own card, a small amount, then a full refund and credit note, every record read back, then the gate is turned off or left on by the Founder | Founder | NOT_STARTED | read-back of the invoice, the refund, the credit note and the gate audit record |
