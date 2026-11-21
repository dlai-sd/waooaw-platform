# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-11
# Constitutional basis: C-059, C-063, C-088
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from fastapi import FastAPI
from opentelemetry import metrics as otel_metrics
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from wallet.spend_events import (  # noqa: F401 - the spend event and metric surface of C4-11
    LIVE_MARGIN_BREACH_METRIC,
    PARITY_DIFFERENCE_METRIC,
    SPEND_DENIED,
    SPEND_DENIED_METRIC,
    SPEND_PAISE_METRIC,
    SPEND_RELEASED,
    SPEND_RESERVED,
    SPEND_SETTLED,
    emit_spend_event,
)

_JOURNEY_OPERATIONS = {
    "/trial/start": "trial.start",
    "/payments/hire-checkout": "hire.checkout.start",
    "/payments/hire-checkout/confirm": "hire.checkout.confirm",
    "/payments/hire-checkout/bind": "hire.relationship.bind",
}


def _status_class(status: int) -> str:
    return f"{status // 100}xx" if 100 <= status <= 599 else "unknown"


def _typed_outcome(operation: str, status: int) -> str:
    if 200 <= status < 300:
        return {
            "trial.start": "TRIAL_ALLOCATED",
            "hire.checkout.start": "CHECKOUT_OUTCOME_PRODUCED",
            "hire.checkout.confirm": "PAYMENT_CONFIRMED",
            "hire.relationship.bind": "COMMERCIAL_OUTCOME_BOUND",
        }.get(operation, "SUCCEEDED")
    if status == 409:
        return "CONFLICT"
    if status in {502, 503, 504}:
        return "DEPENDENCY_UNAVAILABLE"
    return "REJECTED"


def _server_request_hook(span: trace.Span, scope: Mapping[str, Any]) -> None:
    if not span.is_recording():
        return
    operation = _JOURNEY_OPERATIONS.get(str(scope.get("path", "")))
    if operation is None:
        return
    span.set_attribute("waooaw.journey.operation", operation)
    span.set_attribute("waooaw.correlation_id", span.get_span_context().trace_id.to_bytes(16, "big").hex())


def _server_response_hook(span: trace.Span, message: Mapping[str, Any]) -> None:
    if not span.is_recording() or message.get("type") != "http.response.start":
        return
    operation = span.attributes.get("waooaw.journey.operation") if hasattr(span, "attributes") else None
    if not isinstance(operation, str):
        return
    status = int(message.get("status", 0))
    span.set_attribute("waooaw.journey.status_class", _status_class(status))
    span.set_attribute("waooaw.journey.outcome", _typed_outcome(operation, status))


def configure_telemetry(app: FastAPI) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTLP_ENDPOINT")
    if not endpoint:
        return
    resource = Resource.create(
        {
            "service.name": "waooaw-billing-engine",
            "service.version": os.getenv("SERVICE_REVISION", "development"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=endpoint.startswith("http://")))
    )
    trace.set_tracer_provider(provider)
    exporter = OTLPMetricExporter(endpoint=endpoint, insecure=endpoint.startswith("http://"))
    otel_metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[PeriodicExportingMetricReader(exporter)])
    )
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        server_request_hook=_server_request_hook,
        server_response_hook=_server_response_hook,
        excluded_urls="health",
    )