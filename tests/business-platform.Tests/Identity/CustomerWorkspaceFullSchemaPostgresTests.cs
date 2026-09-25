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
        await reader.DisposeAsync();

        await using var seedCommand = new NpgsqlCommand("""
            ALTER TABLE identity.accounts DISABLE TRIGGER ALL;
            INSERT INTO identity.accounts (
                account_id, initial_tenant_id, origin_registration_id, status
            ) VALUES (
                '10000000-0000-0000-0000-000000000001',
                '20000000-0000-0000-0000-000000000001',
                '30000000-0000-0000-0000-000000000001',
                'ACTIVE'
            );
            ALTER TABLE identity.accounts ENABLE TRIGGER ALL;
            INSERT INTO identity.memberships (
                membership_id, account_id, tenant_id, roles, status
            ) VALUES (
                '40000000-0000-0000-0000-000000000001',
                '10000000-0000-0000-0000-000000000001',
                '20000000-0000-0000-0000-000000000001',
                ARRAY['OWNER']::text[],
                'ACTIVE'
            );
            SELECT count(*),
                   bool_and(admission_content_digest ~ '^sha256:[0-9a-f]{64}$'),
                   bool_and(evidence_set_digest ~ '^sha256:[0-9a-f]{64}$'),
                   bool_and(artifact_digest ~ '^sha256:[0-9a-f]{64}$'),
                   bool_and(policy_version = 'demo-marketplace-admission-v1')
            FROM business.agent_admissions
            WHERE tenant_id = '20000000-0000-0000-0000-000000000001'
              AND professional_type_id = 'DIGITAL_MARKETING_LOCAL_SERVICE'
              AND professional_version = '1.0.0';
            """, connection);
        await using var seedReader = await seedCommand.ExecuteReaderAsync();

        Assert.True(await seedReader.ReadAsync());
        Assert.Equal(1, seedReader.GetInt64(0));
        Assert.True(seedReader.GetBoolean(1));
        Assert.True(seedReader.GetBoolean(2));
        Assert.True(seedReader.GetBoolean(3));
        Assert.True(seedReader.GetBoolean(4));
    }
}