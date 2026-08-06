"""Wallet domain models — dataclasses and exceptions for wallet/service.py."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True)
class BucketBalance:
    bucket_id: UUID
    customer_id: UUID
    thread_type: str
    balance_paise: int


@dataclass(frozen=True)
class BucketReservation:
    reservation_id: UUID
    bucket_id: UUID
    customer_id: UUID
    thread_type: str
    reserved_paise: int
    idempotency_key: UUID
    created_at: datetime


@dataclass(frozen=True)
class SubscriptionActivationResult:
    subscription_id: UUID
    customer_id: UUID
    agent_type: str
    bundle_tier: str
    activated_at: datetime


@dataclass(frozen=True)
class RenewalResult:
    contract_id: UUID
    customer_id: UUID
    new_period_start: date
    renewed_at: datetime


class BucketNotFoundError(Exception):
    """Raised when no active wallet bucket matches the query."""


class InsufficientBalanceError(Exception):
    """Raised when bucket balance < requested amount. C-004 guard."""


class DuplicateReservationError(Exception):
    """Raised when an idempotency_key collision is detected."""
