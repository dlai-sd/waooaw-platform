# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Typed views of the visitor API payloads and of a recorded simulated conversation."""

from dataclasses import dataclass, field
from typing import Any

STATES = (
    "NEW",
    "CONSENT_PENDING",
    "DISCOVER",
    "QUALIFY",
    "SHOW_VALUE",
    "OTHER_PROFESSIONALS",
    "HANDOFF",
    "STOPPED",
)
OUTCOMES = ("NONE", "LEAD", "INTENT", "FULL_SUCCESS", "OPT_OUT")


@dataclass(frozen=True)
class Choice:
    id: str
    label: str


@dataclass(frozen=True)
class Row:
    id: str
    title: str
    description: str = ""


@dataclass(frozen=True)
class Block:
    type: str
    text: str = ""
    choices: tuple[Choice, ...] = ()
    list_title: str = ""
    rows: tuple[Row, ...] = ()
    label: str = ""
    url: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Block":
        return cls(
            type=str(data.get("type", "")),
            text=str(data.get("text", "")),
            choices=tuple(Choice(str(c["id"]), str(c["label"])) for c in data.get("choices", [])),
            list_title=str(data.get("listTitle", "")),
            rows=tuple(Row(str(r["id"]), str(r["title"]), str(r.get("description", ""))) for r in data.get("rows", [])),
            label=str(data.get("label", "")),
            url=str(data.get("url", "")),
        )

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type}
        if self.text:
            out["text"] = self.text
        if self.choices:
            out["choices"] = [{"id": c.id, "label": c.label} for c in self.choices]
        if self.list_title:
            out["listTitle"] = self.list_title
        if self.rows:
            out["rows"] = [{"id": r.id, "title": r.title, "description": r.description} for r in self.rows]
        if self.label:
            out["label"] = self.label
        if self.url:
            out["url"] = self.url
        return out


@dataclass(frozen=True)
class Reply:
    state: str
    blocks: tuple[Block, ...] = ()
    content_version: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Reply":
        return cls(
            state=str(data.get("state", "")),
            blocks=tuple(Block.from_json(b) for b in data.get("blocks", [])),
            content_version=str(data.get("contentVersion", "")),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "state": self.state,
            "contentVersion": self.content_version,
            "blocks": [b.to_json() for b in self.blocks],
        }

    @property
    def text(self) -> str:
        return "\n".join(b.text for b in self.blocks if b.type == "TEXT" and b.text)

    @property
    def text_blocks(self) -> tuple[str, ...]:
        return tuple(b.text for b in self.blocks if b.type == "TEXT" and b.text)

    @property
    def options(self) -> tuple[Choice, ...]:
        """Every tappable option: CHOICES buttons first, then LIST rows."""
        out: list[Choice] = []
        for block in self.blocks:
            if block.type == "CHOICES":
                out.extend(block.choices)
            elif block.type == "LIST":
                out.extend(Choice(r.id, r.title) for r in block.rows)
        return tuple(out)

    @property
    def link(self) -> Block | None:
        return next((b for b in self.blocks if b.type == "LINK"), None)

    @property
    def is_empty(self) -> bool:
        return not self.blocks


@dataclass(frozen=True)
class Captured:
    business_domain: str | None = None
    city: str | None = None
    goal_code: str | None = None
    has_name: bool = False
    has_email: bool = False

    @classmethod
    def from_json(cls, data: dict[str, Any] | None) -> "Captured":
        data = data or {}
        return cls(
            business_domain=data.get("businessDomain"),
            city=data.get("city"),
            goal_code=data.get("goalCode"),
            has_name=bool(data.get("hasName", False)),
            has_email=bool(data.get("hasEmail", False)),
        )


@dataclass(frozen=True)
class SessionView:
    session_id: str
    channel: str
    state: str
    outcome: str
    captured: Captured
    reply: Reply | None = None
    created: bool = False


@dataclass(frozen=True)
class TurnView:
    session_id: str
    message_id: str
    cursor: str
    state: str
    outcome: str
    captured: Captured
    reply: Reply


@dataclass(frozen=True)
class GoalSpec:
    kind: str = "handoff_tap"
    state: str = "HANDOFF"
    accepted_outcomes: tuple[str, ...] = ("FULL_SUCCESS",)
    patience: int = 12


@dataclass
class TurnRecord:
    index: int
    visitor_turn: int
    visitor_kind: str
    visitor_text: str = ""
    choice_id: str = ""
    reply: Reply | None = None
    state: str = ""
    outcome: str = ""
    latency_ms: float = 0.0
    note: str = ""
    tap_recorded: bool | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "visitorTurn": self.visitor_turn,
            "visitor": {"kind": self.visitor_kind, "text": self.visitor_text, "choiceId": self.choice_id},
            "reply": self.reply.to_json() if self.reply else None,
            "state": self.state,
            "outcome": self.outcome,
            "latencyMs": round(self.latency_ms, 2),
            "note": self.note,
            "tapRecorded": self.tap_recorded,
        }


@dataclass
class Conversation:
    persona_id: str
    mode: str = "normal"
    seed: int = 0
    subject_key: str = ""
    session_id: str = ""
    injections: tuple[str, ...] = ()
    goal: GoalSpec = field(default_factory=GoalSpec)
    business_terms: tuple[str, ...] = ()
    turns: list[TurnRecord] = field(default_factory=list)
    final_state: str = "NEW"
    final_outcome: str = "NONE"
    captured: Captured = field(default_factory=Captured)
    tapped: bool = False
    interest_expressed: bool = False
    stop_sent: bool = False
    ended_reason: str = ""
    timeouts: int = 0
    resumed: bool = False
    states_visited: list[str] = field(default_factory=list)
    server_transcript_items: int = -1

    @property
    def visitor_turns(self) -> int:
        return sum(1 for t in self.turns if t.visitor_kind in {"TEXT", "CHOICE"})

    @property
    def replies(self) -> list[tuple[int, Reply]]:
        return [(t.index, t.reply) for t in self.turns if t.reply is not None]

    @property
    def first_value_turn(self) -> int | None:
        for t in self.turns:
            if t.reply is not None and t.reply.state in {"SHOW_VALUE", "OTHER_PROFESSIONALS", "HANDOFF"}:
                return t.visitor_turn
        return None

    def to_json(self) -> dict[str, Any]:
        return {
            "personaId": self.persona_id,
            "mode": self.mode,
            "seed": self.seed,
            "subjectKey": self.subject_key,
            "sessionId": self.session_id,
            "injections": list(self.injections),
            "finalState": self.final_state,
            "finalOutcome": self.final_outcome,
            "tapped": self.tapped,
            "interestExpressed": self.interest_expressed,
            "stopSent": self.stop_sent,
            "endedReason": self.ended_reason,
            "timeouts": self.timeouts,
            "resumed": self.resumed,
            "serverTranscriptItems": self.server_transcript_items,
            "turns": [t.to_json() for t in self.turns],
        }

    def transcript_signature(self) -> list[tuple[str, str, str, str]]:
        """Timing-free view of the transcript, used to prove same seed gives the same conversation."""
        return [
            (
                t.visitor_kind,
                t.visitor_text,
                t.choice_id,
                repr(t.reply.to_json()) if t.reply else "",
            )
            for t in self.turns
        ]


def build_conversation(
    turns: list[dict[str, Any]],
    *,
    persona_id: str = "fixture",
    goal: GoalSpec | None = None,
    **fields: Any,
) -> Conversation:
    """Build a Conversation from a compact fixture: the first item is the opening reply.

    Each item is ``{visitor: str | {kind, id, text}, state, blocks: [...], outcome}``.
    """
    conv = Conversation(persona_id=persona_id, goal=goal or GoalSpec(), **fields)
    visitor_turn = 0
    for index, item in enumerate(turns):
        visitor = item.get("visitor")
        kind, text, choice_id = "OPEN", "", ""
        if isinstance(visitor, str):
            kind, text = "TEXT", visitor
        elif isinstance(visitor, dict):
            kind = visitor.get("kind", "TEXT")
            text = visitor.get("text", "")
            choice_id = visitor.get("id", "")
        if kind in {"TEXT", "CHOICE"}:
            visitor_turn += 1
        reply = Reply.from_json({"state": item.get("state", "NEW"), "blocks": item.get("blocks", [])})
        conv.turns.append(
            TurnRecord(
                index=index,
                visitor_turn=visitor_turn,
                visitor_kind=kind,
                visitor_text=text,
                choice_id=choice_id,
                reply=reply,
                state=reply.state,
                outcome=item.get("outcome", "NONE"),
            )
        )
        conv.states_visited.append(reply.state)
    if conv.turns:
        conv.final_state = conv.turns[-1].state
        conv.final_outcome = conv.turns[-1].outcome
    return conv
