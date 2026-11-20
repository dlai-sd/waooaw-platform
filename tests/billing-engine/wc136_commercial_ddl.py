# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
# Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-10
# Constitutional basis: C-059, C-088, C-089, C-063
"""SQLite twins of the commercial tables (component units, periods, commands, adjustments) for service tests."""

from __future__ import annotations

from sqlalchemy import text

COMPONENT_DDL = (
    """CREATE TABLE business.component_units (
        tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL, agent_instance_id TEXT NOT NULL,
        package_version_id TEXT NOT NULL, component_id TEXT NOT NULL, kind TEXT NOT NULL,
        period_start TIMESTAMP NOT NULL, period_end TIMESTAMP NOT NULL, quantity INTEGER NOT NULL,
        released_cadence TEXT,
        PRIMARY KEY (tenant_id, relationship_id, component_id, period_start)
    )""",
    """CREATE TABLE business.component_unit_entries (
        entry_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL,
        component_id TEXT NOT NULL, period_start TIMESTAMP NOT NULL, entry_kind TEXT NOT NULL,
        units INTEGER, item_ref TEXT, completion_evidence_id TEXT, idempotency_key TEXT NOT NULL,
        occurred_at TIMESTAMP NOT NULL, UNIQUE (tenant_id, relationship_id, idempotency_key)
    )""",
    """CREATE UNIQUE INDEX business.component_unit_entries_evidence ON component_unit_entries (
        tenant_id, relationship_id, component_id, completion_evidence_id)
        WHERE completion_evidence_id IS NOT NULL""",
)

COMMERCIAL_DDL = (
    """CREATE TABLE business.commercial_projections (
        tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL, projection_version TEXT NOT NULL,
        body TEXT NOT NULL, produced_at TIMESTAMP NOT NULL, valid_until TIMESTAMP,
        PRIMARY KEY (tenant_id, relationship_id, projection_version)
    )""",
    """CREATE TABLE business.commercial_commands (
        command_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL,
        idempotency_key TEXT NOT NULL, request_digest TEXT NOT NULL, command_kind TEXT NOT NULL,
        status TEXT NOT NULL, receipt TEXT NOT NULL, outcome TEXT NOT NULL,
        accepted_at TIMESTAMP NOT NULL, resolved_at TIMESTAMP,
        UNIQUE (tenant_id, relationship_id, idempotency_key)
    )""",
    """CREATE TABLE business.relationship_periods (
        tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL, period_start TIMESTAMP NOT NULL,
        period_end TIMESTAMP NOT NULL, package_version_id TEXT NOT NULL, fee_paid_paise INTEGER NOT NULL,
        status TEXT NOT NULL, paused_component_ids TEXT NOT NULL DEFAULT '[]',
        refunded_fee_paise INTEGER NOT NULL DEFAULT 0, scheduled_package_version_id TEXT,
        grace_until TIMESTAMP, updated_at TIMESTAMP NOT NULL, payment_reference TEXT,
        PRIMARY KEY (tenant_id, relationship_id, period_start)
    )""",
    """CREATE TABLE business.billing_adjustments (
        adjustment_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL,
        command_id TEXT NOT NULL UNIQUE, adjustment_kind TEXT NOT NULL, amount_paise INTEGER NOT NULL,
        payment_reference TEXT, status TEXT NOT NULL, provider_reference TEXT,
        created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL
    )""",
    """CREATE TABLE payment_intents (
        razorpay_payment_id TEXT PRIMARY KEY, tenant_id TEXT, relationship_id TEXT,
        status TEXT NOT NULL, activated_at TIMESTAMP
    )""",
)


async def install(session, *groups: tuple[str, ...]) -> None:
    for group in groups or (COMPONENT_DDL, COMMERCIAL_DDL):
        for statement in group:
            await session.execute(text(statement))
