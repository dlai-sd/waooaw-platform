// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-076 (test coverage), C-082 (build validation)
using System.Text.Json;
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    private static EvaluationContext MakeContext(
        string actionType = "MCP_TOOL_CALL",
        string? toolName = "my_tool",
        string[]? authorizedTools = null,
        string[]? escalationTools = null,
        string tenantId = "tenant-1",
        bool omitToolNameKey = false)
    {
        var parameters = new Dictionary<string, object?>();

        if (!omitToolNameKey && toolName is not null)
            parameters["tool_name"] = toolName;
        else if (!omitToolNameKey && toolName is not null)
            parameters["tool_name"] = toolName;

        if (omitToolNameKey)
        {
            // deliberately exclude tool_name key
        }
        else if (toolName is not null)
        {
            parameters["tool_name"] = toolName;
        }
        else
        {
            parameters["tool_name"] = (object?)null;
        }

        if (authorizedTools is not null)
            parameters["authorized_tools"] = authorizedTools;

        if (escalationTools is not null)
            parameters["escalation_required_tools"] = escalationTools;

        var actionParameters = JsonSerializer.Serialize(parameters);

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
            BudgetSkillType: "default");
    }

    private static EvaluationContext MakeContextWithRawParameters(
        string actionType,
        string rawActionParameters,
        string tenantId = "tenant-1")
    {
        return new EvaluationContext(
            ContractId: "contract-001",
            ActionType: actionType,
            ActionParameters: rawActionParameters,
            DecisionSpaceVersion: 1,
            TenantId: tenantId,
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "default");
    }

    // ── Non-MCP passthrough ────────────────────────────────────────────────────

    [xUnit.Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        var ctx = MakeContext(actionType: "BUDGET_SPEND");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Allow scenarios ────────────────────────────────────────────────────────

    [xUnit.Fact]
    public async Task McpToolCall_AuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(
            toolName: "my_tool",
            authorizedTools: new[] { "my_tool", "other_tool" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task McpToolCall_AnotherAuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(
            toolName: "other_tool",
            authorizedTools: new[] { "my_tool", "other_tool" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Deny scenarios ─────────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_UnlistedTool_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "unlisted_tool",
            authorizedTools: new[] { "my_tool", "other_tool" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        // Serialize a dict that has authorized_tools but no tool_name key at all
        var parameters = new Dictionary<string, object?>
        {
            ["authorized_tools"] = new[] { "my_tool" }
        };
        var ctx = MakeContextWithRawParameters("MCP_TOOL_CALL", JsonSerializer.Serialize(parameters));

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyToolName_ShouldDeny()
    {
        var ctx = MakeContext(
            toolName: "",
            authorizedTools: new[] { "my_tool" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyActionParameters_ShouldDeny()
    {
        var ctx = MakeContextWithRawParameters("MCP_TOOL_CALL", "");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = MakeContextWithRawParameters("MCP_TOOL_CALL", "not-valid-json{{{{");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_NoAuthorizedToolsList_ShouldDeny()
    {
        // authorizedTools omitted — key absent from JSON
        var parameters = new Dictionary<string, object?>
        {
            ["tool_name"] = "my_tool"
        };
        var ctx = MakeContextWithRawParameters("MCP_TOOL_CALL", JsonSerializer.Serialize(parameters));

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
    public async Task McpToolCall_ToolNameCaseMismatch_ShouldDeny()
    {
        // Authorized list uses lowercase; request uses mixed case — case-sensitive match expected
        var ctx = MakeContext(
            toolName: "My_Tool",
            authorizedTools: new[] { "my_tool" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Escalate scenarios ─────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "escalate_tool",
            authorizedTools: new[] { "my_tool", "escalate_tool" },
            escalationTools: new[] { "escalate_tool" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    [Fact]
    public async Task McpToolCall_ToolInBothAuthorizedAndEscalation_ShouldEscalate()
    {
        var ctx = MakeContext(
            toolName: "shared_tool",
            authorizedTools: new[] { "shared_tool" },
            escalationTools: new[] { "shared_tool" });

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    // ── Contract invariants ────────────────────────────────────────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("BUDGET_SPEND")]
    [InlineData("CUSTOM_ACTION")]
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
    [InlineData("BUDGET_SPEND")]
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
        var ctx = MakeContext(
            toolName: "my_tool",
            authorizedTools: new[] { "my_tool" });

        var act = async () => await _sut.EvaluateAsync(ctx, CancellationToken.None);

        await act.Should().NotThrowAsync();
    }

    // ── Tenant-invariance ──────────────────────────────────────────────────────

    [Theory]
    [InlineData("tenant-alpha")]
    [InlineData("tenant-beta")]
    [InlineData("tenant-gamma")]
    public async Task McpToolCall_UnlistedTool_DeniedAcrossTenants(string tenantId)
    {
        var ctx = MakeContext(
            toolName: "unlisted_tool",
            authorizedTools: new[] { "my_tool" },
            tenantId: tenantId);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}