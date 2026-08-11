// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-01
// Constitutional basis: C-009, C-048, C-059, C-076

using FluentAssertions;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc;
using Moq;
using System.Runtime.CompilerServices;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;
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
        _controller = new ProfessionalsController(_catalog);
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
    public void Disclosure_ReturnsAllNineteenSkillsAndTrialBoundaries()
    {
        var result = _controller.GetDisclosure("DIGITAL_MARKETING_LOCAL_SERVICE");

        var ok = result.Result.Should().BeOfType<OkObjectResult>().Subject;
        var disclosure = ok.Value.Should().BeOfType<ProfessionalDisclosure>().Subject;
        disclosure.ProjectionVersion.Should().Be("1.0.0");
        disclosure.Skills.Should().HaveCount(19);
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
}