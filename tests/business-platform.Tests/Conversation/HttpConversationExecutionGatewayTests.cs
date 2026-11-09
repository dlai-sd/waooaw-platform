// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md §6.3
// constitutional_basis: C-005, C-023, C-026, C-059, C-063, C-076, C-079

using System.Net;
using System.Net.Http.Json;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Moq;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class HttpConversationExecutionGatewayTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>,
        IDisposable
{
    private readonly WorkloadIdentityClient _identity = fixture.CreateIdentity();

    [Fact]
    public async Task RecoverySignsFreshRequesterButBindsOriginalExecutionWithoutRedispatch()
    {
        var (source, permission) = RecoveryContext();
        var gateway = CreateGateway(request =>
        {
            Assert.Equal(HttpMethod.Post, request.Method);
            Assert.Equal($"/api/v1/internal/conversations/{source.ConversationId:D}/executions/{source.ExecutionId:D}/reconcile",
                request.RequestUri!.AbsolutePath);
            using var envelope = ReadEnvelope(request);
            var context = envelope.RootElement;
            Assert.Equal("reconcileConversationExecutionInternal", context.GetProperty("operation").GetString());
            Assert.Equal("READ_EXISTING_RUNTIME_RESULT", context.GetProperty("purpose").GetString());
            Assert.Equal(permission.RequesterId.ToString("D"), context.GetProperty("actor_subject").GetString());
            Assert.NotEqual(source.OriginalActorId.ToString("D"), context.GetProperty("actor_subject").GetString());
            Assert.Equal(permission.Role, context.GetProperty("effective_role").GetString());
            Assert.Equal(permission.AuthorityId.ToString("D"), context.GetProperty("command_id").GetString());
            var versions = context.GetProperty("expected_versions");
            Assert.Equal(permission.SourceDigest, versions.GetProperty("source_digest").GetString());
            Assert.Equal("4", versions.GetProperty("after_sequence").GetString());
            Assert.Equal("9", versions.GetProperty("projection_version").GetString());
            using var body = JsonDocument.Parse(request.Content!.ReadAsStringAsync().GetAwaiter().GetResult());
            Assert.Equal(7, body.RootElement.EnumerateObject().Count());
            Assert.Equal(source.OriginalMessageId.ToString("D"), body.RootElement.GetProperty("originalMessageId").GetString());
            Assert.Equal(permission.AuthorityId.ToString("D"), body.RootElement.GetProperty("reconciliationAuthorityId").GetString());
            return UnknownRecovery(source, permission);
        });
        var result = await gateway.ReadTerminalAsync(source, permission, 4, CancellationToken.None);
        Assert.Equal("UNKNOWN", result.State);
        Assert.Empty(result.Events);
        Assert.Null(result.ResultDigest);
    }

    [Fact]
    public async Task UnconfiguredRecoveryCannotResolveAClientOrFabricateAuthority()
    {
        var (source, permission) = RecoveryContext();
        var factory = new Mock<IHttpClientFactory>(MockBehavior.Strict);
        var gateway = new HttpConversationExecutionGateway(factory.Object);
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.ReadTerminalAsync(source, permission, 0, CancellationToken.None));
        factory.VerifyNoOtherCalls();
    }

    [Theory]
    [InlineData(HttpStatusCode.Locked, typeof(ConversationStoppedException))]
    [InlineData(HttpStatusCode.Conflict, typeof(ConversationStateConflictException))]
    [InlineData(HttpStatusCode.Unauthorized, typeof(ConversationNotAccessibleException))]
    [InlineData(HttpStatusCode.NotFound, typeof(ConversationNotAccessibleException))]
    [InlineData(HttpStatusCode.ServiceUnavailable, typeof(ConversationExecutionUnavailableException))]
    public async Task RecoveryPreservesOwnerFailureMeaning(HttpStatusCode status, Type expected)
    {
        var (source, permission) = RecoveryContext();
        var gateway = CreateGateway(_ => new HttpResponseMessage(status));
        var failure = await Record.ExceptionAsync(() => gateway.ReadTerminalAsync(source, permission, 0, CancellationToken.None));
        Assert.NotNull(failure);
        Assert.Equal(expected, failure.GetType());
    }

    [Fact]
    public async Task RecoveryRejectsOversizedResultBodyBeforeParsingOrProjection()
    {
        var (source, permission) = RecoveryContext();
        var gateway = CreateGateway(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(new string('x', 4_194_305), Encoding.UTF8, "application/json"),
        });
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.ReadTerminalAsync(source, permission, 0, CancellationToken.None));
    }

    [Fact]
    public async Task RecoveryDeadlineBoundsStalledBodyAndCannotBecomeUnknownSuccess()
    {
        var (source, permission) = RecoveryContext(lifetime: TimeSpan.FromMilliseconds(500));
        var gateway = CreateGateway(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StreamContent(new StalledBodyStream())
            {
                Headers = { ContentType = new("application/json") },
            },
        });
        using var outer = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        var elapsed = System.Diagnostics.Stopwatch.StartNew();
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.ReadTerminalAsync(source, permission, 0, outer.Token));
        Assert.True(elapsed.Elapsed >= TimeSpan.FromMilliseconds(100));
        Assert.False(outer.IsCancellationRequested);
    }

    [Fact]
    public async Task RecoveryPreservesCallerCancellationDuringResultRead()
    {
        var (source, permission) = RecoveryContext();
        var gateway = CreateGateway(_ => new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StreamContent(new StalledBodyStream())
            {
                Headers = { ContentType = new("application/json") },
            },
        });
        using var outer = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            gateway.ReadTerminalAsync(source, permission, 0, outer.Token));
    }

    private static (ConversationOriginalSourceV1, ConversationReconciliationAuthority) RecoveryContext(TimeSpan? lifetime = null)
    {
        var original = Mandate();
        var source = new ConversationOriginalSourceV1("1.0", original.TenantId, original.RelationshipId,
            ConversationId, ExecutionId(original), MessageId, original.ActorId, original.MandateId, original.MandateDigest);
        var now = DateTimeOffset.UtcNow;
        return (source, new ConversationReconciliationAuthority
        {
            AuthorityId = Guid.NewGuid(), TenantId = source.TenantId, RelationshipId = source.RelationshipId,
            RequesterId = Guid.NewGuid(), Role = "OWNER", AccountId = Guid.NewGuid(), MembershipId = Guid.NewGuid(),
            Issuer = "synthetic-identity", EvidenceId = Guid.NewGuid(), DecisionSpaceVersion = 1,
            IdempotencyKey = Guid.NewGuid(), SourceDigest = ConversationReconciliationBinding.Digest(source),
            CreatedAt = now, ExpiresAt = now.Add(lifetime ?? TimeSpan.FromMinutes(5)), ExpectedProjectionVersion = 9,
        });
    }

    private static HttpResponseMessage UnknownRecovery(ConversationOriginalSourceV1 source, ConversationReconciliationAuthority permission) =>
        new(HttpStatusCode.OK)
        {
            Content = JsonContent.Create(new RuntimeReconciliationResultV1("1.0", source.ConversationId,
                source.ExecutionId, source.OriginalMessageId, permission.SourceDigest, permission.AuthorityId,
                "UNKNOWN", [], "OPERATOR_RECONCILIATION_REQUIRED")),
        };

    [Fact]
    public async Task MissingWorkloadIdentityCannotDispatchEvenWithConfiguredClient()
    {
        var factory = new Mock<IHttpClientFactory>(MockBehavior.Strict);
        var gateway = new HttpConversationExecutionGateway(factory.Object);
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            Start(gateway, Mandate())
        );
        factory.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task PlaintextRuntimeCannotReceiveSignedContext()
    {
        using var client = new HttpClient(
            new StubHandler(_ =>
                throw new InvalidOperationException("Plaintext dispatch must not occur.")
            )
        )
        {
            BaseAddress = new Uri("http://professional-runtime/"),
        };
        var factory = new Mock<IHttpClientFactory>();
        factory
            .Setup(value => value.CreateClient("ConversationProfessionalRuntime"))
            .Returns(client);
        var gateway = new HttpConversationExecutionGateway(factory.Object, _identity);
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            Start(gateway, Mandate())
        );
    }

    private static readonly Guid ConversationId = new("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa");
    private static readonly Guid MessageId = new("cccccccc-cccc-4ccc-8ccc-cccccccccccc");

    [Theory]
    [InlineData(0)]
    [InlineData(2)]
    public async Task RuntimeStreamSignsExactOriginalIdentityAndCommittedCursor(long afterSequence)
    {
        var mandate = Mandate();
        var runtimeId = ExecutionId(mandate);
        var caller = new ConversationExecutionCallerV1(
            mandate.TenantId, mandate.RelationshipId, mandate.ActorId, mandate.ActorRole,
            mandate.ConstitutionalDecisionRef, runtimeId);
        var gateway = CreateGateway(request =>
        {
            Assert.Equal(HttpMethod.Get, request.Method);
            Assert.Equal(
                $"/api/v1/internal/conversations/{ConversationId:D}/executions/{runtimeId:D}/stream",
                request.RequestUri!.AbsolutePath);
            using var envelope = ReadEnvelope(request);
            var signed = envelope.RootElement;
            var expectedCursor = afterSequence == 0 ? "" : $"{runtimeId:D}:{afterSequence}";
            Assert.Equal("streamConversationExecution", signed.GetProperty("operation").GetString());
            Assert.Equal(mandate.TenantId.ToString("D"), signed.GetProperty("tenant_id").GetString());
            Assert.Equal(mandate.ActorId.ToString("D"), signed.GetProperty("actor_subject").GetString());
            Assert.Equal(runtimeId.ToString("D"), signed.GetProperty("command_id").GetString());
            Assert.Equal(mandate.IdempotencyIdentity.ToString("D"), signed.GetProperty("idempotency_key").GetString());
            Assert.Equal(MessageId.ToString("D"), signed.GetProperty("expected_versions").GetProperty("message").GetString());
            Assert.Equal(expectedCursor, signed.GetProperty("expected_versions").GetProperty("cursor").GetString());
            Assert.Equal(expectedCursor, request.Headers.TryGetValues("Last-Event-ID", out var values)
                ? values.Single() : "");
            return EventStream(RuntimeFrame(runtimeId, afterSequence + 1, "execution.completed",
                new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" }));
        });
        var events = new List<RuntimeExecutionEventV1>();
        await foreach (var value in gateway.ReadEventsAsync(
            ConversationId, MessageId, caller, mandate.IdempotencyIdentity, afterSequence, CancellationToken.None))
            events.Add(value);
        Assert.Single(events);
        Assert.Equal(afterSequence + 1, events[0].Sequence);
        Assert.Equal("COMPLETE", events[0].Data.GetProperty("completionReason").GetString());
    }

    [Fact]
    public async Task RuntimeStreamHeartbeatDoesNotAdvanceDurableCursor()
    {
        var mandate = Mandate();
        var runtimeId = ExecutionId(mandate);
        var gateway = CreateGateway(_ => EventStream(
            RuntimeFrame(runtimeId, 1, "execution.accepted", new { serverTime = DateTimeOffset.UtcNow })
            + RuntimeFrame(runtimeId, 1, "heartbeat", new { serverTime = DateTimeOffset.UtcNow }, durable: false)
            + RuntimeFrame(runtimeId, 2, "execution.completed",
                new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" })));
        var events = await ReadAllRuntimeEvents(gateway, mandate);
        Assert.Equal(new long[] { 1, 2 }, events.Select(value => value.Sequence));
    }

    [Theory]
    [InlineData("gap")]
    [InlineData("foreign-message")]
    [InlineData("duplicate-property")]
    [InlineData("wrong-frame-id")]
    [InlineData("wrong-type")]
    [InlineData("invalid-terminal")]
    [InlineData("oversize")]
    [InlineData("truncated")]
    public async Task RuntimeStreamRejectsInvalidFramesWithoutAcceptingAnEvent(string defect)
    {
        var mandate = Mandate();
        var runtimeId = ExecutionId(mandate);
        var frame = RuntimeFrame(runtimeId, defect == "gap" ? 2 : 1, "execution.completed",
            new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" });
        frame = defect switch
        {
            "foreign-message" => frame.Replace(MessageId.ToString("D"), Guid.NewGuid().ToString("D")),
            "duplicate-property" => frame.Replace("\"schemaVersion\":\"1.0\"", "\"schemaVersion\":\"1.0\",\"SchemaVersion\":\"1.0\""),
            "wrong-frame-id" => "id: wrong\n" + frame,
            "wrong-type" => frame.Replace("event: execution.completed", "event: card.proposed"),
            "invalid-terminal" => frame.Replace("\"partial\":false", "\"partial\":\"false\""),
            "oversize" => "data: " + new string('x', 262_145) + "\n\n",
            "truncated" => frame.TrimEnd('\n'),
            _ => frame,
        };
        var gateway = CreateGateway(_ => EventStream(frame));
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() => ReadAllRuntimeEvents(gateway, mandate));
    }

    [Theory]
    [InlineData(HttpStatusCode.Locked)]
    [InlineData(HttpStatusCode.Gone)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    public async Task RuntimeStreamPreservesStopAndCursorReconciliation(HttpStatusCode status)
    {
        var gateway = CreateGateway(_ => new HttpResponseMessage(status));
        if (status == HttpStatusCode.Locked)
            await Assert.ThrowsAsync<ConversationStoppedException>(() => ReadAllRuntimeEvents(gateway, Mandate()));
        else if (status == HttpStatusCode.Gone)
            await Assert.ThrowsAsync<ConversationCursorExpiredException>(() => ReadAllRuntimeEvents(gateway, Mandate()));
        else
            await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() => ReadAllRuntimeEvents(gateway, Mandate()));
    }

    [Fact]
    public async Task RuntimeStreamInterruptAfterCommittedEventCannotFabricateCompletion()
    {
        var mandate = Mandate();
        var runtimeId = ExecutionId(mandate);
        var gateway = CreateGateway(_ => EventStream(RuntimeFrame(runtimeId, 1, "execution.accepted",
            new { serverTime = DateTimeOffset.UtcNow })));
        var caller = new ConversationExecutionCallerV1(mandate.TenantId, mandate.RelationshipId,
            mandate.ActorId, mandate.ActorRole, mandate.ConstitutionalDecisionRef, runtimeId);
        await using var stream = gateway.ReadEventsAsync(
            ConversationId, MessageId, caller, mandate.IdempotencyIdentity, 0, CancellationToken.None).GetAsyncEnumerator();
        Assert.True(await stream.MoveNextAsync());
        Assert.Equal(1, stream.Current.Sequence);
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() => stream.MoveNextAsync().AsTask());
    }

    [Fact]
    public async Task RuntimeStreamPreservesCallerCancellationWhileWaitingForBody()
    {
        var mandate = Mandate();
        var caller = new ConversationExecutionCallerV1(mandate.TenantId, mandate.RelationshipId,
            mandate.ActorId, mandate.ActorRole, mandate.ConstitutionalDecisionRef, ExecutionId(mandate));
        using var cancelled = new CancellationTokenSource(TimeSpan.FromMilliseconds(50));
        var gateway = CreateGateway(_ =>
        {
            var content = new StreamContent(new StalledBodyStream());
            content.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("text/event-stream");
            return new HttpResponseMessage(HttpStatusCode.OK) { Content = content };
        });
        await using var stream = gateway.ReadEventsAsync(
            ConversationId, MessageId, caller, mandate.IdempotencyIdentity, 0, cancelled.Token).GetAsyncEnumerator();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() => stream.MoveNextAsync().AsTask());
        Assert.True(cancelled.IsCancellationRequested);
    }

    private static string RuntimeFrame(Guid runtimeId, long sequence, string eventType, object data, bool durable = true)
    {
        var id = $"{runtimeId:D}:{sequence}";
        return (durable ? $"id: {id}\n" : "") + $"event: {eventType}\ndata: "
            + JsonSerializer.Serialize(new
            {
                schemaVersion = "1.0", eventId = id, eventType,
                conversationId = ConversationId, executionId = runtimeId, messageId = MessageId,
                sequence, occurredAt = DateTimeOffset.UtcNow, data,
            }) + "\n\n";
    }

    private static HttpResponseMessage EventStream(string frames) =>
        new(HttpStatusCode.OK) { Content = new StringContent(frames, Encoding.UTF8, "text/event-stream") };

    private static async Task<List<RuntimeExecutionEventV1>> ReadAllRuntimeEvents(
        HttpConversationExecutionGateway gateway, OperationalMandateV1 mandate)
    {
        var result = new List<RuntimeExecutionEventV1>();
        var caller = new ConversationExecutionCallerV1(mandate.TenantId, mandate.RelationshipId,
            mandate.ActorId, mandate.ActorRole, mandate.ConstitutionalDecisionRef, ExecutionId(mandate));
        await foreach (var value in gateway.ReadEventsAsync(
            ConversationId, MessageId, caller, mandate.IdempotencyIdentity, 0, CancellationToken.None))
            result.Add(value);
        return result;
    }

    [Theory]
    [InlineData("literal <tag> & \\\"quoted\\\"")]
    [InlineData("\u092e\u0930\u093e\u0920\u0940 \ud83d\ude00")]
    [InlineData("line\u2028paragraph\u2029end")]
    public async Task CanonicalWireDigestPreservesUnicodeAndFreshRetryEnvelope(string text)
    {
        var envelopes = new List<(string Id, string Digest, string Body)>();
        var gateway = CreateGateway(request =>
        {
            using var envelope = ReadEnvelope(request);
            var body = request.Content!.ReadAsStringAsync().GetAwaiter().GetResult();
            var digest = envelope.RootElement.GetProperty("request_digest").GetString()!;
            Assert.Equal(
                Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(body))),
                digest
            );
            using var document = JsonDocument.Parse(body);
            Assert.Equal(
                text,
                document.RootElement.GetProperty("content").GetProperty("text").GetString()
            );
            envelopes.Add(
                (envelope.RootElement.GetProperty("envelope_id").GetString()!, digest, body)
            );
            return Acknowledgement(replayed: envelopes.Count > 1);
        });
        var mandate = Mandate();
        for (var attempt = 0; attempt < 2; attempt++)
            await gateway.StartAsync(
                ConversationId,
                ExecutionId(mandate),
                MessageId,
                mandate.RelationshipId,
                "en-IN",
                [new ConversationTextBlockV1("1.0", "TEXT", text, "en")],
                mandate,
                mandate.IdempotencyIdentity,
                CancellationToken.None
            );
        Assert.Equal(envelopes[0].Body, envelopes[1].Body);
        Assert.Equal(envelopes[0].Digest, envelopes[1].Digest);
        Assert.NotEqual(envelopes[0].Id, envelopes[1].Id);
    }

    [Fact]
    public async Task SendsExactMandateContentAndScopedAssertion()
    {
        HttpRequestMessage? captured = null;
        string? capturedBody = null;
        var gateway = CreateGateway(request =>
        {
            captured = request;
            capturedBody = request.Content!.ReadAsStringAsync().GetAwaiter().GetResult();
            return Acknowledgement();
        });
        var mandate = Mandate();
        var idempotencyKey = mandate.IdempotencyIdentity;

        await gateway.StartAsync(
            ConversationId,
            ExecutionId(mandate),
            MessageId,
            mandate.RelationshipId,
            "en-IN",
            [new ConversationTextBlockV1("1.0", "TEXT", "Prepare the profile", "en")],
            mandate,
            idempotencyKey,
            CancellationToken.None
        );

        Assert.NotNull(captured);
        Assert.Equal(
            idempotencyKey.ToString("D"),
            captured!.Headers.GetValues("Idempotency-Key").Single()
        );
        using var envelope = ReadEnvelope(captured);
        var token = envelope.RootElement;
        Assert.Equal("startConversationExecution", token.GetProperty("operation").GetString());
        Assert.Equal(mandate.TenantId.ToString("D"), token.GetProperty("tenant_id").GetString());
        Assert.Equal(mandate.ActorId.ToString("D"), token.GetProperty("actor_subject").GetString());
        using var document = JsonDocument.Parse(capturedBody!);
        var root = document.RootElement;
        Assert.Equal(
            AgentAdmissionCanonicalizer.Digest(root)["sha256:".Length..],
            token.GetProperty("request_digest").GetString()
        );
        Assert.Equal(
            "/api/v1/internal/conversations/{conversationId}/executions",
            token.GetProperty("route").GetString()
        );
        Assert.Equal(
            ExecutionId(mandate).ToString("D"),
            token.GetProperty("command_id").GetString()
        );
        Assert.Equal(
            ConversationId.ToString("D"),
            token.GetProperty("subject_reference").GetString()
        );
        Assert.Equal(
            mandate.ConstitutionalDecisionRef,
            token
                .GetProperty("expected_versions")
                .GetProperty("constitutional_decision")
                .GetString()
        );
        Assert.Equal(
            60,
            token.GetProperty("expires_at").GetInt64() - token.GetProperty("issued_at").GetInt64()
        );
        Assert.Equal(
            "CUSTOMER_PROFILING",
            root.GetProperty("operationalMandate").GetProperty("skillId").GetString()
        );
        Assert.Equal(
            mandate.MandateDigest,
            root.GetProperty("operationalMandate").GetProperty("mandateDigest").GetString()
        );
        Assert.Equal(
            "Prepare the profile",
            root.GetProperty("content").GetProperty("text").GetString()
        );
    }

    [Fact]
    public void ExecutionIdentityMatchesPythonUuid5AndSeparatesActorsAndKeys()
    {
        var mandate = Mandate();
        var actual = ExecutionId(mandate);
        Assert.Equal(Guid.Parse("3eb488ad-51e6-5409-988b-7c7cd8ed8389"), actual);
        Assert.NotEqual(
            actual,
            ConversationExecutionIdentity.Create(
                mandate.TenantId,
                mandate.RelationshipId,
                Guid.NewGuid(),
                ConversationId,
                mandate.IdempotencyIdentity
            )
        );
        Assert.NotEqual(
            actual,
            ConversationExecutionIdentity.Create(
                mandate.TenantId,
                mandate.RelationshipId,
                mandate.ActorId,
                ConversationId,
                Guid.NewGuid()
            )
        );
    }

    [Theory]
    [InlineData("execution")]
    [InlineData("conversation")]
    [InlineData("message")]
    [InlineData("schema")]
    [InlineData("state")]
    [InlineData("missing")]
    [InlineData("empty")]
    [InlineData("oversized")]
    [InlineData("duplicate")]
    [InlineData("case-duplicate")]
    [InlineData("not-replayed")]
    [InlineData("accepted-replayed")]
    [InlineData("partial")]
    [InlineData("completion")]
    [InlineData("accepted-at")]
    [InlineData("updated-before-accepted")]
    public async Task RejectsSuccessShapedInvalidAcknowledgements(string failure)
    {
        var mandate = Mandate();
        var gateway = CreateGateway(_ =>
        {
            var response = Acknowledgement();
            var fields = new Dictionary<string, object?>
            {
                ["schemaVersion"] = failure == "schema" ? "2.0" : "1.0",
                ["executionId"] = failure == "execution" ? Guid.NewGuid() : ExecutionId(mandate),
                ["conversationId"] = failure == "conversation" ? Guid.NewGuid() : ConversationId,
                ["messageId"] = failure == "message" ? Guid.NewGuid() : MessageId,
                ["state"] = failure == "state" ? "COMPLETED" : "ACCEPTED",
                ["partial"] = failure == "partial",
                ["replayed"] = failure == "accepted-replayed",
                ["acceptedAt"] =
                    failure == "accepted-at"
                        ? "0001-01-01T00:00:00Z"
                        : "2026-11-07T00:00:00Z",
                ["updatedAt"] =
                    failure == "updated-before-accepted"
                        ? "2026-11-06T00:00:00Z"
                        : "2026-11-07T00:00:00Z",
            };
            if (failure == "completion")
                fields["completionReason"] = "unexpected";
            if (failure == "missing")
                fields.Remove("replayed");
            response.Content = failure switch
            {
                "empty" => new StringContent(""),
                "oversized" => new StringContent(new string('x', 16_385)),
                "duplicate" => new StringContent(
                    "{\"schemaVersion\":\"1.0\",\"schemaVersion\":\"2.0\"}"
                ),
                "case-duplicate" => new StringContent(
                    "{\"schemaVersion\":\"1.0\",\"SchemaVersion\":\"2.0\"}"
                ),
                _ => JsonContent.Create(fields),
            };
            if (failure == "not-replayed")
                response.StatusCode = HttpStatusCode.OK;
            return response;
        });
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            Start(gateway, mandate)
        );
    }

    [Fact]
    public async Task AcceptsBoundTerminalReplayWithOriginalExecutionIdentity()
    {
        var gateway = CreateGateway(_ => Acknowledgement(replayed: true, state: "COMPLETED"));
        await Start(gateway, Mandate());
    }

    [Theory]
    [InlineData("QUEUED")]
    [InlineData("RUNNING")]
    [InlineData("UNRESOLVED")]
    [InlineData("FAILED")]
    [InlineData("CANCELLED")]
    public async Task AcceptsEveryBoundRuntimeReplayState(string state)
    {
        var gateway = CreateGateway(_ => Acknowledgement(replayed: true, state: state));

        await Start(gateway, Mandate());
    }

    [Fact]
    public async Task BoundStoppedReplayPreservesStopMeaning()
    {
        var gateway = CreateGateway(_ => Acknowledgement(replayed: true, state: "STOPPED"));

        await Assert.ThrowsAsync<ConversationStoppedException>(() => Start(gateway, Mandate()));
    }

    [Fact]
    public async Task LegacyLocalExecutionReferenceCanRetryTheOriginalRuntimeIdentity()
    {
        var gateway = CreateGateway(_ => Acknowledgement(replayed: true));
        var mandate = Mandate();
        await gateway.StartAsync(
            ConversationId,
            Guid.NewGuid(),
            MessageId,
            mandate.RelationshipId,
            "en-IN",
            [new ConversationTextBlockV1("1.0", "TEXT", "Prepare the profile", "en")],
            mandate,
            mandate.IdempotencyIdentity,
            CancellationToken.None
        );
    }

    [Fact]
    public async Task CancellationUsesOriginalRuntimeIdentityAndSignedCallerWithoutNewMandate()
    {
        var mandate = Mandate();
        var localId = Guid.NewGuid();
        var key = Guid.NewGuid();
        var gateway = CreateGateway(request =>
        {
            Assert.Equal(HttpMethod.Delete, request.Method);
            Assert.Equal(
                $"/api/v1/internal/conversations/{ConversationId:D}/executions/{ExecutionId(mandate):D}",
                request.RequestUri!.AbsolutePath
            );
            Assert.Equal(key.ToString("D"), request.Headers.GetValues("Idempotency-Key").Single());
            Assert.Null(request.Content);
            using var envelope = ReadEnvelope(request);
            Assert.Equal(
                mandate.ActorId.ToString("D"),
                envelope.RootElement.GetProperty("actor_subject").GetString()
            );
            Assert.Equal("DELETE", envelope.RootElement.GetProperty("method").GetString());
            Assert.Equal(
                "cancelConversationExecutionInternal",
                envelope.RootElement.GetProperty("operation").GetString()
            );
            Assert.Equal(
                "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                envelope.RootElement.GetProperty("request_digest").GetString()
            );
            return Acknowledgement(state: "CANCELLED", partial: false);
        });
        var result = await gateway.CancelAsync(
            ConversationId,
            localId,
            MessageId,
            Caller(mandate),
            key,
            CancellationToken.None
        );
        Assert.Equal(localId, result.ExecutionId);
        Assert.Equal("CANCELLED", result.State);
        Assert.False(result.Partial);
    }

    [Theory]
    [InlineData("identity")]
    [InlineData("execution")]
    [InlineData("actor")]
    [InlineData("tenant")]
    [InlineData("relationship")]
    [InlineData("role")]
    [InlineData("decision")]
    public async Task CancellationRejectsEveryIncompleteCallerAuthority(string defect)
    {
        var mandate = Mandate();
        var caller = Caller(mandate) with
        {
            RuntimeExecutionId =
                defect == "execution" ? Guid.Empty : ExecutionId(mandate),
            ActorId = defect == "actor" ? Guid.Empty : mandate.ActorId,
            TenantId = defect == "tenant" ? Guid.Empty : mandate.TenantId,
            RelationshipId =
                defect == "relationship" ? Guid.Empty : mandate.RelationshipId,
            ActorRole = defect == "role" ? " " : mandate.ActorRole,
            ConstitutionalDecisionRef =
                defect == "decision" ? " " : mandate.ConstitutionalDecisionRef,
        };
        var gateway =
            defect == "identity"
                ? new HttpConversationExecutionGateway(
                    new Mock<IHttpClientFactory>(MockBehavior.Strict).Object
                )
                : CreateGateway(_ =>
                    throw new InvalidOperationException("Invalid authority must not dispatch.")
                );

        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.CancelAsync(
                ConversationId,
                ExecutionId(mandate),
                MessageId,
                caller,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task CancellationUsesRuntimeUpdatedTimestampWhenPresent()
    {
        var mandate = Mandate();
        var updatedAt = DateTimeOffset.Parse("2026-11-07T00:00:01Z");
        var gateway = CreateGateway(_ =>
            new HttpResponseMessage(HttpStatusCode.Accepted)
            {
                Content = JsonContent.Create(
                    new
                    {
                        schemaVersion = "1.0",
                        executionId = ExecutionId(mandate),
                        conversationId = ConversationId,
                        messageId = MessageId,
                        state = "CANCELLED",
                        partial = false,
                        replayed = false,
                        acceptedAt = "2026-11-07T00:00:00Z",
                        updatedAt,
                        completionReason = "CANCELLED",
                    }
                ),
            }
        );

        var result = await gateway.CancelAsync(
            ConversationId,
            ExecutionId(mandate),
            MessageId,
            Caller(mandate),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(updatedAt, result.UpdatedAt);
    }

    [Theory]
    [InlineData("CANCELLED", true)]
    [InlineData("COMPLETED", false)]
    [InlineData("FAILED", true)]
    public async Task CancellationProjectsConfirmedTerminalReplay(string state, bool partial)
    {
        var mandate = Mandate();
        var gateway = CreateGateway(_ =>
            Acknowledgement(replayed: true, state: state, partial: partial)
        );
        var result = await gateway.CancelAsync(
            ConversationId,
            ExecutionId(mandate),
            MessageId,
            Caller(mandate),
            Guid.NewGuid(),
            CancellationToken.None
        );
        Assert.Equal(state, result.State);
        Assert.Equal(partial, result.Partial);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CancellationNeverReleasesOrRelabelsStop(bool locked)
    {
        var mandate = Mandate();
        var gateway = CreateGateway(_ =>
            locked
                ? new HttpResponseMessage(HttpStatusCode.Locked)
                : Acknowledgement(replayed: true, state: "STOPPED")
        );
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            gateway.CancelAsync(
                ConversationId,
                ExecutionId(mandate),
                MessageId,
                Caller(mandate),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task CancellationCannotInferCompletionFromAcceptedOrUnboundResponse()
    {
        var mandate = Mandate();
        var gateway = CreateGateway(_ => Acknowledgement());
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.CancelAsync(
                ConversationId,
                ExecutionId(mandate),
                MessageId,
                Caller(mandate),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        var wrongMessage = CreateGateway(_ => Acknowledgement(state: "CANCELLED"));
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            wrongMessage.CancelAsync(
                ConversationId,
                ExecutionId(mandate),
                Guid.NewGuid(),
                Caller(mandate),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
    }

    private static ConversationExecutionCallerV1 Caller(OperationalMandateV1 mandate) =>
        new(
            mandate.TenantId,
            mandate.RelationshipId,
            mandate.ActorId,
            mandate.ActorRole,
            mandate.ConstitutionalDecisionRef,
            ExecutionId(mandate)
        );

    [Fact]
    public async Task CallerCancellationRemainsCancellationNotRuntimeFailure()
    {
        var gateway = CreateGateway(_ => throw new TaskCanceledException());
        using var cancelled = new CancellationTokenSource();
        cancelled.Cancel();
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            Start(gateway, Mandate(), cancelled.Token)
        );
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CommandDeadlineAlsoBoundsAResponseBodyStalledAfterSuccessfulHeaders(
        bool cancelling
    )
    {
        var gateway = CreateGateway(
            _ => new HttpResponseMessage(HttpStatusCode.Accepted)
            {
                Content = new StreamContent(new StalledBodyStream()),
            },
            TimeSpan.FromMilliseconds(50)
        );
        var mandate = Mandate();
        using var outerCancellation = new CancellationTokenSource(TimeSpan.FromSeconds(5));
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            cancelling
                ? gateway.CancelAsync(
                    ConversationId,
                    ExecutionId(mandate),
                    MessageId,
                    Caller(mandate),
                    Guid.NewGuid(),
                    outerCancellation.Token
                )
                : Start(gateway, mandate, outerCancellation.Token)
        );
        Assert.False(outerCancellation.IsCancellationRequested);
    }

    [Fact]
    public async Task CallerCancellationDuringResponseBodyRemainsCancellation()
    {
        var gateway = CreateGateway(_ => new HttpResponseMessage(HttpStatusCode.Accepted)
        {
            Content = new StreamContent(new StalledBodyStream()),
        });
        using var cancelled = new CancellationTokenSource(TimeSpan.FromMilliseconds(50));
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            Start(gateway, Mandate(), cancelled.Token)
        );
        Assert.True(cancelled.IsCancellationRequested);
    }

    private sealed class StalledBodyStream : MemoryStream
    {
        public override async ValueTask<int> ReadAsync(
            Memory<byte> buffer,
            CancellationToken cancellationToken = default
        )
        {
            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
            return 0;
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task StartPreservesOwnerStopInsteadOfAcceptingOrOfferingOrdinaryRetry(bool locked)
    {
        var gateway = CreateGateway(_ =>
            locked
                ? new HttpResponseMessage(HttpStatusCode.Locked)
                : Acknowledgement(replayed: true, state: "STOPPED")
        );
        await Assert.ThrowsAsync<ConversationStoppedException>(() => Start(gateway, Mandate()));
    }

    [Theory]
    [InlineData(HttpStatusCode.Conflict)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    public async Task FailsClosedForAnyRejectedExecution(HttpStatusCode status)
    {
        var gateway = CreateGateway(_ => new HttpResponseMessage(status));
        var mandate = Mandate();
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.StartAsync(
                ConversationId,
                ExecutionId(mandate),
                MessageId,
                mandate.RelationshipId,
                "en-IN",
                [new ConversationTextBlockV1("1.0", "TEXT", "Prepare the profile", "en")],
                mandate,
                mandate.IdempotencyIdentity,
                CancellationToken.None
            )
        );
    }

    private static Guid ExecutionId(OperationalMandateV1 mandate) =>
        ConversationExecutionIdentity.Create(
            mandate.TenantId,
            mandate.RelationshipId,
            mandate.ActorId,
            ConversationId,
            mandate.IdempotencyIdentity
        );

    private static Task Start(
        HttpConversationExecutionGateway gateway,
        OperationalMandateV1 mandate,
        CancellationToken cancellationToken = default
    ) =>
        gateway.StartAsync(
            ConversationId,
            ExecutionId(mandate),
            MessageId,
            mandate.RelationshipId,
            "en-IN",
            [new ConversationTextBlockV1("1.0", "TEXT", "Prepare the profile", "en")],
            mandate,
            mandate.IdempotencyIdentity,
            cancellationToken
        );

    private static HttpResponseMessage Acknowledgement(
        bool replayed = false,
        string state = "ACCEPTED",
        bool partial = false
    )
    {
        var mandate = Mandate();
        return new HttpResponseMessage(replayed ? HttpStatusCode.OK : HttpStatusCode.Accepted)
        {
            Content = JsonContent.Create(
                new
                {
                    schemaVersion = "1.0",
                    executionId = ExecutionId(mandate),
                    conversationId = ConversationId,
                    messageId = MessageId,
                    state,
                    partial,
                    replayed,
                    acceptedAt = "2026-11-07T00:00:00Z",
                    completionReason = state switch
                    {
                        "COMPLETED" => "COMPLETE",
                        "CANCELLED" => "CANCELLED",
                        "FAILED" => "PARTIAL_FAILURE",
                        "STOPPED" => "EMERGENCY_STOPPED",
                        _ => null,
                    },
                }
            ),
        };
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task BatchStartSignsExactCanonicalSourcesAndValidatesReceipt(bool replayed)
    {
        var batchId = Guid.NewGuid();
        var runtimeExecutionId = Guid.NewGuid();
        var sources = BatchSources();
        var prepared = HttpConversationExecutionGateway.PrepareBatchExecution(batchId, sources);
        HttpRequestMessage? captured = null;
        var gateway = CreateGateway(
            request =>
            {
                captured = request;
                return new HttpResponseMessage(
                    replayed ? HttpStatusCode.OK : HttpStatusCode.Accepted
                )
                {
                    Content = JsonContent.Create(
                        new
                        {
                            schemaVersion = "1.0",
                            batchId,
                            executionId = runtimeExecutionId,
                            conversationId = ConversationId,
                            sourceListDigest = prepared.SourceListDigest,
                            requestDigest = prepared.RequestDigest,
                            state = "ACCEPTED",
                            replayed,
                            acceptedAt = "2026-11-07T00:00:00Z",
                        }
                    ),
                };
            }
        );

        var receipt = await gateway.StartBatchAsync(
            ConversationId,
            batchId,
            runtimeExecutionId,
            sources[0].OperationalMandate.RelationshipId,
            sources,
            CancellationToken.None
        );

        Assert.Equal(batchId, receipt.BatchId);
        Assert.Equal(
            $"/api/v1/internal/conversations/{ConversationId:D}/batch-executions",
            captured!.RequestUri!.AbsolutePath
        );
        Assert.Equal(batchId.ToString("D"), captured.Headers.GetValues("Idempotency-Key").Single());
        Assert.NotNull(captured.Headers.Authorization);
    }

    [Theory]
    [InlineData(HttpStatusCode.Locked, "stopped")]
    [InlineData(HttpStatusCode.BadGateway, "unavailable")]
    [InlineData(HttpStatusCode.Accepted, "mismatch")]
    [InlineData(HttpStatusCode.Accepted, "invalid-json")]
    public async Task BatchStartFailsClosedForRuntimeFailures(
        HttpStatusCode status,
        string failure
    )
    {
        var batchId = Guid.NewGuid();
        var runtimeExecutionId = Guid.NewGuid();
        var sources = BatchSources();
        var prepared = HttpConversationExecutionGateway.PrepareBatchExecution(batchId, sources);
        var gateway = CreateGateway(
            _ =>
                new(status)
                {
                    Content = failure == "invalid-json"
                        ? new StringContent("{invalid", Encoding.UTF8, "application/json")
                        : JsonContent.Create(
                            new
                            {
                                schemaVersion = "1.0",
                                batchId = failure == "mismatch" ? Guid.NewGuid() : batchId,
                                executionId = runtimeExecutionId,
                                conversationId = ConversationId,
                                sourceListDigest = prepared.SourceListDigest,
                                requestDigest = prepared.RequestDigest,
                                state = "ACCEPTED",
                                replayed = false,
                                acceptedAt = "2026-11-07T00:00:00Z",
                            }
                        ),
                }
        );
        Task Act() =>
            gateway.StartBatchAsync(
                ConversationId,
                batchId,
                runtimeExecutionId,
                sources[0].OperationalMandate.RelationshipId,
                sources,
                CancellationToken.None
            );

        if (failure == "stopped")
            await Assert.ThrowsAsync<ConversationStoppedException>(Act);
        else
            await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(Act);
    }

    [Fact]
    public async Task BatchStartRejectsMissingIdentityAndInvalidSourceCount()
    {
        var sources = BatchSources();
        var gateway = new HttpConversationExecutionGateway(
            Mock.Of<IHttpClientFactory>()
        );
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(
            () =>
                gateway.StartBatchAsync(
                    ConversationId,
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    sources[0].OperationalMandate.RelationshipId,
                    sources,
                    CancellationToken.None
                )
        );
        Assert.Throws<ConversationStateConflictException>(
            () =>
                HttpConversationExecutionGateway.PrepareBatchExecution(
                    Guid.NewGuid(),
                    [sources[0]]
                )
        );
    }

    [Theory]
    [InlineData("relationship")]
    [InlineData("idempotency")]
    public async Task BatchStartRejectsSourcesOutsideTheirMandateAuthority(string defect)
    {
        var sources = BatchSources().ToArray();
        if (defect == "idempotency")
            sources[0] = sources[0] with { IdempotencyKey = Guid.NewGuid() };
        var relationshipId =
            defect == "relationship"
                ? Guid.NewGuid()
                : sources[0].OperationalMandate.RelationshipId;
        var gateway = CreateGateway(_ =>
            throw new InvalidOperationException("Invalid sources must not dispatch.")
        );

        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
            gateway.StartBatchAsync(
                ConversationId,
                Guid.NewGuid(),
                Guid.NewGuid(),
                relationshipId,
                sources,
                CancellationToken.None
            )
        );
    }

    private static IReadOnlyList<HttpConversationExecutionGateway.BatchExecutionSource> BatchSources()
    {
        var mandate = Mandate();
        return Enumerable
            .Range(1, 2)
            .Select(sequence =>
            {
                var key = Guid.NewGuid();
                var sourceMandate = mandate with
                {
                    IdempotencyIdentity = key,
                    MandateId = Guid.NewGuid(),
                    MandateDigest = "sha256:" + sequence.ToString().PadLeft(64, 'a'),
                };
                return new HttpConversationExecutionGateway.BatchExecutionSource(
                    "1.0",
                    Guid.NewGuid(),
                    Guid.NewGuid(),
                    sequence,
                    Guid.Parse("66666666-6666-4666-8666-666666666666"),
                    4,
                    Guid.Parse("77777777-7777-4777-8777-777777777777"),
                    key,
                    Guid.NewGuid(),
                    $"message-{sequence}",
                    "en",
                    sourceMandate
                );
            })
            .ToArray();
    }

    private static OperationalMandateV1 Mandate() =>
        new(
            "1.0",
            Guid.NewGuid(),
            "sha256:" + new string('1', 64),
            Guid.Parse("11111111-1111-4111-8111-111111111111"),
            Guid.Parse("22222222-2222-4222-8222-222222222222"),
            Guid.Parse("33333333-3333-4333-8333-333333333333"),
            Guid.Parse("44444444-4444-4444-8444-444444444444"),
            "EMPLOYER",
            "ACTIVE",
            "LIVE",
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            1,
            "1.0.0",
            "3.1",
            "sha256:" + new string('2', 64),
            1,
            "sha256:" + new string('3', 64),
            "sha256:" + new string('4', 64),
            "1.0",
            "2.0",
            "1.0.0",
            "1.0.0",
            "sha256:" + new string('8', 64),
            "CUSTOMER_PROFILING",
            "1.0.0",
            "sha256:" + new string('5', 64),
            "sha256:" + new string('6', 64),
            "1.0.0",
            "sha256:" + new string('7', 64),
            1,
            1,
            1,
            1,
            "allowance-a",
            1,
            ["approval-a"],
            false,
            null,
            "Prepare the profile",
            ["PRESENT_PROFILE_PROPOSAL"],
            ["UNDECLARED_ACTION"],
            new DateTimeOffset(2027, 1, 1, 0, 0, 0, TimeSpan.Zero),
            Guid.Parse("55555555-5555-4555-8555-555555555555"),
            "decision-a",
            "evidence-a",
            null,
            null
        );

    private HttpConversationExecutionGateway CreateGateway(
        Func<HttpRequestMessage, HttpResponseMessage> response,
        TimeSpan? timeout = null
    )
    {
        var client = new HttpClient(new StubHandler(response))
        {
            BaseAddress = new Uri("https://professional-runtime/"),
            Timeout = timeout ?? TimeSpan.FromSeconds(10),
        };
        var factory = new Mock<IHttpClientFactory>();
        factory
            .Setup(value => value.CreateClient("ConversationProfessionalRuntime"))
            .Returns(client);
        return new HttpConversationExecutionGateway(factory.Object, _identity);
    }

    private static JsonDocument ReadEnvelope(HttpRequestMessage request)
    {
        var parts = request.Headers.Authorization!.Parameter!.Split('.');
        Assert.Equal(2, parts.Length);
        var encoded = parts[0].Replace('-', '+').Replace('_', '/');
        return JsonDocument.Parse(
            Convert.FromBase64String(encoded + new string('=', (4 - encoded.Length % 4) % 4))
        );
    }

    public void Dispose() => _identity.Dispose();

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> response)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(response(request));
    }
}
