variable "environment" {
  type = string
}

variable "location" {
  type = string
}

variable "repository_id" {
  type = string
}

variable "image_digests" {
  type = map(string)
}

variable "key_vault_secret_ids" {
  type = map(string)
}

variable "ce_min_replicas" {
  type = number
}

variable "pr_min_replicas" {
  type = number
}