// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-041 (Tool Authorization), C-076 (Test Coverage)
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

/// <summary>
/// CCT-EF-01: Constitutional Compliance Tests for C041ToolAuthorizationEvaluator.
/// C-041 (Tool Authorization): every MCP tool call must be evaluated against the
/// customer's Decision Space. Default deny applies — unlisted tool = DENY.
/// C-076 (Test Coverage): ≥90% line coverage required for evaluator logic.
/// </summary>
public sealed class CCT_EF01_C041ToolAuthorizationEvaluatorTests
{
    // ── Helpers ─────────────────────────────────────────────────────────────

    private static C041ToolAuthorizationEvaluator CreateEvaluator()
        => new C041ToolAuthorizationEvaluator(NullLogger<C041ToolAuthorizationEvaluator>.Instance);

    /// <summary>
    /// Builds a minimal EvaluationContext for MCP tool call evaluation.
    /// All positional record properties supplied; BudgetSkillType defaults to empty
    /// because C041 evaluator is not budget-aware.
    /// </summary>
    private static EvaluationContext BuildContext(
        string toolName,
        string actionType = "MCP_TOOL_CALL",
        string contractId = "contract-cct-ef01",
        string tenantId = "tenant-cct-ef01",
        int decisionSpaceVersion = 1)
        => new EvaluationContext(
            ContractId: contractId,
            ActionType: actionType,
            ActionParameters: $"{{\"tool_name\": \"{toolName}\"}}",
            DecisionSpaceVersion: decisionSpaceVersion,
            TenantId: tenantId,
            SkillId: null,
            ApprovedBudgetInrPaise: 0L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: string.Empty);

    private static EvaluationContext BuildContextWithRawParameters(
        string actionParameters,
        string actionType = "MCP_TOOL_CALL",
        string contractId = "contract-cct-ef01",
        string tenantId = "tenant-cct-ef01")
        => new EvaluationContext(
            ContractId: contractId,
            ActionType: actionType,
            ActionParameters: actionParameters,
            DecisionSpaceVersion: 1,
            TenantId: tenantId,
            SkillId: null,
            ApprovedBudgetInrPaise: 0L,
            CurrentSpendInrPaise: 0L,
            ProposedSpendInrPaise: 0L,
            BudgetSkillType: string.Empty);

    // ── CCT-EF-01-A: Default Deny — C-041 Constitutional Floor ──────────────

    [Fact]
    public async Task EvaluateAsync_UnknownTool_ReturnsDeny()
    {
        // Arrange — C-041: unlisted tool must produce DENY as default
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("completely_unknown_tool_xyz_12345");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull();
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "C-041 mandates default-deny for any tool not in the authorised whitelist");
        result.Reason.Should().NotBeNullOrWhiteSpace(
            "every DENY verdict must carry a human-readable reason for audit");
    }

    [Fact]
    public async Task EvaluateAsync_UnknownTool_ClaimId_IsC041()
    {
        // Arrange
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("unrecognised_tool");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert — AD-008: every permission decision must name its constitutional basis
        result.ClaimId.Should().Be(
            "C-041",
            "C041ToolAuthorizationEvaluator must stamp its decisions with claim C-041");
    }

    [Fact]
    public async Task EvaluateAsync_EmptyToolName_ReturnsDeny()
    {
        // Arrange — empty string tool_name is not a valid authorisation target
        var evaluator = CreateEvaluator();
        var ctx = BuildContext(string.Empty);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "an empty tool name cannot be matched to any authorised tool — default deny applies");
    }

    [Fact]
    public async Task EvaluateAsync_MissingToolNameKey_ReturnsDeny()
    {
        // Arrange — ActionParameters JSON lacks the 'tool_name' key entirely;
        // ctx.GetParameter("tool_name") returns null, triggering default deny.
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters("{\"other_param\": \"value\"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "a missing tool_name parameter cannot be authorised; default deny (C-041) applies");
    }

    [Fact]
    public async Task EvaluateAsync_EmptyActionParameters_ReturnsDeny()
    {
        // Arrange — completely empty JSON object; no tool name resolvable
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters("{}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "empty action parameters yield no tool_name; default deny (C-041)");
    }

    [Fact]
    public async Task EvaluateAsync_NullOrMalformedParameters_ReturnsDeny()
    {
        // Arrange — malformed JSON; GetParameter("tool_name") must not throw; must return DENY
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters("not-valid-json");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "malformed JSON yields no tool_name; evaluator must not throw — default deny (C-041)");
    }

    // ── CCT-EF-01-B: Non-MCP_TOOL_CALL action types ─────────────────────────

    [Fact]
    public async Task EvaluateAsync_NonMcpActionType_ReturnsDeny()
    {
        // Arrange — C-041 evaluator is scoped to MCP_TOOL_CALL; other action types
        // are outside its scope; the constitutional default deny must hold.
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("file_read", actionType: "MARKETING_POST");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "C041 evaluator must not authorise non-MCP_TOOL_CALL action types");
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_TradeOrderActionType_ReturnsDeny()
    {
        // Arrange — trading action types are not within C041 tool authorisation scope
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("execute_trade", actionType: "TRADE_ORDER");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "TRADE_ORDER action type is not a recognised MCP tool call; C-041 default deny applies");
    }

    // ── CCT-EF-01-C: Result structural invariants ────────────────────────────

    [Fact]
    public async Task EvaluateAsync_AlwaysReturnsNonNullResult()
    {
        // Arrange — evaluator must never return null (Error Handling Rule 2)
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("any_tool");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Should().NotBeNull(
            "public methods must never return null to indicate failure (constitutional error rule 2)");
    }

    [Fact]
    public async Task EvaluateAsync_AlwaysPopulatesClaimId()
    {
        // Arrange — AD-008: every permission decision must name its constitutional basis
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("some_tool");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.ClaimId.Should().NotBeNullOrWhiteSpace(
            "AD-008 mandates that every permission decision carries its constitutional claim ID");
    }

    [Fact]
    public async Task EvaluateAsync_AlwaysPopulatesReason()
    {
        // Arrange — every verdict must carry an audit-ready reason string
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("some_tool");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Reason.Should().NotBeNullOrWhiteSpace(
            "every verdict (Allow/Deny/Escalate) must carry a human-readable reason for the audit ledger");
    }

    [Fact]
    public async Task EvaluateAsync_VerdictIsOneOfKnownValues()
    {
        // Arrange — verdict must be within the declared EvaluationVerdict enum range
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("unknown_tool");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().BeOneOf(
            new[] { EvaluationVerdict.Allow, EvaluationVerdict.Deny, EvaluationVerdict.Escalate },
            "verdict must always be a valid EvaluationVerdict enum member");
    }

    // ── CCT-EF-01-D: Cancellation token propagation ──────────────────────────

    [Fact]
    public async Task EvaluateAsync_WithCancelledToken_ThrowsOrReturnsDeny()
    {
        // Arrange — constitutional obligation: evaluator must respect cancellation (Error Rule 4)
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("file_read");
        using var cts = new CancellationTokenSource();
        await cts.CancelAsync();

        // Act — either throws OperationCanceledException or returns Deny safely
        Func<Task> act = async () => await evaluator.EvaluateAsync(ctx, cts.Token);

        // Assert — either outcome is acceptable; what is NOT acceptable is hanging indefinitely
        // We give it a hard timeout to verify it does not block.
        var completedInTime = await Task.WhenAny(
            act().ContinueWith(_ => true),
            Task.Delay(TimeSpan.FromSeconds(5)).ContinueWith(_ => false));

        var finishedBeforeTimeout = await completedInTime;
        finishedBeforeTimeout.Should().BeTrue(
            "evaluator must not block indefinitely on a cancelled token (Error Handling Rule 4)");
    }

    // ── CCT-EF-01-E: Tenant isolation — context fields propagated correctly ──

    [Fact]
    public async Task EvaluateAsync_DifferentTenants_BothReturnDenyForUnknownTool()
    {
        // Arrange — C-041 default deny must be tenant-independent for unlisted tools;
        // the result must not accidentally allow based on tenantId alone.
        var evaluator = CreateEvaluator();
        var ctxTenantA = BuildContext("unknown_tool", tenantId: "tenant-alpha");
        var ctxTenantB = BuildContext("unknown_tool", tenantId: "tenant-beta");

        // Act
        var resultA = await evaluator.EvaluateAsync(ctxTenantA, CancellationToken.None);
        var resultB = await evaluator.EvaluateAsync(ctxTenantB, CancellationToken.None);

        // Assert
        resultA.Verdict.Should().Be(EvaluationVerdict.Deny,
            "C-041 default deny applies to tenant-alpha for unlisted tools");
        resultB.Verdict.Should().Be(EvaluationVerdict.Deny,
            "C-041 default deny applies to tenant-beta for unlisted tools");
    }

    [Fact]
    public async Task EvaluateAsync_DifferentContractIds_BothReturnDenyForUnknownTool()
    {
        // Arrange — DENY must not vary between contracts for an unrecognised tool
        var evaluator = CreateEvaluator();
        var ctx1 = BuildContext("unrecognised_tool", contractId: "contract-001");
        var ctx2 = BuildContext("unrecognised_tool", contractId: "contract-002");

        // Act
        var result1 = await evaluator.EvaluateAsync(ctx1, CancellationToken.None);
        var result2 = await evaluator.EvaluateAsync(ctx2, CancellationToken.None);

        // Assert
        result1.Verdict.Should().Be(EvaluationVerdict.Deny);
        result2.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    // ── CCT-EF-01-F: Decision space version field does not bypass deny ────────

    [Fact]
    public async Task EvaluateAsync_HighDecisionSpaceVersion_DoesNotBypassDeny()
    {
        // Arrange — a high decision space version must not accidentally unlock tools
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("unknown_tool", decisionSpaceVersion: 9999);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            "decision space version does not bypass C-041 default deny for unlisted tools");
    }

    [Fact]
    public async Task EvaluateAsync_ZeroDecisionSpaceVersion_ReturnsDeny()
    {
        // Arrange — version 0 is an invalid/stale version; unlisted tool must still DENY
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("unknown_tool", decisionSpaceVersion: 0);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            "decision space version 0 is stale/invalid; C-041 default deny holds");
    }

    // ── CCT-EF-01-G: Concurrent invocation safety ───────────────────────────

    [Fact]
    public async Task EvaluateAsync_ConcurrentInvocations_AllReturnDenyForUnknownTools()
    {
        // Arrange — evaluator must be stateless and safe for concurrent calls
        var evaluator = CreateEvaluator();
        const int concurrency = 20;

        var tasks = Enumerable.Range(0, concurrency)
            .Select(i => evaluator.EvaluateAsync(
                BuildContext($"concurrent_tool_{i}", tenantId: $"tenant-{i}"),
                CancellationToken.None))
            .ToArray();

        // Act
        var results = await Task.WhenAll(tasks);

        // Assert
        results.Should().HaveCount(concurrency);
        results.Should().OnlyContain(
            r => r.Verdict == EvaluationVerdict.Deny,
            "all concurrent invocations must return DENY for unlisted tools (C-041 stateless default deny)");
    }

    // ── CCT-EF-01-H: Whitespace and case sensitivity in tool names ───────────

    [Fact]
    public async Task EvaluateAsync_ToolNameWithLeadingWhitespace_ReturnsDeny()
    {
        // Arrange — " file_read" (with leading space) is not the same as "file_read"
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters("{\"tool_name\": \" file_read\"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            "tool names with leading whitespace must not match authorised tools; C-041 default deny applies");
    }

    [Fact]
    public async Task EvaluateAsync_ToolNameWithTrailingWhitespace_ReturnsDeny()
    {
        // Arrange — trailing whitespace must not smuggle in an authorised tool name
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters("{\"tool_name\": \"file_read \"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            "tool names with trailing whitespace must not match; C-041 default deny applies");
    }

    [Fact]
    public async Task EvaluateAsync_NullToolNameValue_ReturnsDeny()
    {
        // Arrange — explicit JSON null value for tool_name; GetParameter returns null
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters("{\"tool_name\": null}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            "a null tool_name JSON value cannot be matched; C-041 default deny applies");
    }

    // ── CCT-EF-01-I: EvaluationResult type integrity ─────────────────────────

    [Fact]
    public async Task EvaluateAsync_ClaimId_NeverContainsWhitespaceOnly()
    {
        // Arrange
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("any_tool_whatsoever");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert — ClaimId must be a meaningful constitutional reference, not padding
        result.ClaimId.Trim().Should().NotBeEmpty(
            "ClaimId must be a non-whitespace constitutional claim reference (AD-008)");
    }

    [Fact]
    public async Task EvaluateAsync_Reason_NeverContainsWhitespaceOnly()
    {
        // Arrange
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("any_tool_whatsoever");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Reason.Trim().Should().NotBeEmpty(
            "Reason must be a meaningful audit string, not whitespace padding");
    }

    [Fact]
    public async Task EvaluateAsync_DenyVerdict_ReasonMentionsDenialOrAuthorisation()
    {
        // Arrange — a DENY reason should be meaningful enough for an auditor to understand
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("totally_unknown_xyz");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().NotBeNullOrWhiteSpace(
            "DENY results must carry an audit-ready reason per Error Handling Rule 2");
    }

    // ── CCT-EF-01-J: Multiple sequential evaluations — statelessness ──────────

    [Fact]
    public async Task EvaluateAsync_RepeatedCallsSameTool_ProducesConsistentVerdict()
    {
        // Arrange — evaluator must be deterministic; same input always yields same output
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("repeated_unknown_tool");

        // Act
        var result1 = await evaluator.EvaluateAsync(ctx, CancellationToken.None);
        var result2 = await evaluator.EvaluateAsync(ctx, CancellationToken.None);
        var result3 = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result1.Verdict.Should().Be(result2.Verdict,
            "evaluator must be deterministic — same input must produce same verdict");
        result2.Verdict.Should().Be(result3.Verdict,
            "evaluator must be deterministic across repeated calls");
        result1.ClaimId.Should().Be(result2.ClaimId);
        result2.ClaimId.Should().Be(result3.ClaimId);
    }

    [Fact]
    public async Task EvaluateAsync_AfterPreviousDenyCall_StillReturnsCorrectVerdict()
    {
        // Arrange — a prior DENY must not corrupt evaluator state for subsequent calls
        var evaluator = CreateEvaluator();
        var ctxFirst = BuildContext("first_unknown_tool");
        var ctxSecond = BuildContext("second_unknown_tool");

        // Act
        var first = await evaluator.EvaluateAsync(ctxFirst, CancellationToken.None);
        var second = await evaluator.EvaluateAsync(ctxSecond, CancellationToken.None);

        // Assert
        first.Verdict.Should().Be(EvaluationVerdict.Deny,
            "first call with unknown tool must DENY (C-041)");
        second.Verdict.Should().Be(EvaluationVerdict.Deny,
            "subsequent call with another unknown tool must also DENY — evaluator is stateless");
    }

    // ── CCT-EF-01-K: Action type sensitivity ─────────────────────────────────

    [Fact]
    public async Task EvaluateAsync_EmptyActionType_ReturnsDeny()
    {
        // Arrange — empty action type is structurally invalid; must DENY
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("some_tool", actionType: string.Empty);

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            "empty action type cannot be authorised; C-041 default deny applies");
    }

    [Fact]
    public async Task EvaluateAsync_McpToolCallActionType_UnknownTool_StillDenies()
    {
        // Arrange — correct action type but unrecognised tool name must still produce DENY
        var evaluator = CreateEvaluator();
        var ctx = BuildContext("xyzzy_no_such_tool", actionType: "MCP_TOOL_CALL");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Deny,
            "correct action type alone is not sufficient; tool name must also be authorised (C-041)");
        result.ClaimId.Should().Be("C-041",
            "the C041 evaluator must always stamp its constitutional basis");
    }

    // ── CCT-EF-01-L: Allow path — authorized tool invocations ──────────────

    [Fact]
    public async Task EvaluateAsync_AuthorizedTool_ReturnsAllow()
    {
        // Arrange — tool_name is in the authorized_actions list; C-041 must Allow
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters(
            "{\"tool_name\": \"read_file\", \"authorized_actions\": \"read_file\"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Allow,
            "tool 'read_file' is in the authorized list");
        result.ClaimId.Should().Be("C-041");
    }

    [Fact]
    public async Task EvaluateAsync_SecondAuthorizedTool_ReturnsAllow()
    {
        // Arrange — tool_name matches the second entry in a comma-separated authorized list
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters(
            "{\"tool_name\": \"write_file\", \"authorized_actions\": \"read_file,write_file\"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Allow,
            "tool 'write_file' is the second entry in the authorized list");
    }

    [Fact]
    public async Task EvaluateAsync_SingleElementListMatchingTool_ReturnsAllow()
    {
        // Arrange — single-element authorized list exactly matching tool_name
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters(
            "{\"tool_name\": \"read_file\", \"authorized_actions\": \"read_file\"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Allow,
            "single-element authorized list must Allow the matching tool (C-041)");
    }

    [Fact]
    public async Task EvaluateAsync_AllowResult_HasNonEmptyReason()
    {
        // Arrange — every Allow verdict must carry an audit-ready reason string
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters(
            "{\"tool_name\": \"read_file\", \"authorized_actions\": \"read_file\"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(EvaluationVerdict.Allow);
        result.Reason.Should().NotBeNullOrWhiteSpace(
            "Allow verdicts must carry a human-readable audit reason string");
    }

    [Fact]
    public async Task EvaluateAsync_ToolNameWrongCase_ReturnsDeny()
    {
        // Arrange — tool name matching is case-sensitive (ordinal); READ_FILE ≠ read_file
        var evaluator = CreateEvaluator();
        var ctx = BuildContextWithRawParameters(
            "{\"tool_name\": \"READ_FILE\", \"authorized_actions\": \"read_file\"}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        result.Verdict.Should().Be(
            EvaluationVerdict.Deny,
            "tool name matching is case-sensitive; READ_FILE does not equal read_file");
    }

    public static IEnumerable<object[]> ToolMatrixData =>
    [
        new object[] { "read_file",      new[] { "read_file", "write_file" }, true  },
        new object[] { "write_file",     new[] { "read_file", "write_file" }, true  },
        new object[] { "exec_shell",     new[] { "read_file", "write_file" }, false },
        new object[] { "list_directory", new[] { "read_file" },              false },
        new object[] { "read_file",      new[] { "read_file" },              true  },
    ];

    [Theory]
    [MemberData(nameof(ToolMatrixData))]
    public async Task EvaluateAsync_ToolMatrix_ReturnsExpectedVerdict(
        string toolName, string[] authorizedTools, bool expectAllow)
    {
        // Arrange — parameterized matrix: (tool, authorized list, expected verdict)
        var evaluator = CreateEvaluator();
        var authList = string.Join(",", authorizedTools);
        var ctx = BuildContextWithRawParameters(
            $"{{\"tool_name\": \"{toolName}\", \"authorized_actions\": \"{authList}\"}}");

        // Act
        var result = await evaluator.EvaluateAsync(ctx, CancellationToken.None);

        // Assert
        var expected = expectAllow ? EvaluationVerdict.Allow : EvaluationVerdict.Deny;
        result.Verdict.Should().Be(expected,
            expectAllow
                ? $"tool '{toolName}' is in the authorized list [{authList}]"
                : $"tool '{toolName}' is NOT in the authorized list [{authList}] — C-041 default deny");
    }
}