from pathlib import Path

import yaml

from validation_policy import classify_paths, compare_shadow, parse_name_status, validate_policy, validate_selection_manifest


ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "validation/engineering-validation.yaml"


def load_policy() -> dict[str, object]:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def test_classifier_direct_reverse_and_unknown_paths() -> None:
    policy = load_policy()

    web = classify_paths(policy, ["web/app/page.tsx"])
    business = classify_paths(policy, ["src/business-platform/Program.cs"])
    unknown = classify_paths(policy, ["unexpected/new-system/file.txt"])

    assert web["selected_components"] == ["web"]
    assert "test-web" in web["selected_gates"]
    assert business["selected_components"] == [
        "agent-runtime-adapter-digital-marketing",
        "billing-engine",
        "business-platform",
        "professional-runtime",
        "web",
    ]
    assert unknown["full"] is True
    assert unknown["reasons"] == ["unknown path: unexpected/new-system/file.txt"]


def test_classifier_failure_modes_select_full() -> None:
    policy = load_policy()
    policy["components"]["web"]["reverse_dependencies"] = ["constitutional-engine"]

    result = classify_paths(policy, ["src/constitutional-engine/Program.cs"])

    assert result["full"] is True
    assert any("cycle" in reason.lower() for reason in result["reasons"])


def test_global_and_normative_changes_select_full() -> None:
    policy = load_policy()

    for path in (
        ".github/agent-context/office-platform-it-expert.md",
        ".github/workflows/ci.yaml",
        "constitution/BOOTSTRAP.md",
        "docker-compose.yml",
        "scripts/run_wc100_qualification.sh",
        "tests/pipeline/test_platform_it_process_intake.py",
        "tests/pipeline/test_platform_it_story_commentary.py",
        "validation/process-control.yaml",
        "work-contracts/WC-100-example.md",
    ):
        result = classify_paths(policy, [path])
        assert result["full"] is True
        assert result["selected_gates"] == policy["full_gates"]


def test_docs_only_and_renamed_paths_are_reasoned() -> None:
    policy = load_policy()

    docs = classify_paths(policy, ["README.md"])
    renamed = classify_paths(policy, ["web/old.ts", "src/business-platform/New.cs"])

    assert docs["full"] is False
    assert docs["selected_components"] == []
    assert docs["skipped_gates"]
    assert "business-platform" in renamed["selected_components"]
    assert "web" in renamed["selected_components"]


def test_deployment_workflow_change_selects_release_without_service_builds() -> None:
    policy = load_policy()

    result = classify_paths(
        policy,
        [".github/workflows/deploy.yaml", "tests/pipeline/test_goal006_terraform_foundations.py"],
    )

    assert result["full"] is False
    assert result["selected_components"] == []
    assert result["selected_gates"] == [
        "author-review-gate",
        "authorization-tier-check",
        "constitutional-commit-gate",
        "quality:commitlint",
        "release-qualification",
        "secrets",
    ]
    assert result["required_runners"] == ["full", "python", "typescript"]
    assert result["service_builds"] == []
    assert result["service_build_matrix"] == []


def test_component_change_selects_required_runners_and_service_images() -> None:
    policy = load_policy()

    result = classify_paths(policy, ["src/business-platform/Program.cs"])

    assert result["required_runners"] == ["dotnet", "full", "python", "typescript"]
    assert result["service_builds"] == [
        "agent-runtime-adapter-digital-marketing",
        "billing-engine",
        "business-platform",
        "professional-runtime",
        "web",
    ]
    assert {entry["name"] for entry in result["service_build_matrix"]} == set(result["service_builds"])
    assert result["dotnet_test_matrix"] == [
        {"service": "business-platform", "gate": "test-dotnet:business-platform"}
    ]
    assert result["python_test_matrix"] == [
        {"service": "professional-runtime", "gate": "test-python:professional-runtime"}
    ]


def test_local_prechecks_are_scoped_independently_from_full_hosted_inventory() -> None:
    policy = load_policy()

    evidence_only = classify_paths(policy, ["reviews/R-144-wc104-platform-it-expert-author-review.md"])
    business = classify_paths(policy, ["src/business-platform/Program.cs"])
    release = classify_paths(policy, ["infrastructure/terraform/phase2/main.tf"])
    hosted = classify_paths(policy, ["README.md"], event="push")

    assert evidence_only["full"] is True
    assert evidence_only["selected_prechecks"] == ["gitleaks"]
    assert business["selected_prechecks"] == [
        "business_platform",
        "dotnet_quality_business_platform",
        "gitleaks",
        "release_qualification",
        "typescript_quality",
    ]
    assert release["selected_prechecks"] == ["gitleaks", "release_qualification"]
    assert hosted["selected_gates"] == policy["full_gates"]


def test_name_status_parser_keeps_deleted_and_renamed_paths() -> None:
    paths = parse_name_status("D\tweb/deleted.ts\nR100\tweb/old.ts\tsrc/business-platform/New.cs\n")

    assert paths == ["web/deleted.ts", "web/old.ts", "src/business-platform/New.cs"]


def test_enforced_mode_requires_founder_activation() -> None:
    policy = load_policy()
    policy["mode"] = "enforced"

    violations = validate_policy(policy)

    assert "ENFORCED_WITHOUT_FOUNDER_APPROVAL" in violations
    assert "ENFORCED_WITHOUT_SHADOW_EVIDENCE" in violations


def test_prechecks_require_declared_gate_inputs() -> None:
    policy = load_policy()
    del policy["prechecks"]["business_platform"]["inputs"]

    assert "PRECHECK_INPUTS_MISSING: business_platform" in validate_policy(policy)


def test_scoped_and_always_on_gates_must_be_defined() -> None:
    policy = load_policy()
    policy["always_on_gates"].append("missing-always-on")
    policy["scoped_paths"]["deployment-workflows"]["gates"].append("missing-scoped")

    violations = validate_policy(policy)

    assert "GATE_UNDEFINED: missing-always-on" in violations
    assert "GATE_UNDEFINED: missing-scoped" in violations


def test_shadow_comparison_detects_omitted_failure() -> None:
    comparison = compare_shadow(["test-web"], ["test-web", "test-dotnet"])

    assert comparison["false_negatives"] == ["test-dotnet"]
    assert comparison["passed"] is False


def test_selection_manifest_rejects_merge_base_movement() -> None:
    policy = load_policy()
    manifest = classify_paths(policy, ["web/app/page.tsx"], base_sha="b" * 40, head_sha="h" * 40)

    assert validate_selection_manifest(manifest, "b" * 40, "h" * 40, policy["version"]) == []
    assert validate_selection_manifest(manifest, "c" * 40, "h" * 40, policy["version"])


def test_policy_is_single_selection_source() -> None:
    preparer = (ROOT / "scripts/prepare_pr_body.py").read_text(encoding="utf-8")
    workflow = (ROOT / ".github/workflows/ci.yaml").read_text(encoding="utf-8")
    planner = (ROOT / ".github/workflows/validation-plan.yaml").read_text(encoding="utf-8")

    assert "BUSINESS_PLATFORM_GATE_PATHS" not in preparer
    assert "RELEASE_QUALIFICATION_GATE_PATHS" not in preparer
    assert "uses: ./.github/workflows/validation-plan.yaml" in workflow
    assert "validation/engineering-validation.yaml" in planner
