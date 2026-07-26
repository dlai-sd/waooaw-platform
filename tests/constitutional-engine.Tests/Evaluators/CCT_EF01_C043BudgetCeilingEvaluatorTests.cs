// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator
// constitutional_basis: C-043 (Budget Ceiling), C-051 (Resource Transparency),
//                       C-059 (Traceability), C-073 (Annotation), C-076 (Unit Tests ≥90%)

#nullable enable

using FluentAssertions;
using Microsoft.Extensions.Logging;
using Moq;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01 gate: unit tests for C043BudgetCeilingEvaluator.
/// Verifies that actions whose proposed spend would breach the approved monthly
/// budget ceiling are denied (C-043), and that actions within budget are allowed.
/// </summary>
// C-073: test class annotates constitutional obligation under test
public sealed class CCT_EF01_C043BudgetCeilingEvaluatorTests
{
    private readonly C043BudgetCeilingEvaluator _sut;
    private readonly Mock<ILogger<C043BudgetCeilingEvaluator>> _loggerMock;

    public CCT_EF01_C043BudgetCeilingEvaluatorTests()
    {
        _loggerMock = new Mock<ILogger<C043BudgetCeilingEvaluator>>();
        _sut = new C043BudgetCeilingEvaluator(_loggerMock.Object);
    }

    // ── helpers ─────────────────────────────────────────────────────────────

    // C-073: helper encapsulates EvaluationContext construction for budget scenarios
    private static EvaluationContext BuildContext(
        long approvedBudgetInrPaise,
        long currentSpendInrPaise,
        long proposedSpendInrPaise,
        string actionType = "tool_invocation",
        string actionParameters = "{}",
        string budgetSkillType = "general",
        string tenantId = "tenant-abc",
        string contractId = "contract-123")
    {
        return new EvaluationContext(
            ContractId: contractId,
            ActionType: actionType,
            ActionParameters: actionParameters,
            DecisionSpaceVersion: 1,
            TenantId: tenantId,
            SkillId: null,
            ApprovedBudgetInrPaise: approvedBudgetInrPaise,
            CurrentSpendInrPaise: currentSpendInrPaise,
            ProposedSpendInrPaise: proposedSpendInrPaise,
            BudgetSkillType: budgetSkillType);
    }

    // ── identity ─────────────────────────────────────────────────────────────

    [Fact]
    // C-073: constitutional obligation — evaluator must identify itself as C-043
    public void ClaimId_IsC043()
    {
        _sut.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public void C043BudgetCeilingEvaluator_ImplementsIClaimEvaluator()
    {
        _sut.Should().BeAssignableTo<IClaimEvaluator>();
    }

    // ── ALLOW scenarios ───────────────────────────────────────────────────────

    [Fact]
    // C-073: allow when proposed spend is well within budget
    public async Task EvaluateAsync_WhenProposedSpendWellWithinBudget_ReturnsAllow()
    {
        // Arrange — approved=10000, current=2000, proposed=3000 → total=5000 ≤ 10000
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 2_000L,
            proposedSpendInrPaise: 3_000L);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    // C-073: allow when proposed spend lands exactly on the ceiling (boundary inclusive)
    public async Task EvaluateAsync_WhenProposedSpendExactlyAtCeiling_ReturnsAllow()
    {
        // Arrange — approved=10000, current=4000, proposed=6000 → total=10000 == approved
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 4_000L,
            proposedSpendInrPaise: 6_000L);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    // C-073: allow when there is no current spend and proposed spend is within budget
    public async Task EvaluateAsync_WhenNoCurrentSpendAndProposedWithinBudget_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 5_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 5_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    // C-073: allow when proposed spend is zero (no-cost action always within any budget)
    public async Task EvaluateAsync_WhenProposedSpendIsZero_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 1_000L,
            currentSpendInrPaise: 1_000L,
            proposedSpendInrPaise: 0L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    // C-073: allow when all budget fields are zero and proposed spend is zero
    public async Task EvaluateAsync_WhenAllBudgetFieldsAreZero_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 0L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 0L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── DENY scenarios ────────────────────────────────────────────────────────

    [Fact]
    // C-073: deny when proposed spend would exceed the budget ceiling by one unit
    public async Task EvaluateAsync_WhenProposedSpendExceedsCeilingByOne_ReturnsDeny()
    {
        // Arrange — approved=10000, current=5000, proposed=5001 → total=10001 > 10000
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 5_000L,
            proposedSpendInrPaise: 5_001L);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    // C-073: deny when current spend alone already exhausted the budget
    public async Task EvaluateAsync_WhenCurrentSpendAlreadyAtCeilingAndProposedNonZero_ReturnsDeny()
    {
        // Arrange — approved=8000, current=8000, proposed=1 → total=8001 > 8000
        var ctx = BuildContext(
            approvedBudgetInrPaise: 8_000L,
            currentSpendInrPaise: 8_000L,
            proposedSpendInrPaise: 1L);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    // C-073: deny when proposed spend alone already exceeds approved budget
    public async Task EvaluateAsync_WhenProposedSpendAloneExceedsBudget_ReturnsDeny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 500L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 501L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    // C-073: deny when budget is zero but proposed spend is positive
    public async Task EvaluateAsync_WhenZeroBudgetAndPositiveProposedSpend_ReturnsDeny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 0L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 1L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    // C-073: deny for large overspend — not just boundary cases
    public async Task EvaluateAsync_WhenProposedSpendMassivelyExceedsBudget_ReturnsDeny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 1_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 1_000_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Theory: parameterised boundary sweep ─────────────────────────────────

    [Theory]
    [InlineData(10_000L, 0L, 9_999L, EvaluationVerdict.Allow)]
    [InlineData(10_000L, 0L, 10_000L, EvaluationVerdict.Allow)]
    [InlineData(10_000L, 0L, 10_001L, EvaluationVerdict.Deny)]
    [InlineData(10_000L, 9_999L, 1L, EvaluationVerdict.Allow)]
    [InlineData(10_000L, 9_999L, 2L, EvaluationVerdict.Deny)]
    [InlineData(10_000L, 10_000L, 0L, EvaluationVerdict.Allow)]
    [InlineData(10_000L, 10_000L, 1L, EvaluationVerdict.Deny)]
    [InlineData(0L, 0L, 0L, EvaluationVerdict.Allow)]
    [InlineData(0L, 0L, 1L, EvaluationVerdict.Deny)]
    // C-073: boundary sweep confirms C-043 ceiling enforcement at every transition point
    public async Task EvaluateAsync_BoundarySweep_ReturnsExpectedVerdict(
        long approved,
        long current,
        long proposed,
        EvaluationVerdict expectedVerdict)
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: approved,
            currentSpendInrPaise: current,
            proposedSpendInrPaise: proposed);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(expectedVerdict,
            because: $"approved={approved}, current={current}, proposed={proposed} → total={current + proposed}");
    }

    // ── result shape ──────────────────────────────────────────────────────────

    [Fact]
    // C-073: every result must carry ClaimId and a non-empty Reason (C-059 traceability)
    public async Task EvaluateAsync_AllowResult_HasCorrectShape()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 1_000L,
            proposedSpendInrPaise: 2_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
        result.Reason.Should().NotBeNullOrWhiteSpace();
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    // C-073: deny result must carry ClaimId and a non-empty Reason (C-059 traceability)
    public async Task EvaluateAsync_DenyResult_HasCorrectShape()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 1_000L,
            currentSpendInrPaise: 999L,
            proposedSpendInrPaise: 2L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
        result.Reason.Should().NotBeNullOrWhiteSpace();
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    // C-073: result must never expose null fields regardless of budget inputs
    public async Task EvaluateAsync_ResultFields_AreNeverNull()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 500L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 1_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Should().NotBeNull();
        result.ClaimId.Should().NotBeNull();
        result.Reason.Should().NotBeNull();
    }

    // ── idempotency ───────────────────────────────────────────────────────────

    [Fact]
    // C-073: same context evaluated twice must return same verdict (determinism)
    public async Task EvaluateAsync_CalledTwiceWithSameContext_ReturnsSameVerdict()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 3_000L,
            proposedSpendInrPaise: 4_000L);

        var first = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        var second = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        second.Verdict.Should().Be(first.Verdict);
        second.ClaimId.Should().Be(first.ClaimId);
    }

    // ── cancellation ──────────────────────────────────────────────────────────

    [Fact]
    // C-073: evaluator must respect cancellation and not hang
    public async Task EvaluateAsync_WhenCancellationRequested_DoesNotHang()
    {
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 100L);

        // Act — should complete (allow fast-path return) or throw OperationCanceledException
        // Either is constitutionally acceptable; it must not block indefinitely.
        Func<Task> act = async () =>
            await _sut.EvaluateAsync(ctx, cts.Token);

        await act.Should().CompleteWithinAsync(TimeSpan.FromSeconds(2));
    }

    // ── action-type independence ──────────────────────────────────────────────

    [Theory]
    [InlineData("tool_invocation")]
    [InlineData("file_write")]
    [InlineData("api_call")]
    [InlineData("email_send")]
    // C-073: budget ceiling applies regardless of action type
    public async Task EvaluateAsync_BudgetBreachDenied_RegardlessOfActionType(string actionType)
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 500L,
            currentSpendInrPaise: 400L,
            proposedSpendInrPaise: 200L,
            actionType: actionType);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: $"action type '{actionType}' does not exempt an action from budget ceiling C-043");
    }

    [Theory]
    [InlineData("tool_invocation")]
    [InlineData("read_only")]
    [InlineData("notification")]
    // C-073: allow is also action-type independent when budget not exceeded
    public async Task EvaluateAsync_BudgetWithinCeiling_AllowedRegardlessOfActionType(string actionType)
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 1_000L,
            proposedSpendInrPaise: 2_000L,
            actionType: actionType);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow,
            because: $"action type '{actionType}' with spend within ceiling must be allowed");
    }

    // ── tenant isolation ──────────────────────────────────────────────────────

    [Fact]
    // C-073: budget evaluation is per-context; different tenants do not bleed state
    public async Task EvaluateAsync_DifferentTenants_EvaluatedIndependently()
    {
        var ctxAllow = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 5_000L,
            tenantId: "tenant-a");

        var ctxDeny = BuildContext(
            approvedBudgetInrPaise: 1_000L,
            currentSpendInrPaise: 999L,
            proposedSpendInrPaise: 5_000L,
            tenantId: "tenant-b");

        var allowResult = await _sut.EvaluateAsync(ctxAllow, CancellationToken.None);
        var denyResult = await _sut.EvaluateAsync(ctxDeny, CancellationToken.None);

        allowResult.Verdict.Should().Be(EvaluationVerdict.Allow);
        denyResult.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── budget skill type ──────────────────────────────────────────────────────

    [Theory]
    [InlineData("general")]
    [InlineData("research")]
    [InlineData("coding")]
    // C-073: budget ceiling enforcement is not limited to a specific skill type
    public async Task EvaluateAsync_BudgetBreachDenied_AcrossSkillTypes(string skillType)
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 1_000L,
            currentSpendInrPaise: 900L,
            proposedSpendInrPaise: 200L,
            budgetSkillType: skillType);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: $"skill type '{skillType}' does not exempt overspend from budget ceiling C-043");
    }
}