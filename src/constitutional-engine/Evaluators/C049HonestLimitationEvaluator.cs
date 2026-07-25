// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-023 (Evidence First),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Coverage)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Implements C-049 (Honest Limitation).
/// When an action's declared confidence falls below the configured threshold,
/// or when the agent lacks sufficient prior-approval history, the evaluator
/// returns Escalate — routing the decision to human oversight rather than
/// either approving or denying autonomously.
/// Escalate is the C-049 path: "forward to human (Sujay)".
/// </summary>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    // C-059: named tracer matches service-wide ActivitySource convention.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // C-073: Constructor enforces null-safety per C# 12 discipline.
    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-049";

    /// <summary>
    /// C-073: Evaluates C-049 Honest Limitation.
    ///
    /// Decision rules (evaluated in order, short-circuit on first Escalate):
    ///   1. If "confidence_score" and "configured_threshold" are present AND
    ///      confidence_score &lt; configured_threshold → Escalate.
    ///   2. If "prior_approval_count" and "min_history_required" are present AND
    ///      prior_approval_count &lt; min_history_required → Escalate.
    ///   3. Otherwise → Allow.
    ///
    /// There is no Deny path for C-049 — uncertainty routes to human, not blocks.
    /// Parameters are extracted via ctx.GetParameter() (JSON-encoded ActionParameters).
    /// MUST NOT perform network I/O. Completes synchronously via Task.FromResult.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: OpenTelemetry span per C-059 traceability requirement.
        using var activity = _tracer.StartActivity(
            "C049HonestLimitation.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("contract_id", ctx.ContractId);

        // ── Rule 1: Confidence score vs. configured threshold ──────────────────
        // C-073: C-049 requires the agent to acknowledge when its confidence is
        // below the threshold agreed in the employment contract. Escalate to human.
        string? confidenceStr = ctx.GetParameter("confidence_score");
        string? thresholdStr  = ctx.GetParameter("configured_threshold");

        if (confidenceStr is not null && thresholdStr is not null)
        {
            bool confidenceParsed = float.TryParse(
                confidenceStr,
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                out float confidenceScore);

            bool thresholdParsed = float.TryParse(
                thresholdStr,
                System.Globalization.NumberStyles.Float,
                System.Globalization.CultureInfo.InvariantCulture,
                out float configuredThreshold);

            if (!confidenceParsed || !thresholdParsed)
            {
                // Malformed numeric parameters — cannot verify honesty claim → Escalate.
                _logger.LogWarning(
                    "C-049 parse failure: confidence_score={RawConfidence} configured_threshold={RawThreshold} " +
                    "ActionType={ActionType} TenantId={TenantId}",
                    confidenceStr, thresholdStr, ctx.ActionType, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "malformed_confidence_params");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Unable to parse confidence parameters " +
                    $"(confidence_score='{confidenceStr}', configured_threshold='{thresholdStr}'). " +
                    $"Escalating to human oversight — cannot verify honest-limitation constraint."));
            }

            if (confidenceScore < configuredThreshold)
            {
                _logger.LogInformation(
                    "C-049 Escalate: confidence {ConfidenceScore:F4} below threshold {Threshold:F4} " +
                    "ActionType={ActionType} TenantId={TenantId}",
                    confidenceScore, configuredThreshold, ctx.ActionType, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.confidence_score", confidenceScore);
                activity?.SetTag("c049.configured_threshold", configuredThreshold);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049 Honest Limitation: confidence score {confidenceScore:F4} is below " +
                    $"configured threshold {configuredThreshold:F4}. " +
                    $"Action escalated to human oversight rather than approved autonomously."));
            }

            activity?.SetTag("c049.confidence_score", confidenceScore);
            activity?.SetTag("c049.configured_threshold", configuredThreshold);
            activity?.SetTag("c049.confidence_check", "passed");
        }
        else
        {
            // Parameters absent — confidence check not applicable to this action type.
            activity?.SetTag("c049.confidence_check", "not_applicable");
        }

        // ── Rule 2: Prior-approval history vs. minimum required ────────────────
        // C-073: C-049 requires that novel action patterns with insufficient
        // historical precedent be escalated rather than autonomously approved.
        string? priorCountStr    = ctx.GetParameter("prior_approval_count");
        string? minHistoryStr    = ctx.GetParameter("min_history_required");

        if (priorCountStr is not null && minHistoryStr is not null)
        {
            bool priorParsed   = int.TryParse(priorCountStr,   out int priorApprovalCount);
            bool minParsed     = int.TryParse(minHistoryStr,    out int minHistoryRequired);

            if (!priorParsed || !minParsed)
            {
                // Malformed history parameters — cannot verify precedent → Escalate.
                _logger.LogWarning(
                    "C-049 parse failure: prior_approval_count={RawPrior} min_history_required={RawMin} " +
                    "ActionType={ActionType} TenantId={TenantId}",
                    priorCountStr, minHistoryStr, ctx.ActionType, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.escalation_reason", "malformed_history_params");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049: Unable to parse approval history parameters " +
                    $"(prior_approval_count='{priorCountStr}', min_history_required='{minHistoryStr}'). " +
                    $"Escalating to human oversight — cannot verify honest-limitation constraint."));
            }

            if (priorApprovalCount < minHistoryRequired)
            {
                _logger.LogInformation(
                    "C-049 Escalate: insufficient approval history " +
                    "{PriorApprovalCount}/{MinHistoryRequired} " +
                    "ActionType={ActionType} TenantId={TenantId}",
                    priorApprovalCount, minHistoryRequired, ctx.ActionType, ctx.TenantId);

                activity?.SetTag("c049.verdict", "Escalate");
                activity?.SetTag("c049.prior_approval_count", priorApprovalCount);
                activity?.SetTag("c049.min_history_required", minHistoryRequired);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Escalate,
                    $"C-049 Honest Limitation: insufficient approval history — " +
                    $"{priorApprovalCount} prior approval(s) recorded, " +
                    $"{minHistoryRequired} required before autonomous execution. " +
                    $"Action escalated to human oversight."));
            }

            activity?.SetTag("c049.prior_approval_count", priorApprovalCount);
            activity?.SetTag("c049.min_history_required", minHistoryRequired);
            activity?.SetTag("c049.history_check", "passed");
        }
        else
        {
            // Parameters absent — history check not applicable to this action type.
            activity?.SetTag("c049.history_check", "not_applicable");
        }

        // ── Rule 3: All applicable checks passed → Allow ───────────────────────
        _logger.LogInformation(
            "C-049 Allow: honest-limitation constraints satisfied " +
            "ActionType={ActionType} TenantId={TenantId}",
            ctx.ActionType, ctx.TenantId);

        activity?.SetTag("c049.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-049 Honest Limitation: confidence and prior-approval history requirements satisfied."));
    }
}