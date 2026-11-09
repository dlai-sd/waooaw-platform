// Implements: work-contracts/WC-134-whatsapp-demo-complete-rollout-work-component.md WC134-R008
// Constitutional basis: C-023, C-026, C-059, C-063

namespace Waooaw.BusinessPlatform.Services;

public static class WhatsAppGuestOperatingHours
{
    private static readonly TimeZoneInfo BusinessTimeZone = TimeZoneInfo.FindSystemTimeZoneById(
        "Asia/Kolkata"
    );
    public const string ClosedNotice =
        "Thanks for messaging WAOOAW Demo. Our guest discovery service is open daily from 09:00 to 21:00 IST. Please message us again during those hours. Reply STOP to stop messages.";

    public static bool IsOpen(DateTimeOffset instant)
    {
        var localTime = TimeZoneInfo.ConvertTime(instant, BusinessTimeZone).TimeOfDay;
        return localTime >= TimeSpan.FromHours(9) && localTime < TimeSpan.FromHours(21);
    }
}
