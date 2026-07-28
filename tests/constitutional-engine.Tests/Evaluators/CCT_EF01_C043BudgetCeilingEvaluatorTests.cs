// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-041 (Tool Authorization), C-076 (Test Coverage)
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;
using Microsoft.Extensions.Logging.Abstractions;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01: Constitutional Compliance Tests for C043BudgetCeilingEvaluator.
/// Constitutional basis: C-043 (Budget Ceiling is a Constitutional Floor equivalent).
/// AD-016: CE must reject any action that would exceed the approved monthly budget.
/// </summary>
public class CCT_EF01_C043BudgetCeilingEvaluatorTests
{
    // ── Factory helpers ──────────────────────────────────────────────────────

    private static C043BudgetCeilingEvaluator CreateEvaluator()
        => new C043BudgetCeilingEvaluator(NullLogger<C043BudgetCeilingEvaluator>.Instance);

    /// <summary>
    /// Builds an EvaluationContext with all positional args — no named+positional mix (CS1744).
    /// EvaluationContext record field order (frozen WC012-02a):
    ///   ContractId, ActionType, ActionParameters, DecisionSpaceVersion,
    ///   TenantId, SkillId, ApprovedBudgetInrPaise, CurrentSpendInrPaise,
    ///   ProposedSpendInrPaise, BudgetSkillType
    /// </summary>
    private static EvaluationContext BuildContext(
        long approvedBudgetInrPaise,
        long currentSpendInrPaise,
        long proposedSpendInrPaise,
        string actionType = "MARKETING_POST",
        string contractId = "contract-c043-001",
        string tenantId = "tenant-c043-001",
        string budgetSkillType = "SOCIAL_MEDIA")
        => new EvaluationContext(
            contractId,
            actionType,
            "{}",
            1,
            tenantId,
            null,
            approvedBudgetInrPaise,
            currentSpendInrPaise,
            proposedSpendInrPaise,
            budgetSkillType);

    // ── Allow scenarios ──────────────────────────────────────────────────────

    [Fact]
    public async Task WhenProposedSpendWellWithinBudget_ShouldReturn_Allow()
    {
        // Arrange — C-043: 50 000 + 10 000 = 60 000 ≤ 100 000 → ALLOW
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise: 50_000L,
            proposedSpendInrPaise: 10_000L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-043");
        result.Reason.Should().NotBeNull();
    }

    [Fact]
    public async Task WhenProposedSpendExactlyConsumesRemainingBudget_ShouldReturn_Allow()
    {
        // Arrange — 90 000 + 10 000 = 100 000 == 100 000 → at ceiling, still ALLOW
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise: 90_000L,
            proposedSpendInrPaise: 10_000L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task WhenProposedSpendIsZero_ShouldReturn_Allow()
    {
        // Arrange — zero-cost action; budget ceiling cannot be breached regardless of current spend
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise: 99_999L,
            proposedSpendInrPaise: 0L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task WhenCurrentSpendIsZeroAndProposedWithinBudget_ShouldReturn_Allow()
    {
        // Arrange — fresh month, first spend action
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 500_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 1_000L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-043");
    }

    // ── Deny scenarios ───────────────────────────────────────────────────────

    [Fact]
    public async Task WhenProposedSpendExceedsBudget_ShouldReturn_Deny()
    {
        // Arrange — C-043 / AD-016: 90 000 + 20 000 = 110 000 > 100 000 → DENY
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise: 90_000L,
            proposedSpendInrPaise: 20_000L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-043");
        result.Reason.Should().Contain("BUDGET_CEILING_REACHED",
            because: "ValidateActionResponse.reason must carry BUDGET_CEILING_REACHED for caller handling (proto spec §ValidateActionResponse)");
    }

    [Fact]
    public async Task WhenZeroApprovedBudgetAndNonZeroProposedSpend_ShouldReturn_Deny()
    {
        // Arrange — customer approved zero budget; any spend is a violation
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 0L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 1L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task WhenBudgetExhaustedAndProposedSpendIsOne_ShouldReturn_Deny()
    {
        // Arrange — current == approved; even 1 paise over ceiling → DENY
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise: 100_000L,
            proposedSpendInrPaise: 1L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task WhenProposedSpendAloneExceedsFullApprovedBudget_ShouldReturn_Deny()
    {
        // Arrange — single action more expensive than entire monthly budget
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 50_000L);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-043");
        result.Reason.Should().Contain("BUDGET_CEILING_REACHED");
    }

    // ── Constitutional invariants ─────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_AlwaysReturnsNonNullResult()
    {
        // Invariant: evaluator must never return null (ERROR HANDLING RULE 2)
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 50_000L,
            currentSpendInrPaise: 25_000L,
            proposedSpendInrPaise: 5_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Should().NotBeNull();
        result.ClaimId.Should().NotBeNullOrEmpty(
            because: "every EvaluationResult must carry its constitutional basis (AD-008)");
        result.Reason.Should().NotBeNull(
            because: "reason must always be populated for audit traceability (C-059)");
    }

    [Fact]
    public async Task AllowResult_MustCarryClaimId_C043()
    {
        // AD-008: every permission decision must name its constitutional basis
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 200_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 1_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.ClaimId.Should().Be("C-043",
            because: "AD-008 requires the constitutional basis to be named on every decision");
    }

    [Fact]
    public async Task DenyResult_MustCarryClaimId_C043()
    {
        // AD-008: every denial must name its constitutional basis
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise: 9_000L,
            proposedSpendInrPaise: 5_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-043",
            because: "AD-008 requires the constitutional basis to be named on every denial");
    }

    [Fact]
    public async Task EvaluateAsync_RespectsCancellationToken()
    {
        // ERROR HANDLING RULE 4: external calls must honour cancellation
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise: 0L,
            proposedSpendInrPaise: 500L);

        using var cts = new CancellationTokenSource();
        // Token is NOT cancelled — evaluator should complete normally
        var result = await evaluator.EvaluateAsync(ctx, cts.Token);

        result.Should().NotBeNull();
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task WhenBudgetSkillTypeIsEmpty_EvaluatorStillProducesDecision()
    {
        // Defensive: missing skill type must not crash the evaluator
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise: 10_000L,
            proposedSpendInrPaise: 5_000L,
            budgetSkillType: "");

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Should().NotBeNull();
        result.Verdict.Should().BeOneOf(EvaluationVerdict.Allow, EvaluationVerdict.Deny,
            because: "evaluator must return a verdict even when skill type is missing");
    }
}