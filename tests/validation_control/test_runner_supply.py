"""WC-104 canonical runner supply contracts."""

# Implements: work-contracts/WC-104-end-to-end-docker-runner-supply.md §4.1-4.4
# Constitutional basis: C-023, C-059, C-071, C-080, C-086

import json
from pathlib import Path
import re

import pytest
import yaml

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
        assert all(
            not path.startswith(("src/", "tests/")) or path.endswith(".csproj")
            for path in specification["identity_inputs"]["context_manifest"]
        )


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
        supply_duration_ms=1200,
    )

    assert validate_supply_manifest(manifest, specification).endswith("@sha256:" + "d" * 64)
    for key, value in (
        ("runner_identity", "sha256:" + "e" * 64),
        ("oci_digest", "latest"),
        ("provenance_reference", ""),
        ("build_count", 2),
        ("cache_outcome", "registry-hit"),
        ("supply_duration_ms", -1),
        ("image_repository", "ghcr.io/dlai-sd/runner:latest"),
    ):
        invalid = json.loads(json.dumps(manifest))
        invalid[key] = value
        with pytest.raises(ValueError):
            validate_supply_manifest(invalid, specification)


def test_hosted_workflows_use_one_supply_graph_and_never_build_in_consumers() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow_paths = [
        root / ".github/workflows/ci.yaml",
        root / ".github/workflows/code-quality.yaml",
        root / ".github/workflows/integration-tests.yaml",
        root / ".github/workflows/e2e-acceptance-tests.yaml",
    ]

    for workflow_path in workflow_paths:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        jobs = workflow["jobs"]
        assert jobs["runner-supply"]["uses"] == "./.github/workflows/validation-runner-supply.yaml"
        for job_id, job in jobs.items():
            if not isinstance(job, dict) or "steps" not in job:
                continue
            rendered = json.dumps(job)
            if "docker compose" not in rendered or "test-runner" not in rendered:
                continue
            for step in job["steps"]:
                command = step.get("run", "") if isinstance(step, dict) else ""
                assert re.search(r"docker compose.*\bbuild\b.*test-runner", command) is None, job_id
            needs = job.get("needs", [])
            needs = [needs] if isinstance(needs, str) else needs
            assert "runner-supply" in needs, job_id
            assert "./.github/actions/use-validation-runner" in rendered, job_id


def test_reusable_validation_plan_preserves_consumer_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    source = (root / ".github/workflows/validation-plan.yaml").read_text(encoding="utf-8")
    workflow = yaml.safe_load(source)
    plan = workflow["jobs"]["plan"]
    rendered = json.dumps(plan)

    assert "release_required" in workflow[True]["workflow_call"]["outputs"]
    assert plan["outputs"]["release_required"] == "${{ steps.plan.outputs.release_required }}"
    assert rendered.count("./.github/actions/use-validation-runner") == 1
    assert '"runner-id": "full"' in rendered
    assert "wc104-qualification-plan-${{ github.run_id }}" in rendered
    assert "--all-gates" in rendered
    assert '[[ "$EVENT_NAME" == "schedule" ]]' in source
    assert 'git rev-parse "$head_sha^"' in source


def test_code_quality_jobs_execute_catalog_gates() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/code-quality.yaml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load((root / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    catalog_jobs = {
        "commitlint",
        "dotnet-quality",
        "python-quality",
        "scripts-quality",
        "typescript-quality",
        "sql-quality",
        "proto-quality",
        "observability-security",
        "traceability-scan",
        "constitutional-naming",
        "mutation-dotnet",
        "mutation-python",
    }

    assert jobs["validation-plan"]["uses"] == "./.github/workflows/validation-plan.yaml"
    for job_id in catalog_jobs:
        rendered = json.dumps(jobs[job_id])
        assert jobs[job_id]["needs"] == ["runner-supply", "validation-plan"], job_id
        assert "./.github/actions/run-validation-gate" in rendered, job_id
        assert "docker compose" not in rendered, job_id

    assert workflow[True]["schedule"] == [{"cron": "0 0 * * 0"}]

    expected_runners = {
        "quality:commitlint": "typescript",
        "quality:dotnet:constitutional-engine": "dotnet",
        "quality:dotnet:business-platform": "dotnet",
        "quality:python:professional-runtime": "python",
        "quality:python:ai-runtime": "python",
        "quality:scripts": "python",
        "quality:typescript": "typescript",
        "quality:sql": "python",
        "quality:proto": "python",
        "quality:observability": "python",
        "quality:traceability": "python",
        "quality:constitutional-naming": "python",
        "mutation:dotnet": "dotnet",
        "mutation:python": "python",
    }
    assert {gate: catalog["gates"][gate]["runner_id"] for gate in expected_runners} == expected_runners
    rendered_workflow = json.dumps(workflow)
    for gate_id in expected_runners:
        assert gate_id in rendered_workflow

    assert "|| true" in catalog["commands"]["quality-sql"]["shell"]
    assert "test-results/traceability-report.json" in rendered_workflow
    assert "test-results/stryker-ce-results/" in rendered_workflow
    dotnet_mutation = (root / "scripts/validation_control/run_dotnet_mutation_gate.sh").read_text(encoding="utf-8")
    python_mutation = (root / "scripts/validation_control/run_python_mutation_gate.sh").read_text(encoding="utf-8")
    assert "--threshold-high 80 --threshold-low 75 --threshold-break 65" in dotnet_mutation
    assert '"${score:-0}" -lt 60' in python_mutation


def test_integration_jobs_execute_catalog_gates() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/integration-tests.yaml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load((root / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    expected_gates = {
        "integration:multi-tenant": "python",
        "integration:postgres-migrations": "python",
        "integration:dotnet": "dotnet",
        "integration:python": "python",
        "contract:rest": "python",
        "contract:seed-prompts": "python",
        "security:prompt-injection": "python",
    }

    assert jobs["validation-plan"]["uses"] == "./.github/workflows/validation-plan.yaml"
    for job_id in (
        "multi-tenant-isolation",
        "service-integration",
        "contract-rest",
        "seed-prompts-contract",
        "prompt-injection",
    ):
        rendered = json.dumps(jobs[job_id])
        assert "runner-supply" in jobs[job_id]["needs"], job_id
        assert "validation-plan" in jobs[job_id]["needs"], job_id
        assert "./.github/actions/run-validation-gate" in rendered, job_id
        assert "docker compose" not in rendered, job_id
        assert '"runner-id"' not in rendered, job_id

    assert {gate: catalog["gates"][gate]["runner_id"] for gate in expected_gates} == expected_gates
    rendered_workflow = json.dumps(workflow)
    for gate_id in expected_gates:
        assert gate_id in rendered_workflow
    assert jobs["multi-tenant-isolation"]["steps"][-1]["if"] == "always()"
    assert catalog["commands"]["contract-rest"]["execution"] == "host"
    assert "host.docker.internal:5432/waooaw_test" in catalog["commands"]["integration-multi-tenant"]["shell"]
    assert "Host=host.docker.internal;Port=5432" in catalog["commands"]["integration-dotnet"]["shell"]
    assert "--pull never test-runner-python" in (
        root / "scripts/validation_control/run_rest_contract_gate.sh"
    ).read_text(encoding="utf-8")


def test_supply_workflow_serializes_producers_and_consumers_verify_digests() -> None:
    root = Path(__file__).resolve().parents[2]
    supply = (root / ".github/workflows/validation-runner-supply.yaml").read_text(encoding="utf-8")
    consumer = (root / ".github/actions/use-validation-runner/action.yml").read_text(encoding="utf-8")

    assert "group: wc104-runner-supply-${{ matrix.runner }}" in supply
    assert "matrix:\n        runner: [python, dotnet, typescript, full]" in supply
    assert "cache-from: type=gha,scope=wc104-${{ matrix.runner }}-${{ steps.identity.outputs.identity }}" in supply
    assert "cache-to: type=gha,mode=max,scope=wc104-${{ matrix.runner }}-${{ steps.identity.outputs.identity }}" in supply
    assert 'resolution_tag="candidate-${candidate_sha}-${identity#sha256:}"' in supply
    assert 'imagetools inspect "$REPOSITORY:$RESOLUTION_TAG"' in supply
    assert "candidate-${GITHUB_RUN_ID}" not in supply
    assert "actions/attest-build-provenance@v2" in supply
    assert 'gh attestation verify "oci://$image"' in consumer
    assert 'docker pull "$image"' in consumer
    assert "@$digest" in supply


def test_web_ci_executes_catalog_gate_without_duplicate_command_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["test-web"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    assert "./.github/actions/run-validation-gate" in rendered
    assert '"gate-id": "test-web"' in rendered
    assert '"runner-id": "typescript"' not in rendered
    assert "tsc --noEmit" not in rendered
    assert "jest --runInBand" not in rendered
    assert job["steps"][1]["continue-on-error"] is True
    assert job["steps"][-1]["if"] == "steps.runner-build.outcome != 'success'"


def test_dotnet_ci_executes_catalog_gates_without_duplicate_commands_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["test-dotnet"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    assert all(set(row) == {"service", "gate"} for row in job["strategy"]["matrix"]["include"])
    assert "./.github/actions/run-validation-gate" in rendered
    assert '"runner-id": "dotnet"' not in rendered
    assert "dotnet restore" not in rendered
    assert "dotnet test" not in rendered
    assert "line-rate" not in rendered


def test_python_ci_executes_catalog_gates_without_duplicate_commands_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["test-python"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    assert all(set(row) == {"service", "gate"} for row in job["strategy"]["matrix"]["include"])
    assert "./.github/actions/run-validation-gate" in rendered
    assert '"runner-id": "python"' not in rendered
    assert "matrix.source" not in rendered
    assert "matrix.tests" not in rendered
    assert "matrix.mypy_path" not in rendered
    assert "docker compose" not in rendered


def test_release_ci_executes_catalog_gate_without_duplicate_command_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["release-qualification"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    assert "./.github/actions/run-validation-gate" in rendered
    assert '"gate-id": "release-qualification"' in rendered
    assert '"runner-id": "full"' not in rendered
    assert "scripts/run_release_qualification.sh" not in rendered


def test_dependency_ci_executes_catalog_gates_without_duplicate_commands_or_runner_mappings() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load((root / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["dep-scan"]
    rendered = json.dumps(job)
    split_gates = {"dep-scan:python", "dep-scan:dotnet", "dep-scan:typescript"}

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    assert rendered.count("./.github/actions/run-validation-gate") == 3
    assert {
        step["with"]["gate-id"]
        for step in job["steps"]
        if step.get("uses") == "./.github/actions/run-validation-gate"
    } == split_gates
    assert split_gates.issubset(catalog["full_gates"])
    assert "dep-scan" not in catalog["full_gates"]
    assert all(step.get("continue-on-error") is True for step in job["steps"] if step.get("id", "").endswith("-scan"))
    assert job["steps"][-1]["name"] == "Enforce catalog dependency scan results"
    assert '"runner-id"' not in rendered
    assert "pip-audit -r" not in rendered
    assert "dotnet list" not in rendered
    assert "pnpm audit" not in rendered


def test_license_ci_executes_advisory_catalog_gate_without_duplicate_command_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["license-check"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    gate_step = next(step for step in job["steps"] if step.get("uses") == "./.github/actions/run-validation-gate")
    assert gate_step["with"]["gate-id"] == "license-check"
    assert gate_step["continue-on-error"] is True
    assert '"runner-id"' not in rendered
    assert "pip install" not in rendered
    assert "pip-licenses" not in rendered
    assert "docker compose" not in rendered


def test_c059_ci_executes_catalog_gate_without_duplicate_command_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["constitutional-commit-gate"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    gate_step = next(step for step in job["steps"] if step.get("uses") == "./.github/actions/run-validation-gate")
    assert gate_step["with"]["gate-id"] == "constitutional-commit-gate"
    assert '"runner-id"' not in rendered
    assert "python scripts/validate_c059.py" not in rendered
    assert "docker compose" not in rendered


def test_c065_ci_retries_catalog_gate_without_duplicate_command_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    action = yaml.safe_load((root / ".github/actions/run-validation-gate/action.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["author-review-gate"]
    rendered = json.dumps(job)
    action_rendered = json.dumps(action)
    gate_steps = [step for step in job["steps"] if step.get("uses") == "./.github/actions/run-validation-gate"]

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    assert len(gate_steps) == 1
    assert all(step["with"]["gate-id"] == "author-review-gate" for step in gate_steps)
    assert gate_steps[0]["with"]["attempts"] == "3"
    assert gate_steps[0]["with"]["retry-delay-seconds"] == "5"
    assert '"runner-id"' not in rendered
    assert "python scripts/validate_author_review.py" not in rendered
    assert "python scripts/validate_runtime_lifecycle_evidence.py" not in rendered
    assert "docker compose" not in rendered
    assert action_rendered.count("./.github/actions/use-validation-runner") == 1
    assert "attempt <= ATTEMPTS" in action_rendered
    assert "Unable to refresh PR metadata for attempt $attempt" in action_rendered


def test_spec_lint_ci_executes_catalog_gate_without_duplicate_commands() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["spec-lint"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    gate_step = next(step for step in job["steps"] if step.get("uses") == "./.github/actions/run-validation-gate")
    assert gate_step["with"]["gate-id"] == "spec-lint"
    assert "stoplight/spectral" not in rendered
    assert "bufbuild/buf" not in rendered
    assert "docker run" not in rendered


def test_c066_ci_executes_catalog_gate_without_duplicate_command_or_runner_mapping() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = yaml.safe_load((root / ".github/workflows/ci.yaml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["authorization-tier-check"]
    rendered = json.dumps(job)

    assert set(job["needs"]) == {"runner-supply", "validation-plan"}
    gate_step = next(step for step in job["steps"] if step.get("uses") == "./.github/actions/run-validation-gate")
    assert gate_step["with"]["gate-id"] == "authorization-tier-check"
    assert '"runner-id"' not in rendered
    assert 'test "$BASE_BRANCH" = "main"' not in rendered
    assert "docker compose" not in rendered


def test_every_runner_base_is_digest_pinned_and_has_locked_package_caches() -> None:
    root = Path(__file__).resolve().parents[2]
    config = load_supply_config(root / "validation/runner-supply.json")

    for runner in config["runners"].values():
        dockerfile = (root / runner["dockerfile"]).read_text(encoding="utf-8")
        from_lines = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]
        assert from_lines
        assert all("@sha256:" in line for line in from_lines)
        if runner["system_packages"]:
            assert "target=/var/cache/apt,sharing=locked" in dockerfile
    assert "wc104-python-pip" in (root / config["runners"]["python"]["dockerfile"]).read_text()
    assert "wc104-dotnet-nuget" in (root / config["runners"]["dotnet"]["dockerfile"]).read_text()
    assert "wc104-typescript-pnpm" in (root / config["runners"]["typescript"]["dockerfile"]).read_text()
    python_runner = (root / config["runners"]["python"]["dockerfile"]).read_text()
    assert "COPY --from=buf /usr/local/bin/buf /usr/local/bin/buf" in python_runner
