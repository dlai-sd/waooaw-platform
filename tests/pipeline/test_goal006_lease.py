from __future__ import annotations

from datetime import datetime, timezone

import pytest

from goal006_lease import renew_lease, validate_active_lease


def configuration() -> dict[str, object]:
    return {
        "lease_issued_at": "2026-08-23T12:46:35Z",
        "lease_expires_at": "2026-08-25T12:46:35Z",
        "lease_state": "ACTIVE",
        "lease_revoked_at": None,
        "unrelated": {"preserved": True},
    }


def test_failed_run_expiry_is_rejected() -> None:
    with pytest.raises(ValueError, match="deployment lease expired at 2026-08-25T12:46:35Z"):
        validate_active_lease(
            configuration(), datetime(2026, 8, 25, 17, 23, tzinfo=timezone.utc)
        )


def test_renewal_changes_only_lease_control_fields() -> None:
    original = configuration()
    renewed = renew_lease(
        original,
        issued_at=datetime(2026, 8, 26, 4, 45, 39, tzinfo=timezone.utc),
        expires_at=datetime(2026, 8, 28, 4, 45, 39, tzinfo=timezone.utc),
    )

    assert renewed["lease_expires_at"] == "2026-08-28T04:45:39Z"
    assert renewed["unrelated"] == original["unrelated"]
    assert original["lease_expires_at"] == "2026-08-25T12:46:35Z"


def test_revoked_lease_cannot_be_renewed() -> None:
    values = configuration()
    values["lease_revoked_at"] = "2026-08-25T12:00:00Z"

    with pytest.raises(ValueError, match="revoked lease"):
        renew_lease(
            values,
            issued_at=datetime(2026, 8, 26, tzinfo=timezone.utc),
            expires_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
        )