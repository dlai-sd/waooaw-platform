// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R030, R032, R036
// Constitutional basis: C-005, C-023, C-059, C-063

using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;

namespace Waooaw.BusinessPlatform.Services.AgentOperation;

/// <summary>A count of how outcomes were reached or what needs attention. It carries no content (WC174-R032).</summary>
public sealed record OperationCounter(
    DateOnly Day,
    string RelationshipRef,
    string Metric,
    int Count
);

public static class OperationMetrics
{
    public const string RouteAsked = "ROUTE_ASKED";
    public const string RouteAccepted = "ROUTE_ACCEPTED";
    public const string RouteTool = "ROUTE_TOOL";
    public const string Published = "PUBLISHED";
    public const string PublishFailed = "PUBLISH_FAILED";
    public const string ConnectionRepair = "CONNECTION_REPAIR";

    public static string ForRoute(string route) =>
        route switch
        {
            OperationVocabulary.Routes.Asked => RouteAsked,
            OperationVocabulary.Routes.Accepted => RouteAccepted,
            _ => RouteTool,
        };

    /// <summary>A stable reference for a relationship that does not reveal its identifier.</summary>
    public static string RefOf(Guid relationshipId) =>
        Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(relationshipId.ToString("N")))
        )[..24];
}

/// <summary>Everything Agent Operation persists. Items are versioned and never deleted; undo writes a new version.</summary>
public interface IAgentOperationStore
{
    Task<IReadOnlyList<OperationItem>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    );

    Task<OperationItem?> GetAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    );

    /// <summary>Creates the item as version one; returns false when the id already exists (an idempotent replay).</summary>
    Task<bool> InsertAsync(OperationItem item, CancellationToken ct);

    /// <summary>Writes the next version; returns false when another writer got there first.</summary>
    Task<bool> UpdateAsync(OperationItem item, int expectedVersion, CancellationToken ct);

    Task<IReadOnlyList<OperationItem>> VersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    );

    Task<RelationshipOperationState> GetStateAsync(
        Guid tenantId,
        Guid relationshipId,
        DateTimeOffset now,
        CancellationToken ct
    );

    Task SaveStateAsync(RelationshipOperationState state, CancellationToken ct);

    Task<AgentOperationSettings> GetSettingsAsync(CancellationToken ct);

    Task SaveSettingsAsync(AgentOperationSettings settings, string actor, CancellationToken ct);

    Task CountAsync(
        DateOnly day,
        string relationshipRef,
        string metric,
        int by,
        CancellationToken ct
    );

    Task<IReadOnlyList<OperationCounter>> CountersAsync(
        DateOnly from,
        DateOnly to,
        CancellationToken ct
    );
}

public sealed class InMemoryAgentOperationStore : IAgentOperationStore
{
    private readonly object gate = new();
    private readonly Dictionary<(Guid, Guid, Guid), List<OperationItem>> items = [];
    private readonly Dictionary<(Guid, Guid), RelationshipOperationState> states = [];
    private readonly Dictionary<(DateOnly, string, string), int> counters = [];
    private AgentOperationSettings settings = AgentOperationSettings.Default;

    public Task<IReadOnlyList<OperationItem>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    )
    {
        lock (gate)
            return Task.FromResult<IReadOnlyList<OperationItem>>(
                items
                    .Where(pair => pair.Key.Item1 == tenantId && pair.Key.Item2 == relationshipId)
                    .Select(pair => pair.Value[^1])
                    .OrderBy(item => item.CreatedAt)
                    .ThenBy(item => item.ItemId)
                    .ToArray()
            );
    }

    public Task<OperationItem?> GetAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    )
    {
        lock (gate)
            return Task.FromResult(
                items.TryGetValue((tenantId, relationshipId, itemId), out var versions)
                    ? versions[^1]
                    : null
            );
    }

    public Task<bool> InsertAsync(OperationItem item, CancellationToken ct)
    {
        lock (gate)
        {
            var key = (item.TenantId, item.RelationshipId, item.ItemId);
            if (items.ContainsKey(key))
                return Task.FromResult(false);
            items[key] = [item];
            return Task.FromResult(true);
        }
    }

    public Task<bool> UpdateAsync(OperationItem item, int expectedVersion, CancellationToken ct)
    {
        lock (gate)
        {
            var key = (item.TenantId, item.RelationshipId, item.ItemId);
            if (
                !items.TryGetValue(key, out var versions)
                || versions[^1].VersionNo != expectedVersion
            )
                return Task.FromResult(false);
            versions.Add(item);
            return Task.FromResult(true);
        }
    }

    public Task<IReadOnlyList<OperationItem>> VersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    )
    {
        lock (gate)
            return Task.FromResult<IReadOnlyList<OperationItem>>(
                items.TryGetValue((tenantId, relationshipId, itemId), out var versions)
                    ? versions.ToArray()
                    : []
            );
    }

    public Task<RelationshipOperationState> GetStateAsync(
        Guid tenantId,
        Guid relationshipId,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        lock (gate)
            return Task.FromResult(
                states.TryGetValue((tenantId, relationshipId), out var state)
                    ? state
                    : RelationshipOperationState.Empty(tenantId, relationshipId, now)
            );
    }

    public Task SaveStateAsync(RelationshipOperationState state, CancellationToken ct)
    {
        lock (gate)
            states[(state.TenantId, state.RelationshipId)] = state;
        return Task.CompletedTask;
    }

    public Task<AgentOperationSettings> GetSettingsAsync(CancellationToken ct)
    {
        lock (gate)
            return Task.FromResult(settings);
    }

    public Task SaveSettingsAsync(AgentOperationSettings value, string actor, CancellationToken ct)
    {
        lock (gate)
            settings = value;
        return Task.CompletedTask;
    }

    public Task CountAsync(
        DateOnly day,
        string relationshipRef,
        string metric,
        int by,
        CancellationToken ct
    )
    {
        lock (gate)
        {
            var key = (day, relationshipRef, metric);
            counters[key] = counters.GetValueOrDefault(key) + by;
        }
        return Task.CompletedTask;
    }

    public Task<IReadOnlyList<OperationCounter>> CountersAsync(
        DateOnly from,
        DateOnly to,
        CancellationToken ct
    )
    {
        lock (gate)
            return Task.FromResult<IReadOnlyList<OperationCounter>>(
                counters
                    .Where(pair => pair.Key.Item1 >= from && pair.Key.Item1 <= to)
                    .Select(pair => new OperationCounter(
                        pair.Key.Item1,
                        pair.Key.Item2,
                        pair.Key.Item3,
                        pair.Value
                    ))
                    .OrderBy(counter => counter.Day)
                    .ToArray()
            );
    }
}

/// <summary>
/// Postgres storage. Tenant tables run under row security with the tenant set per transaction; the settings and
/// counter tables hold no tenant data (no content, hashed relationship references only).
/// </summary>
public sealed class PostgresAgentOperationStore(
    IDbContextFactory<ConversationStoreDbContext> conversations
) : IAgentOperationStore
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public async Task<IReadOnlyList<OperationItem>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        var rows = await db
            .Database.SqlQuery<DocRow>(
                $"""
                SELECT doc::text AS "Doc"
                FROM business.agent_operation_items
                WHERE tenant_id={tenantId} AND relationship_id={relationshipId}
                ORDER BY created_at, item_id
                LIMIT 2000
                """
            )
            .ToListAsync(ct);
        await transaction.CommitAsync(ct);
        return rows.Select(row => Read(row.Doc)).ToArray();
    }

    public async Task<OperationItem?> GetAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        var row = await db
            .Database.SqlQuery<DocRow>(
                $"""
                SELECT doc::text AS "Doc"
                FROM business.agent_operation_items
                WHERE tenant_id={tenantId} AND relationship_id={relationshipId} AND item_id={itemId}
                """
            )
            .FirstOrDefaultAsync(ct);
        await transaction.CommitAsync(ct);
        return row is null ? null : Read(row.Doc);
    }

    public async Task<bool> InsertAsync(OperationItem item, CancellationToken ct)
    {
        var doc = JsonSerializer.Serialize(item, Json);
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, item.TenantId, ct);
        var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.agent_operation_items
                (tenant_id,relationship_id,item_id,kind,version_no,doc,created_at,updated_at)
            VALUES ({item.TenantId},{item.RelationshipId},{item.ItemId},{item.Kind},{item.VersionNo},
                {doc}::jsonb,{item.CreatedAt},{item.UpdatedAt})
            ON CONFLICT (tenant_id,relationship_id,item_id) DO NOTHING
            """,
            ct
        );
        if (inserted == 1)
            await AppendVersionAsync(db, item, doc, ct);
        await transaction.CommitAsync(ct);
        return inserted == 1;
    }

    public async Task<bool> UpdateAsync(
        OperationItem item,
        int expectedVersion,
        CancellationToken ct
    )
    {
        var doc = JsonSerializer.Serialize(item, Json);
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, item.TenantId, ct);
        var updated = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.agent_operation_items
            SET version_no={item.VersionNo},doc={doc}::jsonb,updated_at={item.UpdatedAt}
            WHERE tenant_id={item.TenantId} AND relationship_id={item.RelationshipId}
                AND item_id={item.ItemId} AND version_no={expectedVersion}
            """,
            ct
        );
        if (updated == 1)
            await AppendVersionAsync(db, item, doc, ct);
        await transaction.CommitAsync(ct);
        return updated == 1;
    }

    private static Task<int> AppendVersionAsync(
        ConversationStoreDbContext db,
        OperationItem item,
        string doc,
        CancellationToken ct
    ) =>
        db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.agent_operation_item_versions
                (tenant_id,relationship_id,item_id,version_no,doc,recorded_at)
            VALUES ({item.TenantId},{item.RelationshipId},{item.ItemId},{item.VersionNo},{doc}::jsonb,
                {item.UpdatedAt})
            ON CONFLICT (tenant_id,item_id,version_no) DO NOTHING
            """,
            ct
        );

    public async Task<IReadOnlyList<OperationItem>> VersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid itemId,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        var rows = await db
            .Database.SqlQuery<DocRow>(
                $"""
                SELECT doc::text AS "Doc"
                FROM business.agent_operation_item_versions
                WHERE tenant_id={tenantId} AND relationship_id={relationshipId} AND item_id={itemId}
                ORDER BY version_no
                LIMIT 500
                """
            )
            .ToListAsync(ct);
        await transaction.CommitAsync(ct);
        return rows.Select(row => Read(row.Doc)).ToArray();
    }

    public async Task<RelationshipOperationState> GetStateAsync(
        Guid tenantId,
        Guid relationshipId,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        var row = await db
            .Database.SqlQuery<DocRow>(
                $"""
                SELECT doc::text AS "Doc"
                FROM business.agent_operation_state
                WHERE tenant_id={tenantId} AND relationship_id={relationshipId}
                """
            )
            .FirstOrDefaultAsync(ct);
        await transaction.CommitAsync(ct);
        return row is null
            ? RelationshipOperationState.Empty(tenantId, relationshipId, now)
            : JsonSerializer.Deserialize<RelationshipOperationState>(row.Doc, Json)!;
    }

    public async Task SaveStateAsync(RelationshipOperationState state, CancellationToken ct)
    {
        var doc = JsonSerializer.Serialize(state, Json);
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, state.TenantId, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.agent_operation_state (tenant_id,relationship_id,doc,updated_at)
            VALUES ({state.TenantId},{state.RelationshipId},{doc}::jsonb,{state.UpdatedAt})
            ON CONFLICT (tenant_id,relationship_id)
            DO UPDATE SET doc=EXCLUDED.doc,updated_at=EXCLUDED.updated_at
            """,
            ct
        );
        await transaction.CommitAsync(ct);
    }

    public async Task<AgentOperationSettings> GetSettingsAsync(CancellationToken ct)
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        var row = await db
            .Database.SqlQuery<DocRow>(
                $"""
                SELECT doc::text AS "Doc" FROM business.agent_operation_settings WHERE setting_key='platform'
                """
            )
            .FirstOrDefaultAsync(ct);
        return row is null
            ? AgentOperationSettings.Default
            : JsonSerializer.Deserialize<AgentOperationSettings>(row.Doc, Json)
                ?? AgentOperationSettings.Default;
    }

    public async Task SaveSettingsAsync(
        AgentOperationSettings settings,
        string actor,
        CancellationToken ct
    )
    {
        var doc = JsonSerializer.Serialize(settings, Json);
        await using var db = await conversations.CreateDbContextAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.agent_operation_settings (setting_key,doc,updated_at,updated_by)
            VALUES ('platform',{doc}::jsonb,now(),{actor})
            ON CONFLICT (setting_key)
            DO UPDATE SET doc=EXCLUDED.doc,updated_at=now(),updated_by=EXCLUDED.updated_by
            """,
            ct
        );
    }

    public async Task CountAsync(
        DateOnly day,
        string relationshipRef,
        string metric,
        int by,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.agent_operation_counters (day,relationship_ref,metric,total)
            VALUES ({day},{relationshipRef},{metric},{by})
            ON CONFLICT (day,relationship_ref,metric)
            DO UPDATE SET total=business.agent_operation_counters.total+EXCLUDED.total
            """,
            ct
        );
    }

    public async Task<IReadOnlyList<OperationCounter>> CountersAsync(
        DateOnly from,
        DateOnly to,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        var rows = await db
            .Database.SqlQuery<CounterRow>(
                $"""
                SELECT day AS "Day",relationship_ref AS "RelationshipRef",metric AS "Metric",total AS "Total"
                FROM business.agent_operation_counters
                WHERE day >= {from} AND day <= {to}
                ORDER BY day,relationship_ref,metric
                LIMIT 20000
                """
            )
            .ToListAsync(ct);
        return rows.Select(row => new OperationCounter(
                row.Day,
                row.RelationshipRef,
                row.Metric,
                row.Total
            ))
            .ToArray();
    }

    private static OperationItem Read(string doc) =>
        JsonSerializer.Deserialize<OperationItem>(doc, Json)!;

    private sealed class DocRow
    {
        public string Doc { get; init; } = "";
    }

    private sealed class CounterRow
    {
        public DateOnly Day { get; init; }
        public string RelationshipRef { get; init; } = "";
        public string Metric { get; init; } = "";
        public int Total { get; init; }
    }
}
