#!/usr/bin/env python3
# constitutional_basis: C-008, C-051, C-065, C-071, C-077, C-083, C-084, C-085
# ib_item: IB-009
"""Build and validate post-BOOTSTRAP context manifests for low-risk work.

# Implements: strategy/FOUNDER-PROPOSAL-2026-08-10-constitutional-fast-path.md
# Constitutional basis: C-008, C-051, C-065, C-071, C-077, C-083, C-084, C-085
# ib_item: IB-009 (FinOps context injector lineage)
# Founder authorization: 2026-08-10, low-risk constitutional fast path only

This tool routes context. It does not grant authority, make semantic decisions,
edit repository files, invoke RAG, or execute validation commands.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_VERSION = "1.0"
MAX_MANIFEST_TOKENS = 500
MAX_SOURCE_TOKENS = 1_500
MAX_TASK_CONTEXT_TOKENS = 4_500

REQUIRED_BOOTSTRAP_FILES = (
    "constitution/BOOTSTRAP.md",
    "README.md",
    "constitution/PROJECT_STATE.md",
)

ELIGIBLE_TASK_CLASSES = frozenset(
    {
        "retrieval_routing",
        "mechanical_status",
        "format_validation",
        "orchestration_preparation",
        "mechanical_checkpoint",
        "documentation_consistency",
    }
)

MODEL_HINTS = frozenset({"none", "auto", "reasoning"})
PROVENANCE_CLASSES = frozenset(
    {
        "authoritative_source",
        "accepted_decision",
        "immutable_evidence",
        "current_checkpoint",
        "informative_context",
    }
)
RETRIEVAL_MODES = frozenset({"index", "index+rag"})

RISK_FLAGS = (
    "constitutional_change",
    "authority_or_acceptance",
    "independent_review",
    "adr_change",
    "agent_lifecycle",
    "application_implementation",
    "security_or_identity",
    "financial_or_billing",
    "customer_rights",
    "evidence_first",
    "emergency_stop",
    "provider_or_deployment",
)

SAFE_WRITE_PREFIXES = (
    "strategy/",
    "sprint-context/fast-path/",
)


class ManifestError(ValueError):
    """A fail-closed manifest validation error."""


def _git_head(repo_root: Path = REPO_ROOT) -> str:
    git_executable = shutil.which("git")
    if git_executable is None:
        raise ManifestError("git executable cannot be resolved")
    result = subprocess.run(  # noqa: S603 - executable and arguments are fixed above
        [git_executable, "rev-parse", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise ManifestError("repository HEAD cannot be resolved")
    return result.stdout.strip()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"cannot read JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError("request and manifest roots must be JSON objects")
    return value


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{field} must be a non-empty string")
    return value.strip()


def _require_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ManifestError(f"{field} must be a list of non-empty strings")
    return [item.strip() for item in value]


def _repo_path(value: Any, field: str, *, must_exist: bool) -> str:
    path = _require_string(value, field).replace("\\", "/")
    pure_path = PurePosixPath(path)
    if pure_path.is_absolute() or ".." in pure_path.parts or path.startswith("./"):
        raise ManifestError(f"{field} must be a normalized repository-relative path")
    normalized = pure_path.as_posix()
    if must_exist and not (REPO_ROOT / normalized).exists():
        raise ManifestError(f"{field} does not exist: {normalized}")
    return normalized


def _validate_bootstrap(bootstrap: Any) -> dict[str, Any]:
    if not isinstance(bootstrap, dict):
        raise ManifestError("bootstrap must be an object")
    if bootstrap.get("completed") is not True:
        raise ManifestError("mandatory BOOTSTRAP sequence is not complete")
    if bootstrap.get("status") != "READY":
        raise ManifestError("fast path requires an exact READY bootstrap status")
    files_read = _require_string_list(bootstrap.get("files_read"), "bootstrap.files_read")
    if tuple(files_read) != REQUIRED_BOOTSTRAP_FILES:
        raise ManifestError("bootstrap.files_read must match the mandatory sequence exactly")
    return {
        "completed": True,
        "status": "READY",
        "files_read": files_read,
    }


def _validate_risk_flags(risk_flags: Any) -> dict[str, bool]:
    if not isinstance(risk_flags, dict):
        raise ManifestError("risk_flags must be an object")
    missing = [flag for flag in RISK_FLAGS if flag not in risk_flags]
    extra = sorted(set(risk_flags) - set(RISK_FLAGS))
    if missing or extra:
        raise ManifestError(f"risk_flags must contain the exact risk set; missing={missing}, extra={extra}")
    enabled = [flag for flag in RISK_FLAGS if risk_flags[flag] is not False]
    if enabled:
        raise ManifestError(f"ordinary constitutional path required for risk flags: {enabled}")
    return {flag: False for flag in RISK_FLAGS}


def _validate_write_paths(write_paths: Any) -> list[str]:
    paths = _require_string_list(write_paths, "write_paths")
    normalized: list[str] = []
    for index, path in enumerate(paths):
        repo_path = _repo_path(path, f"write_paths[{index}]", must_exist=False)
        if not any(repo_path.startswith(prefix) for prefix in SAFE_WRITE_PREFIXES):
            raise ManifestError(f"ordinary path required for write target: {repo_path}")
        normalized.append(repo_path)
    return sorted(set(normalized))


def _validate_sources(sources: Any) -> tuple[list[dict[str, Any]], int]:
    if not isinstance(sources, list) or not sources:
        raise ManifestError("sources must be a non-empty list")
    normalized: list[dict[str, Any]] = []
    total_tokens = 0
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ManifestError(f"sources[{index}] must be an object")
        path = _repo_path(source.get("path"), f"sources[{index}].path", must_exist=True)
        section = _require_string(source.get("section"), f"sources[{index}].section")
        provenance = _require_string(source.get("provenance"), f"sources[{index}].provenance")
        if provenance not in PROVENANCE_CLASSES:
            raise ManifestError(f"sources[{index}].provenance is not recognized: {provenance}")
        retrieved_via = _require_string(source.get("retrieved_via"), f"sources[{index}].retrieved_via")
        if retrieved_via not in {"direct", "index", "rag"}:
            raise ManifestError(f"sources[{index}].retrieved_via must be direct, index, or rag")
        max_tokens = source.get("max_tokens")
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 1 <= max_tokens <= MAX_SOURCE_TOKENS:
            raise ManifestError(f"sources[{index}].max_tokens must be between 1 and {MAX_SOURCE_TOKENS}")
        retrieval_score = source.get("retrieval_score")
        if retrieved_via == "rag":
            if not isinstance(retrieval_score, (int, float)) or isinstance(retrieval_score, bool):
                raise ManifestError(f"sources[{index}].retrieval_score is required for RAG results")
            if not 0 <= float(retrieval_score) <= 1:
                raise ManifestError(f"sources[{index}].retrieval_score must be between 0 and 1")
        elif retrieval_score is not None:
            raise ManifestError(f"sources[{index}].retrieval_score is only valid for RAG results")
        total_tokens += max_tokens
        entry: dict[str, Any] = {
            "path": path,
            "section": section,
            "provenance": provenance,
            "retrieved_via": retrieved_via,
            "max_tokens": max_tokens,
        }
        if retrieval_score is not None:
            entry["retrieval_score"] = float(retrieval_score)
        normalized.append(entry)
    return normalized, total_tokens


def _validate_retrieval(retrieval: Any) -> dict[str, Any]:
    if not isinstance(retrieval, dict):
        raise ManifestError("retrieval must be an object")
    mode = _require_string(retrieval.get("mode"), "retrieval.mode")
    if mode not in RETRIEVAL_MODES:
        raise ManifestError(f"retrieval.mode must be one of {sorted(RETRIEVAL_MODES)}")
    index_path = _repo_path(retrieval.get("index_path"), "retrieval.index_path", must_exist=True)
    query = retrieval.get("query")
    if mode == "index+rag":
        query = _require_string(query, "retrieval.query")
    elif query not in (None, ""):
        raise ManifestError("retrieval.query is only valid in index+rag mode")
    return {"mode": mode, "index_path": index_path, "query": query or None}


def _validate_identifiers(values: Any, field: str, pattern: str) -> list[str]:
    identifiers = _require_string_list(values, field)
    invalid = [value for value in identifiers if re.fullmatch(pattern, value) is None]
    if invalid:
        raise ManifestError(f"{field} contains invalid identifiers: {invalid}")
    return sorted(set(identifiers))


def _normalize_request(request: dict[str, Any]) -> tuple[dict[str, Any], int]:
    task_class = _require_string(request.get("task_class"), "task_class")
    if task_class not in ELIGIBLE_TASK_CLASSES:
        raise ManifestError(f"ordinary constitutional path required for task_class: {task_class}")
    model_hint = _require_string(request.get("model_hint"), "model_hint")
    if model_hint not in MODEL_HINTS:
        raise ManifestError(f"model_hint must be one of {sorted(MODEL_HINTS)}")
    sources, source_tokens = _validate_sources(request.get("sources"))
    total_tokens = MAX_MANIFEST_TOKENS + source_tokens
    if total_tokens > MAX_TASK_CONTEXT_TOKENS:
        raise ManifestError(
            f"post-BOOTSTRAP context budget exceeded: {total_tokens}/{MAX_TASK_CONTEXT_TOKENS} tokens"
        )
    normalized = {
        "task_id": _require_string(request.get("task_id"), "task_id"),
        "task_class": task_class,
        "goal_id": _require_string(request.get("goal_id"), "goal_id"),
        "work_contract": _require_string(request.get("work_contract"), "work_contract"),
        "office": _require_string(request.get("office"), "office"),
        "decision_space": _require_string(request.get("decision_space"), "decision_space"),
        "bootstrap": _validate_bootstrap(request.get("bootstrap")),
        "retrieval": _validate_retrieval(request.get("retrieval")),
        "sources": sources,
        "relevant_claims": _validate_identifiers(request.get("relevant_claims"), "relevant_claims", r"C-\d{3}"),
        "relevant_adrs": _validate_identifiers(request.get("relevant_adrs"), "relevant_adrs", r"ADR-\d{3}"),
        "write_paths": _validate_write_paths(request.get("write_paths")),
        "validations": _require_string_list(request.get("validations"), "validations"),
        "risk_flags": _validate_risk_flags(request.get("risk_flags")),
        "model_hint": model_hint,
    }
    return normalized, total_tokens


def build_manifest(request: dict[str, Any], *, generated_utc: str | None = None) -> dict[str, Any]:
    """Build a normalized manifest from an explicit low-risk request."""
    normalized, total_tokens = _normalize_request(request)
    timestamp = generated_utc or datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ROUTED_LOW_RISK",
        "generated_utc": timestamp,
        "source_commit": _git_head(),
        **normalized,
        "token_budget": {
            "manifest_tokens": MAX_MANIFEST_TOKENS,
            "source_tokens": total_tokens - MAX_MANIFEST_TOKENS,
            "total_tokens": total_tokens,
            "limit": MAX_TASK_CONTEXT_TOKENS,
            "budget_ok": True,
        },
        "ordinary_path_trigger": "Any validation failure, ambiguity, scope expansion, or enabled risk flag",
    }


def validate_manifest(manifest: dict[str, Any], *, require_current_commit: bool = True) -> None:
    """Validate a built manifest and fail closed on drift or expansion."""
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ManifestError(f"schema_version must be {SCHEMA_VERSION}")
    if manifest.get("status") != "ROUTED_LOW_RISK":
        raise ManifestError("manifest status must be ROUTED_LOW_RISK")
    generated_utc = _require_string(manifest.get("generated_utc"), "generated_utc")
    try:
        datetime.fromisoformat(generated_utc.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestError("generated_utc must be an ISO 8601 timestamp") from exc
    source_commit = _require_string(manifest.get("source_commit"), "source_commit")
    if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise ManifestError("source_commit must be a full lowercase Git commit SHA")
    if require_current_commit and source_commit != _git_head():
        raise ManifestError("manifest source_commit is stale; rebuild from current HEAD")
    normalized, total_tokens = _normalize_request(manifest)
    for field, value in normalized.items():
        if manifest.get(field) != value:
            raise ManifestError(f"manifest field is not normalized: {field}")
    expected_budget = {
        "manifest_tokens": MAX_MANIFEST_TOKENS,
        "source_tokens": total_tokens - MAX_MANIFEST_TOKENS,
        "total_tokens": total_tokens,
        "limit": MAX_TASK_CONTEXT_TOKENS,
        "budget_ok": True,
    }
    if manifest.get("token_budget") != expected_budget:
        raise ManifestError("token_budget does not match normalized sources")


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _manifest_output_path(path: Path) -> Path:
    candidate = path if path.is_absolute() else REPO_ROOT / path
    resolved = candidate.resolve()
    allowed_root = (REPO_ROOT / "sprint-context" / "fast-path").resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise ManifestError("output must remain under sprint-context/fast-path/") from exc
    return resolved


def _build_command(request_path: Path, output_path: Path) -> None:
    manifest = build_manifest(_load_json(request_path))
    validate_manifest(manifest)
    contained_output = _manifest_output_path(output_path)
    _write_json(contained_output, manifest)
    print(f"PASS: low-risk manifest written to {contained_output}")


def _validate_command(manifest_path: Path, allow_stale_commit: bool) -> None:
    validate_manifest(_load_json(manifest_path), require_current_commit=not allow_stale_commit)
    print(f"PASS: low-risk manifest is valid: {manifest_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Build and validate a manifest from a JSON request")
    build_parser.add_argument("--request", type=Path, required=True)
    build_parser.add_argument("--output", type=Path, required=True)

    validate_parser = subparsers.add_parser("validate", help="Validate an existing manifest")
    validate_parser.add_argument("--manifest", type=Path, required=True)
    validate_parser.add_argument("--allow-stale-commit", action="store_true")

    args = parser.parse_args()
    try:
        if args.command == "build":
            _build_command(args.request, args.output)
        else:
            _validate_command(args.manifest, args.allow_stale_commit)
    except ManifestError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())