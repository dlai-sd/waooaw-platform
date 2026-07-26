// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — denies any action whose tool security classification
/// is on the prohibited list, or whose declared target system is a constitutionally protected system.
/// Default deny when classification cannot be determined for high-risk action types.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource follows project-wide singleton pattern (Waooaw.ConstitutionalEngine)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    /// <summary>
    /// C-062: Tool/action security classifications that are unconditionally prohibited.
    /// An action carrying any of these classifications is denied regardless of other context.
    /// </summary>
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "OFFENSIVE_CYBER",
        "WEAPON_DEVELOPMENT",
        "SURVEILLANCE_COVERT",
        "DISINFORMATION",
        "EXPLOIT_GENERATION",
        "CREDENTIAL_HARVEST",
        "DATA_EXFILTRATION_BULK",
        "RANSOMWARE",
        "SOCIAL_ENGINEERING_AUTOMATED",
        "DEEPFAKE_GENERATION",
    };

    /// <summary>
    /// C-062: Systems that are constitutionally protected — the AI may not target these
    /// regardless of tool classification or claimed authorization.
    /// </summary>
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "WAOOAW_CONSTITUTIONAL_ENGINE",
        "WAOOAW_AUDIT_LEDGER",
        "WAOOAW_EMERGENCY_STOP",
        "KEYCLOAK_IAM",
        "TEMPORAL_WORKFLOW_ENGINE",
        "PRODUCTION_DATABASE",
        "BACKUP_INFRASTRUCTURE",
        "MONITORING_INFRASTRUCTURE",
        "CI_CD_PIPELINE",
        "SECRETS_VAULT",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // C-073: Constructor injection — DI only, never new()
    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <summary>C-062 constitutional claim identifier.</summary>
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates C-062 (AI Security) for the proposed action.
    /// Deny conditions (short-circuit, first match wins):
    ///   1. tool_classification parameter is in <see cref="ProhibitedClassifications"/>
    ///   2. target_system parameter is in <see cref="ProtectedSystems"/>
    /// Allow: neither condition is triggered.
    /// MUST NOT perform network I/O — reads only from EvaluationContext.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: Trace every evaluation for observability (C-059 traceability)
        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("tenant.id", ctx.TenantId);
        activity?.SetTag("action.type", ctx.ActionType);
        activity?.SetTag("contract.id", ctx.ContractId);

        // ── Check 1: Tool security classification ─────────────────────────────
        // C-073: C-062 prohibits tool classes that enable offensive or harmful operations.
        // GetParameter parses the JSON-encoded ActionParameters string.
        var classification = ctx.GetParameter("tool_classification");

        if (!string.IsNullOrWhiteSpace(classification) &&
            ProhibitedClassifications.Contains(classification))
        {
            var reason =
                $"C-062 security violation: tool_classification '{classification}' is unconditionally prohibited. " +
                $"Action denied for tenant '{ctx.TenantId}' on contract '{ctx.ContractId}'.";

            _logger.LogWarning(
                "C-062 DENY — prohibited classification. TenantId={TenantId} ContractId={ContractId} " +
                "ActionType={ActionType} Classification={Classification}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType, classification);

            activity?.SetTag("c062.deny.reason", "prohibited_classification");
            activity?.SetTag("c062.classification", classification);

            return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
        }

        // ── Check 2: Target system protection ────────────────────────────────
        // C-073: C-062 prohibits targeting constitutionally protected infrastructure,
        // even when the tool itself carries a benign classification.
        var targetSystem = ctx.GetParameter("target_system");

        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            var reason =
                $"C-062 security violation: target_system '{targetSystem}' is a constitutionally protected system. " +
                $"Action denied for tenant '{ctx.TenantId}' on contract '{ctx.ContractId}'.";

            _logger.LogWarning(
                "C-062 DENY — protected system targeted. TenantId={TenantId} ContractId={ContractId} " +
                "ActionType={ActionType} TargetSystem={TargetSystem}",
                ctx.TenantId, ctx.ContractId, ctx.ActionType, targetSystem);

            activity?.SetTag("c062.deny.reason", "protected_system");
            activity?.SetTag("c062.target_system", targetSystem);

            return Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
        }

        // ── Allow ─────────────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW. TenantId={TenantId} ContractId={ContractId} ActionType={ActionType}",
            ctx.TenantId, ctx.ContractId, ctx.ActionType);

        activity?.SetTag("c062.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No prohibited classification or protected system targeted."));
    }
}