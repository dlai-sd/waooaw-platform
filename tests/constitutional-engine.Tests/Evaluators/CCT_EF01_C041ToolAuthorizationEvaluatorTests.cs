// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-076 (Audit Coverage ≥90%)
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    // ── helpers ────────────────────────────────────────────────────────────────

    private static EvaluationContext MakeContext(
        string actionType,
        string actionParameters,
        string contractId = "contract-001",
        string tenantId   = "tenant-001") =>
        new(
            ContractId:             contractId,
            ActionType:             actionType,
            ActionParameters:       actionParameters,
            DecisionSpaceVersion:   1,
            TenantId:               tenantId,
            SkillId:                null,
            ApprovedBudgetInrPaise: 1_000_000L,
            CurrentSpendInrPaise:   0L,
            ProposedSpendInrPaise:  500L,
            BudgetSkillType:        "default"
        );

    // ── CCT-EF-01-A: non-MCP action type → Allow (evaluator is not applicable) ─

    [xUnit.Fact]
    public async Task NonMcpActionType_ShouldAllow()
    {
        // Arrange
        var ctx = MakeContext(
            actionType:       "HTTP_CALL",
            actionParameters: """{"url":"https://example.com"}""");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }
    // ── CCT-EF-01-B: MCP_TOOL_CALL with an explicitly authorised tool → Allow ──

    [Fact]
    public async Task McpToolCall_AuthorizedTool_ShouldAllow()
    {
        // Arrange — "github_search" is an allowed tool in the whitelist
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: """{"tool_name":"github_search","args":{}}""");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── CCT-EF-01-C: MCP_TOOL_CALL with a second authorised tool → Allow ──────

    [Fact]
    public async Task McpToolCall_AnotherAuthorizedTool_ShouldAllow()
    {
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: """{"tool_name":"file_read","args":{}}""");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── CCT-EF-01-D: Default-deny — unlisted tool name → Deny (C-041 §1) ──────

    [Fact]
    public async Task McpToolCall_UnlistedTool_ShouldDeny()
    {
        // Arrange — "rm_rf_root" is not in any authorised list
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: """{"tool_name":"rm_rf_root","args":{}}""");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert — default-deny: unlisted tool MUST be denied
        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ── CCT-EF-01-E: Missing tool_name key → Deny ────────────────────────────

    [Fact]
    public async Task McpToolCall_MissingToolNameKey_ShouldDeny()
    {
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: """{"args":{}}""");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── CCT-EF-01-F: Empty tool_name value → Deny ────────────────────────────

    [Fact]
    public async Task McpToolCall_EmptyToolName_ShouldDeny()
    {
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: """{"tool_name":"","args":{}}""");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── CCT-EF-01-G: Empty/blank ActionParameters → Deny ─────────────────────

    [Fact]
    public async Task McpToolCall_EmptyActionParameters_ShouldDeny()
    {
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: "");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── CCT-EF-01-H: Malformed JSON ActionParameters → Deny ──────────────────

    [Fact]
    public async Task McpToolCall_MalformedJson_ShouldDeny()
    {
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: "NOT_JSON");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── CCT-EF-01-I: Tool requiring human review → Escalate ──────────────────

    [Fact]
    public async Task McpToolCall_EscalationRequiredTool_ShouldEscalate()
    {
        // Arrange — tool is known but flagged as requiring human review
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: """{"tool_name":"payment_execute","requires_approval":true}""");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert — any verdict other than a silent pass is acceptable;
        // the evaluator MUST NOT silently Allow an approval-flagged tool.
        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().NotBe(EvaluationVerdict.Allow,
            because: "tools requiring approval must not be silently allowed");
    }

    // ── CCT-EF-01-J: ClaimId is always "C-041" regardless of outcome ─────────

    [Theory]
    [InlineData("MCP_TOOL_CALL", """{"tool_name":"github_search"}""")]
    [InlineData("MCP_TOOL_CALL", """{"tool_name":"unknown_tool_xyz"}""")]
    [InlineData("HTTP_CALL",     """{}""")]
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC041(
        string actionType, string actionParameters)
    {
        var ctx = MakeContext(actionType, actionParameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
    }

    // ── CCT-EF-01-K: Reason is always populated (non-empty) ──────────────────

    [Theory]
    [InlineData("MCP_TOOL_CALL", """{"tool_name":"github_search"}""")]
    [InlineData("MCP_TOOL_CALL", """{"tool_name":"no_such_tool"}""")]
    [InlineData("HTTP_CALL",     """{}""")]
    public async Task EvaluateAsync_AlwaysPopulatesReason(
        string actionType, string actionParameters)
    {
        var ctx = MakeContext(actionType, actionParameters);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNullOrWhiteSpace(
            because: "C-059 traceability requires a non-empty reason on every verdict");
    }

    // ── CCT-EF-01-L: CancellationToken.None completes synchronously ──────────

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        var ctx = MakeContext(
            actionType:       "MCP_TOOL_CALL",
            actionParameters: """{"tool_name":"github_search"}""");

        using var cts = new CancellationTokenSource();
        var result = await _sut.EvaluateAsync(ctx, cts.Token);

        result.Should().NotBeNull();
    }

    // ── CCT-EF-01-M: Different tenants receive same verdict for same tool ─────

    [Fact]
    public async Task McpToolCall_UnlistedTool_DeniedAcrossTenants()
    {
        var ctxA = MakeContext("MCP_TOOL_CALL", """{"tool_name":"unknown_tool"}""", tenantId: "tenant-A");
        var ctxB = MakeContext("MCP_TOOL_CALL", """{"tool_name":"unknown_tool"}""", tenantId: "tenant-B");

        var resultA = await _sut.EvaluateAsync(ctxA, CancellationToken.None);
        var resultB = await _sut.EvaluateAsync(ctxB, CancellationToken.None);

        resultA.Verdict.Should().Be(EvaluationVerdict.Deny);
        resultB.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}