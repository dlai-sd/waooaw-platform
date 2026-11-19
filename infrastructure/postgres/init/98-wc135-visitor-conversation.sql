-- Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R001, WC135-R007, WC135-R008, WC135-R009, WC135-R014
-- Constitutional basis: C-009, C-023, C-026, C-048, C-049, C-059, C-063
-- Visitor conversation state, protected lead record, transcript and handoff references.
-- Additive and idempotent: Demo re-applies every init file at BP startup.

BEGIN;

CREATE TABLE IF NOT EXISTS business.visitor_sessions (
    session_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    subject_hash CHAR(64) NOT NULL CHECK (subject_hash ~ '^[0-9a-f]{64}$'),
    channel VARCHAR(12) NOT NULL CHECK (channel IN ('WHATSAPP', 'WEB', 'MOBILE', 'SIMULATION')),
    state VARCHAR(24) NOT NULL CHECK (
        state IN ('NEW', 'CONSENT_PENDING', 'DISCOVER', 'QUALIFY', 'SHOW_VALUE',
                  'OTHER_PROFESSIONALS', 'HANDOFF', 'STOPPED')
    ),
    outcome VARCHAR(16) NOT NULL DEFAULT 'NONE' CHECK (
        outcome IN ('NONE', 'LEAD', 'INTENT', 'FULL_SUCCESS', 'OPT_OUT')
    ),
    content_version VARCHAR(64) NOT NULL,
    consent_at TIMESTAMPTZ,
    consent_notice_version VARCHAR(32),
    consent_evidence_id UUID,
    lead_id UUID,
    turn_count INTEGER NOT NULL DEFAULT 0 CHECK (turn_count >= 0),
    turns_to_first_value INTEGER CHECK (turns_to_first_value IS NULL OR turns_to_first_value > 0),
    nudges INTEGER NOT NULL DEFAULT 0 CHECK (nudges >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE (tenant_id, subject_hash)
);
CREATE INDEX IF NOT EXISTS idx_visitor_sessions_tenant_updated
    ON business.visitor_sessions (tenant_id, updated_at);

CREATE TABLE IF NOT EXISTS business.visitor_turns (
    session_id UUID NOT NULL REFERENCES business.visitor_sessions (session_id) ON DELETE CASCADE,
    sequence BIGINT NOT NULL CHECK (sequence >= 0),
    tenant_id UUID NOT NULL,
    message_id UUID NOT NULL,
    idempotency_key UUID NOT NULL,
    request_hash CHAR(64) NOT NULL CHECK (request_hash ~ '^[0-9a-f]{64}$'),
    visitor_content_type VARCHAR(8) NOT NULL CHECK (visitor_content_type IN ('TEXT', 'CHOICE')),
    visitor_text_protected TEXT,
    visitor_choice_id VARCHAR(64),
    reply_json JSONB NOT NULL,
    state_after VARCHAR(24) NOT NULL,
    outcome_after VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (session_id, sequence),
    UNIQUE (session_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_visitor_turns_tenant_created
    ON business.visitor_turns (tenant_id, created_at);

CREATE TABLE IF NOT EXISTS business.visitor_leads (
    lead_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    subject_hash CHAR(64) NOT NULL CHECK (subject_hash ~ '^[0-9a-f]{64}$'),
    phone_protected TEXT,
    business_domain VARCHAR(64),
    business_text VARCHAR(120),
    city VARCHAR(80),
    goal_code VARCHAR(48),
    contact_name_protected TEXT,
    contact_email_protected TEXT,
    source_channel VARCHAR(12) NOT NULL CHECK (
        source_channel IN ('WHATSAPP', 'WEB', 'MOBILE', 'SIMULATION')
    ),
    consent_reference UUID NOT NULL,
    status VARCHAR(12) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'INTENT', 'CONVERTED')),
    acquisition_intent_id UUID,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT visitor_leads_converted_has_intent
        CHECK (status <> 'CONVERTED' OR acquisition_intent_id IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_visitor_leads_open_subject
    ON business.visitor_leads (tenant_id, subject_hash)
    WHERE status <> 'CONVERTED';
CREATE INDEX IF NOT EXISTS idx_visitor_leads_tenant_updated
    ON business.visitor_leads (tenant_id, updated_at);

CREATE TABLE IF NOT EXISTS business.visitor_handoff_references (
    reference_hash CHAR(64) PRIMARY KEY CHECK (reference_hash ~ '^[0-9a-f]{64}$'),
    tenant_id UUID NOT NULL,
    lead_id UUID NOT NULL REFERENCES business.visitor_leads (lead_id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    tapped_at TIMESTAMPTZ,
    consumed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_visitor_handoff_tenant_expiry
    ON business.visitor_handoff_references (tenant_id, expires_at);

ALTER TABLE business.whatsapp_guest_sessions
    ADD COLUMN IF NOT EXISTS resumed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resume_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS business.visitor_render_hints (
    tenant_id UUID NOT NULL,
    message_id UUID NOT NULL,
    reply_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_visitor_render_hints_created
    ON business.visitor_render_hints (tenant_id, created_at);

DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'visitor_sessions', 'visitor_turns', 'visitor_leads', 'visitor_handoff_references',
        'visitor_render_hints'
    ]
    LOOP
        EXECUTE format('ALTER TABLE business.%I ENABLE ROW LEVEL SECURITY', table_name);
        EXECUTE format('ALTER TABLE business.%I FORCE ROW LEVEL SECURITY', table_name);
        EXECUTE format('DROP POLICY IF EXISTS %I ON business.%I', table_name || '_tenant_isolation', table_name);
        EXECUTE format(
            'CREATE POLICY %I ON business.%I USING (tenant_id = NULLIF(current_setting(%L, TRUE), %L)::UUID) '
            || 'WITH CHECK (tenant_id = NULLIF(current_setting(%L, TRUE), %L)::UUID)',
            table_name || '_tenant_isolation', table_name,
            'app.current_tenant_id', '', 'app.current_tenant_id', ''
        );
        EXECUTE format('REVOKE ALL ON business.%I FROM PUBLIC', table_name);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON business.%I TO business_app', table_name);
    END LOOP;
END
$$;

COMMIT;
