"""Deterministic domain behavior for DMA Release 1 Skills 0, 1, and 2."""

# Implements: architecture/reference/components/dma-employment-conformance-work-component.md §4, §8, §9
# Constitutional basis: C-023, C-049, C-062, C-071, C-094

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from ipaddress import ip_address
from typing import Any
from urllib.parse import urlparse

from .employment import MATURITY_DIMENSIONS, MaturityDimension, assess_maturity


class SkillInputDenied(ValueError):  # noqa: N818 - domain denial term
    """Raised when structured Skill input violates its admitted contract."""


PROFILE_FIELDS = (
    "accountMode",
    "businessIdentity",
    "audience",
    "priority",
    "constraints",
    "approvedChannels",
)
PROVENANCE_CLASSES = frozenset({"OBSERVED", "INFERRED", "MISSING", "CONFIRMED"})


def profile_customer(payload: dict[str, Any]) -> dict[str, Any]:
    supplied = payload.get("fields")
    if not isinstance(supplied, dict):
        raise SkillInputDenied("DMA_PROFILE_FIELDS_INVALID")

    fields: dict[str, dict[str, Any]] = {}
    for field_name in PROFILE_FIELDS:
        candidate = supplied.get(field_name, {"value": None, "provenance": "MISSING"})
        if not isinstance(candidate, dict) or set(candidate) != {"value", "provenance"}:
            raise SkillInputDenied("DMA_PROFILE_FIELD_INVALID")
        provenance = candidate["provenance"]
        if provenance not in PROVENANCE_CLASSES:
            raise SkillInputDenied("DMA_PROFILE_PROVENANCE_INVALID")
        if provenance == "CONFIRMED" and candidate["value"] in (None, "", []):
            raise SkillInputDenied("DMA_PROFILE_CONFIRMATION_EMPTY")
        fields[field_name] = {"value": candidate["value"], "provenance": provenance}

    confirmed = sum(value["provenance"] == "CONFIRMED" for value in fields.values())
    return {
        "kind": "CUSTOMER_PROFILE_PROPOSAL",
        "status": "READY_FOR_CONFIRMATION" if confirmed == len(PROFILE_FIELDS) else "INCOMPLETE",
        "fields": fields,
        "confirmedFieldCount": confirmed,
        "requiredFieldCount": len(PROFILE_FIELDS),
        "sideEffects": [],
    }


def research_market(payload: dict[str, Any]) -> dict[str, Any]:
    sources = payload.get("sources")
    claims = payload.get("claims")
    unavailable = payload.get("unavailableProviders", [])
    if not isinstance(sources, list) or not isinstance(claims, list) or not isinstance(unavailable, list):
        raise SkillInputDenied("DMA_RESEARCH_INPUT_INVALID")

    source_ids: set[str] = set()
    normalized_sources: list[dict[str, str]] = []
    for source in sources:
        if not isinstance(source, dict) or set(source) != {"sourceId", "url", "observedAt"}:
            raise SkillInputDenied("DMA_RESEARCH_SOURCE_INVALID")
        parsed = urlparse(str(source["url"]))
        if parsed.scheme != "https" or not parsed.hostname or _is_private_host(parsed.hostname):
            raise SkillInputDenied("DMA_RESEARCH_SOURCE_FORBIDDEN")
        source_id = str(source["sourceId"])
        if not source_id or source_id in source_ids:
            raise SkillInputDenied("DMA_RESEARCH_SOURCE_INVALID")
        source_ids.add(source_id)
        normalized_sources.append(
            {"sourceId": source_id, "url": str(source["url"]), "observedAt": str(source["observedAt"])}
        )

    normalized_claims: list[dict[str, str]] = []
    for claim in claims:
        if not isinstance(claim, dict) or set(claim) != {"claim", "sourceId"}:
            raise SkillInputDenied("DMA_RESEARCH_CLAIM_INVALID")
        if claim["sourceId"] not in source_ids or not str(claim["claim"]).strip():
            raise SkillInputDenied("DMA_RESEARCH_CITATION_MISSING")
        normalized_claims.append({"claim": str(claim["claim"]), "sourceId": str(claim["sourceId"])})

    maturity_inputs = payload.get("maturityDimensions", {})
    if not isinstance(maturity_inputs, dict) or set(maturity_inputs) != set(MATURITY_DIMENSIONS):
        raise SkillInputDenied("DMA_RESEARCH_MATURITY_INVALID")
    try:
        dimensions = {
            dimension_id: MaturityDimension(
                dimension_id=dimension_id,
                score=value.get("score"),
                evidence_refs=tuple(value.get("evidenceRefs", ())),
                confidence=Decimal(str(value.get("confidence", 0))),
                limitations=tuple(value.get("limitations", ())),
                disputed=bool(value.get("disputed", False)),
                stale=bool(value.get("stale", False)),
            )
            for dimension_id, value in maturity_inputs.items()
        }
        maturity = assess_maturity(dimensions)
    except (AttributeError, TypeError, ValueError, ArithmeticError) as error:
        raise SkillInputDenied("DMA_RESEARCH_MATURITY_INVALID") from error
    return {
        "kind": "MARKET_RESEARCH_REPORT",
        "status": "PARTIAL" if unavailable else "COMPLETE",
        "sources": normalized_sources,
        "claims": normalized_claims,
        "maturity": {
            "state": maturity.state,
            "auditScore": str(maturity.audit_score) if maturity.audit_score is not None else None,
            "displayLevel": maturity.display_level,
            "evidenceCoverage": maturity.evidence_coverage,
            "missingDimensions": list(maturity.missing_dimensions),
        },
        "unavailableProviders": [str(value) for value in unavailable],
        "limitations": [f"Unavailable source: {value}" for value in unavailable],
        "sideEffects": [],
    }


def create_content_strategy(payload: dict[str, Any]) -> dict[str, Any]:
    profile_revision = payload.get("profileRevision")
    research_revision = payload.get("researchRevision")
    themes = payload.get("themes")
    if not isinstance(profile_revision, str) or not profile_revision:
        raise SkillInputDenied("DMA_STRATEGY_PROFILE_REVISION_REQUIRED")
    if not isinstance(research_revision, str) or not research_revision:
        raise SkillInputDenied("DMA_STRATEGY_RESEARCH_REVISION_REQUIRED")
    if payload.get("researchStatus") not in {"REVIEWED", "PARTIAL_REVIEWED"}:
        raise SkillInputDenied("DMA_STRATEGY_RESEARCH_NOT_REVIEWED")
    if not isinstance(themes, list) or not themes or any(not isinstance(theme, str) or not theme for theme in themes):
        raise SkillInputDenied("DMA_STRATEGY_THEMES_INVALID")
    try:
        start_date = date.fromisoformat(str(payload["startDate"]))
    except (KeyError, ValueError) as error:
        raise SkillInputDenied("DMA_STRATEGY_START_DATE_INVALID") from error

    calendar = [
        {
            "day": day + 1,
            "date": (start_date + timedelta(days=day)).isoformat(),
            "theme": themes[day % len(themes)],
            "state": "DRAFT",
        }
        for day in range(30)
    ]
    return {
        "kind": "CONTENT_STRATEGY_PROPOSAL",
        "status": "PENDING_CUSTOMER_APPROVAL",
        "profileRevision": profile_revision,
        "researchRevision": research_revision,
        "calendar": calendar,
        "publicationAllowed": False,
        "sideEffects": [],
    }


def _is_private_host(hostname: str) -> bool:
    if hostname == "localhost" or hostname.endswith(".local"):
        return True
    try:
        return ip_address(hostname).is_private
    except ValueError:
        return False