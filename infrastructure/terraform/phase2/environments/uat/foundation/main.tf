terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
  backend "azurerm" {
    key = "goal006/uat/foundation.tfstate"
  }
}

provider "azurerm" {
  use_oidc                        = true
  use_cli                         = false
  resource_provider_registrations = "none"
  features {}
}

module "foundation" {
  source                     = "../../../modules/foundation"
  environment                = "uat"
  location                   = "centralindia"
  repository_id              = "dlai-sd/waooaw-platform"
  repository_environment     = "uat"
  tfstate_storage_account_id = var.tfstate_storage_account_id
}

output "deployment_client_id" {
  value = module.foundation.deployment_client_id
}

output "verification_client_id" {
  value = module.foundation.verification_client_id
}