# Work Contract 038 — Trust Layer Sprint 2: Provider Registry + oauth-vault Service

**Office:** Platform IT Expert (INST-010)  
**Sprint:** WC-038  
**Backlog Item:** IB-010 — Trust Layer & Open Platform Integration (pending Founder ratification)  
**Sprint Track:** Track GREENFIELD — new service (oauth-vault) + BP migration  
**Gate:** G5 CLEAR  
**Reviewer:** Enterprise Architect (INST-004)  
**Constitutional Basis:** C-031 (ADR-042 required — satisfied), C-041 (tool authorization), C-003 (authority licensed), ADR-014 (secret management), ADR-021 (OAuth token management — this WC implements it)  
**Authorization:** Founder must authorize — *"Authorize WC-038"*

**Depends on:** WC-037 DONE (Audit Sink must exist — oauth-vault reads will need CE write path available), ADR-042 merged (✅)  
**Blocks:** WC-039 — CTG library cannot call oauth-vault until it exists  
**Service scope:** Business Platform (.NET 9), new `src/trust-layer/oauth_vault/` (Python FastAPI)

---

## Sprint Goal

Two deliverables:
1. **Provider Registry** — BP gains a `provider_configs` table and a read API. Meta (OAuth2) and OpenAI (API_KEY) are the first two rows seeded. New platform = new config row, no code change.
2. **oauth-vault** — Dedicated Python FastAPI service at port 8130 (internal only). Stores and retrieves OAuth tokens + API keys from Azure Key Vault. Supports JIT retrieval, status health check, revocation. Token never leaves the service boundary as a log value.

After this sprint, the building blocks exist for the CTG library (WC-039) to perform JIT token injection at the socket boundary.

---

## Tasks

| task_id | scope | model_hint | status |
|---|---|---|---|
| WC038-01 | BP migration — `provider_configs` table per ADR-042 §1 schema. Seed two rows: Meta (`auth_method=OAUTH2`, `mcp_server_url=null` for now, `scope_set=[pages_manage_posts, instagram_content_publish]`, `vault_path_key=providers/{tenant_id}/meta`) and OpenAI (`auth_method=API_KEY`, `mcp_server_url=null`, `scope_set=[]`, `vault_path_key=providers/platform/openai`). OpenAI is platform-level (not per-tenant) — `tenant_id = NULL` with unique constraint override. | `reasoning` | pending |
| WC038-02 | BP API — `GET /api/v1/providers` (list active providers for tenant) and `GET /api/v1/providers/{provider_name}` (get config). Internal-only endpoints (requires service-to-service JWT, not customer JWT). These are called by CTG registry cache. | `auto` | pending |
| WC038-03 | `src/trust-layer/oauth_vault/main.py` — FastAPI app skeleton; `src/trust-layer/oauth_vault/routes/tokens.py` — four routes: `POST /tokens/{contract_id}/{provider_name}` (store), `GET /tokens/{contract_id}/{provider_name}` (retrieve + auto-refresh), `DELETE /tokens/{contract_id}/{provider_name}` (revoke — requires CE evidence record before write), `GET /health/{contract_id}/{provider_name}` (token status: VALID/EXPIRING_SOON/EXPIRED/NOT_CONNECTED). | `reasoning` | pending |
| WC038-04 | `src/trust-layer/oauth_vault/vault_client.py` — Azure Key Vault client using `azure-identity` (`DefaultAzureCredential`). Functions: `store_token(vault_alias, path, token_data)`, `retrieve_token(vault_alias, path) → TokenData | None`, `delete_token(vault_alias, path)`. Token data encrypted at rest by AKV. Vault alias from env var `OAUTH_VAULT_ALIAS` (default: `waooaw-dev-kv`). Full KV URL never logged — only `vault_alias` logged. | `reasoning` | pending |
| WC038-05 | `src/trust-layer/oauth_vault/refresh_scheduler.py` — background `asyncio` task started at app startup. Polls `GET /health/*` for all stored tokens every 30 minutes. Tokens with status `EXPIRING_SOON` (< 2 hours remaining): call provider token refresh endpoint using stored refresh_token. On refresh failure: publish `PLATFORM_TOKEN_EXPIRED` event to PR (HTTP POST to PR internal endpoint). | `reasoning` | pending |
| WC038-06 | `src/trust-layer/oauth_vault/exception_handler.py` — global exception handler for oauth-vault. All exceptions caught at FastAPI middleware level. Raw exception (including any token fragments in stack traces) written to internal structured log at WARN level. Caller receives `{ "error": "VAULT_ERROR", "code": "TOKEN_UNAVAILABLE" }` only — no stack trace, no token fragment, no AKV path. | `auto` | pending |
| WC038-07 | Tests — `tests/trust-layer/test_oauth_vault.py`: CCT-VAULT-01 (verify token not in any log output on store/retrieve/error path — mock AKV, inspect log records); CCT-VAULT-02 (revoke requires CE call first — mock CE, assert called before AKV delete); CCT-VAULT-03 (EXPIRING_SOON triggers refresh — mock time + AKV, assert refresh endpoint called); CCT-TOKEN-HEALTH-01 (health returns correct status for VALID/EXPIRING_SOON/EXPIRED). | `auto` | pending |

---

## Required Inputs

| Input | File |
|---|---|
| ADR-042 Provider Registry + CTG spec | `adr/ADR-042-provider-registry-constitutional-tool-gateway.md` |
| ADR-021 OAuth Token Management | `adr/ADR-021-external-platform-oauth-token-management.md` |
| ADR-014 Secret Management | `adr/ADR-014-secret-management.md` |
| Existing AIR requirements for reference | `src/ai-runtime/requirements.txt` |

---

## Definition of Done

- [ ] `provider_configs` table migrated in BP with Meta + OpenAI seed rows
- [ ] BP provider API endpoints functional (internal auth only)
- [ ] oauth-vault FastAPI service starts and passes `GET /health` 200
- [ ] Token store → retrieve round-trip functional against Azure KV (`waooaw-dev-kv`)
- [ ] CCT-VAULT-01: token value absent from all log output under any code path
- [ ] CCT-VAULT-02: revoke calls CE before AKV delete
- [ ] CCT-VAULT-03: EXPIRING_SOON triggers refresh call
- [ ] `ruff` clean, `pytest` clean on trust-layer tests
- [ ] `docker-compose.yml` updated to include `oauth-vault` service on port 8130 (internal network only — not exposed on host)
- [ ] VERSION bumped, CHANGELOG, PROJECT_STATE updated
