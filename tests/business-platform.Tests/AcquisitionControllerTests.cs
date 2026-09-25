// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md R-005, R-006
// constitutional_basis: C-023, C-026, C-049, C-059, C-063

using System.Runtime.CompilerServices;
using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
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
    [Theory]
    [InlineData("TRIAL")]
    [InlineData("HIRE")]
    public async Task AcceptedDisclosureUsesResolvedMembershipAndReplaysExactlyOnce(string intent)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        var trialOwners = new TrialOwnerGatewayStub
        {
            Wbe = new(trialId, startsAt, startsAt.AddDays(14)),
            Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14)),
        };
        var trials = new RelationshipTrialService(factory, relationships, trialOwners);
        var membership = new CustomerWorkspaceMembership(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        await SeedAdmissionAsync(factory, membership.TenantId);
        var controller = Controller(factory, Catalog(), relationships, membership, trials);
        var key = Guid.NewGuid();
        var request = ValidRequest(intent);

        var created = Assert.IsType<ObjectResult>(await controller.ContinueAsync(
            request, key, Guid.NewGuid(), CancellationToken.None));
        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        var replayed = Assert.IsType<OkObjectResult>(await controller.ContinueAsync(
            request, key, Guid.NewGuid(), CancellationToken.None));
        var createdBody = Assert.IsType<AcquisitionContinuationResponse>(created.Value);
        var replayedBody = Assert.IsType<AcquisitionContinuationResponse>(replayed.Value);

        Assert.Equal(createdBody.RelationshipId, replayedBody.RelationshipId);
        Assert.True(replayedBody.Replayed);
        Assert.Equal(3, gateway.CallCount);
        var evidence = JsonSerializer.SerializeToElement(
            Assert.Single(gateway.Calls, call => call.ActionType == "ADMIT_EMPLOYMENT_RELATIONSHIP").ActionParameters);
        Assert.Equal(intent, evidence.GetProperty("acquisition_intent").GetString());
        Assert.Equal("1.0.0", evidence.GetProperty("disclosure_revision").GetString());
        Assert.Equal("2026-07-18", evidence.GetProperty("terms_version").GetString());
        await using var db = factory.CreateDbContext();
        var relationship = Assert.Single(await db.EmploymentRelationships.ToListAsync());
        var participant = Assert.Single(await db.RelationshipParticipants.ToListAsync());
        Assert.Equal(membership.TenantId, relationship.TenantId);
        Assert.Equal(membership.AccountId, relationship.InitiatingParticipantId);
        Assert.Equal(intent, relationship.AcquisitionMode);
        Assert.Equal(membership.AccountId, participant.ParticipantId);
        Assert.Equal(
            intent == "TRIAL" ? EmploymentRelationshipState.TrialActive : EmploymentRelationshipState.Configuring,
            relationship.State);
        Assert.Equal(intent == "TRIAL" ? 1 : 0, trialOwners.WbeCalls);
        Assert.Equal(intent == "TRIAL" ? 1 : 0, trialOwners.PrCalls);
    }

    [Fact]
    public async Task StaleDisclosureCreatesNoRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var membership = new CustomerWorkspaceMembership(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        var controller = Controller(factory, Catalog(), relationships, membership);

        var result = await controller.ContinueAsync(
            ValidRequest("HIRE") with { DisclosureRevision = "0.9.0" },
            Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Equal(0, gateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task MissingActiveAdmissionCreatesNoRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var membership = new CustomerWorkspaceMembership(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        var controller = Controller(factory, Catalog(), relationships, membership);

        var result = await controller.ContinueAsync(
            ValidRequest("HIRE"), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Equal(0, gateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task UnconfiguredTrialOwnersRejectBeforeRelationshipCreation()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var membership = new CustomerWorkspaceMembership(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        await SeedAdmissionAsync(factory, membership.TenantId);
        var trials = new RelationshipTrialService(
            factory,
            relationships,
            new UnconfiguredRelationshipTrialOwnerGateway()
        );
        var controller = Controller(factory, Catalog(), relationships, membership, trials);

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Equal(0, gateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task ConstitutionalEvidenceDenialCreatesNoRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new Mock<IRelationshipConstitutionalGateway>();
        gateway.Setup(value => value.AuthorizeAndRecordAsync(
                It.IsAny<Guid>(), It.IsAny<Guid>(), It.IsAny<string>(), It.IsAny<string>(),
                It.IsAny<Guid>(), It.IsAny<object>(), It.IsAny<CancellationToken>()))
            .ThrowsAsync(new ConstitutionalActionDeniedException("Denied by policy."));
        var relationships = new EmploymentRelationshipService(
            factory, gateway.Object, NullLogger<EmploymentRelationshipService>.Instance);
        var membership = new CustomerWorkspaceMembership(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);
        await SeedAdmissionAsync(factory, membership.TenantId);
        var controller = Controller(factory, Catalog(), relationships, membership);

        var result = await controller.ContinueAsync(
            ValidRequest("HIRE"), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);

        Assert.Equal(StatusCodes.Status403Forbidden, Assert.IsType<ObjectResult>(result).StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task MissingResolvedMembershipCannotFallBackToBrowserIdentityClaims()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory, gateway, NullLogger<EmploymentRelationshipService>.Instance);
        var controller = Controller(factory, Catalog(), relationships, membership: null);

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"), Guid.NewGuid(), Guid.NewGuid(), CancellationToken.None);

        Assert.IsType<ForbidResult>(result);
        Assert.Equal(0, gateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    private static ContinueAcquisitionRequest ValidRequest(string intent) => new(
        "DIGITAL_MARKETING_LOCAL_SERVICE", "1.0.0", intent, "1.0.0", "2026-07-18", "ACCEPT_DISCLOSURE");

    private static async Task SeedAdmissionAsync(
        InMemoryEmploymentRelationshipFactory factory,
        Guid tenantId)
    {
        await using var db = factory.CreateDbContext();
        db.AgentAdmissions.Add(new AgentAdmission
        {
            TenantId = tenantId,
            ProfessionalTypeId = "DIGITAL_MARKETING_LOCAL_SERVICE",
            ProfessionalVersion = "1.0.0",
            OwnerSubjectId = Guid.NewGuid(),
            State = AgentAdmissionState.Active,
            AdmissionContentDigest = "sha256:" + new string('a', 64),
            EvidenceSetDigest = "sha256:" + new string('b', 64),
            ArtifactDigest = "sha256:" + new string('c', 64),
        });
        await db.SaveChangesAsync();
    }

    private static AcquisitionController Controller(
        InMemoryEmploymentRelationshipFactory factory,
        IProfessionalCatalog catalog,
        EmploymentRelationshipService relationships,
        CustomerWorkspaceMembership? membership,
        RelationshipTrialService? trials = null)
    {
        var controller = new AcquisitionController(
            factory,
            catalog,
            relationships,
            NullLogger<AcquisitionController>.Instance,
            trials
        )
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(
                        [new Claim("sub", "google-oauth2|customer-subject")], "Test")),
                },
            },
        };
        if (membership is not null)
        {
            controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = membership.TenantId.ToString();
            controller.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] = membership;
        }
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
