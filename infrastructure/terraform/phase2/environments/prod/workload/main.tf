terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
  backend "azurerm" {
    key = "goal006/prod/workload.tfstate"
  }
}

provider "azurerm" {
  use_oidc = true
  use_cli  = false
  features {}
}

data "terraform_remote_state" "foundation" {
  backend = "azurerm"
  config = {
    key = "goal006/prod/foundation.tfstate"
  }
}

module "workload" {
  source = "../../../modules/workload"

  environment                  = "prod"
  location                     = data.terraform_remote_state.foundation.outputs.location
  resource_group_name          = data.terraform_remote_state.foundation.outputs.resource_group_name
  container_app_environment_id = data.terraform_remote_state.foundation.outputs.container_app_environment_id
  image_digests                = var.image_digests
  key_vault_secret_ids         = var.key_vault_secret_ids
  ce_min_replicas              = var.ce_min_replicas
  pr_min_replicas              = var.pr_min_replicas
}