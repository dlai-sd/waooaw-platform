# GitHub Actions Secrets — WAOOAW Platform
# constitutional_basis: C-059 (Implementation Traceability), ADR-014 (Secret Management)
# ib_item: IB-009 (WC011-07)
# produced_by: WC011-07 autonomous sprint task

This document lists all GitHub Actions secrets required by the WAOOAW platform CI/CD pipelines.
No secret values are stored here. Obtain each secret from the source listed and add to:
**Settings → Secrets and variables → Actions** in the `dlai-sd/waooaw-platform` repository.

---

## Required Secrets

| Secret | Used By | Obtain From | Status | Notes |
|---|---|---|---|---|
| `AZURE_CREDENTIALS_DEV` | `promote.yaml` (dev deploy) | Azure SP — FA-NNN: create Service Principal with Container Apps Contributor | PENDING | Required before any `docker compose` on Azure |
| `AZURE_CREDENTIALS_QA` | `promote.yaml` (QA promote) | Azure SP — same app registration, QA scope | PENDING | Unblocks QA promotion gate |
| `AZURE_CREDENTIALS_PROD` | `promote.yaml` (prod promote) | Azure SP — prod scope, separate credentials | PENDING | Restricted: Yogesh approval required |
| `CODECOV_TOKEN` | `ci.yaml` (coverage upload) | [codecov.io](https://codecov.io) → Add repo → copy token | PENDING | Required for C-076 coverage gate |
| `DEV_BASE_URL` | `post-deploy-verify.yaml` | Terraform output `azurerm_container_app.web.ingress[0].fqdn` after M1 | PENDING | Available after first Terraform apply |
| `DEV_CONSTITUTIONAL_DB_URL` | `promote.yaml` CCT jobs | Terraform output `postgresql_flexible_server.dev.fqdn` + credentials | PENDING | Available after M2 |
| `DEV_TEST_JWT_TENANT_A` | `promote.yaml` CCT jobs | `scripts/get-dev-token.sh TENANT_A` after Keycloak is live | PENDING | Test JWT for tenant isolation CCTs |
| `DEV_TEST_JWT_TENANT_B` | `promote.yaml` CCT jobs | `scripts/get-dev-token.sh TENANT_B` after Keycloak is live | PENDING | Second tenant — cross-tenant isolation tests |
| `REVIEW_APP_TOKEN` | `autonomous-sprint.yaml` review job | GitHub App private key — see FA-023 | PENDING | Until provisioned: advisory comments only (C-065) |

---

## Optional Secrets (enable specific capabilities)

| Secret | Used By | When Needed |
|---|---|---|
| `GCP_SA_KEY` | AI Runtime (Vertex AI) | FA-021: Sprint 015 AI Runtime real inference |
| `SARVAM_API_KEY` | AI Runtime (Sarvam PSE) | FA-022: Agricultural Agent live deployment |
| `META_APP_SECRET` | instagram-mcp / meta-ads-mcp | FA-002: After Meta Business Manager verification |
| `GOOGLE_CLIENT_SECRET` | google-ads-mcp / google-business-mcp | FA-003: After Google Ads MCC setup |

---

## Secret Rotation Policy (ADR-014)

- Azure SP credentials: rotate every 90 days (Azure enforced)
- API keys: rotate if leaked; quarterly audit minimum
- JWT test tokens: regenerate per sprint if used in automated tests
- **Never**: commit secret values to code, log files, or PR descriptions

---

## Validation Command

After adding secrets, verify they are available:
```bash
# In GitHub Actions runner context (not locally):
echo "CODECOV_TOKEN is set: ${CODECOV_TOKEN:+yes}"
echo "AZURE_CREDENTIALS_DEV is set: ${AZURE_CREDENTIALS_DEV:+yes}"
```
