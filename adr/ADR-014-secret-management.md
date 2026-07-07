# ADR-014: Secret Management

**Status:** Accepted
**Date:** 2026-07-07
**Roles Applied:** Security Architect (secret lifecycle) + Platform Architect (pipeline integration)
**Constitutional Basis:** Constitution Article IX (Constitutional Floors — Security by Design); GENESIS Design Principles — Security by Design; OWASP A02 (Cryptographic Failures — secrets must never appear in plaintext in logs, code, or version control)

---

## Context

The platform has secrets at multiple layers:
- Database passwords (PostgreSQL superuser, app user)
- Keycloak admin password and client secrets
- GHCR pull token (PAT for Container Apps to pull images)
- LLM API keys (OpenAI / Azure OpenAI for AI Runtime)
- Temporal Cloud API key (UAT and production)
- JWT signing keys (Keycloak manages these — not a platform secret)
- Azure infrastructure credentials (for Terraform / GitHub Actions deployment)

Secrets exist in three environments with different characteristics:
1. **Development** — local developer machine, Docker Compose
2. **CI/CD** — GitHub Actions pipelines
3. **Cloud** — Azure Container Apps environments (dev, QA, UAT, prod)

The question is: how are secrets stored, accessed, and rotated in each context?

## Decision

**Three-tier secret management: `.env` files for dev (git-ignored), GitHub Actions Secrets for CI, Azure Key Vault for cloud environments. Secrets never appear in any committed file.**

### Tier 1: Development (Docker Compose)

```
.env                — actual secret values (git-ignored, never committed)
.env.example        — template with placeholder values (committed to git)
```

Developer onboarding: copy `.env.example` to `.env`, fill in values. The `.gitignore` entry for `.env` is present from repository day one — there is no "safe" moment to add it later.

```
# .env.example (committed)
POSTGRES_PASSWORD=change-me
KEYCLOAK_ADMIN_PASSWORD=change-me
KEYCLOAK_CLIENT_SECRET=change-me
GHCR_PAT=change-me
LLM_API_KEY=change-me

# .env (git-ignored, never committed)
POSTGRES_PASSWORD=actual-strong-password-here
KEYCLOAK_ADMIN_PASSWORD=actual-keycloak-password
...
```

**Prohibited in dev:**
- Hardcoded secrets in `docker-compose.yaml` or any source file
- Default passwords that are unchanged from vendor defaults (e.g., `postgres/postgres`)

### Tier 2: CI/CD (GitHub Actions)

All pipeline secrets are stored as **GitHub Actions Encrypted Secrets** (repository or environment level).

```
GitHub Repository Secrets:
  AZURE_CLIENT_ID          — Service principal for Terraform deployments
  AZURE_CLIENT_SECRET      — Service principal secret
  AZURE_SUBSCRIPTION_ID    — Azure subscription
  AZURE_TENANT_ID          — Azure tenant
  GHCR_PAT                 — Used to configure Container Apps image pull

GitHub Environment Secrets (per environment: dev, qa, uat, prod):
  DATABASE_APP_PASSWORD    — App user password for this environment
  KEYCLOAK_CLIENT_SECRET   — Keycloak client secret for this environment
  LLM_API_KEY              — LLM API key for this environment
  TEMPORAL_CLOUD_API_KEY   — Temporal Cloud key (uat and prod only)
```

GitHub environment secrets require environment-level approval. UAT and production environment secrets are only accessible when the corresponding deployment workflow receives manual approval.

### Tier 3: Cloud (Azure Key Vault)

Each cloud environment (dev, QA, UAT, prod) has its own Azure Key Vault instance. Container Apps read secrets from Key Vault at startup via **managed identity** — no PAT or credential needed in the application.

```
Key Vault secret → Container Apps secret reference → container environment variable

Example:
  Key Vault: waooaw-dev-kv / secret: database-app-password
  Container Apps: secretRef "db-password" → env var DATABASE_CONNECTION_STRING
```

**Secret rotation:**
- Key Vault secrets are rotated by updating the Key Vault secret version
- Container Apps pick up the new version on next revision deployment (not live — requires a redeploy)
- Rotation frequency: annually or on personnel change

### What Is Never a Secret

- JWT signing keys (Keycloak manages its own signing keys)
- OTel OTLP endpoint (not a secret — it is a configuration value)
- Service URLs and hostnames (not secrets — they appear in logs)

## Alternatives Considered

| Option | Reason Rejected |
|---|---|
| Secrets in environment-specific config files (committed) | Any committed secret is permanently in git history. Rotation requires a git history rewrite. OWASP A02 violation. |
| HashiCorp Vault | Excellent tool. Requires operational management of Vault itself (HA, unsealing, backup). Zero justification at MVI when Azure Key Vault + GitHub Secrets covers all cases. |
| Azure App Configuration | Designed for configuration values, not secrets. Secrets belong in Key Vault. Using both would split the mental model. |
| Single shared Key Vault across environments | A compromised dev secret would give access to production secrets. Each environment has its own Key Vault — blast radius is limited to one environment. |

## Consequences

**Benefits:**
- No secret ever appears in version control, including git history
- Each environment's secrets are isolated — a dev credential cannot access production
- Managed identity for cloud environments means no long-lived service credentials in container configuration
- GitHub environment approval gates protect production secrets

**Trade-offs:**
- New developer setup requires manual `.env` file creation (can't be automated without exposing secrets)
- Secret rotation requires a container revision deployment in Container Apps (not live reload)
- Key Vault costs ~₹150-300/month per environment (negligible)

**Audit obligation:**
Secret access is logged by Azure Key Vault. Access logs must be reviewed monthly as part of the Security Architect's constitutional compliance obligation.
