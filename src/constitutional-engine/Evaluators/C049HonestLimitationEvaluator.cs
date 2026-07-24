// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049: The agent MUST NOT claim capability or confidence it does not possess.
/// When SyntheticApprovalContext is present, ConfidenceScore must meet ConfiguredThreshold
/// and PriorApprovalCount must satisfy MinHistoryRequired.
/// If neither is satisfied → Escalate (forward to human Sujay for review).
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: Implements constitutional obligation C-049 (Honest Limitation)
    public string ClaimId => "C-049";

    // C-073: Universal — honesty obligation applies to ALL action types
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Evaluates C-049 — confidence and history requirements for synthetic approval
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("contract.id", ctx.ContractId);

        // Check explicit dishonesty signal in parameters
        var claimsCapability = ctx.GetParameter("claims_unsupported_capability");
        if (!string.IsNullOrWhiteSpace(claimsCapability) &&
            claimsCapability.Equals("true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-049 DENY: Agent claims unsupported capability. ContractId={ContractId}",
                ctx.ContractId);
            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                "C-049: Action parameter 'claims_unsupported_capability=true' violates honest limitation obligation."));
        }

        // Check confidence threshold via synthetic_confidence / synthetic_threshold parameters
        // These mirror SyntheticApprovalContext fields forwarded into ActionParameters
        var confidenceStr  = ctx.GetParameter("synthetic_confidence");
        var thresholdStr   = ctx.GetParameter("synthetic_threshold");
        var historyStr     = ctx.GetParameter("synthetic_prior_approval_count");
        var minHistoryStr  = ctx.GetParameter("synthetic_min_history_required");

        if (!string.IsNullOrWhiteSpace(confidenceStr) && !string.IsNullOrWhiteSpace(thresholdStr))
        {
            if (float.TryParse(confidenceStr, out var confidence) &&
                float.TryParse(thresholdStr, out var threshold))
            {
                activity?.SetTag("c049.confidence", confidence);
                activity?.SetTag("c049.threshold", threshold);

                var historyCount = 0;
                var minHistory   = 0;
                int.TryParse(historyStr, out historyCount);
                int.TryParse(minHistoryStr, out minHistory);

                var confidenceMet = confidence >= threshold;
                var historyMet    = historyCount >= minHistory;

                if (!confidenceMet || !historyMet)
                {
                    _logger.LogWarning(
                        "C-049 ESCALATE: Confidence or history insufficient. " +
                        "ContractId={ContractId} Confidence={Confidence} Threshold={Threshold} " +
                        "History={History} MinHistory={MinHistory}",
                        ctx.ContractId, confidence, threshold, historyCount, minHistory);

                    activity?.SetTag("c049.verdict", "Escalate");
                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Escalate,
                        $"C-049: Insufficient synthetic approval basis. " +
                        $"Confidence={confidence:F3} (need {threshold:F3}), " +
                        $"History={historyCount} (need {minHistory}). Escalating to human review."));
                }
            }
        }

        _logger.LogInformation(
            "C-049 ALLOW: Honest limitation check passed. ContractId={ContractId}", ctx.ContractId);

        activity?.SetTag("c049.verdict", "Allow");
        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049: Honest limitation check passed."));
    }
}