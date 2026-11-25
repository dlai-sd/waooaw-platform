// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R005, WC171-R006, WC171-R007
// Constitutional basis: C-001, C-005, C-007, C-023, C-049, C-059, C-063
// IB: IB-171

namespace Waooaw.BusinessPlatform.Services.Alerts;

public static class AlertClasses
{
    public const string Floor = "FLOOR";
    public const string ActionRequired = "ACTION_REQUIRED";
    public const string AtRisk = "AT_RISK";
    public const string Information = "INFORMATION";
    public const string Operations = "OPERATIONS";

    public static readonly IReadOnlyList<string> All =
    [
        Floor,
        ActionRequired,
        AtRisk,
        Information,
        Operations,
    ];

    /// <summary>Higher is more material. A later event of a higher class may escalate an earlier one, never the reverse.</summary>
    public static int Rank(string alertClass) =>
        alertClass switch
        {
            Floor => 4,
            ActionRequired => 3,
            AtRisk => 2,
            Information => 1,
            _ => 0,
        };
}

public static class AlertSources
{
    public const string AgentDeclared = "AGENT_DECLARED";
    public const string BillingThreshold = "BILLING_THRESHOLD";
    public const string Operations = "OPERATIONS";
    public const string SpendDiscrepancy = "SPEND_DISCREPANCY";
    public const string EmergencyStop = "EMERGENCY_STOP";

    public static readonly IReadOnlyList<string> All =
    [
        AgentDeclared,
        BillingThreshold,
        Operations,
        SpendDiscrepancy,
        EmergencyStop,
    ];
}

public static class AlertChannels
{
    public const string Portal = "portal";
    public const string WhatsAppText = "whatsapp_text";
    public const string OperatorPage = "operator_page";
}

public sealed record EscalationStep(TimeSpan After, string Action);

public sealed record AlertClassRule(
    string Class,
    IReadOnlySet<string> Channels,
    bool CountsAgainstAllowance,
    bool Mutable,
    bool BypassQuietHours,
    IReadOnlyList<EscalationStep> Ladder
);

/// <summary>What happened, in policy terms. The producer states the source and its own severity; the policy decides the rest.</summary>
public sealed record AlertEvent(
    string Source,
    Guid? TenantId,
    Guid? RelationshipId,
    string Signal,
    string Severity,
    string Period,
    string DueMeaning,
    string Category = "GENERAL",
    string DestinationSurface = "ALERTS",
    string? DestinationSubjectId = null
);

public static class WhatsAppDecisions
{
    public const string Send = "SEND";
    public const string SendUncounted = "SEND_UNCOUNTED";
    public const string GateClosed = "PORTAL_ONLY_GATE_CLOSED";
    public const string ClassNotEligible = "PORTAL_ONLY_CLASS";
    public const string NoConsent = "PORTAL_ONLY_NO_CONSENT";
    public const string StopReceived = "PORTAL_ONLY_STOP_RECEIVED";
    public const string QuietHours = "PORTAL_ONLY_QUIET_HOURS";
    public const string Muted = "PORTAL_ONLY_MUTED";
    public const string AllowanceExhausted = "PORTAL_ONLY_ALLOWANCE_EXHAUSTED";
    public const string AllowanceUnavailable = "PORTAL_ONLY_ALLOWANCE_UNAVAILABLE";
    public const string SenderUnavailable = "PORTAL_ONLY_SENDER_UNAVAILABLE";
}

/// <summary>Facts the policy needs to decide a proactive WhatsApp message; the caller reads them from their owners.</summary>
public sealed record DeliveryFacts(
    bool ProactiveGateOpen,
    bool WhatsAppConsent,
    bool StopReceived,
    bool CategoryMuted,
    TimeSpan LocalTimeOfDay
);

/// <summary>
/// The one alert policy (PG-24): which class an event is, which channels the class may use, how it is deduplicated,
/// how it escalates, and which classes are uncounted floor alerts. Pure and deterministic; every alert source is
/// classified here, so one material event gives one primary message and an agent cannot declare a class or channel
/// the policy does not allow.
/// </summary>
public static class AlertPolicy
{
    public const string Version = "1.0";

    private static readonly TimeSpan QuietStart = TimeSpan.FromHours(23);
    private static readonly TimeSpan QuietEnd = TimeSpan.FromHours(6);

    private static IReadOnlySet<string> Set(params string[] values) =>
        new HashSet<string>(values, StringComparer.Ordinal);

    public static readonly IReadOnlyDictionary<string, AlertClassRule> Rules = new Dictionary<
        string,
        AlertClassRule
    >(StringComparer.Ordinal)
    {
        [AlertClasses.Floor] = new(
            AlertClasses.Floor,
            Set(AlertChannels.Portal, AlertChannels.WhatsAppText),
            CountsAgainstAllowance: false,
            Mutable: false,
            BypassQuietHours: true,
            [
                new(TimeSpan.Zero, "PORTAL_AND_WHATSAPP"),
                new(TimeSpan.FromMinutes(5), "REPEAT_WHATSAPP"),
                new(TimeSpan.FromMinutes(15), "OPERATOR_PAGE"),
            ]
        ),
        [AlertClasses.ActionRequired] = new(
            AlertClasses.ActionRequired,
            Set(AlertChannels.Portal, AlertChannels.WhatsAppText),
            CountsAgainstAllowance: true,
            Mutable: false,
            BypassQuietHours: false,
            [
                new(TimeSpan.Zero, "PORTAL_AND_WHATSAPP"),
                new(TimeSpan.FromHours(24), "REMIND_IN_PORTAL"),
                new(TimeSpan.FromHours(72), "OPERATOR_REVIEW"),
            ]
        ),
        [AlertClasses.AtRisk] = new(
            AlertClasses.AtRisk,
            Set(AlertChannels.Portal, AlertChannels.WhatsAppText),
            CountsAgainstAllowance: true,
            Mutable: true,
            BypassQuietHours: false,
            [
                new(TimeSpan.Zero, "PORTAL_AND_WHATSAPP"),
                new(TimeSpan.FromHours(72), "REMIND_IN_PORTAL"),
            ]
        ),
        [AlertClasses.Information] = new(
            AlertClasses.Information,
            Set(AlertChannels.Portal),
            CountsAgainstAllowance: false,
            Mutable: true,
            BypassQuietHours: false,
            [new(TimeSpan.Zero, "PORTAL")]
        ),
        [AlertClasses.Operations] = new(
            AlertClasses.Operations,
            Set(AlertChannels.OperatorPage),
            CountsAgainstAllowance: false,
            Mutable: false,
            BypassQuietHours: true,
            [
                new(TimeSpan.Zero, "OPERATOR_PAGE"),
                new(TimeSpan.FromMinutes(15), "OPERATOR_PAGE"),
                new(TimeSpan.FromMinutes(30), "OPERATOR_PAGE"),
            ]
        ),
    };

    /// <summary>The event families that must collapse into one message: two sources about the same underlying problem.</summary>
    private static string Family(AlertEvent alert) =>
        alert.Source is AlertSources.BillingThreshold or AlertSources.SpendDiscrepancy
            ? "SPEND_RISK"
            : alert.Signal;

    public static string Classify(AlertEvent alert) =>
        alert.Source switch
        {
            AlertSources.EmergencyStop => AlertClasses.Floor,
            AlertSources.Operations => AlertClasses.Operations,
            AlertSources.SpendDiscrepancy => AlertClasses.ActionRequired,
            AlertSources.BillingThreshold or AlertSources.AgentDeclared => alert.Severity switch
            {
                "CRITICAL" or "HIGH" => AlertClasses.ActionRequired,
                "WARNING" or "MEDIUM" => AlertClasses.AtRisk,
                _ => AlertClasses.Information,
            },
            _ => throw new ArgumentException("Unknown alert source.", nameof(alert)),
        };

    /// <summary>One key per (tenant, relationship, family, period): the same problem seen by two sources is one alert.</summary>
    public static string DedupKey(AlertEvent alert) =>
        string.Join(
            ':',
            alert.TenantId?.ToString("N") ?? "platform",
            alert.RelationshipId?.ToString("N") ?? "-",
            Family(alert),
            alert.Period
        );

    /// <summary>An event of a strictly higher class than the one already raised may escalate it once; nothing else is a second message.</summary>
    public static bool Escalates(string existingClass, string incomingClass) =>
        AlertClasses.Rank(incomingClass) > AlertClasses.Rank(existingClass);

    public static string EscalatedKey(string dedupKey, string incomingClass) =>
        $"{dedupKey}:{incomingClass}";

    public static bool IsMutable(string alertClass) =>
        Rules.TryGetValue(alertClass, out var rule) && rule.Mutable;

    /// <summary>Categories whose alerts are floor alerts (Emergency Stop, authority and safety). A mute for one is refused.</summary>
    public static readonly IReadOnlySet<string> FloorCategories = Set(
        "EMERGENCY_STOP",
        "AUTHORITY",
        "SAFETY"
    );

    public static bool IsValidCategory(string category) =>
        category.Length is >= 3 and <= 40
        && char.IsAsciiLetterUpper(category[0])
        && category.All(character =>
            char.IsAsciiLetterUpper(character) || char.IsAsciiDigit(character) || character == '_'
        );

    /// <summary>Why an agent's alert declaration is refused: a class or a channel the policy does not allow.</summary>
    private static readonly IReadOnlyDictionary<string, string> ChannelAliases = new Dictionary<
        string,
        string
    >(StringComparer.Ordinal)
    {
        ["web"] = AlertChannels.Portal,
        ["whatsapp"] = AlertChannels.WhatsAppText,
    };

    private static readonly IReadOnlySet<string> DeclarableSeverities = Set(
        "INFO",
        "LOW",
        "WARNING",
        "MEDIUM",
        "HIGH",
        "CRITICAL"
    );

    public static IReadOnlyList<string> ValidateDeclaration(
        string severity,
        IReadOnlyList<string> channels
    )
    {
        var violations = new List<string>();
        var alertClass = Classify(
            new AlertEvent(AlertSources.AgentDeclared, null, null, "DECLARED", severity, "-", "-")
        );
        var allowed = Rules[alertClass].Channels;
        if (severity.Length > 0 && !DeclarableSeverities.Contains(severity))
            violations.Add("ALERT_SEVERITY_NOT_ALLOWED");
        violations.AddRange(
            channels
                .Select(channel => ChannelAliases.GetValueOrDefault(channel, channel))
                .Where(channel => !allowed.Contains(channel))
                .Select(channel => $"ALERT_CHANNEL_NOT_ALLOWED:{channel}")
        );
        return violations;
    }

    public static bool InQuietHours(TimeSpan timeOfDay) =>
        timeOfDay >= QuietStart || timeOfDay < QuietEnd;

    /// <summary>Whether a proactive WhatsApp message may go now. The portal is always written; this only decides the second channel.</summary>
    public static string DecideWhatsApp(string alertClass, DeliveryFacts facts)
    {
        var rule = Rules[alertClass];
        if (!rule.Channels.Contains(AlertChannels.WhatsAppText))
            return WhatsAppDecisions.ClassNotEligible;
        if (facts.StopReceived)
            return WhatsAppDecisions.StopReceived;
        if (!facts.WhatsAppConsent)
            return WhatsAppDecisions.NoConsent;
        if (!facts.ProactiveGateOpen)
            return WhatsAppDecisions.GateClosed;
        if (rule.Mutable && facts.CategoryMuted)
            return WhatsAppDecisions.Muted;
        if (!rule.BypassQuietHours && InQuietHours(facts.LocalTimeOfDay))
            return WhatsAppDecisions.QuietHours;
        return rule.CountsAgainstAllowance
            ? WhatsAppDecisions.Send
            : WhatsAppDecisions.SendUncounted;
    }
}
