# Implements: work-contracts/WC-027-wbe-s3-markup-engine.md WC027-02
# constitutional_basis: C-023, C-059, C-063, C-088, C-089
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID
from datetime import datetime
from typing import Optional


class PriceValidationOutcome(StrEnum):
    """Constitutional pricing validation outcome (C-089)."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ThreadEntry:
    """
    Single thread type from thread catalog.
    Constitutional basis: C-091 (Thread Catalog structure).
    """
    thread_type: str
    description: str
    max_parallel_tasks: int
    default_pacing_mode: str


@dataclass
class BundleProfile:
    """
    Agent bundle tier pricing profile read from institutional.bundle_profiles.
    Constitutional basis: C-089 (Margin Floor enforcement).
    """
    agent_type: str
    bundle_tier: str
    cost_floor_paise: int
    minimum_margin_pct: float


@dataclass
class PriceConfig:
    """
    Pricing configuration: cost floor + margin percentage.
    """
    cost_floor_paise: int
    margin_pct: float


@dataclass
class PriceValidationRequest:
    """
    Incoming request to validate a proposed price against C-089 floor.
    Constitutional basis: C-089 (Margin Floor).
    """
    agent_type: str
    bundle_tier: str
    proposed_price_paise: int
    target_margin_pct: Optional[float] = None


@dataclass
class PriceDeriveRequest:
    """
    Incoming request to derive compliant price from cost floor + margin %.
    """
    agent_type: str
    bundle_tier: str
    target_margin_pct: Optional[float] = None


@dataclass
class PriceValidation:
    """
    Response from validate_price endpoint.
    Constitutional basis: C-089 (pricing_floor_log audit), C-059 (traceability).
    Fields:
      - outcome: APPROVED | REJECTED (PriceValidationOutcome)
      - cost_floor_paise: read from bundle_profiles
      - minimum_margin_pct: read from bundle_profiles
      - minimum_compliant_price_paise: floor / (1 - margin/100)
      - proposed_price_paise: echo from request
      - pricing_floor_log_id: UUID of written audit row (C-059)
    """
    outcome: PriceValidationOutcome
    cost_floor_paise: int
    minimum_margin_pct: float
    minimum_compliant_price_paise: int
    proposed_price_paise: int
    pricing_floor_log_id: UUID


@dataclass
class PriceDeriveResponse:
    """
    Response from derive_price endpoint.
    Returns the compliant price derived from cost floor + margin %.
    """
    cost_floor_paise: int
    minimum_margin_pct: float
    target_margin_pct: float
    derived_compliant_price_paise: int


@dataclass
class ThreadCatalogResponse:
    """
    Response shape for GET /pricing/thread-catalog.
    Mirrors ThreadEntry structure from thread_catalog.py.
    Constitutional basis: C-091 (Wallet bucket structure).
    """
    thread_type: str
    description: str
    max_parallel_tasks: int
    default_pacing_mode: str


class BelowConstitutionalFloorError(Exception):
    """
    Raised when proposed price violates C-089 margin floor.
    Includes minimum_compliant_price_paise for client correction.
    """
    def __init__(self, message: str, minimum_compliant_price_paise: int):
        super().__init__(message)
        self.minimum_compliant_price_paise = minimum_compliant_price_paise


class BundleNotFoundError(Exception):
    """Raised when agent_type or bundle_tier not in bundle_profiles."""
    pass


@dataclass
class PricingFloorLogRecord:
    """
    Internal representation of institutional.pricing_floor_log row.
    Constitutional basis: C-059 (Audit obligation on all price validations).
    """
    id: UUID
    proposed_price_paise: int
    cost_floor_paise: int
    constitutional_minimum_margin_pct: float
    minimum_compliant_price_paise: int
    outcome: PriceValidationOutcome
    created_at: datetime
    tenant_id: Optional[UUID] = None