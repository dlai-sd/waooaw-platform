# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
import json
import urllib.error
import urllib.request
import uuid

import pytest

from visitor_simulation.client import (
    VisitorClient,
    VisitorConflictError,
    VisitorRateLimitedError,
    VisitorTimeoutError,
    VisitorUnauthorizedError,
    VisitorUnavailableError,
    sign_request,
)

SESSIONS = "/api/v1/visitor/sessions"


def test_signature_matches_independently_computed_vectors():
    body = b'{"channel":"SIMULATION","schemaVersion":"1.0","subjectKey":"sim-dr-mehta-001"}'
    assert (
        sign_request("sim-secret-for-tests", "1700000000", "POST", SESSIONS, body)
        == "9854aefb52efa6b10ebd58c766224bec447f92e2140ae5a74eae1d88bcd96b70"
    )
    empty_get = sign_request("sim-secret-for-tests", "1700000000", "get", f"{SESSIONS}/0b5fd0a2-6c1a-4c6c-8f5e-4a2f2c0e1a11", b"")
    assert empty_get == "859a58f3b81eae2451d91421f229b1208064765b49cacca2c6ebebb8a78f8a5b"


def test_client_signs_exact_bytes_it_sends(good_client, monkeypatch):
    seen = {}
    original = urllib.request.urlopen

    def spy(request, timeout=None):
        seen["body"] = request.data
        seen["headers"] = {k.lower(): v for k, v in request.header_items()}
        return original(request, timeout=timeout)

    monkeypatch.setattr(urllib.request, "urlopen", spy)
    good_client.open_session("sim-dr-mehta-001")
    expected = sign_request("sim-secret-for-tests", seen["headers"]["x-visitor-timestamp"], "POST", SESSIONS, seen["body"])
    assert seen["headers"]["x-visitor-signature"] == expected
    assert json.loads(seen["body"])["channel"] == "SIMULATION"


def test_open_resume_send_read_and_tap(good_client):
    first = good_client.open_session("sim-dr-mehta-001")
    assert first.created and first.state == "CONSENT_PENDING"
    assert first.reply and first.reply.options[0].id == "YES"
    assert not good_client.open_session("sim-dr-mehta-001").created

    turn = good_client.send_message(first.session_id, choice_id="YES")
    assert turn.state == "DISCOVER" and turn.reply.text.count("?") == 1
    turn = good_client.send_message(first.session_id, text="I run a dental clinic in Pune.")
    assert turn.state == "QUALIFY" and turn.captured.city == "Pune"
    turn = good_client.send_message(first.session_id, choice_id="BOOKINGS")
    assert turn.state == "SHOW_VALUE" and turn.captured.goal_code == "BOOKINGS"
    turn = good_client.send_message(first.session_id, choice_id="START_TRIAL")
    assert turn.state == "HANDOFF" and turn.reply.link is not None

    session = good_client.get_session(first.session_id)
    assert session.outcome == "LEAD"
    page = good_client.list_messages(first.session_id, limit=3)
    assert len(page.items) == 3 and page.next_cursor == "3"
    rest = good_client.list_messages(first.session_id, cursor=page.next_cursor)
    assert rest.items[0]["sequence"] == 4

    reference = turn.reply.link.url.split("ref=")[1]
    assert good_client.tap_handoff(reference) is True
    assert good_client.tap_handoff(reference) is False
    assert good_client.tap_handoff("unknown-reference") is False
    assert good_client.get_session(first.session_id).outcome == "FULL_SUCCESS"


def test_bad_missing_and_old_signatures_are_rejected(good_server, secret):
    wrong = VisitorClient(good_server.base_url, "another-secret", sleep=lambda _: None)
    with pytest.raises(VisitorUnauthorizedError) as caught:
        wrong.open_session("sim-dr-mehta-001")
    assert caught.value.status == 401 and caught.value.code == "VISITOR_SESSION_REQUIRED"

    stale = VisitorClient(good_server.base_url, secret, clock=lambda: 1_000.0, sleep=lambda _: None)
    with pytest.raises(VisitorUnauthorizedError):
        stale.open_session("sim-dr-mehta-001")

    unsigned = urllib.request.Request(
        good_server.base_url + SESSIONS,
        data=b"{}",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as http_error:
        urllib.request.urlopen(unsigned, timeout=5)
    assert http_error.value.code == 401
    http_error.value.close()
    assert good_server.requests[-1][2] == 401


def test_idempotency_replay_and_conflict(good_client):
    session = good_client.open_session("sim-dr-mehta-001")
    key = str(uuid.UUID(int=101))
    first = good_client.send_message(session.session_id, choice_id="YES", idempotency_key=key)
    replay = good_client.send_message(session.session_id, choice_id="YES", idempotency_key=key)
    assert replay == first
    assert len(good_client.list_messages(session.session_id).items) == 3
    with pytest.raises(VisitorConflictError) as caught:
        good_client.send_message(session.session_id, text="something else", idempotency_key=key)
    assert caught.value.code == "VISITOR_IDEMPOTENCY_CONFLICT"


def test_retries_429_and_503_honour_retry_after_with_a_cap(good_server, secret):
    sleeps: list[float] = []
    client = VisitorClient(good_server.base_url, secret, sleep=sleeps.append, retry_after_cap=2.0)
    session = client.open_session("sim-dr-mehta-001")
    good_server.queue_failure(429, retry_after=1)
    good_server.queue_failure(503, retry_after=30)
    turn = client.send_message(session.session_id, choice_id="YES")
    assert turn.state == "DISCOVER"
    assert sleeps == [1.0, 2.0]


def test_retries_are_bounded_and_raise_typed_errors(good_server, secret):
    client = VisitorClient(good_server.base_url, secret, sleep=lambda _: None, max_retries=2)
    session = client.open_session("sim-dr-mehta-001")
    for _ in range(3):
        good_server.queue_failure(429)
    with pytest.raises(VisitorRateLimitedError):
        client.send_message(session.session_id, choice_id="YES")
    for _ in range(3):
        good_server.queue_failure(503)
    with pytest.raises(VisitorUnavailableError):
        client.send_message(session.session_id, choice_id="YES")


def test_socket_timeout_and_dropped_response_raise_visitor_timeout(good_server, secret):
    client = VisitorClient(good_server.base_url, secret, timeout=0.2, sleep=lambda _: None)
    session = client.open_session("sim-dr-mehta-001")
    good_server.response_delay = 0.6
    with pytest.raises(VisitorTimeoutError):
        client.get_session(session.session_id)
    good_server.response_delay = 0.0
    client.drop_next_response()
    with pytest.raises(VisitorTimeoutError):
        client.send_message(session.session_id, choice_id="YES", idempotency_key=str(uuid.UUID(int=102)))
    replay = client.send_message(session.session_id, choice_id="YES", idempotency_key=str(uuid.UUID(int=102)))
    assert replay.state == "DISCOVER"


def test_client_rejects_bad_inputs_and_hides_the_secret(good_server, secret):
    with pytest.raises(ValueError):
        VisitorClient("ftp://example.invalid", secret)
    with pytest.raises(ValueError):
        VisitorClient(good_server.base_url, "")
    client = VisitorClient(good_server.base_url, secret)
    assert secret not in repr(client)
    with pytest.raises(ValueError):
        client.send_message("not-a-uuid", text="hi", choice_id="YES")
    with pytest.raises(ValueError):
        client.get_session("../../etc/passwd")
