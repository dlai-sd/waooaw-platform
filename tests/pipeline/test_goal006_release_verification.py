import json
from pathlib import Path

import pytest

from scripts.goal006_release_verification import create_record, validate_record


def test_release_verification_accepts_bound_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"images": {}}\n', encoding="utf-8")
    record = create_record("a" * 40, 123, manifest)

    validate_record(record, "a" * 40, 123, manifest)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("release_sha", "b" * 40, "SHA"),
        ("release_run_id", 456, "run ID"),
        ("attestations_verified", False, "attestations"),
        ("schema_version", "2.0", "schema_version"),
    ],
)
def test_release_verification_rejects_invalid_record(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"images": {}}\n', encoding="utf-8")
    record = create_record("a" * 40, 123, manifest)
    record[field] = value

    with pytest.raises(ValueError, match=message):
        validate_record(record, "a" * 40, 123, manifest)


def test_release_verification_rejects_tampered_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"images": {}}\n', encoding="utf-8")
    record = create_record("a" * 40, 123, manifest)
    manifest.write_text(json.dumps({"images": {"web": "changed"}}), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest digest"):
        validate_record(record, "a" * 40, 123, manifest)