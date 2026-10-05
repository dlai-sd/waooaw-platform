from validation_control.rest_contract_scope import (
    BP_IDENTITY_ALL,
    BP_PRODUCT_ALL,
    PR_ALL,
    combined_regex,
    scope_for_changes,
)


def test_unrelated_changes_skip_rest_runtime() -> None:
    scope = scope_for_changes(["web/components/relationship-card.tsx", "README.md"])

    assert scope.run_bp is False
    assert scope.run_pr is False


def test_missing_manifest_falls_back_to_full_estate() -> None:
    scope = scope_for_changes(None)

    assert BP_IDENTITY_ALL in scope.bp_identity
    assert BP_PRODUCT_ALL in scope.bp_product
    assert PR_ALL in scope.pr_service


def test_owned_business_platform_controller_selects_only_its_paths() -> None:
    scope = scope_for_changes(["src/business-platform/Controllers/PortalInteractionsController.cs"])

    assert scope.run_bp is True
    assert scope.run_pr is False
    assert scope.bp_identity == set()
    assert scope.bp_service == set()
    assert combined_regex(scope.bp_product) == r"^/api/v1/customer-portal/interactions/portal/messages(?:/|$)"


def test_owned_professional_runtime_router_selects_only_its_paths() -> None:
    scope = scope_for_changes(["src/professional-runtime/routers/sessions.py"])

    assert scope.run_bp is False
    assert scope.run_pr is True
    assert combined_regex(scope.pr_service) == r"^/api/v1/paas/sessions(?:/|$)"


def test_unknown_runtime_source_broadens_only_owning_service() -> None:
    scope = scope_for_changes(["src/professional-runtime/session_executor.py"])

    assert scope.run_bp is False
    assert scope.pr_service == {PR_ALL}


def test_shared_contract_infrastructure_broadens_both_services() -> None:
    scope = scope_for_changes(["validation/schemathesis.toml"])

    assert BP_PRODUCT_ALL in scope.bp_product
    assert PR_ALL in scope.pr_service


def test_multiple_owned_changes_combine_path_filters() -> None:
    scope = scope_for_changes(
        [
            "src/business-platform/Controllers/AcquisitionController.cs",
            "src/business-platform/Controllers/PortalInteractionsController.cs",
        ]
    )

    regex = combined_regex(scope.bp_product)
    assert "acquisition/continuations" in regex
    assert "customer-portal/interactions/portal/messages" in regex
