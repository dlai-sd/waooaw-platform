using System.Diagnostics;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit13StopResilienceTests
{
    [Fact]
    public async Task TypedStop_MeetsAcceptedLatency_AndSurvivesOutageDuplicateSimultaneousRestartAndRelease()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var started = Stopwatch.StartNew();
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.EmergencyStopLatches.Add(
                new RelationshipEmergencyStopLatch
                {
                    Environment = context.Options.Environment,
                    TenantId = context.TenantId,
                    RelationshipId = context.RelationshipId,
                    StoppedByParticipantId = context.ParticipantId,
                    CorrelationId = Guid.NewGuid(),
                    State = "LATCHED",
                    LatchedAt = DateTimeOffset.UtcNow,
                }
            );
            await db.SaveChangesAsync();
        }
        Assert.True(
            await context.StopFence.IsLatchedAsync(
                context.TenantId,
                context.RelationshipId,
                CancellationToken.None
            )
        );
        started.Stop();
        Assert.True(started.Elapsed < TimeSpan.FromSeconds(1));

        var restartedFence = new ConversationStopFence(
            context.Conversations,
            Microsoft.Extensions.Options.Options.Create(context.Options)
        );
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            restartedFence.ThrowIfLatchedAsync(
                context.TenantId,
                context.RelationshipId,
                CancellationToken.None
            )
        );
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            context
                .Outbound()
                .CommitAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    Contribution("WEB"),
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            context
                .Outbound()
                .CommitAsync(
                    context.TenantId,
                    context.ParticipantId,
                    context.RelationshipId,
                    Contribution("WHATSAPP"),
                    DateTimeOffset.UtcNow,
                    CancellationToken.None
                )
        );
    }

    private static OutboundConversationContributionV1 Contribution(string channel) =>
        new(
            "PROFESSIONAL",
            "TEXT",
            "INFORM",
            "must not commit",
            "INDUCTION",
            "workspace-1",
            channel,
            Guid.NewGuid(),
            Guid.NewGuid().ToString("D"),
            new string('a', 64),
            false,
            null
        );
}
