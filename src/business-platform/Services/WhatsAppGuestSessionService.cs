// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R001-R003
// Constitutional basis: C-023, C-026, C-039, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppGuestSession
{
    public static string LockKey(Guid tenantId, string bindingDigest) =>
        Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes($"{tenantId:D}:{bindingDigest}"))
        );

    public Guid TenantId { get; init; }
    public string BindingDigest { get; init; } = string.Empty;
    public Guid ParticipantId { get; init; } = Guid.NewGuid();
    public Guid? EvidenceId { get; set; }
    public string? ProtectedDestination { get; set; }
    public DateTimeOffset FirstObservedAt { get; init; }
    public DateTimeOffset? AdmittedAt { get; set; }
    public DateTimeOffset LastInboundAt { get; set; }
    public DateTimeOffset? StoppedAt { get; set; }
    public DateTimeOffset? ServiceConsentNoticeQueuedAt { get; set; }
    public Guid? ServiceConsentNoticeMessageId { get; set; }
    public string? ServiceConsentNoticeVersion { get; set; }
    public DateTimeOffset? ServiceConsentAt { get; set; }
    public string? ServiceConsentMessageId { get; set; }
    public Guid? ServiceConsentEvidenceId { get; set; }
}

public sealed class WhatsAppGuestConsentHistory
{
    public Guid TenantId { get; init; }
    public string BindingDigest { get; init; } = string.Empty;
    public Guid EvidenceId { get; init; }
    public string NoticeVersion { get; init; } = string.Empty;
    public Guid NoticeMessageId { get; init; }
    public DateTimeOffset NoticeQueuedAt { get; init; }
    public string ConsentMessageId { get; init; } = string.Empty;
    public DateTimeOffset ConsentAt { get; init; }
}

public static class WhatsAppGuestConsent
{
    public const string NoticeVersion = "1";
    public const string Notice =
        "Before guest discovery, please review our Privacy Notice: https://cp.demo.waooaw.com/privacy. "
        + "WAOOAW will process and retain your messages to provide this WhatsApp Demo service. "
        + "This does not create an account or hiring relationship; marketing and proactive alerts are off. "
        + "Reply YES to consent and continue, or STOP to opt out.";
    public const string Accepted =
        "Thanks. Your service consent is recorded. You can now ask about current professionals and your goals. "
        + "This does not create an account or hiring relationship. Reply STOP to stop messages.";
    public const string RenewalUnavailable =
        "Your service consent needs renewal, but renewal is not available in this chat yet. "
        + "Please use the web portal for now. Reply STOP to stop messages.";
    public const string RegisteredNumberAccepted =
        "Thanks. Your service consent is recorded. This number has a verified WAOOAW registration. "
        + "You can browse current professionals here. Sign in at https://cp.demo.waooaw.com "
        + "to access your account or start Trial/Hire; this chat is not linked to private account history. "
        + "Reply STOP to stop messages.";

    public static bool IsAcceptance(string text) =>
        text.Trim().Equals("YES", StringComparison.OrdinalIgnoreCase);

    public static bool IsCurrent(WhatsAppGuestSession guest) =>
        guest.ServiceConsentAt is not null
        && guest.ServiceConsentEvidenceId is not null
        && guest.ServiceConsentNoticeVersion == NoticeVersion;

    public static bool IsPreConsentNotice(string text) =>
        text
            is Notice
                or RenewalUnavailable
                or WhatsAppGuestTrafficBudget.UnsupportedContentNotice
                or WhatsAppGuestTrafficBudget.MessageLimitNotice
                or WhatsAppGuestTrafficBudget.GlobalRateLimitNotice
                or WhatsAppGuestTrafficBudget.ActivationLimitNotice
                or WhatsAppGuestOperatingHours.ClosedNotice;
}

public static partial class WhatsAppPhoneDestinationProtector
{
    private const string EnvelopeVersion = "v1";
    private const string Purpose = "WAOOAW-WC134-PHONE-DESTINATION-ENCRYPTION-V1";

    public static string Protect(string keyMaterial, string phoneNumber, string subjectDigest)
    {
        ValidateSubjectDigest(subjectDigest);
        if (!System.Text.RegularExpressions.Regex.IsMatch(phoneNumber, @"^\+[1-9][0-9]{7,14}$"))
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_INVALID");

        var nonce = RandomNumberGenerator.GetBytes(12);
        var plaintext = Encoding.UTF8.GetBytes(phoneNumber);
        var ciphertext = new byte[plaintext.Length];
        var tag = new byte[16];
        var encryptionKey = DeriveKey(keyMaterial);
        try
        {
            using var aes = new AesGcm(encryptionKey, tag.Length);
            aes.Encrypt(nonce, plaintext, ciphertext, tag, Encoding.ASCII.GetBytes(subjectDigest));
        }
        finally
        {
            CryptographicOperations.ZeroMemory(encryptionKey);
            CryptographicOperations.ZeroMemory(plaintext);
        }
        return $"{EnvelopeVersion}.{Convert.ToBase64String(nonce)}."
            + $"{Convert.ToBase64String(tag)}.{Convert.ToBase64String(ciphertext)}";
    }

    public static string Unprotect(
        string keyMaterial,
        string protectedDestination,
        string subjectDigest
    )
    {
        ValidateSubjectDigest(subjectDigest);
        var parts = protectedDestination.Split('.');
        if (
            parts.Length != 4
            || parts[0] != EnvelopeVersion
            || !TryDecode(parts[1], 12, out var nonce)
            || !TryDecode(parts[2], 16, out var tag)
            || !TryDecode(parts[3], 9, 16, out var ciphertext)
        )
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");

        var plaintext = new byte[ciphertext.Length];
        var encryptionKey = DeriveKey(keyMaterial);
        try
        {
            using var aes = new AesGcm(encryptionKey, tag.Length);
            aes.Decrypt(nonce, ciphertext, tag, plaintext, Encoding.ASCII.GetBytes(subjectDigest));
            var phoneNumber = Encoding.UTF8.GetString(plaintext);
            if (!System.Text.RegularExpressions.Regex.IsMatch(phoneNumber, @"^\+[1-9][0-9]{7,14}$"))
                throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
            return phoneNumber;
        }
        catch (CryptographicException)
        {
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
        }
        finally
        {
            CryptographicOperations.ZeroMemory(encryptionKey);
            CryptographicOperations.ZeroMemory(plaintext);
        }
    }

    private static byte[] DeriveKey(string keyMaterial)
    {
        var key = Encoding.UTF8.GetBytes(keyMaterial);
        if (key.Length < 32)
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_KEY_UNAVAILABLE");
        try
        {
            return HMACSHA256.HashData(key, Encoding.ASCII.GetBytes(Purpose));
        }
        finally
        {
            CryptographicOperations.ZeroMemory(key);
        }
    }

    private static bool TryDecode(string value, int expectedLength, out byte[] decoded)
    {
        decoded = [];
        try
        {
            decoded = Convert.FromBase64String(value);
            return decoded.Length == expectedLength;
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static bool TryDecode(
        string value,
        int minimumLength,
        int maximumLength,
        out byte[] decoded
    )
    {
        decoded = [];
        try
        {
            decoded = Convert.FromBase64String(value);
            return decoded.Length >= minimumLength && decoded.Length <= maximumLength;
        }
        catch (FormatException)
        {
            return false;
        }
    }

    private static void ValidateSubjectDigest(string subjectDigest)
    {
        if (
            subjectDigest.Length != 64
            || subjectDigest.Any(character =>
                character is not (>= '0' and <= '9') and not (>= 'a' and <= 'f')
            )
        )
            throw new WhatsAppCapabilityUnavailableException("PHONE_SUBJECT_INVALID");
    }
}

public sealed class WhatsAppGuestSessionService(
    IDbContextFactory<ConversationStoreDbContext> factory,
    IWhatsAppRegistrationEvidenceGateway evidence,
    IWhatsAppCapabilityGate capability,
    IGuestConversation interactions,
    WhatsAppOutboxService outbox,
    WhatsAppGuestTrafficBudget trafficBudget,
    TimeProvider clock,
    IWhatsAppRegistrationRecognition? registrationRecognition = null,
    IWhatsAppAccountLinkConfirmation? accountLinkConfirmation = null
)
{
    public async Task<WhatsAppJourneyReceipt> ReceiveAsync(
        VerifiedPhoneIdentityProof proof,
        CancellationToken ct,
        string? verifiedPhoneNumber = null
    )
    {
        var authority = capability.RequireActive(clock.GetUtcNow());
        if (
            !authority.AllowProvisionalOnboarding
            || proof.Environment != authority.Environment
            || proof.PhoneSubjectHash.Length != 64
            || proof.PhoneSubjectHash.Any(character =>
                character is not (>= '0' and <= '9') and not (>= 'a' and <= 'f')
            )
        )
            throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");
        if (authority.AllowPublicAdmission && proof.ProtectedDestination is null)
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
        if (!authority.AllowPublicAdmission)
            capability.RequireRecipient(
                authority.TenantId,
                proof.PhoneSubjectHash,
                clock.GetUtcNow()
            );
        await using var db = await factory.CreateDbContextAsync(ct);
        await using var transaction = await db.Database.BeginTransactionAsync(ct);
        var lockKey = WhatsAppGuestSession.LockKey(authority.TenantId, proof.PhoneSubjectHash);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
            ct
        );
        var guestSession = await db.Set<WhatsAppGuestSession>()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == authority.TenantId
                    && value.BindingDigest == proof.PhoneSubjectHash,
                ct
            );
        var newSession =
            guestSession is null
            || guestSession.EvidenceId is null && guestSession.AdmittedAt is null;
        if (guestSession is null)
        {
            guestSession = new WhatsAppGuestSession
            {
                TenantId = authority.TenantId,
                BindingDigest = proof.PhoneSubjectHash,
                FirstObservedAt = proof.VerifiedAt,
                LastInboundAt = proof.SentAt,
                ProtectedDestination = proof.ProtectedDestination,
            };
            db.Add(guestSession);
        }
        else if (
            proof.ProtectedDestination is not null
            && proof.SentAt > guestSession.LastInboundAt
            && guestSession.StoppedAt is null
        )
        {
            guestSession.ProtectedDestination = proof.ProtectedDestination;
        }
        var stop = proof.Text.Trim().Equals("STOP", StringComparison.OrdinalIgnoreCase);
        if (stop)
        {
            guestSession.StoppedAt ??= clock.GetUtcNow();
            await db.SaveChangesAsync(ct);
            await transaction.CommitAsync(ct);
            return new(proof.MessageId, "STOPPED", "STOP", string.Empty, false, string.Empty);
        }
        if (guestSession.StoppedAt is not null)
        {
            await transaction.CommitAsync(ct);
            return new(proof.MessageId, "STOPPED", "STOP", string.Empty, false, string.Empty);
        }
        var trafficNotice = await trafficBudget.ReserveInboundAsync(
            guestSession.TenantId,
            guestSession.BindingDigest,
            proof.MessageId,
            newSession,
            ct
        );
        if (trafficNotice == WhatsAppGuestTrafficNotice.GuestSessionLimit)
        {
            await transaction.RollbackAsync(ct);
            return await SendFixedLimitNoticeAsync(authority, proof, ct);
        }
        // A pending record preserves evidence inputs across uncertain CE responses; it grants no admission.
        await db.SaveChangesAsync(ct);
        await transaction.CommitAsync(ct);

        await db.Entry(guestSession).ReloadAsync(ct);
        if (guestSession.StoppedAt is not null)
        {
            return new(proof.MessageId, "STOPPED", "STOP", string.Empty, false, string.Empty);
        }
        Guid? admissionEvidenceId = null;
        if (guestSession.EvidenceId is null)
        {
            var evidenceId = await evidence.RecordGuestAdmissionAsync(
                authority.TenantId,
                $"guest-session:{lockKey}",
                proof.PhoneSubjectHash,
                guestSession.FirstObservedAt,
                ct
            );
            if (evidenceId == Guid.Empty)
                throw new InvalidOperationException(
                    "Guest-session admission requires a valid evidence identifier."
                );
            admissionEvidenceId = evidenceId;
        }
        Guid? recordedConsentEvidenceId = null;
        var noticeQueuedAt = guestSession.ServiceConsentNoticeQueuedAt;
        if (CanConsent(guestSession, proof))
        {
            var consentEvidenceId = await evidence.RecordGuestConsentAsync(
                guestSession.TenantId,
                proof.MessageId,
                guestSession.BindingDigest,
                WhatsAppGuestConsent.NoticeVersion,
                proof.VerifiedAt,
                ct
            );
            if (consentEvidenceId == Guid.Empty)
                throw new InvalidOperationException(
                    "Guest service consent requires a valid evidence identifier."
                );
            recordedConsentEvidenceId = consentEvidenceId;
        }

        await using var admission = await db.Database.BeginTransactionAsync(ct);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
            ct
        );
        await db.Entry(guestSession).ReloadAsync(ct);
        if (guestSession.StoppedAt is not null)
        {
            await admission.CommitAsync(ct);
            return new(proof.MessageId, "STOPPED", "STOP", string.Empty, false, string.Empty);
        }
        if (capability.RequireActive(clock.GetUtcNow()) != authority)
            throw new WhatsAppCapabilityUnavailableException("ADMISSION_AUTHORITY_CHANGED");
        if (guestSession.EvidenceId is null)
        {
            guestSession.EvidenceId =
                admissionEvidenceId ?? throw new ConversationStateConflictException();
            guestSession.AdmittedAt = clock.GetUtcNow();
        }
        if (
            recordedConsentEvidenceId is { } confirmedConsent
            && guestSession.ServiceConsentNoticeQueuedAt == noticeQueuedAt
            && CanConsent(guestSession, proof)
        )
        {
            guestSession.ServiceConsentAt = proof.VerifiedAt;
            guestSession.ServiceConsentMessageId = proof.MessageId;
            guestSession.ServiceConsentEvidenceId = confirmedConsent;
        }
        var consentedThisMessage =
            WhatsAppGuestConsent.IsCurrent(guestSession)
            && guestSession.ServiceConsentMessageId == proof.MessageId;
        if (proof.SentAt > guestSession.LastInboundAt)
            guestSession.LastInboundAt = proof.SentAt;
        await db.SaveChangesAsync(ct);
        await admission.CommitAsync(ct);
        var renewalRequired =
            guestSession.ServiceConsentNoticeVersion is not null
                && guestSession.ServiceConsentNoticeVersion != WhatsAppGuestConsent.NoticeVersion
            || guestSession.ServiceConsentAt is not null
                && !WhatsAppGuestConsent.IsCurrent(guestSession);
        if (guestSession.ServiceConsentAt is null || consentedThisMessage || renewalRequired)
        {
            var recognizedRegistration =
                consentedThisMessage
                && !proof.UnsupportedContent
                && WhatsAppGuestOperatingHours.IsOpen(clock.GetUtcNow())
                && trafficNotice == WhatsAppGuestTrafficNotice.None
                && registrationRecognition is not null
                && verifiedPhoneNumber is not null
                && await registrationRecognition.IsVerifiedRegistrationAsync(
                    verifiedPhoneNumber,
                    ct
                );
            var notice =
                proof.UnsupportedContent ? WhatsAppGuestTrafficBudget.UnsupportedContentNotice
                : !WhatsAppGuestOperatingHours.IsOpen(clock.GetUtcNow())
                    ? WhatsAppGuestOperatingHours.ClosedNotice
                : trafficNotice switch
                {
                    WhatsAppGuestTrafficNotice.GuestMessageLimit =>
                        WhatsAppGuestTrafficBudget.MessageLimitNotice,
                    WhatsAppGuestTrafficNotice.GlobalRateLimit =>
                        WhatsAppGuestTrafficBudget.GlobalRateLimitNotice,
                    WhatsAppGuestTrafficNotice.ActivationLimit =>
                        WhatsAppGuestTrafficBudget.ActivationLimitNotice,
                    _ => renewalRequired ? WhatsAppGuestConsent.Notice
                    : consentedThisMessage
                        ? recognizedRegistration ? WhatsAppGuestConsent.RegisteredNumberAccepted
                            : WhatsAppGuestConsent.Accepted
                    : WhatsAppGuestConsent.Notice,
                };
            var noticeSubmission = await interactions.SendGuestFixedNoticeAsync(
                guestSession.TenantId,
                guestSession.ParticipantId,
                MessageKey(proof),
                notice,
                ct
            );
            await outbox.QueueGuestDiscoveryAsync(
                guestSession,
                noticeSubmission.Value,
                proof.VerifiedAt,
                ct
            );
            if (notice == WhatsAppGuestConsent.Notice)
            {
                await using var noticeTransaction = await db.Database.BeginTransactionAsync(ct);
                await db.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
                    ct
                );
                await db.Entry(guestSession).ReloadAsync(ct);
                if (guestSession.StoppedAt is not null)
                {
                    await noticeTransaction.CommitAsync(ct);
                    return new(
                        proof.MessageId,
                        "STOPPED",
                        "STOP",
                        string.Empty,
                        false,
                        string.Empty
                    );
                }
                if (capability.RequireActive(clock.GetUtcNow()) != authority)
                    throw new WhatsAppCapabilityUnavailableException("ADMISSION_AUTHORITY_CHANGED");
                if (
                    guestSession.ServiceConsentNoticeQueuedAt is null
                    || guestSession.ServiceConsentNoticeVersion
                        != WhatsAppGuestConsent.NoticeVersion
                )
                {
                    if (guestSession.ServiceConsentAt is { } previousConsentAt)
                    {
                        db.Add(
                            new WhatsAppGuestConsentHistory
                            {
                                TenantId = guestSession.TenantId,
                                BindingDigest = guestSession.BindingDigest,
                                EvidenceId =
                                    guestSession.ServiceConsentEvidenceId
                                    ?? throw new ConversationStateConflictException(),
                                NoticeVersion =
                                    guestSession.ServiceConsentNoticeVersion
                                    ?? throw new ConversationStateConflictException(),
                                NoticeMessageId =
                                    guestSession.ServiceConsentNoticeMessageId
                                    ?? throw new ConversationStateConflictException(),
                                NoticeQueuedAt =
                                    guestSession.ServiceConsentNoticeQueuedAt
                                    ?? throw new ConversationStateConflictException(),
                                ConsentMessageId =
                                    guestSession.ServiceConsentMessageId
                                    ?? throw new ConversationStateConflictException(),
                                ConsentAt = previousConsentAt,
                            }
                        );
                        guestSession.ServiceConsentAt = null;
                        guestSession.ServiceConsentMessageId = null;
                        guestSession.ServiceConsentEvidenceId = null;
                    }
                    guestSession.ServiceConsentNoticeQueuedAt = clock.GetUtcNow();
                    guestSession.ServiceConsentNoticeMessageId = noticeSubmission.Value.MessageId;
                    guestSession.ServiceConsentNoticeVersion = WhatsAppGuestConsent.NoticeVersion;
                    await db.SaveChangesAsync(ct);
                }
                await noticeTransaction.CommitAsync(ct);
            }
            return new(
                proof.MessageId,
                renewalRequired ? "CONSENT_REQUIRED"
                    : consentedThisMessage ? "CONSENT_RECORDED"
                    : "CONSENT_REQUIRED",
                "GUEST_CONSENT",
                noticeSubmission.Value.Content.Single().Text,
                noticeSubmission.Replayed,
                string.Empty
            );
        }
        var messageKey = new Guid(
            SHA256
                .HashData(
                    Encoding.UTF8.GetBytes(
                        $"{proof.Environment}:{proof.AppBindingDigest}:{proof.MessageId}"
                    )
                )
                .AsSpan(0, 16)
        );
        var request = new SendPortalInteractionMessageRequestV1(
            "1.0",
            messageKey,
            [
                new(
                    "1.0",
                    "TEXT",
                    proof.UnsupportedContent ? "Unsupported WhatsApp content" : proof.Text,
                    "en-IN"
                ),
            ],
            "en-IN",
            "MARKETPLACE"
        );
        var fixedNotice = !WhatsAppGuestOperatingHours.IsOpen(clock.GetUtcNow())
            ? WhatsAppGuestOperatingHours.ClosedNotice
            : trafficNotice switch
            {
                WhatsAppGuestTrafficNotice.GuestMessageLimit =>
                    WhatsAppGuestTrafficBudget.MessageLimitNotice,
                WhatsAppGuestTrafficNotice.GlobalRateLimit =>
                    WhatsAppGuestTrafficBudget.GlobalRateLimitNotice,
                WhatsAppGuestTrafficNotice.ActivationLimit =>
                    WhatsAppGuestTrafficBudget.ActivationLimitNotice,
                _ => proof.UnsupportedContent
                    ? WhatsAppGuestTrafficBudget.UnsupportedContentNotice
                    : null,
            };
        if (WhatsAppAccountLinkInstruction.IsInstruction(proof.Text))
        {
            var linkNotice =
                fixedNotice ?? await ConfirmAccountLinkAsync(proof, verifiedPhoneNumber, ct);
            var linkReply = await interactions.SendGuestFixedNoticeAsync(
                guestSession.TenantId,
                guestSession.ParticipantId,
                messageKey,
                linkNotice,
                ct
            );
            await outbox.QueueGuestDiscoveryAsync(
                guestSession,
                linkReply.Value,
                proof.VerifiedAt,
                ct
            );
            return new(
                proof.MessageId,
                "ACCEPTED",
                "ACCOUNT_LINK",
                linkReply.Value.Content.Single().Text,
                linkReply.Replayed,
                string.Empty
            );
        }
        var submitted = fixedNotice is not null
            ? proof.UnsupportedContent
                ? await interactions.SendGuestFixedNoticeAsync(
                    guestSession.TenantId,
                    guestSession.ParticipantId,
                    messageKey,
                    fixedNotice,
                    ct
                )
                : await SendOrdinaryGuestNoticeAsync(
                    guestSession,
                    messageKey,
                    request,
                    fixedNotice,
                    ct
                )
            : await SendOrdinaryGuestDiscoveryAsync(guestSession, messageKey, request, ct);
        var reply = submitted.Value;
        await outbox.QueueGuestDiscoveryAsync(guestSession, reply, proof.VerifiedAt, ct);
        return new(
            proof.MessageId,
            "ACCEPTED",
            "GUEST_DISCOVERY",
            reply.Content.Single().Text,
            submitted.Replayed,
            string.Empty
        );
    }

    private static bool CanConsent(
        WhatsAppGuestSession guestSession,
        VerifiedPhoneIdentityProof proof
    ) =>
        guestSession.ServiceConsentAt is null
        && guestSession.ServiceConsentNoticeQueuedAt is not null
        && guestSession.ServiceConsentNoticeVersion == WhatsAppGuestConsent.NoticeVersion
        && proof.VerifiedAt > guestSession.ServiceConsentNoticeQueuedAt
        && proof.SentAt > guestSession.ServiceConsentNoticeQueuedAt
        && !proof.UnsupportedContent
        && WhatsAppGuestConsent.IsAcceptance(proof.Text);

    private async Task<string> ConfirmAccountLinkAsync(
        VerifiedPhoneIdentityProof proof,
        string? phoneNumber,
        CancellationToken ct
    )
    {
        if (accountLinkConfirmation is null || phoneNumber is null)
            throw new IdentityDeliveryUnavailableException("Account linking is unavailable.");
        try
        {
            await accountLinkConfirmation.ConfirmAsync(
                proof.Text.Trim()[4..].Trim(),
                phoneNumber,
                proof,
                ct
            );
            return WhatsAppAccountLinkInstruction.ConfirmedNotice;
        }
        catch (IdentityActionDeniedException)
        {
            return WhatsAppAccountLinkInstruction.DeniedNotice;
        }
        catch (IdentityResourceNotFoundException)
        {
            return WhatsAppAccountLinkInstruction.DeniedNotice;
        }
    }

    private async Task<
        ConversationCommandResult<PortalInteractionMessageV1>
    > SendOrdinaryGuestNoticeAsync(
        WhatsAppGuestSession guestSession,
        Guid messageKey,
        SendPortalInteractionMessageRequestV1 request,
        string notice,
        CancellationToken ct
    )
    {
        var result = await interactions.SendGuestNoticeAsync(
            guestSession.TenantId,
            guestSession.ParticipantId,
            messageKey,
            request,
            notice,
            ct
        );
        return new(result.Value.GuideMessage, result.Replayed);
    }

    private async Task<
        ConversationCommandResult<PortalInteractionMessageV1>
    > SendOrdinaryGuestDiscoveryAsync(
        WhatsAppGuestSession guestSession,
        Guid messageKey,
        SendPortalInteractionMessageRequestV1 request,
        CancellationToken ct
    )
    {
        var result = await interactions.SendGuestDiscoveryAsync(
            guestSession.TenantId,
            guestSession.ParticipantId,
            messageKey,
            request,
            ct
        );
        return new(result.Value.GuideMessage, result.Replayed);
    }

    private async Task<WhatsAppJourneyReceipt> SendFixedLimitNoticeAsync(
        WhatsAppActivationAuthority authority,
        VerifiedPhoneIdentityProof proof,
        CancellationToken ct
    )
    {
        if (proof.ProtectedDestination is null)
            throw new WhatsAppCapabilityUnavailableException("PHONE_DESTINATION_UNAVAILABLE");
        var messageKey = MessageKey(proof);
        var participantId = AdmissionNoticeParticipantId(authority.TenantId, proof);
        var notice = WhatsAppGuestTrafficBudget.SessionLimitNotice;
        var submission = await interactions.SendGuestFixedNoticeAsync(
            authority.TenantId,
            participantId,
            messageKey,
            notice,
            ct
        );
        await outbox.QueueGuestAdmissionNoticeAsync(
            authority.TenantId,
            participantId,
            proof.PhoneSubjectHash,
            proof.ProtectedDestination,
            submission.Value,
            proof.SentAt,
            ct
        );
        return new(
            proof.MessageId,
            "LIMIT_REACHED",
            "GUEST_SESSION_LIMIT",
            notice,
            submission.Replayed,
            string.Empty
        );
    }

    private static Guid AdmissionNoticeParticipantId(
        Guid tenantId,
        VerifiedPhoneIdentityProof proof
    )
    {
        var digest = SHA256.HashData(
            Encoding.UTF8.GetBytes(
                $"WC134:admission-limit:{proof.Environment}:{tenantId:D}:{proof.PhoneSubjectHash}"
            )
        );
        return new Guid(digest.AsSpan(0, 16));
    }

    private static Guid MessageKey(VerifiedPhoneIdentityProof proof) =>
        new(
            SHA256
                .HashData(
                    Encoding.UTF8.GetBytes(
                        $"{proof.Environment}:{proof.AppBindingDigest}:{proof.MessageId}"
                    )
                )
                .AsSpan(0, 16)
        );
}
