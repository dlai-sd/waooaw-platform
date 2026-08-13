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

variable "repository_ref" {
  type    = string
  default = "refs/heads/main"
  validation {
    condition     = var.repository_ref == "refs/heads/main"
    error_message = "Phase 2 deployment trust is restricted to refs/heads/main."
  }
}

variable "repository_workflows" {
  type = set(string)
  default = [
    ".github/workflows/promote.yaml",
    ".github/workflows/post-deploy-verify.yaml",
  ]
  validation {
    condition = var.repository_workflows == toset([
      ".github/workflows/promote.yaml",
      ".github/workflows/post-deploy-verify.yaml",
    ])
    error_message = "Phase 2 deployment trust requires the exact approved workflow set."
  }
}