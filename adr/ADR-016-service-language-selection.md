# ADR-016: Service Language Selection

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Enterprise Architect (structural technology selection)
**Constitutional Basis:** GENESIS Engineering Quality Mandate — "Technology decisions require ADRs"; AD-002 (Evidence First — type-safe contract enforcement); AD-007 (Runtime Universality — single codebase across professional types); C-023 (Constitutional Engine must enforce Evidence First atomically)

---

## Context

The platform comprises four deployable services. Two handle constitutional governance and customer-facing operations (.NET services). Two handle professional execution and AI inference (Python services). The language selection is a long-lived architectural decision — changing languages mid-implementation is extremely costly.

The selection criteria in priority order:
1. **Constitutional Engine suitability** — the CE must enforce Evidence First atomically under high concurrency. Type safety and transactional guarantees are paramount.
2. **LLM SDK maturity** — the AI Runtime must call LLM providers reliably. Language support for OpenAI, Azure OpenAI, and future providers is critical.
3. **Temporal SDK maturity** — both the Business Platform (Temporal client) and Professional Runtime (Temporal worker) require a mature Temporal SDK.
4. **Team velocity at MVI scale** — India-based development team; language familiarity and tooling availability matter.
5. **gRPC support** — Constitutional Engine and all callers need production-grade gRPC libraries.

---

## Decision

### Business Platform + Constitutional Engine: .NET 9 (C#)

**Reasons:**
- **Type safety**: C#'s strict type system prevents null reference errors and malformed evidence records at compile time. For the Constitutional Engine — the only service writing to the append-only audit ledger — compile-time guarantees are not optional.
- **gRPC**: `Grpc.AspNetCore` is the reference implementation for gRPC in .NET. Protocol Buffer codegen integrates natively into the .NET build pipeline.
- **Entity Framework Core 9**: Mature ORM with migration support (ADR-011), RLS-aware connection handling, and no raw SQL exposure in business logic.
- **Temporal .NET SDK**: Production-grade, maintained by Temporal Technologies. Supports workflow, activity, and signal patterns required for employment lifecycle management.
- **Azure-native**: Azure Container Apps, Azure Monitor, and Application Insights have first-class .NET instrumentation.
- **ASP.NET Core performance**: Consistently top-5 in TechEmpower benchmarks. Meets latency requirements for Evidence First (sub-80ms gRPC path, AD-005).

### Professional Runtime + AI Runtime: Python 3.12 (CPython)

**Reasons:**
- **LLM SDK dominance**: OpenAI, Azure OpenAI, Anthropic, and every other major LLM provider ships Python-first SDKs with full feature parity. Python is the de facto language of the AI inference layer.
- **FastAPI**: Async HTTP framework with automatic OpenAPI generation, Pydantic validation, and WebSocket support. The Emergency Stop WebSocket (AD-001) requires async I/O that FastAPI handles natively.
- **Temporal Python SDK**: Production-grade, supports the PAAS session workflow model (ADR-018).
- **Type hints (3.12)**: PEP 695 (type aliases), `@override` decorator, and `TypeVar` improvements in 3.12 bring Python sufficiently close to strong typing for the execution layer. `mypy --strict` is enforced in CI.
- **Separation of concerns**: Using different languages for governance (CE/BP) and execution (PR/AI) makes it structurally impossible to accidentally call CE from AI Runtime without a gRPC contract — the language boundary enforces the architectural boundary.
- **pgvector**: Python `asyncpg` + `sqlalchemy` with pgvector extension support is mature and tested for embedding operations required by Creative Standard Profiles (Amendment A-005).

---

## Alternatives Considered

| Option | Service | Reason Rejected |
|---|---|---|
| Java (Spring Boot) | CE, BP | JVM cold-start in Azure Container Apps scale-to-zero adds 8–15 seconds. Unacceptable for dev environment UX. Less Azure-native than .NET for monitoring/identity. Similar performance to .NET but higher infrastructure overhead. |
| Go | CE, BP | Excellent performance but immature ORM ecosystem (no EF Core equivalent). Raw SQL exposure risk for constitutional schema. Smaller Indian dev talent pool for this domain. gRPC support is good but Temporal Go SDK is less mature than .NET. |
| Python | CE, BP | Dynamic typing is architecturally inappropriate for the Constitutional Engine. A type error in evidence recording is a constitutional violation. `mypy` in strict mode is not equivalent to compile-time guarantees. The CE's correctness requirements exceed what Python's runtime type system can guarantee. |
| Node.js / TypeScript | PR, AI | LLM SDK support exists but Python SDKs have 6–12 months feature lead. Temporal Node SDK is less mature than Python. Async patterns for PAAS hot path (sub-50ms) are achievable but the Python async ecosystem (asyncio + FastAPI) is better suited for this workload profile. |
| Rust | Any | Exceptional performance and type safety, but: no mature Temporal SDK, no mature LLM SDK, steep learning curve incompatible with MVI timeline. Reserve for specific high-performance components post-MVI if benchmarks demand. |

---

## Version Pins

| Service | Language | Version | Rationale |
|---|---|---|---|
| Constitutional Engine | .NET / C# | .NET 9.0 LTS | LTS release, security-supported through May 2027 |
| Business Platform | .NET / C# | .NET 9.0 LTS | As above |
| Professional Runtime | Python | 3.12.x | Stable, type improvements, latest security patches |
| AI Runtime | Python | 3.12.x | As above; same base image as Professional Runtime |
| Web App | TypeScript | 5.x (via Next.js) | Managed by Next.js version pin |

Version upgrade policy: security patches applied within 7 days. Minor version upgrades tested in QA before promotion. Major version upgrades require a new ADR entry.

---

## Consequences

**Benefits:**
- Language boundary enforces architectural boundary (Python cannot accidentally call CE internals)
- Both language stacks have mature tooling for all WAOOAW requirements
- .NET type system provides compile-time Evidence First enforcement guarantees
- Python's AI SDK ecosystem is unmatched and will remain so through MVI

**Trade-offs:**
- Two language stacks require developers who know both, or team specialization
- Shared types (e.g., Decision Space schema) must be maintained in two representations — mitigated by proto file as the shared contract
- Docker images are larger (two base images vs one) — acceptable given AD-006 cost constraint analysis
