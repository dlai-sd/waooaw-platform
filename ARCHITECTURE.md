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

## Four Services (Current)

| Service | Language | Port | Responsibility |
|---|---|---|---|
| Constitutional Engine | .NET 9 gRPC | 5002 (internal) | Evidence First enforcer, audit ledger, authority licensing |
| Business Platform | .NET 9 REST | 5001 (public) | Employment management, approvals, evidence reading |
| Professional Runtime | Python 3.12 FastAPI | 5003 (public WSS) | PAAS + approval-gate execution, Emergency Stop WebSocket |
| AI Runtime | Python 3.12 FastAPI | 5004 (internal) | LLM gateway, tool execution — no governance authority |

Quick reference for all services: [architecture/reference/COMPONENT-QUICK-REF.md](architecture/reference/COMPONENT-QUICK-REF.md)

---

## Planned Components

| Component | Sprint | Stack | Constitutional Pre-requisites |
|---|---|---|---|
| Web Application | WC-016 | Next.js 14 / TypeScript | C-082 (TypeScript validation path required) |
| Mobile Application | Post WC-018 | Flutter 3 / Dart | C-001 (push stop signal), C-078 (device PII), C-079 (offline halt), C-081 (pubspec.yaml reference), C-082 (flutter analyze validation), ADR-032 (reserved) |

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

## Architecture Decision Records

18 ADRs govern all technology selections. Quick reference: [adr/ADR-INDEX.md](adr/ADR-INDEX.md)

---

## Constitutional Traceability

Every architecture decision traces to a ratified constitutional claim (82 claims, `knowledge/claims/`).
Every component traces to a business capability (26 capabilities, `knowledge/business-capabilities.md`).
Constitutional compliance is verified by automated tests (`tests/constitutional/`).
