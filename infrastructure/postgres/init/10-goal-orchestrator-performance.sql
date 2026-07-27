-- Implements: architecture/reference/goal-orchestrator/component-contracts.md §5
-- Constitutional basis: C-069 (Platform Self-Improvement), C-059 (Traceability)
-- Schema: institutional
-- Phase: GOAL-002 Phase C

-- Goal Orchestrator routing performance table.
-- Every routing decision is recorded here.
-- The go_routing_scores view drives Cat. 10 (Routing Intelligence) model selection.

CREATE TABLE IF NOT EXISTS institutional.goal_orchestrator_performance (
    id                          BIGSERIAL PRIMARY KEY,
    goal_id                     TEXT NOT NULL,
    goal_type                   TEXT NOT NULL,      -- nature classification from GEOM G-3
    institution_id              TEXT NOT NULL,       -- INST-NNN that was routed to
    routing_decision_id         TEXT,               -- MDR record_id for Cat. 10 invocation

    -- Routing outcome signals (updated after Goal Closure)
    delivered_on_sla            BOOLEAN,
    cascade_triggered           BOOLEAN     DEFAULT FALSE,
    cascade_level_reached       INTEGER,            -- 1, 2, 3, or NULL if no cascade
    cascade_resolved            BOOLEAN,
    founder_escalated           BOOLEAN     DEFAULT FALSE,

    -- Understanding quality (updated after Registrant confirms SC)
    understanding_accuracy      FLOAT,              -- 0-1: did draft SC match intent?
    clarifications_needed       INTEGER     DEFAULT 0,

    -- Research quality — Level 2
    research_query_used         BOOLEAN     DEFAULT FALSE,
    research_resolution_rate    FLOAT,              -- 0-1: did research enable L2 success?

    -- Decision brief quality — Founder escalation
    founder_asked_followup      BOOLEAN     DEFAULT FALSE,  -- needed more info before deciding?

    -- Composite routing score (recomputed daily by C-069 loop)
    routing_score               FLOAT,

    recorded_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_go_perf_inst_type
    ON institutional.goal_orchestrator_performance (institution_id, goal_type);

CREATE INDEX IF NOT EXISTS idx_go_perf_goal
    ON institutional.goal_orchestrator_performance (goal_id);

CREATE INDEX IF NOT EXISTS idx_go_perf_recorded
    ON institutional.goal_orchestrator_performance (recorded_at DESC);

-- Materialised view: current Institution routing scores per Goal type.
-- Refreshed every 48 hours by C-069 self-improvement loop.
-- Used by Cat. 10 (Routing Intelligence) to select optimal Institutions.
CREATE MATERIALIZED VIEW IF NOT EXISTS institutional.go_routing_scores AS
SELECT
    institution_id,
    goal_type,
    COUNT(*)                                                    AS total_routings,
    AVG(CASE WHEN delivered_on_sla     THEN 1.0 ELSE 0.0 END)  AS sla_rate,
    AVG(CASE WHEN NOT cascade_triggered THEN 1.0 ELSE 0.0 END) AS no_cascade_rate,
    AVG(CASE WHEN NOT COALESCE(founder_escalated, FALSE)
             THEN 1.0 ELSE 0.0 END)                             AS no_escalation_rate,
    -- Weighted composite routing score
    (  AVG(CASE WHEN delivered_on_sla     THEN 1.0 ELSE 0.0 END) * 0.50
     + AVG(CASE WHEN NOT cascade_triggered THEN 1.0 ELSE 0.0 END) * 0.35
     + AVG(CASE WHEN NOT COALESCE(founder_escalated, FALSE)
               THEN 1.0 ELSE 0.0 END) * 0.15
    )                                                            AS routing_score
FROM institutional.goal_orchestrator_performance
WHERE recorded_at > NOW() - INTERVAL '48 hours'
  AND delivered_on_sla IS NOT NULL    -- only completed routings
GROUP BY institution_id, goal_type;

CREATE UNIQUE INDEX IF NOT EXISTS idx_go_routing_scores_pk
    ON institutional.go_routing_scores (institution_id, goal_type);

-- Refresh function (called by daily C-069 maintenance job)
CREATE OR REPLACE FUNCTION institutional.refresh_go_routing_scores()
RETURNS VOID
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY institutional.go_routing_scores;
END;
$$;

COMMENT ON TABLE institutional.goal_orchestrator_performance IS
    'GO-Intelligence performance log. Every routing decision recorded here. '
    'Drives Cat. 10 Routing Intelligence self-improvement (C-069). '
    'Implements: architecture/reference/goal-orchestrator/component-contracts.md §5';
