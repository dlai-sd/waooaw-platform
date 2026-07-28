// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043 Evaluator — Budget Ceiling
// Constitutional basis: C-043 (Budget Ceiling), C-076 (Test Coverage ≥90%), C-059 (Traceability)
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C043BudgetCeilingEvaluatorTests
{
    private readonly C043BudgetCeilingEvaluator _sut = new();

    private static EvaluationContext BuildContext(
        long approvedBudgetInrPaise = 100_000L,
        long currentSpendInrPaise = 0L,
        long proposedSpendInrPaise = 0L,
        string contractId = "contract-test",
        string tenantId = "tenant-test",
        string actionType = "tool_call",
        string budgetSkillType = "general")
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

    // ── ClaimId ──────────────────────────────────────────────────────────────

    [FactAttribute]
    public void ClaimId_IsC043()
    {
        _sut.ClaimId.Should().Be("C-043");
    }

    // ── Allow paths ───────────────────────────────────────────────────────────

    [FactAttribute]
    public async Task EvaluateAsync_ProposedWellWithinBudget_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   40_000L,
            proposedSpendInrPaise:  10_000L);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_ExactlyAtCeiling_ReturnsAllow()
    {
        // current + proposed == approved  →  still within ceiling
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   80_000L,
            proposedSpendInrPaise:  20_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_ZeroProposedSpend_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   50_000L,
            proposedSpendInrPaise:  0L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_ZeroCurrentSpend_SmallProposed_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   0L,
            proposedSpendInrPaise:  1_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_LargeBudgetLargeRoom_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: long.MaxValue / 2,
            currentSpendInrPaise:   1_000_000L,
            proposedSpendInrPaise:  500_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ── Deny paths ────────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_ProposedExceedsCeiling_ReturnsDeny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   90_000L,
            proposedSpendInrPaise:  20_000L);   // 110 000 > 100 000

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_OneOverCeiling_ReturnsDeny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   90_000L,
            proposedSpendInrPaise:  10_001L);   // 1 paise over

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_ZeroApprovedBudget_AnySpend_ReturnsDeny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 0L,
            currentSpendInrPaise:   0L,
            proposedSpendInrPaise:  1L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_DenyResult_ReasonIsNotNullOrWhiteSpace()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   90_000L,
            proposedSpendInrPaise:  20_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ── Result shape guarantees ───────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_ResultAlwaysHasClaimIdC043_Allow()
    {
        var ctx = BuildContext(approvedBudgetInrPaise: 100_000L, proposedSpendInrPaise: 1_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task EvaluateAsync_ResultAlwaysHasClaimIdC043_Deny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   90_000L,
            proposedSpendInrPaise:  20_000L);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    [Fact]
    public async Task EvaluateAsync_ResultVerdictIsDefinedEnumValue()
    {
        var ctx = BuildContext();

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        Enum.IsDefined(typeof(EvaluationVerdict), result.Verdict).Should().BeTrue();
    }

    [Fact]
    public async Task EvaluateAsync_ReturnedResult_HasNonNullProperties()
    {
        var ctx = BuildContext();

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Should().NotBeNull();
        result.ClaimId.Should().NotBeNull();
        result.Reason.Should().NotBeNull();
    }

    // ── Idempotency ───────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_SameContext_IsIdempotent_Allow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   40_000L,
            proposedSpendInrPaise:  10_000L);

        var r1 = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        r1.Verdict.Should().Be(r2.Verdict);
        r1.ClaimId.Should().Be(r2.ClaimId);
    }

    [Fact]
    public async Task EvaluateAsync_SameContext_IsIdempotent_Deny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   90_000L,
            proposedSpendInrPaise:  20_000L);

        var r1 = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        r1.Verdict.Should().Be(r2.Verdict);
        r1.ClaimId.Should().Be(r2.ClaimId);
    }

    // ── Tenant / contract isolation ───────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_DifferentTenantIds_SameBudgetExceeded_BothDeny()
    {
        var ctx1 = BuildContext(
            tenantId: "tenant-A",
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   90_000L,
            proposedSpendInrPaise:  20_000L);

        var ctx2 = BuildContext(
            tenantId: "tenant-B",
            approvedBudgetInrPaise: 100_000L,
            currentSpendInrPaise:   90_000L,
            proposedSpendInrPaise:  20_000L);

        var r1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        r1.Verdict.Should().Be(EvaluationVerdict.Deny);
        r2.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_DifferentContractIds_SameBudgetExceeded_BothDeny()
    {
        var ctx1 = BuildContext(
            contractId: "contract-X",
            approvedBudgetInrPaise: 50_000L,
            currentSpendInrPaise:   40_000L,
            proposedSpendInrPaise:  20_000L);

        var ctx2 = BuildContext(
            contractId: "contract-Y",
            approvedBudgetInrPaise: 50_000L,
            currentSpendInrPaise:   40_000L,
            proposedSpendInrPaise:  20_000L);

        var r1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        r1.Verdict.Should().Be(EvaluationVerdict.Deny);
        r2.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Cancellation ──────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_CancelledToken_DoesNotHang()
    {
        var ctx = BuildContext();
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        // Should complete (not throw or hang) — evaluator is synchronous internally
        var result = await _sut.EvaluateAsync(ctx, cts.Token);

        result.Should().NotBeNull();
    }

    // ── BudgetSkillType coverage ──────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_NonDefaultBudgetSkillType_WithinBudget_ReturnsAllow()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 200_000L,
            currentSpendInrPaise:   50_000L,
            proposedSpendInrPaise:  30_000L,
            budgetSkillType:        "premium");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task EvaluateAsync_NonDefaultBudgetSkillType_OverBudget_ReturnsDeny()
    {
        var ctx = BuildContext(
            approvedBudgetInrPaise: 10_000L,
            currentSpendInrPaise:   8_000L,
            proposedSpendInrPaise:  5_000L,
            budgetSkillType:        "premium");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }
}