// Implements: architecture/reference/components/conversation-core.md § Public BP Contract
// constitutional_basis: C-001, C-005, C-023, C-026, C-049, C-059, C-063

using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ConversationTextBlockV1(
    string SchemaVersion,
    string BlockType,
    string Text,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? Language = null);

public sealed record SendConversationMessageRequestV1(
    string SchemaVersion,
    Guid ClientMessageId,
    IReadOnlyList<ConversationTextBlockV1> Content,
    string Locale,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? ExpectedCursor = null);

public sealed record UpdateConversationReadPositionRequestV1(
    string SchemaVersion,
    Guid LastVisibleMessageId,
    string AuthoritativeCursor);

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
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? CompletionReason,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? RetryOfMessageId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ClientMessageId,
    DateTimeOffset AcceptedAt,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] DateTimeOffset? CompletedAt);

public sealed record ConversationTimelinePageV1(
    string SchemaVersion,
    Guid RelationshipId,
    IReadOnlyList<ConversationMessageV1> Items,
    string AuthoritativeCursor,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? NextCursor,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? UnreadBoundaryMessageId,
    bool HasMore,
    DateTimeOffset ServerTime);

public sealed record ConversationSubmissionV1(
    string SchemaVersion,
    string Outcome,
    ConversationMessageV1 Message,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ExecutionId,
    string AuthoritativeCursor,
    bool Replayed);

public sealed record ConversationReadPositionV1(
    string SchemaVersion,
    Guid RelationshipId,
    Guid LastReadMessageId,
    DateTimeOffset UpdatedAt);

public sealed record ConversationExecutionStatusV1(
    string SchemaVersion,
    Guid ExecutionId,
    string State,
    bool Partial,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? CompletionReason,
    DateTimeOffset UpdatedAt);

public sealed record ConversationStreamEventV1(
    string SchemaVersion,
    string EventId,
    string EventType,
    Guid RelationshipId,
    long Sequence,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? MessageId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] Guid? ExecutionId,
    DateTimeOffset OccurredAt,
    JsonElement Data);

public sealed record ConversationCommandResult<T>(T Value, bool Replayed);

public sealed class ConversationNotAccessibleException : Exception;
public sealed class ConversationIdempotencyConflictException : Exception;
public sealed class ConversationStateConflictException : Exception;
public sealed class ConversationCursorExpiredException : Exception;
public sealed class ConversationRetryNotAllowedException : Exception;
public sealed class ConversationStoppedException : Exception;
public sealed class ConversationExecutionUnavailableException : Exception;

public sealed class ConversationRequestException(string message) : Exception(message);

public sealed class ConversationCursorOptions
{
    public string HmacKey { get; set; } = string.Empty;
}

public interface IConversationExecutionGateway
{
    Task StartAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        Guid relationshipId,
        string locale,
        Guid idempotencyKey,
        CancellationToken cancellationToken);

    Task CancelAsync(
        Guid conversationId,
        Guid executionId,
        Guid idempotencyKey,
        CancellationToken cancellationToken);
}

public sealed class UnconfiguredConversationExecutionGateway : IConversationExecutionGateway
{
    public Task StartAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        Guid relationshipId,
        string locale,
        Guid idempotencyKey,
        CancellationToken cancellationToken) =>
        throw new ConversationExecutionUnavailableException();

    public Task CancelAsync(
        Guid conversationId,
        Guid executionId,
        Guid idempotencyKey,
        CancellationToken cancellationToken) =>
        throw new ConversationExecutionUnavailableException();
}

public sealed class ConversationCursorCodec
{
    private readonly byte[] _key;

    public ConversationCursorCodec(IOptions<ConversationCursorOptions> options)
    {
        var configuredKey = options.Value.HmacKey;
        if (string.IsNullOrWhiteSpace(configuredKey) || configuredKey.Length < 32)
        {
            throw new InvalidOperationException("Conversation:CursorHmacKey must contain at least 32 characters.");
        }

        _key = Encoding.UTF8.GetBytes(configuredKey);
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
            var expectedSignature = HMACSHA256.HashData(_key, payloadBytes);
            if (!CryptographicOperations.FixedTimeEquals(suppliedSignature, expectedSignature))
            {
                throw new ConversationCursorExpiredException();
            }

            var fields = Encoding.UTF8.GetString(payloadBytes).Split('|');
            if (fields.Length != 4
                || fields[0] != tenantId.ToString("D")
                || fields[1] != relationshipId.ToString("D")
                || fields[2] != purpose
                || !long.TryParse(fields[3], out var sequence)
                || sequence < 0)
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
    private static readonly ActivitySource ActivitySource = new("waooaw.business-platform.conversation");
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    private readonly IDbContextFactory<ConversationStoreDbContext> _conversationFactory;
    private readonly IDbContextFactory<EmploymentRelationshipDbContext> _relationshipFactory;
    private readonly IRelationshipConstitutionalGateway _constitutionalGateway;
    private readonly IConversationExecutionGateway _executionGateway;
    private readonly ConversationCursorCodec _cursorCodec;

    public ConversationService(
        IDbContextFactory<ConversationStoreDbContext> conversationFactory,
        IDbContextFactory<EmploymentRelationshipDbContext> relationshipFactory,
        IRelationshipConstitutionalGateway constitutionalGateway,
        IConversationExecutionGateway executionGateway,
        ConversationCursorCodec cursorCodec)
    {
        _conversationFactory = conversationFactory;
        _relationshipFactory = relationshipFactory;
        _constitutionalGateway = constitutionalGateway;
        _executionGateway = executionGateway;
        _cursorCodec = cursorCodec;
    }

    public async Task<ConversationTimelinePageV1> ListMessagesAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string? cursor,
        string? afterCursor,
        int limit,
        CancellationToken cancellationToken)
    {
        using var activity = StartActivity("bp.conversation.timeline", relationshipId);
        if (cursor is not null && afterCursor is not null)
        {
            throw new ConversationRequestException("cursor and afterCursor are mutually exclusive.");
        }

        if (limit is < 1 or > 100)
        {
            throw new ConversationRequestException("limit must be between 1 and 100.");
        }

        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var conversation = await db.Conversations.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        if (conversation is null)
        {
            return new ConversationTimelinePageV1(
                SchemaVersion,
                relationshipId,
                [],
                _cursorCodec.Encode(tenantId, relationshipId, "timeline", 0),
                null,
                null,
                false,
                DateTimeOffset.UtcNow);
        }

        var query = db.Messages.AsNoTracking().Where(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId);
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

        var descending = await query.OrderByDescending(value => value.Sequence).Take(limit + 1).ToListAsync(cancellationToken);
        var hasMore = descending.Count > limit;
        var selected = descending.Take(limit).OrderBy(value => value.Sequence).ToList();
        var maximumSequence = await db.Messages
            .Where(value => value.TenantId == tenantId && value.RelationshipId == relationshipId)
            .Select(value => (long?)value.Sequence)
            .MaxAsync(cancellationToken) ?? 0;
        var readSequence = await db.ReadPositions.AsNoTracking()
            .Where(value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId)
            .Select(value => (long?)value.LastReadSequence)
            .SingleOrDefaultAsync(cancellationToken) ?? 0;
        var unreadBoundary = await db.Messages.AsNoTracking()
            .Where(value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Sequence > readSequence)
            .OrderBy(value => value.Sequence)
            .Select(value => (Guid?)value.MessageId)
            .FirstOrDefaultAsync(cancellationToken);
        var nextCursor = hasMore && selected.Count > 0
            ? _cursorCodec.Encode(tenantId, relationshipId, "timeline", selected[0].Sequence)
            : null;

        return new ConversationTimelinePageV1(
            SchemaVersion,
            relationshipId,
            selected.Select(ToContract).ToList(),
            _cursorCodec.Encode(tenantId, relationshipId, "timeline", maximumSequence),
            nextCursor,
            unreadBoundary,
            hasMore,
            DateTimeOffset.UtcNow);
    }

    public async Task<ConversationCommandResult<ConversationSubmissionV1>> SendAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        SendConversationMessageRequestV1 request,
        CancellationToken cancellationToken)
    {
        using var activity = StartActivity("bp.conversation.send", relationshipId);
        ValidateSendRequest(request);
        var relationship = await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        var requestHash = HashCanonical(request);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var replay = await FindIdempotencyAsync(db, tenantId, participantId, relationshipId, "SEND", idempotencyKey, cancellationToken);
        if (replay is not null)
        {
            EnsureMatchingHash(replay, requestHash);
            return new ConversationCommandResult<ConversationSubmissionV1>(
                Deserialize<ConversationSubmissionV1>(replay.ResponseJson) with { Replayed = true, Outcome = "REPLAYED" },
                true);
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
            cancellationToken);

        var conversation = await GetOrCreateConversationAsync(db, tenantId, relationshipId, cancellationToken);
        var message = new ConversationMessage
        {
            TenantId = tenantId,
            ConversationId = conversation.ConversationId,
            RelationshipId = relationshipId,
            Sequence = conversation.NextMessageSequence++,
            ContentJson = JsonSerializer.Serialize(request.Content, JsonOptions),
            ClientMessageId = request.ClientMessageId,
            EvidenceState = "RECORDED",
            EvidenceRecordId = evidenceId,
        };
        var execution = new ConversationExecution
        {
            TenantId = tenantId,
            ConversationId = conversation.ConversationId,
            RelationshipId = relationshipId,
            MessageId = message.MessageId,
        };
        var conversationEvent = CreateEvent(
            conversation,
            tenantId,
            relationshipId,
            "message.accepted",
            message.MessageId,
            execution.ExecutionId,
            new { message = ToContract(message) });
        conversation.UpdatedAt = DateTimeOffset.UtcNow;
        var submission = CreateSubmission(tenantId, relationshipId, message, execution, "ACCEPTED", false);
        var idempotency = CreateIdempotency(
            tenantId,
            participantId,
            relationshipId,
            "SEND",
            idempotencyKey,
            requestHash,
            submission,
            message.MessageId,
            execution.ExecutionId);
        db.Messages.Add(message);
        db.Executions.Add(execution);
        db.Events.Add(conversationEvent);
        db.IdempotencyOutcomes.Add(idempotency);
        try
        {
            await db.SaveChangesAsync(cancellationToken);
        }
        catch (DbUpdateException)
        {
            await using var replayDb = await _conversationFactory.CreateDbContextAsync(cancellationToken);
            var concurrentOutcome = await FindIdempotencyAsync(
                replayDb,
                tenantId,
                participantId,
                relationshipId,
                "SEND",
                idempotencyKey,
                cancellationToken);
            if (concurrentOutcome is null)
            {
                throw new ConversationStateConflictException();
            }

            EnsureMatchingHash(concurrentOutcome, requestHash);
            return new ConversationCommandResult<ConversationSubmissionV1>(
                Deserialize<ConversationSubmissionV1>(concurrentOutcome.ResponseJson) with
                {
                    Replayed = true,
                    Outcome = "REPLAYED",
                },
                true);
        }

        try
        {
            await _executionGateway.StartAsync(
                conversation.ConversationId,
                execution.ExecutionId,
                message.MessageId,
                relationshipId,
                request.Locale,
                idempotencyKey,
                cancellationToken);
            return new ConversationCommandResult<ConversationSubmissionV1>(submission, false);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            message.DeliveryState = "UNRESOLVED";
            message.ProcessingState = "FAILED";
            execution.ProcessingState = "FAILED";
            execution.UpdatedAt = DateTimeOffset.UtcNow;
            idempotency.Outcome = "UNRESOLVED";
            var unresolved = CreateSubmission(tenantId, relationshipId, message, execution, "UNRESOLVED", false);
            idempotency.ResponseJson = JsonSerializer.Serialize(unresolved, JsonOptions);
            db.Events.Add(CreateEvent(
                conversation,
                tenantId,
                relationshipId,
                "message.failed",
                message.MessageId,
                execution.ExecutionId,
                new { code = "CONVERSATION_EXECUTION_UNAVAILABLE", retryable = true, partial = false }));
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
        CancellationToken cancellationToken)
    {
        using var activity = StartActivity("bp.conversation.retry", relationshipId);
        var relationship = await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        EnsureRelationshipNotStopped(relationship);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var original = await FindIdempotencyAsync(
            db, tenantId, participantId, relationshipId, "SEND", originalIdempotencyKey, cancellationToken);
        var message = await db.Messages.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.MessageId == messageId,
            cancellationToken);
        if (original is null || message is null || original.MessageId != messageId)
        {
            throw new ConversationRetryNotAllowedException();
        }

        var execution = await db.Executions.SingleAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.MessageId == messageId,
            cancellationToken);
        if (message.ProcessingState == "COMPLETED")
        {
            return new ConversationCommandResult<ConversationSubmissionV1>(
                CreateSubmission(tenantId, relationshipId, message, execution, "REPLAYED", true),
                true);
        }

        if (message.DeliveryState is not ("FAILED" or "UNRESOLVED")
            && message.ProcessingState is not "FAILED")
        {
            throw new ConversationRetryNotAllowedException();
        }

        await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "RETRY_CONVERSATION_MESSAGE",
            originalIdempotencyKey,
            new { message_id = messageId, request_hash = original.RequestHash },
            cancellationToken);
        message.DeliveryState = "ACCEPTED";
        message.ProcessingState = "QUEUED";
        execution.ProcessingState = "QUEUED";
        execution.UpdatedAt = DateTimeOffset.UtcNow;
        original.Outcome = "ACCEPTED";
        var conversation = await db.Conversations.SingleAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        var submission = CreateSubmission(tenantId, relationshipId, message, execution, "ACCEPTED", false);
        original.ResponseJson = JsonSerializer.Serialize(submission, JsonOptions);
        db.Events.Add(CreateEvent(
            conversation,
            tenantId,
            relationshipId,
            "processing.started",
            message.MessageId,
            execution.ExecutionId,
            new { messageId = message.MessageId, executionId = execution.ExecutionId }));
        await db.SaveChangesAsync(cancellationToken);

        try
        {
            await _executionGateway.StartAsync(
                conversation.ConversationId,
                execution.ExecutionId,
                message.MessageId,
                relationshipId,
                ExtractLocale(message),
                originalIdempotencyKey,
                cancellationToken);
            return new ConversationCommandResult<ConversationSubmissionV1>(submission, false);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            message.DeliveryState = "UNRESOLVED";
            message.ProcessingState = "FAILED";
            execution.ProcessingState = "FAILED";
            original.Outcome = "UNRESOLVED";
            await db.SaveChangesAsync(cancellationToken);
            throw new ConversationExecutionUnavailableException();
        }
    }

    public async Task<ConversationCommandResult<ConversationReadPositionV1>> UpdateReadPositionAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid idempotencyKey,
        UpdateConversationReadPositionRequestV1 request,
        CancellationToken cancellationToken)
    {
        using var activity = StartActivity("bp.conversation.read_position", relationshipId);
        if (request.SchemaVersion != SchemaVersion)
        {
            throw new ConversationRequestException("Unsupported schemaVersion.");
        }

        var relationship = await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        var requestHash = HashCanonical(request);
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var replay = await FindIdempotencyAsync(
            db, tenantId, participantId, relationshipId, "READ_POSITION", idempotencyKey, cancellationToken);
        if (replay is not null)
        {
            EnsureMatchingHash(replay, requestHash);
            return new ConversationCommandResult<ConversationReadPositionV1>(
                Deserialize<ConversationReadPositionV1>(replay.ResponseJson),
                true);
        }

        var observedSequence = _cursorCodec.Decode(request.AuthoritativeCursor, tenantId, relationshipId, "timeline");
        var message = await db.Messages.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.MessageId == request.LastVisibleMessageId,
            cancellationToken);
        if (message is null)
        {
            throw new ConversationNotAccessibleException();
        }

        if (message.Sequence > observedSequence)
        {
            throw new ConversationStateConflictException();
        }

        var current = await db.ReadPositions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId,
            cancellationToken);
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
            cancellationToken);
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

        var response = new ConversationReadPositionV1(SchemaVersion, relationshipId, message.MessageId, now);
        db.IdempotencyOutcomes.Add(CreateIdempotency(
            tenantId,
            participantId,
            relationshipId,
            "READ_POSITION",
            idempotencyKey,
            requestHash,
            response));
        await db.SaveChangesAsync(cancellationToken);
        return new ConversationCommandResult<ConversationReadPositionV1>(response, false);
    }

    public async Task<ConversationCommandResult<ConversationExecutionStatusV1>> CancelAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        Guid executionId,
        Guid idempotencyKey,
        CancellationToken cancellationToken)
    {
        using var activity = StartActivity("bp.conversation.cancel", relationshipId);
        var relationship = await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        EnsureRelationshipNotStopped(relationship);
        var requestHash = HashCanonical(new { executionId });
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var replay = await FindIdempotencyAsync(
            db, tenantId, participantId, relationshipId, "CANCEL", idempotencyKey, cancellationToken);
        if (replay is not null)
        {
            EnsureMatchingHash(replay, requestHash);
            return new ConversationCommandResult<ConversationExecutionStatusV1>(
                Deserialize<ConversationExecutionStatusV1>(replay.ResponseJson),
                true);
        }

        var execution = await db.Executions.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ExecutionId == executionId,
            cancellationToken);
        if (execution is null)
        {
            throw new ConversationNotAccessibleException();
        }

        if (execution.ProcessingState is "COMPLETED" or "FAILED" or "CANCELLED" or "STOPPED")
        {
            return new ConversationCommandResult<ConversationExecutionStatusV1>(ToContract(execution), true);
        }

        await _constitutionalGateway.AuthorizeAndRecordAsync(
            tenantId,
            relationshipId,
            relationship.ProfessionalType,
            "CANCEL_CONVERSATION_EXECUTION",
            idempotencyKey,
            new { execution_id = executionId, request_hash = requestHash },
            cancellationToken);
        await _executionGateway.CancelAsync(execution.ConversationId, executionId, idempotencyKey, cancellationToken);

        execution.ProcessingState = "CANCELLED";
        execution.Partial = true;
        execution.CompletionReason = "CANCELLED";
        execution.UpdatedAt = DateTimeOffset.UtcNow;
        var message = await db.Messages.SingleAsync(
            value => value.TenantId == tenantId && value.MessageId == execution.MessageId,
            cancellationToken);
        message.ProcessingState = "CANCELLED";
        message.Partial = true;
        message.CompletionReason = "CANCELLED";
        message.CompletedAt = execution.UpdatedAt;
        var conversation = await db.Conversations.SingleAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        db.Events.Add(CreateEvent(
            conversation,
            tenantId,
            relationshipId,
            "stream.cancelled",
            message.MessageId,
            execution.ExecutionId,
            new { message = ToContract(message) }));
        var response = ToContract(execution);
        db.IdempotencyOutcomes.Add(CreateIdempotency(
            tenantId,
            participantId,
            relationshipId,
            "CANCEL",
            idempotencyKey,
            requestHash,
            response,
            message.MessageId,
            execution.ExecutionId));
        await db.SaveChangesAsync(cancellationToken);
        return new ConversationCommandResult<ConversationExecutionStatusV1>(response, false);
    }

    public async Task<IReadOnlyList<ConversationStreamEventV1>> GetEventReplayAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string? lastEventId,
        CancellationToken cancellationToken)
    {
        using var activity = StartActivity("bp.conversation.stream_replay", relationshipId);
        await EnsureAccessAsync(tenantId, participantId, relationshipId, cancellationToken);
        var after = lastEventId is null ? 0 : _cursorCodec.Decode(lastEventId, tenantId, relationshipId, "event");
        await using var db = await _conversationFactory.CreateDbContextAsync(cancellationToken);
        var events = await db.Events.AsNoTracking()
            .Where(value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.Sequence > after)
            .OrderBy(value => value.Sequence)
            .Take(500)
            .ToListAsync(cancellationToken);
        return events.Select(value => new ConversationStreamEventV1(
            SchemaVersion,
            _cursorCodec.Encode(tenantId, relationshipId, "event", value.Sequence),
            value.EventType,
            relationshipId,
            value.Sequence,
            value.MessageId,
            value.ExecutionId,
            value.OccurredAt,
            JsonDocument.Parse(value.DataJson).RootElement.Clone())).ToList();
    }

    private async Task<EmploymentRelationship> EnsureAccessAsync(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        await using var db = await _relationshipFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        if (relationship is null)
        {
            throw new ConversationNotAccessibleException();
        }

        var authorized = await db.RelationshipParticipants.AsNoTracking().AnyAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ParticipantId == participantId
                && value.Status == "ACTIVE",
            cancellationToken);
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

    private static async Task<ConversationProjection> GetOrCreateConversationAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid relationshipId,
        CancellationToken cancellationToken)
    {
        var conversation = await db.Conversations.SingleOrDefaultAsync(
            value => value.TenantId == tenantId && value.RelationshipId == relationshipId,
            cancellationToken);
        if (conversation is not null)
        {
            return conversation;
        }

        conversation = new ConversationProjection { TenantId = tenantId, RelationshipId = relationshipId };
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
        object data) =>
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
        bool replayed) =>
        new(
            SchemaVersion,
            outcome,
            ToContract(message),
            execution.ExecutionId,
            _cursorCodec.Encode(tenantId, relationshipId, "timeline", message.Sequence),
            replayed);

    private static ConversationMessageV1 ToContract(ConversationMessage message) =>
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
            message.CompletedAt);

    private static ConversationExecutionStatusV1 ToContract(ConversationExecution execution) =>
        new(
            SchemaVersion,
            execution.ExecutionId,
            execution.ProcessingState,
            execution.Partial,
            execution.CompletionReason,
            execution.UpdatedAt);

    private static ConversationIdempotencyOutcome CreateIdempotency<T>(
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string operationFamily,
        Guid idempotencyKey,
        string requestHash,
        T response,
        Guid? messageId = null,
        Guid? executionId = null) =>
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

    private static Task<ConversationIdempotencyOutcome?> FindIdempotencyAsync(
        ConversationStoreDbContext db,
        Guid tenantId,
        Guid participantId,
        Guid relationshipId,
        string operationFamily,
        Guid idempotencyKey,
        CancellationToken cancellationToken) =>
        db.IdempotencyOutcomes.SingleOrDefaultAsync(
            value => value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.ActorParticipantId == participantId
                && value.OperationFamily == operationFamily
                && value.IdempotencyKey == idempotencyKey,
            cancellationToken);

    private static void EnsureMatchingHash(ConversationIdempotencyOutcome outcome, string requestHash)
    {
        if (!CryptographicOperations.FixedTimeEquals(
            Encoding.ASCII.GetBytes(outcome.RequestHash),
            Encoding.ASCII.GetBytes(requestHash)))
        {
            throw new ConversationIdempotencyConflictException();
        }
    }

    private static void ValidateSendRequest(SendConversationMessageRequestV1 request)
    {
        if (request.SchemaVersion != SchemaVersion
            || request.Content.Count != 1
            || request.Content[0].SchemaVersion != SchemaVersion
            || request.Content[0].BlockType != "TEXT"
            || string.IsNullOrWhiteSpace(request.Content[0].Text)
            || request.Content[0].Text.Length > 32000
            || request.Locale.Length is < 2 or > 35)
        {
            throw new ConversationRequestException("Conversation request is malformed or unsupported.");
        }
    }

    private static string HashCanonical<T>(T value) =>
        Convert.ToHexString(SHA256.HashData(JsonSerializer.SerializeToUtf8Bytes(value, JsonOptions))).ToLowerInvariant();

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