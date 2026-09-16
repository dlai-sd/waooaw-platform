// Implements: ADR-046 section 10.1 end-to-end business-operation matrix
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-076, C-083, C-084, C-085

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

internal sealed class RelationshipOwnerGatewayStub : IRelationshipWorkspaceOwnerGateway
{
    public ExecutionOwnerProjection? Execution { get; set; }
    public CommercialOwnerProjection? Commercial { get; set; }
    public RelationshipOwnerContext? LastContext { get; private set; }

    public Task<ExecutionOwnerProjection?> GetExecutionAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken)
    {
        LastContext = context;
        return Task.FromResult(Execution);
    }

    public Task<CommercialOwnerProjection?> GetCommercialAsync(
        RelationshipOwnerContext context, CancellationToken cancellationToken)
    {
        LastContext = context;
        return Task.FromResult(Commercial);
    }
}

public sealed class RelationshipWorkspaceControllerTests
{
    [Fact]
    public async Task Configuration_AlwaysReturnsOnboardAndInductInOrder()
    {
        var (controller, relationship, _, _) = await CreateControllerAsync();

        var configuration = Json(await controller.GetConfigurationAsync(
            relationship.RelationshipId, CancellationToken.None));
        var items = configuration.GetProperty("items").EnumerateArray().ToArray();

        Assert.Equal("ONBOARD", configuration.GetProperty("lifecyclePhase").GetString());
        Assert.Equal(2, items.Length);
        Assert.Equal("ONBOARD", items[0].GetProperty("stepKey").GetString());
        Assert.Equal("INDUCT", items[1].GetProperty("stepKey").GetString());
    }

    [Fact]
    public async Task Onboard_PersistsAndReplaysButConflictingReuseIsRejected()
    {
        var (controller, relationship, _, _) = await CreateControllerAsync();
        var key = Guid.NewGuid().ToString();
        var request = new RelationshipOnboardRequest("1.0.0", "Maya", "COMPACT", "ABSOLUTE", "DARK");

        var first = Json(await controller.UpdateOnboardAsync(
            relationship.RelationshipId, request, key, CancellationToken.None));
        var replay = Json(await controller.UpdateOnboardAsync(
            relationship.RelationshipId, request, key, CancellationToken.None));
        var conflict = Assert.IsType<ObjectResult>(await controller.UpdateOnboardAsync(
            relationship.RelationshipId, request with { PreferredAgentDisplayName = "Nora" }, key, CancellationToken.None));

        Assert.Equal("INDUCT", first.GetProperty("lifecyclePhase").GetString());
        Assert.Equal(first.GetProperty("items").ToString(), replay.GetProperty("items").ToString());
        Assert.Equal(409, conflict.StatusCode);
    }

    [Fact]
    public async Task Workspace_DoesNotExposeRelationshipToUnboundParticipant()
    {
        var (controller, relationship, _, _) = await CreateControllerAsync();
        controller.HttpContext.User = new ClaimsPrincipal(new ClaimsIdentity(
            [new Claim("participant_id", Guid.NewGuid().ToString())], "Test"));

        var result = Assert.IsType<ObjectResult>(await controller.GetConfigurationAsync(
            relationship.RelationshipId, CancellationToken.None));

        Assert.Equal(404, result.StatusCode);
    }

    [Fact]
    public async Task GoalsArePendingCustomerAndOperationsRemainLocked()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var goal = await configuration.SaveGoalAsync(
            relationship.TenantId, relationship.RelationshipId, "Increase bookings", "10 monthly",
            "Confirmed bookings", "15 monthly", "Customer records", "ACCEPTED", CancellationToken.None);
        await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "ACCEPTED", CancellationToken.None);

        var goals = Json(await controller.GetGoalsAsync(relationship.RelationshipId, CancellationToken.None));
        var projected = Assert.Single(goals.GetProperty("activeGoals").EnumerateArray());
        var operations = Json(await controller.GetOperationsAsync(relationship.RelationshipId, CancellationToken.None));

        Assert.Equal("PENDING_CUSTOMER", projected.GetProperty("verificationStatus").GetString());
        Assert.Equal("local-seo", projected.GetProperty("skillId").GetString());
        Assert.Equal("LOCKED", operations.GetProperty("eligibilityState").GetString());
        Assert.Equal(goal.GoalId, Assert.Single(operations.GetProperty("requiredGoalIds").EnumerateArray()).GetGuid());
        Assert.Empty(operations.GetProperty("verifiedGoalIds").EnumerateArray());
    }

    [Fact]
    public async Task VerifyGoal_CompletesReplaysAndUnlocksOperations()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var goal = await configuration.SaveGoalAsync(
            relationship.TenantId, relationship.RelationshipId, "Increase bookings", "10 monthly",
            "Confirmed bookings", "15 monthly", "Customer records", "ACCEPTED", CancellationToken.None);
        await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "ACCEPTED", CancellationToken.None);
        var key = Guid.NewGuid().ToString("D");
        var version = RelationshipConfigurationService.GetGoalVersion(goal);
        var command = JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0",
            expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = version,
            payload = new
            {
                commandKind = "VERIFY_GOAL",
                goalId = goal.GoalId,
                goalVersion = version,
                verificationDecision = "VERIFIED",
            },
        });

        var accepted = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, key, CancellationToken.None));
        var replay = Assert.IsType<OkObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, key, CancellationToken.None));
        var receipt = JsonSerializer.SerializeToElement(accepted.Value);
        var goals = Json(await controller.GetGoalsAsync(relationship.RelationshipId, CancellationToken.None));
        var operations = Json(await controller.GetOperationsAsync(relationship.RelationshipId, CancellationToken.None));
        var outcome = Json(await controller.GetCommandAsync(
            relationship.RelationshipId, receipt.GetProperty("commandId").GetGuid(), CancellationToken.None));

        Assert.Equal(202, accepted.StatusCode);
        Assert.True(JsonSerializer.SerializeToElement(replay.Value).GetProperty("replayed").GetBoolean());
        Assert.Equal("VERIFIED", Assert.Single(goals.GetProperty("activeGoals").EnumerateArray())
            .GetProperty("verificationStatus").GetString());
        Assert.Equal("ELIGIBLE", operations.GetProperty("eligibilityState").GetString());
        Assert.Equal(goal.GoalId, Assert.Single(operations.GetProperty("verifiedGoalIds").EnumerateArray()).GetGuid());
        Assert.Equal("COMPLETED", outcome.GetProperty("status").GetString());
    }

    [Fact]
    public async Task VerifyGoal_RequiresFreshAal3AndPreservesLockedStateForChangeRequest()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var goal = await configuration.SaveGoalAsync(
            relationship.TenantId, relationship.RelationshipId, "Increase bookings", null,
            "Confirmed bookings", null, null, "ACCEPTED", CancellationToken.None);
        await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "ACCEPTED", CancellationToken.None);
        var version = RelationshipConfigurationService.GetGoalVersion(goal);
        var command = JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0",
            expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = version,
            payload = new
            {
                commandKind = "VERIFY_GOAL",
                goalId = goal.GoalId,
                goalVersion = version,
                verificationDecision = "CHANGES_REQUESTED",
                correctionReason = "Clarify attribution.",
            },
        });
        ((ClaimsIdentity)controller.User.Identity!).RemoveClaim(controller.User.FindFirst("auth_time")!);
        ((ClaimsIdentity)controller.User.Identity!).AddClaim(new Claim(
            "auth_time", DateTimeOffset.UtcNow.AddMinutes(-6).ToUnixTimeSeconds().ToString()));

        var stale = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, Guid.NewGuid().ToString("D"), CancellationToken.None));
        Assert.Equal(423, stale.StatusCode);

        ((ClaimsIdentity)controller.User.Identity!).RemoveClaim(controller.User.FindFirst("auth_time")!);
        ((ClaimsIdentity)controller.User.Identity!).AddClaim(new Claim(
            "auth_time", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString()));
        var accepted = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, Guid.NewGuid().ToString("D"), CancellationToken.None));
        var operations = Json(await controller.GetOperationsAsync(relationship.RelationshipId, CancellationToken.None));

        Assert.Equal(202, accepted.StatusCode);
        Assert.Equal("LOCKED", operations.GetProperty("eligibilityState").GetString());
        Assert.Empty(operations.GetProperty("verifiedGoalIds").EnumerateArray());
    }

    [Fact]
    public async Task VerifyGoal_RejectsMalformedAndGoalChangePayloadsWithoutMutation()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var goal = await configuration.SaveGoalAsync(
            relationship.TenantId, relationship.RelationshipId, "Increase bookings", null,
            "Confirmed bookings", null, null, "ACCEPTED", CancellationToken.None);
        await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "ACCEPTED", CancellationToken.None);
        var version = RelationshipConfigurationService.GetGoalVersion(goal);
        var envelope = new
        {
            schemaVersion = "1.0",
            expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = version,
        };
        var invalidPayloads = new[]
        {
            JsonSerializer.SerializeToElement(new { envelope.schemaVersion, envelope.expectedWorkspaceVersion,
                envelope.expectedSubjectVersion, payload = new { commandKind = "VERIFY_GOAL", goalId = "invalid",
                    goalVersion = version, verificationDecision = "VERIFIED" } }),
            JsonSerializer.SerializeToElement(new { envelope.schemaVersion, envelope.expectedWorkspaceVersion,
                envelope.expectedSubjectVersion, payload = new { commandKind = "VERIFY_GOAL", goalId = goal.GoalId,
                    goalVersion = version, verificationDecision = "CHANGES_REQUESTED" } }),
            JsonSerializer.SerializeToElement(new { envelope.schemaVersion, envelope.expectedWorkspaceVersion,
                envelope.expectedSubjectVersion, payload = new { commandKind = "VERIFY_GOAL", goalId = goal.GoalId,
                    goalVersion = version, verificationDecision = "VERIFIED", correctionReason = "Not allowed" } }),
        };

        foreach (var invalid in invalidPayloads.Select(async payload => Assert.IsType<ObjectResult>(
                     await controller.SubmitCommandAsync(relationship.RelationshipId, payload,
                         Guid.NewGuid().ToString("D"), CancellationToken.None))))
        {
            Assert.Equal(400, (await invalid).StatusCode);
        }
        foreach (var commandKind in new[] { "AMEND_GOAL", "REPLACE_GOAL" })
        {
            var unsupported = JsonSerializer.SerializeToElement(new
            {
                envelope.schemaVersion,
                envelope.expectedWorkspaceVersion,
                envelope.expectedSubjectVersion,
                payload = new { commandKind },
            });
            var blocked = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
                relationship.RelationshipId, unsupported, Guid.NewGuid().ToString("D"), CancellationToken.None));
            Assert.Equal(423, blocked.StatusCode);
        }

        var operations = Json(await controller.GetOperationsAsync(relationship.RelationshipId, CancellationToken.None));
        Assert.Equal("LOCKED", operations.GetProperty("eligibilityState").GetString());
    }

    [Fact]
    public async Task VerifyGoal_MapsVersionAndIdempotencyConflicts()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var goal = await configuration.SaveGoalAsync(
            relationship.TenantId, relationship.RelationshipId, "Increase bookings", null,
            "Confirmed bookings", null, null, "ACCEPTED", CancellationToken.None);
        await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "ACCEPTED", CancellationToken.None);
        var version = RelationshipConfigurationService.GetGoalVersion(goal);
        JsonElement Command(string subjectVersion, string decision)
        {
            var payload = new Dictionary<string, object?>
            {
                ["commandKind"] = "VERIFY_GOAL",
                ["goalId"] = goal.GoalId,
                ["goalVersion"] = subjectVersion,
                ["verificationDecision"] = decision,
            };
            if (decision == "CHANGES_REQUESTED") payload["correctionReason"] = "Clarify attribution.";
            return JsonSerializer.SerializeToElement(new
            {
                schemaVersion = "1.0",
                expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
                expectedSubjectVersion = subjectVersion,
                payload,
            });
        }

        var stale = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command("goal-stale", "VERIFIED"),
            Guid.NewGuid().ToString("D"), CancellationToken.None));
        Assert.Equal(409, stale.StatusCode);

        var key = Guid.NewGuid().ToString("D");
        Assert.Equal(202, Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command(version, "VERIFIED"), key, CancellationToken.None)).StatusCode);
        var conflict = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command(version, "CHANGES_REQUESTED"), key, CancellationToken.None));
        Assert.Equal(409, conflict.StatusCode);
    }

    [Fact]
    public async Task AcceptSkill_CompletesReplaysAndRemainsRelationshipScoped()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var skill = await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", null,
            "NOT_GRANTED", "APPLICABLE", null, "PROPOSED", CancellationToken.None);
        var key = Guid.NewGuid().ToString("D");
        var command = JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0",
            expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = $"skill-{skill.UpdatedAt.UtcTicks}",
            payload = new
            {
                commandKind = "ACCEPT_SKILL",
                configurationId = skill.ConfigurationId,
                skillId = skill.SkillId,
                skillVersion = skill.SkillVersion,
            },
        });

        var accepted = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, key, CancellationToken.None));
        var replay = Assert.IsType<OkObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, key, CancellationToken.None));
        var receipt = JsonSerializer.SerializeToElement(accepted.Value);
        var outcome = Json(await controller.GetCommandAsync(
            relationship.RelationshipId, receipt.GetProperty("commandId").GetGuid(), CancellationToken.None));
        var skills = await configuration.GetPortalSkillsAsync(
            relationship.TenantId, relationship.RelationshipId, CancellationToken.None);

        Assert.Equal(202, accepted.StatusCode);
        Assert.True(JsonSerializer.SerializeToElement(replay.Value).GetProperty("replayed").GetBoolean());
        Assert.Equal("ACCEPT_SKILL", outcome.GetProperty("commandKind").GetString());
        Assert.Equal("COMPLETED", outcome.GetProperty("status").GetString());
        Assert.Equal("ACCEPTED", Assert.Single(skills).Status);
    }

    [Theory]
    [InlineData("SELECT_SKILL", "SELECTED")]
    [InlineData("UPDATE_SKILL", "SELECTED")]
    [InlineData("DEFER_SKILL", "DEFERRED")]
    public async Task SkillDecisions_MapToRelationshipLocalState(string commandKind, string expectedStatus)
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var skill = await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "market-research", "1.0.0", null,
            "NOT_GRANTED", "APPLICABLE", null, "PROPOSED", CancellationToken.None);
        var command = JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0", expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = RelationshipConfigurationService.GetSkillVersion(skill),
            payload = new { commandKind, configurationId = skill.ConfigurationId,
                skillId = skill.SkillId, skillVersion = skill.SkillVersion },
        });

        var accepted = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, Guid.NewGuid().ToString("D"), CancellationToken.None));
        var state = Assert.Single(await configuration.GetPortalSkillsAsync(
            relationship.TenantId, relationship.RelationshipId, CancellationToken.None));

        Assert.Equal(202, accepted.StatusCode);
        Assert.Equal(expectedStatus, state.Status);
    }

    [Fact]
    public async Task SkillDecision_RejectsStaleVersionAndChangedIdempotencyReuse()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var skill = await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "market-research", "1.0.0", null,
            "NOT_GRANTED", "APPLICABLE", null, "PROPOSED", CancellationToken.None);
        JsonElement Command(string version, string commandKind) => JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0", expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = version,
            payload = new { commandKind, configurationId = skill.ConfigurationId,
                skillId = skill.SkillId, skillVersion = skill.SkillVersion },
        });

        var stale = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command("skill-stale", "ACCEPT_SKILL"),
            Guid.NewGuid().ToString("D"), CancellationToken.None));
        Assert.Equal(409, stale.StatusCode);

        var key = Guid.NewGuid().ToString("D");
        var version = RelationshipConfigurationService.GetSkillVersion(skill);
        Assert.Equal(202, Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command(version, "ACCEPT_SKILL"), key, CancellationToken.None)).StatusCode);
        var conflict = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command(version, "DEFER_SKILL"), key, CancellationToken.None));
        Assert.Equal(409, conflict.StatusCode);
    }

    [Fact]
    public async Task UpdateSkill_MovesSelectionAndAcceptedSkillCannotBeReselected()
    {
        var (controller, relationship, _, configuration) = await CreateControllerAsync();
        var first = await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "market-research", "1.0.0", null,
            "NOT_GRANTED", "APPLICABLE", null, "SELECTED", CancellationToken.None);
        var second = await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", null,
            "NOT_GRANTED", "APPLICABLE", null, "PROPOSED", CancellationToken.None);
        JsonElement Command(RelationshipSkillConfiguration skill, string commandKind) => JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0", expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = RelationshipConfigurationService.GetSkillVersion(skill),
            payload = new { commandKind, configurationId = skill.ConfigurationId,
                skillId = skill.SkillId, skillVersion = skill.SkillVersion },
        });

        Assert.Equal(202, Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command(second, "UPDATE_SKILL"),
            Guid.NewGuid().ToString("D"), CancellationToken.None)).StatusCode);
        var moved = await configuration.GetPortalSkillsAsync(
            relationship.TenantId, relationship.RelationshipId, CancellationToken.None);
        Assert.Equal("PROPOSED", moved.Single(item => item.ConfigurationId == first.ConfigurationId).Status);
        Assert.Equal("SELECTED", moved.Single(item => item.ConfigurationId == second.ConfigurationId).Status);

        var selected = moved.Single(item => item.ConfigurationId == second.ConfigurationId);
        Assert.Equal(202, Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command(selected, "ACCEPT_SKILL"),
            Guid.NewGuid().ToString("D"), CancellationToken.None)).StatusCode);
        var accepted = Assert.Single(await configuration.GetPortalSkillsAsync(
            relationship.TenantId, relationship.RelationshipId, CancellationToken.None),
            item => item.ConfigurationId == second.ConfigurationId);
        var illegal = Assert.IsType<ObjectResult>(await controller.SubmitCommandAsync(
            relationship.RelationshipId, Command(accepted, "SELECT_SKILL"),
            Guid.NewGuid().ToString("D"), CancellationToken.None));
        Assert.Equal(409, illegal.StatusCode);
    }

    [Fact]
    public async Task BusinessOutcomesAreExplicitlyUnavailableWithoutOwnerEvidence()
    {
        var (controller, relationship, _, _) = await CreateControllerAsync();

        var outcomes = Json(await controller.GetBusinessOutcomesAsync(
            relationship.RelationshipId, CancellationToken.None));

        Assert.Equal("UNAVAILABLE", outcomes.GetProperty("currencyState").GetString());
        Assert.Empty(outcomes.GetProperty("items").EnumerateArray());
    }

    [Fact]
    public async Task AuthenticatedOwnerTruthReplacesUnavailablePlaceholders()
    {
        var (controller, relationship, gateway, _) = await CreateControllerAsync();
        var producedAt = DateTimeOffset.UtcNow;
        var workItemId = Guid.NewGuid();
        var invocationId = Guid.NewGuid();
        gateway.Execution = new ExecutionOwnerProjection("execution-7", "CURRENT", producedAt,
        [
            new ExecutionOwnerWorkItem(
                workItemId, relationship.AgentInstanceId, "MARKET_RESEARCH", "1.0.0",
                invocationId, 2, "SUCCEEDED", "Cited market research is ready.", "result-research-2", producedAt),
        ]);
        gateway.Commercial = new CommercialOwnerProjection(
            "commercial-9", "CURRENT", "INR 125", "INR 700 to INR 900", "BELOW_LIMIT", producedAt);

        var work = Json(await controller.GetWorkAsync(relationship.RelationshipId, CancellationToken.None));
        var results = Json(await controller.GetResultsAsync(relationship.RelationshipId, CancellationToken.None));
        var usage = Json(await controller.GetUsageBudgetAsync(relationship.RelationshipId, CancellationToken.None));

        Assert.Equal("CURRENT", work.GetProperty("currencyState").GetString());
        Assert.Equal("execution-7", work.GetProperty("provenance").GetProperty("sourceProjectionVersion").GetString());
        var workItem = Assert.Single(work.GetProperty("items").EnumerateArray());
        Assert.Equal(workItemId, workItem.GetProperty("itemId").GetGuid());
        Assert.Equal(relationship.AgentInstanceId, workItem.GetProperty("agentInstanceId").GetGuid());
        Assert.Equal("MARKET_RESEARCH", workItem.GetProperty("skillId").GetString());
        Assert.Equal(invocationId, workItem.GetProperty("invocationId").GetGuid());
        var outcome = Assert.Single(results.GetProperty("outcomes").EnumerateArray());
        Assert.Equal("result-research-2", outcome.GetProperty("attributionBasis").GetString());
        Assert.Equal(2, outcome.GetProperty("revision").GetInt32());
        Assert.Equal("CURRENT", usage.GetProperty("currencyState").GetString());
        Assert.Equal("INR 125", usage.GetProperty("actualAmount").GetString());
        Assert.Equal("commercial-9", usage.GetProperty("wbeProjectionVersion").GetString());
        Assert.Equal(relationship.TenantId, gateway.LastContext?.TenantId);
        Assert.Equal(relationship.RelationshipId, gateway.LastContext?.RelationshipId);
        Assert.Equal(relationship.AgentInstanceId, gateway.LastContext?.AgentInstanceId);
    }

    [Fact]
    public async Task MissingOwnerTruthRemainsExplicitlyUnavailable()
    {
        var (controller, relationship, _, _) = await CreateControllerAsync();

        var work = Json(await controller.GetWorkAsync(relationship.RelationshipId, CancellationToken.None));
        var usage = Json(await controller.GetUsageBudgetAsync(relationship.RelationshipId, CancellationToken.None));

        Assert.Equal("UNAVAILABLE", work.GetProperty("currencyState").GetString());
        Assert.Equal("unavailable-1", work.GetProperty("provenance").GetProperty("sourceProjectionVersion").GetString());
        Assert.Equal("UNAVAILABLE", usage.GetProperty("currencyState").GetString());
        Assert.Equal("Unavailable", usage.GetProperty("actualAmount").GetString());
    }

    [Fact]
    public async Task AggregatePreservesEachOwnerStateIndependently()
    {
        var (controller, relationship, gateway, _) = await CreateControllerAsync();
        gateway.Execution = new ExecutionOwnerProjection("execution-2", "STALE", DateTimeOffset.UtcNow);

        var workspace = Json(await controller.GetWorkspaceAsync(relationship.RelationshipId, CancellationToken.None));
        var sections = workspace.GetProperty("sections").EnumerateArray().ToDictionary(
            section => section.GetProperty("sectionType").GetString()!);

        Assert.Equal("STALE", sections["WORK"].GetProperty("currencyState").GetString());
        Assert.Equal("UNAVAILABLE", sections["USAGE_BUDGET"].GetProperty("currencyState").GetString());
        Assert.Equal("PARTIAL", workspace.GetProperty("snapshotState").GetString());
    }

    [Fact]
    public async Task AggregateComposesFiveStageLifecycleWithoutInventingRelationshipStates()
    {
        var (controller, relationship, _, _) = await CreateControllerAsync();

        var workspace = Json(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None));
        var profile = workspace.GetProperty("lifecycleProfile");
        var stages = profile.GetProperty("stages").EnumerateArray().ToArray();

        Assert.Equal(relationship.AgentInstanceId, profile.GetProperty("agentInstanceId").GetGuid());
        Assert.Equal(
            new[] { "ONBOARD", "INDUCT", "GOAL_VERIFICATION", "BUSINESS_OUTCOMES", "OPERATIONS" },
            stages.Select(stage => stage.GetProperty("stage").GetString()).ToArray());
        Assert.Equal("NOT_STARTED", stages[0].GetProperty("state").GetString());
        Assert.Equal("BLOCKED", stages[^1].GetProperty("state").GetString());
        Assert.NotEmpty(stages[^1].GetProperty("blockerReasons").EnumerateArray());
    }

    [Fact]
    public async Task AggregateProjectsEachLifecycleProgressionFromAuthoritativeInputs()
    {
        var (controller, relationship, gateway, configuration) = await CreateControllerAsync();

        await controller.UpdateOnboardAsync(
            relationship.RelationshipId,
            new RelationshipOnboardRequest("1.0.0", "Maya", "COMPACT", "ABSOLUTE", "DARK"),
            Guid.NewGuid().ToString("D"), CancellationToken.None);
        var onboarded = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None));
        Assert.Equal("VERIFIED", onboarded[0].GetProperty("state").GetString());
        Assert.Equal("NOT_STARTED", onboarded[1].GetProperty("state").GetString());

        await ConfirmContextAsync(configuration, relationship, "NAME");
        var partialInduction = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None));
        var partialConfiguration = Json(await controller.GetConfigurationAsync(
            relationship.RelationshipId, CancellationToken.None));
        Assert.Equal("IN_PROGRESS", partialInduction[1].GetProperty("state").GetString());
        Assert.Equal("INDUCT", partialConfiguration.GetProperty("lifecyclePhase").GetString());
        Assert.Equal("IN_PROGRESS", partialConfiguration.GetProperty("items")[1].GetProperty("state").GetString());
        Assert.Equal("context-1", partialConfiguration.GetProperty("items")[1]
            .GetProperty("confirmedContextVersion").GetString());

        await ConfirmContextAsync(configuration, relationship, "LOCATION");
        await ConfirmContextAsync(configuration, relationship, "BUSINESS_NATURE");
        var inducted = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None));
        var completedConfiguration = Json(await controller.GetConfigurationAsync(
            relationship.RelationshipId, CancellationToken.None));
        Assert.Equal("VERIFIED", inducted[1].GetProperty("state").GetString());
        Assert.Equal("NOT_STARTED", inducted[2].GetProperty("state").GetString());
        Assert.Equal("GOAL_VERIFICATION", completedConfiguration.GetProperty("lifecyclePhase").GetString());
        Assert.Equal("VERIFIED", completedConfiguration.GetProperty("items")[1].GetProperty("state").GetString());

        var goal = await configuration.SaveGoalAsync(
            relationship.TenantId, relationship.RelationshipId, "Increase bookings", "10 monthly",
            "Confirmed bookings", "15 monthly", "Customer records", "ACCEPTED", CancellationToken.None);
        await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "ACCEPTED", CancellationToken.None);
        var pendingGoal = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None));
        Assert.Equal("READY_FOR_CONFIRMATION", pendingGoal[2].GetProperty("state").GetString());
        Assert.Equal("BLOCKED", pendingGoal[3].GetProperty("state").GetString());

        var goalVersion = RelationshipConfigurationService.GetGoalVersion(goal);
        var command = JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0",
            expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = goalVersion,
            payload = new
            {
                commandKind = "VERIFY_GOAL",
                goalId = goal.GoalId,
                goalVersion,
                verificationDecision = "VERIFIED",
            },
        });
        await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, Guid.NewGuid().ToString("D"), CancellationToken.None);

        var ownersUnavailable = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None))[^1];
        Assert.Equal("BLOCKED", ownersUnavailable.GetProperty("state").GetString());

        gateway.Execution = new ExecutionOwnerProjection("execution-current", "CURRENT", DateTimeOffset.UtcNow);
        var commercialUnavailable = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None))[^1];
        Assert.Equal("BLOCKED", commercialUnavailable.GetProperty("state").GetString());

        gateway.Commercial = new CommercialOwnerProjection(
            "commercial-current", "CURRENT", "INR 0", "INR 0", "WITHIN_LIMIT", DateTimeOffset.UtcNow);

        var verified = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None));
        Assert.Equal("VERIFIED", verified[2].GetProperty("state").GetString());
        Assert.Equal("VERIFIED", verified[3].GetProperty("state").GetString());
        Assert.Equal("BLOCKED", verified[4].GetProperty("state").GetString());
        Assert.Equal("RECORDED", verified[3].GetProperty("evidenceState").GetString());
    }

    private static async Task ConfirmContextAsync(
        RelationshipConfigurationService configuration,
        EmploymentRelationship relationship,
        string fieldType)
    {
        await configuration.ConfirmContextAsync(
            relationship.TenantId, relationship.RelationshipId, relationship.InitiatingParticipantId,
            fieldType, JsonSerializer.SerializeToElement("confirmed"), "STATED", null, null,
            Guid.NewGuid(), CancellationToken.None);
    }

    private static JsonElement[] Stages(IActionResult result) =>
        Json(result).GetProperty("lifecycleProfile").GetProperty("stages").EnumerateArray().ToArray();

    [Fact]
    public async Task AggregateVerifiesOperationsOnlyWhenEveryOwnerDependencyIsCurrent()
    {
        var (controller, relationship, gateway, configuration) = await CreateControllerAsync(
            EmploymentRelationshipState.Active);
        await controller.UpdateOnboardAsync(
            relationship.RelationshipId,
            new RelationshipOnboardRequest("1.0.0", "Maya", "COMPACT", "ABSOLUTE", "DARK"),
            Guid.NewGuid().ToString("D"), CancellationToken.None);
        foreach (var fieldType in new[] { "NAME", "LOCATION", "BUSINESS_NATURE" })
            await ConfirmContextAsync(configuration, relationship, fieldType);
        var goal = await configuration.SaveGoalAsync(
            relationship.TenantId, relationship.RelationshipId, "Increase bookings", "10 monthly",
            "Confirmed bookings", "15 monthly", "Customer records", "ACCEPTED", CancellationToken.None);
        await configuration.SaveSkillAsync(
            relationship.TenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "ACCEPTED", CancellationToken.None);
        var goalVersion = RelationshipConfigurationService.GetGoalVersion(goal);
        var command = JsonSerializer.SerializeToElement(new
        {
            schemaVersion = "1.0",
            expectedWorkspaceVersion = $"relationship-{relationship.StateVersion}",
            expectedSubjectVersion = goalVersion,
            payload = new
            {
                commandKind = "VERIFY_GOAL",
                goalId = goal.GoalId,
                goalVersion,
                verificationDecision = "VERIFIED",
            },
        });
        await controller.SubmitCommandAsync(
            relationship.RelationshipId, command, Guid.NewGuid().ToString("D"), CancellationToken.None);
        gateway.Execution = new ExecutionOwnerProjection("execution-current", "CURRENT", DateTimeOffset.UtcNow);
        gateway.Commercial = new CommercialOwnerProjection(
            "commercial-current", "CURRENT", "INR 0", "INR 0", "WITHIN_LIMIT", DateTimeOffset.UtcNow);

        var operations = Stages(await controller.GetWorkspaceAsync(
            relationship.RelationshipId, CancellationToken.None))[^1];

        Assert.Equal("VERIFIED", operations.GetProperty("state").GetString());
        Assert.Equal("RECORDED", operations.GetProperty("evidenceState").GetString());
        Assert.Equal($"relationship-{relationship.StateVersion}", operations.GetProperty("outputRevision").GetString());
        Assert.Empty(operations.GetProperty("blockerReasons").EnumerateArray());
        Assert.Equal("Continue governed work.", operations.GetProperty("nextAuthorizedAction").GetString());
    }

    private static async Task<(RelationshipWorkspaceController Controller, EmploymentRelationship Relationship,
        RelationshipOwnerGatewayStub Gateway, RelationshipConfigurationService Configuration)> CreateControllerAsync(
        EmploymentRelationshipState? state = null)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await service.AdmitAsync(
            tenantId, participantId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        if (state.HasValue)
        {
            await using var db = factory.CreateDbContext();
            var stored = await db.EmploymentRelationships.SingleAsync(item =>
                item.TenantId == tenantId && item.RelationshipId == admitted.Relationship.RelationshipId);
            stored.State = state.Value;
            await db.SaveChangesAsync();
            admitted.Relationship.State = state.Value;
        }
        var gateway = new RelationshipOwnerGatewayStub();
        var configuration = new RelationshipConfigurationService(
            factory, new RecordingRelationshipConstitutionalGateway());
        var httpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                [
                    new Claim("participant_id", participantId.ToString()),
                    new Claim("participant_role", "EMPLOYER"),
                    new Claim("authentication_assurance", "AAL3_FRESH"),
                    new Claim("auth_time", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString()),
                ],
                "Test")),
            TraceIdentifier = Guid.NewGuid().ToString(),
        };
        httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        var controller = new RelationshipWorkspaceController(service, gateway, configuration: configuration)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
        return (controller, admitted.Relationship, gateway, configuration);
    }

    private static JsonElement Json(IActionResult result)
    {
        var ok = Assert.IsType<OkObjectResult>(result);
        return JsonSerializer.SerializeToElement(ok.Value);
    }
}