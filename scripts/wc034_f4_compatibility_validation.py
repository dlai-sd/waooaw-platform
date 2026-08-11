#!/usr/bin/env python3
"""Static compatibility validation for WC-034 F4 executable evidence."""

# Implements: architecture/reference/components/relationship-workspace-compatibility-evidence-spec.md §6-§13
# Constitutional basis: C-059 (Implementation Traceability), C-080 (Docker Test Isolation)

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
BP_SPEC_PATH = REPO_ROOT / "architecture/reference/api-specs/business-platform.openapi.yaml"

REL_TAG = "Relationship Workspace"
REL_ROOT = "/api/v1/employment/relationships/{relationshipId}/workspace"
EXPECTED_OPERATIONS = {
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
EXPECTED_F4_CODES = {
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
FORBIDDEN_PATTERNS = {
    "routing": ["destinationurl", "service selector", "callbackurl", "routefield"],
    "ranking": ["priorityscore", "rank", "weight", "secondarysort", "reorder"],
    "private_surface": [
        "professional-runtime",
        "wbe-relationship",
        "constitutional-engine",
        "ledger",
        "provider",
        "api-key",
    ],
}
POST_WITH_IDEMPOTENCY = {
    "submitRelationshipCommand",
    "requestRelationshipEvidenceExport",
}
TENANT_AUTHORITY_NORMALIZED = {"tenantid"}


class ValidationError(RuntimeError):
    """Raised for a blocking compatibility failure."""


@dataclass(frozen=True)
class TreeHash:
    path: str
    size: int
    sha256: str


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _operation_rows(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    rows: list[tuple[str, str, dict[str, Any]]] = []
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method.lower() in {"get", "post", "put", "patch", "delete"} and isinstance(operation, dict):
                rows.append((method.lower(), path, operation))
    return rows


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize_bytes(path: Path, raw: bytes) -> bytes:
    # Normalize line endings for deterministic cross-platform hashing.
    if path.suffix.lower() in {".ts", ".js", ".json", ".md", ".yaml", ".yml", ".txt"}:
        return raw.replace(b"\r\n", b"\n")
    return raw


def _hash_tree(root: Path) -> tuple[list[TreeHash], str]:
    rows: list[TreeHash] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        raw = path.read_bytes()
        normalized = _normalize_bytes(path, raw)
        rows.append(TreeHash(path=rel, size=len(normalized), sha256=_sha256_bytes(normalized)))
    digest_material = "\n".join(f"{row.path}|{row.size}|{row.sha256}" for row in rows).encode("utf-8")
    return rows, _sha256_bytes(digest_material)


def _collect_strings(node: Any, out: list[str]) -> None:
    if isinstance(node, str):
        out.append(node)
        return
    if isinstance(node, list):
        for item in node:
            _collect_strings(item, out)
        return
    if isinstance(node, dict):
        for key, value in node.items():
            out.append(str(key))
            _collect_strings(value, out)


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _is_tenant_authority_identifier(value: str) -> bool:
    return _normalize_identifier(value) in TENANT_AUTHORITY_NORMALIZED


def _resolve_ref(doc: dict[str, Any], ref: str) -> Any:
    _assert(ref.startswith("#/"), f"Only local refs are supported: {ref}")
    node: Any = doc
    for segment in ref[2:].split("/"):
        node = node[segment]
    return node


def _iter_parameter_objects(operation: dict[str, Any], doc: dict[str, Any]) -> list[dict[str, Any]]:
    params: list[dict[str, Any]] = []
    for parameter in operation.get("parameters", []):
        if not isinstance(parameter, dict):
            continue
        if "$ref" in parameter:
            resolved = _resolve_ref(doc, parameter["$ref"])
            if isinstance(resolved, dict):
                params.append(resolved)
            continue
        params.append(parameter)
    return params


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


def _assert_no_customer_selectable_tenant_authority(
    operation: dict[str, Any],
    method: str,
    path: str,
    spec: dict[str, Any],
) -> None:
    op_id = operation.get("operationId", f"{method.upper()} {path}")

    template_vars = re.findall(r"\{([^{}]+)\}", path)
    for var_name in template_vars:
        _assert(
            not _is_tenant_authority_identifier(var_name),
            f"{op_id} exposes customer-selectable tenant authority in path template variable '{var_name}'",
        )

    for parameter in _iter_parameter_objects(operation, spec):
        location = parameter.get("in")
        name = parameter.get("name")
        if location in {"path", "query", "header", "cookie"} and isinstance(name, str):
            _assert(
                not _is_tenant_authority_identifier(name),
                f"{op_id} exposes customer-selectable tenant authority via {location} parameter '{name}'",
            )

            schema = parameter.get("schema")
            if isinstance(schema, dict):
                _assert(
                    not _schema_has_tenant_authority_field(schema, spec, set()),
                    f"{op_id} exposes customer-selectable tenant authority via {location} parameter schema",
                )

    request_body = operation.get("requestBody")
    if isinstance(request_body, dict) and "$ref" in request_body:
        resolved = _resolve_ref(spec, request_body["$ref"])
        request_body = resolved if isinstance(resolved, dict) else request_body

    if isinstance(request_body, dict):
        for media in request_body.get("content", {}).values():
            schema = media.get("schema") if isinstance(media, dict) else None
            if isinstance(schema, dict):
                _assert(
                    not _schema_has_tenant_authority_field(schema, spec, set()),
                    f"{op_id} request body allows customer-selectable tenant authority",
                )


def validate_spec(slice_path: Path) -> dict[str, Any]:
    spec = _load_yaml(slice_path)
    canonical = _load_yaml(BP_SPEC_PATH)

    rows = _operation_rows(spec)
    canonical_rows = _operation_rows(canonical)
    canonical_ids = [operation["operationId"] for _, _, operation in canonical_rows if "operationId" in operation]
    _assert(len(canonical_ids) == len(set(canonical_ids)), "Canonical BP operationId values are not globally unique")

    rel_rows = [row for row in rows if REL_ROOT in row[1]]
    ids_by_route = {(method, path): operation.get("operationId") for method, path, operation in rel_rows}
    _assert(ids_by_route == EXPECTED_OPERATIONS, "F4 operation inventory mismatch (must be exact fourteen operations)")

    top_security = spec.get("security", [])
    _assert(top_security == [{"BearerAuth": []}], "Slice security baseline must be BearerAuth")

    responses = spec.get("components", {}).get("responses", {})
    for method, path, operation in rel_rows:
        _assert(REL_TAG in operation.get("tags", []), f"{method.upper()} {path} missing Relationship Workspace tag")
        op_security = operation.get("security")
        _assert(op_security in (None, [{"BearerAuth": []}]), f"{operation.get('operationId')} has weakened security")
        _assert_no_customer_selectable_tenant_authority(operation, method, path, spec)

        parameters = operation.get("parameters", [])
        has_relationship_param = any(
            isinstance(param, dict)
            and (
                param.get("$ref", "").endswith("/RelationshipId")
                or (param.get("name") == "relationshipId" and param.get("required") is True)
            )
            for param in parameters
        )
        _assert(has_relationship_param, f"{operation.get('operationId')} must require relationship binding")

        op_id = operation.get("operationId", "")
        if method == "post":
            expects_idempotency = op_id in POST_WITH_IDEMPOTENCY
            has_idempotency = any(
                isinstance(param, dict)
                and (
                    param.get("$ref", "").endswith("/IdempotencyKey")
                    or param.get("name") == "Idempotency-Key"
                )
                for param in parameters
            )
            _assert(expects_idempotency and has_idempotency, f"{op_id} must require Idempotency-Key")

        for status, response in operation.get("responses", {}).items():
            if not status.startswith(("4", "5")):
                continue
            if isinstance(response, dict) and "$ref" in response:
                ref = response["$ref"]
                if not ref.startswith("#/components/responses/"):
                    raise ValidationError(f"Unexpected response ref format on {op_id}: {ref}")
                response_name = ref.split("/")[-1]
                schema_ref = (
                    responses.get(response_name, {})
                    .get("content", {})
                    .get("application/problem+json", {})
                    .get("schema", {})
                    .get("$ref")
                )
                _assert(
                    schema_ref == "#/components/schemas/RelationshipWorkspaceProblemDetailV1",
                    f"{op_id} {status} must map to RelationshipWorkspaceProblemDetailV1",
                )

    command_union = spec["components"]["schemas"]["RelationshipTypedCommandPayloadV1"]
    discriminator = command_union.get("discriminator", {})
    mapping = discriminator.get("mapping", {})
    _assert(command_union.get("oneOf"), "RelationshipTypedCommandPayloadV1 must declare oneOf")
    _assert(discriminator.get("propertyName") == "commandKind", "Command discriminator must use commandKind")
    _assert(mapping and len(mapping) == len(command_union.get("oneOf", [])), "Command discriminator mapping must be complete")

    command_request = spec["components"]["schemas"]["SubmitRelationshipCommandRequestV1"]
    _assert(command_request.get("additionalProperties") is False, "SubmitRelationshipCommandRequestV1 must disallow untyped fallback")

    problem_codes = set(spec["components"]["schemas"]["RelationshipWorkspaceProblemCodeV1"]["enum"])
    _assert(problem_codes == EXPECTED_F4_CODES, "RelationshipWorkspaceProblemCodeV1 must match required F4 coverage")

    collected: list[str] = []
    _collect_strings(spec, collected)
    flattened = "\n".join(collected).lower()
    for family, patterns in FORBIDDEN_PATTERNS.items():
        for pattern in patterns:
            if pattern in flattened:
                raise ValidationError(f"Forbidden surface detected ({family}): {pattern}")

    operation_ids = [op_id for op_id in ids_by_route.values() if op_id]
    return {
        "operation_inventory": [
            {
                "operationId": operation["operationId"],
                "method": method.upper(),
                "path": path,
            }
            for method, path, operation in rel_rows
        ],
        "problem_codes": sorted(problem_codes),
        "operation_ids_unique": len(operation_ids) == len(set(operation_ids)),
    }


def validate_generation(run_a: Path, run_b: Path) -> dict[str, Any]:
    rows_a, tree_a = _hash_tree(run_a)
    rows_b, tree_b = _hash_tree(run_b)
    map_a = {row.path: row for row in rows_a}
    map_b = {row.path: row for row in rows_b}

    _assert(set(map_a) == set(map_b), "Generated file inventories differ across independent runs")
    differing = [path for path in sorted(map_a) if map_a[path].sha256 != map_b[path].sha256]
    _assert(not differing, f"Generated per-file hashes differ: {', '.join(differing[:5])}")
    _assert(tree_a == tree_b, "Normalized generated tree hash differs across runs")

    op_file = run_a / "apis" / "RelationshipWorkspaceApi.ts"
    _assert(op_file.exists(), "RelationshipWorkspaceApi.ts is missing in generated output")

    generated_text = op_file.read_text(encoding="utf-8")
    for operation_id in EXPECTED_OPERATIONS.values():
        _assert(f"async {operation_id}(" in generated_text, f"Generated API missing operation {operation_id}")

    return {
        "tree_hash": tree_a,
        "file_count": len(rows_a),
        "files": [row.__dict__ for row in rows_a],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slice", type=Path, required=True, help="Dependency-closed F4 OpenAPI slice path")
    parser.add_argument("--generated-run-a", type=Path, required=True, help="First clean generated output path")
    parser.add_argument("--generated-run-b", type=Path, required=True, help="Second clean generated output path")
    parser.add_argument("--output", type=Path, required=True, help="Manifest JSON output path")
    args = parser.parse_args()

    report = {
        "schema_version": "1.0",
        "bp_spec": {
            "path": str(BP_SPEC_PATH.relative_to(REPO_ROOT)),
            "sha256": _sha256_bytes(BP_SPEC_PATH.read_bytes()),
        },
        "slice": {
            "path": str(args.slice),
            "sha256": _sha256_bytes(args.slice.read_bytes()),
        },
    }

    try:
        report["spec_validation"] = validate_spec(args.slice)
        report["generation_validation"] = validate_generation(args.generated_run_a, args.generated_run_b)
        report["status"] = "PASS"
    except ValidationError as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())