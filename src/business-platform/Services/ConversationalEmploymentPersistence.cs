// Implements: architecture/reference/components/conversational-employment-solution-contract.md §10 Data And Retention Contract
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Text.Json;
using Npgsql;

namespace Waooaw.BusinessPlatform.Services;

public sealed record PersistedEmploymentCommand(
    string CanonicalDigest,
    EmploymentCommandOutcome Outcome,
    bool Replayed
);

public sealed record EmploymentOwnerContext(
    string ContextRef,
    string ContextKind,
    string ContextVersion,
    string ContextDigest,
    JsonElement Context
);

public interface IConversationalEmploymentPersistence
{
    EmploymentWorkspaceSnapshot? LoadWorkspace(Guid tenantId, Guid relationshipId);
    void AppendWorkspace(EmploymentWorkspaceSnapshot snapshot);
    EmploymentCommandOutcome? LoadCommand(Guid tenantId, Guid relationshipId, Guid commandId);
    PersistedEmploymentCommand ReserveCommand(
        Guid tenantId,
        Guid relationshipId,
        Guid actorId,
        Guid idempotencyKey,
        string commandKind,
        string canonicalDigest,
        string expectedWorkspaceVersion,
        string expectedManifestVersion,
        EmploymentCommandOutcome proposed
    );
    void AppendCommandOutcome(Guid tenantId, Guid relationshipId, EmploymentCommandOutcome outcome);
    Guid EraseProjectionContent(Guid tenantId, Guid relationshipId, string authorityRef);
    void AppendOwnerContext(Guid tenantId, Guid relationshipId, EmploymentOwnerContext context);
    EmploymentOwnerContext? LoadOwnerContext(
        Guid tenantId,
        Guid relationshipId,
        string contextRef,
        string contextKind
    );
}

public sealed class PostgresConversationalEmploymentPersistence(string connectionString)
    : IConversationalEmploymentPersistence
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    public EmploymentWorkspaceSnapshot? LoadWorkspace(Guid tenantId, Guid relationshipId)
    {
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, tenantId);
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            SELECT content.projection_json::text
            FROM business.employment_workspace_versions AS version
            JOIN business.employment_workspace_projection_content AS content
              USING (tenant_id, relationship_id, workspace_version)
            WHERE version.tenant_id = @tenant_id
              AND version.relationship_id = @relationship_id
            ORDER BY version.produced_at DESC, version.workspace_version DESC
            LIMIT 1
            """;
        command.Parameters.AddWithValue("tenant_id", tenantId);
        command.Parameters.AddWithValue("relationship_id", relationshipId);
        var payload = command.ExecuteScalar() as string;
        transaction.Commit();
        return payload is null
            ? null
            : JsonSerializer.Deserialize<EmploymentWorkspaceSnapshot>(payload, JsonOptions)
                ?? throw new InvalidOperationException(
                    "The persisted employment workspace projection is invalid."
                );
    }

    public void AppendWorkspace(EmploymentWorkspaceSnapshot snapshot)
    {
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, snapshot.TenantId);
        using var version = connection.CreateCommand();
        version.Transaction = transaction;
        version.CommandText = """
            INSERT INTO business.employment_workspace_versions
                (tenant_id, relationship_id, workspace_version, manifest_version,
                 decision_space_version, wbe_source_version, protocol_version,
                 projection_state, customer_summary)
            VALUES
                (@tenant_id, @relationship_id, @workspace_version, @manifest_version,
                 @decision_space_version, @wbe_source_version, '1.0-candidate',
                 'CURRENT', '{}'::jsonb)
            """;
        version.Parameters.AddWithValue("tenant_id", snapshot.TenantId);
        version.Parameters.AddWithValue("relationship_id", snapshot.RelationshipId);
        version.Parameters.AddWithValue("workspace_version", snapshot.WorkspaceVersion);
        version.Parameters.AddWithValue("manifest_version", snapshot.ManifestVersion);
        version.Parameters.AddWithValue("decision_space_version", snapshot.DecisionSpaceVersion);
        version.Parameters.AddWithValue("wbe_source_version", snapshot.WbeSourceVersion);
        try
        {
            version.ExecuteNonQuery();
        }
        catch (PostgresException error) when (error.SqlState == PostgresErrorCodes.UniqueViolation)
        {
            throw new EmploymentProtocolException("EMPLOYMENT_VERSION_CONFLICT");
        }

        using var content = connection.CreateCommand();
        content.Transaction = transaction;
        content.CommandText = """
            INSERT INTO business.employment_workspace_projection_content
                (tenant_id, relationship_id, workspace_version, projection_json)
            VALUES (@tenant_id, @relationship_id, @workspace_version, @projection_json::jsonb)
            """;
        content.Parameters.AddWithValue("tenant_id", snapshot.TenantId);
        content.Parameters.AddWithValue("relationship_id", snapshot.RelationshipId);
        content.Parameters.AddWithValue("workspace_version", snapshot.WorkspaceVersion);
        content.Parameters.AddWithValue(
            "projection_json",
            JsonSerializer.Serialize(snapshot, JsonOptions)
        );
        content.ExecuteNonQuery();
        foreach (var (planVersion, plan) in snapshot.Plans)
        {
            using var planCommand = connection.CreateCommand();
            planCommand.Transaction = transaction;
            planCommand.CommandText = """
                INSERT INTO business.employment_plan_versions
                    (tenant_id, relationship_id, plan_version, workspace_version,
                     manifest_version, decision_space_version, wbe_source_version,
                     state, plan_json, supersedes_plan_version)
                VALUES
                    (@tenant_id, @relationship_id, @plan_version, @workspace_version,
                     @manifest_version, @decision_space_version, @wbe_source_version,
                     @state, @plan_json::jsonb, @supersedes_plan_version)
                """;
            planCommand.Parameters.AddWithValue("tenant_id", snapshot.TenantId);
            planCommand.Parameters.AddWithValue("relationship_id", snapshot.RelationshipId);
            planCommand.Parameters.AddWithValue("plan_version", planVersion);
            planCommand.Parameters.AddWithValue("workspace_version", snapshot.WorkspaceVersion);
            planCommand.Parameters.AddWithValue("manifest_version", snapshot.ManifestVersion);
            planCommand.Parameters.AddWithValue(
                "decision_space_version",
                snapshot.DecisionSpaceVersion
            );
            planCommand.Parameters.AddWithValue("wbe_source_version", snapshot.WbeSourceVersion);
            planCommand.Parameters.AddWithValue("state", plan.GetProperty("state").GetString()!);
            planCommand.Parameters.AddWithValue("plan_json", plan.GetRawText());
            object priorPlanVersion =
                plan.TryGetProperty("priorPlanVersion", out var priorPlan)
                && priorPlan.GetString() is { } prior
                    ? prior
                    : DBNull.Value;
            planCommand.Parameters.AddWithValue("supersedes_plan_version", priorPlanVersion);
            planCommand.ExecuteNonQuery();
        }
        transaction.Commit();
    }

    public EmploymentCommandOutcome? LoadCommand(Guid tenantId, Guid relationshipId, Guid commandId)
    {
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, tenantId);
        var outcome = LoadCommand(connection, transaction, tenantId, relationshipId, commandId);
        transaction.Commit();
        return outcome;
    }

    public PersistedEmploymentCommand ReserveCommand(
        Guid tenantId,
        Guid relationshipId,
        Guid actorId,
        Guid idempotencyKey,
        string commandKind,
        string canonicalDigest,
        string expectedWorkspaceVersion,
        string expectedManifestVersion,
        EmploymentCommandOutcome proposed
    )
    {
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, tenantId);
        using var reserve = connection.CreateCommand();
        reserve.Transaction = transaction;
        reserve.CommandText = """
            INSERT INTO business.employment_commands
                (tenant_id, relationship_id, command_id, actor_id, operation_family,
                 idempotency_key, canonical_payload_hash, command_kind,
                 expected_workspace_version, expected_manifest_version, rollback_epoch)
            VALUES
                (@tenant_id, @relationship_id, @command_id, @actor_id, @operation_family,
                 @idempotency_key, @canonical_payload_hash, @command_kind,
                 @expected_workspace_version, @expected_manifest_version, 0)
            ON CONFLICT (tenant_id, relationship_id, actor_id, operation_family, idempotency_key)
            DO NOTHING
            RETURNING command_id
            """;
        reserve.Parameters.AddWithValue("tenant_id", tenantId);
        reserve.Parameters.AddWithValue("relationship_id", relationshipId);
        reserve.Parameters.AddWithValue("command_id", proposed.CommandId);
        reserve.Parameters.AddWithValue("actor_id", actorId);
        reserve.Parameters.AddWithValue("operation_family", commandKind);
        reserve.Parameters.AddWithValue("idempotency_key", idempotencyKey);
        reserve.Parameters.AddWithValue("canonical_payload_hash", canonicalDigest);
        reserve.Parameters.AddWithValue("command_kind", commandKind);
        reserve.Parameters.AddWithValue("expected_workspace_version", expectedWorkspaceVersion);
        reserve.Parameters.AddWithValue("expected_manifest_version", expectedManifestVersion);
        var inserted = reserve.ExecuteScalar() is Guid;
        if (!inserted)
        {
            using var existing = connection.CreateCommand();
            existing.Transaction = transaction;
            existing.CommandText = """
                SELECT command_id, canonical_payload_hash
                FROM business.employment_commands
                WHERE tenant_id = @tenant_id
                  AND relationship_id = @relationship_id
                  AND actor_id = @actor_id
                  AND operation_family = @operation_family
                  AND idempotency_key = @idempotency_key
                """;
            existing.Parameters.AddWithValue("tenant_id", tenantId);
            existing.Parameters.AddWithValue("relationship_id", relationshipId);
            existing.Parameters.AddWithValue("actor_id", actorId);
            existing.Parameters.AddWithValue("operation_family", commandKind);
            existing.Parameters.AddWithValue("idempotency_key", idempotencyKey);
            using var reader = existing.ExecuteReader();
            if (!reader.Read())
                throw new InvalidOperationException("Employment command reservation disappeared.");
            var existingCommandId = reader.GetGuid(0);
            var existingDigest = reader.GetString(1);
            reader.Close();
            var existingOutcome =
                LoadCommand(connection, transaction, tenantId, relationshipId, existingCommandId)
                ?? throw new InvalidOperationException(
                    "Employment command reservation has no durable outcome."
                );
            transaction.Commit();
            return new PersistedEmploymentCommand(existingDigest, existingOutcome, true);
        }

        AppendCommandEvent(connection, transaction, tenantId, relationshipId, proposed, 1);
        AppendOutbox(connection, transaction, tenantId, relationshipId, proposed);
        transaction.Commit();
        return new PersistedEmploymentCommand(canonicalDigest, proposed, false);
    }

    public void AppendCommandOutcome(
        Guid tenantId,
        Guid relationshipId,
        EmploymentCommandOutcome outcome
    )
    {
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, tenantId);
        using (var commandLock = connection.CreateCommand())
        {
            commandLock.Transaction = transaction;
            commandLock.CommandText = """
                SELECT command_id
                FROM business.employment_commands
                WHERE tenant_id = @tenant_id
                  AND relationship_id = @relationship_id
                  AND command_id = @command_id
                FOR UPDATE
                """;
            commandLock.Parameters.AddWithValue("tenant_id", tenantId);
            commandLock.Parameters.AddWithValue("relationship_id", relationshipId);
            commandLock.Parameters.AddWithValue("command_id", outcome.CommandId);
            if (commandLock.ExecuteScalar() is not Guid)
                throw new InvalidOperationException("Employment command does not exist.");
        }
        using var sequence = connection.CreateCommand();
        sequence.Transaction = transaction;
        sequence.CommandText = """
            SELECT COALESCE(MAX(event_sequence), 0) + 1
            FROM business.employment_command_events
            WHERE tenant_id = @tenant_id
              AND relationship_id = @relationship_id
              AND command_id = @command_id
            """;
        sequence.Parameters.AddWithValue("tenant_id", tenantId);
        sequence.Parameters.AddWithValue("relationship_id", relationshipId);
        sequence.Parameters.AddWithValue("command_id", outcome.CommandId);
        var nextSequence = Convert.ToInt64(sequence.ExecuteScalar());
        AppendCommandEvent(
            connection,
            transaction,
            tenantId,
            relationshipId,
            outcome,
            nextSequence
        );
        AppendOutbox(connection, transaction, tenantId, relationshipId, outcome);
        transaction.Commit();
    }

    public Guid EraseProjectionContent(Guid tenantId, Guid relationshipId, string authorityRef)
    {
        if (string.IsNullOrWhiteSpace(authorityRef))
            throw new EmploymentProtocolException("EMPLOYMENT_INVALID_REQUEST");
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, tenantId);
        using var select = connection.CreateCommand();
        select.Transaction = transaction;
        select.CommandText = """
            DELETE FROM business.employment_workspace_projection_content
            WHERE tenant_id = @tenant_id AND relationship_id = @relationship_id
            RETURNING workspace_version
            """;
        select.Parameters.AddWithValue("tenant_id", tenantId);
        select.Parameters.AddWithValue("relationship_id", relationshipId);
        var versions = new List<string>();
        using (var reader = select.ExecuteReader())
        {
            while (reader.Read())
                versions.Add(reader.GetString(0));
        }
        versions.Sort(StringComparer.Ordinal);
        var erasureId = Guid.NewGuid();
        using var tombstone = connection.CreateCommand();
        tombstone.Transaction = transaction;
        tombstone.CommandText = """
            INSERT INTO business.employment_projection_erasure_tombstones
                (tenant_id, relationship_id, erasure_id, authority_ref,
                 erased_workspace_versions)
            VALUES
                (@tenant_id, @relationship_id, @erasure_id, @authority_ref,
                 @erased_workspace_versions::jsonb)
            """;
        tombstone.Parameters.AddWithValue("tenant_id", tenantId);
        tombstone.Parameters.AddWithValue("relationship_id", relationshipId);
        tombstone.Parameters.AddWithValue("erasure_id", erasureId);
        tombstone.Parameters.AddWithValue("authority_ref", authorityRef);
        tombstone.Parameters.AddWithValue(
            "erased_workspace_versions",
            JsonSerializer.Serialize(versions, JsonOptions)
        );
        tombstone.ExecuteNonQuery();
        transaction.Commit();
        return erasureId;
    }

    public void AppendOwnerContext(
        Guid tenantId,
        Guid relationshipId,
        EmploymentOwnerContext context
    )
    {
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, tenantId);
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            INSERT INTO business.employment_owner_contexts
                (tenant_id, relationship_id, context_ref, context_kind, context_version,
                 context_digest, context_json)
            VALUES
                (@tenant_id, @relationship_id, @context_ref, @context_kind, @context_version,
                 @context_digest, @context_json::jsonb)
            ON CONFLICT (tenant_id, relationship_id, context_ref, context_kind, context_version)
            DO NOTHING
            """;
        command.Parameters.AddWithValue("tenant_id", tenantId);
        command.Parameters.AddWithValue("relationship_id", relationshipId);
        command.Parameters.AddWithValue("context_ref", context.ContextRef);
        command.Parameters.AddWithValue("context_kind", context.ContextKind);
        command.Parameters.AddWithValue("context_version", context.ContextVersion);
        command.Parameters.AddWithValue("context_digest", context.ContextDigest);
        command.Parameters.AddWithValue("context_json", context.Context.GetRawText());
        command.ExecuteNonQuery();
        transaction.Commit();
    }

    public EmploymentOwnerContext? LoadOwnerContext(
        Guid tenantId,
        Guid relationshipId,
        string contextRef,
        string contextKind
    )
    {
        using var connection = Open();
        using var transaction = BeginTenantTransaction(connection, tenantId);
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            SELECT context_version, context_digest, context_json
            FROM business.employment_owner_contexts
            WHERE tenant_id = @tenant_id
              AND relationship_id = @relationship_id
              AND context_ref = @context_ref
              AND context_kind = @context_kind
            ORDER BY created_at DESC
            LIMIT 1
            """;
        command.Parameters.AddWithValue("tenant_id", tenantId);
        command.Parameters.AddWithValue("relationship_id", relationshipId);
        command.Parameters.AddWithValue("context_ref", contextRef);
        command.Parameters.AddWithValue("context_kind", contextKind);
        EmploymentOwnerContext? result = null;
        using (var reader = command.ExecuteReader())
        {
            if (reader.Read())
            {
                using var document = JsonDocument.Parse(reader.GetString(2));
                result = new EmploymentOwnerContext(
                    contextRef,
                    contextKind,
                    reader.GetString(0),
                    reader.GetString(1),
                    document.RootElement.Clone()
                );
            }
        }
        transaction.Commit();
        return result;
    }

    private NpgsqlConnection Open()
    {
        var connection = new NpgsqlConnection(connectionString);
        connection.Open();
        return connection;
    }

    private static NpgsqlTransaction BeginTenantTransaction(
        NpgsqlConnection connection,
        Guid tenantId
    )
    {
        var transaction = connection.BeginTransaction();
        using var tenant = connection.CreateCommand();
        tenant.Transaction = transaction;
        tenant.CommandText = "SELECT set_config('app.current_tenant_id', @tenant_id, true)";
        tenant.Parameters.AddWithValue("tenant_id", tenantId.ToString("D"));
        tenant.ExecuteScalar();
        return transaction;
    }

    private static EmploymentCommandOutcome? LoadCommand(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        Guid tenantId,
        Guid relationshipId,
        Guid commandId
    )
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            SELECT result_json::text
            FROM business.employment_command_events
            WHERE tenant_id = @tenant_id
              AND relationship_id = @relationship_id
              AND command_id = @command_id
            ORDER BY event_sequence DESC
            LIMIT 1
            """;
        command.Parameters.AddWithValue("tenant_id", tenantId);
        command.Parameters.AddWithValue("relationship_id", relationshipId);
        command.Parameters.AddWithValue("command_id", commandId);
        var payload = command.ExecuteScalar() as string;
        return payload is null
            ? null
            : JsonSerializer.Deserialize<EmploymentCommandOutcome>(payload, JsonOptions)
                ?? throw new InvalidOperationException(
                    "The persisted employment command outcome is invalid."
                );
    }

    private static void AppendCommandEvent(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        Guid tenantId,
        Guid relationshipId,
        EmploymentCommandOutcome outcome,
        long sequence
    )
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            INSERT INTO business.employment_command_events
                (tenant_id, relationship_id, command_id, event_sequence, state,
                 owner_steps_json, evidence_refs_json, result_json)
            VALUES
                (@tenant_id, @relationship_id, @command_id, @event_sequence, @state,
                 @owner_steps_json::jsonb, @evidence_refs_json::jsonb, @result_json::jsonb)
            """;
        command.Parameters.AddWithValue("tenant_id", tenantId);
        command.Parameters.AddWithValue("relationship_id", relationshipId);
        command.Parameters.AddWithValue("command_id", outcome.CommandId);
        command.Parameters.AddWithValue("event_sequence", sequence);
        command.Parameters.AddWithValue("state", outcome.State);
        command.Parameters.AddWithValue(
            "owner_steps_json",
            JsonSerializer.Serialize(outcome.OwnerSteps, JsonOptions)
        );
        command.Parameters.AddWithValue(
            "evidence_refs_json",
            JsonSerializer.Serialize(outcome.EvidenceRefs, JsonOptions)
        );
        command.Parameters.AddWithValue(
            "result_json",
            JsonSerializer.Serialize(outcome, JsonOptions)
        );
        command.ExecuteNonQuery();
    }

    private static void AppendOutbox(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        Guid tenantId,
        Guid relationshipId,
        EmploymentCommandOutcome outcome
    )
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = """
            INSERT INTO business.employment_outbox
                (tenant_id, event_id, relationship_id, owner, aggregate_id,
                 aggregate_version, event_type, payload_json, rollback_epoch)
            VALUES
                (@tenant_id, @event_id, @relationship_id, 'BP', @aggregate_id,
                 @aggregate_version, 'EMPLOYMENT_COMMAND_OUTCOME', @payload_json::jsonb, 0)
            """;
        command.Parameters.AddWithValue("tenant_id", tenantId);
        command.Parameters.AddWithValue("event_id", Guid.NewGuid());
        command.Parameters.AddWithValue("relationship_id", relationshipId);
        command.Parameters.AddWithValue("aggregate_id", outcome.CommandId.ToString("D"));
        command.Parameters.AddWithValue(
            "aggregate_version",
            outcome.UpdatedAt.ToUnixTimeMilliseconds().ToString()
        );
        command.Parameters.AddWithValue(
            "payload_json",
            JsonSerializer.Serialize(outcome, JsonOptions)
        );
        command.ExecuteNonQuery();
    }
}
