// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-03
// constitutional_basis: C-023, C-026, C-059, C-063, C-076, C-078

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipConfigurationServiceTests
{
    [Fact]
    public async Task CorrectionInvalidatesPayloadAndAppendsPrivacySafeEvidence()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance);
        var service = new RelationshipConfigurationService(factory, gateway);
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId, actorId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);

        var first = await service.ConfirmContextAsync(
            tenantId,
            admitted.Relationship.RelationshipId,
            actorId,
            "location",
            JsonSerializer.SerializeToElement("Mumbai"),
            "customer",
            null,
            null,
            Guid.NewGuid(),
            CancellationToken.None);
        var corrected = await service.ConfirmContextAsync(
            tenantId,
            admitted.Relationship.RelationshipId,
            actorId,
            "location",
            JsonSerializer.SerializeToElement("Pune"),
            "customer",
            null,
            first.PayloadReference,
            Guid.NewGuid(),
            CancellationToken.None);

        var active = await service.GetActiveContextAsync(
            tenantId, admitted.Relationship.RelationshipId, CancellationToken.None);
        Assert.Single(active);
        Assert.Equal(corrected.PayloadReference, active[0].PayloadReference);
        Assert.Equal("Pune", active[0].Value.GetString());

        await using var db = factory.CreateDbContext();
        var payloads = await db.RelationshipContextPayloads.OrderBy(item => item.CreatedAt).ToListAsync();
        var events = await db.ContextConfirmationEvents.OrderBy(item => item.OccurredAt).ToListAsync();
        Assert.Equal(2, payloads.Count);
        Assert.NotNull(payloads[0].InvalidatedAt);
        Assert.Equal("CORRECTED", payloads[0].ConfirmationStatus);
        Assert.Equal(2, events.Count);
        Assert.Equal(["CONFIRMED", "CORRECTED"], events.Select(item => item.Action));
        Assert.DoesNotContain("Mumbai", JsonSerializer.Serialize(events));
        Assert.DoesNotContain("Pune", JsonSerializer.Serialize(events));
    }

    [Fact]
    public async Task ProgressiveContextReturnsAtMostOneMissingQuestionPerCycle()
    {
        var (service, relationship, tenantId, actorId, _) = await CreateServiceAsync();

        var firstQuestion = await service.GetNextContextQuestionAsync(
            tenantId, relationship.RelationshipId, CancellationToken.None);
        Assert.Equal("NAME", firstQuestion?.FieldType);

        foreach (var field in new[] { "name", "location", "business_nature" })
        {
            await service.ConfirmContextAsync(
                tenantId, relationship.RelationshipId, actorId, field,
                JsonSerializer.SerializeToElement($"value-{field}"), "customer", null, null,
                Guid.NewGuid(), CancellationToken.None);
        }

        Assert.Null(await service.GetNextContextQuestionAsync(
            tenantId, relationship.RelationshipId, CancellationToken.None));
    }

    [Fact]
    public async Task ConfigurationPersistsIndependentDecisionsAndImmutableSnapshots()
    {
        var (service, relationship, tenantId, actorId, _) = await CreateServiceAsync();
        var goal = await service.SaveGoalAsync(
            tenantId, relationship.RelationshipId, "Increase bookings", "10 monthly", "Confirmed bookings",
            "15 monthly", "customer records", "ACCEPTED", CancellationToken.None);
        var skill = await service.SaveSkillAsync(
            tenantId, relationship.RelationshipId, "local-seo", "1.0.0", goal.GoalId,
            "NOT_GRANTED", "APPLICABLE", null, "DEFERRED", CancellationToken.None);
        var first = await service.CreateDecisionSpaceAsync(
            tenantId, relationship.RelationshipId, actorId, 250000,
            ["No publishing"], ["Stop on customer request"], 2, [Guid.NewGuid()],
            Guid.NewGuid(), CancellationToken.None);
        var second = await service.CreateDecisionSpaceAsync(
            tenantId, relationship.RelationshipId, actorId, 300000,
            ["Approval required"], ["Stop at budget ceiling"], 2, [Guid.NewGuid()],
            Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(2, goal.ReviewCadenceMonths);
        Assert.Equal("DEFERRED", skill.Status);
        Assert.Equal(1, first.Version);
        Assert.Equal(2, second.Version);

        await Assert.ThrowsAsync<ArgumentOutOfRangeException>(() => service.CreateDecisionSpaceAsync(
            tenantId, relationship.RelationshipId, actorId, 300000,
            ["Approval required"], ["Stop at budget ceiling"], 1, [],
            Guid.NewGuid(), CancellationToken.None));
    }

    [Fact]
    public async Task ErasureRemovesValuesButPreservesHashesAndConfirmationEvents()
    {
        var (service, relationship, tenantId, actorId, factory) = await CreateServiceAsync();
        await service.ConfirmContextAsync(
            tenantId, relationship.RelationshipId, actorId, "name",
            JsonSerializer.SerializeToElement("Sensitive Name"), "customer", null, null,
            Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(1, await service.EraseContextPayloadsAsync(
            tenantId, relationship.RelationshipId, CancellationToken.None));
        Assert.Empty(await service.GetActiveContextAsync(
            tenantId, relationship.RelationshipId, CancellationToken.None));

        await using var db = factory.CreateDbContext();
        var payload = await db.RelationshipContextPayloads.SingleAsync();
        Assert.Null(payload.ValueJson);
        Assert.NotNull(payload.ErasedAt);
        Assert.Equal(64, payload.PayloadHash.Length);
        Assert.Single(await db.ContextConfirmationEvents.ToListAsync());
    }

    [Fact]
    public async Task EvidenceFailurePersistsNeitherPayloadNorEvent()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId, actorId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        gateway.FailNext = true;
        var service = new RelationshipConfigurationService(factory, gateway);

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.ConfirmContextAsync(
            tenantId, admitted.Relationship.RelationshipId, actorId, "name",
            JsonSerializer.SerializeToElement("Sensitive Name"), "customer", null, null,
            Guid.NewGuid(), CancellationToken.None));

        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.RelationshipContextPayloads.ToListAsync());
        Assert.Empty(await db.ContextConfirmationEvents.ToListAsync());
    }

    [Fact]
    public async Task CctAe01Stop01_StoppedRelationshipRejectsConfigurationWithoutMutation()
    {
        var (service, relationship, tenantId, actorId, factory) = await CreateServiceAsync();
        await using (var db = factory.CreateDbContext())
        {
            (await db.EmploymentRelationships.SingleAsync()).State = EmploymentRelationshipState.StoppedEmergency;
            await db.SaveChangesAsync();
        }

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => service.ConfirmContextAsync(
            tenantId, relationship.RelationshipId, actorId, "name",
            JsonSerializer.SerializeToElement("Blocked value"), "customer", null, null,
            Guid.NewGuid(), CancellationToken.None));

        await using var verificationDb = factory.CreateDbContext();
        Assert.Empty(await verificationDb.RelationshipContextPayloads.ToListAsync());
        Assert.Empty(await verificationDb.ContextConfirmationEvents.ToListAsync());
    }

    private static async Task<(RelationshipConfigurationService Service, EmploymentRelationship Relationship, Guid TenantId, Guid ActorId, InMemoryEmploymentRelationshipFactory Factory)> CreateServiceAsync()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var admitted = await relationships.AdmitAsync(
            tenantId, actorId, Guid.NewGuid(), "DMA", Guid.NewGuid(), CancellationToken.None);
        return (new RelationshipConfigurationService(factory, gateway), admitted.Relationship, tenantId, actorId, factory);
    }
}