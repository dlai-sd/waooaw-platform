# Work Contract 021 — GOAL-004: Usage Meter + Alert + Proactive Offer Engine

**Office:** WAOOAW AI Agent — Platform IT Expert (INST-010)
**Sprint:** 021 | **Goal:** GOAL-004 | **Depends on:** WC-018 complete
**Spec:** wbe-component-spec.md §2.3
**Constitutional Basis:** C-049, C-051, C-059, C-076, ADR-034

## Tasks
| Task | Scope | model_hint |
|---|---|---|
| WC021-01 | `meter/service.py`: record_usage(), project_depletion() 7-day velocity, check_thresholds() | `reasoning` |
| WC021-02 | `meter/alert_policy.py`: 50/60/85/95 thresholds; quiet hours 23:00–07:00 IST hold/send | `reasoning` |
| WC021-03 | `meter/proactive_offer.py`: daily scan at 06:00 IST; seasonal calendar; offer generation | `reasoning` |
| WC021-04 | `meter/whatsapp_notifier.py`: C-049 language (no tech terms, no provider names); BSP send | `standard` |
| WC021-05 | Tests ≥90%: 50% alert fires; 85% bypasses quiet hours; proactive offer on <50% days remaining | `standard` |

## Definition of Done
- CCT-BILLINGLOOP-01: S-02 scenario (new month zero gap) simulated and alert fires correctly
- Quiet hours: 50%/60% alerts held 23:00–07:00; 85%+ alerts immediate regardless
- Proactive offer generated when velocity projects < 50% days remaining
