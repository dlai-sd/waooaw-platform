terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.6.3"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "= 2.2.0"
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

provider "azurerm" {
  alias                           = "deployment"
  client_id                       = var.deployment_client_id
  use_oidc                        = true
  use_cli                         = false
  resource_provider_registrations = "none"
  features {}
}

module "foundation" {
  source = "../../../modules/foundation"
  providers = {
    azurerm            = azurerm
    azurerm.deployment = azurerm.deployment
  }
  environment                               = "uat"
  location                                  = "centralindia"
  repository_id                             = "dlai-sd/waooaw-platform"
  repository_environment                    = "uat"
  runner_resource_group_name                = var.runner_resource_group_name
  runner_private_endpoints_subnet_id        = var.runner_private_endpoints_subnet_id
  tfstate_storage_account_id                = var.tfstate_storage_account_id
  external_environment                      = true
  persistent_state_enabled                  = true
  postgresql_password_auth_enabled          = var.postgresql_password_auth_enabled
  database_bootstrap_admin_enabled          = var.database_bootstrap_admin_enabled
  database_provisioner_vault_access_enabled = var.database_provisioner_vault_access_enabled
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

output "runner_key_vault_dns_record_id" {
  value = module.foundation.runner_key_vault_dns_record_id
}

output "runner_key_vault_private_endpoint_id" {
  value = module.foundation.runner_key_vault_private_endpoint_id
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

output "auth_abuse_redis_url" {
  value     = module.foundation.auth_abuse_redis_url
  sensitive = true
}

output "postgresql_server_id" {
  value = module.foundation.postgresql_server_id
}

output "postgresql_server_fqdn" {
  value = module.foundation.postgresql_server_fqdn
}

output "database_bootstrap_client_id" {
  value = module.foundation.database_bootstrap_client_id
}

output "database_bootstrap_identity_id" {
  value = module.foundation.database_bootstrap_identity_id
}

output "database_provisioner_client_id" {
  value = module.foundation.database_provisioner_client_id
}

output "database_provisioner_identity_id" {
  value = module.foundation.database_provisioner_identity_id
}