"""Focused tests for the low-risk constitutional fast-path manifest tool."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import constitutional_fast_path as fast_path

CURRENT_COMMIT = "a" * 40


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for relative_path in (
        "constitution/BOOTSTRAP.md",
        "constitution/PROJECT_STATE.md",
        "README.md",
        "knowledge/index.md",
        "sprint-context/index.json",
        "strategy/existing.md",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {relative_path}\n", encoding="utf-8")
    monkeypatch.setattr(fast_path, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(fast_path, "_git_head", lambda: CURRENT_COMMIT)
    return tmp_path


@pytest.fixture
def valid_request() -> dict:
    return {
        "task_id": "FAST-001",
        "task_class": "orchestration_preparation",
        "goal_id": "GOAL-005",
        "work_contract": "WC-034",
        "office": "INST-013",
        "decision_space": "Prepare a bounded context manifest only",
        "bootstrap": {
            "completed": True,
            "status": "READY",
            "files_read": list(fast_path.REQUIRED_BOOTSTRAP_FILES),
        },
        "retrieval": {
            "mode": "index+rag",
            "index_path": "sprint-context/index.json",
            "query": "GOAL-005 low-risk orchestration context",
        },
        "sources": [
            {
                "path": "constitution/PROJECT_STATE.md",
                "section": "current checkpoint",
                "provenance": "current_checkpoint",
                "retrieved_via": "rag",
                "retrieval_score": 0.97,
                "max_tokens": 900,
            },
            {
                "path": "knowledge/index.md",
                "section": "relevant claims",
                "provenance": "authoritative_source",
                "retrieved_via": "index",
                "max_tokens": 600,
            },
        ],
        "relevant_claims": ["C-077", "C-051"],
        "relevant_adrs": ["ADR-019"],
        "write_paths": ["strategy/fast-path-checkpoint.md"],
        "validations": ["git diff --check", "verify source paths"],
        "risk_flags": {flag: False for flag in fast_path.RISK_FLAGS},
        "model_hint": "auto",
    }


def test_build_and_validate_manifest(repository: Path, valid_request: dict) -> None:
    manifest = fast_path.build_manifest(valid_request, generated_utc="2026-08-10T18:00:00+00:00")

    fast_path.validate_manifest(manifest)

    assert manifest["source_commit"] == CURRENT_COMMIT
    assert manifest["status"] == "ROUTED_LOW_RISK"
    assert manifest["relevant_claims"] == ["C-051", "C-077"]
    assert manifest["token_budget"] == {
        "manifest_tokens": 500,
        "source_tokens": 1_500,
        "total_tokens": 2_000,
        "limit": 4_500,
        "budget_ok": True,
    }


def test_rejects_incomplete_bootstrap(repository: Path, valid_request: dict) -> None:
    valid_request["bootstrap"]["files_read"] = ["README.md", "constitution/PROJECT_STATE.md"]

    with pytest.raises(fast_path.ManifestError, match="mandatory sequence exactly"):
        fast_path.build_manifest(valid_request)


def test_rejects_any_enabled_risk(repository: Path, valid_request: dict) -> None:
    valid_request["risk_flags"]["application_implementation"] = True

    with pytest.raises(fast_path.ManifestError, match="ordinary constitutional path required"):
        fast_path.build_manifest(valid_request)


def test_rejects_unknown_or_missing_risk_flags(repository: Path, valid_request: dict) -> None:
    del valid_request["risk_flags"]["customer_rights"]
    valid_request["risk_flags"]["invented_flag"] = False

    with pytest.raises(fast_path.ManifestError, match="exact risk set"):
        fast_path.build_manifest(valid_request)


@pytest.mark.parametrize(
    "write_path",
    [
        "src/business-platform/main.py",
        "adr/ADR-999.md",
        "constitution/PROJECT_STATE.md",
        ".github/skills/fast-path/SKILL.md",
        "../outside.md",
    ],
)
def test_rejects_unsafe_write_targets(repository: Path, valid_request: dict, write_path: str) -> None:
    valid_request["write_paths"] = [write_path]

    with pytest.raises(
        fast_path.ManifestError,
        match=r"ordinary path|required path|normalized repository-relative",
    ):
        fast_path.build_manifest(valid_request)


def test_rejects_context_budget_overflow(repository: Path, valid_request: dict) -> None:
    valid_request["sources"] = [
        {
            "path": "knowledge/index.md",
            "section": f"section {index}",
            "provenance": "authoritative_source",
            "retrieved_via": "index",
            "max_tokens": 1_500,
        }
        for index in range(3)
    ]

    with pytest.raises(fast_path.ManifestError, match="context budget exceeded"):
        fast_path.build_manifest(valid_request)


def test_rejects_missing_source(repository: Path, valid_request: dict) -> None:
    valid_request["sources"][0]["path"] = "strategy/missing.md"

    with pytest.raises(fast_path.ManifestError, match="does not exist"):
        fast_path.build_manifest(valid_request)


def test_rejects_rag_result_without_score(repository: Path, valid_request: dict) -> None:
    del valid_request["sources"][0]["retrieval_score"]

    with pytest.raises(fast_path.ManifestError, match="retrieval_score is required"):
        fast_path.build_manifest(valid_request)


def test_rejects_stale_manifest(repository: Path, valid_request: dict) -> None:
    manifest = fast_path.build_manifest(valid_request)
    manifest["source_commit"] = "b" * 40

    with pytest.raises(fast_path.ManifestError, match="source_commit is stale"):
        fast_path.validate_manifest(manifest)

    fast_path.validate_manifest(manifest, require_current_commit=False)


def test_rejects_tampered_budget(repository: Path, valid_request: dict) -> None:
    manifest = fast_path.build_manifest(valid_request)
    manifest["token_budget"]["source_tokens"] = 1

    with pytest.raises(fast_path.ManifestError, match="token_budget"):
        fast_path.validate_manifest(manifest)


def test_build_command_contains_output_to_fast_path_directory(
    repository: Path, valid_request: dict
) -> None:
    request_path = repository / "request.json"
    request_path.write_text(json.dumps(valid_request), encoding="utf-8")

    with pytest.raises(fast_path.ManifestError, match="output"):
        fast_path._build_command(request_path, repository / "strategy" / "manifest.json")

    output_path = repository / "sprint-context" / "fast-path" / "manifest.json"
    fast_path._build_command(request_path, output_path)
    assert output_path.is_file()