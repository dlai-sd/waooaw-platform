// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator
// constitutional_basis: C-062 (AI Security), C-023 (Evidence First), C-059 (Traceability), C-073 (Annotation)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — denies actions targeting prohibited security
/// classifications or protected systems that AI must not access or manipulate.
/// Runs as a pure in-process evaluator: no network I/O, no DB reads.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: ActivitySource matches service-wide tracer name — see ADR-009
    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    // C-073: Prohibited security classifications — actions carrying these are denied under C-062.
    // DESIGN_QUESTION: Should this set be tenant-configurable at runtime (DB-backed)?
    // For now: compile-time constant per EA guidance (no DB on evaluators before WC012-03a lands).
    private static readonly HashSet<string> ProhibitedClassifications = new(StringComparer.OrdinalIgnoreCase)
    {
        "adversarial",
        "jailbreak",
        "prompt_injection",
        "data_exfiltration",
        "privilege_escalation",
        "model_inversion",
        "membership_inference",
        "backdoor",
        "trojan",
        "adversarial_example",
        "evasion_attack",
    };

    // C-073: Protected systems — AI agents must not target these systems directly under C-062.
    private static readonly HashSet<string> ProtectedSystems = new(StringComparer.OrdinalIgnoreCase)
    {
        "constitutional_engine_internal",
        "keycloak_admin",
        "kernel",
        "hypervisor",
        "audit_store",
        "temporal_admin",
        "postgres_admin",
        "infrastructure_secrets",
        "certificate_authority",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        // C-073: ArgumentNullException guard — mandatory per null-safety policy
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    /// <inheritdoc/>
    public string ClaimId => "C-062";

    /// <summary>
    /// C-073: Evaluates C-062 AI Security.
    /// Decision tree:
    ///   1. If <c>security_classification</c> parameter is a prohibited classification → DENY
    ///   2. If <c>target_system</c> parameter is a protected system → DENY
    ///   3. If <c>tool_name</c> contains a prohibited classification substring → DENY
    ///   4. Otherwise → Allow
    /// All checks are O(1) HashSet lookups — no I/O.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        // C-073: OpenTelemetry span for this evaluation — budget is 40ms across all evaluators
        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("constitutional.claim", ClaimId);
        activity?.SetTag("constitutional.tenant_id", ctx.TenantId);
        activity?.SetTag("constitutional.action_type", ctx.ActionType);
        activity?.SetTag("constitutional.contract_id", ctx.ContractId);

        // ── Check 1: security_classification parameter ──────────────────────────────
        // C-073: Agents may self-declare a security classification on the action.
        // If that classification is on the prohibited list, deny immediately.
        var securityClassification = ctx.GetParameter("security_classification");
        if (!string.IsNullOrWhiteSpace(securityClassification))
        {
            activity?.SetTag("constitutional.c062.security_classification", securityClassification);

            if (ProhibitedClassifications.Contains(securityClassification.Trim()))
            {
                _logger.LogWarning(
                    "C-062 DENY: prohibited security_classification={Classification} ContractId={ContractId} TenantId={TenantId}",
                    securityClassification, ctx.ContractId, ctx.TenantId);

                activity?.SetTag("constitutional.c062.verdict", "Deny");
                activity?.SetTag("constitutional.c062.deny_reason", "prohibited_classification");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Action carries prohibited security classification '{securityClassification}'. AI agents must not initiate actions with this classification."));
            }
        }

        // ── Check 2: target_system parameter ────────────────────────────────────────
        // C-073: AI agents must not directly target protected infrastructure systems.
        // Targeting keycloak_admin, constitutional_engine_internal, etc. is denied.
        var targetSystem = ctx.GetParameter("target_system");
        if (!string.IsNullOrWhiteSpace(targetSystem))
        {
            activity?.SetTag("constitutional.c062.target_system", targetSystem);

            if (ProtectedSystems.Contains(targetSystem.Trim()))
            {
                _logger.LogWarning(
                    "C-062 DENY: protected target_system={TargetSystem} ContractId={ContractId} TenantId={TenantId}",
                    targetSystem, ctx.ContractId, ctx.TenantId);

                activity?.SetTag("constitutional.c062.verdict", "Deny");
                activity?.SetTag("constitutional.c062.deny_reason", "protected_system");

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Action targets protected system '{targetSystem}'. AI agents are prohibited from directly accessing this system."));
            }
        }

        // ── Check 3: tool_name substring scan ───────────────────────────────────────
        // C-073: Tool names that embed prohibited classification keywords are denied.
        // Prevents an agent from routing around Check 1 by embedding the classification
        // in the tool name (e.g., a tool called "run_adversarial_probe").
        var toolName = ctx.GetParameter("tool_name");
        if (!string.IsNullOrWhiteSpace(toolName))
        {
            var toolNameLower = toolName.Trim().ToLowerInvariant();
            activity?.SetTag("constitutional.c062.tool_name", toolNameLower);

            foreach (var prohibited in ProhibitedClassifications)
            {
                if (toolNameLower.Contains(prohibited, StringComparison.OrdinalIgnoreCase))
                {
                    _logger.LogWarning(
                        "C-062 DENY: tool_name={ToolName} contains prohibited classification={Classification} ContractId={ContractId} TenantId={TenantId}",
                        toolName, prohibited, ctx.ContractId, ctx.TenantId);

                    activity?.SetTag("constitutional.c062.verdict", "Deny");
                    activity?.SetTag("constitutional.c062.deny_reason", "prohibited_tool_name");

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Deny,
                        $"C-062: Tool name '{toolName}' contains prohibited security classification '{prohibited}'. Tool invocation denied under AI Security policy."));
                }
            }
        }

        // ── All checks passed ────────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 Allow: no prohibited classification or protected system detected ContractId={ContractId} TenantId={TenantId}",
            ctx.ContractId, ctx.TenantId);

        activity?.SetTag("constitutional.c062.verdict", "Allow");

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            "C-062: No prohibited security classification or protected system target detected."));
    }
}