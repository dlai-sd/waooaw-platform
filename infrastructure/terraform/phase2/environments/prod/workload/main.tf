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
  use_oidc                        = true
  use_cli                         = false
  resource_provider_registrations = "none"
  features {}
}

data "terraform_remote_state" "foundation" {
  backend = "azurerm"
  config = {
    resource_group_name  = var.tfstate_resource_group
    storage_account_name = var.tfstate_storage_account
    container_name       = var.tfstate_container
    key                  = "goal006/prod/foundation.tfstate"
    use_oidc             = true
    use_azuread_auth     = true
  }
}

module "workload" {
  source = "../../../modules/workload"

  environment                              = "prod"
  location                                 = data.terraform_remote_state.foundation.outputs.location
  resource_group_name                      = data.terraform_remote_state.foundation.outputs.resource_group_name
  container_app_environment_id             = data.terraform_remote_state.foundation.outputs.container_app_environment_id
  container_app_environment_default_domain = data.terraform_remote_state.foundation.outputs.container_app_environment_default_domain
  verification_principal_id                = data.terraform_remote_state.foundation.outputs.verification_principal_id
  image_digests                            = var.image_digests
  key_vault_secret_uris                    = var.key_vault_secret_uris
  key_vault_secret_resource_ids            = var.key_vault_secret_resource_ids
  ghcr_packages_public                     = var.ghcr_packages_public
  ce_min_replicas                          = var.ce_min_replicas
  pr_min_replicas                          = var.pr_min_replicas
}