// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R001
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Npgsql;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Tests;

/// <summary>A leased Postgres with the provider registry applied exactly as the init files apply it (16, then WC-148).</summary>
internal sealed class ProviderRegistryDatabase : IAsyncDisposable
{
    public const string RegistryInit = "infrastructure/postgres/init/16-provider-registry.sql";
    public const string CredentialsInit =
        "infrastructure/postgres/init/99zzzzzzzz-wc148-01-provider-credentials.sql";
    public const string ConnectionsInit =
        "infrastructure/postgres/init/99zzzzzzzz-wc149-01-customer-provider-connections.sql";

    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
        .WithDatabase("provider_registry")
        .WithUsername("test_owner")
        .WithPassword("synthetic-owner-password")
        .Build();

    public static async Task<ProviderRegistryDatabase> CreateAsync(bool applyConnections = true)
    {
        var database = new ProviderRegistryDatabase();
        await database._postgres.StartAsync();
        await database.ExecuteAsync(
            "CREATE ROLE business_app; CREATE ROLE bp_owner; CREATE SCHEMA business AUTHORIZATION bp_owner;"
        );
        await database.ApplyAsync(RegistryInit);
        await database.ExecuteAsync("ALTER TABLE business.provider_configs OWNER TO bp_owner;");
        await database.ApplyAsync(CredentialsInit);
        if (applyConnections)
            await database.ApplyAsync(ConnectionsInit);
        return database;
    }

    public string ConnectionString => _postgres.GetConnectionString();

    public Task ApplyAsync(string relativePath) =>
        ExecuteAsync(File.ReadAllText(RepositoryPaths.Resolve(relativePath)));

    public IDbContextFactory<ProviderRegistryDbContext> Factory() =>
        new PooledDbContextFactory<ProviderRegistryDbContext>(
            new DbContextOptionsBuilder<ProviderRegistryDbContext>()
                .UseNpgsql(_postgres.GetConnectionString())
                .Options
        );

    public async Task ExecuteAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    public async Task<T> ScalarAsync<T>(string sql)
    {
        await using var connection = new NpgsqlConnection(_postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        return (T)(await command.ExecuteScalarAsync())!;
    }

    public ValueTask DisposeAsync() => _postgres.DisposeAsync();
}
