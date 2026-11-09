// Implements: WC-134 R006/R009 durable dispatch Stop admission and result fencing.
// Constitutional basis: C-001, C-005, C-023, C-059
using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentDispatchStopPostgresTests
{
    [Fact]
    public async Task StopSerializesWithAdmissionAndRemainsTenantScopedAcrossRestart()
    {
        await using var postgres = new PostgreSqlBuilder("pgvector/pgvector:pg16").Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        var password = Guid.NewGuid().ToString("N");
        await ExecuteAsync(owner, $"""
            CREATE ROLE bp_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE ce_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE air_owner NOLOGIN NOSUPERUSER NOBYPASSRLS;
            CREATE ROLE migration_user LOGIN NOSUPERUSER NOBYPASSRLS CREATEROLE PASSWORD '{password}';
            GRANT bp_owner, ce_owner, air_owner TO migration_user WITH ADMIN OPTION;
            CREATE ROLE business_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
            CREATE ROLE ai_runtime_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
            CREATE ROLE constitutional_app LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '{password}';
            CREATE SCHEMA business AUTHORIZATION bp_owner;
            CREATE SCHEMA ai_runtime AUTHORIZATION air_owner;
            CREATE SCHEMA constitutional AUTHORIZATION ce_owner;
            GRANT USAGE ON SCHEMA constitutional TO constitutional_app;
            CREATE TABLE business.relationship_emergency_stop_latches (
                tenant_id UUID NOT NULL,
                relationship_id UUID NOT NULL,
                PRIMARY KEY (tenant_id, relationship_id)
            );
            ALTER TABLE business.relationship_emergency_stop_latches OWNER TO bp_owner;
            ALTER TABLE business.relationship_emergency_stop_latches ENABLE ROW LEVEL SECURITY;
            ALTER TABLE business.relationship_emergency_stop_latches FORCE ROW LEVEL SECURITY;
            CREATE POLICY tenant ON business.relationship_emergency_stop_latches
                USING (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid)
                WITH CHECK (tenant_id = nullif(current_setting('app.current_tenant_id', true), '')::uuid);
            GRANT USAGE ON SCHEMA business TO business_app;
            GRANT INSERT ON business.relationship_emergency_stop_latches TO business_app;
            """);
        var historicalTenant = Guid.NewGuid();
        var historicalRelationship = Guid.NewGuid();
        await ExecuteAsync(owner,
            $"INSERT INTO business.relationship_emergency_stop_latches VALUES ('{historicalTenant:D}', '{historicalRelationship:D}')");
        await using var migrator = AppConnection(postgres.GetConnectionString(), "migration_user", password);
        await migrator.OpenAsync();
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve("infrastructure/postgres/init/85-wc134-employment-dispatch-stop-fence.sql"));
        await ExecuteAsync(migrator, migration);
        await ExecuteAsync(migrator, migration);
        var evidenceMigration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve("infrastructure/postgres/init/86-wc134-constitutional-stop-evidence.sql"));
        await ExecuteAsync(migrator, evidenceMigration);
        await ExecuteAsync(migrator, evidenceMigration);
        await using (var backfilled = new NpgsqlCommand(
            $"SELECT count(*) FROM constitutional.employment_dispatch_stops WHERE tenant_id = '{historicalTenant:D}' AND relationship_ref = '{historicalRelationship:D}'", owner))
            Assert.Equal(1L, await backfilled.ExecuteScalarAsync());
        await using (var migrationPolicy = new NpgsqlCommand(
            "SELECT count(*) FROM pg_policies WHERE policyname = 'wc134_dispatch_stop_backfill'", owner))
            Assert.Equal(0L, await migrationPolicy.ExecuteScalarAsync());
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        await using var air = AppConnection(postgres.GetConnectionString(), "ai_runtime_app", password);
        await using var bp = AppConnection(postgres.GetConnectionString(), "business_app", password);
        await air.OpenAsync();
        await bp.OpenAsync();
        await ExecuteAsync(bp, $"SELECT set_config('app.current_tenant_id', '{tenant:D}', false)");
        await using var admission = await air.BeginTransactionAsync();
        await ExecuteAsync(air, $"SELECT set_config('app.current_tenant_id', '{tenant:D}', true)");
        await ExecuteAsync(air, $"SELECT ai_runtime.lock_employment_dispatch('{tenant:D}', '{relationship:D}')");
        var stop = ExecuteAsync(bp,
            $"INSERT INTO business.relationship_emergency_stop_latches VALUES ('{tenant:D}', '{relationship:D}')");
        var deadline = DateTimeOffset.UtcNow.AddSeconds(10);
        var waiting = false;
        while (DateTimeOffset.UtcNow < deadline)
        {
            await using var check = new NpgsqlCommand(
                $"SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid = {bp.ProcessID} AND NOT granted)", owner);
            waiting = (bool)(await check.ExecuteScalarAsync())!;
            if (waiting) break;
            await Task.Delay(10);
        }
        Assert.True(waiting);
        Assert.False(stop.IsCompleted);
        await admission.CommitAsync();
        await stop.WaitAsync(TimeSpan.FromSeconds(10));
        await using var restarted = AppConnection(postgres.GetConnectionString(), "ai_runtime_app", password);
        await restarted.OpenAsync();
        await ExecuteAsync(restarted, $"SELECT set_config('app.current_tenant_id', '{tenant:D}', false)");
        await using (var stopped = new NpgsqlCommand(
            $"SELECT count(*) FROM constitutional.employment_dispatch_stops WHERE relationship_ref = ai_runtime.employment_dispatch_relationship_key('{relationship.ToString("D").ToUpperInvariant()}')", restarted))
            Assert.Equal(1L, await stopped.ExecuteScalarAsync());
        await ExecuteAsync(restarted,
            $"SELECT set_config('app.current_tenant_id', '{Guid.NewGuid():D}', false)");
        await using (var isolated = new NpgsqlCommand("SELECT count(*) FROM constitutional.employment_dispatch_stops", restarted))
            Assert.Equal(0L, await isolated.ExecuteScalarAsync());
        await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(restarted,
            $"SELECT ai_runtime.lock_employment_dispatch('{tenant:D}', '{relationship:D}')"));

        await using var ce = AppConnection(postgres.GetConnectionString(), "constitutional_app", password);
        await ce.OpenAsync();
        await ExecuteAsync(ce, $"SELECT set_config('app.current_tenant_id', '{tenant:D}', false)");
        var evidence = Guid.NewGuid();
        await using (var transaction = await ce.BeginTransactionAsync())
        {
            await ExecuteAsync(ce, $"SELECT ai_runtime.lock_employment_dispatch('{tenant:D}', '{relationship:D}')");
            await ExecuteAsync(ce,
                $"INSERT INTO constitutional.employment_dispatch_stops VALUES ('{tenant:D}', '{relationship:D}', now()) ON CONFLICT DO NOTHING");
            await ExecuteAsync(ce, $"""
                INSERT INTO constitutional.emergency_stop_events
                VALUES ('{evidence:D}', '{tenant:D}', '{relationship:D}', 'synthetic-actor',
                    ARRAY['synthetic-execution'], now(), NULL, 'CUSTOMER_INITIATED')
                """);
            await transaction.CommitAsync();
        }
        await ExecuteAsync(ce,
            $"UPDATE constitutional.emergency_stop_events SET temporal_signalled_at = now() WHERE id = '{evidence:D}'");
        await Assert.ThrowsAsync<PostgresException>(() => ExecuteAsync(ce,
            $"UPDATE constitutional.emergency_stop_events SET initiated_by_user_id = 'changed' WHERE id = '{evidence:D}'"));
        await ExecuteAsync(ce, $"SELECT set_config('app.current_tenant_id', '{Guid.NewGuid():D}', false)");
        await using var foreignEvidence = new NpgsqlCommand("SELECT count(*) FROM constitutional.emergency_stop_events", ce);
        Assert.Equal(0L, await foreignEvidence.ExecuteScalarAsync());
    }

    private static NpgsqlConnection AppConnection(string owner, string role, string password) =>
        new(new NpgsqlConnectionStringBuilder(owner) { Username = role, Password = password }.ConnectionString);

    private static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }
}
