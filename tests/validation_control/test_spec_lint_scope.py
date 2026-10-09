from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.validation_control.spec_lint_scope import CANONICAL_SPECS, select_specs


def test_select_specs_adds_changed_openapi_contracts_once(tmp_path: Path) -> None:
    candidate = Path("architecture/reference/api-specs/example.openapi.yaml")
    candidate_path = tmp_path / candidate
    candidate_path.parent.mkdir(parents=True)
    candidate_path.write_text("openapi: 3.1.0\n", encoding="utf-8")
    changed_files = tmp_path / "changed-files.txt"
    changed_files.write_text(
        "\n".join(
            [
                str(candidate),
                "README.md",
                str(candidate),
            ]
        ),
        encoding="utf-8",
    )

    assert select_specs(tmp_path, changed_files) == [*CANONICAL_SPECS, str(candidate)]


def test_select_specs_keeps_canonical_defaults_without_changed_file(tmp_path: Path) -> None:
    assert select_specs(tmp_path, None) == list(CANONICAL_SPECS)


@pytest.mark.parametrize(
    "changed_path",
    [
        "/tmp/escape.openapi.yaml",
        "architecture/reference/api-specs/../../escape.openapi.yaml",
    ],
)
def test_select_specs_rejects_paths_outside_repository(tmp_path: Path, changed_path: str) -> None:
    changed_files = tmp_path / "changed-files.txt"
    changed_files.write_text(f"{changed_path}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repository-relative"):
        select_specs(tmp_path, changed_files)


def test_select_specs_rejects_missing_changed_contract(tmp_path: Path) -> None:
    changed_files = tmp_path / "changed-files.txt"
    changed_files.write_text(
        "architecture/reference/api-specs/missing.openapi.yaml\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="does not exist"):
        select_specs(tmp_path, changed_files)


def test_spec_lint_catalog_receives_changed_files_and_selects_openapi_paths() -> None:
    repository = Path(__file__).resolve().parents[2]
    catalog = yaml.safe_load(
        (repository / "validation/engineering-validation.yaml").read_text(encoding="utf-8")
    )

    assert catalog["gates"]["spec-lint"]["environment"] == ["WAOOAW_CHANGED_FILES_FILE"]
    assert catalog["scoped_paths"]["openapi-contracts"] == {
        "paths": ["architecture/reference/api-specs/*.openapi.yaml"],
        "gates": ["spec-lint"],
    }
