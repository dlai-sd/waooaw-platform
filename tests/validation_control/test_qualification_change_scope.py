from pathlib import Path

from validation_control.qualification_change_scope import full_scope, scope_for_changes, shell_output

ROOT = Path(__file__).resolve().parents[2]


def test_pull_request_and_push_runs_choose_release_lanes_with_the_same_selector() -> None:
    # A push to main diffs before..sha and feeds the same file list to the same selector; no event-specific branch.
    plan = (ROOT / ".github/workflows/validation-plan.yaml").read_text(encoding="utf-8")

    assert "PUSH_BASE_SHA: ${{ github.event.before }}" in plan
    assert 'git diff --name-only --find-renames "$base_sha" "$head_sha" > test-results/wc102/changed-files.txt' in plan
    lane_step = plan.split('release_scope="$RUNNER_TEMP/release-scope.env"', 1)[1].split("release_lanes=$(jq", 1)[0]
    assert "qualification_change_scope.py" in lane_step
    assert "--changed-files test-results/wc102/changed-files.txt" in lane_step
    assert "EVENT_NAME" not in lane_step


def test_business_platform_controller_change_selects_only_dotnet_integration() -> None:
    scope = scope_for_changes(("src/business-platform/Controllers/AgentsController.cs",))

    assert scope.integration_dotnet is True
    assert scope.mutation_dotnet is False
    assert scope.mutation_python is False
    assert scope.release_lanes == ()
    assert scope.broadened is False


def test_each_mutation_gate_tracks_only_its_owned_runtime() -> None:
    dotnet = scope_for_changes(("src/constitutional-engine/Services/EvidenceService.cs",))
    python = scope_for_changes(("src/ai-runtime/providers/router.py",))

    assert dotnet.mutation_dotnet is True and dotnet.mutation_python is False
    assert python.mutation_python is True and python.mutation_dotnet is False


def test_release_scope_selects_only_affected_lane() -> None:
    scope = scope_for_changes(("infrastructure/recovery/phase2/fixtures/valid-recovery-bundle.json",))

    assert scope.release_lanes == ("simulator",)
    assert "RELEASE_RUN_SIMULATOR=true" in shell_output("release-qualification", scope)
    assert "RELEASE_RUN_AZURE=false" in shell_output("release-qualification", scope)


def test_shared_validation_change_broadens_every_expensive_gate() -> None:
    scope = scope_for_changes(("scripts/validation_control/catalog_execution.py",))

    assert scope == full_scope()


def test_planning_only_inputs_do_not_select_release_qualification() -> None:
    scope = scope_for_changes(
        (
            "requirements-validation-plan.txt",
            "scripts/validation_control/hosted_policy.py",
        )
    )

    assert scope.release_lanes == ()
    assert scope.broadened is False


def test_azure_verifier_image_selects_only_azure_lane() -> None:
    scope = scope_for_changes(("architecture/reference/dockerfiles/Dockerfile.test-runner-azure",))

    assert scope.release_lanes == ("azure",)
    assert scope.broadened is False


def test_missing_or_ambiguous_scope_broadens_instead_of_skipping() -> None:
    assert scope_for_changes(()) == full_scope()
    assert scope_for_changes(("unexpected-root/runtime.conf",)) == full_scope()


def test_every_pr_shaped_state_refresh_and_process_change_runs_no_release_lane() -> None:
    # Regression: README.md, SPRINT-REGISTRY.md, validation/process-control.yaml and .githooks/* were "unknown"
    # paths, so almost every PR broadened to all lanes and paid for the 5-minute Azure lane for nothing.
    scope = scope_for_changes(
        (
            "README.md",
            "SPRINT-REGISTRY.md",
            "ARCHITECTURE.md",
            "validation/process-control.yaml",
            ".githooks/pre-push",
            "standards/CI-VALIDATION-SPEED-POLICY.md",
            "work-contracts/WC-154-requirements.yaml",
        )
    )

    assert scope.release_lanes == ()
    assert scope.broadened is False
    assert "RELEASE_RUN_AZURE=false" in shell_output("release-qualification", scope)


def test_the_gate_catalog_still_broadens_every_lane_but_other_validation_files_do_not() -> None:
    assert scope_for_changes(("validation/engineering-validation.yaml",)) == full_scope()
    assert scope_for_changes(("validation/runner-supply.json",)) == full_scope()
    assert scope_for_changes(("validation/process-control.yaml",)).broadened is False


def test_documentation_change_skips_expensive_runtime_work() -> None:
    scope = scope_for_changes(("constitution/PROJECT_STATE.md", "work-contracts/WC-109-requirements.yaml"))

    assert scope.integration_dotnet is False
    assert scope.mutation_dotnet is False
    assert scope.mutation_python is False
    assert scope.release_lanes == ()
