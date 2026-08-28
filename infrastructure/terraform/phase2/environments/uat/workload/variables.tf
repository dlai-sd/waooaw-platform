variable "image_digests" {
  type = map(string)
}

variable "key_vault_secret_uris" {
  type = map(string)
}

variable "key_vault_secret_resource_ids" {
  type = map(string)
}

variable "ghcr_packages_public" {
  type        = bool
  description = "Administrator attestation that all exact-six GHCR packages allow anonymous digest pulls."
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