# WAOOAW Platform — Architecture Overview

**Version:** 0.6.0 | **Gate:** G5 CLEAR | **Status:** Implementation AUTHORIZED

This file is the entry point for understanding the platform architecture.
For detailed views, use the altitude map below.

---

## The Institution in One Sentence

WAOOAW is an institution that enables organizations to employ autonomous digital professionals under constitutional governance.

---

## Architectural Altitude Map

| Altitude | View | File |
|---|---|---|
| **100K** | System context — actors, external systems | [architecture/100k/README.md](architecture/100k/README.md) |
| **50K** | C4 Context diagram | [architecture/reference/context.md](architecture/reference/context.md) |
| **32K** | Service communication patterns | [architecture/32k/README.md](architecture/32k/README.md) |
| **20K** | C4 Container diagram — 4 services + infra | [architecture/reference/containers.md](architecture/reference/containers.md) |
| **10K** | C4 Component specs — all 4 services | [architecture/reference/components/](architecture/reference/components/) |
| **5K** | Domain model — Decision Space, Employment Contract, Evidence state machine | [architecture/reference/domain-model.md](architecture/reference/domain-model.md) |
| **1K** | API contracts — REST (OpenAPI) + gRPC (proto) | [architecture/reference/api-specs/](architecture/reference/api-specs/) · [architecture/reference/proto/](architecture/reference/proto/) |
| **500** | Data architecture — three-ledger model, state machine | [architecture/reference/data/](architecture/reference/data/) |
| **200** | Security — threat model, network topology, JWT spec | [architecture/reference/security/](architecture/reference/security/) |
| **100** | Infrastructure — local stack, Dockerfiles, Temporal config | [docker-compose.yml](docker-compose.yml) · [infrastructure/](infrastructure/) · [architecture/reference/dockerfiles/](architecture/reference/dockerfiles/) |
| **50** | Engineering standards — coding, testing, CCTs, OTel | [architecture/reference/engineering-standards.md](architecture/reference/engineering-standards.md) |

---

## Service Mesh (Current — 4+1)

| Service | Language | Port | Responsibility |
|---|---|---|---|
| Constitutional Engine | .NET 9 gRPC | 5002 (internal) | Evidence First enforcer, `audit_sink` schema (WORM evidence records), authority licensing |
| Business Platform | .NET 9 REST | 5001 (public) | Employment management, approvals, Skill Catalog, Provider Registry, `payload_store` schema |
| Professional Runtime | Python 3.12 FastAPI | 5003 (public WSS) | PAAS + Skill Runtime (in-process) + approval-gate execution, Emergency Stop WebSocket |
| AI Runtime | Python 3.12 FastAPI | 5004 (internal) | PSE tier routing + CTG library (LLM + OAuth tool calls) — no governance authority of its own |
| **oauth-vault** | Python FastAPI | **8130 (internal only)** | **Token storage (Azure KV), JIT retrieval, background refresh — called by CTG only** |

**Constitutional Tool Gateway (CTG):** Python shared library (`src/trust-layer/ctg/`) — NOT a service. Imported by PR and AIR. Every external call (LLM + OAuth-protected APIs) routes through CTG → CE.ValidateAction → oauth-vault → execution → Audit Sink. ADR-042.

**Skill Architecture:** Skill Catalog in BP (Postgres `skills` table). Skill Runtime in PR (in-process, session-open-time resolution). No 6th service. ADR-043.

Quick reference for all services: [architecture/reference/COMPONENT-QUICK-REF.md](architecture/reference/COMPONENT-QUICK-REF.md)

---

## Container Communication Map (EA Decision 2026-08-06)

```
Customer / Steward
      │ HTTPS
      ▼
Business Platform (5001)
  ├── gRPC → Constitutional Engine (5002)        [ValidateAction, RecordErasure]
  ├── HTTP  → Professional Runtime (5003)        [session management, approvals]
  └── HTTP  → oauth-vault (8130)                 [connect platform, revoke token]

Professional Runtime (5003)
  ├── gRPC → Constitutional Engine (5002)        [ValidateAction, EmergencyStop]
  ├── HTTP  → Business Platform (5001)           [fetch Employment Contract, Skill manifests]
  ├── HTTP  → AI Runtime (5004)                  [task delegation]
  └── CTG library → CE (gRPC) + oauth-vault (HTTP)  [all external tool calls]

AI Runtime (5004) — all external calls via CTG library
  ├── CTG → CE (5002) → oauth-vault (8130) → [LLM API]       [llm.complete]
  └── CTG → CE (5002) → oauth-vault (8130) → [Platform API]  [meta.*, google.*, etc.]

Constitutional Engine (5002)
  └── Postgres audit_sink schema (WORM — INSERT only)

Business Platform (5001)
  └── Postgres payload_store schema (erasable on DPDPA request)

oauth-vault (8130)
  └── Azure Key Vault (waooaw-dev-kv)            [token storage, master key]
```

---

## Planned Components (not yet sprinted)

| Component | ADR | Stack | Prerequisites |
|---|---|---|---|
| CTG library | ADR-042 | Python | ADR-042 + ADR-044 merged; AIR refactored off direct LLM SDK |
| Provider Registry table | ADR-042 | BP Postgres migration | ADR-042 merged |
| oauth-vault service | ADR-021, ADR-042 | Python FastAPI | ADR-042 + ADR-044 merged |
| Skill Catalog (BP) | ADR-043 | BP Postgres migration | ADR-043 merged |
| Skill Runtime (PR) | ADR-043 | PR Python in-process | ADR-043 + Skill Catalog |
| Audit Sink schema (CE) | ADR-044 | CE Postgres migration | ADR-044 merged |
| Payload Store schema (BP) | ADR-044 | BP Postgres migration | ADR-044 merged |
| Web Application | WC-016 | Next.js 14 / TypeScript | C-082 |
| Mobile Application | Post WC-018 | Flutter 3 / Dart | C-001, C-078, C-079, C-081, C-082, ADR-032 |

**Mobile authorization gate:** Before any mobile Work Contract is opened, the following must be in place:
1. `architecture/reference/dotfiles/pubspec.yaml` created and EA-approved (C-081)
2. `flutter analyze` added to `validate_written_files()` (C-082)
3. Push notification stop-signal path specified in CE (C-001 mobile extension)
4. Mobile offline behavior spec written and ratified (C-079 mobile extension)

---

## Reference Dependency Files (C-081)

EA-approved dependency version files that autonomous agents MUST copy verbatim:

| File | Stack | Sprint |
|---|---|---|
| [constitutional-engine.csproj](architecture/reference/dotfiles/constitutional-engine.csproj) | .NET 9 (CE) | WC-012 |
| `business-platform.csproj` | .NET 9 (BP) | Before WC-014 |
| `requirements-ai-runtime.txt` | Python 3.12 (AI Runtime) | Before WC-015 |
| `package.json` | Next.js / TypeScript | Before WC-016 |
| `pubspec.yaml` | Flutter / Dart (Mobile) | Before mobile sprint |

---

## `scripts/runner/` Package

Modular package extracted from `autonomous_sprint_runner.py` (4,034 → 1,572 lines) in sprint IB-009:

| Module | Responsibility |
|---|---|
| `constants.py` | `REPO_ROOT`, `STATE_FILE`, `EVIDENCE_LOG`, `ALLOWED_WRITE_ROOTS` — single path source of truth |
| `state.py` | Shared mutable runtime state (`_MONITOR_SIGNAL`, `_INFRA_ERROR_TASKS`) — module-level singletons |
| `git_ops.py` | Shell/git/gh helpers: `run`, `git`, `gh`, `set_output`, `record_evidence` |
| `system_prompts.py` | Constitutional LLM system prompt architecture: `_build_system_prompt`, `get_branch_context` |
| `sprint_ops.py` | Sprint state lifecycle: `parse_sprint_state`, `check_platform_phase_gate`, `run_runner_integrity_checks` |
| `llm_codegen.py` | LLM code generation with Anthropic prompt caching (ADR-030, C-077): `call_llm`, `call_llm_via_magiclm`, `parse_llm_files`, `write_llm_files`, `validate_written_files` |
| `task_executor.py` | Retry loop with Retry Advisor: `execute_with_llm`, `flag_spec_gap` |
| `legacy_handlers.py` | Deterministic per-WC task handlers: `execute_wc011_01` through `execute_wc015_01` |

`autonomous_sprint_runner.py` remains the CLI entry-point and TASK_HANDLERS registry. `groom_sprint.py` injects new handlers at the `RUNNER_ANCHOR` comment preserved inside that file.

**Prompt Caching**: All LLM call sites use `anthropic-beta: prompt-caching-2024-07-31` with system prompt wrapped in `cache_control: {type: ephemeral}` — tokens procured once and reused across retries (C-077 cost reduction).

---

## Architecture Decision Records

18 ADRs govern all technology selections. Quick reference: [adr/ADR-INDEX.md](adr/ADR-INDEX.md)

---

## Constitutional Traceability

Every architecture decision traces to a ratified constitutional claim (82 claims, `knowledge/claims/`).
Every component traces to a business capability (26 capabilities, `knowledge/business-capabilities.md`).
Constitutional compliance is verified by automated tests (`tests/constitutional/`).
