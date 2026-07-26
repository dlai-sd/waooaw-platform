// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 AI Security boundary at runtime.
/// Denies actions whose tool classification is prohibited under C-062,
/// and escalates actions that target protected systems for human review.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Constitutional annotation — OpenTelemetry ActivitySource for distributed tracing per ADR-009
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Constitutional annotation — absolute boundary per C-062; these tool classifications are
    // unconditionally prohibited. Any action whose tool_security_classification matches one of these
    // values must be DENIED regardless of tenant contract or budget state.
    private static readonly HashSet<string> ProhibitedClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "OFFENSIVE_CYBER",
            "WEAPON_SYSTEM",
            "MASS_SURVEILLANCE",
            "AUTONOMOUS_LETHAL",
            "SOCIAL_MANIPULATION",
            "DISINFORMATION",
        };

    // C-073: Constitutional annotation — protected systems per C-062; actions targeting these systems
    // require human review (Escalate path). They are not unconditionally denied because a legitimate
    // operator may authorise access, but the decision cannot be made autonomously.
    private static readonly HashSet<string> ProtectedSystems =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "FINANCIAL_CORE",
            "IDENTITY_PROVIDER",
            "AUDIT_LEDGER",
            "EMERGENCY_STOP",
            "CONSTITUTIONAL_ENGINE",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        // C-073: Constructor guard — null logger would silently suppress security audit trail
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Implements IClaimEvaluator.ClaimId — identifies the constitutional claim enforced here
    public string ClaimId => "C-062";

    // C-073: Implements IClaimEvaluator.EvaluateAsync — enforces AI Security boundary per C-062
    /// <summary>
    /// Evaluates the proposed action against the C-062 AI Security boundary.
    /// <para>Decision logic (in order):</para>
    /// <list type="number">
    ///   <item>If <c>tool_security_classification</c> parameter matches a prohibited classification → DENY.</item>
    ///   <item>If <c>target_system</c> parameter matches a protected system → ESCALATE.</item>
    ///   <item>Otherwise → ALLOW.</item>
    /// </list>
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("c062.tenant_id", ctx.TenantId);
        activity?.SetTag("c062.action_type", ctx.ActionType);
        activity?.SetTag("c062.contract_id", ctx.ContractId);

        // C-073: Extract classification and target from JSON-encoded action parameters
        // ActionParameters is a JSON string — GetParameter(key) is the ONLY safe accessor
        var classification = ctx.GetParameter("tool_security_classification");
        var targetSystem   = ctx.GetParameter("target_system");

        activity?.SetTag("c062.classification", classification ?? "(none)");
        activity?.SetTag("c062.target_system",  targetSystem  ?? "(none)");

        // ── Step 1: Prohibited classification check (C-062 absolute boundary) ──────────────────
        // C-073: A non-null, non-whitespace classification that maps to a prohibited entry is an
        // unconditional DENY. No contract override is possible at this evaluation layer.
        if (!string.IsNullOrWhiteSpace(classification) &&
            ProhibitedClassifications.Contains(classification))
        {
            _logger.LogWarning(
                "C-062 DENY prohibited_classification={Classification} " +
                "tenant={TenantId} action_type={ActionType} contract={ContractId}",
                classification, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.decision", "DENY");
            activity?.SetTag("c062.deny_reason", $"prohibited_classification:{classification}");

            return Task.FromResult(
                Deny($"Tool classification '{classification}' is prohibited under C-062 AI Security."));
        }

        // ── Step 2: Protected system check (C-062 escalation boundary) ───────────────────────
        // C-073: Targeting a protected system is not unconditionally denied — a human operator may
        // legitimately authorise such access — but the decision cannot be made autonomously.
        // Escalate surfaces the action to the C-049 human-review path.
        if (!string.IsNullOrWhiteSpace(targetSystem) &&
            ProtectedSystems.Contains(targetSystem))
        {
            _logger.LogWarning(
                "C-062 ESCALATE protected_system={TargetSystem} " +
                "tenant={TenantId} action_type={ActionType} contract={ContractId}",
                targetSystem, ctx.TenantId, ctx.ActionType, ctx.ContractId);

            activity?.SetTag("c062.decision", "ESCALATE");
            activity?.SetTag("c062.escalate_reason", $"protected_system:{targetSystem}");

            return Task.FromResult(
                Escalate(
                    $"Target system '{targetSystem}' is a protected system under C-062 — " +
                    "human review required before proceeding."));
        }

        // ── Step 3: No security concern detected — allow ──────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW tenant={TenantId} action_type={ActionType} contract={ContractId}",
            ctx.TenantId, ctx.ActionType, ctx.ContractId);

        activity?.SetTag("c062.decision", "ALLOW");

        return Task.FromResult(Allow());
    }

    // ── Private helpers ───────────────────────────────────────────────────────────────────────

    // C-073: Constructs a DENY EvaluationResult attributed to C-062
    private EvaluationResult Deny(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);

    // C-073: Constructs an ESCALATE EvaluationResult attributed to C-062
    private EvaluationResult Escalate(string reason) =>
        new(ClaimId, EvaluationVerdict.Escalate, reason);

    // C-073: Constructs an ALLOW EvaluationResult attributed to C-062
    private EvaluationResult Allow() =>
        new(ClaimId, EvaluationVerdict.Allow, "AI security boundary check passed (C-062).");
}