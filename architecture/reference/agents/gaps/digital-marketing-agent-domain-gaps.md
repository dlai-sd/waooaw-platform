# Digital Marketing Agent — Domain Gap Register

**Agent:** Digital Marketing Professional v3.1 (`DIGITAL_MARKETING_LOCAL_SERVICE`)
**Purpose:** Grooming input for customer release; not an approved implementation backlog
**Evidence date:** 2026-08-08
**Current status:** Activation Gate pass; Founder approval through v3.0; no customer activation or customer-proof evidence

## Release Boundary

The first customer release must profile one local business, establish its brand and channel connections, produce a coherent campaign, obtain the required approvals, publish through governed provider APIs, attribute enquiries or bookings, and report outcome, spend, and evidence.

Shared WAOOAW marketplace, interview, trial, hiring, billing lifecycle, omnichannel conversation, generic alerts, and employment lifecycle capabilities are excluded from this register.

## Evidence Sources

- `architecture/reference/agents/digital-marketing-agent.md`
- `architecture/reference/billing/billing-profiles/dma-billing-profile.md`
- `architecture/reference/billing/dma-bundle-definitions.md`
- `architecture/reference/skill-dependency-register.md` (supplementary provider inventory; agent header is historical v2.4, so the v3.1 agent spec controls scope)
- `simulation/SIM-019-dma-restaurant-domain-validation.md`
- `architecture/reference/platform-component-registry.yaml` and `constitution/PROJECT_STATE.md` (platform maturity and customer-proof baseline)

## Domain Gaps

| Priority | Gap | Customer impact | Grooming outcome |
|---|---|---|---|
| P0 | Meta Business Verification and required Instagram/Facebook scopes are not production-ready | DMA cannot publish or manage the customer's primary social channels | Approved Meta app, scope inventory, test-business account, token renewal, revocation, and degraded-mode acceptance criteria |
| P0 | Customer channel connection has no proven end-to-end onboarding for Meta, Google Business Profile, Search Console, or Ads | Customer can hire DMA but cannot give it governed access to work | Domain connection journey, provider-specific eligibility checks, OAuth evidence, reconnect flow, and ownership transfer rules |
| P0 | Campaign execution is not integrated from crystallized brief through approval, schedule, publish, and provider receipt | The core marketing outcome remains a simulation | One production-like campaign slice with idempotent publication, retry policy, artifact versioning, and evidence chain |
| P0 | Enquiry-to-booking attribution is not operational | DMA cannot prove customer business outcome beyond impressions and clicks | Booking/enquiry event contract, source attribution, consent, deduplication, and KPI calculation for one release domain |
| P0 | Ad-spend controls are not integrated with real Meta/Google campaign actions | Customer funds could be spent without proven campaign-level ceiling and reconciliation | Segregated ad wallet, CE pre-action check, platform fee disclosure, provider spend reconciliation, and overspend CCT |
| P1 | Domain Vocabulary Engine is validated by simulation but not proven against a production taxonomy/content pipeline | New business domains may receive wrong terminology or compliance rules | Versioned domain taxonomy, fallback behavior, domain-content review, and regression corpus for initial supported domains |
| P1 | Provider and asset stack remains largely stubbed | Image, video, voice, SEO, and optimization skills cannot meet advertised capability | Select release providers, contract cost/SLA/content rights, implement only bundle-supported assets, and mark unavailable skills honestly |
| P1 | Content compliance varies by business domain and platform | Regulated or sensitive businesses may publish invalid claims | Domain compliance packs, platform policy checks, escalation rules, and zero-violation release gate |
| P1 | Campaign performance data has no proven normalized analytics model | Performance review cannot connect spend, content, enquiries, and bookings | Cross-provider metric schema, attribution windows, freshness rules, and evidence-backed review calculation |
| P1 | Local SEO, GBP, directory, and reputation workflows require provider-specific operating rules | DMA may recommend actions it cannot complete or verify | Define supported actions, customer-assisted actions, evidence, and completion semantics per provider |
| P2 | Multi-location and agency-client ownership are specified but not customer-proven | Context, credentials, and spend may cross business boundaries | Location/client isolation tests, delegated approval model, portfolio reporting, and agency offboarding rules |
| P2 | Domain extension governance is not operational | Adding a vertical may silently expand expertise claims | Grooming gate for taxonomy entry, Tier-1 knowledge, vocabulary tests, compliance pack, simulation, and approval |

## Specialized Customer Interface

- Campaign brief and theme cascade
- Content calendar and artifact preview/revision
- Channel connection and health
- Campaign approval and publishing status
- Ad wallet, campaign spend, management fee, and pacing
- Enquiry/booking funnel and outcome attribution
- Domain-specific compliance warnings

## Release Decisions and Dependencies

1. Select the first production customer domain and deliberately limit the release claim.
2. Complete Meta Business Verification and choose the Google provider scope included in the first release.
3. Select image/video providers that fit the released bundle economics and content rights.
4. Decide whether the first release includes paid advertising or proves organic publishing first.

## Grooming Exit

Each accepted item must identify its owning component, provider contract, customer-visible acceptance scenario, constitutional controls, executable tests, operational telemetry, and release maturity target.
