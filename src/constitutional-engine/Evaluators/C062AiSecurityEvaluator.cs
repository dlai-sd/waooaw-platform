// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-001, C-003, C-023, C-041, C-059
using Grpc.Core;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// C-062 (AI Security) evaluator — enforces the constitutional prohibition on
/// security-violating tool invocations and prompt-injection attack patterns.
/// <para>
/// Constitutional basis: C-062 (AI Security), C-041 (Tool Authorization)
/// Spec: architecture/reference/ce-validate-action-evaluators.md
/// </para>
/// <para>
/// Evaluation strategy (fail-secure):
///   1. Action type on the static prohibited list → DENY immediately.
///   2. Tool name (from ActionParameters key "tool_name") matches a prohibited
///      prefix or exact name → DENY immediately.
///   3. Prompt-injection marker present in ActionParameters ("injection_marker"
///      key set by the AI Runtime sentinel) → DENY immediately.
///   4. All checks clear → ALLOW.
/// Any unhandled evaluator fault → DENY (fail-secure, C-062).
/// </para>
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // C-062: constitutional floor — these action types are ALWAYS denied.
    // Static set: evaluators MUST NOT perform network I/O (40ms ValidateAction budget, ADR-001).
    private static readonly IReadOnlySet<string> ProhibitedActionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "SYSTEM_PROMPT_INJECTION",
            "PRIVILEGE_ESCALATION",
            "CREDENTIAL_EXFILTRATION",
            "MODEL_JAILBREAK",
            "CONSTITUTIONAL_BYPASS",
            "DIRECT_DB_ACCESS",
            "RAW_SYSTEM_COMMAND",
            "ARBITRARY_CODE_EXECUTION",
        };

    // C-062: tool name prefixes that are constitutionally prohibited regardless of action type.
    private static readonly IReadOnlySet<string> ProhibitedToolPrefixes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "SHELL_",
            "EXEC_",
            "ADMIN_OVERRIDE_",
            "BYPASS_",
        };

    // C-062: exact tool names that are constitutionally prohibited.
    private static readonly IReadOnlySet<string> ProhibitedToolNames =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "bash",
            "shell",
            "eval",
            "exec",
            "subprocess",
            "os.system",
            "powershell",
            "cmd",
        };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    /// <inheritdoc />
    public string ClaimId => "C-062";

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        try
        {
            ct.ThrowIfCancellationRequested();

            // ── Guard 1: prohibited action type (C-062 constitutional floor) ──────────
            if (ProhibitedActionTypes.Contains(ctx.ActionType))
            {
                _logger.LogWarning(
                    "C-062 AI Security: prohibited action type '{ActionType}' denied. ContractId={ContractId} TenantId={TenantId}",
                    ctx.ActionType, ctx.ContractId, ctx.TenantId);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Action type '{ctx.ActionType}' is constitutionally prohibited under AI Security policy."));
            }

            // ── Guard 2: tool name checks (exact + prefix) ────────────────────────────
            var toolName = ctx.GetParameter("tool_name");
            if (toolName is not null)
            {
                // Exact-match prohibited tool names.
                if (ProhibitedToolNames.Contains(toolName))
                {
                    _logger.LogWarning(
                        "C-062 AI Security: prohibited tool name '{ToolName}' denied. ContractId={ContractId} TenantId={TenantId}",
                        toolName, ctx.ContractId, ctx.TenantId);

                    return Task.FromResult(new EvaluationResult(
                        ClaimId,
                        EvaluationVerdict.Deny,
                        $"C-062: Tool '{toolName}' is constitutionally prohibited under AI Security policy."));
                }

                // Prefix-match prohibited tool families.
                foreach (var prefix in ProhibitedToolPrefixes)
                {
                    if (toolName.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    {
                        _logger.LogWarning(
                            "C-062 AI Security: tool '{ToolName}' matches prohibited prefix '{Prefix}'. ContractId={ContractId} TenantId={TenantId}",
                            toolName, prefix, ctx.ContractId, ctx.TenantId);

                        return Task.FromResult(new EvaluationResult(
                            ClaimId,
                            EvaluationVerdict.Deny,
                            $"C-062: Tool '{toolName}' matches constitutionally prohibited tool-family prefix '{prefix}'."));
                    }
                }
            }

            // ── Guard 3: prompt-injection sentinel ────────────────────────────────────
            // The AI Runtime sets "injection_marker" in ActionParameters when its
            // internal sentinel detects a prompt-injection attack pattern (C-062, AD-019).
            var injectionMarker = ctx.GetParameter("injection_marker");
            if (injectionMarker is not null)
            {
                _logger.LogWarning(
                    "C-062 AI Security: prompt-injection marker detected. Marker='{Marker}' ContractId={ContractId} TenantId={TenantId}",
                    injectionMarker, ctx.ContractId, ctx.TenantId);

                return Task.FromResult(new EvaluationResult(
                    ClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Prompt-injection marker detected ('{injectionMarker}') — action denied under AI Security policy."));
            }

            // ── All C-062 guards passed ───────────────────────────────────────────────
            _logger.LogDebug(
                "C-062 AI Security: action cleared. ActionType={ActionType} ContractId={ContractId} TenantId={TenantId}",
                ctx.ActionType, ctx.ContractId, ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Allow,
                "C-062: Action cleared by AI Security evaluator."));
        }
        catch (OperationCanceledException)
        {
            // Propagate cancellation — do not swallow (C-059 ERROR HANDLING RULE 1).
            throw;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1: log before any return (C-059, C-082).
            // Fail-secure: evaluator fault → DENY (C-062 constitutional floor).
            _logger.LogError(
                ex,
                "C-062 AI Security evaluator fault — denying for safety. ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            return Task.FromResult(new EvaluationResult(
                ClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Evaluator fault — action denied for safety. Error: {ex.Message}"));
        }
    }
}