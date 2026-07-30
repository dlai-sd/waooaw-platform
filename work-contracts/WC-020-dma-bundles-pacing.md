# Work Contract 020 — GOAL-004: DMA Bundle Profiles + Pacing Choice

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 020 | **Goal:** GOAL-004 | **Depends on:** WC-018 + WC-019 complete
**Spec:** dma-bundle-definitions.md, wbe-component-spec.md §2.1
**Constitutional Basis:** C-059, C-076, C-088, C-090, ADR-034

## Tasks
| Task | Scope | model_hint |
|---|---|---|
| WC020-01 | Seed DMA bundle profiles to institutional.bundle_profiles with rations from D-05 | `reasoning` |
| WC020-02 | `wallet/service.py`: activate_subscription() — atomic wallet + 7 buckets + mode flip | `reasoning` |
| WC020-03 | `wallet/service.py`: pacing_preference enforcement (SPREAD weekly cap; BURST no cap) | `standard` |
| WC020-04 | `wallet/router.py`: POST /subscriptions/activate + POST /subscriptions/renew + C-090 check | `standard` |
| WC020-05 | Tests ≥90%: Starter activates 7 buckets; SPREAD enforces weekly cap; C-090 blocks unauthorized price increase | `standard` |

## Definition of Done
- POST /subscriptions/activate for DMA Starter → 7 wallet buckets created
- Customer mode flipped to LIVE before subscription object fully created (race condition fix)
- C-090: renew rejects if Razorpay plan price > agreed_monthly_price_paise without acknowledged notice
