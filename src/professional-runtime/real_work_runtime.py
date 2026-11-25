"""Composition of the real-work execution path: CE stop barrier and step gate, BP timeline sink, optional spend chain."""

# Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R011 (C1, C2)
# Constitutional basis: C-001, C-005, C-023, C-059, C-063
# IB: IB-171

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from execution_timeline import (
    BarrierDecision,
    ExecutionTimeline,
    SpendHook,
    TimelineSink,
)
from routers.conversation_execution import ConstitutionalDecision

PROBE_ACTION = "CONVERSATION_EXECUTION"


class ActionValidator(Protocol):
    async def validate_action(
        self,
        *,
        contract_id: str,
        tenant_id: str,
        action_type: str,
        parameters: dict[str, str],
        decision_space_version: int,
    ) -> ConstitutionalDecision: ...


@dataclass(frozen=True)
class RunContext:
    """What the Constitutional Engine needs to answer for one running employment contract."""

    contract_id: str
    tenant_id: UUID
    decision_space_version: int
    delegated_actor_id: str


class CeStopBarrier:
    """The durable stop owner. CE answers STOP for any step of a stopped contract, from any replica, after any restart."""

    def __init__(self, validator: ActionValidator, run: RunContext) -> None:
        self._validator = validator
        self._run = run

    async def decide(self, tenant_id: UUID, relationship_id: UUID) -> BarrierDecision:
        if tenant_id != self._run.tenant_id:
            return BarrierDecision.BLOCKED
        decision = await self._validator.validate_action(
            contract_id=self._run.contract_id,
            tenant_id=str(tenant_id),
            action_type=PROBE_ACTION,
            parameters={
                "conversation_id": str(relationship_id),
                "relationship_id": str(relationship_id),
                "delegated_actor_id": self._run.delegated_actor_id,
                "request_hash": "real-work-stop-probe",
            },
            decision_space_version=self._run.decision_space_version,
        )
        if decision is ConstitutionalDecision.ALLOW:
            return BarrierDecision.CLEAR
        if decision is ConstitutionalDecision.STOPPED:
            return BarrierDecision.STOPPED
        return BarrierDecision.BLOCKED


class CeStepGate:
    """CE validation before every consequential step; the artifact binding travels as the action parameters."""

    def __init__(self, validator: ActionValidator, run: RunContext) -> None:
        self._validator = validator
        self._run = run

    async def validate(self, action_type: str, parameters: dict[str, str]) -> None:
        decision = await self._validator.validate_action(
            contract_id=self._run.contract_id,
            tenant_id=str(self._run.tenant_id),
            action_type=action_type,
            parameters=parameters,
            decision_space_version=self._run.decision_space_version,
        )
        if decision is not ConstitutionalDecision.ALLOW:
            raise PermissionError(f"constitutional engine answered {decision.value}")


def timeline_for_run(
    validator: ActionValidator, sink: TimelineSink, run: RunContext, spend: SpendHook | None = None
) -> ExecutionTimeline:
    """A timeline whose stop fence is the durable one, so a second replica or a restart cannot forget a stop."""
    return ExecutionTimeline(sink=sink, gate=CeStepGate(validator, run), barrier=CeStopBarrier(validator, run), spend=spend)
