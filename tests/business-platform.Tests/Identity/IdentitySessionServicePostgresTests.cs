// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S07, §AUTH-S11
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R013, WC105-R014, WC105-R016
// Constitutional basis: C-001, C-007, C-026, C-059, C-063

using System.Data.Common;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Diagnostics;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentitySessionServicePostgresTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("identity_sessions")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    private string AppConnection => new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
    {
        Username = "business_app",
        Password = "synthetic-app-password",
    }.ConnectionString;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await OwnerAsync("CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS; CREATE SCHEMA business;");
        foreach (var migration in new[] { "38-identity-security-events.sql", "39-identity-sessions.sql" })
            await OwnerAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve($"infrastructure/postgres/init/{migration}")));
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    [Fact]
    public async Task Lifecycle_IsAccountScopedReplaySafeAndRejectsRevokedTokens()
    {
        var service = CreateService();
        var account = Guid.NewGuid();
        var otherAccount = Guid.NewGuid();
        var issuedAt = DateTimeOffset.UtcNow.AddMinutes(-2);
        var expiresAt = issuedAt.AddHours(1);
        var first = await service.ObserveAsync(account, "issuer\u001factor", "session-one", issuedAt, expiresAt, "AAL2", "GOOGLE", CancellationToken.None);
        var second = await service.ObserveAsync(account, "issuer\u001factor", "session-two", issuedAt, expiresAt, "AAL2", "FACEBOOK", CancellationToken.None);

        var sessions = await service.ListAsync(account, first, CancellationToken.None);
        Assert.Equal(2, sessions.Count);
        Assert.Single(sessions, value => value.Current);
        Assert.Empty(await service.ListAsync(otherAccount, Guid.NewGuid(), CancellationToken.None));

        Assert.Equal(1, await service.RevokeOneAsync(account, "issuer\u001factor", second, "revoke-one:test", CancellationToken.None));
        Assert.Equal(0, await service.RevokeOneAsync(account, "issuer\u001factor", second, "revoke-one:test", CancellationToken.None));
        await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
            service.RevokeOneAsync(otherAccount, "issuer\u001factor", first, "revoke-foreign:test", CancellationToken.None));
        Assert.Single(await service.ListAsync(account, first, CancellationToken.None));
        Assert.Equal(1, await service.RevokeAllAsync(account, "issuer\u001factor", "revoke-all:test", CancellationToken.None));
        Assert.Empty(await service.ListAsync(account, first, CancellationToken.None));

        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            service.ObserveAsync(account, "issuer\u001factor", "unseen-old-session", issuedAt, expiresAt, "AAL2", "GOOGLE", CancellationToken.None));
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            service.ObserveAsync(account, "issuer\u001factor", "session-one", issuedAt, expiresAt, "AAL2", "GOOGLE", CancellationToken.None));

        Assert.Equal(4L, await OwnerScalarAsync("SELECT count(*) FROM institutional.identity_security_events"));
    }

    [Fact]
    public async Task ObserveAsync_IsSafeUnderConcurrentReplay()
    {
        var commandFailures = new CommandFailureCounter();
        var service = CreateService(commandFailures);
        var account = Guid.NewGuid();
        var issuedAt = DateTimeOffset.UtcNow.AddMinutes(-2);
        var expiresAt = issuedAt.AddHours(1);

        var observations = await Task.WhenAll(
            Enumerable.Range(0, 8).Select(_ =>
                service.ObserveAsync(
                    account,
                    "issuer\u001factor",
                    "shared-session",
                    issuedAt,
                    expiresAt,
                    "AAL2",
                    "GOOGLE",
                    CancellationToken.None
                )
            )
        );

        Assert.Single(observations.Distinct());
        Assert.Equal(1L, await OwnerScalarAsync("SELECT count(*) FROM business.identity_sessions"));
        Assert.Equal(1L, await OwnerScalarAsync("SELECT count(*) FROM institutional.identity_security_events"));
        Assert.Equal(0, commandFailures.Count);
    }

    [Fact]
    public async Task SecurityEventRecordAsync_ConcurrentReplayUsesConflictFreeInsert()
    {
        var commandFailures = new CommandFailureCounter();
        var options = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(AppConnection)
            .AddInterceptors(commandFailures)
            .Options;
        var factory = new PooledDbContextFactory<IdentityDbContext>(options);
        var hmac = Options.Create(
            new IdentityHmacOptions { Key = "test-only-session-registry-hmac-key-32-bytes" }
        );
        var service = new IdentitySecurityEventService(
            factory,
            hmac,
            Options.Create(new IdentityEnvironmentOptions { Environment = "local" })
        );
        var sourceEventId = $"concurrent:{Guid.NewGuid():N}";
        var before = await OwnerScalarAsync(
            "SELECT count(*) FROM institutional.identity_security_events"
        );

        var results = await Task.WhenAll(
            Enumerable.Range(0, 16).Select(_ =>
                service.RecordAsync(
                    new IdentitySecurityEventInput(
                        Guid.NewGuid(),
                        sourceEventId,
                        "SESSION_ESTABLISHMENT",
                        "GOOGLE",
                        "SUCCEEDED",
                        "SESSION_ACTIVE",
                        "AAL2",
                        "BUSINESS_PLATFORM"
                    ),
                    CancellationToken.None
                )
            )
        );

        Assert.Single(results, inserted => inserted);
        Assert.Equal(15, results.Count(inserted => !inserted));
        Assert.Equal(
            before + 1,
            await OwnerScalarAsync("SELECT count(*) FROM institutional.identity_security_events")
        );
        Assert.Equal(0, commandFailures.Count);
    }

    private IdentitySessionService CreateService(params IInterceptor[] interceptors)
    {
        var options = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(AppConnection)
            .AddInterceptors(interceptors)
            .Options;
        var factory = new PooledDbContextFactory<IdentityDbContext>(options);
        var hmac = Options.Create(new IdentityHmacOptions { Key = "test-only-session-registry-hmac-key-32-bytes" });
        var environment = Options.Create(new IdentityEnvironmentOptions { Environment = "local" });
        return new IdentitySessionService(factory, new IdentitySecurityEventService(factory, hmac, environment), hmac);
    }

    private async Task OwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task<long> OwnerScalarAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (long)(await command.ExecuteScalarAsync())!;
    }
}

internal sealed class CommandFailureCounter : DbCommandInterceptor
{
    private int _count;

    public int Count => _count;

    public override Task CommandFailedAsync(
        DbCommand command,
        CommandErrorEventData eventData,
        CancellationToken cancellationToken = default
    )
    {
        Interlocked.Increment(ref _count);
        return Task.CompletedTask;
    }
}
