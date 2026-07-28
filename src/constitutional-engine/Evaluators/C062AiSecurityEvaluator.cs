// Implements: architecture/reference/components/constitutional-engine.md §2 PAAS Boundary Validator
// constitutional_basis: C-041, C-059
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
// Constitutional basis: C-062 (AI Security), C-041 (Tool Authorization), C-059 (Implementation Traceability)
// Purpose: Evaluates whether a proposed AI tool call is constitutionally permitted under the
//          AI Security constraint (C-062). Enforces a security allowlist of permitted tool
//          categories and a denylist of prohibited tool patterns. Default deny for all
//          unlisted tools — any tool not explicitly permitted is constitutionally prohibited.
// ADR reference: ADR-001 (gRPC Constitutional Engine)
// Spec reference: architecture/reference/ce-validate-action-evaluators.md

using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-062 (AI Security) — every AI tool call must be in the constitutional
/// security allowlist. Unlisted tools are denied by default (constitutional floor).
/// Prohibited injection patterns are detected and denied unconditionally.
/// </summary>
public sealed class C062AiSecurityEvaluator : IClaimEvaluator
{
    // ── Constitutional Constants (C-062, C-041) ───────────────────────────────

    private const string ConstitutionalClaimId = "C-062";

    /// <summary>
    /// Permitted AI tool prefixes — only tool names that begin with one of these
    /// prefixes are constitutionally permitted. All others are denied (default deny,
    /// C-041 constitutional floor extended to AI security scope by C-062).
    /// </summary>
    private static readonly IReadOnlySet<string> PermittedToolPrefixes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "calendar",
            "email",
            "document",
            "search",
            "analytics",
            "crm",
            "social_post",
            "content_draft",
            "invoice",
            "report"
        };

    /// <summary>
    /// Prohibited tool identifiers — these are unconditionally denied regardless of
    /// any other context. C-062: shell execution, code execution, and raw system
    /// access are constitutional floors that may never be crossed by a Digital Professional.
    /// </summary>
    private static readonly IReadOnlySet<string> ProhibitedToolNames =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "execute_code",
            "shell_exec",
            "shell_command",
            "system_command",
            "os_exec",
            "process_spawn",
            "file_write_raw",
            "network_raw",
            "database_admin",
            "iam_modify",
            "credential_read",
            "secret_read"
        };

    /// <summary>
    /// Prohibited substrings within action parameters — detects injection attempts.
    /// C-062: parameter injection is an AI Security violation regardless of tool name.
    /// Comparison is case-insensitive to prevent trivial bypass via casing.
    /// </summary>
    private static readonly string[] ProhibitedParameterPatterns =
    {
        "DROP TABLE",
        "DELETE FROM",
        "TRUNCATE TABLE",
        "EXEC(",
        "EXECUTE(",
        "xp_cmdshell",
        "<script",
        "javascript:",
        "vbscript:",
        "data:text/html",
        "os.system(",
        "subprocess.run(",
        "subprocess.call(",
        "__import__(",
        "eval(",
        "exec("
    };

    private readonly ILogger<C062AiSecurityEvaluator> _logger;

    public C062AiSecurityEvaluator(ILogger<C062AiSecurityEvaluator> logger)
    {
        _logger = logger ?? throw new ArgumentNullException(nameof(logger));
    }

    // ── IClaimEvaluator ───────────────────────────────────────────────────────

    /// <inheritdoc/>
    public string ClaimId => ConstitutionalClaimId;

    /// <inheritdoc/>
    public async Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Yield to honour cooperative cancellation before beginning evaluation.
        ct.ThrowIfCancellationRequested();
        await Task.Yield();

        try
        {
            // ── Step 1: Resolve tool name ─────────────────────────────────────
            // tool_name may be nested inside JSON action_parameters.
            // ctx.GetParameter() handles JSON extraction; fall back to ActionType
            // if the caller passed the tool identifier there instead.
            var toolName = ctx.GetParameter("tool_name")
                           ?? ctx.GetParameter("tool")
                           ?? ctx.ActionType
                           ?? string.Empty;

            _logger.LogDebug(
                "C-062 AI Security evaluation starting. ContractId={ContractId} ToolName={ToolName}",
                ctx.ContractId,
                toolName);

            // ── Step 2: Denylist — unconditionally prohibited tools ────────────
            // Check before allowlist: a prohibited tool is denied even if its name
            // accidentally starts with a permitted prefix (e.g., "execute_code_calendar").
            if (ProhibitedToolNames.Contains(toolName))
            {
                _logger.LogWarning(
                    "C-062 DENY: Prohibited tool invoked. ContractId={ContractId} ToolName={ToolName}",
                    ctx.ContractId,
                    toolName);

                return new EvaluationResult(
                    ConstitutionalClaimId,
                    EvaluationVerdict.Deny,
                    $"C-062: Tool '{toolName}' is unconditionally prohibited by the AI Security " +
                    "constitutional constraint. Shell execution, code execution, raw system, and " +
                    "credential access tools are constitutional floors that may never be crossed.");
            }

            // ── Step 3: Injection pattern scan on raw action parameters ───────
            // The full ActionParameters string (JSON) is scanned for prohibited
            // substrings. GetParameter() alone is insufficient: an adversarial payload
            // may embed injection content in values we do not explicitly extract.
            if (!string.IsNullOrWhiteSpace(ctx.ActionParameters))
            {
                var injectionPattern = FindInjectionPattern(ctx.ActionParameters);
                if (injectionPattern is not null)
                {
                    _logger.LogWarning(
                        "C-062 DENY: Injection pattern detected. ContractId={ContractId} " +
                        "Pattern={Pattern} ToolName={ToolName}",
                        ctx.ContractId,
                        injectionPattern,
                        toolName);

                    return new EvaluationResult(
                        ConstitutionalClaimId,
                        EvaluationVerdict.Deny,
                        $"C-062: Action parameters contain a prohibited injection pattern " +
                        $"('{injectionPattern}'). Injection attempts are an AI Security violation " +
                        "regardless of the tool being invoked.");
                }
            }

            // ── Step 4: Allowlist — permitted tool prefixes ───────────────────
            // A tool is constitutionally permitted only when its name begins with
            // one of the explicitly authorised prefixes. All other tools are denied
            // by default (C-041 + C-062 default-deny constitutional floor).
            foreach (var prefix in PermittedToolPrefixes)
            {
                if (toolName.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                {
                    _logger.LogDebug(
                        "C-062 ALLOW: Tool within permitted security boundary. " +
                        "ContractId={ContractId} ToolName={ToolName} MatchedPrefix={Prefix}",
                        ctx.ContractId,
                        toolName,
                        prefix);

                    return new EvaluationResult(
                        ConstitutionalClaimId,
                        EvaluationVerdict.Allow,
                        $"C-062: Tool '{toolName}' is within the AI Security constitutional " +
                        $"boundary (permitted prefix: '{prefix}').");
                }
            }

            // ── Step 5: Default deny — unlisted tool ──────────────────────────
            // C-062 + C-041: any tool not in the explicit allowlist is constitutionally
            // prohibited. The agent must operate only within its licensed Decision Space.
            _logger.LogWarning(
                "C-062 DENY (default): Tool not in security allowlist. " +
                "ContractId={ContractId} ToolName={ToolName}",
                ctx.ContractId,
                toolName);

            return new EvaluationResult(
                ConstitutionalClaimId,
                EvaluationVerdict.Deny,
                $"C-062: Tool '{toolName}' is not in the AI Security constitutional allowlist. " +
                "Default deny applies — only explicitly permitted tool categories may be invoked " +
                "by a Digital Professional. Permitted categories: " +
                string.Join(", ", PermittedToolPrefixes) + ".");
        }
        catch (OperationCanceledException)
        {
            // Propagate cancellation — do not swallow.
            throw;
        }
        catch (Exception ex)
        {
            // ERROR HANDLING RULE 1 + C-059: log before rethrowing; never swallow silently.
            _logger.LogError(
                ex,
                "C-062 evaluator encountered an unexpected error. Operation failed: " +
                "ContractId={ContractId} ActionType={ActionType}",
                ctx.ContractId,
                ctx.ActionType);

            // Fail-closed: on evaluator error, deny the action.
            // A failed security check must never become an accidental allow.
            return new EvaluationResult(
                ConstitutionalClaimId,
                EvaluationVerdict.Deny,
                $"C-062: AI Security evaluation failed with an internal error ({ex.GetType().Name}). " +
                "Fail-closed: action denied to preserve constitutional security boundary.");
        }
    }

    // ── Private Helpers ───────────────────────────────────────────────────────

    /// <summary>
    /// Scans <paramref name="parameters"/> for any prohibited injection substring.
    /// Returns the first matched pattern, or <c>null</c> if none found.
    /// Case-insensitive to prevent trivial bypass via casing variations.
    /// </summary>
    private static string? FindInjectionPattern(string parameters)
    {
        foreach (var pattern in ProhibitedParameterPatterns)
        {
            if (parameters.Contains(pattern, StringComparison.OrdinalIgnoreCase))
            {
                return pattern;
            }
        }

        return null;
    }
}