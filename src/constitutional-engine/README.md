# Service README — Constitutional Engine

## Purpose
Internal-only gRPC service. Constitutional Audit Ledger writes. Evidence First enforcer.
Never exposed to the internet. Called by Business Platform and Professional Runtime.

## Run locally
```bash
cd src/constitutional-engine
dotnet run
# Or via docker compose (recommended — needs postgres)
docker compose up constitutional-engine
```

## Run tests
```bash
dotnet test src/constitutional-engine
```

## Key env vars
- `ConnectionStrings__DefaultConnection` — PostgreSQL (constitutional_app user — INSERT+SELECT only)
- `GRPC_PORT` — gRPC port (default 5002)
- `OTLP_ENDPOINT` — OTel collector

## gRPC health check (dev)
```bash
grpc_health_probe -addr=:5002  # installed in Dockerfile
# or in docker compose:
nc -z localhost 5002
```

## Constitutional obligations
- Every RecordEvidence call writes to DB atomically before returning OK (C-023)
- If write fails → return gRPC INTERNAL — caller must not return success (C-023)
- No UPDATE or DELETE ever issued on constitutional schema (C-027, enforced by DB RULE + permissions)
- tenant_id from gRPC metadata x-tenant-id only — never from request body (ADR-003)
