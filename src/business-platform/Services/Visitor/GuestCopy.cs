// Implements: work-contracts/WC-135-visitor-conversation-and-simulated-customers.md WC135-R005, WC135-R006, WC135-R009
// Constitutional basis: C-009, C-023, C-026, C-048, C-049, C-059, C-063

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.Visitor;

/// <summary>
/// The consent, notice and opening-hours text the WhatsApp guest session uses. LEGACY keeps the exact texts that
/// shipped with WC-134; V2 takes them from the scripted content set (Conversation Policy layers).
/// </summary>
public sealed record GuestCopy(
    string NoticeVersion,
    string Notice,
    string Accepted,
    string RegisteredNumberAccepted,
    string RenewalUnavailable,
    string ClosedNotice,
    string UnsupportedContent,
    string StopAcknowledged,
    string ResumeNotice,
    string YesLabel,
    string StopLabel,
    VisitorHoursContent Hours,
    bool IsV2
)
{
    public static readonly GuestCopy Legacy = new(
        WhatsAppGuestConsent.NoticeVersion,
        WhatsAppGuestConsent.Notice,
        WhatsAppGuestConsent.Accepted,
        WhatsAppGuestConsent.RegisteredNumberAccepted,
        WhatsAppGuestConsent.RenewalUnavailable,
        WhatsAppGuestOperatingHours.ClosedNotice,
        WhatsAppGuestTrafficBudget.UnsupportedContentNotice,
        string.Empty,
        string.Empty,
        "YES",
        "STOP",
        new VisitorHoursContent("Asia/Kolkata", "09:00", "21:00"),
        false
    );

    public static GuestCopy FromContent(VisitorContentSet content, int retentionDays) =>
        new(
            content.Consent.NoticeVersion,
            VisitorStateMachine.Fill(
                content.Consent.Notice,
                ("retentionDays", retentionDays.ToString())
            ),
            content.Consent.Accepted,
            content.Consent.RegisteredNumberAccepted,
            content.Consent.RenewalUnavailable,
            content.Fixed.ClosedNotice,
            content.Fixed.UnsupportedContent,
            content.Fixed.StopAcknowledged,
            content.Fixed.ResumeNotice,
            content.Consent.YesLabel,
            content.Consent.StopLabel,
            content.Hours,
            true
        );

    /// <summary>Every fixed text the guest flow may send before or outside a consented conversation.</summary>
    public IEnumerable<string> PreConsentTexts() =>
        new[] { Notice, RenewalUnavailable, ClosedNotice, UnsupportedContent, ResumeNotice }.Where(
            text => !string.IsNullOrEmpty(text)
        );
}

/// <summary>
/// Process-wide guest copy, set once at startup. The consent notice version and texts are read from static
/// helpers in several places, so one active set is held here and defaults to the legacy WC-134 copy.
/// </summary>
public static class GuestCopyRegistry
{
    private static volatile GuestCopy _current = GuestCopy.Legacy;

    public static GuestCopy Current => _current;

    public static void Use(GuestCopy copy) => _current = copy;

    public static void Reset() => _current = GuestCopy.Legacy;
}

/// <summary>Applies the scripted content as the guest copy when the visitor conversation is in V2 mode.</summary>
public sealed class VisitorGuestCopyInitializer(
    IVisitorContentProvider contents,
    IOptionsMonitor<VisitorConversationOptions> conversation,
    IOptionsMonitor<VisitorLeadOptions> leads,
    ILogger<VisitorGuestCopyInitializer> logger
) : IHostedService
{
    public Task StartAsync(CancellationToken cancellationToken)
    {
        if (!conversation.CurrentValue.IsV2)
        {
            GuestCopyRegistry.Reset();
            return Task.CompletedTask;
        }
        try
        {
            var content = contents.Get(Guid.Empty);
            GuestCopyRegistry.Use(GuestCopy.FromContent(content, leads.CurrentValue.RetentionDays));
            logger.LogInformation(
                "visitor.guestcopy.active contentVersion={ContentVersion} noticeVersion={NoticeVersion}",
                content.VersionLabel,
                content.Consent.NoticeVersion
            );
        }
        catch (VisitorContentException exception)
        {
            // Fail closed: V2 without valid content must not fall back to hardcoded text.
            logger.LogError("visitor.guestcopy.unavailable reason={Reason}", exception.Reason);
            throw;
        }
        return Task.CompletedTask;
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
