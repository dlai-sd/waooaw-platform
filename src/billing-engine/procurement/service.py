# Implements: <spec-path> §<section>
# constitutional_basis: C-059 (Implementation Traceability)
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from procurement.models import ProviderRunwayStatus

if TYPE_CHECKING:
    from procurement.founder_action import FounderActionGenerator

from skeleton.wbe_interfaces import FounderActionCreated

logger = logging.getLogger(__name__)

# Import PROCUREMENT_POLICY from WC-028 singleton
try:
    from meter.alert_policy import PROCUREMENT_POLICY
except ImportError:
    PROCUREMENT_POLICY = None  # type: ignore[assignment]
    logger.warning("PROCUREMENT_POLICY not available -- meter.alert_policy not found")


class ProcurementService:
    """
    Platform procurement ledger service.
    - record_cost: append-only per C-007 (no dedup at DB level)
    - project_runway: 7d rolling avg burn rate
    - check_and_alert: threshold breach -> FounderAction
    """

    def __init__(
        self,
        session: AsyncSession,
        founder_action_generator: FounderActionGenerator,
    ) -> None:
        self._session = session
        self._fa_generator = founder_action_generator

    async def record_cost(
        self,
        provider: str,
        thread_type: str,
        customer_id: UUID,
        agent_type: str,
        cost_paise: int,
        fx_rate_inr_per_usd: float,
    ) -> None:
        """
        Append one row to platform_cost_ledger.
        Intentionally NOT idempotent per C-007 (append-only evidence trail).
        Resolves provider_account_id from provider_name lookup.
        PII: customer_id is logged only as a redacted indicator (C-063).
        """
        try:
            # Resolve provider_account_id from provider_name
            lookup_sql = text(
                "SELECT id FROM institutional.provider_accounts"
                " WHERE provider_name = :pname AND is_active = TRUE"
                " LIMIT 1"
            ).bindparams(pname=provider)
            result = await self._session.execute(lookup_sql)
            row = result.fetchone()
            if row is None:
                logger.error(
                    "provider_account not found for provider=%s -- cost not recorded",
                    provider,
                )
                return

            provider_account_id: UUID = row[0]
            recorded_at = datetime.now(timezone.utc)

            insert_sql = text(
                "INSERT INTO institutional.platform_cost_ledger"
                " (provider_account_id, thread_type, customer_id, agent_type,"
                "  raw_cost_inr_paise, fx_rate_inr_per_usd, recorded_at)"
                " VALUES (:paid, :ttype, :cid, :atype, :cost, :fx, :rat)"
            ).bindparams(
                paid=provider_account_id,
                ttype=thread_type,
                cid=customer_id,
                atype=agent_type,
                cost=cost_paise,
                fx=fx_rate_inr_per_usd,
                rat=recorded_at,
            )
            await self._session.execute(insert_sql)
            await self._session.commit()

            logger.info(
                "platform_cost_ledger: appended provider=%s thread_type=%s cost_paise=%s",
                provider,
                thread_type,
                cost_paise,
            )
        except asyncio.CancelledError:
            raise
        except (ValueError, TypeError):
            logger.error(
                "record_cost: invalid argument -- provider=%s",
                provider,
                exc_info=True,
                extra={"context": "record_cost param validation"},
            )
            raise
        except Exception:
            logger.error(
                "record_cost: DB error -- provider=%s",
                provider,
                exc_info=True,
                extra={"context": "record_cost DB insert"},
            )
            await self._session.rollback()
            raise

    async def project_runway(self, provider_name: str) -> float:
        """
        7d rolling average daily burn, then balance / avg.
        Returns float('inf') when avg == 0 (no burn recorded).
        Formula: SUM(raw_cost_inr_paise WHERE recorded_at >= NOW()-7d) / 7
                 -> balance_paise / avg_daily_burn
        """
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)

            burn_sql = text(
                "SELECT COALESCE(SUM(pcl.raw_cost_inr_paise), 0)"
                " FROM institutional.platform_cost_ledger pcl"
                " JOIN institutional.provider_accounts pa"
                "   ON pa.id = pcl.provider_account_id"
                " WHERE pa.provider_name = :pname"
                "   AND pcl.recorded_at >= :cutoff"
            ).bindparams(pname=provider_name, cutoff=cutoff)
            result = await self._session.execute(burn_sql)
            total_7d: int = result.scalar() or 0

            avg_daily_burn: float = total_7d / 7.0

            if avg_daily_burn == 0.0:
                return float("inf")

            balance_sql = text(
                "SELECT balance_paise FROM institutional.provider_accounts"
                " WHERE provider_name = :pname AND is_active = TRUE"
                " LIMIT 1"
            ).bindparams(pname=provider_name)
            bal_result = await self._session.execute(balance_sql)
            balance_row = bal_result.fetchone()
            if balance_row is None:
                logger.warning(
                    "project_runway: provider_account not found for provider=%s",
                    provider_name,
                )
                return float("inf")

            balance_paise: int = balance_row[0]
            days_remaining: float = balance_paise / avg_daily_burn
            return days_remaining

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error(
                "project_runway: error computing runway for provider=%s",
                provider_name,
                exc_info=True,
                extra={"context": "project_runway DB query"},
            )
            raise

    async def check_and_alert(
        self, provider_name: str
    ) -> list[FounderActionCreated]:
        """
        Read PROCUREMENT_POLICY thresholds, project runway, and call
        FounderActionGenerator.maybe_create for each breached threshold.
        Returns list of FounderActionCreated events (may be empty).
        """
        created: list[FounderActionCreated] = []

        if PROCUREMENT_POLICY is None:
            logger.warning(
                "check_and_alert: PROCUREMENT_POLICY not loaded -- skipping provider=%s",
                provider_name,
            )
            return created

        try:
            days_remaining = await self.project_runway(provider_name)

            for rule in PROCUREMENT_POLICY.rules:
                threshold_days: float = rule.threshold_days
                priority: str = rule.priority  # P0 | P1 | P2

                if days_remaining <= threshold_days:
                    fa_result = await self._fa_generator.maybe_create(
                        provider=provider_name,
                        days_remaining=days_remaining,
                        priority=priority,
                    )
                    if fa_result is not None:
                        created.append(
                            FounderActionCreated(
                                fa_number=fa_result,
                                provider_name=provider_name,
                                days_remaining=days_remaining,
                                priority=priority,
                                created_at=datetime.now(timezone.utc),
                            )
                        )

            return created

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error(
                "check_and_alert: error for provider=%s",
                provider_name,
                exc_info=True,
                extra={"context": "check_and_alert threshold scan"},
            )
            raise

    async def get_all_runway_statuses(self) -> list[ProviderRunwayStatus]:
        """
        Return ProviderRunwayStatus for every active provider account.
        Used by GET /platform/procurement/status.
        """
        try:
            accounts_sql = text(
                "SELECT provider_name, balance_paise"
                " FROM institutional.provider_accounts"
                " WHERE is_active = TRUE"
                " ORDER BY provider_name"
            )
            result = await self._session.execute(accounts_sql)
            rows = result.fetchall()

            statuses: list[ProviderRunwayStatus] = []
            for row in rows:
                pname: str = row[0]
                balance: int = row[1]

                cutoff = datetime.now(timezone.utc) - timedelta(days=7)
                burn_sql = text(
                    "SELECT COALESCE(SUM(pcl.raw_cost_inr_paise), 0)"
                    " FROM institutional.platform_cost_ledger pcl"
                    " JOIN institutional.provider_accounts pa"
                    "   ON pa.id = pcl.provider_account_id"
                    " WHERE pa.provider_name = :pname"
                    "   AND pcl.recorded_at >= :cutoff"
                ).bindparams(pname=pname, cutoff=cutoff)
                burn_result = await self._session.execute(burn_sql)
                total_7d: int = burn_result.scalar() or 0
                avg_daily_burn: float = total_7d / 7.0

                if avg_daily_burn == 0.0:
                    days_rem: float = float("inf")
                else:
                    days_rem = balance / avg_daily_burn

                # Fetch last FA level triggered for this provider (C-059 evidence)
                last_fa_sql = text(
                    "SELECT priority FROM institutional.founder_action_log"
                    " WHERE provider_name = :pname"
                    " ORDER BY created_at DESC LIMIT 1"
                )
                last_fa_level: str | None = None
                try:
                    fa_result = await self._session.execute(
                        last_fa_sql.bindparams(pname=pname)
                    )
                    fa_row = fa_result.fetchone()
                    if fa_row is not None:
                        last_fa_level = fa_row[0]
                except Exception:
                    # founder_action_log table may not exist in all environments
                    logger.warning(
                        "get_all_runway_statuses: could not fetch last FA for provider=%s",
                        pname,
                        exc_info=True,
                        extra={"context": "last_fa_level lookup"},
                    )

                statuses.append(
                    ProviderRunwayStatus(
                        provider_name=pname,
                        balance_paise=balance,
                        daily_burn_rate_paise=avg_daily_burn,
                        days_remaining=days_rem,
                        last_fa_level_triggered=last_fa_level,
                    )
                )

            return statuses

        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error(
                "get_all_runway_statuses: failed to fetch provider statuses",
                exc_info=True,
                extra={"context": "get_all_runway_statuses"},
            )
            raise