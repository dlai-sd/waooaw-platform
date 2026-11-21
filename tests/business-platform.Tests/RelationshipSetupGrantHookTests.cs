// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
// constitutional_basis: C-023, C-059, C-063, C-076
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class RelationshipSetupGrantHookTests
{
    private sealed class RecordingPlatformAccounts : IPlatformAccountGateway
    {
        public List<(
            Guid Tenant,
            Guid Relationship,
            string Type,
            string Version,
            Guid Key
        )> Opened { get; } = [];
        public bool Fail { get; set; }

        public Task<SetupGrantReceipt> OpenSetupGrantAsync(
            Guid tenantId,
            Guid actorId,
            Guid relationshipId,
            string agentType,
            string agentVersion,
            Guid idempotencyKey,
            CancellationToken ct
        )
        {
            if (Fail)
                throw new OfferingUsageOwnerUnavailableException("owner down");
            Opened.Add((tenantId, relationshipId, agentType, agentVersion, idempotencyKey));
            return Task.FromResult(
                new SetupGrantReceipt("GRANTED", Guid.NewGuid(), Guid.NewGuid(), 500, true)
            );
        }

        public Task<PlatformAccountReceipt> ReserveAccountAsync(
            PlatformAccountReserveRequest request,
            CancellationToken ct
        ) => throw new NotSupportedException();

        public Task<SetupGrantDrawReceipt> ReserveSetupGrantAsync(
            Guid tenantId,
            Guid actorId,
            Guid relationshipId,
            string agentType,
            string agentVersion,
            string componentId,
            long maximumPaise,
            Guid invocationId,
            Guid ownerEvidenceId,
            Guid idempotencyKey,
            CancellationToken ct
        ) => throw new NotSupportedException();

        public Task<WalletReservationOutcome> SettleAccountAsync(
            Guid tenantId,
            Guid actorId,
            Guid reservationId,
            long actualPaise,
            Guid evidenceId,
            Guid idempotencyKey,
            CancellationToken ct
        ) => throw new NotSupportedException();

        public Task<WalletReservationOutcome> ReleaseAccountAsync(
            Guid tenantId,
            Guid actorId,
            Guid reservationId,
            Guid nonDispatchEvidenceId,
            Guid idempotencyKey,
            CancellationToken ct
        ) => throw new NotSupportedException();
    }

    private static async Task<(
        EmploymentRelationshipService Service,
        Guid Tenant,
        Guid Actor,
        AgentAdmission Admission
    )> CreateAsync(IPlatformAccountGateway? accounts)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance,
            accounts
        );
        var tenant = Guid.NewGuid();
        var admission = new AgentAdmission
        {
            TenantId = tenant,
            ProfessionalTypeId = "DMA",
            ProfessionalVersion = "1.0.0",
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.AgentAdmissions.Add(admission);
            await seed.SaveChangesAsync();
        }
        return (service, tenant, Guid.NewGuid(), admission);
    }

    private static Task<AdmitRelationshipResult> AdmitAsync(
        EmploymentRelationshipService service,
        Guid tenant,
        Guid actor,
        AgentAdmission admission,
        Guid intent
    ) =>
        service.AdmitAsync(
            tenant,
            actor,
            intent,
            "DMA",
            admission.AdmissionId,
            admission.ProfessionalVersion,
            Guid.NewGuid(),
            CancellationToken.None
        );

    [Fact]
    public async Task AdmissionOpensOneSetupGrantWithAKeyDerivedFromTheRelationship()
    {
        var accounts = new RecordingPlatformAccounts();
        var (service, tenant, actor, admission) = await CreateAsync(accounts);
        var intent = Guid.NewGuid();

        var first = await AdmitAsync(service, tenant, actor, admission, intent);
        var replay = await AdmitAsync(service, tenant, actor, admission, intent);
        var second = await AdmitAsync(service, tenant, actor, admission, Guid.NewGuid());

        Assert.False(replay.Created);
        Assert.Equal(2, accounts.Opened.Count);
        var opened = accounts.Opened[0];
        Assert.Equal(
            (tenant, first.Relationship.RelationshipId, "DMA", "1.0.0"),
            (opened.Tenant, opened.Relationship, opened.Type, opened.Version)
        );
        Assert.Equal(
            EmploymentRelationshipService.SetupGrantKey(first.Relationship.RelationshipId),
            opened.Key
        );
        Assert.NotEqual(opened.Key, accounts.Opened[1].Key);
        Assert.Equal(second.Relationship.RelationshipId, accounts.Opened[1].Relationship);
    }

    [Fact]
    public async Task AdmissionSurvivesAnUnavailableWalletOwner()
    {
        var accounts = new RecordingPlatformAccounts { Fail = true };
        var (service, tenant, actor, admission) = await CreateAsync(accounts);

        var admitted = await AdmitAsync(service, tenant, actor, admission, Guid.NewGuid());

        Assert.True(admitted.Created);
        Assert.Empty(accounts.Opened);
    }

    [Fact]
    public async Task AdmissionWithoutAGatewayStillWorks()
    {
        var (service, tenant, actor, admission) = await CreateAsync(null);

        var admitted = await AdmitAsync(service, tenant, actor, admission, Guid.NewGuid());

        Assert.True(admitted.Created);
    }
}
