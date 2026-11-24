// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004, WC137-R005
// constitutional_basis: C-009, C-023, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.PlatformAccess;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.PlatformAccess;

public sealed class PlatformAccessStorePostgresTests : IAsyncLifetime
{
    private static readonly string[] Migrations =
    [
        "infrastructure/postgres/init/99zzzzzzzz-wc137-01-platform-access.sql",
        "infrastructure/postgres/init/99zzzzzzzz-wc167-01-founder-subject-release-event.sql",
    ];
    private static readonly DateTimeOffset Now = new(2026, 11, 22, 9, 0, 0, TimeSpan.Zero);

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("platform_access")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    private PostgresPlatformAccessStore _store = null!;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsync("CREATE ROLE business_app; CREATE ROLE bp_owner; CREATE SCHEMA business AUTHORIZATION bp_owner;");
        await ApplyMigrationAsync();
        _store = NewStore(new PlatformAccessOptions());
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    private PostgresPlatformAccessStore NewStore(PlatformAccessOptions options) =>
        new(
            new PooledDbContextFactory<ConversationStoreDbContext>(
                new DbContextOptionsBuilder<ConversationStoreDbContext>()
                    .UseNpgsql(_postgres.GetConnectionString())
                    .Options
            ),
            Options.Create(options)
        );

    private static ConfiguredFounder Founder(string email, string? subject = null, bool rebindOnStart = false) =>
        new() { Email = email, Subject = subject, RebindOnStart = rebindOnStart };

    private async Task ApplyMigrationAsync()
    {
        foreach (var migration in Migrations)
            await ExecuteAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve(migration)));
    }

    private async Task ExecuteAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task<long> CountAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (long)(await command.ExecuteScalarAsync())!;
    }

    [Fact]
    public async Task MigrationIsIdempotentAndKeepsGrants()
    {
        await _store.ReconcileFoundersAsync([Founder("Owner@Example.org")], Now, default);
        await ApplyMigrationAsync();
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("owner@example.org", "subject-owner-1", Now, default));
    }

    [Fact]
    public async Task ConfiguredFounderIsReassertedAfterAnEmptyDatabaseAndIsNeverDuplicated()
    {
        var founders = new[] { Founder("Owner@Example.org") };
        await _store.ReconcileFoundersAsync(founders, Now, default);
        await _store.ReconcileFoundersAsync(founders, Now.AddMinutes(1), default);
        Assert.Equal(1, await CountAsync("SELECT count(*) FROM business.platform_role_grants WHERE revoked_at IS NULL"));

        // A Demo database reset recreates empty tables; the next start restores the Founder.
        await ExecuteAsync("DROP TABLE business.platform_role_grants, business.platform_access_requests, business.platform_access_events;");
        await ApplyMigrationAsync();
        await _store.ReconcileFoundersAsync(founders, Now.AddHours(1), default);
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("OWNER@example.org", "subject-owner-1", Now, default));
    }

    [Fact]
    public async Task FounderSubjectIsBoundOnFirstSignInAndAnotherSubjectGetsNothing()
    {
        await _store.ReconcileFoundersAsync([Founder("owner@example.org")], Now, default);
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("owner@example.org", "subject-owner-1", Now, default));
        Assert.Empty(await _store.ResolveRolesAsync("owner@example.org", "subject-intruder", Now, default));
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("owner@example.org", "subject-owner-1", Now, default));
        Assert.Equal(1, await CountAsync("SELECT count(*) FROM business.platform_access_events WHERE event_type='FOUNDER_SUBJECT_BOUND'"));
    }

    [Fact]
    public async Task OptInFounderSubjectIsReleasedAtEveryStartAndTheNextVerifiedSignInTiesItAgain()
    {
        var founders = new[] { Founder("owner@example.org", rebindOnStart: true) };
        await _store.ReconcileFoundersAsync(founders, Now, default);
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("owner@example.org", "old-subject-1", Now, default));

        // A redeploy gives the person a new sign-in identity; the old tie must not lock the Founder out.
        await _store.ReconcileFoundersAsync(founders, Now.AddHours(1), default);
        Assert.Equal(1, await CountAsync("SELECT count(*) FROM business.platform_access_events WHERE event_type='FOUNDER_SUBJECT_RELEASED'"));
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("owner@example.org", "new-subject-1", Now.AddHours(1), default));
        Assert.Empty(await _store.ResolveRolesAsync("owner@example.org", "intruder-subject", Now.AddHours(1), default));
        Assert.Empty(await _store.ResolveRolesAsync("owner@example.org", "old-subject-1", Now.AddHours(1), default));
    }

    [Fact]
    public async Task ReleaseOnlyHappensWhenOptedInAndNeverForAConfiguredSubjectOrAnotherPersonsGrant()
    {
        var founders = new[] { Founder("strict@example.org"), Founder("other@example.org", rebindOnStart: true) };
        await _store.ReconcileFoundersAsync(founders, Now, default);
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("strict@example.org", "strict-subject", Now, default));
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("other@example.org", "other-subject", Now, default));

        await _store.ReconcileFoundersAsync(founders, Now.AddHours(1), default);
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("strict@example.org", "strict-subject", Now, default));
        Assert.Empty(await _store.ResolveRolesAsync("strict@example.org", "someone-else-1", Now, default));
        Assert.Equal(1, await CountAsync("SELECT count(*) FROM business.platform_access_events WHERE event_type='FOUNDER_SUBJECT_RELEASED'"));
    }

    [Fact]
    public async Task ConfiguredSubjectIsEnforcedFromTheFirstSignIn()
    {
        await _store.ReconcileFoundersAsync([Founder("owner@example.org", "configured-subject")], Now, default);
        Assert.Empty(await _store.ResolveRolesAsync("owner@example.org", "someone-else-1", Now, default));
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("owner@example.org", "configured-subject", Now, default));
        await _store.ReconcileFoundersAsync([Founder("owner@example.org", "rotated-subject")], Now, default);
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("owner@example.org", "rotated-subject", Now, default));
        Assert.Empty(await _store.ResolveRolesAsync("owner@example.org", "configured-subject", Now, default));
    }

    [Fact]
    public async Task FounderRemovedFromConfigurationLosesPowerButAnEmptyListChangesNothing()
    {
        await _store.ReconcileFoundersAsync([Founder("a-owner@example.org"), Founder("b-owner@example.org")], Now, default);
        await _store.ReconcileFoundersAsync([], Now, default);
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("b-owner@example.org", "subject-b-0001", Now, default));
        await _store.ReconcileFoundersAsync([Founder("a-owner@example.org")], Now, default);
        Assert.Empty(await _store.ResolveRolesAsync("b-owner@example.org", "subject-b-0001", Now, default));
        Assert.Equal(["founder"], await _store.ResolveRolesAsync("a-owner@example.org", "subject-a-0001", Now, default));
    }

    [Fact]
    public async Task ApprovedRequestBecomesATimeLimitedGrantAndRevocationRemovesIt()
    {
        var (created, requestId) = await _store.CreateRequestAsync("subject-admin-1", "Admin@Example.org", "pricing_admin", "I maintain the price list.", Now, default);
        Assert.Equal(AccessRequestResult.Created, created);
        Assert.Empty(await _store.ResolveRolesAsync("admin@example.org", "subject-admin-1", Now, default));

        Assert.Equal(AccessDecisionResult.Decided, await _store.DecideAsync(requestId!.Value, true, "Owner@Example.org", "Known colleague", Now, default));
        Assert.Equal(["pricing_admin"], await _store.ResolveRolesAsync("admin@example.org", "subject-admin-1", Now, default));
        Assert.Empty(await _store.ResolveRolesAsync("admin@example.org", "another-subject", Now, default));
        Assert.Empty(await _store.ResolveRolesAsync("admin@example.org", "subject-admin-1", Now.AddDays(91), default));

        var grant = Assert.Single(await _store.ListGrantsAsync(Now, default));
        Assert.Equal(AccessRevocationResult.Revoked, await _store.RevokeAsync(grant.GrantId, "owner@example.org", "Left the team", Now, default));
        Assert.Empty(await _store.ResolveRolesAsync("admin@example.org", "subject-admin-1", Now, default));
        Assert.Equal(AccessRevocationResult.NotFound, await _store.RevokeAsync(grant.GrantId, "owner@example.org", "again", Now, default));
        Assert.Equal(3, await CountAsync("SELECT count(*) FROM business.platform_access_events"));
    }

    [Fact]
    public async Task RejectedRequestGrantsNothingAndCannotBeDecidedTwice()
    {
        var (_, requestId) = await _store.CreateRequestAsync("subject-admin-1", "admin@example.org", "admission_reviewer", "Reviewing admissions.", Now, default);
        Assert.Equal(AccessDecisionResult.Decided, await _store.DecideAsync(requestId!.Value, false, "owner@example.org", "Not needed", Now, default));
        Assert.Equal(AccessDecisionResult.NotPending, await _store.DecideAsync(requestId.Value, true, "owner@example.org", null, Now, default));
        Assert.Equal(AccessDecisionResult.NotFound, await _store.DecideAsync(Guid.NewGuid(), true, "owner@example.org", null, Now, default));
        Assert.Empty(await _store.ResolveRolesAsync("admin@example.org", "subject-admin-1", Now, default));
        var listed = Assert.Single(await _store.ListRequestsAsync("REJECTED", "subject-admin-1", 10, default));
        Assert.Equal("Not needed", listed.DecisionReason);
        Assert.Empty(await _store.ListRequestsAsync("PENDING", null, 10, default));
    }

    [Fact]
    public async Task PeopleCannotApproveTheirOwnRequestOrKeepTwoOpenRequests()
    {
        var (_, requestId) = await _store.CreateRequestAsync("subject-admin-1", "admin@example.org", "pricing_admin", "I maintain the price list.", Now, default);
        Assert.Equal(AccessRequestResult.AlreadyPending, (await _store.CreateRequestAsync("subject-admin-1", "admin@example.org", "admission_operator", "Second request.....", Now, default)).Result);
        Assert.Equal(AccessDecisionResult.SelfApproval, await _store.DecideAsync(requestId!.Value, true, "ADMIN@example.org", null, Now, default));
        Assert.Equal(AccessDecisionResult.Decided, await _store.DecideAsync(requestId.Value, false, "admin@example.org", null, Now, default));
    }

    [Fact]
    public async Task AbuseLimitsStopRepeatedRequestsAndAFullBacklog()
    {
        for (var attempt = 0; attempt < 3; attempt++)
        {
            var (result, id) = await _store.CreateRequestAsync("subject-abuser-1", "abuser@example.org", "pricing_admin", "Please grant me access.", Now.AddMinutes(attempt), default);
            Assert.Equal(AccessRequestResult.Created, result);
            await _store.DecideAsync(id!.Value, false, "owner@example.org", null, Now, default);
        }
        Assert.Equal(AccessRequestResult.RateLimited, (await _store.CreateRequestAsync("subject-abuser-1", "abuser@example.org", "pricing_admin", "Please grant me access.", Now.AddHours(1), default)).Result);
        Assert.Equal(AccessRequestResult.Created, (await _store.CreateRequestAsync("subject-abuser-1", "abuser@example.org", "pricing_admin", "Please grant me access.", Now.AddHours(25), default)).Result);

        var small = NewStore(new PlatformAccessOptions { MaximumPendingRequests = 1 });
        Assert.Equal(AccessRequestResult.BacklogFull, (await small.CreateRequestAsync("subject-other-01", "other@example.org", "pricing_admin", "Please grant me access.", Now.AddHours(25), default)).Result);
    }

    [Fact]
    public async Task ARoleAlreadyHeldCannotBeRequestedAgain()
    {
        var (_, id) = await _store.CreateRequestAsync("subject-admin-1", "admin@example.org", "pricing_admin", "I maintain the price list.", Now, default);
        await _store.DecideAsync(id!.Value, true, "owner@example.org", null, Now, default);
        Assert.Equal(AccessRequestResult.AlreadyGranted, (await _store.CreateRequestAsync("subject-admin-1", "admin@example.org", "pricing_admin", "I maintain the price list.", Now.AddMinutes(1), default)).Result);
    }

    [Fact]
    public async Task ConfiguredFounderCannotBeRevokedThroughTheApplication()
    {
        await _store.ReconcileFoundersAsync([Founder("owner@example.org")], Now, default);
        var grant = Assert.Single(await _store.ListGrantsAsync(Now, default));
        Assert.Equal(AccessRevocationResult.ProtectedFounder, await _store.RevokeAsync(grant.GrantId, "owner@example.org", "no", Now, default));
    }

    [Fact]
    public async Task TheDatabaseRefusesAFounderGrantedByApprovalAndEditsToTheEventTrail()
    {
        await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(
            "INSERT INTO business.platform_role_grants(grant_id,email_normalized,role,source,granted_by,granted_at) VALUES (gen_random_uuid(),'x@example.org','founder','APPROVAL','a',now())"));
        await _store.ReconcileFoundersAsync([Founder("owner@example.org")], Now, default);
        await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync("SET ROLE business_app; DELETE FROM business.platform_access_events;"));
        await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync("SET ROLE business_app; UPDATE business.platform_access_events SET actor='x';"));
    }
}
