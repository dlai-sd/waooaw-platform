// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-076 (test coverage), C-082 (build validation)
using System.Text.Json;
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    /// <summary>
    /// Builds an EvaluationContext whose ActionParameters is a JSON object
    /// containing the keys expected by C041ToolAuthorizationEvaluator.
    /// Pass <paramref name="rawActionParameters"/> to override the generated JSON entirely.
    /// </summary>
    private static EvaluationContext MakeContext(
        string actionType = "MCP_TOOL_CALL",
        string? toolName = null,
        string[]? authorizedTools = null,
        string[]? escalationTools = null,
        string tenantId = "tenant-001",
        string? rawActionParameters = null)
    {
        string paramsJson;
        if (rawActionParameters is not null)
        {
            paramsJson = rawActionParameters;
        }
        else
        {
            var dict = new Dictionary<string, string>();
            if (toolName is not null)
                dict["tool_name"] = toolName;
            if (authorizedTools is not null)
                dict["authorized_tools"] = JsonSerializer.Serialize(authorizedTools);
            if (escalationTools is not null)
                dict["escalation_required_tools"] = JsonSerializer.Serialize(escalationTools);
            paramsJson = JsonSerializer.Serialize(dict);
        }

        return new EvaluationContext(
            "contract-1",
            actionType,
            paramsJson,
            1,
            tenantId,
            null,
            100_000L,
            0L,
            0L,
            "default");
    }

    // ── Non-MCP action type ────────────────────────────────────────────────────

    [Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        var ctx = MakeContext(actionType: "SEND_EMAIL");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── MCP_TOOL_CALL — Allow scenarios ───────────────────────────────────────

    [Fact]
    public async Task McpToolCall_AuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(
            toolName: "read_file",
            authorizedTools: new[] { "read_file", "list_dir" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task McpToolCall_AnotherAuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(
            toolName: "list_dir",
            authorizedTools: new[] { "read_file", "list_dir" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── MCP_TOOL_CALL — Deny scenarios ────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_UnlistedTool_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "delete_file",
            authorizedTools: new[] { "read_file", "list_dir" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        // ActionParameters has authorized_tools but no tool_name key
        var ctx = MakeContext(
            authorizedTools: new[] { "read_file" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyToolName_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "",
            authorizedTools: new[] { "read_file" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyActionParameters_ShouldDeny()
    {
        // Empty JSON object — no tool_name, no authorized_tools
        var ctx = MakeContext(rawActionParameters: "{}");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = MakeContext(rawActionParameters: "not-valid-json{{");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_NoAuthorizedToolsList_ShouldDeny()
    {
        // tool_name present but authorized_tools key is absent
        var ctx = MakeContext(
            toolName: "read_file",
            authorizedTools: null);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyAuthorizedToolsList_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "read_file",
            authorizedTools: Array.Empty<string>());
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_ToolNameCaseMismatch_ShouldDeny()
    {
        // "Read_File" ≠ "read_file" — case-sensitive check
        var ctx = MakeContext(
            toolName: "Read_File",
            authorizedTools: new[] { "read_file" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── MCP_TOOL_CALL — Escalate scenarios ───────────────────────────────────

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "sensitive_op",
            authorizedTools: new[] { "read_file", "sensitive_op" },
            escalationTools: new[] { "sensitive_op" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    [Fact]
    public async Task McpToolCall_ToolInBothAuthorizedAndEscalation_ShouldEscalate()
    {
        // Escalation wins over authorization
        var ctx = MakeContext(
            toolName: "hybrid_tool",
            authorizedTools: new[] { "hybrid_tool" },
            escalationTools: new[] { "hybrid_tool" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    // ── Claim-ID and Reason invariants ────────────────────────────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("SEND_EMAIL")]
    [InlineData("HTTP_REQUEST")]
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC041(string actionType)
    {
        var ctx = MakeContext(actionType: actionType, rawActionParameters: "{}");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("SEND_EMAIL")]
    [InlineData("HTTP_REQUEST")]
    public async Task EvaluateAsync_AlwaysPopulatesReason(string actionType)
    {
        var ctx = MakeContext(actionType: actionType, rawActionParameters: "{}");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ── Cancellation / completion ─────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        var ctx = MakeContext(
            toolName: "read_file",
            authorizedTools: new[] { "read_file" });
        var act = async () => await _sut.EvaluateAsync(ctx, CancellationToken.None);
        await act.Should().NotThrowAsync();
    }

    // ── Cross-tenant consistency ──────────────────────────────────────────────

    [Theory]
    [InlineData("tenant-alpha")]
    [InlineData("tenant-beta")]
    [InlineData("tenant-gamma")]
    public async Task McpToolCall_UnlistedTool_DeniedAcrossTenants(string tenantId)
    {
        var ctx = MakeContext(
            toolName: "forbidden_tool",
            authorizedTools: new[] { "read_file" },
            tenantId: tenantId);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}