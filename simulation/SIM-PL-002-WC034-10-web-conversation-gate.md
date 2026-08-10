# SIM-PL-002 — WC034-10 Web Conversation BFF and Client Integration
**Date:** 2026-08-10
**Author:** Platform IT Expert (INST-010) — pipeline grooming simulation
**Task:** WC034-10
**Sprint:** WC-034 (F3)

## Scope Simulated
- Generate `typescript-fetch` conversation client from canonical BP OpenAPI.
- Implement server-only BFF conversation routes following existing identity BFF pattern.
- Implement conversation timeline/composer/retry/reconciliation UI behavior with typed cards/events.

## Dependency Analysis
- Upstream dependency: WC034-08 BP contracts must be stable before web generation.
- Upstream dependency: WC034-09 PR stream payload shape determines timeline/reconnect behavior.
- Pattern dependency: existing `web/lib/api/identity.ts` and `web/app/api/identity/*` define BFF hard boundary conventions.
- Acceptance dependency: 360px behavior and resilience criteria in UX acceptance contracts feed WC034-11 and WC034-12 validation.

## Risk Analysis
- Medium risk: generated client drift if operation IDs or schema names are not frozen before generation.
- Medium risk: accidental browser exposure of internal/runtime URLs if server-only boundary is violated.
- Low risk: accessibility regressions in timeline interactions at 360px if composition grows without overflow constraints.
- Mitigation in pipeline: isolate to `web/` paths, generate the six-operation/31-model dependency-closed client with pinned OpenAPI Generator 7.17.0, run strict `tsc` inside the C-080 container, and defer runnable browser tests to WC034-12 Docker evidence.

## Readiness Verdict
Verdict: ✅ PASS
Rationale: task is bounded to canonical web pathing, compile/lint gates exist and are deterministic, and downstream acceptance checks are explicitly staged.
