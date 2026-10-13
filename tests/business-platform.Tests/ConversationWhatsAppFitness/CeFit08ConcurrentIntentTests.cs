using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit08ConcurrentIntentTests
{
    [Fact]
    public async Task ConcurrentWebAndWhatsAppIntent_CommitsOnce_ReplaysPriorOutcome_AndRejectsDivergentReuse()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var idempotencyKey = Guid.NewGuid();
        var contribution = Contribution(idempotencyKey, "protected intent");
        var results = await Task.WhenAll(
            Enumerable
                .Range(0, 256)
                .Select(_ =>
                    context
                        .Outbound()
                        .CommitAsync(
                            context.TenantId,
                            context.ParticipantId,
                            context.RelationshipId,
                            contribution,
                            DateTimeOffset.UtcNow,
                            CancellationToken.None
                        )
                )
        );

        Assert.Single(results.Select(value => value.MessageId).Distinct());
        Assert.Single(results.Select(value => value.Sequence).Distinct());
        Assert.Equal(255, results.Count(value => value.Replayed));
        await using (var db = context.Conversations.CreateDbContext())
        {
            Assert.Single(db.Messages);
            Assert.Single(db.IdempotencyOutcomes);
        }

        await Assert.ThrowsAsync<ConversationIdempotencyConflictException>(() =>
            context
                .Outbound()
                .CommitAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    Contribution(idempotencyKey, "divergent intent"),
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
    }

    private static OutboundConversationContributionV1 Contribution(Guid key, string content) =>
        new(
            "PROFESSIONAL",
            "TEXT",
            "INFORM",
            content,
            "INDUCTION",
            "workspace-1",
            "WEB",
            key,
            Guid.NewGuid().ToString("D"),
            new string('f', 64),
            false,
            null
        );
}
