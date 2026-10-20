variable "environment" {
  type = string
  validation {
    condition     = contains(["demo", "uat", "prod"], var.environment)
    error_message = "Environment must be demo, uat, or prod."
  }
}

variable "location" {
  type = string
}

variable "repository_environment" {
  type = string
}

variable "repository_id" {
  type = string
}

variable "tfstate_storage_account_id" {
  type = string
  validation {
    condition = (
      var.environment == "uat"
      ? can(regex("^/subscriptions/[0-9a-f-]+/resourceGroups/waooaw-platform-rg/providers/Microsoft.Storage/storageAccounts/waooawuatstate2ed118$", var.tfstate_storage_account_id))
      : can(regex("^/subscriptions/[0-9a-f-]+/resourceGroups/waooaw-platform-rg/providers/Microsoft.Storage/storageAccounts/waooawp3tfstate2ed118$", var.tfstate_storage_account_id))
    )
    error_message = "State access must use the exact environment-owned protected storage account."
  }
}

variable "runner_resource_group_name" {
  type = string
  validation {
    condition     = can(regex("^waooaw-(demo|uat|prod)-runner-rg$", var.runner_resource_group_name))
    error_message = "Runner resource group must be environment-scoped."
  }
}

variable "runner_private_endpoints_subnet_id" {
  type = string
  validation {
    condition     = can(regex("/resourceGroups/waooaw-(demo|uat|prod)-runner-rg/providers/Microsoft.Network/virtualNetworks/goal006-(demo|uat|prod)-runner-vnet/subnets/private-endpoints$", var.runner_private_endpoints_subnet_id))
    error_message = "Runner private endpoints subnet must be environment-scoped."
  }
}

variable "auth_redis_ha_enabled" {
  type        = bool
  default     = false
  description = "Create the separately authorized private Production HA authentication limiter dependency."

  validation {
    condition     = !var.auth_redis_ha_enabled || var.environment == "prod"
    error_message = "Managed HA authentication Redis is reserved for Production."
  }
}

variable "external_environment" {
  type        = bool
  description = "Expose the Container Apps environment load balancer for an explicitly authorized lower environment."
  default     = false
}

variable "persistent_state_enabled" {
  type        = bool
  description = "Create the protected Demo/UAT PostgreSQL persistent-state foundation."
  default     = false

  validation {
    condition     = !var.persistent_state_enabled || contains(["demo", "uat"], var.environment)
    error_message = "Persistent PostgreSQL is authorized only for Demo and UAT."
  }
}

variable "postgresql_password_auth_enabled" {
  type        = bool
  description = "Enable non-admin password compatibility only after the WC-124 bootstrap transaction passes."
  default     = false

  validation {
    condition     = !var.postgresql_password_auth_enabled || var.persistent_state_enabled
    error_message = "PostgreSQL password compatibility requires the persistent-state foundation."
  }
}

variable "database_bootstrap_admin_enabled" {
  type        = bool
  description = "Keep the Entra bootstrap administrator only through the WC-124 bootstrap transaction."
  default     = true

  validation {
    condition     = !var.database_bootstrap_admin_enabled || var.persistent_state_enabled
    error_message = "The database bootstrap administrator requires the persistent-state foundation."
  }
}

variable "database_provisioner_vault_access_enabled" {
  type        = bool
  description = "Retain provisioner Key Vault access until WC-124 handoff and revocation evidence passes."
  default     = true

  validation {
    condition     = !var.database_provisioner_vault_access_enabled || var.persistent_state_enabled
    error_message = "Database provisioner Key Vault access requires the persistent-state foundation."
  }
}

variable "log_analytics_workspace_name" {
  type        = string
  description = "Existing workspace name to adopt when one was provisioned before Terraform ownership."
  default     = null
  nullable    = true
  validation {
    condition     = var.log_analytics_workspace_name == null || can(regex("^law-waooaw-(demo|uat|prod)(-validation)?$", var.log_analytics_workspace_name))
    error_message = "Log Analytics workspace name must belong to a WAOOAW deployment environment."
  }
}