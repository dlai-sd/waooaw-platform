variable "environment" {
  type = string
}

variable "auth_preview_origin" {
  type        = string
  default     = null
  nullable    = true
  description = "Exact Demo-only Codespaces origin for the public PKCE authentication preview client."

  validation {
    condition = var.auth_preview_origin == null || (
      var.environment == "demo" &&
      can(regex("^https://[a-z0-9-]+-[0-9]+[.]app[.]github[.]dev$", var.auth_preview_origin))
    )
    error_message = "Authentication preview origin must be one exact Demo Codespaces HTTPS origin without a path or wildcard."
  }
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

variable "container_app_environment_default_domain" {
  type    = string
  default = "unconfigured.invalid"
}

variable "verification_principal_id" {
  type        = string
  description = "Independent verification identity permitted only to execute the scoped internal probe job."
  default     = null
  nullable    = true
}

variable "image_digests" {
  type = map(string)
  validation {
    condition = (
      length(var.image_digests) == 7 &&
      alltrue([for image in values(var.image_digests) : can(regex("@sha256:[0-9a-f]{64}$", image))])
    )
    error_message = "Exactly seven immutable sha256 image references are required."
  }
}

variable "dma_admission_content_digest" {
  type        = string
  description = "Immutable SHA-256 digest of the admitted DMA Release 1 content."
  validation {
    condition     = can(regex("^sha256:[0-9a-f]{64}$", var.dma_admission_content_digest))
    error_message = "DMA admission content digest must be an immutable sha256 digest."
  }
}

variable "key_vault_secret_uris" {
  type = map(string)
  validation {
    condition = (
      toset(keys(var.key_vault_secret_uris)) == toset(keys(var.image_digests)) &&
      alltrue([for uri in values(var.key_vault_secret_uris) : can(regex("^https://[^/]+[.]vault[.]azure[.]net/secrets/[^/]+$", uri))])
    )
    error_message = "Every release member requires one versionless Key Vault secret URI."
  }
}

variable "key_vault_secret_resource_ids" {
  type = map(string)
  validation {
    condition = (
      toset(keys(var.key_vault_secret_resource_ids)) == toset(keys(var.image_digests)) &&
      alltrue([for id in values(var.key_vault_secret_resource_ids) : can(regex("^/subscriptions/.+/secrets/[^/]+$", id))])
    )
    error_message = "Every release member requires one Key Vault secret RBAC resource ID."
  }
}

variable "founder_ipv4_cidr" {
  type        = string
  description = "Single Founder IPv4 /32 permitted to reach public Demo applications."
  default     = null
  nullable    = true
  validation {
    condition = var.environment != "demo" ? var.founder_ipv4_cidr == null : (
      can(regex("^(?:[0-9]{1,3}[.]){3}[0-9]{1,3}/32$", var.founder_ipv4_cidr)) && var.founder_ipv4_cidr != "0.0.0.0/32"
    )
    error_message = "Founder review access requires one nonzero IPv4 /32."
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

variable "demo_data_generation_id" {
  type        = string
  description = "Immutable identifier for the disposable Demo data generation."
  default     = null
  nullable    = true
  validation {
    condition     = var.environment != "demo" || can(regex("^sha256:[0-9a-f]{64}$", var.demo_data_generation_id))
    error_message = "Demo requires a sha256-bound disposable data generation identifier."
  }
}

variable "demo_fixture_digest" {
  type        = string
  description = "SHA-256 digest of the complete synthetic Demo fixture inputs."
  default     = null
  nullable    = true
  validation {
    condition     = var.environment != "demo" || can(regex("^[0-9a-f]{64}$", var.demo_fixture_digest))
    error_message = "Demo requires an exact synthetic fixture digest."
  }
}

variable "identity_hmac_active_version" {
  type        = string
  description = "Stable version identifier for the active identity HMAC key."
  default     = "v1"
  validation {
    condition     = can(regex("^[A-Za-z0-9_-]+$", var.identity_hmac_active_version))
    error_message = "Identity HMAC active version must be alphanumeric with optional hyphens or underscores."
  }
}

variable "ghcr_packages_public" {
  type        = bool
  description = "Administrator attestation that all exact-seven GHCR packages allow anonymous digest pulls."
  default     = false
}