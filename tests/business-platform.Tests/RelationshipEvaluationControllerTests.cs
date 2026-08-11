// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-059, C-076

using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipEvaluationControllerTests
{
    [Fact]
    public async Task ProjectionReturnsDurableTrialContextAndIndependentDecisions()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var startsAt = DateTimeOffset.UtcNow;
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ProfessionalType = "DIGITAL_MARKETING_LOCAL_SERVICE",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = Guid.NewGuid(),
                State = EmploymentRelationshipState.TrialActive,
            });
            db.RelationshipContextPayloads.Add(new RelationshipContextPayload
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                FieldType = "NAME",
                ValueJson = "\"Acme Clinic\"",
                Source = "CUSTOMER",
                ConfirmationStatus = "CONFIRMED",
                PayloadHash = new string('a', 64),
            });
            db.RelationshipTrialBindings.Add(new RelationshipTrialBinding
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                CustomerId = Guid.NewGuid(),
                CorrelationId = Guid.NewGuid(),
                TrialId = Guid.NewGuid(),
                StartsAt = startsAt,
                ExpiresAt = startsAt.AddDays(14),
                Status = "ACTIVE",
            });
            db.RelationshipGoals.Add(new RelationshipGoal
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                Goal = "Increase qualified enquiries",
                Measure = "Qualified enquiries per month",
                Status = "ACCEPTED",
            });
            db.RelationshipSkillConfigurations.Add(new RelationshipSkillConfiguration
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                SkillId = "MARKET_RESEARCH",
                SkillVersion = "1.0.0",
                Status = "DEFERRED",
            });
            await db.SaveChangesAsync();
        }
        var controller = Controller(factory, tenantId);

        var result = Assert.IsType<OkObjectResult>(await controller.GetAsync(relationshipId, CancellationToken.None));
        var projection = Assert.IsType<RelationshipEvaluationProjection>(result.Value);

        Assert.Equal("TRIAL_ACTIVE", projection.LifecycleState);
        Assert.Equal("Where does your business serve customers?", projection.NextContextQuestion);
        Assert.Equal(TimeSpan.FromDays(14), projection.Trial!.ExpiresAt - projection.Trial.StartsAt);
        Assert.Equal("ACCEPTED", Assert.Single(projection.Goals).Status);
        Assert.Equal("DEFERRED", Assert.Single(projection.Skills).Status);
    }

    [Fact]
    public async Task ProjectionDoesNotRevealAnotherTenantRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationshipId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(new EmploymentRelationship
            {
                TenantId = Guid.NewGuid(),
                RelationshipId = relationshipId,
                ProfessionalType = "FIXTURE",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = Guid.NewGuid(),
            });
            await db.SaveChangesAsync();
        }

        var result = await Controller(factory, Guid.NewGuid()).GetAsync(relationshipId, CancellationToken.None);

        Assert.IsType<NotFoundResult>(result);
    }

    private static RelationshipEvaluationController Controller(
        InMemoryEmploymentRelationshipFactory factory, Guid tenantId)
    {
        var context = new DefaultHttpContext();
        context.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        return new RelationshipEvaluationController(factory)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
    }
}