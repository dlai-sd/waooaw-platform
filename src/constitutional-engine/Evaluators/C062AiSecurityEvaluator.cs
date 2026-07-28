// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator — AI Security
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) — denies any action that carries a detected prompt injection,
/// high security risk, critical data classification, high exfiltration risk, a cross-tenant
/// boundary violation, or a detected privilege escalation signal.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── parameter keys (extracted from EvaluationContext.ActionParameters JSON) ──────────────
    private const string PromptInjectionKey      = "prompt_injection_detected";
    private const string SecurityRiskKey         = "security_risk";
    private const string DataClassificationKey   = "data_classification";
    private const string ExfiltrationRiskKey     = "exfiltration_risk";
    private const string CrossTenantBoundaryKey  = "cross_tenant_boundary_violation";
    private const string PrivilegeEscalationKey  = "privilege_escalation_detected";

    // ── sentinel values ───────────────────────────────────────────────────────────────────────
    private const string HighRisk               = "high";
    private const string CriticalClassification = "critical";

    /// <inheritdoc/>
    public string ClaimId => "C-062";

    /// <inheritdoc/>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. Prompt injection ───────────────────────────────────────────────────────────────
        var promptInjection = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(promptInjection, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny("C-062: prompt injection detected in action parameters — action denied.");
        }

        // ── 2. Privilege escalation ───────────────────────────────────────────────────────────
        var privilegeEscalation = ctx.GetParameter(PrivilegeEscalationKey);
        if (string.Equals(privilegeEscalation, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny("C-062: privilege escalation detected — action denied.");
        }

        // ── 3. Cross-tenant boundary violation ────────────────────────────────────────────────
        var crossTenant = ctx.GetParameter(CrossTenantBoundaryKey);
        if (string.Equals(crossTenant, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Deny("C-062: cross-tenant boundary violation detected — action denied.");
        }

        // ── 4. High security risk ─────────────────────────────────────────────────────────────
        var securityRisk = ctx.GetParameter(SecurityRiskKey);
        if (string.Equals(securityRisk, HighRisk, StringComparison.OrdinalIgnoreCase))
        {
            return Deny("C-062: action carries high security risk — action denied.");
        }

        // ── 5. High exfiltration risk ─────────────────────────────────────────────────────────
        var exfiltrationRisk = ctx.GetParameter(ExfiltrationRiskKey);
        if (string.Equals(exfiltrationRisk, HighRisk, StringComparison.OrdinalIgnoreCase))
        {
            return Deny("C-062: action carries high data-exfiltration risk — action denied.");
        }

        // ── 6. Critical data classification ──────────────────────────────────────────────────
        var dataClassification = ctx.GetParameter(DataClassificationKey);
        if (string.Equals(dataClassification, CriticalClassification, StringComparison.OrdinalIgnoreCase))
        {
            return Deny("C-062: action targets critically classified data — action denied.");
        }

        // ── All checks passed ─────────────────────────────────────────────────────────────────
        return Allow("C-062: no AI security violations detected — action permitted.");
    }

    // ── helpers ───────────────────────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}