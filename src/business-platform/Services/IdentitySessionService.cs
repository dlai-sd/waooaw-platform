// Implements: architecture/reference/data/identity-security-data-contract.md §Session Projection
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R003, WC105-R006, WC105-R008, WC105-R013
// Constitutional basis: C-001, C-007, C-026, C-059, C-063

using System.Data;
using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record IdentityManagedSession(
    Guid SessionId,
    DateTimeOffset IssuedAt,
    DateTimeOffset LastSeenAt,
    DateTimeOffset ExpiresAt,
    string AssuranceLevel,
    string Provider,
    string DeviceLabel,
    bool Current
);

public sealed class IdentitySessionService
{
    private readonly IDbContextFactory<IdentityDbContext> _factory;
    private readonly IdentitySecurityEventService _events;
    private readonly byte[] _key;

    public IdentitySessionService(
        IDbContextFactory<IdentityDbContext> factory,
        IdentitySecurityEventService events,
        IOptions<IdentityHmacOptions> options
    )
    {
        _factory = factory;
        _events = events;
        var key = options.Value.Key;
        if (string.IsNullOrEmpty(key) || key.Length < IdentityHmacOptions.MinKeyLength)
            throw new InvalidOperationException("Identity sessions require valid HMAC material.");
        _key = Encoding.UTF8.GetBytes(key);
    }

    public async Task<Guid> ObserveAsync(
        Guid accountId,
        string actorIdentifier,
        string sourceSessionId,
        DateTimeOffset issuedAt,
        DateTimeOffset expiresAt,
        string assuranceClass,
        string providerClass,
        CancellationToken ct
    )
    {
        if (expiresAt <= DateTimeOffset.UtcNow || expiresAt <= issuedAt)
            throw new IdentityActionDeniedException("IDENTITY_SESSION_REQUIRED");
        var accountRef = Reference("account", accountId.ToString("D"));
        var actorRef = Reference("actor", actorIdentifier);
        var sessionId = SessionId(sourceSessionId);
        var establishmentEvent = new IdentitySecurityEventInput(
            Guid.NewGuid(),
            $"session-observed:{sessionId:D}",
            "SESSION_ESTABLISHMENT",
            providerClass,
            "SUCCEEDED",
            "SESSION_ACTIVE",
            assuranceClass,
            "BUSINESS_PLATFORM",
            actorIdentifier,
            sourceSessionId,
            issuedAt
        );
        await ObserveSessionAsync(
            accountRef,
            actorRef,
            sessionId,
            issuedAt,
            expiresAt,
            assuranceClass,
            providerClass,
            establishmentEvent,
            ct
        );
        return sessionId;
    }

    private async Task ObserveSessionAsync(
        string accountRef,
        string actorRef,
        Guid sessionId,
        DateTimeOffset issuedAt,
        DateTimeOffset expiresAt,
        string assuranceClass,
        string providerClass,
        IdentitySecurityEventInput establishmentEvent,
        CancellationToken ct
    )
    {
        await using var db = await _factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await AcquireAccountLockAsync(db, accountRef, ct);
        await SetAccountContextAsync(db, accountRef, ct);
        var generation = await db.IdentitySessionGenerations.FindAsync([accountRef], ct);
        if (generation?.RevokedBefore is { } revokedBefore && issuedAt <= revokedBefore)
            throw new IdentityActionDeniedException("IDENTITY_SESSION_REVOKED");

        var session = await db.IdentitySessions.FindAsync([sessionId], ct);
        if (session?.RevokedAt is not null)
            throw new IdentityActionDeniedException("IDENTITY_SESSION_REVOKED");
        if (session is null)
        {
            db.IdentitySessions.Add(
                new IdentitySessionRecord
                {
                    SessionId = sessionId,
                    AccountRef = accountRef,
                    ActorRef = actorRef,
                    IssuedAt = issuedAt,
                    LastSeenAt = DateTimeOffset.UtcNow,
                    AbsoluteExpiresAt = expiresAt,
                    AssuranceClass = assuranceClass,
                    ProviderClass = providerClass,
                    DeviceLabel = "Browser session",
                }
            );
        }
        else
        {
            if (session.AccountRef != accountRef || session.ActorRef != actorRef)
                throw new IdentityActionDeniedException("IDENTITY_SESSION_REQUIRED");
            session.LastSeenAt = DateTimeOffset.UtcNow;
        }
        await db.SaveChangesAsync(ct);
        await _events.RecordAsync(establishmentEvent, db, ct);
        await transaction.CommitAsync(ct);
    }

    public async Task<IReadOnlyList<IdentityManagedSession>> ListAsync(
        Guid accountId,
        Guid currentSessionId,
        CancellationToken ct
    )
    {
        var accountRef = Reference("account", accountId.ToString("D"));
        await using var db = await _factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetAccountContextAsync(db, accountRef, ct);
        var sessions = await db
            .IdentitySessions.Where(value =>
                value.AccountRef == accountRef
                && value.RevokedAt == null
                && value.AbsoluteExpiresAt > DateTimeOffset.UtcNow
            )
            .OrderByDescending(value => value.LastSeenAt)
            .Select(value => new IdentityManagedSession(
                value.SessionId,
                value.IssuedAt,
                value.LastSeenAt,
                value.AbsoluteExpiresAt,
                value.AssuranceClass,
                value.ProviderClass,
                value.SessionId == currentSessionId ? "Current browser" : value.DeviceLabel,
                value.SessionId == currentSessionId
            ))
            .ToListAsync(ct);
        await transaction.CommitAsync(ct);
        return sessions;
    }

    public async Task<int> RevokeOneAsync(
        Guid accountId,
        string actorIdentifier,
        Guid sessionId,
        string sourceEventId,
        CancellationToken ct
    )
    {
        var accountRef = Reference("account", accountId.ToString("D"));
        await using var db = await _factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await AcquireAccountLockAsync(db, accountRef, ct);
        await SetAccountContextAsync(db, accountRef, ct);
        var session =
            await db.IdentitySessions.SingleOrDefaultAsync(
                value => value.SessionId == sessionId && value.AccountRef == accountRef,
                ct
            )
            ?? throw new IdentityResourceNotFoundException("Session not found or not accessible.");
        var changed = session.RevokedAt is null ? 1 : 0;
        if (changed == 1)
        {
            session.RevokedAt = DateTimeOffset.UtcNow;
            session.RevocationReason = "CUSTOMER_REVOKED";
            await db.SaveChangesAsync(ct);
        }
        await transaction.CommitAsync(ct);
        await RecordRevocationAsync(
            "SESSION_REVOCATION_ONE",
            actorIdentifier,
            sessionId,
            sourceEventId,
            ct
        );
        return changed;
    }

    public async Task<int> RevokeAllAsync(
        Guid accountId,
        string actorIdentifier,
        string sourceEventId,
        CancellationToken ct
    )
    {
        var accountRef = Reference("account", accountId.ToString("D"));
        var now = DateTimeOffset.UtcNow;
        await using var db = await _factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.ReadCommitted,
            ct
        );
        await AcquireAccountLockAsync(db, accountRef, ct);
        await SetAccountContextAsync(db, accountRef, ct);
        var generation = await db.IdentitySessionGenerations.FindAsync([accountRef], ct);
        if (generation is null)
        {
            generation = new IdentitySessionGenerationRecord
            {
                AccountRef = accountRef,
                Generation = 1,
                RevokedBefore = now,
                UpdatedAt = now,
            };
            db.IdentitySessionGenerations.Add(generation);
        }
        else
        {
            generation.Generation += 1;
            generation.RevokedBefore = now;
            generation.UpdatedAt = now;
        }
        var active = await db
            .IdentitySessions.Where(value =>
                value.AccountRef == accountRef && value.RevokedAt == null
            )
            .ToListAsync(ct);
        foreach (var session in active)
        {
            session.RevokedAt = now;
            session.RevocationReason = "CUSTOMER_REVOKED_ALL";
        }
        await db.SaveChangesAsync(ct);
        await transaction.CommitAsync(ct);
        await RecordRevocationAsync(
            "SESSION_REVOCATION_ALL",
            actorIdentifier,
            null,
            sourceEventId,
            ct
        );
        return active.Count;
    }

    private Task RecordRevocationAsync(
        string eventType,
        string actorIdentifier,
        Guid? sessionId,
        string sourceEventId,
        CancellationToken ct
    ) =>
        _events.RecordAsync(
            new IdentitySecurityEventInput(
                Guid.NewGuid(),
                sourceEventId,
                eventType,
                "INTERNAL",
                "SUCCEEDED",
                "CUSTOMER_REQUESTED",
                "AAL2",
                "BUSINESS_PLATFORM",
                actorIdentifier,
                sessionId?.ToString("D")
            ),
            ct
        );

    private static Task SetAccountContextAsync(
        IdentityDbContext db,
        string accountRef,
        CancellationToken ct
    ) =>
        db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_catalog.set_config('app.identity_account_ref', {accountRef}, true)",
            ct
        );

    private static Task AcquireAccountLockAsync(
        IdentityDbContext db,
        string accountRef,
        CancellationToken ct
    ) =>
        db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock({AdvisoryLockKey(accountRef)})",
            ct
        );

    private static long AdvisoryLockKey(string accountRef)
    {
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes($"identity-session:{accountRef}"));
        return BitConverter.ToInt64(digest, 0);
    }

    private string Reference(string purpose, string value) =>
        Convert
            .ToHexString(
                HMACSHA256.HashData(_key, Encoding.UTF8.GetBytes($"wc103:{purpose}:{value}"))
            )
            .ToLowerInvariant();

    public Guid SessionId(string sourceSessionId)
    {
        if (string.IsNullOrWhiteSpace(sourceSessionId))
            throw new IdentityActionDeniedException("IDENTITY_SESSION_REQUIRED");
        var bytes = HMACSHA256.HashData(
            _key,
            Encoding.UTF8.GetBytes($"wc103:session-id:{sourceSessionId}")
        );
        return new Guid(bytes.AsSpan(0, 16));
    }
}
