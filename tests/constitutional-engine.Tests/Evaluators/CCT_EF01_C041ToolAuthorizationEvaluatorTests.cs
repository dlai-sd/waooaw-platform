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

    private static EvaluationContext MakeContext(
        string actionType = "MCP_TOOL_CALL",
        string? toolName = "my_tool",
        string[]? authorizedTools = null,
        string[]? escalationTools = null,
        string tenantId = "tenant-001",
        string contractId = "contract-001")
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
            ProposedSpendInrPaise: 1_000L,
            BudgetSkillType: "generic");
    }

    // ── Non-MCP action type ────────────────────────────────────────────────

    [Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        var ctx = MakeContext(actionType: "REST_CALL");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Authorized tool scenarios ──────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_AuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(
            toolName: "approved_tool",
            authorizedTools: ["approved_tool", "other_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task McpToolCall_AnotherAuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(
            toolName: "other_tool",
            authorizedTools: ["approved_tool", "other_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Deny scenarios ─────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_UnlistedTool_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "unknown_tool",
            authorizedTools: ["approved_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: null,
            authorizedTools: ["approved_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyToolName_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "",
            authorizedTools: ["approved_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyActionParameters_ShouldDeny()
    {
        var ctx = new EvaluationContext(
            ContractId: "c-1",
            ActionType: "MCP_TOOL_CALL",
            ActionParameters: "",
            DecisionSpaceVersion: 1,
            TenantId: "t-1",
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "generic");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = new EvaluationContext(
            ContractId: "c-1",
            ActionType: "MCP_TOOL_CALL",
            ActionParameters: "not-valid-json{{{{",
            DecisionSpaceVersion: 1,
            TenantId: "t-1",
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "generic");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_NoAuthorizedToolsList_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "some_tool",
            authorizedTools: null);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyAuthorizedToolsList_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "some_tool",
            authorizedTools: []);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_ToolNameCaseMismatch_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "Approved_Tool",
            authorizedTools: ["approved_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Escalate scenarios ─────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "sensitive_tool",
            authorizedTools: ["sensitive_tool"],
            escalationTools: ["sensitive_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    [Fact]
    public async Task McpToolCall_ToolInBothAuthorizedAndEscalation_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "dual_tool",
            authorizedTools: ["dual_tool", "safe_tool"],
            escalationTools: ["dual_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    // ── ClaimId and Reason invariants ──────────────────────────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("REST_CALL")]
    [InlineData("GRAPHQL_QUERY")]
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC041(string actionType)
    {
        var ctx = MakeContext(actionType: actionType, authorizedTools: ["any"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("REST_CALL")]
    [InlineData("OTHER_ACTION")]
    public async Task EvaluateAsync_AlwaysPopulatesReason(string actionType)
    {
        var ctx = MakeContext(actionType: actionType, authorizedTools: ["my_tool"]);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ── Cancellation ───────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        var ctx = MakeContext(
            toolName: "approved_tool",
            authorizedTools: ["approved_tool"]);
        var act = async () => await _sut.EvaluateAsync(ctx, CancellationToken.None);
        await act.Should().NotThrowAsync();
    }

    // ── Cross-tenant consistency ───────────────────────────────────────────

    [Theory]
    [InlineData("tenant-alpha")]
    [InlineData("tenant-beta")]
    [InlineData("tenant-gamma")]
    public async Task McpToolCall_UnlistedTool_DeniedAcrossTenants(string tenantId)
    {
        var ctx = MakeContext(
            toolName: "unknown_tool",
            authorizedTools: ["approved_tool"],
            tenantId: tenantId);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}