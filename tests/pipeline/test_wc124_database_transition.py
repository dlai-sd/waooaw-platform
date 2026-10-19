from __future__ import annotations

import pytest

from wc124_database_transition import resolve_transition


@pytest.mark.parametrize(
    ("server_exists", "password_auth", "admin_count", "role_count", "state"),
    [
        (False, "Absent", 0, 0, "PLAN_A"),
        (True, "Disabled", 1, 1, "PLAN_A"),
        (True, "Enabled", 1, 1, "PLAN_B_ENABLED"),
        (True, "Enabled", 0, 1, "REVOCATION_PENDING"),
        (True, "Enabled", 0, 0, "REVOKED"),
    ],
)
def test_resolves_authorized_transition_states(
    server_exists: bool,
    password_auth: str,
    admin_count: int,
    role_count: int,
    state: str,
) -> None:
    transition = resolve_transition(
        server_exists=server_exists,
        password_auth=password_auth,
        bootstrap_admin_count=admin_count,
        provisioner_vault_role_count=role_count,
    )

    assert transition.state == state
    assert transition.mutations_allowed is True
    assert transition.hold_reason is None


def test_revocation_pending_preserves_provisioner_access_for_independent_verification() -> None:
    transition = resolve_transition(
        server_exists=True,
        password_auth="Enabled",
        bootstrap_admin_count=0,
        provisioner_vault_role_count=1,
    )

    assert transition.revocation_verification_required is True
    assert transition.revocation_required is True
    assert transition.bootstrap_admin_enabled is False
    assert transition.provisioner_vault_access_enabled is True


@pytest.mark.parametrize(
    ("password_auth", "admin_count", "role_count"),
    [
        ("Disabled", 0, 0),
        ("Disabled", 1, 0),
        ("Disabled", 0, 1),
        ("Enabled", 1, 0),
        ("Unknown", 0, 0),
        ("Enabled", 2, 1),
        ("Enabled", 0, 2),
    ],
)
def test_inconsistent_transition_evidence_enters_recovery_hold(
    password_auth: str,
    admin_count: int,
    role_count: int,
) -> None:
    transition = resolve_transition(
        server_exists=True,
        password_auth=password_auth,
        bootstrap_admin_count=admin_count,
        provisioner_vault_role_count=role_count,
    )

    assert transition.state == "RECOVERY_HOLD"
    assert transition.mutations_allowed is False
    assert transition.hold_reason
