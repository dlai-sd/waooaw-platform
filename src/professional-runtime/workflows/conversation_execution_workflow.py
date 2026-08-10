# Implements: architecture/reference/components/professional-runtime.md §6 Conversation Execution Coordinator
# constitutional_basis: C-001, C-023, C-025, C-059; ADR-015, ADR-018, ADR-031
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from temporalio import workflow


@dataclass(frozen=True)
class ConversationExecutionInput:
    schema_version: str
    execution_id: str
    conversation_id: str
    message_id: str
    tenant_id: str
    relationship_id: str
    delegated_actor_id: str
    participant_role: str
    decision_space_version: int
    locale: str
    content: dict[str, Any]
    active_goal_context_id: str | None
    request_hash: str
    accepted_at: str


@dataclass(frozen=True)
class CancellationSignal:
    idempotency_key: str
    request_hash: str
    requested_at: str


@dataclass(frozen=True)
class ExecutionEventSignal:
    event_type: str
    data: dict[str, Any]
    occurred_at: str


@workflow.defn(name="ConversationExecutionWorkflow")
class ConversationExecutionWorkflow:
    """Durable execution responsibility; model dispatch remains outside WC034-09."""

    def __init__(self) -> None:
        self._input: ConversationExecutionInput | None = None
        self._state = "ACCEPTED"
        self._partial = False
        self._completion_reason: str | None = None
        self._terminal = False
        self._updated_at: str | None = None
        self._events: list[dict[str, Any]] = []
        self._cancellation_requests: dict[str, str] = {}

    def _append_event(
        self,
        event_type: str,
        data: dict[str, Any],
        occurred_at: str,
    ) -> None:
        if self._input is None:
            return
        sequence = len(self._events) + 1
        self._events.append(
            {
                "schemaVersion": self._input.schema_version,
                "eventId": f"{self._input.execution_id}:{sequence}",
                "eventType": event_type,
                "conversationId": self._input.conversation_id,
                "executionId": self._input.execution_id,
                "messageId": self._input.message_id,
                "sequence": sequence,
                "occurredAt": occurred_at,
                "data": data,
            }
        )
        self._updated_at = occurred_at

    @workflow.signal(name="CancelConversationExecution")
    async def cancel(self, signal: CancellationSignal) -> None:
        prior_hash = self._cancellation_requests.get(signal.idempotency_key)
        if prior_hash is not None:
            return
        self._cancellation_requests[signal.idempotency_key] = signal.request_hash
        if self._state == "STOPPED" or self._terminal:
            return
        self._state = "CANCELLED"
        self._partial = any(event["eventType"] == "response.delta" for event in self._events)
        self._completion_reason = "CANCELLED"
        self._terminal = True
        self._append_event(
            "execution.cancelled",
            {
                "state": self._state,
                "partial": self._partial,
                "completionReason": self._completion_reason,
            },
            signal.requested_at,
        )

    @workflow.signal(name="EmergencyStop")
    async def emergency_stop(self, stopped_at: str | None = None) -> None:
        if self._state == "STOPPED":
            return
        effective_stopped_at = stopped_at or workflow.now().isoformat()
        self._state = "STOPPED"
        self._partial = any(event["eventType"] == "response.delta" for event in self._events)
        self._completion_reason = "EMERGENCY_STOPPED"
        self._terminal = True
        self._append_event(
            "execution.stopped",
            {
                "state": self._state,
                "partial": self._partial,
                "completionReason": self._completion_reason,
            },
            effective_stopped_at,
        )

    @workflow.signal(name="AppendConversationExecutionEvent")
    async def append_event(self, signal: ExecutionEventSignal) -> None:
        if not self._terminal:
            self._append_event(signal.event_type, signal.data, signal.occurred_at)

    @workflow.query(name="GetConversationExecutionState")
    def state(self) -> dict[str, Any]:
        return {
            "schemaVersion": self._input.schema_version if self._input is not None else "1.0",
            "executionId": self._input.execution_id if self._input is not None else None,
            "conversationId": self._input.conversation_id if self._input is not None else None,
            "messageId": self._input.message_id if self._input is not None else None,
            "tenantId": self._input.tenant_id if self._input is not None else None,
            "relationshipId": self._input.relationship_id if self._input is not None else None,
            "delegatedActorId": self._input.delegated_actor_id if self._input is not None else None,
            "participantRole": self._input.participant_role if self._input is not None else None,
            "state": self._state,
            "partial": self._partial,
            "completionReason": self._completion_reason,
            "requestHash": self._input.request_hash if self._input is not None else None,
            "acceptedAt": self._input.accepted_at if self._input is not None else None,
            "updatedAt": self._updated_at,
            "cancellationRequests": dict(self._cancellation_requests),
        }

    @workflow.query(name="GetConversationExecutionEvents")
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    @workflow.run
    async def run(self, execution_input: ConversationExecutionInput) -> dict[str, Any]:
        self._input = execution_input
        self._updated_at = execution_input.accepted_at
        self._append_event(
            "execution.accepted",
            {"serverTime": execution_input.accepted_at},
            execution_input.accepted_at,
        )
        await workflow.wait_condition(lambda: self._terminal)
        return self.state()
