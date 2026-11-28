# Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R015, WC176-R016
# Constitutional basis: C-023, C-059, C-063
"""SQLite twins of the WC-176 capture and renewal tables (99zzzzzzzz-wc176-02-billing-capture-invoice.sql)."""

from __future__ import annotations


def capture_ddl(schema: str = "") -> tuple[str, ...]:
    prefix = f"{schema}." if schema else ""
    return (
        f"""CREATE TABLE {prefix}razorpay_webhook_events (
            event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, payment_id TEXT, payload_digest TEXT NOT NULL,
            received_at TIMESTAMP NOT NULL, processed_at TIMESTAMP, outcome TEXT
        )""",
        f"""CREATE TABLE {prefix}razorpay_captures (
            payment_id TEXT PRIMARY KEY, order_id TEXT NOT NULL DEFAULT '', amount_paise INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'INR', notes TEXT NOT NULL DEFAULT '{{}}', source TEXT NOT NULL,
            status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, last_error TEXT,
            first_seen_at TIMESTAMP NOT NULL, completed_at TIMESTAMP, refund_due_at TIMESTAMP, refund_reference TEXT
        )""",
        f"""CREATE TABLE {prefix}renewal_collections (
            tenant_id TEXT NOT NULL, relationship_id TEXT NOT NULL, period_start TIMESTAMP NOT NULL, order_id TEXT,
            amount_paise INTEGER NOT NULL, status TEXT NOT NULL, created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL, PRIMARY KEY (tenant_id, relationship_id, period_start)
        )""",
    )
