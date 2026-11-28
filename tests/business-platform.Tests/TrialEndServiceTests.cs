// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R011
// Constitutional basis: C-005, C-023, C-049, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.Alerts;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class TrialEndServiceTests
{
    private static readonly DateTimeOffset Now = new(2026, 12, 20, 6, 30, 0, TimeSpan.Zero);

    private sealed class FixedOwners(string? status) : IRelationshipTrialOwnerGateway
    {
        public bool IsConfigured => true;

        public Task<WbeTrialEntitlement?> StartWbeTrialAsync(
            Guid c,
            string t,
            string v,
            Guid r,
            Guid k,
            CancellationToken ct,
            TrialIdentityContext? x = null
        ) => Task.FromResult<WbeTrialEntitlement?>(null);

        public Task<WbeTrialStatus?> GetWbeTrialStatusAsync(
            Guid customerId,
            Guid trialId,
            CancellationToken ct
        ) => Task.FromResult(status is null ? null : new WbeTrialStatus(trialId, status));

        public Task<PrTrialWorkflow?> StartPrTrialAsync(
            Guid tenantId,
            Guid relationshipId,
            Guid agentInstanceId,
            Guid professionalAdmissionId,
            string professionalType,
            string professionalVersion,
            Guid trialId,
            DateTimeOffset startsAt,
            DateTimeOffset expiresAt,
            Guid correlationId,
            CancellationToken ct
        ) => Task.FromResult<PrTrialWorkflow?>(null);
    }

    private static async Task<(
        TrialEndService Service,
        InMemoryEmploymentRelationshipFactory Factory,
        Guid Tenant,
        Guid Relationship
    )> CreateAsync(string? billingStatus, DateTimeOffset expiresAt)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var tenant = Guid.NewGuid();
        var customer = Guid.NewGuid();
        var relationship = new EmploymentRelationship
        {
            TenantId = tenant,
            InitiatingParticipantId = customer,
            ProfessionalType = "DIGITAL_MARKETING_LOCAL_SERVICE",
            State = EmploymentRelationshipState.TrialActive,
        };
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(relationship);
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationship.RelationshipId,
                    ParticipantId = customer,
                    Role = RelationshipParticipantRole.Evaluator,
                }
            );
            db.RelationshipTrialBindings.Add(
                new RelationshipTrialBinding
                {
                    TenantId = tenant,
                    RelationshipId = relationship.RelationshipId,
                    CustomerId = customer,
                    TrialId = Guid.NewGuid(),
                    StartsAt = expiresAt.AddDays(-14),
                    ExpiresAt = expiresAt,
                    Status = "ACTIVE",
                }
            );
            await db.SaveChangesAsync();
        }
        var clock = new Mock<TimeProvider>();
        clock.Setup(value => value.GetUtcNow()).Returns(Now);
        var service = new TrialEndService(
            factory,
            new FixedOwners(billingStatus),
            new EmploymentRelationshipService(
                factory,
                new RecordingRelationshipConstitutionalGateway(),
                NullLogger<EmploymentRelationshipService>.Instance
            ),
            new AlertPolicyService(
                factory,
                Options.Create(new AlertDeliveryOptions()),
                new UnavailableProactiveAllowance(),
                new ClosedAlertWhatsAppSender(),
                clock.Object
            ),
            Options.Create(new TrialEndOptions { RetentionDays = 45 }),
            clock.Object,
            NullLogger<TrialEndService>.Instance
        );
        return (service, factory, tenant, relationship.RelationshipId);
    }

    [Fact]
    public async Task ATrialTheBillingOwnerReportsExpiredStopsTheAgentAndTellsTheCustomerOnce()
    {
        var (service, factory, tenant, relationshipId) = await CreateAsync(
            "EXPIRED",
            Now.AddHours(-1)
        );

        Assert.Equal(1, await service.EndDueTrialsAsync(default));
        Assert.Equal(0, await service.EndDueTrialsAsync(default));

        await using var db = factory.CreateDbContext();
        Assert.Equal(
            EmploymentRelationshipState.Configuring,
            (
                await db.EmploymentRelationships.SingleAsync(value =>
                    value.RelationshipId == relationshipId
                )
            ).State
        );
        var alert = await db.CustomerAlerts.SingleAsync(value => value.TenantId == tenant);
        Assert.Equal("ACTIONABLE", alert.AlertType);
        Assert.Contains("45 days", alert.DueMeaning);
        Assert.Contains("Hire your agent", alert.DueMeaning);
    }

    [Theory]
    [InlineData("ACTIVE")]
    [InlineData("CONVERTED")]
    [InlineData(null)]
    public async Task ATrialTheBillingOwnerDoesNotReportExpiredIsLeftRunning(string? billingStatus)
    {
        var (service, factory, tenant, relationshipId) = await CreateAsync(
            billingStatus,
            Now.AddHours(-1)
        );

        Assert.Equal(0, await service.EndDueTrialsAsync(default));

        await using var db = factory.CreateDbContext();
        Assert.Equal(
            EmploymentRelationshipState.TrialActive,
            (
                await db.EmploymentRelationships.SingleAsync(value =>
                    value.RelationshipId == relationshipId
                )
            ).State
        );
        Assert.Empty(
            await db.CustomerAlerts.Where(value => value.TenantId == tenant).ToListAsync()
        );
    }

    [Fact]
    public async Task ATrialThatHasNotReachedItsEndIsNotTouched()
    {
        var (service, _, _, _) = await CreateAsync("EXPIRED", Now.AddDays(3));

        Assert.Equal(0, await service.EndDueTrialsAsync(default));
    }
}
