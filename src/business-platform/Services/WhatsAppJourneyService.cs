// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §25.2 WC120-P2
// constitutional_basis: C-023, C-026, C-042, C-059, C-063

using System.Data;
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
    public bool VerificationEnabled { get; set; }
    public bool CallbackAcceptanceEnabled { get; set; }
    public bool DispatchEnabled { get; set; }
    public int MaxBodyBytes { get; set; } = 1_048_576;
    public string[] ApprovedTemplates { get; set; } = [];
    public WhatsAppTemplateProjection[] TemplateProjections { get; set; } = [];
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
    Guid CorrelationId,
    VerifiedCustomerActor? Actor = null,
    CustomerWorkspaceMembership? Membership = null
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
    public string? ReplyContextDigest { get; init; }
    public string? ProtectedDestination { get; init; }
    public bool UnsupportedContent { get; init; }
}

public sealed class WhatsAppWebhookException(int statusCode, string code) : Exception(code)
{
    public int StatusCode { get; } = statusCode;
    public string Code { get; } = code;
}

public sealed class WhatsAppChannelBindingUnavailableException(string message) : Exception(message);

public sealed partial class WhatsAppJourneyService
{
    private sealed record ProviderClaimAcquisition(Guid LeaseOwner, WhatsAppJourneyReceipt? Replay);

    private sealed class ConversationRequestAnswerResult
    {
        public Guid QuestionId { get; init; }
        public string Decision { get; init; } = string.Empty;
        public string ResultStatus { get; init; } = string.Empty;
    }

    private const int MaximumProviderTextLength = 4096;
    private const string UnsupportedRelationshipContentNotice =
        "I can't read attachments in WhatsApp. Please send your question as text.";
    private static readonly TimeSpan ProviderClaimLeaseDuration = TimeSpan.FromSeconds(60);
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _dbFactory;
    private readonly IWhatsAppRegistrationEvidenceGateway _evidenceGateway;
    private readonly WhatsAppJourneyOptions _identityOptions;
    private byte[] _webhookSecret =>
        RequireKey(_identityOptions.WebhookSecret, nameof(WhatsAppJourneyOptions.WebhookSecret));
    private byte[] _tokenKey =>
        RequireKey(_identityOptions.TenantTokenKey, nameof(WhatsAppJourneyOptions.TenantTokenKey));
    private readonly IRelationshipConstitutionalGateway? _relationshipGateway;
    private readonly RelationshipEmergencyStopService? _emergencyStops;
    private readonly IDbContextFactory<ConversationStoreDbContext>? _conversationDbFactory;
    private readonly Wc120ConversationOptions? _conversationOptions;
    private readonly ConversationStopFence? _stopFence;
    private readonly ConversationService? _conversationService;
    private readonly ConversationOutboundContributionService? _outboundContributions;
    private readonly WhatsAppOutboxService? _outboxService;
    private readonly CustomerEngagementWorkspaceService? _engagementWorkspace;
    private readonly IWhatsAppCapabilityGate? _capabilityGate;
    private readonly IWhatsAppWebhookCredentials? _webhookCredentials;
    private readonly WhatsAppGuestSessionService? _guestSessions;
    private readonly WhatsAppTenantExecutionScope? _tenantExecutionScope;
    private readonly IdentitySecurityEventService? _securityEvents;
    private readonly TimeProvider _clock;
    private readonly WhatsAppTrafficBudget? _trafficBudget;
    private readonly IdentityService? _identity;
    private readonly WhatsAppRelationshipRouting? _relationshipRouting;

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
        CustomerEngagementWorkspaceService? engagementWorkspace = null,
        IWhatsAppCapabilityGate? capabilityGate = null,
        IWhatsAppWebhookCredentials? webhookCredentials = null,
        WhatsAppGuestSessionService? guestSessions = null,
        ConversationOutboundContributionService? outboundContributions = null,
        TimeProvider? clock = null,
        WhatsAppTenantExecutionScope? tenantExecutionScope = null,
        IdentitySecurityEventService? securityEvents = null,
        WhatsAppTrafficBudget? trafficBudget = null,
        IdentityService? identity = null,
        WhatsAppRelationshipRouting? relationshipRouting = null
    )
    {
        _dbFactory = dbFactory;
        _evidenceGateway = evidenceGateway;
        _identityOptions = options.Value;
        _relationshipGateway = relationshipGateway;
        _emergencyStops = emergencyStops;
        _conversationDbFactory = conversationDbFactory;
        _conversationOptions = conversationOptions?.Value;
        _stopFence = stopFence;
        _conversationService = conversationService;
        _outboundContributions = outboundContributions;
        _outboxService = outboxService;
        _engagementWorkspace = engagementWorkspace;
        _capabilityGate = capabilityGate;
        _webhookCredentials = webhookCredentials;
        _guestSessions = guestSessions;
        _tenantExecutionScope = tenantExecutionScope;
        _securityEvents = securityEvents;
        _clock = clock ?? TimeProvider.System;
        _trafficBudget =
            trafficBudget
            ?? (
                conversationDbFactory is not null && capabilityGate is not null
                    ? new WhatsAppTrafficBudget(
                        conversationDbFactory,
                        capabilityGate,
                        _clock,
                        tenantExecutionScope
                    )
                    : null
            );
        _identity = identity;
        _relationshipRouting = relationshipRouting;
    }

    public async Task<WhatsAppJourneyReceipt> ReceiveAsync(
        byte[] rawBody,
        string signatureHeader,
        DateTimeOffset receivedAt,
        CancellationToken cancellationToken
    )
    {
        await ValidateSignatureAsync(rawBody, signatureHeader, cancellationToken);
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
            if (document.RootElement.ValueKind != JsonValueKind.Object)
                throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
            RejectDuplicateProperties(document.RootElement);
            if (
                _webhookCredentials is not null
                && (
                    !document.RootElement.TryGetProperty("object", out var objectType)
                    || objectType.ValueKind != JsonValueKind.String
                    || objectType.GetString() != "whatsapp_business_account"
                    || !document.RootElement.TryGetProperty("entry", out var entries)
                    || entries.ValueKind != JsonValueKind.Array
                    || entries.GetArrayLength() == 0
                    || document.RootElement.TryGetProperty("eventType", out _)
                )
            )
                throw new WhatsAppWebhookException(400, "WHATSAPP_PROVIDER_ENVELOPE_REQUIRED");
            var statuses = ParseProviderStatuses(document.RootElement);
            var messages = ParseProviderMessages(document.RootElement);
            foreach (var status in statuses)
                ValidateEnvironmentBinding(status.WabaId, status.RecipientId);
            foreach (var message in messages)
                ValidateEnvironmentBinding(message.WabaId, message.RecipientId);
            var senderBinding =
                _webhookCredentials is not null
                && (
                    messages.Count > 0 || statuses.Any(value => value.SenderPhoneNumber is not null)
                )
                    ? await _webhookCredentials.ReadSenderBindingAsync(cancellationToken)
                    : null;
            var publicAdmission =
                senderBinding is not null
                && _capabilityGate?.RequireActive(receivedAt).AllowPublicAdmission == true;
            string? phoneSubjectKey = null;
            if (senderBinding is not null)
            {
                foreach (var message in messages)
                    if (
                        senderBinding.WabaId != message.WabaId
                        || senderBinding.PhoneNumberId != message.RecipientId
                        || Sha256(senderBinding.AppId) != _conversationOptions!.AppBindingDigest
                        || (
                            !publicAdmission
                            && (
                                message.From != senderBinding.RecipientPhoneNumber
                                && message.From != senderBinding.RecipientPhoneNumber.TrimStart('+')
                            )
                        )
                    )
                        throw new WhatsAppWebhookException(403, "WHATSAPP_SENDER_NOT_BOUND");
                if (publicAdmission)
                    phoneSubjectKey = await _webhookCredentials!.ReadPhoneSubjectKeyAsync(
                        cancellationToken
                    );
            }
            if (statuses.Count > 0)
            {
                if (_outboxService is null)
                    throw new WhatsAppWebhookException(503, "WHATSAPP_STATUS_OWNER_UNAVAILABLE");
                foreach (var status in statuses)
                {
                    var statusEvent = status.Event;
                    if (senderBinding is not null && status.SenderPhoneNumber is not null)
                    {
                        if (
                            senderBinding.WabaId != status.WabaId
                            || senderBinding.PhoneNumberId != status.RecipientId
                            || Sha256(senderBinding.AppId) != _conversationOptions!.AppBindingDigest
                        )
                            throw new WhatsAppWebhookException(403, "WHATSAPP_SENDER_NOT_BOUND");
                        var sender = NormalizePublicSender(status.SenderPhoneNumber);
                        if (
                            !publicAdmission
                            && sender != NormalizePublicSender(senderBinding.RecipientPhoneNumber)
                        )
                            throw new WhatsAppWebhookException(403, "WHATSAPP_SENDER_NOT_BOUND");
                        statusEvent = statusEvent with
                        {
                            SenderBindingDigest = publicAdmission
                                ? HmacHex(
                                    Encoding.UTF8.GetBytes(
                                        phoneSubjectKey
                                            ?? throw new WhatsAppCapabilityUnavailableException(
                                                "PHONE_SUBJECT_KEY_UNAVAILABLE"
                                            )
                                    ),
                                    sender
                                )
                                : senderBinding.RecipientBindingDigest,
                        };
                    }
                    await _outboxService.RecordProviderStatusAsync(statusEvent, cancellationToken);
                }
            }
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
                    var publicSender = publicAdmission
                        ? NormalizePublicSender(message.From)
                        : message.From;
                    var phoneSubjectHash =
                        senderBinding is null ? HmacHex(_webhookSecret, publicSender)
                        : publicAdmission
                            ? HmacHex(
                                Encoding.UTF8.GetBytes(
                                    phoneSubjectKey
                                        ?? throw new WhatsAppCapabilityUnavailableException(
                                            "PHONE_SUBJECT_KEY_UNAVAILABLE"
                                        )
                                ),
                                publicSender
                            )
                        : senderBinding.RecipientBindingDigest;
                    var proof = new VerifiedPhoneIdentityProof(
                        message.MessageId,
                        phoneSubjectHash,
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
                        PayloadDigest = message.PayloadDigest,
                        ReplyContextDigest = message.ReplyContextDigest,
                        UnsupportedContent = message.UnsupportedContent,
                        ProtectedDestination = publicAdmission
                            ? WhatsAppPhoneDestinationProtector.Protect(
                                phoneSubjectKey
                                    ?? throw new WhatsAppCapabilityUnavailableException(
                                        "PHONE_SUBJECT_KEY_UNAVAILABLE"
                                    ),
                                publicSender,
                                phoneSubjectHash
                            )
                            : null,
                    };
                    Task<WhatsAppJourneyReceipt> Receive(CancellationToken token) =>
                        ReceiveVerifiedCoreAsync(
                            proof,
                            senderBinding is not null ? NormalizePublicSender(message.From) : null,
                            token
                        );
                    var safetyControl =
                        IsRecipientStopRequest(proof.Text)
                        || IsRelationshipEmergencyStopRequest(proof.Text);
                    if (
                        senderBinding is not null
                        && _tenantExecutionScope is not null
                        && _relationshipRouting is null
                    )
                        throw new WhatsAppWebhookException(
                            503,
                            "WHATSAPP_ROUTING_OWNER_UNAVAILABLE"
                        );
                    var receipt =
                        senderBinding is not null && _relationshipRouting is not null
                            ? safetyControl
                                ? await ReceiveSignedSafetyEventAsync(proof, cancellationToken)
                                : await _relationshipRouting.ExecuteSignedIngressAsync(
                                    proof.PhoneSubjectHash,
                                    Receive,
                                    cancellationToken
                                )
                            : await Receive(cancellationToken);
                    firstReceipt ??= receipt;
                }
                return firstReceipt!;
            }
            if (statuses.Count > 0)
                return new(
                    statuses[0].Event.ProviderMessageId,
                    "ACCEPTED",
                    "DELIVERY_STATUS",
                    string.Empty,
                    false,
                    string.Empty
                );
        }

        if (_webhookCredentials is not null)
            throw new WhatsAppWebhookException(400, "WHATSAPP_PROVIDER_ENVELOPE_REQUIRED");
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

    public async Task ValidateSignatureAsync(
        byte[] rawBody,
        string signatureHeader,
        CancellationToken cancellationToken
    )
    {
        var signatureKey = _webhookCredentials is null
            ? null
            : RequireKey(
                await _webhookCredentials.ReadAppSecretAsync(cancellationToken),
                "ProviderAppSecret"
            );
        VerifySignature(rawBody, signatureHeader, signatureKey);
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

    public Task<WhatsAppJourneyReceipt> ReceiveVerifiedAsync(
        VerifiedPhoneIdentityProof proof,
        CancellationToken cancellationToken
    ) => ReceiveVerifiedCoreAsync(proof, null, cancellationToken);

    private async Task<WhatsAppJourneyReceipt> ReceiveVerifiedCoreAsync(
        VerifiedPhoneIdentityProof proof,
        string? verifiedPhoneNumber,
        CancellationToken cancellationToken
    )
    {
        var receivedAt = proof.VerifiedAt;
        if (
            string.IsNullOrWhiteSpace(proof.MessageId)
            || string.IsNullOrWhiteSpace(proof.PhoneSubjectHash)
            || !proof.UnsupportedContent && string.IsNullOrWhiteSpace(proof.Text)
            || proof.ExpiresAt <= _clock.GetUtcNow()
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
        if (
            contact is null
            && _tenantExecutionScope?.CurrentTenantId is { } selectedTenant
            && selectedTenant != _tenantExecutionScope.ServiceTenantId
        )
            throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");
        if (contact is null && _conversationOptions is not null && _guestSessions is not null)
            return await ReceiveGuestEventAsync(proof, verifiedPhoneNumber, cancellationToken);
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
        if (
            _tenantExecutionScope?.ServiceTenantId is { } serviceTenant
            && serviceTenant != contact.TenantId
        )
        {
            var route = _tenantExecutionScope.RequireConfirmedRelationshipRoute();
            if (route.TenantId != contact.TenantId || route.SenderHash != proof.PhoneSubjectHash)
                throw new WhatsAppWebhookException(403, "WHATSAPP_IDENTITY_NOT_BOUND");
        }
        else
            _capabilityGate?.RequireRecipient(
                contact.TenantId,
                proof.PhoneSubjectHash,
                _clock.GetUtcNow()
            );
        contact.LastInboundAt = receivedAt;

        var bindings = await db
            .ChannelBindings.AsNoTracking()
            .Where(value =>
                value.TenantId == contact.TenantId
                && value.Channel == "WHATSAPP"
                && value.ExternalSubjectHash == proof.PhoneSubjectHash
                && value.Status == "ACTIVE"
            )
            .Take(2)
            .ToListAsync(cancellationToken);
        var binding = bindings.Count == 1 ? bindings[0] : null;
        if (
            _tenantExecutionScope?.ServiceTenantId is { } ownerTenant
            && ownerTenant != contact.TenantId
        )
        {
            var route = _tenantExecutionScope.RequireConfirmedRelationshipRoute();
            if (
                binding is null
                || binding.BindingId != route.BindingId
                || binding.RelationshipId != route.RelationshipId
                || binding.ParticipantId != route.ParticipantId
                || binding.ParticipantRole != route.ParticipantRole
                || binding.ConversationId != route.ConversationId.ToString("D")
            )
                throw new WhatsAppWebhookException(403, "WHATSAPP_IDENTITY_NOT_BOUND");
        }
        if (_conversationOptions is not null && bindings.Count > 1)
        {
            var events =
                _securityEvents
                ?? throw new InvalidOperationException(
                    "WhatsApp binding ambiguity requires identity security event recording."
                );
            await events.RecordAsync(
                new IdentitySecurityEventInput(
                    proof.CorrelationId,
                    $"whatsapp-binding:{Sha256($"{proof.Environment}:{proof.AppBindingDigest}:{proof.MessageId}")}",
                    "AUTHORIZATION_DENIAL",
                    "UNKNOWN",
                    "DENIED",
                    "WHATSAPP_BINDING_AMBIGUOUS",
                    "UNKNOWN",
                    "BUSINESS_PLATFORM"
                ),
                cancellationToken
            );
        }
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

        if (
            _conversationOptions is not null
            && WhatsAppAccountLinkInstruction.IsInstruction(proof.Text)
        )
        {
            if (
                contact.OptedOutAt is not null
                || attachedRelationship?.State == EmploymentRelationshipState.StoppedEmergency
                || (
                    _stopFence is not null
                    && binding is not null
                    && await _stopFence.IsLatchedAsync(
                        contact.TenantId,
                        binding.RelationshipId,
                        cancellationToken
                    )
                )
            )
                throw new WhatsAppWebhookException(403, "WHATSAPP_CHANNEL_STOPPED");
            return await ReceiveGuestEventAsync(proof, verifiedPhoneNumber, cancellationToken);
        }

        if (
            _conversationOptions is not null
            && binding is not null
            && !IsRecipientStopRequest(proof.Text)
        )
        {
            var boundRole = RelationshipRoleCodec.FromDatabase(binding.ParticipantRole);
            if (
                !await db
                    .RelationshipParticipants.AsNoTracking()
                    .AnyAsync(
                        participant =>
                            participant.TenantId == contact.TenantId
                            && participant.RelationshipId == binding.RelationshipId
                            && participant.ParticipantId == binding.ParticipantId
                            && participant.Status == "ACTIVE"
                            && participant.Role == boundRole,
                        cancellationToken
                    )
            )
                throw new WhatsAppWebhookException(404, "WHATSAPP_IDENTITY_NOT_BOUND");
        }

        var claim = await ClaimProviderEventAsync(proof, cancellationToken);
        if (claim.Replay is not null)
            return claim.Replay;
        try
        {
            if (
                binding is not null
                && attachedRelationship is not null
                && contact.OptedOutAt is null
                && !proof.UnsupportedContent
                && !IsRecipientStopRequest(proof.Text)
                && !IsRelationshipEmergencyStopRequest(proof.Text)
            )
            {
                var clarificationReceipt = await TryRecordClarificationResponseAsync(
                    proof,
                    claim.LeaseOwner,
                    contact.TenantId,
                    binding,
                    attachedRelationship.StateVersion,
                    cancellationToken
                );
                if (clarificationReceipt is not null)
                    return clarificationReceipt;
            }

            var journeyReplyKey = DeterministicGuid(
                $"{proof.Environment}:{proof.AppBindingDigest}:{proof.MessageId}:JOURNEY_REPLY"
            );
            if (binding is not null && _outboundContributions is not null)
            {
                var recovered = await _outboundContributions.RecoverJourneyReplyAsync(
                    contact.TenantId,
                    binding.ParticipantId,
                    binding.RelationshipId,
                    journeyReplyKey,
                    cancellationToken
                );
                if (recovered is not null)
                {
                    var previous = new WhatsAppJourneyReceipt(
                        proof.MessageId,
                        recovered.Value.Receipt.JourneyStatus!,
                        recovered.Value.Receipt.JourneyStage!,
                        recovered.Value.Text,
                        true,
                        string.Empty
                    );
                    await CompleteProviderEventAsync(
                        proof,
                        claim.LeaseOwner,
                        previous,
                        cancellationToken
                    );
                    return previous;
                }
            }
            var locallyStopped =
                _stopFence is not null
                && binding is not null
                && await _stopFence.IsLatchedAsync(
                    contact.TenantId,
                    binding.RelationshipId,
                    cancellationToken
                );
            var inboundLimit = WhatsAppGuestTrafficNotice.None;
            if (
                _conversationOptions is not null
                && _capabilityGate is not null
                && binding is not null
                && !locallyStopped
                && contact.OptedOutAt is null
                && attachedRelationship?.State != EmploymentRelationshipState.StoppedEmergency
                && !IsRecipientStopRequest(proof.Text)
                && !IsRelationshipEmergencyStopRequest(proof.Text)
            )
            {
                var traffic =
                    _trafficBudget
                    ?? throw new WhatsAppWebhookException(
                        503,
                        "WHATSAPP_TRAFFIC_BUDGET_UNAVAILABLE"
                    );
                inboundLimit = await traffic.ReserveRelationshipInboundAsync(
                    contact.TenantId,
                    binding.RelationshipId,
                    binding.BindingId,
                    proof.PhoneSubjectHash,
                    proof.MessageId,
                    cancellationToken
                );
            }

            if (
                !locallyStopped
                && contact.OptedOutAt is null
                && attachedRelationship?.State != EmploymentRelationshipState.StoppedEmergency
                && binding is not null
                && verifiedPhoneNumber is not null
                && proof.ProtectedDestination is not null
                && !IsRecipientStopRequest(proof.Text)
                && !IsRelationshipEmergencyStopRequest(proof.Text)
                && !IsEndSessionRequest(proof.Text)
                && (
                    contact.DestinationVerifiedAt is null
                    || proof.SentAt > contact.DestinationVerifiedAt
                )
            )
            {
                contact.ProtectedDestination = proof.ProtectedDestination;
                contact.DestinationVerifiedAt = proof.SentAt;
            }

            var riskTier = proof.RiskTier?.Trim().ToUpperInvariant() ?? "TIER_1_LOW_RISK";
            var confirmation =
                proof.Text.Trim().Equals("YES", StringComparison.OrdinalIgnoreCase)
                || proof.Text.Trim().Equals("CONFIRM", StringComparison.OrdinalIgnoreCase);
            string status;
            string reply;
            var journeyReply = false;
            if (IsRecipientStopRequest(proof.Text))
            {
                contact.OptedOutAt ??= receivedAt;
                contact.PendingMediumRiskConfirmation = false;
                contact.JourneyStage = "STOP";
                status = "STOPPED";
                reply = string.Empty;
            }
            else if (binding is not null && IsRelationshipEmergencyStopRequest(proof.Text))
            {
                if (_emergencyStops is null)
                    throw new InvalidOperationException(
                        "Relationship Emergency Stop is unavailable."
                    );
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
                    "Emergency Stop is recorded and the relationship is blocked. Session halt confirmation may still be pending.";
            }
            else if (contact.OptedOutAt is not null)
            {
                contact.PendingMediumRiskConfirmation = false;
                contact.JourneyStage = "STOP";
                status = "STOPPED";
                reply = string.Empty;
            }
            else if (
                attachedRelationship?.State == EmploymentRelationshipState.StoppedEmergency
                || (locallyStopped && !IsRelationshipEmergencyStopRequest(proof.Text))
            )
            {
                contact.PendingMediumRiskConfirmation = false;
                contact.JourneyStage = "STOP";
                status = "STOPPED";
                reply =
                    "This relationship is STOPPED_EMERGENCY. Consequential commands, configuration, contract, activation, and handoff remain blocked. Release is available only in the secure Tier-4 employer portal.";
            }
            else if (inboundLimit != WhatsAppGuestTrafficNotice.None)
            {
                contact.PendingMediumRiskConfirmation = false;
                status = "TRAFFIC_LIMIT";
                reply =
                    inboundLimit == WhatsAppGuestTrafficNotice.GlobalRateLimit
                        ? "This channel is temporarily at its message capacity. Please try again in a minute."
                        : "This channel has reached its current message capacity. Please try again later.";
                journeyReply = true;
            }
            else if (proof.UnsupportedContent)
            {
                contact.PendingMediumRiskConfirmation = false;
                status = "UNSUPPORTED_CONTENT";
                reply = binding is null
                    ? WhatsAppGuestTrafficBudget.UnsupportedContentNotice
                    : UnsupportedRelationshipContentNotice;
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
                journeyReply = true;
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
                && !proof.UnsupportedContent
                && !journeyReply
                && _conversationService is not null
                && binding is not null
            )
            {
                var canonicalIdempotency = DeterministicGuid(
                    $"{proof.Environment}:{proof.AppBindingDigest}:{proof.MessageId}"
                );
                string? skillId;
                try
                {
                    skillId = await _conversationService.ResolveChannelSkillAsync(
                        contact.TenantId,
                        binding.ParticipantId,
                        binding.RelationshipId,
                        cancellationToken,
                        canonicalIdempotency
                    );
                }
                catch (ConversationContextConflictException exception)
                    when (exception.Code == "CONVERSATION_SKILL_SELECTION_REQUIRED"
                        && _outboundContributions is not null
                    )
                {
                    skillId = null;
                    status = "CONTEXT_SELECTION_REQUIRED";
                    reply =
                        "I need the current task before I can continue. "
                        + "Open this relationship in the secure portal and choose the skill or task, "
                        + "then return here. No professional work was started.";
                    journeyReply = true;
                }
                if (skillId is not null)
                {
                    var submitted = await _conversationService.SendAsync(
                        contact.TenantId,
                        binding.ParticipantId,
                        binding.RelationshipId,
                        canonicalIdempotency,
                        new SendConversationMessageRequestV1(
                            "1.0",
                            canonicalIdempotency,
                            skillId,
                            [
                                new ConversationTextBlockV1(
                                    "1.0",
                                    "TEXT",
                                    proof.Text.Trim(),
                                    "en-IN"
                                ),
                            ],
                            "en-IN",
                            PayloadDigest: proof.PayloadDigest,
                            Channel: "WHATSAPP"
                        ),
                        cancellationToken,
                        new ConversationChannelOrigin(binding.BindingId, proof.PhoneSubjectHash)
                    );
                    if (submitted.Value.Message.DeliveryState == "UNRESOLVED")
                    {
                        status = "RECONCILIATION_REQUIRED";
                        reply =
                            "The earlier request has an unconfirmed outcome. No new professional work was started. "
                            + "Open this relationship in the secure portal to reconcile its recorded outcome.";
                        journeyReply = true;
                    }
                    else if (
                        submitted.Value.Message.ProcessingState == "FAILED"
                        || submitted.Value.Message.DeliveryState == "FAILED"
                    )
                    {
                        // A webhook replay cannot mint fresh execution authority, even for a known failure.
                        status = "SECURE_PORTAL_REQUIRED";
                        reply =
                            "The earlier request did not complete. No new professional work was started. "
                            + "Review the recorded request in the secure portal before requesting another action.";
                        journeyReply = true;
                    }
                }
            }
            if (
                (
                    status == "UNSUPPORTED_CONTENT"
                    || journeyReply
                    || status
                        is "SECURE_PORTAL_REQUIRED"
                            or "PORTAL_STEP_UP_REQUIRED"
                            or "CONFIRMATION_REQUIRED"
                )
                && _outboundContributions is not null
                && binding is not null
                && contact.OptedOutAt is null
            )
            {
                await db.SaveChangesAsync(cancellationToken);
                await _outboundContributions.CommitAsync(
                    contact.TenantId,
                    binding.ParticipantId,
                    binding.RelationshipId,
                    new OutboundConversationContributionV1(
                        "SYSTEM",
                        "TEXT",
                        status == "ACCEPTED" ? "INFORM" : "DISCLOSE_LIMITATION",
                        reply,
                        "INDUCTION",
                        null,
                        "WHATSAPP",
                        journeyReplyKey,
                        $"whatsapp-journey:{journeyReplyKey:D}",
                        Sha256(reply),
                        true,
                        new WhatsAppOutboundEligibility(
                            contact.OptedInAt <= receivedAt,
                            contact.OptedOutAt is not null,
                            false,
                            receivedAt,
                            "CUSTOMER_REQUEST",
                            proof.PhoneSubjectHash,
                            null,
                            null,
                            null,
                            null,
                            false
                        ),
                        JourneyStatus: status,
                        JourneyStage: contact.JourneyStage
                    ),
                    receivedAt,
                    cancellationToken
                );
            }
            else if (
                (
                    status == "UNSUPPORTED_CONTENT"
                    || journeyReply
                    || status
                        is "SECURE_PORTAL_REQUIRED"
                            or "PORTAL_STEP_UP_REQUIRED"
                            or "CONFIRMATION_REQUIRED"
                )
                && binding is not null
                && contact.OptedOutAt is null
            )
            {
                throw new InvalidOperationException(
                    "Conversation outbound contributions are unavailable for WhatsApp journey replies."
                );
            }

            var tenantToken = string.Empty;
            if (_conversationDbFactory is null && contact.OptedOutAt is null)
            {
                var issued = IssueTenantToken(contact.TenantId, proof.PhoneSubjectHash, receivedAt);
                tenantToken = issued.Token;
                db.WhatsAppMessageReceipts.Add(
                    new WhatsAppMessageReceipt
                    {
                        MessageId = proof.MessageId,
                        TenantId = contact.TenantId,
                        ContactId = contact.ContactId,
                        SessionTokenHash = issued.TokenHash,
                        SessionExpiresAt = issued.ExpiresAt,
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
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            await ReleaseProviderEventClaimAsync(proof, claim.LeaseOwner, cancellationToken);
            throw;
        }
    }

    private async Task<WhatsAppJourneyReceipt?> TryRecordClarificationResponseAsync(
        VerifiedPhoneIdentityProof proof,
        Guid leaseOwner,
        Guid tenantId,
        ChannelBinding binding,
        int relationshipVersion,
        CancellationToken cancellationToken
    )
    {
        if (
            proof.ReplyContextDigest is not { } questionProviderDigest
            || !IsLowerHexDigest(questionProviderDigest)
            || _conversationDbFactory is null
            || _conversationOptions is null
            || _tenantExecutionScope is null
        )
            return null;
        if (
            !Guid.TryParse(binding.ConversationId, out var conversationId)
            || conversationId == Guid.Empty
            || binding.BindingId == Guid.Empty
            || binding.ParticipantId == Guid.Empty
            || binding.RelationshipId == Guid.Empty
            || relationshipVersion < 0
        )
            throw new WhatsAppWebhookException(403, "WHATSAPP_REPLY_CONTEXT_INVALID");
        var route = _tenantExecutionScope.RequireConfirmedRelationshipRoute();
        if (
            route.TenantId != tenantId
            || route.ParticipantId != binding.ParticipantId
            || route.ParticipantRole != binding.ParticipantRole
            || route.RelationshipId != binding.RelationshipId
            || route.ConversationId != conversationId
            || route.BindingId != binding.BindingId
            || route.SenderHash != proof.PhoneSubjectHash
            || route.RelationshipVersion != relationshipVersion
        )
            throw new WhatsAppWebhookException(403, "WHATSAPP_REPLY_CONTEXT_INVALID");

        var decision = ConversationRequestClarification.Interpret(proof.Text) switch
        {
            ConversationRequestBoundary.OneRequest => "ONE",
            ConversationRequestBoundary.SeparateRequests => "SEPARATE",
            _ => "UNCLEAR",
        };
        await using var db = await _conversationDbFactory.CreateDbContextAsync(cancellationToken);
        await using var transaction = await db.Database.BeginTransactionAsync(
            IsolationLevel.Serializable,
            cancellationToken
        );
        await WhatsAppRelationshipRouting.RequireIngressCommitAsync(
            _tenantExecutionScope,
            _relationshipRouting,
            db,
            tenantId,
            binding.ParticipantId,
            binding.RelationshipId,
            conversationId,
            "WHATSAPP",
            binding.BindingId,
            proof.PhoneSubjectHash,
            cancellationToken
        );
        var response = await db
            .Database.SqlQuery<ConversationRequestAnswerResult>(
                $"""
                SELECT question_id AS "QuestionId", decision AS "Decision",
                       result_status AS "ResultStatus"
                FROM business.record_conversation_request_answer(
                    {_conversationOptions.Environment}, {_conversationOptions.AppBindingDigest},
                    {proof.MessageId}, {proof.PayloadDigest}, {leaseOwner}, {tenantId},
                    {binding.RelationshipId}, {conversationId}, {binding.ParticipantId},
                    {binding.ParticipantRole}, {relationshipVersion}, {binding.BindingId},
                    {proof.PhoneSubjectHash}, {questionProviderDigest}, {decision}
                )
                """
            )
            .ToListAsync(cancellationToken);
        if (response.Count == 0)
        {
            await transaction.CommitAsync(cancellationToken);
            return null;
        }
        if (
            response.Count != 1
            || response[0].QuestionId == Guid.Empty
            || response[0].ResultStatus
                is not ("CLARIFICATION_RECORDED" or "CLARIFICATION_ALREADY_RESOLVED")
        )
            throw new ConversationStateConflictException();
        _tenantExecutionScope.RequireUnchangedAuthority();
        await transaction.CommitAsync(cancellationToken);
        return new WhatsAppJourneyReceipt(
            proof.MessageId,
            response[0].ResultStatus,
            "CLARIFICATION",
            string.Empty,
            false,
            string.Empty
        );
    }

    private async Task<WhatsAppJourneyReceipt> ReceiveSignedSafetyEventAsync(
        VerifiedPhoneIdentityProof proof,
        CancellationToken ct
    )
    {
        var routing =
            _relationshipRouting
            ?? throw new WhatsAppWebhookException(503, "WHATSAPP_ROUTING_OWNER_UNAVAILABLE");
        WhatsAppJourneyReceipt? receipt = null;
        // A held/replayed provider claim must not delay recipient opt-out containment.
        if (IsRecipientStopRequest(proof.Text))
            receipt = await routing.ReceiveSignedSafetyControlAsync(proof, _emergencyStops, ct);
        var claim = await ClaimProviderEventAsync(proof, ct);
        if (claim.Replay is not null)
            return claim.Replay;
        try
        {
            receipt ??= await routing.ReceiveSignedSafetyControlAsync(proof, _emergencyStops, ct);
            await CompleteProviderEventAsync(proof, claim.LeaseOwner, receipt, ct);
            return receipt;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            await ReleaseProviderEventClaimAsync(proof, claim.LeaseOwner, ct);
            throw;
        }
    }

    private async Task<WhatsAppJourneyReceipt> ReceiveGuestEventAsync(
        VerifiedPhoneIdentityProof proof,
        string? verifiedPhoneNumber,
        CancellationToken cancellationToken
    )
    {
        if (_guestSessions is null)
            throw new WhatsAppWebhookException(503, "WHATSAPP_ACCOUNT_LINK_UNAVAILABLE");
        var claim = await ClaimProviderEventAsync(proof, cancellationToken);
        if (claim.Replay is not null)
            return claim.Replay;
        try
        {
            var admitted = await _guestSessions.ReceiveAsync(
                proof,
                cancellationToken,
                verifiedPhoneNumber
            );
            await CompleteProviderEventAsync(proof, claim.LeaseOwner, admitted, cancellationToken);
            return admitted;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested)
        {
            throw;
        }
        catch
        {
            await ReleaseProviderEventClaimAsync(proof, claim.LeaseOwner, cancellationToken);
            throw;
        }
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
        catch (DbUpdateException exception)
            when (ProviderEventClaimConflict.IsIdentityCollision(exception))
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

    internal async Task CompleteProviderEventAsync(
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
        await using var transaction = db.Database.IsNpgsql()
            ? await db.Database.BeginTransactionAsync(cancellationToken)
            : null;
        if (transaction is not null)
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT claim_id FROM business.provider_event_claims WHERE environment = {proof.Environment} AND provider = 'WHATSAPP' AND app_binding_digest = {proof.AppBindingDigest} AND event_identity = {proof.MessageId} FOR UPDATE",
                cancellationToken
            );
        var terminalAt = _clock.GetUtcNow();
        var resultJson = JsonSerializer.Serialize(
            receipt with
            {
                InternalTenantToken = string.Empty,
            }
        );
        var ownedClaim = db.ProviderEventClaims.Where(value =>
            value.Environment == proof.Environment
            && value.Provider == "WHATSAPP"
            && value.AppBindingDigest == proof.AppBindingDigest
            && value.EventIdentity == proof.MessageId
            && value.PayloadDigest == proof.PayloadDigest
            && value.LeaseOwner == leaseOwner
            && value.State != "ACCEPTED"
            && value.LeaseExpiresAt > terminalAt
        );
        if (db.Database.IsRelational())
        {
            var updated = await ownedClaim.ExecuteUpdateAsync(
                updates =>
                    updates
                        .SetProperty(value => value.State, "ACCEPTED")
                        .SetProperty(value => value.ResultJson, resultJson)
                        .SetProperty(value => value.TerminalAt, terminalAt)
                        .SetProperty(value => value.ExpiresAt, terminalAt.AddDays(30))
                        .SetProperty(value => value.LeaseOwner, (Guid?)null)
                        .SetProperty(value => value.LeaseExpiresAt, (DateTimeOffset?)null),
                cancellationToken
            );
            if (updated != 1)
                throw new WhatsAppWebhookException(409, "WHATSAPP_EVENT_LEASE_LOST");
            if (transaction is not null)
                await transaction.CommitAsync(cancellationToken);
            return;
        }
        var claim =
            await ownedClaim.SingleOrDefaultAsync(cancellationToken)
            ?? throw new WhatsAppWebhookException(409, "WHATSAPP_EVENT_LEASE_LOST");
        claim.State = "ACCEPTED";
        claim.ResultJson = resultJson;
        claim.TerminalAt = terminalAt;
        claim.ExpiresAt = terminalAt.AddDays(30);
        claim.LeaseOwner = null;
        claim.LeaseExpiresAt = null;
        await db.SaveChangesAsync(cancellationToken);
    }

    private async Task ReleaseProviderEventClaimAsync(
        VerifiedPhoneIdentityProof proof,
        Guid leaseOwner,
        CancellationToken cancellationToken
    )
    {
        if (
            _conversationDbFactory is null
            || string.IsNullOrWhiteSpace(proof.Environment)
            || string.IsNullOrWhiteSpace(proof.AppBindingDigest)
            || leaseOwner == Guid.Empty
        )
            return;

        await using var db = await _conversationDbFactory.CreateDbContextAsync(cancellationToken);
        var ownedClaims = db.ProviderEventClaims.Where(value =>
            value.Environment == proof.Environment
            && value.Provider == "WHATSAPP"
            && value.AppBindingDigest == proof.AppBindingDigest
            && value.EventIdentity == proof.MessageId
            && value.LeaseOwner == leaseOwner
            && value.State != "ACCEPTED"
        );
        if (db.Database.IsRelational())
        {
            await ownedClaims.ExecuteUpdateAsync(
                updates =>
                    updates
                        .SetProperty(value => value.LeaseOwner, (Guid?)null)
                        .SetProperty(value => value.LeaseExpiresAt, (DateTimeOffset?)null),
                cancellationToken
            );
            return;
        }
        foreach (var claim in await ownedClaims.ToListAsync(cancellationToken))
        {
            claim.LeaseOwner = null;
            claim.LeaseExpiresAt = null;
        }
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
        if (
            _conversationDbFactory is null
            || _conversationOptions is null
            || string.IsNullOrWhiteSpace(_conversationOptions.Environment)
            || string.IsNullOrEmpty(_conversationOptions.AppBindingDigest)
            || !IsLowerHexDigest(_conversationOptions.AppBindingDigest)
        )
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
        if (
            _conversationDbFactory is null
            || _conversationOptions is null
            || string.IsNullOrWhiteSpace(_conversationOptions.Environment)
            || string.IsNullOrEmpty(_conversationOptions.AppBindingDigest)
            || !IsLowerHexDigest(_conversationOptions.AppBindingDigest)
        )
            throw new InvalidOperationException("Provider claim owner is unavailable.");
        await using var db = await _conversationDbFactory.CreateDbContextAsync(cancellationToken);
        var due = db.ProviderEventClaims.Where(value =>
            value.Environment == _conversationOptions.Environment
            && (value.Provider == "WHATSAPP" || value.Provider == "WHATSAPP_STATUS")
            && value.AppBindingDigest == _conversationOptions.AppBindingDigest
            && value.TerminalAt != null
            && value.ExpiresAt != null
            && value.ExpiresAt <= now
            && !value.LegalHold
        );
        if (db.Database.IsRelational())
            return await due.ExecuteDeleteAsync(cancellationToken);

        var claims = await due.ToListAsync(cancellationToken);
        db.ProviderEventClaims.RemoveRange(claims);
        await db.SaveChangesAsync(cancellationToken);
        return claims.Count;
    }

    private sealed record ParsedProviderStatus(
        string WabaId,
        string RecipientId,
        WhatsAppProviderStatusEvent Event,
        string? SenderPhoneNumber = null
    );

    internal sealed record ParsedProviderMessage(
        string WabaId,
        string RecipientId,
        string MessageId,
        string From,
        string Text,
        DateTimeOffset SentAt,
        bool UnsupportedContent,
        string PayloadDigest,
        string? ReplyContextDigest
    );

    private List<ParsedProviderStatus> ParseProviderStatuses(JsonElement root)
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
                        Sha256(
                            JsonSerializer.Serialize(
                                new
                                {
                                    eventIdentity,
                                    providerMessageId,
                                    state,
                                    wabaId,
                                    recipientId,
                                    unixTimestamp,
                                }
                            )
                        )
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
                    change.ValueKind != JsonValueKind.Object
                    || !change.TryGetProperty("value", out var value)
                    || value.ValueKind != JsonValueKind.Object
                    || !value.TryGetProperty("metadata", out var metadata)
                    || !TryGetRequiredString(metadata, "phone_number_id", out recipientId)
                    || !value.TryGetProperty("statuses", out var providerStatuses)
                    || providerStatuses.ValueKind != JsonValueKind.Array
                )
                    continue;
                foreach (var providerStatus in providerStatuses.EnumerateArray())
                {
                    string? statusSender = null;
                    if (providerStatus.TryGetProperty("recipient_id", out var recipient))
                    {
                        if (
                            recipient.ValueKind != JsonValueKind.String
                            || string.IsNullOrWhiteSpace(recipient.GetString())
                        )
                            throw new WhatsAppWebhookException(400, "WHATSAPP_STATUS_INVALID");
                        statusSender = NormalizePublicSender(recipient.GetString()!);
                    }
                    if (
                        !TryGetRequiredString(providerStatus, "id", out providerMessageId)
                        || !TryGetRequiredString(providerStatus, "status", out state)
                        || !TryGetRequiredString(providerStatus, "timestamp", out var timestampText)
                        || !long.TryParse(timestampText, out unixTimestamp)
                    )
                        throw new WhatsAppWebhookException(400, "WHATSAPP_STATUS_INVALID");
                    Guid? outboxId = null;
                    if (providerStatus.TryGetProperty("biz_opaque_callback_data", out var opaque))
                    {
                        if (
                            opaque.ValueKind != JsonValueKind.String
                            || !Guid.TryParseExact(opaque.GetString(), "D", out var parsedOutboxId)
                            || parsedOutboxId == Guid.Empty
                        )
                            throw new WhatsAppWebhookException(400, "WHATSAPP_STATUS_INVALID");
                        outboxId = parsedOutboxId;
                    }
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
                                Sha256(
                                    JsonSerializer.Serialize(
                                        new[] { wabaId, recipientId, statusIdentity }
                                    )
                                )
                            )
                            {
                                OutboxId = outboxId,
                            },
                            statusSender
                        )
                    );
                }
            }
        }
        return statuses;
    }

    internal static List<ParsedProviderMessage> ParseProviderMessages(JsonElement root)
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
                    change.ValueKind != JsonValueKind.Object
                    || !change.TryGetProperty("value", out var value)
                    || value.ValueKind != JsonValueKind.Object
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
                        || messageType.Length > 32
                    )
                        throw new WhatsAppWebhookException(400, "WHATSAPP_MESSAGE_INVALID");
                    var unsupportedContent = !string.Equals(
                        messageType,
                        "text",
                        StringComparison.Ordinal
                    );
                    var body = string.Empty;
                    if (
                        !unsupportedContent
                        && (
                            !providerMessage.TryGetProperty("text", out var text)
                            || !TryGetRequiredString(text, "body", out body)
                            || body.Length > MaximumProviderTextLength
                        )
                    )
                        throw new WhatsAppWebhookException(400, "WHATSAPP_MESSAGE_INVALID");
                    var payloadDigest = Sha256(
                        JsonSerializer.Serialize(
                            new
                            {
                                wabaId,
                                recipientId,
                                messageId,
                                from,
                                timestampText,
                                messageType,
                                text = unsupportedContent ? null : body,
                            }
                        )
                    );
                    messages.Add(
                        new(
                            wabaId,
                            recipientId,
                            messageId,
                            from,
                            body,
                            FromProviderTimestamp(timestamp),
                            unsupportedContent,
                            payloadDigest,
                            ReadReplyContextDigest(providerMessage)
                        )
                    );
                }
            }
        }
        return messages;
    }

    internal static string? ReadReplyContextDigest(JsonElement providerMessage)
    {
        if (
            providerMessage.ValueKind != JsonValueKind.Object
            || !providerMessage.TryGetProperty("context", out var context)
            || !TryGetRequiredString(context, "id", out var id)
        )
            return null;
        return Sha256(id);
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
            element.ValueKind != JsonValueKind.Object
            || !element.TryGetProperty(propertyName, out var property)
            || property.ValueKind != JsonValueKind.String
        )
            return false;
        value = property.GetString() ?? string.Empty;
        return !string.IsNullOrWhiteSpace(value);
    }

    private static void RejectDuplicateProperties(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name))
                    throw new WhatsAppWebhookException(400, "WHATSAPP_PAYLOAD_INVALID");
                RejectDuplicateProperties(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
            foreach (var value in element.EnumerateArray())
                RejectDuplicateProperties(value);
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

    public async Task<WhatsAppRelationshipResolution> AttachLinkedPhoneAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid identityLinkId,
        string phoneSubjectHash,
        bool consentToRelationshipChannel,
        PortalPhoneAttachProof proof,
        CancellationToken cancellationToken
    )
    {
        ValidateFreshPortalProof(proof);
        if (
            identityLinkId == Guid.Empty
            || !IsLowerHexDigest(phoneSubjectHash)
            || !consentToRelationshipChannel
        )
            throw new ConstitutionalActionDeniedException(
                "A verified WhatsApp identity and explicit channel consent are required."
            );
        if (
            _relationshipGateway is null
            || _conversationService is null
            || _conversationDbFactory is null
            || _tenantExecutionScope is null
        )
            throw new WhatsAppChannelBindingUnavailableException(
                "Relationship channel-binding dependencies are unavailable."
            );
        IDisposable guestTenantScope;
        try
        {
            guestTenantScope = _tenantExecutionScope.Begin();
        }
        catch (WhatsAppCapabilityUnavailableException exception)
        {
            throw new WhatsAppChannelBindingUnavailableException(exception.Message);
        }
        using var tenantScope = guestTenantScope;
        var guestTenantId = _tenantExecutionScope.CurrentTenantId;
        if (guestTenantId is null)
            throw new WhatsAppChannelBindingUnavailableException(
                "WhatsApp guest-session authority is unavailable."
            );
        await using (
            var guestDb = await _conversationDbFactory.CreateDbContextAsync(cancellationToken)
        )
        {
            using var guestTenantOverride = _tenantExecutionScope.BeginDatabaseTenantOverride(
                guestTenantId.Value
            );
            await using var guestTransaction = guestDb.Database.IsRelational()
                ? await guestDb.Database.BeginTransactionAsync(cancellationToken)
                : null;
            if (guestDb.Database.IsNpgsql())
            {
                var guestLockKey = WhatsAppGuestSession.LockKey(
                    guestTenantId.Value,
                    phoneSubjectHash
                );
                await guestDb.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT pg_advisory_xact_lock(hashtextextended({guestLockKey}, 0))",
                    cancellationToken
                );
            }
            var guestSession = await guestDb
                .Set<WhatsAppGuestSession>()
                .AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == guestTenantId.Value
                        && value.BindingDigest == phoneSubjectHash,
                    cancellationToken
                );
            if (guestSession?.StoppedAt is not null)
                throw new ConstitutionalActionDeniedException(
                    "A stopped WhatsApp guest session cannot be re-enabled by account linking."
                );
        }
        await using var db = await _dbFactory.CreateDbContextAsync(cancellationToken);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(cancellationToken)
            : null;
        if (db.Database.IsNpgsql())
        {
            var lockKey = $"wc134:whatsapp-channel:{phoneSubjectHash}";
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({lockKey}, 0))",
                cancellationToken
            );
        }
        var relationship =
            await db
                .EmploymentRelationships.AsNoTracking()
                .SingleOrDefaultAsync(
                    value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                    cancellationToken
                )
            ?? throw new KeyNotFoundException("Employment relationship was not found.");
        if (
            relationship.State
            is not (EmploymentRelationshipState.TrialActive or EmploymentRelationshipState.Active)
        )
            throw new ConstitutionalActionDeniedException(
                "WhatsApp channel attachment requires an active or trial-active relationship."
            );
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
        var contact = await db.WhatsAppJourneyContacts.SingleOrDefaultAsync(
            value => value.PhoneHmac == phoneSubjectHash,
            cancellationToken
        );
        if (contact is not null && contact.TenantId != tenantId)
            throw new ConstitutionalActionDeniedException(
                "WhatsApp identity is already scoped to another tenant."
            );
        if (contact?.OptedOutAt is not null)
            throw new ConstitutionalActionDeniedException(
                "A withdrawn WhatsApp channel cannot be re-enabled by account linking."
            );

        var senderBindings = await db
            .ChannelBindings.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.Channel == "WHATSAPP"
                && value.ExternalSubjectHash == phoneSubjectHash
                && value.Status == "ACTIVE"
            )
            .Take(2)
            .ToListAsync(cancellationToken);
        if (
            senderBindings.Count > 1
            || senderBindings.Any(value => value.RelationshipId != relationshipId)
        )
            throw new ConstitutionalActionDeniedException(
                "The WhatsApp sender has an ambiguous active relationship binding."
            );
        var relationshipBindings = await db
            .ChannelBindings.Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Channel == "WHATSAPP"
                && value.Status == "ACTIVE"
            )
            .Take(2)
            .ToListAsync(cancellationToken);
        if (relationshipBindings.Count > 1)
            throw new ConstitutionalActionDeniedException(
                "The relationship has ambiguous active WhatsApp bindings."
            );
        var existing = relationshipBindings.SingleOrDefault();
        if (existing is not null)
        {
            var existingConversation = await _conversationService.EnsureConversationAsync(
                tenantId,
                relationshipId,
                cancellationToken
            );
            if (
                existing.ParticipantId == proof.ParticipantId
                && existing.ExternalSubjectHash == phoneSubjectHash
                && existing.ConversationId == existingConversation.ConversationId.ToString("D")
            )
            {
                await using var replayGuestDb = await _conversationDbFactory.CreateDbContextAsync(
                    cancellationToken
                );
                await using var replayGuestTransaction = replayGuestDb.Database.IsRelational()
                    ? await replayGuestDb.Database.BeginTransactionAsync(cancellationToken)
                    : null;
                using (_tenantExecutionScope.BeginDatabaseTenantOverride(guestTenantId.Value))
                {
                    await LockGuestSessionAsync(
                        replayGuestDb,
                        guestTenantId.Value,
                        phoneSubjectHash,
                        cancellationToken
                    );
                    if (
                        await IsGuestSessionStoppedAsync(
                            replayGuestDb,
                            guestTenantId.Value,
                            phoneSubjectHash,
                            cancellationToken
                        )
                    )
                        throw new ConstitutionalActionDeniedException(
                            "A stopped WhatsApp guest session cannot be re-enabled by account linking."
                        );
                }
                await RevalidateLinkedPhoneAuthorityAsync(
                    db,
                    relationship,
                    participant,
                    phoneSubjectHash,
                    existing,
                    proof,
                    cancellationToken,
                    identityLinkId
                );
                RequireCurrentAttachmentAuthority();
                ValidateFreshPortalProof(proof);
                await PublishLinkedPhoneRouteAsync(
                    db,
                    guestTenantId.Value,
                    existing,
                    identityLinkId,
                    proof,
                    cancellationToken
                );
                RequireCurrentAttachmentAuthority();
                ValidateFreshPortalProof(proof);
                if (transaction is not null)
                    await transaction.CommitAsync(cancellationToken);
                if (replayGuestTransaction is not null)
                    await replayGuestTransaction.CommitAsync(cancellationToken);
                return new(
                    tenantId,
                    relationshipId,
                    proof.ParticipantId,
                    existing.BindingId,
                    existing.AssuranceLevel
                );
            }
            throw new ConstitutionalActionDeniedException(
                "The relationship already has a different active WhatsApp binding."
            );
        }

        var now = _clock.GetUtcNow();
        contact ??= new WhatsAppJourneyContact
        {
            TenantId = tenantId,
            PhoneHmac = phoneSubjectHash,
            OptedInAt = now,
            LastInboundAt = now,
        };
        if (db.Entry(contact).State == EntityState.Detached)
            db.WhatsAppJourneyContacts.Add(contact);
        var conversation = await _conversationService.EnsureConversationAsync(
            tenantId,
            relationshipId,
            cancellationToken
        );
        var conversationId = conversation.ConversationId.ToString("D");

        var evidenceId = await _relationshipGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "ATTACH_WHATSAPP_PHONE",
            proof.CorrelationId,
            new
            {
                identity_account_link_id = identityLinkId,
                participant_id = proof.ParticipantId,
                participant_role = RelationshipRoleCodec.ToDatabase(participant.Role),
                phone_subject_hash = phoneSubjectHash,
                conversation_id = conversationId,
                relationship_channel_consent = consentToRelationshipChannel,
                relationship_channel_consent_version = "WC134-WHATSAPP-RELATIONSHIP-CHANNEL-1",
            },
            cancellationToken
        );
        await using var finalGuestDb = await _conversationDbFactory.CreateDbContextAsync(
            cancellationToken
        );
        await using var finalGuestTransaction = finalGuestDb.Database.IsRelational()
            ? await finalGuestDb.Database.BeginTransactionAsync(cancellationToken)
            : null;
        using (_tenantExecutionScope.BeginDatabaseTenantOverride(guestTenantId.Value))
        {
            await LockGuestSessionAsync(
                finalGuestDb,
                guestTenantId.Value,
                phoneSubjectHash,
                cancellationToken
            );
            if (
                await IsGuestSessionStoppedAsync(
                    finalGuestDb,
                    guestTenantId.Value,
                    phoneSubjectHash,
                    cancellationToken
                )
            )
                throw new ConstitutionalActionDeniedException(
                    "A stopped WhatsApp guest session cannot be re-enabled by account linking."
                );
        }
        await RevalidateLinkedPhoneAuthorityAsync(
            db,
            relationship,
            participant,
            phoneSubjectHash,
            null,
            proof,
            cancellationToken,
            identityLinkId
        );
        var binding = new ChannelBinding
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = proof.ParticipantId,
            ParticipantRole = RelationshipRoleCodec.ToDatabase(participant.Role),
            Channel = "WHATSAPP",
            ExternalSubjectHash = phoneSubjectHash,
            ConversationId = conversationId,
            AssuranceLevel = "TIER_4_PORTAL_FRESH",
            Status = "ACTIVE",
            PreparedEvidenceId = evidenceId,
            BoundEvidenceId = evidenceId,
            CreatedAt = now,
            BoundAt = now,
        };
        db.ChannelBindings.Add(binding);
        RequireCurrentAttachmentAuthority();
        await db.SaveChangesAsync(cancellationToken);
        await PublishLinkedPhoneRouteAsync(
            db,
            guestTenantId.Value,
            binding,
            identityLinkId,
            proof,
            cancellationToken
        );
        if (transaction is not null)
        {
            RequireCurrentAttachmentAuthority();
            ValidateFreshPortalProof(proof);
        }
        if (transaction is not null)
            await transaction.CommitAsync(cancellationToken);
        if (finalGuestTransaction is not null)
            await finalGuestTransaction.CommitAsync(cancellationToken);
        return new(
            tenantId,
            relationshipId,
            proof.ParticipantId,
            binding.BindingId,
            binding.AssuranceLevel
        );
    }

    private async Task PublishLinkedPhoneRouteAsync(
        EmploymentRelationshipDbContext db,
        Guid serviceTenantId,
        ChannelBinding binding,
        Guid identityLinkId,
        PortalPhoneAttachProof proof,
        CancellationToken ct
    )
    {
        if (proof.Actor is null && proof.Membership is null && !db.Database.IsRelational())
            return;
        if (_identity is null || proof.Actor is null)
            throw new WhatsAppChannelBindingUnavailableException(
                "Identity route publication authority is unavailable."
            );
        if (
            db.Database.IsRelational()
            && string.IsNullOrWhiteSpace(_conversationOptions?.Environment)
        )
            throw new WhatsAppChannelBindingUnavailableException(
                "WhatsApp route environment authority is unavailable."
            );
        var route = await WhatsAppRelationshipRoutePublication.PublishAsync(
            db,
            serviceTenantId,
            binding,
            identityLinkId,
            proof,
            _clock.GetUtcNow(),
            ct
        );
        await WhatsAppRelationshipRouteAuthority.RequireCurrentAsync(
            db,
            _identity,
            route,
            serviceTenantId,
            binding.ExternalSubjectHash,
            proof.Actor.Issuer,
            _conversationOptions?.Environment ?? "legacy",
            _clock.GetUtcNow(),
            ct
        );
    }

    private void RequireCurrentAttachmentAuthority()
    {
        try
        {
            _tenantExecutionScope!.RequireUnchangedAuthority();
        }
        catch (WhatsAppCapabilityUnavailableException exception)
        {
            throw new WhatsAppChannelBindingUnavailableException(exception.ReasonCode);
        }
    }

    private async Task RevalidateLinkedPhoneAuthorityAsync(
        EmploymentRelationshipDbContext db,
        EmploymentRelationship relationship,
        RelationshipParticipant participant,
        string phoneSubjectHash,
        ChannelBinding? existingBinding,
        PortalPhoneAttachProof proof,
        CancellationToken cancellationToken,
        Guid identityLinkId
    )
    {
        if (db.Database.IsRelational() || proof.Actor is not null || proof.Membership is not null)
        {
            if (_identity is null)
                throw new WhatsAppChannelBindingUnavailableException(
                    "Identity channel-binding authority is unavailable."
                );
            if (
                proof.Actor is null
                || proof.Membership is null
                || proof.Actor.Subject != proof.ParticipantId.ToString("D")
                || proof.Membership.TenantId != relationship.TenantId
            )
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            await _identity.RequireRelationshipChannelLinkAsync(
                db,
                identityLinkId,
                phoneSubjectHash,
                proof.Actor,
                proof.Membership,
                cancellationToken
            );
        }
        if (db.Database.IsNpgsql())
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT relationship_id FROM business.employment_relationships WHERE tenant_id = {relationship.TenantId} AND relationship_id = {relationship.RelationshipId} FOR UPDATE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT binding_id FROM business.relationship_participants WHERE tenant_id = {participant.TenantId} AND binding_id = {participant.BindingId} FOR UPDATE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT contact_id FROM business.whatsapp_journey_contacts WHERE tenant_id = {relationship.TenantId} AND phone_hmac = {phoneSubjectHash} FOR UPDATE",
                cancellationToken
            );
            if (existingBinding is not null)
                await db.Database.ExecuteSqlInterpolatedAsync(
                    $"SELECT binding_id FROM business.channel_bindings WHERE tenant_id = {relationship.TenantId} AND binding_id = {existingBinding.BindingId} FOR UPDATE",
                    cancellationToken
                );
        }
        var currentRelationship = await db
            .EmploymentRelationships.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == relationship.TenantId
                    && value.RelationshipId == relationship.RelationshipId,
                cancellationToken
            );
        var participantCurrent = await db
            .RelationshipParticipants.AsNoTracking()
            .AnyAsync(
                value =>
                    value.TenantId == participant.TenantId
                    && value.BindingId == participant.BindingId
                    && value.RelationshipId == participant.RelationshipId
                    && value.ParticipantId == participant.ParticipantId
                    && value.Role == participant.Role
                    && value.Status == "ACTIVE",
                cancellationToken
            );
        var withdrawn = await db
            .WhatsAppJourneyContacts.AsNoTracking()
            .AnyAsync(
                value =>
                    value.TenantId == relationship.TenantId
                    && value.PhoneHmac == phoneSubjectHash
                    && value.OptedOutAt != null,
                cancellationToken
            );
        var senderBindings = await db
            .ChannelBindings.AsNoTracking()
            .Where(value =>
                value.TenantId == relationship.TenantId
                && value.Channel == "WHATSAPP"
                && value.ExternalSubjectHash == phoneSubjectHash
                && value.Status == "ACTIVE"
            )
            .Select(value => value.BindingId)
            .Take(2)
            .ToListAsync(cancellationToken);
        var relationshipBindings = await db
            .ChannelBindings.AsNoTracking()
            .Where(value =>
                value.TenantId == relationship.TenantId
                && value.RelationshipId == relationship.RelationshipId
                && value.Channel == "WHATSAPP"
                && value.Status == "ACTIVE"
            )
            .Select(value => value.BindingId)
            .Take(2)
            .ToListAsync(cancellationToken);
        var cardinalityCurrent = existingBinding is null
            ? senderBindings.Count == 0 && relationshipBindings.Count == 0
            : senderBindings.Count == 1
                && senderBindings[0] == existingBinding.BindingId
                && relationshipBindings.Count == 1
                && relationshipBindings[0] == existingBinding.BindingId;
        var bindingCurrent =
            existingBinding is null
            || await db
                .ChannelBindings.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == relationship.TenantId
                        && value.BindingId == existingBinding.BindingId
                        && value.RelationshipId == relationship.RelationshipId
                        && value.ParticipantId == participant.ParticipantId
                        && value.ParticipantRole
                            == RelationshipRoleCodec.ToDatabase(participant.Role)
                        && value.Channel == "WHATSAPP"
                        && value.ExternalSubjectHash == phoneSubjectHash
                        && value.ConversationId == existingBinding.ConversationId
                        && value.AssuranceLevel == existingBinding.AssuranceLevel
                        && value.PreparedEvidenceId == existingBinding.PreparedEvidenceId
                        && value.BoundEvidenceId == existingBinding.BoundEvidenceId
                        && value.Status == "ACTIVE",
                    cancellationToken
                );
        ValidateFreshPortalProof(proof);
        if (
            currentRelationship is null
            || currentRelationship.State != relationship.State
            || currentRelationship.StateVersion != relationship.StateVersion
            || currentRelationship.ProfessionalType != relationship.ProfessionalType
            || !participantCurrent
            || !cardinalityCurrent
            || !bindingCurrent
            || withdrawn
        )
            throw new ConstitutionalActionDeniedException(
                "WhatsApp channel authority changed during attachment."
            );
    }

    private static async Task LockGuestSessionAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        string phoneSubjectHash,
        CancellationToken cancellationToken
    )
    {
        if (!db.Database.IsNpgsql())
            return;
        var guestLockKey = WhatsAppGuestSession.LockKey(tenantId, phoneSubjectHash);
        await db.Database.ExecuteSqlInterpolatedAsync(
            $"SELECT pg_advisory_xact_lock(hashtextextended({guestLockKey}, 0))",
            cancellationToken
        );
    }

    private static Task<bool> IsGuestSessionStoppedAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        string phoneSubjectHash,
        CancellationToken cancellationToken
    ) =>
        db.Set<WhatsAppGuestSession>()
            .AsNoTracking()
            .AnyAsync(
                value =>
                    value.TenantId == tenantId
                    && value.BindingDigest == phoneSubjectHash
                    && value.StoppedAt != null,
                cancellationToken
            );

    private void VerifySignature(
        byte[] rawBody,
        string signatureHeader,
        byte[]? signatureKey = null
    )
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
        var expected = HMACSHA256.HashData(signatureKey ?? _webhookSecret, rawBody);
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

    private static bool IsRecipientStopRequest(string text) =>
        text.Trim().Equals("STOP", StringComparison.OrdinalIgnoreCase);

    private static bool IsRelationshipEmergencyStopRequest(string text) =>
        text.Trim().Equals("EMERGENCY STOP", StringComparison.OrdinalIgnoreCase);

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

    private static string NormalizePublicSender(string value)
    {
        var normalized = value.StartsWith('+') ? value : $"+{value}";
        if (!Regex.IsMatch(normalized, @"^\+[1-9][0-9]{7,14}$"))
            throw new WhatsAppWebhookException(400, "WHATSAPP_SENDER_INVALID");
        return normalized;
    }

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

    private void ValidateFreshPortalProof(PortalPhoneAttachProof proof)
    {
        var age = _clock.GetUtcNow() - proof.AuthenticatedAt;
        if (
            proof.AuthenticationAssurance != "TIER_4_PORTAL_FRESH"
            || age < TimeSpan.FromSeconds(-30)
            || age > TimeSpan.FromMinutes(5)
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
