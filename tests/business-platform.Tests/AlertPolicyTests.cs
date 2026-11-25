// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R005, WC171-R006, WC171-R007
// Constitutional basis: C-001, C-005, C-007, C-023, C-049, C-059, C-063, C-076
// IB: IB-171

using Waooaw.BusinessPlatform.Services.Alerts;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AlertPolicyTests
{
    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly Guid Relationship = Guid.NewGuid();

    private static AlertEvent Event(
        string source,
        string severity,
        string signal = "SIGNAL",
        string period = "2026-11"
    ) => new(source, Tenant, Relationship, signal, severity, period, "Something needs you.");

    private static DeliveryFacts Facts(
        bool gate = true,
        bool consent = true,
        bool stop = false,
        bool muted = false,
        int hour = 11
    ) => new(gate, consent, stop, muted, TimeSpan.FromHours(hour));

    [Theory]
    [InlineData(AlertSources.EmergencyStop, "CRITICAL", AlertClasses.Floor)]
    [InlineData(AlertSources.Operations, "HIGH", AlertClasses.Operations)]
    [InlineData(AlertSources.SpendDiscrepancy, "LOW", AlertClasses.ActionRequired)]
    [InlineData(AlertSources.BillingThreshold, "HIGH", AlertClasses.ActionRequired)]
    [InlineData(AlertSources.BillingThreshold, "MEDIUM", AlertClasses.AtRisk)]
    [InlineData(AlertSources.BillingThreshold, "LOW", AlertClasses.Information)]
    [InlineData(AlertSources.AgentDeclared, "CRITICAL", AlertClasses.ActionRequired)]
    [InlineData(AlertSources.AgentDeclared, "WARNING", AlertClasses.AtRisk)]
    [InlineData(AlertSources.AgentDeclared, "INFO", AlertClasses.Information)]
    public void EverySourceIsClassifiedByThePolicy(
        string source,
        string severity,
        string expected
    ) => Assert.Equal(expected, AlertPolicy.Classify(Event(source, severity)));

    [Fact]
    public void AnUnknownSourceIsRefusedNotGuessed() =>
        Assert.Throws<ArgumentException>(() =>
            AlertPolicy.Classify(Event("SOMETHING_NEW", "INFO"))
        );

    [Fact]
    public void AllFiveSourcesAreInTheContract() =>
        Assert.Equal(
            new[]
            {
                "AGENT_DECLARED",
                "BILLING_THRESHOLD",
                "OPERATIONS",
                "SPEND_DISCREPANCY",
                "EMERGENCY_STOP",
            },
            AlertSources.All
        );

    [Fact]
    public void ASpendDiscrepancyAndItsBillingThresholdAreOneAlertNotTwo()
    {
        var threshold = Event(AlertSources.BillingThreshold, "HIGH", "BUDGET_PERCENT_90");
        var discrepancy = Event(AlertSources.SpendDiscrepancy, "HIGH", "SPEND_MISMATCH");

        Assert.Equal(AlertPolicy.DedupKey(threshold), AlertPolicy.DedupKey(discrepancy));
        Assert.False(
            AlertPolicy.Escalates(
                AlertPolicy.Classify(threshold),
                AlertPolicy.Classify(discrepancy)
            )
        );
    }

    [Fact]
    public void ADifferentPeriodOrRelationshipOrTenantIsAnotherAlert()
    {
        var baseline = Event(AlertSources.AgentDeclared, "WARNING");

        Assert.NotEqual(
            AlertPolicy.DedupKey(baseline),
            AlertPolicy.DedupKey(baseline with { Period = "2026-12" })
        );
        Assert.NotEqual(
            AlertPolicy.DedupKey(baseline),
            AlertPolicy.DedupKey(baseline with { RelationshipId = Guid.NewGuid() })
        );
        Assert.NotEqual(
            AlertPolicy.DedupKey(baseline),
            AlertPolicy.DedupKey(baseline with { TenantId = Guid.NewGuid() })
        );
    }

    [Fact]
    public void OnlyAStrictlyMoreMaterialClassMayEscalateAndNeverTheReverse()
    {
        Assert.True(AlertPolicy.Escalates(AlertClasses.AtRisk, AlertClasses.ActionRequired));
        Assert.True(AlertPolicy.Escalates(AlertClasses.ActionRequired, AlertClasses.Floor));
        Assert.False(
            AlertPolicy.Escalates(AlertClasses.ActionRequired, AlertClasses.ActionRequired)
        );
        Assert.False(AlertPolicy.Escalates(AlertClasses.ActionRequired, AlertClasses.AtRisk));
    }

    [Fact]
    public void FloorAlertsAreUncountedUnmutableAndIgnoreQuietHours()
    {
        var floor = AlertPolicy.Rules[AlertClasses.Floor];

        Assert.False(floor.CountsAgainstAllowance);
        Assert.False(floor.Mutable);
        Assert.True(floor.BypassQuietHours);
        Assert.Equal(
            WhatsAppDecisions.SendUncounted,
            AlertPolicy.DecideWhatsApp(AlertClasses.Floor, Facts(muted: true, hour: 2))
        );
    }

    [Theory]
    [InlineData(AlertClasses.Floor, false)]
    [InlineData(AlertClasses.ActionRequired, false)]
    [InlineData(AlertClasses.Operations, false)]
    [InlineData(AlertClasses.AtRisk, true)]
    [InlineData(AlertClasses.Information, true)]
    public void OnlyRoutineClassesCanBeMuted(string alertClass, bool mutable) =>
        Assert.Equal(mutable, AlertPolicy.IsMutable(alertClass));

    [Fact]
    public void TheEscalationLaddersAreDeclaredPerClassWithTimings()
    {
        Assert.Equal(
            new[] { TimeSpan.Zero, TimeSpan.FromMinutes(5), TimeSpan.FromMinutes(15) },
            AlertPolicy.Rules[AlertClasses.Floor].Ladder.Select(step => step.After)
        );
        Assert.Equal(
            new[] { TimeSpan.Zero, TimeSpan.FromMinutes(15), TimeSpan.FromMinutes(30) },
            AlertPolicy.Rules[AlertClasses.Operations].Ladder.Select(step => step.After)
        );
        Assert.All(
            AlertClasses.All,
            alertClass => Assert.NotEmpty(AlertPolicy.Rules[alertClass].Ladder)
        );
    }

    [Fact]
    public void ProactiveSendingIsClosedByDefaultSoTheGateOffGivesPortalOnly() =>
        Assert.Equal(
            WhatsAppDecisions.GateClosed,
            AlertPolicy.DecideWhatsApp(AlertClasses.AtRisk, Facts(gate: false))
        );

    [Theory]
    [InlineData(false, false, WhatsAppDecisions.NoConsent)]
    [InlineData(true, true, WhatsAppDecisions.StopReceived)]
    public void StopAndMissingConsentAreRespectedEvenForFloorAlerts(
        bool consent,
        bool stop,
        string expected
    ) =>
        Assert.Equal(
            expected,
            AlertPolicy.DecideWhatsApp(AlertClasses.Floor, Facts(consent: consent, stop: stop))
        );

    [Fact]
    public void ARoutineAlertWaitsOutQuietHoursAndRespectsAMuteButStillGoesToThePortal()
    {
        Assert.Equal(
            WhatsAppDecisions.QuietHours,
            AlertPolicy.DecideWhatsApp(AlertClasses.AtRisk, Facts(hour: 23))
        );
        Assert.Equal(
            WhatsAppDecisions.QuietHours,
            AlertPolicy.DecideWhatsApp(AlertClasses.ActionRequired, Facts(hour: 5))
        );
        Assert.Equal(
            WhatsAppDecisions.Muted,
            AlertPolicy.DecideWhatsApp(AlertClasses.AtRisk, Facts(muted: true))
        );
        Assert.Equal(
            WhatsAppDecisions.Send,
            AlertPolicy.DecideWhatsApp(AlertClasses.ActionRequired, Facts(muted: true))
        );
    }

    [Fact]
    public void OperationsAlertsGoToOperatorsNeverToACustomerChannel() =>
        Assert.Equal(
            WhatsAppDecisions.ClassNotEligible,
            AlertPolicy.DecideWhatsApp(AlertClasses.Operations, Facts())
        );

    [Theory]
    [InlineData("INFO", "portal", true)]
    [InlineData("INFO", "whatsapp_text", false)]
    [InlineData("WARNING", "whatsapp_text", true)]
    [InlineData("CRITICAL", "sms", false)]
    [InlineData("CRITICAL", "email", false)]
    [InlineData("CRITICAL", "operator_page", false)]
    public void AnAgentMayDeclareOnlyTheChannelsItsClassAllows(
        string severity,
        string channel,
        bool allowed
    ) => Assert.Equal(allowed, AlertPolicy.ValidateDeclaration(severity, [channel]).Count == 0);

    [Fact]
    public void AnAgentCannotDeclareAnUnknownSeverityAndLegacyChannelNamesAreAliases()
    {
        Assert.Contains(
            "ALERT_SEVERITY_NOT_ALLOWED",
            AlertPolicy.ValidateDeclaration("EMERGENCY", ["portal"])
        );
        Assert.Empty(AlertPolicy.ValidateDeclaration("HIGH", ["web", "whatsapp"]));
        Assert.Contains(
            "ALERT_CHANNEL_NOT_ALLOWED:whatsapp_text",
            AlertPolicy.ValidateDeclaration("INFO", ["whatsapp"])
        );
    }

    [Theory]
    [InlineData("EMERGENCY_STOP", true)]
    [InlineData("AUTHORITY", true)]
    [InlineData("SAFETY", true)]
    [InlineData("PACE", false)]
    public void FloorCategoriesAreReserved(string category, bool floor) =>
        Assert.Equal(floor, AlertPolicy.FloorCategories.Contains(category));

    [Theory]
    [InlineData("PACE_BELOW_TARGET", true)]
    [InlineData("a", false)]
    [InlineData("lower", false)]
    [InlineData("HAS SPACE", false)]
    public void ACategoryIsAClosedIdentifier(string category, bool valid) =>
        Assert.Equal(valid, AlertPolicy.IsValidCategory(category));

    [Fact]
    public void QuietHoursRunFromElevenAtNightToSixInTheMorning()
    {
        Assert.True(AlertPolicy.InQuietHours(TimeSpan.FromHours(23)));
        Assert.True(AlertPolicy.InQuietHours(TimeSpan.FromHours(5.9)));
        Assert.False(AlertPolicy.InQuietHours(TimeSpan.FromHours(6)));
        Assert.False(AlertPolicy.InQuietHours(TimeSpan.FromHours(22.9)));
    }
}
