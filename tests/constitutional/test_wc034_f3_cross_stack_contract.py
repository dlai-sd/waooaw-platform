# Implements: architecture/reference/components/conversation-core.md §9 F3 Acceptance Mapping
# constitutional_basis: C-001, C-023, C-026, C-059, C-063, C-076
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).parents[2]
BP_SPEC_PATH = REPO_ROOT / "architecture/reference/api-specs/business-platform.openapi.yaml"
PR_SPEC_PATH = REPO_ROOT / "architecture/reference/api-specs/professional-runtime.openapi.yaml"

BP_OPERATIONS = {
    ("get", "/api/v1/employment/relationships/{relationshipId}/conversation/messages"): "listConversationMessages",
    ("post", "/api/v1/employment/relationships/{relationshipId}/conversation/messages"): "sendConversationMessage",
    (
        "post",
        "/api/v1/employment/relationships/{relationshipId}/conversation/messages/{messageId}/retry",
    ): "retryConversationMessage",
    (
        "put",
        "/api/v1/employment/relationships/{relationshipId}/conversation/read-position",
    ): "updateConversationReadPosition",
    ("get", "/api/v1/employment/relationships/{relationshipId}/conversation/stream"): "streamConversation",
    (
        "delete",
        "/api/v1/employment/relationships/{relationshipId}/conversation/executions/{executionId}",
    ): "cancelConversationExecution",
}

PR_OPERATIONS = {
    ("post", "/api/v1/internal/conversations/{conversationId}/executions"): "startConversationExecution",
    (
        "get",
        "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream",
    ): "streamConversationExecution",
    (
        "delete",
        "/api/v1/internal/conversations/{conversationId}/executions/{executionId}",
    ): "cancelConversationExecutionInternal",
}

PUBLIC_EVENTS = {
    "message.accepted",
    "processing.started",
    "response.delta",
    "card.upserted",
    "message.completed",
    "message.failed",
    "stream.cancelled",
    "stop.applied",
    "reconciliation.required",
    "heartbeat",
}

INTERNAL_EVENTS = {
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
}


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _operation_ids(spec: dict[str, Any]) -> dict[tuple[str, str], str]:
    return {
        (method, path): operation["operationId"]
        for path, path_item in spec["paths"].items()
        for method, operation in path_item.items()
        if method in {"get", "post", "put", "delete", "patch"} and "operationId" in operation
    }


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_canonical_operations_match_implementations_and_generated_client() -> None:
    bp_spec = _load_yaml(BP_SPEC_PATH)
    pr_spec = _load_yaml(PR_SPEC_PATH)

    bp_operation_ids = _operation_ids(bp_spec)
    pr_operation_ids = _operation_ids(pr_spec)
    assert {key: bp_operation_ids[key] for key in BP_OPERATIONS} == BP_OPERATIONS
    assert {key: pr_operation_ids[key] for key in PR_OPERATIONS} == PR_OPERATIONS

    bp_controller = _read("src/business-platform/Controllers/ConversationController.cs")
    assert '[Route("api/v1/employment/relationships/{relationshipId:guid}/conversation")]' in bp_controller
    for attribute in (
        '[HttpGet("messages")]',
        '[HttpPost("messages")]',
        '[HttpPost("messages/{messageId:guid}/retry")]',
        '[HttpPut("read-position")]',
        '[HttpGet("stream")]',
        '[HttpDelete("executions/{executionId:guid}")]',
    ):
        assert attribute in bp_controller

    pr_router = _read("src/professional-runtime/routers/conversation_execution.py")
    for operation_id in PR_OPERATIONS.values():
        assert f'operation_id="{operation_id}"' in pr_router
    for _, path in PR_OPERATIONS:
        operation = pr_spec["paths"][path][next(method for method, candidate in PR_OPERATIONS if candidate == path)]
        assert operation["x-internal"] is True
        assert operation["security"] == [{"ServiceBearerAuth": []}]

    generated_client = _read("web/lib/api/generated/apis/ConversationApi.ts")
    for operation_id in BP_OPERATIONS.values():
        assert re.search(rf"async {re.escape(operation_id)}(?:Raw)?\(", generated_client)
    for _, path in BP_OPERATIONS:
        assert f"let urlPath = `{path}`;" in generated_client


def test_event_schema_versions_and_vocabularies_match_runtime_sources() -> None:
    bp_spec = _load_yaml(BP_SPEC_PATH)
    pr_spec = _load_yaml(PR_SPEC_PATH)

    assert bp_spec["components"]["schemas"]["ConversationSchemaVersion"]["const"] == "1.0"
    assert pr_spec["components"]["schemas"]["ConversationExecutionSchemaVersion"]["const"] == "1.0"
    assert set(bp_spec["components"]["schemas"]["ConversationStreamEventType"]["enum"]) == PUBLIC_EVENTS
    assert set(pr_spec["components"]["schemas"]["ProfessionalExecutionEventType"]["enum"]) == INTERNAL_EVENTS

    bp_service = _read("src/business-platform/Services/ConversationService.cs")
    bp_migration = _read("infrastructure/postgres/init/21-conversation-core.sql")
    pr_models = _read("src/professional-runtime/routers/conversation_models.py")
    for event_type in PUBLIC_EVENTS - {"heartbeat"}:
        assert f'"{event_type}"' in bp_service or f"'{event_type}'" in bp_migration
    for event_type in PUBLIC_EVENTS:
        assert f"'{event_type}'" in bp_migration
    for event_type in INTERNAL_EVENTS:
        assert f'"{event_type}"' in pr_models


def test_emergency_stop_signal_is_canonical_and_independent_from_cancellation() -> None:
    ce_service = _read("src/constitutional-engine/Services/ConstitutionalEngineService.cs")
    conversation_workflow = _read("src/professional-runtime/workflows/conversation_execution_workflow.py")
    paas_workflow = _read("src/professional-runtime/workflows/paas_workflow.py")

    for source in (ce_service, conversation_workflow, paas_workflow):
        assert '"EmergencyStop"' in source
        assert '"emergency-stop"' not in source
    assert '@workflow.signal(name="CancelConversationExecution")' in conversation_workflow
    assert '@workflow.signal(name="EmergencyStop")' in conversation_workflow
    assert "self._state = SessionState.EMERGENCY_STOPPED" in paas_workflow


def test_browser_boundary_targets_bp_only_and_excludes_unapproved_sdk() -> None:
    package = json.loads(_read("web/package.json"))
    dependencies = {**package["dependencies"], **package["devDependencies"]}
    assert "@ai-sdk/react" not in dependencies

    browser_owned_files = [
        path
        for root in (REPO_ROOT / "web/app", REPO_ROOT / "web/components")
        for path in root.rglob("*")
        if path.suffix in {".ts", ".tsx"} and not path.name.endswith((".test.ts", ".test.tsx"))
        and path.read_text(encoding="utf-8").lstrip().startswith("'use client';")
    ]
    forbidden_urls = re.compile(r"(?:https?://|wss?://)[^\s'\"]*(?:5003|professional-runtime|ai-runtime|provider)", re.I)
    for path in browser_owned_files:
        assert forbidden_urls.search(path.read_text(encoding="utf-8")) is None, path.relative_to(REPO_ROOT)

    server_boundary = _read("web/lib/api/conversation.ts")
    assert "BUSINESS_PLATFORM_URL" in server_boundary
    assert "http://localhost:5001" in server_boundary
    assert "5003" not in server_boundary
    assert "professional-runtime" not in server_boundary.lower()

    emergency_stop_boundary = _read("web/app/api/emergency-stop/route.ts")
    assert "PROFESSIONAL_RUNTIME_URL" in emergency_stop_boundary
    assert "/api/v1/emergency-stop" in emergency_stop_boundary
    assert "/api/v1/internal/conversations" not in emergency_stop_boundary