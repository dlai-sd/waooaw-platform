// Implements: infrastructure/postgres/init/33-wc095-relationship-checkout.sql
// Constitutional basis: C-005, C-007, C-023, C-059, C-063, C-088

using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration33PostgresIntegrationTests : IAsyncLifetime
{
    private const string Password = "wc095testpass";
    private PostgreSqlContainer? _container;
    private string _ownerConnectionString = string.Empty;
    private string _businessConnectionString = string.Empty;

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword(Password)
            .Build();
        await _container.StartAsync();
        _ownerConnectionString = _container.GetConnectionString();
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();
        await ExecuteAsync(connection, "CREATE SCHEMA IF NOT EXISTS business; CREATE SCHEMA IF NOT EXISTS payload_store;");
        await ExecuteAsync(connection, $"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'business_app') THEN
                    CREATE ROLE business_app LOGIN PASSWORD '{Password}';
                END IF;
            END $$;
            GRANT USAGE ON SCHEMA business, payload_store TO business_app;
            """);
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/19-ae01-employment-relationship.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/21b-ae01-contract-activation.sql");
        await ExecuteFileAsync(connection, "infrastructure/postgres/init/33-wc095-relationship-checkout.sql");
        _businessConnectionString = new NpgsqlConnectionStringBuilder(_ownerConnectionString)
        {
            Username = "business_app",
            Password = Password,
        }.ConnectionString;
    }

    public async Task DisposeAsync()
    {
        if (_container is not null) await _container.DisposeAsync();
    }

    [Fact]
    public async Task CheckoutIntentIsExactContractBoundTerminalImmutableAndTenantIsolated()
    {
        var tenantId = Guid.NewGuid();
        var otherTenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var contractId = Guid.NewGuid();
        var contractAcceptanceId = Guid.NewGuid();
        var paymentConsentEvidenceId = Guid.NewGuid();
        var intentId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(_ownerConnectionString))
        {
            await owner.OpenAsync();
            await ExecuteAsync(owner, $"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id, initiating_participant_id)
                VALUES ('{relationshipId:D}', '{tenantId:D}', 'DMA', gen_random_uuid(), gen_random_uuid());
                INSERT INTO business.employment_contract_versions
                    (contract_id, tenant_id, relationship_id, version, contract_hash, aeec_version,
                     domain_schedule_hash, configuration_snapshot_json, price_tax_summary_json,
                     created_by_participant_id)
                VALUES ('{contractId:D}', '{tenantId:D}', '{relationshipId:D}', 1, repeat('a', 64),
                    '1.0', repeat('b', 64), jsonb_build_object(), jsonb_build_object(), gen_random_uuid());
                INSERT INTO business.relationship_checkout_intents
                    (checkout_intent_id, tenant_id, relationship_id, contract_id, contract_version,
                     contract_hash, contract_acceptance_id, payment_consent_evidence_id,
                     idempotency_key, material_request_hash)
                VALUES ('{intentId:D}', '{tenantId:D}', '{relationshipId:D}', '{contractId:D}', 1,
                    repeat('a', 64), '{contractAcceptanceId:D}', '{paymentConsentEvidenceId:D}',
                    '{idempotencyKey:D}', repeat('c', 64));
                UPDATE business.relationship_checkout_intents
                SET status = 'COMPLETED', outcome_kind = 'FULLY_DISCOUNTED',
                    outcome_json = jsonb_build_object('outcomeKind', 'FULLY_DISCOUNTED'), completed_at = NOW()
                WHERE checkout_intent_id = '{intentId:D}';
                """);

            var duplicate = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner, $"""
                INSERT INTO business.relationship_checkout_intents
                    (checkout_intent_id, tenant_id, relationship_id, contract_id, contract_version,
                     contract_hash, contract_acceptance_id, payment_consent_evidence_id,
                     idempotency_key, material_request_hash)
                VALUES (gen_random_uuid(), '{tenantId:D}', '{relationshipId:D}', '{contractId:D}', 1,
                    repeat('a', 64), '{contractAcceptanceId:D}', '{paymentConsentEvidenceId:D}',
                    '{idempotencyKey:D}', repeat('c', 64));
                """));
            Assert.Equal(PostgresErrorCodes.UniqueViolation, duplicate.SqlState);

            var terminalUpdate = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner,
                $"UPDATE business.relationship_checkout_intents SET outcome_kind = 'OUTCOME_UNRESOLVED' WHERE checkout_intent_id = '{intentId:D}';"));
            Assert.Contains("terminal relationship checkout intent is immutable", terminalUpdate.MessageText);
            var delete = await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(owner,
                $"DELETE FROM business.relationship_checkout_intents WHERE checkout_intent_id = '{intentId:D}';"));
            Assert.Contains("append-only", delete.MessageText);
        }

        await using var business = new NpgsqlConnection(_businessConnectionString);
        await business.OpenAsync();
        await ExecuteAsync(business, $"SET app.current_tenant_id = '{otherTenantId:D}';");
        await using var command = business.CreateCommand();
        command.CommandText = "SELECT count(*) FROM business.relationship_checkout_intents WHERE checkout_intent_id = @intent_id";
        command.Parameters.AddWithValue("intent_id", intentId);
        Assert.Equal(0L, (long)(await command.ExecuteScalarAsync())!);
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
