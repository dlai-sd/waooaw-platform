variable "image_digests" {
  type = map(string)
}

variable "key_vault_secret_ids" {
  type = map(string)
}

variable "lease_purpose" {
  type = string
}

variable "manifest_digest" {
  type = string
}

variable "owner_principal_id" {
  type = string
}

variable "lease_issued_at" {
  type = string
}

variable "lease_expires_at" {
  type = string
}

variable "lease_state" {
  type = string
}

variable "lease_revoked_at" {
  type    = string
  default = null
}

variable "cost_centre" {
  type = string
}

variable "evidence_digest" {
  type = string
}