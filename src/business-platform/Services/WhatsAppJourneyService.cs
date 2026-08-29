// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppJourneyOptions
{
    public string WebhookSecret { get; set; } = string.Empty;
    public string TenantTokenKey { get; set; } = string.Empty;
}

public sealed record WhatsAppJourneyReceipt(
    string MessageId,
    string Status,
    string JourneyStage,
    string Reply,
    bool Replayed,
    string InternalTenantToken);

public sealed record PortalPhoneAttachProof(
    Guid ParticipantId,
    string AuthenticationAssurance,
    DateTimeOffset AuthenticatedAt,
    Guid CorrelationId);

public sealed record WhatsAppRelationshipResolution(
    Guid TenantId,
    Guid RelationshipId,
    Guid ParticipantId,
    Guid BindingId,
    string AuthenticationAssurance);

public sealed record VerifiedPhoneIdentityProof(
    string MessageId,
    string PhoneSubjectHash,
    string Text,
    string? RiskTier,
    string Audience,
    string AuthenticationAssurance,
    DateTimeOffset SentAt,
    DateTimeOffset VerifiedAt,
    DateTimeOffset ExpiresAt,
    Guid CorrelationId);

public sealed class WhatsAppWebhookException(int statusCode, string code) : Exception(code)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}

public sealed partial class WhatsAppJourneyService
{
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IWhatsAppRegistrationEvidenceGateway _evidenceGateway;
    private readonly byte[] _webhookSecret;
    private readonly byte[] _tokenKey;
    private readonly IRelationshipConstitutionalGateway? _relationshipGateway;
    private readonly RelationshipEmergencyStopService? _emergencyStops;

    public WhatsAppJourneyService(
        IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
        IWhatsAppRegistrationEvidenceGateway evidenceGateway,
        IOptions<WhatsAppJourneyOptions> options,
        IRelationshipConstitutionalGateway? relationshipGateway = null,
        RelationshipEmergencyStopService? emergencyStops = null)
    {
        _dbFactory = dbFactory;
        _evidenceGateway = evidenceGateway;
        _webhookSecret = RequireKey(options.Value.WebhookSecret, nameof(options.Value.WebhookSecret));
        _tokenKey = RequireKey(options.Value.TenantTokenKey, nameof(options.Value.TenantTokenKey));
        _relationshipGateway = relationshipGateway;
        _emergencyStops = emergencyStops;
    }

    public async Task<WhatsAppJourneyReceipt> ReceiveAsync(
        string rawBody,
        string signatureHeader,
        DateTimeOffset receivedAt,
        CancellationToken cancellationToken)
    {
        VerifySignature(rawBody, signatureHeader);
        WhatsAppInbound inbound;
        try
        {
            inbound = JsonSerializer.Deserialize<WhatsAppInbound>(rawBody, new JsonSerializerOptions(JsonSerializerDefaults.Web))
                ?? throw new JsonException();
        }
        catch (JsonException)
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
        }
        if (string.IsNullOrWhiteSpace(inbound.MessageId) || string.IsNullOrWhiteSpace(inbound.Text)
            || !E164().IsMatch(inbound.From))
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
        }
        DateTimeOffset sentAt;
        try
        {
            sentAt = DateTimeOffset.FromUnixTimeSeconds(inbound.Timestamp);
        }
        catch (ArgumentOutOfRangeException)
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_TIMESTAMP_INVALID");
        }
        if ((receivedAt - sentAt).Duration() > TimeSpan.FromMinutes(5))
        {
            throw new WhatsAppWebhookException(409, "WHATSAPP_REPLAY_WINDOW_EXCEEDED");
        }

        var phoneHmac = HmacHex(_webhookSecret, inbound.From);
        return await ReceiveVerifiedAsync(new VerifiedPhoneIdentityProof(
            inbound.MessageId,
            phoneHmac,
            inbound.Text,
            inbound.RiskTier,
            "legacy-business-platform-adapter",
            "AAL1_CHANNEL",
            sentAt,
            receivedAt,
            receivedAt.AddMinutes(5),
            Guid.NewGuid()), cancellationToken);
    }

    public async Task<WhatsAppJourneyReceipt> ReceiveVerifiedAsync(
        VerifiedPhoneIdentityProof proof,
        CancellationToken cancellationToken)
    {
        var receivedAt = proof.VerifiedAt;
        if (string.IsNullOrWhiteSpace(proof.MessageId)
            || string.IsNullOrWhiteSpace(proof.PhoneSubjectHash)
            || string.IsNullOrWhiteSpace(proof.Text)
            || proof.ExpiresAt <= DateTimeOffset.UtcNow
            || (proof.VerifiedAt - proof.SentAt).Duration() > TimeSpan.FromMinutes(5))
            throw new WhatsAppWebhookException(403, "PHONE_IDENTITY_PROOF_INVALID");

        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var existingReceipt = await db.WhatsAppMessageReceipts
            .SingleOrDefaultAsync(item => item.MessageId == proof.MessageId, cancellationToken);
        if (existingReceipt is not null && existingReceipt.ExpiresAt > receivedAt)
        {
            return new(proof.MessageId, "DUPLICATE", "UNKNOWN",
                "This message was already received.", true, string.Empty);
        }
        if (existingReceipt is not null)
        {
            db.WhatsAppMessageReceipts.Remove(existingReceipt);
            await db.SaveChangesAsync(cancellationToken);
        }

        var contact = await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
            item => item.PhoneHmac == proof.PhoneSubjectHash, cancellationToken);
        if (contact is null)
        {
            contact = new WhatsAppJourneyContact
            {
                TenantId = Guid.NewGuid(),
                PhoneHmac = proof.PhoneSubjectHash,
                OptedInAt = receivedAt,
                LastInboundAt = receivedAt,
            };
            await _evidenceGateway.RecordAsync(
                contact.TenantId, proof.MessageId, proof.PhoneSubjectHash, receivedAt, cancellationToken);
            db.WhatsAppJourneyContacts.Add(contact);
        }
        contact.LastInboundAt = receivedAt;

        var bindings = await db.ChannelBindings.AsNoTracking()
            .Where(value => value.TenantId == contact.TenantId
                && value.Channel == "WHATSAPP"
                && value.ExternalSubjectHash == proof.PhoneSubjectHash
                && value.Status == "ACTIVE")
            .ToListAsync(cancellationToken);
        var binding = bindings.Count == 1 ? bindings[0] : null;
        var attachedRelationship = binding is null ? null : await db.EmploymentRelationships.AsNoTracking()
            .SingleOrDefaultAsync(value => value.TenantId == contact.TenantId
                && value.RelationshipId == binding.RelationshipId, cancellationToken);

        var riskTier = proof.RiskTier?.Trim().ToUpperInvariant() ?? "TIER_1_LOW_RISK";
        var confirmation = proof.Text.Trim().Equals("YES", StringComparison.OrdinalIgnoreCase)
            || proof.Text.Trim().Equals("CONFIRM", StringComparison.OrdinalIgnoreCase);
        string status;
        string reply;
        if (attachedRelationship?.State == EmploymentRelationshipState.StoppedEmergency)
        {
            contact.PendingMediumRiskConfirmation = false;
            contact.JourneyStage = "STOP";
            status = "STOPPED";
            reply = "This relationship is STOPPED_EMERGENCY. Consequential commands, configuration, contract, activation, and handoff remain blocked. Release is available only in the secure Tier-4 employer portal.";
        }
        else if (binding is not null && proof.Text.Contains("STOP", StringComparison.OrdinalIgnoreCase))
        {
            if (_emergencyStops is null) throw new InvalidOperationException("Relationship Emergency Stop is unavailable.");
            await _emergencyStops.StopAsync(
                contact.TenantId, binding.RelationshipId, binding.ParticipantId,
                RelationshipRoleCodec.FromDatabase(binding.ParticipantRole), Guid.NewGuid(), cancellationToken);
            contact.PendingMediumRiskConfirmation = false;
            contact.JourneyStage = "STOP";
            status = "ACCEPTED";
            reply = "Emergency Stop confirmed for the relationship. All known evaluation and trial sessions were halted; later consequential commands remain blocked.";
        }
        else if (riskTier == "TIER_4_CONSEQUENTIAL")
        {
            contact.PendingMediumRiskConfirmation = false;
            status = "SECURE_PORTAL_REQUIRED";
            reply = "Contracts, hiring, cancellation, and payment cannot be accepted or initiated in WhatsApp. Review the exact contract and current payment or activation status in the secure portal: /relationships. Payment details are entered only on Razorpay. You may choose Hire, Not now, Cancel, or Exit there.";
        }
        else if (riskTier == "TIER_3_HIGH_RISK")
        {
            status = "PORTAL_STEP_UP_REQUIRED";
            reply = "This high-risk action cannot be authorized by phone identity. Continue in the secure portal.";
        }
        else if (riskTier == "TIER_2_MEDIUM_RISK" && (!contact.PendingMediumRiskConfirmation || !confirmation))
        {
            contact.PendingMediumRiskConfirmation = true;
            status = "CONFIRMATION_REQUIRED";
            reply = "Reply YES to confirm this action. Reply NO or ignore to cancel.";
        }
        else
        {
            contact.PendingMediumRiskConfirmation = false;
            status = "ACCEPTED";
            (contact.JourneyStage, reply) = Present(proof.Text);
        }

        var (tenantToken, tokenHash, tokenExpiresAt) = IssueTenantToken(
            contact.TenantId, proof.PhoneSubjectHash, receivedAt);
        db.WhatsAppMessageReceipts.Add(new WhatsAppMessageReceipt
        {
            MessageId = proof.MessageId,
            TenantId = contact.TenantId,
            SessionTokenHash = tokenHash,
            SessionExpiresAt = tokenExpiresAt,
            ReceivedAt = receivedAt,
            ExpiresAt = receivedAt.AddHours(24),
        });
        await db.SaveChangesAsync(cancellationToken);
        return new(proof.MessageId, status, contact.JourneyStage, reply, false, tenantToken);
    }

    public async Task EnrolMpinAsync(
        Guid tenantId,
        string phone,
        string mpin,
        PortalPhoneAttachProof proof,
        CancellationToken cancellationToken)
    {
        ValidateFreshPortalProof(proof);
        ValidateMpin(mpin);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var phoneHmac = HmacHex(_webhookSecret, phone);
        var contact = await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.PhoneHmac == phoneHmac,
            cancellationToken) ?? throw new ConstitutionalActionDeniedException(
                "Unknown phone identity cannot be attached from portal payload hints.");
        contact.MpinHash = HmacHex(_tokenKey, $"{tenantId:D}:{mpin}");
        contact.MpinFailedAttempts = 0;
        contact.MpinLockedUntil = null;
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task<bool> VerifyMpinAsync(
        Guid tenantId,
        string phone,
        string mpin,
        DateTimeOffset attemptedAt,
        CancellationToken cancellationToken)
    {
        ValidateMpin(mpin);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var phoneHmac = HmacHex(_webhookSecret, phone);
        var contact = await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.PhoneHmac == phoneHmac,
            cancellationToken) ?? throw new ConstitutionalActionDeniedException("Phone identity is not registered.");
        if (contact.MpinLockedUntil > attemptedAt)
            throw new WhatsAppWebhookException(423, "WHATSAPP_MPIN_LOCKED");
        if (contact.MpinHash is null)
            throw new ConstitutionalActionDeniedException("MPIN is not enrolled.");

        var suppliedHash = HmacHex(_tokenKey, $"{tenantId:D}:{mpin}");
        var valid = CryptographicOperations.FixedTimeEquals(
            Convert.FromHexString(contact.MpinHash), Convert.FromHexString(suppliedHash));
        if (valid)
        {
            contact.MpinFailedAttempts = 0;
            contact.MpinLockedUntil = null;
        }
        else
        {
            contact.MpinFailedAttempts += 1;
            if (contact.MpinFailedAttempts >= 3)
            {
                contact.MpinFailedAttempts = 3;
                contact.MpinLockedUntil = attemptedAt.AddMinutes(30);
            }
        }
        await db.SaveChangesAsync(cancellationToken);
        return valid;
    }

    public async Task<WhatsAppRelationshipResolution> AttachPhoneAsync(
        Guid tenantId,
        Guid relationshipId,
        string phone,
        string conversationId,
        PortalPhoneAttachProof proof,
        CancellationToken cancellationToken)
    {
        ValidateFreshPortalProof(proof);
        if (_relationshipGateway is null)
            throw new InvalidOperationException("Relationship constitutional gateway is unavailable.");
        var phoneHmac = HmacHex(_webhookSecret, phone);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var contactExists = await db.WhatsAppJourneyContacts.AsNoTracking().AnyAsync(
            value => value.TenantId == tenantId && value.PhoneHmac == phoneHmac,
            cancellationToken);
        if (!contactExists)
            throw new ConstitutionalActionDeniedException(
                "Unknown phone identity cannot attach to an existing relationship.");
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken) ?? throw new KeyNotFoundException("Employment relationship was not found.");
        var participant = await db.RelationshipParticipants.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == proof.ParticipantId
                && value.Status == "ACTIVE",
            cancellationToken) ?? throw new ConstitutionalActionDeniedException(
                "Phone attachment requires an active same-tenant participant binding.");
        var existing = await db.ChannelBindings.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == proof.ParticipantId
                && value.Channel == "WHATSAPP"
                && value.Status == "ACTIVE",
            cancellationToken);
        if (existing is not null)
            return new(tenantId, relationshipId, proof.ParticipantId, existing.BindingId, existing.AssuranceLevel);

        var evidenceId = await _relationshipGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "ATTACH_WHATSAPP_PHONE",
            proof.CorrelationId,
            new
            {
                participant_id = proof.ParticipantId,
                participant_role = RelationshipRoleCodec.ToDatabase(participant.Role),
                phone_subject_hash = phoneHmac,
            },
            cancellationToken);
        var now = DateTimeOffset.UtcNow;
        var binding = new ChannelBinding
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = proof.ParticipantId,
            ParticipantRole = RelationshipRoleCodec.ToDatabase(participant.Role),
            Channel = "WHATSAPP",
            ExternalSubjectHash = phoneHmac,
            ConversationId = conversationId,
            AssuranceLevel = "TIER_4_PORTAL_FRESH",
            Status = "ACTIVE",
            PreparedEvidenceId = evidenceId,
            BoundEvidenceId = evidenceId,
            CreatedAt = now,
            BoundAt = now,
        };
        db.ChannelBindings.Add(binding);
        await db.SaveChangesAsync(cancellationToken);
        return new(tenantId, relationshipId, proof.ParticipantId, binding.BindingId, binding.AssuranceLevel);
    }

    private void VerifySignature(string rawBody, string signatureHeader)
    {
        if (!signatureHeader.StartsWith("sha256=", StringComparison.OrdinalIgnoreCase))
            throw new WhatsAppWebhookException(403, "WHATSAPP_SIGNATURE_INVALID");
        byte[] supplied;
        try
        {
            supplied = Convert.FromHexString(signatureHeader[7..]);
        }
        catch (FormatException)
        {
            throw new WhatsAppWebhookException(403, "WHATSAPP_SIGNATURE_INVALID");
        }
        var expected = HMACSHA256.HashData(_webhookSecret, Encoding.UTF8.GetBytes(rawBody));
        if (supplied.Length != expected.Length || !CryptographicOperations.FixedTimeEquals(supplied, expected))
            throw new WhatsAppWebhookException(403, "WHATSAPP_SIGNATURE_INVALID");
    }

    private (string Token, string TokenHash, DateTimeOffset ExpiresAt) IssueTenantToken(
        Guid tenantId,
        string phoneSubjectHash,
        DateTimeOffset now)
    {
        const string header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9";
        var expiresAt = now.AddMinutes(30);
        var payload = Base64Url(Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new
        {
            sub = tenantId,
            phone_subject_hash = phoneSubjectHash,
            iss = "waooaw-phone-identity",
            iat = now.ToUnixTimeSeconds(),
            exp = expiresAt.ToUnixTimeSeconds(),
        })));
        var signingInput = $"{header}.{payload}";
        var token = $"{signingInput}.{Base64Url(HMACSHA256.HashData(_tokenKey, Encoding.UTF8.GetBytes(signingInput)))}";
        return (token, Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(token))), expiresAt);
    }

    private static (string Stage, string Reply) Present(string text)
    {
        var normalized = text.Trim().ToUpperInvariant();
        if (normalized.Contains("STOP", StringComparison.Ordinal))
            return ("STOP", "Emergency Stop remains available in the secure relationship workspace. WhatsApp transport acceptance does not prove that every participant observed the Stop; delivery stays unresolved until durable acknowledgement is recorded.");
        if (normalized.Contains("EVIDENCE", StringComparison.Ordinal) || normalized.Contains("EXPORT", StringComparison.Ordinal))
            return ("EVIDENCE", "Open the secure relationship workspace to inspect the customer Evidence Window or request a time-limited canonical export. Evidence access follows your current relationship role.");
        if (normalized.Contains("TIMELINE", StringComparison.Ordinal) || normalized.Contains("STATUS", StringComparison.Ordinal))
            return ("CONTINUITY", "The secure relationship workspace shows the authoritative timeline, current trial and lifecycle state, authority version, actual and forecast cost, and participant delivery acknowledgements. A received WhatsApp message confirms transport acceptance only.");
        if (normalized.Contains("TRIAL", StringComparison.Ordinal))
            return ("TRIAL", "Your evaluation plan spans 14 calendar days. It uses local inference and cannot publish, spend, message third parties, or mutate providers.");
        if (normalized.Contains("CONFIG", StringComparison.Ordinal) || normalized.Contains("BUDGET", StringComparison.Ordinal))
            return ("CONFIGURE", "Review goals, measures, skills, budget, cadence, Decision Space, and stop conditions one item at a time.");
        if (normalized.Contains("NAME", StringComparison.Ordinal) || normalized.Contains("LOCATION", StringComparison.Ordinal))
            return ("CONTEXT", "I will confirm this context and ask at most one new decision-relevant question next.");
        if (normalized.Contains("?", StringComparison.Ordinal) || normalized.StartsWith("INTERVIEW", StringComparison.Ordinal))
            return ("INTERVIEW", "Your question is queued for a sourced answer that distinguishes fact, inference, recommendation, and limitation.");
        if (normalized.Contains("SKILL", StringComparison.Ordinal) || normalized.Contains("LIMIT", StringComparison.Ordinal))
            return ("DISCLOSURE", "I can present skills, limitations, authority needs, rights, evidence posture, trial boundaries, and indicative price before trial.");
        return ("DISCOVER", "Tell me the business outcome you need. I will compare lawful suitable professionals and explain why they fit.");
    }

    private static byte[] RequireKey(string value, string name) =>
        value.Length >= 32 ? Encoding.UTF8.GetBytes(value) : throw new InvalidOperationException($"WhatsApp:{name} must contain at least 32 characters.");
    private static string HmacHex(byte[] key, string value) =>
        Convert.ToHexStringLower(HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(value)));
    private static string Base64Url(byte[] value) => Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static void ValidateFreshPortalProof(PortalPhoneAttachProof proof)
    {
        if (proof.AuthenticationAssurance != "TIER_4_PORTAL_FRESH"
            || (DateTimeOffset.UtcNow - proof.AuthenticatedAt).Duration() > TimeSpan.FromMinutes(5))
            throw new ConstitutionalActionDeniedException("Phone attachment requires fresh Tier-4 portal proof.");
    }

    private static void ValidateMpin(string mpin)
    {
        if (mpin.Length is < 4 or > 8 || mpin.Any(value => !char.IsAsciiDigit(value)))
            throw new ArgumentException("MPIN must contain 4 to 8 digits.", nameof(mpin));
    }

    [GeneratedRegex("^\\+[1-9][0-9]{7,14}$", RegexOptions.CultureInvariant)]
    private static partial Regex E164();

    private sealed record WhatsAppInbound(string MessageId, long Timestamp, string From, string Text, string? RiskTier);
}