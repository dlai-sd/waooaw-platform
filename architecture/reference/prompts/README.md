# Prompt Library — Standard and Governance

**Authority:** C-045 (Prompt as Constitutional Artifact); AD-018 (Prompt Versioning); DP-016 (Prompt-First Execution)
**Date:** 2026-07-09

## Prompt Governance Rules

1. Every prompt file in this directory is a governed constitutional artifact
2. Prompt IDs are permanent — `PROF_TYPE/PIPELINE_STEP/vN.N.N`
3. Breaking changes require a new major version + EA review
4. Behavioural changes (change how the agent decides) require EA review
5. Phrasing-only changes require standard PR review
6. No prompt may be activated in production without an entry in `agent_prompt_versions` table
7. Prompt files here are the SOURCE OF TRUTH; the DB table activates versions

## Prompt ID Naming Convention

```
{AGENT_TYPE}/{PIPELINE}/{STEP}/v{MAJOR}.{MINOR}.{PATCH}

Examples:
  DMA/CUSTOMER_PROFILING/OPENING_MESSAGE/v1.0.0
  DMA/MARKET_RESEARCH/SCORE_AXIS/v1.0.0
  DMA/INSTAGRAM_MARKETING/CONTENT_GENERATION/v1.0.0
  DMA/SYNTHETIC_APPROVAL/CONFIDENCE_ASSESSMENT/v1.0.0
  DMA/SELF_GOVERNANCE/DIAGNOSIS/v1.0.0
  CE/EVALUATE_POLICY/CONSTITUTIONAL_REASONING/v1.0.0
  PLATFORM_OPS/L1/HEALTH_CHECK/v1.0.0
```

## Output Schema Standard

Every agent prompt must produce a response conforming to this base schema plus type-specific extensions:

```json
{
  "reasoning_chain": "string — the agent's step-by-step reasoning before deciding",
  "decision": {
    "action_type": "string",
    "confidence_score": "float 0-1",
    "constitutional_basis": "string — semicolon-separated claim/driver IDs",
    "alternatives_considered": ["string"],
    "why_alternatives_rejected": "string"
  }
}
```

## Prompt Index

| Prompt ID | Pipeline | Step | Version | Status |
|---|---|---|---|---|
| DMA/CUSTOMER_PROFILING/OPENING_MESSAGE | Skill 0 | Profiling interview opening | v1.0.0 | ACTIVE |
| DMA/CUSTOMER_PROFILING/NEXT_QUESTION | Skill 0 | Adaptive next question selection | v1.0.0 | ACTIVE |
| DMA/CUSTOMER_PROFILING/INFERENCE_CONFIRM | Skill 0 | Infer + confirm customer attribute | v1.0.0 | ACTIVE |
| DMA/MARKET_RESEARCH/SCORE_AXIS | Skill 1 | Score one research axis 1-7 | v1.0.0 | ACTIVE |
| DMA/MARKET_RESEARCH/NEEDS_HEATMAP | Skill 1 | Derive needs heat map from findings | v1.0.0 | ACTIVE |
| DMA/MARKET_RESEARCH/MATURITY_REPORT | Skill 1 | Generate maturity report narrative | v1.0.0 | ACTIVE |
| DMA/CONTENT_STRATEGY/MONTHLY_PLAN | Skill 2 | Generate monthly content calendar | v1.0.0 | ACTIVE |
| DMA/INSTAGRAM_MARKETING/CAPTION | Skill 4 | Generate Instagram caption | v1.0.0 | ACTIVE |
| DMA/INSTAGRAM_MARKETING/HASHTAGS | Skill 4 | Select hashtags for post | v1.0.0 | ACTIVE |
| DMA/SYNTHETIC_APPROVAL/CONFIDENCE | All skills | Assess synthetic approval confidence | v1.0.0 | ACTIVE |
| DMA/SELF_GOVERNANCE/DIAGNOSIS | All skills | Diagnose goal miss root cause | v1.0.0 | ACTIVE |
| DMA/SELF_GOVERNANCE/ESCALATION | All skills | Generate escalation report | v1.0.0 | ACTIVE |
| DMA/PERFORMANCE_NARRATIVE/MONTHLY | Skill 9 | Generate monthly narrative | v1.0.0 | ACTIVE |
| CE/EVALUATE_POLICY/CONSTITUTIONAL | CE | Constitutional policy reasoning | v1.0.0 | ACTIVE |
| PLATFORM_OPS/L1/HEALTH_CHECK | Ops Agent | L1 health check reasoning | v1.0.0 | ACTIVE |
| PLATFORM_OPS/L2/INCIDENT_DIAGNOSIS | Ops Agent | L2 incident diagnosis | v1.0.0 | ACTIVE |
