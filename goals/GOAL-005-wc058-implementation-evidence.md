# GOAL-005 WC-058 Implementation Evidence

## Contribution Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-010 — Platform IT Expert |
| `goal_id` | GOAL-005 |
| `record_id` | CR-GOAL-005-INST-010-05 |
| `record_type` | Contribution Record |
| `produced_at` | 2026-08-11T09:20:43Z |
| `authorization_id` | GOA-GOAL-005-INST-010-04 |
| `acceptance_id` | ACC-GOAL-005-INST-010-04 |
| `execution_plan` | GEP-GOAL-005-INST-013-07 |
| `work_contract` | WC-058 — AE-01 S01 through S06 |
| `branch` | `ib/014/wc058-implementation` |
| `decision` | IMPLEMENTATION CONTRIBUTION PUBLISHED — independent INST-011 and INST-003 review required |
| `authority_boundary` | No provider activation or credentials, WC-059/WC-060, contract acceptance, payment, activation, deployment, production/customer proof, self-review, self-approval, merge, or direct push to `main` |

This contribution was produced after the matching Acceptance Record, within the five-session
Participation Window. It records repository implementation and synthetic simulation evidence only.
It does not claim deployment, live provider operation, customer use, attribution, or business outcome.

## Milestone Traceability

| Task | Commit | Implemented outcome |
|---|---|---|
| WC058-01 | `d5c0dc1` | Versioned manifest-driven professional discovery and complete pre-trial disclosure |
| WC058-02 | `dc4f9e6` | Domain-neutral evaluation state machine, typed answer validation, injection/PII gates, and Skill Runtime route |
| WC058-03 | `70427b0` | Tenant-RLS progressive context, append-only confirmation/correction, goals, skills, Decision Space, cadence, and trial binding persistence |
| WC058-04 | `dd0bfed` | BP/WBE/PR/AIR durable trial integration, exact 14-day owner truth, LOCAL-only inference, and trial-safe tool allowlist |
| WC058-05 | `bf8b12c` | Fail-closed expiry uncertainty, one reminder, explicit expiry command, conversion-race preservation, and artifact retention |
| WC058-06 | `777ecc7` | Web S01-S06 surfaces and ADR-023 WhatsApp HMAC, identity, opt-in, evidence, JWT, replay, deduplication, and risk tiers |
| WC058-07 | `140d1b7` | Complete domain-neutral adapter contract, DMA-owned 19-skill recipes, and three-skill non-DMA conformance |
| WC058-08 | `4c85a63` | Synthetic WhatsApp-first fixture and ten catalogued executable `CCT-AE01-*` parent assertions |

## Changed Contract And Implementation Surfaces

| Surface | Contribution |
|---|---|
| BP OpenAPI and catalog | Outcome discovery, disclosure, relationship trial/evaluation projections, and signed WhatsApp webhook; additive BP version advances through 1.5.0 |
| BP .NET | Catalog controller, relationship context/configuration/trial services, expiry workflow, WhatsApp controller/service/evidence gateway, tenant middleware, EF mappings, and DI/configuration |
| PostgreSQL | Migration 20b context/configuration and 20c minimised WhatsApp phone-HMAC/session receipt persistence; tenant RLS where tenant context exists; immutable/bounded-retention evidence controls |
| PR Python | Evaluation state machine and typed answers, full `ProfessionalEvaluationAdapter`, generic demonstration validator, trial entitlement/capability enforcement, and DMA domain package |
| AIR Python | Validated trial forces LOCAL provider and has no paid fallback |
| WBE Python | Owner-authoritative 14-day start/status/expiry behavior and conversion boundary |
| Web | Public professional discovery/comparison and authenticated relationship evaluation, 14-day plan, quota, demonstrations, and item-level configuration decisions |
| WhatsApp | Raw-body HMAC, E.164, five-minute freshness, 24-hour message deduplication, phone-HMAC identity, first-inbound opt-in, fail-closed CE registration evidence, 30-minute internal HS256 JWT, and Tier 2/3 step-up |
| Simulation/CCT | `simulation/fixtures/wc058-whatsapp-first-dma.json`, ten AE-01 catalogue entries, and executable cross-stack constitutional simulation |

No generated production client or build output is part of this contribution. Next.js build output and
coverage databases are validation artifacts, not staged implementation evidence.

## Safety And Boundary Evidence

| Obligation | Executable result |
|---|---|
| Exact 14 calendar days independent of session count | WBE owner tests, PR entitlement tests, BP owner reconciliation, and `CCT-AE01-TRIAL-14D` pass |
| Zero paid provider calls | AIR LOCAL-only/no-fallback tests and generic capability validator pass |
| Zero credentials or external mutation | Paid provider, credential read, publish, spend, third-party message, and provider mutation attempts are denied before dispatch |
| No direct trial-to-active transition | BP lifecycle tests reject the illegal transition; WBE `CONVERTED` remains billing-only |
| Expiry uncertainty fails closed | `UNKNOWN`/unavailable owner state remains `UNRESOLVED`; no inferred lapse or conversion |
| Evidence First | BP relationship changes and WhatsApp first registration fail closed when CE evidence is unavailable |
| Tenant/relationship isolation | Forced-RLS migration checks and tenant-bound controllers/services pass |
| Progressive context | One new question per cycle, correction history, payload separation, and restart survival pass |
| Generic/domain separation | Shared BP/PR production code scan contains zero DMA conditionals; DMA IDs and recipes live only in the domain-owned adapter/catalog; three-skill non-DMA fixture passes |
| Inactivity | Inactivity produces no consent, conversion, or early expiry; safe work remains available until owner-confirmed expiry |

## Validation Evidence

All commands ran inside the Ubuntu development container; Python service suites ran in the
repository `test-runner-python` container. No live provider credential was configured.

| Validation slice | Result |
|---|---|
| WC058-01 BP discovery/disclosure | PASS — 4 focused tests |
| WC058-02 PR evaluation workflow | PASS — 21 focused/neighbor tests; 92% changed-module coverage; Ruff |
| WC058-03 BP context/configuration | PASS — 11 focused/neighbor tests; affected services/entities 97–100% line coverage |
| WC058-03 PostgreSQL | PASS — first apply, reapply, catalogue, forced RLS, append-only and retention checks |
| WC058-04 integration | PASS — BP 10, WBE 27, AIR/PR 42; OpenAPI parse and PostgreSQL checks |
| WC058-05 expiry | PASS — BP 13, WBE 30, PR 14; Ruff and diagnostics |
| WC058-06 presentation | PASS — BP focused 20, full BP process exit 0, web 4, Next.js 23-page production build, OpenAPI/Compose parse, PostgreSQL apply/reapply/retention |
| WC058-07 adapters | PASS — 29 tests; 93.92% combined coverage; Ruff and diagnostics; PR dependency-complete regression 147 |
| WC058-08 CCT | PASS — focused 7 tests covering ten parent CCT identifiers |
| WC058-08 cross-stack | PASS — PR/CCT 50, AIR 24, WBE 30, BP 15, web 4, production build |
| Contract and fixture hygiene | PASS — OpenAPI YAML parse, Compose config, JSON parse, diff check, and editor diagnostics |

## Provenance Classes

| Evidence | Provenance class |
|---|---|
| Catalog, OpenAPI, migrations, runtime code, tests | Committed repository implementation |
| PostgreSQL first/reapply/RLS/immutability checks | Disposable PostgreSQL 16 execution evidence |
| .NET, Python, Jest, build, Ruff results | Container-local executable test/build evidence |
| WhatsApp messages, recipients, campaigns, assets | Synthetic fixtures only |
| Public/free, template, local, deterministic capability labels | Declared trial substitutions enforced by generic validator |
| Provider/customer/production outcomes | NONE — not executed and not claimed |

## Residual Limitations And Review Handoff

1. The Professional Runtime test image lacks `uvicorn`; two unrelated mTLS/private-server files cannot collect in that image. The remaining PR regression surface passes 147/147. This is an environment dependency gap, not a waived WC-058 assertion.
2. Web proof is component, strict TypeScript, lint, and production-build evidence. No deployment, real Meta webhook, browser-to-live-service, or customer acceptance proof is claimed.
3. WhatsApp registration uses the approved BP-called ADR-023 boundary in this contribution; no external Meta endpoint or phone identity container was activated.
4. Trial demonstrations are synthetic proposed behavior. They do not establish live DMA work, campaign effectiveness, customer acquisition, attribution, or provider readiness.
5. Provider activation, WC-059 contract/payment/activation, WC-060 continuity/evidence/Stop, deployment, and production proof remain separately unauthorized.

Independent INST-011 review must verify customer ordering, decision rights, suitability without
preferred-customer exclusion, and honest trial/inactivity semantics. Independent INST-003 review
must verify generic/domain separation, all-skill business meaning, and preservation of zero-paid,
zero-external-action, and no-false-conversion boundaries. INST-010 does not review this contribution.

## Learning Record

| Attestation field | Value |
|---|---|
| `institution_id` | INST-010 — Platform IT Expert |
| `goal_id` | GOAL-005 |
| `record_id` | LR-GOAL-005-INST-010-04 |
| `record_type` | Learning Record |
| `produced_at` | 2026-08-11T09:20:43Z |
| `authorization_id` | GOA-GOAL-005-INST-010-04 |
| `acceptance_id` | ACC-GOAL-005-INST-010-04 |
| `constitutional_discovery` | no |
| `evolution_triggered` | no |
| `improvement_signal` | A multi-owner trial remains reviewable when owner truth, simulation capability provenance, domain recipes, and customer presentation are tested separately and then composed in one synthetic constitutional journey. |

### Reusable Engineering Learning

1. Owner uncertainty is a first-class outcome. Retryable unresolved state is safer than inferring expiry, conversion, or success.
2. Trial safety is easiest to falsify when every capability carries explicit source, paid, and external-mutation metadata and the shared runtime validates the returned artifact provenance.
3. Domain neutrality needs two proofs: no domain literals in shared production code and a materially different adapter passing the same protocol.
4. Identity bootstrap data should be minimised before tenant context exists: HMAC lookup, bounded session metadata, no raw phone or message content, and fail-closed evidence before first persistence.
5. Simulation evidence must remain visibly distinct from provider, deployment, customer, and business-outcome evidence; passing CCTs cannot manufacture those later provenance classes.