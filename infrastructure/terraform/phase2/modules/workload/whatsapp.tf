variable "whatsapp_provider" {
  description = "Demo provider registration configuration only; never callback, dispatch or activation authority."
  type = object({
    callback_host        = string
    secret_versions      = map(string)
    authority_reference  = string
    verification_enabled = bool
    release_digest       = string
    configuration_digest = string
    catalog_digest       = string
  })
  default  = null
  nullable = true

  validation {
    condition = var.whatsapp_provider == null ? true : (
      var.environment == "demo" &&
      can(regex("^whatsapp-demo[.]([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+[a-z]{2,63}$", var.whatsapp_provider.callback_host)) &&
      can(regex("^[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}$", var.whatsapp_provider.authority_reference)) &&
      toset(keys(var.whatsapp_provider.secret_versions)) == toset([
        "whatsapp-provider-binding", "whatsapp-verify-token",
        "whatsapp-app-secret", "whatsapp-outbound-authority"
      ]) &&
      alltrue([for version in values(var.whatsapp_provider.secret_versions) : can(regex("^[a-f0-9]{32}$", version))]) &&
      alltrue([for digest in [
        var.whatsapp_provider.release_digest, var.whatsapp_provider.configuration_digest,
        var.whatsapp_provider.catalog_digest
      ] : can(regex("^sha256:[a-f0-9]{64}$", digest))]) &&
      endswith(var.image_digests["business-platform"], "@${var.whatsapp_provider.release_digest}")
    )
    error_message = "WhatsApp registration requires a Demo-only dedicated hostname, authority reference, four exact secret versions and immutable matching image/configuration/catalog digests."
  }
}

locals {
  whatsapp_provider_runtime = var.whatsapp_provider == null ? {} : {
    WhatsAppProvider__Enabled                    = "true"
    WhatsAppProvider__Environment                = "demo"
    WhatsAppProvider__VaultHost                  = "kv-waooaw-demo.vault.azure.net"
    WhatsAppProvider__BindingVersion             = var.whatsapp_provider.secret_versions["whatsapp-provider-binding"]
    WhatsAppProvider__VerifyTokenVersion         = var.whatsapp_provider.secret_versions["whatsapp-verify-token"]
    WhatsAppProvider__AppSecretVersion           = var.whatsapp_provider.secret_versions["whatsapp-app-secret"]
    WhatsAppProvider__OutboundAuthorityVersion   = var.whatsapp_provider.secret_versions["whatsapp-outbound-authority"]
    WhatsApp__CallbackHost                       = var.whatsapp_provider.callback_host
    WhatsApp__VerificationEnabled                = tostring(var.whatsapp_provider.verification_enabled)
    WhatsApp__CallbackAcceptanceEnabled          = "false"
    WhatsApp__DispatchEnabled                    = "false"
    Wc120Conversation__CallbackAcceptanceEnabled = "false"
    Wc120Conversation__DispatchEnabled           = "false"
    WhatsAppCapability__Configured               = "true"
    WhatsAppCapability__ProviderAvailable        = "false"
    WhatsAppCapability__Environment              = "demo"
    WhatsAppCapability__ReleaseDigest            = var.whatsapp_provider.release_digest
    WhatsAppCapability__ConfigurationDigest      = var.whatsapp_provider.configuration_digest
    WhatsAppCapability__CatalogDigest            = var.whatsapp_provider.catalog_digest
  }
  whatsapp_provider_secret_scopes = var.whatsapp_provider == null ? {} : {
    for name in keys(var.whatsapp_provider.secret_versions) :
    name => "${trimsuffix(var.key_vault_secret_resource_ids["business-platform"], "/business-platform")}/${name}"
  }
}

resource "azurerm_role_assignment" "whatsapp_provider_secret" {
  for_each             = var.workload_enabled ? local.whatsapp_provider_secret_scopes : {}
  scope                = each.value
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.member["business-platform"].principal_id
}

resource "azurerm_container_app_custom_domain" "whatsapp_provider" {
  count            = var.workload_enabled && var.whatsapp_provider != null ? 1 : 0
  name             = var.whatsapp_provider.callback_host
  container_app_id = azurerm_container_app.member["business-platform"].id

  lifecycle {
    ignore_changes = [certificate_binding_type, container_app_environment_certificate_id]
  }
}
