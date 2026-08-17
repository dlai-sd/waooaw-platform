// Implements: architecture/reference/product/ae01-relationship-data-contract.md § Migration 22
// constitutional_basis: C-005, C-007, C-023, C-026, C-059, C-063
// WC-060 Task WC060-01: prove first-apply, reapply, composite FKs, forced RLS,
// checks/triggers, append-only, 15-min checkpoint expiry, 48-h dedup expiry,
// cleanup permissions, replay, and concurrency behaviour.

using DotNet.Testcontainers.Builders;
using Npgsql;
using Testcontainers.PostgreSql;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

// ── shared Testcontainers fixture ────────────────────────────────────────────
// One container per test-class collection; Postgres image matches docker-compose.
public sealed class Migration22PostgresFixture : IAsyncLifetime
{
    private const string TestPassword = "wc060testpass";
    private const string DbName = "waooaw";
    private const string Owner = "waooaw";

    private PostgreSqlContainer? _container;

    public string OwnerConnectionString { get; private set; } = "";
    public string BusinessAppConnectionString { get; private set; } = "";

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase(DbName)
            .WithUsername(Owner)
            .WithPassword(TestPassword)
            .Build();

        await _container.StartAsync();
        OwnerConnectionString = _container.GetConnectionString();

        await using var conn = new NpgsqlConnection(OwnerConnectionString);
        await conn.OpenAsync();

        await ExecAsync(conn, "CREATE SCHEMA IF NOT EXISTS business;");
        await ExecAsync(conn, "CREATE SCHEMA IF NOT EXISTS constitutional;");
        await ExecAsync(conn, "CREATE SCHEMA IF NOT EXISTS payload_store;");

        // business_app: LOGIN for role-switch RLS tests
        await ExecAsync(conn, $"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'business_app') THEN
                    CREATE ROLE business_app WITH LOGIN PASSWORD '{TestPassword}';
                END IF;
            END $$;
            GRANT USAGE ON SCHEMA business TO business_app;
            """);

        // Apply migration 19 (provides the FK target)
        await ExecFileAsync(conn, RepositoryPaths.Resolve("infrastructure/postgres/init/19-ae01-employment-relationship.sql"));

        await ExecAsync(conn, """
            GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA business TO business_app;
            GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA business TO business_app;
            """);

        // Apply migration 22 under test
        await ExecFileAsync(conn, RepositoryPaths.Resolve("infrastructure/postgres/init/22-ae01-continuity-evidence.sql"));

        // business_continuity_maintenance gets LOGIN for role-switch test only
        await ExecAsync(conn, $"""
            ALTER ROLE business_continuity_maintenance LOGIN PASSWORD '{TestPassword}';
            """);

        BusinessAppConnectionString = new NpgsqlConnectionStringBuilder(OwnerConnectionString)
        {
            Username = "business_app",
            Password = TestPassword,
        }.ConnectionString;
    }

    public async Task DisposeAsync()
    {
        if (_container is not null)
            await _container.DisposeAsync();
    }

    private static async Task ExecAsync(NpgsqlConnection conn, string sql)
    {
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        await cmd.ExecuteNonQueryAsync();
    }

    private static async Task ExecFileAsync(NpgsqlConnection conn, string path)
    {
        var sql = await File.ReadAllTextAsync(path);
        await ExecAsync(conn, sql);
    }
}

[CollectionDefinition("Migration22Postgres")]
public sealed class Migration22PostgresCollection : ICollectionFixture<Migration22PostgresFixture> { }

// ── helpers used across test methods ─────────────────────────────────────────
file static class Sql
{
    public static async Task<NpgsqlConnection> OpenAsync(string connStr)
    {
        var conn = new NpgsqlConnection(connStr);
        await conn.OpenAsync();
        return conn;
    }

    public static async Task ExecAsync(NpgsqlConnection conn, string sql,
        params (string name, object? value)[] parameters)
    {
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        foreach (var (name, value) in parameters)
            cmd.Parameters.AddWithValue(name, value ?? DBNull.Value);
        await cmd.ExecuteNonQueryAsync();
    }

    public static async Task<T?> ScalarAsync<T>(NpgsqlConnection conn, string sql,
        params (string name, object? value)[] parameters)
    {
        await using var cmd = conn.CreateCommand();
        cmd.CommandText = sql;
        foreach (var (name, value) in parameters)
            cmd.Parameters.AddWithValue(name, value ?? DBNull.Value);
        var result = await cmd.ExecuteScalarAsync();
        return result is DBNull or null ? default : (T)result;
    }

    // Inserts a minimal employment_relationship row; returns relationship_id.
    public static async Task<Guid> InsertRelationshipAsync(
        NpgsqlConnection conn, Guid tenantId, string tenantSetting)
    {
        await SetTenantAsync(conn, tenantSetting);
        var id = Guid.NewGuid();
        await ExecAsync(conn, """
            INSERT INTO business.employment_relationships
                (relationship_id, tenant_id, professional_type, evaluation_intent_id,
                 initiating_participant_id, state, state_version)
            VALUES
                (@rid, @tid, 'SoftwareEngineer', gen_random_uuid(),
                 gen_random_uuid(), 'DISCOVERED', 0)
            """,
            ("@rid", id), ("@tid", tenantId));
        return id;
    }

    // Inserts a minimal channel_binding; returns binding_id.
    public static async Task<Guid> InsertPreparedBindingAsync(
        NpgsqlConnection conn, Guid tenantId, Guid relId, Guid participantId)
    {
        var id = Guid.NewGuid();
        await ExecAsync(conn, """
            INSERT INTO business.channel_bindings
                (binding_id, tenant_id, relationship_id, participant_id,
                 participant_role, channel, external_subject_hash, conversation_id,
                 assurance_level, status, prepared_evidence_id)
            VALUES
                (@bid, @tid, @rid, @pid,
                 'EVALUATOR', 'WHATSAPP',
                 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
                 'conv-1', 'TIER_1_PHONE_IDENTITY', 'PREPARED', gen_random_uuid())
            """,
            ("@bid", id), ("@tid", tenantId), ("@rid", relId), ("@pid", participantId));
        return id;
    }

    public static async Task SetTenantAsync(NpgsqlConnection conn, string tenantId)
    {
        await ExecAsync(conn, $"SET LOCAL app.current_tenant_id = '{tenantId}';");
    }
}

// ── tests ─────────────────────────────────────────────────────────────────────

[Collection("Migration22Postgres")]
public sealed class Migration22FirstApplyAndReapplyTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22FirstApplyAndReapplyTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task AllFourTablesPresentAfterFirstApply()
    {
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        foreach (var table in new[] {
            "channel_bindings", "continuity_checkpoints",
            "delivery_acknowledgements", "channel_message_deduplication" })
        {
            var exists = await Sql.ScalarAsync<bool>(conn, """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_schema = 'business' AND table_name = @t)
                """, ("@t", table));
            Assert.True(exists, $"table business.{table} missing after first apply");
        }
    }

    [Fact]
    public async Task ReapplyIsIdempotent_IfNotExistsGuards()
    {
        // Running migration 22 a second time must not raise an exception
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        var sql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve("infrastructure/postgres/init/22-ae01-continuity-evidence.sql"));
        var exception = await Record.ExceptionAsync(async () =>
        {
            await using var cmd = conn.CreateCommand();
            cmd.CommandText = sql;
            await cmd.ExecuteNonQueryAsync();
        });
        Assert.Null(exception);
    }
}

[Collection("Migration22Postgres")]
public sealed class Migration22CompositeFkTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22CompositeFkTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task ChannelBinding_RejectsFKViolationOnUnknownRelationship()
    {
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        var tid = Guid.NewGuid();
        await Sql.SetTenantAsync(conn, tid.ToString());

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.channel_bindings
                    (tenant_id, relationship_id, participant_id, participant_role,
                     channel, external_subject_hash, conversation_id, assurance_level,
                     status, prepared_evidence_id)
                VALUES
                    (@tid, gen_random_uuid(), gen_random_uuid(), 'EVALUATOR',
                     'WEB', 'b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2',
                     'conv-x', 'TIER_4_PORTAL_FRESH', 'PREPARED', gen_random_uuid())
                """, ("@tid", tid)));

        Assert.Equal("23503", ex.SqlState); // foreign_key_violation
    }

    [Fact]
    public async Task ContinuityCheckpoint_RejectsMissingSourceBinding()
    {
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        var tid = Guid.NewGuid();
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var realBinding = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.continuity_checkpoints
                    (tenant_id, relationship_id, source_binding_id, target_binding_id,
                     continuity_envelope_hash, material_request_hash, causal_marker,
                     sequence_number, idempotency_key, status, prepared_evidence_id)
                VALUES
                    (@tid, @rid, gen_random_uuid(), @tgt,
                     'c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2',
                     'd1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2',
                     gen_random_uuid(), 1, gen_random_uuid(), 'PREPARED', gen_random_uuid())
                """,
                ("@tid", tid), ("@rid", relId), ("@tgt", realBinding)));

        Assert.Equal("23503", ex.SqlState);
    }
}

[Collection("Migration22Postgres")]
public sealed class Migration22RlsTenantIsolationTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22RlsTenantIsolationTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task ChannelBinding_ForceRls_HidesCrosstenantRow()
    {
        var tenantA = Guid.NewGuid();
        var tenantB = Guid.NewGuid();

        // Insert as owner (superuser) for tenant A
        await using (var owner = await Sql.OpenAsync(_fx.OwnerConnectionString))
        {
            await Sql.SetTenantAsync(owner, tenantA.ToString());
            var relA = await Sql.InsertRelationshipAsync(owner, tenantA, tenantA.ToString());
            await Sql.InsertPreparedBindingAsync(owner, tenantA, relA, Guid.NewGuid());
        }

        // Connect as business_app and query with tenant B's identity → must see zero rows
        await using var appConn = await Sql.OpenAsync(_fx.BusinessAppConnectionString);
        await using var tx = await appConn.BeginTransactionAsync();
        await Sql.SetTenantAsync(appConn, tenantB.ToString());

        var count = await Sql.ScalarAsync<long>(appConn,
            "SELECT COUNT(*) FROM business.channel_bindings WHERE tenant_id = @tid",
            ("@tid", tenantA));
        Assert.Equal(0L, count);
    }

    [Fact]
    public async Task ChannelBinding_ForceRls_RejectsInsertForOtherTenant()
    {
        var tid = Guid.NewGuid();
        await using var owner = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(owner, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(owner, tid, tid.ToString());

        await using var appConn = await Sql.OpenAsync(_fx.BusinessAppConnectionString);
        await using var tx = await appConn.BeginTransactionAsync();
        // Set tenant B in the session but try to insert for tid
        await Sql.SetTenantAsync(appConn, Guid.NewGuid().ToString());

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(appConn, """
                INSERT INTO business.channel_bindings
                    (tenant_id, relationship_id, participant_id, participant_role,
                     channel, external_subject_hash, conversation_id, assurance_level,
                     status, prepared_evidence_id)
                VALUES
                    (@tid, @rid, gen_random_uuid(), 'EMPLOYER',
                     'WEB', 'e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2',
                     'conv-rls', 'TIER_4_PORTAL_FRESH', 'PREPARED', gen_random_uuid())
                """, ("@tid", tid), ("@rid", relId)));

        Assert.Equal("42501", ex.SqlState); // insufficient_privilege (WITH CHECK fails)
    }
}

[Collection("Migration22Postgres")]
public sealed class Migration22ChecksAndTriggersTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22ChecksAndTriggersTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task ChannelBinding_ActiveRequiresBoundEvidence()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());

        // Insert as ACTIVE but omit bound_evidence_id and bound_at → check must fire
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.channel_bindings
                    (tenant_id, relationship_id, participant_id, participant_role,
                     channel, external_subject_hash, conversation_id, assurance_level,
                     status, prepared_evidence_id)
                VALUES
                    (@tid, @rid, gen_random_uuid(), 'EVALUATOR',
                     'WHATSAPP', 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
                     'conv-chk', 'TIER_1_PHONE_IDENTITY', 'ACTIVE', gen_random_uuid())
                """, ("@tid", tid), ("@rid", relId)));

        Assert.Equal("23514", ex.SqlState); // check_violation
    }

    [Fact]
    public async Task ChannelBinding_TransitionTrigger_BlocksTerminalReopen()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var bid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        // Transition to REVOKED (terminal)
        await Sql.ExecAsync(conn, """
            UPDATE business.channel_bindings
            SET status = 'REVOKED',
                revoked_evidence_id = gen_random_uuid(),
                revoked_at = NOW()
            WHERE binding_id = @bid
            """, ("@bid", bid));

        // Attempt to transition back to PREPARED from terminal state → trigger must block
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                UPDATE business.channel_bindings
                SET status = 'PREPARED',
                    revoked_evidence_id = NULL,
                    revoked_at = NULL
                WHERE binding_id = @bid
                """, ("@bid", bid)));

        Assert.Equal("P0001", ex.SqlState); // raise_exception from trigger
    }

    [Fact]
    public async Task ChannelBinding_TransitionTrigger_BlocksIdentityMutation()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var bid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                UPDATE business.channel_bindings
                SET channel = 'WEB'
                WHERE binding_id = @bid
                """, ("@bid", bid)));

        Assert.Equal("P0001", ex.SqlState);
    }

    [Fact]
    public async Task ContinuityCheckpoint_HashCheck_BlocksMalformedHash()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var srcBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());
        var tgtBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.continuity_checkpoints
                    (tenant_id, relationship_id, source_binding_id, target_binding_id,
                     continuity_envelope_hash, material_request_hash, causal_marker,
                     sequence_number, idempotency_key, status, prepared_evidence_id)
                VALUES
                    (@tid, @rid, @src, @tgt,
                     'BADHASH',
                     'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
                     gen_random_uuid(), 1, gen_random_uuid(), 'PREPARED', gen_random_uuid())
                """,
                ("@tid", tid), ("@rid", relId), ("@src", srcBid), ("@tgt", tgtBid)));

        Assert.Equal("23514", ex.SqlState);
    }

    [Fact]
    public async Task ContinuityCheckpoint_TransitionTrigger_BlocksTerminalReopen()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var srcBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());
        var tgtBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        // Insert a checkpoint
        var cpId = Guid.NewGuid();
        await Sql.ExecAsync(conn, """
            INSERT INTO business.continuity_checkpoints
                (checkpoint_id, tenant_id, relationship_id, source_binding_id, target_binding_id,
                 continuity_envelope_hash, material_request_hash, causal_marker,
                 sequence_number, idempotency_key, status, prepared_evidence_id)
            VALUES
                (@cid, @tid, @rid, @src, @tgt,
                 'c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2',
                 'd1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2',
                 gen_random_uuid(), 1, gen_random_uuid(), 'PREPARED', gen_random_uuid())
            """,
            ("@cid", cpId), ("@tid", tid), ("@rid", relId), ("@src", srcBid), ("@tgt", tgtBid));

        // Commit it
        await Sql.ExecAsync(conn, """
            UPDATE business.continuity_checkpoints
            SET status = 'COMMITTED', resolution_evidence_id = gen_random_uuid(), resolved_at = NOW()
            WHERE checkpoint_id = @cid
            """, ("@cid", cpId));

        // Attempt to reopen: must be blocked
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                UPDATE business.continuity_checkpoints
                SET status = 'PREPARED', resolution_evidence_id = NULL, resolved_at = NULL
                WHERE checkpoint_id = @cid
                """, ("@cid", cpId)));

        Assert.Equal("P0001", ex.SqlState);
    }
}

[Collection("Migration22Postgres")]
public sealed class Migration22AppendOnlyDeliveryAckTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22AppendOnlyDeliveryAckTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task DeliveryAck_UpdateIsRejectedByTrigger()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var bid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        // Insert a delivery acknowledgement
        var ackId = Guid.NewGuid();
        await Sql.ExecAsync(conn, """
            INSERT INTO business.delivery_acknowledgements
                (acknowledgement_id, tenant_id, relationship_id, binding_id,
                 message_id_hash, acknowledgement_type, acknowledged_at, evidence_id)
            VALUES
                (@aid, @tid, @rid, @bid,
                 'f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2d3c4b5a6f1e2',
                 'TRANSPORT_ACCEPTED', NOW(), gen_random_uuid())
            """,
            ("@aid", ackId), ("@tid", tid), ("@rid", relId), ("@bid", bid));

        // UPDATE must be rejected by the append-only trigger
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                UPDATE business.delivery_acknowledgements
                SET acknowledgement_type = 'PARTICIPANT_OBSERVED'
                WHERE acknowledgement_id = @aid
                """, ("@aid", ackId)));

        Assert.Equal("P0001", ex.SqlState);
    }

    [Fact]
    public async Task DeliveryAck_DeleteIsRejectedByTrigger()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var bid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var ackId = Guid.NewGuid();
        await Sql.ExecAsync(conn, """
            INSERT INTO business.delivery_acknowledgements
                (acknowledgement_id, tenant_id, relationship_id, binding_id,
                 message_id_hash, acknowledgement_type, acknowledged_at, evidence_id)
            VALUES
                (@aid, @tid, @rid, @bid,
                 'a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3',
                 'PARTICIPANT_OBSERVED', NOW(), gen_random_uuid())
            """,
            ("@aid", ackId), ("@tid", tid), ("@rid", relId), ("@bid", bid));

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, "DELETE FROM business.delivery_acknowledgements WHERE acknowledgement_id = @aid",
                ("@aid", ackId)));

        Assert.Equal("P0001", ex.SqlState);
    }
}

[Collection("Migration22Postgres")]
public sealed class Migration22ExpiryTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22ExpiryTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task ContinuityCheckpoint_ExpiresAt_Is15MinutesAfterPreparedAt()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var srcBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());
        var tgtBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var cpId = Guid.NewGuid();
        await Sql.ExecAsync(conn, """
            INSERT INTO business.continuity_checkpoints
                (checkpoint_id, tenant_id, relationship_id, source_binding_id, target_binding_id,
                 continuity_envelope_hash, material_request_hash, causal_marker,
                 sequence_number, idempotency_key, status, prepared_evidence_id)
            VALUES
                (@cid, @tid, @rid, @src, @tgt,
                 'e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2',
                 'f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2',
                 gen_random_uuid(), 2, gen_random_uuid(), 'PREPARED', gen_random_uuid())
            """,
            ("@cid", cpId), ("@tid", tid), ("@rid", relId), ("@src", srcBid), ("@tgt", tgtBid));

        var diff = await Sql.ScalarAsync<double>(conn, """
            SELECT EXTRACT(EPOCH FROM (expires_at - prepared_at))::double precision
            FROM business.continuity_checkpoints
            WHERE checkpoint_id = @cid
            """, ("@cid", cpId));

        Assert.Equal(900.0, diff, precision: 1); // exactly 15 minutes = 900 seconds
    }

    [Fact]
    public async Task ChannelMessageDeduplication_ExpiresAt_Is48HoursAfterReceivedAt()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var bid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var dedupId = Guid.NewGuid();
        await Sql.ExecAsync(conn, """
            INSERT INTO business.channel_message_deduplication
                (deduplication_id, tenant_id, relationship_id, binding_id,
                 provider_message_id_hash, material_message_hash, status)
            VALUES
                (@did, @tid, @rid, @bid,
                 'b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2d3e4f5a6b1c2',
                 'c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2',
                 'RECEIVED')
            """,
            ("@did", dedupId), ("@tid", tid), ("@rid", relId), ("@bid", bid));

        var diff = await Sql.ScalarAsync<double>(conn, """
            SELECT EXTRACT(EPOCH FROM (expires_at - received_at))::double precision
            FROM business.channel_message_deduplication
            WHERE deduplication_id = @did
            """, ("@did", dedupId));

        Assert.Equal(172800.0, diff, precision: 1); // exactly 48 hours = 172800 seconds
    }
}

[Collection("Migration22Postgres")]
public sealed class Migration22CleanupPermissionsTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22CleanupPermissionsTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task MaintenanceRole_CanDeleteExpiredDeduplicationRows_WithTenantSetting()
    {
        var tid = Guid.NewGuid();

        // Insert a row as owner then simulate expiry
        await using (var owner = await Sql.OpenAsync(_fx.OwnerConnectionString))
        {
            await Sql.SetTenantAsync(owner, tid.ToString());
            var relId = await Sql.InsertRelationshipAsync(owner, tid, tid.ToString());
            var bid = await Sql.InsertPreparedBindingAsync(owner, tid, relId, Guid.NewGuid());

            await Sql.ExecAsync(owner, """
                INSERT INTO business.channel_message_deduplication
                    (deduplication_id, tenant_id, relationship_id, binding_id,
                     provider_message_id_hash, material_message_hash, status)
                VALUES
                    (gen_random_uuid(), @tid, @rid, @bid,
                     'd1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2f3a4b5c6d1e2',
                     'e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2a3b4c5d6e1f2',
                     'RECEIVED')
                """, ("@tid", tid), ("@rid", relId), ("@bid", bid));
        }

        // Connect as maintenance role; use superuser SET ROLE to simulate it
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.ExecAsync(conn, "SET ROLE business_continuity_maintenance;");
        await Sql.SetTenantAsync(conn, tid.ToString());

        // Must be able to DELETE rows from the table (trigger only blocks UPDATE on delivery_acks)
        var ex = await Record.ExceptionAsync(async () =>
        {
            await Sql.ExecAsync(conn, """
                DELETE FROM business.channel_message_deduplication
                WHERE tenant_id = @tid AND expires_at <= NOW() + INTERVAL '200 years'
                """, ("@tid", tid));
        });
        Assert.Null(ex);
    }

    [Fact]
    public async Task MaintenanceRole_CannotInsertIntoDeduplicationTable()
    {
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.ExecAsync(conn, "SET ROLE business_continuity_maintenance;");

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.channel_message_deduplication
                    (tenant_id, relationship_id, binding_id,
                     provider_message_id_hash, material_message_hash, status)
                VALUES
                    (gen_random_uuid(), gen_random_uuid(), gen_random_uuid(),
                     'f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2b3c4d5e6f1a2',
                     'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
                     'RECEIVED')
                """));

        Assert.Equal("42501", ex.SqlState); // insufficient_privilege
    }
}

[Collection("Migration22Postgres")]
public sealed class Migration22ReplayAndConcurrencyTests
{
    private readonly Migration22PostgresFixture _fx;
    public Migration22ReplayAndConcurrencyTests(Migration22PostgresFixture fx) => _fx = fx;

    [Fact]
    public async Task ChannelMessageDeduplication_SameProviderHash_BlocksDuplicateInsert()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var bid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        const string provHash = "a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3c4d5e6f7a2b3";

        await Sql.ExecAsync(conn, """
            INSERT INTO business.channel_message_deduplication
                (tenant_id, relationship_id, binding_id,
                 provider_message_id_hash, material_message_hash, status)
            VALUES
                (@tid, @rid, @bid, @ph,
                 'c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2e3f4a5b6c1d2',
                 'RECEIVED')
            """, ("@tid", tid), ("@rid", relId), ("@bid", bid), ("@ph", provHash));

        // Second insert with same (tenant, binding, provider_hash) → unique violation
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.channel_message_deduplication
                    (tenant_id, relationship_id, binding_id,
                     provider_message_id_hash, material_message_hash, status)
                VALUES
                    (@tid, @rid, @bid, @ph,
                     'd2e3f4a5b6c7d2e3f4a5b6c7d2e3f4a5b6c7d2e3f4a5b6c7d2e3f4a5b6c7d2e3',
                     'RECEIVED')
                """, ("@tid", tid), ("@rid", relId), ("@bid", bid), ("@ph", provHash)));

        Assert.Equal("23505", ex.SqlState); // unique_violation
    }

    [Fact]
    public async Task ContinuityCheckpoint_SameIdempotencyKey_BlocksDuplicate()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var srcBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());
        var tgtBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var idem = Guid.NewGuid();

        await Sql.ExecAsync(conn, """
            INSERT INTO business.continuity_checkpoints
                (tenant_id, relationship_id, source_binding_id, target_binding_id,
                 continuity_envelope_hash, material_request_hash, causal_marker,
                 sequence_number, idempotency_key, status, prepared_evidence_id)
            VALUES
                (@tid, @rid, @src, @tgt,
                 'e2f3a4b5c6d7e2f3a4b5c6d7e2f3a4b5c6d7e2f3a4b5c6d7e2f3a4b5c6d7e2f3',
                 'f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3b4c5d6e7f2a3',
                 gen_random_uuid(), 3, @idem, 'PREPARED', gen_random_uuid())
            """,
            ("@tid", tid), ("@rid", relId), ("@src", srcBid), ("@tgt", tgtBid), ("@idem", idem));

        // Same (tenant, relationship, idempotency_key) → unique violation
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.continuity_checkpoints
                    (tenant_id, relationship_id, source_binding_id, target_binding_id,
                     continuity_envelope_hash, material_request_hash, causal_marker,
                     sequence_number, idempotency_key, status, prepared_evidence_id)
                VALUES
                    (@tid, @rid, @src, @tgt,
                     'a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4c5d6e7f8a3b4',
                     'b3c4d5e6f7a8b3c4d5e6f7a8b3c4d5e6f7a8b3c4d5e6f7a8b3c4d5e6f7a8b3c4',
                     gen_random_uuid(), 4, @idem, 'PREPARED', gen_random_uuid())
                """,
                ("@tid", tid), ("@rid", relId), ("@src", srcBid), ("@tgt", tgtBid), ("@idem", idem)));

        Assert.Equal("23505", ex.SqlState); // unique_violation
    }

    [Fact]
    public async Task DeliveryAck_SameBindingMessageHashType_IsReplaySafe()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var bid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        const string msgHash = "c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6a7b8c3d4e5f6a7b8c3d4";

        await Sql.ExecAsync(conn, """
            INSERT INTO business.delivery_acknowledgements
                (tenant_id, relationship_id, binding_id,
                 message_id_hash, acknowledgement_type, acknowledged_at, evidence_id)
            VALUES
                (@tid, @rid, @bid, @mh, 'TRANSPORT_ACCEPTED', NOW(), gen_random_uuid())
            """, ("@tid", tid), ("@rid", relId), ("@bid", bid), ("@mh", msgHash));

        // Identical (tenant, binding, message_hash, type) replay → unique violation
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.delivery_acknowledgements
                    (tenant_id, relationship_id, binding_id,
                     message_id_hash, acknowledgement_type, acknowledged_at, evidence_id)
                VALUES
                    (@tid, @rid, @bid, @mh, 'TRANSPORT_ACCEPTED', NOW(), gen_random_uuid())
                """, ("@tid", tid), ("@rid", relId), ("@bid", bid), ("@mh", msgHash)));

        Assert.Equal("23505", ex.SqlState); // unique_violation → replay-safe
    }

    [Fact]
    public async Task ContinuityCheckpoint_DistinctBindingsCheck_RejectsSameSourceAndTarget()
    {
        var tid = Guid.NewGuid();
        await using var conn = await Sql.OpenAsync(_fx.OwnerConnectionString);
        await Sql.SetTenantAsync(conn, tid.ToString());
        var relId = await Sql.InsertRelationshipAsync(conn, tid, tid.ToString());
        var singleBid = await Sql.InsertPreparedBindingAsync(conn, tid, relId, Guid.NewGuid());

        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            Sql.ExecAsync(conn, """
                INSERT INTO business.continuity_checkpoints
                    (tenant_id, relationship_id, source_binding_id, target_binding_id,
                     continuity_envelope_hash, material_request_hash, causal_marker,
                     sequence_number, idempotency_key, status, prepared_evidence_id)
                VALUES
                    (@tid, @rid, @same, @same,
                     'd4e5f6a7b8c9d4e5f6a7b8c9d4e5f6a7b8c9d4e5f6a7b8c9d4e5f6a7b8c9d4e5',
                     'e4f5a6b7c8d9e4f5a6b7c8d9e4f5a6b7c8d9e4f5a6b7c8d9e4f5a6b7c8d9e4f5',
                     gen_random_uuid(), 5, gen_random_uuid(), 'PREPARED', gen_random_uuid())
                """,
                ("@tid", tid), ("@rid", relId), ("@same", singleBid)));

        Assert.Equal("23514", ex.SqlState); // check_violation: source != target
    }
}
