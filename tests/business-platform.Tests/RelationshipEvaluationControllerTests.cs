// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-059, C-076

using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
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
    public async Task SameTypeAgentsRetainSeparateIdentityConfigurationTrialContractAndProjection()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var service = new RelationshipConfigurationService(factory, gateway);
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var firstRelationshipId = Guid.NewGuid();
        var secondRelationshipId = Guid.NewGuid();
        var firstAgentInstanceId = Guid.NewGuid();
        var secondAgentInstanceId = Guid.NewGuid();
        var firstTrialId = Guid.NewGuid();
        var secondTrialId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.AddRange(
                new EmploymentRelationship
                {
                    TenantId = tenantId, RelationshipId = firstRelationshipId,
                    AgentInstanceId = firstAgentInstanceId, ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(), InitiatingParticipantId = actorId,
                    State = EmploymentRelationshipState.TrialActive,
                },
                new EmploymentRelationship
                {
                    TenantId = tenantId, RelationshipId = secondRelationshipId,
                    AgentInstanceId = secondAgentInstanceId, ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(), InitiatingParticipantId = actorId,
                    State = EmploymentRelationshipState.TrialActive,
                });
            db.RelationshipGoals.AddRange(
                new RelationshipGoal { TenantId = tenantId, RelationshipId = firstRelationshipId, Goal = "Grow local leads", Measure = "Leads", Status = "ACCEPTED" },
                new RelationshipGoal { TenantId = tenantId, RelationshipId = secondRelationshipId, Goal = "Improve retention", Measure = "Renewals", Status = "ACCEPTED" });
            db.RelationshipTrialBindings.AddRange(
                new RelationshipTrialBinding { TenantId = tenantId, RelationshipId = firstRelationshipId, CustomerId = tenantId, CorrelationId = Guid.NewGuid(), TrialId = firstTrialId, StartsAt = DateTimeOffset.UtcNow, ExpiresAt = DateTimeOffset.UtcNow.AddDays(14), Status = "ACTIVE" },
                new RelationshipTrialBinding { TenantId = tenantId, RelationshipId = secondRelationshipId, CustomerId = tenantId, CorrelationId = Guid.NewGuid(), TrialId = secondTrialId, StartsAt = DateTimeOffset.UtcNow, ExpiresAt = DateTimeOffset.UtcNow.AddDays(14), Status = "ACTIVE" });
            db.EmploymentContractVersions.AddRange(
                new EmploymentContractVersion { TenantId = tenantId, RelationshipId = firstRelationshipId, Version = 2, ContractHash = new string('a', 64), AeecVersion = "1", DomainScheduleHash = new string('b', 64), CreatedByParticipantId = actorId },
                new EmploymentContractVersion { TenantId = tenantId, RelationshipId = secondRelationshipId, Version = 5, ContractHash = new string('c', 64), AeecVersion = "1", DomainScheduleHash = new string('d', 64), CreatedByParticipantId = actorId });
            await db.SaveChangesAsync();
        }
        var firstSkill = await service.SaveSkillAsync(tenantId, firstRelationshipId, "local-seo", "1.0.0", null,
            "NOT_GRANTED", "APPLICABLE", null, "PROPOSED", CancellationToken.None);
        await service.SaveSkillAsync(tenantId, secondRelationshipId, "email-retention", "2.0.0", null,
            "NOT_GRANTED", "APPLICABLE", null, "DEFERRED", CancellationToken.None);

        await service.DecideSkillAsync(tenantId, firstRelationshipId, actorId, Guid.NewGuid(), new string('e', 64),
            "relationship-0", RelationshipConfigurationService.GetSkillVersion(firstSkill), firstSkill.ConfigurationId,
            firstSkill.SkillId, firstSkill.SkillVersion, "ACCEPT_SKILL", Guid.NewGuid(), CancellationToken.None);

        var first = Assert.IsType<RelationshipEvaluationProjection>(Assert.IsType<OkObjectResult>(
            await Controller(factory, tenantId).GetAsync(firstRelationshipId, CancellationToken.None)).Value);
        var second = Assert.IsType<RelationshipEvaluationProjection>(Assert.IsType<OkObjectResult>(
            await Controller(factory, tenantId).GetAsync(secondRelationshipId, CancellationToken.None)).Value);
        await using var verificationDb = factory.CreateDbContext();

        Assert.NotEqual(firstAgentInstanceId, secondAgentInstanceId);
        Assert.Equal(firstTrialId, first.Trial!.TrialId);
        Assert.Equal(secondTrialId, second.Trial!.TrialId);
        Assert.Equal("Grow local leads", Assert.Single(first.Goals).Goal);
        Assert.Equal("Improve retention", Assert.Single(second.Goals).Goal);
        Assert.Equal("ACCEPTED", Assert.Single(first.Skills).Status);
        Assert.Equal("local-seo", Assert.Single(first.Skills).SkillId);
        Assert.Equal("DEFERRED", Assert.Single(second.Skills).Status);
        Assert.Equal("email-retention", Assert.Single(second.Skills).SkillId);
        Assert.Equal(2, (await verificationDb.EmploymentContractVersions.SingleAsync(
            item => item.RelationshipId == firstRelationshipId)).Version);
        Assert.Equal(5, (await verificationDb.EmploymentContractVersions.SingleAsync(
            item => item.RelationshipId == secondRelationshipId)).Version);
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

    [Fact]
    public async Task ProjectionCompletesContextDecisionAndOptionalTrialBranches()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ProfessionalType = "DMA",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = Guid.NewGuid(),
                State = EmploymentRelationshipState.Discovered,
            });
            foreach (var field in new[] { "NAME", "LOCATION", "BUSINESS_NATURE" })
            {
                db.RelationshipContextPayloads.Add(new RelationshipContextPayload
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    FieldType = field,
                    ValueJson = "true",
                    Source = "CUSTOMER",
                    PayloadHash = new string('a', 64),
                });
            }
            db.RelationshipTrialBindings.Add(new RelationshipTrialBinding
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                CustomerId = Guid.NewGuid(),
                CorrelationId = Guid.NewGuid(),
                TrialId = Guid.NewGuid(),
            });
            db.DecisionSpaceSnapshots.Add(new DecisionSpaceSnapshot
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                Version = 2,
                BudgetCeilingInrPaise = 1_000,
                AuthorityBoundariesJson = "[\"LOCAL\"]",
                StopConditionsJson = "[\"STOP\"]",
                CreatedByParticipantId = Guid.NewGuid(),
                EvidenceId = Guid.NewGuid(),
            });
            await db.SaveChangesAsync();
        }

        var projection = Assert.IsType<RelationshipEvaluationProjection>(
            Assert.IsType<OkObjectResult>(await Controller(factory, tenantId).GetAsync(
                relationshipId, CancellationToken.None)).Value);

        Assert.Null(projection.NextContextQuestion);
        Assert.Null(projection.Trial);
        Assert.NotNull(projection.DecisionSpace);
        Assert.Equal("NOT_STARTED", projection.InterviewState);
    }

    [Fact]
    public async Task ProjectionRejectsMissingAndMalformedTenantContext()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        foreach (var value in new object?[] { null, new object(), "not-a-uuid" })
        {
            var context = new DefaultHttpContext();
            if (value is not null) context.Items[TenantIsolationMiddleware.TenantIdItemKey] = value;
            var controller = new RelationshipEvaluationController(factory)
            {
                ControllerContext = new ControllerContext { HttpContext = context },
            };
            Assert.IsType<ForbidResult>(await controller.GetAsync(Guid.NewGuid(), CancellationToken.None));
        }
    }

    [Fact]
    public void ConversationCursor_RejectsEveryMalformedOrMismatchedBoundary()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var codec = new ConversationCursorCodec(Options.Create(new ConversationCursorOptions
        {
            HmacKey = new string('k', 32),
        }));
        var cursor = codec.Encode(tenantId, relationshipId, "messages", 7);

        Assert.Equal(7, codec.Decode(cursor, tenantId, relationshipId, "messages"));
        Assert.Throws<ConversationCursorExpiredException>(() => codec.Decode("single", tenantId, relationshipId, "messages"));
        Assert.Throws<ConversationCursorExpiredException>(() => codec.Decode("%%%.%%%", tenantId, relationshipId, "messages"));
        Assert.Throws<ConversationCursorExpiredException>(() => codec.Decode(cursor, Guid.NewGuid(), relationshipId, "messages"));
        Assert.Throws<ConversationCursorExpiredException>(() => codec.Decode(cursor, tenantId, Guid.NewGuid(), "messages"));
        Assert.Throws<ConversationCursorExpiredException>(() => codec.Decode(cursor, tenantId, relationshipId, "other"));
        Assert.Throws<ConversationCursorExpiredException>(() => codec.Decode(
            codec.Encode(tenantId, relationshipId, "messages", -1), tenantId, relationshipId, "messages"));
        var tampered = $"{cursor}A";
        Assert.Throws<ConversationCursorExpiredException>(() => codec.Decode(
            tampered, tenantId, relationshipId, "messages"));
        Assert.Throws<InvalidOperationException>(() => new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = "short" })));
        Assert.Throws<InvalidOperationException>(() => new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = " " })));
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
