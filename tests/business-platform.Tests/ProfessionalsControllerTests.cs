// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-01
// Constitutional basis: C-009, C-048, C-059, C-076

using FluentAssertions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
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
    private readonly InMemoryEmploymentRelationshipFactory _factory;
    private readonly CustomerWorkspaceMembership _membership;

    public ProfessionalsControllerTests()
    {
        var environment = new Mock<IWebHostEnvironment>();
        environment.SetupGet(value => value.ContentRootPath)
            .Returns(FindBusinessPlatformRoot());
        _catalog = new ProfessionalCatalog(environment.Object);
        _factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        _membership = new CustomerWorkspaceMembership(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        _controller = Controller(_catalog, _factory, _membership);
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
    public async Task Marketplace_MapsActiveCatalogToServerOwnedOfferabilityAndPrice()
    {
        await SeedAdmissionAsync(_factory, _membership.TenantId, "1.0.0");
        var result = await _controller.BrowseMarketplace(null, 20);

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
    public async Task Marketplace_FilterBoundCursorRejectsReuseAgainstDifferentQuery()
    {
        var catalog = new Mock<IProfessionalCatalog>();
        catalog.Setup(value => value.Browse(null, null)).Returns(
        [
            Disclosure("A"), Disclosure("B"),
        ]);
        await SeedAdmissionAsync(_factory, _membership.TenantId, "1.0.0", "A");
        await SeedAdmissionAsync(_factory, _membership.TenantId, "1.0.0", "B");
        var controller = Controller(catalog.Object, _factory, _membership);
        var first = (await controller.BrowseMarketplace(null, 1)).Should().BeOfType<OkObjectResult>().Subject;
        var cursor = System.Text.Json.JsonSerializer.SerializeToElement(first.Value).GetProperty("nextCursor").GetString();

        var invalid = (await controller.BrowseMarketplace(cursor, 1, query: "different"))
            .Should().BeOfType<ObjectResult>().Subject;

        invalid.StatusCode.Should().Be(400);
    }

    [Fact]
    public async Task Marketplace_HidesCatalogVersionWithoutExactActiveArtifact()
    {
        await SeedAdmissionAsync(_factory, _membership.TenantId, "0.9.0");

        var result = (await _controller.BrowseMarketplace(null, 20))
            .Should().BeOfType<OkObjectResult>().Subject;
        var json = System.Text.Json.JsonSerializer.SerializeToElement(result.Value);

        json.GetProperty("items").EnumerateArray().Should().BeEmpty();
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
        InMemoryEmploymentRelationshipFactory factory,
        CustomerWorkspaceMembership membership)
    {
        var controller = new ProfessionalsController(catalog, factory)
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        controller.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] = membership;
        return controller;
    }

    private static async Task SeedAdmissionAsync(
        InMemoryEmploymentRelationshipFactory factory,
        Guid tenantId,
        string version,
        string professionalType = "DIGITAL_MARKETING_LOCAL_SERVICE")
    {
        await using var db = factory.CreateDbContext();
        db.AgentAdmissions.Add(new AgentAdmission
        {
            TenantId = tenantId,
            ProfessionalTypeId = professionalType,
            ProfessionalVersion = version,
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
            AdmissionContentDigest = "sha256:" + new string('a', 64),
            EvidenceSetDigest = "sha256:" + new string('b', 64),
            ArtifactDigest = "sha256:" + new string('c', 64),
        });
        await db.SaveChangesAsync();
    }
}