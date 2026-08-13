ALTER TABLE business.release_recovery_markers
    ADD COLUMN IF NOT EXISTS source_generation VARCHAR(128);

CREATE INDEX IF NOT EXISTS idx_release_recovery_source_generation
    ON business.release_recovery_markers(source_generation);