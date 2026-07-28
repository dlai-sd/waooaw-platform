// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)
using System.Globalization;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) — denies or escalates actions flagged as
/// security risks, including prompt-injection attempts and high risk-score payloads.
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
        // 1. Explicit AI security flag — hard deny.
        if (IsTrue(ctx.GetParameter(AiSecurityFlagKey)))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: ai_security_flag is set — action denied on constitutional security grounds."));
        }

        // 2. Prompt injection detected — hard deny.
        if (IsTrue(ctx.GetParameter(PromptInjectionKey)))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: prompt_injection_detected is set — action denied to prevent AI security breach."));
        }

        // 3. Numeric risk score evaluation.
        var scoreRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (scoreRaw is not null &&
            double.TryParse(scoreRaw, NumberStyles.Any, CultureInfo.InvariantCulture, out var score))
        {
            if (score >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: security_risk_score {score:F4} ≥ deny threshold {DenyThreshold} — action denied."));
            }

            if (score >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: security_risk_score {score:F4} ≥ escalate threshold {EscalateThreshold} — human review required."));
            }
        }

        // 4. No security signals present — allow.
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security signals detected — action permitted."));
    }

    private static bool IsTrue(string? value) =>
        string.Equals(value?.Trim(), "true", StringComparison.OrdinalIgnoreCase);
}