# Trading Agent — Domain Gap Register

**Agent:** Autonomous Trading Professional v1.8 (`TRADING_FO_CRYPTO`)
**Purpose:** Grooming input for customer release; not an approved implementation backlog
**Evidence date:** 2026-08-08
**Current status:** Activation Gate pass recorded; FA-005 complete; no v1.8 Founder approval, customer activation, or customer-proof evidence

## Release Boundary

The first release, if legally authorized, must operate one broker and one constrained Indian F&O strategy within a customer-declared Decision Space. It must prove deterministic pre-trade authorization, real-time loss ceilings, order reconciliation, Emergency Stop, session reporting, and complete customer isolation. Crypto execution is excluded from the first live release.

Shared WAOOAW discovery, interview runtime, trial/hire, common billing lifecycle, generic alerts, and employment lifecycle capabilities are excluded from this register.

## Evidence Sources

- `architecture/reference/agents/trading-agent.md`
- `architecture/reference/billing/billing-profiles/trading-billing-profile.md`
- `architecture/reference/skill-dependency-register.md` (supplementary provider inventory; agent header is historical v1.7, so the v1.8 agent spec controls scope)
- `simulation/008-trading-sir-sil-simulation.md`
- `simulation/013-trading-confidence-run.md`
- `architecture/reference/platform-component-registry.yaml` and `constitution/PROJECT_STATE.md` (platform maturity and customer-proof baseline)

## Domain Gaps

| Priority | Gap | Customer impact | Grooming outcome |
|---|---|---|---|
| P0 | Independent SEBI legal classification of the PAAS model is absent | WAOOAW may operate an unauthorized advisory, execution, or portfolio-management service | Written legal opinion, permitted service boundary, disclosures, record retention, suitability obligations, and prohibited claims |
| P0 | Broker partnership and execution/data entitlements are unavailable | No live market data or lawful order execution | Select one broker, complete developer agreement, define scopes, rate limits, support, sandbox, token lifecycle, and outage obligations |
| P0 | Deterministic pre-trade risk engine is not integrated | Orders could exceed instrument, position, capital, session, or loss authority | Atomic risk snapshot, CE decision, idempotency, stale-price tolerance, margin check, order dispatch, and immutable evidence |
| P0 | Daily loss limit and pending-order cancellation are not proven under concurrency | Customer losses may continue after the constitutional floor is reached | Broker-event ingestion, race-free loss calculation, cancel-all ordering, no-new-order latch, reconciliation, and adversarial CCTs |
| P0 | Emergency Stop is not connected to a real broker/session | Stop may halt WAOOAW while leaving pending orders or unclear positions | Measured end-to-end stop, pending-order cancel, open-position snapshot, customer disclosure, broker outage behavior, and manual recovery |
| P0 | Cross-customer trading isolation is not implemented | Coordinated or copied trades may create regulatory and fairness violations | Per-customer workflow, no active-position Tier-3 sharing, anti-copy controls, tenant-isolation tests, and regulator-ready evidence |
| P1 | Zerodha daily token/auth-relay remains specification-only | Sessions may fail at market open despite active employment | Production auth relay, expiry signals, customer completion SLA, fallback, missed-session handling, and token audit |
| P1 | P&L, fees, taxes, margin, and slippage reconciliation is incomplete | Performance reports may misstate actual customer outcome | Broker contract-note reconciliation, charges model, realized/unrealized separation, discrepancy halt, and correction process |
| P1 | Market-data authority and freshness policy are unresolved | Trading decisions may use stale, partial, or conflicting data | Feed selection, exchange timestamps, sequence gaps, circuit breakers, clock synchronization, fail-closed rules, and telemetry |
| P1 | Exchange calendar and market-event behavior are incomplete | Agent may trade outside valid windows or mishandle expiry/corporate events | NSE/BSE calendar, holidays, expiry changes, freeze quantities, circuit limits, and instrument-master updates |
| P1 | Performance communication risks encouraging unsafe escalation | Customers may increase risk based on selective wins | Risk-adjusted metrics, drawdown context, benchmark, loss periods, no performance promises, and mandatory honest assessment |
| P2 | Crypto scope lacks custody/exchange/regulatory architecture | The higher tier advertises capability not ready for governed execution | Keep read-only advisory excluded or run a separate legal, custody, venue, tax, and risk-design programme |

## Specialized Customer Interface

- Broker connection and daily auth health
- Decision Space and risk-limit editor with consequence preview
- Live session state, positions, orders, margin, P&L, and loss-limit utilization
- Prominent Emergency Stop and post-stop position guidance
- Order/evidence timeline and broker reconciliation
- Risk-adjusted performance, slippage, charges, and drawdown review

## Release Decisions and Dependencies

1. Obtain independent legal clearance before implementation planning for live execution.
2. Select one broker and one market-data source for the constrained release.
3. Decide whether the first customer proof is paper trading, broker sandbox, or tightly capped live capital.
4. Exclude crypto execution until a separate regulatory and custody decision is approved.

## Grooming Exit

No live-execution item may be accepted without legal basis, deterministic failure behavior, concurrency tests, broker-sandbox evidence, observability, incident runbook, and explicit customer-capital blast radius.
