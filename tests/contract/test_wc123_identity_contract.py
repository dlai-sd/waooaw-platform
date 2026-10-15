"""WC-123 provider-neutral identity contract and generated-consumer checks."""

# Implements: CSA-AUTH-001 Section 20.2; WC-123 AUTH-WC-02
# Constitutional basis: C-023, C-032, C-059

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = ROOT / "architecture/reference/api-specs/business-platform.openapi.yaml"
GENERATED_IDENTITY_API = ROOT / "web/lib/api/generated/apis/IdentityApi.ts"


def load_spec() -> dict:
    return yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8"))


def test_canonical_provider_neutral_operations_are_versioned_and_no_store() -> None:
    spec = load_spec()
    paths = spec["paths"]

    expected = {
        ("/api/v1/identity/session", "get"): "getIdentitySession",
        ("/api/v1/identity/memberships", "get"): "listIdentityMemberships",
        (
            "/api/v1/identity/membership-selections/validate",
            "post",
        ): "validateIdentityMembershipSelection",
        (
            "/api/v1/identity/session-revocations",
            "post",
        ): "createIdentitySessionRevocation",
        ("/api/v1/identity/provider-links", "post"): "createIdentityProviderLink",
        (
            "/api/v1/identity/provider-links/{linkId}",
            "delete",
        ): "deleteIdentityProviderLink",
    }

    assert spec["info"]["version"] == "1.11.0"
    for (path, method), operation_id in expected.items():
        operation = paths[path][method]
        assert operation["operationId"] == operation_id
        assert operation["tags"] == ["Identity"]

    memberships = paths["/api/v1/identity/memberships"]["get"]
    cache_header = memberships["responses"]["200"]["headers"]["Cache-Control"]["schema"]
    assert cache_header == {"type": "string", "const": "no-store"}


def test_identity_contract_never_accepts_tokens_subjects_or_tenant_authority() -> None:
    spec = load_spec()
    schemas = spec["components"]["schemas"]
    forbidden_properties = {
        "accessToken",
        "refreshToken",
        "idToken",
        "subject",
        "issuer",
        "tenantId",
        "tenant_id",
        "roleClaim",
    }

    wc123_schema_names = {
        "IdentityMembershipCollectionV1",
        "IdentityMembershipSelectionRequestV1",
        "IdentityMembershipSelectionV1",
        "IdentityMembershipV1",
        "IdentitySessionRevocationRequestV1",
        "IdentitySessionRevocationReceiptV1",
        "IdentityProviderLinkRequestV1",
        "IdentityProviderLinkOperationV1",
    }
    for schema_name in wc123_schema_names:
        properties = set(schemas[schema_name].get("properties", {}))
        assert properties.isdisjoint(forbidden_properties)

    membership = schemas["IdentityMembershipV1"]
    assert set(membership["required"]) == {
        "membershipReference",
        "tenantReference",
        "role",
        "state",
        "selectionEligible",
    }
    assert membership["additionalProperties"] is False


def test_revocation_scope_requires_family_reference_only_for_one_family() -> None:
    request = load_spec()["components"]["schemas"]["IdentitySessionRevocationRequestV1"]

    family_rule, all_rule = request["allOf"]
    assert family_rule["if"]["properties"]["scope"]["const"] == "FAMILY"
    assert family_rule["then"]["required"] == ["sessionFamilyReference"]
    assert all_rule["if"]["properties"]["scope"]["const"] == "ALL"
    assert all_rule["then"]["not"]["required"] == ["sessionFamilyReference"]


def test_generated_web_consumer_exposes_every_canonical_operation() -> None:
    generated = GENERATED_IDENTITY_API.read_text(encoding="utf-8")

    for method in (
        "getIdentitySession",
        "listIdentityMemberships",
        "validateIdentityMembershipSelection",
        "createIdentitySessionRevocation",
        "createIdentityProviderLink",
        "deleteIdentityProviderLink",
    ):
        assert f"async {method}(" in generated
