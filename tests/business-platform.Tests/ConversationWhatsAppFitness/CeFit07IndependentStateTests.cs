using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit07IndependentStateTests
{
    [Fact]
    public async Task TransportExecutionDecisionAndEvidence_TransitionIndependently_WithoutSyntheticSuccess()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await context.SeedConversationAsync(("WHATSAPP", "status test"));
        Guid messageId;
        await using (var db = context.Conversations.CreateDbContext())
        {
            var message = db.Messages.Single();
            message.DeliveryState = "DELIVERED";
            message.ProcessingState = "RUNNING";
            message.EvidenceState = "PENDING";
            messageId = message.MessageId;
            await db.SaveChangesAsync();
        }

        var states = await context.Profiles.GetMessageStatesAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            messageId,
            CancellationToken.None
        );

        Assert.Equal("DELIVERED", states.Delivery);
        Assert.Equal("RUNNING", states.Execution);
        Assert.Equal("NOT_REQUIRED", states.CustomerDecision);
        Assert.Equal("PENDING", states.ConstitutionalEvidence);
    }
}
