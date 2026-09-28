from types import SimpleNamespace

from telemetry import _server_request_hook, _server_response_hook


class RecordingSpan:
    def __init__(self) -> None:
        self.attributes: dict[str, str] = {}

    def is_recording(self) -> bool:
        return True

    def set_attribute(self, name: str, value: str) -> None:
        self.attributes[name] = value

    def get_span_context(self) -> SimpleNamespace:
        return SimpleNamespace(trace_id=int("12" * 16, 16))


def test_hire_bind_span_contains_only_privacy_safe_journey_values() -> None:
    span = RecordingSpan()

    _server_request_hook(span, {"path": "/payments/hire-checkout/bind"})  # type: ignore[arg-type]
    _server_response_hook(span, {"type": "http.response.start", "status": 200})  # type: ignore[arg-type]

    assert span.attributes == {
        "waooaw.journey.operation": "hire.relationship.bind",
        "waooaw.correlation_id": "12" * 16,
        "waooaw.journey.status_class": "2xx",
        "waooaw.journey.outcome": "COMMERCIAL_OUTCOME_BOUND",
    }
    serialized = repr(span.attributes)
    for prohibited in ("customer_id", "relationship_id", "payment_id", "checkout_intent_id", "coupon"):
        assert prohibited not in serialized


def test_unknown_path_adds_no_custom_journey_values() -> None:
    span = RecordingSpan()

    _server_request_hook(span, {"path": "/payments/hire-checkout/private-value"})  # type: ignore[arg-type]
    _server_response_hook(span, {"type": "http.response.start", "status": 200})  # type: ignore[arg-type]

    assert span.attributes == {}