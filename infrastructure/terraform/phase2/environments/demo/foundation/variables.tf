variable "tfstate_storage_account_id" {
  type = string
}

variable "runner_resource_group_name" {
  type = string
}

variable "runner_private_endpoints_subnet_id" {
  type = string
}

variable "postgresql_password_auth_enabled" {
  type    = bool
  default = false
}

variable "database_bootstrap_admin_enabled" {
  type    = bool
  default = true
}

variable "database_provisioner_vault_access_enabled" {
  type    = bool
  default = true
}