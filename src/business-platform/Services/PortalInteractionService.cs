// Implements: work-contracts/WC-096-conversational-customer-portal.md §5
// constitutional_basis: C-005, C-026, C-049, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record PortalNavigationCapabilityV1(string CapabilityType, string Label, string Destination);

public sealed record PortalInteractionMessageV1(
    string SchemaVersion,
    Guid MessageId,
    long Sequence,
    string Actor,
    IReadOnlyList<ConversationTextBlockV1> Content,
    IReadOnlyList<PortalNavigationCapabilityV1> Capabilities,
    string CurrentSurface,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ClientMessageId,
    DateTimeOffset AcceptedAt);

public sealed record PortalInteractionTimelinePageV1(
    string SchemaVersion,
    string Scope,
    Guid ContextId,
    IReadOnlyList<PortalInteractionMessageV1> Items,
    string AuthoritativeCursor,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? NextCursor,
    bool HasMore,
    DateTimeOffset ServerTime);

public sealed record SendPortalInteractionMessageRequestV1(
    string SchemaVersion,
    Guid ClientMessageId,
    IReadOnlyList<ConversationTextBlockV1> Content,
    string Locale,
    string CurrentSurface,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ExpectedCursor = null);

public sealed record PortalInteractionSubmissionV1(
    string SchemaVersion,
    string Scope,
    string Outcome,
    PortalInteractionMessageV1 CustomerMessage,
    PortalInteractionMessageV1 GuideMessage,
    string AuthoritativeCursor,
    bool Replayed);

public sealed class PortalInteractionService
{
    private const string SchemaVersion = "1.0";
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private static readonly HashSet<string> SupportedSurfaces =
        ["MARKETPLACE", "MY_AGENTS", "ALERTS", "RELATIONSHIP", "PERFORMANCE", "BILLING", "SETTINGS", "PROFILE"];
    private readonly IDbContextFactory<ConversationStoreDbContext> _factory;
    private readonly ConversationCursorCodec _cursorCodec;

    public PortalInteractionService(
        IDbContextFactory<ConversationStoreDbContext> factory,
        ConversationCursorCodec cursorCodec)
    {
        _factory = factory;
        _cursorCodec = cursorCodec;
    }

    public async Task<PortalInteractionTimelinePageV1> ListAsync(
        Guid tenantId,
        Guid participantId,
        string? cursor,
        int limit,
        CancellationToken cancellationToken)
    {
        if (limit is < 1 or > 100) throw new ConversationRequestException("limit must be between 1 and 100.");
        await using var db = await _factory.CreateDbContextAsync(cancellationToken);
        var context = await GetOrCreateContextAsync(db, tenantId, participantId, cancellationToken);
        var query = db.PortalInteractionMessages.AsNoTracking().Where(value =>
            value.TenantId == tenantId && value.ParticipantId == participantId);
        if (cursor is not null)
        {
            var before = _cursorCodec.Decode(cursor, tenantId, context.ContextId, "portal-timeline");
            query = query.Where(value => value.Sequence < before);
        }
        var descending = await query.OrderByDescending(value => value.Sequence).Take(limit + 1).ToListAsync(cancellationToken);
        var hasMore = descending.Count > limit;
        var selected = descending.Take(limit).OrderBy(value => value.Sequence).ToArray();
        var maximumSequence = await db.PortalInteractionMessages.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.ParticipantId == participantId)
            .Select(value => (long?)value.Sequence).MaxAsync(cancellationToken) ?? 0;
        var nextCursor = hasMore && selected.Length > 0
            ? _cursorCodec.Encode(tenantId, context.ContextId, "portal-timeline", selected[0].Sequence)
            : null;
        return new PortalInteractionTimelinePageV1(
            SchemaVersion, "PORTAL", context.ContextId, selected.Select(ToContract).ToArray(),
            _cursorCodec.Encode(tenantId, context.ContextId, "portal-timeline", maximumSequence),
            nextCursor, hasMore, DateTimeOffset.UtcNow);
    }

    public async Task<ConversationCommandResult<PortalInteractionSubmissionV1>> SendAsync(
        Guid tenantId,
        Guid participantId,
        Guid idempotencyKey,
        SendPortalInteractionMessageRequestV1 request,
        CancellationToken cancellationToken)
    {
        Validate(request);
        var requestJson = JsonSerializer.Serialize(request, JsonOptions);
        var requestHash = Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(requestJson)));
        await using var db = await _factory.CreateDbContextAsync(cancellationToken);
        var replay = await db.PortalInteractionIdempotencyOutcomes.AsNoTracking().SingleOrDefaultAsync(value =>
            value.TenantId == tenantId && value.ParticipantId == participantId && value.IdempotencyKey == idempotencyKey,
            cancellationToken);
        if (replay is not null)
        {
            if (replay.RequestHash != requestHash) throw new ConversationIdempotencyConflictException();
            var replayed = JsonSerializer.Deserialize<PortalInteractionSubmissionV1>(replay.ResponseJson, JsonOptions)
                ?? throw new ConversationStateConflictException();
            return new ConversationCommandResult<PortalInteractionSubmissionV1>(replayed with { Outcome = "REPLAYED", Replayed = true }, true);
        }

        var context = await GetOrCreateContextAsync(db, tenantId, participantId, cancellationToken);
        var maximumSequence = await db.PortalInteractionMessages
            .Where(value => value.TenantId == tenantId && value.ParticipantId == participantId)
            .Select(value => (long?)value.Sequence).MaxAsync(cancellationToken) ?? 0;
        if (request.ExpectedCursor is not null
            && _cursorCodec.Decode(request.ExpectedCursor, tenantId, context.ContextId, "portal-timeline") != maximumSequence)
        {
            throw new ConversationStateConflictException();
        }

        var customer = new PortalInteractionMessage
        {
            TenantId = tenantId, ContextId = context.ContextId, ParticipantId = participantId,
            Sequence = context.NextMessageSequence++, Actor = "CUSTOMER",
            ContentJson = JsonSerializer.Serialize(request.Content, JsonOptions),
            CurrentSurface = request.CurrentSurface, ClientMessageId = request.ClientMessageId,
        };
        var (guideText, capability) = CreateGuideResponse(request);
        var guide = new PortalInteractionMessage
        {
            TenantId = tenantId, ContextId = context.ContextId, ParticipantId = participantId,
            Sequence = context.NextMessageSequence++, Actor = "GUIDE",
            ContentJson = JsonSerializer.Serialize<IReadOnlyList<ConversationTextBlockV1>>(
                [new(SchemaVersion, "TEXT", guideText, request.Locale)], JsonOptions),
            CapabilitiesJson = JsonSerializer.Serialize<IReadOnlyList<PortalNavigationCapabilityV1>>([capability], JsonOptions),
            CurrentSurface = request.CurrentSurface,
        };
        context.UpdatedAt = DateTimeOffset.UtcNow;
        var submission = new PortalInteractionSubmissionV1(
            SchemaVersion, "PORTAL", "ACCEPTED", ToContract(customer), ToContract(guide),
            _cursorCodec.Encode(tenantId, context.ContextId, "portal-timeline", guide.Sequence), false);
        db.PortalInteractionMessages.AddRange(customer, guide);
        db.PortalInteractionIdempotencyOutcomes.Add(new PortalInteractionIdempotencyOutcome
        {
            TenantId = tenantId, ParticipantId = participantId, IdempotencyKey = idempotencyKey,
            RequestHash = requestHash, ResponseJson = JsonSerializer.Serialize(submission, JsonOptions),
        });
        await db.SaveChangesAsync(cancellationToken);
        return new ConversationCommandResult<PortalInteractionSubmissionV1>(submission, false);
    }

    private static void Validate(SendPortalInteractionMessageRequestV1 request)
    {
        if (request.SchemaVersion != SchemaVersion
            || request.ClientMessageId == Guid.Empty
            || request.Content.Count != 1
            || request.Content[0].BlockType != "TEXT"
            || string.IsNullOrWhiteSpace(request.Content[0].Text)
            || request.Content[0].Text.Length > 4000
            || string.IsNullOrWhiteSpace(request.Locale)
            || !SupportedSurfaces.Contains(request.CurrentSurface))
        {
            throw new ConversationRequestException("Portal interaction request is malformed or unsupported.");
        }
    }

    private static (string Text, PortalNavigationCapabilityV1 Capability) CreateGuideResponse(
        SendPortalInteractionMessageRequestV1 request)
    {
        var text = request.Content[0].Text;
        if (text.Contains("bill", StringComparison.OrdinalIgnoreCase)
            || text.Contains("payment", StringComparison.OrdinalIgnoreCase))
        {
            return ("I can take you to billing details. I cannot approve charges or act for an employed professional.",
                new("NAVIGATE", "Review billing", "/profile#billing"));
        }
        if (text.Contains("alert", StringComparison.OrdinalIgnoreCase))
        {
            return ("I can take you to your authoritative alerts. Open a relationship to discuss one with that professional.",
                new("NAVIGATE", "Review alerts", "/alerts"));
        }
        if (text.Contains("agent", StringComparison.OrdinalIgnoreCase)
            || text.Contains("work", StringComparison.OrdinalIgnoreCase))
        {
            return ("I can take you to My Agents. Relationship decisions and work remain inside the selected professional's conversation.",
                new("NAVIGATE", "Open My Agents", "/professionals/mine"));
        }
        var capability = request.CurrentSurface == "MARKETPLACE"
            ? new PortalNavigationCapabilityV1("NAVIGATE", "Browse professionals", "/marketplace")
            : new PortalNavigationCapabilityV1("NAVIGATE", "Open My Agents", "/professionals/mine");
        return ("I am the WAOOAW Guide. I can help you navigate and explain portal information, but I cannot impersonate a professional or execute relationship commands.", capability);
    }

    private static PortalInteractionMessageV1 ToContract(PortalInteractionMessage value) => new(
        SchemaVersion, value.MessageId, value.Sequence, value.Actor,
        JsonSerializer.Deserialize<IReadOnlyList<ConversationTextBlockV1>>(value.ContentJson, JsonOptions) ?? [],
        JsonSerializer.Deserialize<IReadOnlyList<PortalNavigationCapabilityV1>>(value.CapabilitiesJson, JsonOptions) ?? [],
        value.CurrentSurface, value.ClientMessageId, value.AcceptedAt);

    private static async Task<PortalInteractionContext> GetOrCreateContextAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        CancellationToken cancellationToken)
    {
        var existing = await db.PortalInteractionContexts.SingleOrDefaultAsync(value =>
            value.TenantId == tenantId && value.ParticipantId == participantId, cancellationToken);
        if (existing is not null) return existing;
        var created = new PortalInteractionContext { TenantId = tenantId, ParticipantId = participantId };
        db.PortalInteractionContexts.Add(created);
        await db.SaveChangesAsync(cancellationToken);
        return created;
    }
}