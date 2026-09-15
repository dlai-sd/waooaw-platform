"""Focused deterministic behavior tests for DMA Release 1 Skills 0/1/2."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from digital_marketing.skills import (
    SkillInputDenied,
    create_content_strategy,
    profile_customer,
    research_market,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIRECTORY = ROOT / "architecture/reference/api-specs/schemas"


def validate_contract(name: str, payload: dict[str, object]) -> None:
    schema = json.loads((SCHEMA_DIRECTORY / name).read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(payload)


def test_profile_never_promotes_inference_to_confirmed_fact() -> None:
    payload = {
        "fields": {
            "accountMode": {"value": "OWNER_OPERATED", "provenance": "CONFIRMED"},
            "businessIdentity": {"value": "Clinic", "provenance": "OBSERVED"},
            "audience": {"value": "Families", "provenance": "INFERRED"},
        }
    }
    result = profile_customer(payload)

    validate_contract("dma-customer-profiling-v1.schema.json", payload)
    validate_contract("dma-customer-profiling-v1.schema.json", result)
    assert result["status"] == "INCOMPLETE"
    assert result["confirmedFieldCount"] == 1
    assert result["fields"]["audience"]["provenance"] == "INFERRED"
    assert result["fields"]["priority"]["provenance"] == "MISSING"
    assert result["sideEffects"] == []


def test_research_requires_citations_and_discloses_partial_sources() -> None:
    payload = {
        "sources": [{"sourceId": "source-1", "url": "https://public.example/market", "observedAt": "2026-09-15"}],
        "claims": [{"claim": "Demand is seasonal.", "sourceId": "source-1"}],
        "maturitySignals": {"website": 2, "directory": 1},
        "unavailableProviders": ["public-directory-simulator"],
    }

    result = research_market(payload)

    validate_contract("dma-market-research-v1.schema.json", payload)
    validate_contract("dma-market-research-v1.schema.json", result)
    assert result["status"] == "PARTIAL"
    assert result["maturityPercent"] == 75
    assert result["claims"][0]["sourceId"] == "source-1"
    assert result["limitations"] == ["Unavailable source: public-directory-simulator"]
    with pytest.raises(SkillInputDenied, match="DMA_RESEARCH_CITATION_MISSING"):
        research_market({**payload, "claims": [{"claim": "Unsupported", "sourceId": "missing"}]})
    with pytest.raises(SkillInputDenied, match="DMA_RESEARCH_SOURCE_FORBIDDEN"):
        research_market(
            {
                **payload,
                "sources": [{"sourceId": "source-1", "url": "http://127.0.0.1/private", "observedAt": "2026-09-15"}],
            }
        )


def test_strategy_binds_upstream_revisions_and_has_no_publication_path() -> None:
    payload = {
        "profileRevision": "profile-3",
        "researchRevision": "research-2",
        "researchStatus": "REVIEWED",
        "startDate": "2026-10-01",
        "themes": ["education", "community"],
    }
    result = create_content_strategy(payload)

    validate_contract("dma-content-strategy-v1.schema.json", payload)
    validate_contract("dma-content-strategy-v1.schema.json", result)
    assert result["status"] == "PENDING_CUSTOMER_APPROVAL"
    assert result["profileRevision"] == "profile-3"
    assert result["researchRevision"] == "research-2"
    assert len(result["calendar"]) == 30
    assert result["publicationAllowed"] is False
    assert result["sideEffects"] == []
    with pytest.raises(SkillInputDenied, match="DMA_STRATEGY_RESEARCH_NOT_REVIEWED"):
        create_content_strategy(
            {
                "profileRevision": "profile-3",
                "researchRevision": "research-2",
                "researchStatus": "UNREVIEWED",
                "startDate": "2026-10-01",
                "themes": ["education"],
            }
        )
