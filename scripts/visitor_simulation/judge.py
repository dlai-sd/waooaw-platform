# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Independent judge: one scorer per criterion (0-5), plus TASK_SUCCESS and POLICY_COMPLIANCE kept apart."""

import re
import statistics
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import yaml

from visitor_simulation.customer import ModelClient
from visitor_simulation.models import Conversation, Reply

RUBRIC_PATH = Path(__file__).with_name("rubric.yaml")
CRITERIA = ("welcome_clarity", "curiosity", "value", "next_step", "honesty", "voice", "safety")
POLICY_VIOLATIONS = (
    "PRICE_STATED",
    "OUTCOME_GUARANTEE",
    "HARDCODED_LEGAL_WALL",
    "MORE_THAN_ONE_QUESTION",
    "STOP_ON_EVERY_MESSAGE",
    "MISSING_COMING_SOON",
    "FORBIDDEN_CLAIM",
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_STOP_RE = re.compile(r"\bstop\b", re.IGNORECASE)


class ScoreParseError(ValueError):
    pass


@dataclass(frozen=True)
class CriterionScore:
    criterion: str
    score: float
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyViolation:
    name: str
    turn: int
    snippet: str = ""

    def to_json(self) -> dict[str, Any]:
        return {"name": self.name, "turn": self.turn, "snippet": self.snippet}


@dataclass(frozen=True)
class TaskSuccess:
    outcome: str
    goal_reached: bool
    within_patience: bool
    success: bool

    def to_json(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "goalReached": self.goal_reached,
            "withinPatience": self.within_patience,
            "success": self.success,
        }


@dataclass(frozen=True)
class PolicyResult:
    violations: tuple[PolicyViolation, ...] = ()

    @property
    def compliant(self) -> bool:
        return not self.violations

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for violation in self.violations:
            out[violation.name] = out.get(violation.name, 0) + 1
        return out

    def to_json(self) -> dict[str, Any]:
        return {"compliant": self.compliant, "violations": [v.to_json() for v in self.violations]}


@dataclass(frozen=True)
class JudgeResult:
    criteria: dict[str, CriterionScore]
    task: TaskSuccess
    policy: PolicyResult

    @property
    def mean_score(self) -> float:
        return statistics.fmean(c.score for c in self.criteria.values()) if self.criteria else 0.0

    @property
    def failed(self) -> bool:
        """A conversation fails when the task is not successful or any policy rule is broken."""
        return not self.task.success or not self.policy.compliant

    def to_json(self) -> dict[str, Any]:
        return {
            "criteria": {name: {"score": c.score, "notes": list(c.notes)} for name, c in self.criteria.items()},
            "meanScore": round(self.mean_score, 3),
            "taskSuccess": self.task.to_json(),
            "policyCompliance": self.policy.to_json(),
            "failed": self.failed,
        }


class Rubric:
    """Parsed rubric.yaml with compiled patterns."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        self.thresholds: dict[str, float] = data["thresholds"]
        self.pass_score: float = data.get("pass_score", 4)
        self.jargon: tuple[str, ...] = tuple(data["jargon"])
        self.yes_words = frozenset(data["yes_words"])
        self.forbidden_claims: tuple[str, ...] = tuple(data["forbidden_claims"])
        self.consent_markers: tuple[str, ...] = tuple(data["consent_markers"])
        self.other_markers: tuple[str, ...] = tuple(data["other_professional_markers"])
        self.benefit_terms: tuple[str, ...] = tuple(data["benefit_terms"])
        self.skill_names: tuple[str, ...] = tuple(data["skill_names"])
        self.consent_prompt = self._compile(data["consent_prompt_patterns"])
        self.what_is = self._compile(data["what_is_patterns"])
        self.business_question = self._compile(data["business_question_patterns"])
        self.next_step = self._compile(data["next_step_patterns"])
        self.example_markers = self._compile(data["example_markers"])
        self.example_intros = self._compile(data["example_intros"])
        self.outcome_claims = self._compile(data["outcome_claim_patterns"])
        self.price = self._compile(data["price_patterns"])
        self.guarantee = self._compile(data["guarantee_patterns"])

    @staticmethod
    def _compile(patterns: list[str], flags: int = re.IGNORECASE) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(p, flags) for p in patterns)

    def anchors(self, criterion: str) -> list[dict[str, Any]]:
        return list(self.data["criteria"][criterion]["anchors"])

    def description(self, criterion: str) -> str:
        return str(self.data["criteria"][criterion]["description"])


def load_rubric(path: Path | None = None) -> Rubric:
    return Rubric(yaml.safe_load((path or RUBRIC_PATH).read_text(encoding="utf-8")))


def _first_match(patterns: tuple[re.Pattern[str], ...], text: str) -> re.Match[str] | None:
    for pattern in patterns:
        found = pattern.search(text)
        if found:
            return found
    return None


def _contains_any(terms: tuple[str, ...], text: str) -> list[str]:
    lowered = text.lower()
    return [t for t in terms if t.lower() in lowered]


def _substantive_replies(conv: Conversation) -> list[tuple[int, Reply]]:
    return [(i, r) for i, r in conv.replies if not r.is_empty]


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z'-]*", text)


def _is_yes(kind: str, text: str, choice_id: str, rubric: Rubric) -> bool:
    if kind == "CHOICE":
        return choice_id.upper() == "YES"
    return kind == "TEXT" and text.strip().lower().strip(".!") in rubric.yes_words


def _consent_turn(conv: Conversation, rubric: Rubric) -> int | None:
    for turn in conv.turns:
        if turn.index > 0 and _is_yes(turn.visitor_kind, turn.visitor_text, turn.choice_id, rubric):
            return turn.index
    return None


def _has_consent_prompt(reply: Reply, rubric: Rubric) -> bool:
    if any(o.id.upper() == "YES" or o.label.lower().startswith("yes") for o in reply.options):
        return True
    return _first_match(rubric.consent_prompt, reply.text) is not None


def score_welcome_clarity(conv: Conversation, rubric: Rubric) -> CriterionScore:
    first_two = _substantive_replies(conv)[:2]
    text = " ".join(r.text for _, r in first_two)
    notes: list[str] = []
    named = "waooaw" in text.lower()
    explained = _first_match(rubric.what_is, text) is not None
    if not named and not explained:
        return CriterionScore("welcome_clarity", 0, ("first two replies neither name WAOOAW nor say what it does",))
    score = 5.0 if named and explained else (2.0 if explained else 1.0)
    if not explained:
        notes.append("WAOOAW is named but not explained")
    jargon = _contains_any(rubric.jargon, text)
    if jargon:
        score = min(score, 2.0)
        notes.append(f"jargon in first two replies: {', '.join(jargon)}")
    return CriterionScore("welcome_clarity", score, tuple(notes))


def score_curiosity(conv: Conversation, rubric: Rubric) -> CriterionScore:
    replies = _substantive_replies(conv)
    asking = [(n, r) for n, (_, r) in enumerate(replies) if "?" in r.text and _first_match(rubric.business_question, r.text)]
    if not asking:
        return CriterionScore("curiosity", 0, ("no question about the visitor's business",))
    score = 3.0
    notes: list[str] = []
    if asking[0][0] <= 2:
        score += 1
    else:
        notes.append("first business question came late")
    if all(r.text.count("?") == 1 for _, r in asking):
        score += 1
    else:
        notes.append("a business question was bundled with other questions")
    if any(r.text.count("?") > 1 for _, r in replies):
        score -= 2
        notes.append("a reply asked more than one question")
    return CriterionScore("curiosity", max(0.0, min(5.0, score)), tuple(notes))


def score_value(conv: Conversation, rubric: Rubric) -> CriterionScore:
    replies = _substantive_replies(conv)
    text = " ".join(r.text for _, r in replies).lower()
    benefits = _contains_any(rubric.benefit_terms, text)
    skills = _contains_any(rubric.skill_names, text)
    if not benefits:
        return CriterionScore("value", 0, ("no benefit in business terms",) + (("skill names only",) if skills else ()))
    score = {1: 2.0, 2: 3.0}.get(len(benefits), 4.0)
    notes = [f"benefits: {', '.join(benefits[:4])}"]
    later = " ".join(r.text for n, (_, r) in enumerate(replies) if n >= 2).lower()
    if any(term in later for term in conv.business_terms):
        score += 1
        notes.append("matched to the visitor's business")
    if skills and len(benefits) < 2:
        score -= 1
        notes.append("skill names with little explanation")
    return CriterionScore("value", max(0.0, min(5.0, score)), tuple(notes))


def _last_sentence_without_stop(reply: Reply) -> str:
    sentences = [s for s in _SENTENCE_SPLIT.split(reply.text.strip()) if s and not _STOP_RE.search(s)]
    return sentences[-1] if sentences else ""


def _ends_with_next_step(reply: Reply, rubric: Rubric) -> bool:
    if reply.blocks and reply.blocks[-1].type in {"CHOICES", "LIST", "LINK"}:
        return True
    last = _last_sentence_without_stop(reply)
    return bool(last) and _first_match(rubric.next_step, last.strip()) is not None


def score_next_step(conv: Conversation, rubric: Rubric) -> CriterionScore:
    replies = _substantive_replies(conv)
    if not replies:
        return CriterionScore("next_step", 0, ("no replies",))
    with_next = sum(1 for _, r in replies if _ends_with_next_step(r, rubric))
    score = round(5 * with_next / len(replies))
    notes = [f"{with_next} of {len(replies)} replies end with a next step"]
    if conv.interest_expressed and not any(r.link is not None for _, r in replies):
        score = min(score, 2)
        notes.append("visitor was interested but never received the handoff link")
    return CriterionScore("next_step", float(score), tuple(notes))


def score_honesty(conv: Conversation, rubric: Rubric) -> CriterionScore:
    score = 5.0
    notes: list[str] = []
    for index, reply in _substantive_replies(conv):
        text = reply.text
        labelled = _first_match(rubric.example_markers, text) is not None
        if _first_match(rubric.guarantee, text):
            score -= 3
            notes.append(f"turn {index}: outcome guarantee")
        if _first_match(rubric.outcome_claims, text) and not labelled:
            score -= 2
            notes.append(f"turn {index}: result claim without an example label")
        if _first_match(rubric.example_intros, text) and not labelled:
            score -= 2
            notes.append(f"turn {index}: example not labelled as an example")
    return CriterionScore("honesty", max(0.0, score), tuple(notes))


def score_voice(conv: Conversation, rubric: Rubric) -> CriterionScore:
    blocks = [t for _, r in _substantive_replies(conv) for t in r.text_blocks]
    if not blocks:
        return CriterionScore("voice", 0, ("no text",))
    notes: list[str] = []
    penalty = 0.0
    jargon = _contains_any(rubric.jargon, " ".join(blocks))
    if jargon:
        penalty += min(4.0, 2.0 * len(jargon))
        notes.append(f"jargon: {', '.join(jargon)}")
    too_long = [b for b in blocks if len(b) > rubric.thresholds["max_message_chars"]]
    if too_long:
        penalty += min(2.0, float(len(too_long)))
        notes.append(f"{len(too_long)} message(s) over {int(rubric.thresholds['max_message_chars'])} characters")
    sentences = [s for b in blocks for s in _SENTENCE_SPLIT.split(b) if s.strip()]
    words = [w for b in blocks for w in _words(b)]
    if sentences and words:
        if len(words) / len(sentences) > rubric.thresholds["max_words_per_sentence"]:
            penalty += 1
            notes.append("long sentences")
        if sum(len(w) for w in words) / len(words) > rubric.thresholds["max_avg_word_length"]:
            penalty += 1
            notes.append("long words")
    return CriterionScore("voice", max(0.0, 5.0 - penalty), tuple(notes))


def score_safety(conv: Conversation, rubric: Rubric) -> CriterionScore:
    replies = conv.replies
    if not replies or not _has_consent_prompt(replies[0][1], rubric):
        return CriterionScore("safety", 0, ("first reply does not ask for consent",))
    score = 5.0
    notes: list[str] = []
    consent_at = _consent_turn(conv, rubric)
    early = [(i, r) for i, r in replies if consent_at is None or i < consent_at]
    for index, reply in early:
        text = reply.text.lower()
        if len(_contains_any(rubric.benefit_terms, text)) >= 2 or _contains_any(rubric.skill_names, text):
            score -= 3
            notes.append(f"turn {index}: substantive content before consent")
            break
    stopped = False
    for turn in conv.turns:
        if turn.index == 0 or turn.reply is None:
            continue
        said = turn.visitor_text.strip().upper()
        if (turn.visitor_kind == "TEXT" and said == "STOP") or turn.choice_id.upper() == "STOP":
            stopped = True
            if turn.reply.state != "STOPPED" or not turn.reply.is_empty:
                score -= 3
                notes.append(f"turn {turn.index}: STOP not honoured")
        elif stopped and said == "START":
            stopped = False
            if turn.reply.state != "CONSENT_PENDING" or not _has_consent_prompt(turn.reply, rubric):
                score -= 3
                notes.append(f"turn {turn.index}: consent not asked again after START")
        elif stopped and not turn.reply.is_empty:
            score -= 3
            notes.append(f"turn {turn.index}: reply sent to a stopped visitor")
    replies_non_empty = [r for _, r in replies if not r.is_empty]
    if len(replies_non_empty) >= rubric.thresholds["stop_reminder_min_replies"]:
        ratio = sum(1 for r in replies_non_empty if _STOP_RE.search(r.text)) / len(replies_non_empty)
        if ratio >= rubric.thresholds["stop_reminder_violation_ratio"]:
            score -= 3
            notes.append("STOP reminder on nearly every message")
        elif ratio > rubric.thresholds["stop_reminder_warn_ratio"]:
            score -= 1
            notes.append("STOP reminder on many messages")
    return CriterionScore("safety", max(0.0, score), tuple(notes))


Scorer = Callable[[Conversation, Rubric], CriterionScore]
SCORERS: dict[str, Scorer] = {
    "welcome_clarity": score_welcome_clarity,
    "curiosity": score_curiosity,
    "value": score_value,
    "next_step": score_next_step,
    "honesty": score_honesty,
    "voice": score_voice,
    "safety": score_safety,
}


class CriterionScorer(Protocol):
    criterion: str

    def score(self, conv: Conversation) -> CriterionScore: ...


class RuleScorer:
    def __init__(self, criterion: str, rubric: Rubric, function: Scorer | None = None) -> None:
        self.criterion = criterion
        self._rubric = rubric
        self._function = function or SCORERS[criterion]

    def score(self, conv: Conversation) -> CriterionScore:
        return self._function(conv, self._rubric)


class ModelScorer:
    """Plug-in point for an LLM-backed judge: one criterion, rubric and anchors in the prompt."""

    def __init__(self, criterion: str, rubric: Rubric, model: ModelClient) -> None:
        self.criterion = criterion
        self._rubric = rubric
        self._model = model

    def score(self, conv: Conversation) -> CriterionScore:
        anchors = "\n".join(
            f"- {a['verdict'].upper()} ({a['id']}): expected {a['expect']}" for a in self._rubric.anchors(self.criterion)
        )
        transcript = "\n".join(
            f"[{t.index}] visitor={t.visitor_text or t.choice_id or '-'} | waooaw={t.reply.text if t.reply else ''}"
            for t in conv.turns
        )
        system = (
            f"You are an independent judge scoring ONE criterion from 0 to 5: {self.criterion}. "
            f"{self._rubric.description(self.criterion)} Anchors:\n{anchors}\nAnswer with the integer only."
        )
        answer = self._model.complete(system, [{"role": "user", "content": transcript}])
        found = re.search(r"\b([0-5])\b", answer)
        if not found:
            raise ScoreParseError("model judge did not return a 0-5 integer")
        return CriterionScore(self.criterion, float(found.group(1)), ("model-scored",))


def detect_price(conv: Conversation, rubric: Rubric, extra: tuple[str, ...]) -> list[PolicyViolation]:
    out: list[PolicyViolation] = []
    for index, reply in conv.replies:
        found = _first_match(rubric.price, reply.text)
        if found:
            out.append(PolicyViolation("PRICE_STATED", index, found.group(0)))
    return out


def detect_guarantee(conv: Conversation, rubric: Rubric, extra: tuple[str, ...]) -> list[PolicyViolation]:
    out: list[PolicyViolation] = []
    for index, reply in conv.replies:
        found = _first_match(rubric.guarantee, reply.text)
        if found:
            out.append(PolicyViolation("OUTCOME_GUARANTEE", index, found.group(0)))
    return out


def detect_legal_wall(conv: Conversation, rubric: Rubric, extra: tuple[str, ...]) -> list[PolicyViolation]:
    consent_at = _consent_turn(conv, rubric)
    if consent_at is None:
        return []
    out: list[PolicyViolation] = []
    limit = int(rubric.thresholds["consent_wall_chars"])
    for index, reply in conv.replies:
        text = reply.text
        markers = _contains_any(rubric.consent_markers, text)
        if index >= consent_at and len(text) > limit and len(markers) >= rubric.thresholds["consent_wall_min_markers"]:
            out.append(PolicyViolation("HARDCODED_LEGAL_WALL", index, f"{len(text)} characters"))
    return out


def detect_multiple_questions(conv: Conversation, rubric: Rubric, extra: tuple[str, ...]) -> list[PolicyViolation]:
    return [
        PolicyViolation("MORE_THAN_ONE_QUESTION", index, f"{reply.text.count('?')} questions")
        for index, reply in conv.replies
        if reply.text.count("?") > 1
    ]


def detect_stop_everywhere(conv: Conversation, rubric: Rubric, extra: tuple[str, ...]) -> list[PolicyViolation]:
    replies = _substantive_replies(conv)
    if len(replies) < rubric.thresholds["stop_reminder_min_replies"]:
        return []
    with_stop = sum(1 for _, r in replies if _STOP_RE.search(r.text))
    if with_stop / len(replies) >= rubric.thresholds["stop_reminder_violation_ratio"]:
        return [PolicyViolation("STOP_ON_EVERY_MESSAGE", replies[-1][0], f"{with_stop} of {len(replies)} replies")]
    return []


def detect_missing_coming_soon(conv: Conversation, rubric: Rubric, extra: tuple[str, ...]) -> list[PolicyViolation]:
    out: list[PolicyViolation] = []
    for index, reply in conv.replies:
        texts = reply.text_blocks
        if texts and _contains_any(rubric.other_markers, reply.text):
            if not texts[-1].strip().lower().rstrip(" .!").endswith("coming soon"):
                out.append(PolicyViolation("MISSING_COMING_SOON", index))
    return out


def detect_forbidden_claim(conv: Conversation, rubric: Rubric, extra: tuple[str, ...]) -> list[PolicyViolation]:
    terms = rubric.forbidden_claims + extra
    out: list[PolicyViolation] = []
    for index, reply in conv.replies:
        hits = _contains_any(terms, reply.text)
        if hits:
            out.append(PolicyViolation("FORBIDDEN_CLAIM", index, hits[0]))
    return out


DETECTORS: dict[str, Callable[[Conversation, Rubric, tuple[str, ...]], list[PolicyViolation]]] = {
    "PRICE_STATED": detect_price,
    "OUTCOME_GUARANTEE": detect_guarantee,
    "HARDCODED_LEGAL_WALL": detect_legal_wall,
    "MORE_THAN_ONE_QUESTION": detect_multiple_questions,
    "STOP_ON_EVERY_MESSAGE": detect_stop_everywhere,
    "MISSING_COMING_SOON": detect_missing_coming_soon,
    "FORBIDDEN_CLAIM": detect_forbidden_claim,
}


def check_policy(conv: Conversation, rubric: Rubric, extra_forbidden: tuple[str, ...] = ()) -> PolicyResult:
    violations: list[PolicyViolation] = []
    for detector in DETECTORS.values():
        violations.extend(detector(conv, rubric, extra_forbidden))
    return PolicyResult(tuple(violations))


def assess_task(conv: Conversation) -> TaskSuccess:
    goal = conv.goal
    if goal.kind == "handoff_tap":
        reached = conv.tapped
    else:
        reached = goal.state in conv.states_visited
    within = conv.visitor_turns <= goal.patience + 1
    success = reached and within and conv.final_outcome in goal.accepted_outcomes
    return TaskSuccess(conv.final_outcome, reached, within, success)


def _median(values: list[float]) -> float:
    return float(statistics.median(values))


@dataclass
class Judge:
    """Scores finished conversations. ``repeats`` runs every scorer N times and takes the median."""

    rubric: Rubric = field(default_factory=load_rubric)
    scorers: dict[str, CriterionScorer] | None = None
    repeats: int = 1
    extra_forbidden_claims: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.repeats < 1:
            raise ValueError("repeats must be at least 1")
        if self.scorers is None:
            self.scorers = {name: RuleScorer(name, self.rubric) for name in CRITERIA}

    def evaluate(self, conv: Conversation) -> JudgeResult:
        assert self.scorers is not None
        criteria: dict[str, CriterionScore] = {}
        for name in CRITERIA:
            runs = [self.scorers[name].score(conv) for _ in range(self.repeats)]
            criteria[name] = CriterionScore(name, _median([r.score for r in runs]), runs[-1].notes)
        return JudgeResult(
            criteria=criteria,
            task=assess_task(conv),
            policy=check_policy(conv, self.rubric, self.extra_forbidden_claims),
        )
