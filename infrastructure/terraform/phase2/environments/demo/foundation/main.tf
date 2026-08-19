terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
  backend "azurerm" {
    key = "goal006/demo/foundation.tfstate"
  }
}

provider "azurerm" {
  use_oidc = true
  use_cli  = false
  features {}
}

module "foundation" {
  source                     = "../../../modules/foundation"
  environment                = "demo"
  location                   = "centralindia"
  repository_id              = "dlai-sd/waooaw-platform"
  repository_environment     = "demo"
  tfstate_storage_account_id = var.tfstate_storage_account_id
}