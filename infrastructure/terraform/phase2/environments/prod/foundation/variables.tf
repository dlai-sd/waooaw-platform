variable "tfstate_storage_account_id" {
  type = string
}

variable "runner_resource_group_name" {
  type = string
}

variable "runner_private_endpoints_subnet_id" {
  type = string
}

variable "deployment_client_id" {
  type     = string
  default  = null
  nullable = true
}

variable "auth_redis_ha_enabled" {
  type        = bool
  default     = false
  description = "Separately authorized switch for the retained private Production HA authentication limiter."
}