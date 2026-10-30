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

variable "ghcr_packages_public" {
  type        = bool
  description = "Administrator attestation that all exact-seven GHCR packages allow anonymous digest pulls."
  default     = false
}

variable "ce_min_replicas" {
  type = number
  validation {
    condition     = var.ce_min_replicas > 0
    error_message = "Production CE minimum requires an accepted positive owner value."
  }
}

variable "pr_min_replicas" {
  type = number
  validation {
    condition     = var.pr_min_replicas > 0
    error_message = "Production PR minimum requires an accepted positive owner value."
  }
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
