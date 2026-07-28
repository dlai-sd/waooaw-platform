// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator — AI Security
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)
// Spec: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) — blocks actions that carry prompt injection signals,
/// high security-risk scores, critical data-classification exposure, data-exfiltration
/// indicators, or cross-tenant boundary violations.
/// Short-circuits on the first violation; falls through to Allow only when all checks pass.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── parameter keys resolved from JSON-encoded ActionParameters ──────────────
    private const string PromptInjectionKey       = "prompt_injection_detected";
    private const string SecurityRiskKey          = "security_risk";
    private const string DataClassificationKey    = "data_classification";
    private const string ExfiltrationRiskKey      = "exfiltration_risk";
    private const string CrossTenantBoundaryKey   = "cross_tenant_boundary_violation";
    private const string PrivilegeEscalationKey   = "privilege_escalation_detected";

    // ── sentinel values ──────────────────────────────────────────────────────────
    private const string HighRisk              = "high";
    private const string CriticalClassification = "critical";

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // 1. Prompt injection — hard deny; an injected payload must never execute.
        var promptInjection = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(promptInjection, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "C-062: Prompt injection detected in action parameters — " +
                "action blocked by AI Security policy.");
        }

        // 2. High security-risk flag set by upstream risk scorer.
        var securityRisk = ctx.GetParameter(SecurityRiskKey);
        if (string.Equals(securityRisk, HighRisk, StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "C-062: Action flagged as high security risk — " +
                "denied by AI Security policy.");
        }

        // 3. Critical data classification — AI must not act on critical-tier data directly.
        var dataClassification = ctx.GetParameter(DataClassificationKey);
        if (string.Equals(dataClassification, CriticalClassification, StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "C-062: Action targets critical-classification data — " +
                "denied by AI Security policy.");
        }

        // 4. Exfiltration risk — any signal of data leaving the platform boundary is denied.
        var exfiltrationRisk = ctx.GetParameter(ExfiltrationRiskKey);
        if (string.Equals(exfiltrationRisk, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "C-062: Data exfiltration risk detected — " +
                "action blocked by AI Security policy.");
        }

        // 5. Cross-tenant boundary — PAAS boundary must not be breached across tenant scopes.
        var crossTenantViolation = ctx.GetParameter(CrossTenantBoundaryKey);
        if (string.Equals(crossTenantViolation, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "C-062: Cross-tenant boundary violation detected — " +
                "action blocked to protect PAAS isolation.");
        }

        // 6. Privilege escalation — the AI must not acquire capabilities beyond its contract.
        var privilegeEscalation = ctx.GetParameter(PrivilegeEscalationKey);
        if (string.Equals(privilegeEscalation, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny(
                "C-062: Privilege escalation attempt detected — " +
                "denied by AI Security policy.");
        }

        return Allow("C-062: No AI security violations detected — action permitted.");
    }

    // ── verdict helpers ──────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}