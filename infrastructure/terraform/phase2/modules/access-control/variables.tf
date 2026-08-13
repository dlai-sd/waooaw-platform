variable "approver_principal_id" {
  type = string
}

variable "executor_principal_id" {
  type = string
}

variable "requested_scope" {
  type = string
}

variable "incident_id" {
  type = string
}

variable "reason" {
  type = string
}

variable "expires_at" {
  type = string
}

variable "issued_at" {
  type = string
}

variable "activation_state" {
  type = string
  validation {
    condition     = contains(["ACTIVE", "REVOKED"], var.activation_state)
    error_message = "Break-glass state must be ACTIVE or REVOKED."
  }
}

variable "revoked_at" {
  type    = string
  default = null
}

variable "evidence_digest" {
  type = string
}