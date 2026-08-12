-- Implements: architecture/reference/data/wc062-voice-data-contract.md § Migration Decision
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063

CREATE TABLE IF NOT EXISTS business.voice_contribution_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    actor_participant_id UUID NOT NULL,
    contribution_id UUID,
    schema_version VARCHAR(16) NOT NULL DEFAULT '1.0',
    state VARCHAR(24) NOT NULL DEFAULT 'CREATED',
    selected_locale VARCHAR(16) NOT NULL,
    consent_version VARCHAR(64) NOT NULL,
    current_transcript_version INTEGER NOT NULL DEFAULT 0,
    accepted_transcript_id UUID,
    evidence_reference UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT voice_sessions_scope_unique UNIQUE (tenant_id, relationship_id, session_id),
    CONSTRAINT voice_sessions_contribution_unique UNIQUE (tenant_id, contribution_id),
    CONSTRAINT voice_sessions_relationship_fk FOREIGN KEY (tenant_id, relationship_id)
        REFERENCES business.employment_relationships (tenant_id, relationship_id),
    CONSTRAINT voice_sessions_schema_check CHECK (schema_version = '1.0'),
    CONSTRAINT voice_sessions_locale_check CHECK (selected_locale IN ('en-IN', 'hi-IN', 'mr-IN')),
    CONSTRAINT voice_sessions_state_check CHECK (state IN (
        'CREATED', 'UPLOADING', 'UPLOADED', 'TRANSCRIBING', 'REVIEW_REQUIRED',
        'READY_TO_SEND', 'SENDING', 'RECORDED', 'CANCELLED', 'REJECTED',
        'QUARANTINED', 'UNAVAILABLE', 'UNKNOWN', 'STOPPED'
    ))
);

CREATE TABLE IF NOT EXISTS business.voice_audio_payloads (
    audio_payload_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    session_id UUID NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    declared_media_type VARCHAR(64) NOT NULL,
    detected_media_type VARCHAR(64) NOT NULL,
    size_bytes BIGINT NOT NULL,
    duration_milliseconds INTEGER NOT NULL,
    scan_state VARCHAR(16) NOT NULL,
    payload_reference TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    retain_until TIMESTAMPTZ NOT NULL,
    erased_at TIMESTAMPTZ,
    CONSTRAINT voice_audio_session_unique UNIQUE (tenant_id, session_id),
    CONSTRAINT voice_audio_session_fk FOREIGN KEY (session_id)
        REFERENCES business.voice_contribution_sessions (session_id),
    CONSTRAINT voice_audio_hash_check CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT voice_audio_size_check CHECK (size_bytes BETWEEN 0 AND 15728640),
    CONSTRAINT voice_audio_duration_check CHECK (duration_milliseconds BETWEEN 0 AND 180000),
    CONSTRAINT voice_audio_scan_check CHECK (scan_state IN ('PENDING', 'CLEAN', 'QUARANTINED'))
);

CREATE TABLE IF NOT EXISTS business.voice_transcript_versions (
    transcript_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    session_id UUID NOT NULL,
    audio_payload_id UUID NOT NULL,
    version INTEGER NOT NULL,
    predecessor_transcript_id UUID,
    source VARCHAR(32) NOT NULL,
    locale VARCHAR(16) NOT NULL,
    locale_source VARCHAR(16) NOT NULL,
    confidence NUMERIC(5,4),
    confidence_band VARCHAR(16) NOT NULL,
    text_ciphertext TEXT NOT NULL,
    text_sha256 CHAR(64) NOT NULL,
    contract_version VARCHAR(16) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    erased_at TIMESTAMPTZ,
    CONSTRAINT voice_transcript_version_unique UNIQUE (tenant_id, session_id, version),
    CONSTRAINT voice_transcript_session_fk FOREIGN KEY (session_id)
        REFERENCES business.voice_contribution_sessions (session_id),
    CONSTRAINT voice_transcript_audio_fk FOREIGN KEY (audio_payload_id)
        REFERENCES business.voice_audio_payloads (audio_payload_id),
    CONSTRAINT voice_transcript_predecessor_fk FOREIGN KEY (predecessor_transcript_id)
        REFERENCES business.voice_transcript_versions (transcript_id),
    CONSTRAINT voice_transcript_hash_check CHECK (text_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT voice_transcript_version_check CHECK (version >= 1),
    CONSTRAINT voice_transcript_confidence_check CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    CONSTRAINT voice_transcript_band_check CHECK (confidence_band IN ('HIGH', 'REVIEW', 'LOW', 'UNAVAILABLE'))
);

CREATE TABLE IF NOT EXISTS business.voice_idempotency_outcomes (
    outcome_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    actor_participant_id UUID NOT NULL,
    session_id UUID,
    operation VARCHAR(16) NOT NULL,
    idempotency_key UUID NOT NULL,
    request_sha256 CHAR(64) NOT NULL,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT voice_idempotency_scope_unique UNIQUE (
        tenant_id, relationship_id, actor_participant_id, operation, idempotency_key
    ),
    CONSTRAINT voice_idempotency_hash_check CHECK (request_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS business.voice_erasure_tombstones (
    tombstone_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    relationship_id UUID NOT NULL,
    contribution_id UUID NOT NULL,
    actor_participant_id UUID NOT NULL,
    scope VARCHAR(32) NOT NULL,
    reason_class VARCHAR(32) NOT NULL,
    evidence_reference UUID NOT NULL,
    erased_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT voice_erasure_scope_unique UNIQUE (tenant_id, contribution_id, scope),
    CONSTRAINT voice_erasure_scope_check CHECK (scope IN ('AUDIO', 'TRANSCRIPT', 'AUDIO_AND_TRANSCRIPT'))
);

ALTER TABLE business.voice_contribution_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.voice_contribution_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE business.voice_audio_payloads ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.voice_audio_payloads FORCE ROW LEVEL SECURITY;
ALTER TABLE business.voice_transcript_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.voice_transcript_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE business.voice_idempotency_outcomes ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.voice_idempotency_outcomes FORCE ROW LEVEL SECURITY;
ALTER TABLE business.voice_erasure_tombstones ENABLE ROW LEVEL SECURITY;
ALTER TABLE business.voice_erasure_tombstones FORCE ROW LEVEL SECURITY;

CREATE POLICY voice_sessions_tenant_isolation ON business.voice_contribution_sessions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY voice_audio_tenant_isolation ON business.voice_audio_payloads
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY voice_transcripts_tenant_isolation ON business.voice_transcript_versions
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY voice_idempotency_tenant_isolation ON business.voice_idempotency_outcomes
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);
CREATE POLICY voice_erasure_tenant_isolation ON business.voice_erasure_tombstones
USING (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID)
WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', TRUE), '')::UUID);

GRANT SELECT, INSERT, UPDATE ON business.voice_contribution_sessions TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.voice_audio_payloads TO business_app;
GRANT SELECT, INSERT, UPDATE ON business.voice_transcript_versions TO business_app;
GRANT SELECT, INSERT ON business.voice_idempotency_outcomes TO business_app;
GRANT SELECT, INSERT ON business.voice_erasure_tombstones TO business_app;