// Implements: WC-065 WC065-02, WC065-03, WC065-06, FA-047
// constitutional_basis: C-002, C-023, C-059, C-089, C-091

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class OfferabilityOrchestrationServiceTests
{
    [Fact]
    public async Task FreshOwnerApprovalRecordsEvidenceAndPersistsAllow()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var evidenceId = Guid.NewGuid();
        var constitutional = new OfferabilityConstitutionalGateway(evidenceId);
        var owner = new OfferabilityOwnerGatewayStub(new OwnerOfferabilityValidation(
            "APPROVED", 5_000, 6_250, 7_000, 2_000, "wbe-validation-7", DateTimeOffset.UtcNow));
        var service = new OfferabilityOrchestrationService(
            owner, constitutional, factory, new OfferabilityService());

        var record = await service.EvaluateAsync(Request(), CancellationToken.None);

        Assert.Equal("ALLOW", record.Disposition);
        Assert.Equal(2_000m, record.DirectContributionAmount);
        Assert.Equal(evidenceId, record.EvidenceId);
        Assert.True(constitutional.Called);
        Assert.Equal(constitutional.LastCorrelationId, record.IdempotencyKey);
        await using var db = factory.CreateDbContext();
        Assert.Equal(record.DecisionId, (await db.OfferabilityDecisions.SingleAsync()).DecisionId);
    }

    [Fact]
    public async Task IdenticalReplayReturnsStoredDecisionWithoutRepeatingOwnerOrEvidence()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var constitutional = new OfferabilityConstitutionalGateway(Guid.NewGuid());
        var owner = new OfferabilityOwnerGatewayStub(new OwnerOfferabilityValidation(
            "APPROVED", 5_000, 6_250, 7_000, 2_000, "wbe-validation-7", DateTimeOffset.UtcNow));
        var service = new OfferabilityOrchestrationService(owner, constitutional, factory, new OfferabilityService());
        var request = Request();

        var first = await service.EvaluateAsync(request, CancellationToken.None);
        var replay = await service.EvaluateAsync(request, CancellationToken.None);

        Assert.Equal(first.DecisionId, replay.DecisionId);
        Assert.Equal(1, owner.CallCount);
        Assert.Equal(1, constitutional.CallCount);
    }

    [Fact]
    public async Task ChangedIntentUnderSameKeyConflictsBeforeOwnerOrEvidence()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var constitutional = new OfferabilityConstitutionalGateway(Guid.NewGuid());
        var owner = new OfferabilityOwnerGatewayStub(new OwnerOfferabilityValidation(
            "APPROVED", 5_000, 6_250, 7_000, 2_000, "wbe-validation-7", DateTimeOffset.UtcNow));
        var service = new OfferabilityOrchestrationService(owner, constitutional, factory, new OfferabilityService());
        var request = Request();
        await service.EvaluateAsync(request, CancellationToken.None);

        await Assert.ThrowsAsync<OfferabilityIdempotencyConflictException>(() =>
            service.EvaluateAsync(request with { ProposedPricePaise = 7_001 }, CancellationToken.None));

        Assert.Equal(1, owner.CallCount);
        Assert.Equal(1, constitutional.CallCount);
    }

    [Fact]
    public async Task MissingOwnerTruthRecordsNonEligibleDecisionWithoutInventingCost()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new OfferabilityOrchestrationService(
            new OfferabilityOwnerGatewayStub(null),
            new OfferabilityConstitutionalGateway(Guid.NewGuid()),
            factory,
            new OfferabilityService());

        var record = await service.EvaluateAsync(Request(), CancellationToken.None);

        Assert.Equal("BLOCK", record.Disposition);
        Assert.Contains("OWNER_EVIDENCE_UNAVAILABLE_OR_STALE", record.ReasonsJson);
        Assert.Contains("CONSTITUTIONAL_FLOOR_FAILED", record.ReasonsJson);
    }

    [Fact]
    public async Task ChangedIntentAfterOwnerFailureConflictsFromDurableReservation()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var owner = new ThrowingOwnerGateway();
        var service = new OfferabilityOrchestrationService(
            owner,
            new OfferabilityConstitutionalGateway(Guid.NewGuid()),
            factory,
            new OfferabilityService());
        var request = Request();
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.EvaluateAsync(request, CancellationToken.None));

        await Assert.ThrowsAsync<OfferabilityIdempotencyConflictException>(() =>
            service.EvaluateAsync(request with { ProposedPricePaise = 7_001 }, CancellationToken.None));

        Assert.Equal(1, owner.CallCount);
    }

    [Fact]
    public async Task PersistentGuard_RequiresCurrentAllowForExactRelationshipVersion()
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
                StateVersion = 3,
            });
            var admission = new AgentAdmission
            {
                TenantId = tenantId,
                ProfessionalTypeId = "DMA",
                ProfessionalVersion = "1.0.0",
                OwnerSubjectId = Guid.NewGuid(),
                State = AgentAdmissionState.Active,
                CurrentRevision = 1,
                AdmissionContentDigest = "sha256:" + new string('a', 64),
            };
            db.AgentAdmissions.Add(admission);
            db.AgentAdmissionRevisions.Add(new AgentAdmissionRevision
            {
                TenantId = tenantId,
                AdmissionId = admission.AdmissionId,
                Revision = 1,
                ContractSchemaVersion = "1.0.0",
                AdmissionContentDigest = admission.AdmissionContentDigest,
                AdmissionContentJson = "{\"skillManifest\":[{\"skillId\":\"SKILL\"}]}",
                ActorSubjectId = admission.OwnerSubjectId,
            });
            db.RelationshipSkillConfigurations.Add(new RelationshipSkillConfiguration
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                SkillId = "SKILL",
                SkillVersion = "1.0.0",
                GoalId = Guid.NewGuid(),
            });
            await db.SaveChangesAsync();
        }
        var guard = new PersistentOfferabilityGuard(factory);

        await Assert.ThrowsAsync<ActivationEligibilityException>(() => guard.RequireEligibleAsync(
            Guid.NewGuid(), relationshipId, CancellationToken.None));
        await Assert.ThrowsAsync<ActivationEligibilityException>(() => guard.RequireEligibleAsync(
            tenantId, relationshipId, CancellationToken.None));

        foreach (var (disposition, expiresAt, version, allowed) in new[]
        {
            ("BLOCK", DateTimeOffset.UtcNow.AddHours(1), 3, false),
            ("ALLOW", DateTimeOffset.UtcNow.AddMinutes(-1), 3, false),
            ("ALLOW", DateTimeOffset.UtcNow.AddHours(1), 2, false),
            ("ALLOW", DateTimeOffset.UtcNow.AddHours(1), 3, true),
        })
        {
            await using (var db = factory.CreateDbContext())
            {
                db.OfferabilityDecisions.RemoveRange(db.OfferabilityDecisions);
                db.OfferabilityDecisions.Add(new OfferabilityDecisionRecord
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    RelationshipStateVersion = version,
                    PolicyVersion = "policy",
                    DirectContributionAmount = 50,
                    Disposition = disposition,
                    ReasonsJson = "[]",
                    OwnerVersionsJson = "{}",
                    MaterialRequestHash = new string('a', 64),
                    ExpiresAt = expiresAt,
                });
                await db.SaveChangesAsync();
            }
            if (allowed)
                await guard.RequireEligibleAsync(tenantId, relationshipId, CancellationToken.None);
            else
                await Assert.ThrowsAsync<ActivationEligibilityException>(() => guard.RequireEligibleAsync(
                    tenantId, relationshipId, CancellationToken.None));
        }
    }

    private static OfferabilityEvaluationRequest Request() => new(
        Guid.NewGuid(),
        Guid.NewGuid(),
        3,
        Guid.NewGuid(),
        Guid.NewGuid(),
        Guid.NewGuid(),
        "dma-starter-v1",
        "DMA",
        "STARTER",
        7_000);

    private sealed class OfferabilityOwnerGatewayStub(OwnerOfferabilityValidation? result)
        : IOfferabilityOwnerGateway
    {
        public int CallCount { get; private set; }

        public Task<OwnerOfferabilityValidation?> ValidateAsync(
            OfferabilityEvaluationRequest request, CancellationToken cancellationToken)
        {
            CallCount++;
            return Task.FromResult(result);
        }
    }

    private sealed class OfferabilityConstitutionalGateway(Guid evidenceId)
        : IRelationshipConstitutionalGateway
    {
        public bool Called { get; private set; }
        public int CallCount { get; private set; }
        public Guid LastCorrelationId { get; private set; }

        public Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken)
        {
            Called = true;
            CallCount++;
            LastCorrelationId = correlationId;
            return Task.FromResult(evidenceId);
        }
    }

    private sealed class ThrowingOwnerGateway : IOfferabilityOwnerGateway
    {
        public int CallCount { get; private set; }

        public Task<OwnerOfferabilityValidation?> ValidateAsync(
            OfferabilityEvaluationRequest request,
            CancellationToken cancellationToken)
        {
            CallCount++;
            throw new InvalidOperationException("owner unavailable");
        }
    }
}
