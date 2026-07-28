// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) — denies or escalates actions flagged as AI security risks,
/// prompt injection attempts, or high-risk AI behaviour patterns.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private const string AiSecurityFlagKey    = "ai_security_flag";
    private const string SecurityRiskScoreKey = "security_risk_score";
    private const string PromptInjectionKey   = "prompt_injection_detected";
    private const double DenyThreshold        = 0.90;
    private const double EscalateThreshold    = 0.50;

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Check hard ai_security_flag — explicit raise always denies
        var aiSecurityFlag = ctx.GetParameter(AiSecurityFlagKey);
        if (string.Equals(aiSecurityFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: AI security flag raised — action denied."));
        }

        // Check prompt_injection_detected — direct injection always denies
        var promptInjection = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(promptInjection, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Prompt injection detected — action denied."));
        }

        // Check security_risk_score — continuous risk signal
        var riskScoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (riskScoreRaw is not null &&
            double.TryParse(
                riskScoreRaw,
                System.Globalization.NumberStyles.Any,
                System.Globalization.CultureInfo.InvariantCulture,
                out var riskScore))
        {
            if (riskScore >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Security risk score {riskScore:F2} >= deny threshold {DenyThreshold:F2} — action denied."));
            }

            if (riskScore >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: Security risk score {riskScore:F2} >= escalate threshold {EscalateThreshold:F2} — escalating to human review."));
            }
        }

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security concerns detected — action permitted."));
    }
}