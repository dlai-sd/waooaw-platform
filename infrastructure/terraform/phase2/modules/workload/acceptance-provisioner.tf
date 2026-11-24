variable "acceptance_provisioner_enabled" {
  type        = bool
  default     = false
  description = "WC-167: import the Founder-approved acceptance provisioning client, role and group into the Demo realm. The client secret is read from the acceptance vault."

  validation {
    condition     = !var.acceptance_provisioner_enabled || var.environment == "demo"
    error_message = "WC-167 authorizes the acceptance provisioning client in Demo only."
  }
}

variable "acceptance_key_vault_id" {
  type        = string
  default     = null
  description = "Resource id of the acceptance vault that holds the provisioning client secret."

  validation {
    condition     = !var.acceptance_provisioner_enabled || var.acceptance_key_vault_id != null
    error_message = "The acceptance provisioning client needs the acceptance vault resource id."
  }
}

variable "acceptance_key_vault_uri" {
  type        = string
  default     = null
  description = "Vault URI of the acceptance vault that holds the provisioning client secret."

  validation {
    condition     = !var.acceptance_provisioner_enabled || var.acceptance_key_vault_uri != null
    error_message = "The acceptance provisioning client needs the acceptance vault URI."
  }
}

locals {
  acceptance_provisioner_secret_name = "acceptance-keycloak-provisioner-client-secret"
  # The authored fragment is the single source of the client, role, group and service account.
  acceptance_provisioner_fragment = var.acceptance_provisioner_enabled ? jsondecode(file("${path.module}/../../../../keycloak/acceptance-provisioner.realm-fragment.json")) : null
  acceptance_provisioner_secret = var.acceptance_provisioner_enabled ? {
    acceptance-provisioner-secret = {
      env_name    = "ACCEPTANCE_PROVISIONER_CLIENT_SECRET"
      resource_id = "${var.acceptance_key_vault_id}/secrets/${local.acceptance_provisioner_secret_name}"
      uri         = "${trimsuffix(var.acceptance_key_vault_uri, "/")}/secrets/${local.acceptance_provisioner_secret_name}"
    }
  } : {}
  acceptance_provisioner_clients     = var.acceptance_provisioner_enabled ? local.acceptance_provisioner_fragment.clients : []
  acceptance_provisioner_realm_roles = var.acceptance_provisioner_enabled ? local.acceptance_provisioner_fragment.realm.roles.realm : []
  acceptance_provisioner_users = var.acceptance_provisioner_enabled ? [
    for account in local.acceptance_provisioner_fragment.serviceAccountUsers : {
      username               = account.username
      enabled                = account.enabled
      serviceAccountClientId = account.serviceAccountClientId
      clientRoles            = account.clientRoles
      realmRoles             = account.realmRoles
    }
  ] : []
  # Empty when the flag is off, so UAT, production and an un-flipped Demo realm are byte-for-byte unchanged.
  acceptance_provisioner_realm_settings = jsondecode(var.acceptance_provisioner_enabled ? jsonencode({
    adminEventsEnabled        = local.acceptance_provisioner_fragment.realm.adminEventsEnabled
    adminEventsDetailsEnabled = local.acceptance_provisioner_fragment.realm.adminEventsDetailsEnabled
    groups                    = local.acceptance_provisioner_fragment.realm.groups
  }) : "{}")
}
