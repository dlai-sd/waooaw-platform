// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// constitutional_basis: C-062 (AI Security), C-059 (Traceability), C-076 (test coverage)

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): denies or escalates actions flagged for prompt injection,
/// AI security violations, or elevated security risk scores.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private const string AiSecurityFlagKey    = "ai_security_flag";
    private const string SecurityRiskScoreKey = "security_risk_score";
    private const string PromptInjectionKey   = "prompt_injection_detected";

    private const double DenyThreshold      = 0.90;
    private const double EscalateThreshold  = 0.50;

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Hard deny: explicit AI security flag raised
        var aiSecurityFlag = ctx.GetParameter(AiSecurityFlagKey);
        if (string.Equals(aiSecurityFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: AI security flag is set — action denied to protect system integrity."));
        }

        // Hard deny: prompt injection detected
        var promptInjection = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(promptInjection, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Prompt injection detected — action denied per AI security policy."));
        }

        // Score-based evaluation
        var scoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (scoreRaw is not null
            && double.TryParse(scoreRaw, System.Globalization.NumberStyles.Any,
                               System.Globalization.CultureInfo.InvariantCulture, out var score))
        {
            if (score >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Security risk score {score:F2} meets or exceeds deny threshold {DenyThreshold:F2}."));
            }

            if (score >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: Security risk score {score:F2} meets or exceeds escalation threshold {EscalateThreshold:F2} — human review required."));
            }
        }

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security violations detected."));
    }
}