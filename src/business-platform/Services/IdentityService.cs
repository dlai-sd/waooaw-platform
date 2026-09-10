// Implements: architecture/reference/components/identity-boundary.md §5-§11
// constitutional_basis: C-005, C-007, C-023, C-026, C-059

using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

// ── HMAC options (injected; fails closed when key absent or too short) ────────

public sealed class IdentityHmacOptions
{
    public const int MinKeyLength = 32;
    public string Key { get; set; } = string.Empty;
}

// ── Dispatcher abstraction ────────────────────────────────────────────────────

public interface IIdentityVerificationDispatcher
{
    Task DispatchAsync(IdentityVerificationPurpose purpose, string destination, string code, CancellationToken ct);
}

/// Fail-closed stand-in; replaced by a concrete provider implementation when configured.
public sealed class UnconfiguredVerificationDispatcher : IIdentityVerificationDispatcher
{
    public Task DispatchAsync(IdentityVerificationPurpose purpose, string destination, string code, CancellationToken ct)
        => throw new InvalidOperationException(
            "No IIdentityVerificationDispatcher is configured. OTP delivery cannot proceed.");
}

// ── Additional result type ────────────────────────────────────────────────────

public sealed record IdentityMobileStatusResult(
    bool MobileVerified,
    string MaskedMobile,
    DateTimeOffset VerifiedAt);

// ── Result types ─────────────────────────────────────────────────────────────

public sealed record IdentityCompletionResult(
    string Outcome,
    Guid AccountReference,
    string AssuranceLevel,
    string DefaultTarget);

public sealed record IdentitySessionState(
    Guid AccountReference,
    bool EmailVerified,
    bool MobileVerified);

public sealed record CustomerPortalProfileState(
    Guid AccountReference,
    string DisplayName,
    string OrganizationDisplayName,
    bool EmailVerified,
    bool MobileVerified,
    DateTimeOffset UpdatedAt);

public sealed record CustomerPortalSettingsState(
    string Locale,
    string Theme,
    string TimestampVisibility,
    IReadOnlyList<string> ApprovalRequests,
    IReadOnlyList<string> MaturityReports,
    IReadOnlyList<string> MonthlyNarratives,
    IReadOnlyList<string> SelfGovernanceAlerts,
    DateTimeOffset UpdatedAt);

public sealed class IdentityIdempotencyConflict(string idempotencyKey)
    : Exception($"Idempotency-Key {idempotencyKey} was reused with a different canonical request hash.");

public sealed class IdentityActionDeniedException(string reason) : Exception(reason);
public sealed class IdentityResourceNotFoundException(string reason) : Exception(reason);
public sealed class IdentityChallengeExpiredException(string reason) : Exception(reason);
public sealed class IdentityVerificationRequiredException(string reason) : Exception(reason);
public sealed class IdentityDeliveryUnavailableException(string reason) : Exception(reason);
public sealed class IdentityStepUpRequiredException(string reason, Guid intentId) : Exception(reason)
{
    public Guid IntentId { get; } = intentId;
}

public sealed class IdentityService
{
    private readonly IDbContextFactory<IdentityDbContext> _dbFactory;
    private readonly string _hmacKey;
    private readonly IIdentityVerificationDispatcher _dispatcher;

    private const int Aal3FreshWindowMinutes = 5;

    public IdentityService(
        IDbContextFactory<IdentityDbContext> dbFactory,
        IOptions<IdentityHmacOptions> hmacOptions,
        IIdentityVerificationDispatcher dispatcher)
    {
        _dbFactory = dbFactory ?? throw new ArgumentNullException(nameof(dbFactory));
        _dispatcher = dispatcher ?? throw new ArgumentNullException(nameof(dispatcher));
        var key = hmacOptions?.Value?.Key;
        if (string.IsNullOrEmpty(key) || key.Length < IdentityHmacOptions.MinKeyLength)
            throw new InvalidOperationException(
                $"Identity:HmacKey is absent or too short; minimum {IdentityHmacOptions.MinKeyLength} characters required. " +
                "IdentityService cannot be constructed without valid secret material.");
        _hmacKey = key;
    }

    // ── Registration ────────────────────────────────────────────────────────

    public Task<(IdentityRegistrationRecord reg, bool isNew)> StartRegistrationAsync(
        VerifiedCustomerActor actor, Guid idempotencyKey, string canonicalHash,
        string languagePreference, CancellationToken ct) =>
        MutateGoogleRegistrationAsync(actor, null, idempotencyKey, canonicalHash,
            "StartRegistration", languagePreference, null, null, null, ct);

    public Task<(IdentityRegistrationRecord reg, bool isNew)> UpdateProfileAsync(
        Guid registrationId, VerifiedCustomerActor actor, Guid idempotencyKey, string canonicalHash,
        string displayName, string businessName, string businessDomain, string languagePreference,
        CancellationToken ct) =>
        MutateGoogleRegistrationAsync(actor, registrationId, idempotencyKey, canonicalHash,
            "UpdateProfile", languagePreference, displayName, businessName, businessDomain, ct);

    private async Task<(IdentityRegistrationRecord reg, bool isNew)> MutateGoogleRegistrationAsync(
        VerifiedCustomerActor actor, Guid? registrationId, Guid idempotencyKey, string canonicalHash,
        string operation, string languagePreference, string? displayName, string? businessName,
        string? businessDomain, CancellationToken ct)
    {
        if (idempotencyKey == Guid.Empty)
            throw new ArgumentException("An idempotency key is required.");
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        db.Database.SetCommandTimeout(15);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetActorContextAsync(db, actor, ct);
        var lockIdentity = System.Text.Json.JsonSerializer.Serialize(new[] { actor.Issuer, actor.Subject });
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended({lockIdentity}, 0))", ct);
        var key = idempotencyKey.ToString("D");
        var replay = await db.IdempotencyLedger.SingleOrDefaultAsync(entry => entry.ActorIssuer == actor.Issuer
            && entry.ActorSubject == actor.Subject && entry.OperationFamily == operation && entry.IdempotencyKey == key, ct);
        if (replay is not null && (replay.CanonicalHash != canonicalHash
            || registrationId.HasValue && replay.RegistrationId != registrationId))
            throw new IdentityIdempotencyConflict(key);
        var targetId = registrationId ?? replay?.RegistrationId;
        IdentityRegistrationRecord registration;
        if (targetId.HasValue)
        {
            registration = (await db.Registrations.FromSqlInterpolated($"""
                SELECT * FROM identity.registrations WHERE registration_id = {targetId.Value}
                    AND actor_issuer = {actor.Issuer} COLLATE "C" AND actor_subject = {actor.Subject} COLLATE "C" FOR UPDATE
                """).ToListAsync(ct)).SingleOrDefault()
                ?? throw new IdentityResourceNotFoundException("Registration not found or not accessible.");
            if (registration.ExpiresAt < DateTimeOffset.UtcNow && registration.State != IdentityRegistrationState.Completed)
                throw new IdentityResourceNotFoundException("Registration not found or not accessible.");
        }
        else
        {
            registration = new IdentityRegistrationRecord
            {
                ActorIssuer = actor.Issuer, ActorSubject = actor.Subject,
                AuthenticationPath = IdentityAuthenticationPath.Google, ProviderLabel = "google",
                ProviderIssuer = actor.Issuer, EmailVerified = true, LanguagePreference = languagePreference,
                State = IdentityRegistrationState.FederatedIdentityAccepted,
            };
            db.Registrations.Add(registration);
        }
        if (replay is not null)
        {
            await transaction.CommitAsync(ct);
            return (registration, false);
        }
        if (registrationId.HasValue)
        {
            if (registration.State == IdentityRegistrationState.Completed
                || registration.AuthenticationPath != IdentityAuthenticationPath.Google)
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            registration.DisplayName = displayName;
            registration.BusinessName = businessName;
            registration.BusinessDomain = businessDomain;
            registration.LanguagePreference = languagePreference;
            registration.State = ComputeRegistrationState(registration);
            registration.UpdatedAt = DateTimeOffset.UtcNow;
        }
        db.IdempotencyLedger.Add(new IdentityIdempotencyEntry
        {
            ActorIssuer = actor.Issuer, ActorSubject = actor.Subject, RegistrationId = registration.RegistrationId,
            IdempotencyKey = key, OperationFamily = operation, CanonicalHash = canonicalHash,
            StatusCode = registrationId.HasValue ? 200 : 201, ResponseBody = registration.RegistrationId.ToString("D"),
        });
        await db.SaveChangesAsync(ct);
        await transaction.CommitAsync(ct);
        return (registration, !registrationId.HasValue);
    }

    public async Task<(IdentityRegistrationRecord reg, bool isNew)> StartRegistrationAsync(
        string actorSubject,
        Guid idempotencyKey,
        string canonicalHash,
        string languagePreference,
        IdentityAuthenticationPath authPath,
        string? providerLabel,
        string? providerIssuer,
        bool emailVerifiedByClaim,
        string? maskedEmail,
        string? emailHmacKey,
        CancellationToken ct)
    {
        if (authPath == IdentityAuthenticationPath.WhatsApp)
            throw new IdentityActionDeniedException(
                "WhatsApp registration uses an internal adapter and is not accepted by browser endpoints.");

        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "StartRegistration", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());
        if (replay is not null)
        {
            var replayReg = await db.Registrations.FindAsync([Guid.Parse(replay)], ct);
            return (replayReg!, false);
        }

        var initialState = authPath switch
        {
            IdentityAuthenticationPath.Google => emailVerifiedByClaim
                ? IdentityRegistrationState.FederatedIdentityAccepted
                : IdentityRegistrationState.EmailVerificationRequired,
            IdentityAuthenticationPath.Credential => IdentityRegistrationState.CredentialIdentityAccepted,
            _ => IdentityRegistrationState.Started,
        };

        var reg = new IdentityRegistrationRecord
        {
            ActorSubject       = actorSubject,
            State              = initialState,
            AuthenticationPath = authPath,
            ProviderLabel      = providerLabel,
            ProviderIssuer     = providerIssuer,
            EmailVerified      = emailVerifiedByClaim,
            MaskedEmail        = maskedEmail,
            EmailHmacKey       = emailHmacKey,
            LanguagePreference = languagePreference,
        };

        db.Registrations.Add(reg);
        await db.SaveChangesAsync(ct);
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "StartRegistration",
            canonicalHash, 201, reg.RegistrationId.ToString(), ct);

        return (reg, true);
    }

    public async Task<IdentityRegistrationRecord> GetRegistrationAsync(
        Guid registrationId,
        VerifiedCustomerActor actor,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        db.Database.SetCommandTimeout(15);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        await SetActorContextAsync(db, actor, ct);
        var registration = await db.Registrations.SingleOrDefaultAsync(record =>
            record.RegistrationId == registrationId && record.ActorIssuer == actor.Issuer
            && record.ActorSubject == actor.Subject, ct)
            ?? throw new IdentityResourceNotFoundException("Registration not found or not accessible.");
        await transaction.CommitAsync(ct);
        return registration;
    }

    private static Task SetActorContextAsync(IdentityDbContext db, VerifiedCustomerActor actor, CancellationToken ct) =>
        db.Database.ExecuteSqlInterpolatedAsync($"""
            SELECT pg_catalog.set_config('app.identity_issuer', {actor.Issuer}, true),
                   pg_catalog.set_config('app.identity_subject', {actor.Subject}, true),
                   pg_catalog.set_config('app.tenant_id', '', true),
                   pg_catalog.set_config('app.current_tenant_id', '', true)
            """, ct);

    public async Task<IdentityRegistrationRecord> GetRegistrationAsync(
        Guid registrationId,
        string actorSubject,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var reg = await db.Registrations.FindAsync([registrationId], ct);
        if (reg is null || reg.ActorSubject != actorSubject)
            throw new IdentityResourceNotFoundException("Registration not found or not accessible.");
        return reg;
    }

    public async Task<(IdentityRegistrationRecord reg, bool isNew)> UpdateProfileAsync(
        Guid registrationId,
        string actorSubject,
        Guid idempotencyKey,
        string canonicalHash,
        string displayName,
        string businessName,
        string businessDomain,
        string languagePreference,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var reg = await db.Registrations.FindAsync([registrationId], ct);
        if (reg is null || reg.ActorSubject != actorSubject)
            throw new IdentityResourceNotFoundException("Registration not found or not accessible.");

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "UpdateProfile", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());
        if (replay is not null) return (reg, false);

        reg.DisplayName        = displayName;
        reg.BusinessName       = businessName;
        reg.BusinessDomain     = businessDomain;
        reg.LanguagePreference = languagePreference;
        reg.UpdatedAt          = DateTimeOffset.UtcNow;
        reg.State              = ComputeRegistrationState(reg);
        await db.SaveChangesAsync(ct);
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "UpdateProfile",
            canonicalHash, 200, reg.RegistrationId.ToString(), ct);

        return (reg, false);
    }

    // ── Email Verification ───────────────────────────────────────────────────

    public async Task<(IdentityVerificationChallengeRecord challenge, bool isNew)> StartEmailVerificationAsync(
        Guid registrationId,
        string actorSubject,
        Guid idempotencyKey,
        string canonicalHash,
        string email,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var reg = await db.Registrations.FindAsync([registrationId], ct);
        if (reg is null || reg.ActorSubject != actorSubject)
            throw new IdentityResourceNotFoundException("Registration not found or not accessible.");

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "StartEmailVerification", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());

        if (replay is not null)
        {
            var replayChallenge = await db.VerificationChallenges.FindAsync([Guid.Parse(replay)], ct);
            return (replayChallenge!, false);
        }

        // Generate cryptographically secure 6-digit OTP; raw code must never be persisted or logged
        var rawCode = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
        var codeHmac = ComputeHmac(rawCode);

        var masked = MaskEmail(email);
        var emailHmac = ComputeHmac(email.ToLowerInvariant().Trim());

        var challenge = new IdentityVerificationChallengeRecord
        {
            RegistrationId    = registrationId,
            ActorSubject      = actorSubject,
            Purpose           = IdentityVerificationPurpose.Email,
            CodeHmac          = codeHmac,
            MaskedDestination = masked,
        };

        reg.EmailHmacKey = emailHmac;
        reg.MaskedEmail  = masked;
        reg.UpdatedAt    = DateTimeOffset.UtcNow;

        db.VerificationChallenges.Add(challenge);
        await db.SaveChangesAsync(ct);
        try
        {
            await _dispatcher.DispatchAsync(IdentityVerificationPurpose.Email, email, rawCode, ct);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            challenge.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync(ct);
            throw new IdentityDeliveryUnavailableException("Verification delivery is unavailable.");
        }
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "StartEmailVerification",
            canonicalHash, 202, challenge.ChallengeId.ToString(), ct);

        return (challenge, true);
    }

    public async Task<(IdentityRegistrationRecord reg, bool isNew)> ConfirmEmailVerificationAsync(
        Guid registrationId,
        string actorSubject,
        Guid idempotencyKey,
        string canonicalHash,
        Guid challengeId,
        string code,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var reg = await db.Registrations.FindAsync([registrationId], ct);
        if (reg is null || reg.ActorSubject != actorSubject)
            throw new IdentityResourceNotFoundException("Registration not found or not accessible.");

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "ConfirmEmailVerification", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());
        if (replay is not null) return (reg, false);

        var challenge = await db.VerificationChallenges.FindAsync([challengeId], ct);
        if (challenge is null
            || challenge.ActorSubject != actorSubject
            || challenge.RegistrationId != registrationId
            || challenge.Purpose != IdentityVerificationPurpose.Email)
            throw new IdentityResourceNotFoundException("Challenge not found or not accessible.");

        if (challenge.State != IdentityVerificationState.Pending)
            throw new IdentityChallengeExpiredException("Challenge is no longer usable.");

        if (challenge.ExpiresAt < DateTimeOffset.UtcNow)
        {
            challenge.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync(ct);
            throw new IdentityChallengeExpiredException("Challenge has expired.");
        }

        // Constant-time HMAC comparison; wrong code returns privacy-safe denial without consuming
        if (!VerifyCode(code, challenge.CodeHmac))
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");

        challenge.State      = IdentityVerificationState.Consumed;
        challenge.VerifiedAt = DateTimeOffset.UtcNow;
        reg.EmailVerified    = true;
        reg.UpdatedAt        = DateTimeOffset.UtcNow;
        reg.State            = ComputeRegistrationState(reg);
        await db.SaveChangesAsync(ct);
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "ConfirmEmailVerification",
            canonicalHash, 200, reg.RegistrationId.ToString(), ct);

        return (reg, false);
    }

    // ── Mobile Verification ──────────────────────────────────────────────────

    public async Task<(IdentityVerificationChallengeRecord challenge, bool isNew)> StartMobileVerificationAsync(
        Guid? registrationId,
        string actorSubject,
        Guid idempotencyKey,
        string canonicalHash,
        string mobile,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        IdentityRegistrationRecord? reg = null;
        if (registrationId.HasValue)
        {
            reg = await db.Registrations.FindAsync([registrationId.Value], ct);
            if (reg is null || reg.ActorSubject != actorSubject)
                throw new IdentityResourceNotFoundException("Registration not found or not accessible.");
        }

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "StartMobileVerification", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());
        if (replay is not null)
        {
            var replayChallenge = await db.VerificationChallenges.FindAsync([Guid.Parse(replay)], ct);
            return (replayChallenge!, false);
        }

        // Generate cryptographically secure 6-digit OTP; raw code must never be persisted
        var rawCode = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
        var codeHmac = ComputeHmac(rawCode);
        var masked = MaskMobile(mobile);

        // Store normalized HMAC key and masked mobile on registration; never raw mobile
        if (reg is not null)
        {
            reg.MobileHmacKey = ComputeHmac(mobile.Trim());
            reg.MaskedMobile  = masked;
            reg.UpdatedAt     = DateTimeOffset.UtcNow;
        }

        var challenge = new IdentityVerificationChallengeRecord
        {
            RegistrationId    = registrationId,
            ActorSubject      = actorSubject,
            Purpose           = IdentityVerificationPurpose.Mobile,
            CodeHmac          = codeHmac,
            MaskedDestination = masked,
        };

        db.VerificationChallenges.Add(challenge);
        await db.SaveChangesAsync(ct);
        try
        {
            await _dispatcher.DispatchAsync(IdentityVerificationPurpose.Mobile, mobile, rawCode, ct);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            challenge.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync(ct);
            throw new IdentityDeliveryUnavailableException("Verification delivery is unavailable.");
        }
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "StartMobileVerification",
            canonicalHash, 202, challenge.ChallengeId.ToString(), ct);

        return (challenge, true);
    }

    public async Task<(object result, bool isNew)> ConfirmMobileVerificationAsync(
        Guid? registrationId,
        string actorSubject,
        Guid idempotencyKey,
        string canonicalHash,
        Guid challengeId,
        string code,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "ConfirmMobileVerification", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());

        // Replay returns original outcome before any state validation
        if (replay is not null)
        {
            if (registrationId.HasValue)
            {
                var replayReg = await db.Registrations.FindAsync([registrationId.Value], ct);
                return (replayReg!, false);
            }
            var replayCh = await db.VerificationChallenges.FindAsync([challengeId], ct);
            return (new IdentityMobileStatusResult(
                true,
                replayCh?.MaskedDestination ?? "***",
                replayCh?.VerifiedAt ?? DateTimeOffset.UtcNow), false);
        }

        var challenge = await db.VerificationChallenges.FindAsync([challengeId], ct);
        if (challenge is null
            || challenge.ActorSubject != actorSubject
            || challenge.Purpose != IdentityVerificationPurpose.Mobile)
            throw new IdentityResourceNotFoundException("Challenge not found or not accessible.");

        // Challenge must belong to this registration
        if (registrationId.HasValue && challenge.RegistrationId != registrationId.Value)
            throw new IdentityResourceNotFoundException("Challenge does not belong to this registration.");

        if (challenge.State != IdentityVerificationState.Pending)
            throw new IdentityChallengeExpiredException("Challenge is no longer usable.");

        if (challenge.ExpiresAt < DateTimeOffset.UtcNow)
        {
            challenge.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync(ct);
            throw new IdentityChallengeExpiredException("Challenge has expired.");
        }

        // Constant-time HMAC comparison; wrong code returns privacy-safe denial without consuming
        if (!VerifyCode(code, challenge.CodeHmac))
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");

        var verifiedAt = DateTimeOffset.UtcNow;
        challenge.State      = IdentityVerificationState.Consumed;
        challenge.VerifiedAt = verifiedAt;

        if (registrationId.HasValue)
        {
            var reg = await db.Registrations.FindAsync([registrationId.Value], ct);
            if (reg is not null && reg.ActorSubject == actorSubject)
            {
                reg.MobileVerified = true;
                reg.MaskedMobile   = challenge.MaskedDestination;
                reg.UpdatedAt      = DateTimeOffset.UtcNow;
                reg.State          = ComputeRegistrationState(reg);
            }
            await db.SaveChangesAsync(ct);
            await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "ConfirmMobileVerification",
                canonicalHash, 200, reg!.RegistrationId.ToString(), ct);
            return (reg!, false);
        }

        await db.SaveChangesAsync(ct);
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "ConfirmMobileVerification",
            canonicalHash, 200, $"mobile:{challenge.MaskedDestination}", ct);

        return (new IdentityMobileStatusResult(true, challenge.MaskedDestination, verifiedAt), true);
    }

    // ── Registration Completion ──────────────────────────────────────────────

    public async Task<(IdentityCompletionResult result, bool isNew)> CompleteRegistrationAsync(
        Guid registrationId,
        string actorSubject,
        Guid idempotencyKey,
        string canonicalHash,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var reg = await db.Registrations.FindAsync([registrationId], ct);
        if (reg is null || reg.ActorSubject != actorSubject)
            throw new IdentityResourceNotFoundException("Registration not found or not accessible.");

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "CompleteRegistration", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());

        if (replay is not null)
        {
            var parts = replay.Split(':');
            return (new IdentityCompletionResult(
                parts[0], Guid.Parse(parts[1]), "AAL2_ACCOUNT", "APPLICATION_HOME"), false);
        }

        // Completion requires confirmed email
        if (!reg.EmailVerified)
            throw new IdentityVerificationRequiredException(
                "Email verification must be completed before registration can be finalized.");

        // Require minimum profile fields
        if (string.IsNullOrWhiteSpace(reg.DisplayName)
            || string.IsNullOrWhiteSpace(reg.BusinessName)
            || string.IsNullOrWhiteSpace(reg.BusinessDomain))
            throw new IdentityVerificationRequiredException(
                "Minimum profile fields are required before registration can be finalized.");

        var isNew = reg.State != IdentityRegistrationState.Completed;
        var accountId = reg.AccountId ?? Guid.NewGuid();
        var outcome = (reg.AccountId is null) ? "ACCOUNT_CREATED" : "ACCOUNT_REUSED";

        reg.AccountId   = accountId;
        reg.State       = IdentityRegistrationState.Completed;
        reg.UpdatedAt   = DateTimeOffset.UtcNow;

        var result = new IdentityCompletionResult(outcome, accountId, "AAL2_ACCOUNT", "APPLICATION_HOME");
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "CompleteRegistration",
            canonicalHash, 200, $"{outcome}:{accountId}", ct);

        return (result, isNew);
    }

    public async Task<IdentitySessionState> GetSessionStateAsync(
        string actorSubject,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var registration = await db.Registrations
            .Where(value => value.ActorSubject == actorSubject
                && value.State == IdentityRegistrationState.Completed
                && value.AccountId != null)
            .OrderByDescending(value => value.UpdatedAt)
            .FirstOrDefaultAsync(ct);

        if (registration?.AccountId is null)
            throw new IdentityResourceNotFoundException("Completed account session not found.");

        var progressiveMobileVerified = await db.VerificationChallenges.AnyAsync(
            value => value.ActorSubject == actorSubject
                && value.Purpose == IdentityVerificationPurpose.Mobile
                && value.VerifiedAt != null,
            ct);

        return new IdentitySessionState(
            registration.AccountId.Value,
            registration.EmailVerified,
            registration.MobileVerified || progressiveMobileVerified);
    }

    public async Task<CustomerPortalProfileState> GetCustomerProfileAsync(
        string actorSubject,
        Guid tenantId,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var registration = await GetCompletedRegistrationAsync(db, actorSubject, ct);
        var preference = await db.CustomerPortalPreferences.SingleOrDefaultAsync(
            value => value.ActorSubject == actorSubject && value.TenantId == tenantId, ct);

        return new CustomerPortalProfileState(
            registration.AccountId!.Value,
            preference?.DisplayName ?? registration.DisplayName!,
            preference?.OrganizationDisplayName ?? registration.BusinessName!,
            registration.EmailVerified,
            registration.MobileVerified || await HasVerifiedMobileAsync(db, actorSubject, ct),
            preference?.UpdatedAt ?? registration.UpdatedAt);
    }

    public async Task<CustomerPortalProfileState> UpdateCustomerProfileAsync(
        string actorSubject,
        Guid tenantId,
        Guid idempotencyKey,
        string canonicalHash,
        string displayName,
        string organizationDisplayName,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var registration = await GetCompletedRegistrationAsync(db, actorSubject, ct);
        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, $"UpdateCustomerProfile:{tenantId}", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());

        var preference = await GetOrCreatePortalPreferenceAsync(db, actorSubject, tenantId, ct);
        if (replay is null)
        {
            preference.DisplayName = displayName;
            preference.OrganizationDisplayName = organizationDisplayName;
            preference.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(ct);
            await RecordIdempotencyAsync(db, actorSubject, idempotencyKey,
                $"UpdateCustomerProfile:{tenantId}", canonicalHash, 200, preference.PreferenceId.ToString(), ct);
        }

        return new CustomerPortalProfileState(
            registration.AccountId!.Value,
            preference.DisplayName ?? registration.DisplayName!,
            preference.OrganizationDisplayName ?? registration.BusinessName!,
            registration.EmailVerified,
            registration.MobileVerified || await HasVerifiedMobileAsync(db, actorSubject, ct),
            preference.UpdatedAt);
    }

    public async Task<CustomerPortalSettingsState> GetCustomerSettingsAsync(
        string actorSubject,
        Guid tenantId,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        var registration = await GetCompletedRegistrationAsync(db, actorSubject, ct);
        var preference = await db.CustomerPortalPreferences.SingleOrDefaultAsync(
            value => value.ActorSubject == actorSubject && value.TenantId == tenantId, ct);
        return ToSettings(preference, registration.LanguagePreference ?? "en", registration.UpdatedAt);
    }

    public async Task<CustomerPortalSettingsState> UpdateCustomerSettingsAsync(
        string actorSubject,
        Guid tenantId,
        Guid idempotencyKey,
        string canonicalHash,
        string locale,
        string theme,
        string timestampVisibility,
        IReadOnlyList<string> approvalRequests,
        IReadOnlyList<string> maturityReports,
        IReadOnlyList<string> monthlyNarratives,
        IReadOnlyList<string> selfGovernanceAlerts,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        await GetCompletedRegistrationAsync(db, actorSubject, ct);
        var operation = $"UpdateCustomerSettings:{tenantId}";
        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, operation, canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());

        var preference = await GetOrCreatePortalPreferenceAsync(db, actorSubject, tenantId, ct);
        if (replay is null)
        {
            preference.Locale = locale;
            preference.Theme = theme;
            preference.TimestampVisibility = timestampVisibility;
            preference.ApprovalRequestChannels = SerializeChannels(approvalRequests);
            preference.MaturityReportChannels = SerializeChannels(maturityReports);
            preference.MonthlyNarrativeChannels = SerializeChannels(monthlyNarratives);
            preference.SelfGovernanceAlertChannels = SerializeChannels(selfGovernanceAlerts);
            preference.UpdatedAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync(ct);
            await RecordIdempotencyAsync(db, actorSubject, idempotencyKey,
                operation, canonicalHash, 200, preference.PreferenceId.ToString(), ct);
        }
        return ToSettings(preference, locale, preference.UpdatedAt);
    }

    private static async Task<IdentityRegistrationRecord> GetCompletedRegistrationAsync(
        IdentityDbContext db, string actorSubject, CancellationToken ct)
    {
        var registration = await db.Registrations
            .Where(value => value.ActorSubject == actorSubject
                && value.State == IdentityRegistrationState.Completed
                && value.AccountId != null)
            .OrderByDescending(value => value.UpdatedAt)
            .FirstOrDefaultAsync(ct);
        return registration ?? throw new IdentityResourceNotFoundException("Completed account not found.");
    }

    private static Task<bool> HasVerifiedMobileAsync(
        IdentityDbContext db, string actorSubject, CancellationToken ct) =>
        db.VerificationChallenges.AnyAsync(value => value.ActorSubject == actorSubject
            && value.Purpose == IdentityVerificationPurpose.Mobile
            && value.VerifiedAt != null, ct);

    private static async Task<CustomerPortalPreferenceRecord> GetOrCreatePortalPreferenceAsync(
        IdentityDbContext db, string actorSubject, Guid tenantId, CancellationToken ct)
    {
        var preference = await db.CustomerPortalPreferences.SingleOrDefaultAsync(
            value => value.ActorSubject == actorSubject && value.TenantId == tenantId, ct);
        if (preference is not null) return preference;
        preference = new CustomerPortalPreferenceRecord { ActorSubject = actorSubject, TenantId = tenantId };
        db.CustomerPortalPreferences.Add(preference);
        return preference;
    }

    private static string SerializeChannels(IReadOnlyList<string> channels) =>
        System.Text.Json.JsonSerializer.Serialize(channels);

    private static IReadOnlyList<string> DeserializeChannels(string channels) =>
        System.Text.Json.JsonSerializer.Deserialize<string[]>(channels) ?? [];

    private static CustomerPortalSettingsState ToSettings(
        CustomerPortalPreferenceRecord? preference, string defaultLocale, DateTimeOffset defaultUpdatedAt) =>
        new(
            preference?.Locale ?? defaultLocale,
            preference?.Theme ?? "SYSTEM",
            preference?.TimestampVisibility ?? "RELATIVE",
            DeserializeChannels(preference?.ApprovalRequestChannels ?? "[\"IN_APP\"]"),
            DeserializeChannels(preference?.MaturityReportChannels ?? "[\"IN_APP\"]"),
            DeserializeChannels(preference?.MonthlyNarrativeChannels ?? "[\"IN_APP\"]"),
            DeserializeChannels(preference?.SelfGovernanceAlertChannels ?? "[\"IN_APP\"]"),
            preference?.UpdatedAt ?? defaultUpdatedAt);

    // ── Account Links (WhatsApp-to-web) ──────────────────────────────────────

    public async Task<(IdentityAccountLinkRecord link, bool isNew)> StartAccountLinkAsync(
        string actorSubject,
        Guid tenantId,
        Guid idempotencyKey,
        string canonicalHash,
        Guid verifiedMobileProofId,
        DateTimeOffset authTime,
        CancellationToken ct)
    {
        EnforceAal3Fresh(authTime);

        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "StartAccountLink", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());
        if (replay is not null)
        {
            var replayLink = await db.AccountLinks.FindAsync([Guid.Parse(replay)], ct);
            return (replayLink!, false);
        }

        var link = new IdentityAccountLinkRecord
        {
            ActorSubject          = actorSubject,
            TenantId              = tenantId,
            MaskedMobile          = "***",
            VerifiedMobileProofId = verifiedMobileProofId,
        };

        db.AccountLinks.Add(link);
        await db.SaveChangesAsync(ct);
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "StartAccountLink",
            canonicalHash, 201, link.LinkId.ToString(), ct);

        return (link, true);
    }

    public async Task<(IdentityAccountLinkRecord link, bool isNew)> ApproveAccountLinkAsync(
        Guid linkId,
        string actorSubject,
        Guid tenantId,
        Guid idempotencyKey,
        string canonicalHash,
        DateTimeOffset authTime,
        CancellationToken ct)
    {
        EnforceAal3Fresh(authTime);

        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var link = await db.AccountLinks.FindAsync([linkId], ct);
        if (link is null || link.ActorSubject != actorSubject || link.TenantId != tenantId)
            throw new IdentityResourceNotFoundException("Link not found or not accessible.");

        var (replay, conflict) = await CheckIdempotencyAsync(
            db, actorSubject, idempotencyKey, "ApproveAccountLink", canonicalHash, ct);
        if (conflict) throw new IdentityIdempotencyConflict(idempotencyKey.ToString());
        if (replay is not null) return (link, false);

        if (link.State == IdentityAccountLinkState.Expired
            || link.ExpiresAt < DateTimeOffset.UtcNow)
        {
            link.State = IdentityAccountLinkState.Expired;
            await db.SaveChangesAsync(ct);
            throw new IdentityChallengeExpiredException("Link challenge has expired.");
        }

        link.State     = IdentityAccountLinkState.PendingWhatsAppConfirmation;
        link.UpdatedAt = DateTimeOffset.UtcNow;
        await db.SaveChangesAsync(ct);
        await RecordIdempotencyAsync(db, actorSubject, idempotencyKey, "ApproveAccountLink",
            canonicalHash, 200, link.LinkId.ToString(), ct);

        return (link, false);
    }

    public async Task<IdentityAccountLinkRecord> GetAccountLinkAsync(
        Guid linkId,
        string actorSubject,
        Guid tenantId,
        CancellationToken ct)
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);

        var link = await db.AccountLinks.FindAsync([linkId], ct);
        if (link is null || link.ActorSubject != actorSubject || link.TenantId != tenantId)
            throw new IdentityResourceNotFoundException("Link not found or not accessible.");

        return link;
    }

    // ── Helpers ──────────────────────────────────────────────────────────────

    private static void EnforceAal3Fresh(DateTimeOffset authTime)
    {
        if ((DateTimeOffset.UtcNow - authTime).TotalMinutes > Aal3FreshWindowMinutes)
            throw new IdentityStepUpRequiredException(
                "A freshly authenticated session is required for this action.",
                Guid.NewGuid());
    }

    private static IdentityRegistrationState ComputeRegistrationState(IdentityRegistrationRecord reg)
    {
        if (reg.State == IdentityRegistrationState.Completed) return reg.State;
        if (!reg.EmailVerified) return IdentityRegistrationState.EmailVerificationRequired;

        var hasMinProfile = !string.IsNullOrWhiteSpace(reg.DisplayName)
            && !string.IsNullOrWhiteSpace(reg.BusinessName)
            && !string.IsNullOrWhiteSpace(reg.BusinessDomain);
        if (!hasMinProfile) return IdentityRegistrationState.ProfileCompletionRequired;

        return IdentityRegistrationState.ReadyToComplete;
    }

    public static string MaskEmail(string email)
    {
        var at = email.IndexOf('@');
        if (at <= 1) return "***@***";
        return $"{email[0]}***{email[at..]}";
    }

    public static string MaskMobile(string mobile)
    {
        if (mobile.Length < 5) return "***";
        return mobile[..^4].Replace(mobile[1..^4], "***") + mobile[^4..];
    }

    private byte[] ComputeHmacBytes(string value)
    {
        var data = Encoding.UTF8.GetBytes(value.ToLowerInvariant().Trim());
        using var hmac = new HMACSHA256(Encoding.UTF8.GetBytes(_hmacKey));
        return hmac.ComputeHash(data)[..16];
    }

    private string ComputeHmac(string value) =>
        Convert.ToHexString(ComputeHmacBytes(value)).ToLowerInvariant();

    private bool VerifyCode(string submittedCode, string storedHex)
    {
        var submitted = ComputeHmacBytes(submittedCode);
        byte[] stored;
        try { stored = Convert.FromHexString(storedHex); }
        catch (FormatException) { return false; }
        return stored.Length == submitted.Length
            && CryptographicOperations.FixedTimeEquals(submitted, stored);
    }

    private static async Task<(string? replayRef, bool conflict)> CheckIdempotencyAsync(
        IdentityDbContext db,
        string actorSubject,
        Guid idempotencyKey,
        string operationFamily,
        string canonicalHash,
        CancellationToken ct)
    {
        var key = idempotencyKey.ToString();
        var existing = await db.IdempotencyLedger
            .FirstOrDefaultAsync(e => e.ActorSubject == actorSubject
                && e.IdempotencyKey == key
                && e.OperationFamily == operationFamily, ct);

        if (existing is null) return (null, false);
        if (existing.CanonicalHash != canonicalHash) return (null, true);   // conflict
        return (existing.ResponseBody, false);                               // replay
    }

    private static async Task RecordIdempotencyAsync(
        IdentityDbContext db,
        string actorSubject,
        Guid idempotencyKey,
        string operationFamily,
        string canonicalHash,
        int statusCode,
        string? responseRef,
        CancellationToken ct)
    {
        db.IdempotencyLedger.Add(new IdentityIdempotencyEntry
        {
            ActorSubject    = actorSubject,
            IdempotencyKey  = idempotencyKey.ToString(),
            OperationFamily = operationFamily,
            CanonicalHash   = canonicalHash,
            StatusCode      = statusCode,
            ResponseBody    = responseRef,
        });
        await db.SaveChangesAsync(ct);
    }
}
