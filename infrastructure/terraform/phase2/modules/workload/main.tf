terraform {
  required_version = "= 1.9.8"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
}

locals {
  release_members = toset([
    "constitutional-engine",
    "business-platform",
    "professional-runtime",
    "ai-runtime",
    "web",
    "billing-engine",
  ])
  active_members = var.workload_enabled ? local.release_members : toset([])
  public_ingress = {
    "constitutional-engine" = false
    "ai-runtime"            = false
    "billing-engine"        = false
    "web"                   = true
    "business-platform"     = true
    "professional-runtime"  = true
  }
  target_ports = {
    "constitutional-engine" = 5002
    "business-platform"     = 5001
    "professional-runtime"  = 5003
    "ai-runtime"            = 5004
    "web"                   = 3000
    "billing-engine"        = 8140
  }
  ingress_transports = {
    "constitutional-engine" = "http2"
    "business-platform"     = "auto"
    "professional-runtime"  = "auto"
    "ai-runtime"            = "auto"
    "web"                   = "auto"
    "billing-engine"        = "auto"
  }
  service_urls = {
    constitutional_engine = "http://ca-${var.environment}-constitutional-engine"
    business_platform     = "http://ca-${var.environment}-business-platform"
    professional_runtime  = "http://ca-${var.environment}-professional-runtime"
    ai_runtime            = "http://ca-${var.environment}-ai-runtime"
    billing_engine        = "http://ca-${var.environment}-billing-engine"
    keycloak              = "https://ca-${var.environment}-keycloak.${var.container_app_environment_default_domain}"
    web                   = "https://ca-${var.environment}-web.${var.container_app_environment_default_domain}"
  }
  verification_urls = {
    business_platform = "http://ca-${var.environment}-business-platform"
    keycloak          = "http://ca-${var.environment}-keycloak"
    web               = "http://ca-${var.environment}-web"
  }
  runtime_environment = {
    "constitutional-engine" = {
      ASPNETCORE_URLS                      = "http://+:5002"
      ConnectionStrings__DefaultConnection = "Host=localhost;Port=5432;Database=waooaw;Username=postgres"
    }
    "business-platform" = {
      ASPNETCORE_ENVIRONMENT               = "Production"
      ASPNETCORE_URLS                      = "http://+:5001"
      ConnectionStrings__DefaultConnection = "Host=localhost;Port=5432;Database=waooaw;Username=postgres"
      ConstitutionalEngine__Address        = local.service_urls.constitutional_engine
      Keycloak__Audience                   = "waooaw-platform"
      Keycloak__Authority                  = "${local.service_urls.keycloak}/realms/waooaw"
      Keycloak__RequireHttpsMetadata       = "true"
    }
    "professional-runtime" = {
      AIR_TRANSCRIPTION_BASE_URL    = local.service_urls.ai_runtime
      CONSTITUTIONAL_ENGINE_ADDRESS = "ca-${var.environment}-constitutional-engine:80"
      KEYCLOAK_AUDIENCE             = "waooaw-platform"
      KEYCLOAK_ISSUER               = "${local.service_urls.keycloak}/realms/waooaw"
      KEYCLOAK_JWKS_URL             = "${local.service_urls.keycloak}/realms/waooaw/protocol/openid-connect/certs"
    }
    "ai-runtime" = {
      BP_BASE_URL                   = local.service_urls.business_platform
      CONSTITUTIONAL_ENGINE_ADDRESS = "ca-${var.environment}-constitutional-engine:80"
      PLATFORM_PHASE                = "IMPLEMENTATION"
    }
    "web" = {
      BUSINESS_PLATFORM_URL = local.service_urls.business_platform
      KEYCLOAK_CLIENT_ID    = "waooaw-web"
      KEYCLOAK_ISSUER       = "${local.service_urls.keycloak}/realms/waooaw"
      NEXTAUTH_URL          = local.service_urls.web
      NODE_ENV              = "production"
    }
    "billing-engine" = {
      BILLING_CONTRACT_ID            = "goal006-demo"
      BILLING_DECISION_SPACE_VERSION = "1"
      CONSTITUTIONAL_ENGINE_ADDRESS  = "ca-${var.environment}-constitutional-engine:80"
      DATABASE_URL                   = "postgresql+asyncpg://postgres@localhost:5432/waooaw"
      RAZORPAY_KEY_ID                = "demo-disabled"
      RAZORPAY_KEY_SECRET            = "demo-disabled"
      RAZORPAY_WEBHOOK_SECRET        = "demo-disabled"
      REDIS_URL                      = "redis://localhost:6379/0"
      WBE_INTERNAL_BASE_URL          = local.service_urls.billing_engine
    }
  }
  credential_environment = {
    "constitutional-engine" = "CE_RUNTIME_CREDENTIAL"
    "business-platform"     = "BP_SERVICE_JWT_SECRET"
    "professional-runtime"  = "PR_SERVICE_JWT_SECRET"
    "ai-runtime"            = "PR_SERVICE_JWT_SECRET"
    "web"                   = "KEYCLOAK_CLIENT_SECRET"
    "billing-engine"        = "OPS_AUTH_TOKEN"
  }
  credential_member = {
    "constitutional-engine" = "constitutional-engine"
    "business-platform"     = "business-platform"
    "professional-runtime"  = "professional-runtime"
    "ai-runtime"            = "professional-runtime"
    "web"                   = "web"
    "billing-engine"        = "billing-engine"
  }
  minimum_replicas = {
    "constitutional-engine" = var.ce_min_replicas
    "professional-runtime"  = var.pr_min_replicas
    "business-platform"     = 0
    "ai-runtime"            = 0
    "web"                   = 0
    "billing-engine"        = 0
  }
}

resource "azurerm_user_assigned_identity" "member" {
  for_each = local.active_members

  name                = "id-${var.environment}-${each.key}"
  location            = var.location
  resource_group_name = var.resource_group_name
}

resource "azurerm_role_assignment" "member_secret" {
  for_each = local.active_members

  scope                = var.key_vault_secret_resource_ids[local.credential_member[each.key]]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member[each.key].principal_id
}

resource "azurerm_role_assignment" "professional_runtime_bp_secret" {
  count = var.workload_enabled ? 1 : 0

  scope                = var.key_vault_secret_resource_ids["business-platform"]
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["professional-runtime"].principal_id
}

resource "azurerm_container_app" "member" {
  for_each = local.active_members

  name                         = "ca-${var.environment}-${each.key}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Multiple"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.member[each.key].id]
  }

  secret {
    name                = "runtime-reference"
    identity            = azurerm_user_assigned_identity.member[each.key].id
    key_vault_secret_id = var.key_vault_secret_uris[local.credential_member[each.key]]
  }

  dynamic "secret" {
    for_each = each.key == "professional-runtime" ? [1] : []
    content {
      name                = "bp-service-credential"
      identity            = azurerm_user_assigned_identity.member[each.key].id
      key_vault_secret_id = var.key_vault_secret_uris["business-platform"]
    }
  }

  template {
    min_replicas = local.minimum_replicas[each.key]
    max_replicas = var.max_replicas

    container {
      name   = each.key
      image  = var.image_digests[each.key]
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = local.credential_environment[each.key]
        secret_name = "runtime-reference"
      }

      dynamic "env" {
        for_each = each.key == "professional-runtime" ? [1] : []
        content {
          name        = "BP_SERVICE_JWT_SECRET"
          secret_name = "bp-service-credential"
        }
      }

      dynamic "env" {
        for_each = each.key == "web" ? [1] : []
        content {
          name        = "NEXTAUTH_SECRET"
          secret_name = "runtime-reference"
        }
      }

      dynamic "env" {
        for_each = local.runtime_environment[each.key]
        content {
          name  = env.key
          value = env.value
        }
      }
    }

    dynamic "container" {
      for_each = contains(["constitutional-engine", "business-platform", "billing-engine"], each.key) ? [1] : []
      content {
        name   = "postgres"
        image  = "postgres@sha256:cf78e76683b9ca8c5733cbbdce6c9262b45b6767934dd0a95e671f9a0fc20685"
        cpu    = 0.25
        memory = "0.5Gi"

        env {
          name  = "POSTGRES_DB"
          value = "waooaw"
        }
        env {
          name  = "POSTGRES_HOST_AUTH_METHOD"
          value = "trust"
        }
      }
    }

    dynamic "container" {
      for_each = each.key == "billing-engine" ? [1] : []
      content {
        name   = "redis"
        image  = "redis@sha256:e7723ff73d963f5cc6d9c4643ea3d989527a402a319239054e9472a7fb9219a2"
        cpu    = 0.25
        memory = "0.5Gi"
      }
    }
  }

  ingress {
    external_enabled = local.public_ingress[each.key]
    target_port      = local.target_ports[each.key]
    transport        = local.ingress_transports[each.key]

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

    dynamic "ip_security_restriction" {
      for_each = local.public_ingress[each.key] ? [var.founder_ipv4_cidr] : []
      content {
        name             = "founder-review"
        ip_address_range = ip_security_restriction.value
        action           = "Allow"
        description      = "Founder-only Demo review"
      }
    }
  }

  lifecycle {
    precondition {
      condition     = toset(keys(var.image_digests)) == local.release_members
      error_message = "Release membership must be exactly CE, BP, PR, AIR, Web, and Billing."
    }

    precondition {
      condition     = !var.workload_enabled || var.ghcr_packages_public
      error_message = "Enabled workloads require administrator verification that all exact-six GHCR packages allow anonymous digest pulls."
    }
  }
}

resource "azurerm_container_app" "keycloak" {
  count = var.workload_enabled ? 1 : 0

  name                         = "ca-${var.environment}-keycloak"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.member["web"].id]
  }

  secret {
    name                = "keycloak-credential"
    identity            = azurerm_user_assigned_identity.member["web"].id
    key_vault_secret_id = var.key_vault_secret_uris["web"]
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name    = "keycloak"
      image   = "quay.io/keycloak/keycloak@sha256:82c5b7a110456dbd42b86ea572e728878549954cc8bd03cd65410d75328095d2"
      cpu     = 1
      memory  = "2Gi"
      command = ["/bin/sh", "-c"]
      args = [<<-EOT
        set -eu
        /opt/keycloak/bin/kc.sh start-dev --http-enabled=true --hostname-strict=false &
        server_pid=$!
        until /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user "$KC_BOOTSTRAP_ADMIN_USERNAME" --password "$KC_BOOTSTRAP_ADMIN_PASSWORD"; do sleep 2; done
        /opt/keycloak/bin/kcadm.sh get realms/waooaw >/dev/null 2>&1 || /opt/keycloak/bin/kcadm.sh create realms -s realm=waooaw -s enabled=true
        client_id=$(/opt/keycloak/bin/kcadm.sh get clients -r waooaw -q clientId=waooaw-web --fields id --format csv --noquotes 2>/dev/null || true)
        test -n "$client_id" || /opt/keycloak/bin/kcadm.sh create clients -r waooaw -s clientId=waooaw-web -s enabled=true -s publicClient=false -s standardFlowEnabled=true -s 'redirectUris=["${local.service_urls.web}/*"]' -s 'webOrigins=["${local.service_urls.web}"]' -s secret="$KEYCLOAK_CLIENT_SECRET"
        wait "$server_pid"
      EOT
      ]

      env {
        name  = "KC_BOOTSTRAP_ADMIN_USERNAME"
        value = "demo-admin"
      }
      env {
        name        = "KC_BOOTSTRAP_ADMIN_PASSWORD"
        secret_name = "keycloak-credential"
      }
      env {
        name        = "KEYCLOAK_CLIENT_SECRET"
        secret_name = "keycloak-credential"
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

    ip_security_restriction {
      name             = "founder-review"
      ip_address_range = var.founder_ipv4_cidr
      action           = "Allow"
      description      = "Founder-only Demo identity"
    }
  }

  depends_on = [azurerm_role_assignment.member_secret]
}

resource "azurerm_container_app_job" "verification" {
  count = var.workload_enabled && var.verification_principal_id != null ? 1 : 0

  name                         = "job-${var.environment}-deployment-verification"
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_retry_limit          = 1
  replica_timeout_in_seconds   = 300

  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }

  template {
    container {
      name    = "http-probes"
      image   = "mcr.microsoft.com/azure-cli@sha256:4faeb3c955086c3842d4f8cf0ff1d900ce3a1c68c6e6c6430c5e8a3cb882c5aa"
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args = [<<-EOT
        set -eu
        probe() {
          name="$1"
          url="$2"
          for attempt in 1 2 3 4 5 6 7 8 9 10; do
            http_code=$(curl --silent --show-error --max-time 15 --output /dev/null --write-out '%%{http_code}' "$url") && curl_exit=0 || curl_exit=$?
            if [ "$curl_exit" -eq 0 ] && [ "$http_code" -ge 200 ] && [ "$http_code" -lt 400 ]; then
              echo "probe_result name=$name status=succeeded http_code=$http_code attempt=$attempt url=$url"
              return 0
            fi
            echo "probe_attempt name=$name status=failed curl_exit=$curl_exit http_code=$http_code attempt=$attempt url=$url" >&2
            sleep 6
          done
          echo "probe_result name=$name status=failed url=$url" >&2
          return 1
        }
        probe web "${local.verification_urls.web}/"
        probe business-platform "${local.verification_urls.business_platform}/health/ready"
        probe keycloak "${local.verification_urls.keycloak}/realms/waooaw/.well-known/openid-configuration"
      EOT
      ]
    }

    container {
      name    = "constitutional-health"
      image   = var.image_digests["constitutional-engine"]
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["/bin/sh", "-c"]
      args    = ["for attempt in 1 2 3 4 5 6 7 8 9 10; do grpc_health_probe -addr=ca-${var.environment}-constitutional-engine:80 -connect-timeout=10s -rpc-timeout=10s && exit 0; sleep 6; done; exit 1"]
    }
  }

  depends_on = [azurerm_container_app.member, azurerm_container_app.keycloak]
}

resource "azurerm_role_assignment" "verification_job_operator" {
  count = length(azurerm_container_app_job.verification)

  scope                = azurerm_container_app_job.verification[0].id
  role_definition_name = "Container Apps Jobs Operator"
  principal_id         = var.verification_principal_id
}

output "web_url" {
  value = try("https://${azurerm_container_app.member["web"].latest_revision_fqdn}", null)
}