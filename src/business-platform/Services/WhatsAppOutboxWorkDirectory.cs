using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

internal sealed record WhatsAppOutboxWork(Guid OutboxId, string SenderHash);

public sealed class WhatsAppOutboxWorkDirectory(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    WhatsAppTenantExecutionScope execution,
    IWhatsAppCapabilityGate capability,
    IOptions<Wc120ConversationOptions> conversationOptions,
    IOptionsMonitor<WhatsAppJourneyOptions> channelOptions,
    TimeProvider clock
)
{
    internal async Task<WhatsAppOutboxWork?> ClaimAsync(CancellationToken ct)
    {
        if (!conversationOptions.Value.Enabled || !channelOptions.CurrentValue.DispatchEnabled)
            return null;
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (
            execution.ServiceTenantId != authority.TenantId
            || execution.CurrentTenantId != authority.TenantId
            || execution.DatabaseTenantOverrideId is not null
            || conversationOptions.Value.Environment != authority.Environment
        )
            throw new WhatsAppCapabilityUnavailableException("OUTBOX_DISCOVERY_SCOPE_REQUIRED");
        execution.RequireUnchangedAuthority();
        await using var db = await conversations.CreateDbContextAsync(ct);
        if (!db.Database.IsNpgsql())
            throw new WhatsAppChannelBindingUnavailableException(
                "Outbox discovery requires PostgreSQL."
            );
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var candidates = await db
            .Database.SqlQuery<WorkRow>(
                $"""
                SELECT outbox_id AS "OutboxId", sender_hash AS "SenderHash"
                FROM business.claim_whatsapp_outbox_work({authority.TenantId}, {authority.Environment})
                """
            )
            .ToListAsync(ct);
        if (candidates.Count > 1)
            throw new ConversationIdempotencyConflictException();
        WhatsAppOutboxWork? work = null;
        if (candidates.Count == 1)
        {
            var row = candidates[0];
            if (
                row.OutboxId == Guid.Empty
                || row.SenderHash.Length != 64
                || row.SenderHash.Any(value =>
                    value is not (>= '0' and <= '9' or >= 'a' and <= 'f')
                )
            )
                throw new ConversationIdempotencyConflictException();
            capability.RequireRecipient(authority.TenantId, row.SenderHash, clock.GetUtcNow());
            work = new(row.OutboxId, row.SenderHash);
        }
        execution.RequireUnchangedAuthority();
        await transaction.CommitAsync(ct);
        return work;
    }

    private sealed class WorkRow
    {
        public Guid OutboxId { get; init; }
        public string SenderHash { get; init; } = string.Empty;
    }
}
