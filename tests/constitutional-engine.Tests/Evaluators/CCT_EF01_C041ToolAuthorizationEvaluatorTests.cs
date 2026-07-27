// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization), C-076 (test coverage), C-082 (build validation)
using System.Text.Json;
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    private static EvaluationContext MakeContext(
        string actionType = "MCP_TOOL_CALL",
        string? toolName = "my_tool",
        string[]? authorizedTools = null,
        string[]? escalationTools = null,
        string contractId = "contract-1",
        string tenantId = "tenant-a")
    {
        var parameters = new Dictionary<string, object?>();
        if (toolName is not null)
            parameters["tool_name"] = toolName;
        if (authorizedTools is not null)
            parameters["authorized_tools"] = authorizedTools;
        if (escalationTools is not null)
            parameters["escalation_required_tools"] = escalationTools;

        var actionParameters = JsonSerializer.Serialize(parameters);

        return new EvaluationContext(
            ContractId: contractId,
            ActionType: actionType,
            ActionParameters: actionParameters,
            DecisionSpaceVersion: 1,
            TenantId: tenantId,
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "general");
    }

    [Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        var ctx = MakeContext(actionType: "HTTP_POST");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

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
            toolName: null,
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
        var ctx = new EvaluationContext(
            ContractId: "c1",
            ActionType: "MCP_TOOL_CALL",
            ActionParameters: "",
            DecisionSpaceVersion: 1,
            TenantId: "t1",
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "general");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = new EvaluationContext(
            ContractId: "c1",
            ActionType: "MCP_TOOL_CALL",
            ActionParameters: "not-valid-json{{{",
            DecisionSpaceVersion: 1,
            TenantId: "t1",
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "general");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "send_email",
            authorizedTools: new[] { "read_file", "send_email" },
            escalationTools: new[] { "send_email" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_POST")]
    [InlineData("UNKNOWN_ACTION")]
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC041(string actionType)
    {
        var ctx = MakeContext(
            actionType: actionType,
            authorizedTools: new[] { "my_tool" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_GET")]
    [InlineData("CUSTOM_ACTION")]
    public async Task EvaluateAsync_AlwaysPopulatesReason(string actionType)
    {
        var ctx = MakeContext(
            actionType: actionType,
            authorizedTools: new[] { "my_tool" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        var ctx = MakeContext(authorizedTools: new[] { "my_tool" });
        using var cts = new CancellationTokenSource();
        var result = await _sut.EvaluateAsync(ctx, cts.Token);
        result.Should().NotBeNull();
    }

    [Theory]
    [InlineData("tenant-x")]
    [InlineData("tenant-y")]
    public async Task McpToolCall_UnlistedTool_DeniedAcrossTenants(string tenantId)
    {
        var ctx = MakeContext(
            toolName: "forbidden_tool",
            authorizedTools: new[] { "safe_tool" },
            tenantId: tenantId);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_NoAuthorizedToolsList_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "my_tool",
            authorizedTools: null);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyAuthorizedToolsList_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "my_tool",
            authorizedTools: Array.Empty<string>());
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_ToolInBothAuthorizedAndEscalation_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "dual_listed_tool",
            authorizedTools: new[] { "dual_listed_tool" },
            escalationTools: new[] { "dual_listed_tool" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    [Fact]
    public async Task McpToolCall_ToolNameCaseMismatch_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "Read_File",
            authorizedTools: new[] { "read_file" });
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}