// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-01
// Constitutional basis: C-009, C-048, C-059, C-076

using FluentAssertions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Moq;
using System.Runtime.CompilerServices;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests;
using Xunit;

namespace BusinessPlatform.Tests;

public sealed class ProfessionalsControllerTests
{
    private readonly IProfessionalCatalog _catalog;
    private readonly ProfessionalsController _controller;

    public ProfessionalsControllerTests()
    {
        var environment = new Mock<IWebHostEnvironment>();
        environment.SetupGet(value => value.ContentRootPath)
            .Returns(FindBusinessPlatformRoot());
        _catalog = new ProfessionalCatalog(environment.Object);
        _controller = Controller(_catalog);
    }

    [Fact]
    public void Discover_LawfulOutcome_ReturnsFitWithoutPreferredCustomerScore()
    {
        var result = _controller.Discover("get more patient bookings");

        var ok = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        var professionals = ok.Value.Should()
            .BeAssignableTo<IReadOnlyList<ProfessionalDiscoveryResult>>().Subject;
        professionals.Should().ContainSingle();
        professionals[0].ProfessionalType.Should().Be("DIGITAL_MARKETING_LOCAL_SERVICE");
        professionals[0].Eligibility.Eligible.Should().BeTrue();
        professionals[0].Eligibility.Explanation.ToLowerInvariant().Should().NotContain("score");
    }

    [Fact]
    public void Discover_ProhibitedOutcome_ReturnsNoProfessional()
    {
        var result = _controller.Discover("help with deceptive impersonation marketing");

        var ok = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        ok.Value.Should().BeAssignableTo<IReadOnlyList<ProfessionalDiscoveryResult>>()
            .Which.Should().BeEmpty();
    }

    [Fact]
    public void Disclosure_ReturnsExactlyReleaseOneSkillsAndTrialBoundaries()
    {
        var result = _controller.GetDisclosure("DIGITAL_MARKETING_LOCAL_SERVICE");

        var ok = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        var disclosure = ok.Value.Should().BeOfType<ProfessionalDisclosure>().Subject;
        disclosure.ProjectionVersion.Should().Be("1.0.0");
        disclosure.Skills.Select(skill => skill.SkillId).Should().BeEquivalentTo(
            ["CUSTOMER_PROFILING", "MARKET_RESEARCH", "CONTENT_STRATEGY"]);
        disclosure.Trial.DurationDays.Should().Be(14);
        disclosure.Trial.PaidApiCallsAllowed.Should().BeFalse();
        disclosure.Trial.ExternalActionsAllowed.Should().BeFalse();
        disclosure.CustomerRights.Should().NotBeEmpty();
        disclosure.Limitations.Should().NotBeEmpty();
        disclosure.AuthorityNeeds.Should().NotBeEmpty();
    }

    [Fact]
    public void Disclosure_UnknownProfessional_ReturnsPrivacySafeNotFound()
    {
        var result = _controller.GetDisclosure("UNKNOWN");

        var problem = result.Result.Should().BeOfType<ObjectResult>().Subject;
        problem.StatusCode.Should().Be(404);
        problem.Value.Should().BeOfType<ProblemDetails>()
            .Which.Title.Should().Be("Professional not found");
    }

    [Fact]
    public void Marketplace_MapsActiveCatalogToServerOwnedOfferabilityAndPrice()
    {
        var result = _controller.BrowseMarketplace(null, 20);

        var ok = result.Should().BeOfType<OkObjectResult>().Subject;
        var json = System.Text.Json.JsonSerializer.SerializeToElement(ok.Value);
        var listing = json.GetProperty("items").EnumerateArray().Should().ContainSingle().Subject;
        listing.GetProperty("professionalType").GetString().Should().Be("DIGITAL_MARKETING_LOCAL_SERVICE");
        listing.GetProperty("disclosurePath").GetString().Should().Be("/marketplace/digital-marketing");
        listing.GetProperty("availableIntents").EnumerateArray()
            .Select(value => value.GetString()).Should().Equal("TRIAL", "HIRE");
        listing.GetProperty("offerabilityState").GetString().Should().Be("OFFERABLE");
        listing.GetProperty("nextAction").GetString().Should().Be("VIEW_DISCLOSURE");
        listing.GetProperty("indicativePrice").GetProperty("Currency").GetString().Should().Be("INR");
    }

    [Fact]
    public void Marketplace_DoesNotOfferTrialWhenOwnerServicesAreUnconfigured()
    {
        var controller = Controller(
            _catalog,
            new UnconfiguredRelationshipTrialOwnerGateway()
        );

        var result = controller.BrowseMarketplace(null, 20)
            .Should().BeOfType<OkObjectResult>().Subject;
        var listing = System.Text.Json.JsonSerializer.SerializeToElement(result.Value)
            .GetProperty("items").EnumerateArray().Should().ContainSingle().Subject;

        listing.GetProperty("availableIntents").EnumerateArray()
            .Select(value => value.GetString()).Should().Equal("HIRE");
        listing.GetProperty("trialTerms").ValueKind.Should().Be(System.Text.Json.JsonValueKind.Null);
    }

    [Fact]
    public void Marketplace_FilterBoundCursorRejectsReuseAgainstDifferentQuery()
    {
        var catalog = new Mock<IProfessionalCatalog>();
        catalog.Setup(value => value.Browse(null, null)).Returns(
        [
            Disclosure("A"), Disclosure("B"),
        ]);
        var controller = Controller(catalog.Object);
        var first = controller.BrowseMarketplace(null, 1).Should().BeOfType<OkObjectResult>().Subject;
        var cursor = System.Text.Json.JsonSerializer.SerializeToElement(first.Value).GetProperty("nextCursor").GetString();

        var invalid = controller.BrowseMarketplace(cursor, 1, query: "different")
            .Should().BeOfType<ObjectResult>().Subject;

        invalid.StatusCode.Should().Be(400);
    }

    [Fact]
    public void Marketplace_IsAvailableBeforeCustomerRegistration()
    {
        var result = _controller.BrowseMarketplace(null, 20)
            .Should().BeOfType<OkObjectResult>().Subject;
        var json = System.Text.Json.JsonSerializer.SerializeToElement(result.Value);

        json.GetProperty("items").EnumerateArray().Should().ContainSingle();
        var route = typeof(ProfessionalsController)
            .GetMethod(nameof(ProfessionalsController.BrowseMarketplace))!
            .GetCustomAttributes(typeof(CustomerIdentityRouteAttribute), true)
            .Cast<CustomerIdentityRouteAttribute>()
            .Single();
        route.RequiresMembership.Should().BeFalse();
    }

    [Theory]
    [InlineData(nameof(ProfessionalsController.Discover))]
    [InlineData(nameof(ProfessionalsController.GetDisclosure))]
    public void InformedPreTrialCatalog_IsAvailableBeforeAuthentication(string methodName)
    {
        var method = typeof(ProfessionalsController).GetMethod(methodName);

        method.Should().NotBeNull();
        method!.GetCustomAttributes(typeof(AllowAnonymousAttribute), true).Should().ContainSingle();
    }

    private static string FindBusinessPlatformRoot([CallerFilePath] string sourcePath = "")
    {
        foreach (var startPath in new[]
                 {
                     Path.GetDirectoryName(sourcePath)!,
                     Directory.GetCurrentDirectory(),
                     AppContext.BaseDirectory,
                 })
        {
            var directory = new DirectoryInfo(startPath);
            while (directory is not null)
            {
                var candidate = Path.Combine(directory.FullName, "src", "business-platform");
                if (Directory.Exists(candidate))
                {
                    return candidate;
                }

                directory = directory.Parent;
            }
        }

        throw new DirectoryNotFoundException("Could not locate src/business-platform.");
    }

    private static ProfessionalDisclosure Disclosure(string type) => new(
        type, "1.0.0", type.ToLowerInvariant(), type, ["Suitable"], [], [], [], [],
        new ProfessionalTrialDisclosure(true, 14, false, false), "RECORDED",
        new IndicativePriceDisclosure("INR", 100, "MONTHLY", "Indicative"),
        new ProfessionalEligibility(true, "Eligible"));

    private static ProfessionalsController Controller(
        IProfessionalCatalog catalog,
        IRelationshipTrialOwnerGateway? trialOwners = null)
    {
        var controller = new ProfessionalsController(
            catalog,
            trialOwners ?? new TrialOwnerGatewayStub()
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        return controller;
    }
}