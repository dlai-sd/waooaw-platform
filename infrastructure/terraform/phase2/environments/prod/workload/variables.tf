variable "image_digests" {
  type = map(string)
}

variable "key_vault_secret_uris" {
  type = map(string)
}

variable "key_vault_secret_resource_ids" {
  type = map(string)
}

variable "founder_ipv4_cidr" {
  type = string
}

variable "ghcr_packages_public" {
  type        = bool
  description = "Administrator attestation that all exact-six GHCR packages allow anonymous digest pulls."
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