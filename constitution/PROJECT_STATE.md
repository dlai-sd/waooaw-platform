# PROJECT_STATE.md

**Last Updated:** 2026-07-24 (full day session — evening close)
**Version:** 1.5.0 — WC-012 READY, pipeline hardened, 3 new constitutional claims ratified
**Declared by:** Yogesh Khandge (Founder), 2026-07-23 (implementation authorization unchanged)
**Session:** 2026-07-24 — RCA complete, C-083/C-084/C-085 ratified, Sprint Monitor built, all pipeline gates pass

---

## SESSION CLOSE RECORD — 2026-07-24 (full day — evening close)

### Audit → RCA → Pipeline Hardening → Constitutional Ratification

**What happened overnight (runs #30046231957 → #30065913447):**
- Pipeline produced PR #28 with build errors: WC012-02/04 committed before WC012-01 scaffold was clean
- 9 false spec-gap issues created — all closed with RCA documentation in #36

**Root causes fixed + pipeline hardened:**

| RC | Fix | Constitutional Claim |
|---|---|---|
| RC#1: scaffold failure didn't halt sprint | SCAFFOLD_TASKS frozenset + break in execution loop | C-084 |
| RC#2: tasks_done never written | Per-task set-list after each success | C-085 |
| RC#3: Moq non-virtual ServerCallContext | FakeServerCallContext concrete stub | C-076 |

**Sprint Monitor built (C-069 self-improvement loop):**
- `scripts/sprint_monitor.py` — runs after every sprint execution
- Classifies: INFRA_ERROR / CASCADE_PIPELINE_BUG / IDEMPOTENCY_BUG / SPEC_GAP_GENUINE
- Emits signals: runner writes `monitor-signal.json` artifact; monitor downloads and reads it
- Auto-closes false spec-gap issues; drafts constitutional proposals
- Fixed 5 design defects in monitor: signal in wrong job, scaffold from wrong source, dashboard noise, duplicate proposals, misleading success messages

**Constitutional claims ratified (3 new — total now 85):**

| Claim | Title | Source |
|---|---|---|
| C-083 | Emit-Transport-Listen — streaming signals at every action boundary | Pipeline failure: monitor couldn't see runner's work |
| C-084 | Step Dependency Ordering — upstream fail MUST halt downstream steps | Pipeline failure: WC012-02/04 committed on broken WC012-01 |
| C-085 | Idempotency Obligation — completed steps not re-executed on retry | Pipeline failure: tasks_done not tracked, tasks re-ran |

**Additional fixes:**
- CCT-EF-01, CCT-HO-01, evaluator test suite (42/42 passing) added to test project
- Workflow YAML: `monitor needs report` (broken dep caused push-validation failure runs #40–#43)
- `sprint_state.py`: set-list command restored after automated edit removed it
- `knowledge/index.md`: C-077–C-085 all indexed
- `sprint-context/*.json` added to .gitignore (regenerated artifacts)

### State at Session Close

- sprint_status: READY | tasks_done: [] | tasks_remaining: [WC012-01, WC012-02, WC012-03, WC012-04]
- consecutive_failures: 0 | autonomous_halt: false | platform_phase: IMPLEMENTATION
- No open PRs. No open spec-gap issues. No stale branches.
- Pipeline: all 6 scripts syntax-clean. Workflow YAML: all job deps valid.
- Ready to trigger WC-012.

### Tomorrow First Actions

1. Complete BOOTSTRAP sequence
2. Check Issue #7 — did WC-012 run? What did the Constitutional Monitor report?
3. If PR opened → code review (build ✅ + 42/42 tests ✅ standard), approve/merge
4. If run failed with spec-gap → check monitor classification (genuine gap or pipeline bug?)

---

## SESSION CLOSE RECORD — 2026-07-24 (EA+IT Expert RCA session — morning)

**Root causes fixed (all 3 on main now):**
| RC | Fix | Location |
|---|---|---|
| RC#1: scaffold failure didn't halt sprint | Break on scaffold fail; dependent tasks stop | `autonomous_sprint_runner.py` |
| RC#2: tasks_done never advanced | Per-task `tasks_done`/`tasks_remaining` write via `set-list` | `autonomous_sprint_runner.py` + `sprint_state.py` |
| RC#3: Moq can't mock non-virtual ServerCallContext | `FakeServerCallContext` concrete stub | test project |

**CCTs added to test project (now 42/42 pass):**
- CCT-EF-01: Evidence First ordering (PersistEvidence before TriggerTemporalSignal)
- CCT-HO-01: EmergencyStop handler ≤100ms budget
- Evaluator suite: C-041/C-043/C-048/C-049/C-051/C-062 + registry ordering

**Clean state declared:**
- PR #28 closed (not merged), branch `ib/009/sprint-012` deleted
- All 9 spec-gap issues closed, RCA issue #36 closed
- sprint_status=READY, tasks_done=[], all 4 WC-012 tasks in tasks_remaining
- Pipeline fixes on `main` — next run will execute WC-012 cleanly end-to-end

### Next Session
1. Trigger WC-012 run (manual or next cron at `0 */3 * * *`)
2. Monitor Issue #7 — expect 4/4 tasks pass with fixed pipeline
3. Review PR when opened — code builds + 42/42 tests pass is the exit gate

---

## SESSION CLOSE RECORD — 2026-07-23 (FULL DAY — evening close)

### WC-012 Execution Status
- **2/4 tasks PROVEN working** — WC012-01 (scaffold ✅) + WC012-02 (evaluators ✅) passed on first attempt in run #35
- **WC012-03/04** — failed due to MSB1050 (multiple .csproj) + test path convention — BOTH FIXED
- **Cron running overnight** — expected full 4/4 pass in next run
- **PR auto-merge FIXED** — CODEOWNERS no longer requires @dlai-sd for src/tests/scripts

### Critical Fixes Applied (35 runs of learning)

| Fix | Root cause it solves |
|---|---|
| API timeout 120s→600-960s | All API calls silently timed out (run #33 — 12/12 failures) |
| CODEOWNERS @dlai-sd removed from src/ | Auto-merge blocked: "mergePullRequest not accessible" |
| max_tokens 8000→16000/10000 per task | Output truncation — ConstitutionalEngineService.cs never generated |
| validate_written_files: specific .csproj | MSB1050 — multiple .csproj in same dir |
| Reference .csproj + requirements files | NuGet/pip package hallucination (OpenTelemetry.Exporter.Otlp etc.) |
| CONSTITUTIONAL_SYSTEM_PROMPT: project structure | Test .csproj in wrong subdirectory |
| CODING-STANDARDS.md §2.0 | No documented .NET test project convention |
| Error categorization INFRA_ERROR | False spec gap issues created for API timeouts |
| INFRA_ERROR visible on Issue #7 | Silent failures — founder assumed progress |
| WC013/014/015 reference files | Proactive: prevents same failures in future sprints |
| Python package rules in system prompt | Sarvam no-SDK, Vertex AI correct import, AI4Bharat transformers only |

### State at Session Close
- Sprint: WC-012 READY, consecutive_failures=0, all 4 tasks queued
- No open PRs, no stale branches, no open spec gap issues
- VERSION file: 1.11.0 (bumps to 1.12.0 when WC-012 PR merges)
- Reference dotfiles: CE .csproj ✅, BP .csproj ✅, PR requirements ✅, AIR requirements ✅

### Tomorrow — First Actions for New Session
1. Complete BOOTSTRAP sequence
2. Check Issue #7 for overnight cron results
3. If PR opened + merged → code review src/constitutional-engine/ (C-059 headers, CCT-EF-01, append-only evidence)
4. If PR not merged → analyse WHY, fix, close stale issues, clean branch
5. If INFRA_ERROR on Issue #7 → no action needed, auto-retries

---

## SESSION CLOSE RECORD — 2026-07-23 (evening update)

### IB-020: LLM Code Generation (ADR-030) — ✅ COMPLETE
- ADR-030 ratified: Autonomous Sprint Code Generation spec
- `call_llm()`, `parse_llm_files()`, `validate_written_files()`, `execute_with_llm()` implemented
- WC012-01 to WC012-04 registered in TASK_HANDLERS
- Model: `claude-sonnet-4-6` (authorized by Yogesh 2026-07-23 for all planned sprints WC-011→WC-018)
- `SPRINT_LLM_MODEL` GitHub Variable set to `claude-sonnet-4-6` — confirmed valid via live Anthropic API call
- 3-attempt retry loop, XML `<file path="...">` response format, write boundary enforcement

### Automated Version Bump — ✅ LIVE
- Scheme: `MAJOR.WC_SPRINT_NUMBER.0` (e.g. WC-012 merge → `1.12.0`)
- `VERSION` file created at repo root (baseline: `1.11.0` = WC-011 done)
- `bump_version()` + `update_changelog()` added to `autonomous_sprint_reviewer.py`
- Reviewer post-merge flow: rebase → bump VERSION → prepend CHANGELOG entry → advance sprint state → single commit → push
- CHANGELOG.md auto-updated on every sprint merge

### Critical Bug Fixed — Reviewer kwargs TypeError
- 8 calls to `run(cmd, check=False, capture=True)` in reviewer would have raised `TypeError` at WC-012 merge
- `run()` only accepts `cmd` and `env` — invalid kwargs silently crash post-merge steps
- All 8 removed; confirmed clean via AST scan + syntax check

### Pre-flight Simulation — ✅ ALL GREEN (Docker)
- CCT-PIPE-01: 15/15 PASS in Docker test-runner
- CCT-PIPE-02: 4/4 PASS in Docker test-runner
- Sprint index dry-run WC012-01→04: 10,449/100,000 tokens — OK
- Syntax: all 4 pipeline scripts compile clean
- Anthropic model alias `claude-sonnet-4-6` confirmed valid via `/v1/models` API

### Infrastructure FA Actions — ✅ ALL DONE
- **FA-005 Trading ack**: Yogesh acknowledged TRADING/EXECUTION/ESCALATION_DECISION boundary
- **FA-021 GCP Vertex AI**: SA key → `waooaw-dev-kv` → `GOOGLE-VERTEX-SA-KEY`
  SA: `waooaw-vertex-sa@heroic-arbor-483004-d4.iam.gserviceaccount.com`, Role: `roles/aiplatform.user`
- **FA-022 Sarvam AI**: API key → `waooaw-dev-kv` → `SARVAM-API-KEY`
- **FA-003 Azure OpenAI**: Resource `waooaw-openai-uae` (UAE North) created, endpoint + key stored in KV
  Model deployment deferred — Azure OpenAI is fallback only (Gemini is primary)
- Key Vault `waooaw-dev-kv` now has **9 secrets**: ANTHROPIC-API-KEY, AZURE-OPENAI-ENDPOINT, AZURE-OPENAI-KEY, CODECOV-TOKEN, GH-APP-ID, GH-APP-INSTALLATION-ID, GH-APP-PRIVATE-KEY, GOOGLE-VERTEX-SA-KEY, SARVAM-API-KEY

### Bugs Fixed This Session
- `docker-compose.yml`: removed hard `depends_on: postgres` from test-runner (blocked all Docker CCT runs)
- `build_sprint_index.py`: token budget display now shows effective limit (100k) not free limit (8k)

### Constitutional Status
- **Claims ratified**: 80 (C-001 → C-080)
- **ADRs**: 31 (ADR-001 → ADR-031)
- **C-080**: Docker Test Isolation enforced — no virtual environments permitted

---

## SESSION CLOSE RECORD — 2026-07-23 (morning baseline)

### Part 1: 12-Chapter Agent AI Audit (all gaps fixed)
All 12 chapters passed. 4 new constitutional claims ratified. 8 new/updated spec files.

### Part 2: Azure Infrastructure (fully live)
- Azure account: yogesh.khandge@dlaisd.com (Pay-as-you-go, Central India)
- Tenant: `0471534c-1bbe-40ab-ae65-3f721b62582c`
- Subscription: `2ed11839-6a0f-4eaa-bd94-44ca96ff5d84`
- Resource Group: `waooaw-dev-rg`
- Key Vault: `waooaw-dev-kv`
- App Registration: `waooaw-platform-sp` (Client ID: `ccd13909-d004-4340-aa26-990a00bed9c0`)
- OIDC: federated credentials for main branch + PRs — **no stored client secrets**
- GitHub Variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_KEYVAULT_NAME`, `SPRINT_LLM_MODEL`

### Part 3: WC-011 Proven End-to-End (Run #29)
- execute → PR opened → auto-merge by waooaw-reviewer → sprint advance to WC-012
- All 7 WC-011 tasks DONE: docker validation, DB migrations, Keycloak, GitHub Secrets doc, CCTs

### Part 4: EA Post-Mortem + Constitutional Hardening
- CCT-PIPE-01/02: 19 tests added and passing
- C-080 Docker Test Isolation: Dockerfile.test-runner, requirements-test.txt, docker-compose service
- SIM-PL-001: Pipeline health simulation protocol
- ADR-031: CE Fail-Safe Halt on Unavailability (C-079)

### Part 5: FOUNDER-ACTION.md Items
| Item | Status |
|---|---|
| T0-1 Anthropic API key | ✅ DONE |
| T0-2 Azure OIDC + Key Vault | ✅ DONE |
| T0-3 platform_phase=IMPLEMENTATION | ✅ DONE 2026-07-23 18:00 IST |
| T0-4 GitHub App waooaw-reviewer | ✅ DONE |
| T0-5 Codecov token | ✅ DONE |
| T1-1 FA-002 Meta BM | ⏳ IN PROGRESS (2-4 weeks external) |
| T1-2 FA-021 GCP Vertex AI key | ✅ DONE |
| T1-3 FA-022 Sarvam AI key | ✅ DONE |
| T1-4 FA-003 Azure OpenAI | ✅ DONE (model deployment deferred — fallback only) |

---

## NEXT SESSION OPTIONS

```
CURRENT STATE: platform_phase=SPEC · AUTONOMOUS_HALT=true · Version=v1.0.0
CLAIMS: 78 RATIFIED (C-001→C-076 + C-078 + C-079) · C-077 RATIFIED ₹5,000/month
ADRs: 30 (ADR-001→ADR-029 + ADR-031 · ADR-030 reserved IB-020)

OPTION A — Authorize implementation (T0-3)
  → Say: "Yogesh authorizes IB-009 Sprint 011 implementation"
  → Monitor: github.com/dlai-sd/waooaw-platform/issues/7

OPTION B — Complete T1 actions while waiting for sprint
  → T1-1: Submit Meta BM verification (START TODAY — 2-4 week clock)
  → T1-2: GCP Vertex AI SA key (2h)
  → T1-3: Sarvam AI key (1h)
  → T1-4: Azure OpenAI UAE North (1h)
  → T1-5: Trading ESCALATION_DECISION ack (5 min)

OPTION C — Nothing needed from you until sprint opens first PR
  → Sprint runs autonomously, posts to Issue #7
  → You review PR when notified (mobile push)
```

---

## SPRINT_STATE_MACHINE
<!-- Machine-readable by autonomous-sprint.yaml. YAML-parseable block. -->
<!-- Edit ONLY the fields below. Do not alter the block structure. -->

```yaml
autonomous_halt: false        # ← IMPLEMENTATION AUTHORIZED by Yogesh Khandge 2026-07-23 18:00 IST
                              #   Authorization: "Yogesh authorizes IB-009 Sprint 011 implementation"
                              #   Recorded: constitution/PROJECT_STATE.md + FOUNDER-ACTION.md

platform_phase: IMPLEMENTATION  # SPEC | IMPLEMENTATION | LIVE
                              # SPEC = design, specs, planning only. No src/ code allowed.
                              # Agents MUST check this field before any implementation action.

current_sprint: WC-012
sprint_ib_item: IB-009
sprint_status: IN_PROGRESS
branch: ib/009/sprint-012
last_attempt_utc: 2026-07-24T13:39:08.339665+00:00
last_attempt_result: SUCCESS
consecutive_failures: 0
tasks_done:
  - WC012-01
tasks_remaining:
  - WC012-02
  - WC012-03
  - WC012-04

current_task:
blocker: ""
blocker_raised_utc: ""
```

---

## NEXT SESSION OPTIONS

```
CURRENT STATE: platform_phase=IMPLEMENTATION · AUTONOMOUS_HALT=false
               current_sprint=WC-012 · sprint_status=READY
               CLAIMS: 80 RATIFIED (C-001→C-080) · ADRs: 31

SPRINT SCOPE — WC-012 (Constitutional Engine v1 — 4 tasks):
  WC012-01: .NET 9 gRPC project scaffold    → src/constitutional-engine/ created
  WC012-02: ValidateAction RPC + tests ≥90% → core business logic
  WC012-03: Evidence First + CCT-EF-01      → C-059 constitutional enforcement
  WC012-04: Emergency Stop + CCT-HO-01      → C-073 emergency stop
  Full CE v1 delivered by end of sprint — not just skeleton.

OPTION A — Trigger WC-012 now (recommended)
  → github.com/dlai-sd/waooaw-platform/actions/workflows/autonomous-sprint.yaml → Run workflow
  → Claude Sonnet 4.6 will generate 4 tasks of .NET 9 CE code
  → Monitor: github.com/dlai-sd/waooaw-platform/issues/7

OPTION B — Wait for next 3-hour cron (no action needed)
  → Cron: 0 */3 * * * — auto-fires within 3 hours

OPTION C — Pending founder action (non-blocking)
  → FA-002 Meta BM verification: IN PROGRESS externally (2-4 weeks)
  → FA-003 Azure OpenAI model deployment: deferred (fallback only, non-critical)
```


---

*Session history archived to `constitution/PROJECT_STATE_ARCHIVE.md`*
*Agents do not need to read the archive — it is human reference only.*