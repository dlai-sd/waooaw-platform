// Implements: architecture/reference/components/conversation-core.md § Public BP Contract; WC-134 R006
// constitutional_basis: C-001, C-005, C-023, C-026, C-049, C-059, C-063

using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

internal static class ConversationInputContract
{
    private static readonly Regex LanguageTagPattern = new(
        "^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*\\z",
        RegexOptions.CultureInvariant
    );

    public static bool IsLanguageTag(string? value) =>
        value is { Length: >= 2 and <= 35 } && LanguageTagPattern.IsMatch(value);

    public static bool IsPersistableText(string value) => !value.Contains('\0');
}

public sealed record ConversationTextBlockV1(
    string SchemaVersion,
    string BlockType,
    string Text,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Language = null
);

public sealed record ConversationChannelOrigin(Guid BindingId, string RecipientDigest);

public sealed record ConversationWorkItemReferenceV1(
    string Owner,
    Guid WorkItemId,
    int Revision,
    Guid InvocationId
);

public sealed record SendConversationMessageRequestV1(
    string SchemaVersion,
    Guid ClientMessageId,
    string SkillId,
    IReadOnlyList<ConversationTextBlockV1> Content,
    string Locale,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? ExpectedCursor = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? ContextVersion = null,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? PayloadDigest = null,
    string Channel = "WEB",
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        ConversationWorkItemReferenceV1? WorkItem = null
);

public sealed record UpdateConversationReadPositionRequestV1(
    string SchemaVersion,
    Guid LastVisibleMessageId,
    string AuthoritativeCursor
);

public sealed record ConversationMessageV1(
    string SchemaVersion,
    Guid MessageId,
    Guid RelationshipId,
    long Sequence,
    string Actor,
    string Channel,
    IReadOnlyList<ConversationTextBlockV1> Content,
    IReadOnlyList<JsonElement> Cards,
    string DeliveryState,
    string ProcessingState,
    string EvidenceState,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? EvidenceRecordId,
    bool Partial,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? CompletionReason,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? RetryOfMessageId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ClientMessageId,
    DateTimeOffset AcceptedAt,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        DateTimeOffset? CompletedAt
);

public sealed record ConversationTimelinePageV1(
    string SchemaVersion,
    Guid RelationshipId,
    IReadOnlyList<ConversationMessageV1> Items,
    string AuthoritativeCursor,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? NextCursor,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        Guid? UnreadBoundaryMessageId,
    bool HasMore,
    DateTimeOffset ServerTime
);

public sealed record ConversationSubmissionV1(
    string SchemaVersion,
    string Outcome,
    ConversationMessageV1 Message,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ExecutionId,
    string AuthoritativeCursor,
    bool Replayed
);

public sealed record ConversationReadPositionV1(
    string SchemaVersion,
    Guid RelationshipId,
    Guid LastReadMessageId,
    DateTimeOffset UpdatedAt
);

public sealed record ConversationExecutionStatusV1(
    string SchemaVersion,
    Guid ExecutionId,
    string State,
    bool Partial,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        string? CompletionReason,
    DateTimeOffset UpdatedAt,
    long ProjectionVersion = 0
);

public sealed record ConversationExecutionCallerV1(
    Guid TenantId,
    Guid RelationshipId,
    Guid ActorId,
    string ActorRole,
    string ConstitutionalDecisionRef,
    Guid RuntimeExecutionId
);

public sealed record ConversationStreamEventV1(
    string SchemaVersion,
    string EventId,
    string EventType,
    Guid RelationshipId,
    long Sequence,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? MessageId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ExecutionId,
    DateTimeOffset OccurredAt,
    JsonElement Data
);

public sealed record ConversationCommandResult<T>(T Value, bool Replayed);

public sealed record OperationalMandateV1(
    string SchemaVersion,
    Guid MandateId,
    string MandateDigest,
    Guid TenantId,
    Guid RelationshipId,
    Guid AgentInstanceId,
    Guid ActorId,
    string ActorRole,
    string RelationshipLifecycle,
    string EngagementMode,
    string ProfessionalType,
    int ReleaseSequence,
    string ProfessionalVersion,
    string SpecificationRevision,
    string SpecificationDigest,
    int AdmissionRevision,
    string AdmissionContentDigest,
    string ArtifactDigest,
    string BaseSpecVersion,
    string ConstitutionalDnaVersion,
    string PacVersion,
    string AdapterProtocolVersion,
    string CustomerContractDigest,
    string SkillId,
    string SkillVersion,
    string InputSchemaDigest,
    string OutputSchemaDigest,
    string PromptVersion,
    string PromptDigest,
    int ContextRevision,
    int ConfigurationRevision,
    int GoalRevision,
    int DecisionSpaceRevision,
    string BudgetAllowanceRef,
    int ReviewPolicyRevision,
    IReadOnlyList<string> ApprovalRefs,
    bool Stopped,
    string? StopEvidenceRef,
    string OperationalPurpose,
    IReadOnlyList<string> PermittedActions,
    IReadOnlyList<string> Exclusions,
    DateTimeOffset Deadline,
    Guid IdempotencyIdentity,
    string ConstitutionalDecisionRef,
    string ConstitutionalEvidenceRef,
    string? BillingReservationRef,
    string? BillingAttributionRef,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
        ConversationOperationBindingV1? ConversationOperation = null
);

public sealed class ConversationNotAccessibleException : Exception;

public sealed class ConversationIdempotencyConflictException : Exception;

public sealed class ConversationStateConflictException : Exception;

public sealed class ConversationCursorExpiredException : Exception;

public sealed class ConversationRetryNotAllowedException : Exception;

public sealed class ConversationStoppedException : Exception;

public sealed class ConversationExecutionUnavailableException : Exception;

public sealed class OperationalMandateUnavailableException : Exception;

public sealed class ConversationRequestException(string message) : Exception(message);

public sealed class ConversationCursorOptions
{
    public string HmacKey { get; set; } = string.Empty;
    public string CursorHmacKey { get; set; } = string.Empty;
    public string[] PreviousHmacKeys { get; set; } = [];

    public string EffectiveHmacKey =>
        string.IsNullOrWhiteSpace(CursorHmacKey) ? HmacKey : CursorHmacKey;
}

public sealed class ConversationCursorOptionsValidator : IValidateOptions<ConversationCursorOptions>
{
    public ValidateOptionsResult Validate(string? name, ConversationCursorOptions options)
    {
        var errors = new List<string>();
        if (options.EffectiveHmacKey.Length < 32)
            errors.Add("Conversation:CursorHmacKey must contain at least 32 characters.");
        if (options.PreviousHmacKeys.Any(key => string.IsNullOrWhiteSpace(key) || key.Length < 32))
            errors.Add(
                "Conversation:PreviousHmacKeys must contain keys of at least 32 characters."
            );
        return errors.Count == 0
            ? ValidateOptionsResult.Success
            : ValidateOptionsResult.Fail(errors);
    }
}

public sealed class ConversationCursorHealthCheck(
    IOptions<ConversationCursorOptions> options,
    IValidateOptions<ConversationCursorOptions> validator
) : IHealthCheck
{
    public Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default
    )
    {
        var result = validator.Validate(Options.DefaultName, options.Value);
        return Task.FromResult(
            result.Succeeded
                ? HealthCheckResult.Healthy()
                : HealthCheckResult.Unhealthy(
                    "Conversation cursor signing configuration is invalid."
                )
        );
    }
}

public interface IConversationExecutionGateway
{
    Task StartAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        Guid relationshipId,
        string locale,
        IReadOnlyList<ConversationTextBlockV1> content,
        OperationalMandateV1 operationalMandate,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    );

    Task<ConversationExecutionStatusV1> CancelAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        ConversationExecutionCallerV1 caller,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    );
}

public interface IOperationalMandateResolver
{
    Task<OperationalMandateReadiness> GetReadinessAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    );

    Task<OperationalMandateV1> ResolveAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        Guid constitutionalEvidenceId,
        string skillId,
        string operationalPurpose,
        CancellationToken cancellationToken
    );
}

public sealed record OperationalMandateReadiness(bool Ready, IReadOnlyList<string> BlockedReasons);

public sealed class UnconfiguredOperationalMandateResolver : IOperationalMandateResolver
{
    public Task<OperationalMandateReadiness> GetReadinessAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    ) =>
        Task.FromResult(
            new OperationalMandateReadiness(
                false,
                ["The admitted artifact and runtime binding coordinates are unavailable."]
            )
        );

    public Task<OperationalMandateV1> ResolveAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        Guid constitutionalEvidenceId,
        string skillId,
        string operationalPurpose,
        CancellationToken cancellationToken
    ) => throw new OperationalMandateUnavailableException();
}

public sealed class UnconfiguredConversationExecutionGateway : IConversationExecutionGateway
{
    public Task StartAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        Guid relationshipId,
        string locale,
        IReadOnlyList<ConversationTextBlockV1> content,
        OperationalMandateV1 operationalMandate,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    ) => throw new ConversationExecutionUnavailableException();

    public Task<ConversationExecutionStatusV1> CancelAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        ConversationExecutionCallerV1 caller,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    ) => throw new ConversationExecutionUnavailableException();
}

public sealed class ConversationCursorCodec
{
    private readonly byte[] _key;
    private readonly IReadOnlyList<byte[]> _verificationKeys;

    public ConversationCursorCodec(IOptions<ConversationCursorOptions> options)
    {
        var effectiveKey = options.Value.EffectiveHmacKey;
        if (string.IsNullOrWhiteSpace(effectiveKey) || effectiveKey.Length < 32)
        {
            throw new InvalidOperationException(
                "Conversation:CursorHmacKey must contain at least 32 characters."
            );
        }

        _key = Encoding.UTF8.GetBytes(effectiveKey);
        if (
            options.Value.PreviousHmacKeys.Any(key =>
                string.IsNullOrWhiteSpace(key) || key.Length < 32
            )
        )
        {
            throw new InvalidOperationException(
                "Conversation:PreviousHmacKeys must contain keys of at least 32 characters."
            );
        }
        _verificationKeys =
        [
            _key,
            .. options.Value.PreviousHmacKeys.Distinct().Select(Encoding.UTF8.GetBytes),
        ];
    }

    public string Encode(Guid tenantId, Guid relationshipId, string purpose, long sequence)
    {
        var payload = $"{tenantId:D}|{relationshipId:D}|{purpose}|{sequence}";
        var payloadBytes = Encoding.UTF8.GetBytes(payload);
        var signature = HMACSHA256.HashData(_key, payloadBytes);
        return $"{Base64UrlEncode(payloadBytes)}.{Base64UrlEncode(signature)}";
    }

    public long Decode(string cursor, Guid tenantId, Guid relationshipId, string purpose)
    {
        var parts = cursor.Split('.', StringSplitOptions.RemoveEmptyEntries);
        if (parts.Length != 2)
        {
            throw new ConversationCursorExpiredException();
        }

        try
        {
            var payloadBytes = Base64UrlDecode(parts[0]);
            var suppliedSignature = Base64UrlDecode(parts[1]);
            if (
                !_verificationKeys.Any(key =>
                    CryptographicOperations.FixedTimeEquals(
                        suppliedSignature,
                        HMACSHA256.HashData(key, payloadBytes)
                    )
                )
            )
            {
                throw new ConversationCursorExpiredException();
            }

            var fields = Encoding.UTF8.GetString(payloadBytes).Split('|');
            if (
                fields.Length != 4
                || fields[0] != tenantId.ToString("D")
                || fields[1] != relationshipId.ToString("D")
                || fields[2] != purpose
                || !long.TryParse(fields[3], out var sequence)
                || sequence < 0
            )
            {
                throw new ConversationCursorExpiredException();
            }

            return sequence;
        }
        catch (FormatException)
        {
            throw new ConversationCursorExpiredException();
        }
    }

    private static string Base64UrlEncode(byte[] value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

    private static byte[] Base64UrlDecode(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        padded += new string('=', (4 - padded.Length % 4) % 4);
        return Convert.FromBase64String(padded);
    }
}

public sealed class ConversationService
{
    private const string SchemaVersion = "1.0";
    private static readonly ActivitySource ActivitySource = new(
        "waooaw.business-platform.conversation"
    );
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    private readonly IDbContextFactory<ConversationStoreDbContext> _conversationFactory;
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _relationshipFactory;
    private readonly IRelationshipConstitutionalGateway _constitutionalGateway;
    private readonly IConversationExecutionGateway _executionGateway;
    private readonly IOperationalMandateResolver _mandateResolver;
    private readonly ConversationCursorCodec _cursorCodec;
    private readonly ConversationStopFence? _stopFence;
    private readonly IConversationReferenceResolver? _referenceResolver;
    private readonly string _environment;
    private readonly ConversationRuntimeIdentityAuthority? _runtimeIdentity;
    private readonly bool _runtimeIngestionEnabled;
    private readonly WhatsAppTenantExecutionScope? _whatsAppExecution;
    private readonly WhatsAppRelationshipRouting? _whatsAppRouting;
    private readonly IConversationBatchTaskResolver? _batchTaskResolver;
    private readonly ConversationBatchingOptions _batching;

    public ConversationService(
        IDbContextFactory<ConversationStoreDbContext> conversationFactory,
        IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory,
        IRelationshipConstitutionalGateway constitutionalGateway,
        IConversationExecutionGateway executionGateway,
        IOperationalMandateResolver mandateResolver,
        ConversationCursorCodec cursorCodec,
        ConversationStopFence? stopFence = null,
        IConversationReferenceResolver? referenceResolver = null,
        IOptions<Wc120ConversationOptions>? conversationOptions = null,
        ConversationRuntimeIdentityAuthority? runtimeIdentity = null,
        WhatsAppTenantExecutionScope? whatsAppExecution = null,
        WhatsAppRelationshipRouting? whatsAppRouting = null,
        IConversationBatchTaskResolver? batchTaskResolver = null,
        IOptions<ConversationBatchingOptions>? batchingOptions = null
    )
    {
        _conversationFactory = conversationFactory;
        _relationshipFactory = relationshipFactory;
        _constitutionalGateway = constitutionalGateway;
        _executionGateway = executionGateway;
        _mandateResolver = mandateResolver;
        _cursorCodec = cursorCodec;
        _stopFence = stopFence;
        _referenceResolver = referenceResolver;
        _runtimeIdentity = runtimeIdentity;
        _whatsAppExecution = whatsAppExecution;
        _whatsAppRouting = whatsAppRouting;
        _batchTaskResolver = batchTaskResolver;
        _batching = batchingOptions?.Value ?? new ConversationBatchingOptions();
        _runtimeIngestionEnabled = conversationOptions?.Value.RuntimeEventIngestionEnabled == true;
        _environment =
            conversationOptions?.Value.Enabled == true
                ? conversationOptions.Value.Environment
                : "legacy";
    }

    public async Task<ConversationProjection> EnsureConversationAsync(
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken,
        Guid? preparedConversationId = null
    )
    {
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var conversation = await GetOrCreateConversationAsync(
            db,
            tenantId,
            relationshipId,
            cancellationToken,
            preparedConversationId
        );
        try
        {
            await db.SaveChangesAsync(cancellationToken);
            return conversation;
        }
        catch (DbUpdateException)
        {
            await using var replayDb = await _conversationFactory.CreateDbContextAsync(
                cancellationToken
            );
            return await replayDb.Conversations.SingleAsync(
                value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                cancellationToken
            );
        }
    }

    public async Task<ConversationTimelinePageV1> ListMessagesAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string? cursor,
        string? afterCursor,
        int limit,
        CancellationToken cancellationToken
    )
    {
        using var activity = StartActivity("bp.conversation.timeline", relationshipId);
        if (limit is < 1 or > 100)
        {
            throw new ConversationRequestException("limit must be between 1 and 100.");
        }

        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            _environment,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var conversation = await db
            .Conversations.AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                cancellationToken
            );
        if (conversation is null)
        {
            WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
            return new ConversationTimelinePageV1(
                SchemaVersion,
                relationshipId,
                [],
                _cursorCodec.Encode(tenantId, relationshipId, "timeline", 0),
                null,
                null,
                false,
                DateTimeOffset.UtcNow
            );
        }

        var query = db
            .Messages.AsNoTracking()
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId);
        if (cursor is not null)
        {
            var before = _cursorCodec.Decode(cursor, tenantId, relationshipId, "timeline");
            query = query.Where(value => value.Sequence < before);
        }
        else if (afterCursor is not null)
        {
            var after = _cursorCodec.Decode(afterCursor, tenantId, relationshipId, "timeline");
            query = query.Where(value => value.Sequence > after);
        }

        var descending = await query
            .OrderByDescending(value => value.Sequence)
            .Take(limit + 1)
            .ToListAsync(cancellationToken);
        var hasMore = descending.Count > limit;
        var selected = descending.Take(limit).OrderBy(value => value.Sequence).ToList();
        var maximumSequence =
            await db
                .Messages.Where(value =>
                    value.TenantId == tenantId && value.RelationshipId == relationshipId
                )
                .Select(value => (long?)value.Sequence)
                .MaxAsync(cancellationToken)
            ?? 0;
        var readSequence =
            await db
                .ReadPositions.AsNoTracking()
                .Where(value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ParticipantId == participantId
                )
                .Select(value => (long?)value.LastReadSequence)
                .SingleOrDefaultAsync(cancellationToken)
            ?? 0;
        var unreadBoundary = await db
            .Messages.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Sequence > readSequence
            )
            .OrderBy(value => value.Sequence)
            .Select(value => (Guid?)value.MessageId)
            .FirstOrDefaultAsync(cancellationToken);
        var nextCursor =
            hasMore && selected.Count > 0
                ? _cursorCodec.Encode(tenantId, relationshipId, "timeline", selected[0].Sequence)
                : null;

        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        return new ConversationTimelinePageV1(
            SchemaVersion,
            relationshipId,
            selected.Select(ToContract).ToList(),
            _cursorCodec.Encode(tenantId, relationshipId, "timeline", maximumSequence),
            nextCursor,
            unreadBoundary,
            hasMore,
            DateTimeOffset.UtcNow
        );
    }

    public async Task<string> ResolveChannelSkillAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken,
        Guid? idempotencyKey = null
    )
    {
        var relationship = await EnsureAccessAsync(
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        EnsureRelationshipNotStopped(relationship);
        await using var conversations = await _conversationFactory.CreateDbContextAsync(
            cancellationToken
        );
        await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            conversations,
            _environment,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        if (idempotencyKey.HasValue)
        {
            var replay = await FindIdempotencyAsync(
                conversations,
                tenantId,
                participantId,
                relationshipId,
                "SEND",
                idempotencyKey.Value,
                cancellationToken
            );
            if (replay is not null)
            {
                var originalSkill =
                    await conversations
                        .Messages.AsNoTracking()
                        .Where(value =>
                            value.Environment == _environment
                            && value.TenantId == tenantId
                            && value.RelationshipId == relationshipId
                            && value.MessageId == replay.MessageId
                        )
                        .Select(value => value.SkillId)
                        .SingleOrDefaultAsync(cancellationToken)
                    ?? throw new ConversationContextConflictException(
                        "CONVERSATION_REPLAY_UNAVAILABLE"
                    );
                WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
                return originalSkill;
            }
        }
        await using var relationships = await _relationshipFactory.CreateDbContextAsync(
            cancellationToken
        );
        var skills = await relationships
            .RelationshipSkillConfigurations.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Status == "ACCEPTED"
                && value.Applicability == "APPLICABLE"
                && (value.AuthorityState == "GRANTED" || value.AuthorityState == "CONSTRAINED")
            )
            .Select(value => value.SkillId)
            .Distinct()
            .ToListAsync(cancellationToken);
        if (skills.Any(string.IsNullOrWhiteSpace))
            throw new ConversationContextConflictException("CONVERSATION_SKILL_SELECTION_REQUIRED");
        if (skills.Count == 1)
        {
            WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
            return skills[0];
        }
        if (skills.Count > 1)
        {
            var current = await conversations
                .Messages.AsNoTracking()
                .Where(value =>
                    value.Environment == _environment
                    && value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.Actor == "CUSTOMER"
                )
                .OrderByDescending(value => value.Sequence)
                .Select(value => value.SkillId)
                .FirstOrDefaultAsync(cancellationToken);
            if (current is not null && skills.Contains(current, StringComparer.Ordinal))
            {
                WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
                return current;
            }
        }
        throw new ConversationContextConflictException("CONVERSATION_SKILL_SELECTION_REQUIRED");
    }

    public async Task<ConversationCommandResult<ConversationSubmissionV1>> SendAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        SendConversationMessageRequestV1 request,
        CancellationToken cancellationToken,
        ConversationChannelOrigin? channelOrigin = null
    )
    {
        using var activity = StartActivity("bp.conversation.send", relationshipId);
        ValidateSendRequest(request);
        if (
            request.Channel == "WHATSAPP"
            && (
                channelOrigin is null
                || channelOrigin.BindingId == Guid.Empty
                || channelOrigin.RecipientDigest.Length != 64
                || channelOrigin.RecipientDigest.Any(character =>
                    !(
                        (character >= '0' && character <= '9')
                        || (character >= 'a' && character <= 'f')
                    )
                )
            )
        )
            throw new ConversationNotAccessibleException();
        if (request.Channel != "WHATSAPP" && channelOrigin is not null)
            throw new ConversationStateConflictException();
        if (_stopFence is not null)
            await _stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
        var relationship = await EnsureAccessAsync(
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        if (channelOrigin is not null)
        {
            await using var channels = await _relationshipFactory.CreateDbContextAsync(
                cancellationToken
            );
            if (
                !await channels.ChannelBindings.AnyAsync(
                    binding =>
                        binding.BindingId == channelOrigin.BindingId
                        && binding.TenantId == tenantId
                        && binding.RelationshipId == relationshipId
                        && binding.ParticipantId == participantId
                        && binding.Channel == "WHATSAPP"
                        && binding.Status == "ACTIVE"
                        && binding.ExternalSubjectHash == channelOrigin.RecipientDigest,
                    cancellationToken
                )
            )
                throw new ConversationNotAccessibleException();
        }
        var requestHash = HashCanonical(request);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var replay = await FindIdempotencyAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            "SEND",
            idempotencyKey,
            cancellationToken
        );
        if (replay is not null)
        {
            EnsureMatchingHash(replay, requestHash);
            await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
                _whatsAppExecution,
                _whatsAppRouting,
                db,
                _environment,
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
            var retainedSubmission = await GetSendReplayAsync(
                db,
                tenantId,
                relationshipId,
                replay,
                cancellationToken
            );
            WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
            return new ConversationCommandResult<ConversationSubmissionV1>(
                retainedSubmission,
                true
            );
        }

        EnsureRelationshipNotStopped(relationship);
        var evidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "SEND_CONVERSATION_MESSAGE",
            idempotencyKey,
            new
            {
                client_message_id = request.ClientMessageId,
                locale = request.Locale,
                request_hash = requestHash,
            },
            cancellationToken
        );
        var operationalMandate = await _mandateResolver.ResolveAsync(
            tenantId,
            participantId,
            relationshipId,
            idempotencyKey,
            evidenceId,
            request.SkillId,
            request.Content[0].Text,
            cancellationToken
        );
        ConversationBatchTaskIdentity? batchTask = null;
        if (
            _batching.Enabled
            && request.Channel == "WHATSAPP"
            && channelOrigin is not null
            && _batchTaskResolver is not null
            && request.Content.Count == 1
            && request.Content[0].BlockType == "TEXT"
            && request.Content[0].Text.Length <= _batching.MaximumTextLength
        )
        {
            batchTask = await _batchTaskResolver.ResolveFreshAsync(
                new(
                    tenantId,
                    relationshipId,
                    participantId,
                    operationalMandate.ActorRole,
                    relationship.StateVersion,
                    operationalMandate.AgentInstanceId,
                    request.SkillId,
                    operationalMandate.SkillVersion,
                    idempotencyKey,
                    request.WorkItem
                ),
                cancellationToken
            );
        }

        await using var admissionTransaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(cancellationToken)
            : null;
        ConversationRuntimeMembership? runtimeMembership = null;
        var conversation = await GetOrCreateConversationAsync(
            db,
            tenantId,
            relationshipId,
            cancellationToken
        );
        var references = _referenceResolver is null
            ? null
            : await _referenceResolver.ResolveAsync(
                tenantId,
                participantId,
                relationshipId,
                conversation.ConversationId,
                request.SkillId,
                request.ContextVersion,
                request.Channel,
                cancellationToken
            );
        await WhatsAppRelationshipRouting.RequireIngressCommitAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            tenantId,
            participantId,
            relationshipId,
            conversation.ConversationId,
            request.Channel,
            channelOrigin?.BindingId,
            channelOrigin?.RecipientDigest,
            cancellationToken
        );
        if (admissionTransaction is not null && (_runtimeIngestionEnabled || batchTask is not null))
        {
            if (_runtimeIdentity is null)
                throw new ConversationExecutionUnavailableException();
            runtimeMembership = await _runtimeIdentity.ResolveAsync(
                db,
                tenantId,
                participantId,
                cancellationToken
            );
        }
        if (admissionTransaction is not null)
        {
            await ConversationPendingStartAdmission.LockConversationAsync(
                db,
                conversation.Environment,
                tenantId,
                relationshipId,
                cancellationToken
            );
            if (db.Entry(conversation).State != EntityState.Added)
                await db.Entry(conversation).ReloadAsync(cancellationToken);
        }
        var message = new ConversationMessage
        {
            Environment = conversation.Environment,
            TenantId = tenantId,
            ConversationId = conversation.ConversationId,
            RelationshipId = relationshipId,
            Sequence = conversation.NextMessageSequence++,
            SkillId = request.SkillId,
            Channel = request.Channel,
            ContentJson = JsonSerializer.Serialize(
                request
                    .Content.Select(block =>
                        block with
                        {
                            Language = block.Language ?? request.Locale,
                        }
                    )
                    .ToArray(),
                JsonOptions
            ),
            InteractionContextJson = references is null
                ? "{}"
                : JsonSerializer.Serialize(references.Context, JsonOptions),
            ConversationPolicyJson = references is null
                ? "{}"
                : JsonSerializer.Serialize(references.Policy, JsonOptions),
            ClientMessageId = request.ClientMessageId,
            EvidenceState = "RECORDED",
            EvidenceRecordId = evidenceId,
        };
        var execution = new ConversationExecution
        {
            ExecutionId = ConversationExecutionIdentity.Create(
                tenantId,
                relationshipId,
                participantId,
                conversation.ConversationId,
                idempotencyKey
            ),
            TenantId = tenantId,
            ConversationId = conversation.ConversationId,
            RelationshipId = relationshipId,
            MessageId = message.MessageId,
            OriginChannelBindingId = channelOrigin?.BindingId,
            OriginRecipientDigest = channelOrigin?.RecipientDigest,
            RuntimeActorIssuer = runtimeMembership?.Issuer,
            RuntimeMembershipId = runtimeMembership?.MembershipId,
            RuntimeAccountId = runtimeMembership?.AccountId,
            RuntimeActorId = runtimeMembership is null ? null : participantId,
        };
        var conversationEvent = CreateEvent(
            conversation,
            tenantId,
            relationshipId,
            "message.accepted",
            message.MessageId,
            execution.ExecutionId,
            new { message = ToContract(message) }
        );
        conversation.UpdatedAt = DateTimeOffset.UtcNow;
        var submission = CreateSubmission(
            tenantId,
            relationshipId,
            message,
            execution,
            "ACCEPTED",
            false
        );
        var idempotency = CreateIdempotency(
            tenantId,
            participantId,
            relationshipId,
            "SEND",
            idempotencyKey,
            requestHash,
            submission,
            message.MessageId,
            execution.ExecutionId
        );
        db.Messages.Add(message);
        db.Executions.Add(execution);
        db.Events.Add(conversationEvent);
        db.IdempotencyOutcomes.Add(idempotency);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
            if (batchTask is not null)
            {
                await ConversationPendingStartAdmission.InsertAsync(
                    db,
                    new(
                        conversation.Environment,
                        tenantId,
                        relationshipId,
                        conversation.ConversationId,
                        message.MessageId,
                        execution.ExecutionId,
                        participantId,
                        idempotencyKey,
                        evidenceId,
                        operationalMandate.MandateId,
                        batchTask
                    ),
                    _batching.ToLimits().MaximumWait,
                    cancellationToken
                );
            }
        }
        catch (DbUpdateException)
        {
            if (admissionTransaction is not null)
                await admissionTransaction.RollbackAsync(cancellationToken);
            await using var replayDb = await _conversationFactory.CreateDbContextAsync(
                cancellationToken
            );
            var concurrentOutcome = await FindIdempotencyAsync(
                replayDb,
                tenantId,
                participantId,
                relationshipId,
                "SEND",
                idempotencyKey,
                cancellationToken
            );
            if (concurrentOutcome is null)
            {
                throw new ConversationStateConflictException();
            }

            EnsureMatchingHash(concurrentOutcome, requestHash);
            return new ConversationCommandResult<ConversationSubmissionV1>(
                await GetSendReplayAsync(
                    replayDb,
                    tenantId,
                    relationshipId,
                    concurrentOutcome,
                    cancellationToken
                ),
                true
            );
        }

        if (admissionTransaction is not null)
        {
            if (_whatsAppExecution?.ServiceTenantId is not null)
                _whatsAppExecution.RequireUnchangedAuthority();
            await admissionTransaction.CommitAsync(cancellationToken);
            await admissionTransaction.DisposeAsync();
        }
        if (batchTask is not null)
            return new ConversationCommandResult<ConversationSubmissionV1>(submission, false);
        await WhatsAppRelationshipRouting.RequireIngressDispatchAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            cancellationToken
        );
        try
        {
            if (_stopFence is not null)
                await _stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
            await _executionGateway.StartAsync(
                conversation.ConversationId,
                execution.ExecutionId,
                message.MessageId,
                relationshipId,
                request.Locale,
                request.Content,
                operationalMandate,
                idempotencyKey,
                cancellationToken
            );
            return new ConversationCommandResult<ConversationSubmissionV1>(submission, false);
        }
        catch (ConversationStoppedException)
        {
            await RecordStoppedExecutionAsync(
                db,
                conversation,
                message,
                execution,
                idempotency,
                cancellationToken
            );
            throw;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            message.DeliveryState = "UNRESOLVED";
            message.ProcessingState = "FAILED";
            execution.ProcessingState = "FAILED";
            execution.UpdatedAt = DateTimeOffset.UtcNow;
            idempotency.Outcome = "UNRESOLVED";
            var unresolved = CreateSubmission(
                tenantId,
                relationshipId,
                message,
                execution,
                "UNRESOLVED",
                false
            );
            idempotency.ResponseJson = JsonSerializer.Serialize(unresolved, JsonOptions);
            db.Events.Add(
                CreateEvent(
                    conversation,
                    tenantId,
                    relationshipId,
                    "message.failed",
                    message.MessageId,
                    execution.ExecutionId,
                    new
                    {
                        code = "CONVERSATION_EXECUTION_UNAVAILABLE",
                        retryable = true,
                        partial = false,
                    }
                )
            );
            await db.SaveChangesAsync(cancellationToken);
            throw new ConversationExecutionUnavailableException();
        }
    }

    public async Task<ConversationCommandResult<ConversationSubmissionV1>> RetryAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid messageId,
        Guid originalIdempotencyKey,
        CancellationToken cancellationToken
    )
    {
        using var activity = StartActivity("bp.conversation.retry", relationshipId);
        if (_stopFence is not null)
            await _stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
        var relationship = await EnsureAccessAsync(
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        EnsureRelationshipNotStopped(relationship);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var original = await FindIdempotencyAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            "SEND",
            originalIdempotencyKey,
            cancellationToken
        );
        var message = await db.Messages.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.MessageId == messageId,
            cancellationToken
        );
        if (original is null || message is null || original.MessageId != messageId)
        {
            throw new ConversationRetryNotAllowedException();
        }

        var execution = await db.Executions.SingleAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.MessageId == messageId,
            cancellationToken
        );
        var routedRetry =
            _whatsAppExecution?.CurrentTenantId is { } selectedTenant
            && selectedTenant != _whatsAppExecution.ServiceTenantId;
        if (
            routedRetry
            && (execution.OriginChannelBindingId is null || execution.OriginRecipientDigest is null)
        )
            throw new ConversationRetryNotAllowedException();
        var priorRequestHash = original.RequestHash;
        var priorBindingId = execution.OriginChannelBindingId;
        var priorRecipient = execution.OriginRecipientDigest;
        if (message.ProcessingState == "STOPPED" || execution.ProcessingState == "STOPPED")
            throw new ConversationStoppedException();
        if (message.ProcessingState == "CANCELLED" || execution.ProcessingState == "CANCELLED")
            throw new ConversationRetryNotAllowedException();
        if (
            message.ProcessingState == "COMPLETED"
            || (
                execution.ProcessingState == "FAILED"
                && execution.CompletionReason == "PARTIAL_FAILURE"
            )
        )
        {
            await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
                _whatsAppExecution,
                _whatsAppRouting,
                db,
                _environment,
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
            if (routingRead is not null)
            {
                await db.Entry(message).ReloadAsync(cancellationToken);
                await db.Entry(execution).ReloadAsync(cancellationToken);
            }
            WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
            return new ConversationCommandResult<ConversationSubmissionV1>(
                CreateSubmission(tenantId, relationshipId, message, execution, "REPLAYED", true),
                true
            );
        }

        if (
            message.DeliveryState is not ("FAILED" or "UNRESOLVED")
            && message.ProcessingState is not "FAILED"
        )
        {
            throw new ConversationRetryNotAllowedException();
        }
        if (
            routedRetry
            && (message.DeliveryState == "UNRESOLVED" || original.Outcome == "UNRESOLVED")
        )
            throw new ConversationRetryNotAllowedException();

        var retryEvidenceId = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "RETRY_CONVERSATION_MESSAGE",
            originalIdempotencyKey,
            new { message_id = messageId, request_hash = original.RequestHash },
            cancellationToken
        );
        var retryContent = ToContract(message).Content;
        var retryMandate = await _mandateResolver.ResolveAsync(
            tenantId,
            participantId,
            relationshipId,
            originalIdempotencyKey,
            retryEvidenceId,
            message.SkillId,
            retryContent[0].Text,
            cancellationToken
        );
        await using var retryAdmission =
            routedRetry && db.Database.IsRelational()
                ? await db.Database.BeginTransactionAsync(cancellationToken)
                : null;
        await WhatsAppRelationshipRouting.RequireIngressCommitAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            tenantId,
            participantId,
            relationshipId,
            execution.ConversationId,
            message.Channel,
            execution.OriginChannelBindingId,
            execution.OriginRecipientDigest,
            cancellationToken
        );
        if (routedRetry)
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT message_id FROM business.conversation_messages WHERE tenant_id = {tenantId} AND relationship_id = {relationshipId} AND message_id = {messageId} FOR UPDATE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id = {tenantId} AND relationship_id = {relationshipId} AND execution_id = {execution.ExecutionId} FOR UPDATE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT idempotency_key FROM business.conversation_idempotency_outcomes WHERE tenant_id = {tenantId} AND relationship_id = {relationshipId} AND actor_participant_id = {participantId} AND operation_family = 'SEND' AND idempotency_key = {originalIdempotencyKey} FOR UPDATE",
                cancellationToken
            );
            await db.Entry(message).ReloadAsync(cancellationToken);
            await db.Entry(execution).ReloadAsync(cancellationToken);
            await db.Entry(original).ReloadAsync(cancellationToken);
            if (
                db.Entry(message).State == EntityState.Detached
                || db.Entry(execution).State == EntityState.Detached
                || db.Entry(original).State == EntityState.Detached
                || original.RequestHash != priorRequestHash
                || original.MessageId != messageId
                || execution.MessageId != messageId
                || execution.ConversationId != message.ConversationId
                || execution.OriginChannelBindingId != priorBindingId
                || execution.OriginRecipientDigest != priorRecipient
            )
                throw new ConversationRetryNotAllowedException();
            if (message.ProcessingState == "STOPPED" || execution.ProcessingState == "STOPPED")
                throw new ConversationStoppedException();
            if (
                message.ProcessingState is "COMPLETED" or "CANCELLED"
                || execution.ProcessingState is "COMPLETED" or "CANCELLED"
                || execution.CompletionReason == "PARTIAL_FAILURE"
                || message.DeliveryState == "UNRESOLVED"
                || original.Outcome == "UNRESOLVED"
                || message.DeliveryState is not ("FAILED" or "UNRESOLVED")
                    && message.ProcessingState != "FAILED"
            )
                throw new ConversationRetryNotAllowedException();
        }
        message.DeliveryState = "ACCEPTED";
        message.ProcessingState = "QUEUED";
        execution.ProcessingState = "QUEUED";
        execution.UpdatedAt = DateTimeOffset.UtcNow;
        original.Outcome = "ACCEPTED";
        var conversation = await db.Conversations.SingleAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken
        );
        var submission = CreateSubmission(
            tenantId,
            relationshipId,
            message,
            execution,
            "ACCEPTED",
            false
        );
        original.ResponseJson = JsonSerializer.Serialize(submission, JsonOptions);
        db.Events.Add(
            CreateEvent(
                conversation,
                tenantId,
                relationshipId,
                "processing.started",
                message.MessageId,
                execution.ExecutionId,
                new { messageId = message.MessageId, executionId = execution.ExecutionId }
            )
        );
        await db.SaveChangesAsync(cancellationToken);

        if (retryAdmission is not null)
        {
            if (_whatsAppExecution?.ServiceTenantId is not null)
                _whatsAppExecution.RequireUnchangedAuthority();
            await retryAdmission.CommitAsync(cancellationToken);
            await retryAdmission.DisposeAsync();
        }
        await WhatsAppRelationshipRouting.RequireIngressDispatchAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            cancellationToken
        );
        try
        {
            if (_stopFence is not null)
                await _stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
            await _executionGateway.StartAsync(
                conversation.ConversationId,
                execution.ExecutionId,
                message.MessageId,
                relationshipId,
                ExtractLocale(message),
                retryContent,
                retryMandate,
                originalIdempotencyKey,
                cancellationToken
            );
            return new ConversationCommandResult<ConversationSubmissionV1>(submission, false);
        }
        catch (ConversationStoppedException)
        {
            await RecordStoppedExecutionAsync(
                db,
                conversation,
                message,
                execution,
                original,
                cancellationToken
            );
            throw;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            message.DeliveryState = "UNRESOLVED";
            message.ProcessingState = "FAILED";
            execution.ProcessingState = "FAILED";
            execution.UpdatedAt = DateTimeOffset.UtcNow;
            original.Outcome = "UNRESOLVED";
            original.ResponseJson = JsonSerializer.Serialize(
                CreateSubmission(tenantId, relationshipId, message, execution, "UNRESOLVED", false),
                JsonOptions
            );
            db.Events.Add(
                CreateEvent(
                    conversation,
                    tenantId,
                    relationshipId,
                    "message.failed",
                    message.MessageId,
                    execution.ExecutionId,
                    new
                    {
                        code = "CONVERSATION_EXECUTION_UNAVAILABLE",
                        retryable = true,
                        partial = false,
                    }
                )
            );
            await db.SaveChangesAsync(cancellationToken);
            throw new ConversationExecutionUnavailableException();
        }
    }

    public async Task<
        ConversationCommandResult<ConversationReadPositionV1>
    > UpdateReadPositionAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        UpdateConversationReadPositionRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        using var activity = StartActivity("bp.conversation.read_position", relationshipId);
        // codeql[cs/user-controlled-bypass] Exact allowlist validation rejects unsupported client schemas.
        if (request.SchemaVersion != SchemaVersion)
        {
            throw new ConversationRequestException("Unsupported schemaVersion.");
        }

        var relationship = await EnsureAccessAsync(
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var requestHash = HashCanonical(request);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var replay = await FindIdempotencyAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            "READ_POSITION",
            idempotencyKey,
            cancellationToken
        );
        if (replay is not null)
        {
            EnsureMatchingHash(replay, requestHash);
            await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
                _whatsAppExecution,
                _whatsAppRouting,
                db,
                _environment,
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
            WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
            return new ConversationCommandResult<ConversationReadPositionV1>(
                Deserialize<ConversationReadPositionV1>(replay.ResponseJson),
                true
            );
        }

        var observedSequence = _cursorCodec.Decode(
            request.AuthoritativeCursor,
            tenantId,
            relationshipId,
            "timeline"
        );
        var message = await db
            .Messages.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.MessageId == request.LastVisibleMessageId,
                cancellationToken
            );
        if (message is null)
        {
            throw new ConversationNotAccessibleException();
        }

        if (message.Sequence > observedSequence)
        {
            throw new ConversationStateConflictException();
        }

        var current = await db.ReadPositions.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId,
            cancellationToken
        );
        if (current is not null && message.Sequence < current.LastReadSequence)
        {
            throw new ConversationStateConflictException();
        }

        await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "UPDATE_CONVERSATION_READ_POSITION",
            idempotencyKey,
            new { last_visible_message_id = message.MessageId, request_hash = requestHash },
            cancellationToken
        );
        await using var readPositionTransaction =
            await WhatsAppRelationshipRouting.BeginIngressReadAsync(
                _whatsAppExecution,
                _whatsAppRouting,
                db,
                _environment,
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
        if (readPositionTransaction is not null)
        {
            current = await db.ReadPositions.SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ParticipantId == participantId,
                cancellationToken
            );
            if (current is not null)
            {
                await db.Entry(current).ReloadAsync(cancellationToken);
                if (message.Sequence < current.LastReadSequence)
                    throw new ConversationStateConflictException();
            }
        }
        var now = DateTimeOffset.UtcNow;
        if (current is null)
        {
            current = new ConversationReadPosition
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                LastReadMessageId = message.MessageId,
                LastReadSequence = message.Sequence,
                UpdatedAt = now,
            };
            db.ReadPositions.Add(current);
        }
        else
        {
            current.LastReadMessageId = message.MessageId;
            current.LastReadSequence = message.Sequence;
            current.UpdatedAt = now;
        }

        var response = new ConversationReadPositionV1(
            SchemaVersion,
            relationshipId,
            message.MessageId,
            now
        );
        db.IdempotencyOutcomes.Add(
            CreateIdempotency(
                tenantId,
                participantId,
                relationshipId,
                "READ_POSITION",
                idempotencyKey,
                requestHash,
                response
            )
        );
        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        await db.SaveChangesAsync(cancellationToken);
        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        if (readPositionTransaction is not null)
            await readPositionTransaction.CommitAsync(cancellationToken);
        return new ConversationCommandResult<ConversationReadPositionV1>(response, false);
    }

    public async Task<ConversationCommandResult<ConversationExecutionStatusV1>> CancelAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid executionId,
        Guid idempotencyKey,
        CancellationToken cancellationToken,
        object? requestBinding = null
    )
    {
        using var activity = StartActivity("bp.conversation.cancel", relationshipId);
        var relationship = await EnsureAccessAsync(
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        EnsureRelationshipNotStopped(relationship);
        if (_stopFence is not null)
            await _stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
        var requestHash = requestBinding is null
            ? HashCanonical(new { executionId })
            : HashCanonical(new { executionId, requestBinding });
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var replay = await FindIdempotencyAsync(
            db,
            tenantId,
            participantId,
            relationshipId,
            "CANCEL",
            idempotencyKey,
            cancellationToken
        );
        if (replay is not null)
        {
            EnsureMatchingHash(replay, requestHash);
            await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
                _whatsAppExecution,
                _whatsAppRouting,
                db,
                _environment,
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
            WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
            return new ConversationCommandResult<ConversationExecutionStatusV1>(
                Deserialize<ConversationExecutionStatusV1>(replay.ResponseJson),
                true
            );
        }

        var execution = await db.Executions.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ExecutionId == executionId,
            cancellationToken
        );
        if (execution is null)
        {
            throw new ConversationNotAccessibleException();
        }

        if (execution.ProcessingState == "STOPPED")
            throw new ConversationStoppedException();
        if (
            execution.ProcessingState is "COMPLETED" or "CANCELLED"
            || (
                execution.ProcessingState == "FAILED"
                && execution.CompletionReason == "PARTIAL_FAILURE"
            )
        )
        {
            await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
                _whatsAppExecution,
                _whatsAppRouting,
                db,
                _environment,
                tenantId,
                participantId,
                relationshipId,
                cancellationToken
            );
            if (routingRead is not null)
                await db.Entry(execution).ReloadAsync(cancellationToken);
            WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
            return new ConversationCommandResult<ConversationExecutionStatusV1>(
                ToContract(execution),
                true
            );
        }

        var message = await db.Messages.SingleAsync(
            value => value.TenantId == tenantId && value.MessageId == execution.MessageId,
            cancellationToken
        );
        var origin =
            await db
                .IdempotencyOutcomes.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.OperationFamily == "SEND"
                        && value.ExecutionId == executionId
                        && value.MessageId == message.MessageId,
                    cancellationToken
                )
            ?? throw new ConversationStateConflictException();
        await using var relationships = await _relationshipFactory.CreateDbContextAsync(
            cancellationToken
        );
        var originalActor =
            await relationships
                .RelationshipParticipants.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.ParticipantId == origin.ActorParticipantId
                        && value.Status == "ACTIVE",
                    cancellationToken
                )
            ?? throw new ConversationNotAccessibleException();
        if (message.EvidenceRecordId is not { } startEvidence || startEvidence == Guid.Empty)
            throw new ConversationStateConflictException();
        var caller = new ConversationExecutionCallerV1(
            tenantId,
            relationshipId,
            origin.ActorParticipantId,
            RelationshipRoleCodec.ToDatabase(originalActor.Role),
            $"ce-decision:{startEvidence:D}",
            ConversationExecutionIdentity.Create(
                tenantId,
                relationshipId,
                origin.ActorParticipantId,
                execution.ConversationId,
                origin.IdempotencyKey
            )
        );
        var cancellationEvidence = await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "CANCEL_CONVERSATION_EXECUTION",
            idempotencyKey,
            new { execution_id = executionId, request_hash = requestHash },
            cancellationToken
        );
        if (cancellationEvidence == Guid.Empty)
            throw new ConversationExecutionUnavailableException();
        EnsureRelationshipNotStopped(
            await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken)
        );
        if (
            !await relationships
                .RelationshipParticipants.AsNoTracking()
                .AnyAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.ParticipantId == originalActor.ParticipantId
                        && value.Status == "ACTIVE"
                        && value.Role == originalActor.Role,
                    cancellationToken
                )
        )
            throw new ConversationNotAccessibleException();
        if (_stopFence is not null)
            await _stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
        if (
            _whatsAppExecution?.CurrentTenantId is { } routedTenant
            && routedTenant != _whatsAppExecution.ServiceTenantId
        )
        {
            var route = _whatsAppExecution.RequireConfirmedRelationshipRoute();
            if (
                route.TenantId != tenantId
                || route.ParticipantId != participantId
                || route.RelationshipId != relationshipId
                || route.ConversationId != execution.ConversationId
                || execution.OriginChannelBindingId != route.BindingId
                || execution.OriginRecipientDigest != route.SenderHash
            )
                throw new WhatsAppCapabilityUnavailableException("INGRESS_ROUTE_DENIED");
        }
        await WhatsAppRelationshipRouting.RequireIngressDispatchAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            cancellationToken
        );
        var confirmed = await _executionGateway.CancelAsync(
            execution.ConversationId,
            executionId,
            message.MessageId,
            caller,
            idempotencyKey,
            cancellationToken
        );

        if (
            confirmed.ExecutionId != executionId
            || confirmed.UpdatedAt < message.AcceptedAt
            || confirmed.State is not ("CANCELLED" or "COMPLETED" or "FAILED")
            || confirmed.CompletionReason
                != (
                    confirmed.State switch
                    {
                        "CANCELLED" => "CANCELLED",
                        "COMPLETED" => "COMPLETE",
                        _ => "PARTIAL_FAILURE",
                    }
                )
        )
            throw new ConversationExecutionUnavailableException();
        await using var cancellationTransaction = db.Database.IsRelational()
            ? await db.Database.BeginTransactionAsync(
                System.Data.IsolationLevel.Serializable,
                cancellationToken
            )
            : null;
        await WhatsAppRelationshipRouting.RequireIngressCommitAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            tenantId,
            participantId,
            relationshipId,
            execution.ConversationId,
            "WHATSAPP",
            execution.OriginChannelBindingId,
            execution.OriginRecipientDigest,
            cancellationToken
        );
        if (cancellationTransaction is not null)
        {
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT execution_id FROM business.conversation_executions WHERE tenant_id = {tenantId} AND execution_id = {executionId} FOR UPDATE",
                cancellationToken
            );
            await db.Database.ExecuteSqlInterpolatedAsync(
                $"SELECT message_id FROM business.conversation_messages WHERE tenant_id = {tenantId} AND message_id = {message.MessageId} FOR UPDATE",
                cancellationToken
            );
        }
        if (_stopFence is not null)
            await _stopFence.ThrowIfLatchedAsync(tenantId, relationshipId, cancellationToken);
        await db.Entry(execution).ReloadAsync(cancellationToken);
        await db.Entry(message).ReloadAsync(cancellationToken);
        if (execution.ProcessingState == "STOPPED" || message.ProcessingState == "STOPPED")
            throw new ConversationStoppedException();
        if (
            execution.ProcessingState is "COMPLETED" or "CANCELLED"
            && execution.ProcessingState != confirmed.State
        )
            throw new ConversationStateConflictException();
        execution.ProcessingState = confirmed.State;
        execution.Partial = confirmed.Partial;
        execution.CompletionReason = confirmed.CompletionReason;
        execution.UpdatedAt = confirmed.UpdatedAt;
        message.ProcessingState = confirmed.State;
        message.Partial = confirmed.Partial;
        message.CompletionReason = confirmed.CompletionReason;
        message.CompletedAt = execution.UpdatedAt;
        var conversation = await db.Conversations.SingleAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken
        );
        db.Events.Add(
            CreateEvent(
                conversation,
                tenantId,
                relationshipId,
                confirmed.State switch
                {
                    "CANCELLED" => "stream.cancelled",
                    "COMPLETED" => "message.completed",
                    _ => "message.failed",
                },
                message.MessageId,
                execution.ExecutionId,
                new { message = ToContract(message) }
            )
        );
        db.AdvanceProjectionVersions();
        var response = ToContract(execution);
        db.IdempotencyOutcomes.Add(
            CreateIdempotency(
                tenantId,
                participantId,
                relationshipId,
                "CANCEL",
                idempotencyKey,
                requestHash,
                response,
                message.MessageId,
                execution.ExecutionId
            )
        );
        await db.SaveChangesAsync(cancellationToken);
        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        if (cancellationTransaction is not null)
            await cancellationTransaction.CommitAsync(cancellationToken);
        return new ConversationCommandResult<ConversationExecutionStatusV1>(response, false);
    }

    public async Task<ConversationExecutionStatusV1?> GetMessageExecutionAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid messageId,
        CancellationToken cancellationToken
    )
    {
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            _environment,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var execution = await db
            .Executions.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.MessageId == messageId,
                cancellationToken
            );
        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        return execution is null ? null : ToContract(execution);
    }

    public async Task<ConversationExecutionStatusV1?> GetExecutionAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid executionId,
        CancellationToken cancellationToken
    )
    {
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            _environment,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var execution = await db
            .Executions.AsNoTracking()
            .SingleOrDefaultAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ExecutionId == executionId,
                cancellationToken
            );
        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        return execution is null ? null : ToContract(execution);
    }

    public async Task<IReadOnlyList<ConversationStreamEventV1>> GetEventReplayAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string? lastEventId,
        CancellationToken cancellationToken
    )
    {
        using var activity = StartActivity("bp.conversation.stream_replay", relationshipId);
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        var after = lastEventId is null
            ? 0
            : _cursorCodec.Decode(lastEventId, tenantId, relationshipId, "event");
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            _environment,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var events = await db
            .Events.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Sequence > after
            )
            .OrderBy(value => value.Sequence)
            .Take(500)
            .ToListAsync(cancellationToken);
        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        return events
            .Select(value => new ConversationStreamEventV1(
                SchemaVersion,
                _cursorCodec.Encode(tenantId, relationshipId, "event", value.Sequence),
                value.EventType,
                relationshipId,
                value.Sequence,
                value.MessageId,
                value.ExecutionId,
                value.OccurredAt,
                JsonDocument.Parse(value.DataJson).RootElement.Clone()
            ))
            .ToList();
    }

    public async Task<IReadOnlyList<ConversationStreamEventV1>> GetEventReplayAfterSequenceAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        long afterSequence,
        CancellationToken cancellationToken
    )
    {
        if (afterSequence < 0)
            throw new ConversationRequestException("afterSequence must not be negative.");
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        await using var routingRead = await WhatsAppRelationshipRouting.BeginIngressReadAsync(
            _whatsAppExecution,
            _whatsAppRouting,
            db,
            _environment,
            tenantId,
            participantId,
            relationshipId,
            cancellationToken
        );
        var events = await db
            .Events.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Sequence > afterSequence
            )
            .OrderBy(value => value.Sequence)
            .Take(500)
            .ToListAsync(cancellationToken);
        WhatsAppRelationshipRouting.RequireIngressReadRelease(_whatsAppExecution);
        return events
            .Select(value => new ConversationStreamEventV1(
                SchemaVersion,
                _cursorCodec.Encode(tenantId, relationshipId, "event", value.Sequence),
                value.EventType,
                relationshipId,
                value.Sequence,
                value.MessageId,
                value.ExecutionId,
                value.OccurredAt,
                JsonDocument.Parse(value.DataJson).RootElement.Clone()
            ))
            .ToList();
    }

    private async Task<EmploymentRelationship> EnsureAccessAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await _relationshipFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db
            .EmploymentRelationships.AsNoTracking()
            .SingleOrDefaultAsync(
                value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
                cancellationToken
            );
        if (relationship is null)
        {
            throw new ConversationNotAccessibleException();
        }

        var authorized = await db
            .RelationshipParticipants.AsNoTracking()
            .AnyAsync(
                value =>
                    value.TenantId == tenantId
                    && value.RelationshipId == relationshipId
                    && value.ParticipantId == participantId
                    && value.Status == "ACTIVE",
                cancellationToken
            );
        if (!authorized)
        {
            throw new ConversationNotAccessibleException();
        }

        return relationship;
    }

    private static void EnsureRelationshipNotStopped(EmploymentRelationship relationship)
    {
        if (relationship.State == EmploymentRelationshipState.StoppedEmergency)
        {
            throw new ConversationStoppedException();
        }
    }

    private async Task<ConversationProjection> GetOrCreateConversationAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken,
        Guid? preparedConversationId = null
    )
    {
        var conversation = await db.Conversations.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken
        );
        if (conversation is not null)
        {
            return conversation;
        }

        conversation = new ConversationProjection
        {
            ConversationId = preparedConversationId ?? Guid.NewGuid(),
            Environment = _environment,
            TenantId = tenantId,
            RelationshipId = relationshipId,
        };
        db.Conversations.Add(conversation);
        return conversation;
    }

    private static ConversationEvent CreateEvent(
        ConversationProjection conversation,
        Guid tenantId,
        Guid relationshipId,
        string eventType,
        Guid? messageId,
        Guid? executionId,
        object data
    ) =>
        new()
        {
            TenantId = tenantId,
            ConversationId = conversation.ConversationId,
            RelationshipId = relationshipId,
            Sequence = conversation.NextEventSequence++,
            EventType = eventType,
            MessageId = messageId,
            ExecutionId = executionId,
            DataJson = JsonSerializer.Serialize(data, JsonOptions),
        };

    private ConversationSubmissionV1 CreateSubmission(
        Guid tenantId,
        Guid relationshipId,
        ConversationMessage message,
        ConversationExecution execution,
        string outcome,
        bool replayed
    ) =>
        new(
            SchemaVersion,
            outcome,
            ToContract(message),
            execution.ExecutionId,
            _cursorCodec.Encode(tenantId, relationshipId, "timeline", message.Sequence),
            replayed
        );

    private async Task RecordStoppedExecutionAsync(
        ConversationStoreDbContext db,
        ConversationProjection conversation,
        ConversationMessage message,
        ConversationExecution execution,
        ConversationIdempotencyOutcome idempotency,
        CancellationToken cancellationToken
    )
    {
        message.DeliveryState = "FAILED";
        message.ProcessingState = "STOPPED";
        message.CompletionReason = "EMERGENCY_STOPPED";
        message.CompletedAt = DateTimeOffset.UtcNow;
        execution.ProcessingState = "STOPPED";
        execution.CompletionReason = "EMERGENCY_STOPPED";
        execution.UpdatedAt = message.CompletedAt.Value;
        idempotency.Outcome = "STOPPED";
        idempotency.ResponseJson = JsonSerializer.Serialize(
            CreateSubmission(
                message.TenantId,
                message.RelationshipId,
                message,
                execution,
                "STOPPED",
                false
            ),
            JsonOptions
        );
        db.Events.Add(
            CreateEvent(
                conversation,
                message.TenantId,
                message.RelationshipId,
                "stop.applied",
                message.MessageId,
                execution.ExecutionId,
                new { message = ToContract(message) }
            )
        );
        await db.SaveChangesAsync(cancellationToken);
    }

    internal static ConversationMessageV1 ToContract(ConversationMessage message) =>
        new(
            message.SchemaVersion,
            message.MessageId,
            message.RelationshipId,
            message.Sequence,
            message.Actor,
            message.Channel,
            Deserialize<List<ConversationTextBlockV1>>(message.ContentJson),
            Deserialize<List<JsonElement>>(message.CardsJson),
            message.DeliveryState,
            message.ProcessingState,
            message.EvidenceState,
            message.EvidenceRecordId,
            message.Partial,
            message.CompletionReason,
            message.RetryOfMessageId,
            message.ClientMessageId,
            message.AcceptedAt,
            message.CompletedAt
        );

    private static ConversationExecutionStatusV1 ToContract(ConversationExecution execution) =>
        new(
            SchemaVersion,
            execution.ExecutionId,
            execution.ProcessingState,
            execution.Partial,
            execution.CompletionReason,
            execution.UpdatedAt,
            execution.ProjectionVersion
        );

    private static ConversationIdempotencyOutcome CreateIdempotency<T>(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string operationFamily,
        Guid idempotencyKey,
        string requestHash,
        T response,
        Guid? messageId = null,
        Guid? executionId = null
    ) =>
        new()
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ActorParticipantId = participantId,
            OperationFamily = operationFamily,
            IdempotencyKey = idempotencyKey,
            RequestHash = requestHash,
            MessageId = messageId,
            ExecutionId = executionId,
            ResponseJson = JsonSerializer.Serialize(response, JsonOptions),
        };

    private async Task<ConversationSubmissionV1> GetSendReplayAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid relationshipId,
        ConversationIdempotencyOutcome outcome,
        CancellationToken cancellationToken
    )
    {
        var message =
            await db
                .Messages.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.MessageId == outcome.MessageId,
                    cancellationToken
                )
            ?? throw new ConversationStateConflictException();
        var execution =
            await db
                .Executions.AsNoTracking()
                .SingleOrDefaultAsync(
                    value =>
                        value.TenantId == tenantId
                        && value.RelationshipId == relationshipId
                        && value.ExecutionId == outcome.ExecutionId
                        && value.MessageId == message.MessageId,
                    cancellationToken
                )
            ?? throw new ConversationStateConflictException();
        return CreateSubmission(tenantId, relationshipId, message, execution, "REPLAYED", true);
    }

    private static Task<ConversationIdempotencyOutcome?> FindIdempotencyAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string operationFamily,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    ) =>
        db.IdempotencyOutcomes.SingleOrDefaultAsync(
            value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ActorParticipantId == participantId
                && value.OperationFamily == operationFamily
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken
        );

    private static void EnsureMatchingHash(
        ConversationIdempotencyOutcome outcome,
        string requestHash
    )
    {
        if (
            !CryptographicOperations.FixedTimeEquals(
                Encoding.ASCII.GetBytes(outcome.RequestHash),
                Encoding.ASCII.GetBytes(requestHash)
            )
        )
        {
            throw new ConversationIdempotencyConflictException();
        }
    }

    private static void ValidateSendRequest(SendConversationMessageRequestV1 request)
    {
        if (
            request.SchemaVersion != SchemaVersion
            || string.IsNullOrWhiteSpace(request.SkillId)
            || request.SkillId.Length > 128
            || request.Content.Count != 1
            || request.Content[0].SchemaVersion != SchemaVersion
            || request.Content[0].BlockType != "TEXT"
            || string.IsNullOrWhiteSpace(request.Content[0].Text)
            || request.Content[0].Text.Length > 32000
            || !ConversationInputContract.IsPersistableText(request.Content[0].Text)
            || !ConversationInputContract.IsLanguageTag(request.Locale)
            || request.Content[0].Language is { } language
                && !ConversationInputContract.IsLanguageTag(language)
            || request.ContextVersion is { Length: > 128 }
            || request.WorkItem is { } workItem
                && (
                    workItem.Owner != "professional-runtime"
                    || workItem.WorkItemId == Guid.Empty
                    || workItem.Revision < 1
                    || workItem.InvocationId == Guid.Empty
                )
            || request.PayloadDigest is { } digest
                && (
                    digest.Length != 64
                    || digest.Any(character =>
                        character is not (>= '0' and <= '9' or >= 'a' and <= 'f')
                    )
                    || request.Channel is not ("WEB" or "WHATSAPP" or "MOBILE")
                )
        )
        {
            throw new ConversationRequestException(
                "Conversation request is malformed or unsupported."
            );
        }
    }

    private static string HashCanonical<T>(T value) =>
        Convert
            .ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(value, JsonOptions)))
            .ToLowerInvariant();

    private static T Deserialize<T>(string json) =>
        JsonSerializer.Deserialize<T>(json, JsonOptions)
        ?? throw new InvalidOperationException("Stored conversation outcome is invalid.");

    private static string ExtractLocale(ConversationMessage message)
    {
        var content = Deserialize<List<ConversationTextBlockV1>>(message.ContentJson);
        return content.FirstOrDefault()?.Language ?? "en";
    }

    private static Activity? StartActivity(string name, Guid relationshipId)
    {
        var activity = ActivitySource.StartActivity(name);
        activity?.SetTag("waooaw.relationship_id", relationshipId.ToString("D"));
        activity?.SetTag("waooaw.claim_id", "C-023,C-026");
        return activity;
    }
}
