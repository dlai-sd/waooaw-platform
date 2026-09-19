from pathlib import Path
import sys
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_pr_body import (  # noqa: E402
    add_runtime_evidence,
    business_platform_gate_required,
    changed_files_digest,
    configuration_digest,
    expected_pr_labels,
    execution_preflight,
    load_runtime_evidence,
    preparation_head,
    prepare_body,
    release_qualification_gate_required,
    run_ci_prechecks,
    runner_digest,
    validate_precheck_evidence,
)
from validate_author_review import validate_author_review  # noqa: E402


HEAD = "a" * 40


def test_prepare_body_canonicalizes_author_review_for_current_head() -> None:
    source = """## Summary

Ready for review.

## Author Review

- [ ] stale wording

**Reviewed Commit:** FULL_40_CHARACTER_HEAD_SHA
**Author Review Result:** PENDING

## Specification Compliance
Content remains.
"""

    prepared = prepare_body(source, HEAD)

    assert validate_author_review(prepared, HEAD) == []
    assert prepared.count("## Author Review") == 1
    assert "## Specification Compliance\nContent remains." in prepared


def test_prepare_body_requires_template_section() -> None:
    try:
        prepare_body("## Summary\n", HEAD)
    except ValueError as error:
        assert "Author Review" in str(error)
    else:
        raise AssertionError("missing Author Review section was accepted")


def test_preparation_head_rejects_unpushed_commit_by_default() -> None:
    try:
        preparation_head("a" * 40, "b" * 40, False)
    except ValueError as error:
        assert "does not match pushed branch HEAD" in str(error)
    else:
        raise AssertionError("unpublished commit was accepted without explicit prebinding")


def test_preparation_head_allows_explicit_existing_pr_prebinding() -> None:
    assert preparation_head("a" * 40, "b" * 40, True) == "a" * 40


def test_loaded_runtime_evidence_must_match_selected_head(tmp_path: Path) -> None:
    evidence_file = tmp_path / "runtime.json"
    evidence_file.write_text('{"commit_sha":"' + ("b" * 40) + '"}', encoding="utf-8")

    try:
        load_runtime_evidence(evidence_file, HEAD)
    except ValueError as error:
        assert "selected branch HEAD" in str(error)
    else:
        raise AssertionError("stale runtime evidence was accepted")


def test_runtime_evidence_is_inserted_before_author_review() -> None:
    source = "## Summary\n\nReady.\n\n## Author Review\n\nPending.\n"
    evidence = {
        "schema": "waooaw.goal006-runtime-lifecycle/v1",
        "passed": True,
        "commit_sha": HEAD,
        "initial_http_status": 503,
        "recovered_http_status": 200,
    }

    prepared = add_runtime_evidence(source, evidence)

    assert prepared.index("## Pre-PR Runtime Evidence") < prepared.index("## Author Review")
    assert '"initial_http_status": 503' in prepared
    assert '"recovered_http_status": 200' in prepared


def test_runtime_evidence_rejects_failed_gate() -> None:
    try:
        add_runtime_evidence("## Author Review\n", {"passed": False})
    except ValueError as error:
        assert "passed=true" in str(error)
    else:
        raise AssertionError("failed runtime evidence was accepted")


def test_business_platform_gate_covers_shared_runtime_and_deployment_paths() -> None:
    for path in (
        "src/business-platform/Program.cs",
        "tests/business-platform.Tests/OwnerGatewayCoverageTests.cs",
        "infrastructure/postgres/init/029_identity.sql",
        "infrastructure/terraform/phase2/modules/workload/main.tf",
        "architecture/reference/api-specs/business-platform.openapi.yaml",
    ):
        assert business_platform_gate_required([path])


def test_business_platform_gate_ignores_unrelated_paths() -> None:
    assert not business_platform_gate_required(["web/components/auth/LoginView.tsx"])


def test_release_qualification_gate_matches_ci_change_paths() -> None:
    for path in (
        "infrastructure/terraform/phase2/modules/workload/main.tf",
        "tests/pipeline/test_wc091_environment_readiness.py",
        "scripts/goal006_release_simulator.py",
        ".github/workflows/ci.yaml",
        "docker-compose.yml",
    ):
        assert release_qualification_gate_required([path])


def test_release_qualification_gate_ignores_application_only_paths() -> None:
    assert not release_qualification_gate_required(["web/components/auth/LoginView.tsx"])


def test_expected_pr_labels_include_lifecycle_and_branch_tier() -> None:
    assert expected_pr_labels("fix/precheck") == (
        "tier:1-bugfix",
        "status:pr-open",
        "awaiting:review",
    )
    assert expected_pr_labels("agent/update/platform") == (
        "tier:3-constitutional",
        "status:pr-open",
        "awaiting:review",
    )
    assert expected_pr_labels("feature/new-flow")[0] == "tier:2-feature"


def test_precheck_evidence_must_match_base_and_head() -> None:
    digest = changed_files_digest(["scripts/example.py"])
    evidence = {
        "schema": "waooaw.pr-prechecks/v3",
        "passed": True,
        "base_sha": "b" * 40,
        "commit_sha": HEAD,
        "changed_file_digest": digest,
        "graph_version": "wc100-prechecks-v2",
        "configuration_digest": "c" * 64,
        "runner_digest": "r" * 64,
    }
    assert validate_precheck_evidence(evidence, "b" * 40, HEAD, digest, "c" * 64, "r" * 64) == evidence

    for base_sha, head in (("c" * 40, HEAD), ("b" * 40, "d" * 40)):
        try:
            validate_precheck_evidence(evidence, base_sha, head, digest, "c" * 64, "r" * 64)
        except ValueError as error:
            assert "selected base and branch HEAD" in str(error)
        else:
            raise AssertionError("stale precheck evidence was accepted")


def test_precheck_evidence_rejects_changed_files_or_graph_version() -> None:
    evidence = {
        "schema": "waooaw.pr-prechecks/v3",
        "passed": True,
        "base_sha": "b" * 40,
        "commit_sha": HEAD,
        "changed_file_digest": "d" * 64,
        "graph_version": "wc100-prechecks-v2",
        "configuration_digest": "c" * 64,
        "runner_digest": "r" * 64,
    }

    for digest, graph_version in (("e" * 64, "wc100-prechecks-v2"), ("d" * 64, "stale")):
        try:
            validate_precheck_evidence(
                evidence,
                "b" * 40,
                HEAD,
                digest,
                "c" * 64,
                "r" * 64,
                graph_version,
            )
        except ValueError as error:
            assert "changed files" in str(error) or "gate graph" in str(error)
        else:
            raise AssertionError("stale precheck evidence was accepted")


def test_precheck_evidence_rejects_configuration_or_runner_mismatch() -> None:
    evidence = {
        "schema": "waooaw.pr-prechecks/v3",
        "passed": True,
        "base_sha": "b" * 40,
        "commit_sha": HEAD,
        "changed_file_digest": "d" * 64,
        "graph_version": "wc100-prechecks-v2",
        "configuration_digest": "c" * 64,
        "runner_digest": "r" * 64,
    }

    for config, runner, expected in (
        ("x" * 64, "r" * 64, "configuration"),
        ("c" * 64, "x" * 64, "runner"),
    ):
        try:
            validate_precheck_evidence(evidence, "b" * 40, HEAD, "d" * 64, config, runner)
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError(f"stale {expected} identity was accepted")


def test_prepare_pr_body_uses_requirement_ledger_validator() -> None:
    source = (ROOT / "scripts/prepare_pr_body.py").read_text(encoding="utf-8")

    assert "validate_changed_ledgers" in source
    assert '"--preflight-only"' in source


def test_run_ci_prechecks_builds_current_gate_graph(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "prepare_pr_body.git", lambda *arguments: "b" * 40 if "--git-common-dir" not in arguments else str(tmp_path)
    )
    monkeypatch.setattr("prepare_pr_body.shutil.which", lambda executable: f"/usr/bin/{executable}")

    def capture(nodes, **arguments):
        captured["nodes"] = nodes
        captured.update(arguments)
        return {"passed": True}

    monkeypatch.setattr("prepare_pr_body.run_prechecks", capture)

    assert run_ci_prechecks("origin/main", HEAD, ["src/business-platform/Program.cs", ".github/workflows/ci.yaml"])["passed"]
    nodes = captured["nodes"]
    assert [node.name for node in nodes] == ["gitleaks", "business_platform", "release_qualification"]
    assert captured["graph_version"] == "wc100-prechecks-v2"
    assert captured["configuration_digest"] == configuration_digest()
    assert captured["runner_digest"] == runner_digest(nodes)


def test_execution_preflight_rejects_wrong_worktree_before_docker(monkeypatch, tmp_path: Path) -> None:
    repository_root = tmp_path / "selected"
    repository_root.mkdir()
    body_file = tmp_path / "pr-body.md"
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("prepare_pr_body.git", lambda *arguments: "")

    try:
        execution_preflight(
            repository_root,
            body_file,
            tmp_path / "other",
            HEAD,
            HEAD,
            require_docker=False,
        )
    except ValueError as error:
        assert "selected worktree" in str(error)
    else:
        raise AssertionError("wrong worktree was accepted")


def test_execution_preflight_checks_tools_only_when_gates_will_run(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("prepare_pr_body.git", lambda *arguments: "")
    monkeypatch.setattr("prepare_pr_body.shutil.which", lambda executable: None)

    execution_preflight(tmp_path, tmp_path / "pr-body.md", tmp_path, HEAD, HEAD, require_docker=False)
    try:
        execution_preflight(tmp_path, tmp_path / "pr-body.md", tmp_path, HEAD, HEAD, require_docker=True)
    except ValueError as error:
        assert "docker, jq" in str(error)
    else:
        raise AssertionError("missing costly-run tools were accepted")


def test_execution_preflight_rejects_wrong_head(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("prepare_pr_body.git", lambda *arguments: "")

    try:
        execution_preflight(tmp_path, tmp_path / "pr-body.md", tmp_path, "b" * 40, HEAD, require_docker=False)
    except ValueError as error:
        assert "local HEAD" in str(error)
    else:
        raise AssertionError("wrong HEAD was accepted")


def test_execution_preflight_rejects_tracked_worktree_changes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("prepare_pr_body.git", lambda *arguments: " M scripts/prepare_pr_body.py")

    try:
        execution_preflight(tmp_path, tmp_path / "pr-body.md", tmp_path, HEAD, HEAD, require_docker=False)
    except ValueError as error:
        assert "tracked worktree changes" in str(error)
    else:
        raise AssertionError("dirty tracked worktree was accepted")


def test_execution_preflight_checks_each_docker_capability(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr("prepare_pr_body.git", lambda *arguments: "")
    monkeypatch.setattr("prepare_pr_body.shutil.which", lambda executable: f"/usr/bin/{executable}")

    for failing_subcommand, expected in (("info", "daemon"), ("compose", "Compose"), ("buildx", "Buildx")):
        monkeypatch.setattr(
            "prepare_pr_body.subprocess.run",
            lambda command, failing=failing_subcommand, **unused: SimpleNamespace(
                returncode=1 if command[1] == failing else 0
            ),
        )
        try:
            execution_preflight(tmp_path, tmp_path / "pr-body.md", tmp_path, HEAD, HEAD, require_docker=True)
        except ValueError as error:
            assert expected in str(error)
        else:
            raise AssertionError(f"unavailable Docker {failing_subcommand} was accepted")
