#!/usr/bin/env python3
"""Resolve the governed WC-124 database transition from independent live facts."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Transition:
    state: str
    mutations_allowed: bool
    bootstrap_required: bool
    provisioner_required: bool
    plan_b_required: bool
    handoff_required: bool
    revocation_verification_required: bool
    revocation_required: bool
    password_auth_enabled: bool
    bootstrap_admin_enabled: bool
    provisioner_vault_access_enabled: bool
    hold_reason: str | None = None


def recovery_hold(reason: str) -> Transition:
    return Transition(
        state="RECOVERY_HOLD",
        mutations_allowed=False,
        bootstrap_required=False,
        provisioner_required=False,
        plan_b_required=False,
        handoff_required=False,
        revocation_verification_required=False,
        revocation_required=False,
        password_auth_enabled=False,
        bootstrap_admin_enabled=False,
        provisioner_vault_access_enabled=False,
        hold_reason=reason,
    )


def resolve_transition(
    *,
    server_exists: bool,
    password_auth: str,
    bootstrap_admin_count: int,
    provisioner_vault_role_count: int,
) -> Transition:
    auth_state = {"Absent": 0, "Disabled": 1, "Enabled": 2}.get(password_auth)
    if bootstrap_admin_count not in (0, 1):
        return recovery_hold("expected zero or one WC-124 Entra bootstrap administrator")
    if provisioner_vault_role_count not in (0, 1):
        return recovery_hold("expected zero or one WC-124 provisioner Key Vault role assignment")

    if not server_exists:
        if auth_state != 0 or bootstrap_admin_count != 0 or provisioner_vault_role_count != 0:
            return recovery_hold("absent server has contradictory transition evidence")
        return Transition(
            state="PLAN_A",
            mutations_allowed=True,
            bootstrap_required=True,
            provisioner_required=True,
            plan_b_required=True,
            handoff_required=True,
            revocation_verification_required=False,
            revocation_required=True,
            password_auth_enabled=False,
            bootstrap_admin_enabled=True,
            provisioner_vault_access_enabled=True,
        )

    if auth_state == 1 and bootstrap_admin_count == 1 and provisioner_vault_role_count == 1:
        return Transition(
            state="PLAN_A",
            mutations_allowed=True,
            bootstrap_required=True,
            provisioner_required=True,
            plan_b_required=True,
            handoff_required=True,
            revocation_verification_required=False,
            revocation_required=True,
            password_auth_enabled=False,
            bootstrap_admin_enabled=True,
            provisioner_vault_access_enabled=True,
        )

    if auth_state == 2 and bootstrap_admin_count == 1 and provisioner_vault_role_count == 1:
        return Transition(
            state="PLAN_B_ENABLED",
            mutations_allowed=True,
            bootstrap_required=False,
            provisioner_required=True,
            plan_b_required=False,
            handoff_required=True,
            revocation_verification_required=False,
            revocation_required=True,
            password_auth_enabled=True,
            bootstrap_admin_enabled=True,
            provisioner_vault_access_enabled=True,
        )

    if auth_state == 2 and bootstrap_admin_count == 0 and provisioner_vault_role_count == 1:
        return Transition(
            state="REVOCATION_PENDING",
            mutations_allowed=True,
            bootstrap_required=False,
            provisioner_required=False,
            plan_b_required=False,
            handoff_required=False,
            revocation_verification_required=True,
            revocation_required=True,
            password_auth_enabled=True,
            bootstrap_admin_enabled=False,
            provisioner_vault_access_enabled=True,
        )

    if auth_state == 2 and bootstrap_admin_count == 0 and provisioner_vault_role_count == 0:
        return Transition(
            state="REVOKED",
            mutations_allowed=True,
            bootstrap_required=False,
            provisioner_required=False,
            plan_b_required=False,
            handoff_required=False,
            revocation_verification_required=False,
            revocation_required=False,
            password_auth_enabled=True,
            bootstrap_admin_enabled=False,
            provisioner_vault_access_enabled=False,
        )

    if auth_state not in {1, 2}:
        return recovery_hold(f"unsupported PostgreSQL password authentication state: {password_auth}")
    return recovery_hold(
        "live WC-124 controls do not match an authorized transition state "
        f"(password_auth={password_auth}, bootstrap_admin_count={bootstrap_admin_count}, "
        f"provisioner_vault_role_count={provisioner_vault_role_count})"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-exists", required=True, choices=("true", "false"))
    parser.add_argument("--password-auth", required=True)
    parser.add_argument("--bootstrap-admin-count", required=True, type=int)
    parser.add_argument("--provisioner-vault-role-count", required=True, type=int)
    arguments = parser.parse_args()
    transition = resolve_transition(
        server_exists=arguments.server_exists == "true",
        password_auth=arguments.password_auth,
        bootstrap_admin_count=arguments.bootstrap_admin_count,
        provisioner_vault_role_count=arguments.provisioner_vault_role_count,
    )
    print(json.dumps(asdict(transition), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
