// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization), C-076 (test coverage), C-082 (build validation)
using System.Text.Json;
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    private static EvaluationContext MakeContext(
        string actionType = "MCP_TOOL_CALL",
        string? toolName = "calc",
        string[]? authorizedTools = null,
        string[]? escalationTools = null,
        string tenantId = "tenant-abc",
        string contractId = "contract-001")
    {
        var authorizedJson = authorizedTools is not null
            ? JsonSerializer.Serialize(authorizedTools)
            : null;
        var escalationJson = escalationTools is not null
            ? JsonSerializer.Serialize(escalationTools)
            : null;

        var parameters = new Dictionary<string, object?>();
        if (toolName is not null)
            parameters["tool_name"] = toolName;
        if (authorizedJson is not null)
            parameters["authorized_tools"] = authorizedJson;
        if (escalationJson is not null)
            parameters["escalation_required_tools"] = escalationJson;

        var actionParameters = JsonSerializer.Serialize(parameters);

        return new EvaluationContext(
            contractId,
            actionType,
            actionParameters,
            1,
            tenantId,
            null,
            100_000L,
            0L,
            0L,
            "GENERAL");
    }

    // ── Allow scenarios ────────────────────────────────────────────────────────

    [Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        var ctx = MakeContext(actionType: "HTTP_CALL", toolName: "calc",
            authorizedTools: new[] { "calc" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task McpToolCall_AuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(toolName: "calculator",
            authorizedTools: new[] { "calculator", "search" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task McpToolCall_AnotherAuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(toolName: "search",
            authorizedTools: new[] { "calculator", "search", "summarise" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Deny scenarios ─────────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_UnlistedTool_ShouldDeny()
    {
        var ctx = MakeContext(toolName: "delete_all",
            authorizedTools: new[] { "calculator", "search" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        // Construct parameters without tool_name
        var actionParameters = JsonSerializer.Serialize(new Dictionary<string, object?>
        {
            ["authorized_tools"] = JsonSerializer.Serialize(new[] { "calculator" })
        });

        var ctx = new EvaluationContext(
            "contract-001", "MCP_TOOL_CALL", actionParameters,
            1, "tenant-abc", null, 100_000L, 0L, 0L, "GENERAL");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyToolName_ShouldDeny()
    {
        var ctx = MakeContext(toolName: "",
            authorizedTools: new[] { "calculator", "search" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyActionParameters_ShouldDeny()
    {
        var ctx = new EvaluationContext(
            "contract-001", "MCP_TOOL_CALL", "{}",
            1, "tenant-abc", null, 100_000L, 0L, 0L, "GENERAL");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = new EvaluationContext(
            "contract-001", "MCP_TOOL_CALL", "NOT_VALID_JSON",
            1, "tenant-abc", null, 100_000L, 0L, 0L, "GENERAL");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_NoAuthorizedToolsList_ShouldDeny()
    {
        var actionParameters = JsonSerializer.Serialize(new Dictionary<string, object?>
        {
            ["tool_name"] = "calculator"
            // no authorized_tools key
        });

        var ctx = new EvaluationContext(
            "contract-001", "MCP_TOOL_CALL", actionParameters,
            1, "tenant-abc", null, 100_000L, 0L, 0L, "GENERAL");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyAuthorizedToolsList_ShouldDeny()
    {
        var ctx = MakeContext(toolName: "calculator",
            authorizedTools: Array.Empty<string>());

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_ToolNameCaseMismatch_ShouldDeny()
    {
        // authorized_tools has "Calculator" (capital C), tool_name is "calculator" (lower c)
        var ctx = MakeContext(toolName: "calculator",
            authorizedTools: new[] { "Calculator", "Search" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Escalate scenarios ─────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "send_email",
            authorizedTools: new[] { "calculator", "send_email" },
            escalationTools: new[] { "send_email" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    [Fact]
    public async Task McpToolCall_ToolInBothAuthorizedAndEscalation_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "delete_record",
            authorizedTools: new[] { "delete_record", "calculator" },
            escalationTools: new[] { "delete_record" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    // ── Invariant scenarios ────────────────────────────────────────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_CALL")]
    [InlineData("DB_QUERY")]
    [InlineData("FILE_READ")]
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC041(string actionType)
    {
        var ctx = MakeContext(actionType: actionType,
            toolName: "calculator",
            authorizedTools: new[] { "calculator" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
    }

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_CALL")]
    [InlineData("UNKNOWN_TYPE")]
    public async Task EvaluateAsync_AlwaysPopulatesReason(string actionType)
    {
        var ctx = MakeContext(actionType: actionType,
            toolName: "calculator",
            authorizedTools: new[] { "calculator" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        var ctx = MakeContext(toolName: "calculator",
            authorizedTools: new[] { "calculator" });

        using var cts = new CancellationTokenSource();

        var act = async () => await _sut.EvaluateAsync(ctx, cts.Token);

        await act.Should().NotThrowAsync();
    }

    // ── Cross-tenant invariant ─────────────────────────────────────────────────

    [Theory]
    [InlineData("tenant-alpha")]
    [InlineData("tenant-beta")]
    [InlineData("org-gamma")]
    [InlineData("")]
    public async Task McpToolCall_UnlistedTool_DeniedAcrossTenants(string tenantId)
    {
        var ctx = MakeContext(
            toolName: "forbidden_tool",
            authorizedTools: new[] { "calculator" },
            tenantId: tenantId);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}