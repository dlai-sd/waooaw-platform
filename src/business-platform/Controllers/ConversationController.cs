// Implements: architecture/reference/components/conversation-core.md § Public BP Contract
// constitutional_basis: C-001, C-005, C-023, C-026, C-049, C-059, C-063

using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record ConversationProblemDetail(
    string Type,
    string Title,
    int Status,
    string Code,
    Guid CorrelationId,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? RetryAfterSeconds = null);

[ApiController]
[Authorize]
[Route("api/v1/employment/relationships/{relationshipId:guid}/conversation")]
public sealed class ConversationController : ControllerBase
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private readonly ConversationService _service;

    public ConversationController(ConversationService service)
    {
        _service = service;
    }

    [HttpGet("messages")]
    public async Task<IActionResult> ListMessagesAsync(
        Guid relationshipId,
        [FromQuery] string? cursor,
        [FromQuery] string? afterCursor,
        [FromQuery] int limit = 50,
        CancellationToken cancellationToken = default)
    {
        var correlationId = Guid.NewGuid();
        if (!TryGetAuthority(out var tenantId, out var participantId))
        {
            return ConversationProblem(
                StatusCodes.Status401Unauthorized,
                "CONVERSATION_SESSION_REQUIRED",
                "Authenticated conversation session required.",
                correlationId);
        }

        try
        {
            return Ok(await _service.ListMessagesAsync(
                tenantId,
                participantId,
                relationshipId,
                cursor,
                afterCursor,
                limit,
                cancellationToken));
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return MapProblem(exception, correlationId);
        }
    }

    [HttpPost("messages")]
    public async Task<IActionResult> SendMessageAsync(
        Guid relationshipId,
        [FromBody] SendConversationMessageRequestV1 request,
        CancellationToken cancellationToken)
    {
        var correlationId = Guid.NewGuid();
        if (!TryGetAuthority(out var tenantId, out var participantId))
        {
            return ConversationProblem(
                StatusCodes.Status401Unauthorized,
                "CONVERSATION_SESSION_REQUIRED",
                "Authenticated conversation session required.",
                correlationId);
        }

        if (!TryGetIdempotencyKey(out var idempotencyKey))
        {
            return ConversationProblem(
                StatusCodes.Status400BadRequest,
                "CONVERSATION_REQUEST_INVALID",
                "A UUID Idempotency-Key header is required.",
                correlationId);
        }

        try
        {
            var result = await _service.SendAsync(
                tenantId,
                participantId,
                relationshipId,
                idempotencyKey,
                request,
                cancellationToken);
            return result.Replayed ? Ok(result.Value) : Accepted(result.Value);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return MapProblem(exception, correlationId);
        }
    }

    [HttpPost("messages/{messageId:guid}/retry")]
    public async Task<IActionResult> RetryMessageAsync(
        Guid relationshipId,
        Guid messageId,
        CancellationToken cancellationToken)
    {
        var correlationId = Guid.NewGuid();
        if (!TryGetAuthority(out var tenantId, out var participantId))
        {
            return ConversationProblem(
                StatusCodes.Status401Unauthorized,
                "CONVERSATION_SESSION_REQUIRED",
                "Authenticated conversation session required.",
                correlationId);
        }

        if (!TryGetIdempotencyKey(out var idempotencyKey))
        {
            return ConversationProblem(
                StatusCodes.Status400BadRequest,
                "CONVERSATION_REQUEST_INVALID",
                "A UUID Idempotency-Key header is required.",
                correlationId);
        }

        try
        {
            var result = await _service.RetryAsync(
                tenantId,
                participantId,
                relationshipId,
                messageId,
                idempotencyKey,
                cancellationToken);
            return result.Replayed ? Ok(result.Value) : Accepted(result.Value);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return MapProblem(exception, correlationId);
        }
    }

    [HttpPut("read-position")]
    public async Task<IActionResult> UpdateReadPositionAsync(
        Guid relationshipId,
        [FromBody] UpdateConversationReadPositionRequestV1 request,
        CancellationToken cancellationToken)
    {
        var correlationId = Guid.NewGuid();
        if (!TryGetAuthority(out var tenantId, out var participantId))
        {
            return ConversationProblem(
                StatusCodes.Status401Unauthorized,
                "CONVERSATION_SESSION_REQUIRED",
                "Authenticated conversation session required.",
                correlationId);
        }

        if (!TryGetIdempotencyKey(out var idempotencyKey))
        {
            return ConversationProblem(
                StatusCodes.Status400BadRequest,
                "CONVERSATION_REQUEST_INVALID",
                "A UUID Idempotency-Key header is required.",
                correlationId);
        }

        try
        {
            var result = await _service.UpdateReadPositionAsync(
                tenantId,
                participantId,
                relationshipId,
                idempotencyKey,
                request,
                cancellationToken);
            return Ok(result.Value);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return MapProblem(exception, correlationId);
        }
    }

    [HttpGet("stream")]
    public async Task StreamAsync(
        Guid relationshipId,
        [FromHeader(Name = "Last-Event-ID")] string? lastEventId,
        CancellationToken cancellationToken)
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
        {
            Response.StatusCode = StatusCodes.Status401Unauthorized;
            return;
        }

        IReadOnlyList<ConversationStreamEventV1> replay;
        try
        {
            replay = await _service.GetEventReplayAsync(
                tenantId,
                participantId,
                relationshipId,
                lastEventId,
                cancellationToken);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            var result = MapProblem(exception, Guid.NewGuid());
            Response.StatusCode = result is ObjectResult objectResult
                ? objectResult.StatusCode ?? StatusCodes.Status500InternalServerError
                : StatusCodes.Status500InternalServerError;
            return;
        }

        Response.StatusCode = StatusCodes.Status200OK;
        Response.ContentType = "text/event-stream";
        Response.Headers.CacheControl = "no-store";
        Response.Headers["X-Accel-Buffering"] = "no";
        var cursor = lastEventId;
        var sequence = 1L;
        while (!cancellationToken.IsCancellationRequested)
        {
            foreach (var conversationEvent in replay)
            {
                await WriteEventAsync(conversationEvent, cancellationToken);
                cursor = conversationEvent.EventId;
                sequence = conversationEvent.Sequence;
            }

            var serverTime = DateTimeOffset.UtcNow;
            await WriteEventAsync(
                new ConversationStreamEventV1(
                    "1.0",
                    cursor ?? "heartbeat",
                    "heartbeat",
                    relationshipId,
                    sequence,
                    null,
                    null,
                    serverTime,
                    JsonSerializer.SerializeToElement(new { serverTime }, JsonOptions)),
                cancellationToken,
                includeCursor: false);
            await Task.Delay(TimeSpan.FromSeconds(1), cancellationToken);
            replay = await _service.GetEventReplayAsync(
                tenantId,
                participantId,
                relationshipId,
                cursor,
                cancellationToken);
        }
    }

    [HttpDelete("executions/{executionId:guid}")]
    public async Task<IActionResult> CancelExecutionAsync(
        Guid relationshipId,
        Guid executionId,
        CancellationToken cancellationToken)
    {
        var correlationId = Guid.NewGuid();
        if (!TryGetAuthority(out var tenantId, out var participantId))
        {
            return ConversationProblem(
                StatusCodes.Status401Unauthorized,
                "CONVERSATION_SESSION_REQUIRED",
                "Authenticated conversation session required.",
                correlationId);
        }

        if (!TryGetIdempotencyKey(out var idempotencyKey))
        {
            return ConversationProblem(
                StatusCodes.Status400BadRequest,
                "CONVERSATION_REQUEST_INVALID",
                "A UUID Idempotency-Key header is required.",
                correlationId);
        }

        try
        {
            var result = await _service.CancelAsync(
                tenantId,
                participantId,
                relationshipId,
                executionId,
                idempotencyKey,
                cancellationToken);
            return result.Replayed ? Ok(result.Value) : Accepted(result.Value);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return MapProblem(exception, correlationId);
        }
    }

    private async Task WriteEventAsync(
        ConversationStreamEventV1 conversationEvent,
        CancellationToken cancellationToken,
        bool includeCursor = true)
    {
        var data = JsonSerializer.Serialize(conversationEvent, JsonOptions);
        var cursor = includeCursor ? $"id: {conversationEvent.EventId}\n" : string.Empty;
        var frame = $"{cursor}event: {conversationEvent.EventType}\ndata: {data}\n\n";
        await Response.WriteAsync(frame, cancellationToken);
        await Response.Body.FlushAsync(cancellationToken);
    }

    private bool TryGetAuthority(out Guid tenantId, out Guid participantId)
    {
        tenantId = default;
        participantId = default;
        var tenantValid = HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var tenantValue)
            && tenantValue is string tenantText
            && Guid.TryParse(tenantText, out tenantId);
        var participantValue = User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        return tenantValid && Guid.TryParse(participantValue, out participantId);
    }

    private bool TryGetIdempotencyKey(out Guid idempotencyKey) =>
        Guid.TryParse(Request.Headers["Idempotency-Key"].FirstOrDefault(), out idempotencyKey);

    private IActionResult MapProblem(Exception exception, Guid correlationId) => exception switch
    {
        ConversationRequestException => ConversationProblem(
            StatusCodes.Status400BadRequest,
            "CONVERSATION_REQUEST_INVALID",
            "Conversation request is malformed or unsupported.",
            correlationId),
        ConversationNotAccessibleException => ConversationProblem(
            StatusCodes.Status404NotFound,
            "CONVERSATION_NOT_ACCESSIBLE",
            "Conversation is not accessible.",
            correlationId),
        ConversationIdempotencyConflictException => ConversationProblem(
            StatusCodes.Status409Conflict,
            "CONVERSATION_IDEMPOTENCY_CONFLICT",
            "Idempotency identity conflicts with a prior request.",
            correlationId),
        ConversationStateConflictException => ConversationProblem(
            StatusCodes.Status409Conflict,
            "CONVERSATION_STATE_CONFLICT",
            "Authoritative conversation state must be reconciled.",
            correlationId),
        ConversationCursorExpiredException => ConversationProblem(
            StatusCodes.Status410Gone,
            "CONVERSATION_CURSOR_EXPIRED",
            "Conversation cursor can no longer be resumed.",
            correlationId),
        ConversationRetryNotAllowedException => ConversationProblem(
            StatusCodes.Status422UnprocessableEntity,
            "CONVERSATION_RETRY_NOT_ALLOWED",
            "Conversation message cannot be retried in its current state.",
            correlationId),
        ConversationStoppedException => ConversationProblem(
            StatusCodes.Status423Locked,
            "CONVERSATION_STOPPED",
            "Conversation execution is stopped.",
            correlationId),
        ConversationExecutionUnavailableException => ConversationProblem(
            StatusCodes.Status503ServiceUnavailable,
            "CONVERSATION_EXECUTION_UNAVAILABLE",
            "Conversation execution is temporarily unavailable.",
            correlationId,
            30),
        ConstitutionalActionDeniedException => ConversationProblem(
            StatusCodes.Status409Conflict,
            "CONVERSATION_STATE_CONFLICT",
            "Conversation command is not permitted in its current state.",
            correlationId),
        _ => ConversationProblem(
            StatusCodes.Status503ServiceUnavailable,
            "CONSTITUTIONAL_ENGINE_UNAVAILABLE",
            "Constitutional governance is temporarily unavailable.",
            correlationId,
            30),
    };

    private ObjectResult ConversationProblem(
        int status,
        string code,
        string title,
        Guid correlationId,
        int? retryAfterSeconds = null)
    {
        if (retryAfterSeconds.HasValue)
        {
            Response.Headers.RetryAfter = retryAfterSeconds.Value.ToString(System.Globalization.CultureInfo.InvariantCulture);
        }

        return new ObjectResult(new ConversationProblemDetail(
            $"https://api.waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
            title,
            status,
            code,
            correlationId,
            retryAfterSeconds))
        {
            StatusCode = status,
            ContentTypes = { "application/problem+json" },
        };
    }
}