// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization), C-076 (test coverage), C-082 (build validation)
using System.Text.Json;
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    /// <summary>
    /// Builds an EvaluationContext. Pass <c>omitToolName: true</c> to exclude the
    /// "tool_name" key entirely, or pass <c>toolName: ""</c> for an empty string value.
    /// Pass <c>rawActionParameters</c> to override the entire JSON blob.
    /// </summary>
    private static EvaluationContext MakeContext(
        string actionType = "MCP_TOOL_CALL",
        string? toolName = "my_tool",
        bool omitToolName = false,
        string[]? authorizedTools = null,
        string[]? escalationTools = null,
        string tenantId = "tenant-001",
        string? rawActionParameters = null)
    {
        string actionParameters;
        if (rawActionParameters is not null)
        {
            actionParameters = rawActionParameters;
        }
        else
        {
            var dict = new Dictionary<string, object?>();
            if (!omitToolName)
                dict["tool_name"] = toolName;
            if (authorizedTools is not null)
                dict["authorized_tools"] = authorizedTools;
            if (escalationTools is not null)
                dict["escalation_required_tools"] = escalationTools;
            actionParameters = JsonSerializer.Serialize(dict);
        }

        return new EvaluationContext(
            ContractId: "contract-001",
            ActionType: actionType,
            ActionParameters: actionParameters,
            DecisionSpaceVersion: 1,
            TenantId: tenantId,
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "GENERAL");
    }

    // ── Non-MCP passthrough ────────────────────────────────────────────────────

    [Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        var ctx = MakeContext(actionType: "HTTP_CALL");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Allow scenarios ────────────────────────────────────────────────────────

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

    // ── Deny scenarios ─────────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_UnlistedTool_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "delete_all",
            authorizedTools: new[] { "read_file" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        var ctx = MakeContext(
            omitToolName: true,
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
        var ctx = MakeContext(rawActionParameters: "");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = MakeContext(rawActionParameters: "{ not valid json {{");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_NoAuthorizedToolsList_ShouldDeny()
    {
        // authorized_tools key is absent entirely — default deny
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
        // Authorized list contains "read_file" but tool_name is "Read_File" (case differs)
        var ctx = MakeContext(
            toolName: "Read_File",
            authorizedTools: new[] { "read_file" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Escalate scenarios ─────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "send_payment",
            authorizedTools: new[] { "read_file", "send_payment" },
            escalationTools: new[] { "send_payment" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    [Fact]
    public async Task McpToolCall_ToolInBothAuthorizedAndEscalation_ShouldEscalate()
    {
        // Escalation takes precedence over authorization
        var ctx = MakeContext(
            toolName: "transfer_funds",
            authorizedTools: new[] { "transfer_funds", "read_file" },
            escalationTools: new[] { "transfer_funds" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    // ── Cross-cutting contract properties ─────────────────────────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_CALL")]
    [InlineData("DB_QUERY")]
    [InlineData("SEND_EMAIL")]
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC041(string actionType)
    {
        var ctx = MakeContext(actionType: actionType, authorizedTools: new[] { "my_tool" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_CALL")]
    [InlineData("DB_QUERY")]
    public async Task EvaluateAsync_AlwaysPopulatesReason(string actionType)
    {
        var ctx = MakeContext(actionType: actionType, authorizedTools: new[] { "my_tool" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        var ctx = MakeContext(
            toolName: "read_file",
            authorizedTools: new[] { "read_file" });
        using var cts = new CancellationTokenSource();
        var result = await _sut.EvaluateAsync(ctx, cts.Token);
        result.Should().NotBeNull();
    }

    // ── Tenant-isolation (deny is universal) ──────────────────────────────────

    [Theory]
    [InlineData("tenant-alpha")]
    [InlineData("tenant-beta")]
    [InlineData("tenant-gamma")]
    [InlineData("")]
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