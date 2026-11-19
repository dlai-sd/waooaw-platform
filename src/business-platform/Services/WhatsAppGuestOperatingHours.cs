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
        var hours = Visitor.GuestCopyRegistry.Current.Hours;
        if (
            !TimeSpan.TryParseExact(hours.OpensAt, @"hh\:mm", null, out var opens)
            || !TimeSpan.TryParseExact(hours.ClosesAt, @"hh\:mm", null, out var closes)
        )
            return false;
        var zone =
            hours.TimeZone == "Asia/Kolkata"
                ? BusinessTimeZone
                : TimeZoneInfo.FindSystemTimeZoneById(hours.TimeZone);
        var localTime = TimeZoneInfo.ConvertTime(instant, zone).TimeOfDay;
        return localTime >= opens && localTime < closes;
    }
}
