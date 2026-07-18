# Terraform — WAOOAW Platform Azure Infrastructure
# Constitutional basis: ADR-010 (Azure-first, portable at app layer)
#                       ADR-013 (CI/CD — Terraform applied by GitHub Actions)
#                       ADR-014 (Secret Management — Key Vault)
#                       ADR-027 (Cost Optimization — Consumption plan, scale to zero)
#                       C-067 (Cost-Constrained Deployment — ₹10k/env ceiling)

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.52"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Remote state — Azure Storage Account (one per subscription, all envs)
  # Bucket created once manually before first terraform init
  backend "azurerm" {
    resource_group_name  = "rg-waooaw-tfstate"
    storage_account_name = "stwaooawtfstate"   # globally unique; adjust if taken
    container_name       = "tfstate"
    key                  = "env.terraform.tfstate"  # overridden per environment
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy          = false  # Protect Key Vault from accidental deletion
      recover_soft_deleted_key_vaults       = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = true   # Safety: never auto-delete RG with resources
    }
  }

  # Authentication via Service Principal (GitHub Actions) or Azure CLI (local)
  # Set ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_SUBSCRIPTION_ID, ARM_TENANT_ID
  # OR use az login (local dev)
}

provider "azuread" {}
provider "random" {}

#   providers.tf          — AzureRM + backend config
#   variables.tf          — All input variables
#   main.tf               — Root module (calls child modules)
#   outputs.tf            — Useful outputs for CI/CD
#   modules/
#     networking/         — VNet + subnets (prod only; dev uses managed networking)
#     observability/      — Log Analytics + Application Insights (OTel)
#     secrets/            — Azure Key Vault
#     database/           — PostgreSQL Flexible Server + PgBouncer
#     identity/           — Keycloak Container App
#     container-env/      — Container Apps Environment + all 9 apps
#   environments/
#     dev/                — Dev environment (Burstable PostgreSQL, minimal replicas)
#     qa/                 — QA (same as dev, separate resource group)
#     demo/               — Demo (same as qa)
#     uat/                — UAT (closer to prod sizing)
#     prod/               — Production (Standard PostgreSQL, 2 min replicas for CE/PR)
#
# Apply:
#   cd infrastructure/terraform/environments/dev
#   terraform init
#   terraform plan -var-file=terraform.tfvars
#   terraform apply -var-file=terraform.tfvars
#
# Prerequisites: Azure CLI authenticated (az login); GHCR token in Key Vault
# IB Gate: Requires IB-009 Founder authorization before terraform apply to cloud environments
