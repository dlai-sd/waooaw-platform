"""CCT-DMA-BUILD-AUTH-01 candidate build denial proof."""

from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/agent-adapters"))

from digital_marketing.build_authority import (
    BuildAuthorityDenied,
    CandidateBuildAuthorityGate,
    run_candidate_build,
)


FIXTURES = ROOT / "tests/fixtures/dma-release-1"
SOURCE_HEAD = "a" * 40
NOW = datetime(2026, 9, 15, 12, tzinfo=timezone.utc)


def fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "authority",
    [
        pytest.param(fixture("build-authority-missing.json"), id="missing-founder-approval"),
        pytest.param({**fixture("build-authority-valid.json"), "professionalVersion": "3.1.0"}, id="mismatch"),
        pytest.param({**fixture("build-authority-valid.json"), "expiresAt": "2026-09-15T11:59:59Z"}, id="expired"),
    ],
)
def test_invalid_authority_creates_no_artifact(
    authority: dict[str, Any], tmp_path: Path
) -> None:
    output = tmp_path / "candidate"
    builder_calls: list[Path] = []

    with pytest.raises(BuildAuthorityDenied):
        run_candidate_build(
            CandidateBuildAuthorityGate(),
            authority,
            source_head=SOURCE_HEAD,
            builder_identity="platform-it-expert",
            now=NOW,
            output_directory=output,
            build=builder_calls.append,
        )

    assert builder_calls == []
    assert not output.exists()
    assert list(tmp_path.iterdir()) == []


def test_authority_is_single_use_and_replay_creates_no_second_artifact(tmp_path: Path) -> None:
    authority = copy.deepcopy(fixture("build-authority-valid.json"))
    gate = CandidateBuildAuthorityGate()
    first_output = tmp_path / "candidate-1"
    second_output = tmp_path / "candidate-2"

    run_candidate_build(
        gate,
        authority,
        source_head=SOURCE_HEAD,
        builder_identity="platform-it-expert",
        now=NOW,
        output_directory=first_output,
        build=lambda output: (output / "invoked").write_text("yes", encoding="utf-8"),
    )
    with pytest.raises(BuildAuthorityDenied, match="BUILD_AUTHORITY_REPLAYED"):
        run_candidate_build(
            gate,
            authority,
            source_head=SOURCE_HEAD,
            builder_identity="platform-it-expert",
            now=NOW,
            output_directory=second_output,
            build=lambda output: (output / "invoked").write_text("yes", encoding="utf-8"),
        )

    assert (first_output / "invoked").read_text(encoding="utf-8") == "yes"
    assert not second_output.exists()