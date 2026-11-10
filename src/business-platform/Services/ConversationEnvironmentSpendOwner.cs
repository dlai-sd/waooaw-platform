// Implements: work-contracts/WC-134-batching-offering-and-spend-work-component.md §9.4
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

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

public sealed class ConversationEnvironmentSpendOwner
{
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
        CancellationToken ct
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
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({"environment-spend:" + environment},0))",
            ct
        );
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
        var existing = await db
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
        var exposure = await ExposureAsync(db, environment, now, ct);
        if (existing is not null)
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
                Math.Min(authority.MaximumPaise, activeLimitPaise)
            );
        }
        if (
            await db
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
        var effectiveMaximum = Math.Min(authority.MaximumPaise, activeLimitPaise);
        if (checked(exposure + reservedPaise) > effectiveMaximum)
            throw new WhatsAppCapabilityUnavailableException("COMBINED_DAILY_COST_EXHAUSTED");
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
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({"environment-spend:" + environment},0))",
            ct
        );
        var row =
            await db
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
                .SingleOrDefaultAsync(ct)
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
