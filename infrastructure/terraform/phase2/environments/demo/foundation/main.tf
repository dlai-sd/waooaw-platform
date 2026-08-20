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
  use_oidc                        = true
  use_cli                         = false
  resource_provider_registrations = "none"
  features {}
}

module "foundation" {
  source                     = "../../../modules/foundation"
  environment                = "demo"
  location                   = "centralindia"
  repository_id              = "dlai-sd/waooaw-platform"
  repository_environment     = "demo"
  tfstate_storage_account_id = var.tfstate_storage_account_id
  external_environment       = true
}

output "resource_group_name" {
  value = module.foundation.resource_group_name
}

output "container_app_environment_id" {
  value = module.foundation.container_app_environment_id
}

output "container_app_environment_name" {
  value = module.foundation.container_app_environment_name
}

output "container_app_environment_default_domain" {
  value = module.foundation.container_app_environment_default_domain
}

output "key_vault_id" {
  value = module.foundation.key_vault_id
}

output "key_vault_name" {
  value = module.foundation.key_vault_name
}

output "key_vault_uri" {
  value = module.foundation.key_vault_uri
}

output "location" {
  value = module.foundation.location
}

output "deployment_client_id" {
  value = module.foundation.deployment_client_id
}

output "deployment_identity_id" {
  value = module.foundation.deployment_identity_id
}

output "verification_client_id" {
  value = module.foundation.verification_client_id
}

output "verification_principal_id" {
  value = module.foundation.verification_principal_id
}