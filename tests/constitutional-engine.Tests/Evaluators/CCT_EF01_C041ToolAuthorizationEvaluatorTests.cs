// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-076 (Test Coverage ≥90%), C-082 (Build Validation)
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
        string? actionParameters = null,
        string tenantId = "tenant-1",
        string contractId = "contract-1")
    {
        var parameters = actionParameters
            ?? JsonSerializer.Serialize(new
            {
                tool_name          = "file_read",
                authorized_tools   = new[] { "file_read", "file_write" },
                escalation_required_tools = new[] { "delete_all_files" }
            });

        return new EvaluationContext(
            ContractId:            contractId,
            ActionType:            actionType,
            ActionParameters:      parameters,
            DecisionSpaceVersion:  1,
            TenantId:              tenantId,
            SkillId:               null,
            ApprovedBudgetInrPaise: 500_000L,
            CurrentSpendInrPaise:  0L,
            ProposedSpendInrPaise: 100L,
            BudgetSkillType:       "default");
    }

    // ─── Allow scenarios ──────────────────────────────────────────────────────

    [Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        var ctx = MakeContext(actionType: "HTTP_CALL");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task McpToolCall_AuthorizedTool_ShouldAllow()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "file_read",
            authorized_tools = new[] { "file_read", "file_write" },
            escalation_required_tools = Array.Empty<string>()
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task McpToolCall_AnotherAuthorizedTool_ShouldAllow()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "file_write",
            authorized_tools = new[] { "file_read", "file_write" },
            escalation_required_tools = Array.Empty<string>()
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ─── Deny scenarios ───────────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_UnlistedTool_ShouldDeny()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "exec_shell",
            authorized_tools = new[] { "file_read", "file_write" },
            escalation_required_tools = Array.Empty<string>()
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            authorized_tools = new[] { "file_read" },
            escalation_required_tools = Array.Empty<string>()
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyToolName_ShouldDeny()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "",
            authorized_tools = new[] { "file_read" },
            escalation_required_tools = Array.Empty<string>()
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_EmptyActionParameters_ShouldDeny()
    {
        var ctx = MakeContext(actionParameters: "{}");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = MakeContext(actionParameters: "{ this is not valid json !!!");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ─── Escalate scenarios ───────────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "delete_all_files",
            authorized_tools = new[] { "file_read", "file_write" },
            escalation_required_tools = new[] { "delete_all_files" }
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
    }

    // ─── ClaimId invariants ───────────────────────────────────────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_CALL")]
    [InlineData("DATABASE_QUERY")]
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC041(string actionType)
    {
        var ctx = MakeContext(actionType: actionType);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
    }

    // ─── Reason invariants ────────────────────────────────────────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("HTTP_CALL")]
    [InlineData("BATCH_TASK")]
    public async Task EvaluateAsync_AlwaysPopulatesReason(string actionType)
    {
        var ctx = MakeContext(actionType: actionType);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ─── Cancellation ─────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        using var cts = new CancellationTokenSource();
        var ctx = MakeContext();

        var result = await _sut.EvaluateAsync(ctx, cts.Token);

        result.Should().NotBeNull();
    }

    // ─── Cross-tenant isolation ───────────────────────────────────────────────

    [Fact]
    public async Task McpToolCall_UnlistedTool_DeniedAcrossTenants()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "exec_shell",
            authorized_tools = new[] { "file_read" },
            escalation_required_tools = Array.Empty<string>()
        });

        var tenants = new[] { "tenant-alpha", "tenant-beta", "tenant-gamma" };

        foreach (var tenant in tenants)
        {
            var ctx = MakeContext(tenantId: tenant, actionParameters: parameters);
            var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
            result.Verdict.Should().Be(EvaluationVerdict.Deny,
                because: $"tenant '{tenant}' should not be able to use unlisted tool 'exec_shell'");
        }
    }

    // ─── Default-deny assertion (C-041 constitutional basis) ─────────────────

    [Fact]
    public async Task McpToolCall_NoAuthorizedToolsList_ShouldDeny()
    {
        // authorized_tools omitted entirely — default deny must hold
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name = "file_read"
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "C-041 requires default deny when no authorized_tools list is provided");
    }

    [Fact]
    public async Task McpToolCall_EmptyAuthorizedToolsList_ShouldDeny()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "file_read",
            authorized_tools = Array.Empty<string>(),
            escalation_required_tools = Array.Empty<string>()
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "C-041 requires default deny when authorized_tools list is empty");
    }

    // ─── Escalation takes priority over authorized list ───────────────────────

    [Fact]
    public async Task McpToolCall_ToolInBothAuthorizedAndEscalation_ShouldEscalate()
    {
        // escalation_required_tools takes precedence over authorized_tools
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "sensitive_read",
            authorized_tools = new[] { "sensitive_read" },
            escalation_required_tools = new[] { "sensitive_read" }
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Escalate,
            because: "escalation_required_tools must take precedence over authorized_tools for the same tool");
    }

    // ─── Case-sensitivity (tools must match exactly) ──────────────────────────

    [Fact]
    public async Task McpToolCall_ToolNameCaseMismatch_ShouldDeny()
    {
        var parameters = JsonSerializer.Serialize(new
        {
            tool_name        = "File_Read",           // different case
            authorized_tools = new[] { "file_read" },
            escalation_required_tools = Array.Empty<string>()
        });
        var ctx = MakeContext(actionParameters: parameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Evaluator is expected to perform case-sensitive matching (default deny)
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "tool name matching should be case-sensitive per C-041 default-deny");
    }
}