# Core infrastructure module — all Azure resources for one WAOOAW environment
# Constitutional basis: ADR-010 (Azure-first), ADR-027 (cost optimisation)
# Module called by: environments/{dev,qa,demo,uat,prod}/main.tf

terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm" }
    random  = { source = "hashicorp/random" }
  }
}

locals {
  prefix = "waooaw-${var.environment}"
  rg     = "rg-${local.prefix}"
  env    = var.environment
  tags   = merge(var.tags, { environment = var.environment })
}

# ─── Resource Group ───────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = local.rg
  location = var.location
  tags     = local.tags
}

# ─── Log Analytics Workspace (OTel → Azure Monitor) ──────────────────────────
# ADR-009: OpenTelemetry → Jaeger (dev) / Azure Monitor (cloud)
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days
  tags                = local.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = local.tags
}

# ─── Key Vault (ADR-014 — Secret Management) ─────────────────────────────────
data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "main" {
  name                        = "kv-${local.prefix}"
  resource_group_name         = azurerm_resource_group.main.name
  location                    = azurerm_resource_group.main.location
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  sku_name                    = "standard"
  enable_rbac_authorization   = true
  soft_delete_retention_days  = 7
  purge_protection_enabled    = local.env == "prod"  # Purge protection only in prod
  tags                        = local.tags
}

# GitHub Actions service principal gets read access to Key Vault
resource "azurerm_role_assignment" "kv_reader" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Store secrets in Key Vault (values passed as sensitive variables)
resource "azurerm_key_vault_secret" "postgres_password" {
  name         = "postgres-admin-password"
  value        = var.postgres_admin_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

resource "azurerm_key_vault_secret" "keycloak_admin_password" {
  name         = "keycloak-admin-password"
  value        = var.keycloak_admin_password
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

resource "azurerm_key_vault_secret" "ghcr_token" {
  name         = "ghcr-pull-token"
  value        = var.ghcr_token
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

# ─── LLM Provider Secrets (ADR-029 — Multi-Provider Strategy) ────────────────
# Google Vertex AI (primary MID_TIER + FRONTIER — asia-south1 Mumbai, DPDPA-primary)
# Founder Action FA-021: Create GCP project + Vertex AI SA key
resource "azurerm_key_vault_secret" "google_vertex_project" {
  name         = "google-vertex-project-id"
  value        = var.google_vertex_project_id
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

resource "azurerm_key_vault_secret" "google_vertex_sa_key" {
  name         = "google-vertex-sa-key"
  value        = var.google_vertex_sa_key  # Service account JSON — sensitive
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

# Sarvam AI (MID_TIER — Agricultural agent override, India-hosted, C-042 compliance)
# Founder Action FA-022: Register at sarvam.ai, get API key
resource "azurerm_key_vault_secret" "sarvam_api_key" {
  name         = "sarvam-api-key"
  value        = var.sarvam_api_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

# LLM provider model routing config (non-secret — can be Key Vault or env var)
resource "azurerm_key_vault_secret" "steward_frontier_model" {
  name         = "steward-frontier-model"
  value        = "gemini-2.5-pro"  # ADR-028 + ADR-029: steward always FRONTIER; updated from gpt-4o
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

resource "azurerm_key_vault_secret" "mid_tier_model_primary" {
  name         = "mid-tier-model-primary"
  value        = "gemini-2.0-flash"  # ADR-029: primary MID_TIER, 40% cheaper than gpt-4o-mini
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

resource "azurerm_key_vault_secret" "mid_tier_model_agri" {
  name         = "mid-tier-model-agri"
  value        = "sarvam-saaras-1.0"  # ADR-029: Agricultural agent override (C-042)
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_reader]
}

# ─── PostgreSQL Flexible Server (ADR-027 O-08) ────────────────────────────────
# Burstable B2ms for dev/qa/demo/uat; Standard D2ds_v5 for prod
resource "azurerm_postgresql_flexible_server" "main" {
  name                   = "psql-${local.prefix}"
  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  version                = var.postgres_version
  administrator_login    = "waooaw_admin"
  administrator_password = var.postgres_admin_password
  storage_mb             = var.postgres_storage_mb
  sku_name               = var.postgres_sku_name

  # High availability — prod only (doubles cost; unnecessary for dev)
  dynamic "high_availability" {
    for_each = local.env == "prod" ? [1] : []
    content {
      mode = "SameZone"
    }
  }

  tags = local.tags
}

# Enable pgvector extension (required for RAG — ADR-019)
resource "azurerm_postgresql_flexible_server_configuration" "pgvector" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.main.id
  value     = "VECTOR,UUID-OSSP,PGCRYPTO"
}

# Allow Container Apps Environment to reach PostgreSQL
resource "azurerm_postgresql_flexible_server_firewall_rule" "container_apps" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"  # Azure-internal traffic; not public internet
}

# ─── Container Apps Environment ───────────────────────────────────────────────
# ADR-027: Consumption plan — scales to zero when idle, pay-per-use
resource "azurerm_container_app_environment" "main" {
  name                       = "cae-${local.prefix}"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = local.tags
}

# ─── Container Apps — all 9 services ──────────────────────────────────────────

locals {
  image_base = "${var.ghcr_server}/${var.image_org}"
  tag        = var.image_tag
  # Container Apps registry credentials (GHCR)
  registries = [{
    server               = var.ghcr_server
    username             = var.ghcr_username
    password_secret_name = "ghcr-token"
  }]
  registry_secret = [{
    name  = "ghcr-token"
    value = var.ghcr_token
  }]
  # Common DB connection (via PgBouncer)
  pg_host  = azurerm_postgresql_flexible_server.main.fqdn
  pg_user  = "waooaw_admin"
}

# 1. Constitutional Engine (gRPC :5002) — internal only, no external ingress
resource "azurerm_container_app" "constitutional_engine" {
  name                         = "ca-ce-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Multiple"   # Required for Blue-Green (C-067)
  tags                         = local.tags

  template {
    min_replicas = var.ce_min_replicas
    max_replicas = var.ce_max_replicas

    container {
      name   = "constitutional-engine"
      image  = "${local.image_base}/constitutional-engine:${local.tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "DB_CONNECTION_STRING"
        value = "Host=${local.pg_host};Port=5432;Database=waooaw;Username=${local.pg_user};Password=${var.postgres_admin_password};SSL Mode=Require"
      }
      env {
        name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
        value = "https://${azurerm_application_insights.main.connection_string}"
      }
      env {
        name  = "ASPNETCORE_ENVIRONMENT"
        value = local.env == "prod" ? "Production" : "Development"
      }
    }
  }

  secret {
    name  = "ghcr-token"
    value = var.ghcr_token
  }

  registry {
    server               = var.ghcr_server
    username             = var.ghcr_username
    password_secret_name = "ghcr-token"
  }

  ingress {
    external_enabled = false
    target_port      = 5002
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
    transport = "http2"   # gRPC requires HTTP/2
  }
}

# 2. Business Platform (REST :5001) — external ingress (customer API + admin)
resource "azurerm_container_app" "business_platform" {
  name                         = "ca-bp-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Multiple"
  tags                         = local.tags

  template {
    min_replicas = var.default_min_replicas
    max_replicas = var.default_max_replicas

    container {
      name   = "business-platform"
      image  = "${local.image_base}/business-platform:${local.tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "CE_GRPC_ENDPOINT"
        value = "https://${azurerm_container_app.constitutional_engine.ingress[0].fqdn}:443"
      }
      env {
        name  = "DB_CONNECTION_STRING"
        value = "Host=${local.pg_host};Port=5432;Database=waooaw;Username=${local.pg_user};Password=${var.postgres_admin_password};SSL Mode=Require"
      }
      env {
        name  = "KEYCLOAK_AUTHORITY"
        value = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}/realms/waooaw"
      }
      env {
        name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
        value = azurerm_application_insights.main.connection_string
      }
    }
  }

  secret {
    name  = "ghcr-token"
    value = var.ghcr_token
  }

  registry {
    server               = var.ghcr_server
    username             = var.ghcr_username
    password_secret_name = "ghcr-token"
  }

  ingress {
    external_enabled = true
    target_port      = 5001
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_container_app.constitutional_engine]
}

# 3. Professional Runtime (REST + WebSocket :5003) — external (Emergency Stop WebSocket)
resource "azurerm_container_app" "professional_runtime" {
  name                         = "ca-pr-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Multiple"
  tags                         = local.tags

  template {
    min_replicas = var.ce_min_replicas  # Same min as CE — trading hours cron rule
    max_replicas = var.default_max_replicas

    container {
      name   = "professional-runtime"
      image  = "${local.image_base}/professional-runtime:${local.tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "CE_GRPC_ENDPOINT"
        value = "https://${azurerm_container_app.constitutional_engine.ingress[0].fqdn}:443"
      }
      env {
        name  = "BP_API_ENDPOINT"
        value = "https://${azurerm_container_app.business_platform.ingress[0].fqdn}"
      }
      env {
        name  = "DB_URL"
        value = "postgresql://${local.pg_user}:${var.postgres_admin_password}@${local.pg_host}:5432/waooaw"
      }
      env {
        name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
        value = azurerm_application_insights.main.connection_string
      }
    }
  }

  secret {
    name  = "ghcr-token"
    value = var.ghcr_token
  }

  registry {
    server               = var.ghcr_server
    username             = var.ghcr_username
    password_secret_name = "ghcr-token"
  }

  ingress {
    external_enabled = true
    target_port      = 5003
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [
    azurerm_container_app.constitutional_engine,
    azurerm_container_app.business_platform
  ]
}

# 4. AI Runtime (REST :5004) — internal only; called by Professional Runtime
resource "azurerm_container_app" "ai_runtime" {
  name                         = "ca-air-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Multiple"
  tags                         = local.tags

  template {
    min_replicas = var.default_min_replicas
    max_replicas = var.default_max_replicas

    container {
      name   = "ai-runtime"
      image  = "${local.image_base}/ai-runtime:${local.tag}"
      cpu    = 1.0          # AI inference needs more CPU than other services
      memory = "2Gi"

      env {
        name  = "CE_GRPC_ENDPOINT"
        value = "https://${azurerm_container_app.constitutional_engine.ingress[0].fqdn}:443"
      }
      env {
        name  = "DB_URL"
        value = "postgresql://${local.pg_user}:${var.postgres_admin_password}@${local.pg_host}:5432/waooaw"
      }
      # ── LLM Provider config (ADR-029 — read from Key Vault at runtime) ──────
      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = "https://waooaw-ai.openai.azure.com/"  # UAE North fallback (ADR-027 O-10)
      }
      env {
        name  = "OLLAMA_BASE_URL"
        value = "http://ca-ollama-${local.prefix}"     # LOCAL tier LLM (ADR-027 O-07)
      }
      env {
        name  = "OLLAMA_INDIC_MODEL"
        value = "ai4bharat/indic-bert"                 # LOCAL Indian language tasks (ADR-029)
      }
      env {
        name        = "GOOGLE_VERTEX_PROJECT_ID"
        secret_name = "google-vertex-project-id"       # Key Vault — FA-021 required
      }
      env {
        name        = "GOOGLE_VERTEX_SA_KEY"
        secret_name = "google-vertex-sa-key"           # Key Vault — FA-021 required (sensitive)
      }
      env {
        name  = "GOOGLE_VERTEX_REGION"
        value = "asia-south1"                          # Mumbai — DPDPA primary (ADR-029)
      }
      env {
        name        = "SARVAM_API_KEY"
        secret_name = "sarvam-api-key"                 # Key Vault — FA-022 required
      }
      env {
        name        = "STEWARD_FRONTIER_MODEL"
        secret_name = "steward-frontier-model"         # gemini-2.5-pro (ADR-028+ADR-029)
      }
      env {
        name        = "MID_TIER_MODEL_PRIMARY"
        secret_name = "mid-tier-model-primary"         # gemini-2.0-flash (ADR-029)
      }
      env {
        name        = "MID_TIER_MODEL_AGRI"
        secret_name = "mid-tier-model-agri"            # sarvam-saaras-1.0 (C-042 override)
      }
      env {
        name  = "OTEL_EXPORTER_OTLP_ENDPOINT"
        value = azurerm_application_insights.main.connection_string
      }
    }
  }

  secret {
    name  = "ghcr-token"
    value = var.ghcr_token
  }

  registry {
    server               = var.ghcr_server
    username             = var.ghcr_username
    password_secret_name = "ghcr-token"
  }

  ingress {
    external_enabled = false
    target_port      = 5004
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_container_app.constitutional_engine]
}

# 5. Web (Next.js PWA :3000) — external
resource "azurerm_container_app" "web" {
  name                         = "ca-web-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Multiple"
  tags                         = local.tags

  template {
    min_replicas = var.default_min_replicas
    max_replicas = var.default_max_replicas

    container {
      name   = "web"
      image  = "${local.image_base}/web:${local.tag}"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "NEXT_PUBLIC_API_BASE"
        value = "https://${azurerm_container_app.business_platform.ingress[0].fqdn}"
      }
      env {
        name  = "NEXT_PUBLIC_KEYCLOAK_URL"
        value = "https://${azurerm_container_app.keycloak.ingress[0].fqdn}"
      }
      env {
        name  = "NODE_ENV"
        value = local.env == "prod" ? "production" : "development"
      }
    }
  }

  secret {
    name  = "ghcr-token"
    value = var.ghcr_token
  }

  registry {
    server               = var.ghcr_server
    username             = var.ghcr_username
    password_secret_name = "ghcr-token"
  }

  ingress {
    external_enabled = true
    target_port      = 3000
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_container_app.business_platform]
}

# 6. Keycloak (Identity broker — ADR-008)
resource "azurerm_container_app" "keycloak" {
  name                         = "ca-keycloak-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"   # Keycloak has its own cluster mode; single revision for now
  tags                         = local.tags

  template {
    min_replicas = 1    # Keycloak must not cold-start on auth requests
    max_replicas = 3

    container {
      name   = "keycloak"
      image  = "quay.io/keycloak/keycloak:25.0.6"
      cpu    = 1.0
      memory = "2Gi"

      command = ["/opt/keycloak/bin/kc.sh", "start", "--import-realm"]

      env {
        name  = "KC_DB"
        value = "postgres"
      }
      env {
        name  = "KC_DB_URL"
        value = "jdbc:postgresql://${local.pg_host}:5432/waooaw"
      }
      env {
        name  = "KC_DB_USERNAME"
        value = local.pg_user
      }
      env {
        name  = "KC_DB_PASSWORD"
        value = var.postgres_admin_password
      }
      env {
        name  = "KEYCLOAK_ADMIN"
        value = "admin"
      }
      env {
        name  = "KEYCLOAK_ADMIN_PASSWORD"
        value = var.keycloak_admin_password
      }
      env {
        name  = "KC_PROXY"
        value = "edge"   # Behind Container Apps ingress
      }
      env {
        name  = "KC_HOSTNAME_STRICT"
        value = "false"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8080
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_postgresql_flexible_server.main]
}

# 7. Temporal Server (workflow engine — ADR-015)
resource "azurerm_container_app" "temporal" {
  name                         = "ca-temporal-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = 1    # Temporal must not cold-start — active workflows would be lost
    max_replicas = 3

    container {
      name   = "temporal"
      image  = "temporalio/auto-setup:1.24"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "DB"
        value = "postgresql"
      }
      env {
        name  = "DB_PORT"
        value = "5432"
      }
      env {
        name  = "POSTGRES_SEEDS"
        value = local.pg_host
      }
      env {
        name  = "POSTGRES_USER"
        value = local.pg_user
      }
      env {
        name  = "POSTGRES_PWD"
        value = var.postgres_admin_password
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = 7233
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
    transport = "http2"   # Temporal uses gRPC over HTTP/2
  }

  depends_on = [azurerm_postgresql_flexible_server.main]
}

# 8. Ollama (LOCAL tier LLM — ADR-027 O-07)
resource "azurerm_container_app" "ollama" {
  name                         = "ca-ollama-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = 0    # Scale to zero — LOCAL tier inference is not latency-sensitive
    max_replicas = 2

    container {
      name   = "ollama"
      image  = "ollama/ollama:latest"
      cpu    = 2.0      # CPU inference needs more resources
      memory = "4Gi"
    }
  }

  ingress {
    external_enabled = false
    target_port      = 11434
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

# 9. PgBouncer (connection pooling — ADR-027 O-05)
resource "azurerm_container_app" "pgbouncer" {
  name                         = "ca-pgbouncer-${local.prefix}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"
  tags                         = local.tags

  template {
    min_replicas = 1    # PgBouncer must be always available — it's the DB gateway
    max_replicas = 3

    container {
      name   = "pgbouncer"
      image  = "pgbouncer/pgbouncer:1.22"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "DATABASES_HOST"
        value = local.pg_host
      }
      env {
        name  = "DATABASES_PORT"
        value = "5432"
      }
      env {
        name  = "DATABASES_DBNAME"
        value = "waooaw"
      }
      env {
        name  = "PGBOUNCER_POOL_MODE"
        value = "transaction"
      }
      env {
        name  = "PGBOUNCER_MAX_CLIENT_CONN"
        value = "200"
      }
      env {
        name  = "PGBOUNCER_DEFAULT_POOL_SIZE"
        value = "25"
      }
      env {
        name  = "PGBOUNCER_AUTH_USER"
        value = local.pg_user
      }
      env {
        name  = "PGBOUNCER_AUTH_PASSWORD"
        value = var.postgres_admin_password
      }
    }
  }

  ingress {
    external_enabled = false
    target_port      = 5432
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  depends_on = [azurerm_postgresql_flexible_server.main]
}
