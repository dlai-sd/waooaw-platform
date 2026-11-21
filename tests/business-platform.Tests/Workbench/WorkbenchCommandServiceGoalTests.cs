// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchCommandServiceGoalTests
{
    private const string Schema = "1.0";

    private static Dictionary<string, string> Parameters() =>
        new() { ["BUSINESS_DOMAIN"] = "bakery", ["PRIMARY_LOCATION"] = "Pune" };

    private static CreateWorkbenchGoalRequest Create(
        string version,
        string title = "  Know where we stand  ",
        string goalTypeId = WorkbenchCommandServiceFixture.GoalTypeId,
        Dictionary<string, string>? parameters = null,
        string schema = Schema
    ) => new(schema, version, goalTypeId, title, parameters ?? Parameters());

    private static ReviseWorkbenchGoalRequest Revise(
        string version,
        string reason = " The location changed ",
        string? title = null,
        Dictionary<string, string>? parameters = null
    ) => new(Schema, version, parameters ?? Parameters(), reason, title);

    private static async Task<WorkbenchException> Refused(Func<Task> action)
    {
        var failure = await Assert.ThrowsAsync<WorkbenchException>(action);
        return failure;
    }

    [Fact]
    public async Task CreateGoal_ProposesTheGoalAtTheOwnerAndRecordsItsFirstVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var context = fixture.Employer();

        var result = await fixture.Commands.CreateGoalAsync(
            context,
            Guid.NewGuid(),
            Create(await fixture.VersionAsync()),
            CancellationToken.None
        );

        Assert.False(result.Replayed);
        Assert.Equal("ACCEPTED", result.Body.Status);
        Assert.Equal(context.CorrelationId, result.Body.CorrelationId);
        var goals = await fixture.Configuration.GetPortalGoalsAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            CancellationToken.None
        );
        var stored = Assert.Single(goals).Goal;
        Assert.Equal("Know where we stand", stored.Goal);
        Assert.Equal(WorkbenchCommandServiceFixture.GoalTypeId, stored.Measure);
        Assert.Equal("PROPOSED", stored.Status);
        Assert.Contains("\"BUSINESS_DOMAIN\":\"bakery\"", stored.Baseline);
        Assert.Equal(stored.GoalId.ToString("D"), result.Body.ResourceRef);
        Assert.Equal(RelationshipConfigurationService.GetGoalVersion(stored), result.Body.Version);
        var history = await fixture.GoalHistory.ListAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            stored.GoalId,
            CancellationToken.None
        );
        var entry = Assert.Single(history);
        Assert.Equal("Know where we stand", entry.Title);
        Assert.Equal("Customer", entry.RevisedBy);
        Assert.Null(entry.Reason);
        Assert.Equal("Pune", entry.Parameters["PRIMARY_LOCATION"]);
    }

    [Fact]
    public async Task CreateGoal_ReplaysTheSameCommandWithoutCreatingASecondGoal()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var key = Guid.NewGuid();
        var request = Create(await fixture.VersionAsync());

        var first = await fixture.Commands.CreateGoalAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.CreateGoalAsync(
            fixture.Employer(),
            key,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.True(second.Body.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
        Assert.Single(
            await fixture.Configuration.GetPortalGoalsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task CreateGoal_RefusesTheSameKeyUsedForADifferentRequest()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var key = Guid.NewGuid();
        var version = await fixture.VersionAsync();
        await fixture.Commands.CreateGoalAsync(
            fixture.Employer(),
            key,
            Create(version),
            CancellationToken.None
        );

        var failure = await Refused(() =>
            fixture.Commands.CreateGoalAsync(
                fixture.Employer(),
                key,
                Create(version, title: "Another goal"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.IdempotencyConflict, failure.Code);
    }

    public static TheoryData<string, string> InvalidCreateRequests() =>
        new()
        {
            { "schema", "schemaVersion must be 1.0" },
            { "blank-version", "expectedVersion must be 1 to 128" },
            { "long-version", "expectedVersion must be 1 to 128" },
            { "blank-goal-type", "goalTypeId is required." },
            { "blank-title", "title must be 1 to 240 characters." },
            { "long-title", "title must be 1 to 240 characters." },
            { "null-parameters", "parameters may hold at most 20 values." },
            { "many-parameters", "parameters may hold at most 20 values." },
            { "blank-key", "Every parameter needs a name" },
            { "long-key", "Every parameter needs a name" },
            { "blank-value", "Every parameter needs a name" },
            { "long-value", "Every parameter needs a name" },
            { "oversized-json", "parameters are too long." },
        };

    [Theory]
    [MemberData(nameof(InvalidCreateRequests))]
    public async Task CreateGoal_RejectsAnInvalidRequestBeforeAnyOwnerIsAsked(
        string defect,
        string detail
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var version = await fixture.VersionAsync();
        var request = defect switch
        {
            "schema" => Create(version, schema: "2.0"),
            "blank-version" => Create(" "),
            "long-version" => Create(new string('v', 129)),
            "blank-goal-type" => Create(version, goalTypeId: " "),
            "blank-title" => Create(version, title: "  "),
            "long-title" => Create(version, title: new string('t', 241)),
            "null-parameters" => Create(version) with { Parameters = null! },
            "many-parameters" => Create(
                version,
                parameters: Enumerable
                    .Range(0, 21)
                    .ToDictionary(index => $"KEY_{index}", _ => "value")
            ),
            "blank-key" => Create(version, parameters: new() { [" "] = "value" }),
            "long-key" => Create(version, parameters: new() { [new string('k', 81)] = "value" }),
            "blank-value" => Create(version, parameters: new() { ["KEY"] = " " }),
            "long-value" => Create(version, parameters: new() { ["KEY"] = new string('v', 201) }),
            _ => Create(
                version,
                parameters: Enumerable
                    .Range(0, 15)
                    .ToDictionary(index => $"KEY_{index:D2}", _ => new string('v', 190))
            ),
        };

        var failure = await Refused(() =>
            fixture.Commands.CreateGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                request,
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, failure.Code);
        Assert.Contains(detail, failure.Detail);
        Assert.Empty(
            await fixture.Configuration.GetPortalGoalsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task CreateGoal_IsRefusedForAnAudienceThatMayNotDecide()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Refused(() =>
            fixture.Commands.CreateGoalAsync(
                fixture.Evaluator(),
                Guid.NewGuid(),
                Create("relationship-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchCommandService.RoleDetail, failure.Detail);
    }

    [Fact]
    public async Task CreateGoal_IsAllowedForADelegate()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var result = await fixture.Commands.CreateGoalAsync(
            fixture.Manager(),
            Guid.NewGuid(),
            Create(await fixture.VersionAsync()),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", result.Body.Status);
    }

    [Fact]
    public async Task CreateGoal_IsRefusedOnAStoppedRelationship()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(
            EmploymentRelationshipState.StoppedEmergency
        );

        var failure = await Refused(async () =>
            await fixture.Commands.CreateGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Create(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
        Assert.Contains("stopped", failure.Detail);
    }

    [Fact]
    public async Task CreateGoal_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Refused(() =>
            fixture.Commands.CreateGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Create("relationship-0"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task CreateGoal_ReportsAMissingRelationshipAsNotFound()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var context = fixture.Employer() with { RelationshipId = Guid.NewGuid() };

        await Assert.ThrowsAsync<KeyNotFoundException>(() =>
            fixture.Commands.CreateGoalAsync(
                context,
                Guid.NewGuid(),
                Create("relationship-1"),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task CreateGoal_IsUnavailableWhenTheAgentDeclaresNoExperience()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(withDeclaration: false);

        var failure = await Refused(async () =>
            await fixture.Commands.CreateGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Create(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.Unavailable, failure.Code);
        Assert.Contains("declaration", failure.Detail);
    }

    [Fact]
    public async Task CreateGoal_RefusesAGoalTypeTheAgentDoesNotDeclare()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Refused(async () =>
            await fixture.Commands.CreateGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Create(await fixture.VersionAsync(), goalTypeId: "WIN_THE_LOTTERY"),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("not declared", failure.Detail);
    }

    [Fact]
    public async Task CreateGoal_RefusesAParameterTheGoalTypeDoesNotDeclare()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Refused(async () =>
            await fixture.Commands.CreateGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Create(
                    await fixture.VersionAsync(),
                    parameters: new() { ["THREE_MONTH_ASPIRATION"] = "grow" }
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("parameter is not declared", failure.Detail);
    }

    [Fact]
    public async Task CreateGoal_StillSucceedsWhenTheHistoryCannotBeWritten()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        fixture.GoalHistory.FailAppend = true;

        var result = await fixture.Commands.CreateGoalAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            Create(await fixture.VersionAsync()),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", result.Body.Status);
        Assert.Single(
            await fixture.Configuration.GetPortalGoalsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        var warning = Assert.Single(
            fixture.Logger.Entries,
            entry => entry.Level == LogLevel.Warning
        );
        Assert.Contains("history append failed", warning.Message);
        Assert.IsType<InvalidOperationException>(warning.Exception);
    }

    [Fact]
    public async Task ReviseGoal_ChangesTheGoalAndKeepsTheEarlierVersionInTheHistory()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();
        var goalVersion = RelationshipConfigurationService.GetGoalVersion(goal);

        var result = await fixture.Commands.ReviseGoalAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            goal.GoalId,
            Revise(
                goalVersion,
                title: "  Know our position in Pune ",
                parameters: new() { ["BUSINESS_DOMAIN"] = "cafe" }
            ),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", result.Body.Status);
        Assert.Equal(goal.GoalId.ToString("D"), result.Body.ResourceRef);
        var revised = Assert
            .Single(
                await fixture.Configuration.GetPortalGoalsAsync(
                    fixture.TenantId,
                    fixture.RelationshipId,
                    CancellationToken.None
                )
            )
            .Goal;
        Assert.Equal("Know our position in Pune", revised.Goal);
        Assert.Contains("cafe", revised.Baseline);
        Assert.Equal(RelationshipConfigurationService.GetGoalVersion(revised), result.Body.Version);
        Assert.NotEqual(goalVersion, result.Body.Version);
        var history = await fixture.GoalHistory.ListAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            goal.GoalId,
            CancellationToken.None
        );
        Assert.Equal(2, history.Count);
        Assert.Equal("Know where we stand", history[0].Title);
        Assert.Equal("bakery", history[0].Parameters["BUSINESS_DOMAIN"]);
        Assert.Null(history[0].Reason);
        Assert.Equal("Know our position in Pune", history[1].Title);
        Assert.Equal("The location changed", history[1].Reason);
    }

    [Fact]
    public async Task ReviseGoal_KeepsTheTitleWhenNoneIsGiven()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();

        await fixture.Commands.ReviseGoalAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            goal.GoalId,
            Revise(await fixture.VersionAsync()),
            CancellationToken.None
        );

        var revised = Assert
            .Single(
                await fixture.Configuration.GetPortalGoalsAsync(
                    fixture.TenantId,
                    fixture.RelationshipId,
                    CancellationToken.None
                )
            )
            .Goal;
        Assert.Equal("Know where we stand", revised.Goal);
        Assert.Contains("Pune", revised.Baseline);
    }

    [Fact]
    public async Task ReviseGoal_DoesNotSnapshotAgainWhenTheHistoryAlreadyHoldsTheGoal()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var created = await fixture.Commands.CreateGoalAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            Create(await fixture.VersionAsync()),
            CancellationToken.None
        );
        var goalId = Guid.Parse(created.Body.ResourceRef!);

        await fixture.Commands.ReviseGoalAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            goalId,
            Revise(created.Body.Version),
            CancellationToken.None
        );

        var history = await fixture.GoalHistory.ListAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            goalId,
            CancellationToken.None
        );
        Assert.Equal(2, history.Count);
    }

    [Fact]
    public async Task ReviseGoal_StillSucceedsWhenTheHistoryCannotBeRead()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();
        fixture.GoalHistory.FailList = true;

        var result = await fixture.Commands.ReviseGoalAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            goal.GoalId,
            Revise(await fixture.VersionAsync()),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", result.Body.Status);
        var warning = Assert.Single(
            fixture.Logger.Entries,
            entry => entry.Level == LogLevel.Warning
        );
        Assert.Contains("history read failed", warning.Message);
    }

    [Fact]
    public async Task ReviseGoal_StillSucceedsWhenTheHistoryCannotBeWritten()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();
        fixture.GoalHistory.FailAppend = true;

        var result = await fixture.Commands.ReviseGoalAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            goal.GoalId,
            Revise(await fixture.VersionAsync()),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", result.Body.Status);
        Assert.Equal(2, fixture.Logger.Entries.Count(entry => entry.Level == LogLevel.Warning));
    }

    public static TheoryData<string> InvalidReviseRequests() =>
        new() { "blank-reason", "long-reason", "blank-title", "long-title", "null-parameters" };

    [Theory]
    [MemberData(nameof(InvalidReviseRequests))]
    public async Task ReviseGoal_RejectsAnInvalidRequest(string defect)
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();
        var version = await fixture.VersionAsync();
        var request = defect switch
        {
            "blank-reason" => Revise(version, reason: " "),
            "long-reason" => Revise(version, reason: new string('r', 501)),
            "blank-title" => Revise(version, title: " "),
            "long-title" => Revise(version, title: new string('t', 241)),
            _ => Revise(version) with { Parameters = null! },
        };

        var failure = await Refused(() =>
            fixture.Commands.ReviseGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                goal.GoalId,
                request,
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, failure.Code);
    }

    [Fact]
    public async Task ReviseGoal_IsRefusedForAnAudienceThatMayNotDecide()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();

        var failure = await Refused(() =>
            fixture.Commands.ReviseGoalAsync(
                fixture.Evaluator(),
                Guid.NewGuid(),
                goal.GoalId,
                Revise("relationship-1"),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
    }

    [Fact]
    public async Task ReviseGoal_ReportsAnUnknownGoalAsNotFound()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        await Assert.ThrowsAsync<KeyNotFoundException>(async () =>
            await fixture.Commands.ReviseGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Revise(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task ReviseGoal_IsRefusedWhenTheCustomerSawAnOlderGoalVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();

        var failure = await Refused(() =>
            fixture.Commands.ReviseGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                goal.GoalId,
                Revise("goal-older"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task ReviseGoal_IsUnavailableWhenTheAgentDeclaresNoExperience()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(withDeclaration: false);
        var goal = await fixture.AddGoalAsync();

        var failure = await Refused(async () =>
            await fixture.Commands.ReviseGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                goal.GoalId,
                Revise(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
    }

    [Fact]
    public async Task ReviseGoal_RefusesAGoalWhoseTypeTheAgentNoLongerDeclares()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync(goalTypeId: "RETIRED_GOAL_TYPE");

        var failure = await Refused(async () =>
            await fixture.Commands.ReviseGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                goal.GoalId,
                Revise(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("no longer declared", failure.Detail);
    }

    [Fact]
    public async Task ReviseGoal_RefusesAParameterTheGoalTypeDoesNotDeclare()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();

        var failure = await Refused(async () =>
            await fixture.Commands.ReviseGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                goal.GoalId,
                Revise(
                    await fixture.VersionAsync(),
                    parameters: new() { ["CONTENT_INPUTS"] = "photos" }
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("parameter is not declared", failure.Detail);
    }

    [Fact]
    public async Task ReviseGoal_MapsTheOwnersRefusalOnAStoppedRelationshipToAnUnprocessableChange()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var goal = await fixture.AddGoalAsync();
        await fixture.SetStateAsync(EmploymentRelationshipState.StoppedEmergency);

        var failure = await Refused(async () =>
            await fixture.Commands.ReviseGoalAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                goal.GoalId,
                Revise(await fixture.VersionAsync()),
                CancellationToken.None
            )
        );

        Assert.Equal(422, failure.Status);
        Assert.Contains("constitutional boundary", failure.Detail);
    }
}
