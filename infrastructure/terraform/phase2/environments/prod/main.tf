terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
  backend "azurerm" {
    key = "goal006/prod/terraform.tfstate"
  }
}

provider "azurerm" {
  use_oidc = true
  use_cli  = false
  features {}
}

module "environment" {
  source               = "../../modules/environment"
  environment          = "prod"
  location             = "centralindia"
  repository_id        = "dlai-sd/waooaw-platform"
  image_digests        = var.image_digests
  key_vault_secret_ids = var.key_vault_secret_ids
  ce_min_replicas      = var.ce_min_replicas
  pr_min_replicas      = var.pr_min_replicas
}