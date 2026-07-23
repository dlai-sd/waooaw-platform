// Implements: architecture/reference/ce-validate-action-evaluators.md §C-049 Evaluator
// constitutional_basis: C-049 (Honest Limitation), C-059 (Traceability), C-073 (Annotation)

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-049 — Honest Limitation evaluator.
/// When an agent signals it is operating beyond its known capability boundary,
/// the action is escalated to human review rather than auto-authorized or denied.
/// Applies to ALL action types (universal evaluator).
/// </summary>
/// <remarks>
/// DESIGN_QUESTION: The spec does not define a machine-readable capability-limit signal.
/// This evaluator checks metadata key "capability_limit_exceeded" == "true".
/// EA should confirm the canonical signal format and whether ESCALATE should be DENY
/// in the absence of a human-review workflow being available.
/// </remarks>
public sealed class C049HonestLimitationEvaluator : IClaimEvaluator
{
    private const string CapabilityLimitKey = "capability_limit_exceeded";
    private const string CapabilityLimitValue = "true";

    private readonly ILogger<C049HonestLimitationEvaluator> _logger;

    // C-073: ClaimId links runtime enforcement to C-049.
    public string ClaimId => "C-049";

    // C-073: Empty set = universal evaluator — applies to ALL action types.
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase);

    public C049HonestLimitationEvaluator(ILogger<C049HonestLimitationEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <inheritdoc />
    // C-073: EvaluateAsync implements C-049 — Honest Limitation escalation path.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        if (ctx.Metadata.TryGetValue(CapabilityLimitKey, out var limitValue) &&
            string.Equals(limitValue, CapabilityLimitValue, StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-049 ESCALATE: TenantId={TenantId} ActionType={ActionType} capability limit exceeded",
                ctx.TenantId,
                ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                EvaluationDecision.Escalate,
                Reason: "Agent signalled capability limit exceeded — escalating to human review (C-049).",
                EvidenceHint: $"TenantId={ctx.TenantId}, ActionType={ctx.ActionType}"));
        }

        _logger.LogDebug(
            "C-049 AUTHORIZED: TenantId={TenantId} ActionType={ActionType} no capability limit signal",
            ctx.TenantId,
            ctx.ActionType);

        return Task.FromResult(new EvaluationResult(EvaluationDecision.Authorized));
    }
}