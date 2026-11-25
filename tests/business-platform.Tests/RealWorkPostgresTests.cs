// Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R005, WC170-R007, WC170-R008
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, C-076
// IB: IB-170

using System.Text.Json;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Services.RealWork;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>
/// Applies the real WC-170 init file and proves with the application role that the record store is append-only,
/// idempotent per key, gapless per relationship and isolated per tenant.
/// </summary>
public sealed class RealWorkPostgresTests : IAsyncLifetime
{
    private const string Migration =
        "infrastructure/postgres/init/99zzzzzzzz-wc170-01-real-work-records.sql";

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("real_work")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    private string RuntimeConnectionString =>
        new NpgsqlConnectionStringBuilder(_postgres.GetConnectionString())
        {
            Username = "bp_runtime",
            Password = "synthetic-runtime-password",
        }.ConnectionString;

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        await ExecuteAsAdminAsync(
            """
            CREATE ROLE business_app NOLOGIN;
            CREATE ROLE bp_owner NOLOGIN;
            CREATE ROLE bp_runtime LOGIN PASSWORD 'synthetic-runtime-password' IN ROLE business_app;
            GRANT bp_owner TO test_owner;
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            """
        );
        // Idempotent: applying the file twice must leave the same schema.
        await ExecuteAsAdminAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration)));
        await ExecuteAsAdminAsync(await File.ReadAllTextAsync(RepositoryPaths.Resolve(Migration)));
    }

    public async Task DisposeAsync() => await _postgres.DisposeAsync();

    [Fact]
    public void AppendIsIdempotentGaplessAndConflictsOnADifferentPayload()
    {
        var ledger = new PostgresRealWorkLedger(RuntimeConnectionString);
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;

        var first = ledger.Append(tenant, relationship, "TIMELINE", "k1", Json("""{"a":1}"""), now);
        var replay = ledger.Append(
            tenant,
            relationship,
            "TIMELINE",
            "k1",
            Json("""{ "a": 1 }"""),
            now
        );
        var second = ledger.Append(tenant, relationship, "CLAIM", "k2", Json("""{"a":2}"""), now);

        Assert.Equal(1, first.Sequence);
        Assert.Equal(first.RecordId, replay.RecordId);
        Assert.Equal(2, second.Sequence);
        Assert.Equal(
            "REAL_WORK_IDEMPOTENCY_CONFLICT",
            Assert
                .Throws<RealWorkConflictException>(() =>
                    ledger.Append(tenant, relationship, "TIMELINE", "k1", Json("""{"a":9}"""), now)
                )
                .Code
        );
        Assert.Equal(2, ledger.List(tenant, relationship).Count);
        Assert.Single(ledger.List(tenant, relationship, "CLAIM"));
    }

    [Fact]
    public void ARecordIsInvisibleToAnotherTenantAndNeverRewritten()
    {
        var ledger = new PostgresRealWorkLedger(RuntimeConnectionString);
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        ledger.Append(
            tenant,
            relationship,
            "ARTIFACT",
            "k",
            Json("""{"a":1}"""),
            DateTimeOffset.UtcNow
        );

        Assert.Empty(ledger.List(Guid.NewGuid(), relationship));
        using var connection = new NpgsqlConnection(RuntimeConnectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();
        using var scope = new NpgsqlCommand(
            $"SELECT set_config('app.current_tenant_id', '{tenant:D}', true)",
            connection,
            transaction
        );
        scope.ExecuteScalar();
        using var update = new NpgsqlCommand(
            "UPDATE business.real_work_records SET kind = 'CLAIM'",
            connection,
            transaction
        );
        var failure = Assert.Throws<PostgresException>(() => update.ExecuteNonQuery());
        Assert.Equal("42501", failure.SqlState);
    }

    private async Task ExecuteAsAdminAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private static JsonElement Json(string text)
    {
        using var document = JsonDocument.Parse(text);
        return document.RootElement.Clone();
    }
}
