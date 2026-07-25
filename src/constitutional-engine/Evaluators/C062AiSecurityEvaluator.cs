// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): denies any action whose <c>security_classification</c>
/// parameter falls within the prohibited set, or whose <c>target_system</c> parameter
/// identifies a WAOOAW-protected infrastructure system.
///
/// Design:
///   • No network I/O — all checks are pure in-memory set lookups against the
///     JSON-encoded ActionParameters, extracted via ctx.GetParameter().
///   • Both prohibited-classification and protected-system checks must pass for ALLOW.
///   • Short-circuits on first violation (classification checked before system).
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource annotation — every constitutional obligation carries an OTel span.
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-062: Canonical list of prohibited security classifications.
    // Any action whose security_classification parameter matches one of these is denied.
    // DESIGN_QUESTION: Should this list be DB-driven (tenant-configurable) or remain
    //   compile-time constant? Current spec implies platform-wide invariant — EA to confirm.
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "WEAPON",
            "MALWARE",
            "EXPLOIT",
            "RANSOMWARE",
            "SPYWARE",
            "PHISHING",
            "SOCIAL_ENGINEERING",
            "CREDENTIAL_THEFT",
            "PRIVILEGE_ESCALATION",
            "BACKDOOR",
            "ROOTKIT",
            "KEYLOGGER",
            "DDOS",
            "DATA_EXFILTRATION",
        };

    // C-062: Protected WAOOAW infrastructure systems — AI agents must never target these directly.
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "CONSTITUTIONAL_ENGINE",
            "KEYCLOAK",
            "POSTGRES",
            "TEMPORAL",
            "AUDIT_DB",
            "IDENTITY_PROVIDER",
            "SECRET_STORE",
            "TERRAFORM_STATE",
            "OTEL_COLLECTOR",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        // C-073: Guard — constitutional evaluator must always have an ILogger.
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Implements constitutional claim C-062 (AI Security).
    /// Denies actions whose <c>security_classification</c> is prohibited,
    /// or whose <c>target_system</c> is a protected WAOOAW infrastructure component.
    /// </summary>
    /// <param name="ctx">Evaluation context built from the incoming ValidateAction request.</param>
    /// <param name="ct">Cancellation token — propagated from the gRPC server call context.</param>
    /// <returns>
    /// <see cref="EvaluationVerdict.Deny"/> with a descriptive reason if either check fails;
    /// <see cref="EvaluationVerdict.Allow"/> when both checks pass.
    /// </returns>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Open OTel span for every constitutional evaluation.
        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",    ClaimId);
        activity?.SetTag("action_type", ctx.ActionType);
        activity?.SetTag("tenant_id",   ctx.TenantId);

        // Honour cooperative cancellation before any work begins.
        ct.ThrowIfCancellationRequested();

        // ── Check 1: Prohibited security classification ──────────────────────────
        // C-062: Any action labelled with a prohibited classification is denied
        // regardless of the tenant's authorised action set.
        var classification = ctx.GetParameter("security_classification");

        if (!string.IsNullOrWhiteSpace(classification) &&
            ProhibitedClassifications.Contains(classification))
        {
            _logger.LogWarning(
                "C-062 DENY prohibited classification. " +
                "Classification={Classification} ActionType={ActionType} TenantId={TenantId}",
                classification, ctx.ActionType, ctx.TenantId);

            activity?.SetTag("c062.deny_reason",   "prohibited_classification");
            activity?.SetTag("c062.classification", classification);
            activity?.SetTag("c062.verdict",        "deny");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Action denied — security classification '{classification}' is prohibited."));
        }

        // ── Check 2: Protected system targeting ──────────────────────────────────
        // C-062: AI agents must not directly address WAOOAW infrastructure systems.
        var targetSystem = ctx.GetParameter("target_system");

        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 DENY protected system target. " +
                "TargetSystem={TargetSystem} ActionType={ActionType} TenantId={TenantId}",
                targetSystem, ctx.ActionType, ctx.TenantId);

            activity?.SetTag("c062.deny_reason",  "protected_system");
            activity?.SetTag("c062.target_system", targetSystem);
            activity?.SetTag("c062.verdict",       "deny");

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Action denied — target system '{targetSystem}' is a protected WAOOAW infrastructure component."));
        }

        // ── Both checks passed ───────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW. ActionType={ActionType} TenantId={TenantId}",
            ctx.ActionType, ctx.TenantId);

        activity?.SetTag("c062.verdict", "allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No prohibited security classification or protected system detected."));
    }
}