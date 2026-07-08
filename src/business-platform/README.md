# Service README — Business Platform
# engineering-standards.md mandates a README per service

## Purpose
External-facing REST API. Employment lifecycle, approval workflows, evidence reading, authority management.
Every governance event calls Constitutional Engine before returning success (Evidence First, C-023).

## Run locally
```bash
cd /workspaces/waooaw-platform
cp .env.example .env  # fill in values
./scripts/setup.sh    # start full stack

# Or just BP:
cd src/business-platform
dotnet run
```

## Run tests
```bash
dotnet test src/business-platform --collect:"XPlat Code Coverage"
```

## Key env vars
- `ConnectionStrings__DefaultConnection` — PostgreSQL connection string (business_app user)
- `ConstitutionalEngine__Address` — CE gRPC address (e.g., http://constitutional-engine:5002)
- `Keycloak__Authority` — Keycloak realm URL for JWT validation
- `Keycloak__Audience` — expected JWT audience claim
- `OTLP_ENDPOINT` — OTel collector (http://jaeger:4317 in dev)

## Constitutional obligations
- Every POST/PUT/DELETE must call CE.RecordEvidence BEFORE returning 200 (C-023, AD-002)
- tenant_id comes from JWT only — never from request body (ADR-003)
- All DB queries are tenant-isolated via TenantDbCommandInterceptor (AD-004)
