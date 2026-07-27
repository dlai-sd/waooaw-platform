// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// constitutional_basis: C-043 (Budget Ceiling), C-076 (test coverage), C-082 (build validation)
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C043BudgetCeilingEvaluatorTests
{
    private readonly C043BudgetCeilingEvaluator _sut = new();

    // ── helpers ──────────────────────────────────────────────────────────────

    private static EvaluationContext MakeContext(
        long approvedBudgetInrPaise,
        long currentSpendInrPaise,
        long proposedSpendInrPaise,
        string budgetSkillType = "GENERIC",
        string tenantId = "tenant-001",
        string contractId = "contract-abc",
        string actionType = "SPEND_REQUEST")
        => new(
            ContractId: contractId,
            ActionType: actionType,
            ActionParameters: "{}",
            DecisionSpaceVersion: 1,
            TenantId: tenantId,
            SkillId: null,
            ApprovedBudgetInrPaise: approvedBudgetInrPaise,
            CurrentSpendInrPaise: currentSpendInrPaise,
            ProposedSpendInrPaise: proposedSpendInrPaise,
            BudgetSkillType: budgetSkillType);

    // ── Allow scenarios ───────────────────────────────────────────────────────

    [Fact]
    public async Task WellWithinBudget_ShouldAllow()
    {
        // proposed(500) + current(1_000) = 1_500 — well below approved 10_000
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 1_000,
            proposedSpendInrPaise: 500);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task ZeroProposedSpend_WellUnderBudget_ShouldAllow()
    {
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 3_000,
            proposedSpendInrPaise: 0);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task ZeroSpend_ZeroBudgetUsed_ShouldAllow()
    {
        var ctx = MakeContext(
            approvedBudgetInrPaise: 50_000,
            currentSpendInrPaise: 0,
            proposedSpendInrPaise: 0);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task SmallProposedSpend_LargeApprovedBudget_ShouldAllow()
    {
        var ctx = MakeContext(
            approvedBudgetInrPaise: 1_000_000,
            currentSpendInrPaise: 100_000,
            proposedSpendInrPaise: 50_000);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Deny scenarios ────────────────────────────────────────────────────────

    [Fact]
    public async Task ProposedExceedsApprovedBudget_ShouldDeny()
    {
        // proposed(5_000) + current(6_000) = 11_000 > approved 10_000
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 6_000,
            proposedSpendInrPaise: 5_000);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task ProposedAloneExceedsBudget_ShouldDeny()
    {
        // proposed(20_000) + current(0) = 20_000 > approved 10_000
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 0,
            proposedSpendInrPaise: 20_000);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task CurrentSpendAlreadyExceedsBudget_ShouldDeny()
    {
        // current(10_001) already over approved(10_000), adding any proposed
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 10_001,
            proposedSpendInrPaise: 0);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task ExactlyOnePaiseOverBudget_ShouldDeny()
    {
        // total = approved + 1 paise
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 9_999,
            proposedSpendInrPaise: 2);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task MassiveOverspend_ShouldDeny()
    {
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 9_000,
            proposedSpendInrPaise: 100_000);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Escalate scenarios ────────────────────────────────────────────────────

    [Fact]
    public async Task SpendNearCeiling_ShouldEscalateOrDeny()
    {
        // proposed(400) + current(9_500) = 9_900 — 99% of approved(10_000)
        // Evaluator should Escalate (near ceiling) or Deny — must NOT Allow
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 9_500,
            proposedSpendInrPaise: 400);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().BeOneOf(EvaluationVerdict.Escalate, EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task SpendAt95PercentOfBudget_ShouldNotAllow()
    {
        // total 9_500 / 10_000 = 95% → near ceiling, must escalate or deny
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 9_000,
            proposedSpendInrPaise: 500);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().NotBe(EvaluationVerdict.Allow);
    }

    // ── Contract invariants ───────────────────────────────────────────────────

    [Theory]
    [InlineData(10_000, 1_000, 500)]      // allow region
    [InlineData(10_000, 6_000, 5_000)]    // deny region
    [InlineData(10_000, 9_000, 500)]      // near-ceiling region
    public async Task EvaluateAsync_AlwaysReturnsClaimIdC043(
        long approved, long current, long proposed)
    {
        var ctx = MakeContext(approved, current, proposed);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    [Theory]
    [InlineData(10_000, 1_000, 500)]
    [InlineData(10_000, 6_000, 5_000)]
    [InlineData(10_000, 9_000, 500)]
    public async Task EvaluateAsync_AlwaysPopulatesReason(
        long approved, long current, long proposed)
    {
        var ctx = MakeContext(approved, current, proposed);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_CompletesWithoutCancellation()
    {
        var ctx = MakeContext(10_000, 1_000, 500);
        using var cts = new CancellationTokenSource();

        var act = async () => await _sut.EvaluateAsync(ctx, cts.Token);

        await act.Should().NotThrowAsync();
    }

    // ── Tenant / contract isolation ───────────────────────────────────────────

    [Fact]
    public async Task DeniedBudget_IsSameAcrossDifferentTenants()
    {
        var ctx1 = MakeContext(10_000, 9_000, 2_000, tenantId: "tenant-A");
        var ctx2 = MakeContext(10_000, 9_000, 2_000, tenantId: "tenant-B");

        var r1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        r1.Verdict.Should().Be(EvaluationVerdict.Deny);
        r2.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task AllowedBudget_IsSameAcrossDifferentTenants()
    {
        var ctx1 = MakeContext(10_000, 1_000, 500, tenantId: "tenant-A");
        var ctx2 = MakeContext(10_000, 1_000, 500, tenantId: "tenant-B");

        var r1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        r1.Verdict.Should().Be(EvaluationVerdict.Allow);
        r2.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Skill-type isolation ──────────────────────────────────────────────────

    [Fact]
    public async Task DifferentBudgetSkillTypes_BothDeniedWhenOverBudget()
    {
        var ctxA = MakeContext(10_000, 9_000, 2_000, budgetSkillType: "WRITING");
        var ctxB = MakeContext(10_000, 9_000, 2_000, budgetSkillType: "CODING");

        var rA = await _sut.EvaluateAsync(ctxA, CancellationToken.None);
        var rB = await _sut.EvaluateAsync(ctxB, CancellationToken.None);

        rA.Verdict.Should().Be(EvaluationVerdict.Deny);
        rB.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Edge: exact ceiling ───────────────────────────────────────────────────

    [Fact]
    public async Task TotalSpendExactlyEqualToApprovedBudget_ShouldNotAllow()
    {
        // proposed(1_000) + current(9_000) == approved(10_000) exactly at ceiling
        // must Deny or Escalate — never Allow a spend that maxes out the budget
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 9_000,
            proposedSpendInrPaise: 1_000);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().NotBe(EvaluationVerdict.Allow);
    }

    // ── Non-spend action types still evaluated ────────────────────────────────

    [Fact]
    public async Task NonSpendActionType_WellWithinBudget_ShouldAllow()
    {
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 500,
            proposedSpendInrPaise: 100,
            actionType: "MCP_TOOL_CALL");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task NonSpendActionType_OverBudget_ShouldDeny()
    {
        var ctx = MakeContext(
            approvedBudgetInrPaise: 10_000,
            currentSpendInrPaise: 9_000,
            proposedSpendInrPaise: 2_000,
            actionType: "MCP_TOOL_CALL");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}