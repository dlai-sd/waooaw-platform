terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
  backend "azurerm" {
    key = "goal006/prod/foundation.tfstate"
  }
}

provider "azurerm" {
  use_oidc = true
  use_cli  = false
  features {}
}

module "foundation" {
  source                 = "../../../modules/foundation"
  environment            = "prod"
  location               = "centralindia"
  repository_id          = "dlai-sd/waooaw-platform"
  repository_environment = "prod"
}