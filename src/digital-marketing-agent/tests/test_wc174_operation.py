"""WC-174 DMA behaviour: proposals for the three modes, never actions."""

# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R006, R008, R011, R013, R014, R016, R021
# Constitutional basis: C-058, C-061, C-062, C-063, C-071, C-094

from __future__ import annotations

import pytest

from digital_marketing import create_adapter
from digital_marketing.adapter import OPERATIONS
from digital_marketing.operation import (
    SENSITIVE_LAYERS,
    build_digest,
    build_plan_level,
    create_platform_drafts,
    enrich_public_footprint,
    induction_turn,
    propose_goals,
    research_calendar_events,
    suggest_layers,
)
from digital_marketing.skills import SkillInputDenied

PROFILE = {"businessDomain": "Dental", "location": "Pune, Maharashtra", "language": "en"}
WINDOW = {"start": "2026-12-01", "end": "2026-12-31"}


def candidate(candidate_id: str, layer: str, day: str = "2026-12-12", **extra: object) -> dict[str, object]:
    return {
        "candidateId": candidate_id,
        "layer": layer,
        "title": f"{layer.title()} event",
        "date": day,
        "sourceUrl": "https://example.org/calendar",
        "observedAt": "2026-11-26T10:00:00Z",
        **extra,
    }


def research(candidates: list[dict[str, object]], enabled: list[str]) -> dict[str, object]:
    return research_calendar_events({"profile": PROFILE, "enabledLayers": enabled, "window": WINDOW, "candidates": candidates})


def test_calendar_events_come_with_source_reason_and_confidence_and_layers_off_are_withheld() -> None:
    result = research(
        [
            candidate("a", "FESTIVAL", locality="Pune", language="en"),
            candidate("b", "RELIGION"),
            candidate("c", "SPORT"),
            candidate("d", "LOCAL", day="2027-02-01"),
        ],
        ["FESTIVAL", "LOCAL"],
    )

    assert [item["layer"] for item in result["proposals"]] == ["FESTIVAL"]
    event = result["proposals"][0]
    assert event["sourceRef"] == "https://example.org/calendar"
    assert event["confidence"] == 1.0
    assert "happens in Pune" in event["reason"]
    assert {item["code"] for item in result["withheld"]} == {"LAYER_OFF", "OUTSIDE_WINDOW"}
    assert result["sideEffects"] == []


def test_a_sensitive_layer_is_proposed_only_when_the_customer_switched_it_on_and_stays_approval_gated() -> None:
    result = research([candidate("r", "RELIGION")], ["FESTIVAL", "RELIGION"])

    event = result["proposals"][0]
    assert event["payload"]["approvalGated"] is True
    assert "always needs your approval" in event["reason"]
    assert SENSITIVE_LAYERS == {"RELIGION", "POLITICS"}
    assert not (SENSITIVE_LAYERS & set(suggest_layers("Dental")))
    assert SENSITIVE_LAYERS & set(suggest_layers("Dental", ("RELIGION",))) == {"RELIGION"}
    assert "SPORT" in suggest_layers("fitness") and "ART" in suggest_layers("Beauty")


@pytest.mark.parametrize(
    "bad",
    [
        {"sourceUrl": "http://example.org/x"},
        {"sourceUrl": "https://localhost/x"},
        {"sourceUrl": "https://10.0.0.5/x"},
        {"title": "<script>"},
        {"date": "not-a-date"},
        {"layer": "religion"},
    ],
)
def test_calendar_research_refuses_unsafe_or_malformed_candidates(bad: dict[str, object]) -> None:
    with pytest.raises(SkillInputDenied):
        research([{**candidate("x", "FESTIVAL"), **bad}], ["FESTIVAL"])


def test_the_plan_is_built_one_level_at_a_time_and_only_under_an_approved_parent() -> None:
    master = build_plan_level({"level": "MASTER_THEME", "month": "2026-12", "eventTitles": ["Diwali", "Christmas"]})["proposals"][
        0
    ]
    assert master["levelId"] == "MASTER_THEME" and master["parentProposalKey"] is None

    with pytest.raises(SkillInputDenied, match="DMA_PLAN_PARENT_NOT_APPROVED"):
        build_plan_level(
            {
                "level": "WEEKLY_THEME",
                "month": "2026-12",
                "parent": {"level": "MASTER_THEME", "key": master["proposalKey"], "title": master["title"], "approved": False},
            }
        )
    with pytest.raises(SkillInputDenied, match="DMA_PLAN_PARENT_REQUIRED"):
        build_plan_level(
            {
                "level": "STORY",
                "month": "2026-12",
                "date": "2026-12-03",
                "parent": {"level": "MASTER_THEME", "key": "k", "title": "t", "approved": True},
            }
        )

    weekly = build_plan_level(
        {
            "level": "WEEKLY_THEME",
            "month": "2026-12",
            "eventTitles": ["Diwali"],
            "parent": {"level": "MASTER_THEME", "key": master["proposalKey"], "title": master["title"], "approved": True},
        }
    )["proposals"]
    assert len(weekly) == 5 and all(node["parentProposalKey"] == master["proposalKey"] for node in weekly)
    individual = build_plan_level(
        {
            "level": "INDIVIDUAL_THEME",
            "month": "2026-12",
            "weekStart": "2026-12-01",
            "platforms": ["Facebook", "Instagram"],
            "parent": {"level": "WEEKLY_THEME", "key": weekly[0]["proposalKey"], "title": weekly[0]["title"], "approved": True},
        }
    )["proposals"]
    assert [node["platformId"] for node in individual] == ["FACEBOOK", "INSTAGRAM"]
    story = build_plan_level(
        {
            "level": "STORY",
            "month": "2026-12",
            "date": "2026-12-03",
            "platform": "INSTAGRAM",
            "actors": ["Dr Rao"],
            "parent": {
                "level": "INDIVIDUAL_THEME",
                "key": individual[0]["proposalKey"],
                "title": individual[0]["title"],
                "approved": True,
            },
        }
    )["proposals"][0]
    assert story["payload"]["actors"] == ["Dr Rao"]
    assert story["payload"]["durationSeconds"] == 30 and len(story["payload"]["screenplay"]) == 3


def test_one_story_becomes_a_draft_per_platform_in_that_platforms_style_with_checks_passed() -> None:
    result = create_platform_drafts(
        {
            "story": {"title": "Smile checkup week", "message": "Book a free smile checkup this week." * 3, "layer": "FESTIVAL"},
            "platforms": ["Instagram", "WhatsApp_Business", "Facebook"],
            "enabledLayers": ["FESTIVAL"],
            "componentId": "SOCIAL_PUBLICATION",
            "brand": {"approvedClaims": [], "bannedWords": ["cheap"]},
        }
    )

    by_platform = {item["platformId"]: item for item in result["proposals"]}
    assert set(by_platform) == {"INSTAGRAM", "WHATSAPP_BUSINESS", "FACEBOOK"}
    assert len(by_platform["WHATSAPP_BUSINESS"]["body"]) <= 250
    assert "#" in by_platform["INSTAGRAM"]["body"] and "#" not in by_platform["WHATSAPP_BUSINESS"]["body"]
    for item in result["proposals"]:
        assert item["componentId"] == "SOCIAL_PUBLICATION"
        assert all(check["passed"] for check in item["payload"]["reviewChecks"])
    assert result["withheld"] == []


@pytest.mark.parametrize(
    ("story", "brand", "rights", "layers", "failed"),
    [
        ({"message": "The best dentist in town."}, {}, {}, [], "CLAIMS"),
        ({"message": "Cheap checkups today."}, {"bannedWords": ["cheap"]}, {}, [], "BRAND_VOICE"),
        ({"message": "Meet our patient.", "usesLikeness": True}, {}, {}, [], "RIGHTS_AND_LIKENESS"),
        ({"message": "A prayer for peace.", "layer": "RELIGION"}, {}, {}, ["FESTIVAL"], "CONTENT_SAFETY"),
        ({"message": "We hate waiting rooms and attack plaque."}, {}, {}, [], "CONTENT_SAFETY"),
    ],
)
def test_a_draft_that_fails_a_review_check_is_withheld_and_never_reaches_the_customer(
    story: dict[str, object], brand: dict[str, object], rights: dict[str, object], layers: list[str], failed: str
) -> None:
    result = create_platform_drafts(
        {
            "story": {"title": "Checkup week", **story},
            "platforms": ["Facebook"],
            "enabledLayers": layers,
            "brand": brand,
            "rights": rights,
        }
    )

    assert result["proposals"] == []
    assert failed in result["withheld"][0]["failedChecks"]


def test_a_likeness_with_consent_and_an_approved_claim_passes() -> None:
    result = create_platform_drafts(
        {
            "story": {"title": "Our team", "message": "Meet our team, the best in town.", "usesLikeness": True},
            "platforms": ["Facebook"],
            "rights": {"likenessConsent": True},
            "brand": {"approvedClaims": ["best"]},
        }
    )

    assert len(result["proposals"]) == 1


def test_video_and_audio_say_not_enabled_yet_until_a_provider_and_rate_are_authorized() -> None:
    base = {"story": {"title": "Reel", "message": "A short reel."}, "platforms": ["Instagram"], "wantsMedia": True}

    assert create_platform_drafts(base)["media"]["state"] == "NOT_ENABLED_YET"
    assert "Nothing was attempted" in create_platform_drafts(base)["media"]["message"]
    assert create_platform_drafts({**base, "mediaProviderAuthorized": True})["media"]["state"] == "METADATA_ONLY"
    assert create_platform_drafts({**base, "wantsMedia": False})["media"]["state"] == "NOT_REQUESTED"


def test_induction_asks_exactly_one_new_question_and_explains_purpose_before_a_sensitive_item() -> None:
    requirements = [
        {"ref": "DMA-IND-004", "label": "Business identity", "state": "CONFIRMED", "mandatory": True},
        {"ref": "DMA-IND-005", "label": "Business domain", "state": "MISSING", "mandatory": True},
        {"ref": "DMA-IND-006", "label": "Primary location", "state": "MISSING", "mandatory": True, "sensitive": True},
    ]
    turn = induction_turn(
        {
            "requirements": requirements,
            "firstTurn": True,
            "findings": [
                {"requirementRef": "DMA-IND-004", "value": "Rao Dental", "source": "https://example.org/about", "confidence": 0.8}
            ],
            "platforms": [{"platformId": "FACEBOOK", "label": "Facebook"}],
        }
    )

    assert turn["opening"] == "Here is what I already found about your business."
    assert turn["labels"][0]["title"] == "Rao Dental" and turn["labels"][0]["kind"] == "PROFILE_LABEL"
    assert turn["nextQuestion"]["requirementRef"] == "DMA-IND-005" and turn["nextQuestion"]["kind"] == "ASK"
    assert turn["summaryState"] == "INCOMPLETE"

    sensitive_first = induction_turn({"requirements": requirements[:1] + requirements[2:], "platforms": []})
    assert sensitive_first["nextQuestion"]["kind"] == "EXPLAIN_PURPOSE"
    after_purpose = induction_turn(
        {"requirements": requirements[:1] + requirements[2:], "platforms": [], "trust": {"purposeExplained": True}}
    )
    assert after_purpose["nextQuestion"]["kind"] == "ASK"


def test_induction_is_ready_only_when_every_platform_has_an_answer_and_nothing_is_unknown() -> None:
    done = [{"ref": "DMA-IND-004", "label": "Business identity", "state": "CONFIRMED", "mandatory": True}]

    waiting = induction_turn(
        {
            "requirements": done,
            "platforms": [
                {"platformId": "FACEBOOK", "label": "Facebook"},
                {"platformId": "YOUTUBE", "label": "YouTube", "answer": "NOT_PRESENT"},
            ],
        }
    )
    ready = induction_turn(
        {"requirements": done, "platforms": [{"platformId": "FACEBOOK", "label": "Facebook", "answer": "PRESENT"}]}
    )
    stale = induction_turn(
        {
            "requirements": [*done, {"ref": "DMA-IND-013", "label": "Competitors", "state": "STALE", "mandatory": False}],
            "platforms": [],
        }
    )

    assert waiting["summaryState"] == "INCOMPLETE" and waiting["nextQuestion"]["kind"] == "ASK_PLATFORM"
    assert ready["summaryState"] == "READY" and ready["nextQuestion"] is None
    assert stale["summaryState"] == "PARTIAL"


def test_public_enrichment_keeps_source_and_basis_and_withholds_registry_reads_until_the_founder_decides() -> None:
    facts = [
        {
            "factId": "w",
            "label": "Website",
            "value": "Rao Dental",
            "sourceUrl": "https://example.org",
            "basis": "PUBLIC_PAGE",
            "confidence": 0.9,
        },
        {"factId": "g", "label": "GST", "value": "27ABCDE1234F1Z5", "sourceUrl": "https://example.org/gst", "basis": "REGISTRY"},
    ]

    closed = enrich_public_footprint({"facts": facts})
    opened = enrich_public_footprint({"facts": facts, "registryAllowed": True})

    assert [item["payload"]["basis"] for item in closed["proposals"]] == ["PUBLIC_PAGE"]
    assert closed["withheld"] == [{"factId": "g", "code": "LAWFUL_BASIS_NOT_DECIDED"}]
    assert len(opened["proposals"]) == 2 and opened["withheld"] == []
    with pytest.raises(SkillInputDenied):
        enrich_public_footprint({"facts": [{**facts[0], "basis": "SCRAPED"}]})
    with pytest.raises(SkillInputDenied):
        enrich_public_footprint({"facts": [{**facts[0], "sourceUrl": "https://192.168.1.4/x"}]})


def test_goals_carry_every_field_d06_requires_before_live_work() -> None:
    skills = [
        "CUSTOMER_PROFILING",
        "CONTENT_STRATEGY_AND_CALENDAR",
        "SOCIAL_CONTENT_CREATION_AND_PUBLISHING",
        "VISUAL_AND_VIDEO_CONTENT",
        "MARKETING_PERFORMANCE_AND_IMPROVEMENT",
    ]

    goals = propose_goals({"skills": skills, "baselines": {"CUSTOMER_PROFILING": "3 of 17 confirmed"}})["proposals"]

    assert [goal["payload"]["skillId"] for goal in goals] == skills
    for goal in goals:
        assert {"baseline", "target", "evidenceSource", "cadence", "authorityState"} <= set(goal["payload"])
    assert goals[0]["payload"]["baseline"] == "3 of 17 confirmed" and goals[1]["payload"]["baseline"] == "Not measured yet"
    with pytest.raises(SkillInputDenied):
        propose_goals({"skills": ["RUN_PAID_ADS"]})


def test_the_digest_reads_results_against_goals_says_not_measured_and_makes_one_recommendation() -> None:
    result = build_digest(
        {
            "month": "2026-12",
            "twoMonthReview": True,
            "goals": [
                {
                    "skillId": "SOCIAL_CONTENT_CREATION_AND_PUBLISHING",
                    "baseline": "0",
                    "current": "4 posts",
                    "pace": 0.4,
                    "source": "PLATFORM_OWNER_RECORD",
                    "freshness": "today",
                },
                {"skillId": "MARKETING_PERFORMANCE_AND_IMPROVEMENT", "baseline": "n/a"},
            ],
            "whatWorked": ["Festival posts"],
            "request": "Share last month's enquiry count.",
            "goalChanges": [{"skillId": "SOCIAL_CONTENT_CREATION_AND_PUBLISHING", "target": "12 posts"}],
        }
    )

    digest = result["proposals"][0]
    rows = {row["skillId"]: row for row in digest["payload"]["rows"]}
    assert digest["title"].endswith("and two-month review")
    assert rows["MARKETING_PERFORMANCE_AND_IMPROVEMENT"]["current"] == "Not measured"
    assert "Connect a source" in rows["MARKETING_PERFORMANCE_AND_IMPROVEMENT"]["howToMeasure"]
    assert digest["payload"]["behindPace"] == ["SOCIAL_CONTENT_CREATION_AND_PUBLISHING"]
    assert digest["body"] == "Do more of: Festival posts."
    assert digest["payload"]["request"] == "Share last month's enquiry count."
    with pytest.raises(SkillInputDenied):
        build_digest({"month": "December", "goals": []})


def test_every_operation_is_a_skill_invocation_inside_a_declared_skill_and_adds_no_port() -> None:
    declared = set(create_adapter().describe().skill_versions)

    assert {skill for skill, _ in OPERATIONS} <= declared
    assert len(OPERATIONS) == 7
    assert all(callable(handler) for handler in OPERATIONS.values())
