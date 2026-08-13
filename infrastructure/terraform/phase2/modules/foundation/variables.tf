variable "environment" {
  type = string
  validation {
    condition     = contains(["demo", "uat", "prod"], var.environment)
    error_message = "Environment must be demo, uat, or prod."
  }
}

variable "location" {
  type = string
}

variable "repository_environment" {
  type = string
}

variable "repository_id" {
  type = string
}