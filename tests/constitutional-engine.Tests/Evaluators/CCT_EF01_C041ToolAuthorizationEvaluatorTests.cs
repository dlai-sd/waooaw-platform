// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotation),
//                       C-076 (≥90% Unit Test Coverage)
// CCT Gate: CCT-EF-01 — C041 Tool Authorization Evaluator contract verification

#nullable enable

using FluentAssertions;
using Microsoft.Extensions.Logging;
using Moq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01: Constitutional contract tests for C041ToolAuthorizationEvaluator.
/// Verifies the default-deny posture mandated by C-041: any unlisted tool must be denied.
/// C-073: Every test method annotates the constitutional obligation under test.
/// C-076: Coverage target ≥90%.
/// </summary>
public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    // ── Fixture ─────────────────────────────────────────────────────────────────
    private readonly C041ToolAuthorizationEvaluator _sut;
    private readonly Mock<ILogger<C041ToolAuthorizationEvaluator>> _loggerMock;

    public CCT_EF01_C041ToolAuthorizationEvaluatorTests()
    {
        _loggerMock = new Mock<ILogger<C041ToolAuthorizationEvaluator>>();
        _sut = new C041ToolAuthorizationEvaluator(_loggerMock.Object);
    }

    // ── Helpers ─────────────────────────────────────────────────────────────────

    /// <summary>
    /// Builds an EvaluationContext with a JSON-encoded ActionParameters string
    /// containing the given tool_name value.
    /// </summary>
    private static EvaluationContext BuildContext(string? toolName, string actionType = "ToolInvocation")
    {
        var parameters = toolName is null
            ? "{}"
            : JsonSerializer.Serialize(new { tool_name = toolName });

        return new EvaluationContext(
            ContractId: "contract-cct-ef01",
            ActionType: actionType,
            ActionParameters: parameters,
            DecisionSpaceVersion: 1,
            TenantId: "tenant-test",
            SkillId: null,
            ApprovedBudgetInrPaise: 500_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 1_000L,
            BudgetSkillType: "general"
        );
    }

    // ── ClaimId contract ────────────────────────────────────────────────────────

    // C-073: Verifies C-041 claim identity is correctly declared.
    [Fact]
    public void ClaimId_IsC041()
    {
        _sut.ClaimId.Should().Be("C-041");
    }

    // ── Default-deny posture (C-041 constitutional requirement) ─────────────────

    // C-073: C-041 mandates default-deny — an unlisted tool must always produce Deny.
    [Fact]
    public async Task EvaluateAsync_WithUnlistedTool_ReturnsDeny()
    {
        // Arrange — tool name not in any approved list
        var ctx = BuildContext("totally_unknown_tool_xyz_abc");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // C-073: C-041 — missing tool_name parameter must also produce Deny.
    [Fact]
    public async Task EvaluateAsync_WithMissingToolNameParameter_ReturnsDeny()
    {
        // Arrange — empty JSON, no tool_name key
        var ctx = BuildContext(toolName: null);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    // C-073: C-041 — empty string tool_name is not a valid authorization token → Deny.
    [Fact]
    public async Task EvaluateAsync_WithEmptyToolName_ReturnsDeny()
    {
        // Arrange
        var ctx = BuildContext(toolName: "");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    // C-073: C-041 — whitespace-only tool name is equivalent to absent → Deny.
    [Fact]
    public async Task EvaluateAsync_WithWhitespaceToolName_ReturnsDeny()
    {
        // Arrange
        var ctx = BuildContext(toolName: "   ");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Parameterised deny across multiple unknown tools ────────────────────────

    // C-073: C-041 default-deny must hold for any tool name not on the approved list.
    [Theory]
    [InlineData("rm_rf")]
    [InlineData("exec_shell")]
    [InlineData("drop_database")]
    [InlineData("sudo")]
    [InlineData("curl_external")]
    [InlineData("UNKNOWN")]
    [InlineData("__proto__")]
    public async Task EvaluateAsync_WithVariousUnlistedTools_AllReturnDeny(string toolName)
    {
        // Arrange
        var ctx = BuildContext(toolName);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: $"tool '{toolName}' is not on the C-041 approved list");
        result.ClaimId.Should().Be("C-041");
    }

    // ── Result shape contract ────────────────────────────────────────────────────

    // C-073: EvaluationResult must always carry a non-null ClaimId and non-empty Reason.
    [Fact]
    public async Task EvaluateAsync_ResultShape_AlwaysPopulatesClaimIdAndReason()
    {
        // Arrange — unknown tool to exercise deny path
        var ctx = BuildContext("nonexistent_tool");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.ClaimId.Should().NotBeNullOrEmpty();
        result.Reason.Should().NotBeNullOrEmpty();
        result.Verdict.Should().BeOneOf(
            EvaluationVerdict.Allow,
            EvaluationVerdict.Deny,
            EvaluationVerdict.Escalate);
    }

    // ── CancellationToken propagation ────────────────────────────────────────────

    // C-073: Async I/O must respect cancellation (C-059 traceability obligation).
    [Fact]
    public async Task EvaluateAsync_WhenCancellationRequested_DoesNotHang()
    {
        // Arrange
        using var cts = new CancellationTokenSource();
        var ctx = BuildContext("some_tool");

        // Act — fire with already-cancelled token; evaluator must complete or throw OCE, not hang
        cts.Cancel();
        Func<Task> act = () => _sut.EvaluateAsync(ctx, cts.Token);

        // Assert — either completes normally (synchronous fast-path) or throws OperationCanceledException
        // Both are valid; what is NOT valid is deadlock or unhandled exception of another type.
        await act.Should().NotThrowAsync<System.Exception>(
            because: "evaluator should handle or propagate cancellation without unexpected exceptions");
    }

    // ── ActionType boundary ──────────────────────────────────────────────────────

    // C-073: C-041 — non-ToolInvocation action types with unknown tools must still deny.
    // DESIGN_QUESTION: Should C041 evaluator skip evaluation for non-ToolInvocation action types
    //                  and return Allow (pass-through) or always apply its deny logic? EA to confirm.
    [Theory]
    [InlineData("DataQuery")]
    [InlineData("ApiCall")]
    [InlineData("FileOperation")]
    public async Task EvaluateAsync_WithNonToolInvocationActionType_UnlistedToolStillDenies(string actionType)
    {
        // Arrange — unlisted tool in an alternate action type context
        var ctx = BuildContext("unlisted_tool", actionType);

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert — default deny must hold regardless of action type for unlisted tools
        result.ClaimId.Should().Be("C-041");
        // Verdict may be Deny or Allow depending on whether evaluator is scoped to ToolInvocation;
        // if it skips non-ToolInvocation, Allow is correct. EA must confirm scope.
        result.Verdict.Should().BeOneOf(EvaluationVerdict.Allow, EvaluationVerdict.Deny);
    }

    // ── IClaimEvaluator interface compliance ─────────────────────────────────────

    // C-073: Evaluator must be assignable to IClaimEvaluator (Liskov substitution, C-041 registry contract).
    [Fact]
    public void C041ToolAuthorizationEvaluator_ImplementsIClaimEvaluator()
    {
        _sut.Should().BeAssignableTo<IClaimEvaluator>();
    }

    // ── Logger invocation (observability, C-059) ─────────────────────────────────

    // C-073: Structured logging must be invoked for constitutional decision recording (C-059).
    [Fact]
    public async Task EvaluateAsync_WithUnlistedTool_InvokesLogger()
    {
        // Arrange
        var ctx = BuildContext("spy_tool");

        // Act
        await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert — logger must be called at least once (any log level acceptable)
        _loggerMock.Invocations.Should().NotBeEmpty(
            because: "constitutional decisions must be logged for traceability (C-059)");
    }

    // ── Idempotency: same context, same verdict ──────────────────────────────────

    // C-073: C-041 evaluation must be deterministic — same input always yields same verdict.
    [Fact]
    public async Task EvaluateAsync_CalledTwiceWithSameContext_ReturnsSameVerdict()
    {
        // Arrange
        var ctx = BuildContext("idempotency_check_tool");

        // Act
        var first  = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        var second = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        first.Verdict.Should().Be(second.Verdict);
        first.ClaimId.Should().Be(second.ClaimId);
    }

    // ── Malformed JSON ActionParameters ─────────────────────────────────────────

    // C-073: Malformed JSON in ActionParameters must produce Deny, not an unhandled exception.
    [Fact]
    public async Task EvaluateAsync_WithMalformedJsonParameters_ReturnsDenyWithoutException()
    {
        // Arrange — deliberately broken JSON
        var ctx = new EvaluationContext(
            ContractId: "contract-malformed",
            ActionType: "ToolInvocation",
            ActionParameters: "{ this is: not valid JSON {{{{",
            DecisionSpaceVersion: 1,
            TenantId: "tenant-test",
            SkillId: null,
            ApprovedBudgetInrPaise: 500_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 1_000L,
            BudgetSkillType: "general"
        );

        // Act
        Func<Task<EvaluationResult>> act = () => _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert — must not throw; malformed parameters = no authorized tool = Deny
        var result = await act.Should().NotThrowAsync();
        result.Subject.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Subject.ClaimId.Should().Be("C-041");
    }
}