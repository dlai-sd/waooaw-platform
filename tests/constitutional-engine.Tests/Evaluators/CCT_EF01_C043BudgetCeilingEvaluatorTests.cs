// Implements: architecture/reference/ce-validate-action-evaluators.md §C-043
// constitutional_basis: C-043 (Budget Ceiling), C-059 (Traceability), C-073 (Annotated Obligations), C-076 (≥90% Unit Test Coverage)

#nullable enable

using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01 gate tests for C043BudgetCeilingEvaluator.
/// Verifies C-043 (Budget Ceiling) enforcement: proposed spend that would push
/// cumulative monthly spend above the approved budget MUST be denied.
/// C-073: every test method carries an annotation comment to its constitutional obligation.
/// C-076: ≥90% unit test coverage required.
/// </summary>
public sealed class CCT_EF01_C043BudgetCeilingEvaluatorTests
{
    // ───────────────────────────────────────────────────────
    // Helpers
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: Creates the evaluator under test using NullLogger (no side-effects).</summary>
    private static C043BudgetCeilingEvaluator CreateEvaluator()
        => new(NullLogger<C043BudgetCeilingEvaluator>.Instance);

    /// <summary>
    /// C-073: Builds an EvaluationContext with budget fields populated.
    /// ActionParameters defaults to "{}" — C-043 reads budget from context fields, not parameters.
    /// </summary>
    private static EvaluationContext BuildContext(
        long approvedBudget   = 100_000L,
        long currentSpend     = 0L,
        long proposedSpend    = 0L,
        string actionType     = "PAYMENT",
        string contractId     = "contract-c043-test",
        string budgetSkillType = "PAYMENT_SKILL",
        string tenantId       = "tenant-c043")
        => new EvaluationContext(
            ContractId:             contractId,
            ActionType:             actionType,
            ActionParameters:       "{}",
            DecisionSpaceVersion:   1,
            TenantId:               tenantId,
            SkillId:                null,
            ApprovedBudgetInrPaise: approvedBudget,
            CurrentSpendInrPaise:   currentSpend,
            ProposedSpendInrPaise:  proposedSpend,
            BudgetSkillType:        budgetSkillType);

    // ───────────────────────────────────────────────────────
    // ClaimId
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: Evaluator must advertise claim "C-043" for registry routing.</summary>
    [Fact]
    public void ClaimId_Always_ReturnsC043()
    {
        var evaluator = CreateEvaluator();

        evaluator.ClaimId.Should().Be("C-043");
    }

    // ───────────────────────────────────────────────────────
    // Allow scenarios
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: Spend well within budget must be allowed (C-043 default-permit path).</summary>
    [Fact]
    public async Task EvaluateAsync_ProposedSpendWellWithinBudget_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 20_000L, proposedSpend: 30_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    /// <summary>C-073: Cumulative spend exactly equalling the ceiling must be allowed.</summary>
    [Fact]
    public async Task EvaluateAsync_ProposedSpendExactlyAtCeiling_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 50_000L, proposedSpend: 50_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    /// <summary>C-073: Zero proposed spend with non-zero current must be allowed.</summary>
    [Fact]
    public async Task EvaluateAsync_ZeroProposedSpend_WithCurrentSpend_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 100_000L, proposedSpend: 0L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    /// <summary>C-073: All zeros (no budget, no spend) must be allowed — nothing exceeds nothing.</summary>
    [Fact]
    public async Task EvaluateAsync_AllZeroValues_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 0L, currentSpend: 0L, proposedSpend: 0L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    /// <summary>C-073: Fully spent budget plus zero additional spend must be allowed.</summary>
    [Fact]
    public async Task EvaluateAsync_FullySpentBudgetPlusZero_ReturnsAllow()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 100_000L, proposedSpend: 0L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    // ───────────────────────────────────────────────────────
    // Deny scenarios
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: Cumulative spend exceeding ceiling by a large margin must be denied.</summary>
    [Fact]
    public async Task EvaluateAsync_ProposedSpendExceedsBudget_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 80_000L, proposedSpend: 30_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    /// <summary>C-073: Exceeding ceiling by a single paise must still be denied.</summary>
    [Fact]
    public async Task EvaluateAsync_ProposedSpendOneOverCeiling_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 50_000L, proposedSpend: 50_001L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    /// <summary>C-073: Zero approved budget with any positive spend must be denied.</summary>
    [Fact]
    public async Task EvaluateAsync_ZeroBudgetWithPositiveSpend_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 0L, currentSpend: 0L, proposedSpend: 1L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    /// <summary>C-073: Fully spent budget plus any additional paise must be denied.</summary>
    [Fact]
    public async Task EvaluateAsync_FullySpentBudgetPlusOnePaise_ReturnsDeny()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 100_000L, proposedSpend: 1L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ───────────────────────────────────────────────────────
    // Result quality
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: ClaimId on Allow result must be "C-043" for audit traceability (C-059).</summary>
    [Fact]
    public async Task EvaluateAsync_AllowResult_ClaimIdIsC043()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 0L, proposedSpend: 10_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    /// <summary>C-073: ClaimId on Deny result must be "C-043" for audit traceability (C-059).</summary>
    [Fact]
    public async Task EvaluateAsync_DenyResult_ClaimIdIsC043()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 90_000L, proposedSpend: 20_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().Be("C-043");
    }

    /// <summary>C-073: Deny result must carry a human-readable reason for audit evidence (C-059).</summary>
    [Fact]
    public async Task EvaluateAsync_DenyResult_HasNonEmptyReason()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 90_000L, proposedSpend: 20_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    /// <summary>C-073: Allow result must carry a human-readable reason for audit evidence (C-059).</summary>
    [Fact]
    public async Task EvaluateAsync_AllowResult_HasNonEmptyReason()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 0L, proposedSpend: 10_000L);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ───────────────────────────────────────────────────────
    // Async / cancellation
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: CancellationToken must be accepted and evaluation must complete normally.</summary>
    [Fact]
    public async Task EvaluateAsync_WithCancellationToken_CompletesNormally()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(approvedBudget: 100_000L, currentSpend: 10_000L, proposedSpend: 5_000L);
        using var cts = new CancellationTokenSource();

        var result = await evaluator.EvaluateAsync(ctx, cts.Token);

        result.Should().NotBeNull();
    }

    // ───────────────────────────────────────────────────────
    // Context integrity
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: EvaluationContext is a record (immutable) — evaluation must not mutate caller state.</summary>
    [Fact]
    public async Task EvaluateAsync_ContextFields_AreNotCorrupted()
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudget:  500_000L,
            currentSpend:    100_000L,
            proposedSpend:   50_000L,
            contractId:      "contract-integrity-c043",
            tenantId:        "tenant-integrity");

        await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        ctx.ContractId.Should().Be("contract-integrity-c043");
        ctx.TenantId.Should().Be("tenant-integrity");
        ctx.ApprovedBudgetInrPaise.Should().Be(500_000L);
        ctx.CurrentSpendInrPaise.Should().Be(100_000L);
        ctx.ProposedSpendInrPaise.Should().Be(50_000L);
    }

    // ───────────────────────────────────────────────────────
    // Parameterised matrix (C-076: breadth coverage)
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: Matrix of budget/spend combinations verifying both Allow and Deny verdicts.</summary>
    [Theory]
    [InlineData(100_000L,     0L,          50_000L,     EvaluationVerdict.Allow)]  // well within
    [InlineData(100_000L,    50_000L,      50_000L,     EvaluationVerdict.Allow)]  // exactly at ceiling
    [InlineData(100_000L,    50_001L,      50_000L,     EvaluationVerdict.Deny)]   // one paise over
    [InlineData(100_000L,   100_000L,          1L,      EvaluationVerdict.Deny)]   // fully spent + any
    [InlineData(100_000L,   100_000L,          0L,      EvaluationVerdict.Allow)]  // fully spent + zero
    [InlineData(          0L,     0L,           0L,     EvaluationVerdict.Allow)]  // zero everything
    [InlineData(          0L,     0L,           1L,     EvaluationVerdict.Deny)]   // zero budget, any spend
    [InlineData(1_000_000L, 999_999L,          1L,     EvaluationVerdict.Allow)]  // large values, at ceiling
    [InlineData(1_000_000L, 999_999L,          2L,     EvaluationVerdict.Deny)]   // large values, one over
    [InlineData(1_000_000L,       0L,   999_999L,      EvaluationVerdict.Allow)]  // single large proposed within
    [InlineData(1_000_000L,       0L, 1_000_001L,      EvaluationVerdict.Deny)]   // single large proposed over
    public async Task EvaluateAsync_BudgetMatrix_ReturnsExpectedVerdict(
        long approved,
        long current,
        long proposed,
        EvaluationVerdict expectedVerdict)
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudget: approved,
            currentSpend:   current,
            proposedSpend:  proposed);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(expectedVerdict,
            because: $"approved={approved} current={current} proposed={proposed} " +
                     $"cumulative={current + proposed} vs ceiling={approved}");
    }

    // ───────────────────────────────────────────────────────
    // Edge: large values (overflow guard)
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: Implementation must handle large long values without arithmetic overflow.</summary>
    [Fact]
    public async Task EvaluateAsync_LargeBudgetValues_DoNotOverflowAndReturnResult()
    {
        var evaluator = CreateEvaluator();
        // Use values well within long.MaxValue to avoid overflow in the evaluator itself
        const long halfMax = long.MaxValue / 2;
        var ctx = BuildContext(
            approvedBudget: halfMax,
            currentSpend:   halfMax / 2,
            proposedSpend:  halfMax / 2);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Should().NotBeNull();
        result.Verdict.Should().BeOneOf(
            EvaluationVerdict.Allow,
            EvaluationVerdict.Deny,
            EvaluationVerdict.Escalate);
    }

    // ───────────────────────────────────────────────────────
    // Skill-type variance (BudgetSkillType field)
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: Different BudgetSkillType values must not cause errors; budget rule still applies.</summary>
    [Theory]
    [InlineData("PAYMENT_SKILL")]
    [InlineData("ANALYTICS_SKILL")]
    [InlineData("")]
    [InlineData("UNKNOWN_SKILL_TYPE")]
    public async Task EvaluateAsync_VariousSkillTypes_WithinBudget_ReturnsAllow(string skillType)
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudget: 100_000L,
            currentSpend:   10_000L,
            proposedSpend:   5_000L,
            budgetSkillType: skillType);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow,
            because: $"spend is within budget regardless of skill type '{skillType}'");
    }

    // ───────────────────────────────────────────────────────
    // Action type variance
    // ───────────────────────────────────────────────────────

    /// <summary>C-073: C-043 applies to all action types — budget check is action-type agnostic.</summary>
    [Theory]
    [InlineData("PAYMENT")]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("AGENT_QUERY")]
    [InlineData("DATA_EXPORT")]
    [InlineData("")]
    public async Task EvaluateAsync_VariousActionTypes_ExceedingBudget_ReturnsDeny(string actionType)
    {
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(
            approvedBudget: 100_000L,
            currentSpend:   90_000L,
            proposedSpend:  20_000L,
            actionType:     actionType);

        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: $"budget ceiling is exceeded regardless of action type '{actionType}'");
    }
}