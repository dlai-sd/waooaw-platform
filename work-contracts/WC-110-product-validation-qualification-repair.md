# WC-110 - Product Validation Qualification Repair

## Record Control

| Field | Value |
|---|---|
| Office | Platform IT Expert (INST-012) |
| Authorized by | Founder instruction in the 2026-09-30 continuous working session |
| Implementation authorization | Founder confirmed product-validation implementation in the current session |
| Status | IMPLEMENTATION AUTHORIZED - CUSTOMER SCENARIOS PARKED |
| Baseline | WC-109 branch commit `b1b60303` |
| Parent delivery | WC-109 Stage 4 and CB-011 |
| Delivery unit | One bounded local product-validation repair tranche |

## Objective

Resolve the product-owned failures that block WC-109 Stage 4 without weakening the canonical 43-gate
inventory. Reconcile Business Platform behavior with its canonical OpenAPI contract and add the six
missing executable validation suites for accessibility, customer scenarios, provider failover and
Emergency Stop.

## Authority And Boundaries

Current-session authorization permits changes to product behavior, canonical API contracts, local test
fixtures, test suites and catalog commands only where required by the requirements below. It does not
authorize cloud mutation, deployment, customer traffic, real provider calls, paid services, Production
access, selective validation, approval or merge.

Existing constitutional and product contracts remain authoritative. A test may use deterministic local
providers and synthetic tenants, actors and content, but must cross the real owning application boundary.
Static text checks, empty collections, skips, broad baselines, suppressed Schemathesis checks and smaller
substitutes cannot qualify a requirement.

### Founder Parking Direction - 2026-09-30

The Founder directed that AS-001 remain parked rather than adding DMA theme-to-publishing, advertising
and performance-improvement capabilities under WC-110. Review confirmed AS-003 also requires Trading
brief/compliance and crash-recovery capabilities beyond the shipped signal-analysis adapter, while AS-005
requires Agricultural warning, action-feedback, sell-timing and WhatsApp-stop capabilities absent from
the current product. WC110-R005, WC110-R006 and WC110-R007 therefore remain BLOCKED for a later agent
product Work Contract. Their catalog gates remain mandatory and may not be skipped or substituted.

## Requirements

| Requirement | Normative outcome |
|---|---|
| WC110-R001 | The tranche is bound to the authorized baseline, CB-011 and an atomized requirement ledger. |
| WC110-R002 | Business Platform responses conform to the canonical OpenAPI status, media-type, header and schema contracts without reducing Schemathesis checks. |
| WC110-R003 | Schemathesis exercises every Business Platform and Professional Runtime operation from writable disposable state and emits nonempty JUnit evidence. |
| WC110-R004 | Accessibility runs real Playwright checks on default desktop and 360px mobile states, including axe, keyboard/focus, overflow and visible primary actions. |
| WC110-R005 | AS-001 proves the governed DMA customer path from request through evidence-backed outcome without external provider traffic. |
| WC110-R006 | AS-003 proves the governed Trading path and customer Emergency Stop outcome, including the 250 ms constitutional ceiling. |
| WC110-R007 | AS-005 proves the governed Agricultural multilingual warning/guidance path without leaking customer content. |
| WC110-R008 | AS-PSE proves injected Gemini rate limiting selects the declared fallback, preserves behavior and records privacy-safe dispatch evidence. |
| WC110-R009 | CCT-HO-01 proves Emergency Stop across the executable service boundary, persisted evidence and affected-session response within 250 ms. |
| WC110-R010 | All six previously missing gates collect at least one real test, publish native evidence and pass through the unchanged catalog route. |
| WC110-R011 | A fresh immutable candidate reruns only identity-affected lanes and assembles all 43 required results with no missing, stale or substituted evidence. |

## Delivery Plan

| Lane | Work | Completion evidence |
|---|---|---|
| A - REST shared contract | Repair shared authentication, validation and problem-response semantics first; then address remaining endpoint-specific drift | Both Schemathesis specifications pass all checks and publish nonempty JUnit |
| B - Accessibility | Reuse the production Web fixture and existing accessibility helpers for default desktop/mobile customer states | Playwright report plus explicit axe, focus, overflow and action assertions |
| C - Customer acceptance | PARKED by Founder direction; later agent product contracts must implement the missing governed capabilities before these scenarios can execute | BLOCKED; no substitute evidence accepted |
| D - Constitutional resilience | Implement PSE injected-rate-limit fallback and service-boundary Emergency Stop latency/evidence tests | Nonempty AS-PSE and CCT-HO-01 JUnit reports |
| E - Requalification | Re-run only changed lanes until green, freeze once, then assemble the complete inventory | One exact candidate and canonical 43-result assembly |

## Stop Conditions

Stop and retain a failed result if completion would require real provider credentials, cloud or deployment
mutation, customer traffic, threshold reduction, gate removal, a skipped or empty suite, a static
substitute for runtime behavior, or a change to an unrelated product contract.

## Definition Of Done

- Every WC-110 requirement is PASS with direct source and Docker-executed evidence.
- The REST contract and all six missing gates pass without suppressed checks or empty/skipped suites.
- Product regressions for every repaired shared behavior pass in the owning stack.
- WC-109 binds a fresh candidate and assembles all 43 same-candidate results.
- CB-011 is resolved with exact evidence; hosted shadow and pilot obligations remain separate WC-109 work.
- No deployment, provider, customer-traffic, Production, approval or merge claim is made.

The Definition of Done cannot be reached while the three parked customer-scenario requirements remain
BLOCKED. REST and other independent lanes may continue and retain their own valid evidence.