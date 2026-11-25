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
        created_at TIMESTAMP NOT NULL, updated_at TIMESTAMP NOT NULL, remaining_paise INTEGER
    )""",
    """CREATE TABLE payment_intents (
        razorpay_payment_id TEXT PRIMARY KEY, tenant_id TEXT, relationship_id TEXT,
        status TEXT NOT NULL, activated_at TIMESTAMP
    )""",
)

WC172_DDL = (
    """CREATE TABLE business.relationship_period_marks (
        tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL, period_start TIMESTAMP NOT NULL,
        pause_ends_at TIMESTAMP, terminates_at TIMESTAMP, service_failure_evidence_id TEXT,
        updated_at TIMESTAMP NOT NULL,
        PRIMARY KEY (tenant_id, relationship_id, period_start)
    )""",
    """CREATE TABLE business.relationship_price_notices (
        notice_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL,
        from_package_version_id TEXT NOT NULL, to_package_version_id TEXT NOT NULL,
        current_price_paise INTEGER NOT NULL, new_price_paise INTEGER NOT NULL,
        notified_at TIMESTAMP NOT NULL, effective_from TIMESTAMP NOT NULL, status TEXT NOT NULL,
        acknowledged_at TIMESTAMP, acknowledged_by TEXT, notice_evidence_id TEXT NOT NULL,
        UNIQUE (tenant_id, relationship_id, to_package_version_id)
    )""",
    """CREATE TABLE business.billing_profiles (
        customer_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, legal_name TEXT NOT NULL, gstin TEXT,
        state_code TEXT NOT NULL, address TEXT NOT NULL, updated_at TIMESTAMP NOT NULL
    )""",
    """CREATE TABLE business.funder_acceptances (
        acceptance_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL,
        funder_customer_id TEXT NOT NULL, acceptance_evidence_id TEXT NOT NULL, accepted_at TIMESTAMP NOT NULL,
        UNIQUE (tenant_id, relationship_id, funder_customer_id)
    )""",
    """CREATE TABLE business.tax_document_counters (
        series TEXT NOT NULL, fiscal_year TEXT NOT NULL, last_number INTEGER NOT NULL,
        PRIMARY KEY (series, fiscal_year)
    )""",
    """CREATE TABLE business.tax_documents (
        document_id TEXT PRIMARY KEY, document_kind TEXT NOT NULL, series TEXT NOT NULL,
        fiscal_year TEXT NOT NULL, sequence_no INTEGER NOT NULL, document_number TEXT NOT NULL UNIQUE,
        tenant_id TEXT, relationship_id TEXT, payer_customer_id TEXT NOT NULL,
        funder_customer_id TEXT, source_kind TEXT NOT NULL, source_reference TEXT NOT NULL,
        original_document_id TEXT, issued_at TIMESTAMP NOT NULL, supplier TEXT NOT NULL, bill_to TEXT NOT NULL,
        place_of_supply TEXT NOT NULL, supply_type TEXT NOT NULL, lines TEXT NOT NULL,
        taxable_paise INTEGER NOT NULL, cgst_paise INTEGER NOT NULL, sgst_paise INTEGER NOT NULL,
        igst_paise INTEGER NOT NULL, total_paise INTEGER NOT NULL, currency TEXT NOT NULL,
        body_digest TEXT NOT NULL,
        UNIQUE (series, fiscal_year, sequence_no), UNIQUE (document_kind, source_kind, source_reference)
    )""",
    """CREATE TABLE business.money_gate (
        gate_key TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 0, changed_by TEXT NOT NULL,
        changed_at TIMESTAMP NOT NULL, reason TEXT NOT NULL
    )""",
    """CREATE TABLE business.money_gate_audit (
        audit_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL, environment TEXT NOT NULL, changed_by TEXT NOT NULL,
        step_up INTEGER NOT NULL, reason TEXT NOT NULL, changed_at TIMESTAMP NOT NULL
    )""",
    """CREATE TABLE business.money_discrepancies (
        discrepancy_id TEXT PRIMARY KEY, kind TEXT NOT NULL, reference TEXT NOT NULL,
        expected_paise INTEGER NOT NULL, observed_paise INTEGER NOT NULL, detected_at TIMESTAMP NOT NULL,
        resolved_at TIMESTAMP, resolved_by TEXT, resolution_evidence_id TEXT
    )""",
    """CREATE UNIQUE INDEX business.money_discrepancies_open ON money_discrepancies (kind, reference)
        WHERE resolved_at IS NULL""",
)


async def install(session, *groups: tuple[str, ...]) -> None:
    for group in groups or (COMPONENT_DDL, COMMERCIAL_DDL, WC172_DDL):
        for statement in group:
            await session.execute(text(statement))
