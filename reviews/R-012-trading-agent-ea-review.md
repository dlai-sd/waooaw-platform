# R-012 — Enterprise Architect Review of Trading Agent Specification

**Review ID:** R-012
**Reviewer Office:** Enterprise Architect
**Subject:** `architecture/reference/agents/trading-agent.md` v1.0
**Date:** 2026-07-08
**Learning applied from:** R-011 (Digital Marketing Agent — R011-01 image consent gap)

---

## Overall Verdict: APPROVED WITH THREE NOTES

The Trading Agent specification is constitutionally complete and architecturally consistent. All 5 Skills have measurable business KPIs. All MCP tools are authorized by Decision Space entries. The PAAS execution model is correctly justified. Three notes raised — analogous to R011-01 (image consent) in the Digital Marketing Agent.

---

## Capability-to-Container Mapping Verification

| Skill | Owning Container | Supporting |
|---|---|---|
| 1. Market Analysis | Professional Runtime (PAAS engine) | AI Runtime (analysis + RAG), CE (evidence per session event) |
| 2. Trade Execution | Professional Runtime (PAAS hot path ≤50ms) | CE (ValidateAction before EVERY order), broker-mcp |
| 3. Risk Management | Professional Runtime (continuous monitoring) | CE (stop-loss evidence), broker-mcp |
| 4. Crypto | Professional Runtime | CE, broker-mcp |
| 5. Performance Analytics | Business Platform (Skill 7 equivalent) | platform-analytics-mcp, broker-mcp (read-only) |

All Skills fit within the existing 4-container architecture. No new containers required. ✓

---

## Constitutional Traceability Verification

| Claim | Addressed |
|---|---|
| C-018 (PAAS model) | ✓ PAAS justified — human approval incoherent at trading speed |
| C-019 (deterministic latency makes PAAS constitutional) | ✓ cited in Section 3 |
| C-036 (Skills as constitutional units) | ✓ each Skill independently governed |
| C-037 (Business KPIs) | ✓ daily return, drawdown, Sharpe — not technical metrics |
| C-040 (Domain specialization) | ✓ RAG Tier 1 explicitly lists SEBI regs, India F&O patterns |
| C-041 (Tool calls governed) | ✓ CE.ValidateAction before every broker-mcp call, explicitly stated |
| FR-003 (RAG IP boundary) | ✓ Tier 1+3 WAOOAW IP, Tier 2 customer private |

---

## Note R012-01 (REQUIRED before approval — learned from R011-01)

**Broker API access authorization mechanism not specified.**

R011-01 found that image consent was assumed but the mechanism was undefined. The equivalent here: the onboarding flow says "Credential collection — Zerodha API key + secret" but does not specify how the agent verifies:
1. The API key has `orders:write` permission (not just `data:read`)
2. The customer has enabled API trading in their Zerodha/broker dashboard
3. How API key expiry mid-session is handled (session must halt gracefully)

**Required fix:** Add `BROKER_API_ACCESS_VERIFIED` as an always-ask action in Skill 2. This creates a constitutional evidence record when the customer confirms broker API access is correctly configured with execution permissions. Without this record, the agent could place orders on an API key that the customer configured for read-only — a financial harm.

---

## Note R012-02 (non-blocking — regulatory disclaimer)

**Regulatory disclaimer not in Constitutional Constraints.**

The agent's trade signals and execution are NOT investment advice under SEBI regulations. The specification does not include this as a constitutional constraint.

**Required fix before production:** Add to Skill 1 and Skill 2 Constitutional Constraints: "The agent's analysis and trade execution are not investment advice. The customer is the decision-maker in setting the Decision Space. The agent executes within that space — it does not advise outside it."

This protects both the customer (manages expectations) and WAOOAW (regulatory boundary).

---

## Note R012-03 (non-blocking — session-end open position handling)

**What happens at 3:25 PM with open F&O positions is not specified.**

Skill 3 (Risk Management) mentions "hold positions beyond approved session window" as prohibited, but does not specify whether the agent auto-closes positions at session end or alerts the customer to close manually.

**Recommended resolution:** Add to Skill 3 Decision Space: `SESSION_END_POSITION_CLOSURE` as an always-ask action — the customer decides at onboarding whether to auto-close all positions at session end or receive an alert to close manually. This is a constitutional decision, not a configuration preference.

---

## Learning Applied from Digital Marketing Agent

The Digital Marketing Agent R011-01 (image consent) established the pattern: wherever the agent needs a real-world authorization from the customer (consent for an image, access to a platform), there must be a constitutional evidence record of that authorization.

For the Trading Agent: broker API access authorization + order execution permission is the equivalent. This creates an audit trail that proves the customer explicitly authorized trade execution access — not just data reading.

This pattern (authorization evidence before capability activation) should be applied to ALL future agent specifications in the constitutional checklist as item 9.

---

## Verdict: APPROVED — pending R012-01 fix

R012-01 is required before Founder approval (broker API auth mechanism creates financial risk without it).
R012-02 and R012-03 can be addressed as v1.1 fixes.

**Reviewer:** Enterprise Architect (AI agent, Office 04)
**Date:** 2026-07-08
