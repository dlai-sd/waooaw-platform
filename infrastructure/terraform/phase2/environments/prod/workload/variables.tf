variable "image_digests" {
  type = map(string)
}

variable "key_vault_secret_ids" {
  type = map(string)
}

variable "ce_min_replicas" {
  type = number
  validation {
    condition     = var.ce_min_replicas > 0
    error_message = "Production CE minimum requires an accepted positive owner value."
  }
}

variable "pr_min_replicas" {
  type = number
  validation {
    condition     = var.pr_min_replicas > 0
    error_message = "Production PR minimum requires an accepted positive owner value."
  }
}