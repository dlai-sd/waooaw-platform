// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062 Evaluator — AI Security
// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-062 (AI Security), C-059 (Traceability)

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): validates that proposed actions remain within the PAAS boundary
/// and do not attempt prohibited system-level, credential, or infrastructure operations.
/// Short-circuits the evaluator chain with DENY on first security violation found.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── PAAS boundary: action types that are unconditionally prohibited ──────────────────────────
    private static readonly HashSet<string> ProhibitedActionTypes = new(StringComparer.OrdinalIgnoreCase)
    {
        "SHELL_EXEC",
        "OS_COMMAND",
        "SYSTEM_COMMAND",
        "PROCESS_SPAWN",
        "KERNEL_CALL",
        "FILE_SYSTEM_WRITE",
        "FILE_SYSTEM_DELETE",
        "REGISTRY_WRITE",
        "NETWORK_EGRESS_UNRESTRICTED",
        "CREDENTIAL_ACCESS",
        "SECRET_EXFILTRATION",
        "INFRASTRUCTURE_MUTATE",
    };

    // ── Tool-name prefixes that indicate PAAS boundary violation ────────────────────────────────
    private static readonly string[] ProhibitedToolNamePrefixes =
    {
        "sys_",
        "shell_",
        "exec_",
        "os_",
        "infra_",
        "cred_",
    };

    // ── Parameter keys read from JSON-encoded ActionParameters via GetParameter ─────────────────
    private const string ToolNameKey        = "tool_name";
    private const string SecurityCategoryKey = "security_category";
    private const string ElevatedPrivilegeKey = "requires_elevated_privilege";

    // Security categories that are unconditionally prohibited for AI agents
    private static readonly HashSet<string> ProhibitedSecurityCategories = new(StringComparer.OrdinalIgnoreCase)
    {
        "INFRASTRUCTURE",
        "CREDENTIAL_MANAGEMENT",
        "SECRET_STORE",
        "PLATFORM_ADMIN",
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        _logger = logger;
    }

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── Gate 1: Prohibited action type (PAAS boundary hard stop) ────────────────────────────
        if (ProhibitedActionTypes.Contains(ctx.ActionType))
        {
            _logger.LogWarning(
                "C-062 DENY [contract={ContractId} tenant={TenantId}]: action type '{ActionType}' is prohibited by PAAS boundary",
                ctx.ContractId, ctx.TenantId, ctx.ActionType);

            return Task.FromResult(new EvaluationResult(
                "C-062",
                EvaluationVerdict.Deny,
                $"Action type '{ctx.ActionType}' violates C-062 AI Security: PAAS boundary prohibits this operation category."));
        }

        // ── Gate 2: Prohibited tool-name prefix ─────────────────────────────────────────────────
        var toolName = ctx.GetParameter(ToolNameKey);
        if (toolName is not null)
        {
            foreach (var prefix in ProhibitedToolNamePrefixes)
            {
                if (toolName.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    _logger.LogWarning(
                        "C-062 DENY [contract={ContractId} tenant={TenantId}]: tool '{ToolName}' matches prohibited prefix '{Prefix}'",
                        ctx.ContractId, ctx.TenantId, toolName, prefix);

                    return Task.FromResult(new EvaluationResult(
                        "C-062",
                        EvaluationVerdict.Deny,
                        $"Tool '{toolName}' violates C-062 AI Security: prefix '{prefix}' is reserved for system-level operations outside the PAAS boundary."));
                }
            }
        }

        // ── Gate 3: Prohibited security category ────────────────────────────────────────────────
        var securityCategory = ctx.GetParameter(SecurityCategoryKey);
        if (securityCategory is not null && ProhibitedSecurityCategories.Contains(securityCategory))
        {
            _logger.LogWarning(
                "C-062 DENY [contract={ContractId} tenant={TenantId}]: security_category '{Category}' is prohibited",
                ctx.ContractId, ctx.TenantId, securityCategory);

            return Task.FromResult(new EvaluationResult(
                "C-062",
                EvaluationVerdict.Deny,
                $"Security category '{securityCategory}' violates C-062 AI Security: AI agents may not operate in this category."));
        }

        // ── Gate 4: Elevated privilege flag ─────────────────────────────────────────────────────
        var elevatedPrivilegeRaw = ctx.GetParameter(ElevatedPrivilegeKey);
        if (string.Equals(elevatedPrivilegeRaw, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-062 DENY [contract={ContractId} tenant={TenantId}]: requires_elevated_privilege=true is not permitted for AI agents",
                ctx.ContractId, ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                "C-062",
                EvaluationVerdict.Deny,
                "Elevated privilege operations violate C-062 AI Security: AI agents must operate with least-privilege within the PAAS boundary."));
        }

        // ── All security gates passed ────────────────────────────────────────────────────────────
        _logger.LogDebug(
            "C-062 ALLOW [contract={ContractId} tenant={TenantId} actionType={ActionType}]: passed AI security boundary checks",
            ctx.ContractId, ctx.TenantId, ctx.ActionType);

        return Task.FromResult(new EvaluationResult(
            "C-062",
            EvaluationVerdict.Allow,
            "Action passes all C-062 AI Security PAAS boundary checks."));
    }
}