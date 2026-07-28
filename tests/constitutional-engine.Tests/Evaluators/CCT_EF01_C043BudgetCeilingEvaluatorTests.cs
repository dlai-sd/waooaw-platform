// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-041 (Tool Authorization), C-076 (Test Coverage)
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// Constitutional Compliance Tests — CCT-EF-01
/// Verifies C043BudgetCeilingEvaluator enforces the budget ceiling constitutional floor (C-043).
/// A proposed spend that would cause current + proposed to exceed the approved monthly ceiling
/// MUST return Deny with reason BUDGET_CEILING_REACHED.
/// </summary>
public class CCT_EF01_C043BudgetCeilingEvaluatorTests
{
    // ── factory ──────────────────────────────────────────────────────────────

    private static C043BudgetCeilingEvaluator CreateEvaluator()
        => new C043BudgetCeilingEvaluator(NullLogger<C043BudgetCeilingEvaluator>.Instance);

    /// <summary>
    /// Builds an EvaluationContext for budget tests.
    /// All positional — matches the frozen EvaluationContext record constructor order:
    ///   ContractId, ActionType, ActionParameters, DecisionSpaceVersion,
    ///   TenantId, SkillId, ApprovedBudgetInrPaise, CurrentSpendInrPaise,
    ///   ProposedSpendInrPaise, BudgetSkillType
    /// </summary>
    private static EvaluationContext BuildBudgetContext(
        long approvedPaise,
        long currentPaise,
        long proposedPaise,
        string skillType = "MARKETING")
        => new EvaluationContext(
            "test-contract-budget",
            "SPEND_ACTION",
            "{}",
            1,
            "tenant-budget-001",
            null,
            approvedPaise,
            currentPaise,
            proposedPaise,
            skillType);

    // ── Allow scenarios ───────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_UnderBudget_ReturnsAllow()
    {
        // Arrange: approved=10 000, current=2 000, proposed=3 000  → total 5 000 < 10 000
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 2_000L, 3_000L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_UnderBudget_ClaimId_IsC043()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 2_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task EvaluateAsync_ExactlyAtBudget_ReturnsAllow()
    {
        // Arrange: approved=10 000, current=7 000, proposed=3 000 → total == approved (boundary inclusive)
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 7_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_ExactlyAtBudget_ClaimId_IsC043()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 7_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task EvaluateAsync_ZeroProposedSpend_ReturnsAllow()
    {
        // Arrange: proposed spend = 0 — should always Allow
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 9_500L, 0L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_ZeroCurrentSpend_UnderBudget_ReturnsAllow()
    {
        // Arrange: first spend of the month — current=0, proposed=1
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 0L, 1L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_LargeAllowedBudget_ReturnsAllow()
    {
        // Arrange: large values well within budget
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(1_000_000_000L, 100_000L, 50_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_UnderBudget_ReasonIsNotNull()
    {
        // Reason must always be populated (never null) — C-059 audit requirement
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 2_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNull();
    }

    // ── Deny scenarios ────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_OverBudget_ReturnsDeny()
    {
        // Arrange: approved=10 000, current=8 000, proposed=3 000 → total 11 000 > 10 000
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 8_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_OverBudget_ClaimId_IsC043()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 8_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task EvaluateAsync_OverBudget_Reason_ContainsBudgetCeilingReached()
    {
        // C-043: the deny reason must carry the canonical reason code
        // so callers and audit records can identify the exact constitutional violation.
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 8_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().Contain("BUDGET_CEILING_REACHED");
    }

    [Fact]
    public async Task EvaluateAsync_OverBudget_ReasonIsNotNull()
    {
        // Reason must always be populated on Deny as well — C-059 audit requirement
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 8_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_OnePaiseOverBudget_ReturnsDeny()
    {
        // Arrange: approved=10 000, current=9 999, proposed=2 → total 10 001 > 10 000
        // Off-by-one: the evaluator must not allow even one paise over the ceiling.
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 9_999L, 2L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_OnePaiseOverBudget_ClaimId_IsC043()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 9_999L, 2L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task EvaluateAsync_ZeroApprovedBudget_AnyProposedSpend_ReturnsDeny()
    {
        // Arrange: approved=0 means no budget has been configured — all spend is rejected
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(0L, 0L, 1L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_ZeroApprovedBudget_ZeroProposedSpend_ReturnsAllow()
    {
        // Arrange: approved=0, proposed=0 — zero spend on zero budget is still within ceiling
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(0L, 0L, 0L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_FullyExhaustedBudget_AnyProposedSpend_ReturnsDeny()
    {
        // Arrange: approved=10 000, current=10 000 (already exhausted), proposed=1
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 10_000L, 1L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_FullyExhaustedBudget_Reason_ContainsBudgetCeilingReached()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 10_000L, 1L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().Contain("BUDGET_CEILING_REACHED");
    }

    [Fact]
    public async Task EvaluateAsync_DifferentSkillType_Trading_OverBudget_ReturnsDeny()
    {
        // Arrange: skill type TRADING — budget ceiling is skill-agnostic in C-043
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(50_000L, 40_000L, 15_000L, "TRADING");

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_DifferentSkillType_Trading_UnderBudget_ReturnsAllow()
    {
        // Arrange: skill type TRADING within budget
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(50_000L, 10_000L, 15_000L, "TRADING");

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_DifferentSkillType_AgriAdvisory_UnderBudget_ReturnsAllow()
    {
        // Arrange: skill type AGRI_ADVISORY — evaluator must work for all skill types
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(20_000L, 5_000L, 3_000L, "AGRI_ADVISORY");

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_MaxLongApprovedBudget_LargeProposedSpend_ReturnsAllow()
    {
        // Arrange: approved = long.MaxValue / 2, total well under ceiling — no overflow
        var halfMax = long.MaxValue / 2;
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(halfMax, 1_000_000L, 1_000_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_OverBudget_ResultIsEvaluationResult()
    {
        // Structural: EvaluateAsync must always return a non-null EvaluationResult
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 9_000L, 5_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Should().NotBeNull();
    }

    [Fact]
    public async Task EvaluateAsync_UnderBudget_ResultIsEvaluationResult()
    {
        // Structural: EvaluateAsync must always return a non-null EvaluationResult
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 1_000L, 2_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Should().NotBeNull();
    }

    [Fact]
    public async Task EvaluateAsync_OverBudget_VerdictIsNotAllow()
    {
        // Belt-and-suspenders: when over budget, verdict must never be Allow
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 8_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().NotBe(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_UnderBudget_VerdictIsNotDeny()
    {
        // Belt-and-suspenders: when under budget, verdict must never be Deny
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 2_000L, 3_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().NotBe(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_CancellationTokenNone_DoesNotThrow()
    {
        // EvaluateAsync must be safe to call with CancellationToken.None
        var evaluator = CreateEvaluator();
        var ctx = BuildBudgetContext(10_000L, 2_000L, 3_000L);

        var act = async () => await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        await act.Should().NotThrowAsync();
    }
}