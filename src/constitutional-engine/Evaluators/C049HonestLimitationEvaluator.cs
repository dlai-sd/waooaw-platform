// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability)

#nullable enable

using Microsoft.Extensions.Logging;
using System.Diagnostics;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049: AI must honestly represent its limitations. When an action is declared near or
/// beyond the agent's competence boundary (via 'confidence_score' parameter), the evaluator
/// escalates to human review rather than authorizing silently or denying outright.
/// Escalate path: human (Sujay) notified via C-049 pathway before action proceeds.
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-073: Constitutional obligation annotation
    // Enforces C-049 — AI must escalate rather than fabricate capability it does not have.

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // Confidence below this threshold triggers Escalate (not Deny — C-049 allows action
    // with human oversight, not unconditional refusal).
    private const double EscalateThreshold = 0.70;

    // Hard deny when confidence is critically low — agent should not proceed at all.
    private const double HardDenyThreshold = 0.30;

    // C-049 applies universally.
    private static readonly IReadOnlySet<string> _actionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    public string ClaimId => "C-049";
    public IReadOnlySet<string> ApplicableActionTypes => _actionTypes;

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    // C-073: Implements C-049 — honest limitation escalation path.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity("C049.EvaluateAsync", ActivityKind.Internal);
        activity?.SetTag("claim", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);

        if (!ctx.ActionParameters.TryGetValue("confidence_score", out var rawScore)
            || !double.TryParse(rawScore, System.Globalization.NumberStyles.Number,
                System.Globalization.CultureInfo.InvariantCulture, out var confidence))
        {
            // No confidence declared — allow; C-049 requires honest declaration, not mandatory scoring.
            // DESIGN_QUESTION: Should absent confidence_score trigger Escalate by default?
            // Currently: allow with informational log. Flag for EA review.
            _logger.LogInformation("C-049 ALLOW: confidence_score not declared. action_type={ActionType}", ctx.ActionType);
            return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow,
                "C-049: No confidence score declared; proceeding."));
        }

        activity?.SetTag("confidence_score", confidence);

        if (confidence < HardDenyThreshold)
        {
            _logger.LogWarning(
                "C-049 DENY: confidence_score={Score:F3} below hard-deny threshold={Threshold} action_type={ActionType}",
                confidence, HardDenyThreshold, ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-049: Confidence score {confidence:F3} is critically below threshold {HardDenyThreshold:F2}. " +
                "AI must not proceed with actions far outside its competence boundary."));
        }

        if (confidence < EscalateThreshold)
        {
            _logger.LogInformation(
                "C-049 ESCALATE: confidence_score={Score:F3} below escalation threshold={Threshold} action_type={ActionType}",
                confidence, EscalateThreshold, ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Escalate,
                $"C-049: Confidence score {confidence:F3} below {EscalateThreshold:F2}. " +
                "Action requires human review before proceeding."));
        }

        _logger.LogInformation(
            "C-049 ALLOW: confidence_score={Score:F3} within competence boundary. action_type={ActionType}",
            confidence, ctx.ActionType);

        return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow,
            $"C-049: Confidence score {confidence:F3} within competence boundary."));
    }
}