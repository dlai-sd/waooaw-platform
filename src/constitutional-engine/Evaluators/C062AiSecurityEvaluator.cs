// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// constitutional_basis: C-062 (AI Security), C-059 (Traceability), C-073 (Annotated Obligations)

#nullable enable

using System.Diagnostics;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-073: Enforces C-062 (AI Security) — prohibits tool categories and data scopes that
/// violate the WAOOAW AI security boundary. Default-deny posture: any action missing a
/// recognised security classification is blocked. Security overrides are escalated to
/// human constitutional authority rather than auto-approved.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-073: Constitutional claim enforced by this evaluator.
    public string ClaimId => "C-062";

    private static readonly ActivitySource _tracer = new("Waooaw.ConstitutionalEngine");

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    // ── Prohibited tool categories (C-062 AI Security boundary) ──────────────────────────
    // C-073: Any tool category in this set violates C-062 — unconditional DENY.
    private static readonly HashSet<string> _prohibitedToolCategories =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "credential_exfiltration",
            "privilege_escalation",
            "network_scanning",
            "memory_injection",
            "code_execution_unrestricted",
            "system_shell_access",
            "lateral_movement",
            "audit_tampering",
            "constitutional_bypass",
        };

    // ── Prohibited data scopes (C-062 AI Security boundary) ──────────────────────────────
    // C-073: Any data scope in this set violates C-062 — unconditional DENY.
    private static readonly HashSet<string> _prohibitedDataScopes =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "pii_unrestricted",
            "credentials",
            "private_keys",
            "shadow_copy",
            "audit_log_raw",
            "constitutional_records_write",
        };

    // ── Permitted security classifications (allowlist — everything else is DENY) ─────────
    // C-073: Default-deny posture — only explicitly approved classifications are permitted.
    private static readonly HashSet<string> _allowedSecurityClassifications =
        new(StringComparer.OrdinalIgnoreCase)
        {
            "public",
            "internal",
            "confidential",
        };

    // ActionParameters keys — defined as constants to prevent typos.
    private const string ParamToolCategory           = "tool_category";
    private const string ParamDataScope              = "data_scope";
    private const string ParamSecurityClassification = "security_classification";
    private const string ParamSecurityOverride       = "security_override";

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // C-073: Core constitutional evaluation — implements C-062 AI Security runtime enforcement.
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C062AiSecurityEvaluator.Evaluate", ActivityKind.Internal);
        activity?.SetTag("tenant_id",    ctx.TenantId);
        activity?.SetTag("action_type",  ctx.ActionType);
        activity?.SetTag("contract_id",  ctx.ContractId);

        // ── 1. Security override check — escalate to human authority ─────────────────────
        // C-073: Any attempt to override the AI Security policy cannot be auto-approved;
        //        it must be reviewed by the constitutional authority (C-049 Escalate path).
        var securityOverride = ctx.GetParameter(ParamSecurityOverride);
        if (IsOverrideActive(securityOverride))
        {
            _logger.LogWarning(
                "C-062: Security override attempted. TenantId={TenantId} ContractId={ContractId} Override={Override}",
                ctx.TenantId, ctx.ContractId, securityOverride);

            activity?.SetTag("c062.verdict",        "escalate");
            activity?.SetTag("c062.escalate.reason","security_override_attempted");
            activity?.SetTag("c062.override_value", securityOverride ?? string.Empty);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Escalate,
                Reason:  $"C-062: Security override '{securityOverride}' cannot be auto-approved — " +
                         "escalated to constitutional authority for human review."
            ));
        }

        // ── 2. Prohibited tool category check ────────────────────────────────────────────
        // C-073: Tool categories that violate the AI Security boundary are unconditionally denied.
        var toolCategory = ctx.GetParameter(ParamToolCategory);
        if (!string.IsNullOrWhiteSpace(toolCategory) &&
            _prohibitedToolCategories.Contains(toolCategory))
        {
            _logger.LogWarning(
                "C-062: Prohibited tool category blocked. TenantId={TenantId} ContractId={ContractId} ToolCategory={ToolCategory}",
                ctx.TenantId, ctx.ContractId, toolCategory);

            activity?.SetTag("c062.verdict",      "deny");
            activity?.SetTag("c062.deny.reason",  "prohibited_tool_category");
            activity?.SetTag("c062.tool_category", toolCategory);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-062: Tool category '{toolCategory}' is prohibited by the AI Security policy."
            ));
        }

        // ── 3. Prohibited data scope check ───────────────────────────────────────────────
        // C-073: Data scopes that expose sensitive WAOOAW infrastructure are unconditionally denied.
        var dataScope = ctx.GetParameter(ParamDataScope);
        if (!string.IsNullOrWhiteSpace(dataScope) &&
            _prohibitedDataScopes.Contains(dataScope))
        {
            _logger.LogWarning(
                "C-062: Prohibited data scope blocked. TenantId={TenantId} ContractId={ContractId} DataScope={DataScope}",
                ctx.TenantId, ctx.ContractId, dataScope);

            activity?.SetTag("c062.verdict",     "deny");
            activity?.SetTag("c062.deny.reason", "prohibited_data_scope");
            activity?.SetTag("c062.data_scope",  dataScope);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-062: Data scope '{dataScope}' is prohibited by the AI Security policy."
            ));
        }

        // ── 4. Security classification allowlist — default deny ──────────────────────────
        // C-073: Absent or unrecognised security classification → DENY.
        //        Every AI action must carry an explicit, approved classification.
        var securityClassification = ctx.GetParameter(ParamSecurityClassification);

        if (string.IsNullOrWhiteSpace(securityClassification))
        {
            _logger.LogWarning(
                "C-062: Missing security_classification — default deny applied. " +
                "TenantId={TenantId} ContractId={ContractId}",
                ctx.TenantId, ctx.ContractId);

            activity?.SetTag("c062.verdict",     "deny");
            activity?.SetTag("c062.deny.reason", "missing_security_classification");

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Deny,
                Reason:  "C-062: Action carries no security_classification — " +
                         "AI Security policy requires an explicit classification on every action."
            ));
        }

        if (!_allowedSecurityClassifications.Contains(securityClassification))
        {
            _logger.LogWarning(
                "C-062: Disallowed security classification. TenantId={TenantId} ContractId={ContractId} " +
                "Classification={Classification}",
                ctx.TenantId, ctx.ContractId, securityClassification);

            activity?.SetTag("c062.verdict",                  "deny");
            activity?.SetTag("c062.deny.reason",              "disallowed_security_classification");
            activity?.SetTag("c062.security_classification",  securityClassification);

            return Task.FromResult(new EvaluationResult(
                ClaimId: "C-062",
                Verdict: EvaluationVerdict.Deny,
                Reason:  $"C-062: Security classification '{securityClassification}' is not on the " +
                         "AI Security allowlist. Permitted values: public, internal, confidential."
            ));
        }

        // ── 5. All C-062 checks passed ───────────────────────────────────────────────────
        _logger.LogInformation(
            "C-062: AI Security evaluation passed. TenantId={TenantId} ContractId={ContractId} " +
            "Classification={Classification}",
            ctx.TenantId, ctx.ContractId, securityClassification);

        activity?.SetTag("c062.verdict",                 "allow");
        activity?.SetTag("c062.security_classification", securityClassification);

        return Task.FromResult(new EvaluationResult(
            ClaimId: "C-062",
            Verdict: EvaluationVerdict.Allow,
            Reason:  string.Empty
        ));
    }

    // ── Private helpers ───────────────────────────────────────────────────────────────────

    /// <summary>
    /// Returns true if the raw override parameter value represents an active override request.
    /// Treats null / empty / "false" / "0" as inactive (no override).
    /// </summary>
    private static bool IsOverrideActive(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))                                     return false;
        if (value.Equals("false", StringComparison.OrdinalIgnoreCase))            return false;
        if (value.Equals("0",     StringComparison.OrdinalIgnoreCase))            return false;
        return true;
    }
}