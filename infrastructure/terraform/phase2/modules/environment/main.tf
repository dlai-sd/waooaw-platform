terraform {
  required_version = "= 1.9.8"
}

module "foundation" {
  source                 = "../foundation"
  environment            = var.environment
  location               = var.location
  repository_environment = var.environment
  repository_id          = var.repository_id
}

module "workload" {
  source = "../workload"

  environment                  = var.environment
  resource_group_name          = module.foundation.resource_group_name
  container_app_environment_id = module.foundation.container_app_environment_id
  runtime_identity_id          = module.foundation.runtime_identity_id
  runtime_identity_client_id   = module.foundation.runtime_identity_client_id
  image_digests                = var.image_digests
  key_vault_secret_ids         = var.key_vault_secret_ids
  ce_min_replicas              = var.ce_min_replicas
  pr_min_replicas              = var.pr_min_replicas
}

output "foundation_key_vault_id" {
  value = module.foundation.key_vault_id
}