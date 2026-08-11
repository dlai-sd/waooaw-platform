# Work Contract 058 — AE-01 Discover, Interview, Trial, and Configure

**Goal:** GOAL-005 · **Epic stories:** AE-01-S01 through S06
**Office on execution:** Platform IT Expert (INST-010)
**Reviewer:** Product Owner (INST-011) + Business Architect (INST-003)
**Status:** COMPLETE — IMPLEMENTATION EVIDENCE PUBLISHED; R-078 AND R-079 APPROVED
**Authorization:** FA-038; GEP-GOAL-005-INST-013-07; R-077; ACK-GOAL-005-INST-001-07; GOA-GOAL-005-INST-010-04; ACC-GOAL-005-INST-010-04
**Track:** VERTICAL CUSTOMER OUTCOME
**Service scope:** BP (.NET), PR/AIR/WBE (Python), web, ADR-023 WhatsApp identity

## Sprint Goal

Deliver the complete informed evaluation journey from a business need to an accepted configuration. First proof is a WhatsApp-first DMA trial spanning 14 calendar days, all declared DMA skills, zero paid APIs, and zero consequential external action.

## Dependencies

WC-057 DONE; WC-031–033 and WC-040–041 DONE; D-06 DMA synthesis and Product Attestation accepted. No dependency on coupons, referral promotion, or Founder admin tooling.

The generic journey consumes the normative D-06 Professional Evaluation Adapter. DMA is one domain-owned adapter; shared BP/PR/WBE/web code must contain zero DMA-specific branches.

## Tasks

| Task | Scope | Model hint | Status |
|---|---|---|---|
| WC058-01 | Add versioned professional disclosure/catalog projection in BP from approved agent/skill specifications: suitability, skills, limitations, authority needs, rights, trial capability, evidence posture, indicative price, and eligibility controls. Add outcome-based discovery endpoint; no preferred-customer scoring. | reasoning | done |
| WC058-02 | Implement the D-06 Solution Contract evaluation state machine and typed answer envelope through PAAS/Skill Runtime. Enforce server-assigned tags, source/uncertainty rules, injection/PII gates, validation-to-limitation fallback, evidence references, and payload-store separation. DMA expertise is supplied only through the domain adapter. | reasoning | done |
| WC058-03 | Apply the exact Migration 20 blueprint and BP services in the D-06 Data Contract for progressive context, append-only confirmation/correction evidence, erasable payloads, goals/measures, selected skills, two-month review cadence, budget ceiling, Decision Space, and stop conditions. Ask at most one new decision-relevant question per interaction cycle. | reasoning | done |
| WC058-04 | Integrate BP trial start, WBE trial status/expiry, AIR LOCAL routing, and PR workflow with the durable relationship. Enforce 14 days regardless of session count, no direct trial-to-active transition, no paid provider fallback, no credential use, and no publish/spend/third-party message/provider mutation. | reasoning | done |
| WC058-05 | Correct `TrialExpiryWorkflow`: unknown/unavailable status becomes explicit unresolved state, not automatic lapse; one bounded informational reminder; expiry stops new trial work without deleting evidence or customer-owned approved artifacts. WBE `CONVERTED` is a billing projection only and may be committed solely from WC-059 successful paid-activation outcome; it is never a D-03 lifecycle transition. | reasoning | done |
| WC058-06 | Build web and WhatsApp S01–S06 presentation: professional comparison, disclosure, interview, progressive context summary/correction, visible 14-day plan, skill demonstrations, trial status/quota, and item-by-item configuration decisions. Use ADR-023 HMAC, replay, deduplication, tenant token, opt-in, and risk tiers. | reasoning | done |
| WC058-07 | Implement the DMA-owned Professional Evaluation Adapter for all 19 declared skills using local inference, deterministic tools, public/free sources, approved templates, synthetic recipients, simulated campaigns, and pre-generated/free/customer-approved assets. Non-applicable skills return reason and activation condition. Add a three-skill non-DMA conformance fixture proving the shared journey has no DMA coupling. | reasoning | done |
| WC058-08 | Add end-to-end simulation fixtures and CCTs for S01–S06, all-skill coverage, no-paid-API, no-external-action, progressive context, disclosure ordering, trial expiry/inactivity, and adversarial trial action attempts. | auto | done |

## Required Inputs

`goals/GOAL-005-D06-dma-domain-authority-synthesis.md` · `goals/GOAL-005-D06-product-attestation.md` · `architecture/reference/agents/digital-marketing-agent.md` · `architecture/reference/product/ae01-business-boundary-contract.md` · `architecture/reference/product/ae01-solution-contract.md` · `architecture/reference/product/ae01-relationship-data-contract.md` · `architecture/reference/product/ae01-security-contract.md` · D-01/D-02/D-03/D-04/D-05 · ADR-023 · ADR-044 · WC-031/032/033/040/041 implementation evidence.

## Constitutional Compliance Tests

| CCT | Assertion |
|---|---|
| CCT-AE01-DISC-01 | Outcome query returns lawful suitable professionals and explains fit without preferred-customer exclusion |
| CCT-AE01-DISCLOSE-01 | Rights, limits, authority, trial/live mode, evidence, Stop, and price precede trial |
| CCT-AE01-INTERVIEW-01 | Interview answer labels source/uncertainty and never fabricates evidence or guarantees |
| CCT-AE01-CONTEXT-01 | Minimum context is name/location/business; one new question per cycle; correction replaces inference, not history |
| CCT-AE01-TRIAL-14D | Trial remains entitled for 14 calendar days regardless of session count |
| CCT-AE01-TRIAL-ZERO | All 19 skill demonstrations use zero paid APIs and cause zero external mutation |
| CCT-AE01-CONFIG-01 | Goals, measures, skills, budget, cadence, Decision Space, and stop conditions are independently decidable |
| CCT-AE01-TRIAL-ORDER | Direct trial-to-active and payment-before-acceptance attempts are denied |
| CCT-AE01-ADAPTER-01 | Shared journey passes DMA and non-DMA adapter fixtures with zero domain-specific platform branches |
| CCT-AE01-INJECTION-01 | Customer prompt injection and forged source tags cannot alter policy or become approved evidence |

## Definition of Done

- WhatsApp-first DMA simulation passes S01–S06 and all 19 skill demonstrations.
- Customer context survives session/channel restart without repeated onboarding.
- Trial activity is visibly planned across 14 days; inactivity never becomes consent.
- AIR/WBE evidence proves zero paid provider calls and zero consequential external actions.
- Trial expiry uncertainty fails safe without false conversion or destructive lapse.
- BP, PR, AIR, WBE, web, security, and integration tests pass with required coverage; manifests/OpenAPI and state records match executable behavior.

## Validation Commands

```bash
docker compose --profile test-python run --rm test-runner-python pytest tests/billing-engine/ tests/ai-runtime/ tests/professional-runtime/ -v
docker compose --profile test run --rm test-runner dotnet test tests/business-platform.Tests/
docker compose --profile test run --rm test-runner npm --prefix web test
docker compose --profile test run --rm test-runner npm --prefix web run build
```

## Boundaries

No real campaign, publishing, spending, provider credential use, contract acceptance, payment, or activation. No implementation starts without a future explicit Founder authorization.