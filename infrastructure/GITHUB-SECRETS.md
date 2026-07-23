# GitHub Actions Secrets & Variables — WAOOAW Platform
# constitutional_basis: C-059 (Implementation Traceability), ADR-014 (Secret Management)
# ib_item: IB-009 (WC011-07)
# produced_by: WC011-07 autonomous sprint task

## Architecture: OIDC + Azure Key Vault (no long-lived credentials in GitHub Secrets)

Per ADR-014, all secrets live in Azure Key Vault (waooaw-dev-kv).
GitHub Actions authenticates to Azure via OIDC (no stored client secret).
Non-sensitive config values are GitHub Variables (not Secrets).

---

## GitHub Variables (non-sensitive config — Settings → Variables → Actions)

| Variable | Value | Purpose |
|---|---|---|
| `AZURE_CLIENT_ID` | App Registration Client ID | OIDC authentication to Azure |
| `AZURE_TENANT_ID` | Azure AD Tenant ID | OIDC authentication to Azure |
| `AZURE_SUBSCRIPTION_ID` | Azure Subscription ID | OIDC scope |
| `AZURE_KEYVAULT_NAME` | `waooaw-dev-kv` | Key Vault name for secret fetch |

**Status: All 4 set** (2026-07-23)

---

## Azure Key Vault Secrets (fetched at runtime via OIDC — never stored in GitHub)

| KV Secret Name | Used By | Obtain From | Status |
|---|---|---|---|
| `ANTHROPIC-API-KEY` | `autonomous-sprint.yaml` execute + review | console.anthropic.com → API Keys | ✅ DONE |
| `GH-APP-ID` | `autonomous-sprint.yaml` review | GitHub App waooaw-reviewer | ✅ DONE |
| `GH-APP-INSTALLATION-ID` | `autonomous-sprint.yaml` review | GitHub App installation | ✅ DONE |
| `GH-APP-PRIVATE-KEY` | `autonomous-sprint.yaml` review | GitHub App private key (.pem) | ✅ DONE |
| `CODECOV-TOKEN` | `ci.yaml` coverage upload | codecov.io → repo settings | ✅ DONE |
| `DEV_BASE_URL` | `post-deploy-verify.yaml` | Terraform output after M1 | ⬜ PENDING |
| `DEV_CONSTITUTIONAL_DB_URL` | `promote.yaml` CCTs | Terraform output after M2 | ⬜ PENDING |
| `DEV_TEST_JWT_TENANT_A` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |
| `DEV_TEST_JWT_TENANT_B` | `promote.yaml` CCTs | `scripts/get-dev-token.sh` after Keycloak live | ⬜ PENDING |
| `GOOGLE-VERTEX-SA-KEY` | AI Runtime (Gemini) | GCP SA key JSON (FA-021) | ⬜ PENDING |
| `SARVAM-API-KEY` | AI Runtime (Agricultural) | sarvam.ai API key (FA-022) | ⬜ PENDING |
| `AZURE-OPENAI-KEY` | AI Runtime (fallback LLM) | Azure OpenAI UAE North (FA-003) | ⬜ PENDING |

---

## Secret Rotation Policy (ADR-014)

- Azure OIDC: no rotation needed (no client secret — OIDC federated credential)
- ANTHROPIC-API-KEY: rotate if exposed in logs or AI context
- GH-APP-PRIVATE-KEY: rotate annually or if exposed
- All others: rotate if leaked; quarterly audit minimum

## No Longer Used

The following were in earlier designs but are replaced by OIDC:
- `AZURE_CREDENTIALS_DEV/QA/PROD` — replaced by OIDC federated credential
- `REVIEW_APP_TOKEN` — replaced by `GH-APP-PRIVATE-KEY` in Key Vault + JWT generation
