from pathlib import Path

import pytest

from scripts.goal006_foundation_cache import (
    REQUIRED_OUTPUTS,
    create_cache_record,
    foundation_fingerprint,
    validate_cache_record,
)


def _repository(tmp_path: Path) -> Path:
    environment_root = tmp_path / "infrastructure/terraform/phase2/environments/demo/foundation"
    module_root = tmp_path / "infrastructure/terraform/phase2/modules/foundation"
    environment_root.mkdir(parents=True)
    module_root.mkdir(parents=True)
    (environment_root / "main.tf").write_text('module "foundation" {}\n', encoding="utf-8")
    (module_root / "main.tf").write_text('resource "example" "foundation" {}\n', encoding="utf-8")
    return tmp_path


def _terraform_outputs() -> dict[str, dict[str, str]]:
    return {name: {"value": f"value-{name}"} for name in REQUIRED_OUTPUTS}


def test_fingerprint_changes_with_environment_or_module_input(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    initial = foundation_fingerprint(repository, "demo")

    module = repository / "infrastructure/terraform/phase2/modules/foundation/main.tf"
    module.write_text('resource "example" "foundation" { value = true }\n', encoding="utf-8")

    assert foundation_fingerprint(repository, "demo") != initial


def test_fingerprint_changes_with_runtime_context(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    first = foundation_fingerprint(repository, "demo", {"state_account": "first"})
    second = foundation_fingerprint(repository, "demo", {"state_account": "second"})

    assert first != second


def test_create_and_validate_cache_record() -> None:
    record = create_cache_record("demo", "abc123", _terraform_outputs())

    outputs = validate_cache_record(record, "demo", "abc123")

    assert outputs["resource_group_name"] == "value-resource_group_name"
    assert set(outputs) == set(REQUIRED_OUTPUTS)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", "2.0", "schema_version"),
        ("environment", "uat", "environment"),
        ("fingerprint", "different", "fingerprint"),
    ],
)
def test_cache_validation_rejects_mismatched_contract(field: str, value: str, message: str) -> None:
    record = create_cache_record("demo", "abc123", _terraform_outputs())
    record[field] = value

    with pytest.raises(ValueError, match=message):
        validate_cache_record(record, "demo", "abc123")


def test_cache_validation_requires_every_output() -> None:
    outputs = _terraform_outputs()
    outputs.pop("key_vault_uri")

    with pytest.raises(ValueError, match="key_vault_uri"):
        create_cache_record("demo", "abc123", outputs)


def test_fingerprint_rejects_unknown_environment_or_missing_inputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="environment"):
        foundation_fingerprint(tmp_path, "invalid")
    with pytest.raises(ValueError, match="inputs are missing"):
        foundation_fingerprint(tmp_path, "demo")


def test_cache_creation_rejects_nonterraform_output() -> None:
    outputs = _terraform_outputs()
    outputs["key_vault_uri"] = "not-a-terraform-output"  # type: ignore[assignment]

    with pytest.raises(ValueError, match="key_vault_uri"):
        create_cache_record("demo", "abc123", outputs)


def test_cache_validation_requires_output_mapping_and_values() -> None:
    record = create_cache_record("demo", "abc123", _terraform_outputs())
    record["outputs"] = None
    with pytest.raises(ValueError, match="outputs are missing"):
        validate_cache_record(record, "demo", "abc123")

    record = create_cache_record("demo", "abc123", _terraform_outputs())
    record["outputs"]["key_vault_uri"] = ""  # type: ignore[index]
    with pytest.raises(ValueError, match="key_vault_uri"):
        validate_cache_record(record, "demo", "abc123")