// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-02
// constitutional_basis: C-009, C-023, C-043, C-049, C-059

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentContractServiceTests
{
    private static readonly EmploymentContractCommercialTerms CommercialTerms = new(
        "INR",
        249900,
        38120,
        "MONTHLY",
        "Subscription renews monthly until cancelled.",
        "Advertising spend is separate, customer-funded, and never incurred without approved budget authority.",
        "Cancel before the next renewal; refunds follow the disclosed billing and dispute policy.");

    [Fact]
    public async Task ComposeRequiresAcceptedDecisionSpaceSnapshot()
    {
        var (service, _, tenantId, relationshipId, actorId) = await CreateContextAsync(includeSnapshot: false);

        await Assert.ThrowsAsync<InvalidOperationException>(() => service.ComposeAsync(
            tenantId, relationshipId, actorId, CommercialTerms, CancellationToken.None));
    }

    [Fact]
    public async Task IdenticalMaterialReplaysDeterministicVersionAndCompleteTerms()
    {
        var (service, factory, tenantId, relationshipId, actorId) = await CreateContextAsync();

        var first = await service.ComposeAsync(
            tenantId, relationshipId, actorId, CommercialTerms, CancellationToken.None);
        var replay = await service.ComposeAsync(
            tenantId, relationshipId, actorId, CommercialTerms, CancellationToken.None);

        Assert.True(first.Created);
        Assert.False(replay.Created);
        Assert.Equal(first.Contract.ContractId, replay.Contract.ContractId);
        Assert.Equal(first.Contract.ContractHash, replay.Contract.ContractHash);
        Assert.Equal(1, first.Contract.Version);
        Assert.Equal(64, first.Contract.ContractHash.Length);
        Assert.Equal(64, first.Contract.DomainScheduleHash.Length);
        Assert.NotEmpty(first.Document.Rights);
        Assert.NotEmpty(first.Document.Obligations);
        Assert.NotEmpty(first.Document.Limitations);
        Assert.NotEmpty(first.Document.AuthorityTerms);
        Assert.NotEmpty(first.Document.StopTerms);
        Assert.Equal(2, first.Document.ReviewCadenceMonths);
        Assert.Equal(CommercialTerms, first.Document.PriceTax);
        Assert.Contains("Advertising spend", first.Document.PriceTax.AdSpendTreatment);
        Assert.Contains("Cancel", first.Document.PriceTax.CancellationAndRefundTerms);
        Assert.Single(first.Document.Goals);
        Assert.Single(first.Document.Skills);

        await using var db = factory.CreateDbContext();
        Assert.Equal(1, await db.EmploymentContractVersions.CountAsync());
    }

    [Fact]
    public async Task ChangedAcceptedConfigurationCreatesImmutableNextVersion()
    {
        var (service, factory, tenantId, relationshipId, actorId) = await CreateContextAsync();
        var first = await service.ComposeAsync(
            tenantId, relationshipId, actorId, CommercialTerms, CancellationToken.None);

        await using (var db = factory.CreateDbContext())
        {
            db.DecisionSpaceSnapshots.Add(new DecisionSpaceSnapshot
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                Version = 2,
                BudgetCeilingInrPaise = 500000,
                AuthorityBoundariesJson = "[\"Approval required before publishing\"]",
                StopConditionsJson = "[\"Stop at the approved budget ceiling\"]",
                ReviewCadenceMonths = 2,
                AcceptedEvidenceJson = "[]",
                CreatedByParticipantId = actorId,
                EvidenceId = Guid.NewGuid(),
                CreatedAt = first.Contract.CreatedAt.AddSeconds(1),
            });
            await db.SaveChangesAsync();
        }

        var amendment = await service.ComposeAsync(
            tenantId, relationshipId, actorId, CommercialTerms, CancellationToken.None);

        Assert.True(amendment.Created);
        Assert.Equal(2, amendment.Contract.Version);
        Assert.NotEqual(first.Contract.ContractId, amendment.Contract.ContractId);
        Assert.NotEqual(first.Contract.ContractHash, amendment.Contract.ContractHash);
        Assert.Equal(500000, amendment.Document.BudgetCeilingInrPaise);

        await using var verificationDb = factory.CreateDbContext();
        var versions = await verificationDb.EmploymentContractVersions
            .OrderBy(item => item.Version)
            .ToListAsync();
        Assert.Equal(2, versions.Count);
        Assert.Equal(first.Contract.ContractHash, versions[0].ContractHash);
        Assert.Equal("PRESENTED", versions[0].State);
    }

    [Fact]
    public async Task CctAe01Stop01_StoppedRelationshipRejectsContractPresentationWithoutMutation()
    {
        var (service, factory, tenantId, relationshipId, actorId) = await CreateContextAsync();
        await using (var db = factory.CreateDbContext())
        {
            (await db.EmploymentRelationships.SingleAsync()).State = EmploymentRelationshipState.StoppedEmergency;
            await db.SaveChangesAsync();
        }

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => service.ComposeAsync(
            tenantId, relationshipId, actorId, CommercialTerms, CancellationToken.None));

        await using var verificationDb = factory.CreateDbContext();
        Assert.Empty(await verificationDb.EmploymentContractVersions.ToListAsync());
    }

    private static async Task<(EmploymentContractService Service, InMemoryEmploymentRelationshipFactory Factory, Guid TenantId, Guid RelationshipId, Guid ActorId)> CreateContextAsync(
        bool includeSnapshot = true)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = actorId,
            State = EmploymentRelationshipState.Configuring,
        });
        db.RelationshipGoals.Add(new RelationshipGoal
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Goal = "Increase confirmed bookings",
            Baseline = "10 monthly",
            Measure = "Confirmed bookings",
            DecisionThreshold = "15 monthly",
            EvidenceSource = "Customer booking records",
            Status = "ACCEPTED",
        });
        db.RelationshipSkillConfigurations.Add(new RelationshipSkillConfiguration
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            SkillId = "LOCAL_SEO",
            SkillVersion = "1.0.0",
            AuthorityState = "NOT_GRANTED",
            Applicability = "APPLICABLE",
            Status = "ACCEPTED",
        });
        if (includeSnapshot)
        {
            db.DecisionSpaceSnapshots.Add(new DecisionSpaceSnapshot
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                Version = 1,
                BudgetCeilingInrPaise = 250000,
                AuthorityBoundariesJson = "[\"No publishing without approval\"]",
                StopConditionsJson = "[\"Stop on customer request\"]",
                ReviewCadenceMonths = 2,
                AcceptedEvidenceJson = "[]",
                CreatedByParticipantId = actorId,
                EvidenceId = Guid.NewGuid(),
            });
        }
        await db.SaveChangesAsync();

        return (new EmploymentContractService(factory, new ContractProfessionalCatalogStub()), factory, tenantId, relationshipId, actorId);
    }

    private sealed class ContractProfessionalCatalogStub : IProfessionalCatalog
    {
        public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome) => [];

        public ProfessionalDisclosure? GetDisclosure(string professionalType) => new(
            professionalType,
            "1.0.0",
            "Digital Marketing Professional",
            ["Local service growth"],
            [new ProfessionalSkillDisclosure("LOCAL_SEO", "Local SEO", true, null)],
            ["Results are not guaranteed."],
            ["Publishing and spend require explicit authority."],
            ["Inspect evidence and exit at any time."],
            new ProfessionalTrialDisclosure(true, 14, false, false),
            "Facts and recommendations remain distinguishable.",
            new IndicativePriceDisclosure("INR", 249900, "MONTHLY", "Indicative only."),
            new ProfessionalEligibility(true, "Eligible"));
    }
}