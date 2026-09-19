"""WC102 identity separation and invalidation contracts."""

import pytest

from validation_control.identity import candidate_identity, evidence_identity, runner_identity


def test_runner_identity_excludes_source_tests_and_fixtures() -> None:
    inputs = {"dockerfile": "abc", "lockfile": "def", "platform": "linux/amd64"}
    original = runner_identity(inputs)

    assert runner_identity({**inputs, "lockfile": "changed"}) != original
    with pytest.raises(ValueError, match="application inputs"):
        runner_identity({**inputs, "source": "changed"})


def test_evidence_identity_invalidates_every_authority_input() -> None:
    inputs = {
        "base_sha": "b" * 40,
        "head_sha": "c" * 40,
        "catalog_version": "wc102-shadow-v1",
        "command_id": "test-web",
        "runner_digest": "sha256:" + "d" * 64,
        "source": "source-digest",
        "tests": "test-digest",
        "fixtures": "fixture-digest",
        "specifications": "spec-digest",
        "environment": {},
    }
    original = evidence_identity(inputs)

    for field in inputs:
        assert evidence_identity({**inputs, field: f"changed-{field}"}) != original


def test_candidate_identity_is_distinct_from_runner_and_evidence() -> None:
    candidate = candidate_identity({"production_dockerfile": "abc", "source": "def"})
    runner = runner_identity({"dockerfile": "abc", "lockfile": "def"})
    evidence = evidence_identity(
        {
            "base_sha": "b" * 40,
            "head_sha": "c" * 40,
            "catalog_version": "v1",
            "command_id": "test-web",
            "runner_digest": runner,
        }
    )

    assert len({candidate, runner, evidence}) == 3
