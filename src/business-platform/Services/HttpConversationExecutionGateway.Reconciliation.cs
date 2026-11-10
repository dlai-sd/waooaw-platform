// Implements: architecture/reference/components/conversation-core.md section 4.2.
// constitutional_basis: C-023, C-026, C-059, C-063; ADR-046
using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed partial class HttpConversationExecutionGateway
    : IConversationExecutionReconciliationGateway
{
    public async Task<RuntimeReconciliationResultV1> ReadTerminalAsync(
        ConversationOriginalSourceV1 source,
        ConversationReconciliationAuthority authority,
        long afterSequence,
        CancellationToken cancellationToken
    )
    {
        var now = DateTimeOffset.UtcNow;
        if (workloadIdentity is null)
            throw new ConversationExecutionUnavailableException();
        if (
            authority.ExpiresAt <= now
            || authority.CreatedAt > now
            || authority.ExpiresAt > authority.CreatedAt.AddMinutes(5)
            || afterSequence < 0
            || authority.AuthorityId == Guid.Empty
            || authority.RequesterId == Guid.Empty
            || authority.EvidenceId == Guid.Empty
            || authority.Role is not ("OWNER" or "MANAGER")
            || authority.ExpectedProjectionVersion < 0
            || authority.DecisionSpaceVersion < 1
            || authority.SourceDigest != ConversationReconciliationBinding.Digest(source)
            || authority.TenantId != source.TenantId
            || authority.RelationshipId != source.RelationshipId
        )
            throw new ConversationNotAccessibleException();
        var body = new RuntimeReconciliationRequestV1(
            "1.0",
            source.OriginalMessageId,
            authority.SourceDigest,
            afterSequence,
            authority.AuthorityId,
            authority.ExpiresAt,
            authority.ExpectedProjectionVersion
        );
        var canonical = AgentAdmissionCanonicalizer.Canonicalize(
            JsonSerializer.SerializeToElement(body, ConversationReconciliationBinding.Json)
        );
        const string route =
            "/api/v1/internal/conversations/{conversationId}/executions/{executionId}/reconcile";
        const string operation = "reconcileConversationExecutionInternal";
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"api/v1/internal/conversations/{source.ConversationId:D}/executions/{source.ExecutionId:D}/reconcile"
        );
        request.Headers.Add("Idempotency-Key", authority.IdempotencyKey.ToString("D"));
        request.Headers.Add("X-Correlation-Id", authority.AuthorityId.ToString("D"));
        request.Content = new StringContent(canonical, Encoding.UTF8, "application/json");
        request.Headers.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            workloadIdentity.Sign(
                new DelegatedRequestContext(
                    authority.RequesterId.ToString("D"),
                    authority.Role,
                    authority.TenantId.ToString("D"),
                    authority.RelationshipId.ToString("D"),
                    "READ_EXISTING_RUNTIME_RESULT",
                    source.ConversationId.ToString("D"),
                    authority.AuthorityId.ToString("D"),
                    authority.IdempotencyKey.ToString("D"),
                    new Dictionary<string, string>
                    {
                        ["message"] = source.OriginalMessageId.ToString("D"),
                        ["source_digest"] = authority.SourceDigest,
                        ["after_sequence"] = afterSequence.ToString(CultureInfo.InvariantCulture),
                        ["projection_version"] = authority.ExpectedProjectionVersion.ToString(
                            CultureInfo.InvariantCulture
                        ),
                        ["decision_space"] = authority.DecisionSpaceVersion.ToString(
                            CultureInfo.InvariantCulture
                        ),
                        ["constitutional_decision"] = $"ce-decision:{authority.EvidenceId:D}",
                        ["constitutional_evidence"] = $"ce-evidence:{authority.EvidenceId:D}",
                    },
                    authority.AuthorityId.ToString("D")
                ),
                workloadIdentity.GetAudience("professional-runtime"),
                "POST",
                route,
                operation,
                1,
                AgentAdmissionCanonicalizer.Digest(canonical)["sha256:".Length..],
                now
            )
        );
        var client = httpClientFactory.CreateClient("ConversationProfessionalRuntime");
        if (client.BaseAddress?.Scheme != Uri.UriSchemeHttps)
            throw new ConversationExecutionUnavailableException();
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(
            TimeSpan.FromSeconds(Math.Min(10, (authority.ExpiresAt - now).TotalSeconds))
        );
        try
        {
            using var response = await client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                deadline.Token
            );
            if (response.StatusCode == HttpStatusCode.Locked)
                throw new ConversationStoppedException();
            if (response.StatusCode == HttpStatusCode.Conflict)
                throw new ConversationStateConflictException();
            if (response.StatusCode is HttpStatusCode.Unauthorized or HttpStatusCode.NotFound)
                throw new ConversationNotAccessibleException();
            if (
                response.StatusCode != HttpStatusCode.OK
                || response.Content.Headers.ContentType?.MediaType != "application/json"
            )
                throw new ConversationExecutionUnavailableException();
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            using var payload = new MemoryStream();
            var buffer = new byte[4096];
            int count;
            while ((count = await stream.ReadAsync(buffer, deadline.Token)) > 0)
            {
                if (payload.Length + count > 4_194_304)
                    throw new ConversationExecutionUnavailableException();
                payload.Write(buffer, 0, count);
            }
            using var document = JsonDocument.Parse(payload.ToArray());
            RuntimeEventStreamReader.ValidateUniqueProperties(document.RootElement);
            var result =
                document.RootElement.Deserialize<RuntimeReconciliationResultV1>(
                    new JsonSerializerOptions(ConversationReconciliationBinding.Json)
                    {
                        RespectRequiredConstructorParameters = true,
                    }
                ) ?? throw new ConversationExecutionUnavailableException();
            ValidateReconciliationResult(
                result,
                document.RootElement,
                source,
                authority,
                afterSequence
            );
            if (authority.ExpiresAt <= DateTimeOffset.UtcNow)
                throw new ConversationNotAccessibleException();
            return result;
        }
        catch (Exception failure)
            when (failure is HttpRequestException or IOException or JsonException)
        {
            throw new ConversationExecutionUnavailableException();
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new ConversationExecutionUnavailableException();
        }
    }

    internal static void ValidateReconciliationResult(
        RuntimeReconciliationResultV1 result,
        JsonElement wire,
        ConversationOriginalSourceV1 source,
        ConversationReconciliationAuthority authority,
        long afterSequence
    )
    {
        ValidateReconciliationShape(result, source, authority, afterSequence);
        if (result.State == "UNKNOWN")
            return;
        var canonical = new StringBuilder();
        WriteAsciiCanonical(wire, canonical, excludeDigest: true);
        var digest =
            "sha256:"
            + Convert.ToHexStringLower(
                SHA256.HashData(Encoding.UTF8.GetBytes(canonical.ToString()))
            );
        if (digest != result.ResultDigest)
            throw new ConversationStateConflictException();
    }

    internal static void ValidateReconciliationShape(
        RuntimeReconciliationResultV1 result,
        ConversationOriginalSourceV1 source,
        ConversationReconciliationAuthority authority,
        long afterSequence
    )
    {
        if (
            result.SchemaVersion != "1.0"
            || result.ExecutionId != source.ExecutionId
            || result.ConversationId != source.ConversationId
            || result.OriginalMessageId != source.OriginalMessageId
            || result.ReconciliationAuthorityId != authority.AuthorityId
            || result.OriginalSourceDigest != authority.SourceDigest
            || result.Events is null
            || result.Events.Count > 4096
        )
            throw new ConversationStateConflictException();
        if (result.State == "UNKNOWN")
        {
            if (
                result.Events.Count != 0
                || result.ResultDigest is not null
                || result.OriginalRequestDigest is not null
                || result.NextAction != "OPERATOR_RECONCILIATION_REQUIRED"
            )
                throw new ConversationStateConflictException();
            return;
        }
        if (
            result.State is not ("COMPLETED" or "FAILED" or "CANCELLED")
            || result.NextAction != "RECONCILE_CANONICAL_PROJECTION"
            || !IsDigest(result.OriginalRequestDigest)
            || !IsDigest(result.ResultDigest)
        )
            throw new ConversationStateConflictException();
        var sequence = afterSequence;
        foreach (var value in result.Events)
        {
            if (
                value is null
                || value.SchemaVersion != "1.0"
                || value.ExecutionId != source.ExecutionId
                || value.ConversationId != source.ConversationId
                || value.MessageId != source.OriginalMessageId
                || value.Sequence != ++sequence
                || value.EventId != $"{source.ExecutionId:D}:{sequence}"
                || value.OccurredAt == default
                || value.EventType == "heartbeat"
                || value.Data.ValueKind != JsonValueKind.Object
            )
                throw new ConversationStateConflictException();
            RuntimeEventStreamReader.ValidateUniqueProperties(value.Data);
            RuntimeEventStreamReader.ValidatePayload(value);
            if (
                value != result.Events[^1]
                && value.EventType
                    is "execution.completed"
                        or "execution.failed"
                        or "execution.cancelled"
                        or "execution.stopped"
            )
                throw new ConversationStateConflictException();
        }
        if (result.Events.Count > 0)
        {
            var terminal = result.Events[^1];
            var type = result.State switch
            {
                "COMPLETED" => "execution.completed",
                "FAILED" => "execution.failed",
                _ => "execution.cancelled",
            };
            if (
                terminal.EventType != type
                || terminal.Data.GetProperty("state").GetString() != result.State
            )
                throw new ConversationStateConflictException();
        }
    }

    private static bool IsDigest(string? value) =>
        value is { Length: 71 }
        && value.StartsWith("sha256:", StringComparison.Ordinal)
        && value[7..].All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');

    private static void WriteAsciiCanonical(
        JsonElement value,
        StringBuilder text,
        bool excludeDigest = false
    )
    {
        switch (value.ValueKind)
        {
            case JsonValueKind.Object:
                text.Append('{');
                var first = true;
                foreach (
                    var property in value
                        .EnumerateObject()
                        .OrderBy(property => property.Name, StringComparer.Ordinal)
                )
                {
                    if (excludeDigest && property.Name == "resultDigest")
                        continue;
                    if (!first)
                        text.Append(',');
                    first = false;
                    WriteAsciiString(property.Name, text);
                    text.Append(':');
                    WriteAsciiCanonical(property.Value, text);
                }
                text.Append('}');
                break;
            case JsonValueKind.Array:
                text.Append('[');
                var separator = "";
                foreach (var item in value.EnumerateArray())
                {
                    text.Append(separator);
                    separator = ",";
                    WriteAsciiCanonical(item, text);
                }
                text.Append(']');
                break;
            case JsonValueKind.String:
                WriteAsciiString(value.GetString()!, text);
                break;
            default:
                text.Append(value.GetRawText());
                break;
        }
    }

    private static void WriteAsciiString(string value, StringBuilder text)
    {
        text.Append('"');
        foreach (var character in value)
            text.Append(
                character switch
                {
                    '"' => "\\\"",
                    '\\' => "\\\\",
                    '\b' => "\\b",
                    '\f' => "\\f",
                    '\n' => "\\n",
                    '\r' => "\\r",
                    '\t' => "\\t",
                    < ' ' or >= '\x7f' => "\\u"
                        + ((int)character).ToString("x4", CultureInfo.InvariantCulture),
                    _ => character.ToString(),
                }
            );
        text.Append('"');
    }
}
