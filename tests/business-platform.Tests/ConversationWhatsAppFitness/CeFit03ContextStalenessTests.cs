using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit03ContextStalenessTests
{
    [Fact]
    public async Task SourceVersionChange_MarksAffectedContextStaleBeforeExecution_AndPreventsCurrentPresentation()
    {
        var context = await Wc120FitnessContext.CreateAsync("workspace-2");
        var error = await Assert.ThrowsAsync<ConversationContextConflictException>(() =>
            context.Profiles.ResolveAsync(
                context.TenantId,
                context.ParticipantId,
                context.RelationshipId,
                Guid.NewGuid(),
                "INDUCTION",
                "workspace-1",
                "WEB",
                CancellationToken.None
            )
        );

        Assert.Equal("CONVERSATION_CONTEXT_STALE", error.Code);
    }
}
