// Implements: work-contracts/WC-135-requirements.yaml WC135-R007, WC135-R008, WC135-R009
// Constitutional basis: C-009, C-023, C-026, C-048, C-059, C-063

using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.VisitorConversation;

public sealed class VisitorMigrationPostgresTests
{
    [Fact]
    public async Task MigrationReplaysAndIsolatesTenantsForTheLeastPrivilegeRole()
    {
        await using var postgres = new PostgreSqlBuilder("postgres:16-alpine").Build();
        await postgres.StartAsync();
        await using var owner = new NpgsqlConnection(postgres.GetConnectionString());
        await owner.OpenAsync();
        await Execute(
            owner,
            """
            CREATE ROLE business_app LOGIN PASSWORD 'synthetic-app-password' NOBYPASSRLS;
            CREATE SCHEMA business;
            GRANT USAGE ON SCHEMA business TO business_app;
            CREATE TABLE business.whatsapp_guest_sessions (
                tenant_id uuid NOT NULL,
                binding_digest char(64) NOT NULL,
                PRIMARY KEY (tenant_id, binding_digest)
            );
            """
        );
        var migration = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/98-wc135-visitor-conversation.sql"
            )
        );
        await Execute(owner, migration);
        await Execute(owner, migration);

        var tenant = Guid.NewGuid();
        var other = Guid.NewGuid();
        var session = Guid.NewGuid();
        var subject = new string('c', 64);

        await using (var app = await AppAsync(postgres, tenant))
        {
            await Execute(
                app,
                $$"""
                INSERT INTO business.visitor_sessions
                    (session_id, tenant_id, subject_hash, channel, state, content_version, created_at, updated_at)
                VALUES ('{{session}}', '{{tenant}}', '{{subject}}', 'WHATSAPP', 'DISCOVER', 'waooaw-demo@1.0.0', now(), now());
                INSERT INTO business.visitor_turns
                    (session_id, sequence, tenant_id, message_id, idempotency_key, request_hash,
                     visitor_content_type, reply_json, state_after, outcome_after, created_at)
                VALUES ('{{session}}', 0, '{{tenant}}', '{{Guid.NewGuid()}}', '{{Guid.NewGuid()}}', '{{new string(
                    'd',
                    64
                )}}',
                        'TEXT', '{}', 'DISCOVER', 'NONE', now());
                INSERT INTO business.visitor_render_hints (tenant_id, message_id, reply_json, created_at)
                VALUES ('{{tenant}}', '{{Guid.NewGuid()}}', '{}', now());
                """
            );
            Assert.Equal(1L, await Scalar(app, "SELECT count(*) FROM business.visitor_sessions"));
            Assert.Equal(
                1L,
                await Scalar(app, "SELECT count(*) FROM business.visitor_render_hints")
            );
        }

        await using (var foreign = await AppAsync(postgres, other))
        {
            foreach (
                var table in new[]
                {
                    "visitor_sessions",
                    "visitor_turns",
                    "visitor_leads",
                    "visitor_handoff_references",
                    "visitor_render_hints",
                }
            )
                Assert.Equal(0L, await Scalar(foreign, $"SELECT count(*) FROM business.{table}"));
            var crossTenant = await Assert.ThrowsAsync<PostgresException>(() =>
                Execute(
                    foreign,
                    $"""
                    INSERT INTO business.visitor_sessions
                        (session_id, tenant_id, subject_hash, channel, state, content_version, created_at, updated_at)
                    VALUES ('{Guid.NewGuid()}', '{tenant}', '{subject}', 'WHATSAPP', 'DISCOVER', 'x', now(), now())
                    """
                )
            );
            Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, crossTenant.SqlState);
        }

        await using (var app = await AppAsync(postgres, tenant))
        {
            // Deleting a session removes its transcript, and the least-privilege role may do so.
            await Execute(
                app,
                $"DELETE FROM business.visitor_sessions WHERE session_id = '{session}'"
            );
            Assert.Equal(0L, await Scalar(app, "SELECT count(*) FROM business.visitor_turns"));
            var invalid = await Assert.ThrowsAsync<PostgresException>(() =>
                Execute(
                    app,
                    $"""
                    INSERT INTO business.visitor_sessions
                        (session_id, tenant_id, subject_hash, channel, state, content_version, created_at, updated_at)
                    VALUES ('{Guid.NewGuid()}', '{tenant}', 'not-a-hash', 'WHATSAPP', 'DISCOVER', 'x', now(), now())
                    """
                )
            );
            Assert.Equal(PostgresErrorCodes.CheckViolation, invalid.SqlState);
        }

        // The guest-session columns the START path needs exist exactly once and default safely.
        await Execute(
            owner,
            $"INSERT INTO business.whatsapp_guest_sessions VALUES ('{tenant}', '{subject}')"
        );
        Assert.Equal(
            0L,
            await Scalar(owner, "SELECT resume_count::bigint FROM business.whatsapp_guest_sessions")
        );
    }

    private static async Task<NpgsqlConnection> AppAsync(PostgreSqlContainer postgres, Guid tenant)
    {
        var builder = new NpgsqlConnectionStringBuilder(postgres.GetConnectionString())
        {
            Username = "business_app",
            Password = "synthetic-app-password",
            Options = $"-c app.current_tenant_id={tenant:D}",
            Pooling = false,
        };
        var connection = new NpgsqlConnection(builder.ConnectionString);
        await connection.OpenAsync();
        return connection;
    }

    private static async Task Execute(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        await command.ExecuteNonQueryAsync();
    }

    private static async Task<long> Scalar(NpgsqlConnection connection, string sql)
    {
        await using var command = new NpgsqlCommand(sql, connection);
        return Convert.ToInt64(await command.ExecuteScalarAsync());
    }
}
