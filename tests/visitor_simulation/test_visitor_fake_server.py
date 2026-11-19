# Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R012, WC135-R013
# Constitutional basis: C-048, C-049, C-059, C-063
from pathlib import Path

import yaml

from visitor_simulation.models import OUTCOMES, STATES

SPEC = (
    Path(__file__).resolve().parents[2] / "architecture/reference/api-specs/visitor-conversation-business-platform.openapi.yaml"
)
SCHEMAS = yaml.safe_load(SPEC.read_text(encoding="utf-8"))["components"]["schemas"]


def _check(schema, value, path="$"):
    """Minimal OpenAPI schema check: required, additionalProperties false, enums, lengths, array limits."""
    if "$ref" in schema:
        return _check(SCHEMAS[schema["$ref"].rsplit("/", 1)[1]], value, path)
    if "enum" in schema:
        assert value in schema["enum"], f"{path}: {value!r} not in {schema['enum']}"
    if isinstance(value, str) and "maxLength" in schema:
        assert len(value) <= schema["maxLength"], f"{path}: {len(value)} > {schema['maxLength']}"
    if isinstance(value, list):
        assert len(value) <= schema.get("maxItems", len(value)), f"{path}: too many items"
        for i, item in enumerate(value):
            _check(schema.get("items", {}), item, f"{path}[{i}]")
    if isinstance(value, dict) and "properties" in schema:
        for name in schema.get("required", []):
            assert name in value, f"{path}: missing {name}"
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(schema["properties"]), f"{path}: unexpected {set(value) - set(schema['properties'])}"
        for name, item in value.items():
            _check(schema["properties"][name], item, f"{path}.{name}")


def _raw(client, method, path, body=None):
    status, data = client._request(method, path, body=body)
    return status, data


def test_open_session_and_turn_payloads_conform_to_the_openapi_schemas(good_client):
    status, opened = _raw(
        good_client,
        "POST",
        "/api/v1/visitor/sessions",
        {"schemaVersion": "1.0", "channel": "SIMULATION", "subjectKey": "sim-dr-mehta-001"},
    )
    assert status == 201
    _check(SCHEMAS["VisitorSessionV1"], opened)
    sid = opened["sessionId"]
    for content in (
        {"type": "CHOICE", "choiceId": "YES"},
        {"type": "TEXT", "text": "I run a dental clinic in Pune."},
        {"type": "CHOICE", "choiceId": "BOOKINGS"},
        {"type": "TEXT", "text": "How would this work for a dental clinic like mine?"},
        {"type": "CHOICE", "choiceId": "OTHER_PROFESSIONALS"},
        {"type": "CHOICE", "choiceId": "START_TRIAL"},
    ):
        turn = good_client.send_message(
            sid, **({"choice_id": content["choiceId"]} if content["type"] == "CHOICE" else {"text": content["text"]})
        )
        status, payload = _raw(good_client, "GET", f"/api/v1/visitor/sessions/{sid}")
        _check(SCHEMAS["VisitorSessionV1"], payload)
        assert turn.state in STATES and turn.outcome in OUTCOMES
    _, transcript = _raw(good_client, "GET", f"/api/v1/visitor/sessions/{sid}/messages")
    _check(SCHEMAS["VisitorTranscriptPageV1"], transcript)


def test_every_good_reply_respects_the_block_and_length_limits(good_client):
    sid = good_client.open_session("sim-rupali-001").session_id
    steps = [
        {"choice_id": "YES"},
        {"text": "Mujhe apna beauty business badhana hai, kya aap madad karoge?"},
        {"text": "[voice note]"},
        {"text": "It is a small business."},
        {"text": "I am a solo beauty artist in Pune."},
        {"choice_id": "ENQUIRIES"},
        {"choice_id": "ASK"},
        {"text": "How much does it cost?"},
        {"text": "Is this just ChatGPT?"},
        {"text": "Do you help with farming?"},
        {"choice_id": "START_TRIAL"},
    ]
    for step in steps:
        turn = good_client.send_message(sid, **step)
        _check(SCHEMAS["VisitorReplyV1"], turn.reply.to_json())
        assert len(turn.reply.text.split("?")) <= 2


def test_stop_and_start_semantics(good_client):
    sid = good_client.open_session("sim-dr-mehta-001").session_id
    good_client.send_message(sid, choice_id="YES")
    good_client.send_message(sid, text="I run a dental clinic in Pune.")
    stopped = good_client.send_message(sid, text="stop")
    assert stopped.state == "STOPPED" and stopped.reply.is_empty and stopped.outcome == "OPT_OUT"
    ignored = good_client.send_message(sid, text="hello?")
    assert ignored.state == "STOPPED" and ignored.reply.is_empty
    restarted = good_client.send_message(sid, text="START")
    assert restarted.state == "CONSENT_PENDING" and restarted.reply.options[0].id == "YES"
    resumed = good_client.send_message(sid, choice_id="YES")
    assert resumed.state == "QUALIFY"


def test_start_outside_stopped_is_a_no_op_and_stop_works_in_every_state(good_client):
    sid = good_client.open_session("sim-kiran-001").session_id
    before = good_client.get_session(sid).state
    good_client.send_message(sid, text="START")
    assert good_client.get_session(sid).state == before
    assert good_client.send_message(sid, choice_id="STOP").state == "STOPPED"


def test_consent_notice_is_resent_once_then_waits(good_client):
    sid = good_client.open_session("sim-yashus-001").session_id
    assert good_client.send_message(sid, text="Is this just ChatGPT?").reply.options
    assert good_client.send_message(sid, text="Really?").reply.is_empty


def test_invalid_requests_are_rejected(good_client):
    import pytest

    from visitor_simulation.client import VisitorInvalidRequestError, VisitorNotFoundError

    with pytest.raises(VisitorInvalidRequestError):
        good_client._request("POST", "/api/v1/visitor/sessions", body={"schemaVersion": "1.0", "channel": "WEB"})
    with pytest.raises(VisitorInvalidRequestError):
        good_client._request(
            "POST", "/api/v1/visitor/sessions", body={"schemaVersion": "1.0", "channel": "SIMULATION", "subjectKey": "short"}
        )
    sid = good_client.open_session("sim-kiran-002").session_id
    with pytest.raises(VisitorInvalidRequestError):
        good_client.send_message(sid, text="x" * 1001)
    with pytest.raises(VisitorNotFoundError):
        good_client.get_session("0b5fd0a2-6c1a-4c6c-8f5e-4a2f2c0e1a11")


def test_legacy_behaviour_never_captures_details_or_offers_a_link(legacy_client):
    sid = legacy_client.open_session("sim-dr-mehta-001").session_id
    legacy_client.send_message(sid, text="YES")
    turn = legacy_client.send_message(sid, text="I run a dental clinic in Pune.")
    assert turn.reply.link is None and "catalogue preview" in turn.reply.text
    session = legacy_client.get_session(sid)
    assert session.outcome == "NONE" and session.captured.city is None
    assert legacy_client.send_message(sid, text="STOP").outcome == "OPT_OUT"
