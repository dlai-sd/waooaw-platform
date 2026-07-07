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

## Four Services

| Service | Language | Port | Responsibility |
|---|---|---|---|
| Constitutional Engine | .NET 9 gRPC | 5002 (internal) | Evidence First enforcer, audit ledger, authority licensing |
| Business Platform | .NET 9 REST | 5001 (public) | Employment management, approvals, evidence reading |
| Professional Runtime | Python 3.12 FastAPI | 5003 (public WSS) | PAAS + approval-gate execution, Emergency Stop WebSocket |
| AI Runtime | Python 3.12 FastAPI | 5004 (internal) | LLM gateway, tool execution — no governance authority |

Quick reference for all services: [architecture/reference/COMPONENT-QUICK-REF.md](architecture/reference/COMPONENT-QUICK-REF.md)

---

## Architecture Decision Records

18 ADRs govern all technology selections. Quick reference: [adr/ADR-INDEX.md](adr/ADR-INDEX.md)

---

## Constitutional Traceability

Every architecture decision traces to a ratified constitutional claim (35 claims, `knowledge/claims/`).
Every component traces to a business capability (26 capabilities, `knowledge/business-capabilities.md`).
Constitutional compliance is verified by automated tests (`tests/constitutional/`).
