// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md Sections 10 and 17 SIM-095-14/15
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-079

using Microsoft.EntityFrameworkCore;
using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class PerformanceReviewServiceTests
{
    [Fact]
    public async Task AppendsImmutableSevenDimensionRevisionsWithSourceLineage()
    {
        var fixture = await CreateFixtureAsync();
        var service = new PerformanceReviewService(
            fixture.Factory, new RecordingRelationshipConstitutionalGateway());

        var first = await service.AppendAsync(fixture.TenantId, fixture.RelationshipId,
            "CUSTOMER_PROFILING", "1.0.0", Draft("CONTINUE_CURRENT_MANDATE"), CancellationToken.None);
        var second = await service.AppendAsync(fixture.TenantId, fixture.RelationshipId,
            "CUSTOMER_PROFILING", "1.0.0", Draft("REASSESSMENT_REQUIRED"), CancellationToken.None);
        var projected = await service.ListAsync(
            fixture.TenantId, fixture.RelationshipId, CancellationToken.None);

        Assert.Equal(1, first.Revision);
        Assert.Equal(2, second.Revision);
        Assert.Equal(2, projected.Count);
        Assert.Equal("DELIVERED", second.WorkDelivery.State);
        Assert.Equal("GOOD", second.AgentQuality.State);
        Assert.Equal("POOR", second.CustomerBusinessOutcome.State);
        Assert.Equal("No causal guarantee", second.CustomerBusinessOutcome.AttributionLimits);
        Assert.Equal("CUSTOMER_DISPUTED", second.CustomerAssessment.State);
        Assert.Equal("UNCHANGED", second.TrustAutonomy.State);
        Assert.Equal("pr-17", second.SourceVersions["professionalRuntime"]);
        Assert.True(second.ReassessmentRequired);
        Assert.NotEqual(first.ReviewId, second.ReviewId);
        Assert.NotEqual(first.EvidenceId, second.EvidenceId);
        await using var alertDb = fixture.Factory.CreateDbContext();
        Assert.Single(await alertDb.CustomerAlerts.Where(value => value.RelationshipId == fixture.RelationshipId).ToListAsync());
    }

    [Fact]
    public async Task RecordsExactCustomerDecisionReplaysAndProjectsReassessment()
    {
        var fixture = await CreateFixtureAsync();
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var service = new PerformanceReviewService(fixture.Factory, gateway);
        var review = await service.AppendAsync(fixture.TenantId, fixture.RelationshipId,
            "CUSTOMER_PROFILING", "1.0.0", Draft("REASSESSMENT_REQUIRED"), CancellationToken.None);
        var key = Guid.NewGuid();
        var correlationId = Guid.NewGuid();
        var hash = new string('a', 64);

        var first = await service.RespondAsync(
            fixture.TenantId, fixture.RelationshipId, fixture.ParticipantId, review.ReviewId,
            review.Revision, "REQUEST_REASSESSMENT", "The outcome requires a revised plan.",
            key, hash, correlationId, CancellationToken.None);
        var replay = await service.RespondAsync(
            fixture.TenantId, fixture.RelationshipId, fixture.ParticipantId, review.ReviewId,
            review.Revision, "REQUEST_REASSESSMENT", "The outcome requires a revised plan.",
            key, hash, correlationId, CancellationToken.None);
        var projected = Assert.Single(await service.ListAsync(
            fixture.TenantId, fixture.RelationshipId, CancellationToken.None));

        Assert.False(first.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(first.Response.ResponseId, replay.Response.ResponseId);
        Assert.Equal(1, gateway.CallCount);
        Assert.Equal("RELATIONSHIP_PERFORMANCE_REVIEW_RESPONSE", gateway.LastActionType);
        var constitutionalParameters = JsonSerializer.Serialize(gateway.LastActionParameters);
        Assert.Contains("reasonHash", constitutionalParameters);
        Assert.DoesNotContain("The outcome requires a revised plan.", constitutionalParameters);
        Assert.Contains(fixture.ParticipantId.ToString(), constitutionalParameters, StringComparison.OrdinalIgnoreCase);
        Assert.Equal("REQUEST_REASSESSMENT", projected.CustomerResponse?.Decision);
        Assert.True(projected.ReassessmentRequired);
        await Assert.ThrowsAsync<PerformanceReviewConflictException>(() => service.RespondAsync(
            fixture.TenantId, fixture.RelationshipId, fixture.ParticipantId, review.ReviewId,
            review.Revision, "DISPUTE_ASSESSMENT", "Different request.", key, new string('b', 64),
            Guid.NewGuid(), CancellationToken.None));
        await Assert.ThrowsAsync<PerformanceReviewConflictException>(() => service.RespondAsync(
            fixture.TenantId, fixture.RelationshipId, Guid.NewGuid(), review.ReviewId,
            review.Revision, "REQUEST_REASSESSMENT", "The outcome requires a revised plan.",
            key, hash, Guid.NewGuid(), CancellationToken.None));
    }

    [Fact]
    public async Task RejectsSelfPromotionAndCrossTenantProjectionWithoutMutation()
    {
        var fixture = await CreateFixtureAsync();
        var service = new PerformanceReviewService(
            fixture.Factory, new RecordingRelationshipConstitutionalGateway());

        await Assert.ThrowsAsync<PerformanceReviewInvalidException>(() => service.AppendAsync(
            fixture.TenantId, fixture.RelationshipId, "CUSTOMER_PROFILING", "1.0.0",
            Draft("PROMOTE_OWN_PROMPT"), CancellationToken.None));
        Assert.Empty(await service.ListAsync(fixture.TenantId, fixture.RelationshipId, CancellationToken.None));
        Assert.Empty(await service.ListAsync(Guid.NewGuid(), fixture.RelationshipId, CancellationToken.None));
    }

    [Fact]
    public async Task DoesNotPersistResponseWhenConstitutionalEvidenceIsUnavailable()
    {
        var fixture = await CreateFixtureAsync();
        var gateway = new RecordingRelationshipConstitutionalGateway { FailNext = true };
        var service = new PerformanceReviewService(fixture.Factory, gateway);
        var review = await service.AppendAsync(fixture.TenantId, fixture.RelationshipId,
            "CUSTOMER_PROFILING", "1.0.0", Draft("REASSESSMENT_REQUIRED"), CancellationToken.None);

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.RespondAsync(
            fixture.TenantId, fixture.RelationshipId, fixture.ParticipantId, review.ReviewId,
            review.Revision, "REQUEST_REASSESSMENT", "Reassess this outcome.", Guid.NewGuid(),
            new string('a', 64), Guid.NewGuid(), CancellationToken.None));

        Assert.Null(Assert.Single(await service.ListAsync(
            fixture.TenantId, fixture.RelationshipId, CancellationToken.None)).CustomerResponse);
    }

    [Theory]
    [InlineData("skill")]
    [InlineData("version")]
    [InlineData("policy")]
    [InlineData("period")]
    [InlineData("sources")]
    [InlineData("recommendation")]
    [InlineData("evidence")]
    [InlineData("dimension-state")]
    [InlineData("dimension-summary")]
    [InlineData("dimension-evidence")]
    public async Task RejectsEveryInvalidReviewShape(string invalidField)
    {
        var fixture = await CreateFixtureAsync();
        var service = new PerformanceReviewService(
            fixture.Factory, new RecordingRelationshipConstitutionalGateway());
        var draft = Draft("CONTINUE_CURRENT_MANDATE");
        var skillId = "CUSTOMER_PROFILING";
        var skillVersion = "1.0.0";
        draft = invalidField switch
        {
            "skill" => draft,
            "version" => draft,
            "policy" => draft with { PolicyVersion = " " },
            "period" => draft with { PeriodStart = draft.PeriodEnd },
            "sources" => draft with { SourceVersions = new Dictionary<string, string>() },
            "recommendation" => draft with { Recommendation = "PROMOTE_OWN_PROMPT" },
            "evidence" => draft with { EvidenceId = Guid.Empty },
            "dimension-state" => draft with { WorkDelivery = draft.WorkDelivery with { State = "" } },
            "dimension-summary" => draft with { AgentQuality = draft.AgentQuality with { Summary = " " } },
            "dimension-evidence" => draft with { TrustAutonomy = draft.TrustAutonomy with { EvidenceState = "" } },
            _ => throw new ArgumentOutOfRangeException(nameof(invalidField)),
        };
        if (invalidField == "skill") skillId = " ";
        if (invalidField == "version") skillVersion = "";

        await Assert.ThrowsAsync<PerformanceReviewInvalidException>(() => service.AppendAsync(
            fixture.TenantId, fixture.RelationshipId, skillId, skillVersion, draft,
            CancellationToken.None));
        Assert.Empty(await service.ListAsync(
            fixture.TenantId, fixture.RelationshipId, CancellationToken.None));
    }

    [Theory]
    [InlineData("decision")]
    [InlineData("revision")]
    [InlineData("idempotency")]
    [InlineData("correlation")]
    [InlineData("hash")]
    [InlineData("long-reason")]
    [InlineData("continue-reason")]
    [InlineData("missing-reason")]
    public async Task RejectsEveryInvalidResponseShapeBeforeEvidence(string invalidField)
    {
        var fixture = await CreateFixtureAsync();
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var service = new PerformanceReviewService(fixture.Factory, gateway);
        var review = await service.AppendAsync(fixture.TenantId, fixture.RelationshipId,
            "CUSTOMER_PROFILING", "1.0.0", Draft("CONTINUE_CURRENT_MANDATE"),
            CancellationToken.None);
        var decision = invalidField == "continue-reason"
            ? "CONTINUE_CURRENT_MANDATE" : "REQUEST_REASSESSMENT";
        var reason = invalidField switch
        {
            "long-reason" => new string('x', 501),
            "continue-reason" => "A reason is forbidden for this decision.",
            "missing-reason" => " ",
            _ => "Reassess this outcome.",
        };

        await Assert.ThrowsAsync<PerformanceReviewInvalidException>(() => service.RespondAsync(
            fixture.TenantId, fixture.RelationshipId, fixture.ParticipantId, review.ReviewId,
            invalidField == "revision" ? 0 : review.Revision,
            invalidField == "decision" ? "PROMOTE_OWN_PROMPT" : decision,
            reason,
            invalidField == "idempotency" ? Guid.Empty : Guid.NewGuid(),
            invalidField == "hash" ? "short" : new string('a', 64),
            invalidField == "correlation" ? Guid.Empty : Guid.NewGuid(),
            CancellationToken.None));

        Assert.Equal(0, gateway.CallCount);
        Assert.Null(await service.GetResponseAsync(
            fixture.TenantId, fixture.RelationshipId, Guid.NewGuid(), CancellationToken.None));
    }

    [Fact]
    public async Task ContinueDecisionNeedsNoReasonAndNonMaterialReviewCreatesNoAlert()
    {
        var fixture = await CreateFixtureAsync();
        var service = new PerformanceReviewService(
            fixture.Factory, new RecordingRelationshipConstitutionalGateway());
        var review = await service.AppendAsync(fixture.TenantId, fixture.RelationshipId,
            "CUSTOMER_PROFILING", "1.0.0", Draft("TUNE_NON_MATERIAL_PRESENTATION"),
            CancellationToken.None);
        var response = await service.RespondAsync(
            fixture.TenantId, fixture.RelationshipId, fixture.ParticipantId, review.ReviewId,
            review.Revision, "CONTINUE_CURRENT_MANDATE", null, Guid.NewGuid(), new string('a', 64),
            Guid.NewGuid(), CancellationToken.None);

        Assert.Null(response.Response.Reason);
        Assert.False(Assert.Single(await service.ListAsync(
            fixture.TenantId, fixture.RelationshipId, CancellationToken.None)).ReassessmentRequired);
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Empty(await db.CustomerAlerts.ToListAsync());
    }

    [Fact]
    public async Task PauseRecommendationCreatesHighAlertAndRequiresReassessment()
    {
        var fixture = await CreateFixtureAsync();
        var service = new PerformanceReviewService(
            fixture.Factory, new RecordingRelationshipConstitutionalGateway());

        var review = await service.AppendAsync(fixture.TenantId, fixture.RelationshipId,
            "CUSTOMER_PROFILING", "1.0.0", Draft("PAUSE_AFFECTED_WORK"),
            CancellationToken.None);

        Assert.True(review.ReassessmentRequired);
        await using var db = fixture.Factory.CreateDbContext();
        Assert.Equal("HIGH", Assert.Single(await db.CustomerAlerts.ToListAsync()).Severity);
    }

    private static PerformanceReviewDraftV1 Draft(string recommendation) => new(
        "review-policy-1", DateTimeOffset.UtcNow.AddDays(-30), DateTimeOffset.UtcNow,
        new Dictionary<string, string>
        {
            ["professionalRuntime"] = "pr-17",
            ["constitutionalEngine"] = "ce-9",
            ["billingEngine"] = "wbe-12",
            ["goal"] = "goal-3",
        },
        new("DELIVERED", "Planned work was delivered.", "RECORDED"),
        new("GOOD", "Quality checks passed.", "RECORDED"),
        new("CONFORMANT", "CE validation and evidence are complete.", "RECORDED"),
        new("WITHIN_ALLOWANCE", "Usage stayed within the owner threshold.", "RECORDED"),
        new("POOR", "The external measure did not improve.", "RECORDED", "No causal guarantee", "External factors remain."),
        new("CUSTOMER_DISPUTED", "The customer requested correction.", "RECORDED"),
        new("UNCHANGED", "No autonomy increase is authorized.", "RECORDED"),
        recommendation, Guid.NewGuid());

    private static async Task<Fixture> CreateFixtureAsync()
    {
        var factory = new InMemoryEmploymentRelationshipFactory($"review-{Guid.NewGuid():N}");
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var agentInstanceId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            AgentInstanceId = agentInstanceId,
            ProfessionalType = "DMA",
            ProfessionalVersion = "1.0.0",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = participantId,
            State = EmploymentRelationshipState.Active,
        });
        db.RelationshipSkillConfigurations.Add(new RelationshipSkillConfiguration
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SkillId = "CUSTOMER_PROFILING",
            SkillVersion = "1.0.0",
            AuthorityState = "GRANTED",
            Status = "ACCEPTED",
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Employer,
            BoundEvidenceId = Guid.NewGuid(),
        });
        await db.SaveChangesAsync();
        return new Fixture(factory, tenantId, relationshipId, participantId);
    }

    private sealed record Fixture(
        InMemoryEmploymentRelationshipFactory Factory,
        Guid TenantId,
        Guid RelationshipId,
        Guid ParticipantId);
}
