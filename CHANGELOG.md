# Changelog

All notable changes to the WAOOAW Platform are documented here.
This file is auto-generated from conventional commits. Do not edit manually.

## [1.45.0] — 2026-08-09 · WC-034 Phase B F1 Experience Foundation

### Features
- Next.js App Router shells for public, authentication, customer, Founder, and system-state surfaces with server-owned customer and Founder authorization
- Shared WAOOAW visual tokens, Noto Sans/Noto Nastaliq Urdu typography, light/dark/system themes, and English/Urdu direction bootstrap
- Expanded, intermediate, and exact 360 px navigation with persistent authenticated Emergency Stop placement
- Installable manifest and privacy-safe service worker that caches only static shell assets; navigations, APIs, RSC, and all other requests remain network-only
- Loading, empty, offline, forbidden, not-found, authentication-error, and global-error states
- Static `WAOOAWHome.html` retired; App Router `/` is the single production entry point

### Authorization and Privacy
- Customer routes validate the server session before protected rendering; Founder routes require an explicit validated Founder claim and otherwise redirect to `/403`
- Public navigation emits no protected relationship, employment, evidence, or billing requests
- Registration, verification, conversation transport, relationship integration, Founder operations, voice, attachments, continuity, new APIs, and deployment remain outside F1

### Quality
- Strict TypeScript and Next.js lint: PASS, zero diagnostics or warnings
- Jest/Testing Library: 36/36 PASS; 98.75% overall line coverage
- Playwright/axe: nine logical scenarios across five projects; 38 PASS and 7 expected profile SKIP across Chromium, Firefox, WebKit, 1440×900, 768×1024, and 360×800
- Production build: 20/20 routes generated; shared initial JavaScript 89.5 kB; public route 89.7 kB
- Service-worker audit: one approved static cache, three network-only strategies, zero default API/page/RSC/cross-origin caches, and no precached root HTML
- R-051 remediation adds measured FCP/LCP/CLS/INP assertions and an enabled persistent relationship-route Emergency Stop with compact and expanded keyboard evidence
- R-052 independently approved final F1 acceptance; PR #246 merged to `main` as `798c183` and WC-034 F1 is closed while F2–F8 remain separately gated

---

## [1.44.0] — 2026-08-07 · WC-043 WBE-S8 Reconciliation CCT Suite + Coverage Gate

### Features
- `src/billing-engine/wallet/router.py`: `POST /buckets/{customer_id}/reserve` — C-091 Universal Prepaid Gate HTTP endpoint; 402 BUCKET_EMPTY on empty bucket; 503 BILLING_INTEGRITY_HALT pass-through; 404/409 for not-found/duplicate
- `src/billing-engine/main.py`: wallet router mounted at `/buckets` prefix

### Tests
- `tests/billing-engine/test_ccts.py`: CCT-PREPAID-01 (4 tests), CCT-SELFAUDIT-01 full (3 tests) — 7 new CCTs
- `tests/billing-engine/test_payment.py`: +4 HTTP router tests covering payment/router.py onboarding-order endpoint, webhook ignore, MISSING_CUSTOMER_ID, NOT_A_BYPASS_ORDER
- 361/361 billing-engine tests passing (+11 new)

### Constitutional Compliance
- C-091 Universal Prepaid: WBE enforces 402 before LLM dispatch can proceed
- C-004 Billing Halt: 503 propagated correctly through reserve endpoint
- C-023 Evidence First: `run_self_audit()` emits evidence record on every run (PASS or HALT)
- C-059 Traceability: Founder Action created on any discrepancy > 1 paise

### Quality
- Coverage: 94% (gate: ≥90% ✅)
- ruff: all checks passed

---

## [1.43.0] — 2026-08-07 · WC-042 WBE-S7 Single Onboarding Payment + Renewal Saga

### Features
- `src/billing-engine/payment/`: `OnboardingService` creates single Razorpay order combining first-month subscription + wallet seed (ADR-022 §1.2)
- `src/billing-engine/payment/razorpay_client.py`: Async Razorpay client — all credentials via env vars (ADR-014), HMAC-SHA256 signature verification
- `src/billing-engine/payment/webhook.py`: `WebhookHandler` — idempotent `payment.captured` handler; mode flip before subscription insert (S-09); bypasses HMAC for demo/UAT coupons
- `src/billing-engine/payment/router.py`: `POST /payments/onboarding-order` + `POST /payments/webhooks/razorpay`; registered in `main.py`
- `src/business-platform/Workflows/RenewalFailureSaga.cs`: Temporal saga — Day1/3/7/14 progressive renewal failure; C-049 disclosure at Day3; campaign pause gate at Day7
- `infrastructure/postgres/init/18-wbe-s7-payment.sql`: `business.payment_intents` table + DEMOWAOOAW/UATWAOOAW coupon seeds
- `adr/ADR-022`: Amendment 2 — env-var configuration + lower-environment bypass (FA-029)

### Constitutional Compliance
- C-023 Evidence First: payment_intents IN_PROGRESS recorded before any wallet mutation
- C-090 Grandfather Pricing: `WalletService.renew()` checks `business.price_change_notices` — blocks renewal if plan price > agreed price without acknowledged notice
- C-049 Agent Disclosure: `RenewalFailureSaga` Day3 WhatsApp disclosure when entering degraded mode
- ADR-014 Secret Management: zero Razorpay credentials in source; HMAC verification on every real webhook

### Tests
- `tests/billing-engine/test_payment.py`: CCT-ONBOARD-01 (5 tests), CCT-WEBHOOK-01 (3 tests), CCT-GRANDFATHER-01 (4 tests) = 12 new tests
- `tests/billing-engine/test_wallet.py`: `test_renew_price_increase_raises_422` migrated to mock-session pattern (schema-qualified table compatibility)
- **Total billing-engine: 350/350 (+12)**

### Decisions Recorded
- `security/FOUNDER-ACTIONS.md`: FA-029 — WC-042 authorization + Razorpay env-var decision
- `adr/ADR-022`: Amendment 2 — lower-environment bypass + env-var configuration

Format: [Conventional Commits](https://www.conventionalcommits.org/) —
types: `feat` | `fix` | `constitutional` | `cct` | `chore` | `refactor` | `security` | `docs`

---

## [1.42.0] — 2026-08-07 (WC-041 Skill Architecture Sprint 2: Skill Runtime in Professional Runtime)

### Skill Runtime — ADR-043 §3

**IB:** IB-011 | **Sprint:** WC-041 | **Office:** Platform IT Expert (INST-010)

- `feat(professional-runtime)`: `skill_resolver.py` — `SkillResolver` resolves skill manifests from BP Skill Catalog at session open; `SessionSkillContext` (authorized_tools, crystallizer_configs, dcm_categories, tool_skill_index); `SkillResolutionError` halts session open on unknown skill (ADR-043 §3)
- `feat(professional-runtime)`: `intent_crystallizer.py` — `IntentCrystallizer` produces `LockedArtifact` via LLM + CE approval evidence record (C-023); `CrystallizerRequiredError` blocks tool calls until artifact exists
- `feat(professional-runtime)`: `session_executor.py` — `SessionExecutor` pre-flight gate 1 (C-041 tool authorization) + gate 2 (crystallizer required check); `C041ToolAuthorizationError`; passes `dcm_category` from skill definition to dispatcher (CTG in production)
- `feat(professional-runtime)`: `workflows/paas_workflow.py` — `_locked_artifacts` + `_crystallization_complete` Temporal session state added (ADR-043 §3 — survives session restart)
- `cct(professional-runtime)`: CCT-SKILL-CP-01 — crystallizer produces LockedArtifact before first publish tool dispatch
- `cct(professional-runtime)`: CCT-SKILL-CP-02 — tool call without LockedArtifact raises CrystallizerRequiredError (CONSTITUTIONAL_BLOCKED)
- `cct(professional-runtime)`: CCT-SKILL-CP-03 — dispatcher receives correct dcm_category from skill definition on every tool call
- `cct(professional-runtime)`: CCT-SKILL-UNKNOWN-01 — session open with unknown skill raises SkillResolutionError

**Test results:** PR 20/20 (+10) · TL 27/27 · AIR 22/22 · Total 69/69 · Zero regressions · WC-041 DONE

---

## [1.41.0] — 2026-08-07 (WC-040 Skill Architecture Sprint 1: Skill Catalog + Employment Contract Amendment)

### Skill Architecture Sprint 1 — ADR-043 §2/§4

**IB:** IB-025 | **Sprint:** WC-040 | **Office:** Platform IT Expert (INST-010)

- `feat(business-platform)`: `17-skill-catalog.sql` — `business.skills` table, indexes, RLS policy, `content_publish@1.0.0` seed (ADR-043 §2)
- `feat(business-platform)`: `SkillCatalogDbContext.cs` — EF Core context for `business.skills` table
- `feat(business-platform)`: `SkillsController.cs` — `GET /api/v1/skills`, `GET /api/v1/skills/{id}`, `GET /api/v1/skills/{id}/{version}`, `POST /api/v1/skills` (Founder role + CE gate)
- `feat(business-platform)`: `CustomersController.cs` — `HireAgentRequest` gains `Skills[]`; skill validation pre-gate before CE; 422 `SKILL_NOT_FOUND` for unknown/unpublished skills (C-036)
- `feat(business-platform)`: `AmendContract POST /api/v1/agents/amend` — CE evidence record with `action_type=SKILL_AMENDMENT` required before any amendment (C-023, ADR-043 §4)
- `feat(knowledge)`: `content_publish_v1.0.0.yaml` — first platform skill definition (ADR-043 §1 schema)
- `cct(business-platform)`: CCT-SKILL-CAT-01 — unknown skill on hire → 422 `SKILL_NOT_FOUND` (3 tests)
- `cct(business-platform)`: CCT-SKILL-VER-01 — version pinning: @1.0.0 resolves to @1.0.0, not @2.0.0 (4 tests)
- `cct(business-platform)`: CCT-SKILL-AMEND-01 — skill amendment CE evidence record audit (4 tests)
- `fix(ai-runtime)`: GAP-002 from EA R-022 — startup fail-fast if `_CTG_AVAILABLE=False` in `PLATFORM_PHASE=IMPLEMENTATION`

**Test results:** BP 44/44 (+11) · TL 27/27 · AIR 22/22 · Total 93/93 · Zero regressions

---

## [1.40.0] — 2026-08-07 (WC-039 CTG Library + AIR PSE Router Refactor)

### Trust Layer Sprint 3 — ADR-042 §2 Constitutional Tool Gateway

**IB:** IB-010 | **Sprint:** WC-039 | **Office:** Platform IT Expert (INST-010)

- `feat(trust-layer)`: `ctg/models.py` — `SessionContext`, `MCPToolError`, `GatewayResult`, `ProviderConfig`, `ConstitutionalBlockError`
- `feat(trust-layer)`: `ctg/registry_client.py` — `ProviderRegistryClient` with 60s TTL in-memory cache
- `feat(trust-layer)`: `ctg/exception_translator.py` — sanitising exception-to-`MCPToolError` translation (token never in error payload)
- `feat(trust-layer)`: `ctg/gateway.py` — `ConstitutionalToolGateway` implementing ADR-042 §2 9-step pipeline (CE.ValidateAction → oauth-vault → execute → audit_sink)
- `constitutional(ai-runtime)`: `pse/router.py` — direct LLM dispatch replaced with `gateway.call()` via CTG; `ConstitutionalBlockError` propagates unchanged
- `cct(trust-layer)`: CCT-CTG-01 CE called first before any external call (3 tests)
- `cct(trust-layer)`: CCT-CTG-02 token absent from all error payloads (3 tests)
- `cct(trust-layer)`: CCT-CTG-03 evidence record written to audit sink on every call (3 tests)
- `cct(trust-layer)`: CCT-CTG-04 CE DENY raises ConstitutionalBlockError — vault never called (3 tests)
- `chore(docker)`: `architecture/reference/dockerfiles/Dockerfile.test-runner` — `COPY --chown` eliminates ~500s chown rebuild bottleneck
- `chore(docker)`: `.dockerignore` — build context reduced from 1.52GB to 613KB (excludes .venv, .NET bin/obj)
- `constitutional(docker)`: `ADR-045` — per-service lean Docker image strategy (no multi-runtime images)
- `chore(docker)`: `Dockerfile.test-runner-python` — lean Python-only runner (~350MB vs 1.5GB); BuildKit pip cache mount
- `chore(docker)`: `docker-compose.yml` — `test-runner-python` service added (profile: test-python); monolithic runner deprecated

**Test results:** TL 20/20 · AIR 22/22 · Total 42/42 · ruff clean · Zero regressions

---

## [1.39.1] — 2026-08-08 (WC-038 EA Review — gaps fixed)

### Enterprise Architect Review (INST-004) — R-021

**Review outcome:** 6 gaps found and fixed. WC-039 AUTHORIZED.

- `fix(trust-layer)`: removed dead `_NEVER_LOG` constant from `vault_client.py` (GAP-002)
- `fix(trust-layer)`: removed duplicate `from .models import TokenData` local import in `refresh_scheduler._refresh_token` (GAP-003)
- `fix(trust-layer)`: moved `timedelta` import to module level in `tokens.py` (GAP-004)
- `fix(trust-layer)`: moved `HTTPException` import to module level in `exception_handler.py` (GAP-005)
- `cct(trust-layer)`: +14 tests — TestVaultClientUnit × 5, TestTokensRetrievePaths × 6, TestSchedulerEdgeCases × 3 (GAP-001: C-076 73%→91%)
- `constitutional(adr)`: ADR-042 §1 corrigendum — tenant_id nullability for platform-level rows documented (GAP-006)

**Test results:** CE 82/82 · BP 33/33 · TL 26/26 (+14) · Coverage 91% · ruff clean

---

## [1.39.0] — 2026-08-08 (WC-038 Provider Registry + oauth-vault)

### Trust Layer Sprint 2 — ADR-042 + ADR-021 Implementation

**Constitutional basis:** C-031 (ADR-042 provider routing), C-041 (tool auth), C-003 (authority licensed), ADR-014 (secret management), ADR-021 (OAuth token management)

- `constitutional(bp)`: `business.provider_configs` table — runtime-configurable provider routing; Meta (OAUTH2) + OpenAI (API_KEY) seed rows (`16-provider-registry.sql`)
- `feat(bp)`: `ProviderRegistryDbContext` + `ProviderConfig` entity — EF Core model for provider_configs
- `feat(bp)`: `GET /api/v1/providers` + `GET /api/v1/providers/{name}` — internal Provider Registry API; tenant-specific rows take precedence over platform-level
- `feat(trust-layer)`: `oauth-vault` FastAPI service on port 8130 (ADR-021)
  - `POST /tokens/{contract_id}/{provider_name}` — stores token in Azure Key Vault; registers in refresh scheduler
  - `GET /tokens/{contract_id}/{provider_name}` — retrieves token; auto-refreshes if EXPIRING_SOON
  - `DELETE /tokens/{contract_id}/{provider_name}` — CE evidence record required before AKV delete (C-003)
  - `GET /tokens/health/{contract_id}/{provider_name}` — VALID/EXPIRING_SOON/EXPIRED/NOT_CONNECTED status
- `constitutional(trust-layer)`: Azure Key Vault client wraps sync SDK in `asyncio.to_thread`; no token value ever logged (ADR-014)
- `constitutional(trust-layer)`: 30-minute background refresh scheduler; PLATFORM_TOKEN_EXPIRED notification to PR on failure
- `constitutional(trust-layer)`: `BaseHTTPMiddleware` global exception handler — sanitized 500 response, no token in body
- `cct(trust-layer)`: CCT-VAULT-01 — 3 tests: token never in logs on store/retrieve/error paths
- `cct(trust-layer)`: CCT-VAULT-02 — 2 tests: CE evidence record before AKV delete; 503 if CE unavailable
- `cct(trust-layer)`: CCT-VAULT-03 — 2 tests: EXPIRING_SOON triggers refresh; refresh failure notifies PR
- `cct(trust-layer)`: CCT-TOKEN-HEALTH-01 — 5 tests: VALID/EXPIRING_SOON/EXPIRED/NOT_CONNECTED/API_KEY-no-expiry
- `chore(infra)`: `docker-compose.yml` — `oauth-vault` service on port 8130 with AKV + CE dependencies

**Test results:** CE 82/82 | BP 33/33 | TL 12/12 (new) | Zero regressions

---

## [1.38.0] — 2026-08-07 (WC-037 Constitutional Audit Trail Sink)

### Trust Layer Sprint 1 — ADR-044 Implementation

**Constitutional basis:** C-059 (Traceability), C-078 (DPDPA), ADR-044

- `constitutional(ce)`: `audit_sink` Postgres schema + INSERT-only RLS WORM policy (`14-audit-sink.sql`)
- `constitutional(bp)`: `payload_store` Postgres schema + erasable payload rows (`15-payload-store.sql`)
- `feat(ce)`: `RecordErasure` gRPC RPC added to proto — marks tenant audit records as PAYLOAD_PURGED
- `feat(ce)`: `AuditSinkDbContext` + `AuditSinkEvidenceRecord` entity — audit_sink schema EF Core model
- `constitutional(ce)`: `ValidateAction` now writes one `audit_sink.evidence_records` row per call (ALLOW/DENY/ESCALATED)
- `feat(bp)`: `PayloadStoreDbContext` + `OperationalPayload` entity — payload_store schema EF Core model
- `feat(bp)`: `DELETE /api/v1/customers/{tenantId}/data` — DPDPA Right-to-Erasure endpoint (Founder role only)
- `cct(ce)`: CCT-AUDIT-01 — 6 tests: ALLOW/DENY/ESCALATED paths write audit rows; WORM; RecordErasure stamps PAYLOAD_PURGED; tenant isolation
- `cct(bp)`: CCT-DPDPA-01 — 4 tests: payload wipe; 403 non-founder; 400 missing order ID; tenant isolation

**Test results:** CE 82/82 (±6 new) | BP 33/33 (±4 new) | Zero regressions

---

## [1.37.1] — 2026-08-06 (End-of-Day — EA Architecture + Sprint Planning)

### EA Architecture Session — ADR-042/043/044 + 5 Sprint Contracts

**Constitutional basis:** C-031 (ADR required for architectural decisions)

- `constitutional(arch)`: ADR-042 — Provider Registry + Constitutional Tool Gateway (CTG as shared Python library; AIR breaking change declared)
- `constitutional(arch)`: ADR-043 — Skill Architecture Standard (Skill Runtime in PR, Skill Catalog in BP, 4+1 service mesh preserved)
- `constitutional(arch)`: ADR-044 — Constitutional Audit Trail Sink (WORM audit_sink + erasable payload_store, DPDPA proof/payload decoupling)
- `constitutional(arch)`: C4 container diagram updated to v0.12.0 — oauth-vault, CTG, new Postgres schema zones
- `constitutional(arch)`: WC-037→041 sprint contracts produced (Trust Layer S1/S2/S3 + Skill Architecture S1/S2)
- `cct(arch)`: 13 new CCTs — CCT-VAULT-01/02/03, CCT-CTG-01/02/03/04, CCT-AUDIT-01, CCT-DPDPA-01, CCT-SKILL-CP-01/02/03, CCT-SKILL-CAT-01, CCT-SKILL-VER-01, CCT-SKILL-AMEND-01 (total: 65)
- `docs(strategy)`: Founder strategy session documented — `strategy/FOUNDER-SESSION-2026-08-06-platform-vision.md`
- `constitutional(gov)`: IB-024 (Trust Layer) + IB-025 (Skill Architecture) ratified by Founder
- `constitutional(gov)`: GOAL-WC037 registered; SPRINT_STATE_MACHINE → WC-037 AUTHORIZED
- `docs(repo)`: SPRINT-REGISTRY.md created at repo root — all 40 WCs, active/planned/closed



## [1.37.0] — 2026-08-07

### WC-036: UDCP Pipeline Engine — Complete (124/124 tests, 90.93% coverage)

**Constitutional basis:** ADR-039 §5, C-059, C-076, C-077, C-082, C-097, C-098

#### WC036-06 — test_udcp_engines.py coverage uplift
- `tests/pipeline/test_udcp_engines.py` — 76 → 124 tests
- Added `TestOrchestratorHelpers` class: unit tests for `_fix_b904`, `_hoist_imports`, `_ruff_normalization_check`, `_fix_ruf012`, `_fix_ann201_asynccontextmanager`, `_normalize_and_write`, `_extract_function_block`, `_parse_llm_files_local`
- Added `TestOrchestratorTrack2Integration` class: `_run_track2`, `_patch_artifact`, `_patch_method`, `_append_module_lines` integration paths
- Added `TestOrchestratorDryRunAndInjectFiles` class: dry_run mode, inject_source_files, LLM error paths (LLM_NO_RESPONSE, NO_FILE_BLOCKS, MIXED track)
- Total coverage: 90.93% (≥90% DoD met); udcp_orchestrator: 86%, grooming: 96%, PTR gate: 94%, Track1: 98%, Track2: 90%
- All 5 engine files: `py_compile` → exit 0; `ruff check` → clean

**Engine files completed (previous halted session, verified this session):**
- `scripts/runner/ptr_validation_gate.py` — WorkspaceSymbolIndex, PTR validation gate
- `scripts/runner/track1_scaffolder.py` — conditional APIRouter, LOGIC_FILLER stubs
- `scripts/runner/track2_polymorphic_engine.py` — try/finally decorator guard, splice with compile gate
- `scripts/runner/udcp_grooming_engine.py` — LLM-free TIS/TMD from WC markdown
- `scripts/runner/udcp_orchestrator.py` — Track 1/2 orchestration, logic-fill LLM integration
- `scripts/runner/task_executor.py` — `execute_with_udcp()` entry point for python-stack tasks

---

## [1.36.0] — 2026-08-06

### WC-012: CE gRPC Skeleton (.NET 9) — All 76 CCT Tests Green

**Constitutional basis:** C-027 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling), C-054 (Emergency Stop), C-059

#### WC012-01 — C041 Tool Authorization Evaluator fix
- `src/constitutional-engine/Evaluators/C041ToolAuthorizationEvaluator.cs`
- Fixed: was checking `actionType` against tool name lists; now correctly extracts `tool_name`
  from `ActionParameters` and checks it against `prohibited`/`always_ask`/`authorized` lists
- `ContainsOrdinal` (case-sensitive) replaces `ContainsIgnoreCase` throughout
- Added `ToolNameKey = "tool_name"` and `McpToolCallActionType = "MCP_TOOL_CALL"` constants

#### WC012-02 — C043 Budget Ceiling zero-budget fix
- `src/constitutional-engine/Evaluators/C043BudgetCeilingEvaluator.cs`
- Zero-budget: `approved=0 && proposed=0` → Allow; `approved=0 && proposed>0` → Deny

#### WC012-03 — Evidence StateCode idempotency
- `src/constitutional-engine/Data/Entities/EvidenceRecord.cs` — added `StateCode` field
- `src/constitutional-engine/Services/ConstitutionalEngineService.cs` — idempotency key now
  scoped to (ActionInstanceId, State, TenantId) to allow separate rows per state transition

#### WC012-04 — Test infrastructure (FakeServerCallContext, InMemory schema pre-warm)
- `tests/constitutional-engine.Tests/EmergencyStop/CCT_HO01_EmergencyStopLatencyTests.cs`
- Fixed: `FakeServerCallContext` replaces unmockable Moq stub; EF InMemory `EnsureCreated()`
  pre-warms schema to avoid cold-start latency exceeding 100 ms budget

#### WC012-05 — 10 new C041 test cases (Allow path + ToolMatrix theory)
- `tests/constitutional-engine.Tests/Evaluators/CCT_EF01_C041ToolAuthorizationEvaluatorTests.cs`
- 76/76 CCT tests passing (CE + BP combined: 105/105)

---

### WC-014: PR Python FastAPI + Temporal — 10/10 Tests Green

**Constitutional basis:** C-005 (session isolation), C-059

#### WC014-01 — conftest.py sys.path fix
- `tests/professional-runtime/conftest.py` — `sys.path.insert` for `src/professional-runtime`
- `from main import app` (flat import, not `src.professional_runtime.main`)

#### WC014-02 — MockPAASSessionWorkflow module-level fix
- `tests/professional-runtime/test_sessions.py`
- `@workflow.run` cannot be applied to local inner classes; moved `MockPAASSessionWorkflow`
  to module level; removed 3 duplicate inner class definitions
- 10/10 tests passing

---

### WC-015: AIR Python (PSE, RAG, PII, Ollama) — 32/32 Tests Green

**Constitutional basis:** C-062 (injection guard), C-023, C-059

#### WC015-01 — InjectionGuard scan() sync fix
- `src/ai-runtime/pii/injection_guard.py`
- Changed `async def scan()` to synchronous `def scan()` — was returning an unawaited coroutine
  (always truthy), causing all injection attacks to pass through

#### WC015-02 — Comprehensive injection pattern coverage (CCT-PI-01: 50/50)
- Added 10 new regex pattern categories covering: injection syntax (SQL, shell, template, EL,
  YAML, PHP, XXE, LDAP, path traversal, protocol handlers, XSS, base64), unicode obfuscation
  (BiDi, zero-width, NBSP, ANSI, soft-hyphen, variation selectors, Cyrillic/Greek/Armenian
  homographs, combining diacritics)
- Added obfuscation-aware scan transformations: ROT13 decode, text reversal, leet-speak
  normalisation, pig-Latin decoding, NFKD+diacritic-strip, bracket-stripping, alpha-only
  keyword substring scan
- 32/32 AI-runtime tests passing (CCT-PI-01: 50/50 attack patterns blocked, 10/10 legitimate prompts allowed)

---

## [1.35.0] — 2026-08-06

### WC-033: BP Trial Lifecycle Endpoints + Temporal Expiry Saga

**Constitutional basis:** C-023 (phone gate), C-088 (trial billing mode), C-090 (grandfather at conversion), C-059, C-076

#### WC033-01 — SubscriptionsController (POST /api/v1/subscriptions/trial-start)
- `src/business-platform/Controllers/SubscriptionsController.cs` (new)
- C-023 gate: `phone_verified=false` → 422 `PHONE_NOT_VERIFIED` before any WBE call
- On `phone_verified=true`: calls WBE `POST /trial/start` via `IHttpClientFactory` ("WBE" client)
- WBE 409 `TRIAL_ALREADY_USED` propagated as 409 to caller
- WBE unavailable → 503; WBE 5xx → 502

#### WC033-02 — TrialExpiryWorkflow (Temporal saga)
- `src/business-platform/Workflows/TrialExpiryWorkflow.cs` (new)
- `[Workflow] TrialExpiryWorkflow.RunAsync(TrialExpiryInput)`: Temporal-durable sleep until
  `expires_at - 48h` → `SendReminderAsync`, sleep until `expires_at` → `CheckTrialStatusAsync` →
  if not `CONVERTED`: `MarkLapsedAsync` (C-088 billing state transition)
- `TrialExpiryActivities`: `SendReminderAsync` (non-fatal), `CheckTrialStatusAsync` (returns UNKNOWN on failure),
  `MarkLapsedAsync` (throws on WBE failure — Temporal retries)
- `src/business-platform/business-platform.csproj`: added `Temporalio 1.4.0` + `Temporalio.Extensions.Hosting 1.4.0`
- `Program.cs`: `AddHttpClient("WBE")` + conditional `AddHostedTemporalWorker("bp-trial-worker")` (skipped if `Temporal:Host` not configured)

#### WC033-03 — Tests
- `tests/business-platform.Tests/SubscriptionsControllerTests.cs` (new): 7 controller tests via WebApplicationFactory
  - CCT-PHONE-01: `phone_verified=false` → 422, WBE not called
  - Happy path: WBE 200 → BP 200 + TrialStartResponse
  - WBE 409 → BP 409 conflict propagation
  - WBE unavailable → 503; WBE 5xx → 502; no auth → 401
- `tests/business-platform.Tests/TrialExpiryWorkflowTests.cs` (new): 12 tests
  - Workflow tests via `WorkflowEnvironment.StartTimeSkippingAsync()` (Temporal time-skipping)
  - 48h reminder fires once; ACTIVE at expiry → LAPSED; CONVERTED → skip lapse
  - Already-expired trial completes; UNKNOWN status → LAPSED (safe default)
  - Activity unit tests: SendReminder non-fatal; CheckStatus returns UNKNOWN on failure; MarkLapsed throws on failure

**29/29 tests passing (19 new + 10 pre-existing). Billing-engine 338/338 unchanged.**

---

## [1.34.0] — 2026-08-06

### WC-032: AIR PSE Trial Tier Override

**Constitutional basis:** C-049 (Honest Limitation), C-059 (Traceability), C-076 (≥90% coverage)

#### WC032-01 — PSE Router Trial Override (additive, ≤15 lines)
- `src/ai-runtime/pse/router.py`: `route_and_dispatch()` gains two optional params
  `customer_id: str | None` and `redis_client: Any | None`
- After `_select_tier()`, reads `wbe:customer:{customer_id}:mode` from Redis;
  if `b"TRIAL"` → forces `LlmTier.LOCAL` regardless of configured tier (C-049)
- Zero new error paths: Redis unavailability falls through to existing tier

#### WC032-02 — Tests: CCT-TRIAL-02 + full PSE coverage
- `tests/ai-runtime/test_pse_router.py` (new): 24 tests across 5 classes
- **CCT-TRIAL-02**: TRIAL Redis key → LOCAL dispatch regardless of complexity (complex→LOCAL, medium/indic→LOCAL)
- Non-TRIAL mode (ACTIVE key) → configured tier unchanged
- TTL expiry (no key) + no redis_client + no customer_id → all fall back to configured tier
- `_dispatch_ollama`: success, timeout, HTTP error, request error (respx mocks)
- `_dispatch_mid` / `_dispatch_frontier`: NotImplementedError stubs verified
- Error handlers: CancelledError, TimeoutException, HTTPStatusError, RequestError — all record evidence then re-raise
- `tests/ai-runtime/conftest.py`: fixed `sys.path.insert` pattern (was broken with `src.ai_runtime` import)

#### Coverage
| Module | Coverage |
|---|---|
| `pse/router.py` | **91%** |
| `pse/tiers.py` | 100% |
| Total pse/ | **91.84%** |

**24/24 tests passing. Billing-engine: 338/338 unchanged.**

---

## [1.33.0] — 2026-08-07 (WC-031 — Trial Engine + Promotions Engine)

### Feat (Billing Engine — WC-031 GOAL-005)

- **`src/billing-engine/trial/`** — WBE sub-component 6 (TrialService + router)
  - `start_trial()`: phone-verify gate (C-019), TRIAL_FREE_UNITS config, ONE DB transaction (trial_allocations + wallet_buckets + trial_free_unit_ledger), Redis `wbe:customer:{id}:mode=TRIAL` set after commit (non-fatal on Redis failure)
  - `check_expiry()`: marks EXPIRED, clears Redis key; idempotent
  - `convert_to_paid()`: marks CONVERTED, C-090 grandfather within 14 days, sets Redis mode=ACTIVE
  - `get_status()`: returns TrialStatus with units_consumed/remaining per thread_type
  - Router: `POST /trial/start`, `GET /trial/status/{customer_id}`, `POST /trial/convert` (ops-auth)
- **`src/billing-engine/promotions/`** — WBE sub-component 7 (PromotionsService + router)
  - `validate_coupon()`: COUPON_EXPIRED/USED/AGENT_MISMATCH/TIER_MISMATCH/DISCOUNT_EXCEEDS_CAP checks (C-088 cap enforcement)
  - `apply_discount()`: atomic uses_count increment, referral credit trigger on PENDING referral
  - `credit_referrer()`: idempotent UPDATE WHERE credit_status=PENDING; adds credit to referrer wallet
  - Router: `POST /promotions/validate-coupon`, `POST /promotions/apply-discount`, `GET /promotions/referral-status/{customer_id}`
- **CCTs passing**: CCT-TRIAL-01, CCT-TRIAL-02 (billing layer), CCT-COUPON-01, CCT-REFERRAL-01
- **`tests/billing-engine/test_trial.py`**: 26 tests, trial/ 93%
- **`tests/billing-engine/test_promotions.py`**: 24 tests, promotions/ 92%
- **`src/billing-engine/main.py`**: trial + promotions routers mounted
- **`tests/billing-engine/conftest.py`**: TRIAL_FREE_UNITS, TRIAL_DURATION_DAYS, MAX_DISCOUNT_PCT added to settings stub
- **Full suite: 338/338 tests passing**

---

## [1.32.0] — 2026-08-07 (WC-025 + WC-030 Audits — Thread Catalog & Reconciliation Coverage)

### Fix (Billing Engine — Manual Audit)

- **WC-025 test_thread_catalog.py expanded:** 12 tests → 23 tests; database.py 0% → 100%, thread_catalog.py 88% → 90%
  - `TestDatabaseModule` (7 tests): init_db, get_session_factory, close_db, get_db using `importlib` to bypass conftest stub
  - `TestThreadCatalogSingletons` (4 tests): `_get_redis()` and `_get_session_factory()` init branches (lines 31–33, 43–46) + already-initialised return paths
- **WC-030 test_reconciliation.py expanded:** 14 tests → 24 tests; service.py 86% → 98%, scheduler.py 39% → 91%
  - Scheduler: `_run_daily_reconciliation` full execution, error propagation; `_trigger_meter_daily_scan` success/HTTPStatusError/RequestError
  - Service: `founder_action_created=True` path, `revenue_paise==0 → margin 100%`, exception handlers in `run_daily_audit`/`run_self_audit`/`generate_margin_report`, two-bucket loop branch coverage
- **WC-030 test_reconciliation_router.py expanded:** 18 tests → 20 tests; router.py 91% → 93%
  - `_get_redis` line 40 direct-call test; `_require_ops_auth` line 56→exit with valid token
- **Full suite: 288/288 tests passing; total coverage 95.09%**

---

## [1.31.0] — 2026-08-06 (WC-026 Audit — Wallet Engine Coverage)

### Fix (Billing Engine — Manual Audit)

- **WC-026 test_wallet.py expanded:** 9 tests (60% coverage) expanded to 22 tests; coverage 60% → 98.72%; service.py 98%
- **Schema extended:** `employment_contracts` gains `agreed_price_paise`, `plan_price_paise`, `thread_type`, `period_start`, `renewed_at`; new tables `billing_profiles`, `customers`, `subscriptions` for `activate_subscription()` coverage
- **13 new tests:** `reserve()` success/idempotency/insufficient-balance/Redis-fail-safe; `release()` consumed=True/False/not-found; `activate_subscription()` authorized/403; `renew()` success/C-090-guard/not-found
- **DoD verified:** reserve idempotency (DuplicateReservationError), C-090 price-increase guard, release refund path, C-088 billing profile check
- **Full suite: 264/264 tests passing**

---

## [1.30.0] — 2026-08-06 (WC-027 Audit — Markup Engine Coverage)

### Fix (Billing Engine — Manual Audit)

- **WC-027 test_markup.py rewritten:** 8 mock-SUT tests (51% coverage) replaced with 33 real-service tests; coverage 51% → 94.67%; bundle_engine.py 100%, router.py 100%
- **BundleEngine unit tests (14):** cost_floor DB read, derive_price with default/target margin, margin=100 guard, validate_price APPROVED/REJECTED paths, C-088 FOUNDER_AUTHORIZED enforcement, C-059 audit log commit verified
- **thread_catalog unit tests (12):** cache miss/hit paths, get_thread per-key cache, invalidate_cache Redis flush, list_threads/get_thread_entry/invalidate_thread_cache router handlers
- **get_bundle_engine dependency test:** covers router.py line 28 (100% router coverage)
- **Full suite: 251/251 tests passing** after WC-027 audit
- **Constitutional verified:** C-059 (audit log on BOTH outcomes), C-088 (billing status check), C-089 (margin floor formula), C-091 (thread catalog delegation)

---

## [1.29.0] — 2026-08-06 (WC-028/029 Audit Remediation + Pipeline v2 Design)

### Fix (Billing Engine — Manual Audit)

- **WC-028 test_meter.py rewritten:** 12 mock-only tests (0% coverage) replaced with 41 real-service tests; coverage 0% → 90.24%; all DoD items verified (WARN_10 at 8% remaining, 24h dedup, quiet hours, RUNWAY_P0, CCT-BILLINGLOOP-01)
- **WC-029 procurement bugs fixed (4):** `get_all_runway_statuses` method name, `await` on sync classmethod removed, `rule.days_remaining_trigger` attribute name, `ProviderRunwayStatus` import source corrected; 35 tests, 93.59% coverage
- **wallet/models.py created:** `BucketBalance`, `BucketReservation` dataclasses resolving 0% coverage on test_wallet.py (WC-030 gap)
- **Full suite: 226/226 tests passing** after all three audits

### Docs (Architecture)

- **PIPELINE-V2-PHASE-MODEL.md:** 7-phase autonomous sprint pipeline redesign — root cause analysis (5-why, 6 defect classes), phase model with design emergence / unit / static / integration / contract+security / CCT phases, concrete refactoring plan on existing infrastructure (pytest_cov gate, sut_module field, import_check gate, design_verify gate), implementation tracking IB table

---

## [1.27.0] — 2026-08-04 (Pipeline Hardening + C-100 + WC-028 Stage-Set)

### Constitutional

- **C-100 ratified:** CORS Security Obligation — HTTP services MUST NOT combine `allow_origins=["*"]` with `allow_credentials=True` (OWASP A05). Wildcard origin requires `allow_credentials=False`; credentials require explicit origin allowlist.
- **Claims count:** 97 ratified (C-001→C-100, gaps at C-087/C-092/C-093)

### Agent Spec

- **Platform IT Expert (INST-010) Skill 15:** YAML Authoring and Validation — authoring standards, embedded script rules for GHA `run: |` blocks, validation gate commands, common defect table
- **Skill catalogue updated:** 14 → 15 SDLC Skills

### Fix (CI/Pipeline)

- **GHA graceful exit path (3 defects):** `halt_check` step now has `if: always()` — outputs always emitted even when health check fails; new `Increment consecutive_failures` step fires on health check failure; `SPRINT_RESULT` now reports `FAILED` not `UNKNOWN` on pre-flight error
- **env_validator namespace package detection:** `_collect_local_modules()` now scans conftest sys.path-injected directories for namespace packages (Python 3.3+ dirs without `__init__.py`) — prevents false-positive third-party import failures for local service packages
- **UDCP LOGIC_FILLER idempotency:** `_all_outputs_present_and_compile()` rejects files containing `# [WAOOAW_LOGIC_FILLER_START]` — prevents skipped_idempotent false positives
- **C-100 LLM enforcement:** CORS forbidden pattern added to `_PYTHON_FORBIDDEN_PATTERNS` in every UDCP code generation prompt
- **azure/get-keyvault-secrets replaced:** Abandoned action (only v1 existed) replaced with inline `az keyvault secret show` across all 3 GHA jobs

### Fix (WBE — WC-027 post-run audit)

- **SEC-01:** `allow_origins=["*"]` + `allow_credentials=True` → fixed to `allow_credentials=False` + restricted methods/headers (OWASP A05)
- **BUG-01/02:** Stale FastAPI app init in `models.py` and `bundle_engine.py` removed
- **BUG-03:** 14 LOGIC_FILLER stub test functions replaced with 17 real tests (8 in test_markup.py, 9 in test_models.py)
- **BUG-04:** `BundleEngine` restored to inherit `IMarkupEngine` ABC; `skeleton/wbe_interfaces.py` recovered from git
- **skeleton/__init__.py:** Added — `env_validator` now correctly classifies `skeleton` as a local package

### CCT

- **SIM-PL-002 for WC028-01/02/03:** Pre-execution simulations with PASS verdict committed — C-086 gate unblocked for WC-028 sprint

### Chore

- **Sprint advanced:** WC-027 → WC-028 (Meter + Alert Engine)
- **knowledge/index.md:** C-100 row added

---

## [1.26.0] — 2026-08-04 (Track 1 Constitutional — C-099 Decision Consequence Map)

### Constitutional

- **C-099 ratified:** Decision Consequence Map obligation — every agent must classify each consequential decision as `DETERMINISTIC_REQUIRED` (irreversible/financial/constitutional) or `CONSISTENT_SUFFICIENT` (reversible/retryable/advisory) before committing. CE.ValidateAction extended with DCM category routing: PROCEED_AUTONOMOUS / PROCEED_DETERMINISTIC / BLOCKED.
- **AGENT-AUTHORING-GUIDE v5.0:** New §9k (Section 3.25 DCM standard), Activation Gate Section 16 (DCM Gate, 5 checks), Constitutional Checklist C-099 check added. Gate count 15 → 16.
- **CONSTITUTIONAL_DNA v2.0:** §1.2a Decision Consequence Map Consultation runtime pattern added as universal instinct. Every agent inheriting v2.0 gets the DCM consultation pseudocode and CE.ValidateAction response code table.

### Agent Uplift (all 7 specs — C-099 compliance)

- `trading-agent`: trade_execution / position_rebalance / customer_charge = DETERMINISTIC_REQUIRED
- `agricultural-advisor-agent`: pmfby_submission / financial_recommendation = DETERMINISTIC_REQUIRED
- `platform-operations-agent`: config_change / kill_switch / emergency_stop = DETERMINISTIC_REQUIRED
- `digital-marketing-agent`: campaign_publish / ad_spend / customer_charge = DETERMINISTIC_REQUIRED
- `private-tutor-agent`: customer_charge / lesson_plan_commitment = DETERMINISTIC_REQUIRED
- `reasoning-sprint-analyst-agent`: sprint_auth / claim_proposal / state_machine_update = DETERMINISTIC_REQUIRED
- `self-improvement-analyst-agent`: prompt_version_promotion / spec_amendment = DETERMINISTIC_REQUIRED

---

## [1.23.0] — 2026-07-31 (GEOM G-1→G-5 Pipeline — WBE WC-027→031 + WC-027 Activated)

### Institutional Records (Goal Orchestrator)
- **GOAL-WC027** `goals/GOAL-WC027-markup-engine.md` — GEOM G-1→G-7, 3 spec gaps resolved (markup_thread_catalog non-existent → bundle_profiles; validate_price signature; minimum_compliant_price_paise)
- **GOAL-WC028** `goals/GOAL-WC028-meter-alert-engine.md` — GEOM G-1→G-7, 6 spec gaps resolved (amount_paise; meter_alert_log DDL in migration; WARN_10 at 8% remaining; pct_consumed formula)
- **GOAL-WC029** `goals/GOAL-WC029-procurement-ledger.md` — GEOM G-1→G-7, 8 spec gaps resolved (provider_account_id UUID FK; FA format; cost_paise already INR paise; ProviderAccount phantom columns)
- **GOAL-WC030** `goals/GOAL-WC030-reconciliation-engine.md` — GEOM G-1→G-7, 6 spec gaps resolved (self-audit formula; clear_halt() no args; cross-sprint wallet/service.py reserve() billing halt guard)
- **GOAL-WC031** `goals/GOAL-WC031-trial-promotions.md` — GEOM G-1→G-7, 9 spec gaps resolved (phone_verified gate; direct wallet_buckets insert; settings.TRIAL_FREE_UNITS; DB-then-Redis; Temporal caller; credit_referrer chain)

### Work Contracts (SA-corrected)
- `work-contracts/WC-027` through `WC-031` — all task tables corrected per EA gap analysis
- `pmo/BLUEPRINT-PLAN-WBE-GOAL005.md` — Phases 1-5 annotated as GO-validated

### DB Migrations
- `infrastructure/postgres/init/12-billing-engine.sql` — `meter_alert_log` table (WC-028 SA amendment)
- `infrastructure/postgres/init/13-customer-acquisition.sql` — GOAL-005 tables (trial_allocations, coupon_codes, referral_records)

### Sprint Activation
- WC-027 Markup Engine: `autonomous_halt: false` — READY for CI workflow dispatch

---

## [1.22.0] — 2026-07-30 (Runner Package Extraction + Prompt Caching)

### Refactored
- **`scripts/runner/` package**: Extracted 8 focused modules from `autonomous_sprint_runner.py` (4,034 → 1,572 lines). Modules: `constants`, `state`, `git_ops`, `system_prompts`, `sprint_ops`, `llm_codegen`, `task_executor`, `legacy_handlers`.
- **Anthropic prompt caching** (`anthropic-beta: prompt-caching-2024-07-31`) added to all LLM call sites in `llm_codegen.py` and `groom_sprint.py` — system prompt cached as `ephemeral` block. Tokens procured once and reused across retries (C-077 cost reduction).
- `run_runner_integrity_checks` now accepts `namespace: dict | None = None` for testability; `main()` passes `globals()` explicitly.
- `RUNNER_ANCHOR` and `TASK_HANDLERS` preserved in `autonomous_sprint_runner.py` entry-point — `groom_sprint.py` injection workflow unchanged.

### Tests
- **129 new tests** in `tests/runner/` — 95%+ line coverage for all 8 runner modules.
- `pyproject.toml` `pythonpath = ["scripts"]` added so pytest resolves `runner` package from `scripts/runner/`.
- All 77 existing `tests/test_groom_sprint.py` tests continue to pass (206 total).

---

## [1.16.0] — 2026-07-28 (Pipeline Hardening — Live Sprint Observation)

Fixes identified during live WC-012 sprint run #30370343008.

### Root Cause Fixes (not band-aids)

- **fix(ai)**: Retry advisor was dead on every GoalExecutor call — `sprint_retry_advisor.py` loaded via `importlib.util` without registering in `sys.modules` before `exec_module`. `@dataclass` decorator needs the module in `sys.modules`; got `None` → `AttributeError` on every compile failure. Every retry was blind (raw error, no diagnosis). Fix: `sys.modules['sprint_retry_advisor'] = _m` before `exec_module`.

- **feat(ai)**: `ContextBuilder` EXISTING_FILE slot — when `output_file` already exists on the sprint branch, auto-inject current content into context before LLM call. LLM sees the file to extend on attempt 1, not assumptions. Prevents replace-not-extend failures proactively.

- **refactor(ai)**: Frozen signatures auto-injected in `_build_effective_check()` — for every file in `output_files` that exists on the sprint branch, inject its frozen API signatures from `frozen-artifacts.json` (or first 40 lines if not yet frozen). Structural replacement for hardcoded API guidance in `SubTaskDef.constitutional_check` strings.

- **fix(ai)**: `intelligence.py` `scripts.` dot-notation imports → `magic_llm.` — `goal_orchestrator/__init__.py` eagerly imports `GOIntelligence`; `intelligence.py` used `from scripts.magic_llm.*` which only works when repo root (not `scripts/`) is on `sys.path`. Broke GoalExecutor import on every Actions run.

- **fix(workflow)**: Review job runs on `PARTIAL` result reverted — PARTIAL correctly means sprint incomplete; review should not fire. Identified root cause: WC012-03b failed, not a workflow issue.

- **fix(sprint)**: WC012-02c CCT test API mismatch — constitutional_check told LLM to use `FakeServerCallContext` as second arg to `EvaluateAsync`; actual signature is `(EvaluationContext, CancellationToken)`. Fixed to grounded API spec.

### Sprint Run Results (Run #30370343008)
- WC012-01 ✅ deterministic scaffold — 7 files, dotnet build PASS
- WC012-02a ✅ deterministic interfaces — 4 files, compile PASS
- WC012-02b ✅ 6 evaluators + ConstitutionalEngineService via inline MagicLLM (GoalExecutor import fix not yet deployed for this run)
- WC012-02c ✅ CCT test files via GoalExecutor canonical path (first live GoalExecutor execution), Cascade L1 resolved both files
- WC012-03a ✅ deterministic data layer — ConstitutionalDbContext, EvidenceRecord
- WC012-03b ❌ LLM replaced ConstitutionalEngineService.cs instead of extending (EXISTING_FILE slot + frozen sig injection fixes this for next run)
- PR #143 closed, branch deleted — fresh run queued


## [1.15.0] — 2026-07-28 (GO Seam + MagicLLM Hardening)

### Autonomous Sprint — GO Seam Closed (A7)
- **feat**: `execute_file_by_file()` Path 1 exception handling tightened — `ImportError` falls back silently; runtime errors log prominently and retry failed files only (not the whole batch)
- **feat**: `autonomous_halt: false` — WC-012 sprint AUTHORIZED; `sprint_status: AWAITING_GO` → `AUTHORIZED`
- **constitutional(GEOM.md)**: EEM Step 08 updated to correct execution path: `runner → execute_file_by_file → GoalExecutor → ContextBuilder §7 → MagicLLM → ResponseEvaluator §8 → CascadeHandler`
- **constitutional(BOOTSTRAP.md)**: STEP 5 now mandates GEOM.md read for Platform IT Expert + Goal Orchestrator offices

### GoalExecutor Hardening (scripts/goal_orchestrator/goal_executor.py)
- **fix**: Cascade `original_request` — `set_original_request()` now called before `on_gate_fail()`; every L1 retry has context (was raising `ValueError` silently)
- **fix**: `_call_llm` Docker-safe fallback — `ImportError` from `autonomous_sprint_runner` now falls through to direct `MagicLLMPipeline` call instead of returning `None`
- **fix**: `model_hint` routing — `"reasoning"` → `TEST_GENERATION` (Sonnet), `"auto"` → complexity-scored, `"none"` → `CODE_GENERATION` (Haiku)
- **fix**: `_ANTHROPIC_HAIKU` model name — `claude-haiku-20240307` → `claude-haiku-4-5`
- **fix**: `_load/_save_file_failure_counts` — `fcntl.LOCK_SH/EX` prevents JSON corruption under concurrent Docker requests
- **feat**: Docker-safe `_parse_llm_files_local` + `_write_llm_files_local` with `_WRITE_BOUNDARY` guard

### Pipeline Security + Performance (scripts/magic_llm/)
- **security(S1)**: `_investigate_repo()` applies `_sanitize_input()` at function boundary for all callers — strips prompt injection patterns, truncates to 500 chars
- **fix(R4/R5)**: 3 silent `except: pass` blocks replaced with named + printed exceptions in `goal_executor.py` and `context_builder.py`
- **perf(P2)**: 12 inline `re.compile/search/findall` → 6 module-level `_RE_*` constants in `response_evaluator.py` + `context_builder.py`
- **perf(P3)**: `ContextBuilder._read_cached()` — mtime-keyed per-instance cache; spec + prior files read once across 3-attempt retry loop
- **feat(STACK_BEHAVIORAL_RULES)**: `_build_system()` now injects ERROR HANDLING RULE 1–5 (dotnet/python) into every LLM SYSTEM slot from `task_decomposer.STACK_BEHAVIORAL_RULES`

### MagicLLM Service Hardening (docker/magic-llm-validation branch)
- **security(OWASP A1)**: `_validate_output_files()` — path traversal blocked at request boundary (`../../etc/passwd` → 400)
- **security(OWASP A5)**: `_validate_spec_sections()` — 50K chars/section cap, 20 sections max; 200KB input was producing 601K char context
- **fix**: `_repo_root` depth corrected (`/app/scripts` → `/app`) — failure-count persistence, ContextBuilder reads, frozen registry all correct
- **fix(ANNOTATION gate)**: ANNOTATION gate false negative — now checks XML blocks in `raw_response` when `written_files=[]`

### Workflow Fixes (.github/workflows/autonomous-sprint.yaml)
- **fix(W1)**: `pre_sprint_sim.py` was invoked 3× per run → run once, capture to `$SIM_OUT`
- **fix(W2)**: Dead Python heredoc in `halt_check` (printed to stdout, wrote nothing to `$GITHUB_OUTPUT`) → removed
- **fix(W3)**: `SPRINT_HALT_REASON` used YAML `>= '3'` (string comparison) → computed numerically in bash
- **fix(W4)**: Monitor job skipped when preflight job itself failed → added `preflight.result == 'failure'` clause
- **fix(W5)**: `grep -c` pipe from `python3` masked python3 failure → grep from `$SIM_OUT` variable

### Tests
- **cct**: `tests/constitutional/pipeline/test_goal_executor_retry.py` — 6 new CCT-GO tests (retry loop attempts 2/3, model_hint routing, concurrent file locking, cascade ordering)


## [1.5.0-doc] — 2026-07-24 (Design & Pipeline Hardening)

### Constitutional (3 new claims — total 85 ratified)
- **C-083**: Emit-Transport-Listen Obligation — every agent must emit structured signals at each action boundary; streaming visibility is distinct from Evidence First (C-023) outcome records
- **C-084**: Step Dependency Ordering — step N+1 must not execute if step N produced FAIL/HALT/ERROR; formalises RC#1 pipeline fix; basis for CCT-DEP-01
- **C-085**: Idempotency Obligation — before executing any step with external side effects, check for existing SUCCESS signal; prevents duplicate emails/trades/commits on Temporal retry or cron re-run

### Constitutional (previously missing from index — now indexed)
- C-077: Development Tooling Cost Ceiling (₹5,000/month, ratified 2026-07-23)
- C-078: LLM Constitutional System Prompt mandatory (ratified 2026-07-23)
- C-079: CE fail-safe unavailability (fail-safe deny, ratified 2026-07-23)
- C-080: Docker Test Isolation — no virtual environments (ratified 2026-07-23)
- C-081: Approved Reference Dependency Files (ratified 2026-07-23)
- C-082: Build Validation for All Stacks (ratified 2026-07-23)

### Pipeline (sprint runner + workflow)
- **feat**: Sprint Monitor (`scripts/sprint_monitor.py`) — C-069 self-improvement loop in every sprint run; classifies INFRA_ERROR / CASCADE_PIPELINE_BUG / IDEMPOTENCY_BUG / SPEC_GAP_GENUINE; auto-closes false issues; drafts constitutional proposals
- **fix**: RC#1 — Sprint halts when scaffold task fails (SCAFFOLD_TASKS frozenset + break in execution loop)
- **fix**: RC#2 — tasks_done written per task success via set-list command (C-085 idempotency)
- **fix**: RC#3 — FakeServerCallContext replaces Moq non-virtual mock (10/11 → 11/11 tests)
- **fix**: Monitor signal artifact uploaded from execute job (was incorrectly in preflight)
- **fix**: Monitor scaffold detection from SCAFFOLD_TASKS frozenset (not positional tasks[0])
- **fix**: Sprint Dashboard only updated when actionable — no noise on ALL_PASS runs
- **fix**: Constitutional proposal deduplication — query GitHub before creating
- **fix**: sprint_state.py set-list command (restored after automated edit removal)
- **fix**: Workflow YAML job dependency `monitor needs report` (broken dep caused push-validation failure runs)
- **fix**: sprint_status backtick artifact in PROJECT_STATE.md narrative text

### Tests (CCTs)
- **cct**: CCT-EF-01 — Evidence First: PersistEvidence MUST complete before TriggerTemporalSignal (4 cases)
- **cct**: CCT-HO-01 — Emergency Stop handler ≤100ms budget, 20-run P99 (2 cases)
- **feat**: Evaluator test suite — C-041/C-043/C-048/C-049/C-051/C-062 + EvaluatorRegistry ordering (27 cases)
- **fix**: TenantMetadataExtractor tests — FakeServerCallContext (11 cases; was 1/11 passing)
- **Total**: 42/42 CCT tests pass

### Housekeeping
- `.gitignore`: sprint-context/index.json + monitor-signal.json (regenerated artifacts)
- Closed false spec-gap issues #26–#35 (pipeline bugs, not spec gaps)
- Closed RCA issue #36, pre-runner gap issue #12

---

## [0.99.0] — 2026-07-22

### Fix (infrastructure — GAP-1 complete)
- **GAP-1 fully resolved**: all 14 remaining MCP stub services migrated from inline `python -c` to `mcp_stub_server.py`
  - `signal-watch-worker`: replaced inline Python with YAML-safe shell heartbeat loop
  - `linkedin-mcp` (8139), `x-mcp` (8140): migrated to generic stub server
  - `pinterest-mcp`: port corrected 8145→8151 (was conflicting with `reputation-mcp`)
  - `threads-mcp`: port corrected 8146→8152 (was conflicting with `booking-mcp`)
  - `youtube-mcp` (8141), `ga4-mcp` (8142), `instagram-messaging-mcp` (8143), `instagram-comments-mcp` (8144): migrated
  - `reputation-mcp` (8145), `booking-mcp` (8146), `cms-mcp` (8147), `whatsapp-flows-mcp` (8148): migrated
  - `zomato-mcp` (8149), `swiggy-mcp` (8150): migrated
- `docker compose config`: EXIT 0, zero port conflicts, zero inline `python -c` remaining
- **WC011-01 (docker-compose validation) now passes cleanly** — SIM-023 gap register fully resolved

---

## [0.10.1] — 2026-07-08

### Fix (gate violation correction)
- **OD-008 CRITICAL**: Removed premature IB-009 implementation code from `src/`
  - `src/constitutional-engine/`, `src/business-platform/`, `src/professional-runtime/`, `src/ai-runtime/` — all removed
  - `tests/constitutional/bp/test_cct_ef_01.py` — removed (premature)
  - Code was constitutionally correct in content but produced without Founder authorization
  - Implementation requires explicit Founder authorization per session — G5 CLEAR is not authorization

### Constitutional (gate enforcement)
- `constitution/BOOTSTRAP.md`: IMPLEMENTATION GATE hard stop added
  - G5 CLEAR = prerequisites met, NOT authorization to write code
  - Any action creating files in src/ requires explicit Founder confirmation
- `constitution/AGENT-ENTRY.md`: Implementation gate at the very top — visible every session
- `.github/copilot-instructions.md`: IMPLEMENTATION GATE section added as ABSOLUTE rule
- `work-contracts/operational-discoveries.md`: OD-008 violation recorded with root causes

### Documentation
- `README.md`: Version 0.10.1, G5 wording corrected to "prerequisites met — awaiting Founder authorization"

---

## [0.10.0] — 2026-07-08 (VIOLATION — premature implementation, corrected by 0.10.1)

The v0.10.0 implementation artifacts (src/) were produced without explicit Founder authorization.
They are preserved in git history for institutional transparency but removed from working tree.
See OD-008 in work-contracts/operational-discoveries.md for full analysis.

---

## [0.9.0] — 2026-07-08
- `src/constitutional-engine/`: .NET 9 gRPC service skeleton
  - ConstitutionalServiceImpl: RecordEvidence (writes to DB), ValidateAction stub, TriggerEmergencyStop
  - Evidence First enforced: write confirmed before returning OK; gRPC INTERNAL on failure
  - State transition validation (evidence-schema.md)
  - ConstitutionalDbContext with EvidenceRecord + AuthorityLicense entities
  - Dockerfile (multi-stage, non-root, grpc_health_probe)
- `src/business-platform/`: .NET 9 REST service skeleton
  - POST /api/v1/employment/contracts — Evidence First: CE called BEFORE SaveChangesAsync
  - GET /api/v1/employment/contracts/{id}
  - GET /health
  - TenantDbCommandInterceptor: SET LOCAL app.tenant_id on every DB command
  - JWT middleware: RS256, algorithm enforcement, tenant_id extraction
  - BusinessDbContext with EmploymentContract entity
  - Dockerfile (multi-stage, non-root)
- `src/professional-runtime/`: Python FastAPI skeleton
  - GET /health
  - WSS /ws/emergency-stop (stub — READY frame, PING/PONG, EmergencyStop stub)
  - POST /api/v1/paas/sessions (stub)
  - Dockerfile + pyproject.toml
- `src/ai-runtime/`: Python FastAPI skeleton
  - GET /health
  - POST /api/v1/inference (stub with C-041 enforcement placeholder)
  - POST /api/v1/tools/execute (MCP stub — default deny enforced)
  - Dockerfile + pyproject.toml
- `tests/constitutional/bp/test_cct_ef_01.py`: CCT-EF-01 Evidence First pattern tests
  - EF01_a/b: CE called before SaveChanges, failure path exists
  - EF01_c: action_instance_id present
  - EF01_d: constitutional_basis provided (AD-008)

### Reviews
- R-011: EA review of digital-marketing-agent.md — APPROVED WITH NOTE (patient consent mechanism)

### Data Architecture
- `01-schemas.sql`: institutional schema added (ADR-019, FR-003)
- `03-enums-and-tables.sql`: domain_knowledge + platform_intelligence tables (institutional schema)

---

## [0.9.0] — 2026-07-08

### Constitutional (new claims + GENESIS Part 05)
- C-040: Domain specialization as constitutional obligation (LAW)
- C-041: Every MCP tool call governed by Decision Space (LAW)
- GENESIS Part 05: Agent Definition Protocol — mandatory specification before any new agent implementation
  - RAG Specification Standard (three-tier: Domain / Customer / Platform Intelligence)
  - MCP Tool Specification Standard (default deny, C-041 enforcement)
  - Learning Loop Standard (FR-003 boundary at inference signal boundary)

### Architecture (new ADRs + agent infrastructure)
- ADR-019: RAG Architecture — three-tier, pgvector in `institutional` schema at MVI
- ADR-020: MCP Integration Pattern — AI Runtime as MCP client, CE.ValidateAction before every tool call
- ADR-INDEX.md: updated to 20 ADRs
- AI Runtime component spec: RAG pipeline + MCP client sections added

### Agent Specifications (new directory)
- `architecture/reference/agents/AGENT-AUTHORING-GUIDE.md` — reusable template for new agent types
- `architecture/reference/agents/digital-marketing-agent.md` — first complete agent specification
  - 7 Skills: Content Strategy, Instagram, Facebook, Google Business, WhatsApp, Video, Analytics
  - RAG sources per skill (Tier 1/2/3)
  - MCP tools per skill with authorization + failure mode
  - 15-minute onboarding conversation flow
  - ProfessionalTemplate definition (dental + beauty variants)
  - Full constitutional checklist

---

## [0.8.0] — 2026-07-08

### Constitutional (new claims)
- C-036: Skills as first-class constitutional units (C-036 LAW)
- C-037: Business outcome KPIs as primary performance measure (C-037 LAW)
- C-038: Pro-rata billing as constitutional right (C-038 LAW)
- C-039: Conversational configuration as constitutional obligation (C-039 CONFIRMED)

### Knowledge (Business Architect)
- `knowledge/business-capabilities.md`: 16 new capabilities across D1/D2/D3/D4/D5/D6 + new D9 Commercial
- `knowledge/architectural-drivers.md`: AD-012 (Business KPI Primacy), AD-013 (Conversational Config), AD-014 (Pro-Rata Billing)
- `knowledge/design-principles.md`: DP-011 (Business Outcome First), DP-012 (Skill Granularity in Governance)

### Architecture (EA/SA/DA percolation)
- `architecture/reference/domain-model.md`: Skill entity, SubscriptionBillingEvent entity
- `architecture/reference/components/business-platform.md`: Skill Manager, Performance Monitor, Subscription Manager components
- `architecture/reference/components/ai-runtime.md`: Conversational Configuration Engine component
- `architecture/reference/api-specs/business-platform.openapi.yaml`: Skills, Performance, Billing, Conversational Config endpoints + schemas

### Data Architecture
- `03-enums-and-tables.sql`: skill_state enum, billing_event_type enum, professional_skills table, skill_performance_records table, subscription_billing_events table (append-only)

---

## [0.7.0] — 2026-07-08

### Constitutional (Founder Resolutions)
- FR-002: Trial = full constitutional employment from day one; trial outputs owned by customer
- FR-003: Agent learning is WAOOAW institutional IP; customer data is private and never shared
- FR-004: Agent Teams — enterprise tier, WAOOAW-provided Team Coordinator, deferred from MVI

### Architecture (gaps bridged by simulation)
- `architecture/reference/domain-model.md`: EmploymentContract `isTrial`, `trialEndsAt`, `trialConvertedAt`
- `infrastructure/postgres/init/03-enums-and-tables.sql`: trial columns on `business.employment_contracts`
- `architecture/reference/api-specs/business-platform.openapi.yaml`: trial fields + `POST /convert-trial` endpoint
- `architecture/reference/data/ledger-design.md`: Institutional Learning Zone (FR-003 fourth data zone)
- `architecture/reference/security/security-architecture.md`: Data Classification table §0 (FR-003)

### Backlog
- IB-018: Agent Teams — Constitutional Team Architecture (enterprise, post-MVI, DEFERRED)

---

## [0.6.0] — 2026-07-07

### Added
- Agent efficiency index layer: `constitution/AGENT-ENTRY.md`, `adr/ADR-INDEX.md`, `architecture/reference/COMPONENT-QUICK-REF.md`
- Office Quick-Start cards (50 lines vs 880): `.github/agent-context/office-*.md`
- GitHub labels: 67 labels created on repository (type/office/component/domain/gate/sprint/status)
- `scripts/setup-github-labels.sh` — reproducible label creation
- `architecture/reference/api-specs/emergency-stop-ws.md` — WebSocket frame spec, reconnection, heartbeat
- `ARCHITECTURE.md` and `CHANGELOG.md` at repository root (GENESIS mandate)
- `commitlint.config.js` — enforces conventional commits including `constitutional` type
- BOOTSTRAP Step 3 + 5 updated to route through indices (60-70% token reduction per session)

### Fixed
- CB-001 (simulation): `ABANDONED` enum was already in business-platform.openapi.yaml ✓
- CB-002 (simulation): CE gRPC Health service already specified in component spec ✓

---

## [0.5.0] — 2026-07-07

### Added
- GitHub-grounded operating model: 4 issue templates, CODEOWNERS, PR template
- `.github/workflows/pm-report.yaml` — Platform Delivery Tracker (Office 12) automated reporting
- `.github/workflows/project-automation.yaml` — issue lifecycle automation
- `.github/copilot-instructions.md` updated with GitHub sprint mode, PM role, branch/commit conventions
- `constitution/ORGANIZATION.md`: Office 12 — Platform Delivery Tracker
- `README.md`: Operating Commands section (5 bare-minimum invocations)
- Sprint 1 simulation: 5 components, 2 CCTs proven, 2 Constitutional Blockers surfaced correctly

---

## [0.4.0] — 2026-07-07

### Added (coding agent readiness — 7 fixes)
- `infrastructure/postgres/init/02-users-and-permissions.sh` (bash, proper env var interpolation)
- `architecture/reference/proto/buf.yaml` + `buf.gen.yaml` (proto toolchain)
- Dockerfile templates: `.NET 9`, `Python 3.12`, `Next.js 14`
- `docker-compose.yml` CE healthcheck: TCP check for dev; web service healthcheck
- Engineering-standards §9: EF Core empty initial migration technique
- Engineering-standards §10: `TenantDbCommandInterceptor` pseudocode
- Engineering-standards §11: Dev JWT via `waooaw-dev-client`
- `infrastructure/keycloak/waooaw-realm.json`: dev user + `waooaw-dev-client`
- `scripts/get-dev-token.sh`

---

## [0.3.0] — 2026-07-07

### Added (R-007 P0 gap closure)
- ADR-016: .NET 9 / Python 3.12 language selection
- ADR-017: Next.js 14 TypeScript web framework
- ADR-018: Emergency Stop Temporal signal routing (GAP-003 resolution)
- `architecture/reference/security/`: threat model (STRIDE) + security architecture
- `architecture/reference/api-specs/`: business-platform.openapi.yaml + professional-runtime.openapi.yaml
- IB-017 Phase 2 Readiness: CI/CD pipelines, CCT framework, postgres init SQL, Keycloak realm

---

## [0.2.0] — 2026-07-07

### Added (Architecture phase)
- 35 ratified constitutional claims (C-001 to C-035) — Gate G2 PASSED
- Business Capability Map (26 capabilities), Architectural Drivers (11), Design Principles (10) — Gate G3 PASSED
- Complete Reference Architecture: context, containers, domain model, 4 component specs — Gate G4 PASSED
- Data architecture: three-ledger design, evidence state machine with ABANDONED state
- 15 ADRs (ADR-001 through ADR-015)
- Security architecture, OpenAPI specs, proto contract — Gate G5 CLEAR

---

## [0.1.0] — 2026-07-06

### Added (Institution foundation)
- `constitution/CONSTITUTION.md` v1.2 (17 Articles, 4 Amendments)
- `constitution/GENESIS.md` Parts 01–04 + Engineering Quality Mandate
- `constitution/ORGANIZATION.md` (11 offices, 7 attributes, Operating Protocol)
- `constitution/BOOTSTRAP.md` + `.github/copilot-instructions.md`
- `standards/` (5 professional standards)
- `simulation/` (3 cases, PRECEDENTS.md, ECI-001, ECI-002)
- `constitution/RED_TEAM.md` (11 attacks, 0 constitutional failures)
