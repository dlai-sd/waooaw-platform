-- Implements: WC-105 R049 My Agents acquisition mode
-- constitutional_basis: C-049, C-059

ALTER TABLE business.employment_relationships
    ADD COLUMN IF NOT EXISTS acquisition_mode VARCHAR(8);

UPDATE business.employment_relationships AS relationship
SET acquisition_mode = 'TRIAL'
WHERE relationship.acquisition_mode IS NULL
  AND EXISTS (
      SELECT 1
      FROM business.relationship_trial_bindings AS trial
      WHERE trial.tenant_id = relationship.tenant_id
        AND trial.relationship_id = relationship.relationship_id
  );

UPDATE business.employment_relationships
SET acquisition_mode = 'HIRE'
WHERE acquisition_mode IS NULL
  AND state IN (
      'CONFIGURING',
      'CONTRACT_PENDING_ACCEPTANCE',
      'CONTRACT_ACCEPTED_PENDING_PAYMENT',
      'ACTIVATION_PENDING',
      'ACTIVE',
      'PAUSED',
      'STOPPED_EMERGENCY',
      'TERMINATED'
  );

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'employment_relationships_acquisition_mode_check'
          AND conrelid = 'business.employment_relationships'::regclass
    ) THEN
        ALTER TABLE business.employment_relationships
            ADD CONSTRAINT employment_relationships_acquisition_mode_check
            CHECK (acquisition_mode IS NULL OR acquisition_mode IN ('TRIAL', 'HIRE'));
    END IF;
END;
$$;