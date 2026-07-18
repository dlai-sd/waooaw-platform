# Dev environment — WAOOAW Platform
# Constitutional basis: ADR-027 O-08 (Burstable PostgreSQL for dev — saves ₹2-4k/month)
#                       C-067 (cost ceiling ₹10,000/month for dev)
#
# Apply:
#   terraform init -backend-config="key=dev.terraform.tfstate"
#   terraform plan -var-file=terraform.tfvars
#   terraform apply -var-file=terraform.tfvars

terraform {
  required_version = ">= 1.7.0"
  backend "azurerm" {
    key = "dev.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

module "waooaw_dev" {
  source = "../../modules/core"

  environment  = "dev"
  location     = "centralindia"

  # PostgreSQL — Burstable for dev (ADR-027 O-08)
  postgres_sku_name      = "B2ms"
  postgres_storage_mb    = 32768
  postgres_version       = "16"
  postgres_admin_password = var.postgres_admin_password

  # Keycloak
  keycloak_admin_password = var.keycloak_admin_password

  # Container Registry (GHCR)
  ghcr_server   = "ghcr.io"
  ghcr_username = var.ghcr_username
  ghcr_token    = var.ghcr_token
  image_org     = "dlai-sd"
  image_tag     = "dev"   # promote.yaml retags to :dev on merge to main

  # Scaling — all scale to zero in dev (cost saving)
  ce_min_replicas      = 0
  ce_max_replicas      = 5
  default_min_replicas = 0
  default_max_replicas = 5

  log_retention_days = 30

  tags = {
    platform       = "waooaw"
    environment    = "dev"
    managed_by     = "terraform"
    constitutional = "true"
    cost_ceiling   = "10000-INR-month"   # C-067
  }
}

# Variables (values in terraform.tfvars — never committed)
variable "postgres_admin_password" {
  type      = string
  sensitive = true
}

variable "keycloak_admin_password" {
  type      = string
  sensitive = true
}

variable "ghcr_username" {
  type = string
}

variable "ghcr_token" {
  type      = string
  sensitive = true
}

# Outputs
output "dev_web_url"      { value = module.waooaw_dev.web_url }
output "dev_api_url"      { value = module.waooaw_dev.api_url }
output "dev_keycloak_url" { value = module.waooaw_dev.keycloak_url }
