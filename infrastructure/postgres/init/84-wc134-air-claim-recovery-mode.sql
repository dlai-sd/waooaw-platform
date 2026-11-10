-- Existing claims have unknown provenance and must not be reinterpreted.
ALTER TABLE ai_runtime.employment_patch_dispatch_claims
    ADD COLUMN IF NOT EXISTS recovery_mode TEXT NOT NULL DEFAULT 'UNKNOWN';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'ai_runtime.employment_patch_dispatch_claims'::regclass
          AND conname = 'employment_patch_dispatch_claims_recovery_mode_check'
    ) THEN
        ALTER TABLE ai_runtime.employment_patch_dispatch_claims
            ADD CONSTRAINT employment_patch_dispatch_claims_recovery_mode_check
            CHECK (recovery_mode IN ('UNKNOWN', 'DISABLED_INTERPRETER_V1'));
    END IF;
END
$$;
