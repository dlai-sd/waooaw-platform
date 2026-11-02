// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md S11-S13
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Data;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppTrafficBudget(
    IDbContextFactory<ConversationStoreDbContext> conversations,
    IWhatsAppCapabilityGate gate,
    TimeProvider clock
)
{
    public async Task<WhatsAppActivationAuthority> ReserveAsync(
        WhatsAppProviderDispatchRequest request,
        string recipientBindingDigest,
        CancellationToken cancellationToken
    )
    {
        var now = clock.GetUtcNow();
        gate.RequireRecipient(request.TenantId, recipientBindingDigest, now);
        var authority = gate.RequireActive(now);
        if (
            authority.TenantId != request.TenantId
            || authority.Environment != request.Environment
            || authority.RecipientBindingDigest != recipientBindingDigest
        )
            throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        var digest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(authority.ActivationReference))
        );
        var authorityDigest = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(authority)))
        );
        await using var db = await conversations.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            cancellationToken
        );
        var leaseIsCurrent = await db
            .ConversationOutbox.AsNoTracking()
            .AnyAsync(
                value =>
                    value.OutboxId == request.OutboxId
                    && value.TenantId == request.TenantId
                    && value.Environment == request.Environment
                    && value.State == "DISPATCHING"
                    && value.AttemptNumber == request.AttemptNumber
                    && value.LeaseExpiresAt > now,
                cancellationToken
            );
        if (!leaseIsCurrent)
            throw new WhatsAppCapabilityUnavailableException("OUTBOUND_LEASE_EXPIRED");

        var reservations = db.Set<WhatsAppTrafficReservation>()
            .Where(value => value.TenantId == request.TenantId && value.ActivationDigest == digest);
        if (
            await reservations.AnyAsync(
                value => value.AuthorityDigest != authorityDigest,
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("ACTIVATION_RECORD_CHANGED");
        if (
            await reservations.AnyAsync(
                value => value.OutboxId == request.OutboxId,
                cancellationToken
            )
        )
            throw new WhatsAppCapabilityUnavailableException("OUTBOUND_ALREADY_RESERVED");
        var count = await reservations.CountAsync(cancellationToken);
        var minuteStartsAt = now.AddMinutes(-1);
        var recentCount = await reservations.CountAsync(
            value => value.ReservedAt > minuteStartsAt,
            cancellationToken
        );
        if (
            count >= authority.MaximumMessages
            || count
                >= decimal.Floor(authority.MaximumSpendInr / authority.MaximumCostPerMessageInr)
            || recentCount >= authority.MaximumMessagesPerMinute
        )
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_EXHAUSTED");

        db.Set<WhatsAppTrafficReservation>()
            .Add(
                new()
                {
                    TenantId = request.TenantId,
                    ActivationDigest = digest,
                    AuthorityDigest = authorityDigest,
                    OutboxId = request.OutboxId,
                    AttemptNumber = request.AttemptNumber,
                    ReservedCostInr = authority.MaximumCostPerMessageInr,
                    ReservedAt = now,
                }
            );
        try
        {
            await db.SaveChangesAsync(cancellationToken);
            await transaction.CommitAsync(cancellationToken);
        }
        catch (InvalidOperationException failure)
            when (failure.InnerException
                    is DbUpdateException
                    {
                        InnerException: Npgsql.PostgresException { SqlState: "40001" }
                    }
            )
        {
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_CONCURRENT_CHANGE");
        }
        catch (DbUpdateException failure)
            when (failure.InnerException is Npgsql.PostgresException { SqlState: "40001" })
        {
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_CONCURRENT_CHANGE");
        }
        catch (Npgsql.PostgresException failure) when (failure.SqlState == "40001")
        {
            throw new WhatsAppCapabilityUnavailableException("TRAFFIC_BUDGET_CONCURRENT_CHANGE");
        }
        return authority;
    }
}
