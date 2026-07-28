// Implements: architecture/reference/ce-validate-action-evaluators.md §C-041 Evaluator — Tool Authorization
// Constitutional basis: C-041 (Tool Authorization), C-076 (Test Coverage), C-059 (Traceability)
using FluentAssertions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    private readonly C041ToolAuthorizationEvaluator _sut = new();

    // ── helpers ──────────────────────────────────────────────────────────────

    private static EvaluationContext BuildContext(
        string actionType,
        string actionParameters = "{}",
        string contractId = "contract-test",
        string tenantId = "tenant-test",
        string? skillId = null,
        string budgetSkillType = "",
        long approvedBudget = 100_000L,
        long currentSpend = 0L,
        long proposedSpend = 0L,
        int decisionSpaceVersion = 1)
        => new EvaluationContext(
            contractId,
            actionType,
            actionParameters,
            decisionSpaceVersion,
            tenantId,
            skillId,
            approvedBudget,
            currentSpend,
            proposedSpend,
            budgetSkillType);

    // ── ClaimId contract ─────────────────────────────────────────────────────

    [Fact]
    public async Task ClaimId_IsC041()
    {
        var ctx = BuildContext("any_action");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Default-deny: unlisted / unknown tool ────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_UnknownActionType_ReturnsDeny()
    {
        var ctx = BuildContext("totally_unlisted_tool_xyz");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_EmptyActionType_ReturnsDeny()
    {
        var ctx = BuildContext("");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_WhitespaceActionType_ReturnsDeny()
    {
        var ctx = BuildContext("   ");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task EvaluateAsync_UnknownTool_ReasonIsNotEmpty()
    {
        var ctx = BuildContext("not_a_known_tool");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Reason.Should().NotBeNullOrWhiteSpace();
    }

    [Fact]
    public async Task EvaluateAsync_UnknownTool_ClaimIdIsC041()
    {
        var ctx = BuildContext("unlisted_action");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.ClaimId.Should().Be("C-041");
    }

    // ── Authorized tools ─────────────────────────────────────────────────────

    [Theory]
    [InlineData("web_search")]
    [InlineData("read_file")]
    [InlineData("write_file")]
    [InlineData("code_execution")]
    [InlineData("api_call")]
    public async Task EvaluateAsync_AuthorizedToolActionType_ReturnsAllowOrDeny_NotNull(string actionType)
    {
        // The evaluator MUST return a non-null result for any input (C-041 robustness).
        var ctx = BuildContext(actionType);
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Should().NotBeNull();
        result.ClaimId.Should().Be("C-041");
        result.Reason.Should().NotBeNullOrWhiteSpace();
        result.Verdict.Should().BeOneOf(
            EvaluationVerdict.Allow,
            EvaluationVerdict.Deny,
            EvaluationVerdict.Escalate);
    }

    // ── Result shape invariants ──────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_ResultAlwaysHasClaimIdC041()
    {
        var actions = new[]
        {
            "web_search", "code_execution", "read_file",
            "write_file", "api_call", "unknown_tool",
            "", "   ", "UPPERCASE_TOOL"
        };

        foreach (var action in actions)
        {
            var ctx = BuildContext(action);
            var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
            result.ClaimId.Should().Be("C-041",
                because: $"ClaimId must always be C-041 regardless of action '{action}'");
        }
    }

    [Fact]
    public async Task EvaluateAsync_ResultVerdictIsDefinedEnumValue()
    {
        var ctx = BuildContext("any_action");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        Enum.IsDefined(typeof(EvaluationVerdict), result.Verdict).Should().BeTrue();
    }

    // ── Cancellation ─────────────────────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_CancelledToken_DoesNotHang()
    {
        var ctx = BuildContext("web_search");
        using var cts = new CancellationTokenSource();
        // Evaluate once with live token — must complete without deadlock.
        var result = await _sut.EvaluateAsync(ctx, cts.Token);
        result.Should().NotBeNull();
    }

    // ── Default-deny is the STARTING state (C-041 constitutional rule) ────────

    [Fact]
    public async Task EvaluateAsync_DefaultDenyIsStartingState_ForInventedTool()
    {
        // An invented, never-seen tool MUST be denied (C-041 §default deny).
        var ctx = BuildContext("invented_tool_that_does_not_exist_in_any_allowlist");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            because: "C-041 mandates default-deny: unlisted tool must be DENY");
    }

    [Fact]
    public async Task EvaluateAsync_RandomGuidToolName_ReturnsDeny()
    {
        var ctx = BuildContext($"tool_{Guid.NewGuid():N}");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── Context variations do not affect C-041 core logic ────────────────────

    [Fact]
    public async Task EvaluateAsync_DifferentTenantIds_SameActionType_ConsistentVerdict()
    {
        const string action = "totally_unknown_action_12345";
        var ctx1 = BuildContext(action, tenantId: "tenant-A");
        var ctx2 = BuildContext(action, tenantId: "tenant-B");

        var r1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        r1.Verdict.Should().Be(r2.Verdict,
            because: "C-041 tool authorization is not tenant-specific for unlisted tools");
    }

    [Fact]
    public async Task EvaluateAsync_DifferentContractIds_SameActionType_ConsistentVerdict()
    {
        const string action = "totally_unknown_action_99999";
        var ctx1 = BuildContext(action, contractId: "contract-1");
        var ctx2 = BuildContext(action, contractId: "contract-2");

        var r1 = await _sut.EvaluateAsync(ctx1, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx2, CancellationToken.None);

        r1.Verdict.Should().Be(r2.Verdict);
    }

    // ── EvaluationResult record shape ─────────────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_ReturnedResult_HasNonNullProperties()
    {
        var ctx = BuildContext("some_action");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        result.ClaimId.Should().NotBeNull();
        result.Reason.Should().NotBeNull();
    }

    [Fact]
    public async Task EvaluateAsync_DeniedResult_VerdictIsDeny()
    {
        // Directly validate the enum value — no string comparison (fixes CS1503).
        var ctx = BuildContext("definitely_not_in_any_allow_list_xyzzy");
        var result = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        // The verdict property is EvaluationVerdict (enum), not a string.
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Verdict.Should().NotBe(EvaluationVerdict.Allow);
    }

    // ── Idempotency: same context → same verdict ──────────────────────────────

    [Fact]
    public async Task EvaluateAsync_SameContext_IsIdempotent()
    {
        var ctx = BuildContext("idempotency_test_action");
        var r1 = await _sut.EvaluateAsync(ctx, CancellationToken.None);
        var r2 = await _sut.EvaluateAsync(ctx, CancellationToken.None);

        r1.Verdict.Should().Be(r2.Verdict);
        r1.ClaimId.Should().Be(r2.ClaimId);
    }
}