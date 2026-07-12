# ADR-021 — External Platform OAuth and Token Management

**Status:** Accepted
**Date:** 2026-07-09
**Author:** Enterprise Architect (simulation-driven — Simulation 004 GAP-012)
**Constitutional Basis:** C-041 (tool authorization — authenticated tool calls require customer delegation); C-003 (authority is licensed — OAuth delegation is a license grant); AD-004 (multi-tenant isolation — each customer's tokens are isolated); ADR-014 (secret management)

---

## Context

The Digital Marketing Agent must execute actions on external platforms (Instagram, Facebook, Google Business Profile, Meta Ads, Google Ads, Google Search Console) on behalf of customers. These platforms require OAuth 2.0 authentication using the customer's account credentials — not WAOOAW's own credentials.

Three design problems must be solved:
1. **Token acquisition:** How does the customer's OAuth token get into the platform?
2. **Token storage:** Where are tokens stored securely, with tenant isolation?
3. **Token lifecycle:** How are short-lived tokens refreshed without customer re-interaction?

---

## Decision

### 1. OAuth Flow Architecture

WAOOAW implements a **Server-Side OAuth Authorization Code Flow** for each supported platform:

```
Customer in Portal
    ↓ taps "Connect Instagram"
Business Platform (/api/v1/oauth/connect/{platform})
    ↓ redirects to Meta OAuth authorization endpoint
Meta OAuth (customer logs in, grants permissions)
    ↓ redirects back to WAOOAW callback: /api/v1/oauth/callback/{platform}
Business Platform receives: { code, state }
    ↓ exchanges code for access_token + refresh_token (server-side — PKCE)
oauth-vault service stores tokens (tenant-isolated)
Business Platform returns: { connected: true }
```

### 2. OAuth Vault Service (oauth-vault, port 8130)

A dedicated lightweight service responsible exclusively for credential storage and refresh. **Business logic does NOT live here — it is a secure key-value store with a refresh scheduler.**

**Responsibilities:**
- Store: `POST /tokens/{contract_id}/{platform}` — encrypt and store access_token + refresh_token + expiry
- Retrieve: `GET /tokens/{contract_id}/{platform}` — return current access_token; auto-refresh if expired
- Revoke: `DELETE /tokens/{contract_id}/{platform}` — called on contract termination (evidence record required)
- Health: `GET /health/{contract_id}/{platform}` — returns token status: VALID, EXPIRING_SOON, EXPIRED, NOT_CONNECTED

**Encryption:** Tokens encrypted at rest using AES-256-GCM with a per-tenant key. Master key stored in Azure Key Vault / AWS KMS (ADR-014). Tenant key is derived from the master key + tenant_id using HKDF.

**Tenant isolation:** `contract_id` is always in the URL path. The service verifies the calling service's mTLS certificate (ADR-007) — only AI Runtime and MCP servers may call oauth-vault. Business Platform may call only for connect/revoke operations.

### 3. Token Refresh

- `oauth-vault` runs a background refresh scheduler: checks all tokens every 30 minutes
- Tokens expiring within 2 hours are proactively refreshed using the stored refresh_token
- If refresh fails (refresh_token expired, permissions revoked): set status = EXPIRED; raise PLATFORM_TOKEN_EXPIRED event to Professional Runtime
- Professional Runtime on receiving PLATFORM_TOKEN_EXPIRED: pause affected skill; notify customer via delivery channels; raise approval request to re-connect the platform

### 4. Supported Platforms and Required Scopes

| Platform | OAuth Provider | Required Scopes | Token Lifetime |
|---|---|---|---|
| Instagram Business | Meta | `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_read_engagement` | 60 days (long-lived); refresh before expiry |
| Facebook Page | Meta | `pages_manage_posts`, `pages_read_engagement`, `pages_manage_ads` | Same as Instagram |
| Google Business Profile | Google | `https://www.googleapis.com/auth/business.manage` | 1 hour; refresh_token indefinite |
| Google Ads | Google | `https://www.googleapis.com/auth/adwords` | 1 hour; refresh_token indefinite |
| Google Search Console | Google | `https://www.googleapis.com/auth/webmasters.readonly` | 1 hour; refresh_token indefinite |
| Google Analytics 4 | Google | `https://www.googleapis.com/auth/analytics.readonly` | 1 hour; refresh_token indefinite |
| Meta Ads | Meta | `ads_management`, `ads_read` | 60 days |

### 5. Personal Instagram vs. Business Instagram (GAP-013 from Simulation 004)

Instagram's Content Publishing API requires a **Facebook-connected Instagram Professional account** (Business or Creator). Personal accounts cannot publish via API.

**Platform enforcement:** When the customer initiates Instagram connection, the OAuth flow must check account type via `GET /{ig-user-id}?fields=account_type`. If `account_type = PERSONAL`: reject connection; display: "I need a Professional Instagram account to post for you. Here's how to switch yours — it's free and takes 30 seconds." with a direct link to Instagram's account type settings.

---

## Rejected Alternatives

**A — Store tokens in Keycloak:** Keycloak manages WAOOAW user identity, not external platform credentials. Mixing these creates a security boundary violation — if Keycloak is compromised, all external platform credentials are exposed.

**B — Store tokens in PostgreSQL directly:** Technically feasible but violates ADR-014 (secret management). Tokens are secrets, not business data. They must be managed by a dedicated secret-aware service.

**C — Use WAOOAW's own app credentials for all customers:** Violates Meta and Google Terms of Service. Each customer must authorize WAOOAW's app to act on their specific account.

---

## Consequences

- New container: `oauth-vault` (port 8130) — must be added to docker-compose and containers.md
- New environment variable: `OAUTH_VAULT_URL` in ai-runtime and mcp servers
- New BP endpoints: `GET /api/v1/oauth/connect/{platform}`, `GET /api/v1/oauth/callback/{platform}`, `GET /api/v1/oauth/status/{contractId}`, `DELETE /api/v1/oauth/disconnect/{platform}`
- Trial limitation: Customers in trial who haven't connected Instagram cannot publish posts — skills requiring OAuth connections are blocked until connection is made

### 6. Token Revocation on Contract Termination (GAP-024 — Data Retention)

On `EMPLOYMENT_TERMINATED` event: `oauth-vault` must revoke ALL tokens for that `contract_id` within 24 hours. Revocation sequence:
1. Call platform revocation endpoints (Meta: `DELETE /oauth/revoke_token`; Google: `POST /oauth2/revoke`)
2. Delete tokens from vault storage
3. Record deletion in `data_retention_records` under `deletion_scope = ["oauth_tokens"]`

Tokens are secrets — they are NOT covered by the 180-day Tier 2 data retention period. They are revoked immediately on termination regardless of the customer's data retention preferences.

---

## 7. Secret Vault Backing — Explicit Confirmation (v0.37.1)

**Decision confirmed:** The `oauth-vault` service is explicitly backed by **Azure Key Vault** (ADR-014) for master key storage. This was implicit in Section 2 ("Master key stored in Azure Key Vault / AWS KMS"). This section makes it explicit and non-ambiguous.

**Encryption architecture:**
```
oauth-vault DB (PostgreSQL, encrypted at-rest via Azure Disk Encryption)
    ↓ Each customer token encrypted with per-tenant AES-256-GCM key
    ↓ Per-tenant key = HKDF(master_key, tenant_id)  — never stored
Master key → Azure Key Vault (per-environment: waooaw-dev-kv, waooaw-prod-kv)
    ↓ oauth-vault reads master key from Key Vault AT STARTUP via managed identity (ADR-014 pattern)
    ↓ Master key held in memory only — never written to disk or DB
```

**Why this is sufficient (cost boundary confirmed):**
- Azure Key Vault: ~₹150–300/month per environment (confirmed in ADR-014) — within cost boundary
- No HashiCorp Vault required (ADR-014 rejected it: operational management cost not justified at MVI)
- The oauth-vault service itself is NOT a general secret store — it is narrowly scoped to OAuth tokens only. Platform secrets (DB passwords, API keys, Temporal certs) continue to follow ADR-014 three-tier model: `.env` → GitHub Secrets → Azure Key Vault directly.

**What was deferred (ADR-023 extension):**
The STT service for WhatsApp voice transcription (Agricultural agent) requires a new OAuth credential pattern (STT provider API key, not user-delegated OAuth). This is a platform API key, not a customer OAuth token. It follows ADR-014 directly (GitHub Secret in CI; Azure Key Vault in cloud) — oauth-vault is NOT involved. ADR-023 extension remains open only for STT provider selection, not for credential storage architecture.

**Summary for Founder:** ADR-014 (Azure Key Vault) + ADR-021 (oauth-vault backed by Key Vault) together cover ALL secret storage needs at MVI. No additional secret infrastructure is needed. The architecture is settled.
