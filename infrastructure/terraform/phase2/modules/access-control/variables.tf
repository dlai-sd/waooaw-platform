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

variable "revoked_at" {
  type    = string
  default = null
}

variable "evidence_digest" {
  type = string
}