using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentityPostgresServerFixture : IAsyncLifetime
{
    private PostgreSqlContainer? _postgres;
    private string _ownerConnectionString = string.Empty;

    public async Task InitializeAsync()
    {
        _postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("identity_fixture")
            .WithUsername("test_owner")
            .WithPassword("synthetic-owner-password")
            .Build();
        await _postgres.StartAsync();
        _ownerConnectionString = _postgres.GetConnectionString();
        await ExecuteOwnerAsync("""
            CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE constitutional_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE runtime_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE wbe_app LOGIN PASSWORD 'synthetic-app-password' NOSUPERUSER NOBYPASSRLS;
            """);
    }

    public async Task<string> CreateDatabaseAsync(string prefix)
    {
        var database = $"{prefix}_{Guid.NewGuid():N}";
        await ExecuteOwnerAsync($"CREATE DATABASE {database}");
        return new NpgsqlConnectionStringBuilder(_ownerConnectionString) { Database = database }.ConnectionString;
    }

    public async Task DropDatabaseAsync(string connectionString)
    {
        NpgsqlConnection.ClearAllPools();
        var database = new NpgsqlConnectionStringBuilder(connectionString).Database;
        await ExecuteOwnerAsync($"DROP DATABASE {database} WITH (FORCE)");
        await ExecuteOwnerAsync("DROP ROLE IF EXISTS identity_resolver_owner");
    }

    public async Task DisposeAsync()
    {
        if (_postgres is not null) await _postgres.DisposeAsync();
    }

    private async Task ExecuteOwnerAsync(string sql)
    {
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }
}