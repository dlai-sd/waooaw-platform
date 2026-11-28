// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R006
// Constitutional basis: C-023, C-026, C-059, C-063, C-078

using Npgsql;

namespace Waooaw.BusinessPlatform.Services.CustomerDataRequests;

public static class CustomerDataRequestKinds
{
    public const string Export = "EXPORT";
    public const string Erasure = "ERASURE";

    public static bool IsValid(string? value) => value is Export or Erasure;
}

public sealed record CustomerDataRequest(
    Guid RequestId,
    Guid TenantId,
    string Kind,
    string State,
    DateTimeOffset RequestedAt,
    DateTimeOffset? ResolvedAt,
    string? ResolutionNote
);

public interface ICustomerDataRequests
{
    /// <summary>Records the request, or returns the one already open for this kind; a repeat with the same key is the same request.</summary>
    Task<(CustomerDataRequest Request, bool Created)> RequestAsync(
        Guid tenantId,
        string actorHash,
        string kind,
        Guid idempotencyKey,
        CancellationToken ct
    );

    Task<IReadOnlyList<CustomerDataRequest>> ListForCustomerAsync(
        Guid tenantId,
        CancellationToken ct
    );

    Task<IReadOnlyList<CustomerDataRequest>> ListOpenForOperatorAsync(
        int limit,
        CancellationToken ct
    );

    /// <summary>Marks an open request completed or declined; returns null when it is not open.</summary>
    Task<CustomerDataRequest?> ResolveAsync(
        Guid requestId,
        bool completed,
        string resolvedBy,
        string note,
        CancellationToken ct
    );
}

public sealed class PostgresCustomerDataRequests(string connectionString, TimeProvider clock)
    : ICustomerDataRequests
{
    private const string Columns =
        "request_id, tenant_id, kind, state, requested_at, resolved_at, resolution_note";

    public async Task<(CustomerDataRequest Request, bool Created)> RequestAsync(
        Guid tenantId,
        string actorHash,
        string kind,
        Guid idempotencyKey,
        CancellationToken ct
    )
    {
        if (!CustomerDataRequestKinds.IsValid(kind))
            throw new ArgumentException("Unknown request kind.", nameof(kind));
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        await SetAsync(
            connection,
            transaction,
            "app.current_tenant_id",
            tenantId.ToString("D"),
            ct
        );
        var existing = await ReadAsync(
            connection,
            transaction,
            $"""
            SELECT {Columns} FROM business.customer_data_requests
            WHERE tenant_id = @tenant AND (idempotency_key = @key OR (kind = @kind AND state = 'RECEIVED'))
            ORDER BY requested_at DESC LIMIT 1
            """,
            ct,
            ("tenant", tenantId),
            ("key", idempotencyKey),
            ("kind", kind)
        );
        if (existing.Count > 0)
        {
            await transaction.CommitAsync(ct);
            return (existing[0], false);
        }
        var created = await ReadAsync(
            connection,
            transaction,
            $"""
            INSERT INTO business.customer_data_requests
                (tenant_id, kind, idempotency_key, requested_by_actor_hash, requested_at)
            VALUES (@tenant, @kind, @key, @actor, @now)
            RETURNING {Columns}
            """,
            ct,
            ("tenant", tenantId),
            ("kind", kind),
            ("key", idempotencyKey),
            ("actor", actorHash),
            ("now", clock.GetUtcNow())
        );
        await transaction.CommitAsync(ct);
        return (created[0], true);
    }

    public async Task<IReadOnlyList<CustomerDataRequest>> ListForCustomerAsync(
        Guid tenantId,
        CancellationToken ct
    )
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        await SetAsync(
            connection,
            transaction,
            "app.current_tenant_id",
            tenantId.ToString("D"),
            ct
        );
        var rows = await ReadAsync(
            connection,
            transaction,
            $"SELECT {Columns} FROM business.customer_data_requests WHERE tenant_id = @tenant ORDER BY requested_at DESC LIMIT 20",
            ct,
            ("tenant", tenantId)
        );
        await transaction.CommitAsync(ct);
        return rows;
    }

    public async Task<IReadOnlyList<CustomerDataRequest>> ListOpenForOperatorAsync(
        int limit,
        CancellationToken ct
    )
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        await SetAsync(connection, transaction, "app.data_requests_operator", "on", ct);
        var rows = await ReadAsync(
            connection,
            transaction,
            $"SELECT {Columns} FROM business.customer_data_requests WHERE state = 'RECEIVED' ORDER BY requested_at LIMIT @limit",
            ct,
            ("limit", Math.Clamp(limit, 1, 100))
        );
        await transaction.CommitAsync(ct);
        return rows;
    }

    public async Task<CustomerDataRequest?> ResolveAsync(
        Guid requestId,
        bool completed,
        string resolvedBy,
        string note,
        CancellationToken ct
    )
    {
        await using var connection = new NpgsqlConnection(connectionString);
        await connection.OpenAsync(ct);
        await using var transaction = await connection.BeginTransactionAsync(ct);
        await SetAsync(connection, transaction, "app.data_requests_operator", "on", ct);
        var rows = await ReadAsync(
            connection,
            transaction,
            $"""
            UPDATE business.customer_data_requests
            SET state = @state, resolved_by_subject = @by, resolved_at = @now, resolution_note = @note
            WHERE request_id = @id AND state = 'RECEIVED'
            RETURNING {Columns}
            """,
            ct,
            ("state", completed ? "COMPLETED" : "DECLINED"),
            ("by", resolvedBy.Length > 128 ? resolvedBy[..128] : resolvedBy),
            ("now", clock.GetUtcNow()),
            ("note", note.Length > 500 ? note[..500] : note),
            ("id", requestId)
        );
        await transaction.CommitAsync(ct);
        return rows.Count == 0 ? null : rows[0];
    }

    private static async Task SetAsync(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        string name,
        string value,
        CancellationToken ct
    )
    {
        await using var command = new NpgsqlCommand(
            "SELECT set_config(@name, @value, true)",
            connection,
            transaction
        );
        command.Parameters.AddWithValue("name", name);
        command.Parameters.AddWithValue("value", value);
        await command.ExecuteNonQueryAsync(ct);
    }

    private static async Task<List<CustomerDataRequest>> ReadAsync(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        string sql,
        CancellationToken ct,
        params (string Name, object Value)[] parameters
    )
    {
        await using var command = new NpgsqlCommand(sql, connection, transaction);
        foreach (var (name, value) in parameters)
            command.Parameters.AddWithValue(name, value);
        var rows = new List<CustomerDataRequest>();
        await using var reader = await command.ExecuteReaderAsync(ct);
        while (await reader.ReadAsync(ct))
            rows.Add(
                new CustomerDataRequest(
                    reader.GetGuid(0),
                    reader.GetGuid(1),
                    reader.GetString(2),
                    reader.GetString(3),
                    reader.GetFieldValue<DateTimeOffset>(4),
                    reader.IsDBNull(5) ? null : reader.GetFieldValue<DateTimeOffset>(5),
                    reader.IsDBNull(6) ? null : reader.GetString(6)
                )
            );
        return rows;
    }
}
