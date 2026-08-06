# Changelog

All notable changes to the WAOOAW Platform are documented here.
This file is auto-generated from conventional commits. Do not edit manually.

Format: [Conventional Commits](https://www.conventionalcommits.org/) —
types: `feat` | `fix` | `constitutional` | `cct` | `chore` | `refactor` | `security` | `docs`

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
