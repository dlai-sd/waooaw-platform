"""Customer-facing real-work artifacts the DMA proposes: profile, maturity report, campaign brief, calendar, drafts."""

# Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 DMA instances, DC-1 business domain
# Constitutional basis: C-023, C-042, C-049, C-059, C-063
# IB: IB-170

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from digital_marketing.employment import (
    MATURITY_DIMENSIONS,
    MaturityAssessment,
    MaturityDimension,
    assess_maturity,
)

PROFILE_CONFIRMATION = "PROFILE_CONFIRMATION"
MATURITY_REPORT = "MATURITY_REPORT"
CAMPAIGN_BRIEF = "CAMPAIGN_BRIEF"
CONTENT_CALENDAR = "CONTENT_CALENDAR"
CONTENT_DRAFT = "CONTENT_DRAFT"
MATURITY_BLOCK_ID = "MARKETING_MATURITY_SUMMARY"
NOT_ENOUGH_INFORMATION = "Not enough information"

_BUSINESS_DOMAIN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


def artifact_proposal(
    artifact_type: str,
    content: Mapping[str, Any],
    summary: str,
    *,
    limitations: tuple[str, ...] = (),
    authority_boundary: str | None = None,
    supersedes_artifact_id: str | None = None,
    vocabulary_version: str | None = None,
    vocabulary_digest: str | None = None,
    draft: bool = False,
) -> dict[str, Any]:
    """The BP proposal shape. A correction names the version it replaces and never inherits its approval."""
    proposal: dict[str, Any] = {
        "artifactType": artifact_type,
        "content": dict(content),
        "plainLanguageSummary": summary,
        "limitations": list(limitations),
        "draft": draft,
    }
    if authority_boundary:
        proposal["authorityBoundary"] = authority_boundary
    if supersedes_artifact_id:
        proposal["supersedesArtifactId"] = supersedes_artifact_id
    if vocabulary_version and vocabulary_digest:
        proposal["vocabularyVersion"] = vocabulary_version
        proposal["vocabularyDigest"] = vocabulary_digest
    return proposal


def profile_confirmation(
    profile: Mapping[str, Any],
    summary: str,
    *,
    vocabulary_version: str | None = None,
    vocabulary_digest: str | None = None,
) -> dict[str, Any]:
    """The customer confirms what the agent believes about the business. The business domain is data, never a branch."""
    domain = str(profile.get("business_domain", ""))
    if not _BUSINESS_DOMAIN.match(domain):
        raise ValueError("DMA_BUSINESS_DOMAIN_INVALID")
    limitations = tuple(
        f"{key.replace('_', ' ').capitalize()} was not provided." for key in sorted(profile) if profile[key] in (None, "")
    )
    return artifact_proposal(
        PROFILE_CONFIRMATION,
        profile,
        summary,
        limitations=limitations,
        vocabulary_version=vocabulary_version,
        vocabulary_digest=vocabulary_digest,
    )


def maturity_scorecard(dimensions: Mapping[str, MaturityDimension]) -> dict[str, Any]:
    """Scores 1 to 10 appear only for dimensions with evidence; a gap reads 'not enough information', never a low score."""
    assessment = assess_maturity(dimensions)
    rows = []
    for dimension_id in MATURITY_DIMENSIONS:
        dimension = dimensions[dimension_id]
        scored = dimension_id not in assessment.missing_dimensions
        rows.append(
            {
                "dimensionId": dimension_id,
                "label": dimension_id.replace("_", " ").capitalize(),
                "status": "SCORED" if scored else "NOT_ENOUGH_INFORMATION",
                "score": dimension.score if scored else None,
                "evidenceRefs": list(dimension.evidence_refs) if scored else [],
                "limitations": list(dimension.limitations) + _why_unscored(dimension, scored),
            }
        )
    return {
        "blockId": MATURITY_BLOCK_ID,
        "version": 1,
        "state": assessment.state,
        "evidenceCoverage": assessment.evidence_coverage,
        "auditScore": str(assessment.audit_score) if assessment.audit_score is not None else None,
        "displayLevel": assessment.display_level,
        "dimensions": rows,
        "fallbackText": _fallback_text(assessment, rows),
    }


def maturity_report(
    dimensions: Mapping[str, MaturityDimension],
    summary: str,
    *,
    vocabulary_version: str | None = None,
    vocabulary_digest: str | None = None,
) -> dict[str, Any]:
    scorecard = maturity_scorecard(dimensions)
    limitations = tuple(
        f"{row['label']}: {NOT_ENOUGH_INFORMATION.lower()}." for row in scorecard["dimensions"] if row["score"] is None
    )
    return artifact_proposal(
        MATURITY_REPORT,
        scorecard,
        summary,
        limitations=limitations,
        vocabulary_version=vocabulary_version,
        vocabulary_digest=vocabulary_digest,
    )


def _why_unscored(dimension: MaturityDimension, scored: bool) -> list[str]:
    if scored:
        return []
    if dimension.disputed:
        return ["The customer disputes this finding."]
    if dimension.stale:
        return ["The evidence is out of date."]
    return ["No evidence has been seen yet."]


def _fallback_text(assessment: MaturityAssessment, rows: list[dict[str, Any]]) -> str:
    if assessment.display_level is None:
        head = f"Your marketing maturity is not published yet: {assessment.evidence_coverage} areas have evidence."
    else:
        head = f"Your marketing maturity is level {assessment.display_level} of 10 ({assessment.evidence_coverage} areas have evidence)."
    lines = [f"- {row['label']}: {row['score'] if row['score'] is not None else NOT_ENOUGH_INFORMATION}" for row in rows]
    return "\n".join([head, *lines])
