// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-048, C-049, C-062, C-076
using FluentAssertions;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Skeleton;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public class ConstitutionalSafetyEvaluatorTests
{
    private static EvaluationContext Context(
        string actionType = "CUSTOMER_MESSAGE",
        string parameters = "{}"
    ) => new("contract-safety", actionType, parameters, 1, "tenant-safety");

    [Theory]
    [InlineData("read_file,delete_file")]
    [InlineData("read_file; delete_file")]
    public async Task C041_ProhibitedTool_ReturnsDeny(string prohibitedActions)
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance
        );
        var parameters =
            $"{{\"tool_name\":\"delete_file\",\"prohibited_actions\":\"{prohibitedActions}\",\"authorized_actions\":\"delete_file\"}}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None
        );

        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain("explicitly prohibited");
    }

    [Fact]
    public async Task C041_AlwaysAskTool_ReturnsEscalate()
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(
            Context(
                "MCP_TOOL_CALL",
                "{\"tool_name\":\"send_email\",\"always_ask_actions\":\"send_email\",\"authorized_actions\":\"send_email\"}"
            ),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
        result.Reason.Should().Contain("customer confirmation");
    }

    [Fact]
    public async Task C041_ProhibitedRule_TakesPrecedenceOverAlwaysAsk()
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance
        );
        const string parameters =
            "{\"tool_name\":\"send_email\",\"prohibited_actions\":\"send_email\",\"always_ask_actions\":\"send_email\",\"authorized_actions\":\"send_email\"}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task C041_NonmatchingRestrictedLists_ContinueToAuthorizedList()
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance
        );
        const string parameters =
            "{\"tool_name\":\"read_file\",\"prohibited_actions\":\"delete_file\",\"always_ask_actions\":\"send_email\",\"authorized_actions\":\"read_file\"}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task C041_MissingActionType_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(Context(" "), CancellationToken.None);

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Deny,
                    "C-041: ActionType must be specified. No anonymous tool invocations are permitted."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-041 DENY: ActionType is null or empty. ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C041_OutsideMcpScope_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context("CUSTOMER_MESSAGE"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult("C-041", EvaluationVerdict.Allow, "Outside C-041 MCP scope.")
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Debug,
                    "C-041 not applicable to ActionType=CUSTOMER_MESSAGE. ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C041_MissingToolName_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Deny,
                    "C-041: tool_name must be specified in ActionParameters. No anonymous tool invocations are permitted."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-041 DENY: tool_name is null or empty. ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C041_ProhibitedTool_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);
        const string parameters =
            "{\"tool_name\":\"delete_file\",\"prohibited_actions\":\"delete_file\",\"authorized_actions\":\"delete_file\"}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Deny,
                    "C-041: Action 'MCP_TOOL_CALL' is explicitly prohibited in the Decision Space."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-041 DENY: ActionType=MCP_TOOL_CALL is explicitly prohibited. "
                        + "ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C041_AlwaysAskTool_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);
        const string parameters =
            "{\"tool_name\":\"send_email\",\"always_ask_actions\":\"send_email\",\"authorized_actions\":\"send_email\"}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Escalate,
                    "C-041: Tool 'send_email' is at a scope boundary — explicit customer confirmation required (always-ask)."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Information,
                    "C-041 ESCALATE: tool_name=send_email requires customer confirmation. "
                        + "ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C041_MissingAuthorizedList_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", "{\"tool_name\":\"read_file\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Deny,
                    "C-041: No authorized_actions list present in Decision Space context. Default deny applied."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-041 DENY (default): No 'authorized_actions' parameter in context. "
                        + "ContractId=contract-safety ActionType=MCP_TOOL_CALL TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C041_UnlistedTool_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(
                "MCP_TOOL_CALL",
                "{\"tool_name\":\"delete_file\",\"authorized_actions\":\"read_file\"}"
            ),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Deny,
                    "C-041: Tool 'delete_file' is not listed in the authorized Decision Space. Default deny applied."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-041 DENY (default): tool_name=delete_file not in authorized list. "
                        + "ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C041_AuthorizedTool_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C041ToolAuthorizationEvaluator>();
        var evaluator = new C041ToolAuthorizationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(
                "MCP_TOOL_CALL",
                "{\"tool_name\":\"read_file\",\"authorized_actions\":\"read_file\"}"
            ),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-041",
                    EvaluationVerdict.Allow,
                    "C-041: Tool 'read_file' is within the authorized Decision Space."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Debug,
                    "C-041 Allow: tool_name=read_file is authorized by Decision Space. "
                        + "ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public void EvaluatorConstructors_RejectNullLoggers()
    {
        var constructors = new Action[]
        {
            () => _ = new C041ToolAuthorizationEvaluator(null!),
            () => _ = new C043BudgetCeilingEvaluator(null!),
            () => _ = new C048NonExploitationEvaluator(null!),
            () => _ = new C049HonestLimitationEvaluator(null!),
            () => _ = new C062AiSecurityEvaluator(null!),
        };

        constructors
            .Should()
            .AllSatisfy(constructor => constructor.Should().Throw<ArgumentNullException>());
    }

    [Fact]
    public void CeUnavailableException_PreservesMessage()
    {
        var exception = new CeUnavailableException("constitutional engine unavailable");

        exception.Message.Should().Be("constitutional engine unavailable");
    }

    [Fact]
    public async Task C041_CancelledEvaluation_PropagatesCancellation()
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance
        );
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var act = () => evaluator.EvaluateAsync(Context(), cancellation.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
    }

    [Theory]
    [InlineData("EXPLOIT_CUSTOMER_VULNERABILITY")]
    [InlineData("MANIPULATE_CUSTOMER_DECISION")]
    [InlineData("HIGH_PRESSURE_CLOSE")]
    [InlineData("COERCIVE_RETENTION")]
    public async Task C048_ProhibitedActionType_ReturnsDeny(string actionType)
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(Context(actionType), CancellationToken.None);

        result.ClaimId.Should().Be("C-048");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(actionType);
    }

    [Theory]
    [InlineData("HIGH_PRESSURE_SALES")]
    [InlineData("manipulative_urgency")]
    [InlineData("FEAR_BASED_MARKETING")]
    [InlineData("VULNERABILITY_TARGETING")]
    [InlineData("DECEPTIVE_FRAMING")]
    [InlineData("COERCIVE_UPSELL")]
    [InlineData("DARK_PATTERN")]
    public async Task C048_ProhibitedContentType_ReturnsDeny(string contentType)
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"content_type\":\"{contentType}\"}}"),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(contentType);
    }

    [Theory]
    [InlineData("exploitation_indicator")]
    [InlineData("targeting_vulnerable_customer")]
    public async Task C048_ExplicitExploitationFlag_ReturnsDeny(string parameter)
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"{parameter}\":\"TRUE\"}}"),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(parameter);
    }

    [Fact]
    public async Task C048_UnparseablePressureLevel_ReturnsFailSafeDeny()
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"pressure_level\":\"intense\"}"),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain("not a valid integer");
    }

    [Theory]
    [InlineData("6", EvaluationVerdict.Deny)]
    [InlineData("5", EvaluationVerdict.Allow)]
    [InlineData("", EvaluationVerdict.Allow)]
    public async Task C048_PressureThreshold_IsEnforced(
        string pressureLevel,
        EvaluationVerdict expectedVerdict
    )
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"pressure_level\":\"{pressureLevel}\"}}"),
            CancellationToken.None
        );

        result.Verdict.Should().Be(expectedVerdict);
    }

    [Fact]
    public async Task C048_CancelledEvaluation_PropagatesCancellation()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var act = () => evaluator.EvaluateAsync(Context(), cancellation.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-048 Non-Exploitation: evaluation cancelled for contract contract-safety, action CUSTOMER_MESSAGE"
                )
            );
    }

    [Fact]
    public async Task C048_ProhibitedAction_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context("HIGH_PRESSURE_CLOSE"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-048",
                    EvaluationVerdict.Deny,
                    "Action type 'HIGH_PRESSURE_CLOSE' is constitutionally classified as an exploitation "
                        + "action and is prohibited under C-048 (Non-Exploitation)."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-048 Non-Exploitation: prohibited action type 'HIGH_PRESSURE_CLOSE' denied "
                        + "for contract contract-safety tenant tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C048_ProhibitedContent_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"content_type\":\"DARK_PATTERN\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-048",
                    EvaluationVerdict.Deny,
                    "Parameter content_type='DARK_PATTERN' constitutes exploitation and is "
                        + "prohibited under C-048 (Non-Exploitation)."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-048 Non-Exploitation: prohibited content_type 'DARK_PATTERN' denied "
                        + "for contract contract-safety, action CUSTOMER_MESSAGE, tenant tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C048_ExploitationIndicator_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"exploitation_indicator\":\"true\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-048",
                    EvaluationVerdict.Deny,
                    "Parameter exploitation_indicator=true. Action denied under C-048 (Non-Exploitation)."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-048 Non-Exploitation: exploitation_indicator=true denied "
                        + "for contract contract-safety, action CUSTOMER_MESSAGE, tenant tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C048_VulnerableCustomerTargeting_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"targeting_vulnerable_customer\":\"true\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-048",
                    EvaluationVerdict.Deny,
                    "Parameter targeting_vulnerable_customer=true. Action targets a vulnerable customer "
                        + "and is denied under C-048 (Non-Exploitation)."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-048 Non-Exploitation: targeting_vulnerable_customer=true denied "
                        + "for contract contract-safety, action CUSTOMER_MESSAGE, tenant tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C048_UnparseablePressure_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"pressure_level\":\"intense\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-048",
                    EvaluationVerdict.Deny,
                    "Parameter pressure_level='intense' is not a valid integer. "
                        + "Denied as fail-safe under C-048 (Non-Exploitation)."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-048 Non-Exploitation: non-parseable pressure_level 'intense' denied "
                        + "for contract contract-safety, action CUSTOMER_MESSAGE (fail-safe)"
                )
            );
    }

    [Fact]
    public async Task C048_ExcessivePressure_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"pressure_level\":\"6\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-048",
                    EvaluationVerdict.Deny,
                    "Parameter pressure_level=6 exceeds the constitutional maximum of 5 under C-048 (Non-Exploitation)."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-048 Non-Exploitation: pressure_level 6 exceeds constitutional threshold (5) "
                        + "for contract contract-safety, action CUSTOMER_MESSAGE, tenant tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C048_CleanActionAtPressureBoundary_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C048NonExploitationEvaluator>();
        var evaluator = new C048NonExploitationEvaluator(logger);
        const string parameters =
            "{\"exploitation_indicator\":\"false\",\"targeting_vulnerable_customer\":\"false\",\"pressure_level\":\"5\"}";

        var result = await evaluator.EvaluateAsync(
            Context(parameters: parameters),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-048",
                    EvaluationVerdict.Allow,
                    "No exploitation indicators detected; action is constitutionally compliant with C-048."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Debug,
                    "C-048 Non-Exploitation: action CUSTOMER_MESSAGE allowed for contract contract-safety, tenant tenant-safety"
                )
            );
    }

    [Theory]
    [InlineData("{\"uncertainty_acknowledged\":\"true\"}", "declared honest limitation")]
    [InlineData("{\"confidence_score\":\"unknown\"}", "could not be parsed")]
    [InlineData("{\"confidence_score\":\"0.6999\"}", "below the constitutional floor")]
    public async Task C049_LimitationSignal_ReturnsEscalate(
        string parameters,
        string reasonFragment
    )
    {
        var evaluator = new C049HonestLimitationEvaluator(
            NullLogger<C049HonestLimitationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(
            Context(parameters: parameters),
            CancellationToken.None
        );

        result.ClaimId.Should().Be("C-049");
        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
        result.Reason.Should().ContainEquivalentOf(reasonFragment);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"uncertainty_acknowledged\":\"false\"}")]
    [InlineData("{\"confidence_score\":\"0.70\"}")]
    [InlineData("{\"confidence_score\":\"1.0\"}")]
    public async Task C049_NoLimitationSignal_ReturnsAllow(string parameters)
    {
        var evaluator = new C049HonestLimitationEvaluator(
            NullLogger<C049HonestLimitationEvaluator>.Instance
        );

        var result = await evaluator.EvaluateAsync(
            Context(parameters: parameters),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task C049_CancelledEvaluation_PropagatesCancellation()
    {
        var evaluator = new C049HonestLimitationEvaluator(
            NullLogger<C049HonestLimitationEvaluator>.Instance
        );
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var act = () => evaluator.EvaluateAsync(Context(), cancellation.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
    }

    [Fact]
    public async Task C049_ExplicitUncertainty_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C049HonestLimitationEvaluator>();
        var evaluator = new C049HonestLimitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"uncertainty_acknowledged\":\"true\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-049",
                    EvaluationVerdict.Escalate,
                    "C-049: Agent declared honest limitation (uncertainty_acknowledged=true) — "
                        + "action escalated for explicit customer authorisation."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Information,
                    "C-049: uncertainty_acknowledged=true on ContractId=contract-safety "
                        + "ActionType=CUSTOMER_MESSAGE TenantId=tenant-safety — escalating to customer"
                )
            );
    }

    [Fact]
    public async Task C049_UnparseableConfidence_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C049HonestLimitationEvaluator>();
        var evaluator = new C049HonestLimitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"confidence_score\":\"unknown\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-049",
                    EvaluationVerdict.Escalate,
                    "C-049: confidence_score parameter value 'unknown' could not be parsed as a numeric score — "
                        + "escalating for constitutional safety."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-049: confidence_score present but not parseable as double (raw=unknown) "
                        + "on ContractId=contract-safety TenantId=tenant-safety — escalating for constitutional safety"
                )
            );
    }

    [Fact]
    public async Task C049_LowConfidence_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C049HonestLimitationEvaluator>();
        var evaluator = new C049HonestLimitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"confidence_score\":\"0.6999\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-049",
                    EvaluationVerdict.Escalate,
                    "C-049: Reported confidence 0.6999 is below the constitutional floor of 0.7000 — "
                        + "action escalated to customer."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Information,
                    "C-049: confidence_score=0.6999 below constitutional floor 0.7000 on "
                        + "ContractId=contract-safety ActionType=CUSTOMER_MESSAGE TenantId=tenant-safety — escalating"
                )
            );
    }

    [Fact]
    public async Task C049_ConfidenceAtFloor_EmitsExactDecisionAndAuditLogs()
    {
        var logger = new RecordingLogger<C049HonestLimitationEvaluator>();
        var evaluator = new C049HonestLimitationEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"confidence_score\":\"0.70\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-049",
                    EvaluationVerdict.Allow,
                    "C-049: No honest limitation signal detected — action proceeds."
                )
            );
        logger
            .Entries.Should()
            .Equal(
                (
                    LogLevel.Debug,
                    "C-049: confidence_score=0.7000 meets floor 0.7000 on ContractId=contract-safety ActionType=CUSTOMER_MESSAGE"
                ),
                (
                    LogLevel.Debug,
                    "C-049: Allow — no honest limitation signal on ContractId=contract-safety ActionType=CUSTOMER_MESSAGE TenantId=tenant-safety"
                )
            );
    }

    [Theory]
    [InlineData("SYSTEM_PROMPT_INJECTION")]
    [InlineData("PRIVILEGE_ESCALATION")]
    [InlineData("CREDENTIAL_EXFILTRATION")]
    [InlineData("MODEL_JAILBREAK")]
    [InlineData("CONSTITUTIONAL_BYPASS")]
    [InlineData("DIRECT_DB_ACCESS")]
    [InlineData("RAW_SYSTEM_COMMAND")]
    [InlineData("ARBITRARY_CODE_EXECUTION")]
    public async Task C062_ProhibitedActionType_ReturnsDeny(string actionType)
    {
        var evaluator = new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(Context(actionType), CancellationToken.None);

        result.ClaimId.Should().Be("C-062");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(actionType);
    }

    [Theory]
    [InlineData("bash")]
    [InlineData("PoWeRsHeLl")]
    [InlineData("SHELL_DELETE")]
    [InlineData("exec_process")]
    [InlineData("ADMIN_OVERRIDE_POLICY")]
    [InlineData("BYPASS_GUARD")]
    public async Task C062_ProhibitedTool_ReturnsDeny(string toolName)
    {
        var evaluator = new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"tool_name\":\"{toolName}\"}}"),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(toolName);
    }

    [Fact]
    public async Task C062_InjectionMarker_ReturnsDeny()
    {
        var evaluator = new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"injection_marker\":\"ignore_previous_instructions\"}"),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain("ignore_previous_instructions");
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"tool_name\":\"read_file\"}")]
    public async Task C062_ClearAction_ReturnsAllow(string parameters)
    {
        var evaluator = new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: parameters),
            CancellationToken.None
        );

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task C062_CancelledEvaluation_PropagatesCancellation()
    {
        var evaluator = new C062AiSecurityEvaluator(NullLogger<C062AiSecurityEvaluator>.Instance);
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var act = () => evaluator.EvaluateAsync(Context(), cancellation.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
    }

    [Fact]
    public async Task C062_ProhibitedAction_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C062AiSecurityEvaluator>();
        var evaluator = new C062AiSecurityEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context("PRIVILEGE_ESCALATION"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-062",
                    EvaluationVerdict.Deny,
                    "C-062: Action type 'PRIVILEGE_ESCALATION' is constitutionally prohibited under AI Security policy."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-062 AI Security: prohibited action type 'PRIVILEGE_ESCALATION' denied. "
                        + "ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C062_ProhibitedTool_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C062AiSecurityEvaluator>();
        var evaluator = new C062AiSecurityEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"tool_name\":\"bash\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-062",
                    EvaluationVerdict.Deny,
                    "C-062: Tool 'bash' is constitutionally prohibited under AI Security policy."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-062 AI Security: prohibited tool name 'bash' denied. ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C062_ProhibitedPrefix_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C062AiSecurityEvaluator>();
        var evaluator = new C062AiSecurityEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"tool_name\":\"SHELL_DELETE\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-062",
                    EvaluationVerdict.Deny,
                    "C-062: Tool 'SHELL_DELETE' matches constitutionally prohibited tool-family prefix 'SHELL_'."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-062 AI Security: tool 'SHELL_DELETE' matches prohibited prefix 'SHELL_'. "
                        + "ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C062_InjectionMarker_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C062AiSecurityEvaluator>();
        var evaluator = new C062AiSecurityEvaluator(logger);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"injection_marker\":\"ignore_previous_instructions\"}"),
            CancellationToken.None
        );

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-062",
                    EvaluationVerdict.Deny,
                    "C-062: Prompt-injection marker detected ('ignore_previous_instructions') — action denied under AI Security policy."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Warning,
                    "C-062 AI Security: prompt-injection marker detected. Marker='ignore_previous_instructions' "
                        + "ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }

    [Fact]
    public async Task C062_ClearAction_EmitsExactDecisionAndAuditLog()
    {
        var logger = new RecordingLogger<C062AiSecurityEvaluator>();
        var evaluator = new C062AiSecurityEvaluator(logger);

        var result = await evaluator.EvaluateAsync(Context(), CancellationToken.None);

        result
            .Should()
            .BeEquivalentTo(
                new EvaluationResult(
                    "C-062",
                    EvaluationVerdict.Allow,
                    "C-062: Action cleared by AI Security evaluator."
                )
            );
        logger
            .Entries.Should()
            .ContainSingle()
            .Which.Should()
            .Be(
                (
                    LogLevel.Debug,
                    "C-062 AI Security: action cleared. ActionType=CUSTOMER_MESSAGE ContractId=contract-safety TenantId=tenant-safety"
                )
            );
    }
}
