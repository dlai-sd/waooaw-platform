// Implements: WC-115 R076-R091, R100-R102
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, C-076, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Text.Json;
using Npgsql;
using Testcontainers.PostgreSql;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class Migration53PostgresIntegrationTests : IAsyncLifetime
{
    private static readonly string DatabaseCredential = Guid.NewGuid().ToString("N");
    private PostgreSqlContainer? _container;
    private string _ownerConnectionString = string.Empty;
    private string _businessConnectionString = string.Empty;

    public async Task InitializeAsync()
    {
        _container = new PostgreSqlBuilder("pgvector/pgvector:pg16")
            .WithDatabase("waooaw")
            .WithUsername("waooaw")
            .WithPassword(DatabaseCredential)
            .Build();
        await _container.StartAsync();
        _ownerConnectionString = _container.GetConnectionString();
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();
        await ExecuteAsync(
            connection,
            $"""
            CREATE SCHEMA IF NOT EXISTS business;
            CREATE SCHEMA IF NOT EXISTS professional;
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'business_app') THEN
                    CREATE ROLE business_app LOGIN PASSWORD '{DatabaseCredential}';
                    CREATE ROLE runtime_app;
                    CREATE ROLE ai_runtime_app;
                    CREATE ROLE wbe_app;
                    CREATE ROLE domain_adapter_app;
                END IF;
            END $$;
            GRANT USAGE ON SCHEMA business TO business_app;
            """
        );
        await ExecuteFileAsync(
            connection,
            "infrastructure/postgres/init/19-ae01-employment-relationship.sql"
        );
        await ExecuteFileAsync(
            connection,
            "infrastructure/postgres/init/53-wc115-conversational-employment.sql"
        );
        _businessConnectionString = new NpgsqlConnectionStringBuilder(_ownerConnectionString)
        {
            Username = "business_app",
            Password = DatabaseCredential,
        }.ConnectionString;
    }

    public async Task DisposeAsync()
    {
        if (_container is not null)
            await _container.DisposeAsync();
    }

    [Fact]
    public async Task WorkspaceVersionsAreAppendOnlyAndTenantIsolated()
    {
        var tenantId = Guid.NewGuid();
        var otherTenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(_ownerConnectionString))
        {
            await owner.OpenAsync();
            await ExecuteAsync(
                owner,
                $$"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id, initiating_participant_id)
                VALUES ('{{relationshipId:D}}', '{{tenantId:D}}', 'NEUTRAL', gen_random_uuid(), gen_random_uuid());
                INSERT INTO business.employment_workspace_versions
                    (tenant_id, relationship_id, workspace_version, manifest_version,
                     decision_space_version, wbe_source_version, protocol_version, projection_state)
                VALUES ('{{tenantId:D}}', '{{relationshipId:D}}', 'workspace-1', 'manifest-1',
                    1, 'commercial-1', '1.0-candidate', 'CURRENT');
                """
            );
            var mutation = await Assert.ThrowsAsync<PostgresException>(() =>
                ExecuteAsync(
                    owner,
                    $"UPDATE business.employment_workspace_versions SET projection_state = 'STALE' "
                        + $"WHERE relationship_id = '{relationshipId:D}';"
                )
            );
            Assert.Contains("append-only", mutation.MessageText);
        }

        await using var business = new NpgsqlConnection(_businessConnectionString);
        await business.OpenAsync();
        await ExecuteAsync(business, $"SET app.current_tenant_id = '{otherTenantId:D}';");
        await using var command = business.CreateCommand();
        command.CommandText =
            "SELECT count(*) FROM business.employment_workspace_versions "
            + "WHERE relationship_id = @relationship_id";
        command.Parameters.AddWithValue("relationship_id", relationshipId);
        Assert.Equal(0L, (long)(await command.ExecuteScalarAsync())!);
    }

    [Fact]
    public async Task CommandReservationAndProjectionSurviveServiceRestart()
    {
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using (var owner = new NpgsqlConnection(_ownerConnectionString))
        {
            await owner.OpenAsync();
            await ExecuteAsync(
                owner,
                $$"""
                INSERT INTO business.employment_relationships
                    (relationship_id, tenant_id, professional_type, evaluation_intent_id, initiating_participant_id)
                VALUES ('{{relationshipId:D}}', '{{tenantId:D}}', 'NEUTRAL', gen_random_uuid(), gen_random_uuid());
                """
            );
        }
        var persistence = new PostgresConversationalEmploymentPersistence(
            _businessConnectionString
        );
        var snapshot = new EmploymentWorkspaceSnapshot(
            tenantId,
            relationshipId,
            "workspace-1",
            "manifest-1",
            Json("{}"),
            new Dictionary<string, JsonElement>(),
            Json("{}"),
            new Dictionary<string, JsonElement>(),
            null,
            1,
            "wbe-1"
        );
        persistence.AppendWorkspace(snapshot);
        Assert.Equal(
            snapshot.WorkspaceVersion,
            new PostgresConversationalEmploymentPersistence(_businessConnectionString)
                .LoadWorkspace(tenantId, relationshipId)
                ?.WorkspaceVersion
        );

        var commandId = Guid.NewGuid();
        var outcome = new EmploymentCommandOutcome(
            "1.0",
            commandId,
            "ACCEPTED",
            DateTimeOffset.UtcNow,
            $"/commands/{commandId}",
            [new EmploymentOwnerStep("BP", "COMMITTED"), new EmploymentOwnerStep("CE", "PENDING")],
            [$"bp-command-accepted:{commandId}"],
            new EmploymentResultingVersions("workspace-1", null, "manifest-1", 1, "wbe-1"),
            "Owner validation is pending.",
            DateTimeOffset.UtcNow
        );
        var actorId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        var first = persistence.ReserveCommand(
            tenantId,
            relationshipId,
            actorId,
            idempotencyKey,
            "CONFIRM_INDUCTION_ITEM",
            new string('a', 64),
            "workspace-1",
            "manifest-1",
            outcome
        );
        var replay = new PostgresConversationalEmploymentPersistence(
            _businessConnectionString
        ).ReserveCommand(
            tenantId,
            relationshipId,
            actorId,
            idempotencyKey,
            "CONFIRM_INDUCTION_ITEM",
            new string('a', 64),
            "workspace-1",
            "manifest-1",
            outcome with
            {
                CommandId = Guid.NewGuid(),
            }
        );

        Assert.False(first.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(commandId, replay.Outcome.CommandId);

        var contextPayload = JsonSerializer.SerializeToElement(
            new
            {
                schemaVersion = "1.0",
                manifestVersion = "manifest-1",
                requirementSetVersion = "requirements-1",
                planVersion = "plan-1",
                goalType = "generic",
                skillRefs = new[] { "skill-1" },
                milestoneTypes = Array.Empty<string>(),
                sourceVersion = "source-1",
            }
        );
        var ownerContext = new EmploymentOwnerContext(
            "plan-1",
            "PLAN_VALIDATION",
            "context-1",
            new string('a', 64),
            contextPayload
        );
        persistence.AppendOwnerContext(tenantId, relationshipId, ownerContext);
        persistence.AppendOwnerContext(tenantId, relationshipId, ownerContext);
        var loadedContext = new PostgresConversationalEmploymentPersistence(
            _businessConnectionString
        ).LoadOwnerContext(tenantId, relationshipId, "plan-1", "PLAN_VALIDATION");
        Assert.NotNull(loadedContext);
        Assert.Equal(ownerContext.ContextVersion, loadedContext.ContextVersion);
        Assert.Equal("plan-1", loadedContext.Context.GetProperty("planVersion").GetString());
        Assert.Null(
            persistence.LoadOwnerContext(tenantId, relationshipId, "missing", "PLAN_VALIDATION")
        );

        var erasureId = persistence.EraseProjectionContent(
            tenantId,
            relationshipId,
            "erasure-authority:test"
        );
        Assert.Null(persistence.LoadWorkspace(tenantId, relationshipId));
        await using var business = new NpgsqlConnection(_businessConnectionString);
        await business.OpenAsync();
        await ExecuteAsync(business, $"SET app.current_tenant_id = '{tenantId:D}';");
        await using var preserved = business.CreateCommand();
        preserved.CommandText = """
            SELECT
                (SELECT count(*) FROM business.employment_workspace_versions
                 WHERE relationship_id = @relationship_id),
                (SELECT count(*) FROM business.employment_commands
                 WHERE relationship_id = @relationship_id),
                (SELECT count(*) FROM business.employment_projection_erasure_tombstones
                 WHERE relationship_id = @relationship_id AND erasure_id = @erasure_id)
            """;
        preserved.Parameters.AddWithValue("relationship_id", relationshipId);
        preserved.Parameters.AddWithValue("erasure_id", erasureId);
        await using var reader = await preserved.ExecuteReaderAsync();
        Assert.True(await reader.ReadAsync());
        Assert.Equal(1L, reader.GetInt64(0));
        Assert.Equal(1L, reader.GetInt64(1));
        Assert.Equal(1L, reader.GetInt64(2));
    }

    [Fact]
    public async Task PrivateOwnerRecordsAreAppendOnlyAndTenantScoped()
    {
        var tenantId = Guid.NewGuid();
        var otherTenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var proposalId = Guid.NewGuid();
        var idempotencyKey = Guid.NewGuid();
        await using var connection = new NpgsqlConnection(_ownerConnectionString);
        await connection.OpenAsync();

        await ExecuteAsync(
            connection,
            $$"""
            SET ROLE ai_runtime_app;
            SELECT set_config('app.current_tenant_id', '{{tenantId:D}}', false);
            INSERT INTO ai_runtime.employment_patch_proposals (
                tenant_id, relationship_ref, proposal_id, idempotency_key,
                request_digest, protocol_version,
                semantic_catalogue_version, semantic_catalogue_digest,
                prompt_policy_version, prompt_policy_digest,
                model_policy_version, model_policy_digest, receipt_json, proposal_json
            ) VALUES (
                '{{tenantId:D}}', '{{relationshipId:D}}', '{{proposalId:D}}',
                '{{idempotencyKey:D}}', '{{new string('a', 64)}}', '1.0-candidate',
                'catalogue-1', '{{new string('b', 64)}}',
                'prompt-1', '{{new string('c', 64)}}',
                'model-1', '{{new string('d', 64)}}',
                '{"state":"PENDING"}'::jsonb, '{"state":"PROPOSED"}'::jsonb
            );
            RESET ROLE;
            """
        );

        await ExecuteAsync(
            connection,
            $$"""
            SET ROLE ai_runtime_app;
            SELECT set_config('app.current_tenant_id', '{{otherTenantId:D}}', false);
            """
        );
        await using (var hidden = connection.CreateCommand())
        {
            hidden.CommandText =
                "SELECT count(*) FROM ai_runtime.employment_patch_proposals "
                + "WHERE proposal_id = @proposal_id";
            hidden.Parameters.AddWithValue("proposal_id", proposalId);
            Assert.Equal(0L, (long)(await hidden.ExecuteScalarAsync())!);
        }
        await ExecuteAsync(connection, "RESET ROLE;");

        var mutation = await Assert.ThrowsAsync<PostgresException>(() =>
            ExecuteAsync(
                connection,
                $$"""
                UPDATE ai_runtime.employment_patch_proposals
                SET protocol_version = 'changed'
                WHERE proposal_id = '{{proposalId:D}}';
                """
            )
        );
        Assert.Contains("append-only", mutation.MessageText);
    }

    private static async Task ExecuteAsync(NpgsqlConnection connection, string sql)
    {
        await using var command = connection.CreateCommand();
        command.CommandText = sql;
        await command.ExecuteNonQueryAsync();
    }

    private static async Task ExecuteFileAsync(NpgsqlConnection connection, string relativePath) =>
        await ExecuteAsync(
            connection,
            await File.ReadAllTextAsync(RepositoryPaths.Resolve(relativePath))
        );

    private static JsonElement Json(string value)
    {
        using var document = JsonDocument.Parse(value);
        return document.RootElement.Clone();
    }
}
