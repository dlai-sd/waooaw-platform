// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S12
// Constitutional basis: C-002, C-005, C-007, C-027, C-059, C-063

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.Extensions.Options;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentitySecurityEventPostgresTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("identity_security_events")
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
        await OwnerAsync(
            "CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;"
        );
        await OwnerAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/38-identity-security-events.sql"
                )
            )
        );
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    [Fact]
    public async Task Writer_IsIdempotentOpaqueAndInsertOnly()
    {
        var options = new DbContextOptionsBuilder<IdentityDbContext>()
            .UseNpgsql(AppConnection)
            .Options;
        var factory = new PooledDbContextFactory<IdentityDbContext>(options);
        var service = new IdentitySecurityEventService(
            factory,
            Options.Create(
                new IdentityHmacOptions
                {
                    Key = "test-only-postgres-identity-event-key-32-bytes",
                }
            ),
            Options.Create(new IdentityEnvironmentOptions { Environment = "local" })
        );
        var input = new IdentitySecurityEventInput(
            Guid.NewGuid(),
            "postgres:callback-1",
            "CALLBACK_SUCCESS",
            "FACEBOOK",
            "SUCCEEDED",
            "BROKER_CALLBACK_VALID",
            "AAL2",
            "BUSINESS_PLATFORM",
            "issuer\u001fprovider-subject",
            "browser-session"
        );

        Assert.True(await service.RecordAsync(input, CancellationToken.None));
        Assert.False(await service.RecordAsync(input, CancellationToken.None));

        await using (var owner = new NpgsqlConnection(_postgres.GetConnectionString()))
        {
            await owner.OpenAsync();
            await using var command = new NpgsqlCommand(
                "SELECT count(*), min(length(actor_ref)), min(length(session_ref)) FROM institutional.identity_security_events",
                owner
            );
            await using var reader = await command.ExecuteReaderAsync();
            Assert.True(await reader.ReadAsync());
            Assert.Equal(1L, reader.GetInt64(0));
            Assert.Equal(64, reader.GetInt32(1));
            Assert.Equal(64, reader.GetInt32(2));
        }

        await using (var owner = new NpgsqlConnection(_postgres.GetConnectionString()))
        {
            await owner.OpenAsync();
            await using var command = new NpgsqlCommand(
                "SELECT reference_key_version, retention_class, retain_until >= occurred_at + INTERVAL '400 days' FROM institutional.identity_security_events",
                owner
            );
            await using var reader = await command.ExecuteReaderAsync();
            Assert.True(await reader.ReadAsync());
            Assert.Equal("v1", reader.GetString(0));
            Assert.Equal("SECURITY_400D", reader.GetString(1));
            Assert.True(reader.GetBoolean(2));
        }

        foreach (var statement in new[]
        {
            "UPDATE institutional.identity_security_events SET outcome = 'FAILED'",
            "DELETE FROM institutional.identity_security_events",
            "TRUNCATE institutional.identity_security_events",
        })
        {
            await using var app = new NpgsqlConnection(AppConnection);
            await app.OpenAsync();
            await using var command = new NpgsqlCommand(statement, app);
            await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync());
        }

        await using (var app = new NpgsqlConnection(AppConnection))
        {
            await app.OpenAsync();
            await using var command = new NpgsqlCommand(
                "SELECT count(*) FROM institutional.identity_security_events",
                app
            );
            var exception = await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteScalarAsync());
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, exception.SqlState);
        }

        await OwnerAsync("""
            INSERT INTO institutional.identity_security_event_legal_holds(
                hold_event_id, reference_key_version, action, authority_ref, reason_code)
            VALUES (gen_random_uuid(), 'v1', 'APPLY', repeat('a', 64), 'ACTIVE_INVESTIGATION')
            """);
        Assert.True(await OwnerScalarAsync<bool>(
            "SELECT legal_hold_active AND NOT eligible_for_key_destruction FROM institutional.identity_security_event_key_retirement WHERE reference_key_version = 'v1'"
        ));
        await OwnerAsync("""
            INSERT INTO institutional.identity_security_event_legal_holds(
                hold_event_id, reference_key_version, action, authority_ref, reason_code, occurred_at)
            VALUES (gen_random_uuid(), 'v1', 'RELEASE', repeat('b', 64), 'INVESTIGATION_CLOSED', NOW() + INTERVAL '1 second')
            """);
        Assert.False(await OwnerScalarAsync<bool>(
            "SELECT legal_hold_active FROM institutional.identity_security_event_key_retirement WHERE reference_key_version = 'v1'"
        ));
        await using (var owner = new NpgsqlConnection(_postgres.GetConnectionString()))
        {
            await owner.OpenAsync();
            await using var command = new NpgsqlCommand(
                "DELETE FROM institutional.identity_security_event_legal_holds",
                owner
            );
            await Assert.ThrowsAsync<PostgresException>(() => command.ExecuteNonQueryAsync());
        }
    }

    private async Task OwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private async Task<T> OwnerScalarAsync<T>(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (T)(await command.ExecuteScalarAsync())!;
    }
}
