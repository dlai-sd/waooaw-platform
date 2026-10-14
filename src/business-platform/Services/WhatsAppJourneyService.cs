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
    public string VerifyToken { get; set; } = string.Empty;
    public bool CallbackAcceptanceEnabled { get; set; }
    public bool DispatchEnabled { get; set; }
    public int MaxBodyBytes { get; set; } = 1_048_576;
    public string[] ApprovedTemplates { get; set; } = [];
    public string CallbackHost { get; set; } = string.Empty;
}

public sealed record WhatsAppJourneyReceipt(
    string MessageId,
    string Status,
    string JourneyStage,
    string Reply,
    bool Replayed,
    string InternalTenantToken
);

public sealed record PortalPhoneAttachProof(
    Guid ParticipantId,
    string AuthenticationAssurance,
    DateTimeOffset AuthenticatedAt,
    Guid CorrelationId
);

public sealed record WhatsAppRelationshipResolution(
    Guid TenantId,
    Guid RelationshipId,
    Guid ParticipantId,
    Guid BindingId,
    string AuthenticationAssurance
);

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
    Guid CorrelationId
)
{
    public string? Environment { get; init; }
    public string? AppBindingDigest { get; init; }
    public string? PayloadDigest { get; init; }
}

public sealed class WhatsAppWebhookException(int statusCode, string code) : Exception(code)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}

public sealed partial class WhatsAppJourneyService
{
    private sealed record ProviderClaimAcquisition(Guid LeaseOwner, WhatsAppJourneyReceipt? Replay);

    private static readonly TimeSpan ProviderClaimLeaseDuration = TimeSpan.FromSeconds(60);
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IWhatsAppRegistrationEvidenceGateway _evidenceGateway;
    private readonly byte[] _webhookSecret;
    private readonly byte[] _tokenKey;
    private readonly IRelationshipConstitutionalGateway? _relationshipGateway;
    private readonly RelationshipEmergencyStopService? _emergencyStops;
    private readonly IDbContextFactory<ConversationStoreDbContext>? _conversationDbFactory;
    private readonly Wc120ConversationOptions? _conversationOptions;
    private readonly ConversationStopFence? _stopFence;
    private readonly ConversationService? _conversationService;
    private readonly WhatsAppOutboxService? _outboxService;
    private readonly CustomerEngagementWorkspaceService? _engagementWorkspace;

    public WhatsAppJourneyService(
        IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
        IWhatsAppRegistrationEvidenceGateway evidenceGateway,
        IOptions<WhatsAppJourneyOptions> options,
        IRelationshipConstitutionalGateway? relationshipGateway = null,
        RelationshipEmergencyStopService? emergencyStops = null,
        IDbContextFactory<ConversationStoreDbContext>? conversationDbFactory = null,
        IOptions<Wc120ConversationOptions>? conversationOptions = null,
        ConversationStopFence? stopFence = null,
        ConversationService? conversationService = null,
        WhatsAppOutboxService? outboxService = null,
        CustomerEngagementWorkspaceService? engagementWorkspace = null
    )
    {
        _dbFactory = dbFactory;
        _evidenceGateway = evidenceGateway;
        _webhookSecret = RequireKey(
            options.Value.WebhookSecret,
            nameof(options.Value.WebhookSecret)
        );
        _tokenKey = RequireKey(options.Value.TenantTokenKey, nameof(options.Value.TenantTokenKey));
        _relationshipGateway = relationshipGateway;
        _emergencyStops = emergencyStops;
        _conversationDbFactory = conversationDbFactory;
        _conversationOptions = conversationOptions?.Value;
        _stopFence = stopFence;
        _conversationService = conversationService;
        _outboxService = outboxService;
        _engagementWorkspace = engagementWorkspace;
    }

    public async Task<WhatsAppJourneyReceipt> ReceiveAsync(
        byte[] rawBody,
        string signatureHeader,
        DateTimeOffset receivedAt,
        CancellationToken cancellationToken
    )
    {
        if (
            _conversationOptions is not null
            && (
                !_conversationOptions.Enabled
                || string.IsNullOrWhiteSpace(_conversationOptions.Environment)
                || !IsLowerHexDigest(_conversationOptions.AppBindingDigest)
                || !IsLowerHexDigest(_conversationOptions.WabaBindingDigest)
                || !IsLowerHexDigest(_conversationOptions.RecipientBindingDigest)
            )
        )
            throw new WhatsAppWebhookException(503, "WHATSAPP_BINDING_CONFIGURATION_UNAVAILABLE");
        VerifySignature(rawBody, signatureHeader);
        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(rawBody);
        }
        catch (JsonException)
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
        }
        using (document)
        {
            var statuses = ParseProviderStatuses(document.RootElement, rawBody);
            if (statuses.Count > 0)
            {
                if (_outboxService is null)
                    throw new WhatsAppWebhookException(503, "WHATSAPP_STATUS_OWNER_UNAVAILABLE");
                foreach (var status in statuses)
                {
                    ValidateEnvironmentBinding(status.WabaId, status.RecipientId);
                    await _outboxService.RecordProviderStatusAsync(status.Event, cancellationToken);
                }
                return new(
                    statuses[0].Event.ProviderMessageId,
                    "ACCEPTED",
                    "DELIVERY_STATUS",
                    string.Empty,
                    false,
                    string.Empty
                );
            }
            var messages = ParseProviderMessages(document.RootElement);
            if (messages.Count > 0)
            {
                var conversationOptions =
                    _conversationOptions
                    ?? throw new WhatsAppWebhookException(
                        503,
                        "WHATSAPP_BINDING_CONFIGURATION_UNAVAILABLE"
                    );
                WhatsAppJourneyReceipt? firstReceipt = null;
                foreach (var message in messages)
                {
                    ValidateEnvironmentBinding(message.WabaId, message.RecipientId);
                    var receipt = await ReceiveVerifiedAsync(
                        new VerifiedPhoneIdentityProof(
                            message.MessageId,
                            HmacHex(_webhookSecret, message.From),
                            message.Text,
                            null,
                            "whatsapp-provider-callback",
                            "AAL1_CHANNEL",
                            message.SentAt,
                            receivedAt,
                            receivedAt.AddMinutes(5),
                            Guid.NewGuid()
                        )
                        {
                            Environment = conversationOptions.Environment,
                            AppBindingDigest = conversationOptions.AppBindingDigest,
                            PayloadDigest = Convert.ToHexStringLower(SHA256.HashData(rawBody)),
                        },
                        cancellationToken
                    );
                    firstReceipt ??= receipt;
                }
                return firstReceipt!;
            }
        }

        WhatsAppInbound inbound;
        try
        {
            inbound =
                JsonSerializer.Deserialize<WhatsAppInbound>(
                    rawBody,
                    new JsonSerializerOptions(JsonSerializerDefaults.Web)
                ) ?? throw new JsonException();
        }
        catch (JsonException)
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
        }
        if (
            string.IsNullOrWhiteSpace(inbound.MessageId)
            || string.IsNullOrWhiteSpace(inbound.Text)
            || string.IsNullOrWhiteSpace(inbound.From)
            || !E164().IsMatch(inbound.From)
        )
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
        }
        if (_conversationOptions is not null)
        {
            if (
                string.IsNullOrWhiteSpace(inbound.AppId)
                || string.IsNullOrWhiteSpace(inbound.WabaId)
                || string.IsNullOrWhiteSpace(inbound.RecipientId)
                || !FixedDigestEquals(_conversationOptions.AppBindingDigest, Sha256(inbound.AppId))
            )
                throw new WhatsAppWebhookException(403, "WHATSAPP_ENVIRONMENT_BINDING_INVALID");
            ValidateEnvironmentBinding(inbound.WabaId, inbound.RecipientId);
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
        return await ReceiveVerifiedAsync(
            new VerifiedPhoneIdentityProof(
                inbound.MessageId,
                phoneHmac,
                inbound.Text,
                inbound.RiskTier,
                "legacy-business-platform-adapter",
                "AAL1_CHANNEL",
                sentAt,
                receivedAt,
                receivedAt.AddMinutes(5),
                Guid.NewGuid()
            )
            {
                Environment = _conversationOptions?.Environment,
                AppBindingDigest = _conversationOptions?.AppBindingDigest,
                PayloadDigest = Convert.ToHexStringLower(SHA256.HashData(rawBody)),
            },
            cancellationToken
        );
    }

    public Task<WhatsAppJourneyReceipt> ReceiveAsync(
        string rawBody,
        string signatureHeader,
        DateTimeOffset receivedAt,
        CancellationToken cancellationToken
    ) =>
        ReceiveAsync(
            Encoding.UTF8.GetBytes(rawBody),
            signatureHeader,
            receivedAt,
            cancellationToken
        );

    public async Task<WhatsAppJourneyReceipt> ReceiveVerifiedAsync(
        VerifiedPhoneIdentityProof proof,
        CancellationToken cancellationToken
    )
    {
        var receivedAt = proof.VerifiedAt;
        if (
            string.IsNullOrWhiteSpace(proof.MessageId)
            || string.IsNullOrWhiteSpace(proof.PhoneSubjectHash)
            || string.IsNullOrWhiteSpace(proof.Text)
            || proof.ExpiresAt <= DateTimeOffset.UtcNow
            || (proof.VerifiedAt - proof.SentAt).Duration() > TimeSpan.FromMinutes(5)
        )
            throw new WhatsAppWebhookException(403, "PHONE_IDENTITY_PROOF_INVALID");

        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        if (_conversationDbFactory is null)
        {
            var existingReceipt = await db.WhatsAppMessageReceipts.SingleOrDefaultAsync(
                item => item.MessageId == proof.MessageId,
                cancellationToken
            );
            if (existingReceipt is not null && existingReceipt.ExpiresAt > receivedAt)
            {
                return new(
                    proof.MessageId,
                    "DUPLICATE",
                    "UNKNOWN",
                    "This message was already received.",
                    true,
                    string.Empty
                );
            }
            if (existingReceipt is not null)
            {
                db.WhatsAppMessageReceipts.Remove(existingReceipt);
                await db.SaveChangesAsync(cancellationToken);
            }
        }

        var contact = await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
            item => item.PhoneHmac == proof.PhoneSubjectHash,
            cancellationToken
        );
        if (contact is null)
        {
            if (_conversationOptions is not null)
                throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");
            contact = new WhatsAppJourneyContact
            {
                TenantId = Guid.NewGuid(),
                PhoneHmac = proof.PhoneSubjectHash,
                OptedInAt = receivedAt,
                LastInboundAt = receivedAt,
            };
            await _evidenceGateway.RecordAsync(
                contact.TenantId,
                proof.MessageId,
                proof.PhoneSubjectHash,
                receivedAt,
                cancellationToken
            );
            db.WhatsAppJourneyContacts.Add(contact);
        }
        contact.LastInboundAt = receivedAt;

        var bindings = await db
            .ChannelBindings.AsNoTracking()
            .Where(value =>
                value.TenantId == contact.TenantId
                && value.Channel == "WHATSAPP"
                && value.ExternalSubjectHash == proof.PhoneSubjectHash
                && value.Status == "ACTIVE"
            )
            .ToListAsync(cancellationToken);
        var binding = bindings.Count == 1 ? bindings[0] : null;
        if (_conversationOptions is not null && binding is null)
            throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");
        var attachedRelationship = binding is null
            ? null
            : await db
                .EmploymentRelationships.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == contact.TenantId
                        && value.RelationshipId == binding.RelationshipId,
                    cancellationToken
                );
        if (_conversationOptions is not null && attachedRelationship is null)
            throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");

        var claim = await ClaimProviderEventAsync(proof, cancellationToken);
        if (claim.Replay is not null)
            return claim.Replay;
        var locallyStopped =
            _stopFence is not null
            && binding is not null
            && await _stopFence.IsLatchedAsync(
                contact.TenantId,
                binding.RelationshipId,
                cancellationToken
            );

        var riskTier = proof.RiskTier?.Trim().ToUpperInvariant() ?? "TIER_1_LOW_RISK";
        var confirmation =
            proof.Text.Trim().Equals("YES", StringComparison.OrdinalIgnoreCase)
            || proof.Text.Trim().Equals("CONFIRM", StringComparison.OrdinalIgnoreCase);
        string status;
        string reply;
        if (
            attachedRelationship?.State == EmploymentRelationshipState.StoppedEmergency
            || (locallyStopped && !proof.Text.Contains("STOP", StringComparison.OrdinalIgnoreCase))
        )
        {
            contact.PendingMediumRiskConfirmation = false;
            contact.JourneyStage = "STOP";
            status = "STOPPED";
            reply =
                "This relationship is STOPPED_EMERGENCY. Consequential commands, configuration, contract, activation, and handoff remain blocked. Release is available only in the secure Tier-4 employer portal.";
        }
        else if (
            binding is not null
            && proof.Text.Contains("STOP", StringComparison.OrdinalIgnoreCase)
        )
        {
            if (_emergencyStops is null)
                throw new InvalidOperationException("Relationship Emergency Stop is unavailable.");
            await _emergencyStops.StopAsync(
                contact.TenantId,
                binding.RelationshipId,
                binding.ParticipantId,
                RelationshipRoleCodec.FromDatabase(binding.ParticipantRole),
                Guid.NewGuid(),
                cancellationToken
            );
            contact.PendingMediumRiskConfirmation = false;
            contact.JourneyStage = "STOP";
            status = "ACCEPTED";
            reply =
                "Emergency Stop confirmed for the relationship. All known evaluation and trial sessions were halted; later consequential commands remain blocked.";
        }
        else if (
            binding is not null
            && _engagementWorkspace is not null
            && IsEndSessionRequest(proof.Text)
        )
        {
            var ended = await _engagementWorkspace.EndChannelSessionAsync(
                contact.TenantId,
                binding.ParticipantId,
                binding.RelationshipId,
                binding.BindingId,
                proof.MessageId,
                proof.PayloadDigest ?? HmacHex(_webhookSecret, proof.MessageId),
                0,
                proof.CorrelationId,
                cancellationToken
            );
            contact.PendingMediumRiskConfirmation = false;
            contact.JourneyStage = "END_SESSION";
            status = "ACCEPTED";
            reply =
                $"WhatsApp session ended at {ended.EndedAt:O}. Your employment relationship and secure portal conversation remain active.";
        }
        else if (
            binding is not null
            && attachedRelationship is not null
            && _engagementWorkspace is not null
            && IsProgressRequest(proof.Text)
        )
        {
            var progress = await _engagementWorkspace.GetProgressAsync(
                contact.TenantId,
                binding.ParticipantId,
                binding.RelationshipId,
                cancellationToken
            );
            contact.PendingMediumRiskConfirmation = false;
            contact.JourneyStage = progress.LifecycleStage;
            status = "ACCEPTED";
            reply = PresentProgress(attachedRelationship, progress);
        }
        else if (riskTier == "TIER_4_CONSEQUENTIAL")
        {
            contact.PendingMediumRiskConfirmation = false;
            status = "SECURE_PORTAL_REQUIRED";
            reply =
                "Contracts, hiring, cancellation, and payment cannot be accepted or initiated in WhatsApp. Review the exact contract and current payment or activation status in the secure portal: /relationships. Payment details are entered only on Razorpay. You may choose Hire, Not now, Cancel, or Exit there.";
        }
        else if (riskTier == "TIER_3_HIGH_RISK")
        {
            status = "PORTAL_STEP_UP_REQUIRED";
            reply =
                "This high-risk action cannot be authorized by phone identity. Continue in the secure portal.";
        }
        else if (
            riskTier == "TIER_2_MEDIUM_RISK"
            && (!contact.PendingMediumRiskConfirmation || !confirmation)
        )
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

        if (
            status == "ACCEPTED"
            && contact.JourneyStage != "STOP"
            && contact.JourneyStage != "END_SESSION"
            && _conversationService is not null
            && binding is not null
        )
        {
            var canonicalIdempotency = DeterministicGuid(
                $"{proof.Environment}:{proof.AppBindingDigest}:{proof.MessageId}"
            );
            await _conversationService.SendAsync(
                contact.TenantId,
                binding.ParticipantId,
                binding.RelationshipId,
                canonicalIdempotency,
                new SendConversationMessageRequestV1(
                    "1.0",
                    canonicalIdempotency,
                    "WHATSAPP",
                    [new ConversationTextBlockV1("1.0", "TEXT", proof.Text.Trim(), "en-IN")],
                    "en-IN",
                    PayloadDigest: proof.PayloadDigest,
                    Channel: "WHATSAPP"
                ),
                cancellationToken
            );
        }

        var (tenantToken, tokenHash, tokenExpiresAt) = IssueTenantToken(
            contact.TenantId,
            proof.PhoneSubjectHash,
            receivedAt
        );
        if (_conversationDbFactory is null)
        {
            db.WhatsAppMessageReceipts.Add(
                new WhatsAppMessageReceipt
                {
                    MessageId = proof.MessageId,
                    TenantId = contact.TenantId,
                    SessionTokenHash = tokenHash,
                    SessionExpiresAt = tokenExpiresAt,
                    ReceivedAt = receivedAt,
                    ExpiresAt = receivedAt.AddHours(24),
                }
            );
        }
        await db.SaveChangesAsync(cancellationToken);
        var receipt = new WhatsAppJourneyReceipt(
            proof.MessageId,
            status,
            contact.JourneyStage,
            reply,
            false,
            tenantToken
        );
        await CompleteProviderEventAsync(proof, claim.LeaseOwner, receipt, cancellationToken);
        return receipt;
    }

    private async Task<ProviderClaimAcquisition> ClaimProviderEventAsync(
        VerifiedPhoneIdentityProof proof,
        CancellationToken cancellationToken
    )
    {
        if (
            _conversationDbFactory is null
            || string.IsNullOrWhiteSpace(proof.Environment)
            || string.IsNullOrWhiteSpace(proof.AppBindingDigest)
            || string.IsNullOrWhiteSpace(proof.PayloadDigest)
        )
            return new(Guid.Empty, null);

        var leaseOwner = Guid.NewGuid();
        await using var db = await _conversationDbFactory.CreateDbContextAsync(cancellationToken);
        var existing = await db.ProviderEventClaims.SingleOrDefaultAsync(
            value =>
                value.Environment == proof.Environment
                && value.Provider == "WHATSAPP"
                && value.AppBindingDigest == proof.AppBindingDigest
                && value.EventIdentity == proof.MessageId,
            cancellationToken
        );
        if (existing is not null)
        {
            var replay = ResolveProviderReplay(existing, proof.PayloadDigest);
            if (replay is not null)
                return new(Guid.Empty, replay);
            var acquired = await db
                .ProviderEventClaims.Where(value =>
                    value.ClaimId == existing.ClaimId
                    && value.State != "ACCEPTED"
                    && (value.LeaseExpiresAt == null || value.LeaseExpiresAt <= proof.VerifiedAt)
                )
                .ExecuteUpdateAsync(
                    updates =>
                        updates
                            .SetProperty(value => value.LeaseOwner, leaseOwner)
                            .SetProperty(
                                value => value.LeaseExpiresAt,
                                proof.VerifiedAt.Add(ProviderClaimLeaseDuration)
                            ),
                    cancellationToken
                );
            if (acquired == 0)
                throw new WhatsAppWebhookException(409, "WHATSAPP_EVENT_IN_PROGRESS");
            return new(leaseOwner, null);
        }

        db.ProviderEventClaims.Add(
            new ProviderEventClaim
            {
                Environment = proof.Environment,
                Provider = "WHATSAPP",
                AppBindingDigest = proof.AppBindingDigest,
                EventIdentity = proof.MessageId,
                PayloadDigest = proof.PayloadDigest,
                State = "CLAIMED",
                LeaseOwner = leaseOwner,
                LeaseExpiresAt = proof.VerifiedAt.Add(ProviderClaimLeaseDuration),
                ReceivedAt = proof.VerifiedAt,
            }
        );
        try
        {
            await db.SaveChangesAsync(cancellationToken);
            return new(leaseOwner, null);
        }
        catch (DbUpdateException)
        {
            db.ChangeTracker.Clear();
            existing = await db.ProviderEventClaims.SingleAsync(
                value =>
                    value.Environment == proof.Environment
                    && value.Provider == "WHATSAPP"
                    && value.AppBindingDigest == proof.AppBindingDigest
                    && value.EventIdentity == proof.MessageId,
                cancellationToken
            );
            var replay = ResolveProviderReplay(existing, proof.PayloadDigest);
            if (replay is not null)
                return new(Guid.Empty, replay);
            throw new WhatsAppWebhookException(409, "WHATSAPP_EVENT_IN_PROGRESS");
        }
    }

    private async Task CompleteProviderEventAsync(
        VerifiedPhoneIdentityProof proof,
        Guid leaseOwner,
        WhatsAppJourneyReceipt receipt,
        CancellationToken cancellationToken
    )
    {
        if (
            _conversationDbFactory is null
            || string.IsNullOrWhiteSpace(proof.Environment)
            || string.IsNullOrWhiteSpace(proof.AppBindingDigest)
        )
            return;
        await using var db = await _conversationDbFactory.CreateDbContextAsync(cancellationToken);
        var claim = await db.ProviderEventClaims.SingleAsync(
            value =>
                value.Environment == proof.Environment
                && value.Provider == "WHATSAPP"
                && value.AppBindingDigest == proof.AppBindingDigest
                && value.EventIdentity == proof.MessageId
                && value.LeaseOwner == leaseOwner,
            cancellationToken
        );
        claim.State = "ACCEPTED";
        claim.ResultJson = JsonSerializer.Serialize(
            receipt with
            {
                InternalTenantToken = string.Empty,
            }
        );
        claim.TerminalAt = DateTimeOffset.UtcNow;
        claim.ExpiresAt = claim.TerminalAt.Value.AddDays(30);
        claim.LeaseOwner = null;
        claim.LeaseExpiresAt = null;
        await db.SaveChangesAsync(cancellationToken);
    }

    private static WhatsAppJourneyReceipt? ResolveProviderReplay(
        ProviderEventClaim claim,
        string payloadDigest
    )
    {
        if (!string.Equals(claim.PayloadDigest, payloadDigest, StringComparison.Ordinal))
            throw new ConversationIdempotencyConflictException();
        if (claim.State == "ACCEPTED")
        {
            var receipt =
                JsonSerializer.Deserialize<WhatsAppJourneyReceipt>(claim.ResultJson)
                ?? throw new WhatsAppWebhookException(503, "WHATSAPP_REPLAY_RESULT_UNAVAILABLE");
            return receipt with { Replayed = true, InternalTenantToken = string.Empty };
        }
        return null;
    }

    public async Task SetProviderClaimHoldAsync(
        string provider,
        string eventIdentity,
        bool held,
        CancellationToken cancellationToken
    )
    {
        if (_conversationDbFactory is null || _conversationOptions is null)
            throw new InvalidOperationException("Provider claim owner is unavailable.");
        await using var db = await _conversationDbFactory.CreateDbContextAsync(cancellationToken);
        var claim =
            await db.ProviderEventClaims.SingleOrDefaultAsync(
                value =>
                    value.Environment == _conversationOptions.Environment
                    && value.Provider == provider
                    && value.AppBindingDigest == _conversationOptions.AppBindingDigest
                    && value.EventIdentity == eventIdentity,
                cancellationToken
            ) ?? throw new KeyNotFoundException("Provider claim was not found.");
        claim.LegalHold = held;
        await db.SaveChangesAsync(cancellationToken);
    }

    public async Task<int> PurgeExpiredProviderClaimsAsync(
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        if (_conversationDbFactory is null || _conversationOptions is null)
            return 0;
        await using var db = await _conversationDbFactory.CreateDbContextAsync(cancellationToken);
        var claims = await db
            .ProviderEventClaims.Where(value =>
                value.Environment == _conversationOptions.Environment
                && value.TerminalAt != null
                && value.ExpiresAt != null
                && value.ExpiresAt <= now
                && !value.LegalHold
            )
            .ToListAsync(cancellationToken);
        db.ProviderEventClaims.RemoveRange(claims);
        await db.SaveChangesAsync(cancellationToken);
        return claims.Count;
    }

    private sealed record ParsedProviderStatus(
        string WabaId,
        string RecipientId,
        WhatsAppProviderStatusEvent Event
    );

    private sealed record ParsedProviderMessage(
        string WabaId,
        string RecipientId,
        string MessageId,
        string From,
        string Text,
        DateTimeOffset SentAt
    );

    private List<ParsedProviderStatus> ParseProviderStatuses(JsonElement root, byte[] rawBody)
    {
        var statuses = new List<ParsedProviderStatus>();
        if (
            root.TryGetProperty("eventType", out var eventType)
            && string.Equals(eventType.GetString(), "status", StringComparison.OrdinalIgnoreCase)
            && TryGetRequiredString(root, "statusEventId", out var eventIdentity)
            && TryGetRequiredString(root, "messageId", out var providerMessageId)
            && TryGetRequiredString(root, "status", out var state)
            && TryGetRequiredString(root, "wabaId", out var wabaId)
            && TryGetRequiredString(root, "recipientId", out var recipientId)
            && root.TryGetProperty("timestamp", out var timestamp)
            && timestamp.TryGetInt64(out var unixTimestamp)
        )
        {
            statuses.Add(
                new(
                    wabaId,
                    recipientId,
                    new(
                        eventIdentity,
                        providerMessageId,
                        state,
                        FromProviderTimestamp(unixTimestamp),
                        Convert.ToHexStringLower(SHA256.HashData(rawBody))
                    )
                )
            );
            return statuses;
        }

        if (
            !root.TryGetProperty("entry", out var entries)
            || entries.ValueKind != JsonValueKind.Array
        )
            return statuses;
        foreach (var entry in entries.EnumerateArray())
        {
            if (
                !TryGetRequiredString(entry, "id", out wabaId)
                || !entry.TryGetProperty("changes", out var changes)
                || changes.ValueKind != JsonValueKind.Array
            )
                continue;
            foreach (var change in changes.EnumerateArray())
            {
                if (
                    !change.TryGetProperty("value", out var value)
                    || !value.TryGetProperty("metadata", out var metadata)
                    || !TryGetRequiredString(metadata, "phone_number_id", out recipientId)
                    || !value.TryGetProperty("statuses", out var providerStatuses)
                    || providerStatuses.ValueKind != JsonValueKind.Array
                )
                    continue;
                foreach (var providerStatus in providerStatuses.EnumerateArray())
                {
                    if (
                        !TryGetRequiredString(providerStatus, "id", out providerMessageId)
                        || !TryGetRequiredString(providerStatus, "status", out state)
                        || !TryGetRequiredString(providerStatus, "timestamp", out var timestampText)
                        || !long.TryParse(timestampText, out unixTimestamp)
                    )
                        throw new WhatsAppWebhookException(400, "WHATSAPP_STATUS_INVALID");
                    var statusIdentity = Sha256(
                        string.Join(
                            ':',
                            providerMessageId,
                            state,
                            timestampText,
                            providerStatus.GetRawText()
                        )
                    );
                    statuses.Add(
                        new(
                            wabaId,
                            recipientId,
                            new(
                                statusIdentity,
                                providerMessageId,
                                state,
                                FromProviderTimestamp(unixTimestamp),
                                Convert.ToHexStringLower(SHA256.HashData(rawBody))
                            )
                        )
                    );
                }
            }
        }
        return statuses;
    }

    private static List<ParsedProviderMessage> ParseProviderMessages(JsonElement root)
    {
        var messages = new List<ParsedProviderMessage>();
        if (
            !root.TryGetProperty("entry", out var entries)
            || entries.ValueKind != JsonValueKind.Array
        )
            return messages;
        foreach (var entry in entries.EnumerateArray())
        {
            if (
                !TryGetRequiredString(entry, "id", out var wabaId)
                || !entry.TryGetProperty("changes", out var changes)
                || changes.ValueKind != JsonValueKind.Array
            )
                continue;
            foreach (var change in changes.EnumerateArray())
            {
                if (
                    !change.TryGetProperty("value", out var value)
                    || !value.TryGetProperty("metadata", out var metadata)
                    || !TryGetRequiredString(metadata, "phone_number_id", out var recipientId)
                    || !value.TryGetProperty("messages", out var providerMessages)
                    || providerMessages.ValueKind != JsonValueKind.Array
                )
                    continue;
                foreach (var providerMessage in providerMessages.EnumerateArray())
                {
                    if (
                        !TryGetRequiredString(providerMessage, "id", out var messageId)
                        || !TryGetRequiredString(providerMessage, "from", out var from)
                        || !TryGetRequiredString(
                            providerMessage,
                            "timestamp",
                            out var timestampText
                        )
                        || !long.TryParse(timestampText, out var timestamp)
                        || !TryGetRequiredString(providerMessage, "type", out var messageType)
                        || !string.Equals(messageType, "text", StringComparison.Ordinal)
                        || !providerMessage.TryGetProperty("text", out var text)
                        || !TryGetRequiredString(text, "body", out var body)
                    )
                        throw new WhatsAppWebhookException(400, "WHATSAPP_MESSAGE_INVALID");
                    messages.Add(
                        new(
                            wabaId,
                            recipientId,
                            messageId,
                            from,
                            body,
                            FromProviderTimestamp(timestamp)
                        )
                    );
                }
            }
        }
        return messages;
    }

    private void ValidateEnvironmentBinding(string wabaId, string recipientId)
    {
        if (
            !FixedDigestEquals(_conversationOptions!.WabaBindingDigest, Sha256(wabaId))
            || !FixedDigestEquals(_conversationOptions.RecipientBindingDigest, Sha256(recipientId))
        )
            throw new WhatsAppWebhookException(403, "WHATSAPP_ENVIRONMENT_BINDING_INVALID");
    }

    private static DateTimeOffset FromProviderTimestamp(long timestamp)
    {
        try
        {
            return DateTimeOffset.FromUnixTimeSeconds(timestamp);
        }
        catch (ArgumentOutOfRangeException)
        {
            throw new WhatsAppWebhookException(400, "WHATSAPP_TIMESTAMP_INVALID");
        }
    }

    private static bool TryGetRequiredString(
        JsonElement element,
        string propertyName,
        out string value
    )
    {
        value = string.Empty;
        if (
            !element.TryGetProperty(propertyName, out var property)
            || property.ValueKind != JsonValueKind.String
        )
            return false;
        value = property.GetString() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(value);
    }

    public async Task EnrolMpinAsync(
        Guid tenantId,
        string phone,
        string mpin,
        PortalPhoneAttachProof proof,
        CancellationToken cancellationToken
    )
    {
        ValidateFreshPortalProof(proof);
        ValidateMpin(mpin);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var phoneHmac = HmacHex(_webhookSecret, phone);
        var contact =
            await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.PhoneHmac == phoneHmac,
                cancellationToken
            )
            ?? throw new ConstitutionalActionDeniedException(
                "Unknown phone identity cannot be attached from portal payload hints."
            );
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
        CancellationToken cancellationToken
    )
    {
        ValidateMpin(mpin);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var phoneHmac = HmacHex(_webhookSecret, phone);
        var contact =
            await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.PhoneHmac == phoneHmac,
                cancellationToken
            ) ?? throw new ConstitutionalActionDeniedException("Phone identity is not registered.");
        if (contact.MpinLockedUntil > attemptedAt)
            throw new WhatsAppWebhookException(423, "WHATSAPP_MPIN_LOCKED");
        if (contact.MpinHash is null)
            throw new ConstitutionalActionDeniedException("MPIN is not enrolled.");

        var suppliedHash = HmacHex(_tokenKey, $"{tenantId:D}:{mpin}");
        var valid = CryptographicOperations.FixedTimeEquals(
            Convert.FromHexString(contact.MpinHash),
            Convert.FromHexString(suppliedHash)
        );
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
        CancellationToken cancellationToken
    )
    {
        ValidateFreshPortalProof(proof);
        if (_relationshipGateway is null)
            throw new InvalidOperationException(
                "Relationship constitutional gateway is unavailable."
            );
        var phoneHmac = HmacHex(_webhookSecret, phone);
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        var contactExists = await db
            .WhatsAppJourneyContacts.AsNoTracking()
            .AnyAsync(
                value => value.TenantId == tenantId && value.PhoneHmac == phoneHmac,
                cancellationToken
            );
        if (!contactExists)
            throw new ConstitutionalActionDeniedException(
                "Unknown phone identity cannot attach to an existing relationship."
            );
        var relationship =
            await db
                .EmploymentRelationships.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                    cancellationToken
                )
            ?? throw new KeyNotFoundException("Employment relationship was not found.");
        var participant =
            await db
                .RelationshipParticipants.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.ParticipantId == proof.ParticipantId
                        && value.Status == "ACTIVE",
                    cancellationToken
                )
            ?? throw new ConstitutionalActionDeniedException(
                "Phone attachment requires an active same-tenant participant binding."
            );
        var existing = await db.ChannelBindings.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == proof.ParticipantId
                && value.Channel == "WHATSAPP"
                && value.Status == "ACTIVE",
            cancellationToken
        );
        if (existing is not null)
            return new(
                tenantId,
                relationshipId,
                proof.ParticipantId,
                existing.BindingId,
                existing.AssuranceLevel
            );

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
            cancellationToken
        );
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
        return new(
            tenantId,
            relationshipId,
            proof.ParticipantId,
            binding.BindingId,
            binding.AssuranceLevel
        );
    }

    private void VerifySignature(byte[] rawBody, string signatureHeader)
    {
        if (!signatureHeader.StartsWith("sha256=", StringComparison.Ordinal))
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
        var expected = HMACSHA256.HashData(_webhookSecret, rawBody);
        if (
            supplied.Length != expected.Length
            || !CryptographicOperations.FixedTimeEquals(supplied, expected)
        )
            throw new WhatsAppWebhookException(403, "WHATSAPP_SIGNATURE_INVALID");
    }

    private (string Token, string TokenHash, DateTimeOffset ExpiresAt) IssueTenantToken(
        Guid tenantId,
        string phoneSubjectHash,
        DateTimeOffset now
    )
    {
        const string header = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9";
        var expiresAt = now.AddMinutes(30);
        var payload = Base64Url(
            Encoding.UTF8.GetBytes(
                JsonSerializer.Serialize(
                    new
                    {
                        sub = tenantId,
                        phone_subject_hash = phoneSubjectHash,
                        iss = "waooaw-phone-identity",
                        iat = now.ToUnixTimeSeconds(),
                        exp = expiresAt.ToUnixTimeSeconds(),
                    }
                )
            )
        );
        var signingInput = $"{header}.{payload}";
        var token =
            $"{signingInput}.{Base64Url(HMACSHA256.HashData(_tokenKey, Encoding.UTF8.GetBytes(signingInput)))}";
        return (
            token,
            Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(token))),
            expiresAt
        );
    }

    private static (string Stage, string Reply) Present(string text)
    {
        var normalized = text.Trim().ToUpperInvariant();
        if (normalized.Contains("STOP", StringComparison.Ordinal))
            return (
                "STOP",
                "Emergency Stop remains available in the secure relationship workspace. WhatsApp transport acceptance does not prove that every participant observed the Stop; delivery stays unresolved until durable acknowledgement is recorded."
            );
        if (
            normalized.Contains("EVIDENCE", StringComparison.Ordinal)
            || normalized.Contains("EXPORT", StringComparison.Ordinal)
        )
            return (
                "EVIDENCE",
                "Open the secure relationship workspace to inspect the customer Evidence Window or request a time-limited canonical export. Evidence access follows your current relationship role."
            );
        if (
            normalized.Contains("TIMELINE", StringComparison.Ordinal)
            || normalized.Contains("STATUS", StringComparison.Ordinal)
        )
            return (
                "CONTINUITY",
                "The secure relationship workspace shows the authoritative timeline, current trial and lifecycle state, authority version, actual and forecast cost, and participant delivery acknowledgements. A received WhatsApp message confirms transport acceptance only."
            );
        if (normalized.Contains("TRIAL", StringComparison.Ordinal))
            return (
                "TRIAL",
                "Your evaluation plan spans 14 calendar days. It uses local inference and cannot publish, spend, message third parties, or mutate providers."
            );
        if (
            normalized.Contains("CONFIG", StringComparison.Ordinal)
            || normalized.Contains("BUDGET", StringComparison.Ordinal)
        )
            return (
                "CONFIGURE",
                "Review goals, measures, skills, budget, cadence, Decision Space, and stop conditions one item at a time."
            );
        if (
            normalized.Contains("NAME", StringComparison.Ordinal)
            || normalized.Contains("LOCATION", StringComparison.Ordinal)
        )
            return (
                "CONTEXT",
                "I will confirm this context and ask at most one new decision-relevant question next."
            );
        if (
            normalized.Contains("?", StringComparison.Ordinal)
            || normalized.StartsWith("INTERVIEW", StringComparison.Ordinal)
        )
            return (
                "INTERVIEW",
                "Your question is queued for a sourced answer that distinguishes fact, inference, recommendation, and limitation."
            );
        if (
            normalized.Contains("SKILL", StringComparison.Ordinal)
            || normalized.Contains("LIMIT", StringComparison.Ordinal)
        )
            return (
                "DISCLOSURE",
                "I can present skills, limitations, authority needs, rights, evidence posture, trial boundaries, and indicative price before trial."
            );
        return (
            "DISCOVER",
            "Tell me the business outcome you need. I will compare lawful suitable professionals and explain why they fit."
        );
    }

    private static bool IsProgressRequest(string text)
    {
        var normalized = text.Trim().ToUpperInvariant();
        return normalized.Contains("STATUS", StringComparison.Ordinal)
            || normalized.Contains("PROGRESS", StringComparison.Ordinal)
            || normalized.Contains("NEXT ACTION", StringComparison.Ordinal);
    }

    private static bool IsEndSessionRequest(string text)
    {
        var normalized = text.Trim().ToUpperInvariant();
        return normalized is "END SESSION" or "END WHATSAPP SESSION" or "LOG OUT WHATSAPP";
    }

    private static string PresentProgress(
        EmploymentRelationship relationship,
        CustomerEngagementProgress progress
    )
    {
        var item = progress.Items.FirstOrDefault();
        if (item is null)
            return "Current progress is unavailable. No success or completion is inferred. Try again or open the secure portal.";
        var nextAction = item.NextAction?.Label ?? "Wait for owner-confirmed progress.";
        return string.Join(
            "\n",
            $"{relationship.ProfessionalType} · {progress.Headline}",
            $"Lifecycle: {progress.LifecycleStage}",
            $"State: {item.State}",
            $"Delivery: {item.Truth.Delivery}",
            $"Processing: {item.Truth.Processing}",
            $"Evidence: {item.Truth.Evidence}",
            $"Commercial: {item.Truth.Commercial}",
            $"Outcome: {item.Truth.Outcome}",
            $"Next action: {nextAction}",
            $"Open the secure portal for {item.NextAction?.Focus.Label ?? "the current relationship workspace"}."
        );
    }

    private static byte[] RequireKey(string value, string name) =>
        value.Length >= 32
            ? Encoding.UTF8.GetBytes(value)
            : throw new InvalidOperationException(
                $"WhatsApp:{name} must contain at least 32 characters."
            );

    private static bool IsLowerHexDigest(string value) =>
        value.Length == 64
        && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');

    private static string HmacHex(byte[] key, string value) =>
        Convert.ToHexStringLower(HMACSHA256.HashData(key, Encoding.UTF8.GetBytes(value)));

    private static Guid DeterministicGuid(string value)
    {
        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(value));
        return new Guid(digest.AsSpan(0, 16));
    }

    private static string Sha256(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));

    private static bool FixedDigestEquals(string left, string right) =>
        left.Length == right.Length
        && CryptographicOperations.FixedTimeEquals(
            Encoding.ASCII.GetBytes(left),
            Encoding.ASCII.GetBytes(right)
        );

    private static string Base64Url(byte[] value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static void ValidateFreshPortalProof(PortalPhoneAttachProof proof)
    {
        if (
            proof.AuthenticationAssurance != "TIER_4_PORTAL_FRESH"
            || (DateTimeOffset.UtcNow - proof.AuthenticatedAt).Duration() > TimeSpan.FromMinutes(5)
        )
            throw new ConstitutionalActionDeniedException(
                "Phone attachment requires fresh Tier-4 portal proof."
            );
    }

    private static void ValidateMpin(string mpin)
    {
        if (mpin.Length is < 4 or > 8 || mpin.Any(value => !char.IsAsciiDigit(value)))
            throw new ArgumentException("MPIN must contain 4 to 8 digits.", nameof(mpin));
    }

    [GeneratedRegex("^\\+[1-9][0-9]{7,14}$", RegexOptions.CultureInvariant)]
    private static partial Regex E164();

    private sealed record WhatsAppInbound(
        string MessageId,
        long Timestamp,
        string From,
        string Text,
        string? RiskTier,
        string AppId,
        string WabaId,
        string RecipientId
    );
}
