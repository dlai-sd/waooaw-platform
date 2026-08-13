variable "environment" {
  type = string
  validation {
    condition     = contains(["demo", "uat"], var.environment)
    error_message = "Automatic lease lifecycle is prohibited for Production."
  }
}

variable "purpose" {
  type = string
}

variable "manifest_digest" {
  type = string
}

variable "owner_principal_id" {
  type = string
}

variable "expires_at" {
  type = string
}

variable "issued_at" {
  type = string
}

variable "lifecycle_state" {
  type = string
  validation {
    condition     = contains(["ACTIVE", "REVOKED"], var.lifecycle_state)
    error_message = "Lease state must be ACTIVE or REVOKED."
  }
}

variable "revoked_at" {
  type    = string
  default = null
}

variable "cost_centre" {
  type = string
}

variable "evidence_digest" {
  type = string
}

variable "protected_foundation_id" {
  type = string
}