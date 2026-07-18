# All input variables for the WAOOAW platform Terraform module
# Constitutional basis: ADR-014 (no secrets in IaC — sensitive values via Key Vault)
#                       ADR-027 O-08 (Burstable PostgreSQL for dev/qa)

# ─── Environment ──────────────────────────────────────────────────────────────
variable "environment" {
  type        = string
  description = "Environment name: dev | qa | demo | uat | prod"
  validation {
    condition     = contains(["dev", "qa", "demo", "uat", "prod"], var.environment)
    error_message = "Environment must be one of: dev, qa, demo, uat, prod"
  }
}

variable "location" {
  type        = string
  default     = "centralindia"            # Azure India Central — Pune region (ADR-010)
  description = "Azure region. Must be India Central for DPDPA compliance."
}

variable "location_short" {
  type    = string
  default = "in"                          # Used in resource name abbreviations
}

# ─── Container Registry ───────────────────────────────────────────────────────
variable "ghcr_server" {
  type    = string
  default = "ghcr.io"
}

variable "ghcr_username" {
  type        = string
  description = "GitHub username for GHCR authentication (GitHub Actions: github.actor)"
}

variable "ghcr_token" {
  type        = string
  sensitive   = true
  description = "GitHub PAT with read:packages scope for GHCR. Stored in Key Vault."
}

variable "image_tag" {
  type        = string
  default     = "main"
  description = "Image tag to deploy. Overridden by CI/CD with sha-{git-sha} or environment tag."
}

# ─── PostgreSQL ───────────────────────────────────────────────────────────────
variable "postgres_sku_name" {
  type        = string
  description = "PostgreSQL SKU. dev/qa: B2s (Burstable, ADR-027 O-08). prod: D2ds_v5 (Standard)."
  default     = "B2ms"                    # Burstable — override to Standard for prod
}

variable "postgres_storage_mb" {
  type    = number
  default = 32768                         # 32 GB — sufficient for MVI
}

variable "postgres_admin_password" {
  type        = string
  sensitive   = true
  description = "PostgreSQL admin password. Stored in Key Vault. Never in tfvars file."
}

variable "postgres_version" {
  type    = string
  default = "16"
}

# ─── Keycloak ─────────────────────────────────────────────────────────────────
variable "keycloak_admin_password" {
  type        = string
  sensitive   = true
  description = "Keycloak admin console password. Stored in Key Vault."
}

# ─── Container App image references ──────────────────────────────────────────
variable "image_org" {
  type        = string
  default     = "dlai-sd"                 # GitHub org for GHCR image prefix
  description = "GitHub organisation name for ghcr.io/{org}/{service}:{tag}"
}

# ─── Scaling parameters ───────────────────────────────────────────────────────
# ADR-027 O-06: Constitutional Engine + Professional Runtime must have min=1 during trading hours.
# This is a cron-based scaling rule set on the Container App itself (see container-env module).
variable "ce_min_replicas" {
  type    = number
  default = 0                             # dev: scale-to-zero OK; prod: cron rule handles trading hours
}

variable "ce_max_replicas" {
  type    = number
  default = 10
}

variable "default_min_replicas" {
  type    = number
  default = 0                             # All services scale to zero when idle
}

variable "default_max_replicas" {
  type    = number
  default = 10
}

# ─── Monitoring ───────────────────────────────────────────────────────────────
variable "log_retention_days" {
  type    = number
  default = 30                            # dev: 30 days; prod: 90 days
}

# ─── Tags ─────────────────────────────────────────────────────────────────────
variable "tags" {
  type = map(string)
  default = {
    platform        = "waooaw"
    managed_by      = "terraform"
    constitutional  = "true"             # All WAOOAW resources tagged for cost tracking
  }
}
