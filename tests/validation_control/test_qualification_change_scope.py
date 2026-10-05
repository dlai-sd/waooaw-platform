from validation_control.qualification_change_scope import full_scope, scope_for_changes, shell_output


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


def test_missing_or_ambiguous_scope_broadens_instead_of_skipping() -> None:
    assert scope_for_changes(()) == full_scope()
    assert scope_for_changes(("unexpected-root/runtime.conf",)) == full_scope()


def test_documentation_change_skips_expensive_runtime_work() -> None:
    scope = scope_for_changes(("constitution/PROJECT_STATE.md", "work-contracts/WC-109-requirements.yaml"))

    assert scope.integration_dotnet is False
    assert scope.mutation_dotnet is False
    assert scope.mutation_python is False
    assert scope.release_lanes == ()
