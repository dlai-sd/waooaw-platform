variable "google_login_enabled" {
  type        = bool
  default     = false
  description = "Recreate the approved Demo Google broker from environment Key Vault references."

  validation {
    condition     = !var.google_login_enabled || var.environment == "demo"
    error_message = "WC-085 authorizes reproducible Google login in Demo only."
  }
}

locals {
  google_secret_uris = var.google_login_enabled ? {
    google-client-id     = "${trimsuffix(var.key_vault_secret_uris["web"], "/web")}/google-client-id"
    google-client-secret = "${trimsuffix(var.key_vault_secret_uris["web"], "/web")}/google-client-secret"
  } : {}
  google_secret_resource_ids = var.google_login_enabled ? {
    google-client-id     = "${trimsuffix(var.key_vault_secret_resource_ids["web"], "/web")}/google-client-id"
    google-client-secret = "${trimsuffix(var.key_vault_secret_resource_ids["web"], "/web")}/google-client-secret"
  } : {}
  identity_reader_secret_uris = var.google_login_enabled || var.facebook_login_enabled ? {
    bp-identity-reader-client-secret = "${trimsuffix(var.key_vault_secret_uris["business-platform"], "/business-platform")}/bp-identity-reader-client-secret"
  } : {}
  identity_reader_secret_resource_ids = var.google_login_enabled || var.facebook_login_enabled ? {
    bp-identity-reader-client-secret = "${trimsuffix(var.key_vault_secret_resource_ids["business-platform"], "/business-platform")}/bp-identity-reader-client-secret"
  } : {}
  google_identity_providers = var.google_login_enabled ? [{
    alias                     = "google"
    providerId                = "google"
    enabled                   = true
    trustEmail                = false
    storeToken                = false
    addReadTokenRoleOnCreate  = false
    firstBrokerLoginFlowAlias = "first broker login"
    config = {
      clientId     = "$${GOOGLE_CLIENT_ID}"
      clientSecret = "$${GOOGLE_CLIENT_SECRET}"
      defaultScope = "openid email profile"
      syncMode     = "IMPORT"
    }
  }] : []
}

resource "azurerm_user_assigned_identity" "google_broker" {
  count               = var.workload_enabled && var.google_login_enabled ? 1 : 0
  name                = "id-${var.environment}-keycloak-google"
  location            = var.location
  resource_group_name = var.resource_group_name

  lifecycle {
    precondition {
      condition     = local.service_urls.identity_edge == "https://ca-demo-identity-edge.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io"
      error_message = "Demo Google login requires the identity origin already registered in Google Console; foundation domain replacement requires renewed callback approval."
    }
    precondition {
      condition = (
        can(regex("^https://kv-waooaw-demo[.]vault[.]azure[.]net/secrets/web$", var.key_vault_secret_uris["web"])) &&
        endswith(lower(var.key_vault_secret_resource_ids["web"]), "/resourcegroups/waooaw-demo-rg/providers/microsoft.keyvault/vaults/kv-waooaw-demo/secrets/web")
      )
      error_message = "Google references must use the reviewed Demo vault and web secret naming contract."
    }
  }
}

resource "azurerm_role_assignment" "google_broker_secret" {
  for_each             = var.workload_enabled ? local.google_secret_resource_ids : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.google_broker[0].principal_id
}

resource "azurerm_role_assignment" "identity_reader_secret" {
  for_each             = var.workload_enabled ? local.identity_reader_secret_resource_ids : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id
}