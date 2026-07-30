# Work Contract 023 — GOAL-004: Single Onboarding Payment + Renewal Failure Saga

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 023 | **Goal:** GOAL-004 | **Depends on:** WC-018 + WC-020 complete
**Spec:** ADR-022 Amendment §1.2 + §1.3 + §1.4, wbe-component-spec.md
**Constitutional Basis:** C-049, C-059, C-076, C-090, ADR-022 Amendment, ADR-034

## Tasks
| Task | Scope | model_hint |
|---|---|---|
| WC023-01 | `razorpay-mcp` extension: create_onboarding_order() bundles subscription + wallet seed amount in one Razorpay Order | `reasoning` |
| WC023-02 | payment.captured webhook: atomic activation at payment_intent CONFIRMED; mode flip before subscription creation | `reasoning` |
| WC023-03 | C-090 enforcement: compare Razorpay plan price vs agreed_monthly_price_paise at renewal; block without acknowledged notice | `reasoning` |
| WC023-04 | Temporal saga: RenewalFailureSaga — Day1/Day3/Day7/Day14 states; campaign pause gate at Day7 with rollback | `reasoning` |
| WC023-05 | Tests ≥90%: single payment activates wallet+subscription; saga state transitions; Day7 saga rollback on Meta pause failure | `standard` |

## Definition of Done
- CCT-ONBOARD-01: POST /subscriptions/activate ≤500ms; total UPI-to-LIVE ≤90s
- Campaign pause failure at Day7 rolls back billing suspension (saga compensating transaction)
- C-049: agent discloses reduced mode on Day3+ (tested via mock agent response)
