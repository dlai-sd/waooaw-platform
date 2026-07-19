variable "environment"             { type = string }
variable "location"               { type = string }
variable "postgres_sku_name"      { type = string }
variable "postgres_storage_mb"    { type = number }
variable "postgres_admin_password"{ type = string; sensitive = true }
variable "postgres_version"       { type = string }
variable "keycloak_admin_password"{ type = string; sensitive = true }
variable "ghcr_server"            { type = string }
variable "ghcr_username"          { type = string }
variable "ghcr_token"             { type = string; sensitive = true }
variable "image_org"              { type = string }
variable "image_tag"              { type = string }
variable "ce_min_replicas"        { type = number }
variable "ce_max_replicas"        { type = number }
variable "default_min_replicas"   { type = number }
variable "default_max_replicas"   { type = number }
variable "log_retention_days"     { type = number }
variable "tags"                   { type = map(string) }
