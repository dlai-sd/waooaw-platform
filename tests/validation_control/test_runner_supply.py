"""WC-104 canonical runner supply contracts."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.1-4.4
# Constitutional basis: C-023, C-059, C-071, C-080, C-086

import json
from pathlib import Path

import pytest

from validation_control.runner_supply import (
    build_supply_manifest,
    create_context,
    load_supply_config,
    runner_specification,
    validate_supply_manifest,
)


def fixture_repository(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    (tmp_path / "Dockerfile").write_text("FROM example@sha256:" + "a" * 64, encoding="utf-8")
    (tmp_path / "lock.txt").write_text("locked", encoding="utf-8")
    config = {
        "schema": "waooaw.runner-supply/v1",
        "runners": {
            "python": {
                "dockerfile": "Dockerfile",
                "base_image_digest": "sha256:" + "a" * 64,
                "system_packages": ["git"],
                "build_arguments": {},
                "platform": "linux/amd64",
                "context_inputs": ["Dockerfile", "lock.txt"],
            }
        },
    }
    return tmp_path, config


def test_repository_supply_config_resolves_all_four_narrow_contexts() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_supply_config(root / "validation/runner-supply.json")

    assert set(config["runners"]) == {"python", "dotnet", "typescript", "full"}
    for runner_id in config["runners"]:
        specification = runner_specification(config, root, runner_id)
        assert specification["identity"].startswith("sha256:")
        assert all(not path.startswith(("src/", "tests/")) or path.endswith(".csproj") for path in specification["identity_inputs"]["context_manifest"])


def test_context_and_identity_change_only_for_declared_inputs(tmp_path: Path) -> None:
    repository, config = fixture_repository(tmp_path)
    original = runner_specification(config, repository, "python")
    (repository / "source.py").write_text("unrelated", encoding="utf-8")
    assert runner_specification(config, repository, "python")["identity"] == original["identity"]

    (repository / "lock.txt").write_text("changed", encoding="utf-8")
    changed = runner_specification(config, repository, "python")
    assert changed["identity"] != original["identity"]

    context = repository / "context"
    create_context(repository, context, changed)
    assert sorted(str(path.relative_to(context)) for path in context.rglob("*") if path.is_file()) == [
        "Dockerfile",
        "lock.txt",
    ]


def test_missing_context_input_fails_closed(tmp_path: Path) -> None:
    repository, config = fixture_repository(tmp_path)
    (repository / "lock.txt").unlink()

    with pytest.raises(ValueError, match="required input is missing"):
        runner_specification(config, repository, "python")


def test_manifest_accepts_one_producer_and_rejects_mutable_or_mismatched_supply(tmp_path: Path) -> None:
    repository, config = fixture_repository(tmp_path)
    specification = runner_specification(config, repository, "python")
    manifest = build_supply_manifest(
        specification,
        image_repository="ghcr.io/dlai-sd/validation-runner-python",
        oci_digest="sha256:" + "d" * 64,
        provenance_reference="attestation-123",
        producer_run="run-123",
        cache_outcome="built",
        build_count=1,
    )

    assert validate_supply_manifest(manifest, specification).endswith("@sha256:" + "d" * 64)
    for key, value in (
        ("runner_identity", "sha256:" + "e" * 64),
        ("oci_digest", "latest"),
        ("provenance_reference", ""),
        ("build_count", 2),
        ("image_repository", "ghcr.io/dlai-sd/runner:latest"),
    ):
        invalid = json.loads(json.dumps(manifest))
        invalid[key] = value
        with pytest.raises(ValueError):
            validate_supply_manifest(invalid, specification)