// Implements: architecture/reference/ce-validate-action-evaluators.md §C-062
// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// Constitutional basis: C-062 (AI Security)
// Spec: WC012-02b

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security): prevents the AI agent from crossing PAAS security
/// boundaries, calling prohibited system-level tools, escalating privileges, or
/// reaching external hosts that violate the platform sandbox.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    /// <summary>
    /// MCP tool names unconditionally denied under C-062.
    /// These tools represent PAAS-boundary or OS-level capabilities the AI must never hold.
    /// </summary>
    private static readonly IReadOnlySet<string> ProhibitedToolNames =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "shell_exec",
            "exec",
            "system",
            "os_command",
            "bash",
            "powershell",
            "cmd",
            "file_delete",
            "registry_write",
            "network_raw",
            "kernel_module",
            "credential_dump",
            "secret_extract",
        };

    /// <summary>
    /// Action types unconditionally denied under C-062 regardless of tool name.
    /// </summary>
    private static readonly IReadOnlySet<string> ProhibitedActionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "SYSTEM_EXEC",
            "OS_COMMAND",
            "CREDENTIAL_ACCESS",
            "KERNEL_ACCESS",
            "PAAS_BOUNDARY_ESCAPE",
        };

    /// <summary>
    /// Suffix that identifies an internal WAOOAW host — the only non-localhost targets
    /// the AI agent is permitted to address.
    /// </summary>
    private const string InternalHostSuffix = ".waooaw.internal";

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        _logger = logger;
    }

    public string ClaimId => "C-062";

    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // ── 1. Prohibited action types ─────────────────────────────────────────────
        if (ProhibitedActionTypes.Contains(ctx.ActionType))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited action type {ActionType} | contract={ContractId} tenant={TenantId}",
                ctx.ActionType, ctx.ContractId, ctx.TenantId);

            return Deny(
                $"Action type '{ctx.ActionType}' is unconditionally prohibited by C-062 AI Security policy.");
        }

        // ── 2. Prohibited MCP tool names ───────────────────────────────────────────
        var toolName = ctx.GetParameter("tool_name");
        if (toolName is not null && ProhibitedToolNames.Contains(toolName))
        {
            _logger.LogWarning(
                "C-062 DENY: prohibited tool '{ToolName}' | contract={ContractId} tenant={TenantId}",
                toolName, ctx.ContractId, ctx.TenantId);

            return Deny(
                $"Tool '{toolName}' is prohibited by C-062 AI Security policy — PAAS boundary violation.");
        }

        // ── 3. PAAS boundary — external target host check ─────────────────────────
        var targetHost = ctx.GetParameter("target_host");
        if (targetHost is not null)
        {
            var isInternal =
                targetHost.EndsWith(InternalHostSuffix, StringComparison.OrdinalIgnoreCase) ||
                targetHost.Equals("localhost", StringComparison.OrdinalIgnoreCase);

            if (!isInternal)
            {
                _logger.LogWarning(
                    "C-062 DENY: external target host '{TargetHost}' | contract={ContractId} tenant={TenantId}",
                    targetHost, ctx.ContractId, ctx.TenantId);

                return Deny(
                    $"Target host '{targetHost}' violates C-062 PAAS security boundary — " +
                    $"only hosts ending in '{InternalHostSuffix}' or 'localhost' are permitted.");
            }
        }

        // ── 4. Privilege escalation indicator ─────────────────────────────────────
        var requiresElevation = ctx.GetParameter("requires_elevation");
        if (string.Equals(requiresElevation, "true", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogWarning(
                "C-062 DENY: privilege escalation requested | contract={ContractId} tenant={TenantId}",
                ctx.ContractId, ctx.TenantId);

            return Deny("Privilege escalation is prohibited by C-062 AI Security policy.");
        }

        // ── 5. All checks passed ───────────────────────────────────────────────────
        return Allow("C-062 AI Security checks passed — no PAAS boundary violations detected.");
    }

    // ── Private helpers ────────────────────────────────────────────────────────────

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));
}