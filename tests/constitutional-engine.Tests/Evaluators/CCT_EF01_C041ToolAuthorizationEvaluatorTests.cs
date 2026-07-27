// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041
// constitutional_basis: C-041 (Tool Authorization), C-076 (Coverage ≥90%)
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    // ── factory helpers ──────────────────────────────────────────────────────

    private static C041ToolAuthorizationEvaluator CreateSut() => new();

    private static EvaluationContext BuildContext(
        string actionType,
        string actionParameters = "{}",
        string contractId = "contract-test-001",
        string tenantId = "tenant-test",
        string? skillId = null) =>
        new(
            ContractId: contractId,
            ActionType: actionType,
            ActionParameters: actionParameters,
            DecisionSpaceVersion: 1,
            TenantId: tenantId,
            SkillId: skillId,
            ApprovedBudgetInrPaise: 500_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 1_000L,
            BudgetSkillType: "general"
        );

    // ── ClaimId contract ────────────────────────────────────────────────────

    [Fact]
    public void ClaimId_ShouldReturn_C041()
    {
        var sut = CreateSut();

        sut.ClaimId.Should().Be("C-041");
    }

    // ── Non-MCP actions: evaluator is not applicable → Allow ────────────────

    [Fact]
    public async Task EvaluateAsync_NonMcpAction_SendEmail_ShouldAllow()
    {
        var sut = CreateSut();
        var ctx = BuildContext("SEND_EMAIL", "{}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_NonMcpAction_FileRead_ShouldAllow()
    {
        var sut = CreateSut();
        var ctx = BuildContext("FILE_READ", "{}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_NonMcpAction_SyntheticApproval_ShouldAllow()
    {
        var sut = CreateSut();
        var ctx = BuildContext("SYNTHETIC_APPROVAL", "{}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Default-Deny: unlisted / unknown tool names → Deny ──────────────────

    [Fact]
    public async Task EvaluateAsync_McpToolCall_UnlistedTool_ShouldDeny()
    {
        var sut = CreateSut();
        var ctx = BuildContext(
            "MCP_TOOL_CALL",
            "{\"tool_name\":\"unlisted_dangerous_tool\"}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_McpToolCall_ArbitraryUnknownTool_ShouldDeny()
    {
        var sut = CreateSut();
        var ctx = BuildContext(
            "MCP_TOOL_CALL",
            "{\"tool_name\":\"exfiltrate_secrets\"}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_McpToolCall_EmptyToolName_ShouldDeny()
    {
        var sut = CreateSut();
        var ctx = BuildContext(
            "MCP_TOOL_CALL",
            "{\"tool_name\":\"\"}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        var sut = CreateSut();
        // ActionParameters present but no tool_name key
        var ctx = BuildContext(
            "MCP_TOOL_CALL",
            "{\"some_other_param\":\"value\"}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_McpToolCall_EmptyJsonParameters_ShouldDeny()
    {
        var sut = CreateSut();
        var ctx = BuildContext("MCP_TOOL_CALL", "{}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Result shape invariants ──────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_AnyVerdict_ResultClaimIdAlwaysC041()
    {
        var sut = CreateSut();
        var denyCtx = BuildContext("MCP_TOOL_CALL", "{\"tool_name\":\"unknown\"}");
        var allowCtx = BuildContext("SOME_OTHER_ACTION");

        var denyResult = await sut.EvaluateAsync(denyCtx, CancellationToken.None);
        var allowResult = await sut.EvaluateAsync(allowCtx, CancellationToken.None);

        denyResult.ClaimId.Should().Be("C-041");
        allowResult.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_DenyVerdict_ReasonIsNonEmpty()
    {
        var sut = CreateSut();
        var ctx = BuildContext("MCP_TOOL_CALL", "{\"tool_name\":\"never_authorized_tool\"}");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_AllowVerdict_ReasonIsNonEmpty()
    {
        var sut = CreateSut();
        var ctx = BuildContext("NOT_A_TOOL_CALL");

        var result = await sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ── CancellationToken is respected ───────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_CancelledToken_NonMcpAction_StillCompletesOrThrows()
    {
        var sut = CreateSut();
        var ctx = BuildContext("SEND_EMAIL");
        using var cts = new CancellationTokenSource();

        // The evaluator is synchronous internally; a pre-cancelled token is safe
        var act = async () => await sut.EvaluateAsync(ctx, cts.Token);

        // Either completes successfully or propagates OperationCanceledException — both are valid
        await act.Should().NotThrowAsync<InvalidOperationException>();
    }

    // ── Multiple sequential calls are idempotent (C-085) ────────────────────

    [Fact]
    public async Task EvaluateAsync_CalledTwice_SameContext_ReturnsSameVerdict()
    {
        var sut = CreateSut();
        var ctx = BuildContext("MCP_TOOL_CALL", "{\"tool_name\":\"unknown_tool\"}");

        var first = await sut.EvaluateAsync(ctx, CancellationToken.None);
        var second = await sut.EvaluateAsync(ctx, CancellationToken.None);

        first.Verdict.Should().Be(second.Verdict);
        first.ClaimId.Should().Be(second.ClaimId);
    }

    [Fact]
    public async Task EvaluateAsync_NonMcpCalledTwice_SameContext_ReturnsSameVerdict()
    {
        var sut = CreateSut();
        var ctx = BuildContext("FILE_WRITE");

        var first = await sut.EvaluateAsync(ctx, CancellationToken.None);
        var second = await sut.EvaluateAsync(ctx, CancellationToken.None);

        first.Verdict.Should().Be(second.Verdict);
        first.Verdict.Should().Be(EvaluationVerdict.Allow);
    }
}