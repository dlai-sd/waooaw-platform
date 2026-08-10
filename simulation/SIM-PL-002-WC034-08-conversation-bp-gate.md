# SIM-PL-002 — WC034-08 Business Platform Conversation Core
**Date:** 2026-08-10
**Author:** Platform IT Expert (INST-010) — pipeline grooming simulation
**Task:** WC034-08
**Sprint:** WC-034 (F3)

## Scope Simulated
- BP conversation ingress only: timeline, send, retry, read-position, cancellation, resumable SSE.
- JWT tenant authority, UUID request-hash idempotency, RFC 9457 privacy-safe problem responses.
- Evidence First sequencing before success responses.

## Dependency Analysis
- Upstream contract dependency: `architecture/reference/components/conversation-core.md` defines BP ownership and acceptance obligations.
- API source dependency: `architecture/reference/api-specs/business-platform.openapi.yaml` must remain source of truth (spec-first).
- Runtime dependency: existing BP identity and tenant middleware patterns are reusable and constrain tenant authority extraction.
- Downstream dependency: WC034-10 web BFF and generated client depend on stable BP operation IDs and response schemas.

## Risk Analysis
- Medium risk: idempotency race conditions across retry/read-position if request hash normalization is inconsistent.
- Medium risk: SSE reconnect semantics can drift from canonical cursor model if event ordering is not deterministic.
- Low risk: tenant leakage if request-body tenant fields are ignored and JWT authority remains mandatory.
- Mitigation in pipeline: explicit output boundary to `src/business-platform/`, additive migration `21-conversation-core.sql`, and `tests/business-platform.Tests/`; compile gate `dotnet_build` and Docker-only `dotnet_test` target the actual BP projects.

## Readiness Verdict
Verdict: ✅ PASS
Rationale: contracts are frozen, ownership is isolated to BP paths, compile/test gates are concrete and present, and downstream dependencies are explicit.
