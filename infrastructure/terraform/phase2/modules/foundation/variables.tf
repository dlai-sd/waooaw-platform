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

variable "external_environment" {
  type        = bool
  description = "Expose the Container Apps environment load balancer. Authorized only for bounded Demo review."
  default     = false
}