using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Waooaw.BusinessPlatform.Tests.Identity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppRelationshipRoutingScopeTests
{
    [Theory]
    [InlineData("actor")]
    [InlineData("dialogue")]
    [InlineData("channel")]
    [InlineData("content")]
    [InlineData("publish")]
    [InlineData("eligibility")]
    [InlineData("purpose")]
    [InlineData("environment")]
    [InlineData("tenant")]
    [InlineData("participant")]
    [InlineData("relationship")]
    [InlineData("recipient")]
    [InlineData("too-few")]
    [InlineData("too-many")]
    [InlineData("empty-source")]
    [InlineData("duplicate-source")]
    public async Task ClarificationQuestionRejectsEveryNonCanonicalAuthorityBinding(
        string defect
    )
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        var eligibility = new WhatsAppOutboundEligibility(
            true,
            false,
            false,
            DateTimeOffset.UtcNow,
            defect == "purpose" ? "OTHER" : "CUSTOMER_REQUEST",
            defect == "recipient" ? new string('c', 64) : route.SenderHash,
            null,
            null,
            null,
            null,
            false
        );
        var contribution = new OutboundConversationContributionV1(
            defect == "actor" ? "PROFESSIONAL" : "SYSTEM",
            "TEXT",
            defect == "dialogue" ? "INFORM" : "ASK",
            defect == "content"
                ? "Different question"
                : ConversationRequestClarification.Question,
            "clarification",
            "1.0",
            defect == "channel" ? "WEB" : "WHATSAPP",
            Guid.NewGuid(),
            "question",
            new string('a', 64),
            defect != "publish",
            defect == "eligibility" ? null : eligibility
        );
        var sources = defect switch
        {
            "too-few" => new[] { Guid.NewGuid() },
            "too-many" => Enumerable.Range(0, 4).Select(_ => Guid.NewGuid()).ToArray(),
            "empty-source" => new[] { Guid.NewGuid(), Guid.Empty },
            "duplicate-source" => new[] { Guid.NewGuid(), Guid.Empty },
            _ => new[] { Guid.NewGuid(), Guid.NewGuid() },
        };
        if (defect == "duplicate-source")
            sources[1] = sources[0];
        var options = Options.Create(
            new Wc120ConversationOptions
            {
                Environment = defect == "environment" ? "other" : authority.Environment,
            }
        );
        var service = new ConversationOutboundContributionService(
            null!,
            null!,
            null!,
            options,
            scope
        );
        using (scope.Begin())
        using (scope.BeginRelationshipValidation(candidate))
        {
            scope.ConfirmRelationshipRoute(route);
            await Assert.ThrowsAsync<ConversationRequestException>(
                () =>
                    service.CommitClarificationQuestionAsync(
                        defect == "tenant" ? Guid.NewGuid() : route.TenantId,
                        defect == "participant" ? Guid.NewGuid() : route.ParticipantId,
                        defect == "relationship" ? Guid.NewGuid() : route.RelationshipId,
                        contribution,
                        sources,
                        DateTimeOffset.UtcNow,
                        CancellationToken.None
                    )
            );
        }
    }

    [Theory]
    [InlineData("unchanged")]
    [InlineData("activation-changed")]
    [InlineData("route-published")]
    [InlineData("recipient-denied")]
    public async Task SignedIngressCannotReleaseRetainedServiceReceiptAfterAuthorityOrRouteChanges(string change)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var routing = new WhatsAppRelationshipRouting(context.Relationships, context.Conversations,
            IdentityTestHelpers.CreateService(identities), scope, gate,
            new ConfigurationBuilder().Build(), TimeProvider.System);
        var operationCalls = 0;
        using (scope.Begin())
        {
            Task<string> Receive() => routing.ExecuteSignedIngressAsync(authority.RecipientBindingDigest, async ct =>
            {
                operationCalls++;
                if (change == "activation-changed")
                    gate.Authority = authority with { ActivationReference = "revoked-during-receipt-replay" };
                if (change == "recipient-denied")
                    gate.DenyRecipient = true;
                if (change == "route-published")
                {
                    await using var db = context.Relationships.CreateDbContext();
                    db.Add(new WhatsAppRelationshipRoute
                    {
                        ServiceTenantId = authority.TenantId, SenderHash = authority.RecipientBindingDigest,
                        TenantId = context.TenantId, BindingId = Guid.NewGuid(), ActorId = context.ParticipantId,
                    });
                    await db.SaveChangesAsync(ct);
                }
                return "retained private receipt";
            }, CancellationToken.None);
            if (change == "unchanged")
                Assert.Equal("retained private receipt", await Receive());
            else if (change is "activation-changed" or "recipient-denied")
                await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(Receive);
            else
                await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(Receive);
            Assert.Null(scope.DatabaseTenantOverrideId);
        }
        Assert.Equal(1, operationCalls);
        Assert.Null(scope.CurrentTenantId);
        await using var store = context.Conversations.CreateDbContext();
        Assert.Empty(store.Messages);
        Assert.Empty(store.Executions);
    }

    [Fact]
    public void ProtectedReadReleaseRechecksActivationAndRejectsCandidateOnlyAuthority()
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        WhatsAppRelationshipRouting.RequireIngressReadRelease(scope);
        using (scope.Begin())
        {
            WhatsAppRelationshipRouting.RequireIngressReadRelease(scope);
            var candidate = Candidate(authority);
            using (scope.BeginRelationshipValidation(candidate))
            {
                Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                    WhatsAppRelationshipRouting.RequireIngressReadRelease(scope));
                scope.ConfirmRelationshipRoute(Route(candidate, authority.Environment));
                WhatsAppRelationshipRouting.RequireIngressReadRelease(scope);
                gate.Authority = authority with { ActivationReference = "revoked-at-release" };
                Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                    WhatsAppRelationshipRouting.RequireIngressReadRelease(scope));
            }
        }
        Assert.Null(scope.CurrentTenantId);
    }

    [Theory]
    [InlineData("timeline")]
    [InlineData("message-execution")]
    [InlineData("execution")]
    [InlineData("events")]
    [InlineData("events-after")]
    [InlineData("skill")]
    [InlineData("send-replay")]
    [InlineData("retry-replay")]
    [InlineData("journey-recovery")]
    [InlineData("contribution-replay")]
    [InlineData("read-position-replay")]
    [InlineData("cancel-terminal")]
    [InlineData("cancel-request")]
    [InlineData("read-position-write")]
    public async Task ProtectedReadAndReplayConsumersNeverReleaseContentWithoutCurrentRouting(string surface)
    {
        foreach (var denial in new[] { "missing-owner", "non-postgres", "candidate-only", "changed-activation" })
        {
            var context = await Wc120FitnessContext.CreateAsync();
            var authority = Authority();
            await context.SeedWhatsAppEligibilityAsync(authority.RecipientBindingDigest, DateTimeOffset.UtcNow);
            await using var relationships = context.Relationships.CreateDbContext();
            var binding = await relationships.ChannelBindings.SingleAsync();
            var candidate = new WhatsAppRelationshipRoute
            {
                ServiceTenantId = authority.TenantId, SenderHash = authority.RecipientBindingDigest,
                TenantId = context.TenantId, BindingId = binding.BindingId, ActorId = context.ParticipantId,
            };
            var route = new WhatsAppCurrentRelationshipRoute(
                authority.TenantId, authority.Environment, candidate.SenderHash, context.TenantId,
                binding.BindingId, context.RelationshipId, context.ParticipantId, binding.ParticipantRole,
                context.WhatsAppConversationId, 0);
            var gate = new Gate(authority);
            var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
            var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
            var routing = new WhatsAppRelationshipRouting(context.Relationships, context.Conversations,
                IdentityTestHelpers.CreateService(identities), scope, gate,
                new ConfigurationBuilder().Build(), TimeProvider.System);
            var evidence = new ConversationConstitutionalGatewayStub();
            var runtime = new ConversationExecutionGatewayStub();
            var mandate = new OperationalMandateResolverStub();
            var cursor = new ConversationCursorCodec(
                Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) }));
            ConversationService Service(bool routed) => new(
                context.Conversations, context.Relationships, evidence, runtime, mandate, cursor,
                conversationOptions: Options.Create(context.Options),
                whatsAppExecution: routed ? scope : null,
                whatsAppRouting: routed && denial != "missing-owner" ? routing : null);
            var key = Guid.NewGuid();
            var request = new SendConversationMessageRequestV1("1.0", key, "INDUCTION",
                [new("1.0", "TEXT", "private original customer text", "en-IN")], "en-IN", Channel: "WHATSAPP");
            var origin = new ConversationChannelOrigin(binding.BindingId, candidate.SenderHash);
            await Service(false).SendAsync(context.TenantId, context.ParticipantId, context.RelationshipId,
                key, request, CancellationToken.None, origin);
            await using var store = context.Conversations.CreateDbContext();
            var input = await store.Messages.SingleAsync();
            var execution = await store.Executions.SingleAsync();
            if (surface is "retry-replay" or "cancel-terminal")
            {
                input.ProcessingState = "COMPLETED";
                execution.ProcessingState = "COMPLETED";
                await store.SaveChangesAsync();
            }
            var readPositionKey = Guid.NewGuid();
            var readPosition = new UpdateConversationReadPositionRequestV1("1.0", input.MessageId,
                cursor.Encode(context.TenantId, context.RelationshipId, "timeline", input.Sequence));
            if (surface == "read-position-replay")
                await Service(false).UpdateReadPositionAsync(context.TenantId, context.ParticipantId,
                    context.RelationshipId, readPositionKey, readPosition, CancellationToken.None);
            var contributionKey = Guid.NewGuid();
            var contribution = new OutboundConversationContributionV1("SYSTEM", "TEXT", "INFORM",
                "private retained reply", "INDUCTION", null, "WHATSAPP", contributionKey,
                "retained-reply", new string('a', 64), false, null,
                JourneyStatus: "INFORM", JourneyStage: "INFORM");
            if (surface is "journey-recovery" or "contribution-replay")
                await new ConversationOutboundContributionService(context.Conversations,
                    context.Profiles, context.StopFence, Options.Create(context.Options))
                    .CommitAsync(context.TenantId, context.ParticipantId, context.RelationshipId,
                        contribution, DateTimeOffset.UtcNow, CancellationToken.None);
            var originalStarts = runtime.StartCount;
            var originalCancels = runtime.CancelCount;
            var originalEvidence = evidence.CallCount;
            var originalMandates = mandate.ResolveCount;
            using (scope.Begin())
            using (scope.BeginRelationshipValidation(candidate))
            {
                if (denial != "candidate-only")
                    scope.ConfirmRelationshipRoute(route);
                if (denial == "changed-activation")
                    gate.Authority = authority with { ActivationReference = "retired-before-read" };
                var service = Service(true);
                var outbound = new ConversationOutboundContributionService(context.Conversations,
                    context.Profiles, context.StopFence, Options.Create(context.Options),
                    scope, denial == "missing-owner" ? null : routing);
                async Task Read()
                {
                    switch (surface)
                    {
                        case "timeline":
                            await service.ListMessagesAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, null, null, 20, CancellationToken.None);
                            break;
                        case "message-execution":
                            await service.GetMessageExecutionAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, input.MessageId, CancellationToken.None);
                            break;
                        case "execution":
                            await service.GetExecutionAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, execution.ExecutionId, CancellationToken.None);
                            break;
                        case "events":
                            await service.GetEventReplayAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, null, CancellationToken.None);
                            break;
                        case "events-after":
                            await service.GetEventReplayAfterSequenceAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, 0, CancellationToken.None);
                            break;
                        case "skill":
                            await service.ResolveChannelSkillAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, CancellationToken.None, key);
                            break;
                        case "send-replay":
                            await service.SendAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, key, request, CancellationToken.None, origin);
                            break;
                        case "retry-replay":
                            await service.RetryAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, input.MessageId, key, CancellationToken.None);
                            break;
                        case "journey-recovery":
                            await outbound.RecoverJourneyReplyAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, contributionKey, CancellationToken.None);
                            break;
                        case "contribution-replay":
                            await outbound.CommitAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, contribution, DateTimeOffset.UtcNow, CancellationToken.None);
                            break;
                        case "read-position-replay":
                        case "read-position-write":
                            await service.UpdateReadPositionAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, readPositionKey, readPosition, CancellationToken.None);
                            break;
                        case "cancel-terminal":
                        case "cancel-request":
                            await service.CancelAsync(context.TenantId, context.ParticipantId,
                                context.RelationshipId, execution.ExecutionId, Guid.NewGuid(), CancellationToken.None);
                            break;
                    }
                }
                if (denial is "candidate-only" or "changed-activation")
                    await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(Read);
                else if (denial == "missing-owner")
                    await Assert.ThrowsAsync<WhatsAppWebhookException>(Read);
                else
                    await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(Read);
            }
            Assert.Equal(originalStarts, runtime.StartCount);
            Assert.Equal(originalCancels, runtime.CancelCount);
            Assert.Equal(originalEvidence + (surface is "cancel-request" or "read-position-write" ? 1 : 0),
                evidence.CallCount);
            Assert.Equal(originalMandates, mandate.ResolveCount);
            Assert.Null(scope.CurrentTenantId);
            Assert.Null(scope.DatabaseTenantOverrideId);
            await using var verify = context.Conversations.CreateDbContext();
            Assert.Equal(surface is "journey-recovery" or "contribution-replay" ? 2 : 1,
                await verify.Messages.CountAsync());
            Assert.Equal(surface == "read-position-replay" ? 1 : 0, await verify.ReadPositions.CountAsync());
        }
    }

    [Theory]
    [InlineData("send", "missing-owner")]
    [InlineData("send", "non-postgres")]
    [InlineData("send", "changed-activation")]
    [InlineData("retry", "missing-owner")]
    [InlineData("retry", "non-postgres")]
    [InlineData("retry", "changed-activation")]
    [InlineData("retry", "missing-origin")]
    [InlineData("retry", "unknown-outcome")]
    [InlineData("retry", "queued-outcome")]
    [InlineData("contribution", "missing-owner")]
    [InlineData("contribution", "non-postgres")]
    [InlineData("contribution", "changed-activation")]
    public async Task CanonicalIngressConsumersRecheckAfterEvidenceBeforePersistenceOrRuntime(
        string operation, string denial)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var authority = Authority();
        await context.SeedWhatsAppEligibilityAsync(authority.RecipientBindingDigest, DateTimeOffset.UtcNow);
        await using var relationships = context.Relationships.CreateDbContext();
        var binding = await relationships.ChannelBindings.SingleAsync();
        var candidate = new WhatsAppRelationshipRoute
        {
            ServiceTenantId = authority.TenantId, SenderHash = authority.RecipientBindingDigest,
            TenantId = context.TenantId, BindingId = binding.BindingId, ActorId = context.ParticipantId,
        };
        var expected = new WhatsAppCurrentRelationshipRoute(
            authority.TenantId, authority.Environment, candidate.SenderHash, context.TenantId,
            binding.BindingId, context.RelationshipId, context.ParticipantId, binding.ParticipantRole,
            context.WhatsAppConversationId, 0);
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var routing = new WhatsAppRelationshipRouting(context.Relationships, context.Conversations,
            IdentityTestHelpers.CreateService(identities), scope, gate,
            new ConfigurationBuilder().Build(), TimeProvider.System);
        var evidence = new ConversationConstitutionalGatewayStub();
        var runtime = new ConversationExecutionGatewayStub();
        var mandate = new OperationalMandateResolverStub();
        var cursor = new ConversationCursorCodec(
            Options.Create(new ConversationCursorOptions { HmacKey = new string('p', 48) }));
        ConversationService Service(bool routed) => new(
            context.Conversations, context.Relationships, evidence, runtime, mandate, cursor,
            conversationOptions: Options.Create(context.Options),
            whatsAppExecution: routed ? scope : null,
            whatsAppRouting: routed && denial != "missing-owner" ? routing : null);
        var key = Guid.NewGuid();
        var request = new SendConversationMessageRequestV1(
            "1.0", key, "INDUCTION", [new("1.0", "TEXT", "bounded customer text", "en-IN")],
            "en-IN", Channel: "WHATSAPP");
        var origin = new ConversationChannelOrigin(binding.BindingId, candidate.SenderHash);
        Guid messageId = Guid.Empty;
        if (operation == "retry")
        {
            runtime.FailStart = true;
            await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() =>
                Service(false).SendAsync(context.TenantId, context.ParticipantId, context.RelationshipId,
                    key, request, CancellationToken.None, origin));
            await using var prior = context.Conversations.CreateDbContext();
            messageId = (await prior.Messages.SingleAsync()).MessageId;
            if (denial != "unknown-outcome")
            {
                (await prior.Messages.SingleAsync()).DeliveryState = "FAILED";
                (await prior.IdempotencyOutcomes.SingleAsync()).Outcome = "FAILED";
                await prior.SaveChangesAsync();
            }
            if (denial == "queued-outcome")
            {
                var input = await prior.Messages.SingleAsync();
                input.DeliveryState = "ACCEPTED";
                input.ProcessingState = "QUEUED";
                (await prior.Executions.SingleAsync()).ProcessingState = "QUEUED";
                (await prior.IdempotencyOutcomes.SingleAsync()).Outcome = "ACCEPTED";
                await prior.SaveChangesAsync();
            }
            if (denial == "missing-origin")
            {
                prior.Entry(await prior.Executions.SingleAsync())
                    .Property(value => value.OriginChannelBindingId).CurrentValue = null;
                await prior.SaveChangesAsync();
            }
            runtime.FailStart = false;
        }
        var priorStarts = runtime.StartCount;
        var priorEvidence = evidence.CallCount;
        var priorMandates = mandate.ResolveCount;
        evidence.BeforeConfirm = () =>
        {
            if (denial == "changed-activation")
                gate.Authority = authority with { ActivationReference = "revoked-during-evidence" };
        };
        using (scope.Begin())
        using (scope.BeginRelationshipValidation(candidate))
        {
            scope.ConfirmRelationshipRoute(expected);
            async Task Execute()
            {
                if (operation == "send")
                    await Service(true).SendAsync(context.TenantId, context.ParticipantId, context.RelationshipId,
                        key, request, CancellationToken.None, origin);
                else if (operation == "retry")
                    await Service(true).RetryAsync(context.TenantId, context.ParticipantId, context.RelationshipId,
                        messageId, key, CancellationToken.None);
                else
                {
                    if (denial == "changed-activation")
                        gate.Authority = authority with { ActivationReference = "revoked-before-commit" };
                    var outbound = new ConversationOutboundContributionService(
                        context.Conversations, context.Profiles, context.StopFence, Options.Create(context.Options),
                        scope, denial == "missing-owner" ? null : routing);
                    await outbound.CommitAsync(context.TenantId, context.ParticipantId, context.RelationshipId,
                        new OutboundConversationContributionV1("SYSTEM", "TEXT", "INFORM", "bounded notice",
                            "INDUCTION", null, "WHATSAPP", key, "canonical-notice", new string('a', 64), true,
                            new WhatsAppOutboundEligibility(true, false, false, DateTimeOffset.UtcNow,
                                "CUSTOMER_REQUEST", candidate.SenderHash, null, null, null, null, false)),
                        DateTimeOffset.UtcNow, CancellationToken.None);
                }
            }
            if (denial is "missing-origin" or "unknown-outcome" or "queued-outcome")
                await Assert.ThrowsAsync<ConversationRetryNotAllowedException>(Execute);
            else if (denial == "changed-activation")
                await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(Execute);
            else if (denial == "missing-owner")
                await Assert.ThrowsAsync<WhatsAppWebhookException>(Execute);
            else
                await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(Execute);
        }
        Assert.Equal(priorStarts, runtime.StartCount);
        if (denial is "missing-origin" or "unknown-outcome" or "queued-outcome")
        {
            Assert.Equal(priorEvidence, evidence.CallCount);
            Assert.Equal(priorMandates, mandate.ResolveCount);
        }
        Assert.Null(scope.CurrentTenantId);
        Assert.Null(scope.DatabaseTenantOverrideId);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Equal(operation == "retry" ? 1 : 0, db.Messages.Count());
        Assert.Equal(operation == "retry" ? 1 : 0, db.IdempotencyOutcomes.Count());
        Assert.Empty(db.ConversationOutbox);
        if (operation == "retry")
            Assert.Equal(denial == "queued-outcome" ? "QUEUED" : "FAILED", db.Executions.Single().ProcessingState);
    }

    [Theory]
    [InlineData("tenant")]
    [InlineData("participant")]
    [InlineData("relationship")]
    [InlineData("conversation")]
    [InlineData("channel")]
    [InlineData("binding")]
    [InlineData("sender")]
    [InlineData("candidate-only")]
    public async Task IngressCommitRequiresExactSnapshotNotOnlySelectedCustomerScope(string change)
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        var factory = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        using var service = scope.Begin();
        using var customer = scope.BeginRelationshipValidation(candidate);
        if (change != "candidate-only")
            scope.ConfirmRelationshipRoute(route);
        await using var db = factory.CreateDbContext();
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            WhatsAppRelationshipRouting.RequireIngressCommitAsync(scope, null, db,
                change == "tenant" ? Guid.NewGuid() : route.TenantId,
                change == "participant" ? Guid.NewGuid() : route.ParticipantId,
                change == "relationship" ? Guid.NewGuid() : route.RelationshipId,
                change == "conversation" ? Guid.NewGuid() : route.ConversationId,
                change == "channel" ? "WEB" : "WHATSAPP",
                change == "binding" ? Guid.NewGuid() : route.BindingId,
                change == "sender" ? new string('b', 64) : route.SenderHash,
                CancellationToken.None));
        Assert.Empty(db.Messages);
        Assert.Empty(db.Executions);
        Assert.Empty(db.ConversationOutbox);
        Assert.Null(scope.DatabaseTenantOverrideId);
    }

    [Theory]
    [InlineData("missing-scope")]
    [InlineData("service-override")]
    [InlineData("foreign-sender")]
    [InlineData("ordinary-text")]
    [InlineData("unsupported")]
    [InlineData("expired")]
    [InlineData("environment")]
    [InlineData("non-postgres")]
    public async Task SafetyEntryDeniesInvalidScopeOrInputBeforeAnyEffect(string change)
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var relationships = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var conversations = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var routing = new WhatsAppRelationshipRouting(relationships, conversations,
            IdentityTestHelpers.CreateService(identities), scope, gate,
            new ConfigurationBuilder().Build(), TimeProvider.System);
        var now = DateTimeOffset.UtcNow;
        var proof = new VerifiedPhoneIdentityProof("safety", change == "foreign-sender"
            ? new string('b', 64) : authority.RecipientBindingDigest,
            change == "ordinary-text" ? "please stop the task" : "STOP", null,
            "whatsapp-provider-callback", "AAL1_CHANNEL", now, now,
            now.AddMinutes(change == "expired" ? -1 : 5), Guid.NewGuid())
        {
            Environment = change == "environment" ? "other" : authority.Environment,
            UnsupportedContent = change == "unsupported",
        };
        using var service = change == "missing-scope" ? null : scope.Begin();
        using var budget = change == "service-override" ? scope.BeginDatabaseTenantOverride(authority.TenantId) : null;
        Task<WhatsAppJourneyReceipt> Execute() =>
            routing.ReceiveSignedSafetyControlAsync(proof, null, CancellationToken.None);
        if (change == "non-postgres")
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(Execute);
        else
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(Execute);
        Assert.Equal(change == "missing-scope" ? (Guid?)null : authority.TenantId, scope.CurrentTenantId);
        Assert.Equal(change == "service-override" ? authority.TenantId : (Guid?)null, scope.DatabaseTenantOverrideId);
        await using var db = conversations.CreateDbContext();
        Assert.Empty(db.Set<WhatsAppGuestSession>());
        Assert.Empty(db.EmergencyStopLatches);
        Assert.Empty(db.ConversationOutbox);
    }

    [Theory]
    [InlineData("guest")]
    [InlineData("guest-failure")]
    [InlineData("missing-scope")]
    [InlineData("service-override")]
    [InlineData("customer-non-postgres")]
    [InlineData("foreign-sender")]
    public async Task SignedIngressDoesNotInventCustomerAuthorityOrLeakScope(string change)
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var relationships = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var conversations = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        if (change == "customer-non-postgres")
        {
            await using var seed = relationships.CreateDbContext();
            seed.Add(candidate);
            await seed.SaveChangesAsync();
        }
        var routing = new WhatsAppRelationshipRouting(
            relationships, conversations, IdentityTestHelpers.CreateService(identities),
            scope, gate, new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["IdentityBrokerRead:ActorIssuer"] = "https://identity.test",
            }).Build(), TimeProvider.System);
        using var service = change == "missing-scope" ? null : scope.Begin();
        using var budget = change == "service-override" ? scope.BeginDatabaseTenantOverride(authority.TenantId) : null;
        var called = false;
        Task<int> Execute() => routing.ExecuteSignedIngressAsync(
            change == "foreign-sender" ? new string('b', 64) : candidate.SenderHash,
            _ =>
            {
                called = true;
                Assert.Equal(authority.TenantId, scope.CurrentTenantId);
                Assert.Throws<WhatsAppCapabilityUnavailableException>(() => scope.RequireConfirmedRelationshipRoute());
                return change == "guest-failure" ? Task.FromException<int>(
                    new InvalidOperationException("Synthetic guest dependency failure.")) : Task.FromResult(7);
            }, CancellationToken.None);
        if (change == "guest")
            Assert.Equal(7, await Execute());
        else if (change == "guest-failure")
            await Assert.ThrowsAsync<InvalidOperationException>(Execute);
        else if (change == "customer-non-postgres")
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(Execute);
        else
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(Execute);
        Assert.Equal(change is "guest" or "guest-failure", called);
        Assert.Equal(change == "missing-scope" ? (Guid?)null : authority.TenantId, scope.CurrentTenantId);
        Assert.Equal(change == "service-override" ? authority.TenantId : (Guid?)null, scope.DatabaseTenantOverrideId);
        await using var db = conversations.CreateDbContext();
        Assert.Empty(db.ConversationOutbox);
    }

    [Theory]
    [InlineData("tenant")]
    [InlineData("relationship")]
    [InlineData("conversation")]
    [InlineData("environment")]
    [InlineData("expired")]
    [InlineData("candidate")]
    [InlineData("non-postgres")]
    public async Task LeasedWorkerEntryCannotInvokeProviderWithChangedCoordinates(string change)
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var routing = new WhatsAppRelationshipRouting(
            new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N")),
            new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N")),
            IdentityTestHelpers.CreateService(identities), scope, gate,
            new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
            {
                ["IdentityBrokerRead:ActorIssuer"] = "https://identity.test",
            }).Build(), TimeProvider.System);
        var lease = new WhatsAppOutboxLease(
            Guid.NewGuid(), change == "environment" ? "other" : route.Environment,
            change == "tenant" ? Guid.NewGuid() : route.TenantId,
            change == "relationship" ? Guid.NewGuid() : route.RelationshipId,
            change == "conversation" ? Guid.NewGuid() : route.ConversationId,
            1, "canonical", new string('a', 64), 1, false,
            DateTimeOffset.UtcNow.AddMinutes(change == "expired" ? -1 : 5));
        if (change == "candidate")
            candidate = new WhatsAppRelationshipRoute
            {
                ServiceTenantId = candidate.ServiceTenantId, TenantId = candidate.TenantId,
                SenderHash = candidate.SenderHash, ActorId = Guid.NewGuid(), BindingId = candidate.BindingId,
            };
        using var service = scope.Begin();
        var called = false;
        Task<bool> Execute() => routing.ExecuteLeasedCustomerWorkAsync(
            new(lease, candidate, route), (_, _) =>
            {
                called = true;
                return Task.FromResult(true);
            }, CancellationToken.None);
        if (change == "non-postgres")
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(Execute);
        else
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(Execute);
        Assert.False(called);
        Assert.Equal(authority.TenantId, scope.CurrentTenantId);
        Assert.Null(scope.DatabaseTenantOverrideId);
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() => scope.RequireConfirmedRelationshipRoute());
    }

    [Theory]
    [InlineData("missing-scope")]
    [InlineData("candidate-only")]
    [InlineData("changed-snapshot")]
    [InlineData("changed-activation")]
    [InlineData("missing-issuer")]
    [InlineData("non-postgres")]
    public async Task FinalEgressRouteFailsBeforeExternalWorkAndRestoresScope(string change)
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var expected = Route(candidate, authority.Environment);
        var conversations = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var relationships = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?>
            {
                ["IdentityBrokerRead:ActorIssuer"] = change == "missing-issuer" ? null : "https://identity.test",
            }).Build();
        var routing = new WhatsAppRelationshipRouting(
            relationships, conversations, IdentityTestHelpers.CreateService(identities),
            scope, gate, configuration, TimeProvider.System);
        using var service = change == "missing-scope" ? null : scope.Begin();
        using var customer = change == "missing-scope" ? null : scope.BeginRelationshipValidation(candidate);
        if (change is not ("missing-scope" or "candidate-only"))
            scope.ConfirmRelationshipRoute(expected);
        if (change == "changed-activation")
            gate.Authority = authority with { ActivationReference = "rotated" };
        var submitted = change == "changed-snapshot"
            ? expected with { RelationshipVersion = expected.RelationshipVersion + 1 } : expected;
        if (change is "missing-issuer" or "non-postgres")
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(() =>
                routing.RequireCurrentEgressRouteAsync(submitted, CancellationToken.None));
        else
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                routing.RequireCurrentEgressRouteAsync(submitted, CancellationToken.None));
        Assert.Null(scope.DatabaseTenantOverrideId);
        await using var db = conversations.CreateDbContext();
        Assert.Empty(db.ConversationOutbox);
        Assert.Empty(db.Set<WhatsAppTrafficReservation>());
    }

    [Fact]
    public async Task CustomerOutboundBudgetCannotSubstituteSnapshotOrDispatchCoordinates()
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        var factory = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var budget = new WhatsAppTrafficBudget(factory, gate, TimeProvider.System, scope);
        var request = new WhatsAppProviderDispatchRequest(
            Guid.NewGuid(), route.Environment, route.TenantId, route.RelationshipId,
            route.ConversationId, 1, "canonical", new string('a', 64), 1);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveRelationshipOutboundAsync(request, route, CancellationToken.None));
        using var service = scope.Begin();
        using var customer = scope.BeginRelationshipValidation(candidate);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveRelationshipOutboundAsync(request, route, CancellationToken.None));
        scope.ConfirmRelationshipRoute(route);
        foreach (var wrong in new[]
        {
            request with { TenantId = Guid.NewGuid() },
            request with { RelationshipId = Guid.NewGuid() },
            request with { ConversationId = Guid.NewGuid() },
            request with { Environment = "other" },
        })
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                budget.ReserveRelationshipOutboundAsync(wrong, route, CancellationToken.None));
        foreach (var wrong in new[]
        {
            route with { RelationshipVersion = route.RelationshipVersion + 1 },
            route with { ParticipantRole = "EVALUATOR" },
            route with { BindingId = Guid.NewGuid() },
        })
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
                budget.ReserveRelationshipOutboundAsync(request, wrong, CancellationToken.None));
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            new WhatsAppTrafficBudget(factory, gate, TimeProvider.System)
                .ReserveRelationshipOutboundAsync(request, route, CancellationToken.None));
        await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(() =>
            budget.ReserveRelationshipOutboundAsync(request, route, CancellationToken.None));
        Assert.Null(scope.DatabaseTenantOverrideId);
        Assert.Equal(route.TenantId, scope.CurrentTenantId);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.Set<WhatsAppTrafficReservation>());
        Assert.Empty(db.WhatsAppGuestTrafficEvents);
    }

    [Theory]
    [InlineData("missing-owner")]
    [InlineData("missing-scope")]
    [InlineData("candidate-only")]
    [InlineData("wrong-tenant")]
    [InlineData("wrong-relationship")]
    [InlineData("wrong-binding")]
    [InlineData("wrong-sender")]
    [InlineData("changed-activation")]
    public async Task CustomerInboundBudgetRequiresExactConfirmedRouteBeforeAnyLedgerWrite(string change)
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        var factory = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var budget = new WhatsAppTrafficBudget(
            factory, gate, TimeProvider.System, change == "missing-owner" ? null : scope);
        using var service = change == "missing-scope" ? null : scope.Begin();
        using var customer = change == "missing-scope" ? null : scope.BeginRelationshipValidation(candidate);
        if (change is not ("candidate-only" or "missing-scope"))
            scope.ConfirmRelationshipRoute(route);
        if (change == "changed-activation")
            gate.Authority = authority with { ActivationReference = "rotated" };
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveRelationshipInboundAsync(
                change == "wrong-tenant" ? Guid.NewGuid() : route.TenantId,
                change == "wrong-relationship" ? Guid.NewGuid() : route.RelationshipId,
                change == "wrong-binding" ? Guid.NewGuid() : route.BindingId,
                change == "wrong-sender" ? new string('b', 64) : route.SenderHash,
                "signed-inbound", CancellationToken.None));
        Assert.Null(scope.DatabaseTenantOverrideId);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.WhatsAppGuestTrafficEvents);
        Assert.Empty(db.Set<WhatsAppTrafficReservation>());
    }

    [Fact]
    public void CandidateScopeRequiresConfirmationBeforeRecipientAdmissionAndRestoresServiceTenant()
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        using (scope.Begin())
        {
            Assert.Equal(authority.TenantId, scope.CurrentTenantId);
            using (scope.BeginRelationshipValidation(candidate))
            {
                Assert.Equal(candidate.TenantId, scope.CurrentTenantId);
                Assert.Equal(authority.TenantId, scope.ServiceTenantId);
                Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                    scope.RequireRelationshipRecipient(route.TenantId, route.RelationshipId, route.BindingId, route.SenderHash));
                scope.ConfirmRelationshipRoute(route);
                scope.RequireRelationshipRecipient(route.TenantId, route.RelationshipId, route.BindingId, route.SenderHash);
                using (scope.BeginDatabaseTenantOverride(authority.TenantId))
                    Assert.Equal(authority.TenantId, scope.DatabaseTenantOverrideId);
                Assert.Null(scope.DatabaseTenantOverrideId);
                Assert.Throws<InvalidOperationException>(() => scope.BeginRelationshipValidation(candidate));
            }
            Assert.Equal(authority.TenantId, scope.CurrentTenantId);
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                scope.RequireRelationshipRecipient(route.TenantId, route.RelationshipId, route.BindingId, route.SenderHash));
        }
        Assert.Null(scope.CurrentTenantId);
        Assert.Null(scope.ServiceTenantId);
        Assert.Null(scope.DatabaseTenantOverrideId);
        Assert.All(gate.RecipientTenants, tenant => Assert.Equal(authority.TenantId, tenant));
    }

    [Theory]
    [InlineData("tenant")]
    [InlineData("binding")]
    [InlineData("actor")]
    [InlineData("sender")]
    [InlineData("environment")]
    public void ConfirmationCannotSubstituteCandidateCoordinates(string change)
    {
        var authority = Authority();
        var scope = new WhatsAppTenantExecutionScope(new Gate(authority), TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        using var service = scope.Begin();
        using var customer = scope.BeginRelationshipValidation(candidate);
        var changed = route with
        {
            TenantId = change == "tenant" ? Guid.NewGuid() : route.TenantId,
            BindingId = change == "binding" ? Guid.NewGuid() : route.BindingId,
            ParticipantId = change == "actor" ? Guid.NewGuid() : route.ParticipantId,
            SenderHash = change == "sender" ? new string('b', 64) : route.SenderHash,
            Environment = change == "environment" ? "other" : route.Environment,
        };
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() => scope.ConfirmRelationshipRoute(changed));
        scope.ConfirmRelationshipRoute(route);
        scope.RequireRelationshipRecipient(route.TenantId, route.RelationshipId, route.BindingId, route.SenderHash);
    }

    [Fact]
    public void RevocationFencesTenantSelectionAndRecipientAfterValidation()
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var candidate = Candidate(authority);
        var route = Route(candidate, authority.Environment);
        using var service = scope.Begin();
        using var customer = scope.BeginRelationshipValidation(candidate);
        scope.ConfirmRelationshipRoute(route);
        gate.Authority = authority with { ActivationReference = "changed" };
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() => scope.CurrentTenantId);
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            scope.RequireRelationshipRecipient(route.TenantId, route.RelationshipId, route.BindingId, route.SenderHash));
    }

    [Fact]
    public void CandidateMustUseCurrentServiceTenantAndCannotEnterDuringGuestOverride()
    {
        var authority = Authority();
        var scope = new WhatsAppTenantExecutionScope(new Gate(authority), TimeProvider.System);
        var candidate = Candidate(authority);
        Assert.Throws<InvalidOperationException>(() => scope.BeginRelationshipValidation(candidate));
        using var service = scope.Begin();
        using (scope.BeginDatabaseTenantOverride(authority.TenantId))
            Assert.Throws<InvalidOperationException>(() => scope.BeginRelationshipValidation(candidate));
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            scope.BeginRelationshipValidation(new WhatsAppRelationshipRoute
            {
                ServiceTenantId = Guid.NewGuid(), TenantId = candidate.TenantId,
                BindingId = candidate.BindingId, SenderHash = candidate.SenderHash,
            }));
    }

    [Fact]
    public async Task ConcurrentRoutingScopesDoNotShareCustomerAuthority()
    {
        var authority = Authority();
        var scope = new WhatsAppTenantExecutionScope(new Gate(authority), TimeProvider.System);
        var first = Candidate(authority);
        var second = Candidate(authority);
        var ready = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
        var arrivals = 0;
        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        async Task Run(WhatsAppRelationshipRoute candidate)
        {
            using var service = scope.Begin();
            using var customer = scope.BeginRelationshipValidation(candidate);
            var route = Route(candidate, authority.Environment);
            scope.ConfirmRelationshipRoute(route);
            if (Interlocked.Increment(ref arrivals) == 2)
                ready.TrySetResult();
            await ready.Task.WaitAsync(timeout.Token);
            Assert.Equal(candidate.TenantId, scope.CurrentTenantId);
            scope.RequireRelationshipRecipient(route.TenantId, route.RelationshipId, route.BindingId, route.SenderHash);
            var other = candidate == first ? second : first;
            Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
                scope.RequireRelationshipRecipient(other.TenantId, route.RelationshipId, other.BindingId, route.SenderHash));
        }
        await Task.WhenAll(Task.Run(() => Run(first)), Task.Run(() => Run(second)));
        Assert.Null(scope.CurrentTenantId);
        Assert.Null(scope.ServiceTenantId);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task RoutingEntryDeniesMissingScopeAndNonPostgresWithoutInvokingWork(bool activeScope)
    {
        var authority = Authority();
        var gate = new Gate(authority);
        var scope = new WhatsAppTenantExecutionScope(gate, TimeProvider.System);
        var relationships = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var conversations = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        var identities = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var candidate = Candidate(authority);
        await using (var seed = relationships.CreateDbContext())
        {
            seed.Add(candidate);
            await seed.SaveChangesAsync();
        }
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(
            new Dictionary<string, string?> { ["IdentityBrokerRead:ActorIssuer"] = "https://identity.test" }
        ).Build();
        var routing = new WhatsAppRelationshipRouting(
            relationships, conversations, IdentityTestHelpers.CreateService(identities),
            scope, gate, configuration, TimeProvider.System);
        var called = false;
        using var service = activeScope ? scope.Begin() : null;
        Task<int> Execute() => routing.ExecuteOrdinaryDatabaseWorkAsync(
            candidate.SenderHash, (_, _, _) =>
            {
                called = true;
                return Task.FromResult(1);
            }, CancellationToken.None);
        if (activeScope)
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(Execute);
        else
            await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(Execute);
        Assert.False(called);
        Assert.Equal(activeScope ? authority.TenantId : (Guid?)null, scope.CurrentTenantId);
        Assert.Null(scope.DatabaseTenantOverrideId);
    }

    private static WhatsAppActivationAuthority Authority() => new()
    {
        TenantId = Guid.NewGuid(), Environment = "test", ActivationReference = "original",
        RecipientBindingDigest = new string('a', 64),
    };

    private static WhatsAppRelationshipRoute Candidate(WhatsAppActivationAuthority authority) => new()
    {
        ServiceTenantId = authority.TenantId, TenantId = Guid.NewGuid(), BindingId = Guid.NewGuid(),
        ActorId = Guid.NewGuid(), SenderHash = authority.RecipientBindingDigest,
    };

    private static WhatsAppCurrentRelationshipRoute Route(WhatsAppRelationshipRoute candidate, string environment) =>
        new(candidate.ServiceTenantId, environment, candidate.SenderHash, candidate.TenantId,
            candidate.BindingId, Guid.NewGuid(), candidate.ActorId, "EMPLOYER", Guid.NewGuid(), 1);

    private sealed class Gate(WhatsAppActivationAuthority authority) : IWhatsAppCapabilityGate
    {
        public WhatsAppActivationAuthority Authority { get; set; } = authority;
        public bool DenyRecipient { get; set; }
        public System.Collections.Concurrent.ConcurrentQueue<Guid> RecipientTenants { get; } = new();
        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");
        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) => Authority;
        public void RequireRecipient(Guid tenantId, string digest, DateTimeOffset now)
        {
            RecipientTenants.Enqueue(tenantId);
            if (DenyRecipient || tenantId != Authority.TenantId || digest != Authority.RecipientBindingDigest)
                throw new WhatsAppCapabilityUnavailableException("RECIPIENT_DENIED");
        }
    }
}
