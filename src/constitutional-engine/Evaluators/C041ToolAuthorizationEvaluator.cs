// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-059 (Traceability)
// SCOPE: WC012-02b — ValidateAction evaluator, default-deny tool authorization

namespace Waooaw.ConstitutionalEngine.Evaluators;

/// <summary>
/// Enforces C-041: every MCP tool call requires an explicit authorization entry in the
/// decision space. Anything not listed is DENIED — default deny is the starting state.
/// </summary>
public sealed class C041ToolAuthorizationEvaluator : IClaimEvaluator
{
    private const string ToolNameKey = "tool_name";

    /// <summary>
    /// Action types that this evaluator considers valid candidates for authorization.
    /// Any action type NOT in this set is immediately denied.
    /// </summary>
    private static readonly IReadOnlySet<string> AuthorizedActionTypes =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "MCP_TOOL_CALL",
            "SKILL_INVOKE",
            "DATA_READ",
            "DATA_WRITE",
            "AGENT_SPAWN",
        };

    /// <summary>
    /// Decision-space whitelist of tool names permitted at this version.
    /// Unlisted tool = DENY — constitutional default.
    /// </summary>
    private static readonly IReadOnlySet<string> AuthorizedToolNames =
        new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "file_read",
            "file_write",
            "code_execute",
            "web_search",
            "database_query",
            "calendar_read",
            "calendar_write",
            "email_send",
            "slack_post",
            "github_pr_create",
            "github_pr_read",
            "jira_ticket_create",
            "jira_ticket_read",
            "confluence_page_read",
            "confluence_page_write",
        };

    /// <inheritdoc />
    public string ClaimId => "C-041";

    /// <inheritdoc />
    public Task<EvaluationResult> EvaluateAsync(EvaluationContext ctx, CancellationToken ct)
    {
        // Guard: action type must be present — empty/whitespace is a hard deny.
        if (string.IsNullOrWhiteSpace(ctx.ActionType))
            return Deny("Action type is null or empty — default deny enforced by C-041.");

        // Guard: action type must exist in the authorized decision space.
        if (!AuthorizedActionTypes.Contains(ctx.ActionType))
            return Deny(
                $"Action type '{ctx.ActionType}' is not recognized in the constitutional " +
                $"decision space — default deny enforced by C-041.");

        // Extract tool name from JSON-encoded ActionParameters.
        var toolName = ctx.GetParameter(ToolNameKey);

        // Guard: tool name parameter must be supplied.
        if (string.IsNullOrWhiteSpace(toolName))
            return Deny(
                $"Parameter '{ToolNameKey}' is absent or empty in ActionParameters — " +
                $"cannot authorize an unnamed tool (C-041 default deny).");

        // Guard: tool name must appear in the authorized whitelist.
        if (!AuthorizedToolNames.Contains(toolName))
            return Deny(
                $"Tool '{toolName}' is not listed in the authorized decision space — " +
                $"default deny enforced by C-041.");

        return Allow(
            $"Tool '{toolName}' is authorized for action type '{ctx.ActionType}' (C-041).");
    }

    // ── private helpers ────────────────────────────────────────────────────────

    private Task<EvaluationResult> Deny(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Deny, reason));

    private Task<EvaluationResult> Allow(string reason) =>
        Task.FromResult(new EvaluationResult(ClaimId, EvaluationVerdict.Allow, reason));
}