// Implements: work-contracts/WC-034-goal005-webportal-founder-admin.md § WC034-08
// constitutional_basis: C-001, C-005, C-023, C-026, C-049, C-059, C-063, C-076

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

internal sealed class InMemoryConversationFactory(string databaseName)
    : IDbContextFactory<ConversationStoreDbContext>
{
    public ConversationStoreDbContext CreateDbContext() =>
        new(new DbContextOptionsBuilder<ConversationStoreDbContext>()
            .UseInMemoryDatabase(databaseName)
            .Options);
}

internal sealed class ConversationConstitutionalGatewayStub : IRelationshipConstitutionalGateway
{
    public int CallCount { get; private set; }
    public bool FailNext { get; set; }
    public Action? BeforeConfirm { get; set; }

    public Task<Guid> AuthorizeAndRecordAsync(
        Guid tenantId,
        Guid relationshipId,
        string professionalType,
        string actionType,
        Guid correlationId,
        object actionParameters,
        CancellationToken cancellationToken)
    {
        CallCount += 1;
        BeforeConfirm?.Invoke();
        if (FailNext)
        {
            FailNext = false;
            throw new InvalidOperationException("Constitutional evidence unavailable.");
        }

        return Task.FromResult(Guid.NewGuid());
    }
}

internal sealed class ConversationExecutionGatewayStub : IConversationExecutionGateway
{
    public int StartCount { get; private set; }
    public int CancelCount { get; private set; }
    public bool FailStart { get; set; }

    public Task StartAsync(
        Guid conversationId,
        Guid executionId,
        Guid messageId,
        Guid relationshipId,
        string locale,
        Guid idempotencyKey,
        CancellationToken cancellationToken)
    {
        StartCount += 1;
        if (FailStart)
        {
            throw new ConversationExecutionUnavailableException();
        }

        return Task.CompletedTask;
    }

    public Task CancelAsync(
        Guid conversationId,
        Guid executionId,
        Guid idempotencyKey,
        CancellationToken cancellationToken)
    {
        CancelCount += 1;
        return Task.CompletedTask;
    }
}

public sealed class ConversationServiceTests
{
    [Fact]
    public async Task Timeline_PaginatesInBothDirectionsAndReportsUnreadBoundary()
    {
        var context = await CreateContextAsync();
        var sent = new List<ConversationSubmissionV1>();
        foreach (var text in new[] { "first", "second", "third" })
        {
            var result = await context.Service.SendAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                Guid.NewGuid(),
                CreateRequest(text),
                CancellationToken.None);
            sent.Add(result.Value);
        }

        var latest = await context.Service.ListMessagesAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            null,
            null,
            2,
            CancellationToken.None);
        var older = await context.Service.ListMessagesAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            latest.NextCursor,
            null,
            2,
            CancellationToken.None);
        var newer = await context.Service.ListMessagesAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            null,
            sent[0].AuthoritativeCursor,
            10,
            CancellationToken.None);

        Assert.True(latest.HasMore);
        Assert.Equal([sent[1].Message.MessageId, sent[2].Message.MessageId], latest.Items.Select(item => item.MessageId));
        Assert.Equal(sent[0].Message.MessageId, latest.UnreadBoundaryMessageId);
        Assert.Single(older.Items);
        Assert.Equal(sent[0].Message.MessageId, older.Items[0].MessageId);
        Assert.Equal([sent[1].Message.MessageId, sent[2].Message.MessageId], newer.Items.Select(item => item.MessageId));
        Assert.False(newer.HasMore);
    }

    [Fact]
    public async Task Timeline_EmptyConversationAndInvalidQueriesHaveDeterministicBehavior()
    {
        var context = await CreateContextAsync();

        var empty = await context.Service.ListMessagesAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            null,
            null,
            50,
            CancellationToken.None);

        Assert.Empty(empty.Items);
        Assert.False(empty.HasMore);
        Assert.Null(empty.NextCursor);
        Assert.Null(empty.UnreadBoundaryMessageId);
        await Assert.ThrowsAsync<ConversationRequestException>(() => context.Service.ListMessagesAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            "cursor",
            "after",
            50,
            CancellationToken.None));
        await Assert.ThrowsAsync<ConversationRequestException>(() => context.Service.ListMessagesAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            null,
            null,
            101,
            CancellationToken.None));
    }

    [Fact]
    public async Task Send_ReplaysSameKeyAndHashWithoutDuplicateMutationOrDispatch()
    {
        var context = await CreateContextAsync();
        var key = Guid.NewGuid();
        var request = CreateRequest("same contribution");

        var first = await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            request,
            CancellationToken.None);
        var replay = await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            request,
            CancellationToken.None);

        Assert.False(first.Replayed);
        Assert.True(replay.Replayed);
        Assert.Equal(first.Value.Message.MessageId, replay.Value.Message.MessageId);
        Assert.Equal("REPLAYED", replay.Value.Outcome);
        Assert.Equal(1, context.ConstitutionalGateway.CallCount);
        Assert.Equal(1, context.ExecutionGateway.StartCount);
        await using var db = context.ConversationFactory.CreateDbContext();
        Assert.Equal(1, await db.Messages.CountAsync());
        Assert.Equal(1, await db.Executions.CountAsync());
        Assert.Equal(1, await db.IdempotencyOutcomes.CountAsync());
    }

    [Fact]
    public async Task Send_DivergentReuseReturnsConflictWithZeroAdditionalMutation()
    {
        var context = await CreateContextAsync();
        var key = Guid.NewGuid();
        var original = CreateRequest("original contribution");
        await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            original,
            CancellationToken.None);
        var changed = original with
        {
            Content = [new ConversationTextBlockV1("1.0", "TEXT", "changed contribution", "en")],
        };

        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            context.Service.SendAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                key,
                changed,
                CancellationToken.None));

        Assert.Equal(1, context.ConstitutionalGateway.CallCount);
        Assert.Equal(1, context.ExecutionGateway.StartCount);
        await using var db = context.ConversationFactory.CreateDbContext();
        Assert.Equal(1, await db.Messages.CountAsync());
        Assert.Equal(1, await db.IdempotencyOutcomes.CountAsync());
    }

    [Fact]
    public async Task FailedDispatchCanBeRetriedAndCompletedMessagesReplayWithoutRedispatch()
    {
        var context = await CreateContextAsync();
        var key = Guid.NewGuid();
        context.ExecutionGateway.FailStart = true;

        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() => context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            CreateRequest("retry me"),
            CancellationToken.None));
        await using var failedDb = context.ConversationFactory.CreateDbContext();
        var failedMessage = await failedDb.Messages.SingleAsync();
        Assert.Equal("FAILED", failedMessage.ProcessingState);
        Assert.Equal("UNRESOLVED", failedMessage.DeliveryState);

        context.ExecutionGateway.FailStart = false;
        var retried = await context.Service.RetryAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            failedMessage.MessageId,
            key,
            CancellationToken.None);

        Assert.False(retried.Replayed);
        Assert.Equal("ACCEPTED", retried.Value.Outcome);
        Assert.Equal(2, context.ExecutionGateway.StartCount);
        await using var completedDb = context.ConversationFactory.CreateDbContext();
        var completedMessage = await completedDb.Messages.SingleAsync();
        var completedExecution = await completedDb.Executions.SingleAsync();
        completedMessage.ProcessingState = "COMPLETED";
        completedExecution.ProcessingState = "COMPLETED";
        await completedDb.SaveChangesAsync();

        var replay = await context.Service.RetryAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            failedMessage.MessageId,
            key,
            CancellationToken.None);

        Assert.True(replay.Replayed);
        Assert.Equal("REPLAYED", replay.Value.Outcome);
        Assert.Equal(2, context.ExecutionGateway.StartCount);
    }

    [Fact]
    public async Task RetryRejectsUnknownOrNonFailedMessagesWithoutEvidenceOrRedispatch()
    {
        var context = await CreateContextAsync();
        var key = Guid.NewGuid();
        var sent = await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            CreateRequest("still processing"),
            CancellationToken.None);

        await Assert.ThrowsAsync<ConversationRetryNotAllowedException>(() => context.Service.RetryAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            key,
            CancellationToken.None));
        await Assert.ThrowsAsync<ConversationRetryNotAllowedException>(() => context.Service.RetryAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            sent.Value.Message.MessageId,
            key,
            CancellationToken.None));

        Assert.Equal(1, context.ConstitutionalGateway.CallCount);
        Assert.Equal(1, context.ExecutionGateway.StartCount);
    }

    [Fact]
    public async Task Timeline_OtherTenantCannotInferRelationshipOrReadMessages()
    {
        var context = await CreateContextAsync();
        await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            CreateRequest("tenant private"),
            CancellationToken.None);

        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            context.Service.ListMessagesAsync(
                Guid.NewGuid(),
                context.ParticipantId,
                context.RelationshipId,
                null,
                null,
                50,
                CancellationToken.None));
    }

    [Fact]
    public async Task Controller_NotAccessibleProblemIsPrivacySafeRfc9457()
    {
        var context = await CreateContextAsync();
        var hiddenRelationshipId = Guid.NewGuid();
        var controller = CreateController(context, context.TenantId, context.ParticipantId);

        var result = await controller.ListMessagesAsync(
            hiddenRelationshipId,
            null,
            null,
            50,
            CancellationToken.None);

        var problemResult = Assert.IsType<ObjectResult>(result);
        Assert.Equal(StatusCodes.Status404NotFound, problemResult.StatusCode);
        var problem = Assert.IsType<ConversationProblemDetail>(problemResult.Value);
        Assert.Equal("CONVERSATION_NOT_ACCESSIBLE", problem.Code);
        Assert.Equal(StatusCodes.Status404NotFound, problem.Status);
        Assert.NotEqual(Guid.Empty, problem.CorrelationId);
        var json = JsonSerializer.Serialize(problem);
        Assert.DoesNotContain(hiddenRelationshipId.ToString(), json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(context.TenantId.ToString(), json, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("professional", json, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task Controller_SendRetryReadAndCancelExposeAcceptedThenReplaySemantics()
    {
        var context = await CreateContextAsync();
        var controller = CreateController(context, context.TenantId, context.ParticipantId);
        var sendKey = Guid.NewGuid();
        controller.Request.Headers["Idempotency-Key"] = sendKey.ToString("D");
        var request = CreateRequest("controller contribution");

        var accepted = Assert.IsType<AcceptedResult>(await controller.SendMessageAsync(
            context.RelationshipId,
            request,
            CancellationToken.None));
        var submission = Assert.IsType<ConversationSubmissionV1>(accepted.Value);
        var replay = Assert.IsType<OkObjectResult>(await controller.SendMessageAsync(
            context.RelationshipId,
            request,
            CancellationToken.None));
        Assert.True(Assert.IsType<ConversationSubmissionV1>(replay.Value).Replayed);

        await using (var failedDb = context.ConversationFactory.CreateDbContext())
        {
            var message = await failedDb.Messages.SingleAsync();
            var execution = await failedDb.Executions.SingleAsync();
            message.DeliveryState = "FAILED";
            message.ProcessingState = "FAILED";
            execution.ProcessingState = "FAILED";
            await failedDb.SaveChangesAsync();
        }

        var retryAccepted = Assert.IsType<AcceptedResult>(await controller.RetryMessageAsync(
            context.RelationshipId,
            submission.Message.MessageId,
            CancellationToken.None));
        Assert.Equal("ACCEPTED", Assert.IsType<ConversationSubmissionV1>(retryAccepted.Value).Outcome);

        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        var read = Assert.IsType<OkObjectResult>(await controller.UpdateReadPositionAsync(
            context.RelationshipId,
            new UpdateConversationReadPositionRequestV1(
                "1.0",
                submission.Message.MessageId,
                submission.AuthoritativeCursor),
            CancellationToken.None));
        Assert.Equal(submission.Message.MessageId, Assert.IsType<ConversationReadPositionV1>(read.Value).LastReadMessageId);

        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        var cancelled = Assert.IsType<AcceptedResult>(await controller.CancelExecutionAsync(
            context.RelationshipId,
            Assert.IsType<Guid>(submission.ExecutionId),
            CancellationToken.None));
        Assert.Equal("CANCELLED", Assert.IsType<ConversationExecutionStatusV1>(cancelled.Value).State);
        var cancelReplay = Assert.IsType<OkObjectResult>(await controller.CancelExecutionAsync(
            context.RelationshipId,
            Assert.IsType<Guid>(submission.ExecutionId),
            CancellationToken.None));
        Assert.Equal("CANCELLED", Assert.IsType<ConversationExecutionStatusV1>(cancelReplay.Value).State);
    }

    [Fact]
    public async Task Controller_RequiresAuthorityAndUuidIdempotencyForCommands()
    {
        var context = await CreateContextAsync();
        var unauthorized = CreateController(context, null, null);
        var request = CreateRequest("not authorized");

        foreach (var result in new IActionResult[]
        {
            await unauthorized.ListMessagesAsync(context.RelationshipId, null, null, 50, CancellationToken.None),
            await unauthorized.SendMessageAsync(context.RelationshipId, request, CancellationToken.None),
            await unauthorized.RetryMessageAsync(context.RelationshipId, Guid.NewGuid(), CancellationToken.None),
            await unauthorized.UpdateReadPositionAsync(
                context.RelationshipId,
                new UpdateConversationReadPositionRequestV1("1.0", Guid.NewGuid(), "cursor"),
                CancellationToken.None),
            await unauthorized.CancelExecutionAsync(
                context.RelationshipId,
                Guid.NewGuid(),
                CancellationToken.None),
        })
        {
            var problem = Assert.IsType<ConversationProblemDetail>(Assert.IsType<ObjectResult>(result).Value);
            Assert.Equal("CONVERSATION_SESSION_REQUIRED", problem.Code);
        }

        var authorized = CreateController(context, context.TenantId, context.ParticipantId);
        foreach (var result in new IActionResult[]
        {
            await authorized.SendMessageAsync(context.RelationshipId, request, CancellationToken.None),
            await authorized.RetryMessageAsync(context.RelationshipId, Guid.NewGuid(), CancellationToken.None),
            await authorized.UpdateReadPositionAsync(
                context.RelationshipId,
                new UpdateConversationReadPositionRequestV1("1.0", Guid.NewGuid(), "cursor"),
                CancellationToken.None),
            await authorized.CancelExecutionAsync(context.RelationshipId, Guid.NewGuid(), CancellationToken.None),
        })
        {
            var problem = Assert.IsType<ConversationProblemDetail>(Assert.IsType<ObjectResult>(result).Value);
            Assert.Equal("CONVERSATION_REQUEST_INVALID", problem.Code);
        }
    }

    [Fact]
    public async Task Controller_MapsValidationConflictRetryStoppedAndUnavailableErrorsWithoutDetails()
    {
        var context = await CreateContextAsync();
        var controller = CreateController(context, context.TenantId, context.ParticipantId);
        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");

        var invalid = await controller.SendMessageAsync(
            context.RelationshipId,
            CreateRequest("invalid") with { SchemaVersion = "2.0" },
            CancellationToken.None);
        AssertProblem(invalid, StatusCodes.Status400BadRequest, "CONVERSATION_REQUEST_INVALID");

        var retry = await controller.RetryMessageAsync(
            context.RelationshipId,
            Guid.NewGuid(),
            CancellationToken.None);
        AssertProblem(retry, StatusCodes.Status422UnprocessableEntity, "CONVERSATION_RETRY_NOT_ALLOWED");

        context.ExecutionGateway.FailStart = true;
        var unavailable = await controller.SendMessageAsync(
            context.RelationshipId,
            CreateRequest("gateway unavailable"),
            CancellationToken.None);
        AssertProblem(unavailable, StatusCodes.Status503ServiceUnavailable, "CONVERSATION_EXECUTION_UNAVAILABLE");
        Assert.Equal("30", controller.Response.Headers.RetryAfter);

        await using var relationshipDb = context.RelationshipFactory.CreateDbContext();
        var relationship = await relationshipDb.EmploymentRelationships.SingleAsync();
        relationship.State = EmploymentRelationshipState.StoppedEmergency;
        await relationshipDb.SaveChangesAsync();
        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        var stopped = await controller.CancelExecutionAsync(
            context.RelationshipId,
            Guid.NewGuid(),
            CancellationToken.None);
        AssertProblem(stopped, StatusCodes.Status423Locked, "CONVERSATION_STOPPED");
    }

    [Fact]
    public async Task Controller_MapsCursorIdempotencyReadStateAndGovernanceFailures()
    {
        var context = await CreateContextAsync();
        var controller = CreateController(context, context.TenantId, context.ParticipantId);
        var key = Guid.NewGuid();
        controller.Request.Headers["Idempotency-Key"] = key.ToString("D");
        var request = CreateRequest("original");
        var accepted = Assert.IsType<AcceptedResult>(await controller.SendMessageAsync(
            context.RelationshipId,
            request,
            CancellationToken.None));
        var submission = Assert.IsType<ConversationSubmissionV1>(accepted.Value);

        var divergent = await controller.SendMessageAsync(
            context.RelationshipId,
            request with { Content = [new ConversationTextBlockV1("1.0", "TEXT", "different", "en")] },
            CancellationToken.None);
        AssertProblem(divergent, StatusCodes.Status409Conflict, "CONVERSATION_IDEMPOTENCY_CONFLICT");

        var expired = await controller.ListMessagesAsync(
            context.RelationshipId,
            "not-a-signed-cursor",
            null,
            50,
            CancellationToken.None);
        AssertProblem(expired, StatusCodes.Status410Gone, "CONVERSATION_CURSOR_EXPIRED");

        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        var staleRead = await controller.UpdateReadPositionAsync(
            context.RelationshipId,
            new UpdateConversationReadPositionRequestV1(
                "1.0",
                submission.Message.MessageId,
                new ConversationCursorCodec(Options.Create(new ConversationCursorOptions
                {
                    HmacKey = "wc034-test-cursor-key-at-least-32-characters",
                })).Encode(context.TenantId, context.RelationshipId, "timeline", 0)),
            CancellationToken.None);
        AssertProblem(staleRead, StatusCodes.Status409Conflict, "CONVERSATION_STATE_CONFLICT");

        context.ConstitutionalGateway.FailNext = true;
        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString("D");
        var governanceUnavailable = await controller.SendMessageAsync(
            context.RelationshipId,
            CreateRequest("no evidence, no mutation"),
            CancellationToken.None);
        AssertProblem(
            governanceUnavailable,
            StatusCodes.Status503ServiceUnavailable,
            "CONSTITUTIONAL_ENGINE_UNAVAILABLE");
        Assert.Equal("30", controller.Response.Headers.RetryAfter);
    }

    [Fact]
    public async Task Stream_RejectsMissingAuthorityAndMapsReplayFailureBeforeStartingSse()
    {
        var context = await CreateContextAsync();
        var unauthorized = CreateController(context, null, null);

        await unauthorized.StreamAsync(context.RelationshipId, null, CancellationToken.None);
        Assert.Equal(StatusCodes.Status401Unauthorized, unauthorized.Response.StatusCode);

        var hidden = CreateController(context, context.TenantId, context.ParticipantId);
        await hidden.StreamAsync(Guid.NewGuid(), null, CancellationToken.None);
        Assert.Equal(StatusCodes.Status404NotFound, hidden.Response.StatusCode);
        Assert.NotEqual("text/event-stream", hidden.Response.ContentType);
    }

    [Fact]
    public async Task EventReplay_ContinuesAfterLastEventAndRejectsTampering()
    {
        var context = await CreateContextAsync();
        await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            CreateRequest("first"),
            CancellationToken.None);
        await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            CreateRequest("second"),
            CancellationToken.None);

        var all = await context.Service.GetEventReplayAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            null,
            CancellationToken.None);
        var resumed = await context.Service.GetEventReplayAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            all[0].EventId,
            CancellationToken.None);

        Assert.Equal(2, all.Count);
        Assert.Single(resumed);
        Assert.Equal(all[1].EventId, resumed[0].EventId);
        Assert.True(all[1].Sequence > all[0].Sequence);
        var cursorParts = all[0].EventId.Split('.');
        cursorParts[1] = (cursorParts[1][0] == 'A' ? "B" : "A") + cursorParts[1][1..];
        var tampered = string.Join('.', cursorParts);
        await Assert.ThrowsAsync<ConversationCursorExpiredException>(() =>
            context.Service.GetEventReplayAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                tampered,
                CancellationToken.None));
    }

    [Fact]
    public async Task Stream_EmitsTypedHeartbeatWithoutAdvancingDurableCursorOrExposingProtectedData()
    {
        var context = await CreateContextAsync();
        await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            CreateRequest("protected customer content"),
            CancellationToken.None);
        var durableEvents = await context.Service.GetEventReplayAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            null,
            CancellationToken.None);
        var durableEvent = Assert.Single(durableEvents);
        var controller = CreateController(context, context.TenantId, context.ParticipantId);
        await using var responseBody = new MemoryStream();
        controller.Response.Body = responseBody;
        using var streamCancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            controller.StreamAsync(context.RelationshipId, null, streamCancellation.Token));

        responseBody.Position = 0;
        using var reader = new StreamReader(responseBody);
        var frames = (await reader.ReadToEndAsync()).Split("\n\n", StringSplitOptions.RemoveEmptyEntries);
        var heartbeatFrame = Assert.Single(frames, frame => frame.StartsWith("event: heartbeat\n", StringComparison.Ordinal));
        Assert.DoesNotContain("id: ", heartbeatFrame, StringComparison.Ordinal);
        var dataLine = Assert.Single(
            heartbeatFrame.Split('\n'),
            line => line.StartsWith("data: ", StringComparison.Ordinal));
        using var heartbeatDocument = JsonDocument.Parse(dataLine[6..]);
        var heartbeat = heartbeatDocument.RootElement;
        Assert.Equal("1.0", heartbeat.GetProperty("schemaVersion").GetString());
        Assert.Equal(durableEvent.EventId, heartbeat.GetProperty("eventId").GetString());
        Assert.Equal("heartbeat", heartbeat.GetProperty("eventType").GetString());
        Assert.Equal(context.RelationshipId, heartbeat.GetProperty("relationshipId").GetGuid());
        Assert.Equal(durableEvent.Sequence, heartbeat.GetProperty("sequence").GetInt64());
        Assert.True(heartbeat.GetProperty("occurredAt").TryGetDateTimeOffset(out _));
        var payload = heartbeat.GetProperty("data");
        Assert.Equal(["serverTime"], payload.EnumerateObject().Select(property => property.Name));
        Assert.True(payload.GetProperty("serverTime").TryGetDateTimeOffset(out _));
        Assert.DoesNotContain(context.TenantId.ToString(), heartbeatFrame, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain(context.ParticipantId.ToString(), heartbeatFrame, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("protected customer content", heartbeatFrame, StringComparison.Ordinal);

        var resumed = await context.Service.GetEventReplayAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            durableEvent.EventId,
            CancellationToken.None);
        Assert.Empty(resumed);
        await using var verifyDb = context.ConversationFactory.CreateDbContext();
        Assert.Single(await verifyDb.Events.ToListAsync());
    }

    [Fact]
    public async Task Cancel_RecordsEvidenceBeforeDurableCancelledPartialState()
    {
        var context = await CreateContextAsync();
        var sent = await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            CreateRequest("cancel me"),
            CancellationToken.None);
        var executionId = Assert.IsType<Guid>(sent.Value.ExecutionId);
        var evidenceObservedBeforeMutation = false;
        context.ConstitutionalGateway.BeforeConfirm = () =>
        {
            using var db = context.ConversationFactory.CreateDbContext();
            var execution = db.Executions.Single(value => value.ExecutionId == executionId);
            evidenceObservedBeforeMutation = execution.ProcessingState == "QUEUED";
        };

        var cancelled = await context.Service.CancelAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            executionId,
            Guid.NewGuid(),
            CancellationToken.None);

        Assert.True(evidenceObservedBeforeMutation);
        Assert.Equal("CANCELLED", cancelled.Value.State);
        Assert.True(cancelled.Value.Partial);
        Assert.Equal("CANCELLED", cancelled.Value.CompletionReason);
        Assert.Equal(1, context.ExecutionGateway.CancelCount);
        await using var verifyDb = context.ConversationFactory.CreateDbContext();
        var message = await verifyDb.Messages.SingleAsync();
        Assert.Equal("CANCELLED", message.ProcessingState);
        Assert.True(message.Partial);
        Assert.Equal(2, await verifyDb.Events.CountAsync());
    }

    [Fact]
    public async Task EvidenceFailurePreventsMessageExecutionAndIdempotencyMutation()
    {
        var context = await CreateContextAsync();
        var evidenceObservedBeforeMutation = false;
        context.ConstitutionalGateway.BeforeConfirm = () =>
        {
            using var db = context.ConversationFactory.CreateDbContext();
            evidenceObservedBeforeMutation = !db.Messages.Any()
                && !db.Executions.Any()
                && !db.IdempotencyOutcomes.Any();
        };
        context.ConstitutionalGateway.FailNext = true;

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            context.Service.SendAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                Guid.NewGuid(),
                CreateRequest("must not persist"),
                CancellationToken.None));

        Assert.True(evidenceObservedBeforeMutation);
        Assert.Equal(0, context.ExecutionGateway.StartCount);
        await using var verifyDb = context.ConversationFactory.CreateDbContext();
        Assert.Empty(await verifyDb.Messages.ToListAsync());
        Assert.Empty(await verifyDb.Executions.ToListAsync());
        Assert.Empty(await verifyDb.IdempotencyOutcomes.ToListAsync());
    }

    [Fact]
    public async Task ReadPosition_IsMonotonicAndIdempotent()
    {
        var context = await CreateContextAsync();
        var first = await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            CreateRequest("first"),
            CancellationToken.None);
        var second = await context.Service.SendAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            Guid.NewGuid(),
            CreateRequest("second"),
            CancellationToken.None);
        var key = Guid.NewGuid();
        var request = new UpdateConversationReadPositionRequestV1(
            "1.0",
            second.Value.Message.MessageId,
            second.Value.AuthoritativeCursor);

        var updated = await context.Service.UpdateReadPositionAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            request,
            CancellationToken.None);
        var replay = await context.Service.UpdateReadPositionAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            request,
            CancellationToken.None);

        Assert.False(updated.Replayed);
        Assert.True(replay.Replayed);
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            context.Service.UpdateReadPositionAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                Guid.NewGuid(),
                new UpdateConversationReadPositionRequestV1(
                    "1.0",
                    first.Value.Message.MessageId,
                    second.Value.AuthoritativeCursor),
                CancellationToken.None));
    }

    private static SendConversationMessageRequestV1 CreateRequest(string text) =>
        new(
            "1.0",
            Guid.NewGuid(),
            [new ConversationTextBlockV1("1.0", "TEXT", text, "en")],
            "en-IN");

    private static void AssertProblem(IActionResult result, int status, string code)
    {
        var objectResult = Assert.IsType<ObjectResult>(result);
        Assert.Equal(status, objectResult.StatusCode);
        var problem = Assert.IsType<ConversationProblemDetail>(objectResult.Value);
        Assert.Equal(code, problem.Code);
        Assert.Equal(status, problem.Status);
    }

    private static ConversationController CreateController(
        ConversationTestContext context,
        Guid? tenantId,
        Guid? participantId)
    {
        var httpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(
                participantId.HasValue
                    ? [new Claim("participant_id", participantId.Value.ToString("D"))]
                    : [],
                "Test")),
        };
        if (tenantId.HasValue)
        {
            httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.Value.ToString("D");
        }

        return new ConversationController(context.Service)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
    }

    private static async Task<ConversationTestContext> CreateContextAsync()
    {
        var databaseSuffix = Guid.NewGuid().ToString("N");
        var relationshipFactory = new InMemoryEmploymentRelationshipFactory($"relationship-{databaseSuffix}");
        var conversationFactory = new InMemoryConversationFactory($"conversation-{databaseSuffix}");
        var constitutionalGateway = new ConversationConstitutionalGatewayStub();
        var executionGateway = new ConversationExecutionGatewayStub();
        var cursorCodec = new ConversationCursorCodec(Options.Create(new ConversationCursorOptions
        {
            HmacKey = "wc034-test-cursor-key-at-least-32-characters",
        }));
        var service = new ConversationService(
            conversationFactory,
            relationshipFactory,
            constitutionalGateway,
            executionGateway,
            cursorCodec);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        await using var relationshipDb = relationshipFactory.CreateDbContext();
        relationshipDb.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = participantId,
        });
        relationshipDb.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Evaluator,
            BoundEvidenceId = Guid.NewGuid(),
        });
        await relationshipDb.SaveChangesAsync();
        return new ConversationTestContext(
            service,
            relationshipFactory,
            conversationFactory,
            constitutionalGateway,
            executionGateway,
            tenantId,
            participantId,
            relationshipId);
    }

    private sealed record ConversationTestContext(
        ConversationService Service,
        InMemoryEmploymentRelationshipFactory RelationshipFactory,
        InMemoryConversationFactory ConversationFactory,
        ConversationConstitutionalGatewayStub ConstitutionalGateway,
        ConversationExecutionGatewayStub ExecutionGateway,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId);
}