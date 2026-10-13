using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class CeFit10EligibilityTests
{
    [Fact]
    public async Task ConsentWindowAndTemplateMatrix_IsDeterministic_AndIneligibleCasesDispatchZero()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var now = DateTimeOffset.UtcNow;
        var cases = new[]
        {
            Eligible(now) with
            {
                OptedIn = false,
            },
            Eligible(now) with
            {
                OptedOut = true,
            },
            Eligible(now) with
            {
                RelationshipStopped = true,
            },
            Eligible(now) with
            {
                LastInboundAt = now.AddHours(-24).AddMilliseconds(-1),
            },
            Eligible(now) with
            {
                LastInboundAt = null,
                TemplateName = "unapproved",
                TemplateVersion = "1",
                TemplateLocale = "en_IN",
                TemplateCategory = "UTILITY",
                TemplateApproved = false,
            },
        };
        foreach (var eligibility in cases)
        {
            var result = await context
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
                    eligibility,
                    now,
                    CancellationToken.None
                );
            Assert.Null(result);
        }

        var accepted = await context
            .Outbox()
            .QueueAsync(
                context.TenantId,
                context.RelationshipId,
                Guid.NewGuid(),
                1,
                Guid.NewGuid().ToString("D"),
                Guid.NewGuid(),
                new string('b', 64),
                Guid.NewGuid().ToString("D"),
                Eligible(now),
                now,
                CancellationToken.None
            );
        Assert.NotNull(accepted);
        await using var db = context.Conversations.CreateDbContext();
        Assert.Single(db.ConversationOutbox);
    }

    private static WhatsAppOutboundEligibility Eligible(DateTimeOffset now) =>
        new(
            true,
            false,
            false,
            now.AddHours(-24),
            "CUSTOMER_REQUEST",
            new string('c', 64),
            null,
            null,
            null,
            null,
            false
        );
}
