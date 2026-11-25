// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R003, WC171-R004, WC171-R005, WC171-R006
// Constitutional basis: C-001, C-005, C-023, C-049, C-059, C-063, C-076
// IB: IB-171

using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services.Alerts;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class ExperienceNavigationAdmissionTests
{
    private static JsonNode Dma() =>
        JsonNode.Parse(
            File.ReadAllText(
                RepositoryPaths.Resolve(
                    "src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json"
                )
            )
        )!;

    private static ExperienceScanResult Scan(JsonNode manifest) =>
        ExperienceManifestScanner.Scan(JsonSerializer.SerializeToElement(manifest));

    private static JsonObject Experience(JsonNode manifest) => manifest["experience"]!.AsObject();

    private static JsonObject Entry(
        string id,
        string label,
        JsonObject surface,
        int order = 10,
        string? labelKey = null
    ) =>
        new()
        {
            ["entryId"] = id,
            ["labelKey"] = labelKey ?? "NAV_" + id,
            ["label"] = label,
            ["icon"] = "profile",
            ["order"] = order,
            ["surface"] = surface,
            ["audiences"] = new JsonArray("customer_owner"),
            ["availabilityGate"] = "ALWAYS",
        };

    private static JsonObject Domain(string target) =>
        new() { ["kind"] = "DOMAIN_BLOCK", ["target"] = target };

    private static ExperienceScanResult WithNavigation(params JsonObject[] entries)
    {
        var manifest = Dma();
        Experience(manifest)["navigation"] = new JsonArray(
            entries.Select(entry => (JsonNode)entry).ToArray()
        );
        return Scan(manifest);
    }

    [Fact]
    public void DmaDeclaresItsFourEntriesInOrderAndStaysCompatible()
    {
        var scan = Scan(Dma());

        Assert.True(scan.ExperienceCapable);
        Assert.Equal(
            new[]
            {
                "PROFILE_AND_MATURITY",
                "CAMPAIGNS_AND_CALENDAR",
                "PLATFORM_ACCOUNTS",
                "BUSINESS_RESULTS",
            },
            scan.Declaration!.Navigation.Select(entry => entry.EntryId)
        );
        Assert.All(scan.Declaration.Navigation, entry => Assert.NotEmpty(entry.Audiences));
    }

    [Fact]
    public void ALegacyDeclarationWithoutNavigationStillAdmitsAndShowsOnlyTheFixedSurfaces()
    {
        var manifest = Dma();
        Experience(manifest).Remove("navigation");

        var scan = Scan(manifest);

        Assert.True(scan.ExperienceCapable);
        Assert.Empty(scan.Declaration!.Navigation);
    }

    [Fact]
    public void ASecondProfessionDeclaresDifferentEntriesThroughTheSameCodeWithNoAgentBranch()
    {
        var scan = WithNavigation(
            Entry("LESSON_PLANS", "Lesson plans", Domain("CONTENT_CALENDAR_PREVIEW"), 5),
            Entry(
                "STUDENT_PROGRESS",
                "Student progress",
                new JsonObject
                {
                    ["kind"] = "BLOCK_COMPOSITION",
                    ["blocks"] = new JsonArray("METRIC", "LIST"),
                },
                15
            )
        );

        Assert.True(scan.ExperienceCapable);
        Assert.Equal(
            new[] { "Lesson plans", "Student progress" },
            scan.Declaration!.Navigation.Select(entry => entry.Label)
        );
    }

    [Theory]
    [InlineData("<b>Results</b>")]
    [InlineData("Results {TOKEN}")]
    [InlineData("Results & more")]
    public void MarkupOrTemplateTokensInALabelAreRefused(string label)
    {
        var scan = WithNavigation(Entry("PROFILE", label, Domain("MARKETING_MATURITY_SUMMARY")));

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Contains("EXPERIENCE_NAVIGATION_INVALID", scan.ReasonCodes);
    }

    [Fact]
    public void AnUnknownSurfaceKindIsRefusedSoAnEmbeddedSurfaceNeverAdmits()
    {
        var scan = WithNavigation(
            Entry(
                "EMBEDDED_TOOL",
                "Tool",
                new JsonObject { ["kind"] = "EMBEDDED", ["target"] = "x" }
            )
        );

        Assert.Contains("EXPERIENCE_NAVIGATION_SURFACE_UNSUPPORTED", scan.ReasonCodes);
    }

    [Fact]
    public void DuplicateEntryIdsOrLabelKeysAreRefused()
    {
        var scan = WithNavigation(
            Entry("PROFILE", "Profile", Domain("MARKETING_MATURITY_SUMMARY"), 1),
            Entry("PROFILE", "Profile again", Domain("MARKETING_MATURITY_SUMMARY"), 2)
        );

        Assert.Contains("EXPERIENCE_NAVIGATION_DUPLICATE", scan.ReasonCodes);
    }

    [Theory]
    [InlineData("KERNEL_VIEW", "settings")]
    [InlineData("DOMAIN_BLOCK", "NOT_DECLARED_ANYWHERE")]
    [InlineData("BLOCK_COMPOSITION", null)]
    public void AnEntryThatOpensNothingIsRefused(string kind, string? target)
    {
        var surface = new JsonObject { ["kind"] = kind };
        if (target is not null)
            surface["target"] = target;

        var scan = WithNavigation(Entry("NOTHING", "Nothing", surface));

        Assert.Contains("EXPERIENCE_NAVIGATION_TARGET_UNRESOLVED", scan.ReasonCodes);
    }

    [Fact]
    public void AnEntryNamingAnAudienceTheAgentDoesNotServeIsNeverShownToThatAudience()
    {
        var entry = Entry("PROFILE", "Profile", Domain("MARKETING_MATURITY_SUMMARY"));
        entry["audiences"] = new JsonArray("beneficiary");

        var scan = WithNavigation(entry);

        Assert.True(scan.ExperienceCapable);
        Assert.Empty(scan.Declaration!.Navigation);
    }

    [Fact]
    public void AnEntryNamingAnUnknownAudienceIsInvalid()
    {
        var entry = Entry("PROFILE", "Profile", Domain("MARKETING_MATURITY_SUMMARY"));
        entry["audiences"] = new JsonArray("everyone");

        Assert.Contains("EXPERIENCE_NAVIGATION_INVALID", WithNavigation(entry).ReasonCodes);
    }

    [Fact]
    public void MoreThanTwelveEntriesOrANonArrayIsInvalid()
    {
        var many = Enumerable
            .Range(0, 13)
            .Select(index =>
                Entry(
                    $"ENTRY_{index:00}",
                    $"Entry {index}",
                    Domain("MARKETING_MATURITY_SUMMARY"),
                    index
                )
            )
            .ToArray();
        Assert.Contains("EXPERIENCE_NAVIGATION_INVALID", WithNavigation(many).ReasonCodes);

        var manifest = Dma();
        Experience(manifest)["navigation"] = "not an array";
        Assert.Contains("EXPERIENCE_NAVIGATION_INVALID", Scan(manifest).ReasonCodes);
    }

    [Fact]
    public void AnAgentCannotDeclareAnAlertChannelOrClassThePolicyForbids()
    {
        var manifest = Dma();
        var alerts = Experience(manifest)["monitor"]!["alerts"]!.AsArray();
        alerts[2]!["channels"] = new JsonArray("portal", "whatsapp_text");

        var scan = Scan(manifest);

        Assert.Equal(ExperienceScanResult.Incompatible, scan.State);
        Assert.Contains("EXPERIENCE_ALERT_POLICY_VIOLATION", scan.ReasonCodes);
    }

    [Fact]
    public void ASmsChannelIsNeverAllowed()
    {
        var manifest = Dma();
        Experience(manifest)["monitor"]!["alerts"]![0]!["channels"] = new JsonArray("sms");

        Assert.Contains("EXPERIENCE_ALERT_POLICY_VIOLATION", Scan(manifest).ReasonCodes);
    }

    [Fact]
    public void TheSharedNavigationAndAlertCodeNamesNoAgent()
    {
        var files = new[]
        {
            "src/business-platform/Services/Alerts/AlertPolicy.cs",
            "src/business-platform/Services/Alerts/AlertPolicyService.cs",
            "src/business-platform/Services/Operations/OperationsConsoleService.cs",
        };
        foreach (var file in files)
        {
            var text = File.ReadAllText(RepositoryPaths.Resolve(file));
            Assert.DoesNotContain("DIGITAL_MARKETING", text, StringComparison.OrdinalIgnoreCase);
            Assert.DoesNotContain("MARKETING_MATURITY", text, StringComparison.OrdinalIgnoreCase);
        }
    }

    [Theory]
    [InlineData("MID_MONTH_PACE_BELOW_TARGET", AlertClasses.AtRisk, WhatsAppDecisions.Send)]
    [InlineData("CONSECUTIVE_MONTHLY_MISSES", AlertClasses.ActionRequired, WhatsAppDecisions.Send)]
    [InlineData(
        "COMPONENT_NEARING_EXHAUSTION",
        AlertClasses.Information,
        WhatsAppDecisions.ClassNotEligible
    )]
    public void EachOfDmasDeclaredAlertsIsClassifiedAndRoutedByThePolicy(
        string signal,
        string expectedClass,
        string expectedWhatsApp
    )
    {
        var scan = Scan(Dma());
        var declared = scan.Declaration!.Alerts.Single(alert => alert.Signal == signal);
        var tenant = Guid.NewGuid();
        var alert = new AlertEvent(
            AlertSources.AgentDeclared,
            tenant,
            Guid.NewGuid(),
            declared.Signal,
            declared.Severity,
            "2026-11",
            "Something to know."
        );

        var alertClass = AlertPolicy.Classify(alert);

        Assert.Equal(expectedClass, alertClass);
        Assert.Empty(AlertPolicy.ValidateDeclaration(declared.Severity, declared.Channels));
        Assert.Equal(
            expectedWhatsApp,
            AlertPolicy.DecideWhatsApp(alertClass, OpenGate(TimeSpan.FromHours(11)))
        );
        Assert.Equal(
            AlertPolicy.DedupKey(alert),
            AlertPolicy.DedupKey(alert with { DueMeaning = "Repeated." })
        );
    }

    private static DeliveryFacts OpenGate(TimeSpan timeOfDay) =>
        new(true, true, false, false, timeOfDay);
}
