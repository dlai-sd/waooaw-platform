variable "whatsapp_monitoring" {
  description = "Reviewed bounded operational alert tuple; null preserves the existing no-monitoring default."
  type = object({
    workspace_id         = string
    action_group_id      = string
    approval_reference   = string
    query_digest         = string
    activation_digest    = string
    release_digest       = string
    configuration_digest = string
    starts_at            = string
    expires_at           = string
  })
  default  = null
  nullable = true
}

variable "image_digests" {
  type = map(string)
}

variable "dma_admission_content_digest" {
  type = string
}

variable "auth_preview_origin" {
  type        = string
  default     = "https://probable-waffle-vpqg67gg59jhrrr-3100.app.github.dev"
  description = "Exact Founder Codespaces origin accepted by the Demo-only public PKCE preview client."
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
variable "whatsapp_provider" {
  description = "Optional protected Demo registration-only configuration; provider effects remain disabled."
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
}
