variable "facebook_login_enabled" {
  type        = bool
  default     = false
  description = "Create the Founder-authorized Demo Facebook broker from environment Key Vault references."

  validation {
    condition     = !var.facebook_login_enabled || var.environment == "demo"
    error_message = "WC-090 authorizes reproducible Facebook login in Demo only."
  }
}

locals {
  facebook_secret_uris = var.facebook_login_enabled ? {
    meta-login-client-id     = "${trimsuffix(var.key_vault_secret_uris["web"], "/web")}/meta-login-client-id"
    meta-login-client-secret = "${trimsuffix(var.key_vault_secret_uris["web"], "/web")}/meta-login-client-secret"
  } : {}
  facebook_secret_resource_ids = var.facebook_login_enabled ? {
    meta-login-client-id     = "${trimsuffix(var.key_vault_secret_resource_ids["web"], "/web")}/meta-login-client-id"
    meta-login-client-secret = "${trimsuffix(var.key_vault_secret_resource_ids["web"], "/web")}/meta-login-client-secret"
  } : {}
  facebook_identity_providers = var.facebook_login_enabled ? [{
    alias                     = "facebook"
    providerId                = "facebook"
    enabled                   = true
    trustEmail                = false
    storeToken                = false
    addReadTokenRoleOnCreate  = false
    firstBrokerLoginFlowAlias = "first broker login"
    config = {
      clientId     = "$${META_LOGIN_CLIENT_ID}"
      clientSecret = "$${META_LOGIN_CLIENT_SECRET}"
      defaultScope = "email public_profile"
      syncMode     = "IMPORT"
    }
  }] : []
}

resource "azurerm_user_assigned_identity" "facebook_broker" {
  count               = var.workload_enabled && var.facebook_login_enabled ? 1 : 0
  name                = "id-${var.environment}-keycloak-facebook"
  location            = var.location
  resource_group_name = var.resource_group_name

  lifecycle {
    precondition {
      condition     = local.service_urls.identity_edge == "https://ca-demo-identity-edge.wonderfulmoss-740b2b2d.centralindia.azurecontainerapps.io"
      error_message = "Demo Facebook login requires the reviewed identity origin registered in Meta; foundation domain replacement requires renewed callback approval."
    }
    precondition {
      condition = (
        can(regex("^https://kv-waooaw-demo[.]vault[.]azure[.]net/secrets/web$", var.key_vault_secret_uris["web"])) &&
        endswith(lower(var.key_vault_secret_resource_ids["web"]), "/resourcegroups/waooaw-demo-rg/providers/microsoft.keyvault/vaults/kv-waooaw-demo/secrets/web")
      )
      error_message = "Facebook references must use the reviewed Demo vault and web secret naming contract."
    }
  }
}

resource "azurerm_role_assignment" "facebook_broker_secret" {
  for_each             = var.workload_enabled ? local.facebook_secret_resource_ids : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.facebook_broker[0].principal_id
}