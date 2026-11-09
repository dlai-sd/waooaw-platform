"""Temporal activity for dispatching one durably accepted conversation request."""

# Implements: architecture/reference/components/conversation-core.md §4.1 WC-134 Professional Generation Contract
# Constitutional basis: C-023, C-059, C-063

from __future__ import annotations

import asyncio
import uuid
from contextlib import suppress

from fastapi import FastAPI, Request
from temporalio import activity

from routers.conversation_execution import (
    BPServiceContext,
    ExecutionStoppedDuringDispatchError,
    _dispatch_employment_proposal,
    _dispatch_batch_execution,
    _execution_id,
    _batch_request_hash,
    _request_hash,
)
from routers.conversation_models import StartBatchExecutionRequestV1, StartExecutionRequestV1
from workflows.conversation_execution_workflow import ConversationExecutionInput


class ConversationDispatchActivity:
    def __init__(self, application: FastAPI) -> None:
        self._application = application

    @activity.defn(name="DispatchConversationEmploymentProposal")
    async def dispatch(self, execution: ConversationExecutionInput) -> None:
        payload = execution.dispatch
        temporal = self._application.state.temporal_client
        gateway = self._application.state.conversation_constitutional_gateway
        if payload is None or temporal is None or gateway is None:
            raise RuntimeError("Conversation dispatch dependencies unavailable")
        is_batch = payload.get("kind") == "batch"
        if is_batch:
            body: StartBatchExecutionRequestV1 | StartExecutionRequestV1 = StartBatchExecutionRequestV1.model_validate(
                payload["body"]
            )
        else:
            body = StartExecutionRequestV1.model_validate(payload["body"])
        context = BPServiceContext(
            contract_id=payload["contractId"],
            tenant_id=execution.tenant_id,
            relationship_id=execution.relationship_id,
            delegated_actor_id=execution.delegated_actor_id,
            participant_role=execution.participant_role,
            message_id=execution.message_id,
        )
        conversation_id = uuid.UUID(execution.conversation_id)
        idempotency_key = uuid.UUID(payload["idempotencyKey"])
        if isinstance(body, StartBatchExecutionRequestV1):
            first_mandate = body.sources[0].operational_mandate
            first_message_id = body.sources[0].message_id
            calculated_hash = _batch_request_hash(body, conversation_id, context)
            batch_identity_matches = (
                str(body.batch_id) == execution.batch_id and body.source_list_digest == execution.source_list_digest
            )
        else:
            first_mandate = body.operational_mandate
            first_message_id = body.message_id
            calculated_hash = _request_hash(body, conversation_id, context)
            batch_identity_matches = execution.batch_id is None and execution.source_list_digest is None
        if (
            str(first_message_id) != execution.message_id
            or str(first_mandate.mandate_id) != execution.mandate_id
            or first_mandate.mandate_digest != execution.mandate_digest
            or body.decision_space_version != execution.decision_space_version
            or calculated_hash != execution.request_hash
            or str(_execution_id(context, conversation_id, idempotency_key)) != execution.execution_id
            or not batch_identity_matches
        ):
            raise ValueError("Durable conversation dispatch identity mismatch")
        request = Request({"type": "http", "app": self._application, "headers": []})
        heartbeat_task = None
        heartbeat_timeout = activity.info().heartbeat_timeout if activity.in_activity() else None
        if heartbeat_timeout is not None:
            heartbeat_task = asyncio.create_task(self._heartbeat(heartbeat_timeout.total_seconds() / 2))
        try:
            if isinstance(body, StartBatchExecutionRequestV1):
                await _dispatch_batch_execution(
                    request,
                    temporal,
                    uuid.UUID(execution.execution_id),
                    body,
                    context,
                    idempotency_key,
                    uuid.UUID(payload["correlationId"]),
                    gateway,
                    conversation_id,
                    execution.request_hash,
                    reconcile_only=payload.get("operationPolicyVersion") != "1.0",
                )
            else:
                await _dispatch_employment_proposal(
                    request,
                    temporal,
                    uuid.UUID(execution.execution_id),
                    body,
                    context,
                    idempotency_key,
                    uuid.UUID(payload["correlationId"]),
                    gateway,
                    conversation_id,
                    execution.request_hash,
                    reconcile_only=payload.get("operationPolicyVersion") != "1.0",
                )
        except ExecutionStoppedDuringDispatchError:
            return
        finally:
            if heartbeat_task is not None:
                heartbeat_task.cancel()
                with suppress(asyncio.CancelledError):
                    await heartbeat_task

    @staticmethod
    async def _heartbeat(interval: float) -> None:
        while True:
            activity.heartbeat()
            await asyncio.sleep(interval)
