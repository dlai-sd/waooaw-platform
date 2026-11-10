// Implements: WC-134 R006/R007; conversation-core.md Section4 internal PR event consumption.
// constitutional_basis: C-005, C-023, C-059, C-063; ADR-046
using System.Globalization;
using System.Runtime.CompilerServices;
using System.Text;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed record RuntimeExecutionEventV1(
    string SchemaVersion,
    string EventId,
    string EventType,
    Guid ConversationId,
    Guid ExecutionId,
    Guid MessageId,
    long Sequence,
    DateTimeOffset OccurredAt,
    JsonElement Data
);

public interface IConversationExecutionEventSource
{
    IAsyncEnumerable<RuntimeExecutionEventV1> ReadEventsAsync(
        Guid conversationId,
        Guid messageId,
        ConversationExecutionCallerV1 caller,
        Guid idempotencyKey,
        long afterSequence,
        CancellationToken cancellationToken
    );
}

public sealed partial class HttpConversationExecutionGateway
{
    public async IAsyncEnumerable<RuntimeExecutionEventV1> ReadEventsAsync(
        Guid conversationId,
        Guid messageId,
        ConversationExecutionCallerV1 caller,
        Guid idempotencyKey,
        long afterSequence,
        [EnumeratorCancellation] CancellationToken cancellationToken
    )
    {
        if (
            workloadIdentity is null
            || conversationId == Guid.Empty
            || messageId == Guid.Empty
            || caller.RuntimeExecutionId == Guid.Empty
            || caller.TenantId == Guid.Empty
            || caller.RelationshipId == Guid.Empty
            || caller.ActorId == Guid.Empty
            || string.IsNullOrWhiteSpace(caller.ActorRole)
            || string.IsNullOrWhiteSpace(caller.ConstitutionalDecisionRef)
            || idempotencyKey == Guid.Empty
            || afterSequence < 0
            || caller.RuntimeExecutionId
                != ConversationExecutionIdentity.Create(
                    caller.TenantId,
                    caller.RelationshipId,
                    caller.ActorId,
                    conversationId,
                    idempotencyKey
                )
        )
            throw new ConversationExecutionUnavailableException();
        var cursor =
            afterSequence == 0
                ? string.Empty
                : $"{caller.RuntimeExecutionId:D}:{afterSequence.ToString(CultureInfo.InvariantCulture)}";
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            $"api/v1/internal/conversations/{conversationId:D}/executions/{caller.RuntimeExecutionId:D}/stream"
        );
        request.Headers.Add("Accept", "text/event-stream");
        request.Headers.Add("X-Correlation-Id", caller.RuntimeExecutionId.ToString("D"));
        if (cursor.Length > 0)
            request.Headers.Add("Last-Event-ID", cursor);
        SignRequest(
            request,
            caller,
            conversationId,
            messageId,
            caller.RuntimeExecutionId,
            idempotencyKey,
            "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/stream",
            "streamConversationExecution",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            cursor
        );
        var client = httpClientFactory.CreateClient("ConversationProfessionalRuntime");
        if (client.BaseAddress?.Scheme != Uri.UriSchemeHttps)
            throw new ConversationExecutionUnavailableException();
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(30));
        using var response = await SendStreamRequestAsync(
            client,
            request,
            deadline.Token,
            cancellationToken
        );
        if (response.StatusCode == System.Net.HttpStatusCode.Locked)
            throw new ConversationStoppedException();
        if (response.StatusCode == System.Net.HttpStatusCode.Gone)
            throw new ConversationCursorExpiredException();
        if (
            response.StatusCode != System.Net.HttpStatusCode.OK
            || response.Content.Headers.ContentType?.MediaType != "text/event-stream"
        )
            throw new ConversationExecutionUnavailableException();
        await using var stream = await OpenStreamAsync(response, deadline.Token, cancellationToken);
        var reader = new RuntimeEventStreamReader(
            stream,
            conversationId,
            messageId,
            caller.RuntimeExecutionId,
            afterSequence
        );
        while (true)
        {
            var next = await ReadStreamEventAsync(reader, deadline.Token, cancellationToken);
            if (next is null)
                yield break;
            yield return next;
        }
    }

    private static async Task<Stream> OpenStreamAsync(
        HttpResponseMessage response,
        CancellationToken token,
        CancellationToken callerToken
    )
    {
        try
        {
            return await response.Content.ReadAsStreamAsync(token);
        }
        catch (Exception failure) when (failure is HttpRequestException or IOException)
        {
            throw new ConversationExecutionUnavailableException();
        }
        catch (OperationCanceledException) when (!callerToken.IsCancellationRequested)
        {
            throw new ConversationExecutionUnavailableException();
        }
    }

    private static async Task<HttpResponseMessage> SendStreamRequestAsync(
        HttpClient client,
        HttpRequestMessage request,
        CancellationToken token,
        CancellationToken callerToken
    )
    {
        try
        {
            return await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, token);
        }
        catch (HttpRequestException)
        {
            throw new ConversationExecutionUnavailableException();
        }
        catch (OperationCanceledException) when (!callerToken.IsCancellationRequested)
        {
            throw new ConversationExecutionUnavailableException();
        }
    }

    private static async Task<RuntimeExecutionEventV1?> ReadStreamEventAsync(
        RuntimeEventStreamReader reader,
        CancellationToken token,
        CancellationToken callerToken
    )
    {
        try
        {
            return await reader.NextAsync(token);
        }
        catch (Exception failure)
            when (failure is IOException or JsonException or DecoderFallbackException)
        {
            throw new ConversationExecutionUnavailableException();
        }
        catch (OperationCanceledException) when (!callerToken.IsCancellationRequested)
        {
            throw new ConversationExecutionUnavailableException();
        }
    }
}

internal sealed class RuntimeEventStreamReader(
    Stream stream,
    Guid conversationId,
    Guid messageId,
    Guid executionId,
    long afterSequence
)
{
    private const int MaximumFrameBytes = 262_144;
    private static readonly UTF8Encoding Utf8 = new(false, true);
    private static readonly HashSet<string> EventTypes = new(StringComparer.Ordinal)
    {
        "execution.accepted",
        "processing.started",
        "response.delta",
        "response.system",
        "card.proposed",
        "evidence.pending",
        "evidence.recorded",
        "execution.completed",
        "execution.failed",
        "execution.cancelled",
        "execution.stopped",
        "reconciliation.required",
        "heartbeat",
    };
    private readonly byte[] _buffer = new byte[4096];
    private readonly byte[] _line = new byte[MaximumFrameBytes];
    private int _offset;
    private int _count;
    private long _sequence = afterSequence;
    private bool _terminal;

    public async Task<RuntimeExecutionEventV1?> NextAsync(CancellationToken cancellationToken)
    {
        if (_terminal)
            return null;
        while (true)
        {
            string? id = null;
            string? eventType = null;
            var data = new StringBuilder();
            var frameBytes = 0;
            while (true)
            {
                var line = await ReadLineAsync(cancellationToken);
                if (line is null)
                    throw new IOException("Runtime stream ended without a terminal event.");
                frameBytes += Utf8.GetByteCount(line) + 1;
                if (frameBytes > MaximumFrameBytes)
                    throw new IOException("Runtime event exceeds the bounded frame limit.");
                if (line.Length == 0)
                    break;
                if (line.StartsWith(':'))
                    continue;
                var separator = line.IndexOf(':');
                var field = separator < 0 ? line : line[..separator];
                var value = separator < 0 ? string.Empty : line[(separator + 1)..];
                if (value.StartsWith(' '))
                    value = value[1..];
                switch (field)
                {
                    case "id":
                        if (id is not null)
                            throw new IOException("Runtime frame repeats its identity.");
                        id = value;
                        break;
                    case "event":
                        if (eventType is not null)
                            throw new IOException("Runtime frame repeats its event type.");
                        eventType = value;
                        break;
                    case "data":
                        if (data.Length > 0)
                            data.Append('\n');
                        data.Append(value);
                        break;
                }
            }
            if (data.Length == 0 && id is null && eventType is null)
                continue;
            var result = Decode(data.ToString(), id, eventType);
            if (result.EventType == "heartbeat")
                continue;
            if (result.Sequence != _sequence + 1)
                throw new IOException("Runtime event sequence requires reconciliation.");
            _sequence = result.Sequence;
            _terminal =
                result.EventType
                    is "execution.completed"
                        or "execution.failed"
                        or "execution.cancelled"
                        or "execution.stopped";
            return result;
        }
    }

    private RuntimeExecutionEventV1 Decode(string json, string? id, string? eventType)
    {
        using var document = JsonDocument.Parse(json);
        ValidateUniqueProperties(document.RootElement);
        var result =
            document.RootElement.Deserialize<RuntimeExecutionEventV1>(
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
                {
                    RespectRequiredConstructorParameters = true,
                }
            ) ?? throw new JsonException("Runtime event is missing.");
        if (
            result.SchemaVersion != "1.0"
            || !EventTypes.Contains(result.EventType)
            || result.EventType != eventType
            || result.ConversationId != conversationId
            || result.ExecutionId != executionId
            || result.MessageId != messageId
            || result.Sequence < 1
            || result.OccurredAt == default
            || result.Data.ValueKind != JsonValueKind.Object
            || result.EventId
                != $"{executionId:D}:{result.Sequence.ToString(CultureInfo.InvariantCulture)}"
            || (
                result.EventType == "heartbeat"
                    ? id is not null || result.Sequence != _sequence
                    : id != result.EventId
            )
        )
            throw new JsonException("Runtime event identity or contract is invalid.");
        ValidatePayload(result);
        return result;
    }

    internal static void ValidatePayload(RuntimeExecutionEventV1 value)
    {
        var data = value.Data;
        bool StringIs(string name, params string[] allowed) =>
            data.TryGetProperty(name, out var property)
            && property.ValueKind == JsonValueKind.String
            && allowed.Contains(property.GetString(), StringComparer.Ordinal);
        bool BoundedString(string name, int minimum, int maximum) =>
            data.TryGetProperty(name, out var property)
            && property.ValueKind == JsonValueKind.String
            && property.GetString() is { } text
            && text.Length >= minimum
            && text.Length <= maximum
            && !text.Contains('\0');
        bool Timestamp(string name) =>
            data.TryGetProperty(name, out var property)
            && property.ValueKind == JsonValueKind.String
            && property.TryGetDateTimeOffset(out var timestamp)
            && timestamp != default;
        var valid = value.EventType switch
        {
            "execution.accepted" or "processing.started" or "heartbeat" => Timestamp("serverTime"),
            "response.delta" => data.TryGetProperty("contentIndex", out var index)
                && index.ValueKind == JsonValueKind.Number
                && index.TryGetInt32(out var contentIndex)
                && contentIndex >= 0
                && BoundedString("appendText", 0, 8000)
                && data.TryGetProperty("partial", out var partial)
                && partial.ValueKind == JsonValueKind.True,
            "response.system" => BoundedString("text", 1, 8000)
                && StringIs(
                    "code",
                    "MODEL_UNAVAILABLE",
                    "OPERATION_UNSUPPORTED",
                    "MATERIAL_UNCERTAINTY",
                    "SEMANTIC_PATH_UNREPRESENTABLE",
                    "POLICY_REJECTED",
                    "INTERNAL_FAILURE"
                ),
            "card.proposed" => StringIs("schemaVersion", "1.0")
                && StringIs("cardType", "ACTION", "PLAN", "DELIVERABLE", "DECISION")
                && data.TryGetProperty("cardId", out var cardId)
                && cardId.ValueKind == JsonValueKind.String
                && cardId.TryGetGuid(out var id)
                && id != Guid.Empty
                && StringIs("owner", "CUSTOMER", "PROFESSIONAL", "SHARED")
                && BoundedString("state", 1, 64)
                && BoundedString("effect", 1, 500)
                && data.TryGetProperty("data", out var cardData)
                && cardData.ValueKind == JsonValueKind.Object,
            "evidence.pending" => StringIs("state", "PENDING"),
            "evidence.recorded" => StringIs("state", "RECORDED")
                && data.TryGetProperty("evidenceRecordId", out var evidence)
                && evidence.ValueKind == JsonValueKind.String
                && evidence.TryGetGuid(out var evidenceId)
                && evidenceId != Guid.Empty,
            "reconciliation.required" => StringIs(
                "reason",
                "EVENT_CURSOR_EXPIRED",
                "EVENT_GAP",
                "STATE_CONFLICT"
            ),
            "execution.completed" => Terminal("COMPLETED", "COMPLETE"),
            "execution.failed" => Terminal("FAILED", "PARTIAL_FAILURE"),
            "execution.cancelled" => Terminal("CANCELLED", "CANCELLED"),
            "execution.stopped" => Terminal("STOPPED", "EMERGENCY_STOPPED"),
            _ => false,
        };
        if (!valid)
            throw new JsonException("Runtime event payload does not match its type.");

        bool Terminal(string state, string reason) =>
            StringIs("state", state)
            && StringIs("completionReason", reason)
            && data.TryGetProperty("partial", out var terminalPartial)
            && terminalPartial.ValueKind is JsonValueKind.True or JsonValueKind.False
            && (
                !data.TryGetProperty("errorCode", out var code)
                || code.ValueKind == JsonValueKind.Null
                || BoundedString("errorCode", 0, 64)
            );
    }

    internal static void ValidateUniqueProperties(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name))
                    throw new JsonException("Runtime event repeats a property.");
                ValidateUniqueProperties(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
            foreach (var child in element.EnumerateArray())
                ValidateUniqueProperties(child);
    }

    private async Task<string?> ReadLineAsync(CancellationToken cancellationToken)
    {
        var length = 0;
        while (true)
        {
            if (_offset == _count)
            {
                _count = await stream.ReadAsync(_buffer, cancellationToken);
                _offset = 0;
                if (_count == 0)
                {
                    if (length != 0)
                        throw new IOException("Runtime stream contains a truncated line.");
                    return null;
                }
            }
            var value = _buffer[_offset++];
            if (value == '\n')
            {
                if (length > 0 && _line[length - 1] == '\r')
                    length--;
                return Utf8.GetString(_line, 0, length);
            }
            if (length == _line.Length)
                throw new IOException("Runtime event line exceeds the bounded limit.");
            _line[length++] = value;
        }
    }
}
