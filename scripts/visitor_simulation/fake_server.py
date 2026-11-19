# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""In-process fake of the visitor API (OpenAPI contract) with a weak ``legacy`` and a ``good`` behaviour.

Used by the tests and for local dry runs of the harness. It never leaves the loopback interface.
"""

import hashlib
import hmac
import json
import re
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from visitor_simulation.client import sign_request

SESSIONS = "/api/v1/visitor/sessions"
TAP_PREFIX = "/api/v1/visitor/handoffs/"
SIGNATURE_WINDOW_SECONDS = 300
PROBLEM_TYPE = "https://api.waooaw.com/problems/visitor"
NAMESPACE = uuid.UUID("0b5fd0a2-6c1a-4c6c-8f5e-4a2f2c0e1a11")

LEGACY_OPEN = (
    "WAOOAW Demo: this is a demo conversation. By replying YES you agree that your number is used for this demo only. "
    "Reply YES to continue. If you are using WhatsApp, reply STOP to stop messages."
)
LEGACY_CATALOGUE = (
    "Welcome to WAOOAW Demo. You can browse professionals and ask me to narrow the public catalogue. This discovery "
    "conversation does not create a customer account, membership, trial, or hiring relationship. Digital Marketing "
    "Professional (catalogue preview, not an employed professional): Published skills: Customer Profiling (listed for "
    "trial); Market Research and Maturity Scoring (listed for trial); Content Strategy and Calendar (listed for trial). "
    "Trial or hire starts on the web portal and may require registration and verification. If you are using WhatsApp, "
    "reply STOP to stop messages."
)

OPEN_TEXT = (
    "Hi, I am the WAOOAW assistant. WAOOAW gives small businesses digital professionals who do everyday marketing "
    "work for them. To chat, I need your OK. You can reply STOP at any time. Is it okay if we talk for a few minutes?"
)
MEDIA_REDIRECT = "I cannot play voice notes or pictures yet. Could you type your message instead?"
LANGUAGE_REDIRECT = "I can only chat in simple English for now. Could you write that in English?"
ASK_BUSINESS = "Great, thank you. What kind of business do you run, and in which city?"
REPHRASE = "Sorry, I did not catch that. In a few words, what does your business do, and where is it?"
ASK_CITY = "Thanks. Which city is it in?"
ASK_TYPE = "Thanks. What kind of business is it?"
OTHER_PROFESSIONALS_TEXT = (
    "We are building three more professionals. A Private Tutor Professional will help families with learning. "
    "An Agricultural Advisor will help farmers with crop questions. A Trading Professional will help people learn "
    "about the market. All three are coming soon."
)

GOAL_ROWS = (
    ("BOOKINGS", "More bookings"),
    ("ENQUIRIES", "More enquiries"),
    ("SIGNUPS", "More sign-ups"),
    ("NEW_CLIENTS", "More new clients"),
    ("FOUND_ONLINE", "Be found online"),
    ("OTHER", "Something else"),
)
GOAL_KEYWORDS = (
    ("booking", "BOOKINGS"),
    ("enquir", "ENQUIRIES"),
    ("inquir", "ENQUIRIES"),
    ("sign-up", "SIGNUPS"),
    ("signup", "SIGNUPS"),
    ("member", "SIGNUPS"),
    ("client", "NEW_CLIENTS"),
    ("found", "FOUND_ONLINE"),
    ("online", "FOUND_ONLINE"),
)
GOAL_PHRASES = {
    "BOOKINGS": "more bookings",
    "ENQUIRIES": "more enquiries",
    "SIGNUPS": "more sign-ups",
    "NEW_CLIENTS": "more new clients",
    "FOUND_ONLINE": "being found online",
}
GOAL_ACTIONS = {
    "BOOKINGS": "book a visit",
    "ENQUIRIES": "send an enquiry",
    "SIGNUPS": "join",
    "NEW_CLIENTS": "ask for a call",
}
DOMAIN_KEYWORDS = (
    ("dental", "DENTAL_CLINIC"),
    ("dentist", "DENTAL_CLINIC"),
    ("clinic", "HEALTHCARE"),
    ("beauty", "BEAUTY"),
    ("salon", "BEAUTY"),
    ("makeup", "BEAUTY"),
    ("fitness", "FITNESS"),
    ("gym", "FITNESS"),
    ("agency", "MARKETING_AGENCY"),
    ("marketing", "MARKETING_AGENCY"),
)
DOMAIN_LABELS = {
    "DENTAL_CLINIC": "dental clinic",
    "HEALTHCARE": "clinic",
    "BEAUTY": "beauty business",
    "FITNESS": "fitness studio",
    "MARKETING_AGENCY": "agency",
}
KNOWN_CITIES = ("Pune", "Mumbai", "Bangalore", "Nashik", "Chennai", "Hyderabad", "Delhi")
CITY_RE = re.compile(r"\b(?:in|from|at|near)\s+([A-Z][a-zA-Z]+)")
YES_RE = re.compile(r"^\s*(yes|y|yeah|yep|ok|okay|sure)\b", re.IGNORECASE)
READY_RE = re.compile(r"\b(start|try|trial|ready|interested|sign up|get started|go ahead)\b", re.IGNORECASE)
FIT_RE = re.compile(r"farm|tomato|tutor|share market|invest|stock|\btrad(e|ing|er)\b", re.IGNORECASE)
OTHER_RE = re.compile(r"other professional|what else|other three", re.IGNORECASE)
PRICE_QUESTION_RE = re.compile(r"how much|price|cost|fee|pay", re.IGNORECASE)
CHATGPT_RE = re.compile(r"chatgpt|chat gpt|\bbot\b|different", re.IGNORECASE)
MEDIA_RE = re.compile(r"^\[(voice note|image|video|audio|location|sticker)[^\]]*\]$", re.IGNORECASE)
HINGLISH_TOKENS = frozenset({"mujhe", "apna", "kya", "aap", "hai", "nahi", "karo", "karoge", "madad", "chahiye", "hain"})


def _text(value: str) -> dict[str, Any]:
    return {"type": "TEXT", "text": value}


def _choices(*pairs: tuple[str, str]) -> dict[str, Any]:
    return {"type": "CHOICES", "choices": [{"id": i, "label": label} for i, label in pairs]}


def _reply(state: str, blocks: list[dict[str, Any]], version: str) -> dict[str, Any]:
    return {"schemaVersion": "1.0", "state": state, "contentVersion": version, "blocks": blocks}


@dataclass
class _Session:
    session_id: str
    subject_key: str
    state: str = "NEW"
    resume_state: str = "DISCOVER"
    domain: str | None = None
    business_text: str | None = None
    city: str | None = None
    goal: str | None = None
    tapped: bool = False
    handoff_issued: bool = False
    reference: str = ""
    misses: int = 0
    notice_resends: int = 0
    sequence: int = 0
    transcript: list[dict[str, Any]] = field(default_factory=list)
    idempotency: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)
    last_reply: dict[str, Any] = field(default_factory=dict)

    def outcome(self, legacy: bool) -> str:
        if self.state == "STOPPED":
            return "OPT_OUT"
        if legacy:
            return "NONE"
        complete = bool(self.domain and self.city and self.goal)
        if complete and self.tapped:
            return "FULL_SUCCESS"
        if complete:
            return "LEAD"
        return "INTENT" if self.tapped else "NONE"

    def captured(self) -> dict[str, Any]:
        return {
            "businessDomain": self.domain,
            "city": self.city,
            "goalCode": self.goal,
            "hasName": False,
            "hasEmail": False,
        }


class _LegacyEngine:
    """Today's weak behaviour: one catalogue text, nothing captured, no link."""

    version = "fake-legacy-0"
    is_legacy = True

    def consent_blocks(self, session: _Session) -> list[dict[str, Any]]:
        return [_text(LEGACY_OPEN)]

    def turn(self, session: _Session, kind: str, text: str, choice_id: str) -> list[dict[str, Any]]:
        if session.state == "CONSENT_PENDING":
            if choice_id.upper() == "YES" or YES_RE.match(text):
                session.state = "DISCOVER"
                return [_text(LEGACY_CATALOGUE)]
            return self.consent_blocks(session)
        return [_text(LEGACY_CATALOGUE)]


class _GoodEngine:
    version = "fake-good-1"
    is_legacy = False

    def consent_blocks(self, session: _Session) -> list[dict[str, Any]]:
        return [_text(OPEN_TEXT), _choices(("YES", "Yes, let's talk"), ("STOP", "Stop"))]

    def turn(self, session: _Session, kind: str, text: str, choice_id: str) -> list[dict[str, Any]]:
        if kind == "TEXT" and MEDIA_RE.match(text.strip()):
            return [_text(MEDIA_REDIRECT)]
        if kind == "TEXT" and len(HINGLISH_TOKENS & set(re.findall(r"[a-z]+", text.lower()))) >= 2:
            return [_text(LANGUAGE_REDIRECT)]
        handler = {
            "CONSENT_PENDING": self._consent,
            "DISCOVER": self._discover,
            "QUALIFY": self._qualify,
            "SHOW_VALUE": self._show_value,
            "OTHER_PROFESSIONALS": self._other_professionals,
            "HANDOFF": self._handoff,
        }[session.state]
        return handler(session, text, choice_id)

    def render(self, session: _Session) -> list[dict[str, Any]]:
        state = session.state
        if state == "CONSENT_PENDING":
            return self.consent_blocks(session)
        if state == "DISCOVER":
            return [_text(ASK_BUSINESS)]
        if state == "QUALIFY":
            where = f" in {session.city}" if session.city else ""
            return [
                _text(f"Thanks. A {self._label(session)}{where}. What would you like most?"),
                {
                    "type": "LIST",
                    "listTitle": "Your goal",
                    "rows": [{"id": i, "title": t} for i, t in GOAL_ROWS],
                },
            ]
        if state == "SHOW_VALUE":
            return self._value_blocks(session)
        if state == "OTHER_PROFESSIONALS":
            return [_text(OTHER_PROFESSIONALS_TEXT), _choices(("START_TRIAL", "Get started"))]
        return self._handoff_blocks(session, first=False)

    @staticmethod
    def _label(session: _Session) -> str:
        return DOMAIN_LABELS.get(session.domain or "", "business")

    def _consent(self, session: _Session, text: str, choice_id: str) -> list[dict[str, Any]]:
        if choice_id.upper() == "YES" or YES_RE.match(text):
            session.state = session.resume_state if session.resume_state != "CONSENT_PENDING" else "DISCOVER"
            return self.render(session)
        session.notice_resends += 1
        return self.consent_blocks(session) if session.notice_resends <= 1 else []

    def _discover(self, session: _Session, text: str, choice_id: str) -> list[dict[str, Any]]:
        lowered = text.lower()
        domain = next((code for key, code in DOMAIN_KEYWORDS if key in lowered), None)
        city = next((c for c in KNOWN_CITIES if c.lower() in lowered), None)
        if city is None and (found := CITY_RE.search(text)):
            city = found.group(1)
        session.domain = session.domain or domain
        session.city = session.city or city
        if session.domain is None and session.city and len(text.split()) >= 4:
            session.domain, session.business_text = "OTHER", text[:120]
        if not (session.domain and session.city):
            session.misses += 1
            if session.misses >= 2 and session.domain is None:
                session.domain, session.business_text = "OTHER", text[:120]
        if (session.domain and session.city) or session.misses >= 3:
            session.state = "QUALIFY"
            return self.render(session)
        if session.domain:
            return [_text(ASK_CITY)]
        if session.city:
            return [_text(ASK_TYPE)]
        return [_text(REPHRASE)]

    def _qualify(self, session: _Session, text: str, choice_id: str) -> list[dict[str, Any]]:
        lowered = text.lower()
        if choice_id in {code for code, _ in GOAL_ROWS}:
            session.goal = choice_id
        elif any(word in lowered for word in ("skip", "not sure", "later")):
            session.goal = None
        else:
            session.goal = next((code for key, code in GOAL_KEYWORDS if key in lowered), "OTHER")
        session.state = "SHOW_VALUE"
        return self.render(session)

    def _value_blocks(self, session: _Session) -> list[dict[str, Any]]:
        label = self._label(session)
        phrase = GOAL_PHRASES.get(session.goal or "", "more customers")
        action = GOAL_ACTIONS.get(session.goal or "", "get in touch")
        place = session.city or "your area"
        return [
            _text(
                f"Here is how I can help. Our Digital Marketing Professional is a digital helper for your {label}. "
                f"It plans simple posts and writes them in plain words. It reaches people in {place} who may become "
                f"customers. The aim is {phrase}. You stay in charge and approve everything first."
            ),
            _text(
                f"Example, not a real result: for a {label}, it could draft a weekly post and a short note that "
                f"invites people to {action}."
            ),
            _text("Would you like to see how it could work for you?"),
            _choices(
                ("START_TRIAL", "Get started"),
                ("OTHER_PROFESSIONALS", "Other professionals"),
                ("ASK", "Ask a question"),
            ),
        ]

    def _show_value(self, session: _Session, text: str, choice_id: str) -> list[dict[str, Any]]:
        if choice_id == "START_TRIAL" or (choice_id == "" and READY_RE.search(text)):
            return self._to_handoff(session)
        if choice_id == "OTHER_PROFESSIONALS" or OTHER_RE.search(text) or FIT_RE.search(text):
            session.state = "OTHER_PROFESSIONALS"
            return self.render(session)
        if choice_id == "ASK":
            return [_text("Sure. What would you like to know?")]
        phrase = GOAL_PHRASES.get(session.goal or "", "more customers")
        if PRICE_QUESTION_RE.search(text):
            answer = "Prices are shown on our website when you start. I cannot quote them here. Shall we set up your trial?"
        elif CHATGPT_RE.search(text):
            answer = (
                "WAOOAW professionals are built for one job each. They learn about your business and work with you "
                "every day. Would you like to see it for yours?"
            )
        else:
            answer = f"Good question. In short, it helps you get found and win {phrase}. You stay in control. Shall we begin?"
        return [_text(answer), _choices(("START_TRIAL", "Get started"), ("OTHER_PROFESSIONALS", "Other professionals"))]

    def _other_professionals(self, session: _Session, text: str, choice_id: str) -> list[dict[str, Any]]:
        if choice_id == "START_TRIAL" or READY_RE.search(text):
            return self._to_handoff(session)
        return self.render(session)

    def _handoff(self, session: _Session, text: str, choice_id: str) -> list[dict[str, Any]]:
        if choice_id == "OTHER_PROFESSIONALS" or OTHER_RE.search(text):
            session.state = "OTHER_PROFESSIONALS"
            return self.render(session)
        return self._handoff_blocks(session, first=False)

    def _to_handoff(self, session: _Session) -> list[dict[str, Any]]:
        session.state = "HANDOFF"
        session.handoff_issued = True
        return self._handoff_blocks(session, first=True)

    @staticmethod
    def _handoff_blocks(session: _Session, *, first: bool) -> list[dict[str, Any]]:
        link = {"type": "LINK", "label": "Start your trial", "url": f"https://portal.fake.invalid/trial?ref={session.reference}"}
        if not first:
            return [_text("Your link is ready. Tap it whenever you like."), link]
        return [
            _text(
                "Great. Tap the button to open your trial page on our website. Your business details are saved for "
                "you, so you will not type them again."
            ),
            _text(
                "If you like, share your name and email here. It is optional. The team uses them only to help with your trial."
            ),
            link,
        ]


class FakeVisitorServer:
    """Loopback HTTP server implementing the visitor OpenAPI contract."""

    def __init__(
        self,
        behaviour: str = "good",
        secret: str = "fake-simulator-secret",  # noqa: S107
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if behaviour not in {"good", "legacy"}:
            raise ValueError("behaviour must be 'good' or 'legacy'")
        self.behaviour = behaviour
        self._engine: _LegacyEngine | _GoodEngine = _LegacyEngine() if behaviour == "legacy" else _GoodEngine()
        self._secret = secret
        self._clock = clock
        self._lock = threading.Lock()
        self._sessions: dict[str, _Session] = {}
        self._by_subject: dict[str, str] = {}
        self._references: dict[str, str] = {}
        self._failures: deque[tuple[int, int]] = deque()
        self.response_delay = 0.0
        self.requests: list[tuple[str, str, int]] = []
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        assert self._httpd is not None, "server not started"
        return f"http://127.0.0.1:{self._httpd.server_address[1]}"

    def queue_failure(self, status: int, retry_after: int = 1) -> None:
        """The next message POST fails with this status (429 or 503) before any processing."""
        self._failures.append((status, retry_after))

    def start(self) -> "FakeVisitorServer":
        app = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                status, headers, payload = app.dispatch(self.command, self.path, dict(self.headers.items()), body)
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            do_GET = _serve  # noqa: N815
            do_POST = _serve  # noqa: N815

            def log_message(self, format: str, *args: Any) -> None:
                return

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._httpd.daemon_threads = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> "FakeVisitorServer":
        return self.start()

    def __exit__(self, *exc_info: object) -> None:
        self.stop()

    def dispatch(self, method: str, raw_path: str, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], bytes]:
        path = raw_path.split("?", 1)[0]
        query = raw_path.split("?", 1)[1] if "?" in raw_path else ""
        if self.response_delay:
            time.sleep(self.response_delay)
        with self._lock:
            status, extra, payload = self._route(method, path, query, {k.lower(): v for k, v in headers.items()}, body)
        self.requests.append((method, path, status))
        out_headers = {"Content-Type": "application/problem+json" if status >= 400 else "application/json", **extra}
        return status, out_headers, json.dumps(payload).encode()

    def _problem(
        self, status: int, code: str, title: str, retry_after: int | None = None
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        payload: dict[str, Any] = {
            "type": PROBLEM_TYPE,
            "title": title,
            "status": status,
            "code": code,
            "correlationId": str(uuid.uuid4()),
        }
        extra: dict[str, str] = {}
        if retry_after is not None:
            payload["retryAfterSeconds"] = retry_after
            extra["Retry-After"] = str(retry_after)
        return status, extra, payload

    def _authenticated(self, method: str, path: str, headers: dict[str, str], body: bytes) -> bool:
        timestamp = headers.get("x-visitor-timestamp", "")
        signature = headers.get("x-visitor-signature", "")
        if not timestamp.isdigit() or not signature:
            return False
        if abs(self._clock() - int(timestamp)) > SIGNATURE_WINDOW_SECONDS:
            return False
        expected = sign_request(self._secret, timestamp, method, path, body)
        return hmac.compare_digest(expected, signature)

    def _route(
        self, method: str, path: str, query: str, headers: dict[str, str], body: bytes
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        if path.startswith(TAP_PREFIX) and path.endswith("/tap") and method == "POST":
            return self._tap(path[len(TAP_PREFIX) : -len("/tap")])
        if not self._authenticated(method, path, headers, body):
            return self._problem(401, "VISITOR_SESSION_REQUIRED", "Visitor credential is missing or invalid")
        if path == SESSIONS and method == "POST":
            return self._open(body)
        if path.startswith(SESSIONS + "/"):
            rest = path[len(SESSIONS) + 1 :].split("/")
            session = self._sessions.get(rest[0])
            if session is None:
                return self._problem(404, "VISITOR_SESSION_NOT_FOUND", "Session not found")
            if len(rest) == 1 and method == "GET":
                return 200, {}, self._session_json(session)
            if len(rest) == 2 and rest[1] == "messages":
                if method == "GET":
                    return self._list(session, query)
                if method == "POST":
                    return self._send(session, headers, body)
        return self._problem(404, "VISITOR_SESSION_NOT_FOUND", "Not found")

    def _json_body(self, body: bytes) -> dict[str, Any] | None:
        try:
            parsed = json.loads(body or b"null")
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _invalid(self) -> tuple[int, dict[str, str], dict[str, Any]]:
        return self._problem(400, "VISITOR_REQUEST_INVALID", "Request is malformed or unsupported")

    def _open(self, body: bytes) -> tuple[int, dict[str, str], dict[str, Any]]:
        data = self._json_body(body)
        if data is None or not set(data) <= {"schemaVersion", "channel", "subjectKey", "resumeToken"}:
            return self._invalid()
        subject = data.get("subjectKey")
        if data.get("schemaVersion") != "1.0" or data.get("channel") != "SIMULATION":
            return self._invalid()
        if not isinstance(subject, str) or not 8 <= len(subject) <= 64:
            return self._invalid()
        existing = self._by_subject.get(subject)
        if existing:
            session = self._sessions[existing]
            payload = self._session_json(session)
            payload["reply"] = session.last_reply
            return 200, {}, payload
        session_id = str(uuid.uuid5(NAMESPACE, subject))
        session = _Session(session_id=session_id, subject_key=subject)
        session.reference = "h1." + hashlib.sha256(f"{session_id}:{self._secret}".encode()).hexdigest()[:32]
        session.state = "CONSENT_PENDING"
        session.last_reply = _reply("CONSENT_PENDING", self._engine.consent_blocks(session), self._engine.version)
        self._sessions[session_id] = session
        self._by_subject[subject] = session_id
        self._references[session.reference] = session_id
        self._record(session, "WAOOAW", reply=session.last_reply)
        payload = self._session_json(session)
        payload["reply"] = session.last_reply
        return 201, {}, payload

    def _session_json(self, session: _Session) -> dict[str, Any]:
        return {
            "schemaVersion": "1.0",
            "sessionId": session.session_id,
            "channel": "SIMULATION",
            "state": session.state,
            "outcome": session.outcome(self._engine.is_legacy),
            "captured": session.captured(),
        }

    @staticmethod
    def _record(
        session: _Session, role: str, *, content: dict[str, Any] | None = None, reply: dict[str, Any] | None = None
    ) -> None:
        session.sequence += 1
        item: dict[str, Any] = {"sequence": session.sequence, "role": role, "at": datetime.now(timezone.utc).isoformat()}
        if content is not None:
            item["content"] = content
        if reply is not None:
            item["reply"] = reply
        session.transcript.append(item)

    def _list(self, session: _Session, query: str) -> tuple[int, dict[str, str], dict[str, Any]]:
        params = dict(part.split("=", 1) for part in query.split("&") if "=" in part)
        try:
            after = int(params.get("cursor", "0"))
            limit = int(params.get("limit", "40"))
        except ValueError:
            return self._invalid()
        if not 1 <= limit <= 100 or after < 0:
            return self._invalid()
        page = [i for i in session.transcript if i["sequence"] > after][:limit]
        more = bool(page) and page[-1]["sequence"] < session.sequence
        return 200, {}, {"schemaVersion": "1.0", "items": page, "nextCursor": str(page[-1]["sequence"]) if more else None}

    def _send(self, session: _Session, headers: dict[str, str], body: bytes) -> tuple[int, dict[str, str], dict[str, Any]]:
        if self._failures:
            status, retry_after = self._failures.popleft()
            return self._problem(
                status, "VISITOR_RATE_LIMITED" if status == 429 else "VISITOR_UNAVAILABLE", "Retry later", retry_after
            )
        key = headers.get("idempotency-key", "")
        try:
            uuid.UUID(key)
        except ValueError:
            return self._invalid()
        data = self._json_body(body)
        content = data.get("content") if data else None
        if data is None or not set(data) <= {"schemaVersion", "content", "expectedCursor"} or data.get("schemaVersion") != "1.0":
            return self._invalid()
        if not isinstance(content, dict) or not set(content) <= {"type", "text", "choiceId"}:
            return self._invalid()
        kind = content.get("type")
        text, choice_id = content.get("text"), content.get("choiceId")
        if kind == "TEXT" and isinstance(text, str) and len(text) <= 1000 and choice_id is None:
            pass
        elif kind == "CHOICE" and isinstance(choice_id, str) and 0 < len(choice_id) <= 64 and text is None:
            pass
        else:
            return self._invalid()
        body_hash = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        previous = session.idempotency.get(key)
        if previous is not None:
            if previous[0] != body_hash:
                return self._problem(409, "VISITOR_IDEMPOTENCY_CONFLICT", "Idempotency key reused with a different request")
            return 200, {}, previous[1]
        response = self._process(session, kind, text or "", choice_id or "", content)
        session.idempotency[key] = (body_hash, response)
        return 200, {}, response

    def _process(self, session: _Session, kind: str, text: str, choice_id: str, content: dict[str, Any]) -> dict[str, Any]:
        self._record(session, "VISITOR", content=content)
        said = text.strip().upper() if kind == "TEXT" else ""
        if said == "STOP" or choice_id.upper() == "STOP":
            if session.state != "STOPPED":
                session.resume_state = session.state
            session.state = "STOPPED"
            blocks: list[dict[str, Any]] = []
        elif session.state == "STOPPED":
            blocks = []
            if said == "START":
                session.state = "CONSENT_PENDING"
                session.notice_resends = 0
                blocks = self._engine.consent_blocks(session)
        else:
            blocks = self._engine.turn(session, kind, text, choice_id)
        reply = _reply(session.state, blocks, self._engine.version)
        session.last_reply = reply
        self._record(session, "WAOOAW", reply=reply)
        payload = self._session_json(session)
        payload.update(
            {
                "messageId": str(uuid.uuid5(NAMESPACE, f"{session.session_id}:{session.sequence}")),
                "cursor": str(session.sequence),
                "reply": reply,
            }
        )
        return payload

    def _tap(self, reference: str) -> tuple[int, dict[str, str], dict[str, Any]]:
        session_id = self._references.get(reference)
        session = self._sessions.get(session_id or "")
        recorded = bool(session and not self._engine.is_legacy and session.handoff_issued and not session.tapped)
        if recorded and session is not None:
            session.tapped = True
        return 200, {}, {"schemaVersion": "1.0", "recorded": recorded}
