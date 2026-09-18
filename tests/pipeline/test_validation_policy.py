from pathlib import Path

import yaml

from validation_policy import classify_paths, compare_shadow, validate_policy, validate_selection_manifest


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
    policy["components"]["constitutional-engine"]["depends_on"] = ["web"]

    result = classify_paths(policy, ["src/constitutional-engine/Program.cs"])

    assert result["full"] is True
    assert any("cycle" in reason.lower() for reason in result["reasons"])


def test_global_and_normative_changes_select_full() -> None:
    policy = load_policy()

    for path in (".github/workflows/ci.yaml", "docker-compose.yml", "work-contracts/WC-100-example.md"):
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


def test_enforced_mode_requires_founder_activation() -> None:
    policy = load_policy()
    policy["mode"] = "enforced"

    violations = validate_policy(policy)

    assert "ENFORCED_WITHOUT_FOUNDER_APPROVAL" in violations
    assert "ENFORCED_WITHOUT_SHADOW_EVIDENCE" in violations


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

    assert "BUSINESS_PLATFORM_GATE_PATHS" not in preparer
    assert "RELEASE_QUALIFICATION_GATE_PATHS" not in preparer
    assert "validation/engineering-validation.yaml" in workflow
