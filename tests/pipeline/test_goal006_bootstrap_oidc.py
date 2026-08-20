"""Offline contracts for constrained Phase 3 bootstrap OIDC evidence."""

from __future__ import annotations

from copy import deepcopy

from scripts.goal006_bootstrap_oidc import (
    COST_ROLE,
    STACK_ROLE,
    STATE_MANAGEMENT_ROLE,
    STATE_RBAC_ROLE,
    STATE_ROLE,
    validate_bootstrap_oidc,
)

PRINCIPAL_ID = "00000000-0000-0000-0000-000000000010"
STATE_SCOPE = "/subscriptions/sub/resourceGroups/state/providers/Microsoft.Storage/storageAccounts/state"
SUBSCRIPTION_SCOPE = "/subscriptions/sub"
ENVIRONMENT_SCOPES = {
    f"{SUBSCRIPTION_SCOPE}/resourceGroups/waooaw-demo-rg",
    f"{SUBSCRIPTION_SCOPE}/resourceGroups/waooaw-uat-rg",
    f"{SUBSCRIPTION_SCOPE}/resourceGroups/waooaw-prod-rg",
}
RUNNER_SCOPE = f"{SUBSCRIPTION_SCOPE}/resourceGroups/waooaw-demo-runner-rg"
SUBJECTS = {
    "repo:dlai-sd/waooaw-platform:environment:demo",
    "repo:dlai-sd/waooaw-platform:environment:uat",
    "repo:dlai-sd/waooaw-platform:environment:prod",
}
ROLES = {
    (COST_ROLE, SUBSCRIPTION_SCOPE),
    (STACK_ROLE, SUBSCRIPTION_SCOPE),
    (STATE_MANAGEMENT_ROLE, STATE_SCOPE),
    (STATE_ROLE, STATE_SCOPE),
    (STATE_RBAC_ROLE, STATE_SCOPE),
    *{(role, scope) for scope in ENVIRONMENT_SCOPES for role in ("Contributor", STATE_RBAC_ROLE)},
    *{(role, RUNNER_SCOPE) for role in ("Contributor", STATE_RBAC_ROLE)},
}


def evidence() -> tuple[dict[str, str], list[object], list[dict[str, object]], list[dict[str, str]]]:
    service_principal = {"id": PRINCIPAL_ID}
    credentials: list[object] = []
    federation = [
        {
            "issuer": "https://token.actions.githubusercontent.com",
            "audiences": ["api://AzureADTokenExchange"],
            "subject": subject,
        }
        for subject in sorted(SUBJECTS)
    ]
    assignments = [
        {"principalId": PRINCIPAL_ID, "roleDefinitionName": role, "scope": scope}
        for role, scope in sorted(ROLES)
    ]
    return service_principal, credentials, federation, assignments


def validate(
    service_principal: dict[str, str],
    credentials: list[object],
    federation: list[dict[str, object]],
    assignments: list[dict[str, str]],
) -> list[str]:
    return validate_bootstrap_oidc(
        service_principal,
        credentials,
        federation,
        assignments,
        principal_id=PRINCIPAL_ID,
        expected_subjects=SUBJECTS,
        expected_roles=ROLES,
        subscription_scope=SUBSCRIPTION_SCOPE,
        state_scope=STATE_SCOPE,
        environment_scopes=ENVIRONMENT_SCOPES,
        runner_scope=RUNNER_SCOPE,
    )


def test_exact_bootstrap_oidc_evidence_passes() -> None:
    assert validate(*evidence()) == []


def test_subject_or_audience_drift_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    federation[0]["subject"] = "repo:fork/waooaw-platform:environment:demo"
    federation[1]["audiences"] = ["unexpected"]
    assert validate(service_principal, credentials, federation, assignments) == [
        "OIDC_AUDIENCE_INVALID",
        "OIDC_SUBJECT_SET_MISMATCH",
    ]


def test_client_secret_or_owner_role_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    credentials.append({"displayName": "forbidden-secret"})
    assignments.append({"principalId": PRINCIPAL_ID, "roleDefinitionName": "Owner", "scope": SUBSCRIPTION_SCOPE})
    assert validate(service_principal, credentials, federation, assignments) == [
        "CLIENT_SECRET_PRESENT",
        "PROHIBITED_ROLE_ASSIGNED",
        "ROLE_ASSIGNMENT_SET_MISMATCH",
    ]


def test_missing_state_access_or_unexpected_role_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    assignments = [assignment for assignment in assignments if assignment["roleDefinitionName"] != STATE_ROLE]
    assignments.append({"principalId": PRINCIPAL_ID, "roleDefinitionName": "Reader", "scope": STATE_SCOPE})
    assert validate(service_principal, credentials, federation, assignments) == [
        "ROLE_ASSIGNMENT_SET_MISMATCH",
        "STATE_ACCESS_MISSING",
    ]


def test_missing_cost_access_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    assignments = [assignment for assignment in assignments if assignment["roleDefinitionName"] != COST_ROLE]
    assert validate(service_principal, credentials, federation, assignments) == [
        "ROLE_ASSIGNMENT_SET_MISMATCH",
        "SUBSCRIPTION_COST_ACCESS_MISSING",
    ]


def test_missing_runner_bootstrap_authority_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    assignments = [
        assignment
        for assignment in assignments
        if assignment["roleDefinitionName"] != STACK_ROLE and assignment["scope"] != RUNNER_SCOPE
    ]
    assert validate(service_principal, credentials, federation, assignments) == [
        "ROLE_ASSIGNMENT_SET_MISMATCH",
        "RUNNER_CONTRIBUTOR_ACCESS_MISSING",
        "RUNNER_RBAC_ACCESS_MISSING",
        "SUBSCRIPTION_STACK_ACCESS_MISSING",
    ]


def test_missing_state_management_or_rbac_access_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    assignments = [
        assignment
        for assignment in assignments
        if assignment["roleDefinitionName"] not in {STATE_MANAGEMENT_ROLE, STATE_RBAC_ROLE}
        or assignment["scope"] != STATE_SCOPE
    ]
    assert validate(service_principal, credentials, federation, assignments) == [
        "ROLE_ASSIGNMENT_SET_MISMATCH",
        "STATE_MANAGEMENT_ACCESS_MISSING",
        "STATE_RBAC_ACCESS_MISSING",
    ]


def test_missing_environment_authority_fails_closed() -> None:
    service_principal, credentials, federation, assignments = deepcopy(evidence())
    environment_scope = min(ENVIRONMENT_SCOPES)
    assignments = [assignment for assignment in assignments if assignment["scope"] != environment_scope]
    assert validate(service_principal, credentials, federation, assignments) == [
        "ENVIRONMENT_CONTRIBUTOR_ACCESS_MISSING",
        "ENVIRONMENT_RBAC_ACCESS_MISSING",
        "ROLE_ASSIGNMENT_SET_MISMATCH",
    ]