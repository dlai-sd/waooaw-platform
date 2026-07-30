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
    Holds paise in escrow between reserve() and release() calls.
    Idempotency is enforced via a unique DB constraint on idempotency_key so
    that a duplicate reserve() with the same key returns the existing row
    rather than double-debiting the bucket (ADR-034 §idempotency).

    Status transitions:
        PENDING  → CONSUMED  (release called with consumed=True)
        PENDING  → RELEASED  (release called with consumed=False — funds restored)
        PENDING  → EXPIRED   (TTL sweep job — funds restored automatically)

    C-059: every transition MUST emit a CE evidence record prior to commit.
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
    # Caller-supplied idempotency key (UUID v4) — unique per reservation attempt.
    idempotency_key: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        nullable=False,
        unique=True,
    )
    # Amount held in escrow — must equal the deduction applied to bucket.reserved_paise.
    amount_paise: Mapped[int] = mapped_column(BigInteger, nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReservationStatus.PENDING,
    )

    # Lifecycle timestamps — nullable because they are set only on transition.
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
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expired_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # relationships
    bucket: Mapped[WalletBucket] = relationship(
        "WalletBucket",
        back_populates="reservations",
    )