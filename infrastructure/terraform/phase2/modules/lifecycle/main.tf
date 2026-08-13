terraform {
  required_version = "= 1.9.8"
}

resource "terraform_data" "workload_lease" {
  input = {
    environment             = var.environment
    purpose                 = var.purpose
    manifest_digest         = var.manifest_digest
    owner_principal_id      = var.owner_principal_id
    expires_at              = var.expires_at
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
  }
}