using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class ConversationContextProfileBoundaryTests
{
    [Fact]
    public async Task ContextCorrectionsAndDataRightsEnforceVersionAndIdempotency()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var observation = new ConversationContextObservation
        {
            Environment = context.Options.Environment,
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            Owner = "CUSTOMER",
            SubjectType = "RELATIONSHIP",
            ObservationType = "PREFERENCE",
            SourceType = "CUSTOMER",
            SourceVersion = "profile:1",
            ValueJson = JsonSerializer.Serialize("original"),
            SourceReference = "test",
            SourceDigest = new string('a', 64),
            Revision = 1,
        };
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.ContextObservations.Add(observation);
            await db.SaveChangesAsync();
        }

        var disputed = await context.Profiles.CorrectAsync(
            context.Options.Environment,
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            new(observation.ObservationId, "DISPUTE", null, "not mine", 1, new string('b', 64)),
            CancellationToken.None
        );
        Assert.Equal("DISPUTED", disputed.Status);
        var erased = await context.Profiles.CorrectAsync(
            context.Options.Environment,
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            new(disputed.ObservationId, "ERASE", null, "erase", 2, new string('c', 64)),
            CancellationToken.None
        );
        Assert.Equal("ERASED", erased.Status);
        await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            context.Profiles.CorrectAsync(
                context.Options.Environment,
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                new(erased.ObservationId, "ERASE", null, null, 1, new string('d', 64)),
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            context.Profiles.CorrectAsync(
                context.Options.Environment,
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                new(Guid.NewGuid(), "ERASE", null, null, 3, new string('e', 64)),
                CancellationToken.None
            )
        );

        var key = Guid.NewGuid();
        var request = new RequestConversationDataRightV1(
            "EXPORT",
            "ALL_ELIGIBLE",
            "assurance",
            null,
            new string('f', 64)
        );
        var first = await context.Profiles.RequestDataRightAsync(
            context.Options.Environment,
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            request,
            CancellationToken.None
        );
        var replay = await context.Profiles.RequestDataRightAsync(
            context.Options.Environment,
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            key,
            request,
            CancellationToken.None
        );
        Assert.Equal(first.OperationId, replay.OperationId);
        await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            context.Profiles.RequestDataRightAsync(
                context.Options.Environment,
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                key,
                request with
                {
                    Reason = "different",
                },
                CancellationToken.None
            )
        );

        var invalid = new[]
        {
            request with
            {
                RightType = "INVALID",
            },
            request with
            {
                Scope = "INVALID",
            },
            request with
            {
                AssuranceReference = "",
            },
            request with
            {
                AssuranceReference = new string('x', 257),
            },
            request with
            {
                Reason = new string('x', 1001),
            },
            request with
            {
                PayloadDigest = "bad",
            },
        };
        foreach (var value in invalid)
        {
            await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
                context.Profiles.RequestDataRightAsync(
                    context.Options.Environment,
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    Guid.NewGuid(),
                    value,
                    CancellationToken.None
                )
            );
        }
    }

    [Fact]
    public async Task ContextAndMessageStateBoundariesCoverEveryPublicMapping()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            context.Profiles.GetCanonicalAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                -1,
                0,
                CancellationToken.None
            )
        );
        Assert.True(
            await context.Profiles.IsCurrentContextVersionAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                "workspace-1",
                CancellationToken.None
            )
        );
        Assert.False(
            await context.Profiles.IsCurrentContextVersionAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                "stale",
                CancellationToken.None
            )
        );

        var conversationId = await context.SeedConversationAsync(("WEB", "state"));
        var deliveryStates = new[]
        {
            "QUEUED",
            "SUBMITTED",
            "PROVIDER_ACCEPTED",
            "DELIVERED",
            "READ",
            "FAILED",
            "EXPIRED",
            "UNRESOLVED",
            "OTHER",
        };
        var processingStates = new[]
        {
            "QUEUED",
            "RUNNING",
            "COMPLETED",
            "FAILED",
            "CANCELLED",
            "STOPPED",
            "OTHER",
            "QUEUED",
            "RUNNING",
        };
        var evidenceStates = new[]
        {
            "RECORDED",
            "BUFFERED_CE_UNAVAILABLE",
            "FAILED",
            "OTHER",
            "RECORDED",
            "BUFFERED_CE_UNAVAILABLE",
            "FAILED",
            "OTHER",
            "RECORDED",
        };
        var messageIds = new List<Guid>();
        await using (var db = context.Conversations.CreateDbContext())
        {
            for (var index = 0; index < deliveryStates.Length; index++)
            {
                var message = new ConversationMessage
                {
                    Environment = context.Options.Environment,
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    ConversationId = conversationId,
                    Sequence = index + 10,
                    DeliveryState = deliveryStates[index],
                    ProcessingState = processingStates[index],
                    EvidenceState = evidenceStates[index],
                };
                db.Messages.Add(message);
                messageIds.Add(message.MessageId);
            }
            await db.SaveChangesAsync();
        }
        foreach (var messageId in messageIds)
        {
            await context.Profiles.GetMessageStatesAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                messageId,
                CancellationToken.None
            );
        }

        context.Options.PolicyVersion = "";
        await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            context.Profiles.ResolveAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                conversationId,
                "INDUCTION",
                "workspace-1",
                "WEB",
                CancellationToken.None
            )
        );
    }
}
