terraform {
  required_version = "= 1.9.8"
}

locals {
  workload_enabled = (
    var.lifecycle_state == "ACTIVE" &&
    var.revoked_at == null &&
    timecmp(var.expires_at, plantimestamp()) > 0
  )
}

resource "terraform_data" "workload_lease" {
  input = {
    environment             = var.environment
    purpose                 = var.purpose
    manifest_digest         = var.manifest_digest
    owner_principal_id      = var.owner_principal_id
    expires_at              = var.expires_at
    issued_at               = var.issued_at
    lifecycle_state         = var.lifecycle_state
    revoked_at              = var.revoked_at
    cost_centre             = var.cost_centre
    evidence_digest         = var.evidence_digest
    protected_foundation_id = var.protected_foundation_id
  }

  lifecycle {
    precondition {
      condition     = can(regex("^sha256:[0-9a-f]{64}$", var.manifest_digest)) && can(regex("^sha256:[0-9a-f]{64}$", var.evidence_digest))
      error_message = "Lease activation requires immutable manifest and evidence digests."
    }
    precondition {
      condition     = trimspace(var.purpose) != "" && trimspace(var.owner_principal_id) != "" && trimspace(var.cost_centre) != "" && trimspace(var.expires_at) != ""
      error_message = "Purpose, owner, cost centre, and explicit expiry are required."
    }
    precondition {
      condition     = trimspace(var.protected_foundation_id) != ""
      error_message = "A lease must identify the foundation that shutdown preserves."
    }
    precondition {
      condition     = can(timecmp(var.expires_at, var.issued_at)) && timecmp(var.expires_at, var.issued_at) > 0
      error_message = "Lease expiry must be a valid RFC3339 timestamp after issuance."
    }
    precondition {
      condition     = var.lifecycle_state != "REVOKED" || var.revoked_at != null
      error_message = "A revoked lease requires a revocation timestamp."
    }
  }
}

output "workload_enabled" {
  value = local.workload_enabled
}