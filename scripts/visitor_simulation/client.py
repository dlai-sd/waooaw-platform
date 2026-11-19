# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
"""Stdlib client for the visitor conversation API (VisitorSimulatorAuth scheme)."""

import hashlib
import hmac
import json
import logging
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from visitor_simulation.models import Captured, Reply, SessionView, TurnView

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"
SESSIONS_PATH = "/api/v1/visitor/sessions"


class VisitorApiError(Exception):
    """A problem+json (or otherwise failed) response. Submitted content is never echoed."""

    def __init__(self, status: int, code: str = "", detail: str = "", correlation_id: str = "") -> None:
        super().__init__(f"visitor API error {status} {code}".strip())
        self.status = status
        self.code = code
        self.detail = detail
        self.correlation_id = correlation_id


class VisitorInvalidRequestError(VisitorApiError):
    pass


class VisitorUnauthorizedError(VisitorApiError):
    pass


class VisitorNotFoundError(VisitorApiError):
    pass


class VisitorConflictError(VisitorApiError):
    pass


class VisitorRateLimitedError(VisitorApiError):
    pass


class VisitorUnavailableError(VisitorApiError):
    pass


class VisitorTransportError(Exception):
    """The request did not complete (connection failure)."""


class VisitorTimeoutError(VisitorTransportError):
    """The client gave up waiting for a response. The server may have processed the request."""


_ERROR_TYPES: dict[int, type[VisitorApiError]] = {
    400: VisitorInvalidRequestError,
    401: VisitorUnauthorizedError,
    404: VisitorNotFoundError,
    409: VisitorConflictError,
    429: VisitorRateLimitedError,
    503: VisitorUnavailableError,
}
_RETRYABLE = {429, 503}


def sign_request(secret: str, timestamp: str, method: str, path: str, body: bytes) -> str:
    """Lowercase-hex HMAC-SHA256 over ``{timestamp}.{METHOD}.{path}.{sha256-hex(body)}``."""
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{timestamp}.{method.upper()}.{path}.{body_hash}".encode()
    return hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()


def canonical_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()


def _parse_captured(data: dict[str, Any]) -> Captured:
    return Captured.from_json(data.get("captured"))


def _parse_session(data: dict[str, Any], *, created: bool = False) -> SessionView:
    reply = Reply.from_json(data["reply"]) if data.get("reply") else None
    return SessionView(
        session_id=str(data["sessionId"]),
        channel=str(data["channel"]),
        state=str(data["state"]),
        outcome=str(data["outcome"]),
        captured=_parse_captured(data),
        reply=reply,
        created=created,
    )


def _parse_turn(data: dict[str, Any]) -> TurnView:
    return TurnView(
        session_id=str(data["sessionId"]),
        message_id=str(data["messageId"]),
        cursor=str(data["cursor"]),
        state=str(data["state"]),
        outcome=str(data["outcome"]),
        captured=_parse_captured(data),
        reply=Reply.from_json(data["reply"]),
    )


@dataclass(frozen=True)
class TranscriptPage:
    items: tuple[dict[str, Any], ...]
    next_cursor: str | None


class VisitorClient:
    """Signs and sends visitor API calls; only ever talks to the configured base URL."""

    def __init__(
        self,
        base_url: str,
        secret: str,
        *,
        timeout: float = 10.0,
        max_retries: int = 3,
        retry_after_cap: float = 2.0,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        parts = urllib.parse.urlsplit(base_url)
        if parts.scheme not in {"http", "https"} or not parts.netloc or parts.query or parts.fragment:
            raise ValueError("base_url must be an http(s) URL without query or fragment")
        if not secret:
            raise ValueError("simulator secret must not be empty")
        self._base_url = base_url.rstrip("/")
        self._base_path = parts.path.rstrip("/")
        self._secret = secret
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_after_cap = retry_after_cap
        self._clock = clock
        self._sleep = sleep
        self._drop_next_response = False
        self.request_log: deque[tuple[str, str]] = deque(maxlen=2000)

    def __repr__(self) -> str:
        return f"VisitorClient(base_url={self._base_url!r})"

    @property
    def base_url(self) -> str:
        return self._base_url

    def drop_next_response(self) -> None:
        """Failure injection: the next request is processed by the server but its reply is discarded as a timeout."""
        self._drop_next_response = True

    def open_session(self, subject_key: str, *, channel: str = "SIMULATION") -> SessionView:
        body = {"schemaVersion": SCHEMA_VERSION, "channel": channel, "subjectKey": subject_key}
        status, data = self._request("POST", SESSIONS_PATH, body=body)
        return _parse_session(data, created=status == 201)

    def get_session(self, session_id: str) -> SessionView:
        _, data = self._request("GET", f"{SESSIONS_PATH}/{self._sid(session_id)}")
        return _parse_session(data)

    def send_message(
        self,
        session_id: str,
        *,
        text: str | None = None,
        choice_id: str | None = None,
        idempotency_key: str | None = None,
        expected_cursor: str | None = None,
    ) -> TurnView:
        if (text is None) == (choice_id is None):
            raise ValueError("send exactly one of text or choice_id")
        content: dict[str, Any] = (
            {"type": "TEXT", "text": text} if text is not None else {"type": "CHOICE", "choiceId": choice_id}
        )
        body: dict[str, Any] = {"schemaVersion": SCHEMA_VERSION, "content": content}
        if expected_cursor:
            body["expectedCursor"] = expected_cursor
        key = idempotency_key or str(uuid.uuid4())
        uuid.UUID(key)
        _, data = self._request(
            "POST",
            f"{SESSIONS_PATH}/{self._sid(session_id)}/messages",
            body=body,
            headers={"Idempotency-Key": key},
        )
        return _parse_turn(data)

    def list_messages(self, session_id: str, *, cursor: str | None = None, limit: int | None = None) -> TranscriptPage:
        query: dict[str, str] = {}
        if cursor:
            query["cursor"] = cursor
        if limit:
            query["limit"] = str(limit)
        _, data = self._request("GET", f"{SESSIONS_PATH}/{self._sid(session_id)}/messages", query=query)
        return TranscriptPage(items=tuple(data.get("items", [])), next_cursor=data.get("nextCursor"))

    def tap_handoff(self, reference: str) -> bool:
        """Record the portal link tap on the API; returns the ``recorded`` flag."""
        quoted = urllib.parse.quote(reference, safe="")
        _, data = self._request("POST", f"/api/v1/visitor/handoffs/{quoted}/tap", body=None)
        return bool(data.get("recorded", False))

    @staticmethod
    def _sid(session_id: str) -> str:
        return str(uuid.UUID(session_id))

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        body_bytes = canonical_body(body) if body is not None else b""
        sign_path = f"{self._base_path}{path}"
        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query)}"
        attempt = 0
        while True:
            status, raw, response_headers = self._send_once(method, url, sign_path, body_bytes, headers or {})
            if status < 400:
                return status, self._json(raw)
            problem = self._problem(raw)
            if status in _RETRYABLE and attempt < self._max_retries:
                attempt += 1
                delay = self._retry_delay(response_headers.get("Retry-After"), problem)
                logger.info("visitor API %s on %s %s; retry %d in %.2fs", status, method, sign_path, attempt, delay)
                self._sleep(delay)
                continue
            error_type = _ERROR_TYPES.get(status, VisitorApiError)
            raise error_type(
                status,
                code=str(problem.get("code", "")),
                detail=str(problem.get("detail", ""))[:200],
                correlation_id=str(problem.get("correlationId", "")),
            )

    def _send_once(
        self, method: str, url: str, sign_path: str, body_bytes: bytes, headers: dict[str, str]
    ) -> tuple[int, bytes, dict[str, str]]:
        timestamp = str(int(self._clock()))
        request = urllib.request.Request(url, data=body_bytes if method == "POST" else None, method=method)  # noqa: S310
        request.add_header("Accept", "application/json")
        if method == "POST":
            request.add_header("Content-Type", "application/json")
        request.add_header("X-Visitor-Timestamp", timestamp)
        request.add_header("X-Visitor-Signature", sign_request(self._secret, timestamp, method, sign_path, body_bytes))
        for name, value in headers.items():
            request.add_header(name, value)
        self.request_log.append((method, url))
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                status, raw, response_headers = response.status, response.read(), dict(response.headers.items())
        except urllib.error.HTTPError as exc:
            try:
                status, raw, response_headers = exc.code, exc.read(), dict(exc.headers.items())
            finally:
                exc.close()
        except (TimeoutError, socket.timeout) as exc:
            raise VisitorTimeoutError("request timed out") from exc
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError | socket.timeout):
                raise VisitorTimeoutError("request timed out") from exc
            raise VisitorTransportError(f"connection failed: {type(exc.reason).__name__}") from exc
        if self._drop_next_response:
            self._drop_next_response = False
            raise VisitorTimeoutError("simulated client timeout; response discarded")
        return status, raw, response_headers

    @staticmethod
    def _json(raw: bytes) -> dict[str, Any]:
        try:
            parsed = json.loads(raw or b"{}")
        except json.JSONDecodeError as exc:
            raise VisitorTransportError("response was not valid JSON") from exc
        if not isinstance(parsed, dict):
            raise VisitorTransportError("response was not a JSON object")
        return parsed

    @staticmethod
    def _problem(raw: bytes) -> dict[str, Any]:
        try:
            parsed = json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    def _retry_delay(self, header: str | None, problem: dict[str, Any]) -> float:
        seconds: float = 1.0
        for candidate in (header, problem.get("retryAfterSeconds")):
            try:
                seconds = float(candidate)  # type: ignore[arg-type]
                break
            except (TypeError, ValueError):
                continue
        return max(0.0, min(seconds, self._retry_after_cap))
