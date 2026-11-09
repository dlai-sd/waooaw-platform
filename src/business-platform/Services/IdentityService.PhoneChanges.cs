// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md §8
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record IdentityPhoneChangeResult(
    Guid ChallengeId,
    string State,
    string MaskedMobile,
    DateTimeOffset ExpiresAt,
    bool RelationshipApprovalRequired = true
);

public sealed partial class IdentityService
{
    public async Task<IdentityPhoneChangeResult> StartPhoneChangeAsync(
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        string mobile,
        Guid key,
        DateTimeOffset authTime,
        CancellationToken ct
    )
    {
        RequirePhoneChangeInput(key, authTime);
        if (!Regex.IsMatch(mobile, "\\A\\+[1-9][0-9]{7,14}\\z", RegexOptions.CultureInvariant))
            throw new ArgumentException("Replacement number must be E.164.", nameof(mobile));
        var candidates = ComputeMatchCandidates("mobile", mobile);
        var requestHash = Convert.ToHexString(
            SHA256.HashData(
                Encoding.UTF8.GetBytes(
                    JsonSerializer.Serialize(
                        new
                        {
                            mobile,
                            membership.AccountId,
                            membership.TenantId,
                        }
                    )
                )
            )
        );
        Guid registrationId;
        string previousKey;
        string previousVersion;
        await using (var initial = await _dbFactory.CreateDbContextAsync(ct))
        {
            await using var transaction = await BeginPhoneChangeContextAsync(
                initial,
                actor,
                membership,
                ct
            );
            var registration = await GetPortalRegistrationAsync(
                initial,
                actor.Issuer,
                actor.Subject,
                membership,
                ct
            );
            var (replay, conflict) = await CheckIdempotencyAsync(
                initial,
                actor.Subject,
                key,
                "StartPhoneChange",
                requestHash,
                ct,
                actor.Issuer
            );
            if (conflict)
                throw new IdentityIdempotencyConflict(key.ToString());
            if (replay is not null)
            {
                var prior = await RequirePhoneChangeAsync(
                    initial,
                    Guid.Parse(replay),
                    actor,
                    membership,
                    ct
                );
                var challenge = await initial.VerificationChallenges.SingleAsync(
                    v => v.ChallengeId == prior.ChallengeId,
                    ct
                );
                if (challenge.DeliveryState != "SUBMITTED")
                    throw new IdentityDeliveryUnavailableException(
                        "Phone-change verification delivery is unresolved."
                    );
                return PhoneChangeResult(challenge, prior);
            }
            registrationId = registration.RegistrationId;
            previousKey =
                registration.MobileHmacKey
                ?? throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            previousVersion =
                registration.MobileHmacVersion
                ?? throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            if (candidates.TryGetValue(previousVersion, out var same) && same == previousKey)
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            await RequirePhoneAvailableAsync(initial, membership.AccountId, candidates, ct);
            await RequirePhoneChangeRateAsync(initial, registrationId, ct);
        }
        var evidence = await RequireConstitutionalEvidenceAsync(
            membership.TenantId,
            key,
            "IDENTITY_PHONE_CHANGE_START",
            new { registrationId, requestHash },
            ct
        );
        if (evidence == Guid.Empty)
            throw new IdentityDeliveryUnavailableException("Phone-change evidence is unavailable.");
        var rawCode = RandomNumberGenerator.GetInt32(0, 1_000_000).ToString("D6");
        var now = _clock.GetUtcNow();
        var challengeRecord = new IdentityVerificationChallengeRecord
        {
            RegistrationId = registrationId,
            ActorSubject = actor.Subject,
            Purpose = IdentityVerificationPurpose.Mobile,
            CodeHmac = ComputeHmac("otp", rawCode, _activeHmacVersion),
            CodeHmacVersion = _activeHmacVersion,
            DestinationHmacKey = candidates[_activeHmacVersion],
            DestinationHmacVersion = _activeHmacVersion,
            DestinationHmacDomain = "mobile",
            MaskedDestination = MaskMobile(mobile),
            DeliveryState = "DISPATCHING",
            CreatedAt = now,
            ExpiresAt = now.AddMinutes(5),
            ResendAfter = now.AddMinutes(1),
        };
        await using (var db = await _dbFactory.CreateDbContextAsync(ct))
        {
            await using var transaction = await BeginPhoneChangeContextAsync(
                db,
                actor,
                membership,
                ct
            );
            RequirePhoneChangeInput(key, authTime);
            var registration = await GetPortalRegistrationAsync(
                db,
                actor.Issuer,
                actor.Subject,
                membership,
                ct
            );
            if (
                registration.RegistrationId != registrationId
                || registration.MobileHmacKey != previousKey
                || registration.MobileHmacVersion != previousVersion
            )
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            var (replay, conflict) = await CheckIdempotencyAsync(
                db,
                actor.Subject,
                key,
                "StartPhoneChange",
                requestHash,
                ct,
                actor.Issuer
            );
            if (conflict || replay is not null)
                throw new IdentityIdempotencyConflict(key.ToString());
            await RequirePhoneAvailableAsync(db, membership.AccountId, candidates, ct);
            await RequirePhoneChangeRateAsync(db, registrationId, ct);
            db.VerificationChallenges.Add(challengeRecord);
            db.PhoneChanges.Add(
                new IdentityPhoneChangeRecord
                {
                    ChallengeId = challengeRecord.ChallengeId,
                    RegistrationId = registrationId,
                    ActorIssuer = actor.Issuer,
                    ActorSubject = actor.Subject,
                    AccountId = membership.AccountId,
                    TenantId = membership.TenantId,
                    MembershipId = membership.MembershipId,
                    PreviousMobileKey = previousKey,
                    PreviousMobileVersion = previousVersion,
                    DestinationCandidates = JsonSerializer.Serialize(candidates),
                    StartEvidenceId = evidence,
                    CreatedAt = now,
                }
            );
            await db.SaveChangesAsync(ct);
            await RecordIdempotencyAsync(
                db,
                actor.Subject,
                key,
                "StartPhoneChange",
                requestHash,
                202,
                challengeRecord.ChallengeId.ToString("D"),
                ct,
                actor.Issuer
            );
            RequirePhoneChangeInput(key, authTime);
            if (challengeRecord.ExpiresAt <= _clock.GetUtcNow())
                throw new IdentityChallengeExpiredException(
                    "Phone-change challenge expired before dispatch."
                );
            if (transaction is not null)
                await transaction.CommitAsync(ct);
        }
        try
        {
            await _dispatcher.DispatchRegistrationMobileAsync(
                registrationId,
                challengeRecord.ChallengeId,
                challengeRecord.ExpiresAt,
                mobile,
                rawCode,
                ct
            );
        }
        catch (IdentityDeliveryUnavailableException)
        {
            await SavePhoneChangeDeliveryAsync(
                actor,
                membership,
                challengeRecord.ChallengeId,
                "UNAVAILABLE",
                ct
            );
            throw;
        }
        return await SavePhoneChangeDeliveryAsync(
            actor,
            membership,
            challengeRecord.ChallengeId,
            "SUBMITTED",
            ct
        );
    }

    public async Task<IdentityPhoneChangeResult> ConfirmPhoneChangeAsync(
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        Guid challengeId,
        string code,
        bool consent,
        Guid key,
        DateTimeOffset authTime,
        CancellationToken ct
    )
    {
        RequirePhoneChangeInput(key, authTime);
        if (
            !consent
            || challengeId == Guid.Empty
            || !Regex.IsMatch(code, "\\A[0-9]{6}\\z", RegexOptions.CultureInvariant)
        )
            throw new ArgumentException(
                "Phone-change confirmation requires a challenge, six-digit code and consent."
            );
        string requestHash;
        string destinationKey;
        string destinationVersion;
        await using (var initial = await _dbFactory.CreateDbContextAsync(ct))
        {
            await using var transaction = await BeginPhoneChangeContextAsync(
                initial,
                actor,
                membership,
                ct
            );
            var change = await RequirePhoneChangeAsync(initial, challengeId, actor, membership, ct);
            var challenge = await initial.VerificationChallenges.SingleAsync(
                v => v.ChallengeId == challengeId,
                ct
            );
            requestHash = Convert.ToHexString(
                SHA256.HashData(
                    Encoding.UTF8.GetBytes(
                        JsonSerializer.Serialize(
                            new
                            {
                                challengeId,
                                consent,
                                code = ComputeHmac("otp", code, challenge.CodeHmacVersion),
                            }
                        )
                    )
                )
            );
            var (replay, conflict) = await CheckIdempotencyAsync(
                initial,
                actor.Subject,
                key,
                "ConfirmPhoneChange",
                requestHash,
                ct,
                actor.Issuer
            );
            if (conflict)
                throw new IdentityIdempotencyConflict(key.ToString());
            if (replay == MobileVerificationDeniedReplay)
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            if (change.CompletedAt is not null)
            {
                if (replay is null)
                    await RecordIdempotencyAsync(
                        initial,
                        actor.Subject,
                        key,
                        "ConfirmPhoneChange",
                        requestHash,
                        200,
                        challengeId.ToString("D"),
                        ct,
                        actor.Issuer
                    );
                RequirePhoneChangeInput(key, authTime);
                if (transaction is not null)
                    await transaction.CommitAsync(ct);
                return PhoneChangeResult(challenge, change);
            }
            RequireUsablePhoneChange(challenge);
            if (!VerifyCode(code, challenge.CodeHmac, challenge.CodeHmacVersion))
            {
                challenge.FailedAttempts++;
                if (challenge.FailedAttempts >= MaximumMobileVerificationAttempts)
                    challenge.State = IdentityVerificationState.Expired;
                await initial.SaveChangesAsync(ct);
                await RecordIdempotencyAsync(
                    initial,
                    actor.Subject,
                    key,
                    "ConfirmPhoneChange",
                    requestHash,
                    403,
                    MobileVerificationDeniedReplay,
                    ct,
                    actor.Issuer
                );
                if (transaction is not null)
                    await transaction.CommitAsync(ct);
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            }
            destinationKey = challenge.DestinationHmacKey!;
            destinationVersion = challenge.DestinationHmacVersion!;
        }
        var evidence = await RequireConstitutionalEvidenceAsync(
            membership.TenantId,
            key,
            "IDENTITY_PHONE_CHANGE_CONFIRM",
            new { challengeId, consentVersion = "WC134-PHONE-CHANGE-1" },
            ct
        );
        if (evidence == Guid.Empty)
            throw new IdentityDeliveryUnavailableException("Phone-change evidence is unavailable.");
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        await using var commit = await BeginPhoneChangeContextAsync(db, actor, membership, ct);
        var (committedReplay, committedConflict) = await CheckIdempotencyAsync(
            db,
            actor.Subject,
            key,
            "ConfirmPhoneChange",
            requestHash,
            ct,
            actor.Issuer
        );
        if (committedConflict)
            throw new IdentityIdempotencyConflict(key.ToString());
        if (committedReplay == MobileVerificationDeniedReplay)
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        RequirePhoneChangeInput(key, authTime);
        var currentChange = await RequirePhoneChangeAsync(db, challengeId, actor, membership, ct);
        var currentChallenge = await db.VerificationChallenges.SingleAsync(
            v => v.ChallengeId == challengeId,
            ct
        );
        if (currentChange.CompletedAt is not null)
        {
            if (committedReplay is null)
                await RecordIdempotencyAsync(
                    db,
                    actor.Subject,
                    key,
                    "ConfirmPhoneChange",
                    requestHash,
                    200,
                    challengeId.ToString("D"),
                    ct,
                    actor.Issuer
                );
            if (commit is not null)
            {
                RequirePhoneChangeInput(key, authTime);
                await commit.CommitAsync(ct);
            }
            return PhoneChangeResult(currentChallenge, currentChange);
        }
        RequireUsablePhoneChange(currentChallenge);
        var registrationNow = await GetPortalRegistrationAsync(
            db,
            actor.Issuer,
            actor.Subject,
            membership,
            ct
        );
        if (
            registrationNow.RegistrationId != currentChange.RegistrationId
            || registrationNow.MobileHmacKey != currentChange.PreviousMobileKey
            || registrationNow.MobileHmacVersion != currentChange.PreviousMobileVersion
            || currentChallenge.DestinationHmacKey != destinationKey
            || currentChallenge.DestinationHmacVersion != destinationVersion
        )
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        var candidates =
            JsonSerializer.Deserialize<Dictionary<string, string>>(
                currentChange.DestinationCandidates
            )
            ?? throw new InvalidOperationException("Phone-change destination binding is invalid.");
        await RequirePhoneAvailableAsync(db, membership.AccountId, candidates, ct);
        if (!db.Database.IsNpgsql() || commit is null)
            throw new IdentityActionDeniedException(
                "Phone replacement requires the atomic PostgreSQL owner transaction."
            );
        await using var relationships = new EmploymentRelationshipDbContext(
            new DbContextOptionsBuilder<EmploymentRelationshipDbContext>()
                .UseNpgsql(db.Database.GetDbConnection())
                .Options
        );
        await relationships.Database.UseTransactionAsync(commit.GetDbTransaction(), ct);
        var now = _clock.GetUtcNow();
        var ownedTenants = await db
            .Memberships.Where(v => v.AccountId == membership.AccountId)
            .Select(v => v.TenantId)
            .Distinct()
            .OrderBy(v => v)
            .ToListAsync(ct);
        foreach (var tenant in ownedTenants)
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT set_config('app.current_tenant_id', {tenant.ToString("D")}, true)",
                ct
            );
            var links = await db
                .AccountLinks.Where(v =>
                    v.TenantId == tenant
                    && (
                        v.ActorSubject == actor.Subject
                        || v.ActorSubject == actor.Issuer + "\u001f" + actor.Subject
                    )
                    && v.State != IdentityAccountLinkState.Cancelled
                    && v.State != IdentityAccountLinkState.Expired
                )
                .ToListAsync(ct);
            foreach (var link in links)
            {
                link.State = IdentityAccountLinkState.Cancelled;
                link.CancellationEvidenceId = evidence;
                link.UpdatedAt = now;
            }
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                SELECT relationship_id FROM business.employment_relationships
                WHERE tenant_id = {tenant} AND relationship_id IN
                    (SELECT relationship_id FROM business.channel_bindings WHERE tenant_id = {tenant}
                        AND participant_id = {Guid.Parse(
                    actor.Subject
                )} AND channel = 'WHATSAPP' AND status IN ('ACTIVE', 'PREPARED'))
                ORDER BY relationship_id FOR SHARE
                """,
                ct
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                SELECT binding_id FROM business.relationship_participants WHERE tenant_id = {tenant}
                    AND participant_id = {Guid.Parse(actor.Subject)} ORDER BY binding_id FOR SHARE
                """,
                ct
            );
            var bindings = await relationships
                .ChannelBindings.Where(v =>
                    v.TenantId == tenant
                    && v.ParticipantId == Guid.Parse(actor.Subject)
                    && v.Channel == "WHATSAPP"
                    && (v.Status == "ACTIVE" || v.Status == "PREPARED")
                )
                .OrderBy(v => v.BindingId)
                .ToListAsync(ct);
            foreach (var binding in bindings)
            {
                await db.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT binding_id FROM business.channel_bindings WHERE binding_id = {binding.BindingId} FOR UPDATE",
                    ct
                );
                await relationships.Entry(binding).ReloadAsync(ct);
                if (binding.Status != "ACTIVE" && binding.Status != "PREPARED")
                    continue;
                binding.Status = "REVOKED";
                binding.RevokedAt = now;
                binding.RevokedEvidenceId = evidence;
            }
            await relationships.SaveChangesAsync(ct);
            var otherChallenges = await db
                .PhoneChanges.Where(v =>
                    v.ActorIssuer == actor.Issuer
                    && v.ActorSubject == actor.Subject
                    && v.AccountId == membership.AccountId
                    && v.TenantId == tenant
                    && v.ChallengeId != challengeId
                    && v.CompletedAt == null
                )
                .Select(v => v.ChallengeId)
                .ToListAsync(ct);
            var superseded = await db
                .VerificationChallenges.Where(v =>
                    otherChallenges.Contains(v.ChallengeId)
                    && v.State == IdentityVerificationState.Pending
                )
                .ToListAsync(ct);
            foreach (var other in superseded)
                other.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync(ct);
        }
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT set_config('app.current_tenant_id', {membership.TenantId.ToString("D")}, true)",
            ct
        );
        currentChallenge.State = IdentityVerificationState.Consumed;
        currentChallenge.VerifiedAt = now;
        currentChange.CompletionEvidenceId = evidence;
        currentChange.CompletedAt = now;
        await db.SaveChangesAsync(ct);
        registrationNow.MobileHmacKey = destinationKey;
        registrationNow.MobileHmacVersion = destinationVersion;
        registrationNow.MobileHmacDomain = "mobile";
        registrationNow.MaskedMobile = currentChallenge.MaskedDestination;
        registrationNow.MobileVerified = true;
        registrationNow.UpdatedAt = now;
        await relationships.SaveChangesAsync(ct);
        try
        {
            await RecordIdempotencyAsync(
                db,
                actor.Subject,
                key,
                "ConfirmPhoneChange",
                requestHash,
                200,
                challengeId.ToString("D"),
                ct,
                actor.Issuer
            );
        }
        catch (DbUpdateException conflict) when (IsIdentityMatchKeyConflict(conflict))
        {
            throw new IdentityDuplicateResolutionRequiredException(
                "Replacement number conflicts with an existing account."
            );
        }
        RequirePhoneChangeInput(key, authTime);
        if (currentChallenge.ExpiresAt <= _clock.GetUtcNow())
            throw new IdentityChallengeExpiredException(
                "Phone-change challenge expired before commit."
            );
        await commit.CommitAsync(ct);
        return PhoneChangeResult(currentChallenge, currentChange);
    }

    public async Task<IdentityPhoneChangeResult?> GetPhoneChangeAsync(
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        CancellationToken ct
    )
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        await using var transaction = await BeginPhoneChangeContextAsync(db, actor, membership, ct);
        var latest = await db
            .PhoneChanges.Where(v =>
                v.ActorIssuer == actor.Issuer
                && v.ActorSubject == actor.Subject
                && v.AccountId == membership.AccountId
                && v.TenantId == membership.TenantId
                && v.MembershipId == membership.MembershipId
            )
            .OrderByDescending(v => v.CreatedAt)
            .FirstOrDefaultAsync(ct);
        if (latest is null)
            return null;
        var challenge = await db.VerificationChallenges.SingleAsync(
            v => v.ChallengeId == latest.ChallengeId,
            ct
        );
        return PhoneChangeResult(challenge, latest);
    }

    public async Task<IdentityPhoneChangeResult> CancelPhoneChangeAsync(
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        Guid challengeId,
        Guid key,
        DateTimeOffset authTime,
        CancellationToken ct
    )
    {
        RequirePhoneChangeInput(key, authTime);
        if (challengeId == Guid.Empty)
            throw new IdentityActionDeniedException("IDENTITY_REQUEST_INVALID");
        await using (var initial = await _dbFactory.CreateDbContextAsync(ct))
        {
            await using var transaction = await BeginPhoneChangeContextAsync(
                initial,
                actor,
                membership,
                ct
            );
            await RequirePhoneChangeAsync(initial, challengeId, actor, membership, ct);
        }
        var evidence = await RequireConstitutionalEvidenceAsync(
            membership.TenantId,
            key,
            "IDENTITY_PHONE_CHANGE_CANCEL",
            new { challengeId },
            ct
        );
        if (evidence == Guid.Empty)
            throw new IdentityDeliveryUnavailableException("Phone-change evidence is unavailable.");
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        await using var commit = await BeginPhoneChangeContextAsync(db, actor, membership, ct);
        RequirePhoneChangeInput(key, authTime);
        var change = await RequirePhoneChangeAsync(db, challengeId, actor, membership, ct);
        var challenge = await db.VerificationChallenges.SingleAsync(
            v => v.ChallengeId == challengeId,
            ct
        );
        var hash = challengeId.ToString("D");
        var (replay, conflict) = await CheckIdempotencyAsync(
            db,
            actor.Subject,
            key,
            "CancelPhoneChange",
            hash,
            ct,
            actor.Issuer
        );
        if (conflict)
            throw new IdentityIdempotencyConflict(key.ToString());
        if (change.CompletedAt is not null)
            throw new IdentityActionDeniedException(
                "A completed phone change cannot be cancelled."
            );
        if (replay is not null)
            return PhoneChangeResult(challenge, change);
        challenge.State = IdentityVerificationState.Expired;
        await RecordIdempotencyAsync(
            db,
            actor.Subject,
            key,
            "CancelPhoneChange",
            hash,
            200,
            hash,
            ct,
            actor.Issuer
        );
        RequirePhoneChangeInput(key, authTime);
        if (commit is not null)
            await commit.CommitAsync(ct);
        return PhoneChangeResult(challenge, change);
    }

    private void RequirePhoneChangeInput(Guid key, DateTimeOffset authTime)
    {
        var now = _clock.GetUtcNow();
        if (authTime > now || now - authTime > TimeSpan.FromMinutes(Aal3FreshWindowMinutes))
            throw new IdentityStepUpRequiredException(
                "Fresh authentication is required.",
                Guid.NewGuid()
            );
        if (key == Guid.Empty)
            throw new IdentityActionDeniedException("IDENTITY_REQUEST_INVALID");
    }

    private void RequireUsablePhoneChange(IdentityVerificationChallengeRecord challenge)
    {
        if (
            challenge.State != IdentityVerificationState.Pending
            || challenge.ExpiresAt <= _clock.GetUtcNow()
            || challenge.DeliveryState != "SUBMITTED"
            || challenge.FailedAttempts >= MaximumMobileVerificationAttempts
            || challenge.DestinationHmacKey is null
            || challenge.DestinationHmacVersion is null
        )
            throw new IdentityChallengeExpiredException("Phone-change challenge is unavailable.");
    }

    private async Task RequirePhoneChangeRateAsync(
        IdentityDbContext db,
        Guid registration,
        CancellationToken ct
    )
    {
        var now = _clock.GetUtcNow();
        var recent = await db
            .VerificationChallenges.Where(v =>
                v.RegistrationId == registration
                && v.Purpose == IdentityVerificationPurpose.Mobile
                && v.ResendAfter > now
            )
            .Select(v => (DateTimeOffset?)v.ResendAfter)
            .MaxAsync(ct);
        if (recent is { } next)
            throw new IdentityVerificationRateLimitedException(next);
        var hour = now.AddHours(-1);
        var day = now.AddDays(-1);
        var requests = await db
            .PhoneChanges.Where(v => v.RegistrationId == registration && v.CreatedAt > day)
            .Select(v => v.CreatedAt)
            .ToListAsync(ct);
        if (requests.Count >= 10)
            throw new IdentityVerificationRateLimitedException(requests.Min().AddDays(1));
        var hourly = requests.Where(v => v > hour).ToArray();
        if (hourly.Length >= 3)
            throw new IdentityVerificationRateLimitedException(hourly.Min().AddHours(1));
    }

    private static async Task<IdentityPhoneChangeRecord> RequirePhoneChangeAsync(
        IdentityDbContext db,
        Guid challenge,
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        CancellationToken ct
    ) =>
        await db.PhoneChanges.SingleOrDefaultAsync(
            v =>
                v.ChallengeId == challenge
                && v.ActorIssuer == actor.Issuer
                && v.ActorSubject == actor.Subject
                && v.AccountId == membership.AccountId
                && v.TenantId == membership.TenantId
                && v.MembershipId == membership.MembershipId,
            ct
        ) ?? throw new IdentityResourceNotFoundException("Phone-change request not accessible.");

    private IdentityPhoneChangeResult PhoneChangeResult(
        IdentityVerificationChallengeRecord challenge,
        IdentityPhoneChangeRecord change
    ) =>
        new(
            challenge.ChallengeId,
            change.CompletedAt is not null ? "COMPLETED"
                : challenge.State == IdentityVerificationState.Expired
                || challenge.ExpiresAt <= _clock.GetUtcNow()
                    ? "EXPIRED"
                : challenge.DeliveryState != "SUBMITTED" ? "DELIVERY_UNRESOLVED"
                : "OTP_REQUIRED",
            challenge.MaskedDestination,
            challenge.ExpiresAt
        );

    private async Task RequirePhoneAvailableAsync(
        IdentityDbContext db,
        Guid account,
        IReadOnlyDictionary<string, string> candidates,
        CancellationToken ct
    )
    {
        if (!db.Database.IsNpgsql())
            throw new IdentityActionDeniedException("Phone replacement requires PostgreSQL.");
        var json = JsonSerializer.Serialize(candidates);
        if (
            await db
                .Database.SqlQuery<bool>(
                    $"SELECT identity.phone_change_conflicts({account}, {json}::jsonb) AS \"Value\""
                )
                .SingleAsync(ct)
        )
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
    }

    private async Task<IdentityPhoneChangeResult> SavePhoneChangeDeliveryAsync(
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        Guid challengeId,
        string state,
        CancellationToken ct
    )
    {
        await using var db = await _dbFactory.CreateDbContextAsync(ct);
        await using var transaction = await BeginPhoneChangeContextAsync(db, actor, membership, ct);
        var change = await RequirePhoneChangeAsync(db, challengeId, actor, membership, ct);
        var challenge = await db.VerificationChallenges.SingleAsync(
            v => v.ChallengeId == challengeId,
            ct
        );
        challenge.DeliveryState = state;
        await db.SaveChangesAsync(ct);
        if (transaction is not null)
            await transaction.CommitAsync(ct);
        return PhoneChangeResult(challenge, change);
    }

    private static async Task<IDbContextTransaction?> BeginPhoneChangeContextAsync(
        IdentityDbContext db,
        VerifiedCustomerActor actor,
        CustomerWorkspaceMembership membership,
        CancellationToken ct
    )
    {
        if (!membership.Roles.Contains("OWNER") || !Guid.TryParse(actor.Subject, out var subject))
            throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
        var transaction = await BeginPortalContextAsync(
            db,
            actor.Issuer,
            actor.Subject,
            membership,
            ct
        );
        try
        {
            if (!db.Database.IsNpgsql() || transaction is null)
                throw new IdentityActionDeniedException("Phone replacement requires PostgreSQL.");
            var locked = await db
                .Database.SqlQuery<bool>(
                    $"""
                    SELECT EXISTS (
                        SELECT 1 FROM identity.lock_conversation_runtime_membership(
                            {actor.Issuer}, {subject}, {membership.TenantId}, {membership.MembershipId}) m
                        WHERE m.account_id = {membership.AccountId} AND 'OWNER' = ANY(m.roles)
                    ) AS "Value"
                    """
                )
                .SingleAsync(ct);
            if (!locked)
                throw new IdentityResourceNotFoundException("Active account membership not found.");
            var registration = await GetPortalRegistrationAsync(
                db,
                actor.Issuer,
                actor.Subject,
                membership,
                ct
            );
            await db
                .Registrations.FromSqlInterpolated(
                    $"SELECT * FROM identity.registrations WHERE registration_id = {registration.RegistrationId} FOR UPDATE"
                )
                .ToListAsync(ct);
            await db.Entry(registration).ReloadAsync(ct);
            return transaction;
        }
        catch
        {
            if (transaction is not null)
                await transaction.DisposeAsync();
            throw;
        }
    }
}
