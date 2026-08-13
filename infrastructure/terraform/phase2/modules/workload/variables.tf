variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "container_app_environment_id" {
  type = string
}

variable "image_digests" {
  type = map(string)
  validation {
    condition = (
      length(var.image_digests) == 6 &&
      alltrue([for image in values(var.image_digests) : can(regex("@sha256:[0-9a-f]{64}$", image))])
    )
    error_message = "Exactly six immutable sha256 image references are required."
  }
}

variable "key_vault_secret_ids" {
  type = map(string)
  validation {
    condition     = setequals(toset(keys(var.key_vault_secret_ids)), toset(keys(var.image_digests)))
    error_message = "Every release member requires one Key Vault secret reference."
  }
}

variable "ce_min_replicas" {
  type    = number
  default = 0
}

variable "pr_min_replicas" {
  type    = number
  default = 0
}

variable "max_replicas" {
  type    = number
  default = 10
  validation {
    condition     = var.max_replicas > 0 && var.max_replicas <= 10
    error_message = "ADR-027 limits each offline workload contract to 10 replicas."
  }
}

variable "workload_enabled" {
  type        = bool
  description = "False after lease expiry or revocation; removes disposable workload resources from desired state."
  default     = true
}