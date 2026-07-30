# Implements: architecture/reference/billing/billing-schema-updates.md full
# constitutional_basis: C-023, C-059, C-063, C-073
from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PgUUID  # noqa: N811 — conventional PgUUID alias
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ---------------------------------------------------------------------------
# Declarative base (isolated to wallet models — no cross-module base sharing)
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Status enumerations (StrEnum — Python 3.12 mandatory pattern)
# ---------------------------------------------------------------------------

class WalletStatus(StrEnum):
    ACTIVE    = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED    = "CLOSED"


class BucketStatus(StrEnum):
    ACTIVE    = "ACTIVE"
    DEPLETED  = "DEPLETED"
    SUSPENDED = "SUSPENDED"


class ReservationStatus(StrEnum):
    PENDING  = "PENDING"
    CONSUMED = "CONSUMED"
    RELEASED = "RELEASED"
    EXPIRED  = "EXPIRED"


# ---------------------------------------------------------------------------
# CustomerWallet  →  business.customer_wallets
# C-088: Billing Profile gate — wallet must be ACTIVE before any reservation
# ---------------------------------------------------------------------------

class CustomerWallet(Base):
    """
    One wallet per customer.  Multiple buckets hang off each wallet (one per
    thread_type x agent_type combination).  ADR-034.
    """

    __tablename__ = "customer_wallets"
    __table_args__ = ({"schema": "business"},)

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    customer_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WalletStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # relationships
    buckets: Mapped[list[WalletBucket]] = relationship(
        "WalletBucket",
        back_populates="wallet",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# WalletBucket  →  business.wallet_buckets
# One bucket per (wallet_id, thread_type, agent_type) logical key.
# balance_paise and reserved_paise are maintained by the wallet service;
# available = balance_paise - reserved_paise (computed in Python, not DB).
# ---------------------------------------------------------------------------

class WalletBucket(Base):
    """
    Tracks a single thread-type allocation within a customer wallet.
    C-089: balance may never fall below the constitutional floor once reserved.
    C-090: grandfather price is preserved on renewal — never recalculated.
    """

    __tablename__ = "wallet_buckets"
    __table_args__ = ({"schema": "business"},)

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    wallet_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("business.customer_wallets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # thread_type references institutional.thread_catalog.thread_id (not FK-enforced
    # here to avoid cross-schema FK cascade complexity — validated at service layer).
    thread_type: Mapped[str] = mapped_column(String(50), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Monetary amounts in INR paise (integer arithmetic — no floating point)
    balance_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    reserved_paise: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)

    # C-090: price agreed at subscription time — MUST NOT be overwritten on renewal
    grandfathered_unit_price_paise: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=BucketStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # relationships
    wallet: Mapped[CustomerWallet] = relationship(
        "CustomerWallet",
        back_populates="buckets",
    )
    reservations: Mapped[list[BucketReservation]] = relationship(
        "BucketReservation",
        back_populates="bucket",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


# ---------------------------------------------------------------------------
# BucketReservation  →  business.bucket_reservations
# Idempotency key enforced at DB level (UniqueConstraint) and service layer.
# C-059: status transitions (PENDING → CONSUMED | RELEASED | EXPIRED) must
#         each produce a CE evidence record before the DB write commits.
# ---------------------------------------------------------------------------

class BucketReservation(Base):
    """
    Holds paise reserved against a WalletBucket for in-flight agent actions.

    Lifecycle:
      PENDING   — amount_paise deducted from bucket.balance_paise,
                  added to bucket.reserved_paise.
      CONSUMED  — agent action completed; reserved_paise decremented,
                  balance_paise decremented permanently.
      RELEASED  — agent action aborted; reserved_paise decremented,
                  balance_paise restored (no net change).
      EXPIRED   — TTL elapsed without CONSUMED/RELEASED; treated as RELEASED
                  by the expiry sweep job.

    Idempotency: idempotency_key (UUID supplied by caller) carries a DB-level
    UniqueConstraint — duplicate reserve calls with the same key return the
    existing row without double-debiting the bucket.

    C-059: every transition away from PENDING MUST emit a CE evidence record
    before the owning DB transaction commits.
    """

    __tablename__ = "bucket_reservations"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_bucket_reservations_idempotency_key"),
        {"schema": "business"},
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    bucket_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("business.wallet_buckets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    # Caller-supplied idempotency key — unique per reservation attempt.
    # DB UniqueConstraint prevents double-debit on retry.
    idempotency_key: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        unique=True,
    )
    # Paise reserved at the time of the reserve() call.
    # Captures the marked-up unit cost from thread_catalog at reservation time
    # so that subsequent thread_catalog price changes do not affect in-flight
    # reservations (C-090 principle extended to reservations).
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReservationStatus.PENDING,
    )

    # Optional: agent session or workflow run that created this reservation.
    # Not FK-enforced — stored for audit/traceability (C-059).
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    # TTL: reservation expires if not CONSUMED/RELEASED within this window.
    # The expiry sweep job queries WHERE status='PENDING' AND expires_at < NOW().
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # relationships
    bucket: Mapped[WalletBucket] = relationship(
        "WalletBucket",
        back_populates="reservations",
    )