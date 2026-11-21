// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchCommandServiceCapabilityTests
{
    private const string OtherSkill = "SOCIAL_CONTENT_CREATION_AND_PUBLISHING";

    private static WorkbenchCapabilityCommandRequest Capability(
        string version,
        string command,
        string? approvalMode = null,
        string schema = "1.0"
    ) => new(schema, version, command, approvalMode);

    private static async Task<RelationshipSkillConfiguration> StoredSkillAsync(
        WorkbenchCommandServiceFixture fixture,
        string skillId = WorkbenchCommandServiceFixture.SkillId
    ) =>
        (
            await fixture.Configuration.GetPortalSkillsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        ).Single(item => item.SkillId == skillId);

    [Theory]
    [InlineData("ENABLE", "ACCEPTED", "COMPLETED", false)]
    [InlineData("PAUSE", "DEFERRED", "COMPLETED", false)]
    public async Task Capability_EnableAndPauseAreDecidedByTheSkillOwner(
        string command,
        string expectedStatus,
        string expectedOutcome,
        bool expectsMessage
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();
        var skill = await StoredSkillAsync(fixture);
        var context = fixture.Employer();

        var result = await fixture.Commands.CommandCapabilityAsync(
            context,
            Guid.NewGuid(),
            WorkbenchCommandServiceFixture.SkillId,
            Capability(RelationshipConfigurationService.GetSkillVersion(skill), command),
            CancellationToken.None
        );

        Assert.Equal(expectedOutcome, result.Body.Outcome);
        Assert.NotNull(result.Body.OperationRef);
        Assert.Equal(expectsMessage, result.Body.Message is not null);
        Assert.Equal(context.CorrelationId, result.Body.CorrelationId);
        Assert.Equal(expectedStatus, (await StoredSkillAsync(fixture)).Status);
    }

    [Fact]
    public async Task Capability_ResumeSelectsThePausedSkillAndSaysItNeedsTheCustomersApproval()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync(status: "DEFERRED");
        var skill = await StoredSkillAsync(fixture);

        var result = await fixture.Commands.CommandCapabilityAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            WorkbenchCommandServiceFixture.SkillId,
            Capability(await fixture.VersionAsync(), "RESUME"),
            CancellationToken.None
        );

        Assert.Equal("NEEDS_APPROVAL", result.Body.Outcome);
        Assert.Contains("approval", result.Body.Message);
        Assert.Equal("SELECTED", (await StoredSkillAsync(fixture)).Status);
        Assert.NotEqual(
            RelationshipConfigurationService.GetSkillVersion(skill),
            RelationshipConfigurationService.GetSkillVersion(await StoredSkillAsync(fixture))
        );
    }

    [Fact]
    public async Task Capability_AnEvaluatorMayResolveToo()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();

        var result = await fixture.Commands.CommandCapabilityAsync(
            fixture.Evaluator(),
            Guid.NewGuid(),
            WorkbenchCommandServiceFixture.SkillId,
            Capability(await fixture.VersionAsync(), "ENABLE"),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Outcome);
    }

    [Fact]
    public async Task Capability_ReplaysTheSameCommandWithoutDecidingTwice()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();
        var key = Guid.NewGuid();
        var request = Capability(await fixture.VersionAsync(), "ENABLE");

        var first = await fixture.Commands.CommandCapabilityAsync(
            fixture.Employer(),
            key,
            WorkbenchCommandServiceFixture.SkillId,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.CommandCapabilityAsync(
            fixture.Employer(),
            key,
            WorkbenchCommandServiceFixture.SkillId,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
    }

    [Theory]
    [InlineData("RUN_NOW", null, "cannot be run on request")]
    [InlineData("CHANGE_APPROVAL_MODE", "AUTO", "cannot be changed here")]
    public async Task Capability_RefusesTheCommandsNoOwnerTakes(
        string command,
        string? mode,
        string detail
    )
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                WorkbenchCommandServiceFixture.SkillId,
                Capability(await fixture.VersionAsync(), command, mode),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains(detail, failure.Detail);
        Assert.Equal("PROPOSED", (await StoredSkillAsync(fixture)).Status);
    }

    public static TheoryData<string, string> InvalidCapabilityRequests() =>
        new()
        {
            { "schema", "ENABLE" },
            { "blank-skill", "ENABLE" },
            { "long-skill", "ENABLE" },
            { "unknown-command", "LAUNCH" },
            { "missing-mode", "CHANGE_APPROVAL_MODE" },
            { "long-mode", "CHANGE_APPROVAL_MODE" },
        };

    [Theory]
    [MemberData(nameof(InvalidCapabilityRequests))]
    public async Task Capability_RejectsAnInvalidRequest(string defect, string command)
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var skillId = defect switch
        {
            "blank-skill" => " ",
            "long-skill" => new string('s', 161),
            _ => WorkbenchCommandServiceFixture.SkillId,
        };
        var request = defect switch
        {
            "schema" => Capability("relationship-1", command, schema: "9.9"),
            "long-mode" => Capability("relationship-1", command, new string('m', 161)),
            _ => Capability("relationship-1", command),
        };

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                skillId,
                request,
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.RequestInvalid, failure.Code);
    }

    [Fact]
    public async Task Capability_IsRefusedForARoleThatMayNotResolve()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CommandCapabilityAsync(
                fixture.Manager(),
                Guid.NewGuid(),
                WorkbenchCommandServiceFixture.SkillId,
                Capability("relationship-1", "ENABLE"),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
        Assert.Equal(WorkbenchCommandService.RoleDetail, failure.Detail);
    }

    [Fact]
    public async Task Capability_IsRefusedOnAStoppedRelationship()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(
            EmploymentRelationshipState.StoppedEmergency
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                WorkbenchCommandServiceFixture.SkillId,
                Capability(await fixture.VersionAsync(), "ENABLE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
    }

    [Fact]
    public async Task Capability_IsUnavailableWithoutAnExperienceDeclaration()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync(withDeclaration: false);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                WorkbenchCommandServiceFixture.SkillId,
                Capability(await fixture.VersionAsync(), "ENABLE"),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
    }

    [Fact]
    public async Task Capability_ReportsASkillTheAgentDoesNotDeclareAsNotFound()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        await Assert.ThrowsAsync<KeyNotFoundException>(async () =>
            await fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                "TIME_TRAVEL",
                Capability(await fixture.VersionAsync(), "ENABLE"),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task Capability_ReportsADeclaredSkillThatWasNeverConfiguredAsNotFound()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<KeyNotFoundException>(async () =>
            await fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                OtherSkill,
                Capability(await fixture.VersionAsync(), "ENABLE"),
                CancellationToken.None
            )
        );

        Assert.Contains("not configured", failure.Message);
    }

    [Fact]
    public async Task Capability_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                WorkbenchCommandServiceFixture.SkillId,
                Capability("skill-older", "ENABLE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task Capability_MapsTheOwnersStateRefusalToAVersionConflict()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();
        var version = await fixture.VersionAsync();
        await fixture.Commands.CommandCapabilityAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            WorkbenchCommandServiceFixture.SkillId,
            Capability(version, "ENABLE"),
            CancellationToken.None
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                WorkbenchCommandServiceFixture.SkillId,
                Capability(version, "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task Capability_MapsAnIdempotencyKeyReusedForAnotherDecisionToAConflict()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();
        await fixture.AddSkillAsync(OtherSkill);
        var key = Guid.NewGuid();
        var version = await fixture.VersionAsync();
        await fixture.Commands.CommandCapabilityAsync(
            fixture.Employer(),
            key,
            WorkbenchCommandServiceFixture.SkillId,
            Capability(version, "ENABLE"),
            CancellationToken.None
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.CommandCapabilityAsync(
                fixture.Evaluator(),
                key,
                OtherSkill,
                Capability(version, "PAUSE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.IdempotencyConflict, failure.Code);
    }

    [Fact]
    public async Task Capability_MapsAnOwnerOutageToUnavailableAndChangesNothing()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await fixture.AddSkillAsync();
        fixture.Constitutional.FailNext = true;

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.CommandCapabilityAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                WorkbenchCommandServiceFixture.SkillId,
                Capability(await fixture.VersionAsync(), "ENABLE"),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.Unavailable, failure.Code);
        Assert.Equal("PROPOSED", (await StoredSkillAsync(fixture)).Status);
    }
}

public sealed class WorkbenchCommandServiceDecisionTests
{
    private static ResolveWorkbenchDecisionRequest Resolve(
        string version,
        string resolution,
        string? note = null,
        string schema = "1.0"
    ) => new(schema, version, resolution, note);

    private static async Task<(Guid GoalId, Guid SkillDecisionId)> SeedAsync(
        WorkbenchCommandServiceFixture fixture
    )
    {
        var goal = await fixture.AddGoalAsync();
        var skill = await fixture.Configuration.GetPortalSkillsAsync(
            fixture.TenantId,
            fixture.RelationshipId,
            CancellationToken.None
        );
        return (goal.GoalId, skill.Single().ConfigurationId);
    }

    [Fact]
    public async Task Resolve_ApprovingASkillDecisionLetsTheSkillOwnerAcceptIt()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);
        var context = fixture.Employer();

        var result = await fixture.Commands.ResolveDecisionAsync(
            context,
            Guid.NewGuid(),
            skillDecision,
            Resolve(await fixture.VersionAsync(), "APPROVE"),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(skillDecision.ToString("D"), result.Body.ResourceRef);
        Assert.Equal(context.CorrelationId, result.Body.CorrelationId);
        var skill = Assert.Single(
            await fixture.Configuration.GetPortalSkillsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.Equal("ACCEPTED", skill.Status);
    }

    [Fact]
    public async Task Resolve_DecliningASkillDecisionDefersTheSkill()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);

        var result = await fixture.Commands.ResolveDecisionAsync(
            fixture.Evaluator(),
            Guid.NewGuid(),
            skillDecision,
            Resolve(await fixture.VersionAsync(), "DECLINE", "  not yet "),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        var skill = Assert.Single(
            await fixture.Configuration.GetPortalSkillsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.Equal("DEFERRED", skill.Status);
    }

    [Fact]
    public async Task Resolve_DeferringLeavesTheOwnersUntouchedAndStillAnswersCompleted()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);
        var constitutionalCalls = fixture.Constitutional.CallCount;

        var result = await fixture.Commands.ResolveDecisionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            skillDecision,
            Resolve(await fixture.VersionAsync(), "DEFER"),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        Assert.Equal(constitutionalCalls, fixture.Constitutional.CallCount);
        Assert.Equal(
            "PROPOSED",
            Assert
                .Single(
                    await fixture.Configuration.GetPortalSkillsAsync(
                        fixture.TenantId,
                        fixture.RelationshipId,
                        CancellationToken.None
                    )
                )
                .Status
        );
    }

    [Fact]
    public async Task Resolve_AcceptsTheSubjectVersionAsTheExpectedVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);
        var skill = Assert.Single(
            await fixture.Configuration.GetPortalSkillsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );

        var result = await fixture.Commands.ResolveDecisionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            skillDecision,
            Resolve(RelationshipConfigurationService.GetSkillVersion(skill), "APPROVE"),
            CancellationToken.None
        );

        Assert.Equal(RelationshipConfigurationService.GetSkillVersion(skill), result.Body.Version);
    }

    [Fact]
    public async Task Resolve_ApprovingAGoalDecisionVerifiesTheGoal()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (goalId, _) = await SeedAsync(fixture);

        var result = await fixture.Commands.ResolveDecisionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            goalId,
            Resolve(await fixture.VersionAsync(), "APPROVE"),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        var portal = Assert.Single(
            await fixture.Configuration.GetPortalGoalsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.Equal("VERIFIED", portal.CurrentDecision!.Decision);
        Assert.Equal(result.Body.OperationRef, portal.CurrentDecision.DecisionId);
    }

    [Fact]
    public async Task Resolve_DecliningAGoalDecisionRecordsTheRequestedChange()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (goalId, _) = await SeedAsync(fixture);

        var result = await fixture.Commands.ResolveDecisionAsync(
            fixture.Employer(),
            Guid.NewGuid(),
            goalId,
            Resolve(await fixture.VersionAsync(), "DECLINE", " Aim for June "),
            CancellationToken.None
        );

        Assert.Equal("COMPLETED", result.Body.Status);
        var portal = Assert.Single(
            await fixture.Configuration.GetPortalGoalsAsync(
                fixture.TenantId,
                fixture.RelationshipId,
                CancellationToken.None
            )
        );
        Assert.Equal("CHANGES_REQUESTED", portal.CurrentDecision!.Decision);
        Assert.Contains("Aim for June", portal.CurrentDecision.CorrectionReason);
    }

    [Fact]
    public async Task Resolve_AGoalChangeRequestNeedsANote()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (goalId, _) = await SeedAsync(fixture);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ResolveDecisionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                goalId,
                Resolve(await fixture.VersionAsync(), "DECLINE"),
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
        Assert.Contains("note is required", failure.Detail);
    }

    [Fact]
    public async Task Resolve_ReplaysTheSameCommandWithoutDecidingTwice()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);
        var key = Guid.NewGuid();
        var request = Resolve(await fixture.VersionAsync(), "APPROVE");

        var first = await fixture.Commands.ResolveDecisionAsync(
            fixture.Employer(),
            key,
            skillDecision,
            request,
            CancellationToken.None
        );
        var second = await fixture.Commands.ResolveDecisionAsync(
            fixture.Employer(),
            key,
            skillDecision,
            request,
            CancellationToken.None
        );

        Assert.True(second.Replayed);
        Assert.Equal(first.Body.OperationRef, second.Body.OperationRef);
    }

    [Theory]
    [InlineData("schema")]
    [InlineData("resolution")]
    [InlineData("blank-note")]
    [InlineData("long-note")]
    public async Task Resolve_RejectsAnInvalidRequest(string defect)
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var request = defect switch
        {
            "schema" => Resolve("relationship-1", "APPROVE", schema: "2.0"),
            "resolution" => Resolve("relationship-1", "MAYBE"),
            "blank-note" => Resolve("relationship-1", "DECLINE", " "),
            _ => Resolve("relationship-1", "DECLINE", new string('n', 501)),
        };

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ResolveDecisionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                request,
                CancellationToken.None
            )
        );

        Assert.Equal(400, failure.Status);
    }

    [Fact]
    public async Task Resolve_IsRefusedForARoleThatMayNotResolve()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ResolveDecisionAsync(
                fixture.Manager(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Resolve("relationship-1", "APPROVE"),
                CancellationToken.None
            )
        );

        Assert.Equal(403, failure.Status);
    }

    [Fact]
    public async Task Resolve_IsRefusedOnAStoppedRelationship()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);
        await fixture.SetStateAsync(EmploymentRelationshipState.StoppedEmergency);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ResolveDecisionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                skillDecision,
                Resolve(await fixture.VersionAsync(), "APPROVE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
    }

    [Fact]
    public async Task Resolve_ReportsADecisionThatIsNotPendingAsNotFound()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        await SeedAsync(fixture);

        await Assert.ThrowsAsync<KeyNotFoundException>(async () =>
            await fixture.Commands.ResolveDecisionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                Resolve(await fixture.VersionAsync(), "APPROVE"),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task Resolve_IsRefusedWhenTheCustomerSawAnOlderVersion()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ResolveDecisionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                skillDecision,
                Resolve("skill-older", "APPROVE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.VersionConflict, failure.Code);
    }

    [Fact]
    public async Task Resolve_MapsAnIdempotencyKeyReusedForAnotherDecisionToAConflict()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var first = await fixture.AddSkillAsync();
        var second = await fixture.AddSkillAsync("SOCIAL_CONTENT_CREATION_AND_PUBLISHING");
        var key = Guid.NewGuid();
        var version = await fixture.VersionAsync();
        await fixture.Commands.ResolveDecisionAsync(
            fixture.Employer(),
            key,
            first.ConfigurationId,
            Resolve(version, "APPROVE"),
            CancellationToken.None
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            fixture.Commands.ResolveDecisionAsync(
                fixture.Evaluator(),
                key,
                second.ConfigurationId,
                Resolve(version, "DECLINE"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.IdempotencyConflict, failure.Code);
    }

    [Fact]
    public async Task Resolve_MapsAnOwnerOutageToUnavailable()
    {
        var fixture = await WorkbenchCommandServiceFixture.CreateAsync();
        var (_, skillDecision) = await SeedAsync(fixture);
        fixture.Constitutional.FailNext = true;

        var failure = await Assert.ThrowsAsync<WorkbenchException>(async () =>
            await fixture.Commands.ResolveDecisionAsync(
                fixture.Employer(),
                Guid.NewGuid(),
                skillDecision,
                Resolve(await fixture.VersionAsync(), "APPROVE"),
                CancellationToken.None
            )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.Unavailable, failure.Code);
    }
}
