// Implements: WC-134 R006 runtime receipt migration ownership, replay and tenant binding.
// constitutional_basis: C-023, C-026, C-059, C-063
using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationRuntimeProjectionPostgresTests
{
    [Fact]
    public async Task MigrationReplayRetainsForcedRlsAndCompositeExecutionBinding()
    {
        await using var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await using (var setup = new NpgsqlCommand(
            """
            CREATE ROLE bp_owner NOBYPASSRLS;
            CREATE ROLE business_app LOGIN PASSWORD 'synthetic-runtime-test' NOBYPASSRLS;
            CREATE SCHEMA business;
            CREATE SCHEMA constitutional;
            CREATE SCHEMA ai_runtime;
            GRANT USAGE, CREATE ON SCHEMA business TO bp_owner;
            GRANT USAGE ON SCHEMA business TO business_app;
            CREATE TABLE business.conversation_executions (
                execution_id uuid PRIMARY KEY, tenant_id uuid NOT NULL,
                completion_reason text, created_at timestamptz NOT NULL DEFAULT now()
            );
            GRANT SELECT, INSERT, UPDATE, DELETE ON business.conversation_executions TO business_app;
            CREATE TABLE constitutional.employment_dispatch_stops (
                tenant_id uuid NOT NULL, relationship_ref text NOT NULL
            );
            CREATE FUNCTION ai_runtime.lock_employment_dispatch(uuid, text)
                RETURNS void LANGUAGE plpgsql AS $$ BEGIN RETURN; END $$;
            CREATE FUNCTION ai_runtime.employment_dispatch_relationship_key(text)
                RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
            """, owner))
            await setup.ExecuteNonQueryAsync();
        var migration = await File.ReadAllTextAsync(RepositoryPaths.Resolve(
            "infrastructure/postgres/init/87-wc134-runtime-event-projection.sql"));
        for (var replay = 0; replay < 2; replay++)
        {
            await using var apply = new NpgsqlCommand(migration, owner);
            await apply.ExecuteNonQueryAsync();
        }
        await using (var metadata = new NpgsqlCommand(
            """
            SELECT pg_get_userbyid(relowner), relrowsecurity, relforcerowsecurity
            FROM pg_class WHERE oid = 'business.conversation_runtime_event_receipts'::regclass
            """, owner))
        await using (var reader = await metadata.ExecuteReaderAsync())
        {
            Assert.True(await reader.ReadAsync());
            Assert.Equal("bp_owner", reader.GetString(0));
            Assert.True(reader.GetBoolean(1));
            Assert.True(reader.GetBoolean(2));
        }
        var tenant = Guid.NewGuid();
        var foreignTenant = Guid.NewGuid();
        var execution = Guid.NewGuid();
        var foreignExecution = Guid.NewGuid();
        await using (var seed = new NpgsqlCommand(
            """
            INSERT INTO business.conversation_executions (tenant_id, execution_id)
            VALUES (@tenant, @execution), (@foreign_tenant, @foreign_execution);
            INSERT INTO business.conversation_runtime_event_receipts
                (tenant_id, execution_id, sequence, event_digest, recorded_at)
            VALUES (@foreign_tenant, @foreign_execution, 1, @digest, now());
            """, owner))
        {
            seed.Parameters.AddWithValue("tenant", tenant);
            seed.Parameters.AddWithValue("execution", execution);
            seed.Parameters.AddWithValue("foreign_tenant", foreignTenant);
            seed.Parameters.AddWithValue("foreign_execution", foreignExecution);
            seed.Parameters.AddWithValue("digest", new string('a', 64));
            await seed.ExecuteNonQueryAsync();
        }
        await using var app = new NpgsqlConnection(new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app", Password = "synthetic-runtime-test",
            Options = $"-c app.current_tenant_id={tenant:D}",
        }.ConnectionString);
        await app.OpenAsync();
        await using (var visible = new NpgsqlCommand("SELECT count(*) FROM business.conversation_runtime_event_receipts", app))
            Assert.Equal(0L, await visible.ExecuteScalarAsync());
        await using (var foreignKey = InsertReceipt(app, tenant, foreignExecution))
        {
            var error = await Assert.ThrowsAsync<PostgresException>(() => foreignKey.ExecuteNonQueryAsync());
            Assert.Equal(PostgresErrorCodes.ForeignKeyViolation, error.SqlState);
        }
        await using (var foreignRow = InsertReceipt(app, foreignTenant, foreignExecution))
        {
            var error = await Assert.ThrowsAsync<PostgresException>(() => foreignRow.ExecuteNonQueryAsync());
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, error.SqlState);
        }
        await using (var valid = InsertReceipt(app, tenant, execution))
            Assert.Equal(1, await valid.ExecuteNonQueryAsync());
        await using (var delete = new NpgsqlCommand(
            "DELETE FROM business.conversation_executions WHERE tenant_id = @tenant AND execution_id = @execution", app))
        {
            delete.Parameters.AddWithValue("tenant", tenant);
            delete.Parameters.AddWithValue("execution", execution);
            await delete.ExecuteNonQueryAsync();
        }
        await using (var afterCascade = new NpgsqlCommand("SELECT count(*) FROM business.conversation_runtime_event_receipts", app))
            Assert.Equal(0L, await afterCascade.ExecuteScalarAsync());
    }

    private static NpgsqlCommand InsertReceipt(NpgsqlConnection connection, Guid tenant, Guid execution)
    {
        var command = new NpgsqlCommand(
            """
            INSERT INTO business.conversation_runtime_event_receipts
                (tenant_id, execution_id, sequence, event_digest, recorded_at)
            VALUES (@tenant, @execution, 1, @digest, now())
            """, connection);
        command.Parameters.AddWithValue("tenant", tenant);
        command.Parameters.AddWithValue("execution", execution);
        command.Parameters.AddWithValue("digest", new string('a', 64));
        return command;
    }
}
