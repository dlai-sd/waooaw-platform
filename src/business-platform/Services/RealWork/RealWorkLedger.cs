// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2, DC-3, DC-4, DC-5 (single append-only owner-side record store)
// Constitutional basis: C-005, C-023, C-026, C-059, C-063
// IB: IB-170

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;

namespace Waooaw.BusinessPlatform.Services.RealWork;

public static class RealWorkKinds
{
    public const string Artifact = "ARTIFACT";
    public const string ArtifactSubmitted = "ARTIFACT_SUBMITTED";
    public const string ArtifactLocked = "ARTIFACT_LOCKED";
    public const string ArtifactSuperseded = "ARTIFACT_SUPERSEDED";
    public const string Decision = "DECISION";
    public const string Timeline = "TIMELINE";
    public const string Claim = "CLAIM";
}

public sealed record RealWorkRecord(
    Guid TenantId,
    Guid RelationshipId,
    string Kind,
    Guid RecordId,
    string IdempotencyKey,
    string PayloadDigest,
    JsonElement Payload,
    long Sequence,
    DateTimeOffset CreatedAt
);

public sealed class RealWorkConflictException(string code) : InvalidOperationException(code)
{
    public string Code { get; } = code;
}

/// <summary>
/// The one append-only store behind the real-work projections. Nothing is updated or deleted: a lock, a supersession,
/// a decision and a reconciled outcome are each a new record, and the projections fold them in sequence order.
/// </summary>
public interface IRealWorkLedger
{
    /// <summary>Idempotent on (tenant, relationship, kind, key); the same key with a different payload is a conflict.</summary>
    RealWorkRecord Append(
        Guid tenantId,
        Guid relationshipId,
        string kind,
        string idempotencyKey,
        JsonElement payload,
        DateTimeOffset now
    );

    IReadOnlyList<RealWorkRecord> List(Guid tenantId, Guid relationshipId, string? kind = null);
}

public static class RealWorkDigest
{
    public static string Of(JsonElement value) => Of(Canonical(value));

    public static string Of(string text) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(text)));

    private static readonly JsonSerializerOptions CanonicalOptions = new()
    {
        Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    /// <summary>Property order and whitespace never change a digest; array order does.</summary>
    public static string Canonical(JsonElement value) =>
        Normalize(JsonNode.Parse(value.GetRawText()))?.ToJsonString(CanonicalOptions) ?? "null";

    private static JsonNode? Normalize(JsonNode? node) =>
        node switch
        {
            JsonObject obj => new JsonObject(
                obj.OrderBy(pair => pair.Key, StringComparer.Ordinal)
                    .Select(pair => KeyValuePair.Create(pair.Key, Normalize(pair.Value)))
            ),
            JsonArray array => new JsonArray(array.Select(Normalize).ToArray()),
            _ => node?.DeepClone(),
        };
}

public sealed class InMemoryRealWorkLedger : IRealWorkLedger
{
    private readonly List<RealWorkRecord> _records = [];
    private readonly object _sync = new();

    public RealWorkRecord Append(
        Guid tenantId,
        Guid relationshipId,
        string kind,
        string idempotencyKey,
        JsonElement payload,
        DateTimeOffset now
    )
    {
        var digest = RealWorkDigest.Of(payload);
        lock (_sync)
        {
            var existing = _records.FirstOrDefault(record =>
                record.TenantId == tenantId
                && record.RelationshipId == relationshipId
                && record.Kind == kind
                && record.IdempotencyKey == idempotencyKey
            );
            if (existing is not null)
                return existing.PayloadDigest == digest
                    ? existing
                    : throw new RealWorkConflictException("REAL_WORK_IDEMPOTENCY_CONFLICT");
            var sequence =
                _records
                    .Where(record =>
                        record.TenantId == tenantId && record.RelationshipId == relationshipId
                    )
                    .Select(record => record.Sequence)
                    .DefaultIfEmpty(0)
                    .Max() + 1;
            var created = new RealWorkRecord(
                tenantId,
                relationshipId,
                kind,
                Guid.NewGuid(),
                idempotencyKey,
                digest,
                payload.Clone(),
                sequence,
                now
            );
            _records.Add(created);
            return created;
        }
    }

    public IReadOnlyList<RealWorkRecord> List(
        Guid tenantId,
        Guid relationshipId,
        string? kind = null
    )
    {
        lock (_sync)
            return _records
                .Where(record =>
                    record.TenantId == tenantId
                    && record.RelationshipId == relationshipId
                    && (kind is null || record.Kind == kind)
                )
                .OrderBy(record => record.Sequence)
                .ToArray();
    }
}

public sealed class PostgresRealWorkLedger(string connectionString) : IRealWorkLedger
{
    private const string SelectColumns = """
        tenant_id, relationship_id, kind, record_id, idempotency_key, payload_digest,
        payload::text, sequence, created_at
        """;

    public RealWorkRecord Append(
        Guid tenantId,
        Guid relationshipId,
        string kind,
        string idempotencyKey,
        JsonElement payload,
        DateTimeOffset now
    )
    {
        var digest = RealWorkDigest.Of(payload);
        var created = now.ToUniversalTime();
        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();
        Run(
            connection,
            transaction,
            "SELECT set_config('app.current_tenant_id', @tenant_id, true)",
            ("tenant_id", tenantId.ToString("D"))
        );
        // One writer per relationship at a time, so the sequence is gapless and monotonic.
        Run(
            connection,
            transaction,
            "SELECT pg_advisory_xact_lock(hashtextextended(@scope, 0))",
            ("scope", $"real-work:{tenantId:D}:{relationshipId:D}")
        );
        var existing = Read(
                connection,
                transaction,
                $"""
                SELECT {SelectColumns}
                FROM business.real_work_records
                WHERE tenant_id = @tenant_id AND relationship_id = @relationship_id
                  AND kind = @kind AND idempotency_key = @idempotency_key
                """,
                ("tenant_id", tenantId),
                ("relationship_id", relationshipId),
                ("kind", kind),
                ("idempotency_key", idempotencyKey)
            )
            .FirstOrDefault();
        if (existing is not null)
        {
            transaction.Commit();
            return existing.PayloadDigest == digest
                ? existing
                : throw new RealWorkConflictException("REAL_WORK_IDEMPOTENCY_CONFLICT");
        }
        var recordId = Guid.NewGuid();
        var sequence = Convert.ToInt64(
            Run(
                connection,
                transaction,
                """
                INSERT INTO business.real_work_records
                    (tenant_id, relationship_id, kind, record_id, idempotency_key, payload_digest, payload, sequence, created_at)
                SELECT @tenant_id, @relationship_id, @kind, @record_id, @idempotency_key, @payload_digest,
                       CAST(@payload AS jsonb), COALESCE(MAX(sequence), 0) + 1, @created_at
                FROM business.real_work_records
                WHERE tenant_id = @tenant_id AND relationship_id = @relationship_id
                RETURNING sequence
                """,
                ("tenant_id", tenantId),
                ("relationship_id", relationshipId),
                ("kind", kind),
                ("record_id", recordId),
                ("idempotency_key", idempotencyKey),
                ("payload_digest", digest),
                ("payload", payload.GetRawText()),
                ("created_at", created)
            )
        );
        transaction.Commit();
        return new RealWorkRecord(
            tenantId,
            relationshipId,
            kind,
            recordId,
            idempotencyKey,
            digest,
            payload.Clone(),
            sequence,
            created
        );
    }

    public IReadOnlyList<RealWorkRecord> List(
        Guid tenantId,
        Guid relationshipId,
        string? kind = null
    )
    {
        using var connection = new NpgsqlConnection(connectionString);
        connection.Open();
        using var transaction = connection.BeginTransaction();
        Run(
            connection,
            transaction,
            "SELECT set_config('app.current_tenant_id', @tenant_id, true)",
            ("tenant_id", tenantId.ToString("D"))
        );
        var records = Read(
            connection,
            transaction,
            $"""
            SELECT {SelectColumns}
            FROM business.real_work_records
            WHERE tenant_id = @tenant_id AND relationship_id = @relationship_id
              AND (CAST(@kind AS text) IS NULL OR kind = @kind)
            ORDER BY sequence
            """,
            ("tenant_id", tenantId),
            ("relationship_id", relationshipId),
            ("kind", (object?)kind ?? DBNull.Value)
        );
        transaction.Commit();
        return records;
    }

    private static object? Run(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        string sql,
        params (string Name, object Value)[] parameters
    )
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        foreach (var (name, value) in parameters)
            command.Parameters.AddWithValue(name, value);
        return command.ExecuteScalar();
    }

    private static List<RealWorkRecord> Read(
        NpgsqlConnection connection,
        NpgsqlTransaction transaction,
        string sql,
        params (string Name, object Value)[] parameters
    )
    {
        using var command = connection.CreateCommand();
        command.Transaction = transaction;
        command.CommandText = sql;
        foreach (var (name, value) in parameters)
            command.Parameters.AddWithValue(name, value);
        var records = new List<RealWorkRecord>();
        using var reader = command.ExecuteReader();
        while (reader.Read())
        {
            using var document = JsonDocument.Parse(reader.GetString(6));
            records.Add(
                new RealWorkRecord(
                    reader.GetGuid(0),
                    reader.GetGuid(1),
                    reader.GetString(2),
                    reader.GetGuid(3),
                    reader.GetString(4),
                    reader.GetString(5),
                    document.RootElement.Clone(),
                    reader.GetInt64(7),
                    reader.GetFieldValue<DateTimeOffset>(8)
                )
            );
        }
        return records;
    }
}
