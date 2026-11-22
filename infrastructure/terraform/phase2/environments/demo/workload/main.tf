terraform {
  required_version = "= 1.9.8"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.14.0"
    }
  }
  backend "azurerm" {
    key = "goal006/demo/workload.tfstate"
  }
}

provider "azurerm" {
  use_oidc                        = true
  use_cli                         = false
  resource_provider_registrations = "none"
  features {}
}

# CB-021 interim: adopt the two Key Vault role assignments created when the trust secrets were first wired by hand.
import {
  to = module.workload.azurerm_role_assignment.workload_trust_secret["workload-identity-manifest"]
  id = "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/workload-identity-manifest/providers/Microsoft.Authorization/roleAssignments/550d833f-d1af-408c-a32e-a237d5dfc115"
}

import {
  to = module.workload.azurerm_role_assignment.workload_trust_secret["workload-identity-bp-delegation-cert"]
  id = "/subscriptions/2ed11839-6a0f-4eaa-bd94-44ca96ff5d84/resourceGroups/waooaw-demo-rg/providers/Microsoft.KeyVault/vaults/kv-waooaw-demo/secrets/workload-identity-bp-delegation-cert/providers/Microsoft.Authorization/roleAssignments/a749a302-4eba-4ba9-acf8-13507202f582"
}

data "terraform_remote_state" "foundation" {
  backend = "azurerm"
  config = {
    resource_group_name  = var.tfstate_resource_group
    storage_account_name = var.tfstate_storage_account
    container_name       = var.tfstate_container
    key                  = "goal006/demo/foundation.tfstate"
    use_oidc             = true
    use_azuread_auth     = true
  }
}

module "lease" {
  source = "../../../modules/lifecycle"

  environment             = "demo"
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
  auth_preview_origin                      = var.auth_preview_origin
  whatsapp_provider                        = var.whatsapp_provider
  whatsapp_monitoring                      = var.whatsapp_monitoring
  whatsapp_monitoring_workspace_id         = try(data.terraform_remote_state.foundation.outputs.log_analytics_workspace_id, "")
  log_analytics_workspace_id               = try(data.terraform_remote_state.foundation.outputs.log_analytics_workspace_id, "")
  workload_identity_alert_action_group_id  = try(var.whatsapp_monitoring.action_group_id, null)
  facebook_login_enabled                   = true
  google_login_enabled                     = true
  environment                              = "demo"
  location                                 = data.terraform_remote_state.foundation.outputs.location
  resource_group_name                      = data.terraform_remote_state.foundation.outputs.resource_group_name
  container_app_environment_id             = data.terraform_remote_state.foundation.outputs.container_app_environment_id
  container_app_environment_default_domain = data.terraform_remote_state.foundation.outputs.container_app_environment_default_domain
  web_custom_hostname                      = "cp.demo.waooaw.com"
  identity_custom_hostname                 = "auth.demo.waooaw.com"
  api_custom_hostname                      = "api.demo.waooaw.com"
  verification_principal_id                = data.terraform_remote_state.foundation.outputs.verification_principal_id
  dma_admission_content_digest             = var.dma_admission_content_digest
  image_digests                            = var.image_digests
  feature_settings                         = var.feature_settings
  platform_access                          = var.platform_access
  key_vault_secret_uris                    = var.key_vault_secret_uris
  key_vault_secret_resource_ids            = var.key_vault_secret_resource_ids
  database_secret_uris                     = var.database_secret_uris
  database_secret_resource_ids             = var.database_secret_resource_ids
  persistent_state_enabled                 = true
  postgresql_server_fqdn                   = data.terraform_remote_state.foundation.outputs.postgresql_server_fqdn
  ghcr_packages_public                     = var.ghcr_packages_public
  image_registry_server                    = var.image_registry_server
  image_pull_identity_id                   = var.image_pull_identity_id
  ce_min_replicas                          = 1
  pr_min_replicas                          = 0
  bp_min_replicas                          = 1
  web_min_replicas                         = 1
  whatsapp_guest_limits                    = { messages_per_guest_per_24_hours = 100, new_sessions_per_day = 100 }
  max_replicas                             = 1
  workload_enabled                         = module.lease.workload_enabled
  web_session_mode                         = "disabled"
  web_diagnostic_detail                    = "stack"
  demo_data_generation_id                  = var.manifest_digest
  demo_fixture_digest = sha256(jsonencode({
    environment_contract = filesha256("../../../../../environment-readiness/demo.rendered.json")
    release_members      = var.image_digests
  }))
  visitor_conversation = {
    mode                      = "V2"
    default_tenant_id         = "65797d6b-dc09-5e94-987b-02f365d457ef"
    lead_retention_days       = 90
    simulation_retention_days = 7
    handoff_open_base_url     = "https://api.demo.waooaw.com/api/v1/visitor/handoffs"
  }
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
    whatsapp_monitoring           = var.whatsapp_monitoring
    feature_settings              = var.feature_settings
    platform_access               = var.platform_access
  }
}

output "web_url" {
  value = module.workload.web_url
}
