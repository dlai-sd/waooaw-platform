// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-041 (Tool Authorization), C-076 (Test Coverage)
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01: Constitutional Compliance Tests for C041ToolAuthorizationEvaluator.
/// Constitutional basis: C-041 (Tool Authorization — every tool call must be within the
/// customer's authorized Decision Space).
/// Default-deny principle: unlisted tool = DENY (C-041 constitutional floor).
/// Coverage requirement: ≥90% (C-076).
/// </summary>
public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    // ── Helpers ──────────────────────────────────────────────────────────────

    private static EvaluationContext CreateContext(
        string actionType,
        string contractId = "contract-test-001",
        string tenantId = "tenant-test-001",
        string actionParameters = "{}",
        int decisionSpaceVersion = 1)
    {
        return new EvaluationContext
        {
            ContractId = contractId,
            ActionType = actionType,
            ActionParameters = actionParameters,
            DecisionSpaceVersion = decisionSpaceVersion,
            TenantId = tenantId,
            SkillId = null,
            ApprovedBudgetInrPaise = 0L,
            CurrentSpendInrPaise = 0L,
            ProposedSpendInrPaise = 0L,
            BudgetSkillType = string.Empty
        };
    }

    // ── CCT-EF-01-01: Default Deny — constitutional floor ────────────────────

    [Fact]
    public async Task UnlistedActionType_ShouldReturn_Deny_ConstitutionalFloor()
    {
        // Arrange — C-041: unlisted tool must be denied (constitutional default-deny)
        var ctx = CreateContext("UNKNOWN_TOOL_NOT_IN_ANY_WHITELIST");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Deny, "C-041 default-deny: unlisted tools must be denied");
        result.ClaimId.Should().Be("C-041");
    }

    // ── CCT-EF-01-02: Empty action type ─────────────────────────────────────

    [Fact]
    public async Task EmptyActionType_ShouldReturn_Deny()
    {
        // Arrange — no authorization basis exists for an empty action type
        var ctx = CreateContext(string.Empty);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Deny, "C-041: empty action type has no authorization basis");
    }

    // ── CCT-EF-01-03: Whitespace-only action type ────────────────────────────

    [Fact]
    public async Task WhitespaceActionType_ShouldReturn_Deny()
    {
        // Arrange
        var ctx = CreateContext("   ");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny, "C-041: whitespace action type must be denied");
    }

    // ── CCT-EF-01-04: Result is never null ───────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_AlwaysReturnsNonNullResult()
    {
        // Arrange
        var ctx = CreateContext("ANY_RANDOM_ACTION");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull("evaluator must never return null — ERROR HANDLING RULE 2");
    }

    // ── CCT-EF-01-05: ClaimId is always C-041 ───────────────────────────────

    [Fact]
    public async Task EvaluateAsync_ClaimId_ShouldBe_C041()
    {
        // Arrange — C-073: every evaluator result must name its constitutional claim
        var ctx = CreateContext("SOME_ACTION_TYPE");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.ClaimId.Should().Be("C-041", "C-073 traceability requires result.ClaimId = 'C-041'");
    }

    // ── CCT-EF-01-06: Reason is always populated ─────────────────────────────

    [Fact]
    public async Task EvaluateAsync_Reason_ShouldNotBeNullOrEmpty()
    {
        // Arrange
        var ctx = CreateContext("UNKNOWN_TOOL");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Reason.Should().NotBeNullOrEmpty(
            "every evaluation decision must carry a human-readable reason for audit (C-023)");
    }

    // ── CCT-EF-01-07: Verdict is always a valid enum value ───────────────────

    [Fact]
    public async Task EvaluateAsync_Verdict_ShouldBeValidEnumValue()
    {
        // Arrange
        var ctx = CreateContext("UNKNOWN_TOOL");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        var validVerdicts = new[] { EvaluationVerdict.Allow, EvaluationVerdict.Deny, EvaluationVerdict.Escalate };
        validVerdicts.Should().Contain(result.Verdict, "verdict must be one of the three valid outcomes");
    }

    // ── CCT-EF-01-08: Multiple unlisted tools — all denied ────────────────────

    [Theory]
    [InlineData("ARBITRARY_TOOL")]
    [InlineData("HACK_THE_SYSTEM")]
    [InlineData("ROOT_ACCESS_OVERRIDE")]
    [InlineData("DELETE_ALL_RECORDS")]
    [InlineData("UNRESTRICTED_BATCH_OP")]
    [InlineData("SUDO_EXECUTE")]
    public async Task MultipleUnlistedTools_AllShouldReturn_Deny(string toolName)
    {
        // Arrange — C-041 constitutional floor: every unlisted tool must be denied
        var ctx = CreateContext(toolName);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            $"C-041 constitutional floor: unlisted tool '{toolName}' must be denied");
        result.ClaimId.Should().Be("C-041");
    }

    // ── CCT-EF-01-09: JSON action parameters — no throw ──────────────────────

    [Fact]
    public async Task EvaluateAsync_WithJsonActionParameters_ShouldNotThrow()
    {
        // Arrange — ActionParameters is JSON-encoded; evaluator must handle it safely
        var ctx = CreateContext(
            "UNKNOWN_TOOL",
            actionParameters: "{\"key\":\"value\",\"nested\":{\"count\":42}}");

        // Act
        Func<Task> act = async () => await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        await act.Should().NotThrowAsync(
            "evaluator must handle JSON action parameters without throwing");
    }

    // ── CCT-EF-01-10: Empty JSON object action parameters ────────────────────

    [Fact]
    public async Task EvaluateAsync_WithEmptyJsonObject_ShouldNotThrow()
    {
        // Arrange
        var ctx = CreateContext("UNKNOWN_TOOL", actionParameters: "{}");

        // Act
        Func<Task> act = async () => await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        await act.Should().NotThrowAsync(
            "evaluator must handle empty JSON object for action parameters");
    }

    // ── CCT-EF-01-11: Valid contract + tenant context ─────────────────────────

    [Fact]
    public async Task EvaluateAsync_WithValidContractAndTenant_ShouldComplete()
    {
        // Arrange
        var ctx = CreateContext(
            "SOME_UNKNOWN_ACTION",
            contractId: "e2f7a3bc-1234-5678-abcd-ef0123456789",
            tenantId: "a1b2c3d4-5678-90ab-cdef-0123456789ab");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull("evaluator must complete for valid contract/tenant contexts");
    }

    // ── CCT-EF-01-12: CancellationToken respected — no indefinite block ───────

    [Fact]
    public async Task EvaluateAsync_WithCancelledToken_ShouldNotHangIndefinitely()
    {
        // Arrange — ERROR HANDLING RULE 4: never block indefinitely
        var ctx = CreateContext("SOME_ACTION");
        using var cts = new CancellationTokenSource();
        await cts.CancelAsync();

        // Act — evaluator may complete (synchronous path) or throw OperationCanceledException
        // Either is constitutionally compliant. What it MUST NOT do is hang.
        Func<Task> act = async () => await _sut.EvaluateAsync(ctx, cts.Token);

        // Assert — must not timeout (i.e. must not block indefinitely)
        await act.Should().NotThrowAsync<TimeoutException>(
            "evaluator must never block indefinitely — C-041 latency constraint");
    }

    // ── CCT-EF-01-13: DecisionSpaceVersion propagated in context ─────────────

    [Fact]
    public async Task EvaluateAsync_WithDecisionSpaceVersion_ShouldComplete()
    {
        // Arrange — DecisionSpaceVersion must be carried in context for stale-space detection
        var ctx = CreateContext("UNKNOWN_TOOL", decisionSpaceVersion: 42);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Deny, "unlisted tool is denied regardless of decision space version");
    }

    // ── CCT-EF-01-14: SkillId null — evaluator handles gracefully ────────────

    [Fact]
    public async Task EvaluateAsync_WithNullSkillId_ShouldNotThrow()
    {
        // Arrange — SkillId is optional (nullable)
        var ctx = new EvaluationContext
        {
            ContractId = "contract-001",
            ActionType = "UNKNOWN_TOOL",
            ActionParameters = "{}",
            DecisionSpaceVersion = 1,
            TenantId = "tenant-001",
            SkillId = null,
            ApprovedBudgetInrPaise = 0L,
            CurrentSpendInrPaise = 0L,
            ProposedSpendInrPaise = 0L,
            BudgetSkillType = string.Empty
        };

        // Act
        Func<Task> act = async () => await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        await act.Should().NotThrowAsync(
            "evaluator must handle null SkillId without throwing");
    }

    // ── CCT-EF-01-15: Verdict for unlisted tool is Deny not Escalate ─────────

    [Fact]
    public async Task UnlistedTool_ShouldBe_Deny_NotEscalate()
    {
        // Arrange — C-041: unknown tools must be DENIED outright, not escalated
        // Escalation is for scope-boundary cases, not unauthorized tools.
        var ctx = CreateContext("COMPLETELY_UNKNOWN_XYZ_TOOL");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().NotBe(
            EvaluationVerdict.Allow,
            "C-041: unlisted tool must never be allowed");

        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "C-041 default-deny: completely unknown tools must be Deny, not Escalate");
    }
}