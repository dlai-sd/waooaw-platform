using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit04SemanticEquivalenceTests
{
    [Fact]
    public async Task ConfirmedContextAndPolicy_ProduceEquivalentWebAndWhatsAppRecommendations()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var conversationId = Guid.NewGuid();
        var web = await context.Profiles.ResolveAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            conversationId,
            "INDUCTION",
            "workspace-1",
            "WEB",
            CancellationToken.None
        );
        var whatsApp = await context.Profiles.ResolveAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            conversationId,
            "INDUCTION",
            "workspace-1",
            "WHATSAPP",
            CancellationToken.None
        );

        Assert.Equal(web.Context.Phase, whatsApp.Context.Phase);
        Assert.Equal(web.Context.DecisionSpaceVersion, whatsApp.Context.DecisionSpaceVersion);
        Assert.Equal(web.Context.SourceVersions, whatsApp.Context.SourceVersions);
        Assert.Equal(web.Policy.Version, whatsApp.Policy.Version);
        Assert.Equal(web.Policy.InteractionPolicyVersion, whatsApp.Policy.InteractionPolicyVersion);
        Assert.NotEqual(web.Context.ContextId, whatsApp.Context.ContextId);
    }
}
