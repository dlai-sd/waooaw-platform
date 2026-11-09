// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R015
// constitutional_basis: C-005, C-026, C-049, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record PortalNavigationCapabilityV1(
    string CapabilityType,
    string Label,
    string Destination
);

public sealed record PortalInteractionMessageV1(
    string SchemaVersion,
    Guid MessageId,
    long Sequence,
    string Actor,
    IReadOnlyList<ConversationTextBlockV1> Content,
    IReadOnlyList<PortalNavigationCapabilityV1> Capabilities,
    string CurrentSurface,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ClientMessageId,
    DateTimeOffset AcceptedAt
);

public sealed record PortalInteractionTimelinePageV1(
    string SchemaVersion,
    string Scope,
    Guid ContextId,
    IReadOnlyList<PortalInteractionMessageV1> Items,
    string AuthoritativeCursor,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? NextCursor,
    bool HasMore,
    DateTimeOffset ServerTime
);

public sealed record SendPortalInteractionMessageRequestV1(
    string SchemaVersion,
    Guid ClientMessageId,
    IReadOnlyList<ConversationTextBlockV1> Content,
    string Locale,
    string CurrentSurface,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? ExpectedCursor = null
);

public sealed record PortalInteractionSubmissionV1(
    string SchemaVersion,
    string Scope,
    string Outcome,
    PortalInteractionMessageV1 CustomerMessage,
    PortalInteractionMessageV1 GuideMessage,
    string AuthoritativeCursor,
    bool Replayed
);

public interface IGuestConversation
{
    Task<PortalInteractionTimelinePageV1> ListGuestDiscoveryAsync(
        Guid tenantId,
        Guid participantId,
        string? cursor,
        int limit,
        CancellationToken cancellationToken
    );

    Task<ConversationCommandResult<PortalInteractionSubmissionV1>> SendGuestDiscoveryAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        SendPortalInteractionMessageRequestV1 request,
        CancellationToken cancellationToken
    );

    Task<ConversationCommandResult<PortalInteractionSubmissionV1>> SendGuestNoticeAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        SendPortalInteractionMessageRequestV1 request,
        string notice,
        CancellationToken cancellationToken
    );

    Task<ConversationCommandResult<PortalInteractionMessageV1>> SendGuestFixedNoticeAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        string notice,
        CancellationToken cancellationToken
    );
}

public sealed class PortalInteractionService : IGuestConversation
{
    private sealed record PortalInteractionCoreResult(
        PortalInteractionSubmissionV1? Submission,
        PortalInteractionMessageV1 GuideMessage
    );

    private const string SchemaVersion = "1.0";
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private static readonly HashSet<string> SupportedSurfaces =
    [
        "MARKETPLACE",
        "MY_AGENTS",
        "ALERTS",
        "RELATIONSHIP",
        "PERFORMANCE",
        "BILLING",
        "SETTINGS",
        "PROFILE",
    ];
    private readonly IDbContextFactory<ConversationStoreDbContext> _factory;
    private readonly ConversationCursorCodec _cursorCodec;
    private readonly IProfessionalCatalog? _professionalCatalog;

    public PortalInteractionService(
        IDbContextFactory<ConversationStoreDbContext> factory,
        ConversationCursorCodec cursorCodec,
        IProfessionalCatalog? professionalCatalog = null
    )
    {
        _factory = factory;
        _cursorCodec = cursorCodec;
        _professionalCatalog = professionalCatalog;
    }

    public async Task<PortalInteractionTimelinePageV1> ListAsync(
        Guid tenantId,
        Guid participantId,
        string? cursor,
        int limit,
        CancellationToken cancellationToken
    )
    {
        await using var db = await _factory.CreateDbContextAsync(cancellationToken);
        return await ListCoreAsync(db, tenantId, participantId, cursor, limit, cancellationToken);
    }

    private async Task<PortalInteractionTimelinePageV1> ListCoreAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        string? cursor,
        int limit,
        CancellationToken cancellationToken
    )
    {
        if (limit is < 1 or > 100)
            throw new ConversationRequestException("limit must be between 1 and 100.");
        if (cursor is not null && cursor.Length is < 16 or > 2048)
            throw new ConversationRequestException(
                "cursor must be between 16 and 2048 characters."
            );
        var context = await GetOrCreateContextAsync(db, tenantId, participantId, cancellationToken);
        var query = db
            .PortalInteractionMessages.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.ParticipantId == participantId);
        if (cursor is not null)
        {
            var before = _cursorCodec.Decode(
                cursor,
                tenantId,
                context.ContextId,
                "portal-timeline"
            );
            query = query.Where(value => value.Sequence < before);
        }
        var descending = await query
            .OrderByDescending(value => value.Sequence)
            .Take(limit + 1)
            .ToListAsync(cancellationToken);
        var hasMore = descending.Count > limit;
        var selected = descending.Take(limit).OrderBy(value => value.Sequence).ToArray();
        var maximumSequence =
            await db
                .PortalInteractionMessages.AsNoTracking()
                .Where(value => value.TenantId == tenantId && value.ParticipantId == participantId)
                .Select(value => (long?)value.Sequence)
                .MaxAsync(cancellationToken)
            ?? 0;
        var nextCursor =
            hasMore && selected.Length > 0
                ? _cursorCodec.Encode(
                    tenantId,
                    context.ContextId,
                    "portal-timeline",
                    selected[0].Sequence
                )
                : null;
        return new PortalInteractionTimelinePageV1(
            SchemaVersion,
            "PORTAL",
            context.ContextId,
            selected.Select(ToContract).ToArray(),
            _cursorCodec.Encode(tenantId, context.ContextId, "portal-timeline", maximumSequence),
            nextCursor,
            hasMore,
            DateTimeOffset.UtcNow
        );
    }

    public async Task<PortalInteractionTimelinePageV1> ListGuestDiscoveryAsync(
        Guid tenantId,
        Guid participantId,
        string? cursor,
        int limit,
        CancellationToken cancellationToken
    )
    {
        await using var db = await _factory.CreateDbContextAsync(cancellationToken);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(cancellationToken)
            : null;
        await GuardWhatsAppGuestAsync(db, tenantId, participantId, true, cancellationToken);
        var page = await ListCoreAsync(
            db,
            tenantId,
            participantId,
            cursor,
            limit,
            cancellationToken
        );
        if (transaction is not null)
            await transaction.CommitAsync(cancellationToken);
        return page with { Scope = "GUEST_DISCOVERY" };
    }

    public async Task<ConversationCommandResult<PortalInteractionSubmissionV1>> SendAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        SendPortalInteractionMessageRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        var result = await SendCoreAsync(
            tenantId,
            participantId,
            idempotencyKey,
            request,
            false,
            null,
            true,
            cancellationToken
        );
        return new(result.Value.Submission!, result.Replayed);
    }

    public async Task<
        ConversationCommandResult<PortalInteractionSubmissionV1>
    > SendGuestDiscoveryAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        SendPortalInteractionMessageRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        var result = await SendCoreAsync(
            tenantId,
            participantId,
            idempotencyKey,
            request,
            true,
            null,
            true,
            cancellationToken
        );
        return new(result.Value.Submission!, result.Replayed);
    }

    public async Task<
        ConversationCommandResult<PortalInteractionSubmissionV1>
    > SendGuestNoticeAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        SendPortalInteractionMessageRequestV1 request,
        string notice,
        CancellationToken cancellationToken
    )
    {
        if (string.IsNullOrWhiteSpace(notice) || notice.Length > 4096)
            throw new ConversationRequestException("Guest notice is malformed or unsupported.");
        var result = await SendCoreAsync(
            tenantId,
            participantId,
            idempotencyKey,
            request,
            true,
            notice,
            true,
            cancellationToken
        );
        return new(result.Value.Submission!, result.Replayed);
    }

    public async Task<
        ConversationCommandResult<PortalInteractionMessageV1>
    > SendGuestFixedNoticeAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        string notice,
        CancellationToken cancellationToken
    )
    {
        if (
            notice
            is not (
                WhatsAppGuestTrafficBudget.SessionLimitNotice
                or WhatsAppGuestTrafficBudget.UnsupportedContentNotice
                or WhatsAppGuestTrafficBudget.MessageLimitNotice
                or WhatsAppGuestTrafficBudget.GlobalRateLimitNotice
                or WhatsAppGuestTrafficBudget.ActivationLimitNotice
                or WhatsAppGuestOperatingHours.ClosedNotice
                or WhatsAppGuestConsent.Notice
                or WhatsAppGuestConsent.RenewalUnavailable
                or WhatsAppGuestConsent.Accepted
                or WhatsAppGuestConsent.RegisteredNumberAccepted
                or WhatsAppAccountLinkInstruction.ConfirmedNotice
                or WhatsAppAccountLinkInstruction.DeniedNotice
            )
        )
            throw new ConversationRequestException("Guest fixed notice is unsupported.");
        var request = new SendPortalInteractionMessageRequestV1(
            SchemaVersion,
            idempotencyKey,
            [new(SchemaVersion, "TEXT", "Guest session admission notice", "en-IN")],
            "en-IN",
            "MARKETPLACE"
        );
        var result = await SendCoreAsync(
            tenantId,
            participantId,
            idempotencyKey,
            request,
            true,
            notice,
            false,
            cancellationToken
        );
        return new(result.Value.GuideMessage, result.Replayed);
    }

    private async Task<ConversationCommandResult<PortalInteractionCoreResult>> SendCoreAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        SendPortalInteractionMessageRequestV1 request,
        bool guestDiscovery,
        string? guestNotice,
        bool persistCustomerMessage,
        CancellationToken cancellationToken
    )
    {
        Validate(request);
        var catalogueDiscovery = guestDiscovery || request.CurrentSurface == "MARKETPLACE";
        if (guestDiscovery && request.CurrentSurface != "MARKETPLACE")
            throw new ConversationRequestException(
                "Guest discovery is limited to the public marketplace surface."
            );
        var requestJson = JsonSerializer.Serialize(request, JsonOptions);
        var idempotencyInput =
            guestNotice is null && persistCustomerMessage
                ? requestJson
                : $"{requestJson}\n{guestNotice}\n{persistCustomerMessage}";
        var requestHash = Convert.ToHexStringLower(
            SHA256.HashData(Encoding.UTF8.GetBytes(idempotencyInput))
        );
        await using var db = await _factory.CreateDbContextAsync(cancellationToken);
        await using var transaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(cancellationToken)
            : null;
        if (catalogueDiscovery)
            await GuardWhatsAppGuestAsync(
                db,
                tenantId,
                participantId,
                persistCustomerMessage,
                cancellationToken
            );
        if (transaction is not null)
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({$"interaction:{tenantId:D}:{participantId:D}"}, 0))",
                cancellationToken
            );
        var replay = await db
            .PortalInteractionIdempotencyOutcomes.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.ParticipantId == participantId
                    && value.IdempotencyKey == idempotencyKey,
                cancellationToken
            );
        if (replay is not null)
        {
            if (replay.RequestHash != requestHash)
                throw new ConversationIdempotencyConflictException();
            if (!persistCustomerMessage)
            {
                var replayedGuide =
                    JsonSerializer.Deserialize<PortalInteractionMessageV1>(
                        replay.ResponseJson,
                        JsonOptions
                    ) ?? throw new ConversationStateConflictException();
                return new(new PortalInteractionCoreResult(null, replayedGuide), true);
            }
            var replayed =
                JsonSerializer.Deserialize<PortalInteractionSubmissionV1>(
                    replay.ResponseJson,
                    JsonOptions
                ) ?? throw new ConversationStateConflictException();
            return new(
                new PortalInteractionCoreResult(
                    replayed with
                    {
                        Outcome = "REPLAYED",
                        Replayed = true,
                    },
                    replayed.GuideMessage
                ),
                true
            );
        }
        if (
            await db
                .PortalInteractionMessages.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.ParticipantId == participantId
                        && value.ClientMessageId == request.ClientMessageId,
                    cancellationToken
                )
        )
            throw new ConversationIdempotencyConflictException();

        var context = await GetOrCreateContextAsync(db, tenantId, participantId, cancellationToken);
        var lastOtherSurfaceSequence = catalogueDiscovery
            ? await db
                .PortalInteractionMessages.AsNoTracking()
                .Where(value =>
                    value.TenantId == tenantId
                    && value.ParticipantId == participantId
                    && value.Actor == "CUSTOMER"
                    && value.CurrentSurface != "MARKETPLACE"
                )
                .MaxAsync(value => (long?)value.Sequence, cancellationToken)
                ?? 0
            : 0;
        List<string> priorGuestTurns = catalogueDiscovery
            ? await db
                .PortalInteractionMessages.AsNoTracking()
                .Where(value =>
                    value.TenantId == tenantId
                    && value.ParticipantId == participantId
                    && value.Actor == "CUSTOMER"
                    && value.CurrentSurface == "MARKETPLACE"
                    && value.Sequence > lastOtherSurfaceSequence
                )
                .OrderByDescending(value => value.Sequence)
                .Take(3)
                .Select(value => value.ContentJson)
                .ToListAsync(cancellationToken)
            : [];
        var isFirstGuestTurn = priorGuestTurns.Count == 0;
        var maximumSequence =
            await db
                .PortalInteractionMessages.Where(value =>
                    value.TenantId == tenantId && value.ParticipantId == participantId
                )
                .Select(value => (long?)value.Sequence)
                .MaxAsync(cancellationToken)
            ?? 0;
        if (
            request.ExpectedCursor is not null
            && _cursorCodec.Decode(
                request.ExpectedCursor,
                tenantId,
                context.ContextId,
                "portal-timeline"
            ) != maximumSequence
        )
        {
            throw new ConversationStateConflictException();
        }

        var customer = persistCustomerMessage
            ? new PortalInteractionMessage
            {
                TenantId = tenantId,
                ContextId = context.ContextId,
                ParticipantId = participantId,
                Sequence = context.NextMessageSequence++,
                Actor = "CUSTOMER",
                ContentJson = JsonSerializer.Serialize(request.Content, JsonOptions),
                CurrentSurface = request.CurrentSurface,
                ClientMessageId = request.ClientMessageId,
            }
            : null;
        var (guideText, capability) = guestNotice is null
            ? CreateGuideResponse(request, catalogueDiscovery, isFirstGuestTurn, priorGuestTurns)
            : (
                guestNotice,
                new PortalNavigationCapabilityV1(
                    "NAVIGATE",
                    "Explore professionals",
                    "/marketplace"
                )
            );
        if (guestDiscovery && guideText.Length > 4096)
            throw new ConversationRequestException(
                "Onboarding reply exceeds the WhatsApp text bound."
            );
        var guide = new PortalInteractionMessage
        {
            TenantId = tenantId,
            ContextId = context.ContextId,
            ParticipantId = participantId,
            Sequence = context.NextMessageSequence++,
            Actor = "GUIDE",
            ContentJson = JsonSerializer.Serialize<IReadOnlyList<ConversationTextBlockV1>>(
                [new(SchemaVersion, "TEXT", guideText, request.Locale)],
                JsonOptions
            ),
            CapabilitiesJson = JsonSerializer.Serialize<
                IReadOnlyList<PortalNavigationCapabilityV1>
            >([capability], JsonOptions),
            CurrentSurface = request.CurrentSurface,
        };
        context.UpdatedAt = DateTimeOffset.UtcNow;
        var guideContract = ToContract(guide);
        var submission = customer is null
            ? null
            : new PortalInteractionSubmissionV1(
                SchemaVersion,
                guestDiscovery ? "GUEST_DISCOVERY" : "PORTAL",
                "ACCEPTED",
                ToContract(customer),
                guideContract,
                _cursorCodec.Encode(tenantId, context.ContextId, "portal-timeline", guide.Sequence),
                false
            );
        if (customer is null)
            db.PortalInteractionMessages.Add(guide);
        else
            db.PortalInteractionMessages.AddRange(customer, guide);
        db.PortalInteractionIdempotencyOutcomes.Add(
            new PortalInteractionIdempotencyOutcome
            {
                TenantId = tenantId,
                ParticipantId = participantId,
                IdempotencyKey = idempotencyKey,
                RequestHash = requestHash,
                ResponseJson = submission is null
                    ? JsonSerializer.Serialize(guideContract, JsonOptions)
                    : JsonSerializer.Serialize(submission, JsonOptions),
            }
        );
        await db.SaveChangesAsync(cancellationToken);
        if (transaction is not null)
            await transaction.CommitAsync(cancellationToken);
        return new(new PortalInteractionCoreResult(submission, guideContract), false);
    }

    private static async Task GuardWhatsAppGuestAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        bool requireConsent,
        CancellationToken cancellationToken
    )
    {
        var guest = await db.Set<WhatsAppGuestSession>()
            .AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.ParticipantId == participantId,
                cancellationToken
            );
        if (guest is null)
            return;
        if (db.Database.IsRelational())
        {
            var guestLock = WhatsAppGuestSession.LockKey(tenantId, guest.BindingDigest);
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT pg_advisory_xact_lock(hashtextextended({guestLock}, 0))",
                cancellationToken
            );
            guest = await db.Set<WhatsAppGuestSession>()
                .AsNoTracking()
                .SingleAsync(
                    value => value.TenantId == tenantId && value.ParticipantId == participantId,
                    cancellationToken
                );
        }
        if (guest.StoppedAt is not null)
            throw new ConversationStoppedException();
        if (
            requireConsent
            && (
                guest.EvidenceId is null
                || guest.AdmittedAt is null
                || guest.ServiceConsentAt is null
                || guest.ServiceConsentEvidenceId is null
                || guest.ServiceConsentNoticeVersion != WhatsAppGuestConsent.NoticeVersion
            )
        )
            throw new ConversationNotAccessibleException();
    }

    private static void Validate(SendPortalInteractionMessageRequestV1 request)
    {
        if (
            request.SchemaVersion != SchemaVersion
            || request.ClientMessageId == Guid.Empty
            || request.Content.Count != 1
            || request.Content[0].SchemaVersion != SchemaVersion
            || request.Content[0].BlockType != "TEXT"
            || string.IsNullOrWhiteSpace(request.Content[0].Text)
            || request.Content[0].Text.Length > 32000
            || !ConversationInputContract.IsPersistableText(request.Content[0].Text)
            || !ConversationInputContract.IsLanguageTag(request.Locale)
            || request.Content[0].Language is { } language
                && !ConversationInputContract.IsLanguageTag(language)
            || !SupportedSurfaces.Contains(request.CurrentSurface)
        )
        {
            throw new ConversationRequestException(
                "Portal interaction request is malformed or unsupported."
            );
        }
    }

    private (string Text, PortalNavigationCapabilityV1 Capability) CreateGuideResponse(
        SendPortalInteractionMessageRequestV1 request,
        bool guestDiscovery,
        bool isFirstGuestTurn,
        IReadOnlyList<string> priorGuestTurns
    )
    {
        var text = request.Content[0].Text;
        if (guestDiscovery)
        {
            var catalog =
                _professionalCatalog
                ?? throw new InvalidOperationException(
                    "The professional catalogue is required for guest discovery."
                );
            var correction = IsGuestContextCorrection(text);
            var browseRequested = IsBrowseRequest(text);
            var matches =
                correction || browseRequested ? [] : catalog.Discover(text).Take(3).ToList();
            if (
                !correction
                && !browseRequested
                && matches.Count == 0
                && IsGuestContextFollowUp(text)
            )
            {
                var previousTurns = priorGuestTurns
                    .SelectMany(value =>
                        JsonSerializer.Deserialize<IReadOnlyList<ConversationTextBlockV1>>(
                            value,
                            JsonOptions
                        ) ?? []
                    )
                    .Where(value => value.BlockType == "TEXT")
                    .Select(value => value.Text);
                foreach (var previousTurn in previousTurns)
                {
                    if (IsGuestContextCorrection(previousTurn) || IsBrowseRequest(previousTurn))
                        break;
                    matches = catalog.Discover(previousTurn).Take(3).ToList();
                    if (matches.Count > 0 || !IsGuestContextFollowUp(previousTurn))
                        break;
                }
            }
            var previewTopic = correction ? null : GuestPreviewTopic(text);
            var browse =
                !correction && browseRequested ? catalog.Browse(null, null).Take(3).ToList() : [];
            var discovery =
                correction
                    ? "I will not use the earlier selection. Please describe the outcome you want instead. "
                : previewTopic is not null ? DescribeGuestPreview(catalog, matches, previewTopic)
                : matches.Count > 0
                    ? "The current catalogue suggests: "
                        + string.Join(
                            "; ",
                            matches.Select(value =>
                                $"{value.DisplayName}: {string.Join(", ", value.Suitability)}."
                            )
                        )
                        + " "
                : browse.Count > 0
                    ? "You can explore: "
                        + string.Join(
                            "; ",
                            browse.Select(value =>
                                $"{value.DisplayName}: {string.Join(", ", value.Suitability)}."
                            )
                        )
                        + " "
                : "Tell me the outcome you need so I can check the current professional catalogue. ";
            var introduction = isFirstGuestTurn
                ? "Welcome to WAOOAW Demo. You can browse professionals and ask me to narrow the public catalogue. "
                    + "This discovery conversation does not create a customer account, membership, trial, or hiring relationship. "
                : string.Empty;
            var handoff = isFirstGuestTurn
                ? "Trial or hire starts on the web portal and may require registration and verification. "
                : string.Empty;
            return (
                introduction
                    + discovery
                    + handoff
                    + (
                        isFirstGuestTurn
                            ? "If you are using WhatsApp, reply STOP to stop messages."
                            : "What would you like to explore next?"
                    ),
                new("NAVIGATE", "Explore professionals", "/marketplace")
            );
        }
        if (
            text.Contains("bill", StringComparison.OrdinalIgnoreCase)
            || text.Contains("payment", StringComparison.OrdinalIgnoreCase)
        )
        {
            return (
                "I can take you to billing details. I cannot approve charges or act for an employed professional.",
                new("NAVIGATE", "Review billing", "/profile#billing")
            );
        }
        if (text.Contains("alert", StringComparison.OrdinalIgnoreCase))
        {
            return (
                "I can take you to your authoritative alerts. Open a relationship to discuss one with that professional.",
                new("NAVIGATE", "Review alerts", "/alerts")
            );
        }
        if (
            text.Contains("agent", StringComparison.OrdinalIgnoreCase)
            || text.Contains("work", StringComparison.OrdinalIgnoreCase)
        )
        {
            return (
                "I can take you to My Agents. Relationship decisions and work remain inside the selected professional's conversation.",
                new("NAVIGATE", "Open My Agents", "/professionals/mine")
            );
        }
        var capability =
            request.CurrentSurface == "MARKETPLACE"
                ? new PortalNavigationCapabilityV1(
                    "NAVIGATE",
                    "Browse professionals",
                    "/marketplace"
                )
                : new PortalNavigationCapabilityV1(
                    "NAVIGATE",
                    "Open My Agents",
                    "/professionals/mine"
                );
        return (
            "I am the WAOOAW Guide. I can help you navigate and explain portal information, but I cannot impersonate a professional or execute relationship commands.",
            capability
        );
    }

    private static bool IsBrowseRequest(string text) =>
        text.Contains("browse", StringComparison.OrdinalIgnoreCase)
        || text.Contains("list professionals", StringComparison.OrdinalIgnoreCase)
        || text.Contains("show offerings", StringComparison.OrdinalIgnoreCase)
        || text.Contains("show professionals", StringComparison.OrdinalIgnoreCase);

    private static bool IsGuestContextCorrection(string text) =>
        System.Text.RegularExpressions.Regex.IsMatch(
            text,
            @"\b(?:no|not|don'?t|instead|different|change|reset|restart|cancel|wrong|rather|start\s+over)\b",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase
                | System.Text.RegularExpressions.RegexOptions.CultureInvariant
        );

    private static bool IsGuestContextFollowUp(string text) =>
        System.Text.RegularExpressions.Regex.IsMatch(
            text.Trim(),
            @"^(?:tell me more|what (?:skills|capabilities) (?:are available|are offered)|what (?:skills|capabilities|limitations|trial)|what are the (?:skills|capabilities|limitations)|what is the trial)[?.!]*$",
            System.Text.RegularExpressions.RegexOptions.IgnoreCase
                | System.Text.RegularExpressions.RegexOptions.CultureInvariant
        );

    private static string? GuestPreviewTopic(string text)
    {
        var topics = new List<string>();
        if (
            text.Contains("skill", StringComparison.OrdinalIgnoreCase)
            || text.Contains("capabilit", StringComparison.OrdinalIgnoreCase)
        )
            topics.Add("skills");
        if (
            text.Contains("limitation", StringComparison.OrdinalIgnoreCase)
            || text.Contains("cannot", StringComparison.OrdinalIgnoreCase)
        )
            topics.Add("limitations");
        if (text.Contains("trial", StringComparison.OrdinalIgnoreCase))
            topics.Add("trial");
        return topics.Count switch
        {
            0 => null,
            1 => topics[0],
            _ => "ambiguous",
        };
    }

    private static string DescribeGuestPreview(
        IProfessionalCatalog catalog,
        IReadOnlyList<ProfessionalDiscoveryResult> matches,
        string topic
    )
    {
        if (topic == "ambiguous")
            return "Please ask about skills, limitations, or the trial one at a time. ";
        if (matches.Count != 1)
            return "Please identify one professional or describe the outcome you need before asking about its preview. ";
        var match = matches[0];
        var disclosure = catalog.GetDisclosure(match.ProfessionalType);
        if (
            !match.Eligibility.Eligible
            || disclosure is null
            || !disclosure.Eligibility.Eligible
            || !string.Equals(
                disclosure.ProfessionalType,
                match.ProfessionalType,
                StringComparison.OrdinalIgnoreCase
            )
            || disclosure.ProjectionVersion != match.ProjectionVersion
        )
            return "That professional's current catalogue disclosure is unavailable. Please browse the marketplace. ";
        var details = topic switch
        {
            "skills" when disclosure.Skills.Count > 0 => "Published skills: "
                + string.Join(
                    "; ",
                    disclosure.Skills.Select(skill =>
                        skill.DisplayName
                        + (
                            skill.ApplicableInTrial
                                ? " (listed for trial"
                                : " (not listed for trial"
                        )
                        + (
                            string.IsNullOrWhiteSpace(skill.ActivationCondition)
                                ? ")"
                                : $"; condition: {skill.ActivationCondition})"
                        )
                    )
                ),
            "limitations" when disclosure.Limitations.Count > 0 => "Published limitations: "
                + string.Join("; ", disclosure.Limitations),
            "trial" when disclosure.Trial.Available =>
                $"The published trial lasts {disclosure.Trial.DurationDays} days. "
                    + (
                        disclosure.Trial.PaidApiCallsAllowed
                            ? "Paid API calls may be allowed under its terms. "
                            : "Paid API calls are not allowed in the trial. "
                    )
                    + (
                        disclosure.Trial.ExternalActionsAllowed
                            ? "External actions may be allowed under its terms"
                            : "External actions are not allowed in the trial"
                    )
                    + ". Starting a trial requires the web portal and its separate admission checks",
            "trial" => "The published catalogue does not currently offer a trial",
            _ => "No published details are available for this topic",
        };
        return $"{disclosure.DisplayName} (catalogue preview, not an employed professional): {details}. ";
    }

    private static PortalInteractionMessageV1 ToContract(PortalInteractionMessage value) =>
        new(
            SchemaVersion,
            value.MessageId,
            value.Sequence,
            value.Actor,
            JsonSerializer.Deserialize<IReadOnlyList<ConversationTextBlockV1>>(
                value.ContentJson,
                JsonOptions
            ) ?? [],
            JsonSerializer.Deserialize<IReadOnlyList<PortalNavigationCapabilityV1>>(
                value.CapabilitiesJson,
                JsonOptions
            ) ?? [],
            value.CurrentSurface,
            value.ClientMessageId,
            value.AcceptedAt
        );

    private static async Task<PortalInteractionContext> GetOrCreateContextAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        CancellationToken cancellationToken
    )
    {
        if (db.Database.IsRelational())
        {
            var contextId = Guid.NewGuid();
            var now = DateTimeOffset.UtcNow;
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"""
                INSERT INTO business.portal_interaction_contexts
                    (context_id, tenant_id, participant_id, next_message_sequence, created_at, updated_at)
                VALUES ({contextId}, {tenantId}, {participantId}, {1L}, {now}, {now})
                ON CONFLICT DO NOTHING
                """,
                cancellationToken
            );
            return await db.PortalInteractionContexts.SingleAsync(
                value => value.TenantId == tenantId && value.ParticipantId == participantId,
                cancellationToken
            );
        }

        var existing = await db.PortalInteractionContexts.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.ParticipantId == participantId,
            cancellationToken
        );
        if (existing is not null)
            return existing;
        var created = new PortalInteractionContext
        {
            TenantId = tenantId,
            ParticipantId = participantId,
        };
        db.PortalInteractionContexts.Add(created);
        await db.SaveChangesAsync(cancellationToken);
        return created;
    }
}
