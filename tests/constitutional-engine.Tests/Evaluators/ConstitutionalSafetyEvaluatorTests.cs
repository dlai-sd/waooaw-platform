// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-048, C-049, C-062, C-076
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Skeleton;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public class ConstitutionalSafetyEvaluatorTests
{
    private static EvaluationContext Context(
        string actionType = "CUSTOMER_MESSAGE",
        string parameters = "{}") => new(
            "contract-safety",
            actionType,
            parameters,
            1,
            "tenant-safety");

    [Theory]
    [InlineData("read_file,delete_file")]
    [InlineData("read_file; delete_file")]
    public async Task C041_ProhibitedTool_ReturnsDeny(string prohibitedActions)
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance);
        var parameters =
            $"{{\"tool_name\":\"delete_file\",\"prohibited_actions\":\"{prohibitedActions}\",\"authorized_actions\":\"delete_file\"}}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None);

        result.ClaimId.Should().Be("C-041");
        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain("explicitly prohibited");
    }

    [Fact]
    public async Task C041_AlwaysAskTool_ReturnsEscalate()
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(
                "MCP_TOOL_CALL",
                "{\"tool_name\":\"send_email\",\"always_ask_actions\":\"send_email\",\"authorized_actions\":\"send_email\"}"),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Escalate);
        result.Reason.Should().Contain("customer confirmation");
    }

    [Fact]
    public async Task C041_ProhibitedRule_TakesPrecedenceOverAlwaysAsk()
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance);
        const string parameters =
            "{\"tool_name\":\"send_email\",\"prohibited_actions\":\"send_email\",\"always_ask_actions\":\"send_email\",\"authorized_actions\":\"send_email\"}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
    }

    [Fact]
    public async Task C041_NonmatchingRestrictedLists_ContinueToAuthorizedList()
    {
        var evaluator = new C041ToolAuthorizationEvaluator(
            NullLogger<C041ToolAuthorizationEvaluator>.Instance);
        const string parameters =
            "{\"tool_name\":\"read_file\",\"prohibited_actions\":\"delete_file\",\"always_ask_actions\":\"send_email\",\"authorized_actions\":\"read_file\"}";

        var result = await evaluator.EvaluateAsync(
            Context("MCP_TOOL_CALL", parameters),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
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

        constructors.Should().AllSatisfy(
            constructor => constructor.Should().Throw<ArgumentNullException>());
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
            NullLogger<C041ToolAuthorizationEvaluator>.Instance);
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
            NullLogger<C048NonExploitationEvaluator>.Instance);

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
            NullLogger<C048NonExploitationEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"content_type\":\"{contentType}\"}}"),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(contentType);
    }

    [Theory]
    [InlineData("exploitation_indicator")]
    [InlineData("targeting_vulnerable_customer")]
    public async Task C048_ExplicitExploitationFlag_ReturnsDeny(string parameter)
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"{parameter}\":\"TRUE\"}}"),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(parameter);
    }

    [Fact]
    public async Task C048_UnparseablePressureLevel_ReturnsFailSafeDeny()
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"pressure_level\":\"intense\"}"),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain("not a valid integer");
    }

    [Theory]
    [InlineData("6", EvaluationVerdict.Deny)]
    [InlineData("5", EvaluationVerdict.Allow)]
    [InlineData("", EvaluationVerdict.Allow)]
    public async Task C048_PressureThreshold_IsEnforced(
        string pressureLevel,
        EvaluationVerdict expectedVerdict)
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"pressure_level\":\"{pressureLevel}\"}}"),
            CancellationToken.None);

        result.Verdict.Should().Be(expectedVerdict);
    }

    [Fact]
    public async Task C048_CancelledEvaluation_PropagatesCancellation()
    {
        var evaluator = new C048NonExploitationEvaluator(
            NullLogger<C048NonExploitationEvaluator>.Instance);
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var act = () => evaluator.EvaluateAsync(Context(), cancellation.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
    }

    [Theory]
    [InlineData("{\"uncertainty_acknowledged\":\"true\"}", "declared honest limitation")]
    [InlineData("{\"confidence_score\":\"unknown\"}", "could not be parsed")]
    [InlineData("{\"confidence_score\":\"0.6999\"}", "below the constitutional floor")]
    public async Task C049_LimitationSignal_ReturnsEscalate(
        string parameters,
        string reasonFragment)
    {
        var evaluator = new C049HonestLimitationEvaluator(
            NullLogger<C049HonestLimitationEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(Context(parameters: parameters), CancellationToken.None);

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
            NullLogger<C049HonestLimitationEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(Context(parameters: parameters), CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task C049_CancelledEvaluation_PropagatesCancellation()
    {
        var evaluator = new C049HonestLimitationEvaluator(
            NullLogger<C049HonestLimitationEvaluator>.Instance);
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var act = () => evaluator.EvaluateAsync(Context(), cancellation.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
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
        var evaluator = new C062AiSecurityEvaluator(
            NullLogger<C062AiSecurityEvaluator>.Instance);

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
        var evaluator = new C062AiSecurityEvaluator(
            NullLogger<C062AiSecurityEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: $"{{\"tool_name\":\"{toolName}\"}}"),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain(toolName);
    }

    [Fact]
    public async Task C062_InjectionMarker_ReturnsDeny()
    {
        var evaluator = new C062AiSecurityEvaluator(
            NullLogger<C062AiSecurityEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(
            Context(parameters: "{\"injection_marker\":\"ignore_previous_instructions\"}"),
            CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Deny);
        result.Reason.Should().Contain("ignore_previous_instructions");
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"tool_name\":\"read_file\"}")]
    public async Task C062_ClearAction_ReturnsAllow(string parameters)
    {
        var evaluator = new C062AiSecurityEvaluator(
            NullLogger<C062AiSecurityEvaluator>.Instance);

        var result = await evaluator.EvaluateAsync(Context(parameters: parameters), CancellationToken.None);

        result.Verdict.Should().Be(EvaluationVerdict.Allow);
    }

    [Fact]
    public async Task C062_CancelledEvaluation_PropagatesCancellation()
    {
        var evaluator = new C062AiSecurityEvaluator(
            NullLogger<C062AiSecurityEvaluator>.Instance);
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();

        var act = () => evaluator.EvaluateAsync(Context(), cancellation.Token);

        await act.Should().ThrowAsync<OperationCanceledException>();
    }
}
