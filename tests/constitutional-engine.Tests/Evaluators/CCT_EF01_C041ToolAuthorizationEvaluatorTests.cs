// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// constitutional_basis: C-041 (Tool Authorization), C-059 (Traceability), C-076 (Test Coverage)
using System;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    // ── helpers ────────────────────────────────────────────────────────────────

    private static EvaluationContext BuildContext(
        string actionType       = "tool.invoke",
        string? toolName        = null,
        string contractId       = "contract-001",
        string tenantId         = "tenant-abc",
        string? skillId         = null,
        long approvedBudget     = 100_000L,
        long currentSpend       = 0L,
        long proposedSpend      = 0L,
        string budgetSkillType  = "default",
        int dsVersion           = 1)
    {
        var parameters = toolName is not null
            ? JsonSerializer.Serialize(new { tool_name = toolName })
            : "{}";

        return new EvaluationContext(
            contractId,
            actionType,
            parameters,
            dsVersion,
            tenantId,
            skillId,
            approvedBudget,
            currentSpend,
            proposedSpend,
            budgetSkillType);
    }

    // ── ClaimId ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task ClaimId_IsC041()
    {
        var ctx    = BuildContext();
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    // ── ActionType guard — Deny paths ─────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_UnknownActionType_ReturnsDeny()
    {
        var ctx    = BuildContext(actionType: "unknown.action.type.xyz");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_EmptyActionType_ReturnsDeny()
    {
        var ctx    = BuildContext(actionType: "");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_WhitespaceActionType_ReturnsDeny()
    {
        var ctx    = BuildContext(actionType: "   ");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Unknown tool — structural checks ──────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_UnknownTool_ReasonIsNotEmpty()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: "definitely-not-a-real-tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_UnknownTool_ClaimIdIsC041()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: "definitely-not-a-real-tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Default-deny: invented / random tools ─────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_DefaultDenyIsStartingState_ForInventedTool()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: "invented-tool-name");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "default deny (C-041) must apply to any unlisted tool");
    }

    [Fact]
    public async Task EvaluateAsync_RandomGuidToolName_ReturnsDeny()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: Guid.NewGuid().ToString());
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Authorized action-type paths — result must be non-null ────────────────

    [Theory]
    [InlineData("tool.invoke")]
    [InlineData("tool.read")]
    [InlineData("tool.execute")]
    public async Task EvaluateAsync_AuthorizedToolActionType_ReturnsAllowOrDeny_NotNull(string actionType)
    {
        var ctx    = BuildContext(actionType: actionType);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Should().NotBeNull();
    }

    // ── Result structural invariants ──────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_ResultAlwaysHasClaimIdC041()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: "any-tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_ResultVerdictIsDefinedEnumValue()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: "any-tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        Enum.IsDefined(typeof(EvaluationVerdict), result.Verdict).Should().BeTrue();
    }

    [Fact]
    public async Task EvaluateAsync_ReturnedResult_HasNonNullProperties()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: "any-tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().NotBeNull();
        result.Reason.Should().NotBeNull();
    }

    // ── Deny verdict carries Deny enum ────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_DeniedResult_VerdictIsDeny()
    {
        var ctx    = BuildContext(actionType: "completely-unknown-type", toolName: "unknown-tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Cancellation ──────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_CancelledToken_DoesNotHang()
    {
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        var ctx = BuildContext(actionType: "tool.invoke", toolName: "any-tool");

        // The evaluator must complete (not throw OperationCanceledException
        // for an already-cancelled token because it is synchronous-path).
        var result = await _sut.EvaluateAsync(ctx, cts.Token);
        result.Should().NotBeNull();
    }

    // ── Idempotency ───────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_SameContext_IsIdempotent()
    {
        var ctx     = BuildContext(actionType: "tool.invoke", toolName: Guid.NewGuid().ToString());
        var result1 = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        var result2 = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result1.Verdict.Should().Be(result2.Verdict);
        result1.ClaimId.Should().Be(result2.ClaimId);
    }

    // ── Cross-tenant / cross-contract consistency ─────────────────────────────

    [Fact]
    public async Task EvaluateAsync_DifferentTenantIds_SameActionType_ConsistentVerdict()
    {
        const string unknownTool = "unknown-tool-xyz";

        var ctx1 = BuildContext(actionType: "tool.invoke", toolName: unknownTool, tenantId: "tenant-A");
        var ctx2 = BuildContext(actionType: "tool.invoke", toolName: unknownTool, tenantId: "tenant-B");

        var result1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var result2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        result1.Verdict.Should().Be(result2.Verdict,
            because: "tool authorization is tenant-agnostic for the same action/tool combination");
    }

    [Fact]
    public async Task EvaluateAsync_DifferentContractIds_SameActionType_ConsistentVerdict()
    {
        const string unknownTool = "unknown-tool-xyz";

        var ctx1 = BuildContext(actionType: "tool.invoke", toolName: unknownTool, contractId: "contract-001");
        var ctx2 = BuildContext(actionType: "tool.invoke", toolName: unknownTool, contractId: "contract-002");

        var result1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var result2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        result1.Verdict.Should().Be(result2.Verdict,
            because: "tool authorization must be contract-agnostic for the same action/tool combination");
    }

    // ── No tool_name parameter in ActionParameters ────────────────────────────

    [Fact]
    public async Task EvaluateAsync_NoToolNameParameter_ReturnsDeny()
    {
        // ActionParameters is "{}" — no tool_name key present
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: null);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "missing tool_name must default to deny (C-041)");
    }

    [Fact]
    public async Task EvaluateAsync_EmptyToolName_ReturnsDeny()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: "");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Deny reason is meaningful ─────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_DenyResult_ReasonIsNotNullOrWhiteSpace()
    {
        var ctx    = BuildContext(actionType: "unknown.action", toolName: "unknown-tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Reason.Should().NotBeNullOrWhiteSpace(
            because: "every Deny verdict must carry an explanatory reason (C-059 Traceability)");
    }

    // ── Null/edge-case action parameters JSON ─────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_EmptyJsonParameters_ReturnsDeny()
    {
        var ctx = new EvaluationContext(
            "contract-001",
            "tool.invoke",
            "{}",
            1,
            "tenant-abc",
            null,
            100_000L,
            0L,
            0L,
            "default");

        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Verdict is never Escalate for tool-authorization decisions ────────────

    [Fact]
    public async Task EvaluateAsync_UnknownTool_VerdictIsNeverEscalate()
    {
        var ctx    = BuildContext(actionType: "tool.invoke", toolName: Guid.NewGuid().ToString());
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().NotBe(EvaluationVerdict.Escalate,
            because: "C-041 tool authorization produces Allow or Deny — never Escalate");
    }
}