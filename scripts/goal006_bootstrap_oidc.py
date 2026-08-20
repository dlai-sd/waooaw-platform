#!/usr/bin/env python3
"""Verify constrained bootstrap OIDC evidence without mutating Azure."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

OIDC_ISSUER = "https://token.actions.githubusercontent.com"
OIDC_AUDIENCE = "api://AzureADTokenExchange"
COST_ROLE = "Cost Management Reader"
ENVIRONMENT_ROLES = {"Contributor", "Role Based Access Control Administrator"}
STATE_MANAGEMENT_ROLE = "Storage Account Contributor"
STATE_ROLE = "Storage Blob Data Contributor"
STATE_RBAC_ROLE = "Role Based Access Control Administrator"
PROHIBITED_ROLES = {"Owner"}


def _role_tuple(assignment: Mapping[str, Any]) -> tuple[str, str]:
    return str(assignment.get("roleDefinitionName", "")), str(assignment.get("scope", "")).rstrip("/")


def validate_bootstrap_oidc(
    service_principal: Mapping[str, Any],
    app_credentials: Sequence[Any],
    federated_credentials: Sequence[Mapping[str, Any]],
    role_assignments: Sequence[Mapping[str, Any]],
    *,
    principal_id: str,
    expected_subjects: set[str],
    expected_roles: set[tuple[str, str]],
    subscription_scope: str,
    state_scope: str,
    environment_scopes: set[str],
) -> list[str]:
    violations: list[str] = []
    normalized_roles = {(role, scope.rstrip("/")) for role, scope in expected_roles}
    normalized_subscription_scope = subscription_scope.rstrip("/")
    normalized_state_scope = state_scope.rstrip("/")
    normalized_environment_scopes = {scope.rstrip("/") for scope in environment_scopes}
    required_roles = {
        (COST_ROLE, normalized_subscription_scope),
        (STATE_MANAGEMENT_ROLE, normalized_state_scope),
        (STATE_ROLE, normalized_state_scope),
        (STATE_RBAC_ROLE, normalized_state_scope),
        *{
            (role, scope)
            for scope in normalized_environment_scopes
            for role in ENVIRONMENT_ROLES
        },
    }

    if service_principal.get("id") != principal_id:
        violations.append("SERVICE_PRINCIPAL_MISMATCH")
    if app_credentials:
        violations.append("CLIENT_SECRET_PRESENT")
    if any(role in PROHIBITED_ROLES for role, _ in normalized_roles):
        violations.append("PROHIBITED_EXPECTED_ROLE")

    observed_subjects: set[str] = set()
    for credential in federated_credentials:
        if credential.get("issuer") != OIDC_ISSUER:
            violations.append("OIDC_ISSUER_INVALID")
        if credential.get("audiences") != [OIDC_AUDIENCE]:
            violations.append("OIDC_AUDIENCE_INVALID")
        subject = credential.get("subject")
        if isinstance(subject, str):
            observed_subjects.add(subject)
        else:
            violations.append("OIDC_SUBJECT_INVALID")
    if observed_subjects != expected_subjects:
        violations.append("OIDC_SUBJECT_SET_MISMATCH")

    observed_roles: set[tuple[str, str]] = set()
    for assignment in role_assignments:
        assignment_principal = assignment.get("principalId")
        if assignment_principal is not None and assignment_principal != principal_id:
            violations.append("ROLE_PRINCIPAL_MISMATCH")
        observed_roles.add(_role_tuple(assignment))
    if any(role in PROHIBITED_ROLES for role, _ in observed_roles):
        violations.append("PROHIBITED_ROLE_ASSIGNED")
    if observed_roles != normalized_roles:
        violations.append("ROLE_ASSIGNMENT_SET_MISMATCH")
    if normalized_roles != required_roles:
        violations.append("EXPECTED_ROLE_TOPOLOGY_MISMATCH")
    if (COST_ROLE, normalized_subscription_scope) not in observed_roles:
        violations.append("SUBSCRIPTION_COST_ACCESS_MISSING")
    if (STATE_MANAGEMENT_ROLE, normalized_state_scope) not in observed_roles:
        violations.append("STATE_MANAGEMENT_ACCESS_MISSING")
    if (STATE_ROLE, normalized_state_scope) not in observed_roles:
        violations.append("STATE_ACCESS_MISSING")
    if (STATE_RBAC_ROLE, normalized_state_scope) not in observed_roles:
        violations.append("STATE_RBAC_ACCESS_MISSING")
    if any(("Contributor", scope) not in observed_roles for scope in normalized_environment_scopes):
        violations.append("ENVIRONMENT_CONTRIBUTOR_ACCESS_MISSING")
    if any((STATE_RBAC_ROLE, scope) not in observed_roles for scope in normalized_environment_scopes):
        violations.append("ENVIRONMENT_RBAC_ACCESS_MISSING")

    return sorted(set(violations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-principal", type=Path, required=True)
    parser.add_argument("--app-credentials", type=Path, required=True)
    parser.add_argument("--federated-credentials", type=Path, required=True)
    parser.add_argument("--role-assignments", type=Path, required=True)
    parser.add_argument("--principal-id", required=True)
    parser.add_argument("--expected-subject", action="append", required=True)
    parser.add_argument("--expected-role", action="append", nargs=2, metavar=("ROLE", "SCOPE"), required=True)
    parser.add_argument("--subscription-scope", required=True)
    parser.add_argument("--state-scope", required=True)
    parser.add_argument("--environment-scope", action="append", required=True)
    args = parser.parse_args()
    violations = validate_bootstrap_oidc(
        json.loads(args.service_principal.read_text(encoding="utf-8")),
        json.loads(args.app_credentials.read_text(encoding="utf-8")),
        json.loads(args.federated_credentials.read_text(encoding="utf-8")),
        json.loads(args.role_assignments.read_text(encoding="utf-8")),
        principal_id=args.principal_id,
        expected_subjects=set(args.expected_subject),
        expected_roles={(role, scope) for role, scope in args.expected_role},
        subscription_scope=args.subscription_scope,
        state_scope=args.state_scope,
        environment_scopes=set(args.environment_scope),
    )
    print(json.dumps({"passed": not violations, "violations": violations}, sort_keys=True))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())