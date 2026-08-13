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
  minimum_replicas = {
    "constitutional-engine" = var.ce_min_replicas
    "professional-runtime"  = var.pr_min_replicas
    "business-platform"     = 0
    "ai-runtime"            = 0
    "web"                   = 0
    "billing-engine"        = 0
  }
}

resource "azurerm_container_app" "member" {
  for_each = local.release_members

  name                         = "ca-${var.environment}-${each.key}"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Multiple"

  identity {
    type         = "UserAssigned"
    identity_ids = [var.runtime_identity_id]
  }

  secret {
    name                = "runtime-reference"
    identity            = var.runtime_identity_client_id
    key_vault_secret_id = var.key_vault_secret_ids[each.key]
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
        name        = "RUNTIME_CONFIGURATION"
        secret_name = "runtime-reference"
      }
    }
  }

  ingress {
    external_enabled = local.public_ingress[each.key]
    target_port      = local.target_ports[each.key]

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  lifecycle {
    precondition {
      condition     = setequals(toset(keys(var.image_digests)), local.release_members)
      error_message = "Release membership must be exactly CE, BP, PR, AIR, Web, and Billing."
    }
  }
}