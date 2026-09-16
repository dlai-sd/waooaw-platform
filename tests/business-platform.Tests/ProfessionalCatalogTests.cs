// Implements: work-contracts/WC-096-conversational-customer-portal.md §4.3
// constitutional_basis: C-023, C-049, C-059, C-063

using System.Text.Json;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ProfessionalCatalogTests
{
    [Fact]
    public void MissingCatalogDirectoryIsEmpty()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var catalog = new ProfessionalCatalog(new TestHostEnvironment(root));

        Assert.Empty(catalog.Discover("marketing"));
        Assert.Null(catalog.GetDisclosure("DIGITAL_MARKETING"));
        Assert.Empty(catalog.Browse(null, null));
    }

    [Fact]
    public void CatalogFiltersDiscoveryTypeAndEveryQuerySource()
    {
        var root = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString("N"));
        var directory = Path.Combine(root, "Catalog", "Professionals");
        Directory.CreateDirectory(directory);
        try
        {
            WriteManifest(directory, "active.json", "DIGITAL_MARKETING", "Digital Growth Professional", true);
            WriteManifest(directory, "inactive.json", "INACTIVE_MARKETING", "Inactive Professional", false);
            var catalog = new ProfessionalCatalog(new TestHostEnvironment(root));

            Assert.Empty(catalog.Discover("ad"));
            Assert.Empty(catalog.Discover("marketing fraud"));
            Assert.Equal("DIGITAL_MARKETING", Assert.Single(catalog.Discover("marketing growth")).ProfessionalType);
            Assert.Null(catalog.GetDisclosure("INACTIVE_MARKETING"));
            Assert.Equal("DIGITAL_MARKETING", Assert.Single(catalog.Browse("digital_marketing", null)).ProfessionalType);
            Assert.Empty(catalog.Browse("unknown", null));
            Assert.Single(catalog.Browse(null, "growth"));
            Assert.Single(catalog.Browse(null, "digital_marketing"));
            Assert.Single(catalog.Browse(null, "local outcomes"));
            Assert.Empty(catalog.Browse(null, "accounting"));
        }
        finally
        {
            Directory.Delete(root, recursive: true);
        }
    }

    private static void WriteManifest(string directory, string fileName, string professionalType, string displayName, bool active)
    {
        var manifest = new
        {
            professionalType,
            projectionVersion = "1.0.0",
            customerRouteSlug = "digital-marketing",
            displayName,
            active,
            supportedOutcomeTerms = new[] { "marketing", "growth" },
            prohibitedOutcomeTerms = new[] { "fraud" },
            suitability = new[] { "Supports local outcomes" },
            eligibilityExplanation = "Eligible for lawful outcomes.",
            skills = new[] { new { skillId = "RESEARCH", displayName = "Research", applicableInTrial = true, activationCondition = (string?)null } },
            limitations = new[] { "No guaranteed outcomes." },
            authorityNeeds = new[] { "Approval is required." },
            customerRights = new[] { "The customer may decline." },
            trial = new { available = true, durationDays = 14, paidApiCallsAllowed = false, externalActionsAllowed = false },
            evidencePosture = "Evidence-backed.",
            indicativePrice = new { currency = "INR", amountInrPaise = 249900, cadence = "MONTHLY", qualification = "Indicative." },
        };
        File.WriteAllText(Path.Combine(directory, fileName), JsonSerializer.Serialize(manifest));
    }

    private sealed class TestHostEnvironment(string contentRootPath) : IHostEnvironment
    {
        public string EnvironmentName { get; set; } = Environments.Development;
        public string ApplicationName { get; set; } = "business-platform.Tests";
        public string ContentRootPath { get; set; } = contentRootPath;
        public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
    }
}