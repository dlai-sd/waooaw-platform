# Implements: architecture/reference/components/professional-runtime.md §6 Conversation Execution Coordinator
# constitutional_basis: C-001, C-023, C-025, C-059; ADR-015, ADR-018, ADR-031
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError


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
    mandate_id: str
    mandate_digest: str
    decision_space_version: int
    locale: str
    content: dict[str, Any]
    active_goal_context_id: str | None
    request_hash: str
    accepted_at: str
    dispatch: dict[str, Any] | None = None
    batch_id: str | None = None
    source_list_digest: str | None = None


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
    dispatch_result_key: str | None = None


@workflow.defn(name="ConversationExecutionWorkflow")
class ConversationExecutionWorkflow:
    """Durable execution responsibility and bounded proposal dispatch."""

    def __init__(self) -> None:
        self._input: ConversationExecutionInput | None = None
        self._state = "ACCEPTED"
        self._partial = False
        self._completion_reason: str | None = None
        self._terminal = False
        self._updated_at: str | None = None
        self._events: list[dict[str, Any]] = []
        self._pending_events: list[tuple[str, dict[str, Any], str]] = []
        self._cancellation_requests: dict[str, str] = {}
        self._dispatch_results: dict[str, tuple[str, dict[str, Any]]] = {}
        self._dispatch_task: Any = None

    def _append_event(
        self,
        event_type: str,
        data: dict[str, Any],
        occurred_at: str,
    ) -> None:
        if self._input is None:
            self._pending_events.append((event_type, data, occurred_at))
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
        if self._dispatch_task is not None:
            self._dispatch_task.cancel()
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
        if self._dispatch_task is not None:
            self._dispatch_task.cancel()
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
        if self._terminal or self._input is None:
            return
        if signal.dispatch_result_key == f"legacy-dispatch-reconciliation:{self._input.execution_id}" and any(
            event["eventType"] in {"card.proposed", "reconciliation.required"} for event in self._events
        ):
            return
        if signal.dispatch_result_key is not None:
            result = (signal.event_type, signal.data)
            prior = self._dispatch_results.get(signal.dispatch_result_key)
            if prior is not None:
                if prior == result:
                    return
                if prior[0] == "card.proposed" and signal.event_type == "reconciliation.required":
                    return
                if prior[0] != "reconciliation.required" or signal.event_type != "card.proposed":
                    self._append_event(
                        "reconciliation.required",
                        {"reason": "STATE_CONFLICT"},
                        signal.occurred_at,
                    )
                    return
            self._dispatch_results[signal.dispatch_result_key] = result
        terminal_states = {
            "execution.completed": ("COMPLETED", "COMPLETE"),
            "execution.failed": ("FAILED", "PARTIAL_FAILURE"),
        }
        terminal = terminal_states.get(signal.event_type)
        if terminal is not None:
            state, reason = terminal
            if (
                signal.data.get("state") != state
                or signal.data.get("completionReason") != reason
                or not isinstance(signal.data.get("partial"), bool)
            ):
                self._append_event(
                    "reconciliation.required",
                    {"reason": "STATE_CONFLICT"},
                    signal.occurred_at,
                )
                return
            self._state = state
            self._partial = signal.data["partial"]
            self._completion_reason = reason
            self._terminal = True
        elif signal.event_type in {"processing.started", "response.delta"}:
            self._state = "RUNNING"
        elif signal.event_type in {"execution.cancelled", "execution.stopped"}:
            self._append_event(
                "reconciliation.required",
                {"reason": "STATE_CONFLICT"},
                signal.occurred_at,
            )
            return
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
            "mandateId": self._input.mandate_id if self._input is not None else None,
            "mandateDigest": self._input.mandate_digest if self._input is not None else None,
            "decisionSpaceVersion": self._input.decision_space_version if self._input is not None else None,
            "state": self._state,
            "partial": self._partial,
            "completionReason": self._completion_reason,
            "requestHash": self._input.request_hash if self._input is not None else None,
            "batchId": self._input.batch_id if self._input is not None else None,
            "sourceListDigest": self._input.source_list_digest if self._input is not None else None,
            "legacyDispatchNeedsReconciliation": (
                self._input is not None
                and self._input.dispatch is None
                and not self._terminal
                and not any(event["eventType"] == "card.proposed" for event in self._events)
            ),
            "dispatchNeedsReconciliation": (
                not self._terminal
                and any(event["eventType"] == "reconciliation.required" for event in self._events)
                and not any(event["eventType"] == "card.proposed" for event in self._events)
            ),
            "dispatchNeedsCompletion": (
                not self._terminal and any(event["eventType"] in {"card.proposed", "response.system"} for event in self._events)
            ),
            "acceptedAt": self._input.accepted_at if self._input is not None else None,
            "updatedAt": self._updated_at,
            "cancellationRequests": dict(self._cancellation_requests),
        }

    @workflow.query(name="GetConversationExecutionEvents")
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    @workflow.query(name="GetConversationExecutionTerminalSnapshot")
    def terminal_snapshot(self) -> dict[str, Any]:
        return {
            "state": self.state(),
            "events": list(self._events) if self._terminal else [],
        }

    @workflow.query(name="GetConversationGenerationRecoverySource")
    def generation_recovery_source(self) -> dict[str, Any]:
        return {
            "state": self.state(),
            "events": list(self._events),
            "dispatch": self._input.dispatch if self._input is not None else None,
        }

    @workflow.run
    async def run(self, execution_input: ConversationExecutionInput) -> dict[str, Any]:
        self._input = execution_input
        self._updated_at = execution_input.accepted_at
        self._append_event(
            "execution.accepted",
            {"serverTime": execution_input.accepted_at},
            execution_input.accepted_at,
        )
        for event_type, data, occurred_at in self._pending_events:
            self._append_event(event_type, data, occurred_at)
        self._pending_events.clear()
        if execution_input.dispatch is not None and not self._terminal:
            self._dispatch_task = workflow.start_activity(
                "DispatchConversationEmploymentProposal",
                execution_input,
                start_to_close_timeout=timedelta(seconds=60),
                schedule_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=(timedelta(seconds=6) if workflow.patched("wc134-dispatch-heartbeats") else None),
                retry_policy=RetryPolicy(maximum_attempts=3),
                cancellation_type=workflow.ActivityCancellationType.TRY_CANCEL,
            )
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                if not self._terminal:
                    raise
            except ActivityError:
                if not self._terminal and f"employment-proposal:{execution_input.execution_id}" not in self._dispatch_results:
                    self._append_event(
                        "reconciliation.required",
                        {"reason": "STATE_CONFLICT"},
                        workflow.now().isoformat(),
                    )
        await workflow.wait_condition(lambda: self._terminal)
        return self.state()
