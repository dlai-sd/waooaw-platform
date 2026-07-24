// Implements: architecture/reference/ce-validate-action-evaluators.md
// constitutional_basis: C-041 (Tool Authorization), C-043 (Budget Ceiling), C-048 (Non-Exploitation),
//                       C-049 (Honest Limitation), C-051 (Resource Transparency), C-062 (AI Security),
//                       C-076 (≥90% unit test coverage), C-059 (Traceability)

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.ConstitutionalEngine.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Evaluators;

public sealed class EvaluatorTests
{
    private readonly Mock<IEvaluationDataAccessor> _data = new();

    // ─── C-041 ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task C041_AuthorizedTool_Allow()
    {
        _data.Setup(d => d.GetAuthorizedToolsAsync("t1", It.IsAny<CancellationToken>()))
             .ReturnsAsync(SetOf("send_email"));
        var r = await Eval(new C041_ToolAuthorizationEvaluator(NullLogger<C041_ToolAuthorizationEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ToolName = "send_email"; });
        r.Decision.Should().Be(EvaluationDecision.Authorized);
    }

    [Fact]
    public async Task C041_UnauthorizedTool_Deny()
    {
        _data.Setup(d => d.GetAuthorizedToolsAsync("t1", It.IsAny<CancellationToken>()))
             .ReturnsAsync(SetOf("read_contact"));
        var r = await Eval(new C041_ToolAuthorizationEvaluator(NullLogger<C041_ToolAuthorizationEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ToolName = "delete_all_data"; });
        r.Decision.Should().Be(EvaluationDecision.Deny, because: "C-041 default deny");
    }

    [Fact]
    public async Task C041_NoActiveContract_Deny()
    {
        _data.Setup(d => d.GetAuthorizedToolsAsync("t1", It.IsAny<CancellationToken>()))
             .ReturnsAsync(SetOf());
        var r = await Eval(new C041_ToolAuthorizationEvaluator(NullLogger<C041_ToolAuthorizationEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ToolName = "any_tool"; });
        r.Decision.Should().Be(EvaluationDecision.Deny);
    }

    [Fact]
    public async Task C041_NoToolName_Deny()
    {
        var r = await Eval(new C041_ToolAuthorizationEvaluator(NullLogger<C041_ToolAuthorizationEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ToolName = null; });
        r.Decision.Should().Be(EvaluationDecision.Deny, because: "MCP_TOOL_CALL without tool_name malformed");
    }

    [Fact]
    public void C041_Metadata_Correct()
    {
        var sut = new C041_ToolAuthorizationEvaluator(NullLogger<C041_ToolAuthorizationEvaluator>.Instance);
        sut.ClaimId.Should().Be("C-041");
        sut.ApplicableActionTypes.Should().BeEquivalentTo(new[] { "MCP_TOOL_CALL" });
    }

    // ─── C-043 ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task C043_ZeroCost_Allow()
    {
        var r = await Eval(new C043_BudgetCeilingEvaluator(NullLogger<C043_BudgetCeilingEvaluator>.Instance),
            b => { b.ActionType = "LLM_INFERENCE"; b.EstimatedCostUsd = 0m; });
        r.Decision.Should().Be(EvaluationDecision.Authorized);
    }

    [Fact]
    public async Task C043_WithinBudget_Allow()
    {
        SetupBudget(10m, 1m, 5m);
        var r = await Eval(new C043_BudgetCeilingEvaluator(NullLogger<C043_BudgetCeilingEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ActionType = "LLM_INFERENCE"; b.EstimatedCostUsd = 0.50m; });
        r.Decision.Should().Be(EvaluationDecision.Authorized);
    }

    [Fact]
    public async Task C043_ExceedsPeriodBudget_Deny()
    {
        SetupBudget(0.10m, 0m, 5m);
        var r = await Eval(new C043_BudgetCeilingEvaluator(NullLogger<C043_BudgetCeilingEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ActionType = "LLM_INFERENCE"; b.EstimatedCostUsd = 0.50m; });
        r.Decision.Should().Be(EvaluationDecision.Deny);
    }

    [Fact]
    public async Task C043_ExceedsDailyCeiling_Deny()
    {
        SetupBudget(100m, 4.80m, 5m);
        var r = await Eval(new C043_BudgetCeilingEvaluator(NullLogger<C043_BudgetCeilingEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ActionType = "LLM_INFERENCE"; b.EstimatedCostUsd = 0.50m; });
        r.Decision.Should().Be(EvaluationDecision.Deny);
    }

    [Fact]
    public async Task C043_NoBudgetRecord_Deny()
    {
        SetupBudget(0m, 0m, 0m);
        var r = await Eval(new C043_BudgetCeilingEvaluator(NullLogger<C043_BudgetCeilingEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ActionType = "LLM_INFERENCE"; b.EstimatedCostUsd = 0.01m; });
        r.Decision.Should().Be(EvaluationDecision.Deny, because: "unknown budget → default deny");
    }

    // ─── C-048 ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task C048_NoFlag_Allow()
    {
        _data.Setup(d => d.HasExploitationFlagAsync("agent-1", It.IsAny<CancellationToken>())).ReturnsAsync(false);
        var r = await Eval(new C048_NonExploitationEvaluator(NullLogger<C048_NonExploitationEvaluator>.Instance),
            b => { b.AgentId = "agent-1"; });
        r.Decision.Should().Be(EvaluationDecision.Authorized);
    }

    [Fact]
    public async Task C048_FlagActive_Deny()
    {
        _data.Setup(d => d.HasExploitationFlagAsync("agent-1", It.IsAny<CancellationToken>())).ReturnsAsync(true);
        var r = await Eval(new C048_NonExploitationEvaluator(NullLogger<C048_NonExploitationEvaluator>.Instance),
            b => { b.AgentId = "agent-1"; b.ActionType = "LLM_INFERENCE"; });
        r.Decision.Should().Be(EvaluationDecision.Deny);
    }

    [Fact]
    public void C048_IsUniversal()
    {
        var sut = new C048_NonExploitationEvaluator(NullLogger<C048_NonExploitationEvaluator>.Instance);
        sut.ApplicableActionTypes.Should().BeEmpty(because: "C-048 is universal");
        sut.ClaimId.Should().Be("C-048");
    }

    // ─── C-049 ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task C049_NoLimitation_Allow()
    {
        _data.Setup(d => d.HasHonestLimitationFlagAsync("agent-1", "MCP_TOOL_CALL", It.IsAny<CancellationToken>()))
             .ReturnsAsync(false);
        var r = await Eval(new C049_HonestLimitationEvaluator(NullLogger<C049_HonestLimitationEvaluator>.Instance),
            b => { b.AgentId = "agent-1"; });
        r.Decision.Should().Be(EvaluationDecision.Authorized);
    }

    [Fact]
    public async Task C049_LimitationDeclared_Escalate()
    {
        _data.Setup(d => d.HasHonestLimitationFlagAsync("agent-1", "ESCALATION_DECISION", It.IsAny<CancellationToken>()))
             .ReturnsAsync(true);
        var r = await Eval(new C049_HonestLimitationEvaluator(NullLogger<C049_HonestLimitationEvaluator>.Instance),
            b => { b.AgentId = "agent-1"; b.ActionType = "ESCALATION_DECISION"; });
        r.Decision.Should().Be(EvaluationDecision.Escalate, because: "C-049 honest limitation → escalate");
    }

    // ─── C-051 ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task C051_LlmWithCost_Allow()
    {
        var r = await new C051_ResourceTransparencyEvaluator(NullLogger<C051_ResourceTransparencyEvaluator>.Instance)
            .EvaluateAsync(MakeContext(b => { b.ActionType = "LLM_INFERENCE"; b.EstimatedCostUsd = 0.05m; }), CancellationToken.None);
        r.Decision.Should().Be(EvaluationDecision.Authorized);
    }

    [Fact]
    public async Task C051_LlmWithoutCost_Deny()
    {
        var r = await new C051_ResourceTransparencyEvaluator(NullLogger<C051_ResourceTransparencyEvaluator>.Instance)
            .EvaluateAsync(MakeContext(b => { b.ActionType = "LLM_INFERENCE"; b.EstimatedCostUsd = 0m; }), CancellationToken.None);
        r.Decision.Should().Be(EvaluationDecision.Deny);
    }

    [Fact]
    public async Task C051_ExternalApiWithoutCost_Deny()
    {
        var r = await new C051_ResourceTransparencyEvaluator(NullLogger<C051_ResourceTransparencyEvaluator>.Instance)
            .EvaluateAsync(MakeContext(b => { b.ActionType = "EXTERNAL_API_CALL"; b.EstimatedCostUsd = 0m; }), CancellationToken.None);
        r.Decision.Should().Be(EvaluationDecision.Deny);
    }

    [Fact]
    public void C051_DataRead_NotInApplicableTypes()
    {
        // C-051 relies on the EvaluatorRegistry to filter — DATA_READ is not in ApplicableActionTypes
        var sut = new C051_ResourceTransparencyEvaluator(NullLogger<C051_ResourceTransparencyEvaluator>.Instance);
        sut.ApplicableActionTypes.Should().NotContain("DATA_READ",
            because: "C-051 only applies to LLM_INFERENCE and EXTERNAL_API_CALL");
        sut.ApplicableActionTypes.Should().Contain("LLM_INFERENCE").And.Contain("EXTERNAL_API_CALL");
        sut.ClaimId.Should().Be("C-051");
    }

    // ─── C-062 ────────────────────────────────────────────────────────────────

    [Fact]
    public async Task C062_ProhibitedTool_Deny()
    {
        _data.Setup(d => d.IsToolSecurityProhibitedAsync("dangerous_tool", It.IsAny<CancellationToken>()))
             .ReturnsAsync(true);
        var r = await Eval(new C062_AISecurityEvaluator(NullLogger<C062_AISecurityEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ToolName = "dangerous_tool"; });
        r.Decision.Should().Be(EvaluationDecision.Deny, because: "C-062 security overrides authorization");
    }

    [Fact]
    public async Task C062_AllowedTool_Allow()
    {
        _data.Setup(d => d.IsToolSecurityProhibitedAsync("send_email", It.IsAny<CancellationToken>()))
             .ReturnsAsync(false);
        var r = await Eval(new C062_AISecurityEvaluator(NullLogger<C062_AISecurityEvaluator>.Instance),
            b => { b.TenantId = "t1"; b.ToolName = "send_email"; });
        r.Decision.Should().Be(EvaluationDecision.Authorized);
    }

    [Fact]
    public async Task C062_NoToolName_PassThrough()
    {
        var r = await Eval(new C062_AISecurityEvaluator(NullLogger<C062_AISecurityEvaluator>.Instance),
            b => { b.ToolName = null; });
        r.Decision.Should().Be(EvaluationDecision.Authorized, because: "C-062 passes empty tool to C-041");
    }

    // ─── EvaluatorRegistry ────────────────────────────────────────────────────

    [Fact]
    public void Registry_McpToolCall_IncludesExpectedEvaluators()
    {
        var registry = new EvaluatorRegistry(AllEvaluators(), NullLogger<EvaluatorRegistry>.Instance);
        var ids = registry.GetEvaluators("MCP_TOOL_CALL").Select(e => e.ClaimId).ToList();
        ids.Should().Contain("C-041").And.Contain("C-048").And.Contain("C-049").And.Contain("C-062");
    }

    [Fact]
    public void Registry_LlmInference_IncludesC051()
    {
        var registry = new EvaluatorRegistry(AllEvaluators(), NullLogger<EvaluatorRegistry>.Instance);
        registry.GetEvaluators("LLM_INFERENCE").Select(e => e.ClaimId).Should().Contain("C-051");
    }

    [Fact]
    public void Registry_SecurityBeforeAuthorization()
    {
        var registry = new EvaluatorRegistry(AllEvaluators(), NullLogger<EvaluatorRegistry>.Instance);
        var list = registry.GetEvaluators("MCP_TOOL_CALL").ToList();
        list.FindIndex(e => e.ClaimId == "C-062")
            .Should().BeLessThan(list.FindIndex(e => e.ClaimId == "C-041"),
            because: "C-062 security must run before C-041 authorization");
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    private async Task<EvaluationResult> Eval(IClaimEvaluator ev, Action<CtxBuilder> cfg)
        => await ev.EvaluateAsync(MakeContext(cfg), CancellationToken.None);

    private EvaluationContext MakeContext(Action<CtxBuilder> cfg)
    {
        var b = new CtxBuilder(); cfg(b);
        return new EvaluationContext
        {
            TenantId = b.TenantId, AgentId = b.AgentId,
            ActionType = b.ActionType, ToolName = b.ToolName,
            EstimatedCostUsd = b.EstimatedCostUsd, Data = _data.Object,
        };
    }

    private sealed class CtxBuilder
    {
        public string TenantId { get; set; } = "tenant-test";
        public string AgentId { get; set; } = "agent-test";
        public string ActionType { get; set; } = "MCP_TOOL_CALL";
        public string? ToolName { get; set; }
        public decimal EstimatedCostUsd { get; set; }
    }

    private static IReadOnlySet<string> SetOf(params string[] items) =>
        new HashSet<string>(items, StringComparer.OrdinalIgnoreCase);

    private void SetupBudget(decimal rem, decimal daily, decimal ceiling)
    {
        _data.Setup(d => d.GetRemainingBudgetUsdAsync("t1", It.IsAny<CancellationToken>())).ReturnsAsync(rem);
        _data.Setup(d => d.GetDailySpendUsdAsync("t1", It.IsAny<CancellationToken>())).ReturnsAsync(daily);
        _data.Setup(d => d.GetDailyBudgetCeilingUsdAsync("t1", It.IsAny<CancellationToken>())).ReturnsAsync(ceiling);
    }

    private static IEnumerable<IClaimEvaluator> AllEvaluators() =>
    [
        new C062_AISecurityEvaluator(NullLogger<C062_AISecurityEvaluator>.Instance),
        new C048_NonExploitationEvaluator(NullLogger<C048_NonExploitationEvaluator>.Instance),
        new C041_ToolAuthorizationEvaluator(NullLogger<C041_ToolAuthorizationEvaluator>.Instance),
        new C043_BudgetCeilingEvaluator(NullLogger<C043_BudgetCeilingEvaluator>.Instance),
        new C049_HonestLimitationEvaluator(NullLogger<C049_HonestLimitationEvaluator>.Instance),
        new C051_ResourceTransparencyEvaluator(NullLogger<C051_ResourceTransparencyEvaluator>.Instance),
    ];
}
