// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): denies actions that use prohibited tool classifications
/// or attempt direct AI-agent access to constitutionally protected systems.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource scoped to the Constitutional Engine telemetry provider (ADR-009)
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: C-062 enumerates tool classifications an AI agent may NEVER invoke.
    // Evaluated against action parameter key "tool_classification" (case-insensitive).
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "OFFENSIVE_CYBER",          // Any tool that attacks or probes external systems
            "SURVEILLANCE",             // Mass-monitoring tools without explicit consent
            "BIOMETRIC_MASS_COLLECTION", // Bulk biometric harvesting
            "AUTONOMOUS_WEAPONS",       // Kinetic or cyber weapons with autonomous trigger
            "SOCIAL_SCORING",           // Algorithmic social credit or ranking systems
            "DEEPFAKE_GENERATION",      // Synthetic media that impersonates real persons
            "CREDENTIAL_HARVESTING",    // Tools designed to extract auth credentials
            "EXPLOIT_DEVELOPMENT",      // Zero-day or CVE exploitation tooling
        };

    // C-073: C-062 enumerates systems an AI agent may NEVER directly write to or control.
    // Evaluated against action parameter key "target_system" (case-insensitive).
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "IDENTITY_PROVIDER",        // Keycloak / auth stack — human-only mutations
            "AUDIT_LOG",                // Constitutional audit records are append-only via CE
            "CONSTITUTIONAL_ENGINE",    // CE must not self-modify its own rule set
            "EMERGENCY_STOP",           // Emergency Stop may only be triggered via authorised path
            "HUMAN_OVERRIDE_CHANNEL",   // C-001 override channel is exclusively human-operated
            "PAYMENT_GATEWAY",          // Financial disbursement requires human authorisation
            "CREDENTIAL_STORE",         // Secrets vault — never directly accessible by agents
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        // C-073: Constructor guard — DI must supply a concrete logger (C-059 traceability)
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc />
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Enforces C-062 (AI Security).
    /// Denies on first match of either a prohibited tool classification or a protected target system.
    /// Pure synchronous logic wrapped in Task — no network I/O, satisfies the 40 ms budget share.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // C-073: Null guard — EvaluationContext must be constructed by CE before reaching evaluators
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.Evaluate",
            ActivityKind.Internal);

        activity?.SetTag("claim_id", ClaimId);
        activity?.SetTag("tenant_id", ctx.TenantId);
        activity?.SetTag("action_type", ctx.ActionType);

        // ── Check 1: Prohibited tool classification ──────────────────────────────────
        // C-073: ActionParameters is a JSON string — use GetParameter(), never TryGetValue()
        var toolClassification = ctx.GetParameter("tool_classification");

        if (toolClassification is not null
            && ProhibitedClassifications.Contains(toolClassification))
        {
            _logger.LogWarning(
                "C-062 DENY — prohibited tool classification. " +
                "Classification={Classification} TenantId={TenantId} ActionType={ActionType}",
                toolClassification,
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "prohibited_classification");
            activity?.SetTag("tool_classification", toolClassification);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Tool classification '{toolClassification}' is prohibited for AI agents " +
                $"under the WAOOAW AI Security policy."));
        }

        // ── Check 2: Protected target system ─────────────────────────────────────────
        // C-073: Prevents AI agents from directly mutating constitutionally protected systems
        var targetSystem = ctx.GetParameter("target_system");

        if (targetSystem is not null
            && ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 DENY — direct AI access to protected system. " +
                "TargetSystem={TargetSystem} TenantId={TenantId} ActionType={ActionType}",
                targetSystem,
                ctx.TenantId,
                ctx.ActionType);

            activity?.SetTag("decision", "Deny");
            activity?.SetTag("deny_reason", "protected_system");
            activity?.SetTag("target_system", targetSystem);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Direct AI agent access to protected system '{targetSystem}' " +
                $"is prohibited. Route through the appropriate human-authorised channel."));
        }

        // ── All C-062 checks passed ───────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 Allow. TenantId={TenantId} ActionType={ActionType}",
            ctx.TenantId,
            ctx.ActionType);

        activity?.SetTag("decision", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No AI security violation detected."));
    }
}