// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 AI Security
// constitutional_basis: C-062 (AI Security)
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062 AI Security evaluator.
/// Denies actions that carry a hard security-violation flag or a high security-risk score.
/// Escalates actions whose security-risk score exceeds the escalation threshold.
/// No network I/O — all decisions are derived from EvaluationContext parameters.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── Parameter keys (JSON-encoded in ActionParameters) ──────────────────────
    private const string AiSecurityFlagKey       = "ai_security_flag";
    private const string SecurityRiskScoreKey    = "security_risk_score";
    private const string PromptInjectionKey      = "prompt_injection_detected";

    // ── Decision thresholds ────────────────────────────────────────────────────
    private const double DenyThreshold     = 0.90;
    private const double EscalateThreshold = 0.50;

    // ── IClaimEvaluator ────────────────────────────────────────────────────────
    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // 1. Hard security-violation flag ──────────────────────────────────────
        var securityFlag = ctx.GetParameter(AiSecurityFlagKey);
        if (string.Equals(securityFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: AI security violation flag is set — action denied."
            ));
        }

        // 2. Prompt-injection detection ────────────────────────────────────────
        var injectionFlag = ctx.GetParameter(PromptInjectionKey);
        if (string.Equals(injectionFlag, "true", StringComparison.OrdinalIgnoreCase))
        {
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-062: Prompt injection detected — action denied."
            ));
        }

        // 3. Numeric security-risk score ───────────────────────────────────────
        var riskRaw = ctx.GetParameter(SecurityRiskScoreKey);
        if (riskRaw is not null &&
            double.TryParse(riskRaw, System.Globalization.NumberStyles.Float,
                            System.Globalization.CultureInfo.InvariantCulture, out var riskScore))
        {
            if (riskScore >= DenyThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Security risk score {riskScore:F2} ≥ deny threshold {DenyThreshold} — action denied."
                ));
            }

            if (riskScore >= EscalateThreshold)
            {
                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-062: Security risk score {riskScore:F2} ≥ escalate threshold {EscalateThreshold} — escalating to human review."
                ));
            }
        }

        // 4. No security concerns found ────────────────────────────────────────
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            null
        ));
    }
}
