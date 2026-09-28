// Implements: work-contracts/WC-107-fundamental-customer-journey-integrity.md R015-R016
// constitutional_basis: C-002, C-023, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record MyAgentsSelectionCreated(string Handle, DateTimeOffset ExpiresAt);
public sealed record MyAgentsSelectionConsumed(Guid RelationshipId, string OutcomeKind);

public sealed class MyAgentsSelectionService(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    TimeProvider timeProvider
)
{
    private static readonly ISet<string> OutcomeKinds = new HashSet<string>(StringComparer.Ordinal)
    {
        "TRIAL_STARTED",
        "HIRE_PAID",
        "HIRE_ZERO_PRICE",
    };

    public async Task<MyAgentsSelectionCreated> CreateAsync(
        Guid tenantId,
        Guid actorParticipantId,
        Guid relationshipId,
        string outcomeKind,
        CancellationToken cancellationToken
    )
    {
        if (!OutcomeKinds.Contains(outcomeKind))
            throw new ArgumentException("Selection outcome is invalid.", nameof(outcomeKind));
        var now = timeProvider.GetUtcNow();
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken
        ) ?? throw new InvalidOperationException("Relationship is unavailable.");
        var authorized = await db.RelationshipParticipants.AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == actorParticipantId
                && value.Status == "ACTIVE",
            cancellationToken
        );
        if (!authorized || !IsAuthoritativeOutcome(relationship, outcomeKind))
            throw new InvalidOperationException("Relationship outcome is not authoritative.");
        if (outcomeKind == "TRIAL_STARTED")
        {
            var activeTrial = await db.RelationshipTrialBindings.AnyAsync(
                value => value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.Status == "ACTIVE"
                    && value.TrialId != null,
                cancellationToken
            );
            if (!activeTrial)
                throw new InvalidOperationException("Trial outcome is not authoritative.");
        }

        var handle = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
        db.MyAgentsSelectionFlash.Add(
            new MyAgentsSelectionFlash
            {
                HandleHash = Hash(handle),
                TenantId = tenantId,
                ActorParticipantId = actorParticipantId,
                RelationshipId = relationshipId,
                OutcomeKind = outcomeKind,
                CreatedAt = now,
                ExpiresAt = now.AddMinutes(5),
            }
        );
        await db.SaveChangesAsync(cancellationToken);
        return new(handle, now.AddMinutes(5));
    }

    public async Task<MyAgentsSelectionConsumed?> ConsumeAsync(
        Guid tenantId,
        Guid actorParticipantId,
        string handle,
        CancellationToken cancellationToken
    )
    {
        if (handle.Length != 64 || !handle.All(Uri.IsHexDigit))
            return null;
        var now = timeProvider.GetUtcNow();
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var record = await db.MyAgentsSelectionFlash.SingleOrDefaultAsync(
            value => value.HandleHash == Hash(handle)
                && value.TenantId == tenantId
                && value.ActorParticipantId == actorParticipantId
                && value.ConsumedAt == null
                && value.ExpiresAt > now,
            cancellationToken
        );
        if (record is null)
            return null;
        var authorized = await db.RelationshipParticipants.AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == record.RelationshipId
                && value.ParticipantId == actorParticipantId
                && value.Status == "ACTIVE",
            cancellationToken
        );
        if (!authorized)
            return null;
        record.ConsumedAt = now;
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateConcurrencyException)
        {
            return null;
        }
        return new(record.RelationshipId, record.OutcomeKind);
    }

    private static bool IsAuthoritativeOutcome(EmploymentRelationship relationship, string outcomeKind) =>
        outcomeKind switch
        {
            "TRIAL_STARTED" => relationship.AcquisitionMode == "TRIAL"
                && relationship.State == EmploymentRelationshipState.TrialActive,
            "HIRE_PAID" or "HIRE_ZERO_PRICE" => relationship.AcquisitionMode == "HIRE"
                && relationship.State >= EmploymentRelationshipState.Configuring,
            _ => false,
        };

    private static string Hash(string handle) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.ASCII.GetBytes(handle)));
}