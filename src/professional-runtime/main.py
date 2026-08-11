# Implements: architecture/reference/components/professional-runtime.md
# constitutional_basis: C-025 (PAAS exclusive), C-001 (Emergency Stop ≤250ms),
#   C-059, C-063, ADR-015 (Temporal), ADR-018 (Emergency Stop signal)

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from temporalio.client import Client as TemporalClient
from temporalio.client import TLSConfig
from temporalio.service import RPCError
from temporalio.worker import Worker

from constitutional_gateway import GrpcConversationConstitutionalGateway
from routers.conversation_execution import TEMPORAL_TASK_QUEUE
from routers.conversation_execution import router as conversation_execution_router
from routers.conversation_models import HealthResponse
from routers.emergency_stop import KeycloakJWTValidator
from routers.emergency_stop import router as emergency_stop_router
from routers.sessions import router as sessions_router
from relationship_workspace import configure_relationship_workspace
from relationship_workspace import router as relationship_workspace_router
from workflows.conversation_execution_workflow import ConversationExecutionWorkflow

logger = logging.getLogger(__name__)


async def connect_temporal_client() -> TemporalClient:
    """Connect to self-hosted Temporal or Temporal Cloud using canonical environment names."""
    cloud_namespace = os.getenv("TEMPORAL_CLOUD_NAMESPACE")
    address = (
        os.getenv("TEMPORAL_ADDRESS")
        or os.getenv("TEMPORAL_CLOUD_ADDRESS")
        or (cloud_namespace if cloud_namespace and ":" in cloud_namespace else None)
        or "localhost:7233"
    )
    namespace = (
        os.getenv("TEMPORAL_NAMESPACE")
        or os.getenv("TEMPORAL_CLOUD_NAMESPACE_NAME")
        or (cloud_namespace if cloud_namespace and ":" not in cloud_namespace else None)
        or "default"
    )
    certificate_path = os.getenv("TEMPORAL_CLOUD_CERT_PATH")
    private_key_path = os.getenv("TEMPORAL_CLOUD_KEY_PATH")
    if bool(certificate_path) != bool(private_key_path):
        raise ValueError("Temporal Cloud certificate and key paths must be configured together")
    tls = None
    if certificate_path and private_key_path:
        certificate, private_key = await asyncio.gather(
            asyncio.to_thread(Path(certificate_path).read_bytes),
            asyncio.to_thread(Path(private_key_path).read_bytes),
        )
        tls = TLSConfig(
            client_cert=certificate,
            client_private_key=private_key,
        )
    return await TemporalClient.connect(address, namespace=namespace, tls=tls)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Own production auth, CE, Temporal, and conversation worker composition."""
    application.state.temporal_client = None
    application.state.temporal_worker = None
    application.state.temporal_worker_task = None
    application.state.bp_service_jwt_secret = os.getenv("BP_SERVICE_JWT_SECRET")
    application.state.conversation_constitutional_gateway = None
    application.state.emergency_stop_jwt_validator = None
    worker: Worker | None = None
    worker_task: asyncio.Task[None] | None = None
    gateway: GrpcConversationConstitutionalGateway | None = None
    keycloak_client: httpx.AsyncClient | None = None
    ce_address = os.getenv("CONSTITUTIONAL_ENGINE_ADDRESS")
    if ce_address:
        gateway = GrpcConversationConstitutionalGateway(ce_address)
        application.state.conversation_constitutional_gateway = gateway
    jwks_url = os.getenv("KEYCLOAK_JWKS_URL")
    if jwks_url:
        issuer = os.getenv("KEYCLOAK_ISSUER") or jwks_url.removesuffix("/protocol/openid-connect/certs")
        audience = os.getenv("KEYCLOAK_AUDIENCE", "waooaw-platform")
        keycloak_client = httpx.AsyncClient(timeout=2.0)
        application.state.emergency_stop_jwt_validator = KeycloakJWTValidator(
            jwks_url,
            issuer,
            audience,
            keycloak_client,
        )
    try:
        temporal = await connect_temporal_client()
        worker = Worker(
            temporal,
            task_queue=TEMPORAL_TASK_QUEUE,
            workflows=[ConversationExecutionWorkflow],
        )
        worker_task = asyncio.create_task(worker.run(), name="conversation-execution-worker")
        application.state.temporal_client = temporal
        application.state.temporal_worker = worker
        application.state.temporal_worker_task = worker_task
    except (OSError, RPCError, RuntimeError, ValueError):
        logger.error("Temporal startup failed; Professional Runtime remains fail-safe unavailable", exc_info=True)

    yield

    if worker is not None:
        await worker.shutdown()
    if worker_task is not None:
        with suppress(asyncio.CancelledError):
            await worker_task
    application.state.temporal_client = None
    application.state.temporal_worker = None
    application.state.temporal_worker_task = None
    application.state.conversation_constitutional_gateway = None
    application.state.emergency_stop_jwt_validator = None
    application.state.bp_service_jwt_secret = None
    if gateway is not None:
        await gateway.close()
    if keycloak_client is not None:
        await keycloak_client.aclose()


app = FastAPI(
    title="WAOOAW Professional Runtime",
    description="PAAS execution engine (C-025). All professional work runs here.",
    version="1.2.0",
    lifespan=lifespan,
)

app.include_router(sessions_router)
app.include_router(emergency_stop_router)
app.include_router(conversation_execution_router)
app.include_router(relationship_workspace_router)
configure_relationship_workspace(app)


def _execution_problem_response(name: str) -> dict[str, object]:
    return {"$ref": f"#/components/responses/{name}"}


def canonical_openapi() -> dict:
    """Expose the canonical internal F3 contract rather than framework-derived shapes."""
    if app.openapi_schema is None:
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        schema["servers"] = [
            {"url": "http://localhost:5003", "description": "Local development"},
            {
                "url": "https://rt.waooaw.com",
                "description": "Production (Azure Container Apps — WebSocket endpoint)",
            },
        ]
        schema["tags"] = [
            {"name": "Emergency Stop", "description": "Real-time Emergency Stop WebSocket and REST fallback"},
            {"name": "PAAS Sessions", "description": "Pre-Authorized Action Space session lifecycle"},
            {"name": "Internal", "description": "Internal endpoints called by Business Platform only (not customer-facing)"},
            {
                "name": "Conversation Execution",
                "description": "Internal BP-only professional execution and typed event stream for WC-034 F3",
            },
            {"name": "Health", "description": "Service health"},
        ]
        schema["security"] = [{"BearerAuth": []}]
        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["BearerAuth"] = {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        security_schemes["ServiceBearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": (
                "BP service assertion with PR audience plus signed tenant_id, relationship_id, and\n"
                "delegated actor context. PR derives context only from these claims; request bodies,\n"
                "paths, and headers cannot override tenant or relationship authorization.\n"
            ),
        }
        components.setdefault("parameters", {}).update({
            "ConversationId": {
                "name": "conversationId",
                "in": "path",
                "required": True,
                "schema": {"type": "string", "format": "uuid"},
            },
            "ProfessionalExecutionId": {
                "name": "executionId",
                "in": "path",
                "required": True,
                "schema": {"type": "string", "format": "uuid"},
            },
            "IdempotencyKey": {
                "name": "Idempotency-Key",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "format": "uuid"},
            },
            "CorrelationId": {
                "name": "X-Correlation-Id",
                "in": "header",
                "required": True,
                "schema": {"type": "string", "format": "uuid"},
            },
            "InternalLastEventId": {
                "name": "Last-Event-ID",
                "in": "header",
                "required": False,
                "schema": {"type": "string", "minLength": 1, "maxLength": 256},
            },
        })
        problem_responses = {
            "ExecutionInvalidRequest": "Internal execution request or schema version is invalid",
            "ExecutionUnauthorized": "BP service assertion is missing, invalid, expired, or lacks required scoped claims",
            "ExecutionNotFound": "Conversation or execution is absent or inaccessible to the asserted context",
            "ExecutionConflict": "Idempotency identity, schema, sequence, or execution state conflicts",
            "ExecutionCursorExpired": "Event cursor expired; BP must reconcile from its canonical persisted state",
            "ExecutionStopped": "Emergency Stop is active; cancellation or reconnect cannot release it",
            "ExecutionUnavailable": "Runtime or Constitutional Engine is unavailable; no model dispatch occurs",
        }
        components.setdefault("responses", {}).update(
            {
                name: {
                    "description": description,
                    "content": {
                        "application/problem+json": {
                            "schema": {"$ref": "#/components/schemas/ExecutionProblemDetail"}
                        }
                    }
                }
                for name, description in problem_responses.items()
            }
        )
        schemas = components.setdefault("schemas", {})
        schemas.update(
            {
                "ConversationExecutionSchemaVersion": {"type": "string", "const": "1.0"},
                "ConversationExecutionTextV1": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["schemaVersion", "contentType", "text", "language"],
                    "properties": {
                        "schemaVersion": {"$ref": "#/components/schemas/ConversationExecutionSchemaVersion"},
                        "contentType": {"type": "string", "const": "TEXT"},
                        "text": {"type": "string", "minLength": 1, "maxLength": 32000},
                        "language": {"type": "string", "minLength": 2, "maxLength": 35},
                    },
                },
                "StartConversationExecutionRequestV1": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["schemaVersion", "messageId", "decisionSpaceVersion", "locale", "content"],
                    "properties": {
                        "schemaVersion": {"$ref": "#/components/schemas/ConversationExecutionSchemaVersion"},
                        "messageId": {
                            "type": "string",
                            "format": "uuid",
                            "description": "BP canonical customer message ID",
                        },
                        "decisionSpaceVersion": {"type": "integer", "minimum": 1},
                        "locale": {"type": "string", "minLength": 2, "maxLength": 35},
                        "content": {"$ref": "#/components/schemas/ConversationExecutionTextV1"},
                        "activeGoalContextId": {"type": "string", "format": "uuid"},
                    },
                },
                "ProfessionalExecutionEventType": {
                    "type": "string",
                    "enum": [
                        "execution.accepted",
                        "processing.started",
                        "response.delta",
                        "card.proposed",
                        "evidence.pending",
                        "evidence.recorded",
                        "execution.completed",
                        "execution.failed",
                        "execution.cancelled",
                        "execution.stopped",
                        "reconciliation.required",
                        "heartbeat",
                    ],
                },
                "ProfessionalExecutionEventV1": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "schemaVersion",
                        "eventId",
                        "eventType",
                        "conversationId",
                        "executionId",
                        "messageId",
                        "sequence",
                        "occurredAt",
                        "data",
                    ],
                    "properties": {
                        "schemaVersion": {"$ref": "#/components/schemas/ConversationExecutionSchemaVersion"},
                        "eventId": {"type": "string", "minLength": 1, "maxLength": 256},
                        "eventType": {"$ref": "#/components/schemas/ProfessionalExecutionEventType"},
                        "conversationId": {"type": "string", "format": "uuid"},
                        "executionId": {"type": "string", "format": "uuid"},
                        "messageId": {"type": "string", "format": "uuid"},
                        "sequence": {"type": "integer", "format": "int64", "minimum": 1},
                        "occurredAt": {"type": "string", "format": "date-time"},
                        "data": {
                            "oneOf": [
                                {"$ref": "#/components/schemas/ProfessionalDeltaV1"},
                                {"$ref": "#/components/schemas/ProfessionalCardProposalV1"},
                                {"$ref": "#/components/schemas/ProfessionalEvidenceEventV1"},
                                {"$ref": "#/components/schemas/ProfessionalTerminalEventV1"},
                                {"$ref": "#/components/schemas/ProfessionalReconciliationEventV1"},
                                {"$ref": "#/components/schemas/ProfessionalHeartbeatV1"},
                            ]
                        },
                    },
                },
                "HealthResponse": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {"type": "string", "enum": ["healthy", "degraded", "unhealthy"]},
                        "temporalConnected": {"type": "boolean"},
                        "constitutionalEngineReachable": {"type": "boolean"},
                        "activePAASSessions": {"type": "integer"},
                    },
                },
            }
        )

        start = schema["paths"]["/api/v1/internal/conversations/{conversationId}/executions"]["post"]
        start["x-internal"] = True
        start["security"] = [{"ServiceBearerAuth": []}]
        start["tags"] = ["Conversation Execution"]
        start["parameters"] = [
            {"$ref": "#/components/parameters/ConversationId"},
            {"$ref": "#/components/parameters/IdempotencyKey"},
            {"$ref": "#/components/parameters/CorrelationId"},
        ]
        start["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/StartConversationExecutionRequestV1"}
                }
            },
        }
        start["responses"] = {
            "202": {
                "description": "Durable professional execution accepted",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProfessionalExecutionV1"}}},
            },
            "200": {
                "description": "Prior identical execution outcome replayed",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProfessionalExecutionV1"}}},
            },
            "400": _execution_problem_response("ExecutionInvalidRequest"),
            "401": _execution_problem_response("ExecutionUnauthorized"),
            "404": _execution_problem_response("ExecutionNotFound"),
            "409": _execution_problem_response("ExecutionConflict"),
            "423": _execution_problem_response("ExecutionStopped"),
            "503": _execution_problem_response("ExecutionUnavailable"),
        }

        stream = schema["paths"]["/api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream"]["get"]
        stream["x-internal"] = True
        stream["security"] = [{"ServiceBearerAuth": []}]
        stream["tags"] = ["Conversation Execution"]
        stream["parameters"] = [
            {"$ref": "#/components/parameters/ConversationId"},
            {"$ref": "#/components/parameters/ProfessionalExecutionId"},
            {"$ref": "#/components/parameters/InternalLastEventId"},
            {"$ref": "#/components/parameters/CorrelationId"},
        ]
        stream["responses"] = {
            "200": {
                "description": "Versioned internal professional execution event stream",
                "headers": {"Cache-Control": {"schema": {"type": "string", "const": "no-store"}}},
                "content": {
                    "text/event-stream": {
                        "schema": {"$ref": "#/components/schemas/ProfessionalExecutionEventV1"}
                    }
                },
            },
            "401": _execution_problem_response("ExecutionUnauthorized"),
            "404": _execution_problem_response("ExecutionNotFound"),
            "410": _execution_problem_response("ExecutionCursorExpired"),
            "423": _execution_problem_response("ExecutionStopped"),
            "503": _execution_problem_response("ExecutionUnavailable"),
        }

        cancel = schema["paths"]["/api/v1/internal/conversations/{conversationId}/executions/{executionId}"]["delete"]
        cancel["x-internal"] = True
        cancel["security"] = [{"ServiceBearerAuth": []}]
        cancel["tags"] = ["Conversation Execution"]
        cancel["parameters"] = [
            {"$ref": "#/components/parameters/ConversationId"},
            {"$ref": "#/components/parameters/ProfessionalExecutionId"},
            {"$ref": "#/components/parameters/IdempotencyKey"},
            {"$ref": "#/components/parameters/CorrelationId"},
        ]
        cancel["responses"] = {
            "202": {
                "description": "Cancellation accepted",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProfessionalExecutionV1"}}},
            },
            "200": {
                "description": "Existing terminal outcome replayed",
                "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ProfessionalExecutionV1"}}},
            },
            "401": _execution_problem_response("ExecutionUnauthorized"),
            "404": _execution_problem_response("ExecutionNotFound"),
            "409": _execution_problem_response("ExecutionConflict"),
            "423": _execution_problem_response("ExecutionStopped"),
            "503": _execution_problem_response("ExecutionUnavailable"),
        }
        schema["paths"]["/health"]["get"]["security"] = []
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = canonical_openapi


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, _error: RequestValidationError) -> JSONResponse:
    """Return the F3 RFC 9457 shape without echoing rejected request content."""
    if request.url.path.startswith("/api/v1/internal/conversations/"):
        raw_correlation_id = request.headers.get("X-Correlation-Id", "")
        try:
            correlation_id = str(uuid.UUID(raw_correlation_id))
        except ValueError:
            correlation_id = str(uuid.uuid4())
        return JSONResponse(
            status_code=400,
            media_type="application/problem+json",
            content={
                "type": "https://waooaw.com/problems/execution-request-invalid",
                "title": "Execution request is invalid",
                "status": 400,
                "code": "EXECUTION_REQUEST_INVALID",
                "correlationId": correlation_id,
            },
        )
    return JSONResponse(status_code=422, content={"detail": "Request validation failed"})


@app.get("/health", operation_id="getPRHealth", response_model=HealthResponse, tags=["Health"])
async def health(request: Request) -> HealthResponse:
    """Report canonical runtime health without treating degraded dependencies as healthy."""
    worker_task = getattr(request.app.state, "temporal_worker_task", None)
    temporal_connected = (
        getattr(request.app.state, "temporal_client", None) is not None
        and worker_task is not None
        and not worker_task.done()
    )
    gateway = getattr(request.app.state, "conversation_constitutional_gateway", None)
    try:
        ce_reachable = gateway is not None and await gateway.is_ready()
    except Exception:
        ce_reachable = False
    bp_auth_configured = bool(getattr(request.app.state, "bp_service_jwt_secret", None))
    if not temporal_connected:
        status = "unhealthy"
    elif not ce_reachable or not bp_auth_configured:
        status = "degraded"
    else:
        status = "healthy"
    return HealthResponse(
        status=status,
        temporalConnected=temporal_connected,
        constitutionalEngineReachable=ce_reachable,
        activePAASSessions=max(0, int(getattr(request.app.state, "active_paas_sessions", 0))),
    )
