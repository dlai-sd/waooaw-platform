"""WC-174 DMA behaviour for the three modes: proposals the platform stores as suggestions, never actions."""

# Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R006, R008, R011, R013, R014, R016, R021
# Implements: architecture/reference/agents/digital-marketing-agent.md §Skill 2 (content planning), §3.21 (theme cascade)
# Constitutional basis: C-058, C-061, C-062, C-063, C-071, C-094

from __future__ import annotations

import calendar
import hashlib
import re
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

from .skills import SkillInputDenied, _is_private_host

SENSITIVE_LAYERS = frozenset({"RELIGION", "POLITICS"})
ALWAYS_SUGGESTED_LAYERS = ("FESTIVAL", "LOCAL", "SEASON")
LAYER_FIT = {
    "SPORT": frozenset({"fitness", "sports", "restaurant", "cafe", "gym"}),
    "ART": frozenset({"beauty", "design", "photography", "education", "boutique", "studio"}),
}
MAXIMUM_CANDIDATES = 200
MAXIMUM_PROPOSALS = 100
_IDENTIFIER = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_UNSAFE_TEXT = re.compile(r"[<>{}`\\]")

# One platform's style, tuned per platform while the message stays the same.
PLATFORM_STYLE: dict[str, dict[str, Any]] = {
    "FACEBOOK": {"limit": 600, "hashtags": 2, "tone": "warm"},
    "INSTAGRAM": {"limit": 300, "hashtags": 5, "tone": "visual"},
    "WHATSAPP_BUSINESS": {"limit": 250, "hashtags": 0, "tone": "personal"},
    "YOUTUBE": {"limit": 500, "hashtags": 3, "tone": "descriptive"},
    "LINKEDIN": {"limit": 700, "hashtags": 3, "tone": "professional"},
    "GOOGLE_BUSINESS": {"limit": 300, "hashtags": 0, "tone": "factual"},
}
DEFAULT_STYLE = {"limit": 280, "hashtags": 0, "tone": "plain"}
UNAPPROVED_CLAIMS = ("best", "guaranteed", "#1", "100%", "cure", "no.1", "number one")
UNSAFE_TERMS = ("hate", "kill", "attack", "abuse", "slur")
STORY_DURATION_SECONDS = {"INSTAGRAM": 30, "FACEBOOK": 45, "YOUTUBE": 60, "LINKEDIN": 45}
PLAN_LEVELS = ("MASTER_THEME", "WEEKLY_THEME", "INDIVIDUAL_THEME", "STORY")
GOAL_TEMPLATES = {
    "CUSTOMER_PROFILING": ("A confirmed profile, kept current", "CUSTOMER_CONFIRMATION", "MONTHLY"),
    "CONTENT_STRATEGY_AND_CALENDAR": ("A reviewed plan every month", "PLATFORM_OWNER_RECORD", "MONTHLY"),
    "SOCIAL_CONTENT_CREATION_AND_PUBLISHING": ("Approved posts published on time", "PLATFORM_OWNER_RECORD", "WEEKLY"),
    "VISUAL_AND_VIDEO_CONTENT": ("Pictures and short videos that fit each post", "PLATFORM_OWNER_RECORD", "MONTHLY"),
    "MARKETING_PERFORMANCE_AND_IMPROVEMENT": ("Results read against every goal", "PLATFORM_OWNER_RECORD", "MONTHLY"),
}


def _key(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:24]


def _text(value: Any, *, maximum: int, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or _UNSAFE_TEXT.search(value):
        raise SkillInputDenied(code)
    return value.strip()


def _iso(value: Any, code: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as error:
        raise SkillInputDenied(code) from error


def _public_https(url: Any, code: str) -> str:
    parsed = urlparse(str(url))
    if parsed.scheme != "https" or not parsed.hostname or _is_private_host(parsed.hostname):
        raise SkillInputDenied(code)
    return str(url)


def suggest_layers(business_domain: str, requested: tuple[str, ...] = ()) -> list[str]:
    """Layers that fit the business. A sensitive layer is suggested only when the customer asked for it."""
    domain = business_domain.strip().lower()
    layers = list(ALWAYS_SUGGESTED_LAYERS)
    layers.extend(layer for layer, domains in LAYER_FIT.items() if domain in domains)
    layers.extend(layer for layer in requested if layer in SENSITIVE_LAYERS)
    return layers


def research_calendar_events(payload: dict[str, Any]) -> dict[str, Any]:
    """Ranks candidate events the platform read through the governed tool registry; this never reads anything itself."""
    profile = payload.get("profile")
    enabled = payload.get("enabledLayers")
    window = payload.get("window")
    candidates = payload.get("candidates")
    if not isinstance(profile, dict) or not isinstance(enabled, list) or not isinstance(window, dict):
        raise SkillInputDenied("DMA_CALENDAR_INPUT_INVALID")
    if not isinstance(candidates, list) or len(candidates) > MAXIMUM_CANDIDATES:
        raise SkillInputDenied("DMA_CALENDAR_CANDIDATES_INVALID")
    domain = _text(profile.get("businessDomain"), maximum=80, code="DMA_CALENDAR_PROFILE_INVALID")
    location = _text(profile.get("location"), maximum=120, code="DMA_CALENDAR_PROFILE_INVALID").lower()
    language = str(profile.get("language", "")).lower()
    start, end = _iso(window.get("start"), "DMA_CALENDAR_WINDOW_INVALID"), _iso(window.get("end"), "DMA_CALENDAR_WINDOW_INVALID")
    if end < start or (end - start).days > 400:
        raise SkillInputDenied("DMA_CALENDAR_WINDOW_INVALID")
    layers_on = {str(layer) for layer in enabled}
    fits = set(suggest_layers(domain))

    proposals: list[dict[str, Any]] = []
    withheld: list[dict[str, str]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            raise SkillInputDenied("DMA_CALENDAR_CANDIDATES_INVALID")
        candidate_id = _text(candidate.get("candidateId"), maximum=120, code="DMA_CALENDAR_CANDIDATE_INVALID")
        layer = str(candidate.get("layer", ""))
        if not _IDENTIFIER.match(layer):
            raise SkillInputDenied("DMA_CALENDAR_CANDIDATE_INVALID")
        day = _iso(candidate.get("date"), "DMA_CALENDAR_CANDIDATE_INVALID")
        title = _text(candidate.get("title"), maximum=160, code="DMA_CALENDAR_CANDIDATE_INVALID")
        url = _public_https(candidate.get("sourceUrl"), "DMA_CALENDAR_SOURCE_FORBIDDEN")
        # Nothing is suggested on a layer the customer has off, and a sensitive layer is never on by default.
        if layer not in layers_on:
            withheld.append({"candidateId": candidate_id, "code": "LAYER_OFF"})
            continue
        if not start <= day <= end:
            withheld.append({"candidateId": candidate_id, "code": "OUTSIDE_WINDOW"})
            continue
        locality = str(candidate.get("locality", "")).lower()
        score = 0.5
        reasons = [f"Falls on the {layer.lower()} layer you switched on"]
        if layer in fits:
            score += 0.2
            reasons.append(f"fits a {domain.lower()} business")
        if locality and locality in location:
            score += 0.2
            reasons.append(f"happens in {candidate.get('locality')}")
        if language and language == str(candidate.get("language", "")).lower():
            score += 0.1
            reasons.append("matches your language")
        if layer in SENSITIVE_LAYERS:
            reasons.append("content on this layer always needs your approval")
        proposals.append(
            {
                "proposalKey": _key("event", candidate_id),
                "kind": "EVENT",
                "layer": layer,
                "title": title,
                "startDate": day.isoformat(),
                "sourceRef": url,
                "reason": "; ".join(reasons) + ".",
                "confidence": round(min(score, 1.0), 2),
                "payload": {"observedAt": str(candidate.get("observedAt", "")), "approvalGated": layer in SENSITIVE_LAYERS},
            }
        )
    proposals.sort(key=lambda item: (-item["confidence"], item["startDate"], item["proposalKey"]))
    return {
        "kind": "CALENDAR_EVENT_PROPOSALS",
        "proposals": proposals[:MAXIMUM_PROPOSALS],
        "withheld": withheld,
        "suggestedLayers": suggest_layers(domain),
        "sideEffects": [],
    }


def build_plan_level(payload: dict[str, Any]) -> dict[str, Any]:
    """Builds one level of the plan tree. A level is built only under a parent the customer approved."""
    level = payload.get("level")
    if level not in PLAN_LEVELS:
        raise SkillInputDenied("DMA_PLAN_LEVEL_INVALID")
    month = str(payload.get("month", ""))
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise SkillInputDenied("DMA_PLAN_MONTH_INVALID")
    year, number = int(month[:4]), int(month[5:])
    first = date(year, number, 1)
    last = date(year, number, calendar.monthrange(year, number)[1])
    events = [str(event) for event in payload.get("eventTitles", []) if isinstance(event, str)][:8]
    platforms = [str(value) for value in payload.get("platforms", []) if isinstance(value, str)] or ["FACEBOOK"]
    parent = payload.get("parent")
    if level != PLAN_LEVELS[0]:
        if not isinstance(parent, dict) or parent.get("level") != PLAN_LEVELS[PLAN_LEVELS.index(level) - 1]:
            raise SkillInputDenied("DMA_PLAN_PARENT_REQUIRED")
        if parent.get("approved") is not True:
            raise SkillInputDenied("DMA_PLAN_PARENT_NOT_APPROVED")
        parent_key = _text(parent.get("key"), maximum=120, code="DMA_PLAN_PARENT_REQUIRED")
        parent_title = _text(parent.get("title"), maximum=160, code="DMA_PLAN_PARENT_REQUIRED")
    else:
        parent_key, parent_title = None, ""

    nodes: list[dict[str, Any]] = []
    if level == "MASTER_THEME":
        titles = events[:3] or [f"{first.strftime('%B')} focus"]
        title = f"{first.strftime('%B')}: {titles[0]}"
        nodes.append(_node(level, title, f"Built from {len(events)} calendar events and your profile.", first, last, None))
    elif level == "WEEKLY_THEME":
        starts = [first + timedelta(days=7 * index) for index in range(5) if first + timedelta(days=7 * index) <= last]
        for index, start in enumerate(starts):
            end = min(start + timedelta(days=6), last)
            focus = events[index] if index < len(events) else parent_title
            nodes.append(_node(level, f"Week {index + 1}: {focus}", f"Supports {parent_title}.", start, end, parent_key))
    elif level == "INDIVIDUAL_THEME":
        start = _iso(payload.get("weekStart"), "DMA_PLAN_WEEK_INVALID")
        for index, platform in enumerate(platforms[:4]):
            nodes.append(
                _node(
                    level,
                    f"{parent_title} on {platform.title()}",
                    f"One idea for {platform.title()}.",
                    start + timedelta(days=index),
                    start + timedelta(days=index),
                    parent_key,
                    platform,
                )
            )
    else:
        platform = str(payload.get("platform", platforms[0]))
        actors = [str(value) for value in payload.get("actors", []) if isinstance(value, str)] or ["The owner and the team"]
        duration = STORY_DURATION_SECONDS.get(platform, 30)
        start = _iso(payload.get("date"), "DMA_PLAN_DATE_INVALID")
        screenplay = [f"Open on {actors[0]}.", f"Show {parent_title} in a real moment.", "Close with one clear invitation."]
        node = _node(level, f"Story: {parent_title}", " ".join(screenplay), start, start, parent_key, platform)
        node["payload"].update({"actors": actors, "screenplay": screenplay, "durationSeconds": duration})
        nodes.append(node)
    return {"kind": "PLAN_LEVEL_PROPOSALS", "level": level, "proposals": nodes, "sideEffects": []}


def _node(
    level: str, title: str, body: str, start: date, end: date, parent_key: str | None, platform: str | None = None
) -> dict[str, Any]:
    return {
        "proposalKey": _key("node", level, title, start.isoformat(), parent_key or ""),
        "kind": "PLAN_NODE",
        "levelId": level,
        "parentProposalKey": parent_key,
        "title": title[:160],
        "body": body,
        "startDate": start.isoformat(),
        "endDate": end.isoformat(),
        "platformId": platform.upper() if platform else None,
        "payload": {},
    }


def create_platform_drafts(payload: dict[str, Any]) -> dict[str, Any]:
    """One approved story becomes a draft per platform: same message, platform style, review checks before the customer sees it."""
    story = payload.get("story")
    platforms = payload.get("platforms")
    brand = payload.get("brand", {})
    rights = payload.get("rights", {})
    if not isinstance(story, dict) or not isinstance(platforms, list) or not platforms or not isinstance(brand, dict):
        raise SkillInputDenied("DMA_DRAFT_INPUT_INVALID")
    message = _text(story.get("message"), maximum=900, code="DMA_DRAFT_MESSAGE_INVALID")
    title = _text(story.get("title"), maximum=160, code="DMA_DRAFT_TITLE_INVALID")
    layer = story.get("layer")
    enabled = {str(value) for value in payload.get("enabledLayers", [])}
    component = payload.get("componentId")
    approved_claims = tuple(str(value).lower() for value in brand.get("approvedClaims", []))
    banned = tuple(str(value).lower() for value in brand.get("bannedWords", []))
    uses_likeness = bool(story.get("usesLikeness", False))
    keywords = [word for word in re.findall(r"[A-Za-z]{4,}", title)][:5]

    proposals: list[dict[str, Any]] = []
    withheld: list[dict[str, Any]] = []
    for platform in platforms:
        platform_id = str(platform).upper()
        style = PLATFORM_STYLE.get(platform_id, DEFAULT_STYLE)
        hashtags = [f"#{word.capitalize()}" for word in keywords[: style["hashtags"]]]
        text = message if len(message) <= style["limit"] else message[: style["limit"] - 1].rstrip() + "…"
        if hashtags:
            text = (text + "\n" + " ".join(hashtags))[: max(style["limit"], len(text))]
        lowered = text.lower()
        checks = [
            {"checkId": "BRAND_VOICE", "passed": not any(word in lowered for word in banned), "detail": "No banned words."},
            {
                "checkId": "CLAIMS",
                "passed": all(claim in approved_claims for claim in UNAPPROVED_CLAIMS if claim in lowered),
                "detail": "Only approved claims.",
            },
            {
                "checkId": "RIGHTS_AND_LIKENESS",
                "passed": (not uses_likeness) or bool(rights.get("likenessConsent")),
                "detail": "Likeness has consent (C-058).",
            },
            {
                "checkId": "CONTENT_SAFETY",
                "passed": not any(term in lowered for term in UNSAFE_TERMS)
                and (layer is None or layer not in SENSITIVE_LAYERS or layer in enabled),
                "detail": "Safe and on a layer you chose (C-061).",
            },
            {"checkId": "PLATFORM_FIT", "passed": len(text) <= style["limit"] + 40, "detail": f"Fits {platform_id.title()}."},
        ]
        failed = [check["checkId"] for check in checks if not check["passed"]]
        if failed:
            # A draft that fails a check is never shown to the customer.
            withheld.append({"platformId": platform_id, "failedChecks": failed})
            continue
        proposals.append(
            {
                "proposalKey": _key("draft", platform_id, title, message),
                "kind": "CONTENT",
                "layer": layer,
                "title": f"{title} ({platform_id.title()})",
                "body": text,
                "platformId": platform_id,
                "componentId": component,
                "payload": {"reviewChecks": checks, "tone": style["tone"], "hashtags": hashtags},
            }
        )
    media = _media_state(payload)
    return {"kind": "PLATFORM_DRAFT_PROPOSALS", "proposals": proposals, "withheld": withheld, "media": media, "sideEffects": []}


def _media_state(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload.get("wantsMedia"):
        return {"state": "NOT_REQUESTED"}
    if payload.get("mediaProviderAuthorized") is not True:
        return {"state": "NOT_ENABLED_YET", "message": "Pictures and short videos are not enabled yet. Nothing was attempted."}
    # B1 produces asset metadata only; the provider call itself is the platform's, never this image's.
    return {"state": "METADATA_ONLY", "message": "Asset details recorded; the platform generates it under an authorized rate."}


def induction_turn(payload: dict[str, Any]) -> dict[str, Any]:
    """One focused conversation turn: what is already found, labels to confirm, and exactly one new question."""
    requirements = payload.get("requirements")
    findings = payload.get("findings", [])
    platforms = payload.get("platforms", [])
    trust = payload.get("trust", {})
    if not isinstance(requirements, list) or not requirements:
        raise SkillInputDenied("DMA_INDUCTION_INPUT_INVALID")
    first_turn = bool(payload.get("firstTurn", False))
    labels = []
    for finding in findings if isinstance(findings, list) else []:
        if not isinstance(finding, dict):
            raise SkillInputDenied("DMA_INDUCTION_FINDING_INVALID")
        label = _text(finding.get("value"), maximum=160, code="DMA_INDUCTION_FINDING_INVALID")
        ref = _text(finding.get("requirementRef"), maximum=64, code="DMA_INDUCTION_FINDING_INVALID")
        labels.append(
            {
                "proposalKey": _key("label", ref, label),
                "kind": "PROFILE_LABEL",
                "title": label,
                "reason": f"Found from {finding.get('source', 'your public pages')}; confirm it or correct it.",
                "sourceRef": _public_https(finding["source"], "DMA_INDUCTION_FINDING_INVALID")
                if str(finding.get("source", "")).startswith("http")
                else None,
                "confidence": float(finding.get("confidence", 0.6)),
                "payload": {"requirementRef": ref, "group": str(finding.get("group", "Business"))},
            }
        )
    open_items = [item for item in requirements if isinstance(item, dict) and item.get("state") != "CONFIRMED"]
    mandatory_open = sorted((item for item in open_items if item.get("mandatory")), key=lambda item: str(item.get("ref")))
    unanswered = [item for item in platforms if isinstance(item, dict) and not item.get("answer")]
    purpose_explained = bool(trust.get("purposeExplained")) if isinstance(trust, dict) else False
    question: dict[str, Any] | None = None
    for item in mandatory_open:
        # D06: a sensitive item is asked only after its purpose has been explained.
        if item.get("sensitive") and not purpose_explained:
            question = {
                "requirementRef": item["ref"],
                "kind": "EXPLAIN_PURPOSE",
                "text": f"Before I ask about {item['label']}, here is why it helps and how it is kept safe.",
            }
        else:
            question = {"requirementRef": item["ref"], "kind": "ASK", "text": f"What is your {str(item['label']).lower()}?"}
        break
    if question is None and unanswered:
        label = str(unanswered[0].get("label", "this platform"))
        question = {
            "platformId": unanswered[0].get("platformId"),
            "kind": "ASK_PLATFORM",
            "text": f"Is your business on {label}? Present or not present is fine.",
        }
    unknown = [
        item
        for item in requirements
        if isinstance(item, dict) and item.get("state") in {"MISSING", "STALE", "CONFLICTED", "UNKNOWN"}
    ]
    mandatory_ok = not mandatory_open
    if mandatory_ok and not unanswered and not unknown:
        state = "READY"
    elif mandatory_ok and not unanswered:
        state = "PARTIAL"
    else:
        state = "INCOMPLETE"
    return {
        "kind": "INDUCTION_TURN",
        "opening": "Here is what I already found about your business." if first_turn and labels else None,
        "labels": labels,
        "nextQuestion": question,
        "summaryState": state,
        "sideEffects": [],
    }


def enrich_public_footprint(payload: dict[str, Any]) -> dict[str, Any]:
    """Turns facts the platform read from public pages into findings the customer can see, correct and remove."""
    facts = payload.get("facts")
    if not isinstance(facts, list) or len(facts) > MAXIMUM_PROPOSALS:
        raise SkillInputDenied("DMA_ENRICHMENT_INPUT_INVALID")
    registry_allowed = payload.get("registryAllowed") is True
    findings, withheld = [], []
    for fact in facts:
        if not isinstance(fact, dict):
            raise SkillInputDenied("DMA_ENRICHMENT_FACT_INVALID")
        fact_id = _text(fact.get("factId"), maximum=120, code="DMA_ENRICHMENT_FACT_INVALID")
        basis = str(fact.get("basis", ""))
        if basis not in {"PUBLIC_PAGE", "GOOGLE_LISTING", "REGISTRY", "OPEN_DATA"}:
            raise SkillInputDenied("DMA_ENRICHMENT_BASIS_INVALID")
        if basis in {"REGISTRY", "OPEN_DATA"} and not registry_allowed:
            withheld.append({"factId": fact_id, "code": "LAWFUL_BASIS_NOT_DECIDED"})
            continue
        findings.append(
            {
                "proposalKey": _key("finding", fact_id),
                "kind": "FINDING",
                "title": _text(fact.get("label"), maximum=160, code="DMA_ENRICHMENT_FACT_INVALID"),
                "body": _text(fact.get("value"), maximum=500, code="DMA_ENRICHMENT_FACT_INVALID"),
                "sourceRef": _public_https(fact.get("sourceUrl"), "DMA_ENRICHMENT_SOURCE_FORBIDDEN"),
                "reason": {
                    "PUBLIC_PAGE": "Published openly on a public page.",
                    "GOOGLE_LISTING": "Published openly on the business listing.",
                    "REGISTRY": "Public registry read under the Founder's lawful-use decision.",
                    "OPEN_DATA": "Open government data read under the Founder's lawful-use decision.",
                }[basis],
                "confidence": round(float(fact.get("confidence", 0.5)), 2),
                "payload": {"basis": basis, "observedAt": str(fact.get("observedAt", ""))},
            }
        )
    return {"kind": "PUBLIC_FOOTPRINT_FINDINGS", "proposals": findings, "withheld": withheld, "sideEffects": []}


def propose_goals(payload: dict[str, Any]) -> dict[str, Any]:
    """A goal per skill with the fields D06 requires before any live work: baseline, target, evidence source, cadence, authority."""
    skills = payload.get("skills")
    baselines = payload.get("baselines", {})
    authority = str(payload.get("authorityState", "CUSTOMER_APPROVAL"))
    if not isinstance(skills, list) or not skills or not isinstance(baselines, dict):
        raise SkillInputDenied("DMA_GOALS_INPUT_INVALID")
    proposals = []
    for skill in skills:
        if skill not in GOAL_TEMPLATES:
            raise SkillInputDenied("DMA_GOALS_SKILL_INVALID")
        target, source, cadence = GOAL_TEMPLATES[skill]
        baseline = str(baselines.get(skill, "Not measured yet"))
        proposals.append(
            {
                "proposalKey": _key("goal", skill),
                "kind": "GOAL",
                "title": target,
                "sourceRef": source,
                "payload": {
                    "skillId": skill,
                    "baseline": baseline,
                    "target": target,
                    "evidenceSource": source,
                    "cadence": cadence,
                    "authorityState": authority,
                },
            }
        )
    return {"kind": "GOAL_PROPOSALS", "proposals": proposals, "sideEffects": []}


def build_digest(payload: dict[str, Any]) -> dict[str, Any]:
    """The monthly digest and the two-month review: goal against baseline and now, one recommendation, at most one request."""
    goals = payload.get("goals")
    month = str(payload.get("month", ""))
    if not isinstance(goals, list) or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise SkillInputDenied("DMA_DIGEST_INPUT_INVALID")
    rows, behind = [], []
    for goal in goals:
        if not isinstance(goal, dict) or goal.get("skillId") not in GOAL_TEMPLATES:
            raise SkillInputDenied("DMA_DIGEST_GOAL_INVALID")
        measured = goal.get("current") is not None
        if measured and goal.get("pace") is not None and float(goal["pace"]) < 0.6:
            behind.append(goal["skillId"])
        rows.append(
            {
                "skillId": goal["skillId"],
                "baseline": goal.get("baseline"),
                "current": goal.get("current") if measured else "Not measured",
                "howToMeasure": None if measured else "Connect a source that records it, or tell me the figure.",
                "source": goal.get("source"),
                "freshness": goal.get("freshness"),
            }
        )
    worked = [str(item) for item in payload.get("whatWorked", []) if isinstance(item, str)][:3]
    recommendation = str(payload.get("recommendation", "")) or (
        f"Do more of: {worked[0]}." if worked else "Keep the plan as it is this month."
    )
    request = str(payload.get("request", "")) or None
    changes = [
        {"skillId": change["skillId"], "target": str(change["target"])}
        for change in payload.get("goalChanges", [])
        if isinstance(change, dict) and change.get("skillId") in GOAL_TEMPLATES and change.get("target")
    ][:2]
    review_due = bool(payload.get("twoMonthReview", False))
    return {
        "kind": "MONTHLY_DIGEST",
        "proposals": [
            {
                "proposalKey": _key("digest", month),
                "kind": "DIGEST",
                "title": f"{month} digest" + (" and two-month review" if review_due else ""),
                "body": recommendation,
                "payload": {
                    "month": month,
                    "rows": rows,
                    "recommendation": recommendation,
                    "request": request,
                    "goalChanges": changes,
                    "behindPace": sorted(set(behind)),
                },
            }
        ],
        "sideEffects": [],
    }
