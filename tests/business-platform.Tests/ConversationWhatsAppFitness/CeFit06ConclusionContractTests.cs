using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit06ConclusionContractTests
{
    [Fact]
    public async Task MaterialConversation_RequiresConclusionFieldsOrTypedContinuation_AndRejectsFalseSuccess()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var invalid = Contribution() with
        {
            DialogueAct = "CONCLUDE",
            Conclusion = null,
            ContinuationReason = null,
        };
        await Assert.ThrowsAsync<ConversationRequestException>(() =>
            context
                .Outbound()
                .CommitAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    invalid,
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );

        var continuation = invalid with
        {
            IdempotencyKey = Guid.NewGuid(),
            ContinuationReason = "AWAITING_OWNER_RESULT",
        };
        var accepted = await context
            .Outbound()
            .CommitAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                continuation,
                DateTimeOffset.UtcNow,
                CancellationToken.None
            );
        Assert.Equal(1, accepted.Sequence);
    }

    [Fact]
    public async Task CompleteConclusionAndWhatsAppEligibilityQueueExactlyOnce()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        var contribution = Contribution() with
        {
            DialogueAct = "CONCLUDE",
            Conclusion = new(
                "understanding",
                "analysis",
                "recommendation",
                "accepted",
                "next",
                Array.Empty<string>(),
                "RECORDED"
            ),
            PublishToWhatsApp = true,
            WhatsAppEligibility = new(
                true,
                false,
                false,
                now.AddMinutes(-1),
                "CUSTOMER_REQUEST",
                new string('a', 64),
                null,
                null,
                null,
                null,
                false
            ),
        };
        var first = await context
            .Outbound()
            .CommitAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                contribution,
                now,
                CancellationToken.None
            );
        var replay = await context
            .Outbound()
            .CommitAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                contribution,
                now,
                CancellationToken.None
            );

        Assert.True(first.WhatsAppQueued);
        Assert.True(replay.Replayed);
        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            context
                .Outbound()
                .CommitAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    contribution with
                    {
                        Content = "different",
                    },
                    now,
                    CancellationToken.None
                )
        );
    }

    [Fact]
    public async Task InvalidOutboundFieldsAndEligibilityAreRejectedBeforeMutation()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        var valid = Contribution();
        var invalid = new[]
        {
            valid with
            {
                ActorKind = "CUSTOMER",
            },
            valid with
            {
                ContributionKind = "UNKNOWN",
            },
            valid with
            {
                DialogueAct = "UNKNOWN",
            },
            valid with
            {
                Content = "",
            },
            valid with
            {
                Content = new string('x', 32_001),
            },
            valid with
            {
                ContextKey = "",
            },
            valid with
            {
                ContextVersion = "",
            },
            valid with
            {
                PayloadReference = "",
            },
            valid with
            {
                PayloadDigest = "bad",
            },
        };
        foreach (var contribution in invalid)
        {
            await Assert.ThrowsAsync<ConversationRequestException>(() =>
                context
                    .Outbound()
                    .CommitAsync(
                        context.TenantId,
                        context.ParticipantId,
                        context.RelationshipId,
                        contribution,
                        now,
                        CancellationToken.None
                    )
            );
        }

        var eligibility = new WhatsAppOutboundEligibility(
            true,
            false,
            false,
            now.AddDays(-2),
            "CUSTOMER_REQUEST",
            new string('a', 64),
            null,
            null,
            null,
            null,
            false
        );
        await Assert.ThrowsAsync<ConversationStateConflictException>(() =>
            context
                .Outbound()
                .CommitAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    valid with
                    {
                        IdempotencyKey = Guid.NewGuid(),
                        PublishToWhatsApp = true,
                        WhatsAppEligibility = eligibility,
                    },
                    now,
                    CancellationToken.None
                )
        );
    }

    private static OutboundConversationContributionV1 Contribution() =>
        new(
            "PROFESSIONAL",
            "TEXT",
            "INFORM",
            "Material result",
            "INDUCTION",
            "workspace-1",
            "WEB",
            Guid.NewGuid(),
            Guid.NewGuid().ToString("D"),
            new string('e', 64),
            false,
            null
        );
}
