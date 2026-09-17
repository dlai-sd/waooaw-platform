// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md Sections 10 and 17 SIM-095-14/15
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063, C-079

using Microsoft.EntityFrameworkCore;
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
        var service = new PerformanceReviewService(fixture.Factory);

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
        Assert.NotEqual(first.ReviewId, second.ReviewId);
        Assert.NotEqual(first.EvidenceId, second.EvidenceId);
    }

    [Fact]
    public async Task RejectsSelfPromotionAndCrossTenantProjectionWithoutMutation()
    {
        var fixture = await CreateFixtureAsync();
        var service = new PerformanceReviewService(fixture.Factory);

        await Assert.ThrowsAsync<PerformanceReviewInvalidException>(() => service.AppendAsync(
            fixture.TenantId, fixture.RelationshipId, "CUSTOMER_PROFILING", "1.0.0",
            Draft("PROMOTE_OWN_PROMPT"), CancellationToken.None));
        Assert.Empty(await service.ListAsync(fixture.TenantId, fixture.RelationshipId, CancellationToken.None));
        Assert.Empty(await service.ListAsync(Guid.NewGuid(), fixture.RelationshipId, CancellationToken.None));
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
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            AgentInstanceId = agentInstanceId,
            ProfessionalType = "DMA",
            ProfessionalVersion = "1.0.0",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = Guid.NewGuid(),
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
        await db.SaveChangesAsync();
        return new Fixture(factory, tenantId, relationshipId);
    }

    private sealed record Fixture(
        InMemoryEmploymentRelationshipFactory Factory,
        Guid TenantId,
        Guid RelationshipId);
}
