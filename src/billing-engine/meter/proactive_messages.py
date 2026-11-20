# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-12
# Constitutional basis: C-059, C-088, C-089, C-063
"""Proactive-message accounting: classify an outbound message and count it against the package (C4-12).

Every subscription includes the PROACTIVE_MESSAGE component (the quantity is versioned package data, 30 per
period). Only an agent alert, reminder or narrative sent outside the customer-service window counts. Capacity
notices and emergency alerts never count and never block; their cost is recorded on the PLATFORM FLOOR.
When the included quantity is used up, or the relationship has no package (a trial has no allowance), the
caller delivers in the portal and the next turn instead.

This module only classifies and counts when a caller asks; it does not enable sending. The WC-134 release
policy still refuses proactive messages in the business platform.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Protocol
from uuid import NAMESPACE_URL, UUID, uuid5

from markup.package_models import PROACTIVE_MESSAGE_COMPONENT_ID
from meter.component_units import (
    COMPONENT_EXHAUSTED,
    COMPONENT_UNKNOWN,
    ComponentUnitError,
    ComponentUnitService,
)

PROACTIVE_COUNTED: Final = "PROACTIVE_COUNTED"
PROACTIVE_UNCOUNTED: Final = "PROACTIVE_UNCOUNTED"
REPLY: Final = "REPLY"

COUNTED_STATUS: Final = "COUNTED"
NOT_COUNTED_STATUS: Final = "NOT_COUNTED"
ALLOWANCE_EXHAUSTED: Final = "PROACTIVE_ALLOWANCE_EXHAUSTED"
NO_ALLOWANCE: Final = "PROACTIVE_NO_ALLOWANCE"

FLOOR_PURPOSE: Final = "PROACTIVE_UNCOUNTED"


class FloorRecorder(Protocol):
    """The PLATFORM FLOOR use recorder (``PlatformAccounts.record_floor_use``)."""

    async def record_floor_use(
        self,
        tenant_id: UUID,
        environment: str,
        purpose: str,
        component_id: str,
        paise: int,
        evidence_id: UUID,
        *,
        invocation_id: UUID | None = None,
        use_id: UUID | None = None,
    ) -> object: ...


@dataclass(frozen=True)
class ProactiveDecision:
    message_class: str
    status: str
    quantity: int | None
    used: int | None
    remaining: int | None
    deliver_in_portal: bool
    floor_recorded: bool = False


def classify_message(
    *, inside_service_window: bool, capacity_notice: bool = False, emergency_alert: bool = False
) -> str:
    """Classify an outbound message.

    A message inside an open customer-service window is a REPLY and needs no template. Outside it, a capacity
    notice or emergency alert is PROACTIVE_UNCOUNTED and every other message is PROACTIVE_COUNTED.
    """
    if inside_service_window:
        return REPLY
    if capacity_notice or emergency_alert:
        return PROACTIVE_UNCOUNTED
    return PROACTIVE_COUNTED


class ProactiveMessageAccounting:
    def __init__(self, components: ComponentUnitService, floor: FloorRecorder) -> None:
        self._components = components
        self._floor = floor

    async def account(
        self,
        tenant_id: UUID,
        relationship_id: UUID,
        message_class: str,
        evidence_id: UUID,
        *,
        environment: str = "production",
        floor_paise: int = 0,
    ) -> ProactiveDecision:
        """Account one outbound message; repeating the same evidence id changes nothing."""
        if message_class == REPLY:
            return ProactiveDecision(message_class, NOT_COUNTED_STATUS, None, None, None, deliver_in_portal=False)
        if message_class == PROACTIVE_UNCOUNTED:
            receipt = await self._floor.record_floor_use(
                tenant_id,
                environment,
                FLOOR_PURPOSE,
                PROACTIVE_MESSAGE_COMPONENT_ID,
                floor_paise,
                evidence_id,
                use_id=uuid5(NAMESPACE_URL, f"proactive-floor:{relationship_id}:{evidence_id}"),
            )
            return ProactiveDecision(
                message_class,
                NOT_COUNTED_STATUS,
                None,
                None,
                None,
                deliver_in_portal=False,
                floor_recorded=bool(getattr(receipt, "recorded", False)),
            )
        if message_class != PROACTIVE_COUNTED:
            raise ComponentUnitError("PROACTIVE_CLASS_INVALID", message_class)
        key = uuid5(NAMESPACE_URL, f"proactive-count:{relationship_id}:{evidence_id}")
        try:
            receipt = await self._components.consume(
                tenant_id, relationship_id, PROACTIVE_MESSAGE_COMPONENT_ID, evidence_id, key, paced=False
            )
        except ComponentUnitError as error:
            if error.code == COMPONENT_EXHAUSTED:
                return ProactiveDecision(message_class, ALLOWANCE_EXHAUSTED, None, None, 0, deliver_in_portal=True)
            if error.code == COMPONENT_UNKNOWN:
                return ProactiveDecision(message_class, NO_ALLOWANCE, None, None, None, deliver_in_portal=True)
            raise
        return ProactiveDecision(
            message_class,
            COUNTED_STATUS,
            receipt.quantity,
            receipt.used,
            receipt.remaining,
            deliver_in_portal=False,
        )
