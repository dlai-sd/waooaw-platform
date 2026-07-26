// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-073 (Annotation),
//                       C-076 (≥90% Unit Test Coverage), C-065 (Author ≠ Approver)

#nullable enable

using FluentAssertions;
using Microsoft.Extensions.Logging;
using Moq;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01 Constitutional Compliance Tests for C041ToolAuthorizationEvaluator.
/// C-073: Every test in this class validates a constitutional obligation under C-041.
/// C-076: Coverage target ≥90% for C041ToolAuthorizationEvaluator.
/// </summary>
public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    // ── fixture ──────────────────────────────────────────────────────────────
    private readonly C041ToolAuthorizationEvaluator _sut;
    private readonly Mock<ILogger<C041ToolAuthorizationEvaluator>> _loggerMock;

    public CCT_EF01_C041ToolAuthorizationEvaluatorTests()
    {
        _loggerMock = new Mock<ILogger<C041ToolAuthorizationEvaluator>>();
        _sut = new C041ToolAuthorizationEvaluator(_loggerMock.Object);
    }

    // ── helpers ───────────────────────────────────────────────────────────────

    /// <summary>
    /// Builds an EvaluationContext with ActionParameters JSON containing tool_name
    /// and optionally authorized_tools (a JSON-encoded array).
    /// C-073: Helper encodes constitutional evidence fields correctly per C-041.
    /// </summary>
    private static EvaluationContext BuildContext(
        string? toolName,
        string actionType = "ToolInvocation",
        string? authorizedTools = null)
    {
        // ActionParameters is JSON-encoded. Use ctx.GetParameter(key) inside evaluator.
        var toolNameJson = toolName is null ? "null" : $"\"{toolName}\"";
        var authorizedToolsJson = authorizedTools is null
            ? "null"
            : $"\"{authorizedTools.Replace("\"", "\\\"")}\"";

        var actionParameters =
            $"{{\"tool_name\":{toolNameJson},\"authorized_tools\":{authorizedToolsJson}}}";

        return new EvaluationContext(
            ContractId: "contract-cct-ef01",
            ActionType: actionType,
            ActionParameters: actionParameters,
            DecisionSpaceVersion: 1,
            TenantId: "tenant-test",
            SkillId: null,
            ApprovedBudgetInrPaise: 100_000L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "general"
        );
    }

    // ── ClaimId ───────────────────────────────────────────────────────────────

    /// <summary>C-073: Evaluator must declare its constitutional claim identifier as "C-041".</summary>
    [Fact]
    public void ClaimId_IsC041()
    {
        _sut.ClaimId.Should().Be("C-041");
    }

    // ── Default-deny: missing / empty / whitespace tool name ──────────────────

    /// <summary>C-073 / C-041: An unlisted tool must always result in DENY (default-deny posture).</summary>
    [Fact]
    public async Task EvaluateAsync_WithUnlistedTool_ReturnsDeny()
    {
        // Arrange — tool_name present but NOT in authorized_tools list
        var ctx = BuildContext(
            toolName: "unlisted_tool",
            authorizedTools: "[\\\"web_search\\\",\\\"calculator\\\"]");

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.ClaimId.Should().Be("C-041");
    }

    /// <summary>C-073 / C-041: Missing tool_name parameter must yield DENY — evidence required.</summary>
    [Fact]
    public async Task EvaluateAsync_WithMissingToolNameParameter_ReturnsDeny()
    {
        // Arrange — ActionParameters does not contain tool_name key
        var ctx = new EvaluationContext(
            ContractId: "contract-missing-param",
            ActionType: "ToolInvocation",
            ActionParameters: "{\"other_key\":\"value\"}",
            DecisionSpaceVersion: 1,
            TenantId: "tenant-test",
            SkillId: null,
            ApprovedBudgetInrPaise: 0L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "general"
        );

        // Act
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    /// <summary>C-073 / C-041: Empty tool name must result in DENY.</summary>
    [Fact]
    public async Task EvaluateAsync_WithEmptyToolName_ReturnsDeny()
    {
        var ctx = BuildContext(toolName: string.Empty);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    /// <summary>C-073 / C-041: Whitespace-only tool name must result in DENY.</summary>
    [Fact]
    public async Task EvaluateAsync_WithWhitespaceToolName_ReturnsDeny()
    {
        var ctx = BuildContext(toolName: "   ");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Parameterised: various unlisted tools ─────────────────────────────────

    /// <summary>C-073 / C-041: Multiple distinct unlisted tools must all be denied.</summary>
    [Theory]
    [InlineData("exec_shell")]
    [InlineData("fs_write")]
    [InlineData("network_scan")]
    [InlineData("UNLISTED")]
    [InlineData("__proto__")]
    public async Task EvaluateAsync_WithVariousUnlistedTools_AllReturnDeny(string toolName)
    {
        var ctx = BuildContext(toolName: toolName, authorizedTools: "[\\\"safe_tool\\\"]");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: $"tool '{toolName}' is not in the authorized list");
    }

    // ── Result shape ──────────────────────────────────────────────────────────

    /// <summary>
    /// C-073 / C-059: EvaluationResult must always carry a ClaimId and non-empty Reason
    /// to support constitutional traceability.
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_ResultShape_AlwaysPopulatesClaimIdAndReason()
    {
        var ctx = BuildContext(toolName: "any_tool");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().NotBeNullOrWhiteSpace();
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    // ── Cancellation ──────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Evaluator must respect CancellationToken and must not deadlock.
    /// Completing (even with exception) within 5 s is sufficient for this gate.
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_WhenCancellationRequested_DoesNotHang()
    {
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        var ctx = BuildContext(toolName: "web_search");

        // Either completes normally or throws OperationCanceledException — both are acceptable.
        // The test asserts it does NOT hang (5-second timeout enforced by xUnit runner).
        var act = async () => await _sut.EvaluateAsync(ctx, cts.Token);

        await act.Should().CompleteWithinAsync(TimeSpan.FromSeconds(5));
    }

    // ── Action-type independence ───────────────────────────────────────────────

    /// <summary>
    /// C-073 / C-041: Regardless of ActionType, an unlisted tool must be denied —
    /// C-041 is not scoped to a single action type.
    /// </summary>
    [Theory]
    [InlineData("DataQuery")]
    [InlineData("InferenceTrigger")]
    [InlineData("")]
    public async Task EvaluateAsync_WithNonToolInvocationActionType_UnlistedToolStillDenies(string actionType)
    {
        var ctx = BuildContext(toolName: "unlisted_tool", actionType: actionType);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Type contract ─────────────────────────────────────────────────────────

    /// <summary>C-073: Evaluator must implement IClaimEvaluator for registry integration.</summary>
    [Fact]
    public void C041ToolAuthorizationEvaluator_ImplementsIClaimEvaluator()
    {
        _sut.Should().BeAssignableTo<IClaimEvaluator>();
    }

    // ── Logger invocation ─────────────────────────────────────────────────────

    /// <summary>
    /// C-073 / C-059: Denied evaluations must emit structured log entries for
    /// constitutional audit trail (C-059 Traceability).
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_WithUnlistedTool_InvokesLogger()
    {
        var ctx = BuildContext(toolName: "blacklisted_tool");

        await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Verify that the logger was called at least once at any level.
        _loggerMock.Invocations.Should().NotBeEmpty(
            because: "C-059 requires structured logging on every constitutional evaluation");
    }

    // ── Idempotency ───────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Two evaluations on the same context must yield the same verdict —
    /// deterministic constitutional evaluation (no side-effects between calls).
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_CalledTwiceWithSameContext_ReturnsSameVerdict()
    {
        var ctx = BuildContext(toolName: "repeated_tool");

        var first = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        var second = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        second.Verdict.Should().Be(first.Verdict);
        second.ClaimId.Should().Be(first.ClaimId);
    }

    // ── Malformed JSON ────────────────────────────────────────────────────────

    /// <summary>
    /// C-073 / C-041: Malformed ActionParameters JSON must never throw —
    /// the evaluator must default-deny and remain stable.
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_WithMalformedJsonParameters_ReturnsDenyWithoutException()
    {
        var ctx = new EvaluationContext(
            ContractId: "contract-malformed",
            ActionType: "ToolInvocation",
            ActionParameters: "{ this is : not valid json !!!",
            DecisionSpaceVersion: 1,
            TenantId: "tenant-test",
            SkillId: null,
            ApprovedBudgetInrPaise: 0L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: "general"
        );

        var act = async () => await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // Must not throw — constitutional evaluators must be fault-tolerant
        var result = await act.Should().NotThrowAsync();
        result.Subject.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "default-deny applies when parameters cannot be parsed (C-041)");
    }

    // ── Allow path (authorized tool) ─────────────────────────────────────────

    /// <summary>
    /// C-073 / C-041: A tool explicitly present in the authorized_tools list must
    /// yield ALLOW — confirming the evaluator is not a hard-deny gate.
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_WithAuthorizedTool_ReturnsAllow()
    {
        // authorized_tools inner JSON array, serialised as a JSON string value
        var ctx = BuildContext(
            toolName: "web_search",
            authorizedTools: "[\\\"web_search\\\",\\\"calculator\\\"]");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow,
            because: "web_search is explicitly in the authorized_tools list");
        result.ClaimId.Should().Be("C-041");
    }

    /// <summary>
    /// C-073 / C-041: Only the exact listed tool is authorized — another tool from
    /// the same context must still be denied.
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_WithToolNotInAuthorizedList_ReturnsDenyEvenWhenListNonEmpty()
    {
        var ctx = BuildContext(
            toolName: "fs_write",
            authorizedTools: "[\\\"web_search\\\"]");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    /// <summary>
    /// C-073 / C-041: Null tool name (JSON null) must result in DENY —
    /// absence of evidence is not evidence of authorization.
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_WithNullToolName_ReturnsDeny()
    {
        var ctx = BuildContext(toolName: null);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    /// <summary>
    /// C-073 / C-041: When authorized_tools is null/missing, even a named tool must be denied —
    /// no authorization list means no authorization.
    /// </summary>
    [Fact]
    public async Task EvaluateAsync_WithNoAuthorizedToolsList_ReturnsDeny()
    {
        // authorized_tools intentionally omitted (null)
        var ctx = BuildContext(toolName: "web_search", authorizedTools: null);

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "no authorized_tools list means no tool can be authorized (C-041 default-deny)");
    }
}