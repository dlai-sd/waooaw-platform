// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 (Tool Authorization)
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotated Obligations)

using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041 Tool Authorization: every MCP tool call requires an explicit
/// authorization entry in the tenant's active employment contract. Default deny —
/// an unlisted or unknown tool is always DENY regardless of other context.
/// </summary>
/// <remarks>
/// C-073: This class is a constitutional obligation implementation.
/// Applies to action type: MCP_TOOL_CALL only.
/// Authorization logic: tool_name extracted from JSON ActionParameters, cross-checked
/// against authorized_tools[] pre-populated by the CE caller from
/// business.employment_contracts.authorized_actions[].
///
/// DESIGN_QUESTION: The TYPE CONTRACT for EvaluationContext has no DB-access method and
/// no AuthorizedActions property. The spec says "read from business.employment_contracts".
/// This implementation assumes the CE service layer pre-populates authorized_tools into
/// ActionParameters JSON before evaluators run. EA should confirm this contract or add
/// an AuthorizedActions IReadOnlySet<string> property to EvaluationContext.
/// </remarks>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    // ── Constants ──────────────────────────────────────────────────────────────
    private const string ActionTypeFilter      = "MCP_TOOL_CALL";
    private const string ParamToolName         = "tool_name";
    private const string ParamAuthorizedTools  = "authorized_tools";

    // ── OpenTelemetry ──────────────────────────────────────────────────────────
    private static readonly ActivitySource _tracer =
        new("Waooaw.ConstitutionalEngine");

    // ── DI ────────────────────────────────────────────────────────────────────
    private readonly ILogger<C041ToolAuthorizationEvaluator> _logger;

    // ── IClaimEvaluator identity ───────────────────────────────────────────────
    /// <inheritdoc/>
    public string ClaimId => "C-041";

    /// <inheritdoc/>
    /// <remarks>
    /// C-041 is scoped to MCP tool calls only. Other action types skip this evaluator.
    /// </remarks>
    public IReadOnlySet<string> ApplicableActionTypes { get; } =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase) { ActionTypeFilter };

    // ── Constructor ────────────────────────────────────────────────────────────
    public C041ToolAuthorizationEvaluator(ILogger<C041ToolAuthorizationEvaluator> logger)
    {
        ArgumentNullException.ThrowIfNull(logger);
        _logger = logger;
    }

    // ── Core evaluation ────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Constitutional obligation — C-041 Tool Authorization.
    /// Default deny: an MCP tool call is DENIED unless:
    ///   1. A non-empty ContractId is present (known active contract).
    ///   2. A non-empty tool_name is present in ActionParameters.
    ///   3. tool_name appears in the authorized_tools[] JSON array in ActionParameters.
    /// All other states → DENY.
    /// </summary>
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        ArgumentNullException.ThrowIfNull(ctx);

        using var activity = _tracer.StartActivity(
            "C041ToolAuthorizationEvaluator.EvaluateAsync",
            ActivityKind.Internal);

        activity?.SetTag("claim_id",     ClaimId);
        activity?.SetTag("tenant_id",    ctx.TenantId);
        activity?.SetTag("contract_id",  ctx.ContractId);
        activity?.SetTag("action_type",  ctx.ActionType);

        // ── Guard 1: contract must be known ───────────────────────────────────
        if (string.IsNullOrWhiteSpace(ctx.ContractId))
        {
            return Deny(
                activity,
                reason: "C-041: No active employment contract found for tenant. Default deny.",
                logMessage: "C-041 DENY — ContractId absent. TenantId={TenantId}",
                ctx.TenantId);
        }

        // ── Guard 2: tool_name must be present ────────────────────────────────
        var toolName = ctx.GetParameter(ParamToolName);
        if (string.IsNullOrWhiteSpace(toolName))
        {
            return Deny(
                activity,
                reason: "C-041: tool_name not specified in ActionParameters. Default deny.",
                logMessage: "C-041 DENY — tool_name absent. TenantId={TenantId} ContractId={ContractId}",
                ctx.TenantId, ctx.ContractId);
        }

        activity?.SetTag("requested_tool", toolName);

        // ── Guard 3: authorized_tools[] must be present ───────────────────────
        var authorizedToolsJson = ctx.GetParameter(ParamAuthorizedTools);
        if (string.IsNullOrWhiteSpace(authorizedToolsJson))
        {
            _logger.LogInformation(
                "C-041 DENY — authorized_tools absent for contract. " +
                "ToolName={ToolName} ContractId={ContractId} TenantId={TenantId}",
                toolName, ctx.ContractId, ctx.TenantId);

            activity?.SetTag("deny_reason", "authorized_tools_absent");
            return Task.FromResult(Denied(
                $"C-041: No authorized_tools populated for contract '{ctx.ContractId}'. Default deny."));
        }

        // ── Parse authorized_tools JSON array ─────────────────────────────────
        HashSet<string> authorizedTools;
        try
        {
            var parsed = JsonSerializer.Deserialize<string[]>(
                authorizedToolsJson,
                JsonSerializerOptions.Default);

            authorizedTools = parsed is { Length: > 0 }
                ? new HashSet<string>(parsed, StringComparer.OrdinalIgnoreCase)
                : new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        }
        catch (JsonException ex)
        {
            _logger.LogWarning(
                ex,
                "C-041 DENY — authorized_tools JSON malformed. ContractId={ContractId} TenantId={TenantId}",
                ctx.ContractId, ctx.TenantId);

            activity?.SetTag("deny_reason", "authorized_tools_parse_error");
            return Task.FromResult(Denied(
                $"C-041: Malformed authorized_tools JSON in contract '{ctx.ContractId}'. Default deny."));
        }

        // ── Decision ──────────────────────────────────────────────────────────
        if (!authorizedTools.Contains(toolName))
        {
            _logger.LogInformation(
                "C-041 DENY — tool not in authorized list. " +
                "ToolName={ToolName} ContractId={ContractId} TenantId={TenantId}",
                toolName, ctx.ContractId, ctx.TenantId);

            activity?.SetTag("deny_reason", "tool_not_authorized");
            activity?.SetTag("denied_tool",  toolName);

            return Task.FromResult(Denied(
                $"C-041: Tool '{toolName}' is not in authorized_actions for contract '{ctx.ContractId}'. Default deny."));
        }

        // ── Allow ─────────────────────────────────────────────────────────────
        _logger.LogInformation(
            "C-041 ALLOW — tool authorized. " +
            "ToolName={ToolName} ContractId={ContractId} TenantId={TenantId}",
            toolName, ctx.ContractId, ctx.TenantId);

        activity?.SetTag("allowed_tool", toolName);

        return Task.FromResult(new EvaluationResult(
            ClaimId,
            EvaluationVerdict.Allow,
            $"C-041: Tool '{toolName}' is in authorized_actions for contract '{ctx.ContractId}'."));
    }

    // ── Private helpers ────────────────────────────────────────────────────────

    /// <summary>
    /// Logs and returns a structured DENY result.
    /// Helper avoids repetition while keeping structured log parameters intact.
    /// </summary>
    private Task<EvaluationResult> Deny(
        Activity?  activity,
        string     reason,
        string     logMessage,
        params object[] logArgs)
    {
        // Structured log — args forwarded positionally; no string interpolation.
        _logger.LogInformation(logMessage, logArgs);
        activity?.SetTag("deny_reason", reason);
        return Task.FromResult(Denied(reason));
    }

    private EvaluationResult Denied(string reason) =>
        new(ClaimId, EvaluationVerdict.Deny, reason);
}