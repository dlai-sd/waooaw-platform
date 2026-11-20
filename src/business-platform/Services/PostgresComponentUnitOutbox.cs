// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
// Constitutional basis: C-005, C-023, C-059, C-063, ADR-051

using Npgsql;
using NpgsqlTypes;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>
/// The durable component-unit outbox (<c>business.component_unit_outbox</c>). Enqueue runs inside the caller's
/// tenant scope and is idempotent on (tenant, relationship, component, evidence). The worker claims and marks work
/// across tenants only through the owner-defined claim/mark functions, never through table access.
/// </summary>
public sealed class PostgresComponentUnitOutbox(string connectionString) : IComponentUnitOutbox
{
    public void Completed(ComponentUnitCompletion completion)
    {
        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();
        using (var tenant = connection.CreateCommand())
        {
            tenant.Transaction = transaction;
            tenant.CommandText = "SELECT set_config('app.current_tenant_id', @tenant_id, true)";
            tenant.Parameters.AddWithValue("tenant_id", completion.TenantId.ToString("D"));
            tenant.ExecuteScalar();
        }
        using var insert = connection.CreateCommand();
        insert.Transaction = transaction;
        insert.CommandText = """
            INSERT INTO business.component_unit_outbox
                (tenant_id, relationship_id, component_id, completion_evidence_id, actor_subject)
            VALUES (@tenant_id, @relationship_id, @component_id, @evidence_id, @actor_subject)
            ON CONFLICT (tenant_id, relationship_id, component_id, completion_evidence_id) DO NOTHING
            """;
        insert.Parameters.AddWithValue("tenant_id", completion.TenantId);
        insert.Parameters.AddWithValue("relationship_id", completion.RelationshipId);
        insert.Parameters.AddWithValue("component_id", completion.ComponentId);
        insert.Parameters.AddWithValue("evidence_id", completion.CompletionEvidenceId);
        insert.Parameters.AddWithValue("actor_subject", completion.ActorSubject);
        insert.ExecuteNonQuery();
        transaction.Commit();
    }

    public async Task<IReadOnlyList<ComponentUnitWork>> ClaimAsync(
        int limit,
        TimeSpan lease,
        CancellationToken ct
    )
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var claim = connection.CreateCommand();
        claim.CommandText = """
            SELECT work_id, work_tenant_id, work_relationship_id, work_component_id,
                   work_evidence_id, work_actor_subject, work_attempt
            FROM business.claim_component_unit_work(@limit, @lease_seconds)
            """;
        claim.Parameters.AddWithValue("limit", limit);
        claim.Parameters.AddWithValue("lease_seconds", (int)Math.Ceiling(lease.TotalSeconds));
        var work = new List<ComponentUnitWork>();
        await using var reader = await claim.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
            work.Add(
                new ComponentUnitWork(
                    reader.GetGuid(0),
                    new ComponentUnitCompletion(
                        reader.GetGuid(1),
                        reader.GetGuid(2),
                        reader.GetString(3),
                        reader.GetGuid(4),
                        reader.GetString(5)
                    ),
                    reader.GetInt32(6)
                )
            );
        return work;
    }

    public Task DeliveredAsync(Guid outboxId, CancellationToken ct) =>
        MarkAsync(outboxId, "DELIVERED", 0, null, ct);

    public Task RefusedAsync(Guid outboxId, string code, CancellationToken ct) =>
        MarkAsync(outboxId, "REFUSED", 0, Bounded(code), ct);

    public Task RetryAsync(Guid outboxId, TimeSpan delay, string code, CancellationToken ct) =>
        MarkAsync(outboxId, "RETRY", (int)Math.Ceiling(delay.TotalSeconds), Bounded(code), ct);

    public Task UnresolvedAsync(Guid outboxId, string code, CancellationToken ct) =>
        MarkAsync(outboxId, "UNRESOLVED", 0, Bounded(code), ct);

    private static string Bounded(string code) =>
        string.IsNullOrEmpty(code) ? "UNSPECIFIED"
        : code.Length <= 100 ? code
        : code[..100];

    private async Task MarkAsync(
        Guid outboxId,
        string outcome,
        int delaySeconds,
        string? code,
        CancellationToken ct
    )
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var mark = connection.CreateCommand();
        mark.CommandText = "SELECT business.mark_component_unit_work(@id, @outcome, @delay, @code)";
        mark.Parameters.AddWithValue("id", outboxId);
        mark.Parameters.AddWithValue("outcome", outcome);
        mark.Parameters.AddWithValue("delay", delaySeconds);
        mark.Parameters.Add(
            new NpgsqlParameter("code", NpgsqlDbType.Text) { Value = (object?)code ?? DBNull.Value }
        );
        await mark.ExecuteScalarAsync(ct);
    }
}
