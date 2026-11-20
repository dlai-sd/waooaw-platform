-- Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-07
-- Constitutional basis: C-059, C-088, C-089, C-091
-- WC-136: voice and template-message catalogue entries are inserted pending Founder authorization.
-- No raw cost is invented: every value is 0 until the Founder enters it through the Pricing Console.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';
DO $owner$
BEGIN
    IF NOT pg_has_role(session_user, 'bp_owner', 'SET') THEN
        EXECUTE format('GRANT bp_owner TO %I', session_user);
        PERFORM set_config('waooaw.wc136_catalogue_bp_owner_granted', 'true', true);
    END IF;
END
$owner$;
SET LOCAL ROLE bp_owner;

INSERT INTO institutional.thread_catalog
    (thread_id, display_name, provider, unit_description,
     raw_cost_inr_paise, fx_buffer_pct, operational_overhead_pct, risk_premium_pct,
     is_platform_thread, applicable_agents, status, founder_authorized_at,
     founder_authorized_by, notes)
VALUES
('stt_audio_minute', 'Speech to text', 'To be set by Founder', 'Per audio minute',
 0, 0, 0, 0, TRUE, '{}', 'PENDING_FOUNDER_AUTH', NULL, NULL,
 'value to be entered through the Pricing Console by the Founder'),
('tts_character_1k', 'Text to speech', 'To be set by Founder', 'Per 1,000 characters',
 0, 0, 0, 0, TRUE, '{}', 'PENDING_FOUNDER_AUTH', NULL, NULL,
 'value to be entered through the Pricing Console by the Founder'),
('whatsapp_template_utility', 'WhatsApp utility template message', 'To be set by Founder',
 'Per message', 0, 0, 0, 0, TRUE, '{}', 'PENDING_FOUNDER_AUTH', NULL, NULL,
 'value to be entered through the Pricing Console by the Founder'),
('whatsapp_template_marketing', 'WhatsApp marketing template message', 'To be set by Founder',
 'Per message', 0, 0, 0, 0, TRUE, '{}', 'PENDING_FOUNDER_AUTH', NULL, NULL,
 'value to be entered through the Pricing Console by the Founder'),
('whatsapp_template_authentication', 'WhatsApp authentication template message',
 'To be set by Founder', 'Per message', 0, 0, 0, 0, TRUE, '{}', 'PENDING_FOUNDER_AUTH', NULL, NULL,
 'value to be entered through the Pricing Console by the Founder')
ON CONFLICT (thread_id) DO NOTHING;

RESET ROLE;
DO $owner$
BEGIN
    IF current_setting('waooaw.wc136_catalogue_bp_owner_granted', true) = 'true' THEN
        EXECUTE format('REVOKE bp_owner FROM %I', session_user);
    END IF;
END
$owner$;
COMMIT;
