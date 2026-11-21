// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Workbench;

/// <summary>One recorded version of a goal; <see cref="VersionNo"/> is assigned by the store when it is appended.</summary>
public sealed record WorkbenchGoalVersionEntry(
    int VersionNo,
    DateTimeOffset RevisedAt,
    string RevisedBy,
    string? Reason,
    string Title,
    IReadOnlyDictionary<string, string> Parameters
);

/// <summary>The append-only history of the goal versions the workbench wrote.</summary>
public interface IWorkbenchGoalHistoryStore
{
    Task AppendAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        WorkbenchGoalVersionEntry entry,
        CancellationToken ct
    );

    Task<IReadOnlyList<WorkbenchGoalVersionEntry>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        CancellationToken ct
    );

    /// <summary>The highest recorded version number of each goal of the relationship that has any.</summary>
    Task<IReadOnlyDictionary<Guid, int>> LatestVersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    );
}

public sealed class PostgresWorkbenchGoalHistoryStore(
    IDbContextFactory<ConversationStoreDbContext> conversations
) : IWorkbenchGoalHistoryStore
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    public async Task AppendAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        WorkbenchGoalVersionEntry entry,
        CancellationToken ct
    )
    {
        var parameters = JsonSerializer.Serialize(entry.Parameters, Json);
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({"workbench-goal-version:" + goalId.ToString("N")},0))",
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.workbench_goal_versions
                (tenant_id,relationship_id,goal_id,version_no,revised_at,revised_by,reason,title,parameters)
            SELECT {tenantId},{relationshipId},{goalId},COALESCE(MAX(version_no),0)+1,{entry.RevisedAt},
                {entry.RevisedBy},{entry.Reason},{entry.Title},{parameters}::jsonb
            FROM business.workbench_goal_versions
            WHERE tenant_id={tenantId} AND goal_id={goalId}
            """,
            ct
        );
        await transaction.CommitAsync(ct);
    }

    public async Task<IReadOnlyList<WorkbenchGoalVersionEntry>> ListAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid goalId,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        var rows = await db
            .Database.SqlQuery<VersionRow>(
                $"""
                SELECT version_no AS "VersionNo",revised_at AS "RevisedAt",revised_by AS "RevisedBy",
                    reason AS "Reason",title AS "Title",parameters::text AS "ParametersJson"
                FROM business.workbench_goal_versions
                WHERE tenant_id={tenantId} AND relationship_id={relationshipId} AND goal_id={goalId}
                ORDER BY version_no
                """
            )
            .ToListAsync(ct);
        await transaction.CommitAsync(ct);
        return rows.Select(row => new WorkbenchGoalVersionEntry(
                row.VersionNo,
                row.RevisedAt,
                row.RevisedBy,
                row.Reason,
                row.Title,
                JsonSerializer.Deserialize<SortedDictionary<string, string>>(
                    row.ParametersJson,
                    Json
                ) ?? new SortedDictionary<string, string>(StringComparer.Ordinal)
            ))
            .ToArray();
    }

    public async Task<IReadOnlyDictionary<Guid, int>> LatestVersionsAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        var rows = await db
            .Database.SqlQuery<LatestRow>(
                $"""
                SELECT goal_id AS "GoalId",MAX(version_no) AS "Latest"
                FROM business.workbench_goal_versions
                WHERE tenant_id={tenantId} AND relationship_id={relationshipId}
                GROUP BY goal_id
                """
            )
            .ToListAsync(ct);
        await transaction.CommitAsync(ct);
        return rows.ToDictionary(row => row.GoalId, row => row.Latest);
    }

    private sealed class VersionRow
    {
        public int VersionNo { get; init; }
        public DateTimeOffset RevisedAt { get; init; }
        public string RevisedBy { get; init; } = "";
        public string? Reason { get; init; }
        public string Title { get; init; } = "";
        public string ParametersJson { get; init; } = "{}";
    }

    private sealed class LatestRow
    {
        public Guid GoalId { get; init; }
        public int Latest { get; init; }
    }
}
