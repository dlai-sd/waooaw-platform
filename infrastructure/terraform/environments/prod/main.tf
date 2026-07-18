# Prod environment — WAOOAW Platform
# ADR-027: Standard PostgreSQL (D2ds_v5), 2 min replicas for CE + PR (trading hours)
# C-067: cost ceiling ₹15,000/month for prod

terraform {
  required_version = ">= 1.7.0"
  backend "azurerm" {
    key = "prod.terraform.tfstate"
  }
}

provider "azurerm" {
  features {}
}

module "waooaw_prod" {
  source = "../../modules/core"

  environment  = "prod"
  location     = "centralindia"

  # PostgreSQL — Standard General Purpose for prod (predictable load, HA)
  postgres_sku_name      = "GP_Standard_D2ds_v5"
  postgres_storage_mb    = 65536           # 64 GB for prod
  postgres_version       = "16"
  postgres_admin_password = var.postgres_admin_password

  keycloak_admin_password = var.keycloak_admin_password

  ghcr_server   = "ghcr.io"
  ghcr_username = var.ghcr_username
  ghcr_token    = var.ghcr_token
  image_org     = "dlai-sd"
  image_tag     = "prod"

  # CE + PR: cron-based scale rule handles trading hours min=1 (ADR-027 O-06)
  # Terraform sets the Container App; the cron rule is applied separately via az CLI
  ce_min_replicas      = 1   # Always warm in prod (Constitutional Floor for trading)
  ce_max_replicas      = 20
  default_min_replicas = 0
  default_max_replicas = 20

  log_retention_days = 90   # Longer retention in prod

  tags = {
    platform       = "waooaw"
    environment    = "prod"
    managed_by     = "terraform"
    constitutional = "true"
    cost_ceiling   = "15000-INR-month"   # C-067
  }
}

variable "postgres_admin_password" { type = string; sensitive = true }
variable "keycloak_admin_password" { type = string; sensitive = true }
variable "ghcr_username"           { type = string }
variable "ghcr_token"              { type = string; sensitive = true }

output "prod_web_url"      { value = module.waooaw_prod.web_url }
output "prod_api_url"      { value = module.waooaw_prod.api_url }
output "prod_keycloak_url" { value = module.waooaw_prod.keycloak_url }
