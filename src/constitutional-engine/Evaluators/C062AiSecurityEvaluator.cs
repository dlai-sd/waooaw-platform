// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — denies any action whose tool classification
/// appears on the prohibited list, or whose target system appears on the protected-system list.
/// No network I/O is performed; all data is read from the JSON-encoded ActionParameters
/// via EvaluationContext.GetParameter().
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── C-073: Constitutional tracing ───────────────────────────────────────
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // ── C-062: Prohibited tool-classification labels ─────────────────────────
    // DESIGN_QUESTION: EA to confirm canonical classification taxonomy (e.g. add "OFFENSIVE_SECURITY"?)
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "WEAPONIZED",
            "SURVEILLANCE",
            "DECEPTIVE_IDENTITY",
            "AUTONOMOUS_LETHAL",
            "DATA_EXFILTRATION",
            "ADVERSARIAL_ATTACK",
        };

    // ── C-062: Systems the AI must never target autonomously ─────────────────
    // DESIGN_QUESTION: EA to confirm protected-system registry source-of-truth (config vs. DB table)
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "KEYCLOAK_IAM",
            "CONSTITUTIONAL_ENGINE",
            "TEMPORAL_WORKFLOW",
            "POSTGRES_PRIMARY",
            "AUDIT_LOG_STORE",
            "WAOOAW_PAYMENTS",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── IClaimEvaluator ──────────────────────────────────────────────────────

    /// <summary>C-073: Identifies the constitutional claim this evaluator enforces.</summary>
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates whether the proposed action satisfies C-062 AI Security constraints.
    /// Short-circuits on first violation; never performs network I/O.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every evaluation for auditability (C-023 Evidence First)
        using var activity = _tracer.StartActivity("C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);
        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("ce.contract_id", ctx.ContractId);
        activity?.SetTag("ce.action_type", ctx.ActionType);
        activity?.SetTag("ce.tenant_id", ctx.TenantId);

        // ── Check 1: Prohibited tool classification ──────────────────────────
        var classification = ctx.GetParameter("tool_classification");
        activity?.SetTag("ce.tool_classification", classification ?? "<none>");

        if (!string.IsNullOrWhiteSpace(classification) &&
            ProhibitedClassifications.Contains(classification))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited tool classification {Classification} for contract {ContractId} tenant {TenantId}",
                classification, ctx.ContractId, ctx.TenantId);

            activity?.SetTag("ce.verdict", "Deny");
            activity?.SetTag("ce.deny_reason", $"Prohibited classification: {classification}");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Tool classification '{classification}' is prohibited under AI Security policy."));
        }

        // ── Check 2: Protected system targeting ──────────────────────────────
        var targetSystem = ctx.GetParameter("target_system");
        activity?.SetTag("ce.target_system", targetSystem ?? "<none>");

        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 DENY: autonomous action targeting protected system {TargetSystem} for contract {ContractId} tenant {TenantId}",
                targetSystem, ctx.ContractId, ctx.TenantId);

            activity?.SetTag("ce.verdict", "Deny");
            activity?.SetTag("ce.deny_reason", $"Protected system targeted: {targetSystem}");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Deny,
                Reason: $"C-062: Autonomous action targeting protected system '{targetSystem}' is prohibited."));
        }

        // ── Check 3: Escalate when security_review_required flag is set ──────
        // C-049 / C-062 joint path: uncertain security posture → human review
        var reviewRequired = ctx.GetParameter("security_review_required");
        if (string.Equals(reviewRequired, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogInformation(
                "C-062 ESCALATE: security_review_required flag set for contract {ContractId} tenant {TenantId}",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("ce.verdict", "Escalate");

            return Task.FromResult(new EvaluationResult(
                ClaimId: ClaimId,
                Verdict: EvaluationVerdict.Escalate,
                Reason: "C-062: Action flagged for mandatory human security review before execution."));
        }

        // ── All checks passed ─────────────────────────────────────────────────
        _logger.LogInformation(
            "C-062 ALLOW: no AI security violations detected for contract {ContractId} tenant {TenantId}",
            ctx.ContractId, ctx.TenantId);

        activity?.SetTag("ce.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId: ClaimId,
            Verdict: EvaluationVerdict.Allow,
            Reason: "C-062: No prohibited classification, protected system target, or security review flag detected."));
    }
}