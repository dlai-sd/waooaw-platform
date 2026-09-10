// Implements: WC-087, infrastructure/postgres/init/31-agent-instance-binding.sql
// constitutional_basis: C-005, C-007, C-023, C-026, C-059

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration31PostgresIntegrationTests : IAsyncLifetime
{
    private PostgreSqlContainer? _container;
    private string _connectionString = string.Empty;
    private readonly Guid _legacyRelationshipId = Guid.NewGuid();

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword("wc086testpass")
            .Build();
        await _container.StartAsync();
        _connectionString = _container.GetConnectionString();
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        await ExecuteAsync(connection, "CREATE SCHEMA IF NOT EXISTS business;");
        await ExecuteAsync(connection, """
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'business_app') THEN
                    CREATE ROLE business_app;
                END IF;
            END $$;
            GRANT USAGE ON SCHEMA business TO business_app;
            """);
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/19-ae01-employment-relationship.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/25-agent-admission.sql");
        await ExecuteAsync(connection, $"""
            INSERT INTO business.employment_relationships
                (relationship_id, tenant_id, professional_type, evaluation_intent_id,
                 initiating_participant_id)
            VALUES ('{_legacyRelationshipId:D}', gen_random_uuid(), 'DMA', gen_random_uuid(), gen_random_uuid());
            """);
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/31-agent-instance-binding.sql");
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    [Fact]
    public async Task InstanceBindingIsGloballyUniqueAndImmutable()
    {
        var tenantId = Guid.NewGuid();
        var admissionId = Guid.NewGuid();
        var inactiveAdmissionId = Guid.NewGuid();
        var instanceId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        await ExecuteAsync(connection, $"""
            INSERT INTO business.agent_admissions
                (admission_id, tenant_id, professional_type_id, professional_version,
                 owner_subject_id, state)
            VALUES
                ('{admissionId:D}', '{tenantId:D}', 'DMA', '1.0.0', gen_random_uuid(), 'ACTIVE'),
                ('{inactiveAdmissionId:D}', '{Guid.NewGuid():D}', 'DMA', '1.0.0', gen_random_uuid(), 'APPROVED');

            INSERT INTO business.employment_relationships
                (relationship_id, tenant_id, agent_instance_id, professional_admission_id,
                 professional_type, professional_version, evaluation_intent_id,
                 initiating_participant_id)
            VALUES
                ('{relationshipId:D}', '{tenantId:D}', '{instanceId:D}', '{admissionId:D}',
                 'DMA', '1.0.0', gen_random_uuid(), gen_random_uuid());
            """);

        await using (var activeCommand = connection.CreateCommand())
        {
            activeCommand.CommandText =
                "SELECT business.is_active_professional_admission(@admission_id, @professional_type, @professional_version)";
            activeCommand.Parameters.AddWithValue("admission_id", admissionId);
            activeCommand.Parameters.AddWithValue("professional_type", "DMA");
            activeCommand.Parameters.AddWithValue("professional_version", "1.0.0");
            Assert.True((bool)(await activeCommand.ExecuteScalarAsync())!);
        }

        var duplicate = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(connection, $"""
            INSERT INTO business.employment_relationships
                (tenant_id, agent_instance_id, professional_admission_id, professional_type,
                 professional_version, evaluation_intent_id, initiating_participant_id)
            VALUES ('{Guid.NewGuid():D}', '{instanceId:D}', '{admissionId:D}', 'DMA', '1.0.0',
                gen_random_uuid(), gen_random_uuid());
            """));
        Assert.Equal(PostgresErrorCodes.UniqueViolation, duplicate.SqlState);

        await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(connection, $"""
            INSERT INTO business.employment_relationships
                (tenant_id, professional_admission_id, professional_type, professional_version,
                 evaluation_intent_id, initiating_participant_id)
            VALUES ('{tenantId:D}', '{inactiveAdmissionId:D}', 'DMA', '1.0.0',
                gen_random_uuid(), gen_random_uuid());
            """));

        var mutation = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(connection, $"""
            UPDATE business.employment_relationships
            SET agent_instance_id = gen_random_uuid()
            WHERE relationship_id = '{relationshipId:D}';
            """));
        Assert.Contains("immutable", mutation.MessageText);
    }

    [Fact]
    public async Task ExistingRelationshipReceivesStableInstanceIdentity()
    {
        await using var connection = new NpgsqlConnection(_connectionString);
        await connection.OpenAsync();
        await using var command = connection.CreateCommand();
        command.CommandText = """
            SELECT agent_instance_id, agent_instance_minted_at, professional_admission_id,
                   professional_version
            FROM business.employment_relationships
            WHERE relationship_id = @relationship_id;
            """;
        command.Parameters.AddWithValue("relationship_id", _legacyRelationshipId);
        await using var reader = await command.ExecuteReaderAsync();

        Assert.True(await reader.ReadAsync());
        Assert.NotEqual(Guid.Empty, reader.GetGuid(0));
        Assert.False(reader.IsDBNull(1));
        Assert.True(reader.IsDBNull(2));
        Assert.True(reader.IsDBNull(3));
    }

    private static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        await command.ExecuteNonQueryAsync();
    }

    private static async Task ExecuteFileAsync(NpgsqlConnection connection, string relativePath) =>
        await ExecuteAsync(connection, await File.ReadAllTextAsync(RepositoryPaths.Resolve(relativePath)));
}