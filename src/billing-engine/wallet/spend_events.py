# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-11
# Constitutional basis: C-059, C-063, C-088
"""Spend events and metrics per account class (WC-136 C4-11).

Every field is an identifier, a class, an amount or a reason code. Pseudonymous references (campaign and
lead) are accepted only in an opaque token shape; anything that could be a phone number, an e-mail
address, a name or free text is dropped rather than logged (C-063). Recording never fails the request
it describes.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Final
from uuid import UUID

from wallet import metrics

SPEND_RESERVED: Final = "spend_reserved"
SPEND_SETTLED: Final = "spend_settled"
SPEND_RELEASED: Final = "spend_released"
SPEND_DENIED: Final = "spend_denied"
SPEND_EVENTS: Final = frozenset({SPEND_RESERVED, SPEND_SETTLED, SPEND_RELEASED, SPEND_DENIED})

SPEND_PAISE_METRIC: Final = "waooaw_spend_paise_total"
SPEND_DENIED_METRIC: Final = "waooaw_spend_denied_total"
PARITY_DIFFERENCE_METRIC: Final = "waooaw_wallet_parity_difference"
LIVE_MARGIN_BREACH_METRIC: Final = "waooaw_live_margin_floor_breach"

_logger = logging.getLogger("waooaw.spend")
_TOKEN = re.compile(r"[A-Za-z0-9_.:-]{1,64}")
_PHONE_LIKE = re.compile(r"\+?[0-9][0-9 ()-]{6,}")
_UUID_SHAPE = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_REASON = re.compile(r"[A-Z][A-Z0-9_]{1,63}")


def _token(value: object) -> str | None:
    """An opaque identifier, or None when the value could carry personal data."""
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, str) and _UUID_SHAPE.fullmatch(value):
        return value
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None or _PHONE_LIKE.fullmatch(value):
        return None
    return value


@dataclass(frozen=True)
class SpendEvent:
    event: str
    account_class: str
    tenant_id: str
    paise: int
    reason_code: str
    relationship_id: str | None = None
    skill_id: str | None = None
    component_id: str | None = None
    campaign_ref: str | None = None
    lead_ref: str | None = None

    def fields(self) -> dict[str, object]:
        body: dict[str, object] = {
            "event": self.event,
            "accountClass": self.account_class,
            "tenantId": self.tenant_id,
            "paise": self.paise,
            "reasonCode": self.reason_code,
        }
        optional = {
            "relationshipId": self.relationship_id,
            "skillId": self.skill_id,
            "componentId": self.component_id,
            "campaignRef": self.campaign_ref,
            "leadRef": self.lead_ref,
        }
        body.update({name: value for name, value in optional.items() if value is not None})
        return body


def build_spend_event(
    event: str,
    *,
    account_class: str,
    tenant_id: UUID | str,
    paise: int,
    reason_code: str = "OK",
    relationship_id: UUID | str | None = None,
    skill_id: str | None = None,
    component_id: str | None = None,
    campaign_ref: str | None = None,
    lead_ref: str | None = None,
) -> SpendEvent:
    if event not in SPEND_EVENTS:
        raise ValueError(f"unknown spend event {event}")
    return SpendEvent(
        event=event,
        account_class=_token(account_class) or "UNKNOWN",
        tenant_id=_token(tenant_id) or "UNKNOWN",
        paise=max(0, int(paise)),
        reason_code=reason_code if _REASON.fullmatch(reason_code) else "UNSPECIFIED",
        relationship_id=_token(relationship_id),
        skill_id=_token(skill_id),
        component_id=_token(component_id),
        campaign_ref=_token(campaign_ref),
        lead_ref=_token(lead_ref),
    )


def emit_spend_event(event: str, **values: object) -> dict[str, object] | None:
    """Log the event and count it once; returns the logged fields, or None when recording failed."""
    try:
        built = build_spend_event(event, **values)  # type: ignore[arg-type]
        fields = built.fields()
        _logger.info(json.dumps(fields, sort_keys=True))
        if event == SPEND_SETTLED:
            metrics.count(SPEND_PAISE_METRIC, built.paise, **{"class": built.account_class})
        elif event == SPEND_DENIED:
            metrics.count(
                SPEND_DENIED_METRIC, 1, **{"class": built.account_class, "reason": built.reason_code}
            )
        return fields
    except Exception:
        logging.getLogger(__name__).warning("spend event %s was not recorded", event)
        return None


def record_parity_difference(differing: int) -> None:
    if differing > 0:
        metrics.count(PARITY_DIFFERENCE_METRIC, differing)


def record_live_margin_floor_breach(breaches: int) -> None:
    if breaches > 0:
        metrics.count(LIVE_MARGIN_BREACH_METRIC, breaches)
