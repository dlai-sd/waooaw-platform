# ADR Quick Reference

**20 ADRs — one line each. Read only the full ADR if you need rationale or alternatives.**
**All status: Accepted. Date: 2026-07-07 (ADR-001 to 018) / 2026-07-08 (ADR-019 to 020).**

| ADR | Decision (one line) | Your constraint | Read full if... |
|---|---|---|---|
| **001** | gRPC for all CE internal communication | All calls to CE are gRPC — no REST to CE from any service | Implementing CE client or new RPC method |
| **002** | OpenAPI spec-first — spec is truth, never code-generated | Write spec before any endpoint code; use `openapi-generator-cli` for clients | Adding a new REST endpoint |
| **003** | `tenant_id` from JWT as sole multi-tenancy anchor → `SET LOCAL app.tenant_id` in every DB session | Never accept tenant_id in request body; always from JWT; DB interceptor is mandatory | Implementing JWT middleware or EF Core DbContext |
| **004** | Azure SignalR (cloud) / plain WebSocket (dev) for Emergency Stop | Emergency Stop path is pre-warmed WebSocket — never HTTP long-poll | Implementing Emergency Stop in any service |
| **005** | PAAS session affinity — one replica per session | PAAS sessions hold Decision Space in memory; replica crash = session lost (reload on first post-crash request) | Implementing PAAS Engine or session management |
| **006** | ASP.NET Core built-in rate limiting; no API gateway at MVI | Apply per-tenant rate limits at BP middleware layer; never on Emergency Stop path | Adding rate limiting to any endpoint |
| **007** | mTLS for CE gRPC in cloud; plain TLS in dev | CE uses mTLS in cloud — certificates auto-rotated; cert-manager in prod | Implementing CE client in cloud environment |
| **008** | Keycloak 25.0.6 as OAuth broker; Google default IDP; version pinned | Never bypass Keycloak; pin version; add upgrade protocol note for major updates | Changing auth flow or adding identity provider |
| **009** | OTel SDK in all services → Jaeger (dev) / Azure Monitor (cloud); OTLP_ENDPOINT env var | Every service emits OTel; OTLP_ENDPOINT is the only env change between envs | Adding observability to a new service |
| **010** | Azure-first with named escape hatches per Azure dependency | Document escape hatch for each Azure service used; no undocumented Azure lock-in | Introducing a new Azure service dependency |
| **011** | EF Core Migrations; append-only rule: no destructive migrations on constitutional schema | Never `DROP`, `ALTER TYPE DROP VALUE`, or `UPDATE` on constitutional schema in any migration | Writing DB migrations (read empty-migration technique in engineering-standards §9) |
| **012** | GHCR as container registry; GitHub Actions native | Push to GHCR on CI; tag with `sha-{git-sha}`; retag for promotion | Setting up image build or promotion pipeline |
| **013** | GitHub Actions CI/CD; trunk-based; CCTs as mandatory gate | CCT failure blocks ALL promotion — no exception, no manual override | Adding or modifying the CI/CD pipeline |
| **014** | `.env` dev / GitHub Secrets CI / Azure Key Vault cloud | Never commit secrets; Key Vault ref pattern: `secretref:` in Container Apps | Handling secrets in any environment |
| **015** | Temporal self-hosted (dev/QA) → Temporal Cloud (UAT/prod) | Dev: `temporalio/auto-setup:1.24` in docker-compose; prod: Temporal Cloud mTLS | Implementing Temporal workers or configuring Temporal |
| **016** | .NET 9 for CE + BP; Python 3.12 for PR + AI Runtime | Language is frozen — do not introduce polyglot additions without a new ADR | Never (frozen) |
| **017** | Next.js 14 TypeScript PWA Phase 1 → React Native Phase 2 | Emergency Stop always visible; strict TypeScript; use openapi-generator for API clients | Adding new UI framework or library |
| **018** | Emergency Stop signal routing via Temporal — PAAS sessions are `PAASSessionWorkflow` | CE sends Temporal signal by workflow ID; `active_session_ids` in EmergencyStopRequest are Temporal workflow IDs | Implementing Emergency Stop fan-out at scale |
| **019** | RAG Architecture — three-tier (Domain / Customer / Platform Intelligence) | pgvector in `institutional` schema at MVI; Customer context isolated per tenant | Implementing RAG pipeline or adding new agent domain knowledge |
| **020** | MCP Integration Pattern — AI Runtime is MCP client; each platform capability is MCP server | Every MCP tool call requires CE.ValidateAction FIRST (C-041); default deny in Tool Registry | Adding a new external platform or tool capability |
| **021** | External Platform OAuth — Server-side Auth Code flow; oauth-vault service (port 8130) manages token storage + refresh; MCP servers retrieve tokens from oauth-vault via mTLS | Instagram requires Professional account (not personal); token refresh failure → pause affected skill + notify customer | Adding a new external platform OAuth integration (ADR-021) |
| **022** | Razorpay India for all payments — Subscriptions API for recurring billing; razorpay-mcp sidecar (port 8131); GST invoicing mandatory (SAC 9984, 18%); pro-rata via billing event ledger | Budget ceiling enforcement via CE.ValidateAction with BudgetContext (C-043); payment failure → 3-day grace → suspend | Implementing billing, changing payment processor, adding a new pricing tier (ADR-022) |
| **023** | WhatsApp Phone-as-Identity for C-042 Agents — phone number = Meta-verified identity; Phone Identity Service (port 8137); auto-registration on first message; HMAC webhook validation; TRAI opt-in enforcement | Replay attack prevention (±5 min timestamp); TRAI 24-hour service window; HSM-only outside window; no Keycloak for WhatsApp-native users | Adding a WhatsApp-native onboarding flow to any C-042 agent (ADR-023) |
