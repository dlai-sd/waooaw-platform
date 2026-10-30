terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
  backend "azurerm" {
    key = "goal006/uat/workload.tfstate"
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
    key                  = "goal006/uat/foundation.tfstate"
    use_oidc             = true
    use_azuread_auth     = true
  }
}

module "lease" {
  source = "../../../modules/lifecycle"

  environment             = "uat"
  purpose                 = var.lease_purpose
  manifest_digest         = var.manifest_digest
  owner_principal_id      = var.owner_principal_id
  issued_at               = var.lease_issued_at
  expires_at              = var.lease_expires_at
  lifecycle_state         = var.lease_state
  revoked_at              = var.lease_revoked_at
  cost_centre             = var.cost_centre
  evidence_digest         = var.evidence_digest
  protected_foundation_id = data.terraform_remote_state.foundation.outputs.container_app_environment_id
}

module "workload" {
  source = "../../../modules/workload"

  application_activation_enabled           = var.application_activation_enabled
  dependency_activation_enabled            = var.dependency_activation_enabled
  environment                              = "uat"
  location                                 = data.terraform_remote_state.foundation.outputs.location
  resource_group_name                      = data.terraform_remote_state.foundation.outputs.resource_group_name
  container_app_environment_id             = data.terraform_remote_state.foundation.outputs.container_app_environment_id
  container_app_environment_default_domain = data.terraform_remote_state.foundation.outputs.container_app_environment_default_domain
  verification_principal_id                = data.terraform_remote_state.foundation.outputs.verification_principal_id
  dma_admission_content_digest             = var.dma_admission_content_digest
  image_digests                            = var.image_digests
  key_vault_secret_uris                    = var.key_vault_secret_uris
  key_vault_secret_resource_ids            = var.key_vault_secret_resource_ids
  database_secret_uris                     = var.database_secret_uris
  database_secret_resource_ids             = var.database_secret_resource_ids
  persistent_state_enabled                 = true
  postgresql_server_fqdn                   = data.terraform_remote_state.foundation.outputs.postgresql_server_fqdn
  ghcr_packages_public                     = var.ghcr_packages_public
  image_registry_server                    = var.image_registry_server
  image_pull_identity_id                   = var.image_pull_identity_id
  ce_min_replicas                          = 0
  pr_min_replicas                          = 0
  workload_enabled                         = module.lease.workload_enabled
  web_session_mode                         = "disabled"
}

output "lease_reconciliation_inputs" {
  sensitive = true
  value = {
    image_digests                 = var.image_digests
    dma_admission_content_digest  = var.dma_admission_content_digest
    key_vault_secret_uris         = var.key_vault_secret_uris
    key_vault_secret_resource_ids = var.key_vault_secret_resource_ids
    ghcr_packages_public          = var.ghcr_packages_public
    image_registry_server         = var.image_registry_server
    image_pull_identity_id        = var.image_pull_identity_id
    lease_purpose                 = var.lease_purpose
    manifest_digest               = var.manifest_digest
    owner_principal_id            = var.owner_principal_id
    lease_issued_at               = var.lease_issued_at
    lease_expires_at              = var.lease_expires_at
    lease_state                   = var.lease_state
    lease_revoked_at              = var.lease_revoked_at
    cost_centre                   = var.cost_centre
    evidence_digest               = var.evidence_digest
  }
}

output "web_url" {
  value = module.workload.web_url
}