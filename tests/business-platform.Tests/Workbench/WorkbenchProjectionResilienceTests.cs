// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-01
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchProjectionResilienceTests
{
    [Fact]
    public async Task GoalVersions_StillShowTheCurrentVersionWhenTheHistoryStoreIsDown()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync();
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync();
        fixture.GoalHistory.Failure = new InvalidOperationException("history down");

        var list = await fixture.Service.ListGoalVersionsAsync(
            fixture.Context(),
            goal.GoalId,
            WorkbenchPage.First,
            default
        );

        var version = Assert.Single(list!.Items);
        Assert.Equal(1, version.VersionNo);
        Assert.Equal("Customer", version.RevisedBy);
    }

    [Fact]
    public async Task Goal_WithoutADeclaration_HasNoDeclaredMeasuresOrConstraints()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(withDeclaration: false);
        fixture.SetWorkspace();
        var goal = await fixture.AddGoalAsync();

        var detail = await fixture.Service.GetGoalAsync(fixture.Context(), goal.GoalId, default);

        Assert.NotNull(detail);
        Assert.Empty(detail.Measures);
        Assert.Empty(detail.Constraints);
    }

    [Fact]
    public async Task Decisions_WithoutADeclaration_NameNoComponentsButStillAskTheOwner()
    {
        var fixture = await WorkbenchProjectionFixture.CreateAsync(withDeclaration: false);
        fixture.SetWorkspace();
        await fixture.AddSkillAsync("CONTENT_STRATEGY_AND_CALENDAR", "PROPOSED");

        var items = await fixture.Service.ListDecisionItemsAsync(fixture.Context(), default);

        var item = Assert.Single(items);
        Assert.Equal("SKILL", item.Kind);
        Assert.Equal("CONTENT_STRATEGY_AND_CALENDAR", item.SkillId);
    }
}
