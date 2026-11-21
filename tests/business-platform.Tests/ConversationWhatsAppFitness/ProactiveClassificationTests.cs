// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-12
// Constitutional basis: C-059, C-063, C-023

using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class ProactiveClassificationTests
{
    private static readonly DateTimeOffset Now = new(2026, 3, 10, 12, 0, 0, TimeSpan.Zero);

    [Theory]
    [InlineData(-1, false, false, WhatsAppMessageClass.Reply)]
    [InlineData(-1, true, false, WhatsAppMessageClass.Reply)]
    [InlineData(-25, false, false, WhatsAppMessageClass.ProactiveCounted)]
    [InlineData(-25, true, false, WhatsAppMessageClass.ProactiveUncounted)]
    [InlineData(-25, false, true, WhatsAppMessageClass.ProactiveUncounted)]
    public void ClassificationTable(
        int hoursSinceLastInbound,
        bool capacityNotice,
        bool emergencyAlert,
        WhatsAppMessageClass expected
    )
    {
        var classified = WhatsAppMessageClassifier.Classify(
            Now.AddHours(hoursSinceLastInbound),
            Now,
            capacityNotice,
            emergencyAlert
        );
        Assert.Equal(expected, classified);
    }

    [Fact]
    public void NoInboundMessageEverMeansTheWindowIsClosed()
    {
        Assert.Equal(
            WhatsAppMessageClass.ProactiveCounted,
            WhatsAppMessageClassifier.Classify(null, Now)
        );
    }

    [Fact]
    public void TheWindowEndsExactlyTwentyFourHoursAfterTheLastInboundMessage()
    {
        Assert.True(WhatsAppMessageClassifier.InsideServiceWindow(Now.AddHours(-24), Now));
        Assert.False(
            WhatsAppMessageClassifier.InsideServiceWindow(
                Now.AddHours(-24).AddMilliseconds(-1),
                Now
            )
        );
        Assert.False(WhatsAppMessageClassifier.InsideServiceWindow(Now.AddMinutes(1), Now));
    }

    [Fact]
    public async Task ClassifyingAProactiveMessageDoesNotEnableSending()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        var proactive = new WhatsAppOutboundEligibility(
            true,
            false,
            false,
            now.AddHours(-48),
            "CUSTOMER_REQUEST",
            new string('c', 64),
            "agent_alert",
            "1",
            "en_IN",
            "UTILITY",
            true
        );
        Assert.Equal(
            WhatsAppMessageClass.ProactiveCounted,
            WhatsAppMessageClassifier.Classify(proactive.LastInboundAt, now)
        );

        var queued = await context
            .Outbox()
            .QueueAsync(
                context.TenantId,
                context.RelationshipId,
                Guid.NewGuid(),
                1,
                Guid.NewGuid().ToString("D"),
                Guid.NewGuid(),
                new string('a', 64),
                Guid.NewGuid().ToString("D"),
                proactive,
                now,
                CancellationToken.None
            );

        Assert.Null(queued);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Empty(db.ConversationOutbox);
    }
}
