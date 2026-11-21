variable "image_digests" {
  type = map(string)
}

variable "dma_admission_content_digest" {
  type = string
}

variable "key_vault_secret_uris" {
  type = map(string)
}

variable "key_vault_secret_resource_ids" {
  type = map(string)
}

variable "database_secret_uris" {
  type = map(string)
}

variable "database_secret_resource_ids" {
  type = map(string)
}

variable "application_activation_enabled" {
  type    = bool
  default = true
}

variable "dependency_activation_enabled" {
  type    = bool
  default = false
}

variable "ghcr_packages_public" {
  type        = bool
  description = "Administrator attestation that all exact-seven GHCR packages allow anonymous digest pulls."
  default     = false
}

variable "lease_purpose" {
  type = string
}

variable "manifest_digest" {
  type = string
}

variable "owner_principal_id" {
  type = string
}

variable "lease_issued_at" {
  type = string
}

variable "lease_expires_at" {
  type = string
}

variable "lease_state" {
  type = string
}

variable "lease_revoked_at" {
  type    = string
  default = null
}

variable "cost_centre" {
  type = string
}

variable "evidence_digest" {
  type = string
}

variable "tfstate_resource_group" {
  type = string
}

variable "tfstate_storage_account" {
  type = string
}

variable "tfstate_container" {
  type = string
}

variable "image_registry_server" {
  type        = string
  description = "Environment ACR mirror login server; empty pulls release images from GHCR (WC-127)."
  default     = ""
}

variable "image_pull_identity_id" {
  type        = string
  description = "AcrPull user-assigned identity used with image_registry_server."
  default     = ""
}

variable "feature_settings" {
  description = "Per-environment non-secret feature switches from workload-configuration.json; the module validates the closed set and defaults every switch off."
  type        = any
  default     = {}
}

variable "platform_access" {
  description = "Founder identities from workload-configuration.json; the Business Platform re-asserts them at every start."
  type        = any
  default     = {}
}
