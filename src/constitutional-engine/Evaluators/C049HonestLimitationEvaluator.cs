// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation)
// C-073: This file implements a constitutional obligation — C-049 (AI must not act beyond its honest capability boundary)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-049 — Honest Limitation.
/// The AI must not proceed with an action when its confidence is below a configured threshold,
/// or when the action is explicitly flagged as exceeding known capability boundaries.
/// Low-confidence actions escalate to Sujay (human) rather than being executed autonomously.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation — C-049 Honest Limitation
    public string ClaimId => "C-049";

    /// <summary>Applies to all action types — capability honesty is universal.</summary>
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);  // empty = all types

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");
    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements C-049 — escalate or deny when capability/confidence boundary is exceeded
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C049HonestLimitationEvaluator.Evaluate",
            ActivityKind.Internal);
        activity?.SetTag("contract_id", ctx.ContractId);

        // Hard capability boundary flag: action is known to exceed AI capability
        var exceedsCapability = ctx.GetParameter("exceeds_capability_boundary");
        if (string.Equals(exceedsCapability, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-049 DENY: Action explicitly flagged as exceeding capability boundary. " +
                "ContractId={ContractId} ActionType={ActionType}",
                ctx.ContractId, ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-049",
                Verdict: EvaluationVerdict.Deny,
                Reason: "C-049: Honest limitation violated — action is flagged as exceeding AI capability boundary. " +
                        "The AI must not claim or exercise capabilities it does not reliably possess."));
        }

        // Confidence score check: below configured threshold → escalate to human
        var confidenceRaw = ctx.GetParameter("confidence_score");
        var thresholdRaw = ctx.GetParameter("confidence_threshold");

        if (!string.IsNullOrWhiteSpace(confidenceRaw))
        {
            if (!float.TryParse(confidenceRaw,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var confidenceScore))
            {
                _logger.LogWarning(
                    "C-049 DENY: confidence_score is non-numeric. ContractId={ContractId} Raw={Raw}",
                    ctx.ContractId, confidenceRaw);

                return Task.FromResult(new EvaluationResult(
                    ClaimId: "C-049",
                    Verdict: EvaluationVerdict.Deny,
                    Reason: $"C-049: confidence_score parameter '{confidenceRaw}' is not a valid number; " +
                            "malformed confidence scores are treated as zero-confidence."));
            }

            // Default threshold is 0.70 if not caller-supplied
            float threshold = 0.70f;
            if (!string.IsNullOrWhiteSpace(thresholdRaw) &&
                float.TryParse(thresholdRaw,
                    System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture,
                    out var parsedThreshold))
            {
                threshold = parsedThreshold;
            }

            activity?.SetTag("c049.confidence_score", confidenceScore);
            activity?.SetTag("c049.threshold", threshold);

            if (confidenceScore < threshold)
            {
                _logger.LogInformation(
                    "C-049 ESCALATE: Confidence below threshold. ContractId={ContractId} " +
                    "Score={Score} Threshold={Threshold}",
                    ctx.ContractId, confidenceScore, threshold);

                return Task.FromResult(new EvaluationResult(
                    ClaimId: "C-049",
                    Verdict: EvaluationVerdict.Escalate,
                    Reason: $"C-049: Confidence score {confidenceScore:F2} is below the required threshold {threshold:F2}. " +
                            "Action escalated to human review — the AI must not proceed beyond its honest capability."));
            }
        }

        _logger.LogInformation(
            "C-049 ALLOW: ContractId={ContractId} ActionType={ActionType}",
            ctx.ContractId, ctx.ActionType);

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-049",
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-049: Honest limitation check passed — action is within declared capability boundaries."));
    }
}