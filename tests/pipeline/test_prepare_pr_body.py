from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_pr_body import (  # noqa: E402
    add_runtime_evidence,
    business_platform_gate_required,
    load_runtime_evidence,
    preparation_head,
    prepare_body,
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
