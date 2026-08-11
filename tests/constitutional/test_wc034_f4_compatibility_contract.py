# Implements: architecture/reference/components/relationship-workspace-compatibility-evidence-spec.md §6-§13
# constitutional_basis: C-023, C-026, C-059, C-063, C-080
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pytest
import yaml

from scripts.openapi_slice import write_dependency_closed_openapi_slice


REPO_ROOT = Path(__file__).parents[2]
BP_SPEC = REPO_ROOT / "architecture/reference/api-specs/business-platform.openapi.yaml"

REL_ROOT = "/api/v1/employment/relationships/{relationshipId}/workspace"
EXPECTED_OPS = {
    ("get", f"{REL_ROOT}"): "getRelationshipWorkspace",
    ("get", f"{REL_ROOT}/changes"): "getRelationshipWorkspaceChanges",
    ("get", f"{REL_ROOT}/plan"): "getRelationshipPlan",
    ("get", f"{REL_ROOT}/attention"): "getRelationshipAttention",
    ("get", f"{REL_ROOT}/work"): "getRelationshipWork",
    ("get", f"{REL_ROOT}/results"): "getRelationshipResults",
    ("get", f"{REL_ROOT}/usage-budget"): "getRelationshipUsageBudget",
    ("get", f"{REL_ROOT}/rights-controls"): "getRelationshipRightsControls",
    ("post", f"{REL_ROOT}/commands"): "submitRelationshipCommand",
    ("get", f"{REL_ROOT}/commands/{{commandId}}"): "getRelationshipCommand",
    ("get", f"{REL_ROOT}/evidence"): "listRelationshipEvidence",
    ("get", f"{REL_ROOT}/evidence/{{evidenceId}}"): "getRelationshipEvidence",
    ("post", f"{REL_ROOT}/evidence-exports"): "requestRelationshipEvidenceExport",
    ("get", f"{REL_ROOT}/evidence-exports/{{exportId}}"): "getRelationshipEvidenceExport",
}
POST_IDS = {"submitRelationshipCommand", "requestRelationshipEvidenceExport"}
EXPECTED_CODES = {
    "RELATIONSHIP_WORKSPACE_REQUEST_INVALID",
    "RELATIONSHIP_WORKSPACE_SESSION_REQUIRED",
    "RELATIONSHIP_WORKSPACE_NOT_ACCESSIBLE",
    "RELATIONSHIP_STATE_CONFLICT",
    "RELATIONSHIP_IDEMPOTENCY_CONFLICT",
    "RELATIONSHIP_WORKSPACE_BLOCKED",
    "RELATIONSHIP_WORKSPACE_CURSOR_EXPIRED",
    "RELATIONSHIP_WORKSPACE_OWNER_UNAVAILABLE",
    "CONSTITUTIONAL_ENGINE_UNAVAILABLE",
    "RELATIONSHIP_SCHEMA_UNSUPPORTED",
}

TENANT_AUTHORITY_NORMALIZED = {"tenantid"}


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _is_tenant_authority_identifier(value: str) -> bool:
    return _normalize_identifier(value) in TENANT_AUTHORITY_NORMALIZED


def _resolve_ref(doc: dict[str, Any], ref: str) -> Any:
    assert ref.startswith("#/"), f"Only local refs are supported: {ref}"
    node: Any = doc
    for segment in ref[2:].split("/"):
        node = node[segment]
    return node


def _iter_parameter_objects(operation: dict[str, Any], doc: dict[str, Any]) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for param in operation.get("parameters", []):
        if not isinstance(param, dict):
            continue
        if "$ref" in param:
            target = _resolve_ref(doc, param["$ref"])
            if isinstance(target, dict):
                resolved.append(target)
            continue
        resolved.append(param)
    return resolved


def _schema_has_tenant_authority_field(
    schema: dict[str, Any],
    doc: dict[str, Any],
    visited: set[str],
) -> bool:
    if "$ref" in schema:
        ref = schema["$ref"]
        if ref in visited:
            return False
        visited.add(ref)
        resolved = _resolve_ref(doc, ref)
        if isinstance(resolved, dict):
            return _schema_has_tenant_authority_field(resolved, doc, visited)
        return False

    for key in schema.get("properties", {}):
        if _is_tenant_authority_identifier(key):
            return True

    for child in schema.get("properties", {}).values():
        if isinstance(child, dict) and _schema_has_tenant_authority_field(child, doc, visited):
            return True

    if isinstance(schema.get("additionalProperties"), dict):
        if _schema_has_tenant_authority_field(schema["additionalProperties"], doc, visited):
            return True

    for combiner in ("allOf", "anyOf", "oneOf"):
        for child in schema.get(combiner, []):
            if isinstance(child, dict) and _schema_has_tenant_authority_field(child, doc, visited):
                return True

    if isinstance(schema.get("items"), dict):
        if _schema_has_tenant_authority_field(schema["items"], doc, visited):
            return True

    return False


def _tenant_authority_violations(f4_slice: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    for path, path_item in f4_slice["paths"].items():
        template_vars = re.findall(r"\{([^{}]+)\}", path)
        for var_name in template_vars:
            if _is_tenant_authority_identifier(var_name):
                violations.append(f"Path template exposes tenant authority variable: {path}")

        for method, operation in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"} or not isinstance(operation, dict):
                continue

            op_id = operation.get("operationId", f"{method.upper()} {path}")
            for parameter in _iter_parameter_objects(operation, f4_slice):
                location = parameter.get("in")
                name = parameter.get("name")
                if (
                    location in {"path", "query", "header", "cookie"}
                    and isinstance(name, str)
                    and _is_tenant_authority_identifier(name)
                ):
                    violations.append(
                        f"{op_id} exposes tenant authority via {location} parameter '{name}'"
                    )

                schema = parameter.get("schema")
                if (
                    location in {"path", "query", "header", "cookie"}
                    and isinstance(schema, dict)
                    and _schema_has_tenant_authority_field(schema, f4_slice, set())
                ):
                    violations.append(
                        f"{op_id} exposes tenant authority via {location} parameter schema"
                    )

            request_body = operation.get("requestBody")
            if isinstance(request_body, dict) and "$ref" in request_body:
                resolved = _resolve_ref(f4_slice, request_body["$ref"])
                request_body = resolved if isinstance(resolved, dict) else request_body

            if isinstance(request_body, dict):
                for media in request_body.get("content", {}).values():
                    schema = media.get("schema") if isinstance(media, dict) else None
                    if isinstance(schema, dict) and _schema_has_tenant_authority_field(schema, f4_slice, set()):
                        violations.append(f"{op_id} request body allows tenant authority selection")

    return violations


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def f4_slice(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    tmp = tmp_path_factory.mktemp("f4-compat")
    out = tmp / "relationship-workspace.openapi.yaml"
    write_dependency_closed_openapi_slice(BP_SPEC, out, ["Relationship Workspace"])
    return _load_yaml(out)


def test_exact_fourteen_operation_inventory(f4_slice: dict[str, Any]) -> None:
    found = {}
    for path, path_item in f4_slice["paths"].items():
        for method, op in path_item.items():
            if method in {"get", "post", "put", "patch", "delete"}:
                found[(method, path)] = op.get("operationId")
    assert found == EXPECTED_OPS


def test_global_operation_id_uniqueness() -> None:
    bp = _load_yaml(BP_SPEC)
    op_ids: list[str] = []
    for path_item in bp["paths"].values():
        for method, operation in path_item.items():
            if method in {"get", "post", "put", "patch", "delete"} and isinstance(operation, dict):
                op_ids.append(operation["operationId"])
    assert len(op_ids) == len(set(op_ids))


def test_security_and_tenant_authority_contract(f4_slice: dict[str, Any]) -> None:
    assert f4_slice["security"] == [{"BearerAuth": []}]
    assert _tenant_authority_violations(f4_slice) == []


def test_every_f4_post_requires_idempotency(f4_slice: dict[str, Any]) -> None:
    for path, path_item in f4_slice["paths"].items():
        post = path_item.get("post")
        if not post:
            continue
        op_id = post["operationId"]
        assert op_id in POST_IDS
        refs = [param.get("$ref", "") for param in post.get("parameters", []) if isinstance(param, dict)]
        assert "#/components/parameters/IdempotencyKey" in refs


def test_rfc9457_error_mapping_and_required_codes(f4_slice: dict[str, Any]) -> None:
    responses = f4_slice["components"]["responses"]
    for path_item in f4_slice["paths"].values():
        for method, op in path_item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            for status, response in op.get("responses", {}).items():
                if not status.startswith(("4", "5")):
                    continue
                ref = response.get("$ref")
                assert ref and ref.startswith("#/components/responses/")
                response_obj = responses[ref.split("/")[-1]]
                schema_ref = response_obj["content"]["application/problem+json"]["schema"]["$ref"]
                assert schema_ref == "#/components/schemas/RelationshipWorkspaceProblemDetailV1"

    codes = set(f4_slice["components"]["schemas"]["RelationshipWorkspaceProblemCodeV1"]["enum"])
    assert codes == EXPECTED_CODES


def test_discriminated_command_mapping_is_complete(f4_slice: dict[str, Any]) -> None:
    typed = f4_slice["components"]["schemas"]["RelationshipTypedCommandPayloadV1"]
    assert "oneOf" in typed and typed["oneOf"]
    disc = typed.get("discriminator", {})
    assert disc.get("propertyName") == "commandKind"
    mapping = disc.get("mapping", {})
    assert mapping
    assert len(mapping) == len(typed["oneOf"])

    submit = f4_slice["components"]["schemas"]["SubmitRelationshipCommandRequestV1"]
    assert submit.get("additionalProperties") is False


def test_forbidden_public_surface_absent_in_slice(f4_slice: dict[str, Any]) -> None:
    text = yaml.safe_dump(f4_slice, sort_keys=False).lower()
    for forbidden in [
        "professional-runtime",
        "constitutional-engine",
        "wbe-relationship",
        "ledger",
        "provider",
        "rank",
        "reorder",
        "sort=",
        "destinationurl",
        "callbackurl",
    ]:
        assert forbidden not in text


@pytest.mark.parametrize(
    ("outcome_family", "required_token"),
    [
        ("success", "COMPLETED"),
        ("conflict", "RELATIONSHIP_STATE_CONFLICT"),
        ("stale", "STALE"),
        ("unavailable", "UNAVAILABLE"),
        ("blocked", "BLOCKED"),
        ("partial", "PARTIAL"),
        ("unknown", "UNKNOWN"),
        ("ce_unavailable", "CONSTITUTIONAL_ENGINE_UNAVAILABLE"),
        ("unsupported_version", "RELATIONSHIP_SCHEMA_UNSUPPORTED"),
    ],
)
def test_fixture_schema_matrix_tokens_present(
    f4_slice: dict[str, Any],
    outcome_family: str,
    required_token: str,
) -> None:
    payload = yaml.safe_dump(f4_slice, sort_keys=False)
    assert required_token in payload, outcome_family