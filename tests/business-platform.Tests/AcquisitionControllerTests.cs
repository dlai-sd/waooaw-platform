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
    [Fact]
    public async Task AcquisitionIntentPersistsBeforeRegistrationWithoutCreatingRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var controller = Controller(factory, Catalog(), relationships, null);
        controller.HttpContext.User = new ClaimsPrincipal(
            new ClaimsIdentity(
                [
                    new Claim("iss", "https://identity.example.test/realms/customer"),
                    new Claim("sub", "google-oauth2|customer-subject"),
                ],
                "Test"
            )
        );
        var key = Guid.NewGuid();

        var created = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(ValidRequest("TRIAL"), key, CancellationToken.None)
        );
        var replayed = Assert.IsType<OkObjectResult>(
            await controller.CreateIntentAsync(ValidRequest("TRIAL"), key, CancellationToken.None)
        );

        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        Assert.False(Assert.IsType<AcquisitionIntentResponse>(created.Value).Replayed);
        Assert.True(Assert.IsType<AcquisitionIntentResponse>(replayed.Value).Replayed);
        await using var db = factory.CreateDbContext();
        var intent = Assert.Single(await db.AcquisitionIntents.ToListAsync());
        Assert.Equal("PENDING_REGISTRATION", intent.Status);
        Assert.Equal("1.0.0", intent.ProfessionalVersion);
        Assert.Contains("disclosureRevision=1.0.0", intent.ContractDocumentUri);
        Assert.Empty(await db.EmploymentRelationships.ToListAsync());
        Assert.Equal(0, gateway.CallCount);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task AcquisitionIntentRequiresANonEmptyIdempotencyKey(bool useEmptyKey)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var controller = Controller(factory, Catalog(), relationships, null);
        Guid? key = useEmptyKey ? Guid.Empty : null;

        var result = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(ValidRequest("TRIAL"), key, CancellationToken.None)
        );

        Assert.Equal(StatusCodes.Status400BadRequest, result.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.AcquisitionIntents.ToListAsync());
    }

    [Fact]
    public async Task AcquisitionIntentRejectsDifferentMaterialForTheSameIdempotencyKey()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var controller = Controller(factory, Catalog(), relationships, null);
        var key = Guid.NewGuid();
        await controller.CreateIntentAsync(ValidRequest("TRIAL"), key, CancellationToken.None);

        var result = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(ValidRequest("HIRE"), key, CancellationToken.None)
        );

        Assert.Equal(StatusCodes.Status409Conflict, result.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Equal("TRIAL", Assert.Single(await db.AcquisitionIntents.ToListAsync()).Mode);
    }

    [Fact]
    public async Task AcquisitionIntentRejectsCouponCodesOutsideTheCanonicalCharacterSet()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var controller = Controller(factory, Catalog(), relationships, null);

        var result = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE") with
                {
                    CouponCode = "DEMO 100",
                },
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(StatusCodes.Status409Conflict, result.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.AcquisitionIntents.ToListAsync());
    }

    [Fact]
    public async Task RegistrationHandoffCompletesTheSameIdentityBoundIntent()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        await SeedAdmissionAsync(factory, membership.TenantId);
        var key = Guid.NewGuid();
        var beforeRegistration = Controller(factory, Catalog(), relationships, null);
        var afterRegistration = Controller(factory, Catalog(), relationships, membership);

        var persisted = await beforeRegistration.CreateIntentAsync(
            ValidRequest("HIRE"),
            key,
            CancellationToken.None
        );
        var completed = await afterRegistration.ContinueAsync(
            ValidRequest("HIRE"),
            key,
            key,
            CancellationToken.None
        );

        Assert.Equal(
            StatusCodes.Status201Created,
            Assert.IsType<ObjectResult>(persisted).StatusCode
        );
        Assert.Equal(
            StatusCodes.Status201Created,
            Assert.IsType<ObjectResult>(completed).StatusCode
        );
        await using var db = factory.CreateDbContext();
        var intent = Assert.Single(await db.AcquisitionIntents.ToListAsync());
        Assert.Equal(key, intent.AcquisitionIntentId);
        Assert.Equal("COMPLETED", intent.Status);
        Assert.Equal(membership.TenantId, intent.TenantId);
        Assert.Equal(membership.AccountId, intent.ParticipantId);
        Assert.Single(await db.EmploymentRelationships.ToListAsync());
    }

    [Theory]
    [InlineData("TRIAL")]
    [InlineData("HIRE")]
    public async Task AcceptedDisclosureUsesResolvedMembershipAndReplaysExactlyOnce(string intent)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        var trialOwners = new TrialOwnerGatewayStub
        {
            Wbe = new(trialId, startsAt, startsAt.AddDays(14)),
            Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14)),
        };
        var trials = new RelationshipTrialService(factory, relationships, trialOwners);
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        await SeedAdmissionAsync(factory, membership.TenantId);
        var controller = Controller(factory, Catalog(), relationships, membership, trials);
        var key = Guid.NewGuid();
        var request = ValidRequest(intent);

        var created = Assert.IsType<ObjectResult>(
            await controller.ContinueAsync(request, key, Guid.NewGuid(), CancellationToken.None)
        );
        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        var replayed = Assert.IsType<OkObjectResult>(
            await controller.ContinueAsync(request, key, Guid.NewGuid(), CancellationToken.None)
        );
        var createdBody = Assert.IsType<AcquisitionContinuationResponse>(created.Value);
        var replayedBody = Assert.IsType<AcquisitionContinuationResponse>(replayed.Value);

        Assert.Equal(createdBody.RelationshipId, replayedBody.RelationshipId);
        Assert.True(replayedBody.Replayed);
        Assert.Equal(3, gateway.CallCount);
        var evidence = JsonSerializer.SerializeToElement(
            Assert
                .Single(gateway.Calls, call => call.ActionType == "ADMIT_EMPLOYMENT_RELATIONSHIP")
                .ActionParameters
        );
        Assert.Equal(intent, evidence.GetProperty("acquisition_intent").GetString());
        Assert.Equal("1.0.0", evidence.GetProperty("disclosure_revision").GetString());
        Assert.Equal("2026-07-18", evidence.GetProperty("terms_version").GetString());
        await using var db = factory.CreateDbContext();
        var relationship = Assert.Single(await db.EmploymentRelationships.ToListAsync());
        var participant = Assert.Single(await db.RelationshipParticipants.ToListAsync());
        Assert.Equal(membership.TenantId, relationship.TenantId);
        Assert.Equal(membership.AccountId, relationship.InitiatingParticipantId);
        Assert.Equal(intent, relationship.AcquisitionMode);
        Assert.Equal(key, relationship.AcquisitionIntentId);
        Assert.Equal("2026-07-18", relationship.AcquisitionContractVersion);
        Assert.Matches("^[0-9a-f]{64}$", relationship.AcquisitionContractHash);
        Assert.NotNull(relationship.AcquisitionContractAcceptedAt);
        Assert.Equal(membership.AccountId, participant.ParticipantId);
        Assert.Equal(
            intent == "TRIAL"
                ? RelationshipParticipantRole.Evaluator
                : RelationshipParticipantRole.Employer,
            participant.Role
        );
        Assert.Equal(
            intent == "TRIAL"
                ? EmploymentRelationshipState.TrialActive
                : EmploymentRelationshipState.Configuring,
            relationship.State
        );
        Assert.Equal(intent == "TRIAL" ? 1 : 0, trialOwners.WbeCalls);
        Assert.Equal(intent == "TRIAL" ? 1 : 0, trialOwners.PrCalls);
    }

    [Fact]
    public async Task CompletedIntentCannotBeReboundToAnotherCustomerWorkspace()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var firstMembership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        var secondMembership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        await SeedAdmissionAsync(factory, firstMembership.TenantId);
        await SeedAdmissionAsync(factory, secondMembership.TenantId);
        var key = Guid.NewGuid();

        var first = await Controller(factory, Catalog(), relationships, firstMembership)
            .ContinueAsync(ValidRequest("HIRE"), key, key, CancellationToken.None);
        var conflicting = await Controller(factory, Catalog(), relationships, secondMembership)
            .ContinueAsync(ValidRequest("HIRE"), key, key, CancellationToken.None);

        Assert.Equal(StatusCodes.Status201Created, Assert.IsType<ObjectResult>(first).StatusCode);
        Assert.Equal(
            StatusCodes.Status409Conflict,
            Assert.IsType<ObjectResult>(conflicting).StatusCode
        );
        await using var db = factory.CreateDbContext();
        var relationship = Assert.Single(await db.EmploymentRelationships.ToListAsync());
        Assert.Equal(firstMembership.TenantId, relationship.TenantId);
    }

    [Fact]
    public async Task StaleDisclosureCreatesNoRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        var controller = Controller(factory, Catalog(), relationships, membership);

        var result = await controller.ContinueAsync(
            ValidRequest("HIRE") with
            {
                DisclosureRevision = "0.9.0",
            },
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

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
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        var controller = Controller(factory, Catalog(), relationships, membership);

        var result = await controller.ContinueAsync(
            ValidRequest("HIRE"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

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
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        await SeedAdmissionAsync(factory, membership.TenantId);
        var trials = new RelationshipTrialService(
            factory,
            relationships,
            new UnconfiguredRelationshipTrialOwnerGateway()
        );
        var controller = Controller(factory, Catalog(), relationships, membership, trials);

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        Assert.Equal(0, gateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task TrialOwnerFailureLeavesOnlyTheAcquisitionIntentAndNoRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        await SeedAdmissionAsync(factory, membership.TenantId);
        var trials = new RelationshipTrialService(
            factory,
            relationships,
            new TrialOwnerGatewayStub { Wbe = null }
        );
        var controller = Controller(factory, Catalog(), relationships, membership, trials);

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(
            StatusCodes.Status503ServiceUnavailable,
            Assert.IsType<ObjectResult>(result).StatusCode
        );
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.EmploymentRelationships.ToListAsync());
        Assert.Equal("UNRESOLVED", Assert.Single(await db.AcquisitionIntents.ToListAsync()).Status);
        Assert.Equal(0, gateway.CallCount);
    }

    [Fact]
    public async Task ConstitutionalEvidenceDenialCreatesNoRelationship()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new Mock<IRelationshipConstitutionalGateway>();
        gateway
            .Setup(value =>
                value.AuthorizeAndRecordAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<Guid>(),
                    It.IsAny<string>(),
                    It.IsAny<string>(),
                    It.IsAny<Guid>(),
                    It.IsAny<object>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(new ConstitutionalActionDeniedException("Denied by policy."));
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway.Object,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        await SeedAdmissionAsync(factory, membership.TenantId);
        var controller = Controller(factory, Catalog(), relationships, membership);

        var result = await controller.ContinueAsync(
            ValidRequest("HIRE"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(
            StatusCodes.Status403Forbidden,
            Assert.IsType<ObjectResult>(result).StatusCode
        );
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task MissingResolvedMembershipCannotFallBackToBrowserIdentityClaims()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var relationships = new EmploymentRelationshipService(
            factory,
            gateway,
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var controller = Controller(factory, Catalog(), relationships, membership: null);

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.IsType<ForbidResult>(result);
        Assert.Equal(0, gateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    private static ContinueAcquisitionRequest ValidRequest(string intent) =>
        new(
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "1.0.0",
            intent,
            "1.0.0",
            "2026-07-18",
            "ACCEPT_EMPLOYMENT_CONTRACT"
        );

    private static async Task SeedAdmissionAsync(
        InMemoryEmploymentRelationshipFactory factory,
        Guid tenantId
    )
    {
        await using var db = factory.CreateDbContext();
        db.AgentAdmissions.Add(
            new AgentAdmission
            {
                TenantId = tenantId,
                ProfessionalTypeId = "DIGITAL_MARKETING_LOCAL_SERVICE",
                ProfessionalVersion = "1.0.0",
                OwnerSubjectId = Guid.NewGuid(),
                State = AgentAdmissionState.Active,
                AdmissionContentDigest = "sha256:" + new string('a', 64),
                EvidenceSetDigest = "sha256:" + new string('b', 64),
                ArtifactDigest = "sha256:" + new string('c', 64),
            }
        );
        await db.SaveChangesAsync();
    }

    private static AcquisitionController Controller(
        InMemoryEmploymentRelationshipFactory factory,
        IProfessionalCatalog catalog,
        EmploymentRelationshipService relationships,
        CustomerWorkspaceMembership? membership,
        RelationshipTrialService? trials = null
    )
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
                    User = new ClaimsPrincipal(
                        new ClaimsIdentity(
                            [
                                new Claim("iss", "https://identity.example.test/realms/customer"),
                                new Claim("sub", "google-oauth2|customer-subject"),
                            ],
                            "Test"
                        )
                    ),
                },
            },
        };
        if (membership is not null)
        {
            controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] =
                membership.TenantId.ToString();
            controller.HttpContext.Items[CustomerMembershipMiddleware.MembershipItem] = membership;
        }
        return controller;
    }

    private static IProfessionalCatalog Catalog()
    {
        var environment = new Mock<IHostEnvironment>();
        environment.SetupGet(value => value.ContentRootPath).Returns(FindBusinessPlatformRoot());
        return new ProfessionalCatalog(environment.Object);
    }

    private static string FindBusinessPlatformRoot([CallerFilePath] string sourcePath = "")
    {
        var directory = new DirectoryInfo(Path.GetDirectoryName(sourcePath)!);
        while (directory is not null)
        {
            var candidate = Path.Combine(directory.FullName, "src", "business-platform");
            if (Directory.Exists(candidate))
                return candidate;
            directory = directory.Parent;
        }
        throw new DirectoryNotFoundException("Could not locate src/business-platform.");
    }
}
