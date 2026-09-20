// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S12
// Constitutional basis: C-002, C-005, C-007, C-027, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentitySecurityEventServiceTests
{
    [Fact]
    public async Task RecordAsync_AcceptsEveryRequiredEventType()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString());
        var service = CreateService(factory);

        foreach (var eventType in IdentitySecurityEventService.EventTypes)
        {
            Assert.True(await service.RecordAsync(
                new IdentitySecurityEventInput(
                    Guid.NewGuid(), $"taxonomy:{eventType}", eventType, "INTERNAL", "ATTEMPTED",
                    "TAXONOMY_QUALIFIED", "UNKNOWN", "BUSINESS_PLATFORM"
                ),
                CancellationToken.None
            ));
        }

        await using var db = factory.CreateDbContext();
        Assert.Equal(IdentitySecurityEventService.EventTypes.Count, await db.SecurityEvents.CountAsync());
        Assert.Equal(
            IdentitySecurityEventService.EventTypes.Order(),
            (await db.SecurityEvents.Select(value => value.EventType).ToListAsync()).Order()
        );
    }

    [Fact]
    public async Task RecordAsync_PersistsOnlyOpaqueActorAndSessionReferences()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString());
        var service = CreateService(factory);
        var correlationId = Guid.NewGuid();

        var inserted = await service.RecordAsync(
            new IdentitySecurityEventInput(
                correlationId,
                "callback:synthetic-1",
                "CALLBACK_SUCCESS",
                "GOOGLE",
                "SUCCEEDED",
                "BROKER_CALLBACK_VALID",
                "AAL2",
                "BUSINESS_PLATFORM",
                "issuer\u001fraw-provider-subject",
                "raw-session-identifier"
            ),
            CancellationToken.None
        );

        Assert.True(inserted);
        await using var db = factory.CreateDbContext();
        var record = Assert.Single(await db.SecurityEvents.ToListAsync());
        Assert.Equal(correlationId, record.CorrelationId);
        Assert.Equal(64, record.ActorRef!.Length);
        Assert.Equal(64, record.SessionRef!.Length);
        Assert.DoesNotContain("raw-provider-subject", record.ActorRef, StringComparison.Ordinal);
        Assert.DoesNotContain("raw-session-identifier", record.SessionRef, StringComparison.Ordinal);
        Assert.Equal("local", record.Environment);
        Assert.Equal("business-platform", record.WriterService);
    }

    [Theory]
    [InlineData("UNKNOWN_EVENT", "GOOGLE", "SUCCEEDED", "VALID_REASON")]
    [InlineData("CALLBACK_SUCCESS", "UNBOUNDED_PROVIDER", "SUCCEEDED", "VALID_REASON")]
    [InlineData("CALLBACK_SUCCESS", "GOOGLE", "MAYBE", "VALID_REASON")]
    [InlineData("CALLBACK_SUCCESS", "GOOGLE", "SUCCEEDED", "raw detail")]
    public async Task RecordAsync_RejectsValuesOutsideThePrivacySafeTaxonomy(
        string eventType,
        string providerClass,
        string outcome,
        string reasonCode
    )
    {
        var service = CreateService(new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString()));

        await Assert.ThrowsAsync<ArgumentException>(() =>
            service.RecordAsync(
                new IdentitySecurityEventInput(
                    Guid.NewGuid(),
                    "synthetic:invalid",
                    eventType,
                    providerClass,
                    outcome,
                    reasonCode,
                    "AAL2",
                    "BUSINESS_PLATFORM"
                ),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public void Migration_DefinesAppendOnlyInsertOnlyOperationalStore()
    {
        var sql = File.ReadAllText(
            RepositoryPaths.Resolve("infrastructure/postgres/init/38-identity-security-events.sql")
        );

        Assert.Contains("institutional.identity_security_events", sql, StringComparison.Ordinal);
        Assert.Contains("UNIQUE (source_boundary, source_event_id)", sql, StringComparison.Ordinal);
        Assert.Contains("BEFORE UPDATE OR DELETE", sql, StringComparison.Ordinal);
        Assert.Contains("BEFORE TRUNCATE", sql, StringComparison.Ordinal);
        Assert.Contains("GRANT INSERT", sql, StringComparison.Ordinal);
        Assert.DoesNotContain("GRANT UPDATE", sql, StringComparison.Ordinal);
        Assert.DoesNotContain("GRANT DELETE", sql, StringComparison.Ordinal);
        foreach (var forbidden in new[] { "password", "access_token", "refresh_token", "raw_email", "tenant_id", "remote_address", "user_agent" })
            Assert.DoesNotContain(forbidden, sql, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task RecordAsync_PropagatesPersistenceFailureWithoutReportingSuccess()
    {
        var factory = new InMemoryIdentityDbContextFactory(
            Guid.NewGuid().ToString(),
            new RejectIdentitySecurityEventWriteInterceptor()
        );

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            CreateService(factory).RecordAsync(
                new IdentitySecurityEventInput(
                    Guid.NewGuid(), "synthetic:failure", "AUTHORIZATION_DENIAL", "INTERNAL",
                    "DENIED", "POLICY_DENIED", "AAL2", "BUSINESS_PLATFORM"
                ),
                CancellationToken.None
            )
        );
    }

    private static IdentitySecurityEventService CreateService(
        IDbContextFactory<IdentityDbContext> factory
    ) =>
        new(
            factory,
            Options.Create(
                new IdentityHmacOptions
                {
                    Key = "test-only-identity-security-event-key-32-bytes",
                }
            ),
            Options.Create(new IdentityEnvironmentOptions { Environment = "local" })
        );
}

internal sealed class RejectIdentitySecurityEventWriteInterceptor : Microsoft.EntityFrameworkCore.Diagnostics.SaveChangesInterceptor
{
    public override ValueTask<Microsoft.EntityFrameworkCore.Diagnostics.InterceptionResult<int>> SavingChangesAsync(
        Microsoft.EntityFrameworkCore.Diagnostics.DbContextEventData eventData,
        Microsoft.EntityFrameworkCore.Diagnostics.InterceptionResult<int> result,
        CancellationToken cancellationToken = default
    ) => throw new InvalidOperationException("Synthetic identity event store failure.");
}
