from __future__ import annotations

import asyncio
import uuid
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Replayer, Worker

from workflows.conversation_execution_workflow import (
    ConversationExecutionInput,
    ConversationExecutionWorkflow,
    ExecutionEventSignal,
)


@workflow.defn(name="ConversationExecutionWorkflow")
class PreHeartbeatConversationExecutionWorkflow(ConversationExecutionWorkflow):
    """Generate the original dispatch commands without the heartbeat patch marker."""

    @workflow.run
    async def run(self, execution_input: ConversationExecutionInput) -> dict:
        self._input = execution_input
        self._updated_at = execution_input.accepted_at
        self._append_event(
            "execution.accepted",
            {"serverTime": execution_input.accepted_at},
            execution_input.accepted_at,
        )
        self._dispatch_task = workflow.start_activity(
            "DispatchConversationEmploymentProposal",
            execution_input,
            start_to_close_timeout=timedelta(seconds=60),
            schedule_to_close_timeout=timedelta(minutes=10),
            retry_policy=RetryPolicy(maximum_attempts=3),
            cancellation_type=workflow.ActivityCancellationType.TRY_CANCEL,
        )
        await self._dispatch_task
        await workflow.wait_condition(lambda: self._terminal)
        return self.state()


async def test_real_temporal_replays_pre_heartbeat_dispatch_history() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as environment:

        @activity.defn(name="DispatchConversationEmploymentProposal")
        async def dispatch(execution: ConversationExecutionInput) -> None:
            await environment.client.get_workflow_handle(execution.execution_id).signal(
                "AppendConversationExecutionEvent",
                ExecutionEventSignal(
                    "execution.completed",
                    {"state": "COMPLETED", "partial": False, "completionReason": "COMPLETE"},
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        execution_id = str(uuid.uuid4())
        execution = ConversationExecutionInput(
            "1.0",
            execution_id,
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "original-request-hash",
            datetime.now(timezone.utc).isoformat(),
            {"body": {}},
        )
        queue = f"wc134-pre-heartbeat-{execution_id}"
        async with Worker(
            environment.client,
            task_queue=queue,
            workflows=[PreHeartbeatConversationExecutionWorkflow],
            activities=[dispatch],
        ):
            handle = await environment.client.start_workflow(
                "ConversationExecutionWorkflow",
                execution,
                id=execution_id,
                task_queue=queue,
            )
            assert (await handle.result())["state"] == "COMPLETED"
        history = await handle.fetch_history()
        await Replayer(workflows=[ConversationExecutionWorkflow]).replay_workflow(history)


async def test_real_temporal_retries_dispatch_and_replays_stopped_history() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        attempts = []
        client: Client = environment.client

        @activity.defn(name="DispatchConversationEmploymentProposal")
        async def dispatch(execution: ConversationExecutionInput) -> None:
            attempts.append(execution.request_hash)
            activity.heartbeat()
            if len(attempts) == 1:
                raise ApplicationError("Transient dispatch failure")
            await client.get_workflow_handle(execution.execution_id).signal(
                "AppendConversationExecutionEvent",
                ExecutionEventSignal(
                    "card.proposed",
                    {"cardId": "persisted-result"},
                    datetime.now(timezone.utc).isoformat(),
                    f"employment-proposal:{execution.execution_id}",
                ),
            )

        execution_id = str(uuid.uuid4())
        queue = f"wc134-dispatch-{execution_id}"
        execution = ConversationExecutionInput(
            "1.0",
            execution_id,
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "original-request-hash",
            datetime.now(timezone.utc).isoformat(),
            {"body": {}},
        )
        async with Worker(client, task_queue=queue, workflows=[ConversationExecutionWorkflow], activities=[dispatch]):
            handle = await client.start_workflow(
                ConversationExecutionWorkflow.run,
                execution,
                id=execution_id,
                task_queue=queue,
            )

            async def await_result() -> None:
                while True:
                    events = await handle.query("GetConversationExecutionEvents")
                    if any(event["eventType"] == "card.proposed" for event in events):
                        return
                    await asyncio.sleep(0.05)

            await asyncio.wait_for(await_result(), 30)
            await handle.signal("EmergencyStop")
            result = await handle.result()
            assert result["state"] == "STOPPED"
            assert attempts == ["original-request-hash", "original-request-hash"]
        history = await handle.fetch_history()
        await Replayer(workflows=[ConversationExecutionWorkflow]).replay_workflow(history)


async def test_real_temporal_accepts_and_replays_legacy_input_without_dispatch() -> None:
    async with await WorkflowEnvironment.start_time_skipping() as environment:
        execution_id = str(uuid.uuid4())
        execution = ConversationExecutionInput(
            "1.0",
            execution_id,
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            "tenant-a",
            "relationship-a",
            "participant-a",
            "CUSTOMER",
            str(uuid.uuid4()),
            "sha256:" + "11" * 32,
            1,
            "en-IN",
            {"text": "x"},
            None,
            "original-request-hash",
            datetime.now(timezone.utc).isoformat(),
        )
        legacy_payload = asdict(execution)
        del legacy_payload["dispatch"]
        queue = f"wc134-legacy-{execution_id}"
        async with Worker(environment.client, task_queue=queue, workflows=[ConversationExecutionWorkflow]):
            handle = await environment.client.start_workflow(
                "ConversationExecutionWorkflow",
                legacy_payload,
                id=execution_id,
                task_queue=queue,
            )
            await handle.signal("EmergencyStop")
            result = await handle.result()
            assert result["state"] == "STOPPED"
        await Replayer(workflows=[ConversationExecutionWorkflow]).replay_workflow(await handle.fetch_history())
