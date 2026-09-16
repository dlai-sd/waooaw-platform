// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-005, C-023, C-026, C-049, C-059, C-063

using System.Security.Claims;
using System.Text.Json;
using System.Runtime.CompilerServices;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AcquisitionControllerTests
{
    [Fact]
    public async Task AcceptedExactDisclosureCreatesOneBoundRelationshipAndReplays()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admission = new AgentAdmission
        {
            TenantId = Guid.NewGuid(),
            ProfessionalTypeId = "DIGITAL_MARKETING_LOCAL_SERVICE",
            ProfessionalVersion = "1.0.0",
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
        };
        await using (var seed = factory.CreateDbContext())
        {
            seed.AgentAdmissions.Add(admission);
            await seed.SaveChangesAsync();
        }
        var controller = Controller(factory, Catalog(), relationships, tenantId, participantId);
        var key = Guid.NewGuid();
        var request = new ContinueAcquisitionRequest(
            "DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", "TRIAL", "1.0.0", "2026-07-18", "ACCEPT_DISCLOSURE");

        var created = Assert.IsType<ObjectResult>(await controller.ContinueAsync(request, key, Guid.NewGuid(), CancellationToken.None));
        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        var replayed = Assert.IsType<OkObjectResult>(await controller.ContinueAsync(request, key, Guid.NewGuid(), CancellationToken.None));
        var createdBody = Assert.IsType<AcquisitionContinuationResponse>(created.Value);
        var replayedBody = Assert.IsType<AcquisitionContinuationResponse>(replayed.Value);

        Assert.Equal(createdBody.RelationshipId, replayedBody.RelationshipId);
        Assert.True(replayedBody.Replayed);
        Assert.Equal(1, gateway.CallCount);
        var evidence = JsonSerializer.SerializeToElement(gateway.LastActionParameters);
        Assert.Equal("TRIAL", evidence.GetProperty("acquisition_intent").GetString());
        Assert.Equal("1.0.0", evidence.GetProperty("disclosure_revision").GetString());
        Assert.Equal("2026-07-18", evidence.GetProperty("terms_version").GetString());
    }

    [Fact]
    public async Task StaleOrUnacceptedDisclosureCreatesNoRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var controller = Controller(factory, Catalog(), relationships, Guid.NewGuid(), Guid.NewGuid());

        var result = await controller.ContinueAsync(
            new ContinueAcquisitionRequest(
                "DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", "HIRE", "0.9.0", "2026-07-18", "ACCEPT_DISCLOSURE"),
            Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Equal(0, gateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    private static AcquisitionController Controller(
        InMemoryEmploymentRelationshipFactory factory,
        IProfessionalCatalog catalog,
        EmploymentRelationshipService relationships,
        Guid tenantId,
        Guid participantId)
    {
        var controller = new AcquisitionController(factory, catalog, relationships)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(
                        [new Claim("participant_id", participantId.ToString())], "Test")),
                },
            },
        };
        controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        return controller;
    }

    private static IProfessionalCatalog Catalog()
    {
        var environment = new Mock<IHostEnvironment>();
        environment.SetupGet(value => value.ContentRootPath)
            .Returns(FindBusinessPlatformRoot());
        return new ProfessionalCatalog(environment.Object);
    }

    private static string FindBusinessPlatformRoot([CallerFilePath] string sourcePath = "")
    {
        var directory = new DirectoryInfo(Path.GetDirectoryName(sourcePath)!);
        while (directory is not null)
        {
            var candidate = Path.Combine(directory.FullName, "src", "business-platform");
            if (Directory.Exists(candidate)) return candidate;
            directory = directory.Parent;
        }
        throw new DirectoryNotFoundException("Could not locate src/business-platform.");
    }
}