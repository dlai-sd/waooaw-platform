"""WC-170 DMA real-work artifacts: profile confirmation, maturity scorecard and report."""

# Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R005
# Constitutional basis: C-023, C-042, C-049, C-059, C-076

from __future__ import annotations

from decimal import Decimal

import pytest

from digital_marketing.employment import MATURITY_DIMENSIONS, MaturityDimension
from digital_marketing.real_work import (
    MATURITY_BLOCK_ID,
    NOT_ENOUGH_INFORMATION,
    artifact_proposal,
    maturity_report,
    maturity_scorecard,
    profile_confirmation,
)


def _dimensions(*, unscored: tuple[str, ...] = (), disputed: str | None = None, stale: str | None = None):
    result = {}
    for dimension_id in MATURITY_DIMENSIONS:
        scored = dimension_id not in unscored and dimension_id not in (disputed, stale)
        result[dimension_id] = MaturityDimension(
            dimension_id=dimension_id,
            score=6 if scored else None,
            evidence_refs=(f"evidence:{dimension_id.lower()}",) if scored else (),
            confidence=Decimal("0.8"),
            limitations=("Seen on public pages only.",) if scored else (),
            disputed=dimension_id == disputed,
            stale=dimension_id == stale,
        )
    return result


def test_the_scorecard_scores_only_dimensions_with_evidence_and_says_not_enough_information_otherwise() -> None:
    card = _dimensions(unscored=MATURITY_DIMENSIONS[8:])
    scorecard = maturity_scorecard(card)

    assert scorecard["blockId"] == MATURITY_BLOCK_ID
    assert scorecard["state"] == "PUBLISHED" and scorecard["evidenceCoverage"] == "8/10"
    unscored = [row for row in scorecard["dimensions"] if row["status"] == "NOT_ENOUGH_INFORMATION"]
    assert [row["dimensionId"] for row in unscored] == list(MATURITY_DIMENSIONS[8:])
    assert all(row["score"] is None and row["evidenceRefs"] == [] for row in unscored)
    assert all(row["limitations"] == ["No evidence has been seen yet."] for row in unscored)
    scored = [row for row in scorecard["dimensions"] if row["status"] == "SCORED"]
    assert all(row["score"] == 6 and row["evidenceRefs"] and row["limitations"] for row in scored)
    assert NOT_ENOUGH_INFORMATION in scorecard["fallbackText"]
    assert "level 6 of 10" in scorecard["fallbackText"]


def test_fewer_than_seven_dimensions_publish_no_score_at_all() -> None:
    scorecard = maturity_scorecard(_dimensions(unscored=MATURITY_DIMENSIONS[6:]))

    assert scorecard["state"] == "MATURITY_ASSESSMENT_IN_PROGRESS"
    assert scorecard["auditScore"] is None and scorecard["displayLevel"] is None
    assert "not published yet" in scorecard["fallbackText"]


def test_a_disputed_or_stale_dimension_is_explained_never_scored() -> None:
    scorecard = maturity_scorecard(_dimensions(disputed=MATURITY_DIMENSIONS[0], stale=MATURITY_DIMENSIONS[1]))
    rows = {row["dimensionId"]: row for row in scorecard["dimensions"]}

    assert rows[MATURITY_DIMENSIONS[0]]["limitations"] == ["The customer disputes this finding."]
    assert rows[MATURITY_DIMENSIONS[1]]["limitations"] == ["The evidence is out of date."]
    assert rows[MATURITY_DIMENSIONS[0]]["score"] is None


def test_the_maturity_report_is_a_proposal_that_lists_every_gap_as_a_limitation() -> None:
    proposal = maturity_report(_dimensions(unscored=MATURITY_DIMENSIONS[9:]), "Where your marketing stands today.")

    assert proposal["artifactType"] == "MATURITY_REPORT"
    assert proposal["content"]["blockId"] == MATURITY_BLOCK_ID
    assert proposal["limitations"] == ["Governance and trust: not enough information."]


def test_a_profile_confirmation_needs_a_business_domain_selector_and_lists_what_is_missing() -> None:
    proposal = profile_confirmation(
        {"business_domain": "dental_clinic", "name": "Smile Care", "primary_location": ""},
        "Here is what I understand about your business.",
        vocabulary_version="3.1",
        vocabulary_digest="a" * 64,
    )

    assert proposal["artifactType"] == "PROFILE_CONFIRMATION"
    assert proposal["limitations"] == ["Primary location was not provided."]
    assert proposal["vocabularyVersion"] == "3.1"
    for bad in ("Dental Clinic", "", "x"):
        with pytest.raises(ValueError, match="DMA_BUSINESS_DOMAIN_INVALID"):
            profile_confirmation({"business_domain": bad}, "summary")


def test_a_correction_names_what_it_replaces_and_a_draft_stays_a_draft() -> None:
    proposal = artifact_proposal(
        "CONTENT_DRAFT",
        {"text": "v2"},
        "A corrected draft.",
        authority_boundary="I may draft; only you can approve publication.",
        supersedes_artifact_id="11111111-1111-1111-1111-111111111111",
        draft=True,
    )

    assert proposal["supersedesArtifactId"] == "11111111-1111-1111-1111-111111111111"
    assert proposal["draft"] is True
    assert proposal["authorityBoundary"].startswith("I may draft")
    assert "vocabularyVersion" not in proposal
