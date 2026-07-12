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
| TRADING/MARKET_ANALYSIS/TRADE_SETUP | Skill 1 | Identify trade setup from market data | v1.0.0 | ACTIVE |
| TRADING/RISK_MANAGEMENT/LOSS_LIMIT_ALERT | Skill 3 | Halt/warn on risk threshold breach | v1.0.0 | ACTIVE |
| TRADING/PERFORMANCE/SESSION_REPORT | Skill 5 | End-of-session P&L narrative | v1.0.0 | ACTIVE |
| AGRI/WEATHER_ADVISORY/FARMER_ALERT | Skill 1 | Translate weather to farmer advice (C-042) | v1.0.0 | ACTIVE |
| AGRI/CROP_HEALTH/MORNING_CHECKIN | Skill 2 | Morning crop health check-in | v1.0.0 | ACTIVE |
| AGRI/MANDI_PRICE/SELL_TIMING | Skill 3 | Optimal sell timing advisory | v1.0.0 | ACTIVE |
| AGRI/CROP_PLANNING/NEXT_SEASON | Skill 4 | Next season crop recommendation | v1.0.0 | ACTIVE |
| TRADING/ONBOARDING/PROFILE_SETUP | Onboarding | 5-phase Decision Space configuration | v1.0.0 | ACTIVE |
| TRADING/EXECUTION/ESCALATION_DECISION | Skill 2 | PAAS session escalation (UNCERTAIN action) | v1.0.0 | ACTIVE |
| TRADING/CRYPTO/REBALANCE_DECISION | Skill 4 | Crypto allocation rebalancing decision | v1.0.0 | ACTIVE |
| AGRI/ONBOARDING/OPENING_MESSAGE | Onboarding | First WhatsApp contact greeting | v1.0.0 | ACTIVE |
| AGRI/ONBOARDING/INFERENCE_CONFIRM | Onboarding | Confirm district/crop profile inferences | v1.0.0 | ACTIVE |
| AGRI/HINT_SYSTEM/WEEKLY_HINT | Skill 5 | 5-lens weekly hint convergence engine | v1.0.0 | ACTIVE |
| TRADING/SELF_GOVERNANCE/DIAGNOSIS | Self-Governance | Monthly goal miss + C-049 assessment | v1.0.0 | ACTIVE |
| AGRI/SELF_GOVERNANCE/DIAGNOSIS | Self-Governance | Monthly advisory effectiveness + C-049 | v1.0.0 | ACTIVE |
| DMA/STRATEGIC/SKILL_ACTIVATION_PLAN | Strategic Cognition | Post-maturity report: skill sequence planning (C-050) | v1.0.0 | ACTIVE |
| DMA/STRATEGIC/PERFORMANCE_ASSESSMENT | Strategic Cognition | Monthly portfolio health assessment (C-050) | v1.0.0 | ACTIVE |
| TRADING/STRATEGIC/SESSION_PREP | Strategic Cognition | Pre-session market regime alignment check (C-050) | v1.0.0 | ACTIVE |
| TRADING/STRATEGIC/MONTHLY_PORTFOLIO_ASSESSMENT | Strategic Cognition | Monthly trading strategy health (C-050) | v1.0.0 | ACTIVE |
| AGRI/STRATEGIC/SEASONAL_ADVISORY_PLAN | Strategic Cognition | Seasonal skill activation plan per farmer (C-050) | v1.0.0 | ACTIVE |
| AGRI/STRATEGIC/ADVISORY_EFFECTIVENESS_REVIEW | Strategic Cognition | Monthly/harvest advisory portfolio assessment (C-050) | v1.0.0 | ACTIVE |
| DMA/TOKEN_ECONOMY/USAGE_SUMMARY | Token Economy | Budget status in business language for portal + WhatsApp (C-051) | v1.0.0 | ACTIVE |
| TRADING/TOKEN_ECONOMY/USAGE_SUMMARY | Token Economy | Trading session dashboard usage summary (C-051) | v1.0.0 | ACTIVE |
| AGRI/TOKEN_ECONOMY/USAGE_SUMMARY | Token Economy | Budget status in farmer's language — Marathi WhatsApp voice (C-051) | v1.0.0 | ACTIVE |
| PLATFORM/TOKEN_ECONOMY/MESSAGE_CLASSIFIER | Token Economy | Message Classification Gate — LOCAL tier invariant (C-051, AD-022) | v1.0.0 | ACTIVE |
| PLATFORM/BOUNDARY/OFF_TOPIC_REDIRECT | Off-Topic Boundary | Graceful professional deflection + specific monitoring hook — 3-attempt graduation (C-036, C-037, C-048) | v1.0.0 | ACTIVE |
| DMA/ROUTING/SKILL_INTENT_ROUTER | Skill Intelligence Router | LOCAL-tier intent classification → skill routing plan for DMA agent (C-054) | v1.0.0 | ACTIVE |
| AGRI/ROUTING/SKILL_INTENT_ROUTER | Skill Intelligence Router | LOCAL-tier intent classification → skill routing plan for Agricultural agent (C-054) | v1.0.0 | ACTIVE |
| TRADING/ROUTING/SKILL_INTENT_ROUTER | Skill Intelligence Router | LOCAL-tier intent classification → skill routing plan for Trading agent (C-054) | v1.0.0 | ACTIVE |
| DMA/SIGNAL/PROACTIVE_ALERT | Signal Intelligence | Converts competitor/analytics/review signal into actionable portal notification (C-053) | v1.0.0 | ACTIVE |
| AGRI/SIGNAL/PROACTIVE_ALERT | Signal Intelligence | Converts weather/price/pest signal into farmer-vocabulary WhatsApp voice alert (C-053) | v1.0.0 | ACTIVE |
| TRADING/SIGNAL/PROACTIVE_ALERT | Signal Intelligence | Converts VIX/broker-auth/session signal into PAAS pre-session alert (C-053) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/MASTER_THEME_PROPOSAL | Campaign Theme Engine | Proposes master campaign brief: theme, window, target outcome, weekly cascade, platform mix (C-055) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/WEEKLY_THEME_CASCADE | Campaign Theme Engine | Decomposes master campaign into weekly sub-themes with narrative hooks + emotional targets (C-055) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT | Campaign Theme Engine | Creates platform-native content variant (caption+image+audio) from weekly sub-theme (C-055) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/SCR_QUALITY_CHECK | Synthetic Content Reviewer | SCR Check 5 — quality assessment of content for professional standard (C-055, Check 5 only) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/CAMPAIGN_DIGEST | Campaign Theme Engine | Weekly campaign performance digest + next-week preview for customer (C-055) | v1.0.0 | ACTIVE |
| DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH | Platform Intelligence | Research-driven platform selection recommendation for customer domain + target audience (DP-024) | v1.0.0 | ACTIVE |
| DMA/ONBOARDING/PROFESSIONAL_INTAKE_OPENING | AI Agency Onboarding | Expertise-first opening: agent demonstrates market knowledge before asking configuration (C-057) | v1.0.0 | ACTIVE |
| DMA/ONBOARDING/COMPETITIVE_POSITIONING | AI Agency Onboarding | Honest comparison of WAOOAW DMA vs traditional agencies when prospect asks (C-057 + C-049) | v1.0.0 | ACTIVE |
| DMA/PORTFOLIO/PORTFOLIO_CLAIM_GENERATION | AI Agency Portfolio | Generates accurate portfolio claims from dma_performance_portfolio Tier 3 data (C-057 + C-002) | v1.0.0 | ACTIVE |

**Total active prompts: 61** (v0.44.0 — 58 + 3 new agency onboarding/portfolio prompts)
| AGRI/ROUTING/SKILL_INTENT_ROUTER | Skill Intelligence Router | LOCAL-tier intent classification → skill routing plan for Agricultural agent (C-054) | v1.0.0 | ACTIVE |
| TRADING/ROUTING/SKILL_INTENT_ROUTER | Skill Intelligence Router | LOCAL-tier intent classification → skill routing plan for Trading agent (C-054) | v1.0.0 | ACTIVE |
| DMA/SIGNAL/PROACTIVE_ALERT | Signal Intelligence | Converts competitor/analytics/review signal into actionable portal notification (C-053) | v1.0.0 | ACTIVE |
| AGRI/SIGNAL/PROACTIVE_ALERT | Signal Intelligence | Converts weather/price/pest signal into farmer-vocabulary WhatsApp voice alert (C-053) | v1.0.0 | ACTIVE |
| TRADING/SIGNAL/PROACTIVE_ALERT | Signal Intelligence | Converts VIX/broker-auth/session signal into PAAS pre-session alert (C-053) | v1.0.0 | ACTIVE |

**Total active prompts: 52** (v0.35.0 — includes SIR routing prompts + SIL proactive alert prompts)
=======
| DMA/CAMPAIGN/MASTER_THEME_PROPOSAL | Campaign Theme Engine | Proposes master campaign brief: theme, window, target outcome, weekly cascade, platform mix (C-055) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/WEEKLY_THEME_CASCADE | Campaign Theme Engine | Decomposes master campaign into weekly sub-themes with narrative hooks + emotional targets (C-055) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/PLATFORM_CONTENT_VARIANT | Campaign Theme Engine | Creates platform-native content variant (caption+image+audio) from weekly sub-theme (C-055) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/SCR_QUALITY_CHECK | Synthetic Content Reviewer | SCR Check 5 — quality assessment of content for professional standard (C-055, Check 5 only) | v1.0.0 | ACTIVE |
| DMA/CAMPAIGN/CAMPAIGN_DIGEST | Campaign Theme Engine | Weekly campaign performance digest + next-week preview for customer (C-055) | v1.0.0 | ACTIVE |
| DMA/PLATFORM/PLATFORM_INTELLIGENCE_RESEARCH | Platform Intelligence | Research-driven platform selection recommendation for customer domain + target audience (DP-024) | v1.0.0 | ACTIVE |

**Total active prompts: 52** (v0.34.0 — on main branch; +7 (SIR/SIL) in PR #5 + 6 (Campaign) in PR #6 = 58 when both merged)
>>>>>>> 699f049 (constitutional(dma): C-055 Campaign Theme Engine + SCR + Platform Intelligence (DMA v2.5, v0.39.0))
