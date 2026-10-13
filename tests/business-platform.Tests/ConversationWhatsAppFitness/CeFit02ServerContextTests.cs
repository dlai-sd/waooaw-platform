using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit02ServerContextTests
{
    [Fact]
    public async Task RegisteredContext_UsesAuthenticatedCurrentServerState_AndRejectsForgedUnknownCrossSubjectReferences()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var conversationId = Guid.NewGuid();
        var resolved = await context.Profiles.ResolveAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            conversationId,
            "INDUCTION",
            "workspace-1",
            "WEB",
            CancellationToken.None
        );

        Assert.Equal(context.RelationshipId, resolved.Context.RelationshipId);
        Assert.Equal(conversationId, resolved.Context.ConversationId);
        Assert.Equal("INDUCTION", resolved.Context.Phase);
        Assert.DoesNotContain(
            resolved.Context.SourceVersions,
            value => value.SourceReference == Guid.NewGuid().ToString("D")
        );

        await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            context.Profiles.ResolveAsync(
                context.TenantId,
                Guid.NewGuid(),
                context.RelationshipId,
                conversationId,
                "FORGED_CONTEXT",
                "workspace-1",
                "WEB",
                CancellationToken.None
            )
        );
    }
}
