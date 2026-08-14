# Test Champion Prompt Catalogue v1.0

All prompts treat tool output as immutable input, never fabricate results, and return BLOCKED or
UNKNOWN when evidence is absent. Raw customer evidence uses approved India-resident routing only.

| Prompt ID | Category | Tier | Change | Required output | Evaluator |
|---|---|---|---|---|---|
| `QA/SKILL_ACTIVATION_PLAN` | DEEP_REASONING | FRONTIER | STRATEGIC | strategic_reasoning_chain, skill_activation_sequence, c050_strategic_intent, c048_check, c049_honest_assessment | FORMAT, JSON, EVIDENCE, owner review |
| `QA/PERFORMANCE_ASSESSMENT` | REVIEW_EVALUATION | MID_TIER | BEHAVIOURAL | portfolio_health, skill_assessment, strategic_recommendation, c049_honest_assessment, customer_narrative | FORMAT, JSON, EVIDENCE |
| `QA/CAMPAIGN_DESIGN` | DEEP_REASONING | FRONTIER | STRATEGIC | obligation_map, risks, skills, stop_conditions, unknowns | FORMAT, JSON, EVIDENCE, owner review |
| `QA/FAILURE_TRIAGE` | ROUTING_INTELLIGENCE | LOCAL | CLASSIFICATION | clusters, raw_evidence_refs, reproduction, confidence, unknowns | FORMAT, JSON, EVIDENCE |
| `QA/EVIDENCE_SYNTHESIS` | REVIEW_EVALUATION | MID_TIER | BEHAVIOURAL | baseline, checks, immutable_refs, limitations, result | FORMAT, JSON, HASH, EVIDENCE |
| `QA/GATE_RECOMMENDATION` | REVIEW_EVALUATION | FRONTIER | BREAKING | PASS_BLOCK_CONDITIONAL_UNKNOWN, obligations, defects, independent_decision_required | FORMAT, JSON, HASH, EVIDENCE, independent review |
| `QA/SKILL_INTENT_ROUTER` | ROUTING_INTELLIGENCE | LOCAL | CLASSIFICATION | primary_skill, contributing_skills, gap_detected | FORMAT, JSON |
| `QA/USAGE_SUMMARY` | DOCUMENTATION | LOCAL | USAGE_SUMMARY | deterministic_runs, mid_units, frontier_units, remaining_budget, action | FORMAT, JSON |

Common system instruction: use only supplied approved records; quote raw evidence by hash/reference;
never rewrite deterministic status; expose conflicts; no production fix, PR approval, merge,
activation, target invention, or risk acceptance.
