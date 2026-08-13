# Implements: architecture/reference/components/constitutional-engine.md §ValidateAction
# constitutional_basis: C-023, C-041, C-059, C-099; ADR-001, ADR-031
"""Fail-closed Constitutional Engine adapter for Billing pricing actions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import grpc

from config import Settings


class ConstitutionalValidationError(RuntimeError):
    """Raised when CE cannot affirmatively authorize a Billing action."""


class ConstitutionalEngineValidator:
    """Validate Billing actions over the canonical CE gRPC contract."""

    def __init__(
        self,
        settings: Settings,
        *,
        channel: Any | None = None,
        stub: Any | None = None,
        protobuf: Any | None = None,
    ) -> None:
        self._settings = settings
        self._channel = channel
        self._stub = stub
        self._protobuf = protobuf

    def _load_contract(self) -> tuple[Any, Any]:
        if self._stub is None or self._protobuf is None:
            if self._channel is None:
                self._channel = grpc.aio.insecure_channel(
                    self._settings.CONSTITUTIONAL_ENGINE_ADDRESS
                )
            local_proto = Path(__file__).parent / "proto" / "constitutional_service.proto"
            repository_proto = (
                Path(__file__).parents[2]
                / "architecture"
                / "reference"
                / "proto"
                / "constitutional_service.proto"
            )
            proto_path = local_proto if local_proto.is_file() else repository_proto
            protobuf, protobuf_grpc = grpc.protos_and_services(str(proto_path))
            self._protobuf = protobuf
            self._stub = protobuf_grpc.ConstitutionalServiceStub(self._channel)
        return self._protobuf, self._stub

    async def validate_action(self, action: str) -> None:
        """Require an affirmative CE decision before the Billing action proceeds."""
        protobuf, stub = self._load_contract()
        dcm_category = (
            protobuf.DCM_CATEGORY_DETERMINISTIC_REQUIRED
            if action.endswith(".write")
            else protobuf.DCM_CATEGORY_CONSISTENT_SUFFICIENT
        )
        request = protobuf.ValidateActionRequest(
            contract_id=self._settings.BILLING_CONTRACT_ID,
            action_type=action,
            action_parameters=json.dumps({}, separators=(",", ":")),
            decision_space_version=self._settings.BILLING_DECISION_SPACE_VERSION,
            approval_type=protobuf.APPROVAL_TYPE_PRE_AUTHORIZED,
            dcm_category=dcm_category,
        )
        try:
            response = await stub.ValidateAction(
                request,
                timeout=self._settings.CONSTITUTIONAL_ENGINE_TIMEOUT_SECONDS,
            )
        except Exception as error:
            raise ConstitutionalValidationError("CE validation unavailable") from error

        if (
            response.decision != protobuf.VALIDATION_DECISION_ALLOW
            or not str(response.constitutional_basis).strip()
        ):
            raise ConstitutionalValidationError("CE denied Billing action")


CE = ConstitutionalEngineValidator(Settings())