// Implements: WC-134 R006/R007 atomic runtime reply projection.
// constitutional_basis: C-001, C-005, C-023, C-059, C-063
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Microsoft.Extensions.Logging.Abstractions;
using System.Runtime.CompilerServices;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class ConversationRuntimeEventIngestionTests
{
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    [Theory]
    [InlineData("card-type")]
    [InlineData("missing-proposal")]
    [InlineData("proposal-type")]
    [InlineData("missing-state")]
    [InlineData("state-type")]
    [InlineData("state")]
    [InlineData("missing-id")]
    [InlineData("id-type")]
    [InlineData("id-format")]
    [InlineData("id-mismatch")]
    [InlineData("missing-relationship")]
    [InlineData("relationship-type")]
    [InlineData("relationship-mismatch")]
    [InlineData("missing-contribution")]
    [InlineData("contribution-type")]
    [InlineData("contribution-mismatch")]
    [InlineData("missing-operations")]
    [InlineData("operations-type")]
    [InlineData("operations-empty")]
    [InlineData("operations-too-many")]
    public async Task ProposalCardsRejectUnboundOrInvalidAuthority(string change)
    {
        var context = await CreateAsync();
        var card = Proposal(context.Source);
        var data = card["data"]!.AsObject();
        var proposal = data["employmentPatchProposal"]!.AsObject();
        switch (change)
        {
            case "card-type": card["cardType"] = "ACTION"; break;
            case "missing-proposal": data.Remove("employmentPatchProposal"); break;
            case "proposal-type": data["employmentPatchProposal"] = "invalid"; break;
            case "missing-state": proposal.Remove("state"); break;
            case "state-type": proposal["state"] = 1; break;
            case "state": proposal["state"] = "APPLIED"; break;
            case "missing-id": proposal.Remove("proposalId"); break;
            case "id-type": proposal["proposalId"] = 1; break;
            case "id-format": proposal["proposalId"] = "invalid"; break;
            case "id-mismatch": proposal["proposalId"] = Guid.NewGuid().ToString("D"); break;
            case "missing-relationship": proposal.Remove("relationshipRef"); break;
            case "relationship-type": proposal["relationshipRef"] = 1; break;
            case "relationship-mismatch": proposal["relationshipRef"] = Guid.NewGuid().ToString("D"); break;
            case "missing-contribution": proposal.Remove("contributionRef"); break;
            case "contribution-type": proposal["contributionRef"] = 1; break;
            case "contribution-mismatch": proposal["contributionRef"] = Guid.NewGuid().ToString("D"); break;
            case "missing-operations": proposal.Remove("operations"); break;
            case "operations-type": proposal["operations"] = "invalid"; break;
            case "operations-empty": proposal["operations"] = new JsonArray(); break;
            case "operations-too-many":
                proposal["operations"] = new JsonArray(Enumerable.Range(0, 101).Select(_ => (JsonNode?)new JsonObject()).ToArray());
                break;
            default: throw new InvalidOperationException(change);
        }
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "card.proposed", card), CancellationToken.None));
        await using var db = context.Conversations.CreateDbContext();
        Assert.Empty(await db.RuntimeEventReceipts.ToListAsync());
        Assert.Equal(0, (await db.Executions.SingleAsync()).RuntimeSequence);
    }

    [Fact]
    public async Task BoundProposalRemainsAReviewOnlyDecision()
    {
        var context = await CreateAsync();
        var card = Proposal(context.Source);
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "card.proposed", card), CancellationToken.None);
        await using var db = context.Conversations.CreateDbContext();
        var reply = await db.Messages.SingleAsync(value => value.Actor == "PROFESSIONAL");
        using var cards = JsonDocument.Parse(reply.CardsJson);
        var projected = Assert.Single(cards.RootElement.EnumerateArray());
        Assert.Equal("PROPOSED", projected.GetProperty("decisionState").GetString());
        Assert.Empty(projected.GetProperty("commands").EnumerateArray());
        Assert.Contains("until the customer confirms", projected.GetProperty("authorityImpact").GetString());
        Assert.Single(await db.RuntimeEventReceipts.ToListAsync());
    }

    private static JsonObject Proposal(ConversationRuntimeSource source)
    {
        var proposalId = Guid.NewGuid();
        return new JsonObject
        {
            ["schemaVersion"] = "1.0",
            ["cardType"] = "DECISION",
            ["cardId"] = proposalId.ToString("D"),
            ["owner"] = "CUSTOMER",
            ["state"] = "PROPOSED",
            ["effect"] = "Review this proposal.",
            ["data"] = new JsonObject
            {
                ["employmentPatchProposal"] = new JsonObject
                {
                    ["state"] = "PROPOSED",
                    ["proposalId"] = proposalId.ToString("D"),
                    ["relationshipRef"] = source.RelationshipId.ToString("D"),
                    ["contributionRef"] = source.MessageId.ToString("D"),
                    ["operations"] = new JsonArray(new JsonObject()),
                },
            },
        };
    }

    [Fact]
    public async Task ReplayAndRestartPreserveInputAndAccumulateOnlyOneReply()
    {
        var context = await CreateAsync();
        var accepted = Event(context.Source, 1, "execution.accepted", new { serverTime = DateTimeOffset.UtcNow });
        await context.Ingestion.ApplyAsync(context.Source, accepted, CancellationToken.None);
        await context.Ingestion.ApplyAsync(context.Source, accepted, CancellationToken.None);
        var resumed = await context.Ingestion.GetSourceAsync(context.Source.TenantId, context.Source.ExecutionId, CancellationToken.None);
        Assert.Equal(1, resumed.AfterSequence);
        await context.Ingestion.ApplyAsync(resumed, Event(resumed, 2, "response.delta",
            new { contentIndex = 0, appendText = "पहला ", partial = true }), CancellationToken.None);
        resumed = await context.Ingestion.GetSourceAsync(resumed.TenantId, resumed.ExecutionId, CancellationToken.None);
        await context.Ingestion.ApplyAsync(resumed, Event(resumed, 3, "response.delta",
            new { contentIndex = 0, appendText = "उत्तर", partial = true }), CancellationToken.None);
        await context.Ingestion.ApplyAsync(resumed, Event(resumed, 4, "execution.completed",
            new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" }), CancellationToken.None);
        await using var db = context.Conversations.CreateDbContext();
        var input = await db.Messages.SingleAsync(row => row.MessageId == context.Source.MessageId);
        var reply = await db.Messages.SingleAsync(row => row.Actor == "PROFESSIONAL");
        Assert.Equal(context.InputJson, input.ContentJson);
        var block = Assert.Single(JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(reply.ContentJson, Json)!);
        Assert.Equal("पहला उत्तर", block.Text);
        Assert.Equal("hi-IN", block.Language);
        Assert.Equal("COMPLETED", reply.ProcessingState);
        Assert.Equal("PENDING", reply.EvidenceState);
        Assert.True((await db.Executions.SingleAsync()).RuntimeTerminal);
        Assert.Equal(4, await db.RuntimeEventReceipts.CountAsync());
        Assert.Equal(4, await db.Events.CountAsync());
        using var delta = JsonDocument.Parse((await db.Events.SingleAsync(row => row.Sequence == 2)).DataJson);
        Assert.Equal("पहला ", delta.RootElement.GetProperty("appendText").GetString());
        Assert.Equal(0, delta.RootElement.GetProperty("contentIndex").GetInt32());
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
    }

    [Fact]
    public async Task DivergentReplayAndSequenceGapNeverAdvanceCheckpoint()
    {
        var context = await CreateAsync();
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.delta",
            new { contentIndex = 0, appendText = "one", partial = true }), CancellationToken.None);
        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.delta",
                new { contentIndex = 0, appendText = "other", partial = true }), CancellationToken.None));
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 3, "response.delta",
                new { contentIndex = 0, appendText = "gap", partial = true }), CancellationToken.None));
        await using var db = context.Conversations.CreateDbContext();
        Assert.Equal(1, (await db.Executions.SingleAsync()).RuntimeSequence);
        Assert.Single(await db.RuntimeEventReceipts.ToListAsync());
        Assert.Single(await db.Events.ToListAsync());
    }

    [Fact]
    public async Task ConstructedSourceCannotMixAnOriginalExecutionWithAnotherRelationship()
    {
        var context = await CreateAsync();
        var forged = context.Source with { RelationshipId = Guid.NewGuid() };
        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            context.Ingestion.ApplyAsync(forged, Event(context.Source, 1, "execution.accepted",
                new { serverTime = DateTimeOffset.UtcNow }), CancellationToken.None));
        await using var db = context.Conversations.CreateDbContext();
        Assert.Empty(await db.RuntimeEventReceipts.ToListAsync());
        Assert.Equal(0, (await db.Executions.SingleAsync()).RuntimeSequence);
    }

    [Fact]
    public async Task ExpiredMandateRejectsNewResponseWithoutClaimingCompletion()
    {
        var context = await CreateAsync(expired: true);
        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.delta",
                new { contentIndex = 0, appendText = "late", partial = true }), CancellationToken.None));
        await using var db = context.Conversations.CreateDbContext();
        Assert.Single(await db.Messages.ToListAsync());
        Assert.Empty(await db.RuntimeEventReceipts.ToListAsync());
    }

    [Fact]
    public async Task MandateExpiringAfterDeltaFencesTerminalAndOutboxWithoutAdvancingCursor()
    {
        var clock = new AdvancingTimeProvider();
        var context = await CreateAsync(whatsApp: true, timeProvider: clock);
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.delta",
            new { contentIndex = 0, appendText = "Professional response", partial = true }), CancellationToken.None);
        clock.Advance(TimeSpan.FromMinutes(11));
        await Assert.ThrowsAsync<ConversationNotAccessibleException>(() =>
            context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 2, "execution.completed",
                new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" }), CancellationToken.None));
        await using var db = context.Conversations.CreateDbContext();
        var execution = await db.Executions.SingleAsync();
        Assert.Equal(1, execution.RuntimeSequence);
        Assert.False(execution.RuntimeTerminal);
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
        Assert.Equal("RUNNING", (await db.Messages.SingleAsync(row => row.Actor == "PROFESSIONAL")).ProcessingState);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task EmptyOrSystemOutputCannotBecomeProfessionalSuccess(bool systemOutput)
    {
        var context = await CreateAsync();
        if (systemOutput)
            await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.system",
                new { text = "Model unavailable.", code = "MODEL_UNAVAILABLE" }), CancellationToken.None);
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            context.Ingestion.ApplyAsync(context.Source, Event(context.Source, systemOutput ? 2 : 1, "execution.completed",
                new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" }), CancellationToken.None));
        await using var db = context.Conversations.CreateDbContext();
        Assert.False((await db.Executions.SingleAsync()).RuntimeTerminal);
        Assert.Equal(systemOutput ? 1 : 0, await db.RuntimeEventReceipts.CountAsync());
    }

    [Fact]
    public async Task KnownSystemLimitationIsNotProfessionalSuccess()
    {
        var context = await CreateAsync();
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.system",
            new { text = "Interpretation is unavailable. No professional work was completed.", code = "MODEL_UNAVAILABLE" }),
            CancellationToken.None);
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 2, "execution.failed",
            new { state = "FAILED", partial = false, completionReason = "PARTIAL_FAILURE", errorCode = "MODEL_UNAVAILABLE" }),
            CancellationToken.None);
        await using var db = context.Conversations.CreateDbContext();
        var reply = await db.Messages.SingleAsync(row => row.Actor == "SYSTEM");
        Assert.Equal("FAILED", reply.ProcessingState);
        Assert.Equal("PARTIAL_FAILURE", reply.CompletionReason);
        Assert.DoesNotContain(await db.Messages.ToListAsync(), row => row.Actor == "PROFESSIONAL");
        Assert.Equal(2, (await db.Executions.SingleAsync()).RuntimeSequence);
        var accepted = await db.Events.SingleAsync(row => row.Sequence == 1);
        Assert.Equal("message.accepted", accepted.EventType);
        using var acceptedData = JsonDocument.Parse(accepted.DataJson);
        Assert.Equal(new[] { "message" }, acceptedData.RootElement.EnumerateObject().Select(property => property.Name));
        using var failureData = JsonDocument.Parse((await db.Events.SingleAsync(row => row.Sequence == 2)).DataJson);
        Assert.Equal("MODEL_UNAVAILABLE", failureData.RootElement.GetProperty("code").GetString());
    }

    [Fact]
    public async Task ReplacedBindingCannotReceiveDelayedReplyButWebCompletionIsRetained()
    {
        var context = await CreateAsync(whatsApp: true);
        await using (var authority = context.Relationships.CreateDbContext())
        {
            (await authority.ChannelBindings.SingleAsync()).ExternalSubjectHash = new string('b', 64);
            await authority.SaveChangesAsync();
        }
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.system",
            new { text = "No work completed.", code = "MODEL_UNAVAILABLE" }), CancellationToken.None);
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 2, "execution.failed",
            new { state = "FAILED", partial = false, completionReason = "PARTIAL_FAILURE" }), CancellationToken.None);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Empty(await db.ConversationOutbox.ToListAsync());
        Assert.Equal("UNRESOLVED", (await db.Messages.SingleAsync(row => row.Actor == "SYSTEM")).DeliveryState);
        Assert.True((await db.Executions.SingleAsync()).RuntimeTerminal);
        Assert.Contains(await db.OperationalSignals.ToListAsync(), row => row.Code == "RUNTIME_REPLY_BINDING_UNAVAILABLE");
    }

    [Fact]
    public async Task TerminalReplyAndCheckpointShareOneCanonicalOutboxIdentity()
    {
        var context = await CreateAsync(whatsApp: true);
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.system",
            new { text = "No work completed.", code = "MODEL_UNAVAILABLE" }), CancellationToken.None);
        var terminal = Event(context.Source, 2, "execution.failed",
            new { state = "FAILED", partial = false, completionReason = "PARTIAL_FAILURE" });
        await context.Ingestion.ApplyAsync(context.Source, terminal, CancellationToken.None);
        await context.Ingestion.ApplyAsync(context.Source, terminal, CancellationToken.None);
        await using var db = context.Conversations.CreateDbContext();
        var reply = await db.Messages.SingleAsync(row => row.Actor == "SYSTEM");
        var outbound = Assert.Single(await db.ConversationOutbox.ToListAsync());
        Assert.Equal(reply.MessageId, outbound.IdempotencyKey);
        Assert.Equal(reply.MessageId.ToString("D"), outbound.AggregateId);
        Assert.Equal(context.Source.OriginRecipientDigest, outbound.RecipientBindingDigest);
        Assert.Equal(2, await db.RuntimeEventReceipts.CountAsync());
    }

    [Fact]
    public async Task StopLatchRejectsInFlightResponseBeforeCheckpointOrReply()
    {
        var context = await CreateAsync();
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.EmergencyStopLatches.Add(new()
            {
                Environment = "Demo", TenantId = context.Source.TenantId,
                RelationshipId = context.Source.RelationshipId,
            });
            await db.SaveChangesAsync();
        }
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.delta",
                new { contentIndex = 0, appendText = "late response", partial = true }), CancellationToken.None));
        await using var verify = context.Conversations.CreateDbContext();
        Assert.Empty(await verify.RuntimeEventReceipts.ToListAsync());
        Assert.Single(await verify.Messages.ToListAsync());
    }

    [Fact]
    public async Task OverProviderLimitPreservesFullWebReplyAndQueuesExplicitPortalNotice()
    {
        var context = await CreateAsync(whatsApp: true);
        var text = new string('x', 4097);
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 1, "response.delta",
            new { contentIndex = 0, appendText = text, partial = true }), CancellationToken.None);
        await context.Ingestion.ApplyAsync(context.Source, Event(context.Source, 2, "execution.completed",
            new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" }), CancellationToken.None);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Equal(text, Assert.Single(JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(
            (await db.Messages.SingleAsync(row => row.Actor == "PROFESSIONAL")).ContentJson, Json)!).Text);
        Assert.True((await db.Executions.SingleAsync()).RuntimeTerminal);
        var notice = await db.Messages.SingleAsync(row => row.Actor == "SYSTEM");
        var noticeText = Assert.Single(JsonSerializer.Deserialize<List<ConversationTextBlockV1>>(notice.ContentJson, Json)!).Text;
        Assert.Contains("too long", noticeText);
        Assert.Contains("no content has been cut off", noticeText);
        Assert.True(noticeText.Length <= 4096);
        Assert.Equal(notice.MessageId, Assert.Single(await db.ConversationOutbox.ToListAsync()).IdempotencyKey);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task WorkerDoesNotReadEventsOrChangeDueTimeForPendingStart(bool scopedWork)
    {
        var context = await CreateAsync();
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.PendingStarts.Add(new()
            {
                TenantId = context.Source.TenantId,
                MessageId = context.Source.MessageId,
                ExecutionId = context.Source.ExecutionId,
            });
            await db.SaveChangesAsync();
        }
        var source = new RecordingSource([]);
        var scope = new WhatsAppTenantExecutionScope(new RuntimeGate(context.Source.TenantId), TimeProvider.System);
        var workScope = new ConversationRuntimeWorkScope();
        var worker = new ConversationRuntimeEventWorker(context.Conversations, context.Ingestion, source, scope,
            Options.Create(new Wc120ConversationOptions
            {
                Environment = "Demo", Enabled = true, RuntimeEventIngestionEnabled = true,
            }), TimeProvider.System, NullLogger<ConversationRuntimeEventWorker>.Instance, workScope);
        using var authority = scopedWork
            ? workScope.Begin(new ConversationRuntimeWork(context.Source.TenantId, context.Source.ExecutionId))
            : scope.Begin();

        Assert.False(await worker.ProcessOneAsync(CancellationToken.None));
        Assert.Empty(source.Cursors);
        await using var verify = context.Conversations.CreateDbContext();
        Assert.Null((await verify.Executions.SingleAsync()).RuntimeNextAttemptAt);
        Assert.Empty(await verify.RuntimeEventReceipts.ToListAsync());
    }

    [Fact]
    public async Task WorkerResumesCommittedCursorAfterInterruptedStream()
    {
        var context = await CreateAsync();
        var events = new[]
        {
            Event(context.Source, 1, "execution.accepted", new { serverTime = DateTimeOffset.UtcNow }),
            Event(context.Source, 2, "response.delta",
                new { contentIndex = 0, appendText = "Recovered response", partial = true }),
            Event(context.Source, 3, "execution.completed",
                new { state = "COMPLETED", partial = false, completionReason = "COMPLETE" }),
        };
        var source = new RecordingSource(events) { Interrupt = true };
        var scope = new WhatsAppTenantExecutionScope(new RuntimeGate(context.Source.TenantId), TimeProvider.System);
        var worker = new ConversationRuntimeEventWorker(context.Conversations, context.Ingestion, source, scope,
            Options.Create(new Wc120ConversationOptions
            {
                Environment = "Demo", Enabled = true, RuntimeEventIngestionEnabled = true,
            }), TimeProvider.System, NullLogger<ConversationRuntimeEventWorker>.Instance);
        using var tenant = scope.Begin();
        Assert.True(await worker.ProcessOneAsync(CancellationToken.None));
        await using (var db = context.Conversations.CreateDbContext())
        {
            var execution = await db.Executions.SingleAsync();
            Assert.Equal(1, execution.RuntimeSequence);
            Assert.False(execution.RuntimeTerminal);
            Assert.Contains(await db.OperationalSignals.ToListAsync(),
                row => row.Code == "RUNTIME_EVENT_RECONCILIATION_REQUIRED");
            execution.RuntimeNextAttemptAt = null;
            await db.SaveChangesAsync();
        }
        source.Interrupt = false;
        Assert.True(await worker.ProcessOneAsync(CancellationToken.None));
        Assert.Equal(new long[] { 0, 1 }, source.Cursors);
        await using var complete = context.Conversations.CreateDbContext();
        Assert.Equal(3, await complete.RuntimeEventReceipts.CountAsync());
        Assert.True((await complete.Executions.SingleAsync()).RuntimeTerminal);
        Assert.False(await worker.ProcessOneAsync(CancellationToken.None));
    }

    private sealed class RecordingSource(IReadOnlyList<RuntimeExecutionEventV1> events)
        : IConversationExecutionEventSource
    {
        public bool Interrupt { get; set; }
        public List<long> Cursors { get; } = [];
        public async IAsyncEnumerable<RuntimeExecutionEventV1> ReadEventsAsync(
            Guid conversationId, Guid messageId, ConversationExecutionCallerV1 caller, Guid idempotencyKey,
            long afterSequence, [EnumeratorCancellation] CancellationToken cancellationToken)
        {
            Cursors.Add(afterSequence);
            foreach (var value in events.Where(value => value.Sequence > afterSequence))
            {
                cancellationToken.ThrowIfCancellationRequested();
                await Task.Yield();
                yield return value;
                if (Interrupt)
                    throw new ConversationExecutionUnavailableException();
            }
        }
    }

    private sealed class RuntimeGate(Guid tenantId) : IWhatsAppCapabilityGate
    {
        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");
        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) => new() { TenantId = tenantId };
        public void RequireRecipient(Guid tenant, string recipient, DateTimeOffset now) => throw new NotSupportedException();
    }

    private static RuntimeExecutionEventV1 Event(ConversationRuntimeSource source, long sequence, string type, object data) =>
        new("1.0", $"{source.Caller.RuntimeExecutionId:D}:{sequence}", type, source.ConversationId,
            source.Caller.RuntimeExecutionId, source.MessageId, sequence,
            DateTimeOffset.UtcNow, JsonSerializer.SerializeToElement(data, Json));

    private sealed class AdvancingTimeProvider : TimeProvider
    {
        private DateTimeOffset _now = DateTimeOffset.UtcNow;
        public override DateTimeOffset GetUtcNow() => _now;
        public void Advance(TimeSpan duration) => _now += duration;
    }

    private static async Task<Context> CreateAsync(
        bool expired = false, bool whatsApp = false, TimeProvider? timeProvider = null)
    {
        var conversations = new InMemoryConversationFactory($"runtime-{Guid.NewGuid():N}");
        var relationships = new InMemoryEmploymentRelationshipFactory($"runtime-authority-{Guid.NewGuid():N}");
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var participant = Guid.NewGuid();
        var conversation = Guid.NewGuid();
        var message = Guid.NewGuid();
        var execution = Guid.NewGuid();
        var key = Guid.NewGuid();
        var binding = Guid.NewGuid();
        var recipient = new string('a', 64);
        var inputJson = JsonSerializer.Serialize(new[] { new ConversationTextBlockV1("1.0", "TEXT", "original input", "hi-IN") }, Json);
        await using (var db = conversations.CreateDbContext())
        {
            db.Conversations.Add(new()
            {
                TenantId = tenant, RelationshipId = relationship, ConversationId = conversation,
                Environment = "Demo", NextMessageSequence = 2,
            });
            db.Messages.Add(new()
            {
                MessageId = message, TenantId = tenant, RelationshipId = relationship, ConversationId = conversation,
                Environment = "Demo", Sequence = 1, SkillId = "accepted-skill", EvidenceRecordId = Guid.NewGuid(),
                EvidenceState = "RECORDED", ContentJson = inputJson, Channel = whatsApp ? "WHATSAPP" : "WEB",
            });
            db.Executions.Add(new()
            {
                ExecutionId = execution, TenantId = tenant, RelationshipId = relationship,
                ConversationId = conversation, MessageId = message,
                OriginChannelBindingId = whatsApp ? binding : null,
                OriginRecipientDigest = whatsApp ? recipient : null,
            });
            db.IdempotencyOutcomes.Add(new()
            {
                TenantId = tenant, RelationshipId = relationship, ActorParticipantId = participant,
                ExecutionId = execution, MessageId = message, IdempotencyKey = key, OperationFamily = "SEND",
            });
            await db.SaveChangesAsync();
        }
        await using (var db = relationships.CreateDbContext())
        {
            db.EmploymentRelationships.Add(new()
            {
                TenantId = tenant, RelationshipId = relationship, State = EmploymentRelationshipState.Active,
                ProfessionalType = "DMA", InitiatingParticipantId = participant,
            });
            db.RelationshipParticipants.Add(new()
            {
                TenantId = tenant, RelationshipId = relationship, ParticipantId = participant,
                Role = RelationshipParticipantRole.Employer, BoundEvidenceId = Guid.NewGuid(),
            });
            db.OperationalMandateSnapshots.Add(new()
            {
                TenantId = tenant, RelationshipId = relationship, ActorParticipantId = participant,
                IdempotencyIdentity = key, SkillId = "accepted-skill",
                Deadline = DateTimeOffset.UtcNow.AddMinutes(expired ? -1 : 10),
            });
            if (whatsApp)
            {
                db.ChannelBindings.Add(new()
                {
                    BindingId = binding, TenantId = tenant, RelationshipId = relationship, ParticipantId = participant,
                    Channel = "WHATSAPP", Status = "ACTIVE", ExternalSubjectHash = recipient,
                    ConversationId = conversation.ToString("D"),
                });
                db.WhatsAppJourneyContacts.Add(new()
                {
                    TenantId = tenant, PhoneHmac = recipient, OptedInAt = DateTimeOffset.UtcNow.AddMinutes(-5),
                    LastInboundAt = DateTimeOffset.UtcNow.AddMinutes(-1),
                });
            }
            await db.SaveChangesAsync();
        }
        var ingestion = new ConversationRuntimeEventIngestion(conversations, relationships,
            Options.Create(new Wc120ConversationOptions { Environment = "Demo", Enabled = true, DispatchEnabled = true }),
            timeProvider ?? TimeProvider.System, new ConversationCursorCodec(Options.Create(new ConversationCursorOptions
            {
                HmacKey = "runtime-ingestion-synthetic-key-at-least-32-characters",
            })));
        return new(conversations, relationships, ingestion,
            await ingestion.GetSourceAsync(tenant, execution, CancellationToken.None), inputJson);
    }

    private sealed record Context(
        InMemoryConversationFactory Conversations, InMemoryEmploymentRelationshipFactory Relationships,
        ConversationRuntimeEventIngestion Ingestion, ConversationRuntimeSource Source, string InputJson);
}
