// Implements: architecture/reference/product/wc085-identity-provisioning-data-contract.md CURRENT Sections 1-7
// constitutional_basis: C-005, C-007, C-026, C-059

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class CustomerWorkspaceFullSchemaPostgresTests
{
    [Fact]
    public async Task FullInitChain_AppliesCustomerWorkspaceMigrationAndResolver()
    {
        var initDirectory = Path.GetDirectoryName(
            RepositoryPaths.Resolve("infrastructure/postgres/init/01-schemas.sql"))!;
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword("synthetic-full-schema-password")
            .WithResourceMapping(new DirectoryInfo(initDirectory), "/docker-entrypoint-initdb.d")
            .Build();

        await postgres.StartAsync();

        await using var connection = new NpgsqlConnection(postgres.GetConnectionString());
        await connection.OpenAsync();
        await using var command = new NpgsqlCommand("""
            SELECT
                to_regclass('identity.accounts') IS NOT NULL,
                to_regclass('identity.login_methods') IS NOT NULL,
                to_regclass('identity.actor_bindings') IS NOT NULL,
                to_regclass('identity.memberships') IS NOT NULL,
                to_regprocedure('identity.resolve_customer_membership()') IS NOT NULL
            """, connection);
        await using var reader = await command.ExecuteReaderAsync();

        Assert.True(await reader.ReadAsync());
        Assert.True(reader.GetBoolean(0));
        Assert.True(reader.GetBoolean(1));
        Assert.True(reader.GetBoolean(2));
        Assert.True(reader.GetBoolean(3));
        Assert.True(reader.GetBoolean(4));
    }
}