terraform {
  required_version = "= 1.9.8"
}

locals {
  authority_enabled = (
    var.activation_state == "ACTIVE" &&
    var.revoked_at == null &&
    timecmp(var.expires_at, timestamp()) > 0
  )
}

resource "terraform_data" "jit_break_glass_contract" {
  input = {
    approver_principal_id = var.approver_principal_id
    executor_principal_id = var.executor_principal_id
    requested_scope       = var.requested_scope
    incident_id           = var.incident_id
    reason                = var.reason
    expires_at            = var.expires_at
    issued_at             = var.issued_at
    activation_state      = var.activation_state
    revoked_at            = var.revoked_at
    evidence_digest       = var.evidence_digest
  }

  lifecycle {
    precondition {
      condition     = var.approver_principal_id != var.executor_principal_id
      error_message = "Break-glass approval and execution must be separated."
    }
    precondition {
      condition     = can(regex("^sha256:[0-9a-f]{64}$", var.evidence_digest))
      error_message = "Break-glass activation requires immutable evidence."
    }
    precondition {
      condition     = trimspace(var.incident_id) != "" && trimspace(var.reason) != "" && trimspace(var.requested_scope) != ""
      error_message = "Incident, reason, and exact scope are required."
    }
    precondition {
      condition     = can(timecmp(var.expires_at, var.issued_at)) && timecmp(var.expires_at, var.issued_at) > 0
      error_message = "Break-glass expiry must be a valid RFC3339 timestamp after issuance."
    }
    precondition {
      condition     = var.activation_state != "REVOKED" || var.revoked_at != null
      error_message = "Revoked break-glass authority requires a revocation timestamp."
    }
  }
}

output "authority_enabled" {
  value = local.authority_enabled
}