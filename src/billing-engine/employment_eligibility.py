"""WBE-owned Skill-scoped conversational-employment eligibility."""

# Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.3 WBE eligibility
# Constitutional basis: C-005, C-023, C-038, C-059, C-063, C-079, ADR-051
# IB: N/A - Founder-assigned WC-115

from __future__ import annotations

import logging
import json
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session_factory
from relationship_workspace import _authorize
from workload_identity import DelegatedContext, ServiceAuthError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/internal/v1/relationships", tags=["Employment Commercial Eligibility"])


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


class EmploymentModel(BaseModel):
    model_config = ConfigDict(alias_generator=_camel, populate_by_name=True, extra="forbid")


class SkillEligibility(EmploymentModel):
    skill_ref: str = Field(min_length=1, max_length=128)
    state: Literal["ELIGIBLE", "READ_ONLY", "BLOCKED", "UNKNOWN"]
    consequential_work_funded: bool
    reason_code: Literal[
        "FUNDED",
        "TRIAL_ADVISORY_ONLY",
        "ALLOWANCE_EXHAUSTED",
        "PAYMENT_BLOCKED",
        "PROFILE_STALE",
        "UNKNOWN",
    ]
    consequence_label: str | None = Field(default=None, max_length=240)

    @model_validator(mode="after")
    def validate_funding(self) -> SkillEligibility:
        if self.state == "ELIGIBLE" and (
            not self.consequential_work_funded or self.reason_code != "FUNDED"
        ):
            raise ValueError("eligible Skills must be funded")
        if self.state != "ELIGIBLE" and self.consequential_work_funded:
            raise ValueError("non-eligible Skills cannot authorize consequential work")
        return self


class EmploymentEligibility(EmploymentModel):
    schema_version: Literal["1.0"] = "1.0"
    relationship_id: uuid.UUID
    plan_version: str = Field(min_length=1, max_length=64)
    manifest_version: str = Field(min_length=1, max_length=64)
    source_projection_version: str = Field(min_length=1, max_length=64)
    currency_state: Literal["CURRENT", "STALE", "UNKNOWN", "UNAVAILABLE", "BLOCKED"]
    skill_eligibility: tuple[SkillEligibility, ...] = Field(min_length=1)
    preserved_path_classes: tuple[
        Literal["EMERGENCY_STOP", "CONSTITUTIONAL_RIGHTS", "EVIDENCE_READ", "READ_ONLY_REVIEW"],
        ...,
    ]
    valid_until: datetime | None = None
    produced_at: datetime

    @model_validator(mode="after")
    def validate_paths_and_currency(self) -> EmploymentEligibility:
        expected = {
            "EMERGENCY_STOP",
            "CONSTITUTIONAL_RIGHTS",
            "EVIDENCE_READ",
            "READ_ONLY_REVIEW",
        }
        if set(self.preserved_path_classes) != expected or len(self.preserved_path_classes) != 4:
            raise ValueError("all four preserved path classes are required")
        if self.currency_state != "CURRENT" and any(
            item.state == "ELIGIBLE" for item in self.skill_eligibility
        ):
            raise ValueError("non-current commercial truth cannot authorize work")
        return self


class EmploymentEligibilityStore:
    def __init__(self) -> None:
        self._items: dict[tuple[str, uuid.UUID, str, str], EmploymentEligibility] = {}
        self._lock = Lock()

    def record(self, tenant_id: str, eligibility: EmploymentEligibility) -> None:
        key = (
            tenant_id,
            eligibility.relationship_id,
            eligibility.plan_version,
            eligibility.manifest_version,
        )
        with self._lock:
            if key in self._items:
                raise ValueError("employment eligibility versions are immutable")
            self._items[key] = eligibility

    def get(
        self,
        context: DelegatedContext,
        relationship_id: uuid.UUID,
        plan_version: str,
        manifest_version: str,
    ) -> EmploymentEligibility | None:
        if context.relationship_id != str(relationship_id):
            return None
        with self._lock:
            return self._items.get(
                (context.tenant_id, relationship_id, plan_version, manifest_version)
            )


class PostgresEmploymentEligibilityStore:
    def __init__(self) -> None:
        self._session_factory_provider = get_session_factory

    async def record(self, tenant_id: str, eligibility: EmploymentEligibility) -> None:
        session_factory = self._session_factory_provider()
        async with session_factory() as session, session.begin():
            await self._set_tenant(session, tenant_id)
            payload = eligibility.model_dump(mode="json", by_alias=True)
            for skill in eligibility.skill_eligibility:
                state = {
                    "ELIGIBLE": "ELIGIBLE",
                    "BLOCKED": "BLOCKED",
                    "UNKNOWN": "UNKNOWN",
                    "READ_ONLY": "INELIGIBLE",
                }[skill.state]
                await session.execute(
                    text(
                        """
                        INSERT INTO billing.employment_eligibility_versions (
                            tenant_id, relationship_id, skill_id, source_version,
                            state, reason_codes, consequence_json, produced_at
                        ) VALUES (
                            CAST(:tenant_id AS uuid), CAST(:relationship_id AS uuid),
                            :skill_id, :source_version, :state,
                            CAST(:reason_codes AS jsonb), CAST(:consequence AS jsonb),
                            :produced_at
                        )
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "relationship_id": str(eligibility.relationship_id),
                        "skill_id": skill.skill_ref,
                        "source_version": eligibility.source_projection_version,
                        "state": state,
                        "reason_codes": json.dumps([skill.reason_code]),
                        "consequence": eligibility.model_dump_json(by_alias=True),
                        "produced_at": eligibility.produced_at,
                    },
                )

    async def get(
        self,
        context: DelegatedContext,
        relationship_id: uuid.UUID,
        plan_version: str,
        manifest_version: str,
    ) -> EmploymentEligibility | None:
        if context.relationship_id != str(relationship_id):
            return None
        session_factory = self._session_factory_provider()
        async with session_factory() as session, session.begin():
            await self._set_tenant(session, context.tenant_id)
            result = await session.execute(
                text(
                    """
                    SELECT consequence_json
                    FROM billing.employment_eligibility_versions
                    WHERE tenant_id = CAST(:tenant_id AS uuid)
                      AND relationship_id = CAST(:relationship_id AS uuid)
                      AND consequence_json ->> 'planVersion' = :plan_version
                      AND consequence_json ->> 'manifestVersion' = :manifest_version
                    ORDER BY produced_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "tenant_id": context.tenant_id,
                    "relationship_id": str(relationship_id),
                    "plan_version": plan_version,
                    "manifest_version": manifest_version,
                },
            )
            payload = result.scalar_one_or_none()
        return (
            EmploymentEligibility.model_validate(payload)
            if payload is not None
            else None
        )

    @staticmethod
    async def _set_tenant(session: AsyncSession, tenant_id: str) -> None:
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )


def get_store(
    request: Request,
) -> EmploymentEligibilityStore | PostgresEmploymentEligibilityStore:
    store = getattr(request.app.state, "employment_eligibility_store", None)
    if not isinstance(
        store,
        (EmploymentEligibilityStore, PostgresEmploymentEligibilityStore),
    ):
        raise HTTPException(status_code=503, detail="WBE_EMPLOYMENT_UNAVAILABLE")
    return store


@router.get("/{relationship_id}/employment-eligibility", response_model=EmploymentEligibility)
async def get_employment_commercial_eligibility(
    relationship_id: uuid.UUID,
    request: Request,
    plan_version: str = Query(alias="planVersion", min_length=1, max_length=64),
    manifest_version: str = Query(alias="manifestVersion", min_length=1, max_length=64),
    _correlation_id: uuid.UUID = Header(alias="X-Correlation-Id"),
    store: EmploymentEligibilityStore | PostgresEmploymentEligibilityStore = Depends(get_store),
) -> EmploymentEligibility:
    try:
        context = _authorize(
            request,
            "/internal/v1/relationships/{relationshipId}/employment-eligibility",
            "getEmploymentCommercialEligibility",
            relationship_id,
        )
    except ServiceAuthError as exc:
        logger.warning(
            "service_auth decision=deny target=billing-engine operation=employment_eligibility reason_class=%s",
            exc.code,
        )
        raise HTTPException(status_code=401, detail="WBE_EMPLOYMENT_UNAUTHORIZED") from None
    eligibility = (
        await store.get(context, relationship_id, plan_version, manifest_version)
        if isinstance(store, PostgresEmploymentEligibilityStore)
        else store.get(context, relationship_id, plan_version, manifest_version)
    )
    if eligibility is None:
        raise HTTPException(status_code=404, detail="WBE_EMPLOYMENT_NOT_ACCESSIBLE")
    now = datetime.now(timezone.utc)
    if (
        eligibility.currency_state != "CURRENT"
        or eligibility.valid_until is not None
        and eligibility.valid_until <= now
    ):
        raise HTTPException(status_code=503, detail="WBE_EMPLOYMENT_UNAVAILABLE")
    return eligibility


def configure_employment_eligibility(application: FastAPI) -> None:
    application.state.employment_eligibility_store = PostgresEmploymentEligibilityStore()
