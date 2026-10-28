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

variable "persistent_state_enabled" {
  type        = bool
  default     = false
  description = "Route Demo/UAT authority traffic through the dedicated PgBouncer dependency."

  validation {
    condition     = !var.persistent_state_enabled || contains(["demo", "uat"], var.environment)
    error_message = "Persistent-state workload routing is authorized only for Demo and UAT."
  }
}

variable "postgresql_server_fqdn" {
  type        = string
  default     = null
  nullable    = true
  description = "Private Flexible Server hostname consumed only by PgBouncer."

  validation {
    condition     = !var.persistent_state_enabled || can(regex("^[a-z0-9-]+[.]postgres[.]database[.]azure[.]com$", var.postgresql_server_fqdn))
    error_message = "Persistent-state workloads require the private Flexible Server FQDN."
  }
}

variable "database_secret_uris" {
  type        = map(string)
  default     = {}
  description = "Distinct immutable-version database credential references by principal."

  validation {
    condition = !var.persistent_state_enabled || (
      toset(keys(var.database_secret_uris)) == toset(var.environment == "demo" ? [
        "constitutional-engine", "business-platform", "billing-engine",
        "billing-migration", "keycloak", "keycloak-migration", "pgbouncer",
        "temporal", "temporal-migration",
        ] : [
        "constitutional-engine", "business-platform", "billing-engine",
        "billing-migration", "keycloak", "keycloak-migration", "pgbouncer",
      ]) &&
      alltrue([for uri in values(var.database_secret_uris) : can(regex("^https://[^/]+[.]vault[.]azure[.]net/secrets/[^/]+/[^/]+$", uri))])
    )
    error_message = "Persistent-state workloads require the exact runtime, migration, and PgBouncer database credential references."
  }
}

variable "application_activation_enabled" {
  type        = bool
  default     = true
  description = "Starts application minimum replicas after runtime dependencies are healthy."
}

variable "dependency_activation_enabled" {
  type        = bool
  default     = false
  description = "Starts runtime dependencies before application revisions are activated."
}

variable "database_secret_resource_ids" {
  type        = map(string)
  default     = {}
  description = "RBAC scopes for the distinct database credential references."

  validation {
    condition = !var.persistent_state_enabled || (
      toset(keys(var.database_secret_resource_ids)) == toset(keys(var.database_secret_uris)) &&
      alltrue([for id in values(var.database_secret_resource_ids) : can(regex("^/subscriptions/.+/secrets/[^/]+$", id))])
    )
    error_message = "Every database credential requires one Key Vault secret RBAC scope."
  }
}

variable "web_custom_hostname" {
  type        = string
  default     = null
  nullable    = true
  description = "Optional public custom hostname for the customer web application."

  validation {
    condition     = var.web_custom_hostname == null || can(regex("^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])$", var.web_custom_hostname))
    error_message = "Web custom hostname must be a lowercase DNS hostname without a scheme or path."
  }
}

variable "identity_custom_hostname" {
  type        = string
  default     = null
  nullable    = true
  description = "Optional public custom hostname for the identity edge."

  validation {
    condition     = var.identity_custom_hostname == null || can(regex("^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])$", var.identity_custom_hostname))
    error_message = "Identity custom hostname must be a lowercase DNS hostname without a scheme or path."
  }
}

variable "api_custom_hostname" {
  type        = string
  default     = null
  nullable    = true
  description = "Optional public custom hostname for the Business Platform API."

  validation {
    condition     = var.api_custom_hostname == null || can(regex("^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])$", var.api_custom_hostname))
    error_message = "API custom hostname must be a lowercase DNS hostname without a scheme or path."
  }
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

variable "ce_min_replicas" {
  type    = number
  default = 0
}

variable "pr_min_replicas" {
  type    = number
  default = 0
}

variable "bp_min_replicas" {
  type    = number
  default = 0
  validation {
    condition     = var.bp_min_replicas >= 0 && var.bp_min_replicas <= 1
    error_message = "Business Platform minimum replicas must be zero or one."
  }
}

variable "web_min_replicas" {
  type    = number
  default = 0
  validation {
    condition     = var.web_min_replicas >= 0 && var.web_min_replicas <= 1
    error_message = "Web minimum replicas must be zero or one."
  }
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

variable "web_session_mode" {
  type        = string
  description = "Server-side session migration state. Enabling shadow or enforced requires the complete WC-123 runtime contract."

  validation {
    condition     = contains(["disabled", "shadow", "enforced"], var.web_session_mode)
    error_message = "Web session mode must be disabled, shadow, or enforced."
  }
}

variable "auth_abuse_redis_url" {
  type        = string
  default     = null
  nullable    = true
  sensitive   = true
  description = "Environment-local authentication limiter endpoint. Production receives the private HA foundation output."

  validation {
    condition = (
      var.environment != "prod" ||
      !var.workload_enabled ||
      (var.auth_abuse_redis_url != null && can(regex("^rediss://[^/]+:6380/0$", var.auth_abuse_redis_url)))
    )
    error_message = "An active Production workload requires the private TLS HA Redis foundation endpoint."
  }
}

variable "web_session_config_digest" {
  type        = string
  default     = null
  nullable    = true
  description = "Accepted WC-123 Web session configuration digest."

  validation {
    condition     = var.web_session_mode == "disabled" || can(regex("^sha256:[0-9a-f]{64}$", var.web_session_config_digest))
    error_message = "Enabled Web session authority requires an immutable configuration digest."
  }
}

variable "web_session_expected_config_digest" {
  type        = string
  default     = null
  nullable    = true
  description = "Independently accepted WC-123 Web session configuration digest."

  validation {
    condition     = var.web_session_mode == "disabled" || can(regex("^sha256:[0-9a-f]{64}$", var.web_session_expected_config_digest))
    error_message = "Enabled Web session authority requires an independently accepted configuration digest."
  }
}

variable "web_session_telemetry_route_digest" {
  type        = string
  default     = null
  nullable    = true
  description = "Accepted WC-123 telemetry route digest."

  validation {
    condition     = var.web_session_mode == "disabled" || can(regex("^sha256:[0-9a-f]{64}$", var.web_session_telemetry_route_digest))
    error_message = "Enabled Web session authority requires an immutable telemetry route digest."
  }
}

variable "web_session_expected_telemetry_route_digest" {
  type        = string
  default     = null
  nullable    = true
  description = "Independently accepted WC-123 telemetry route digest."

  validation {
    condition     = var.web_session_mode == "disabled" || can(regex("^sha256:[0-9a-f]{64}$", var.web_session_expected_telemetry_route_digest))
    error_message = "Enabled Web session authority requires an independently accepted telemetry route digest."
  }
}

variable "web_session_deploy_version" {
  type        = string
  default     = "wc123-auth-session-v1"
  description = "Schema-compatible WC-123 Web session deploy version."

  validation {
    condition     = can(regex("^wc123-auth-session-v[0-9]+$", var.web_session_deploy_version))
    error_message = "Web session deploy version must use the accepted wc123-auth-session-vN form."
  }
}

variable "web_session_handle_digest_write_version" {
  type        = string
  default     = "v1"
  description = "Active write version for the WC-123 session-handle digest keyring."

  validation {
    condition     = can(regex("^v[1-9][0-9]*$", var.web_session_handle_digest_write_version))
    error_message = "Session-handle digest write version must use the accepted vN form."
  }
}

variable "web_session_protocol_digest_write_version" {
  type        = string
  default     = "v1"
  description = "Active write version for the WC-123 protocol digest keyring."

  validation {
    condition     = can(regex("^v[1-9][0-9]*$", var.web_session_protocol_digest_write_version))
    error_message = "Protocol digest write version must use the accepted vN form."
  }
}

variable "web_session_token_envelope_write_version" {
  type        = string
  default     = "v1"
  description = "Active write version for the WC-123 token-envelope keyring."

  validation {
    condition     = can(regex("^v[1-9][0-9]*$", var.web_session_token_envelope_write_version))
    error_message = "Token-envelope write version must use the accepted vN form."
  }
}