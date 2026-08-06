# Implements: work-contracts/WC-031-goal005-wbe-trial-promotions.md §WC031-01
# constitutional_basis: C-088 (trial is a billing mode), C-089 (trial costs tracked), C-059 (Traceability)
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrialStartResult:
    trial_id: uuid.UUID
    expires_at: datetime
    free_unit_caps: dict[str, int]
    wallet_bucket_ids: list[uuid.UUID]


@dataclass
class TrialStatus:
    trial_id: uuid.UUID
    agent_type: str
    started_at: datetime
    expires_at: datetime
    status: str
    units_consumed: dict[str, int]
    units_remaining: dict[str, int]


@dataclass
class ConvertResult:
    new_subscription_id: uuid.UUID
    grandfather_applied: bool
    grandfather_threshold_days: int = field(default=14, repr=False)
