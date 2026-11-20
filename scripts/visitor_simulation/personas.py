# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C1-05
# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Loader and validation for the fabricated simulated-customer personas."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from visitor_simulation.models import OUTCOMES, STATES, GoalSpec

PERSONAS_PATH = Path(__file__).with_name("personas.yaml")
MODES = ("normal", "skeptic", "overwhelmed")
DEFAULT_UNKNOWN_LANGUAGE_MESSAGE = "Mujhe apna business badhana hai, kya aap madad karoge?"


class PersonaError(ValueError):
    pass


@dataclass(frozen=True)
class Persona:
    id: str
    display_name: str
    subject_slug: str
    intent: str
    knowledge_of_waooaw: str
    mood: str
    patience: int
    language: str
    business_type: str
    city: str
    statement: str
    goal_keyword: str
    goal_text: str
    choice_style: str
    withhold_until_asked: int
    followup: str
    taps_link: bool
    on_giving_up: str
    goal: GoalSpec
    modes: tuple[str, ...]
    unknown_language_message: str = DEFAULT_UNKNOWN_LANGUAGE_MESSAGE

    @property
    def business_terms(self) -> tuple[str, ...]:
        words = f"{self.business_type} {self.statement}".lower().replace(".", " ").split()
        return tuple(w for w in dict.fromkeys(words) if len(w) >= 4 and w not in {"with", "this", "that", "looking"})

    @property
    def subject_prefix(self) -> str:
        return f"sim-{self.subject_slug}"


def _require(data: dict[str, Any], key: str, where: str) -> Any:
    if key not in data:
        raise PersonaError(f"{where}: missing '{key}'")
    return data[key]


def _parse(entry: dict[str, Any]) -> Persona:
    pid = str(_require(entry, "id", "persona"))
    where = f"persona {pid}"
    business = _require(entry, "business", where)
    behavior = _require(entry, "behavior", where)
    goal = _require(entry, "goal", where)
    patience = int(_require(entry, "patience", where))
    if patience < 3:
        raise PersonaError(f"{where}: patience must be at least 3")
    accepted = tuple(str(o) for o in _require(goal, "accepted_outcomes", where))
    if not accepted or any(o not in OUTCOMES for o in accepted):
        raise PersonaError(f"{where}: accepted_outcomes must be valid outcomes")
    kind = str(_require(goal, "kind", where))
    state = str(goal.get("state", "HANDOFF"))
    if kind not in {"handoff_tap", "reach_state"} or state not in STATES:
        raise PersonaError(f"{where}: invalid goal")
    modes = tuple(str(m) for m in _require(entry, "modes", where))
    if not modes or any(m not in MODES for m in modes):
        raise PersonaError(f"{where}: modes must be drawn from {MODES}")
    choice_style = str(_require(behavior, "choice_style", where))
    if choice_style not in {"taps", "types"}:
        raise PersonaError(f"{where}: choice_style must be taps or types")
    on_giving_up = str(_require(behavior, "on_giving_up", where))
    if on_giving_up not in {"stop", "leave"}:
        raise PersonaError(f"{where}: on_giving_up must be stop or leave")
    return Persona(
        id=pid,
        display_name=str(_require(entry, "display_name", where)),
        subject_slug=str(_require(entry, "subject_slug", where)),
        intent=str(_require(entry, "intent", where)),
        knowledge_of_waooaw=str(_require(entry, "knowledge_of_waooaw", where)),
        mood=str(_require(entry, "mood", where)),
        patience=patience,
        language=str(_require(entry, "language", where)),
        business_type=str(_require(business, "type", where)),
        city=str(_require(business, "city", where)),
        statement=str(_require(business, "statement", where)),
        goal_keyword=str(_require(business, "goal_keyword", where)),
        goal_text=str(_require(business, "goal_text", where)),
        choice_style=choice_style,
        withhold_until_asked=int(_require(behavior, "withhold_until_asked", where)),
        followup=str(_require(behavior, "followup", where)),
        taps_link=bool(_require(behavior, "taps_link", where)),
        on_giving_up=on_giving_up,
        goal=GoalSpec(kind=kind, state=state, accepted_outcomes=accepted, patience=patience),
        modes=modes,
        unknown_language_message=str(entry.get("unknown_language_message", DEFAULT_UNKNOWN_LANGUAGE_MESSAGE)),
    )


def load_personas(path: Path | None = None) -> dict[str, Persona]:
    raw = yaml.safe_load((path or PERSONAS_PATH).read_text(encoding="utf-8"))
    personas: dict[str, Persona] = {}
    for entry in raw["personas"]:
        persona = _parse(entry)
        if persona.id in personas:
            raise PersonaError(f"duplicate persona id {persona.id}")
        personas[persona.id] = persona
    return personas


def load_default_k(path: Path | None = None) -> int:
    """Default number of independent runs per seed for pass^k (``reliability.k`` of personas.yaml)."""
    raw = yaml.safe_load((path or PERSONAS_PATH).read_text(encoding="utf-8"))
    reliability = raw.get("reliability")
    value = reliability.get("k") if isinstance(reliability, dict) else None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PersonaError("reliability.k must be an integer of at least 1")
    return value


def select_personas(ids: list[str] | None, path: Path | None = None) -> list[Persona]:
    personas = load_personas(path)
    if not ids or ids == ["all"]:
        return list(personas.values())
    unknown = [i for i in ids if i not in personas]
    if unknown:
        raise PersonaError(f"unknown persona ids: {', '.join(unknown)}")
    return [personas[i] for i in ids]
