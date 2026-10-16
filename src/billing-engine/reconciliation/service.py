# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from reconciliation.authority import BillingAuthority, ReconciliationIdentity

logger = logging.getLogger(__name__)

BILLING_HALTED_KEY = "wbe:billing_halted"


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass
class DailyAuditResult:
    audit_date: date
    total_consumed_reservations: int
    unlinked_reservations: list[uuid.UUID]
    evidence_id: uuid.UUID
    audited_at: datetime


@dataclass
class SelfAuditResult:
    discrepancy_paise: int
    billing_halted: bool
    founder_action_created: bool
    buckets_audited: int
    evidence_id: uuid.UUID
    audited_at: datetime


@dataclass
class CustomerMarginRow:
    customer_id: uuid.UUID
    thread_type: str
    revenue_paise: int
    cost_paise: int
    margin_pct: Decimal


# ---------------------------------------------------------------------------
# Stub for FounderActionGenerator -- real implementation injected at runtime
# ---------------------------------------------------------------------------


class FounderActionGenerator:
    """Minimal interface contract - real impl lives in founder_actions module."""

    async def maybe_create(
        self,
        *,
        action_type: str,
        payload: dict[str, object],
    ) -> bool:
        """Return True if a new founder action was created."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# ReconciliationService
# ---------------------------------------------------------------------------


class ReconciliationService:
    """
    Integrity floor of the WBE.

    Constitutional obligations:
      C-091 -- financial correctness over availability; any discrepancy > 1 paise
               triggers BILLING_INTEGRITY_HALT.
      C-023 -- every audit emits an evidence record regardless of outcome.
      C-059 -- full traceability on every operation.
      C-063 -- no PII in log statements.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: aioredis.Redis,
        founder_action_generator: FounderActionGenerator,
        environment: str = "production",
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._fag = founder_action_generator
        self._environment = environment

    @property
    def uses_durable_authority(self) -> bool:
        return self._environment in {"demo", "uat"}

    async def is_any_scope_halted(self) -> bool:
        """Return durable environment halt status; database uncertainty propagates."""
        if self._environment == "production":
            return bool(await self._redis.get(BILLING_HALTED_KEY))
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM integrity_states
                        WHERE environment = :environment
                          AND state IN ('HALTED', 'RECONCILIATION_REQUIRED')
                    )
                    """
                ),
                {"environment": self._environment},
            )
            return bool(result.scalar())

    async def last_audit_projection(self) -> tuple[date | None, datetime | None]:
        """Return the latest durable audit projection for this environment."""
        if self._environment == "production":
            return None, None
        async with self._session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT MAX(ar.completed_at)
                    FROM audit_results ar
                    WHERE ar.environment = :environment
                    """
                ),
                {"environment": self._environment},
            )
            completed_at = result.scalar()
            if completed_at is None:
                return None, None
            if isinstance(completed_at, str):
                completed_at = datetime.fromisoformat(completed_at)
            return completed_at.date(), completed_at

    # ------------------------------------------------------------------
    # run_daily_audit
    # ------------------------------------------------------------------

    async def run_daily_audit(self, audit_date: date) -> DailyAuditResult:
        """
        For each bucket_reservation WHERE consumed=True AND consumed_at::date = audit_date,
        verify a matching platform_cost_ledger row with bucket_reservation_id exists.
        Flags unlinked reservations.
        Emits C-023 evidence record regardless of outcome.
        """
        evidence_id = uuid.uuid4()
        audited_at = datetime.now(timezone.utc)
        unlinked: list[uuid.UUID] = []

        try:
            async with self._session_factory() as session:
                consumed_rows = await session.execute(
                    text(
                        """
                        SELECT id
                        FROM bucket_reservations
                        WHERE consumed = TRUE
                          AND date(consumed_at) = :audit_date
                        """
                    ).bindparams(audit_date=audit_date)
                )
                reservation_ids: list[uuid.UUID] = [
                    uuid.UUID(str(row[0])) for row in consumed_rows.fetchall()
                ]

                for res_id in reservation_ids:
                    ledger_row = await session.execute(
                        text(
                            """
                            SELECT id
                            FROM platform_cost_ledger
                            WHERE bucket_reservation_id = :res_id
                            LIMIT 1
                            """
                        ).bindparams(res_id=str(res_id))
                    )
                    if ledger_row.fetchone() is None:
                        unlinked.append(res_id)

                # Emit C-023 evidence record
                await session.execute(
                    text(
                        """
                        INSERT INTO audit_evidence_log
                            (id, audit_type, audit_date, total_checked,
                             unlinked_count, outcome, created_at)
                        VALUES
                            (:id, :audit_type, :audit_date, :total_checked,
                             :unlinked_count, :outcome, :created_at)
                        """
                    ).bindparams(
                        id=str(evidence_id),
                        audit_type="DAILY_RESERVATION_AUDIT",
                        audit_date=audit_date.isoformat(),
                        total_checked=len(reservation_ids),
                        unlinked_count=len(unlinked),
                        outcome="PASS" if not unlinked else "FAIL_UNLINKED",
                        created_at=audited_at.isoformat(),
                    )
                )
                await session.commit()

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error(
                "run_daily_audit failed for date=%s evidence_id=%s",
                audit_date,
                evidence_id,
                exc_info=True,
            )
            raise

        if unlinked:
            logger.warning(
                "run_daily_audit found %s unlinked reservations for date=%s evidence_id=%s",
                len(unlinked),
                audit_date,
                evidence_id,
            )
        else:
            logger.info(
                "run_daily_audit PASS date=%s total_checked=%s evidence_id=%s",
                audit_date,
                len(reservation_ids),
                evidence_id,
            )

        return DailyAuditResult(
            audit_date=audit_date,
            total_consumed_reservations=len(reservation_ids),
            unlinked_reservations=unlinked,
            evidence_id=evidence_id,
            audited_at=audited_at,
        )

    # ------------------------------------------------------------------
    # run_self_audit
    # ------------------------------------------------------------------

    async def run_self_audit(self) -> SelfAuditResult:
        """
        For every active wallet_bucket:
          expected_balance = SUM(topup_orders.amount_paise WHERE applied_at IS NOT NULL
                                 AND thread_type matches)
                           - SUM(bucket_reservations.reserved_paise WHERE consumed=True)
          If |balance_paise - expected_balance| > 1:
            - set Redis wbe:billing_halted (no TTL)
            - call FounderActionGenerator.maybe_create
            - return SelfAuditResult(billing_halted=True, ...)
        Emits C-023 evidence record regardless of outcome.
        """
        evidence_id = uuid.uuid4()
        audited_at = datetime.now(timezone.utc)
        max_discrepancy = 0
        buckets_audited = 0
        billing_halted = False
        founder_action_created = False
        founder_action_payloads: list[dict[str, object]] = []

        try:
            async with self._session_factory() as session:
                # Fetch all active wallet buckets
                bucket_rows = await session.execute(
                    text(
                        """
                        SELECT wb.id,
                               wb.balance_paise,
                               wb.employment_contract_id,
                               wb.thread_type,
                               wb.customer_id
                        FROM wallet_buckets wb
                        WHERE wb.is_active = TRUE
                        """
                    )
                )
                buckets = bucket_rows.fetchall()
                buckets_audited = len(buckets)

                for bucket in buckets:
                    bucket_id = bucket[0]
                    balance_paise = bucket[1]
                    employment_contract_id = bucket[2]
                    thread_type = bucket[3]
                    tenant_id = (
                        uuid.UUID(str(bucket[4]))
                        if self._environment in {"demo", "uat"}
                        else uuid.UUID(int=0)
                    )

                    # Compute topup sum
                    topup_row = await session.execute(
                        text(
                            """
                            SELECT COALESCE(SUM(amount_paise), 0)
                            FROM topup_orders
                            WHERE employment_contract_id = :ec_id
                              AND thread_type = :thread_type
                              AND applied_at IS NOT NULL
                            """
                        ).bindparams(
                            ec_id=employment_contract_id,
                            thread_type=thread_type,
                        )
                    )
                    total_topups: int = topup_row.scalar() or 0

                    # Compute consumed reservation sum
                    consumed_row = await session.execute(
                        text(
                            """
                            SELECT COALESCE(SUM(reserved_paise), 0)
                            FROM bucket_reservations
                            WHERE bucket_id = :bucket_id
                              AND consumed = TRUE
                            """
                        ).bindparams(bucket_id=bucket_id)
                    )
                    total_consumed: int = consumed_row.scalar() or 0

                    expected_balance = total_topups - total_consumed
                    discrepancy = abs(balance_paise - expected_balance)
                    accounting_scope_id = uuid.UUID(str(bucket_id))
                    payload = {
                        "accounting_scope_id": str(accounting_scope_id),
                        "actual_balance_paise": int(balance_paise),
                        "expected_balance_paise": int(expected_balance),
                        "tenant_id": str(tenant_id),
                        "thread_type": str(thread_type),
                    }
                    source_watermark = hashlib.sha256(
                        json.dumps(
                            payload,
                            ensure_ascii=True,
                            separators=(",", ":"),
                            sort_keys=True,
                        ).encode("utf-8")
                    ).hexdigest()
                    period_start = datetime.combine(
                        audited_at.date(),
                        datetime.min.time(),
                        tzinfo=timezone.utc,
                    )
                    authority: BillingAuthority | None = None
                    claim = None
                    if self._environment in {"demo", "uat"}:
                        authority = BillingAuthority(session, self._environment)
                        claim = await authority.claim_execution(
                            ReconciliationIdentity(
                                environment=self._environment,
                                tenant_id=tenant_id,
                                accounting_scope_id=accounting_scope_id,
                                reconciliation_type="SELF_AUDIT",
                                covered_period_start=period_start,
                                covered_period_end=period_start + timedelta(days=1),
                                source_watermark=source_watermark,
                            ),
                            payload,
                        )

                    if discrepancy > max_discrepancy:
                        max_discrepancy = discrepancy

                    if discrepancy > 1:
                        logger.error(
                            "BILLING_INTEGRITY_HALT: bucket_id=%s discrepancy=%s paise "
                            "balance=%s expected=%s evidence_id=%s",
                            bucket_id,
                            discrepancy,
                            balance_paise,
                            expected_balance,
                            evidence_id,
                        )
                        halt_committed = claim is None or not (
                            claim.replayed and claim.status == "COMMITTED"
                        )
                        if authority is not None and claim is not None and halt_committed:
                            await authority.record_halt(
                                execution_id=claim.execution_id,
                                tenant_id=tenant_id,
                                accounting_scope_id=accounting_scope_id,
                                discrepancy_paise=discrepancy,
                                expected_paise=expected_balance,
                                actual_paise=balance_paise,
                                actor_id="billing-reconciliation",
                                authority_reference="ADR-034",
                                evidence_reference=f"billing-audit:{evidence_id}",
                                reason="wallet balance discrepancy exceeded one paise",
                                result_digest=source_watermark,
                            )
                        elif authority is None:
                            await self._redis.set(BILLING_HALTED_KEY, "1")
                        billing_halted = True
                        if halt_committed:
                            founder_action_payloads.append(
                                {
                                    "bucket_id": str(bucket_id),
                                    "discrepancy_paise": discrepancy,
                                    "evidence_id": str(evidence_id),
                                    "audited_at": audited_at.isoformat(),
                                }
                            )
                    elif authority is not None and claim is not None and not (
                        claim.replayed and claim.status == "COMMITTED"
                    ):
                        await authority.record_pass(
                            execution_id=claim.execution_id,
                            tenant_id=tenant_id,
                            accounting_scope_id=accounting_scope_id,
                            discrepancy_paise=discrepancy,
                            evidence_reference=f"billing-audit:{evidence_id}",
                            result_digest=source_watermark,
                        )

                # Emit C-023 evidence record
                await session.execute(
                    text(
                        """
                        INSERT INTO audit_evidence_log
                            (id, audit_type, audit_date, total_checked,
                             unlinked_count, outcome, created_at)
                        VALUES
                            (:id, :audit_type, :audit_date, :total_checked,
                             :unlinked_count, :outcome, :created_at)
                        """
                    ).bindparams(
                        id=str(evidence_id),
                        audit_type="SELF_AUDIT",
                        audit_date=audited_at.date().isoformat(),
                        total_checked=buckets_audited,
                        unlinked_count=0,
                        outcome="HALT" if billing_halted else "PASS",
                        created_at=audited_at.isoformat(),
                    )
                )
                await session.commit()

            for payload in founder_action_payloads:
                if await self._fag.maybe_create(
                    action_type="BILLING_INTEGRITY_HALT",
                    payload=payload,
                ):
                    founder_action_created = True

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error(
                "run_self_audit failed evidence_id=%s",
                evidence_id,
                exc_info=True,
            )
            raise

        logger.info(
            "run_self_audit complete buckets_audited=%s max_discrepancy_paise=%s "
            "billing_halted=%s evidence_id=%s",
            buckets_audited,
            max_discrepancy,
            billing_halted,
            evidence_id,
        )

        return SelfAuditResult(
            discrepancy_paise=max_discrepancy,
            billing_halted=billing_halted,
            founder_action_created=founder_action_created,
            buckets_audited=buckets_audited,
            evidence_id=evidence_id,
            audited_at=audited_at,
        )

    # ------------------------------------------------------------------
    # generate_margin_report
    # ------------------------------------------------------------------

    async def generate_margin_report(self, report_date: date) -> list[CustomerMarginRow]:
        """
        Join consumed bucket_reservations.reserved_paise as revenue against
        platform_cost_ledger.raw_cost_inr_paise as cost.
        margin_pct = (revenue - cost) / revenue
        Zero-cost rows return 100% margin.
        """
        rows: list[CustomerMarginRow] = []

        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    text(
                        """
                        SELECT
                            wb.customer_id,
                            wb.thread_type,
                            COALESCE(SUM(br.reserved_paise), 0)          AS revenue_paise,
                            COALESCE(SUM(pcl.raw_cost_inr_paise), 0)     AS cost_paise
                        FROM bucket_reservations br
                        JOIN wallet_buckets wb
                            ON wb.id = br.bucket_id
                        LEFT JOIN platform_cost_ledger pcl
                            ON pcl.bucket_reservation_id = br.id
                        WHERE br.consumed = TRUE
                          AND date(br.consumed_at) = :report_date
                        GROUP BY wb.customer_id, wb.thread_type
                        """
                    ).bindparams(report_date=report_date)
                )

                for row in result.fetchall():
                    customer_id: uuid.UUID = uuid.UUID(str(row[0]))
                    thread_type: str = row[1]
                    revenue_paise: int = int(row[2])
                    cost_paise: int = int(row[3])

                    if revenue_paise == 0:
                        margin_pct = Decimal("100")
                    else:
                        margin_pct = (
                            Decimal(revenue_paise - cost_paise)
                            / Decimal(revenue_paise)
                            * Decimal("100")
                        ).quantize(Decimal("0.01"))

                    rows.append(
                        CustomerMarginRow(
                            customer_id=customer_id,
                            thread_type=thread_type,
                            revenue_paise=revenue_paise,
                            cost_paise=cost_paise,
                            margin_pct=margin_pct,
                        )
                    )

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error(
                "generate_margin_report failed for date=%s",
                report_date,
                exc_info=True,
            )
            raise

        logger.info(
            "generate_margin_report complete date=%s customer_count=%s",
            report_date,
            len(rows),
        )
        return rows

    # ------------------------------------------------------------------
    # clear_halt
    # ------------------------------------------------------------------

    async def clear_halt(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        accounting_scope_id: uuid.UUID | None = None,
        actor_id: str | None = None,
        authority_reference: str | None = None,
        reason: str | None = None,
        evidence_reference: str | None = None,
    ) -> uuid.UUID | None:
        """
        Append an authorized release event and clear current durable halt state.
        """
        if self._environment == "production":
            await self._redis.delete(BILLING_HALTED_KEY)
            logger.info("Production Billing halt Redis key cleared")
            return None
        if any(
            value is None or (isinstance(value, str) and not value.strip())
            for value in (
                tenant_id,
                accounting_scope_id,
                actor_id,
                authority_reference,
                reason,
                evidence_reference,
            )
        ):
            raise ValueError("durable halt release requires complete authority and evidence")
        assert tenant_id is not None
        assert accounting_scope_id is not None
        assert actor_id is not None
        assert authority_reference is not None
        assert reason is not None
        assert evidence_reference is not None
        async with self._session_factory() as session:
            authority = BillingAuthority(session, self._environment)
            event_id = await authority.release_halt(
                tenant_id=tenant_id,
                accounting_scope_id=accounting_scope_id,
                actor_id=actor_id,
                authority_reference=authority_reference,
                reason=reason,
                evidence_reference=evidence_reference,
            )
            await session.commit()
        logger.info("Billing integrity halt released with event_id=%s", event_id)
        return event_id