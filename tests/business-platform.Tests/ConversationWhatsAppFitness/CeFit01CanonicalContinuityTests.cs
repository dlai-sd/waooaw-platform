using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit01CanonicalContinuityTests
{
    [Fact]
    public async Task WebWhatsAppWeb_RetainsCanonicalIdentitySequencePlanAndAuthority_WithoutDuplicateConversation()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var conversationId = await context.SeedConversationAsync(
            ("WEB", "start"),
            ("WHATSAPP", "continue"),
            ("WEB", "resume")
        );

        var projection = await context.Profiles.GetCanonicalAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            0,
            100,
            CancellationToken.None
        );

        Assert.Equal(conversationId, projection.ConversationId);
        Assert.Equal(
            new long[] { 1, 2, 3 },
            projection.Messages.Select(value => value.Sequence).ToArray()
        );
        Assert.Single(projection.Messages.Select(value => value.Context.RelationshipId).Distinct());
        await using var db = context.Conversations.CreateDbContext();
        Assert.Single(db.Conversations);
    }
}
