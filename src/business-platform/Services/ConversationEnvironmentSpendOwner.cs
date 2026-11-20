// Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.4
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-05
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-06
// Constitutional basis: C-023, C-059, C-063
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Spend;

namespace Waooaw.BusinessPlatform.Services;

public sealed record EnvironmentSpendPermit(
    string Environment,
    string OwnerKind,
    Guid AttemptId,
    Guid ReservationReference,
    long ReservedPaise,
    long ExposurePaise,
    long MaximumPaise
);

public sealed class ConversationEnvironmentSpendOwner(
    EnvironmentSpendOptions? options = null,
    EnvironmentSpendLeaseService? leases = null
)
{
    private readonly EnvironmentSpendOptions _options = options ?? new EnvironmentSpendOptions();

    public async Task<EnvironmentSpendPermit> ReserveAsync(
        ConversationStoreDbContext db,
        string environment,
        string ownerKind,
        Guid attemptId,
        Guid originalTenantId,
        string activationDigest,
        string requestDigest,
        Guid reservationReference,
        long reservedPaise,
        long activeLimitPaise,
        DateTimeOffset now,
        CancellationToken ct,
        SpendAccountPin? pin = null
    )
    {
        if (
            environment.Length is < 1 or > 32
            || ownerKind is not ("MODEL" or "MESSAGING")
            || attemptId == Guid.Empty
            || reservationReference == Guid.Empty
            || reservedPaise < 0
            || activeLimitPaise < 0
        )
            throw new WhatsAppCapabilityUnavailableException("ENVIRONMENT_SPEND_IDENTITY_INVALID");
        var canonicalRequestDigest = requestDigest.StartsWith("sha256:", StringComparison.Ordinal)
            ? requestDigest["sha256:".Length..]
            : requestDigest;
        if (
            canonicalRequestDigest.Length != 64
            || canonicalRequestDigest.Any(value =>
                value is not (>= '0' and <= '9') and not (>= 'a' and <= 'f')
            )
        )
            throw new WhatsAppCapabilityUnavailableException("ENVIRONMENT_SPEND_IDENTITY_INVALID");
        if (!db.Database.IsNpgsql())
            return new(
                environment,
                ownerKind,
                attemptId,
                reservationReference,
                reservedPaise,
                reservedPaise,
                activeLimitPaise
            );
        // The platform floor is always counted but never refused by the ceiling or the fence.
        var bypassLimits = pin?.AccountClass == SpendAccountClass.PlatformFloor;
        var useLease =
            !bypassLimits
            && leases is not null
            && _options.UsesLeases
            && reservedPaise > 0
            && reservedPaise <= leases.LeaseSizePaise;
        if (!useLease)
            await LockEnvironmentAsync(db, environment, ct);
        var authority =
            await db
                .Database.SqlQuery<AuthorityRow>(
                    $"""
                    SELECT environment AS "Environment",maximum_paise AS "MaximumPaise",
                        active AS "Active",migration_complete AS "MigrationComplete"
                    FROM business.environment_spend_authorities
                    WHERE environment={environment}
                    """
                )
                .SingleOrDefaultAsync(ct)
            ?? throw new WhatsAppCapabilityUnavailableException(
                "ENVIRONMENT_SPEND_AUTHORITY_UNAVAILABLE"
            );
        if (!authority.Active || !authority.MigrationComplete)
            throw new WhatsAppCapabilityUnavailableException(
                "ENVIRONMENT_SPEND_RECONCILIATION_REQUIRED"
            );
        var effectiveMaximum = Math.Min(authority.MaximumPaise, activeLimitPaise);
        var existing = await ReadAttemptAsync(db, environment, ownerKind, attemptId, ct);
        var exposure = await ExposureAsync(db, environment, now, ct);
        if (existing is not null)
            return ReplayPermit(
                existing,
                environment,
                ownerKind,
                attemptId,
                originalTenantId,
                activationDigest,
                canonicalRequestDigest,
                reservationReference,
                reservedPaise,
                exposure,
                effectiveMaximum
            );
        if (
            !bypassLimits
            && await db
                .Database.SqlQuery<int>(
                    $"""
                    SELECT 1 AS "Value" FROM business.environment_spend_attempts
                    WHERE environment={environment}
                      AND (overrun OR state='RECONCILIATION_REQUIRED') LIMIT 1
                    """
                )
                .AnyAsync(ct)
        )
            throw new WhatsAppCapabilityUnavailableException("ENVIRONMENT_SPEND_ADMISSION_FENCED");
        if (useLease)
        {
            var leaseInserted = await InsertFromLeaseAsync(
                db,
                environment,
                ownerKind,
                attemptId,
                originalTenantId,
                activationDigest,
                canonicalRequestDigest,
                reservationReference,
                reservedPaise,
                effectiveMaximum,
                now,
                pin,
                ct
            );
            if (leaseInserted)
                return new(
                    environment,
                    ownerKind,
                    attemptId,
                    reservationReference,
                    reservedPaise,
                    exposure + reservedPaise,
                    effectiveMaximum
                );
            var replay =
                await ReadAttemptAsync(db, environment, ownerKind, attemptId, ct)
                ?? throw new ConversationStateConflictException();
            return ReplayPermit(
                replay,
                environment,
                ownerKind,
                attemptId,
                originalTenantId,
                activationDigest,
                canonicalRequestDigest,
                reservationReference,
                reservedPaise,
                exposure,
                effectiveMaximum
            );
        }
        if (!bypassLimits && checked(exposure + reservedPaise) > effectiveMaximum)
            throw new WhatsAppCapabilityUnavailableException("COMBINED_DAILY_COST_EXHAUSTED");
        if (pin is null)
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.environment_spend_attempts
                    (environment,owner_kind,attempt_id,original_tenant_id,activation_digest,
                     request_digest,reservation_reference,reserved_paise,state,reserved_at)
                VALUES ({environment},{ownerKind},{attemptId},{originalTenantId},{activationDigest},
                    {canonicalRequestDigest},{reservationReference},{reservedPaise},'RESERVED',{now})
                """,
                ct
            );
        else
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.environment_spend_attempts
                    (environment,owner_kind,attempt_id,original_tenant_id,activation_digest,
                     request_digest,reservation_reference,reserved_paise,state,reserved_at,
                     account_class,pinned_wallet_account_id)
                VALUES ({environment},{ownerKind},{attemptId},{originalTenantId},{activationDigest},
                    {canonicalRequestDigest},{reservationReference},{reservedPaise},'RESERVED',{now},
                    {pin.AccountClass.ToStorage()},{pin.PinnedWalletAccountId})
                """,
                ct
            );
        return new(
            environment,
            ownerKind,
            attemptId,
            reservationReference,
            reservedPaise,
            exposure + reservedPaise,
            effectiveMaximum
        );
    }

    public async Task SettleAsync(
        ConversationStoreDbContext db,
        string environment,
        string ownerKind,
        Guid attemptId,
        Guid reservationReference,
        long actualPaise,
        bool release,
        Guid evidenceId,
        DateTimeOffset usageAt,
        CancellationToken ct
    )
    {
        if (!db.Database.IsNpgsql())
            return;
        if (!_options.UsesLeases)
            await LockEnvironmentAsync(db, environment, ct);
        var row =
            await ReadAttemptAsync(db, environment, ownerKind, attemptId, ct)
            ?? throw new ConversationNotAccessibleException();
        if (row.ReservationReference != reservationReference)
            throw new ConversationStateConflictException();
        var state = release ? "RELEASED" : "SETTLED";
        var actual = release ? 0 : actualPaise;
        if (row.State is "SETTLED" or "RELEASED")
        {
            if (row.State != state || row.ActualPaise != actual)
                throw new ConversationStateConflictException();
            return;
        }
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"""
            UPDATE business.environment_spend_attempts
            SET actual_paise={actual},state={state},overrun={actual > row.ReservedPaise},
                usage_at={usageAt},settlement_evidence_id={evidenceId}
            WHERE environment={environment} AND owner_kind={ownerKind}
                AND attempt_id={attemptId}
            """,
            ct
        );
    }

    public static Task<long> ExposureAsync(
        ConversationStoreDbContext db,
        string environment,
        DateTimeOffset now,
        CancellationToken ct
    ) =>
        db
            .Database.SqlQuery<long>(
                $"SELECT business.environment_spend_exposure({environment},{now}) AS \"Value\""
            )
            .SingleAsync(ct);

    private static Task LockEnvironmentAsync(
        ConversationStoreDbContext db,
        string environment,
        CancellationToken ct
    ) =>
        db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({"environment-spend:" + environment},0))",
            ct
        );

    private static Task<AttemptRow?> ReadAttemptAsync(
        ConversationStoreDbContext db,
        string environment,
        string ownerKind,
        Guid attemptId,
        CancellationToken ct
    ) =>
        db
            .Database.SqlQuery<AttemptRow>(
                $"""
                SELECT owner_kind AS "OwnerKind",attempt_id AS "AttemptId",
                    original_tenant_id AS "OriginalTenantId",
                    activation_digest AS "ActivationDigest",request_digest AS "RequestDigest",
                    reservation_reference AS "ReservationReference",
                    reserved_paise AS "ReservedPaise",state AS "State",
                    actual_paise AS "ActualPaise"
                FROM business.environment_spend_attempts
                WHERE environment={environment} AND owner_kind={ownerKind}
                    AND attempt_id={attemptId} FOR UPDATE
                """
            )
            .SingleOrDefaultAsync(ct);

    private static EnvironmentSpendPermit ReplayPermit(
        AttemptRow existing,
        string environment,
        string ownerKind,
        Guid attemptId,
        Guid originalTenantId,
        string activationDigest,
        string canonicalRequestDigest,
        Guid reservationReference,
        long reservedPaise,
        long exposure,
        long effectiveMaximum
    )
    {
        if (
            existing.OriginalTenantId != originalTenantId
            || existing.ActivationDigest != activationDigest
            || existing.RequestDigest != canonicalRequestDigest
            || existing.ReservationReference != reservationReference
            || existing.ReservedPaise != reservedPaise
        )
            throw new ConversationStateConflictException();
        return new(
            environment,
            ownerKind,
            attemptId,
            reservationReference,
            reservedPaise,
            exposure,
            effectiveMaximum
        );
    }

    private async Task<bool> InsertFromLeaseAsync(
        ConversationStoreDbContext db,
        string environment,
        string ownerKind,
        Guid attemptId,
        Guid originalTenantId,
        string activationDigest,
        string canonicalRequestDigest,
        Guid reservationReference,
        long reservedPaise,
        long effectiveMaximum,
        DateTimeOffset now,
        SpendAccountPin? pin,
        CancellationToken ct
    )
    {
        var accountClass = pin?.AccountClass.ToStorage();
        var pinnedWallet = pin?.PinnedWalletAccountId;
        for (var attempt = 0; attempt < 2; attempt++)
        {
            var draw =
                await leases!.TryDrawAsync(environment, reservedPaise, effectiveMaximum, now, ct)
                ?? throw new WhatsAppCapabilityUnavailableException(
                    "COMBINED_DAILY_COST_EXHAUSTED"
                );
            // The shared row lock keeps the grantor from expiring or returning the lease mid-attempt.
            var live = await db
                .Database.SqlQuery<int>(
                    $"""
                    SELECT 1 AS "Value" FROM business.environment_spend_leases
                    WHERE lease_id={draw.LeaseId} AND state='ACTIVE' AND expires_at > {now}
                    FOR SHARE
                    """
                )
                .SingleOrDefaultAsync(ct);
            if (live != 1)
            {
                await leases.InvalidateAsync(environment, draw.LeaseId, ct);
                continue;
            }
            var inserted = await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.environment_spend_attempts
                    (environment,owner_kind,attempt_id,original_tenant_id,activation_digest,
                     request_digest,reservation_reference,reserved_paise,state,reserved_at,
                     lease_id,account_class,pinned_wallet_account_id)
                VALUES ({environment},{ownerKind},{attemptId},{originalTenantId},{activationDigest},
                    {canonicalRequestDigest},{reservationReference},{reservedPaise},'RESERVED',{now},
                    {draw.LeaseId},{accountClass},{pinnedWallet})
                ON CONFLICT (environment,owner_kind,attempt_id) DO NOTHING
                """,
                ct
            );
            return inserted == 1;
        }
        throw new WhatsAppCapabilityUnavailableException("ENVIRONMENT_SPEND_LEASE_UNAVAILABLE");
    }

    private sealed class AuthorityRow
    {
        public string Environment { get; init; } = "";
        public long MaximumPaise { get; init; }
        public bool Active { get; init; }
        public bool MigrationComplete { get; init; }
    }

    private sealed class AttemptRow
    {
        public string OwnerKind { get; init; } = "";
        public Guid AttemptId { get; init; }
        public Guid OriginalTenantId { get; init; }
        public string ActivationDigest { get; init; } = "";
        public string RequestDigest { get; init; } = "";
        public Guid ReservationReference { get; init; }
        public long ReservedPaise { get; init; }
        public string State { get; init; } = "";
        public long? ActualPaise { get; init; }
    }
}
