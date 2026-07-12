# Simulation 010 — Developer Simulation: First Day Building WAOOAW

**Type:** Developer Simulation — Infrastructure + API + First Runnable Agent Call
**Status:** Active
**Purpose:** Walk through the complete first-day developer experience: clone repo, start the stack, run migrations, call the first endpoint, trigger the first agent response. Surface infrastructure gaps, missing config, docker-compose gaps, env var gaps, and build friction.
**Persona:** A backend developer (Node.js/Python background, new to .NET), Day 1 on WAOOAW. Has read the README and the ARCHITECTURE.md. Has Docker + git installed.

---

## Phase 1 — Repo Clone + Environment Setup

```bash
git clone https://github.com/dlai-sd/waooaw-platform.git
cd waooaw-platform
cp .env.example .env
```

Developer opens `.env` and sees fields to fill.

### [GAP-DEV-001] .env.example Does Not Exist

**Current state:** The README references `cp .env.example .env` as Step 1 of setup. But `scripts/setup.sh` and `.env.example` are in the scripts directory spec — the actual `.env.example` file has not been created in the repository.

**Developer experience:** `cp .env.example .env` → `cp: .env.example: No such file or directory`.

**Resolution:** Create `.env.example` with all required environment variables documented (with placeholder values for required vars, actual safe defaults for optional ones). This is the foundational onboarding file for every developer.

**Layer:** `.env.example` (new file — high priority); `scripts/setup.sh` (verify it references the correct path).

---

## Phase 2 — Docker Compose Up

```bash
./scripts/setup.sh
# or directly:
docker-compose up -d
```

### [GAP-DEV-002] Signal Watch Worker Not in docker-compose.yml

The Signal Intelligence Layer (C-053) requires `SignalWatchWorkflow` to run as long-running Temporal workflows. These are started by the AI Runtime at boot (`start_signal_watch_workflows()`). But:

- `ai-runtime` service needs to know to start signal watch workers at boot
- The current `ai-runtime` service in docker-compose has no `SIGNAL_WATCH_ENABLED` env var
- There is no worker process definition for the signal watch Temporal worker queue (`signal-watch-queue`)
- Temporal has two queues: the regular `ai-runtime-queue` and the new `signal-watch-queue` — the latter has no registered worker in docker-compose

**Gap:** Signal Watch Workflows will never run in local dev because no worker is registered on `signal-watch-queue`.

**Resolution:**
```yaml
# Add to docker-compose.yml: signal-watch-worker service
signal-watch-worker:
  build: { context: ., dockerfile: architecture/reference/dockerfiles/Dockerfile.python-service }
  command: ["python", "-m", "workers.signal_watch_worker"]
  environment:
    TEMPORAL_HOST: temporal:7233
    TEMPORAL_TASK_QUEUE: signal-watch-queue
    SIGNAL_WATCH_ENABLED: "true"
    # Signal feed MCP URLs
    MCP_WEATHER_ENSEMBLE_URL: http://weather-ensemble-mcp:8121
    MCP_AGMARKNET_URL: http://agmarknet-mcp:8122
    MCP_MARKET_DATA_URL: http://market-data-mcp:8103
    MCP_PLATFORM_ANALYTICS_URL: http://platform-analytics-mcp:8115
    MCP_META_AD_LIBRARY_URL: http://meta-ad-library-mcp:8118
  depends_on:
    - temporal
    - ai-runtime
  restart: unless-stopped
```

**Layer:** `docker-compose.yml` (add signal-watch-worker); AI Runtime worker startup (register both task queues).

---

### [GAP-DEV-003] New Platform MCP Stubs Not in docker-compose.yml

The DMA agent Section 3.21 references `youtube-mcp`, `linkedin-mcp`, `x-mcp`, `pinterest-mcp`, `threads-mcp` as new platform MCPs. These are added to `containers.md` with PLANNED status but have NO stub services in `docker-compose.yml`.

Developer running local simulation of a DMA campaign that includes YOUTUBE_SHORT content variant → `youtube-mcp` call fails → no stub → unhandled error.

**Resolution:** Add stub services for all 5 new platform MCPs. Stubs return realistic mock data.

```yaml
youtube-mcp:
  image: python:3.12-slim
  command: ["python", "-c", "from http.server import HTTPServer,BaseHTTPRequestHandler; import json; ..."]
  ports: ["8138:8138"]
  environment:
    MCP_PORT: "8138"
    MCP_SERVICE: youtube-mcp-stub

linkedin-mcp:
  image: python:3.12-slim
  ports: ["8139:8139"]
  environment:
    MCP_PORT: "8139"

x-mcp:
  image: python:3.12-slim
  ports: ["8140:8140"]
  environment:
    MCP_PORT: "8140"

pinterest-mcp:
  image: python:3.12-slim
  ports: ["8141:8141"]
  environment:
    MCP_PORT: "8141"

threads-mcp:
  image: python:3.12-slim
  ports: ["8142:8142"]
  environment:
    MCP_PORT: "8142"
```

And corresponding `SIGNAL_WATCH_WORKER_URL` + `MCP_YOUTUBE_URL` etc. env vars in `ai-runtime`.

**Layer:** `docker-compose.yml` (5 new stub services); `ai-runtime` service env block (5 new MCP URLs).

---

## Phase 3 — Database Migration

```bash
# postgres init scripts run automatically on first docker-compose up
docker-compose logs postgres | grep -i "migration\|init\|error"
```

### [GAP-DEV-004] SQL Init Script Order Dependency: ALTER TABLE on Non-Existent Columns

The v0.40.0 simulation gap bridges add `ALTER TABLE` statements to `03-enums-and-tables.sql`:
```sql
ALTER TABLE business.farmer_profiles ADD COLUMN IF NOT EXISTS stated_price_target_inr_per_quintal ...
ALTER TABLE business.weather_alert_log ADD COLUMN IF NOT EXISTS imd_warning_id ...
ALTER TABLE institutional.agent_evidence_records ADD COLUMN IF NOT EXISTS parent_request_id ...
```

**Problem:** These `ALTER TABLE` statements are appended at the end of `03-enums-and-tables.sql`. PostgreSQL executes init scripts in alphanumeric order (`01-`, `02-`, `03-`, `04-`). The `ALTER TABLE` on `farmer_profiles` assumes the table exists — which it does, earlier in the same file. But:

- `weather_alert_log` is referenced but created in an earlier sprint migration that may not exist yet in a fresh database
- `agent_evidence_records` is in the constitutional schema (`institutional`) and may be created in a different init file

**Resolution:** Move `ALTER TABLE` statements to a `05-migrations.sql` file that runs AFTER all CREATE TABLE statements, with explicit `IF EXISTS` checks. This makes migrations order-safe for new developer environments.

**Layer:** New file `infrastructure/postgres/init/05-migrations.sql`; move `ALTER TABLE` gap bridge statements from `03-enums-and-tables.sql`.

---

## Phase 4 — Getting a Dev Token

```bash
./scripts/get-dev-token.sh
```

### [GAP-DEV-005] DEV_TEST_USER and DEV_TEST_PASSWORD Not Seeded

`get-dev-token.sh` requires `DEV_TEST_USER` and `DEV_TEST_PASSWORD` in `.env`. These must match a user seeded in Keycloak. But:
- The `infrastructure/keycloak/` directory has realm configuration but no seed user
- A new developer must manually create a test user in Keycloak admin UI (localhost:8443)
- There is no `seed-dev-user.sh` script or Keycloak realm import that includes a test user

**Developer experience:** Script fails with "invalid_grant: Invalid user credentials."

**Resolution:**
- Add test user to Keycloak realm JSON: `dev-test@waooaw.local` / `dev-test-password-123`
- Add to `.env.example`: `DEV_TEST_USER=dev-test@waooaw.local` / `DEV_TEST_PASSWORD=dev-test-password-123`
- OR: Add `scripts/seed-dev-user.sh` that calls Keycloak Admin API to create the user after first boot

**Layer:** `infrastructure/keycloak/` realm import (add test user); `.env.example` (add DEV_TEST_USER, DEV_TEST_PASSWORD with safe defaults).

---

## Phase 5 — First API Call

Developer tries to call the first meaningful endpoint:

```bash
export TOKEN=$(./scripts/get-dev-token.sh)
curl -H "Authorization: Bearer $TOKEN" \
     http://localhost:5001/api/v1/employment/contracts
```

### [GAP-DEV-006] Business Platform Service Not in docker-compose.yml

The Business Platform (port 5001) is referenced in the README curl example. But the `docker-compose.yml` has:
- `postgres` ✓
- `keycloak` ✓
- `temporal` + `temporal-admin-tools` ✓
- `ai-runtime` (stub) ✓
- 23 MCP stub services ✓
- `oauth-vault` (stub) ✓

**But `business-platform` service is NOT in docker-compose.yml.** It exists in the component specs but has never been wired into docker-compose for local development.

Similarly, `professional-runtime` and `constitutional-engine` are not running locally.

**Developer experience:** `curl: (7) Failed to connect to localhost port 5001: Connection refused`

**The honest assessment:** At MVI architecture stage, these services exist only as specs. The docker-compose is designed to run the MCP stubs and infrastructure but not the actual services (which don't exist yet as code — IB-009 is the implementation sprint).

**Resolution:** Add placeholder services for the 4 core WAOOAW services in docker-compose with a `NOT_YET_IMPLEMENTED` image that returns a helpful error message:

```yaml
business-platform:
  image: python:3.12-slim
  command: ["python", "-c", "
import http.server, json
class H(http.server.BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(503)
    self.send_header('Content-Type','application/json')
    self.end_headers()
    self.wfile.write(json.dumps({'error':'IB-009_NOT_YET_IMPLEMENTED',
      'message':'Business Platform is not yet built. This is a spec-only repository at v0.40.0.',
      'implementation':'Awaiting Founder authorization for IB-009 implementation sprint.',
      'spec':'architecture/reference/components/business-platform.md'}).encode())
http.server.HTTPServer(('0.0.0.0',5001),H).serve_forever()
"]
  ports: ["5001:5001"]

constitutional-engine:
  image: python:3.12-slim
  command: [same pattern, port 5000]
  ports: ["5000:5000"]
```

This makes the error informative rather than a silent connection refused.

**Layer:** `docker-compose.yml` (add 4 core service stubs with NOT_YET_IMPLEMENTED message).

---

## Phase 6 — Signal Watch Local Testing

Developer wants to test the Signal Intelligence Layer locally:

```bash
# Trigger a weather alert manually (simulating a hail risk signal)
curl -X POST http://localhost:8000/debug/signal \
     -d '{"signal_type": "WEATHER_HAIL_RISK", "district": "Nagpur", "hail_probability": 0.75}'
```

### [GAP-DEV-007] No Debug/Test Endpoint for Signal Intelligence Layer

There is no way to trigger a signal manually in local development without:
- Waiting for the real-time poll cadence (every 15 minutes for weather)
- Mocking the weather-ensemble-mcp response

**Resolution:** AI Runtime should expose a development-only debug endpoint:
```
POST /debug/signal (only in development — SIGNAL_DEBUG_ENDPOINT_ENABLED=true in .env)
  Body: {signal_type, agent_type, organisation_id, mock_payload}
  Action: bypasses materiality classifier, injects signal directly into customer's workflow
```

This allows developers to test the full signal→execution loop without waiting for real signal cadence.

**Layer:** AI Runtime (add debug signal injection endpoint, gated by env var); `.env.example` (add SIGNAL_DEBUG_ENDPOINT_ENABLED=false with comment).

---

## Gap Register — Developer Simulation 010

### P0 — Blocks first developer run

| ID | Gap | Resolution |
|---|---|---|
| GAP-DEV-001 | `.env.example` does not exist | Create `.env.example` with all env vars documented |
| GAP-DEV-005 | Keycloak test user not seeded | Add test user to realm import; add seed script |
| GAP-DEV-006 | Core services (BP, CE, PR, AIR) not in docker-compose | Add NOT_YET_IMPLEMENTED stubs with helpful error messages |

### P1 — Blocks simulation runs

| ID | Gap | Resolution |
|---|---|---|
| GAP-DEV-002 | Signal watch worker not in docker-compose | Add signal-watch-worker service |
| GAP-DEV-003 | New platform MCP stubs not in docker-compose | Add 5 new platform MCP stubs |
| GAP-DEV-004 | ALTER TABLE in init SQL — order dependency | Move to 05-migrations.sql |

### P2 — Developer experience

| ID | Gap | Resolution |
|---|---|---|
| GAP-DEV-007 | No debug endpoint for signal injection | Add development-only debug signal endpoint |

---

## Developer Simulation: What Would Work Today (v0.40.0)

After fixing P0 gaps, a developer can:
1. `docker-compose up -d` → all infrastructure starts (Postgres, Keycloak, Temporal, 23+ MCP stubs)
2. Run Postgres migrations → all schema is created
3. Get a JWT from Keycloak → `./scripts/get-dev-token.sh`
4. Call ANY MCP stub directly → all return realistic mock data
5. Test the Signal Intelligence Layer via debug endpoint → weather, VIX, broker auth signals
6. Inspect the database → all tables created, RLS policies applied
7. Run Temporal workflows via temporal-admin-tools → can manually trigger AgentExecution

A developer CANNOT yet:
- Call the Business Platform, Constitutional Engine, or Professional Runtime (not built)
- Place an actual trade or publish an actual post (no live integrations)
- Run end-to-end AI agent reasoning (AI Runtime is a stub)
