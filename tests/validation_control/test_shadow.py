"""WC102 Shadow selection comparison contracts."""

from pathlib import Path

import pytest
import yaml

from validation_control.shadow import build_shadow_record
from validation_policy import classify_paths


ROOT = Path(__file__).resolve().parents[2]


def load_catalog() -> dict[str, object]:
    return yaml.safe_load((ROOT / "validation/engineering-validation.yaml").read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("change_class", "path", "expected_gate"),
    [
        ("web-only", "web/app/page.tsx", "test-web"),
        ("business-platform", "src/business-platform/Program.cs", "test-dotnet:business-platform"),
        ("python-service", "src/professional-runtime/app.py", "test-python:professional-runtime"),
        ("shared-contract", "architecture/reference/proto/constitutional.proto", "spec-lint"),
        ("pipeline-global", ".github/workflows/ci.yaml", "test-python"),
    ],
)
def test_shadow_comparison_covers_representative_change_classes(change_class: str, path: str, expected_gate: str) -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, [path], base_sha="b" * 40, head_sha="c" * 40)
    full_results = {gate: "PASS" for gate in catalog["full_gates"]}
    full_results[expected_gate] = "FAIL"
    if expected_gate not in full_results:
        full_results[expected_gate] = "FAIL"

    record = build_shadow_record(change_class, selection, full_results)

    assert expected_gate in selection["selected_gates"]
    assert record["passed"] is True
    assert record["selective_enforcement"] is False


def test_shadow_comparison_records_omitted_full_ci_failure() -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"], base_sha="b" * 40, head_sha="c" * 40)

    record = build_shadow_record("web-only", selection, {"test-web": "PASS", "test-dotnet": "FAIL"})

    assert record["passed"] is False
    assert record["false_negatives"] == ["test-dotnet"]


def test_shadow_comparison_rejects_authoritative_selection() -> None:
    catalog = load_catalog()
    selection = classify_paths(catalog, ["web/app/page.tsx"])
    selection["authoritative"] = True

    with pytest.raises(ValueError, match="non-authoritative Shadow"):
        build_shadow_record("web-only", selection, {"test-web": "PASS"})
