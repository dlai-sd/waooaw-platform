# ADR-042 — Provider Registry and Constitutional Tool Gateway

**Status:** Accepted  
**Date:** 2026-08-06  
**Authority:** C-031 (No significant architectural decision without an ADR — LAW)  
**Deciders:** Yogesh Khandge (Founder), Enterprise Architect (INST-004)  
**Extends:** ADR-020 (MCP Integration Pattern), ADR-021 (External Platform OAuth Token Management)  
**Breaking Change:** YES — ADR-020 §Decision places CE.ValidateAction responsibility in AI Runtime. This ADR supersedes that placement and moves it to the Constitutional Tool Gateway shared library.

---

## Context

ADR-020 established MCP as the standard for external tool connectivity and declared that CE.ValidateAction must be called before every MCP tool invocation. ADR-021 established oauth-vault as the token storage and refresh service.

Two unresolved architectural gaps remain:

**Gap 1 — No runtime-configurable provider routing.** ADR-021 hardcodes platform names (Instagram, Facebook, Google) in the spec. Adding a new OAuth platform requires a code change, not a configuration row. The founding session on 2026-08-06 identified that WAOOAW's competitive position depends on being the single constitutional delegate across ALL external platforms simultaneously. This requires a generic, declarative provider registry that any OAuth2, API key, or internal JWT provider can be added to without modifying service code.

**Gap 2 — CE validation placement creates duplication and bypass risk.** ADR-020 says "AI Runtime calls CE.ValidateAction before every MCP call." This means:
- If Professional Runtime also needs to make an external call (WhatsApp notification, platform webhook), it must re-implement the same CE gate + oauth-vault injection
- There is no structural guarantee that a new service calling an external API will remember to validate first
- LLM provider calls (OpenAI, Anthropic, Google Gemini) are external API calls with cost implications but are NOT routed through CE — creating an evidence gap for budget enforcement

The Constitutional Tool Gateway resolves both gaps by making CE-first governance structurally non-bypassable at the library level, not the convention level.

---

## Constitutional Basis

| Claim | Application |
|---|---|
| **C-031** | This ADR is the required record for the architectural decision to introduce CTG and the Provider Registry |
| **C-041** | Every tool call governed by Decision Space — CTG enforces this structurally, not by convention |
| **C-003** | Authority is licensed, not assumed — Provider Registry stores the license grant (customer OAuth delegation) |
| **C-059** | Traceability — every CTG call writes an evidence record before returning to caller |
| **ADR-014** | Secret management — oauth-vault path is never written to logs; CTG enforces this via Exception Translator |
| **ADR-021** | Token storage model is preserved; CTG adds the governance layer on top of oauth-vault's retrieval |

---

## Decision

### 1. Provider Registry

A **Provider Registry** is a per-tenant, runtime-configurable routing table stored in Business Platform's Postgres instance. Each row maps a provider name to its auth method, MCP server endpoint, required scopes, and vault path pattern.

**Schema (BP Postgres table `provider_configs`):**

```sql
CREATE TABLE provider_configs (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES tenants(id),
  provider_name   VARCHAR(64) NOT NULL,          -- e.g. "meta", "google", "openai"
  auth_method     VARCHAR(32) NOT NULL,           -- OAUTH2 | API_KEY | INTERNAL_JWT
  mcp_server_url  VARCHAR(512),                   -- null for API_KEY providers
  scope_set       TEXT[],                         -- required OAuth scopes
  vault_path_key  VARCHAR(256) NOT NULL,          -- pattern: "providers/{tenant_id}/{provider_name}"
  active          BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, provider_name)
);
```

> **WC-038 Corrigendum (2026-08-08):** `tenant_id` is implemented as nullable (`UUID` with no `NOT NULL`
> constraint) to support platform-level entries (e.g. shared OpenAI API key). `NULL` tenant_id rows
> represent platform-wide defaults; a partial unique index (`WHERE tenant_id IS NULL`) enforces
> uniqueness for platform-level entries since standard `UNIQUE` allows multiple NULLs in Postgres.
> The foreign key reference to `tenants(id)` is omitted for platform-level rows by design.

**Business rules:**
- Adding a new provider = inserting a row. No code change, no redeployment.
- `Meta` is the first platform entry. Google OAuth providers (YouTube, GA4, Search Console) are rows 2–5.
- LLM providers (OpenAI, Anthropic, Gemini) are registered with `auth_method = API_KEY` and `mcp_server_url = null`.
- The registry is owned by Business Platform. Only BP may write to it. PR and AIR read via internal HTTP call or shared Postgres connection (implementation detail deferred to WC for Trust Layer sprint).

### 2. Constitutional Tool Gateway (CTG)

The Constitutional Tool Gateway is a **Python shared library** (`src/trust-layer/ctg/`), NOT a standalone service. It is imported by Professional Runtime and AI Runtime. It provides a single entry point for all external calls.

**Why a library, not a service:**
- Adding a service hop for every external call doubles latency on high-frequency paths
- CE validation is already a gRPC call — adding a second HTTP hop for the gateway itself adds no governance value and increases failure surface
- A shared library enforces the pattern at import time — any service that calls external APIs must import CTG; there is no bypass path that compiles

**CTG execution pipeline:**

```
caller: gateway_call(tool_name, args, session_ctx)
        │
        ▼
1. Fetch ProviderConfig from BP registry
   (cached per tenant_id + provider_name, TTL 60s)
        │
        ▼
2. CE.ValidateAction(tenant_id, tool_name, agent_id, dcm_category, budget_claim)
   → ALLOW + decision_id      → continue
   → DENY / ESCALATE          → raise ConstitutionalBlockError(decision_id)
        │
        ▼
3. Fetch ephemeral credential from oauth-vault
   GET /tokens/{contract_id}/{provider_name}
   → returns Bearer token or API key (in-memory only)
        │
        ▼
4. Execute: inject credential at socket boundary, send request
   (MCP tool call for OAuth2 providers; direct HTTP for API_KEY providers)
        │
        ├─ SUCCESS ─────────────────────────────────────────────────────────────┐
        │                                                                        ▼
        │                                                             Write evidence record to Audit Sink:
        │                                                             { decision_id, tool_name, args_hash,
        │                                                               credential_provider, vault_alias,
        │                                                               execution_status: SUCCESS, ts }
        │
        └─ EXCEPTION ──────────────────────────────────────────────────────────┐
                                                                                ▼
                                                              Exception Translator:
                                                              raw exception → MCPToolError(code, sanitized_message)
                                                              full error + credential metadata → secured audit log
                                                              MCPToolError returned to caller (no token, no vault path)
```

**CTG public API:**

```python
class ConstitutionalToolGateway:
    async def call(
        self,
        tool_name: str,
        args: dict,
        session_ctx: SessionContext,
    ) -> GatewayResult:
        ...

class GatewayResult:
    decision_id: str
    result: dict | None
    error: MCPToolError | None

class MCPToolError:
    code: str            # CONSTITUTIONAL_BLOCKED | PROVIDER_ERROR | TOKEN_DEGRADED | TIMEOUT
    message: str         # sanitized, no credential content
    retry_eligible: bool
```

### 3. Breaking Change to AI Runtime Architecture

**Before ADR-042:**
```
AIR → [LLM Provider SDK] (direct call, no CE gate, no evidence record)
AIR → [MCP client] → CE.ValidateAction → oauth-vault → [Platform API]
```

**After ADR-042:**
```
AIR → CTG.call("llm.complete", args, session_ctx) → CE.ValidateAction (budget claim) → oauth-vault (API key) → [LLM Provider API]
AIR → CTG.call("meta.post_content", args, session_ctx) → CE.ValidateAction → oauth-vault (Bearer token) → [Meta Graph API]
```

**What changes in AIR:**
- PSE router continues to handle tier selection (which model, which provider) — unchanged
- After tier selection, PSE router invokes `CTG.call("llm.complete", ...)` instead of calling the LLM SDK directly
- Budget ceiling enforcement (C-043) now has an evidence record for every LLM call, not just tool calls
- API keys for LLM providers are stored in oauth-vault (API_KEY auth_method), not in environment variables in AIR

**Work Contract impact:** No AIR code changes begin until ADR-042, ADR-043, and ADR-044 are merged. Any open WC for the Trust Layer sprint must declare this ADR as a prerequisite.

### 4. Exception Translator (replaces regex scrubber)

Any approach that inspects exception message text and strips credential patterns (regex scrubber) will be rejected in code review. The correct pattern is:

1. `gateway_call()` catches ALL exceptions from the external call phase
2. The full exception (including any token fragments in stack traces) is written to a **secured, internal-only** audit channel — never returned to caller
3. Caller receives only `MCPToolError` with a sanitized `code` and `message`
4. Token is never in an exception message because it is held in a local variable inside the gateway call stack — it is not serialised into any logging call

This is structural prevention, not detection.

### 5. Audit Record Schema (vault security)

Evidence records written by CTG to the Audit Sink must contain:

```json
{
  "decision_id": "DEC-9912",
  "agent_id": "agt_xxxx",
  "tenant_id": "ten_xxxx",
  "tool_name": "meta.pause_campaign",
  "args_hash": "sha256:8f3c...",
  "credential_provider": "meta",
  "vault_alias": "waooaw-dev-kv",
  "execution_status": "SUCCESS",
  "timestamp_utc": "2026-08-06T09:00:00Z"
}
```

Fields that **must never appear** in any evidence record or log line:
- Full Azure Key Vault URL (`https://waooaw-dev-kv.vault.azure.net/secrets/...`)
- Token value (any fragment)
- Client secret
- oauth-vault internal path

---

## Rejected Alternatives

**A — Regex scrubber in exception handler:** String manipulation on exception messages cannot guarantee zero credential leakage because: (a) token may appear in Base64-encoded form the regex does not match, (b) exception chaining may surface the token from a nested call frame. Rejected as non-structurally-sound.

**B — CTG as a separate service:** Adds network hop and failure point for every external call. CE validation is already a network call (gRPC). A second hop adds no governance value and increases p99 latency on all tool-call paths. Rejected.

**C — Keep AI Runtime as sole MCP client (ADR-020 unchanged):** Leaves Professional Runtime without a governed external-call path. As soon as PR needs to send a WhatsApp notification (ADR-023), it would call oauth-vault directly without CE validation, creating a constitutional bypass. Rejected — CTG as shared library closes this gap.

**D — Infisical or Nango as secret broker:** Moves credential storage outside WAOOAW's constitutional boundary. Azure Key Vault is already live (`waooaw-dev-kv`). Temporal already in stack for refresh. No additional vendor dependency is justified. Rejected.

---

## Implementation Prerequisites (for Sprint Execution)

Before any WC opens for trust layer implementation, the following must be in place:
1. ✅ ADR-042 merged (this document)
2. ⏳ ADR-044 merged (Audit Trail Sink — evidence records written by CTG)
3. ⏳ Provider Registry table migration added to BP migration set
4. ⏳ All existing AIR service READMEs updated to show CTG as external-call entry point

*ARCHITECTURE.md container diagram updated in the same commit as this ADR.*
