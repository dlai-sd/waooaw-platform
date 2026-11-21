// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02, C6-03
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services.Workbench;

internal static class WorkbenchStoreTenant
{
    public static Task SetAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        CancellationToken ct
    ) =>
        db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT set_config('app.current_tenant_id',{tenantId.ToString("D")},true)",
            ct
        );
}

/// <summary>
/// Postgres receipts of workbench commands. A claim is one insert, so two replicas racing on a key cannot both run the
/// command; an abandoned claim is taken over once its lease has lapsed.
/// </summary>
public sealed class PostgresWorkbenchLedgerStore(
    IDbContextFactory<ConversationStoreDbContext> conversations
) : IWorkbenchLedgerStore
{
    public async Task<WorkbenchLedgerClaim> ClaimAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string digest,
        DateTimeOffset now,
        DateTimeOffset leaseUntil,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, context.TenantId, ct);
        var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.workbench_command_ledger
                (tenant_id,relationship_id,participant_id,idempotency_key,request_digest,state,created_at,lease_expires_at)
            VALUES ({context.TenantId},{context.RelationshipId},{context.ParticipantId},{idempotencyKey},
                {digest},'IN_PROGRESS',{now},{leaseUntil})
            ON CONFLICT (tenant_id,relationship_id,participant_id,idempotency_key) DO NOTHING
            """,
            ct
        );
        if (inserted == 1)
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                DELETE FROM business.workbench_command_ledger
                WHERE tenant_id={context.TenantId} AND created_at < now() - INTERVAL '24 hours'
                """,
                ct
            );
            await transaction.CommitAsync(ct);
            return new(WorkbenchLedgerClaimKind.Claimed);
        }

        var row = await db
            .Database.SqlQuery<LedgerRow>(
                $"""
                SELECT request_digest AS "RequestDigest",state AS "State",
                    result_json::text AS "ResultJson",lease_expires_at AS "LeaseExpiresAt"
                FROM business.workbench_command_ledger
                WHERE tenant_id={context.TenantId} AND relationship_id={context.RelationshipId}
                    AND participant_id={context.ParticipantId} AND idempotency_key={idempotencyKey}
                FOR UPDATE
                """
            )
            .SingleAsync(ct);
        if (
            !CryptographicOperations.FixedTimeEquals(
                Encoding.ASCII.GetBytes(row.RequestDigest.Trim()),
                Encoding.ASCII.GetBytes(digest)
            )
        )
        {
            await transaction.CommitAsync(ct);
            return new(WorkbenchLedgerClaimKind.Conflict);
        }
        if (row.State == "COMPLETED")
        {
            await transaction.CommitAsync(ct);
            return new(WorkbenchLedgerClaimKind.Replay, row.ResultJson);
        }
        if (row.LeaseExpiresAt > now)
        {
            await transaction.CommitAsync(ct);
            return new(WorkbenchLedgerClaimKind.InProgress);
        }
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.workbench_command_ledger SET lease_expires_at={leaseUntil}
            WHERE tenant_id={context.TenantId} AND relationship_id={context.RelationshipId}
                AND participant_id={context.ParticipantId} AND idempotency_key={idempotencyKey}
                AND state='IN_PROGRESS'
            """,
            ct
        );
        await transaction.CommitAsync(ct);
        return new(WorkbenchLedgerClaimKind.Claimed);
    }

    public async Task CompleteAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        string resultJson,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, context.TenantId, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.workbench_command_ledger
            SET state='COMPLETED',result_json={resultJson}::jsonb,completed_at={now}
            WHERE tenant_id={context.TenantId} AND relationship_id={context.RelationshipId}
                AND participant_id={context.ParticipantId} AND idempotency_key={idempotencyKey}
                AND state='IN_PROGRESS'
            """,
            ct
        );
        await transaction.CommitAsync(ct);
    }

    public async Task AbandonAsync(
        WorkbenchContext context,
        Guid idempotencyKey,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, context.TenantId, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            DELETE FROM business.workbench_command_ledger
            WHERE tenant_id={context.TenantId} AND relationship_id={context.RelationshipId}
                AND participant_id={context.ParticipantId} AND idempotency_key={idempotencyKey}
                AND state='IN_PROGRESS'
            """,
            ct
        );
        await transaction.CommitAsync(ct);
    }

    private sealed class LedgerRow
    {
        public string RequestDigest { get; init; } = "";
        public string State { get; init; } = "";
        public string? ResultJson { get; init; }
        public DateTimeOffset LeaseExpiresAt { get; init; }
    }
}

/// <summary>Postgres handoffs; a redemption is one conditional update so it succeeds for exactly one caller.</summary>
public sealed class PostgresWorkbenchHandoffStore(
    IDbContextFactory<ConversationStoreDbContext> conversations
) : IWorkbenchHandoffStore
{
    public async Task InsertAsync(WorkbenchHandoffRecord record, CancellationToken ct)
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, record.TenantId, ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            DELETE FROM business.workbench_handoffs
            WHERE tenant_id={record.TenantId} AND expires_at < now() - INTERVAL '1 hour'
            """,
            ct
        );
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            INSERT INTO business.workbench_handoffs
                (handoff_ref,token_hash,tenant_id,relationship_id,participant_id,purpose,context_ref,
                 created_at,expires_at)
            VALUES ({record.HandoffRef},{record.TokenHash},{record.TenantId},{record.RelationshipId},
                {record.ParticipantId},{record.Purpose},{record.ContextRef},{record.CreatedAt},
                {record.ExpiresAt})
            """,
            ct
        );
        await transaction.CommitAsync(ct);
    }

    public async Task<WorkbenchHandoffRedemption?> ConsumeAsync(
        string tokenHash,
        Guid tenantId,
        Guid relationshipId,
        Guid participantId,
        DateTimeOffset now,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await WorkbenchStoreTenant.SetAsync(db, tenantId, ct);
        var consumed = await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.workbench_handoffs SET consumed_at={now}
            WHERE token_hash={tokenHash} AND tenant_id={tenantId} AND relationship_id={relationshipId}
                AND participant_id={participantId} AND consumed_at IS NULL AND expires_at > {now}
            """,
            ct
        );
        if (consumed != 1)
        {
            await transaction.CommitAsync(ct);
            return null;
        }
        var row = await db
            .Database.SqlQuery<RedemptionRow>(
                $"""
                SELECT purpose AS "Purpose",context_ref AS "ContextRef"
                FROM business.workbench_handoffs
                WHERE token_hash={tokenHash} AND tenant_id={tenantId}
                """
            )
            .SingleAsync(ct);
        await transaction.CommitAsync(ct);
        return new(row.Purpose, row.ContextRef);
    }

    private sealed class RedemptionRow
    {
        public string Purpose { get; init; } = "";
        public string? ContextRef { get; init; }
    }
}
