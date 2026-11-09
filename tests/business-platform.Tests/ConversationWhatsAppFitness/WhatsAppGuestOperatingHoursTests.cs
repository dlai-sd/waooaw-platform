// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R008
// constitutional_basis: C-023, C-026, C-059, C-063

using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppGuestOperatingHoursTests
{
    [Theory]
    [InlineData("2026-11-06T03:29:59+00:00", false)]
    [InlineData("2026-11-06T03:30:00+00:00", true)]
    [InlineData("2026-11-06T15:29:59+00:00", true)]
    [InlineData("2026-11-06T15:30:00+00:00", false)]
    public void IsOpenUsesTheDailyIstWindow(string instant, bool expected)
    {
        Assert.Equal(expected, WhatsAppGuestOperatingHours.IsOpen(DateTimeOffset.Parse(instant)));
    }
}
