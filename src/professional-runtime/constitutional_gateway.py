# Implements: architecture/reference/components/conversation-core.md §4 Internal PR Execution and Stream Contract
# constitutional_basis: C-001, C-023, C-041, C-059, C-063; ADR-001, ADR-031
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import timezone
from pathlib import Path
from typing import Any

import grpc
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

from routers.conversation_execution import (
    BPServiceContext,
    ConstitutionalDecision,
    ConstitutionalGatewayUnavailableError,
)


@dataclass(frozen=True)
class EmergencyStopResult:
    emergency_stop_record_id: str
    affected_sessions: tuple[str, ...]
    recorded_at: str


class GrpcConversationConstitutionalGateway:
    """Fail-closed CE readiness and execution authorization over canonical gRPC."""

    def __init__(
        self,
        address: str,
        *,
        timeout_seconds: float = 2.0,
        channel: Any | None = None,
        stub: Any | None = None,
        protobuf: Any | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._channel = channel or grpc.aio.insecure_channel(address)
        self._stub = stub
        self._protobuf = protobuf

    def _load_contract(self) -> tuple[Any, Any]:
        if self._stub is None or self._protobuf is None:
            proto_path = Path(__file__).parent / "proto" / "constitutional_service.proto"
            protobuf, protobuf_grpc = grpc.protos_and_services(str(proto_path))
            self._protobuf = protobuf
            self._stub = protobuf_grpc.ConstitutionalServiceStub(self._channel)
        return self._protobuf, self._stub

    @staticmethod
    def _health_contract() -> tuple[type[Any], type[Any]]:
        file_descriptor = descriptor_pb2.FileDescriptorProto(
            name="grpc/health/v1/health.proto",
            package="grpc.health.v1",
            syntax="proto3",
        )
        request = file_descriptor.message_type.add(name="HealthCheckRequest")
        request.field.add(
            name="service",
            number=1,
            label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
            type=descriptor_pb2.FieldDescriptorProto.TYPE_STRING,
        )
        response = file_descriptor.message_type.add(name="HealthCheckResponse")
        status = response.enum_type.add(name="ServingStatus")
        for name, number in (
            ("UNKNOWN", 0),
            ("SERVING", 1),
            ("NOT_SERVING", 2),
            ("SERVICE_UNKNOWN", 3),
        ):
            status.value.add(name=name, number=number)
        response.field.add(
            name="status",
            number=1,
            label=descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL,
            type=descriptor_pb2.FieldDescriptorProto.TYPE_ENUM,
            type_name=".grpc.health.v1.HealthCheckResponse.ServingStatus",
        )
        pool = descriptor_pool.DescriptorPool()
        pool.Add(file_descriptor)
        return (
            message_factory.GetMessageClass(pool.FindMessageTypeByName("grpc.health.v1.HealthCheckRequest")),
            message_factory.GetMessageClass(pool.FindMessageTypeByName("grpc.health.v1.HealthCheckResponse")),
        )

    async def is_ready(self) -> bool:
        request_type, response_type = self._health_contract()
        health_check = self._channel.unary_unary(
            "/grpc.health.v1.Health/Check",
            request_serializer=request_type.SerializeToString,
            response_deserializer=response_type.FromString,
        )
        try:
            response = await health_check(request_type(service=""), timeout=self._timeout_seconds)
        except (grpc.RpcError, TimeoutError, asyncio.TimeoutError):
            return False
        return bool(response.status == 1)

    async def authorize_execution(
        self,
        context: BPServiceContext,
        conversation_id: Any,
        decision_space_version: int,
        request_hash: str,
    ) -> ConstitutionalDecision:
        try:
            protobuf, stub = self._load_contract()
            request = protobuf.ValidateActionRequest(
                contract_id=context.contract_id,
                action_type="CONVERSATION_EXECUTION",
                action_parameters=json.dumps(
                    {
                        "conversation_id": str(conversation_id),
                        "relationship_id": context.relationship_id,
                        "delegated_actor_id": context.delegated_actor_id,
                        "request_hash": request_hash,
                    },
                    separators=(",", ":"),
                    sort_keys=True,
                ),
                decision_space_version=decision_space_version,
                approval_type=protobuf.APPROVAL_TYPE_PRE_AUTHORIZED,
            )
            response = await stub.ValidateAction(
                request,
                metadata=(("x-tenant-id", context.tenant_id),),
                timeout=self._timeout_seconds,
            )
        except Exception as error:
            raise ConstitutionalGatewayUnavailableError from error
        decision_name = protobuf.ValidationDecision.Name(response.decision).removeprefix("VALIDATION_DECISION_")
        reason = str(response.reason).upper()
        if decision_name == "ALLOW" and str(response.constitutional_basis).strip():
            return ConstitutionalDecision.ALLOW
        if "STOP" in reason:
            return ConstitutionalDecision.STOPPED
        if "STALE" in reason or "DECISION_SPACE" in reason:
            return ConstitutionalDecision.STALE
        return ConstitutionalDecision.DENY

    async def trigger_emergency_stop(
        self,
        *,
        contract_id: str,
        tenant_id: str,
        stopped_by: str,
        active_session_ids: list[str],
    ) -> EmergencyStopResult:
        try:
            protobuf, stub = self._load_contract()
            response = await stub.TriggerEmergencyStop(
                protobuf.EmergencyStopRequest(
                    contract_id=contract_id,
                    stopped_by=stopped_by,
                    active_session_ids=active_session_ids,
                ),
                metadata=(("x-tenant-id", tenant_id),),
                timeout=min(self._timeout_seconds, 0.2),
            )
            recorded_at = response.recorded_at.ToDatetime(tzinfo=timezone.utc)
        except Exception as error:
            raise ConstitutionalGatewayUnavailableError from error
        if not response.emergency_stop_record_id or recorded_at is None:
            raise ConstitutionalGatewayUnavailableError
        return EmergencyStopResult(
            emergency_stop_record_id=str(response.emergency_stop_record_id),
            affected_sessions=tuple(str(session_id) for session_id in response.affected_sessions),
            recorded_at=recorded_at.isoformat().replace("+00:00", "Z"),
        )

    async def close(self) -> None:
        await self._channel.close()
