"""Fault-injection tests for the process-control manifest verifier."""

# Implements: validation/process-control.yaml (process-control currency)
# Constitutional basis: C-023, C-059, C-065, C-071, C-080

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from verify_process_control import (
    MANIFEST,
    SCHEMA,
    expected_version,
    file_digest,
    load_manifest,
    refresh,
    revision_violations,
    violations,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *arguments],
        cwd=root,
        capture_output=True,
        check=True,
    )


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    write(tmp_path, "constitution/BOOTSTRAP.md", "bootstrap v1\n")
    write(tmp_path, "scripts/prepare.py", "prepare v1\n")
    manifest = {
        "schema": "stale-schema",
        "authoritative_ref": "origin/main",
        "required_controls": {
            "process_baseline": {"sources": ["constitution/BOOTSTRAP.md"], "outcome": "baseline"},
            "exact_head_handoff": {"sources": ["constitution/BOOTSTRAP.md", "scripts/prepare.py"], "outcome": "head"},
        },
    }
    write(tmp_path, MANIFEST.as_posix(), yaml.safe_dump(manifest, sort_keys=False))
    assert refresh(tmp_path) is True
    return tmp_path


def test_refreshed_manifest_is_current_and_refresh_is_idempotent(tree: Path) -> None:
    manifest = load_manifest(tree)

    assert violations(tree, manifest) == []
    assert (manifest["schema"], manifest["revision"]) == (SCHEMA, 1)
    assert manifest["version"] == expected_version(1, manifest["source_digests"])
    assert sorted(manifest["source_digests"]) == ["constitution/BOOTSTRAP.md", "scripts/prepare.py"]
    assert refresh(tree) is False


def test_edited_source_is_stale_until_refresh_bumps_the_revision(tree: Path) -> None:
    write(tree, "scripts/prepare.py", "prepare v2\n")

    assert any("stale digest for scripts/prepare.py" in item for item in violations(tree, load_manifest(tree)))
    assert refresh(tree) is True
    manifest = load_manifest(tree)
    assert manifest["revision"] == 2
    assert violations(tree, manifest) == []


def test_missing_source_and_tampered_version_are_rejected(tree: Path) -> None:
    manifest = load_manifest(tree)
    manifest["version"] = "r001-000000000000"
    assert any("version must equal" in item for item in violations(tree, manifest))

    (tree / "scripts/prepare.py").unlink()
    assert any("missing: scripts/prepare.py" in item for item in violations(tree, manifest))


def test_pinned_set_must_match_control_sources(tree: Path) -> None:
    manifest = load_manifest(tree)
    manifest["source_digests"]["unreferenced.md"] = file_digest(tree, "constitution/BOOTSTRAP.md")

    assert any("exactly the sources" in item for item in violations(tree, manifest))


def test_base_comparison_requires_a_higher_revision_when_sources_changed(tree: Path) -> None:
    git(tree, "init", "-q", "-b", "main")
    git(tree, "add", ".")
    git(tree, "commit", "-q", "-m", "base")
    write(tree, "scripts/prepare.py", "prepare v2\n")

    assert refresh(tree) is True
    refreshed = load_manifest(tree)
    assert revision_violations(tree, refreshed, "main") == []

    refreshed["revision"] = 1
    assert any("does not exceed" in item for item in revision_violations(tree, refreshed, "main"))


def test_repository_manifest_is_current() -> None:
    manifest = load_manifest(REPO_ROOT)

    assert violations(REPO_ROOT, manifest) == []
    assert manifest["authoritative_ref"] == "origin/main"
    assert {
        "process_baseline",
        "requirement_intake",
        "story_commentary",
        "docker_execution",
        "exact_head_handoff",
        "resource_governance",
        "validation_speed",
        "state_currency",
    } <= set(manifest["required_controls"])
