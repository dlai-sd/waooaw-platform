# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Persona-driven simulated customer: decides the next visitor message from the previous reply."""

import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Protocol

from visitor_simulation.models import Choice, Reply
from visitor_simulation.personas import Persona

CONSENT_RE = re.compile(r"reply yes|tap yes|okay if we|ok if we|do you agree|your consent|reply \"yes\"")
BUSINESS_Q_RE = re.compile(r"what (kind|type)|your business|what do you do|which city|tell me about (you|your)")
GOAL_Q_RE = re.compile(r"what would you like|your goal|what do you want|help you with")
NAME_EMAIL_RE = re.compile(r"\b(name|email)\b")
START_RE = re.compile(r"start|try|get started|trial")
OTHER_RE = re.compile(r"other professionals|other three|what else")
FALLBACK_OPTION_RE = re.compile(r"else|other|not sure|skip")
MODEL_SYSTEM = (
    "You write one short message from a fabricated visitor to a business chat. Use simple English. "
    "Reply with only the visitor's message: the text after 'SAY:' reworded in the persona's voice, "
    "keeping every fact. Never include real names, phone numbers or emails."
)
VARIANT_PREFIXES = ("", "Okay. ", "Well. ", "Right. ")


class CostCapExceeded(RuntimeError):  # noqa: N818 - name fixed by the work contract
    """A per-run cap on model calls or turns was reached; the run must stop."""


class TurnCapExceeded(CostCapExceeded):
    pass


class ModelNotConfigured(RuntimeError):  # noqa: N818 - name fixed by the work contract
    pass


class ModelClient(Protocol):
    def complete(self, system: str, messages: list[dict[str, str]]) -> str: ...


def stable_index(seed: int, label: str, size: int) -> int:
    digest = hashlib.sha256(f"{seed}:{label}".encode()).hexdigest()
    return int(digest[:8], 16) % size


class ScriptedModel:
    """Deterministic stand-in for a language model: varies the opening words of a line by seed and call count."""

    def __init__(self, seed: int = 0) -> None:
        self._seed = seed
        self.calls = 0

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        content = messages[-1]["content"] if messages else ""
        line = content.split("SAY:", 1)[1].strip() if "SAY:" in content else content.strip()
        prefix = VARIANT_PREFIXES[stable_index(self._seed, f"variant:{self.calls}", len(VARIANT_PREFIXES))]
        return f"{prefix}{line}"


class HttpModelClient:
    """Calls a sanctioned model endpoint (ADR-029). Never used by the test suite."""

    ENDPOINT_ENV = "VISITOR_SIM_MODEL_ENDPOINT"
    KEY_ENV = "VISITOR_SIM_MODEL_API_KEY"

    def __init__(self, *, timeout: float = 20.0) -> None:
        endpoint = os.environ.get(self.ENDPOINT_ENV, "")
        api_key = os.environ.get(self.KEY_ENV, "")
        if not endpoint or not api_key:
            raise ModelNotConfigured(f"set {self.ENDPOINT_ENV} and {self.KEY_ENV} to use a hosted model")
        if urllib.parse.urlsplit(endpoint).scheme != "https":
            raise ModelNotConfigured(f"{self.ENDPOINT_ENV} must be an https URL")
        self._endpoint = endpoint
        self._api_key = api_key
        self._timeout = timeout

    def __repr__(self) -> str:
        return "HttpModelClient()"

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        payload = json.dumps({"system": system, "messages": messages}).encode()
        request = urllib.request.Request(self._endpoint, data=payload, method="POST")  # noqa: S310
        request.add_header("Content-Type", "application/json")
        request.add_header("Authorization", f"Bearer {self._api_key}")
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            body = json.loads(response.read())
        return str(body.get("text", "")).strip()


class RunBudget:
    """Hard caps shared by every conversation of one run (ADR-024 cost gate)."""

    def __init__(
        self,
        *,
        max_model_calls: int = 5000,
        max_total_turns: int = 100_000,
        max_turns_per_conversation: int = 30,
    ) -> None:
        self.max_model_calls = max_model_calls
        self.max_total_turns = max_total_turns
        self.max_turns_per_conversation = max_turns_per_conversation
        self.model_calls = 0
        self.total_turns = 0
        self.conversation_turns = 0

    def start_conversation(self) -> None:
        self.conversation_turns = 0

    def charge_turn(self) -> None:
        if self.conversation_turns >= self.max_turns_per_conversation:
            raise TurnCapExceeded(f"conversation turn cap of {self.max_turns_per_conversation} reached")
        if self.total_turns >= self.max_total_turns:
            raise TurnCapExceeded(f"run turn cap of {self.max_total_turns} reached")
        self.conversation_turns += 1
        self.total_turns += 1

    def charge_model_call(self) -> None:
        if self.model_calls >= self.max_model_calls:
            raise CostCapExceeded(f"model-call cap of {self.max_model_calls} reached")
        self.model_calls += 1

    def usage(self) -> dict[str, int]:
        return {
            "modelCalls": self.model_calls,
            "totalTurns": self.total_turns,
            "maxModelCalls": self.max_model_calls,
            "maxTotalTurns": self.max_total_turns,
            "maxTurnsPerConversation": self.max_turns_per_conversation,
        }


class BudgetedModel:
    def __init__(self, model: ModelClient, budget: RunBudget) -> None:
        self._model = model
        self._budget = budget

    def complete(self, system: str, messages: list[dict[str, str]]) -> str:
        self._budget.charge_model_call()
        return self._model.complete(system, messages)


@dataclass(frozen=True)
class Action:
    kind: str  # TEXT, CHOICE, TAP or END
    text: str = ""
    choice_id: str = ""
    reference: str = ""
    reason: str = ""
    note: str = ""


def extract_reference(url: str) -> str:
    """The opaque lead reference in a LINK url: a ref/reference/lead query value, the segment before a trailing /open, else the last path segment."""
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qs(parts.query)
    for key in ("ref", "reference", "lead"):
        if query.get(key):
            return query[key][0]
    segments = [segment for segment in parts.path.split("/") if segment]
    if len(segments) >= 2 and segments[-1] == "open":
        return segments[-2]
    return segments[-1] if segments else ""


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", value.lower().replace("-", ""))


def best_option(options: tuple[Choice, ...], keyword: str, *, threshold: float = 0.7) -> Choice | None:
    """The option whose label best matches the keyword, else a neutral 'something else' option, else None."""
    key = _normalise(keyword)
    best: Choice | None = None
    best_score = 0.0
    for option in options:
        label = _normalise(option.label)
        if key and key in label:
            score = 1.0
        else:
            score = max((SequenceMatcher(None, key, word).ratio() for word in label.split()), default=0.0)
        if score > best_score:
            best, best_score = option, score
    if best is not None and best_score >= threshold:
        return best
    return next((o for o in options if FALLBACK_OPTION_RE.search(o.label.lower())), best)


class CustomerSimulator:
    """Follows one persona. Deterministic for a given persona, mode, seed and model."""

    def __init__(
        self,
        persona: Persona,
        *,
        mode: str = "normal",
        seed: int = 0,
        model: ModelClient | None = None,
        budget: RunBudget | None = None,
        inject: tuple[str, ...] = (),
    ) -> None:
        self.persona = persona
        self.mode = mode
        self.seed = seed
        self.budget = budget or RunBudget()
        self._model: ModelClient | None = BudgetedModel(model, self.budget) if model is not None else None
        self._withhold = max(persona.withhold_until_asked, 2) if mode == "overwhelmed" else persona.withhold_until_asked
        self.patience = max(8, persona.patience - 2) if mode == "overwhelmed" else persona.patience
        self._stops_when_giving_up = persona.on_giving_up == "stop" or mode == "overwhelmed"
        self._injections = [i for i in inject if i in {"media", "unknown-language", "stop-mid"}]
        self.turns = 0
        self.consented = False
        self.asked_chatgpt = False
        self.facts_given = False
        self.business_asks = 0
        self.goal_given = False
        self.followup_asked = False
        self.asked_other = False
        self.declined_details = False
        self.unclear = 0
        self.interest_attempts = 0
        self.interest_expressed = False
        self.tapped = False
        self.tap_failed = False
        self.stop_sent = False
        self.pending_start = False
        self.gave_up = False

    def next_action(self, reply: Reply) -> Action:
        if self.tapped:
            return Action("END", reason="goal_reached")
        if self.tap_failed:
            return Action("END", reason="tap_not_recorded")
        if self.gave_up:
            return Action("END", reason="gave_up")
        if reply.state == "STOPPED":
            return self._on_stopped()
        if self.persona.goal.kind == "reach_state" and reply.state == self.persona.goal.state:
            return Action("END", reason="goal_reached")
        link_to_tap = reply.link is not None and self.persona.taps_link
        if self.turns >= self.patience and not link_to_tap:
            return self._give_up()
        if self._injections and self.consented and reply.state != "CONSENT_PENDING":
            injected = self._next_injection()
            if injected is not None:
                return injected
        return self._decide(reply)

    def record_tap(self, recorded: bool) -> None:
        if recorded:
            self.tapped = True
        else:
            self.tap_failed = True

    def _on_stopped(self) -> Action:
        if self.pending_start:
            self.pending_start = False
            self.consented = False
            return self._message("TEXT", "START", note="inject:start")
        return Action("END", reason="opted_out")

    def _give_up(self) -> Action:
        self.gave_up = True
        if self._stops_when_giving_up and not self.stop_sent:
            self.stop_sent = True
            return self._message("TEXT", "STOP", note="gave_up:stop")
        return Action("END", reason="patience_exhausted")

    def _next_injection(self) -> Action | None:
        name = self._injections[0]
        if name == "stop-mid" and not self.facts_given:
            return None
        self._injections.pop(0)
        if name == "media":
            return self._message("TEXT", "[voice note]", note="inject:media")
        if name == "unknown-language":
            return self._message("TEXT", self.persona.unknown_language_message, note="inject:unknown-language")
        self.stop_sent = True
        self.pending_start = True
        return self._message("TEXT", "STOP", note="inject:stop-mid")

    def _decide(self, reply: Reply) -> Action:
        options = reply.options
        text = reply.text.lower()
        state = reply.state
        if not self.consented and (state == "CONSENT_PENDING" or CONSENT_RE.search(text)):
            return self._consent(options)
        link = reply.link
        if link is not None and self.persona.taps_link and not self.tapped:
            self.interest_expressed = True
            return Action("TAP", reference=extract_reference(link.url), note="tap")
        if options and not self.goal_given and (state == "QUALIFY" or GOAL_Q_RE.search(text)):
            return self._goal(options)
        if BUSINESS_Q_RE.search(text) or (state == "DISCOVER" and not self.facts_given):
            return self._business()
        if NAME_EMAIL_RE.search(text) and not self.declined_details and state in {"HANDOFF", "SHOW_VALUE"}:
            self.declined_details = True
            return self._message("TEXT", self._say("I would rather not share that, thanks."))
        if state in {"SHOW_VALUE", "OTHER_PROFESSIONALS", "HANDOFF"}:
            action = self._value(options)
            if action is not None:
                return action
        return self._unclear()

    def _consent(self, options: tuple[Choice, ...]) -> Action:
        if self.mode == "skeptic" and not self.asked_chatgpt:
            self.asked_chatgpt = True
            return self._message("TEXT", "Is this just ChatGPT?", note="skeptic")
        self.consented = True
        yes = next((o for o in options if o.id.upper() == "YES" or o.label.lower().startswith("yes")), None)
        if yes is not None and self.persona.choice_style == "taps":
            return self._message("CHOICE", yes.label, choice_id=yes.id, note="consent")
        return self._message("TEXT", "YES", note="consent")

    def _goal(self, options: tuple[Choice, ...]) -> Action:
        self.goal_given = True
        if self.persona.choice_style == "taps":
            chosen = best_option(options, self.persona.goal_keyword)
            if chosen is not None:
                return self._message("CHOICE", chosen.label, choice_id=chosen.id, note="goal")
        return self._message("TEXT", self._say(self.persona.goal_text), note="goal")

    def _business(self) -> Action:
        self.business_asks += 1
        if self.business_asks < self._withhold:
            return self._message("TEXT", self._say("It is a small business. Nothing special."), note="withhold")
        self.facts_given = True
        return self._message("TEXT", self._say(self.persona.statement), note="facts")

    def _value(self, options: tuple[Choice, ...]) -> Action | None:
        if not self.followup_asked:
            self.followup_asked = True
            return self._message("TEXT", self._say(self.persona.followup), note="followup")
        start = next((o for o in options if START_RE.search(o.label.lower()) or "START" in o.id.upper()), None)
        other = next((o for o in options if OTHER_RE.search(o.label.lower())), None)
        if self.persona.goal.kind == "reach_state":
            if self.asked_other:
                return None
            self.asked_other = True
            if other is not None and self.persona.choice_style == "taps":
                return self._message("CHOICE", other.label, choice_id=other.id, note="other-professionals")
            return self._message("TEXT", self._say("What else do you offer?"), note="other-professionals")
        if self.interest_attempts >= 2:
            return None
        self.interest_attempts += 1
        self.interest_expressed = True
        if start is not None and self.persona.choice_style == "taps":
            return self._message("CHOICE", start.label, choice_id=start.id, note="interest")
        return self._message("TEXT", self._say("Yes, I would like to start the trial."), note="interest")

    def _unclear(self) -> Action:
        self.unclear += 1
        if self.unclear == 1 and not self.facts_given:
            self.facts_given = True
            return self._message("TEXT", self._say(self.persona.statement), note="volunteer-facts")
        if self.unclear <= 2:
            return self._message("TEXT", self._say(self.persona.goal_text), note="volunteer-goal")
        if self.unclear == 3:
            return self._message("TEXT", self._say("What can you actually do for me?"), note="unclear")
        return self._message("TEXT", "Hello? I still do not understand what this is.", note="unclear")

    def _say(self, line: str) -> str:
        if self._model is None:
            return line
        system = f"{MODEL_SYSTEM} Persona: {self.persona.display_name}; mood: {self.persona.mood}."
        return self._model.complete(system, [{"role": "user", "content": f"SAY: {line}"}]).strip() or line

    def _message(self, kind: str, text: str, *, choice_id: str = "", note: str = "") -> Action:
        self.budget.charge_turn()
        self.turns += 1
        if note.startswith("inject:"):
            self.patience += 1  # a failure-injection detour does not use up the persona's patience
        if text.strip().upper() == "STOP":
            self.stop_sent = True
        return Action(kind, text=text, choice_id=choice_id, note=note)
