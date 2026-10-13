using System.Text.Json;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit14TelemetryLeakageTests
{
    [Fact]
    public async Task SuccessFailureRetryScannerAndTracePaths_ContainZeroProhibitedTelemetryOrDeadLetterData()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        await using (var db = context.Conversations.CreateDbContext())
        {
            db.OperationalSignals.AddRange(
                new ConversationOperationalSignal
                {
                    Environment = context.Options.Environment,
                    Category = "MEDIA",
                    Code = "MEDIA_REJECTED",
                    OccurredAt = DateTimeOffset.UtcNow,
                },
                new ConversationOperationalSignal
                {
                    Environment = context.Options.Environment,
                    Category = "DEAD_LETTER",
                    Code = "ATTEMPT_LIMIT_REACHED",
                    OccurredAt = DateTimeOffset.UtcNow,
                }
            );
            await db.SaveChangesAsync();
        }

        await using var read = context.Conversations.CreateDbContext();
        var serialized = JsonSerializer.Serialize(read.OperationalSignals.ToList());
        foreach (
            var prohibited in new[]
            {
                context.TenantId.ToString("D"),
                context.RelationshipId.ToString("D"),
                "provider_reference",
                "phone",
                "payload",
                "signature",
                "transcript",
                "template_variable",
            }
        )
            Assert.DoesNotContain(prohibited, serialized, StringComparison.OrdinalIgnoreCase);

        var allowedProperties = new[]
        {
            "SignalId",
            "Environment",
            "Category",
            "Code",
            "State",
            "OccurredAt",
            "ResolvedAt",
        };
        Assert.All(
            typeof(ConversationOperationalSignal).GetProperties(),
            property => Assert.Contains(property.Name, allowedProperties)
        );
    }
}
