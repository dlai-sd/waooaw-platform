-- WC-134: grant the Business Platform runtime role the tables its EF models read and write directly.
-- These tables were created without any grant to business_app, so on a deployment that runs the
-- real least-privilege roles (Demo) the WhatsApp webhook and operations heartbeat failed with
-- SQLSTATE 42501 while privileged test databases hid the gap.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
SET LOCAL ROLE bp_owner;

-- Operations heartbeat and every operational-signal writer.
GRANT SELECT, INSERT ON business.conversation_operational_signals TO business_app;
REVOKE UPDATE, DELETE, TRUNCATE ON business.conversation_operational_signals FROM business_app;

-- Inbound webhook replay claim and lease; claims are never deleted by the runtime.
GRANT SELECT, INSERT, UPDATE ON business.provider_event_claims TO business_app;
REVOKE DELETE, TRUNCATE ON business.provider_event_claims FROM business_app;

COMMIT;
