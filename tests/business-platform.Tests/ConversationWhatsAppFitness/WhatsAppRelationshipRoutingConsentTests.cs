using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppRelationshipRoutingConsentTests
{
    [Theory]
    [InlineData("current")]
    [InlineData("missing")]
    [InlineData("stopped")]
    [InlineData("unadmitted")]
    [InlineData("missing-admission-evidence")]
    [InlineData("missing-consent")]
    [InlineData("missing-consent-evidence")]
    [InlineData("notice-version")]
    [InlineData("future-admission")]
    [InlineData("future-consent")]
    [InlineData("foreign-sender")]
    [InlineData("foreign-tenant")]
    [InlineData("missing-notice-time")]
    [InlineData("missing-notice-message")]
    [InlineData("missing-consent-message")]
    [InlineData("pre-notice-consent")]
    public async Task CustomerRouteCannotBypassSharedGuestConsentOrStop(string change)
    {
        var factory = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
        await using var db = factory.CreateDbContext();
        var tenant = Guid.NewGuid();
        var sender = new string('a', 64);
        var now = DateTimeOffset.UtcNow;
        if (change != "missing")
        {
            db.Add(new WhatsAppGuestSession
            {
                TenantId = tenant, BindingDigest = sender,
                AdmittedAt = change == "unadmitted" ? null
                    : change == "future-admission" ? now.AddMinutes(1) : now.AddMinutes(-1),
                EvidenceId = change == "missing-admission-evidence" ? null : Guid.NewGuid(),
                StoppedAt = change == "stopped" ? now : null,
                ServiceConsentAt = change == "missing-consent" ? null
                    : change == "future-consent" ? now.AddMinutes(1) : now.AddSeconds(-1),
                ServiceConsentEvidenceId = change == "missing-consent-evidence" ? Guid.Empty : Guid.NewGuid(),
                ServiceConsentNoticeVersion = change == "notice-version" ? "old" : WhatsAppGuestConsent.NoticeVersion,
                ServiceConsentNoticeQueuedAt = change == "missing-notice-time" ? null
                    : change == "pre-notice-consent" ? now : now.AddMinutes(-1),
                ServiceConsentNoticeMessageId = change == "missing-notice-message" ? null : Guid.NewGuid(),
                ServiceConsentMessageId = change == "missing-consent-message" ? null : "synthetic-consent",
            });
            await db.SaveChangesAsync();
        }
        Task Require() => WhatsAppRelationshipRouting.RequireGuestConsentAsync(
            db, change == "foreign-tenant" ? Guid.NewGuid() : tenant,
            change == "foreign-sender" ? new string('b', 64) : sender, now, CancellationToken.None);
        if (change == "current")
            await Require();
        else
            await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(Require);
        Assert.Equal(change == "missing" ? 0 : 1, await db.Set<WhatsAppGuestSession>().CountAsync());
    }
}
