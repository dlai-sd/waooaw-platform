// Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R015-R016
// constitutional_basis: C-002, C-023, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class MyAgentsSelectionServiceTests
{
    [Fact]
    public async Task TrialSelectionIsHashedBoundAndConsumedOnce()
    {
        var (service, factory, clock, tenantId, actorId, relationshipId) = await CreateTrialAsync();

        var created = await service.CreateAsync(
            tenantId,
            actorId,
            relationshipId,
            "TRIAL_STARTED",
            CancellationToken.None
        );

        Assert.Equal(64, created.Handle.Length);
        Assert.Equal(clock.GetUtcNow().AddMinutes(5), created.ExpiresAt);
        Assert.DoesNotContain(
            relationshipId.ToString(),
            created.Handle,
            StringComparison.OrdinalIgnoreCase
        );
        await using (var db = factory.CreateDbContext())
        {
            var stored = await db.MyAgentsSelectionFlash.SingleAsync();
            Assert.NotEqual(created.Handle, stored.HandleHash);
            Assert.Equal(stored.CreatedAt.AddMinutes(5), stored.ExpiresAt);
        }
        var consumed = await service.ConsumeAsync(
            tenantId,
            actorId,
            created.Handle,
            CancellationToken.None
        );
        var replayed = await service.ConsumeAsync(
            tenantId,
            actorId,
            created.Handle,
            CancellationToken.None
        );

        Assert.Equal(relationshipId, consumed?.RelationshipId);
        Assert.Equal("TRIAL_STARTED", consumed?.OutcomeKind);
        Assert.Null(replayed);
    }

    [Fact]
    public async Task ForeignActorCannotConsumeSelection()
    {
        var (service, _, _, tenantId, actorId, relationshipId) = await CreateTrialAsync();
        var created = await service.CreateAsync(
            tenantId,
            actorId,
            relationshipId,
            "TRIAL_STARTED",
            CancellationToken.None
        );

        Assert.Null(
            await service.ConsumeAsync(
                tenantId,
                Guid.NewGuid(),
                created.Handle,
                CancellationToken.None
            )
        );
        Assert.NotNull(
            await service.ConsumeAsync(tenantId, actorId, created.Handle, CancellationToken.None)
        );
    }

    [Fact]
    public async Task ExpiredSelectionCannotBeConsumed()
    {
        var (service, _, clock, tenantId, actorId, relationshipId) = await CreateTrialAsync();
        var created = await service.CreateAsync(
            tenantId,
            actorId,
            relationshipId,
            "TRIAL_STARTED",
            CancellationToken.None
        );
        clock.Advance(TimeSpan.FromMinutes(5));

        Assert.Null(
            await service.ConsumeAsync(tenantId, actorId, created.Handle, CancellationToken.None)
        );
    }

    [Fact]
    public async Task RevokedRelationshipAccessCannotBeConsumed()
    {
        var (service, factory, _, tenantId, actorId, relationshipId) = await CreateTrialAsync();
        var created = await service.CreateAsync(
            tenantId,
            actorId,
            relationshipId,
            "TRIAL_STARTED",
            CancellationToken.None
        );
        await using (var db = factory.CreateDbContext())
        {
            var participant = await db.RelationshipParticipants.SingleAsync();
            participant.Status = "REVOKED";
            await db.SaveChangesAsync();
        }

        Assert.Null(
            await service.ConsumeAsync(tenantId, actorId, created.Handle, CancellationToken.None)
        );
    }

    [Fact]
    public async Task OutcomeMustMatchDurableRelationshipState()
    {
        var (service, _, _, tenantId, actorId, relationshipId) = await CreateTrialAsync();

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.CreateAsync(
                tenantId,
                actorId,
                relationshipId,
                "HIRE_PAID",
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ArgumentException>(() =>
            service.CreateAsync(tenantId, actorId, relationshipId, "PAID", CancellationToken.None)
        );
    }

    [Fact]
    public async Task SelectionRequiresExistingAuthorizedRelationship()
    {
        var (service, _, _, tenantId, actorId, relationshipId) = await CreateTrialAsync();

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.CreateAsync(
                tenantId,
                actorId,
                Guid.NewGuid(),
                "TRIAL_STARTED",
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.CreateAsync(
                tenantId,
                Guid.NewGuid(),
                relationshipId,
                "TRIAL_STARTED",
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task TrialSelectionRequiresActiveTrialEvidence()
    {
        var (service, factory, _, tenantId, actorId, relationshipId) = await CreateTrialAsync();
        await using (var db = factory.CreateDbContext())
        {
            var trial = await db.RelationshipTrialBindings.SingleAsync();
            trial.Status = "EXPIRED";
            await db.SaveChangesAsync();
        }

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.CreateAsync(
                tenantId,
                actorId,
                relationshipId,
                "TRIAL_STARTED",
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task MalformedSelectionHandlesAreRejectedBeforeLookup()
    {
        var (service, _, _, tenantId, actorId, _) = await CreateTrialAsync();

        Assert.Null(await service.ConsumeAsync(tenantId, actorId, "short", CancellationToken.None));
        Assert.Null(
            await service.ConsumeAsync(
                tenantId,
                actorId,
                new string('z', 64),
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData("HIRE_PAID")]
    [InlineData("HIRE_ZERO_PRICE")]
    public async Task HireSelectionAcceptsAuthoritativeConfiguringRelationship(string outcomeKind)
    {
        var (service, factory, _, tenantId, actorId, relationshipId) = await CreateTrialAsync();
        await using (var db = factory.CreateDbContext())
        {
            var relationship = await db.EmploymentRelationships.SingleAsync();
            db.Entry(relationship).Property(value => value.AcquisitionMode).CurrentValue = "HIRE";
            relationship.State = EmploymentRelationshipState.Configuring;
            await db.SaveChangesAsync();
        }

        var created = await service.CreateAsync(
            tenantId,
            actorId,
            relationshipId,
            outcomeKind,
            CancellationToken.None
        );
        var consumed = await service.ConsumeAsync(
            tenantId,
            actorId,
            created.Handle,
            CancellationToken.None
        );

        Assert.Equal(outcomeKind, consumed?.OutcomeKind);
    }

    [Fact]
    public async Task AuthorizedRelationshipsRemainLatestFirst()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var older = await relationships.AdmitAsync(
            tenantId,
            actorId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        var newer = await relationships.AdmitAsync(
            tenantId,
            actorId,
            Guid.NewGuid(),
            "DPA",
            Guid.NewGuid(),
            CancellationToken.None
        );
        await using (var db = factory.CreateDbContext())
        {
            (
                await db.EmploymentRelationships.SingleAsync(value =>
                    value.RelationshipId == older.Relationship.RelationshipId
                )
            ).UpdatedAt = new DateTimeOffset(2026, 9, 28, 11, 0, 0, TimeSpan.Zero);
            (
                await db.EmploymentRelationships.SingleAsync(value =>
                    value.RelationshipId == newer.Relationship.RelationshipId
                )
            ).UpdatedAt = new DateTimeOffset(2026, 9, 28, 12, 0, 0, TimeSpan.Zero);
            await db.SaveChangesAsync();
        }

        var page = await relationships.ListAuthorizedAsync(
            tenantId,
            actorId,
            null,
            20,
            CancellationToken.None
        );

        Assert.Equal(
            [newer.Relationship.RelationshipId, older.Relationship.RelationshipId],
            page.Items.Select(value => value.Relationship.RelationshipId)
        );
    }

    private static async Task<(
        MyAgentsSelectionService Service,
        InMemoryEmploymentRelationshipFactory Factory,
        AdjustableTimeProvider Clock,
        Guid TenantId,
        Guid ActorId,
        Guid RelationshipId
    )> CreateTrialAsync()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var clock = new AdjustableTimeProvider(
            new DateTimeOffset(2026, 9, 28, 12, 0, 0, TimeSpan.Zero)
        );
        var tenantId = Guid.NewGuid();
        var actorId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(
            new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                InitiatingParticipantId = actorId,
                ProfessionalType = "DMA",
                AcquisitionMode = "TRIAL",
                State = EmploymentRelationshipState.TrialActive,
            }
        );
        db.RelationshipParticipants.Add(
            new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = actorId,
                Role = RelationshipParticipantRole.Evaluator,
                BoundEvidenceId = Guid.NewGuid(),
            }
        );
        db.RelationshipTrialBindings.Add(
            new RelationshipTrialBinding
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                CustomerId = actorId,
                CorrelationId = Guid.NewGuid(),
                TrialId = Guid.NewGuid(),
                StartsAt = clock.GetUtcNow(),
                ExpiresAt = clock.GetUtcNow().AddDays(14),
                Status = "ACTIVE",
            }
        );
        await db.SaveChangesAsync();
        return (
            new MyAgentsSelectionService(factory, clock),
            factory,
            clock,
            tenantId,
            actorId,
            relationshipId
        );
    }
}

internal sealed class AdjustableTimeProvider(DateTimeOffset now) : TimeProvider
{
    private DateTimeOffset _now = now;

    public override DateTimeOffset GetUtcNow() => _now;

    public void Advance(TimeSpan duration) => _now += duration;
}
