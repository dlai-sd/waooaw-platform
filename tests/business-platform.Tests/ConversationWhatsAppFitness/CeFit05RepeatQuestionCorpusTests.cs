using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit05RepeatQuestionCorpusTests
{
    [Fact]
    public async Task ApprovedCorpus_ReportsRepeatedConfirmedFacts_WithoutPromotingInference()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.ContextObservations.AddRange(
                Observation(context, "CUSTOMER_GOAL", "CONFIRMED", "local customers", 1),
                Observation(context, "BUDGET_RANGE", "INFERRED", "unknown", 2)
            );
            await db.SaveChangesAsync();
        }

        var profile = await context.Profiles.GetProfileAsync(
            context.TenantId,
            context.ParticipantId,
            context.RelationshipId,
            CancellationToken.None
        );
        var questions = new[] { "Who are your target customers?", "What is your budget?" };
        var violations = questions.Where(question =>
            profile.Items.Any(item =>
                item.Status == "CONFIRMED"
                && question.Contains("target customers", StringComparison.OrdinalIgnoreCase)
                && item.FactType == "CUSTOMER_GOAL"
            )
        );

        Assert.Single(violations);
        Assert.Contains(
            profile.Items,
            value => value.FactType == "BUDGET_RANGE" && value.Status == "INFERRED"
        );
    }

    private static ConversationContextObservation Observation(
        Wc120FitnessContext context,
        string type,
        string status,
        string value,
        long revision
    ) =>
        new()
        {
            Environment = context.Options.Environment,
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            Owner = "BUSINESS_PLATFORM",
            SubjectType = "RELATIONSHIP",
            ObservationType = type,
            Status = status,
            SourceType = "CUSTOMER_CONVERSATION",
            SourceVersion = "1",
            ValueJson = JsonSerializer.Serialize(value),
            SourceReference = $"message-{revision}",
            SourceDigest = new string((char)('a' + revision), 64),
            Revision = revision,
        };
}
