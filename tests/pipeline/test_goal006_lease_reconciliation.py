from __future__ import annotations

from datetime import datetime, timezone

from goal006_lease_reconciliation import lease_requires_reconciliation, validate_deletion_plan


def test_expired_or_revoked_lease_requires_reconciliation() -> None:
    now = datetime(2026, 8, 14, tzinfo=timezone.utc)
    assert lease_requires_reconciliation(
        {"lease_state": "ACTIVE", "lease_expires_at": "2026-08-13T00:00:00Z"}, now
    )
    assert lease_requires_reconciliation(
        {"lease_state": "REVOKED", "lease_revoked_at": "2026-08-13T00:00:00Z"}, now
    )
    assert not lease_requires_reconciliation(
        {"lease_state": "ACTIVE", "lease_expires_at": "2026-08-15T00:00:00Z"}, now
    )


def test_reconciliation_plan_allows_only_disposable_deletions() -> None:
    plan = {
        "resource_changes": [
            {
                "address": 'module.workload.azurerm_container_app.member["web"]',
                "change": {"actions": ["delete"]},
            },
            {"address": "module.lease.terraform_data.workload_lease", "change": {"actions": ["no-op"]}},
        ]
    }
    assert validate_deletion_plan("demo", plan) == []
    plan["resource_changes"][0]["change"]["actions"] = ["update"]
    assert validate_deletion_plan("uat", plan)


def test_production_reconciliation_is_prohibited() -> None:
    assert "PRODUCTION_RECONCILIATION_PROHIBITED" in validate_deletion_plan("prod", {"resource_changes": []})