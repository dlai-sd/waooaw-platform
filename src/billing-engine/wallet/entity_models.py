# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-02
# Constitutional basis: C-059, C-088, C-089, C-063
"""Value objects, vocabularies and errors of the WBE Wallet entity (WC-136 Appendix A.1)."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Final
from uuid import UUID

ACCOUNT_CLASSES: Final = (
    "ACQUISITION",
    "SETUP_GRANT",
    "TRIAL",
    "SUBSCRIPTION",
    "PLATFORM_FLOOR",
    "SIMULATION",
)
# There is no refundable lot kind and no rollover (FD9).
LOT_KINDS: Final = ("PERIOD_CREDIT", "TOPUP_CREDIT", "GRANT")
SOURCE_KINDS: Final = (
    "PACKAGE_PERIOD",
    "TOPUP",
    "TRIAL_GRANT",
    "SETUP_GRANT",
    "ACQUISITION_BUDGET",
    "SIMULATION_BUDGET",
)
RESERVATION_OPEN_STATES: Final = ("RESERVED", "UNKNOWN")

DEFAULT_SOURCE_KIND: Final = {
    "PERIOD_CREDIT": "PACKAGE_PERIOD",
    "TOPUP_CREDIT": "TOPUP",
}
GRANT_SOURCE_KIND_BY_ACCOUNT_CLASS: Final = {
    "TRIAL": "TRIAL_GRANT",
    "SETUP_GRANT": "SETUP_GRANT",
    "ACQUISITION": "ACQUISITION_BUDGET",
    "SIMULATION": "SIMULATION_BUDGET",
}


class WalletError(ValueError):
    """A typed wallet refusal; ``str(error)`` is the stable error code."""

    def __init__(self, code: str, detail: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail


def canonical_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def utc_iso(value: datetime) -> str:
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return aware.astimezone(timezone.utc).isoformat()


def as_utc(value: object) -> datetime:
    """Normalise a database timestamp (datetime or ISO string) to an aware UTC datetime."""
    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def as_json_object(value: object) -> dict[str, object]:
    if value is None:
        return {}
    loaded = json.loads(value) if isinstance(value, (str, bytes)) else value
    return dict(loaded)


@dataclass(frozen=True)
class WalletAccount:
    account_id: UUID
    tenant_id: UUID
    owner_kind: str
    owner_ref: UUID | None
    account_class: str
    scope_kind: str
    relationship_id: UUID | None
    skill_id: str | None
    campaign_ref: str | None
    lead_ref: str | None
    environment: str | None
    agent_type: str | None
    agent_version: str | None
    status: str
    created_at: datetime


@dataclass(frozen=True)
class WalletCreditReceipt:
    lot_id: UUID
    account_id: UUID
    lot_kind: str
    source_kind: str
    credited_paise: int
    valid_from: datetime
    valid_until: datetime
    replayed: bool = False


@dataclass(frozen=True)
class ReservationIdentity:
    """What the caller pins at reserve time; later operations read it back and never re-resolve."""

    pinned_versions: Mapping[str, str] = field(default_factory=dict)
    invocation_id: UUID | None = None
    evidence_id: UUID | None = None


@dataclass(frozen=True)
class WalletReservationReceipt:
    reservation_id: UUID
    account_id: UUID
    lot_id: UUID
    component_id: str
    state: str
    reserved_paise: int
    actual_paise: int | None
    pinned_account_class: str
    pinned_versions: Mapping[str, object]
    overrun_paise: int = 0
    fenced: bool = False
    replayed: bool = False


@dataclass(frozen=True)
class WalletBalance:
    account_id: UUID
    at: datetime
    available_paise: int
    credited_paise: int
    reserved_paise: int
    settled_paise: int
    expired_paise: int


@dataclass(frozen=True)
class WalletExpiryReceipt:
    lot_id: UUID
    expired_paise: int
