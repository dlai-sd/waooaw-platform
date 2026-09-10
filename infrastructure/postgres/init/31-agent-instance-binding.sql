-- Implements: WC-087 Agent Instance And Multi-Agent Foundation
-- constitutional_basis: C-005, C-007, C-023, C-026, C-059

ALTER TABLE business.employment_relationships
    ADD COLUMN IF NOT EXISTS agent_instance_id UUID,
    ADD COLUMN IF NOT EXISTS professional_admission_id UUID,
    ADD COLUMN IF NOT EXISTS professional_version VARCHAR(64),
    ADD COLUMN IF NOT EXISTS agent_instance_minted_at TIMESTAMPTZ;

UPDATE business.employment_relationships
SET agent_instance_id = COALESCE(agent_instance_id, gen_random_uuid()),
    agent_instance_minted_at = COALESCE(agent_instance_minted_at, created_at);

ALTER TABLE business.employment_relationships
    ALTER COLUMN agent_instance_id SET DEFAULT gen_random_uuid(),
    ALTER COLUMN agent_instance_id SET NOT NULL,
    ALTER COLUMN agent_instance_minted_at SET DEFAULT NOW(),
    ALTER COLUMN agent_instance_minted_at SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'employment_relationships_professional_admission_fk'
    ) THEN
        ALTER TABLE business.employment_relationships
            ADD CONSTRAINT employment_relationships_professional_admission_fk
            FOREIGN KEY (professional_admission_id)
            REFERENCES business.agent_admissions (admission_id);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'employment_relationships_professional_binding_check'
    ) THEN
        ALTER TABLE business.employment_relationships
            ADD CONSTRAINT employment_relationships_professional_binding_check CHECK (
                (professional_admission_id IS NULL AND professional_version IS NULL)
                OR (professional_admission_id IS NOT NULL
                    AND professional_version IS NOT NULL
                    AND length(trim(professional_version)) BETWEEN 1 AND 64)
            );
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_employment_relationships_agent_instance
    ON business.employment_relationships (agent_instance_id);

CREATE OR REPLACE FUNCTION business.validate_agent_instance_binding()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, business
AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
        NEW.agent_instance_id IS DISTINCT FROM OLD.agent_instance_id
        OR NEW.agent_instance_minted_at IS DISTINCT FROM OLD.agent_instance_minted_at
        OR NEW.professional_admission_id IS DISTINCT FROM OLD.professional_admission_id
        OR NEW.professional_type IS DISTINCT FROM OLD.professional_type
        OR NEW.professional_version IS DISTINCT FROM OLD.professional_version
    ) THEN
        RAISE EXCEPTION 'agent instance binding is immutable';
    END IF;
    IF NEW.professional_admission_id IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM business.agent_admissions AS admission
                WHERE admission.admission_id = NEW.professional_admission_id
          AND admission.professional_type_id = NEW.professional_type
          AND admission.professional_version = NEW.professional_version
          AND admission.state = 'ACTIVE'
    ) THEN
        RAISE EXCEPTION 'agent instance requires an active matching professional admission';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS employment_relationships_agent_instance_immutable
    ON business.employment_relationships;
CREATE TRIGGER employment_relationships_agent_instance_immutable
    BEFORE INSERT OR UPDATE ON business.employment_relationships
    FOR EACH ROW EXECUTE FUNCTION business.validate_agent_instance_binding();

CREATE OR REPLACE FUNCTION business.is_active_professional_admission(
    p_admission_id UUID,
    p_professional_type TEXT,
    p_professional_version TEXT
)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, business
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM business.agent_admissions AS admission
                WHERE admission.admission_id = p_admission_id
          AND admission.professional_type_id = p_professional_type
          AND admission.professional_version = p_professional_version
          AND admission.state = 'ACTIVE'
    );
$$;

REVOKE ALL ON FUNCTION business.is_active_professional_admission(UUID, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION business.is_active_professional_admission(UUID, TEXT, TEXT) TO business_app;
