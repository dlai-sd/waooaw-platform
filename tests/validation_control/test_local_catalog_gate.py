"""Behavior contracts for local WC-104 catalog execution."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from validation_control import local_catalog_gate


IDENTITY = "sha256:" + "a" * 64
IMAGE_ID = "sha256:" + "b" * 64


def specification() -> dict[str, object]:
    return {
        "runner_id": "python",
        "dockerfile": "Dockerfile",
        "identity": IDENTITY,
        "identity_inputs": {"platform": "linux/amd64", "context_manifest": {}},
    }


def test_local_fallback_builds_once_then_reuses_identity_image(monkeypatch, tmp_path: Path) -> None:
    inspected = iter((None, IMAGE_ID, IMAGE_ID))
    builds: list[list[str]] = []
    runner_digest = "sha256:" + "c" * 64
    monkeypatch.setattr(local_catalog_gate, "image_id", lambda image, repository: next(inspected))
    monkeypatch.setattr(local_catalog_gate, "docker_executable", lambda: "/usr/bin/docker")
    monkeypatch.setattr(local_catalog_gate, "create_context", lambda repository, context, spec: context.mkdir(parents=True))

    def build(command: list[str], **unused: object) -> SimpleNamespace:
        builds.append(command)
        metadata = Path(command[command.index("--metadata-file") + 1])
        metadata.write_text(json.dumps({"containerimage.digest": runner_digest}), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        build,
    )

    first = local_catalog_gate.local_fallback_runner(tmp_path, "python", specification())
    second = local_catalog_gate.local_fallback_runner(tmp_path, "python", specification())

    assert first[1:] == (IMAGE_ID, runner_digest, 1)
    assert second[1:] == (IMAGE_ID, runner_digest, 0)
    assert len(builds) == 1
    assert builds[0][0].endswith("docker")
    assert builds[0][1:3] == ["buildx", "build"]
    assert builds[0][builds[0].index("--platform") + 1] == "linux/amd64"


def test_untrusted_manifest_is_a_miss_without_pull(monkeypatch, tmp_path: Path) -> None:
    manifest = tmp_path / "test-results/wc104/runner-manifests/python.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"schema": "untrusted"}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_REPOSITORY", "dlai-sd/waooaw")
    monkeypatch.setattr(local_catalog_gate.shutil, "which", lambda executable: f"/usr/bin/{executable}")
    commands: list[list[str]] = []
    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        lambda command, **unused: commands.append(command) or SimpleNamespace(returncode=0),
    )

    assert local_catalog_gate.trusted_runner(tmp_path, "python", specification()) is None
    assert commands == []


def test_required_services_bind_rendered_images_to_immutable_ids(monkeypatch, tmp_path: Path) -> None:
    compose = {
        "services": {
            "postgres": {"image": "pgvector/pgvector:pg16"},
            "runner": {"image": "runner:local"},
        }
    }
    commands: list[list[str]] = []
    monkeypatch.setattr(local_catalog_gate, "docker_executable", lambda: "/usr/bin/docker")
    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        lambda command, **unused: commands.append(command) or SimpleNamespace(returncode=0, stdout=json.dumps(compose)),
    )
    monkeypatch.setattr(
        local_catalog_gate,
        "image_id",
        lambda image, repository: IMAGE_ID if image == "pgvector/pgvector:pg16" else None,
    )

    identities = local_catalog_gate.required_service_identities(
        tmp_path,
        {"profile": "test-dotnet", "required_services": ["postgres"]},
    )

    assert identities == {"postgres": IMAGE_ID}
    assert commands == [["/usr/bin/docker", "compose", "--profile", "test-dotnet", "config", "--format", "json"]]


def test_required_service_without_local_image_fails_closed(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(local_catalog_gate, "docker_executable", lambda: "/usr/bin/docker")
    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        lambda command, **unused: SimpleNamespace(
            returncode=0,
            stdout=json.dumps({"services": {"postgres": {"image": "postgres:missing"}}}),
        ),
    )
    monkeypatch.setattr(local_catalog_gate, "image_id", lambda image, repository: None)

    with pytest.raises(ValueError, match="required service image is unavailable: postgres"):
        local_catalog_gate.required_service_identities(
            tmp_path,
            {"profile": "test-dotnet", "required_services": ["postgres"]},
        )


def test_rollback_bypasses_trusted_manifest_and_existing_local_image(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WC104_DISABLE_REGISTRY_REUSE", "1")
    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        lambda *unused, **kwargs: pytest.fail("rollback attempted trusted registry consumption"),
    )

    assert local_catalog_gate.trusted_runner(tmp_path, "python", specification()) is None

    runner_digest = "sha256:" + "c" * 64
    inspected = iter((IMAGE_ID, IMAGE_ID))
    builds: list[list[str]] = []
    monkeypatch.setattr(local_catalog_gate, "image_id", lambda image, repository: next(inspected))
    monkeypatch.setattr(local_catalog_gate, "docker_executable", lambda: "/usr/bin/docker")
    monkeypatch.setattr(local_catalog_gate, "create_context", lambda repository, context, spec: context.mkdir(parents=True))

    def build(command: list[str], **unused: object) -> SimpleNamespace:
        builds.append(command)
        metadata = Path(command[command.index("--metadata-file") + 1])
        metadata.write_text(json.dumps({"containerimage.digest": runner_digest}), encoding="utf-8")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(local_catalog_gate.subprocess, "run", build)

    result = local_catalog_gate.local_fallback_runner(tmp_path, "python", specification())

    assert result[1:] == (IMAGE_ID, runner_digest, 1)
    assert len(builds) == 1


def test_host_gate_executes_plan_without_resolving_runner(monkeypatch, tmp_path: Path) -> None:
    catalog = {
        "schema": "waooaw.validation-catalog/v1",
        "version": "test",
        "runners": {"python": {"compose_service": "runner", "profile": "test"}},
        "components": {},
        "commands": {
            "host": {
                "shell": "true",
                "execution": "host",
                "runner_required": False,
                "tool_digest": "sha256:" + "d" * 64,
            }
        },
        "gates": {
            "host": {
                "runner_id": "python",
                "command_id": "host",
                "resources": {},
                "retry_policy": "none",
                "artifacts": {},
            }
        },
    }
    validation = tmp_path / "validation"
    validation.mkdir()
    (validation / "engineering-validation.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    executor = tmp_path / "scripts/validation_control/catalog_execution.py"
    executor.parent.mkdir(parents=True)
    executor.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        local_catalog_gate,
        "load_supply_config",
        lambda unused: pytest.fail("host execution resolved a validation runner"),
    )
    monkeypatch.setattr(local_catalog_gate, "orchestration_preflight", lambda unused: None)
    monkeypatch.setattr(local_catalog_gate, "docker_socket_group", lambda: "321")
    captured: list[list[str]] = []
    captured_environment: dict[str, str] = {}

    def execute(command: list[str], **kwargs: object) -> SimpleNamespace:
        captured.append(command)
        captured_environment.update(kwargs["env"])
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(
        local_catalog_gate.subprocess,
        "run",
        execute,
    )

    assert local_catalog_gate.execute_gate(tmp_path, "host", "a" * 40, "b" * 40, tmp_path) == 0
    assert "--image-id" not in captured[0]
    assert captured_environment["DOCKER_GID"] == "321"
    assert captured_environment["GOAL006_EVIDENCE_DIR"] == str(tmp_path / "test-results/wc104/goal006-local-azure-runtime")
    plan = json.loads((tmp_path / "test-results/wc104/local-plans/host.json").read_text(encoding="utf-8"))
    assert plan["nodes"][0]["command"] == "true"
    records = list((tmp_path / "test-results/wc109/runs").glob("**/wc109-execution.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text(encoding="utf-8"))
    assert record["catalog_controlled"] is True
    assert record["authority"] == "diagnostic-local-only"
    assert record["head_sha"] == "a" * 40
    assert record["base_sha"] == "b" * 40
    assert record["runner_build_events"] == 0
    assert record["product_image_build_events"] == 0
    assert record["service_identities"] == {}
    envelopes = list((tmp_path / "test-results/wc109/runs").glob("**/evidence-envelope.json"))
    assert len(envelopes) == 1
    envelope = json.loads(envelopes[0].read_text(encoding="utf-8"))
    assert envelope["result"] == "PASS"
    assert envelope["routing_class"] == "NONE"
    assert envelope["disposition"] == "executed"
    assert envelope["invocation"]["source"] == "catalog"
    artifact_root = records[0].parent
    assert (artifact_root / "wc104/metadata/base-sha.txt").read_text() == "b" * 40 + "\n"
    assert (artifact_root / "wc104/metadata/head-sha.txt").read_text() == "a" * 40 + "\n"
    assert (artifact_root / "wc104/c059/base-sha.txt").read_text() == "b" * 40 + "\n"
    assert not (artifact_root / "wc104/c059/pr-body.md").exists()


def test_requirement_scope_is_explicit_deduplicated_and_repository_relative(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires --changed-file"):
        local_catalog_gate.write_requirement_scope(tmp_path, [])

    with pytest.raises(ValueError, match="repository-relative"):
        local_catalog_gate.write_requirement_scope(tmp_path, ["../outside.yaml"])

    local_catalog_gate.write_requirement_scope(
        tmp_path,
        [
            "work-contracts/WC-109-requirements.yaml",
            "work-contracts/WC-109-agentic-validation-implementation.md",
            "work-contracts/WC-109-requirements.yaml",
        ],
    )

    assert (tmp_path / "test-results/wc102/changed-files.txt").read_text(encoding="utf-8") == (
        "work-contracts/WC-109-agentic-validation-implementation.md\nwork-contracts/WC-109-requirements.yaml\n"
    )

    isolated = tmp_path / "test-results/wc109/runs/namespace/gate"
    local_catalog_gate.write_requirement_scope(tmp_path, ["constitution/PROJECT_STATE.md"], isolated)
    assert (isolated / "wc102/changed-files.txt").read_text(encoding="utf-8") == "constitution/PROJECT_STATE.md\n"


def test_constitutional_inputs_are_staged_inside_isolated_artifact_root(tmp_path: Path) -> None:
    isolated = tmp_path / "test-results/wc109/runs/namespace/constitutional-commit-gate"
    body = tmp_path / "pr-body.md"
    body.write_text("Work Contract: WC-109\n", encoding="utf-8")

    local_catalog_gate.write_commit_metadata(tmp_path, "b" * 40, "a" * 40, isolated)
    local_catalog_gate.write_pr_body(body, "constitutional-commit-gate", isolated)

    assert (isolated / "wc104/c059/base-sha.txt").read_text(encoding="utf-8") == "b" * 40 + "\n"
    assert (isolated / "wc104/c059/head-sha.txt").read_text(encoding="utf-8") == "a" * 40 + "\n"
    assert (isolated / "wc104/c059/pr-body.md").read_text(encoding="utf-8") == "Work Contract: WC-109\n"
    assert not (tmp_path / "test-results/wc104/c059/base-sha.txt").exists()


def test_constitutional_inputs_require_explicit_pr_body(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires --pr-body-file"):
        local_catalog_gate.write_pr_body(None, "constitutional-commit-gate", tmp_path)

    with pytest.raises(ValueError, match="requires --pr-body-file"):
        local_catalog_gate.write_pr_body(None, "author-review-gate", tmp_path)

    local_catalog_gate.write_pr_body(None, "build", tmp_path)


def test_authorization_context_is_staged_inside_isolated_artifact_root(tmp_path: Path) -> None:
    isolated = tmp_path / "test-results/wc109/runs/namespace/authorization-tier-check"

    local_catalog_gate.write_authorization_context(
        "authorization-tier-check",
        isolated,
        "main",
        "0",
        "dlai-sd/waooaw",
    )

    assert (isolated / "wc104/c066/base-branch.txt").read_text(encoding="utf-8") == "main\n"
    assert (isolated / "wc104/c066/pr-number.txt").read_text(encoding="utf-8") == "0\n"
    assert (isolated / "wc104/c066/repository.txt").read_text(encoding="utf-8") == "dlai-sd/waooaw\n"


def test_authorization_context_requires_explicit_pr_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires explicit PR context"):
        local_catalog_gate.write_authorization_context(
            "authorization-tier-check",
            tmp_path,
            "main",
            None,
            "dlai-sd/waooaw",
        )

    local_catalog_gate.write_authorization_context("build", tmp_path, None, None, None)


def test_gate_identity_hashes_only_declared_environment(monkeypatch, tmp_path: Path) -> None:
    tool_digest = "sha256:" + "d" * 64
    catalog = {
        "schema": "waooaw.validation-catalog/v1",
        "version": "test-v1",
        "runners": {"python": {"compose_service": "runner", "profile": "test"}},
        "components": {},
        "commands": {
            "host": {
                "shell": "true",
                "execution": "host",
                "runner_required": False,
                "tool_digest": tool_digest,
            }
        },
        "gates": {
            "host": {
                "runner_id": "python",
                "command_id": "host",
                "resources": {},
                "retry_policy": "none",
                "artifacts": {},
                "environment": ["DECLARED"],
            }
        },
    }
    validation = tmp_path / "validation"
    validation.mkdir()
    (validation / "engineering-validation.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    monkeypatch.setenv("DECLARED", "first")
    monkeypatch.setenv("UNDECLARED", "first")
    original = local_catalog_gate.gate_execution_identity(tmp_path, "host", "a" * 40)

    monkeypatch.setenv("UNDECLARED", "second")
    undeclared_changed = local_catalog_gate.gate_execution_identity(tmp_path, "host", "a" * 40)
    monkeypatch.setenv("DECLARED", "second")
    declared_changed = local_catalog_gate.gate_execution_identity(tmp_path, "host", "a" * 40)

    assert original["runner_digest"] == tool_digest
    assert undeclared_changed["environment_digest"] == original["environment_digest"]
    assert declared_changed["environment_digest"] != original["environment_digest"]
    assert original["service_digest"] == local_catalog_gate.hashlib.sha256(b"{}").hexdigest()


def test_gate_identity_changes_with_required_service_image(monkeypatch, tmp_path: Path) -> None:
    catalog = {
        "schema": "waooaw.validation-catalog/v1",
        "version": "test-v1",
        "runners": {"python": {"compose_service": "runner", "profile": "test"}},
        "components": {},
        "commands": {"integration": {"shell": "true"}},
        "gates": {
            "integration": {
                "runner_id": "python",
                "command_id": "integration",
                "resources": {},
                "retry_policy": "none",
                "artifacts": {},
                "required_services": ["postgres"],
            }
        },
    }
    validation = tmp_path / "validation"
    validation.mkdir()
    (validation / "engineering-validation.yaml").write_text(yaml.safe_dump(catalog), encoding="utf-8")
    monkeypatch.setattr(
        local_catalog_gate,
        "resolve_runner",
        lambda repository, runner_id: {"runner_digest": "sha256:" + "d" * 64},
    )
    service_identity = {"postgres": "sha256:" + "e" * 64}
    monkeypatch.setattr(local_catalog_gate, "required_service_identities", lambda repository, node: service_identity)

    identity = local_catalog_gate.gate_execution_identity(tmp_path, "integration", "a" * 40)

    assert (
        identity["service_digest"]
        == local_catalog_gate.hashlib.sha256(
            json.dumps(service_identity, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


def test_runner_backed_execution_requires_exact_image_and_disables_pull() -> None:
    source = (Path(__file__).resolve().parents[2] / "scripts/validation_control/catalog_execution.py").read_text(encoding="utf-8")

    assert '"--pull",\n        "never"' in source
    assert 'raise ValueError("--image-id is required for runner-backed catalog execution")' in source
