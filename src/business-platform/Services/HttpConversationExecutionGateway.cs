// Implements: architecture/reference/components/conversation-core.md §4 Internal PR Execution Contract
// constitutional_basis: C-005, C-023, C-026, C-059, C-063, C-079

using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public interface IConversationBatchExecutionGateway
{
    Task<HttpConversationExecutionGateway.BatchExecutionReceipt> StartBatchAsync(
        Guid conversationId,
        Guid batchId,
        Guid runtimeExecutionId,
        Guid relationshipId,
        IReadOnlyList<HttpConversationExecutionGateway.BatchExecutionSource> sources,
        CancellationToken cancellationToken
    );
}

public sealed partial class HttpConversationExecutionGateway(
    IHttpClientFactory httpClientFactory,
    WorkloadIdentityClient? workloadIdentity = null
)
    : IConversationExecutionGateway,
        IConversationExecutionEventSource,
        IConversationBatchExecutionGateway
{
    public sealed record BatchExecutionSource(
        string SchemaVersion,
        Guid MessageId,
        Guid ExecutionId,
        long Sequence,
        Guid WorkItemId,
        int WorkItemRevision,
        Guid WorkItemInvocationId,
        Guid IdempotencyKey,
        Guid EvidenceId,
        string Text,
        string Language,
        OperationalMandateV1 OperationalMandate
    );

    public sealed record BatchStartRequest(
        string SchemaVersion,
        Guid BatchId,
        int DecisionSpaceVersion,
        string Locale,
        string SourceListDigest,
        IReadOnlyList<BatchExecutionSource> Sources,
        ExecutionText Content
    );

    public sealed record BatchExecutionReceipt(
        string SchemaVersion,
        Guid BatchId,
        Guid ExecutionId,
        Guid ConversationId,
        string SourceListDigest,
        string RequestDigest,
        string State,
        bool Replayed,
        DateTimeOffset AcceptedAt
    );

    public sealed record PreparedBatchExecution(
        BatchStartRequest Request,
        string CanonicalBody,
        string SourceListDigest,
        string RequestDigest
    );

    public static PreparedBatchExecution PrepareBatchExecution(
        Guid batchId,
        IReadOnlyList<BatchExecutionSource> sources
    )
    {
        if (batchId == Guid.Empty || sources.Count is < 2 or > 3)
            throw new ConversationStateConflictException();
        var first = sources[0];
        var sourceJson = JsonSerializer.SerializeToElement(
            sources.Select(source => new
            {
                source.SchemaVersion,
                source.MessageId,
                source.ExecutionId,
                source.Sequence,
                source.WorkItemId,
                source.WorkItemRevision,
                source.WorkItemInvocationId,
                source.IdempotencyKey,
                source.EvidenceId,
                source.Text,
                source.Language,
                source.OperationalMandate.MandateId,
                source.OperationalMandate.MandateDigest,
            }),
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var sourceCanonical = AgentAdmissionCanonicalizer.Canonicalize(sourceJson);
        var sourceDigest = AgentAdmissionCanonicalizer.Digest(sourceCanonical);
        var combined = string.Join("\n", sources.Select(source => source.Text));
        var body = new BatchStartRequest(
            "1.0",
            batchId,
            first.OperationalMandate.DecisionSpaceRevision,
            first.Language,
            sourceDigest,
            sources,
            new("1.0", "TEXT", combined, first.Language)
        );
        var canonicalBody = AgentAdmissionCanonicalizer.Canonicalize(
            JsonSerializer.SerializeToElement(
                body,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            )
        );
        return new(
            body,
            canonicalBody,
            sourceDigest,
            AgentAdmissionCanonicalizer.Digest(canonicalBody)
        );
    }

    public sealed record ExecutionText(
        string SchemaVersion,
        string ContentType,
        string Text,
        string Language
    );

    private sealed record StartRequest(
        string SchemaVersion,
        Guid MessageId,
        int DecisionSpaceVersion,
        string Locale,
        OperationalMandateV1 OperationalMandate,
        ExecutionText Content
    );

    private sealed record ExecutionReceipt(
        string SchemaVersion,
        Guid ExecutionId,
        Guid ConversationId,
        Guid MessageId,
        string State,
        bool Partial,
        bool Replayed,
        DateTimeOffset AcceptedAt,
        string? CompletionReason = null,
        DateTimeOffset? UpdatedAt = null
    );

    public async Task StartAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        Guid relationshipId,
        string locale,
        IReadOnlyList<ConversationTextBlockV1> content,
        OperationalMandateV1 operationalMandate,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    )
    {
        if (
            workloadIdentity is null
            || content.Count != 1
            || relationshipId != operationalMandate.RelationshipId
            || idempotencyKey != operationalMandate.IdempotencyIdentity
            || executionId == Guid.Empty
        )
            throw new ConversationExecutionUnavailableException();
        var runtimeExecutionId = ConversationExecutionIdentity.Create(
            operationalMandate.TenantId,
            relationshipId,
            operationalMandate.ActorId,
            conversationId,
            idempotencyKey
        );
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"api/v1/internal/conversations/{conversationId:D}/executions"
        );
        request.Headers.Add("Idempotency-Key", idempotencyKey.ToString("D"));
        request.Headers.Add("X-Correlation-Id", executionId.ToString("D"));
        var body = new StartRequest(
            "1.0",
            messageId,
            operationalMandate.DecisionSpaceRevision,
            locale,
            operationalMandate,
            new ExecutionText("1.0", "TEXT", content[0].Text, content[0].Language ?? locale)
        );
        var canonicalBody = AgentAdmissionCanonicalizer.Canonicalize(
            JsonSerializer.SerializeToElement(
                body,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            )
        );
        request.Content = new StringContent(canonicalBody, Encoding.UTF8, "application/json");
        SignRequest(
            request,
            new ConversationExecutionCallerV1(
                operationalMandate.TenantId,
                operationalMandate.RelationshipId,
                operationalMandate.ActorId,
                operationalMandate.ActorRole,
                operationalMandate.ConstitutionalDecisionRef,
                runtimeExecutionId
            ),
            conversationId,
            messageId,
            executionId,
            idempotencyKey,
            "/api/v1/internal/conversations/{conversationId}/executions",
            "startConversationExecution",
            AgentAdmissionCanonicalizer.Digest(canonicalBody)["sha256:".Length..]
        );
        await SendCommandAsync(
            request,
            runtimeExecutionId,
            conversationId,
            messageId,
            cancelling: false,
            cancellationToken
        );
    }

    public async Task<BatchExecutionReceipt> StartBatchAsync(
        Guid conversationId,
        Guid batchId,
        Guid runtimeExecutionId,
        Guid relationshipId,
        IReadOnlyList<BatchExecutionSource> sources,
        CancellationToken cancellationToken
    )
    {
        if (
            workloadIdentity is null
            || conversationId == Guid.Empty
            || batchId == Guid.Empty
            || runtimeExecutionId == Guid.Empty
            || sources.Count is < 2 or > 3
            || sources.Any(source =>
                source.OperationalMandate.RelationshipId != relationshipId
                || source.IdempotencyKey != source.OperationalMandate.IdempotencyIdentity
            )
        )
            throw new ConversationExecutionUnavailableException();
        var first = sources[0];
        var prepared = PrepareBatchExecution(batchId, sources);
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            $"api/v1/internal/conversations/{conversationId:D}/batch-executions"
        );
        request.Headers.Add("Idempotency-Key", batchId.ToString("D"));
        request.Headers.Add("X-Correlation-Id", runtimeExecutionId.ToString("D"));
        request.Content = new StringContent(
            prepared.CanonicalBody,
            Encoding.UTF8,
            "application/json"
        );
        SignRequest(
            request,
            new(
                first.OperationalMandate.TenantId,
                relationshipId,
                first.OperationalMandate.ActorId,
                first.OperationalMandate.ActorRole,
                first.OperationalMandate.ConstitutionalDecisionRef,
                runtimeExecutionId
            ),
            conversationId,
            first.MessageId,
            runtimeExecutionId,
            batchId,
            "/api/v1/internal/conversations/{conversationId}/batch-executions",
            "startConversationBatchExecution",
            prepared.RequestDigest["sha256:".Length..]
        );
        var client = httpClientFactory.CreateClient("ConversationProfessionalRuntime");
        if (client.BaseAddress?.Scheme != Uri.UriSchemeHttps)
            throw new ConversationExecutionUnavailableException();
        try
        {
            using var response = await client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                cancellationToken
            );
            if (response.StatusCode == System.Net.HttpStatusCode.Locked)
                throw new ConversationStoppedException();
            if (
                response.StatusCode
                is not (System.Net.HttpStatusCode.Accepted or System.Net.HttpStatusCode.OK)
            )
                throw new ConversationExecutionUnavailableException();
            var receipt = await response.Content.ReadFromJsonAsync<BatchExecutionReceipt>(
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
                {
                    RespectRequiredConstructorParameters = true,
                },
                cancellationToken
            );
            if (
                receipt is null
                || receipt.SchemaVersion != "1.0"
                || receipt.BatchId != batchId
                || receipt.ExecutionId != runtimeExecutionId
                || receipt.ConversationId != conversationId
                || !string.Equals(
                    receipt.SourceListDigest,
                    prepared.SourceListDigest,
                    StringComparison.Ordinal
                )
                || !string.Equals(
                    receipt.RequestDigest,
                    prepared.RequestDigest,
                    StringComparison.Ordinal
                )
                || receipt.State != "ACCEPTED"
                || receipt.AcceptedAt == default
                || (response.StatusCode == System.Net.HttpStatusCode.OK) != receipt.Replayed
            )
                throw new ConversationExecutionUnavailableException();
            return receipt;
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new ConversationExecutionUnavailableException();
        }
        catch (HttpRequestException)
        {
            throw new ConversationExecutionUnavailableException();
        }
        catch (JsonException)
        {
            throw new ConversationExecutionUnavailableException();
        }
    }

    private async Task<ExecutionReceipt> SendCommandAsync(
        HttpRequestMessage request,
        Guid runtimeExecutionId,
        Guid conversationId,
        Guid messageId,
        bool cancelling,
        CancellationToken cancellationToken
    )
    {
        var client = httpClientFactory.CreateClient("ConversationProfessionalRuntime");
        if (client.BaseAddress?.Scheme != Uri.UriSchemeHttps)
            throw new ConversationExecutionUnavailableException();
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(
            client.Timeout == Timeout.InfiniteTimeSpan ? TimeSpan.FromSeconds(10) : client.Timeout
        );
        try
        {
            using var response = await client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                deadline.Token
            );
            if (response.StatusCode == System.Net.HttpStatusCode.Locked)
                throw new ConversationStoppedException();
            if (
                response.StatusCode
                is not (System.Net.HttpStatusCode.Accepted or System.Net.HttpStatusCode.OK)
            )
                throw new ConversationExecutionUnavailableException();
            using var body = new MemoryStream();
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            var buffer = new byte[4096];
            int count;
            while ((count = await stream.ReadAsync(buffer, deadline.Token)) > 0)
            {
                if (body.Length + count > 16_384)
                    throw new ConversationExecutionUnavailableException();
                body.Write(buffer, 0, count);
            }
            using var document = JsonDocument.Parse(body.ToArray());
            if (
                document.RootElement.ValueKind != JsonValueKind.Object
                || document
                    .RootElement.EnumerateObject()
                    .Select(value => value.Name)
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .Count() != document.RootElement.EnumerateObject().Count()
            )
                throw new ConversationExecutionUnavailableException();
            var receipt = document.RootElement.Deserialize<ExecutionReceipt>(
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
                {
                    RespectRequiredConstructorParameters = true,
                }
            );
            if (
                receipt is null
                || receipt.SchemaVersion != "1.0"
                || receipt.ExecutionId != runtimeExecutionId
                || receipt.ConversationId != conversationId
                || receipt.MessageId != messageId
                || receipt.AcceptedAt == default
                || receipt.UpdatedAt < receipt.AcceptedAt
                || (response.StatusCode == System.Net.HttpStatusCode.OK && !receipt.Replayed)
                || (
                    response.StatusCode == System.Net.HttpStatusCode.Accepted
                    && (
                        receipt.Replayed
                        || (
                            !cancelling
                            && (
                                receipt.State != "ACCEPTED"
                                || receipt.Partial
                                || receipt.CompletionReason is not null
                            )
                        )
                        || (cancelling && receipt.State != "CANCELLED")
                    )
                )
                || receipt.State
                    is not (
                        "ACCEPTED"
                        or "QUEUED"
                        or "RUNNING"
                        or "COMPLETED"
                        or "FAILED"
                        or "CANCELLED"
                        or "STOPPED"
                        or "UNRESOLVED"
                    )
            )
                throw new ConversationExecutionUnavailableException();
            var terminal = receipt.State is "COMPLETED" or "FAILED" or "CANCELLED" or "STOPPED";
            if (
                (
                    terminal
                    && receipt.CompletionReason
                        != (
                            receipt.State switch
                            {
                                "COMPLETED" => "COMPLETE",
                                "FAILED" => "PARTIAL_FAILURE",
                                "CANCELLED" => "CANCELLED",
                                _ => "EMERGENCY_STOPPED",
                            }
                        )
                ) || (!terminal && receipt.CompletionReason is not null)
            )
                throw new ConversationExecutionUnavailableException();
            if (cancelling && !terminal)
                throw new ConversationExecutionUnavailableException();
            if (receipt.State == "STOPPED")
                throw new ConversationStoppedException();
            return receipt;
        }
        catch (Exception exception)
            when (exception is HttpRequestException or IOException or JsonException
                || (
                    exception is OperationCanceledException
                    && !cancellationToken.IsCancellationRequested
                )
            )
        {
            throw new ConversationExecutionUnavailableException();
        }
    }

    public async Task<ConversationExecutionStatusV1> CancelAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        ConversationExecutionCallerV1 caller,
        Guid idempotencyKey,
        CancellationToken cancellationToken
    )
    {
        if (
            workloadIdentity is null
            || caller.RuntimeExecutionId == Guid.Empty
            || caller.ActorId == Guid.Empty
            || caller.TenantId == Guid.Empty
            || caller.RelationshipId == Guid.Empty
            || string.IsNullOrWhiteSpace(caller.ActorRole)
            || string.IsNullOrWhiteSpace(caller.ConstitutionalDecisionRef)
        )
            throw new ConversationExecutionUnavailableException();
        using var request = new HttpRequestMessage(
            HttpMethod.Delete,
            $"api/v1/internal/conversations/{conversationId:D}/executions/{caller.RuntimeExecutionId:D}"
        );
        request.Headers.Add("Idempotency-Key", idempotencyKey.ToString("D"));
        request.Headers.Add("X-Correlation-Id", executionId.ToString("D"));
        SignRequest(
            request,
            caller,
            conversationId,
            messageId,
            executionId,
            idempotencyKey,
            "/api/v1/internal/conversations/{conversationId}/executions/{executionId}",
            "cancelConversationExecutionInternal",
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
        var receipt = await SendCommandAsync(
            request,
            caller.RuntimeExecutionId,
            conversationId,
            messageId,
            cancelling: true,
            cancellationToken
        );
        return new(
            "1.0",
            executionId,
            receipt.State,
            receipt.Partial,
            receipt.CompletionReason,
            receipt.UpdatedAt ?? receipt.AcceptedAt
        );
    }

    private void SignRequest(
        HttpRequestMessage request,
        ConversationExecutionCallerV1 caller,
        Guid conversationId,
        Guid messageId,
        Guid correlationId,
        Guid idempotencyKey,
        string route,
        string operation,
        string requestDigest,
        string? cursor = null
    )
    {
        var identity = workloadIdentity ?? throw new ConversationExecutionUnavailableException();
        var versions = new Dictionary<string, string>
        {
            ["constitutional_decision"] = caller.ConstitutionalDecisionRef,
            ["message"] = messageId.ToString("D"),
        };
        if (cursor is not null)
            versions["cursor"] = cursor;
        request.Headers.Authorization = new AuthenticationHeaderValue(
            "Bearer",
            identity.Sign(
                new DelegatedRequestContext(
                    caller.ActorId.ToString("D"),
                    caller.ActorRole,
                    caller.TenantId.ToString("D"),
                    caller.RelationshipId.ToString("D"),
                    operation,
                    conversationId.ToString("D"),
                    caller.RuntimeExecutionId.ToString("D"),
                    idempotencyKey.ToString("D"),
                    versions,
                    correlationId.ToString("D")
                ),
                identity.GetAudience("professional-runtime"),
                request.Method.Method,
                route,
                operation,
                1,
                requestDigest,
                DateTimeOffset.UtcNow
            )
        );
    }
}
