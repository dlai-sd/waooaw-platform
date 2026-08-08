# Agricultural Advisor — Domain Gap Register

**Agent:** Agricultural Advisory Professional v2.8 (`AGRICULTURAL_ADVISOR_INDIA`)
**Purpose:** Grooming input for customer release; not an approved implementation backlog
**Evidence date:** 2026-08-08
**Current status:** Activation Gate pass recorded; no version-specific Founder approval, customer activation, or customer-proof evidence

## Release Boundary

The first customer release must understand one farmer's farm and season, provide cited weather and mandi guidance in the farmer's language, deliver time-sensitive alerts, retain acknowledgement evidence, and support a safe seasonal review. PMFBY support is evidence preparation and guided manual submission, not automated claim filing.

Shared WAOOAW discovery, interview runtime, phone identity, trial/hire, generic billing, omnichannel state, alert transport, and employment lifecycle capabilities are excluded from this register.

## Evidence Sources

- `architecture/reference/agents/agricultural-advisor-agent.md`
- `architecture/reference/billing/billing-profiles/agricultural-billing-profile.md`
- `architecture/reference/skill-dependency-register.md` (supplementary provider inventory; agent header is historical v2.6, so the v2.8 agent spec controls scope)
- `simulation/006-suresh-agricultural-nagpur.md`
- `simulation/014-agricultural-confidence-run.md`
- `architecture/reference/platform-component-registry.yaml` and `constitution/PROJECT_STATE.md` (platform maturity and customer-proof baseline)

## Domain Gaps

| Priority | Gap | Customer impact | Grooming outcome |
|---|---|---|---|
| P0 | Regional-language speech recognition and synthesis provider is not selected or validated for farming vocabulary | Voice messages may be mistranscribed into unsafe crop advice | Provider decision, code-switching corpus, pesticide/crop/unit vocabulary tests, confidence threshold, confirmation, and text fallback |
| P0 | Authoritative weather chain is incomplete | Alerts and PMFBY evidence may rely on non-authoritative or stale data | IMD access, district-warning correlation, source precedence, freshness, outage behavior, and evidence retention |
| P0 | Farm/crop/season profile is not operational | Advice cannot be grounded in crop stage, water, location, or farmer constraints | Versioned farm-season model, minimum profile, farmer confirmation, crop-stage updates, and per-farm isolation |
| P0 | Agricultural skills are not integrated with live data and evidence | Weather, mandi, crop-health, planning, and scheme outcomes remain simulations | One end-to-end weather plus mandi release slice with source citations, CE evidence, delivery, acknowledgement, and correction |
| P0 | Advice safety policy for pesticide, dosage, and high-consequence crop action is not executable | Incorrect advice could harm crop, health, or income | Consequence classification, authoritative source requirement, independent verification, uncertainty disclosure, and agronomist escalation |
| P1 | ICAR crop-disease and soil knowledge access/content rights are unresolved | Crop-health and planning advice may be incomplete or unverifiable | Public-source decision, licensing/partnership decision, ingestion ownership, provenance, update cadence, and quality review |
| P1 | Mandi feeds lack complete freshness and market-coverage contracts | Sell-timing guidance may be based on delayed or irrelevant prices | Agmarknet credential, eNAM decision, market matching, timestamp disclosure, target-price configuration, and stale-data behavior |
| P1 | Seasonal employment and billing semantics are unresolved | Farmers may pay during inactive periods or lose continuity between seasons | Founder decision on pause/dormant/seasonal plan, active-season definition, renewal reminder, and pro-rata behavior |
| P1 | Social-mission price sits below the general margin target | The offer cannot be released without an explicit economic policy | Founder Action for agent-specific margin floor or revised price/cost envelope |
| P1 | PMFBY evidence package and operational boundary are not defined | Farmers may mistake WAOOAW evidence for an accepted insurance claim | Supported-document schema, 72-hour guidance, disclaimer, authoritative event link, manual submission path, and escalation directory |
| P1 | Multi-signal bundling is simulated but not operationally validated | Farmers may be overwhelmed or miss the most urgent action | Priority queue, quiet-hour rules, CRITICAL override, bundling telemetry, delivery receipts, and missed-alert escalation |
| P2 | Returning-season context cannot yet traverse prior employment contracts | Rehired farmers may repeat onboarding or lose useful history | Farm identity retention, historical season access, consent, previous-contract chain, and stale-context controls |
| P2 | FPO/family decision models are incomplete | Sponsored farmers and shared decisions lack clear authority | Sponsor, farmer, family contact, payer, consent, data visibility, and offboarding roles |

## Specialized Customer Interface

- Voice-first farm and season setup
- Crop-stage timeline and upcoming actions
- Weather/pest/price alert cards with source and freshness
- Mandi target-price watch
- Photo-assisted crop observation with uncertainty disclosure
- PMFBY evidence timeline and guided checklist
- Seasonal plan, pause, and return flow

## Release Decisions and Dependencies

1. Select STT/TTS provider and validate against regional farming vocabulary.
2. Obtain IMD and data.gov.in access; decide ICAR/NBSS content route.
3. Decide seasonal billing and the agricultural social-mission margin floor.
4. Define the safe boundary between guidance, verified recommendation, and agronomist escalation.

## Grooming Exit

Each accepted item must identify data authority, freshness/SLA, language and uncertainty behavior, customer acceptance scenario, constitutional controls, executable tests, and operational escalation.
