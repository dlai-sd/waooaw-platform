# R-061 — WC-034 F3 Implementation Review

**Date:** 2026-08-10
**Office:** INST-004 Enterprise Architect
**Decision:** APPROVED

## Scope and Independence

This is the independent INST-004 implementation review required by GEP-GOAL-005-INST-013-03 and C-065 for WC034-08 through WC034-12 on `ib/014/wc034-f3-implementation`. The review covers `main..09daae0` plus the WC034-12 candidate changes in `scripts/wc034_f3_validation.py`, `web/components/conversation/ConversationExperience.tsx`, `web/tests/e2e/fixtures/f1-services.mjs`, and `web/tests/e2e/f3-conversation-acceptance.spec.ts`. INST-004 did not implement, commit, push, merge, or deploy the contribution.

## Findings

| Area | Decision | Evidence |
|---|---|---|
| Architecture and scope | PASS | BP remains the sole ordinary public conversation ingress; browser traffic terminates at the same-origin Next.js BFF; PR remains internal; no `@ai-sdk/react`, browser-to-PR/provider path, attachments, voice, F4-F8, provider activation, or deployment is introduced. |
| Generated-client conformance | PASS | Production code uses generated `FromJSON` converters for timeline and submission wire payloads; strict TypeScript and production build pass; two-run generated-client tree hash is `541d5490431311ee2d5f727978c753f376816449938e5299ac5ac0be808dbc21`. |
| Idempotency and reconciliation | PASS | Original retry identity is preserved, reconciliation precedes retry, canonical messages are deduplicated, cursor expiry reconciles, offline state remains relationship-local, and unknown outcomes never become success. |
| Human Override and Evidence First | PASS | Cancellation and Emergency Stop use independent paths; Stop preempts ordinary continuation and requires authoritative confirmation; `PENDING` precedes CE-confirmed `RECORDED`; delivery and evidence remain structurally independent. |
| Tenant isolation and privacy | PASS | Consequential same-tenant unauthorized mutation fails before CE, PR, or persistence; privacy-safe inaccessible responses disclose no protected identifiers; authenticated conversation payloads remain outside service-worker caches. |
| Accessibility and responsive behavior | PASS | Keyboard and focus stability, polite live regions, zero serious or critical axe findings, exact 360x800 and 1440x900 geometry, horizontal overflow, and control occlusion are executable assertions. Pixel screenshot baselines are not a WC034-12 release requirement; executable geometry evidence satisfies the F3 acceptance contract. |
| Evidence quality | PASS | Browser evidence is explicitly fixture-backed production-build integration, not live BP/PR deployment integration. Fixture state is project-isolated and idempotent, and Evidence First transitions use an explicit deterministic trigger. |

## Acceptance Disposition

| Acceptance IDs | Decision |
|---|---|
| UX-CONV-01 through UX-CONV-07 | PASS |
| CCT-UX-HO-01 through CCT-UX-HO-03 | PASS |
| CCT-UX-EF-01 and CCT-UX-EF-02 | PASS |
| UX-PWA-03 and UX-RES-01 | PASS |

## Constitutional Disposition

| Principle | Decision |
|---|---|
| C-001 Human Override | PASS |
| C-023 Evidence First | PASS |
| C-026 Tenant Isolation | PASS |
| C-059 Implementation Traceability | PASS |
| C-063 Data Minimisation | PASS |
| C-065 SDLC Separation | PASS |
| C-071 Quality Framework | PASS |
| C-076 Coverage Obligation | PASS |
| C-080 Docker Test Isolation | PASS |
| C-086 Deterministic Evidence | PASS |

## Validation Evidence

- BP Conversation focused: 22/22 PASS; full BP regression: 170/170 PASS. These are overlapping suites and are not summed as distinct tests.
- PR regression: 89/89 PASS. Affected Python modules each exceed 90% line coverage; aggregate line coverage is 780/827 (94.32%).
- Web unit suite: 80/80 PASS; global line coverage 93.39%; `ConversationExperience` line coverage 93.82%; lint, strict TypeScript, and production build PASS.
- Static cross-stack contract drift sentinels: 4/4 PASS. These are static source/contract checks, not live integration tests.
- Browser acceptance: 16/16 PASS, comprising 8 Chromium tests at 1440x900 and 8 Chromium tests at exact 360x800.
- BP principal affected-file line coverage: controller 94.38%, service 100%, store 100%.
- `scripts/wc034_f3_validation.py` executes Docker-only checks, fails closed, emits structured evidence, and disables deployment, provider activation, and external triggers.

## Residual Risk and Boundary

The browser suite uses deterministic fixture-backed production-build integration and does not prove a live deployed BP/PR/CE environment. That residual integration risk is honestly recorded and does not block WC034-12. G-F3-09 remains BLOCKED: this review does not authorize deployment, provider activation, F4-F8, self-merge, or any ordinary browser connection to PR or model providers.

## Verdict

**APPROVED.** WC-034 F3 satisfies its architecture, acceptance, constitutional, coverage, and Docker evidence obligations. The implementation PR may be prepared for Founder review. Founder approval and merge remain required; deployment remains separately unauthorized.