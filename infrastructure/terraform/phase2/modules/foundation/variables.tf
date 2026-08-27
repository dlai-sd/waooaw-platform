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
    condition     = can(regex("^/subscriptions/[0-9a-f-]+/resourceGroups/waooaw-platform-rg/providers/Microsoft.Storage/storageAccounts/waooawp3tfstate2ed118$", var.tfstate_storage_account_id))
    error_message = "Phase 3 state access is restricted to the authorized protected storage account."
  }
}

variable "runner_resource_group_name" {
  type = string
  validation {
    condition     = can(regex("^waooaw-(demo|uat|prod)-runner-rg$", var.runner_resource_group_name))
    error_message = "Runner resource group must be environment-scoped."
  }
}

variable "external_environment" {
  type        = bool
  description = "Expose the Container Apps environment load balancer. Authorized only for bounded Demo review."
  default     = false
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