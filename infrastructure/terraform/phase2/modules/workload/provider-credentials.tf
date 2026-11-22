# Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R007
# Business Platform writes, and the AI runtime reads, Founder-entered provider keys only in Key Vault secrets named
# "provider-*". The grant sits at vault scope but is limited by an ABAC role-assignment condition on the secret name,
# so no other secret in the vault is reachable through it. Terraform never holds a provider key value.
# Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R011
# Business Platform also writes and reads customer connection tokens under "customer-connection-*"; the AI runtime
# reader condition keeps the "provider-*" prefix only, so it can never reach a customer token.

locals {
  provider_secret_prefix = "provider-"
  provider_secret_actions = {
    getSecret    = { action = "Microsoft.KeyVault/vaults/secrets/getSecret/action", source = "Resource" }
    readMetadata = { action = "Microsoft.KeyVault/vaults/secrets/readMetadata/action", source = "Resource" }
    setSecret    = { action = "Microsoft.KeyVault/vaults/secrets/setSecret/action", source = "Request" }
    update       = { action = "Microsoft.KeyVault/vaults/secrets/update/action", source = "Resource" }
    delete       = { action = "Microsoft.KeyVault/vaults/secrets/delete", source = "Resource" }
    backup       = { action = "Microsoft.KeyVault/vaults/secrets/backup/action", source = "Resource" }
    restore      = { action = "Microsoft.KeyVault/vaults/secrets/restore/action", source = "Request" }
    recover      = { action = "Microsoft.KeyVault/vaults/secrets/recover/action", source = "Resource" }
    purge        = { action = "Microsoft.KeyVault/vaults/secrets/purge/action", source = "Resource" }
  }
  # Every data action of the role is listed, because a condition only constrains the actions it names.
  provider_secret_condition_actions = {
    writer = ["getSecret", "readMetadata", "setSecret", "update", "delete", "backup", "restore", "recover", "purge"]
    reader = ["getSecret", "readMetadata"]
  }
  # WC-149: customer account tokens live only in "customer-connection-*" secrets that Business Platform alone may reach.
  customer_connection_secret_prefix = "customer-connection-"
  provider_secret_condition_prefixes = {
    writer = [local.provider_secret_prefix, local.customer_connection_secret_prefix]
    reader = [local.provider_secret_prefix]
  }
  provider_secret_conditions = {
    for role, names in local.provider_secret_condition_actions : role => "(${join(" AND ", [
      for name in names :
      "((!(ActionMatches{'${local.provider_secret_actions[name].action}'})) OR (${join(" OR ", [
        for prefix in local.provider_secret_condition_prefixes[role] :
        "(@${local.provider_secret_actions[name].source}[Microsoft.KeyVault/vaults/secrets:name] StringStartsWith '${prefix}')"
      ])}))"
    ])})"
  }
  provider_credentials_identity_env = {
    "business-platform" = "ProviderCredentials__ManagedIdentityClientId"
    "ai-runtime"        = "PROVIDER_CREDENTIALS_MANAGED_IDENTITY_CLIENT_ID"
  }
  provider_credentials_runtime = {
    "business-platform" = {
      ProviderCredentials__VaultUrl = local.wid_vault_url
      # WC-149: customer account connections (Meta) reuse the vault and identity under the customer-connection- prefix.
      ProviderConnections__VaultUrl                = local.wid_vault_url
      ProviderConnections__ManagedIdentityClientId = azurerm_user_assigned_identity.member["business-platform"].client_id
      ProviderConnections__Meta__GraphVersion      = "v21.0"
      ProviderConnections__Meta__RedirectUri       = "${local.service_urls.web}/api/provider-connections/meta/callback"
    }
    "ai-runtime" = {
      PROVIDER_CREDENTIALS_VAULT_URL = local.wid_vault_url
    }
  }
}

resource "azurerm_role_assignment" "provider_credential_writer" {
  count = var.workload_enabled ? 1 : 0

  scope                = local.wid_vault_id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id
  description          = "WC-148/WC-149: Business Platform writes provider-* and customer-connection-* secrets only."
  condition_version    = "2.0"
  condition            = local.provider_secret_conditions["writer"]
}

resource "azurerm_role_assignment" "provider_credential_reader" {
  count = var.workload_enabled ? 1 : 0

  scope                = local.wid_vault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["ai-runtime"].principal_id
  description          = "WC-148: AI runtime reads provider-* secrets only."
  condition_version    = "2.0"
  condition            = local.provider_secret_conditions["reader"]
}
