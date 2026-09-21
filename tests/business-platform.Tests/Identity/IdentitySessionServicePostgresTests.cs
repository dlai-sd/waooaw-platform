// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S07, §AUTH-S11
// Constitutional basis: C-001, C-007, C-026, C-059, C-063

using Microsoft.EntityFrameworkCore;
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
        Assert.Single(await service.ListAsync(account, first, CancellationToken.None));
        Assert.Equal(1, await service.RevokeAllAsync(account, "issuer\u001factor", "revoke-all:test", CancellationToken.None));
        Assert.Empty(await service.ListAsync(account, first, CancellationToken.None));

        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            service.ObserveAsync(account, "issuer\u001factor", "unseen-old-session", issuedAt, expiresAt, "AAL2", "GOOGLE", CancellationToken.None));
        await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            service.ObserveAsync(account, "issuer\u001factor", "session-one", issuedAt, expiresAt, "AAL2", "GOOGLE", CancellationToken.None));

        Assert.Equal(4L, await OwnerScalarAsync("SELECT count(*) FROM institutional.identity_security_events"));
    }

    private IdentitySessionService CreateService()
    {
        var options = new DbContextOptionsBuilder<IdentityDbContext>().UseNpgsql(AppConnection).Options;
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
