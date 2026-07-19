# CE ValidateAction — Claim Evaluators Design

**Version:** 1.0
**Date:** 2026-07-19
**Owner:** WAOOAW AI Agent — Enterprise Architect
**Constitutional Basis:** C-023 (Evidence First), C-041 (Tool Authorization), C-043 (Budget Ceiling),
                          C-048 (Non-Exploitation), C-049 (Honest Limitation), C-051 (Resource Transparency),
                          C-062 (AI Security), ADR-001 (gRPC Constitutional Engine)
**Gap Closed:** G-INSTINCT-01 (CE ValidateAction is a stub — constitution not enforced at runtime)
**Status:** SPEC COMPLETE — authorizes IB item for CE implementation sprint

---

## Problem Statement

`CE.ValidateAction` currently returns `AUTHORIZED` for every request (stub implementation).
The 67 constitutional claims are markdown files — they are documented but **not enforced** at
runtime. This means an agent could execute a C-043 budget violation, trigger a C-048 exploitation
event, or call a C-062 prohibited tool, and the Constitutional Engine would approve all three.

The constitution-as-code principle: **every claim that produces a binary AUTHORIZE/DENY decision
at runtime must have a corresponding claim evaluator registered in CE.** Claims that are
architectural constraints (e.g., C-001 Human Override) are enforced through other mechanisms
(WebSocket pre-warm, Emergency Stop Temporal signal) and do not need a ValidateAction evaluator.

---

## Evaluator Architecture

```
ValidateActionRequest arrives at CE (gRPC)
        ↓
EvaluatorRegistry.GetEvaluators(action_type, tool_name)
  — returns ordered list of evaluators that apply to this action
        ↓
For each evaluator (in order):
  EvaluationContext ctx = BuildContext(request, db, tenant)
  EvaluationResult result = evaluator.Evaluate(ctx)
  if result.Decision == DENY:
      RecordEvidence(type=VALIDATION_DENY, constitutional_basis=evaluator.ClaimId, ...)
      return ValidateActionResponse { decision=DENY, claim_id=evaluator.ClaimId, reason=result.Reason }
        ↓
All evaluators pass → AUTHORIZED
RecordEvidence(type=VALIDATION_AUTHORIZED, ...)
return ValidateActionResponse { decision=AUTHORIZED }
```

**Short-circuit on first DENY** — do not evaluate remaining claims once one denies.
**All denials recorded** — every DENY creates an evidence record in constitutional.audit_records
(C-023 Evidence First applies to denials too).

---

## Evaluator Interface (C#/.NET 9)

```csharp
// In src/constitutional-engine/Evaluators/IClaimEvaluator.cs

public interface IClaimEvaluator
{
    /// <summary>Constitutional claim ID this evaluator enforces (e.g., "C-043").</summary>
    string ClaimId { get; }

    /// <summary>
    /// Which action types trigger this evaluator.
    /// Empty = applies to ALL action types (use sparingly — only for universal claims like C-041).
    /// </summary>
    IReadOnlySet<string> ApplicableActionTypes { get; }

    /// <summary>
    /// Evaluate whether the proposed action is constitutionally permitted.
    /// Must complete within its share of the 40ms ValidateAction budget.
    /// MUST NOT perform network I/O — only DB reads via the provided context.
    /// </summary>
    Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct);
}

public record EvaluationResult(
    EvaluationDecision Decision,
    string? Reason = null,       // Required when Decision == DENY — logged in audit record
    string? EvidenceHint = null  // Optional: extra context for the evidence record
);

public enum EvaluationDecision { Authorized, Deny, Escalate }
// Escalate = action is uncertain — forward to human (Sujay) via C-049 path
```

---

## Runtime-Enforceable Claims — Evaluator Specifications

### C-041 Evaluator — Tool Authorization (Decision Space boundary)

**Claim:** Every MCP tool call requires CE.ValidateAction. Default deny.
**Action types:** `MCP_TOOL_CALL`

```
Evaluate:
  1. Read tenant's active employment contract from business.employment_contracts
  2. Read the contract's authorized_actions[] array
  3. If tool_name NOT IN authorized_actions → DENY ("Tool not in authorized Decision Space for this customer")
  4. If authorized_actions is empty or contract is SUSPENDED/TERMINATED → DENY
  5. Otherwise → AUTHORIZED
```

**DB read:** `business.employment_contracts WHERE tenant_id = ctx.TenantId AND status = 'ACTIVE'`
**Budget:** ≤10ms (single indexed read on tenant_id)

---

### C-043 Evaluator — Financial Authority Ceiling

**Claim:** Agent cannot spend above the customer-set budget limit.
**Action types:** `FINANCIAL_SPEND`, `AD_SPEND`, `SUBSCRIPTION_CHARGE`

```
Evaluate:
  1. Read customer's approved_budget from business.employment_contracts
  2. Read current period's total spend from business.billing_events WHERE tenant_id = ctx.TenantId
       AND billing_period = current_month
  3. If (current_spend + ctx.ProposedAmount) > approved_budget → DENY
       ("Financial ceiling would be exceeded: proposed ₹X, available ₹Y, ceiling ₹Z")
  4. If approved_budget is NULL (not set) → ESCALATE (customer must set a budget ceiling)
  5. Otherwise → AUTHORIZED
```

**DB reads:** 2 reads (employment_contracts + billing_events aggregate). Budget: ≤15ms.

---

### C-048 Evaluator — Information Non-Exploitation

**Claim:** Agent's expertise used only for customer benefit. Agent cannot use customer data for any
purpose other than serving that customer.
**Action types:** `DATA_EXPORT`, `CROSS_TENANT_QUERY`, `ANALYTICS_AGGREGATE`

```
Evaluate:
  1. If action_type = CROSS_TENANT_QUERY → DENY always
       ("Cross-tenant data access is absolutely prohibited — C-048")
  2. If action_type = DATA_EXPORT AND ctx.Requester is not the customer tenant → DENY
  3. If action_type = ANALYTICS_AGGREGATE AND result would identify a specific customer → DENY
  4. If ctx.ToolName includes any tool not in authorized_tools for this action type → DENY
  5. Otherwise → AUTHORIZED
```

**Budget:** ≤5ms (no DB read required — evaluates request metadata only)

---

### C-049 Evaluator — Honest Limitation Disclosure

**Claim:** Agent must disclose when it cannot deliver. Continuing to bill for a known-failing skill
is prohibited.
**Action types:** `SKILL_EXECUTION`

```
Evaluate:
  1. Query constitutional.audit_records for C-049 escalations for this
       (tenant_id, agent_type, skill_id) in last 7 days
  2. If escalation_count >= 5 in 7 days → DENY
       ("Skill has escalated 5+ times in 7 days — continuing execution would be exploitation.
         Customer must be informed. Action blocked per C-049.")
  3. Otherwise → AUTHORIZED (the skill MAY still escalate during execution — that is handled
       by the agent's skill logic, not by CE pre-validation)
```

**Note:** This evaluator prevents CONTINUED billing for a demonstrably failing skill. It does not
prevent a first attempt.
**Budget:** ≤15ms (indexed query on tenant_id + agent_type + skill_id + record_type + date)

---

### C-051 Evaluator — Token Economy (Resource Budget)

**Claim:** Customer's token/usage budget must not be exceeded without disclosure.
**Action types:** `LLM_INFERENCE`

```
Evaluate:
  1. Read customer's usage_units_remaining from business.usage_ledger WHERE tenant_id = ctx.TenantId
  2. Read estimated_units for this inference from ctx.EstimatedUsageUnits
  3. If usage_units_remaining <= 0 → DENY
       ("Usage budget exhausted — customer must recharge or upgrade plan (C-051)")
  4. If usage_units_remaining < estimated_units AND plan_tier = 'essential' → ESCALATE
       ("Nearing usage limit — customer should be notified before this inference")
  5. Otherwise → AUTHORIZED
```

**Budget:** ≤10ms (single read on usage_ledger, indexed on tenant_id)

---

### C-062 Evaluator — AI Security (Prompt Injection Defence)

**Claim:** Decision Space cannot be bypassed by conversation. Prompt injection blocked.
**Action types:** `LLM_INFERENCE` (additional check before dispatching to LLM)

```
Evaluate:
  1. Run INPUT_SANITISATION_LAYER checks (regex + LOCAL model classifier, pre-computed score):
       - Detects: "ignore previous instructions", "you are now", "DAN mode", role-play overrides
       - Score threshold: > 0.85 injection probability → DENY
  2. If ctx.MessageContent contains a tool_call outside authorized_actions → DENY
  3. If ctx.SystemPromptIntegrity != expected_sha (prompt was modified in transit) → DENY
       ("System prompt integrity check failed — possible prompt injection")
  4. Otherwise → AUTHORIZED
```

**Note:** `expected_sha` is the `git_sha` from `professional.agent_prompts` for the active prompt.
CE compares it against a HMAC of the prompt text it received. Tampered prompts fail.
**Budget:** ≤8ms (LOCAL classifier pre-computes score; CE only reads the result)

---

## Evaluator Registry — Registration Table

```csharp
// In src/constitutional-engine/Evaluators/EvaluatorRegistry.cs
// Registered at startup — order matters (fast/cheap evaluators first)

services.AddConstitutionalEvaluators(registry => {
    registry.Register<C062PromptInjectionEvaluator>();   // C-062 — cheapest, runs first (no DB)
    registry.Register<C048NonExploitationEvaluator>();   // C-048 — cheap, no DB for most cases
    registry.Register<C041ToolAuthorizationEvaluator>(); // C-041 — 1 DB read
    registry.Register<C051UsageBudgetEvaluator>();       // C-051 — 1 DB read
    registry.Register<C043FinancialCeilingEvaluator>();  // C-043 — 2 DB reads
    registry.Register<C049HonestLimitationEvaluator>();  // C-049 — most expensive, runs last
});
```

---

## Latency Budget Distribution

Total ValidateAction budget: **40ms** (per proto latency notes)

| Evaluator | Max budget | Notes |
|---|---|---|
| C-062 (Prompt Injection) | 3ms | No DB read — regex + pre-computed score |
| C-048 (Non-Exploitation) | 3ms | No DB read for most cases |
| C-041 (Tool Authorization) | 10ms | 1 DB read — indexed on tenant_id |
| C-051 (Usage Budget) | 7ms | 1 DB read — indexed on tenant_id |
| C-043 (Financial Ceiling) | 10ms | 2 DB reads |
| C-049 (Honest Limitation) | 5ms | 1 indexed DB read |
| CE overhead (gRPC, evidence write) | 2ms | |
| **Total** | **40ms** | Within budget |

All DB reads use **read replicas** (once available at 200+ customers) and **prepared statements**.
Each evaluator is independently cancellable — if one times out, it returns ESCALATE (not DENY),
ensuring constitutional caution without false positives.

---

## CCTs Required (CE Implementation Sprint)

| CCT ID | Test | Pass Criterion |
|---|---|---|
| **CCT-CE-01** | C-041: tool not in Decision Space → DENY | ValidateAction returns DENY for unlisted tool |
| **CCT-CE-02** | C-043: spend above ceiling → DENY | ValidateAction returns DENY when proposed + current > ceiling |
| **CCT-CE-03** | C-048: cross-tenant query → DENY | ValidateAction returns DENY for CROSS_TENANT_QUERY always |
| **CCT-CE-04** | C-049: 5+ escalations in 7 days → DENY | ValidateAction returns DENY for that skill after threshold |
| **CCT-CE-05** | C-051: zero usage units → DENY | ValidateAction returns DENY when budget exhausted |
| **CCT-CE-06** | C-062: prompt injection → DENY | ValidateAction returns DENY for "ignore previous instructions" input |
| **CCT-CE-07** | All DENY decisions recorded in audit_records | constitutional.audit_records has row with record_type=VALIDATION_DENY |
| **CCT-CE-08** | All AUTHORIZED decisions recorded | constitutional.audit_records has row with record_type=VALIDATION_AUTHORIZED |
| **CCT-CE-09** | Latency budget: all 6 evaluators complete in ≤40ms P99 | Measured in dev environment under concurrent load |
| **CCT-CE-10** | Prompt SHA integrity: tampered prompt → DENY | ValidateAction returns DENY when system_prompt_sha mismatch |

---

## What Must Change in ValidateActionRequest (proto)

The current proto stub's `ValidateActionRequest` needs two additional fields to support
the evaluators. These are **backward-compatible additions** (proto3):

```protobuf
message ValidateActionRequest {
  string session_id       = 1;
  string action_type      = 2;   // e.g., "MCP_TOOL_CALL", "FINANCIAL_SPEND", "LLM_INFERENCE"
  string tool_name        = 3;   // Tool being invoked (C-041)
  string proposed_by      = 4;   // Agent type + skill_id (e.g., "DMA:3")

  // New fields (ADR-001 backward-compatible additions):
  double proposed_amount  = 5;   // For C-043: proposed spend in INR (0 if not a financial action)
  int32  estimated_usage_units = 6; // For C-051: estimated LLM usage units
  string system_prompt_sha = 7;  // For C-062: SHA of system prompt used in this inference
  string message_content_hash = 8; // For C-062: hash of user message (not raw content — privacy)
  string plan_tier        = 9;   // From JWT (ADR-028): essential|professional|enterprise|steward
}
```

---

*This document authorizes the CE ValidateAction implementation IB item.*
*Owner: WAOOAW AI Agent — Enterprise Architect*
*Reviewer: Yogesh Khandge (Tier 3 — architectural change) · Ojal Khandge (C-048/C-049 evaluators)*
