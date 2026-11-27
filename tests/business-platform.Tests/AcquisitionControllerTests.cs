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
using Waooaw.BusinessPlatform.Services.PlatformApprovals;
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
    public async Task RegistrationHandoffPricesAndCompletesTheHireOnlyAfterTheWorkspaceExists()
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
            StatusCodes.Status409Conflict,
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
        Assert.Equal(118000, intent.QuoteGrossInrPaise);
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
    public async Task WC175_R023_ANewCustomerStartsATrialOnceTheFounderHasApprovedTheVersion()
    {
        var (factory, relationships, trials, membership, owners) = TrialHarness();
        var approvals = Approvals(factory, out var store);
        await approvals.DecideAsync(
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            CancellationToken.None
        );
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            membership,
            trials,
            approvals: approvals
        );

        var created = Assert.IsType<ObjectResult>(
            await controller.ContinueAsync(
                ValidRequest("TRIAL"),
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        Assert.Equal(1, owners.WbeCalls);
        await using var db = factory.CreateDbContext();
        var admission = Assert.Single(await db.AgentAdmissions.ToListAsync());
        Assert.Equal(membership.TenantId, admission.TenantId);
        Assert.Equal(AgentAdmissionState.Active, admission.State);
        Assert.Equal(
            PlatformProfessionalApprovalService.WorkspacePolicyVersion,
            admission.PolicyVersion
        );
        Assert.Equal(
            admission.AdmissionId,
            Assert.Single(await db.EmploymentRelationships.ToListAsync()).ProfessionalAdmissionId
        );
        Assert.Single(store.History);
    }

    [Fact]
    public async Task WC175_R023_WithoutTheFoundersApprovalNoWorkspaceAdmissionAndNoRelationshipIsCreated()
    {
        var (factory, relationships, trials, membership, _) = TrialHarness();
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            membership,
            trials,
            approvals: Approvals(factory, out _)
        );

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.AgentAdmissions);
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task WC175_R023_ASuspendedVersionStopsNewTrialsEvenWhereTheWorkspaceAlreadyHasAnAdmission()
    {
        var (factory, relationships, trials, membership, _) = TrialHarness();
        var approvals = Approvals(factory, out _);
        await approvals.DecideAsync(
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            CancellationToken.None
        );
        Assert.NotNull(
            await approvals.EnsureWorkspaceAdmissionAsync(
                membership.TenantId,
                membership.AccountId,
                "DIGITAL_MARKETING_LOCAL_SERVICE",
                "1.0.0",
                CancellationToken.None
            )
        );
        await approvals.DecideAsync(
            "DIGITAL_MARKETING_LOCAL_SERVICE",
            "1.0.0",
            PlatformApprovalActions.Suspend,
            "founder-1",
            "Paused for a review",
            CancellationToken.None
        );
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            membership,
            trials,
            approvals: approvals
        );

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task WC175_R023_AnApprovalOfAnEarlierDefinitionNoLongerApplies()
    {
        var (factory, relationships, trials, membership, _) = TrialHarness();
        var approvals = Approvals(factory, out var store);
        await store.SaveAsync(
            new PlatformProfessionalApproval(
                "DIGITAL_MARKETING_LOCAL_SERVICE",
                "1.0.0",
                PlatformApprovalStates.Approved,
                "sha256:" + new string('0', 64),
                "rev-1",
                "founder-1",
                DateTimeOffset.UtcNow,
                null,
                1
            ),
            0,
            CancellationToken.None
        );
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            membership,
            trials,
            approvals: approvals
        );

        var result = await controller.ContinueAsync(
            ValidRequest("TRIAL"),
            Guid.NewGuid(),
            Guid.NewGuid(),
            CancellationToken.None
        );

        Assert.Equal(StatusCodes.Status409Conflict, Assert.IsType<ObjectResult>(result).StatusCode);
        var listed = Assert.Single(await approvals.ListAsync(CancellationToken.None));
        Assert.True(listed.DefinitionChanged);
        Assert.Contains(PlatformApprovalActions.Approve, listed.Actions);
    }

    private static (
        InMemoryEmploymentRelationshipFactory Factory,
        EmploymentRelationshipService Relationships,
        RelationshipTrialService Trials,
        CustomerWorkspaceMembership Membership,
        TrialOwnerGatewayStub Owners
    ) TrialHarness()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var relationships = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance
        );
        var startsAt = DateTimeOffset.UtcNow;
        var trialId = Guid.NewGuid();
        var owners = new TrialOwnerGatewayStub
        {
            Wbe = new(trialId, startsAt, startsAt.AddDays(14)),
            Pr = new(trialId, "TRIAL_DEMONSTRATING", startsAt.AddDays(14)),
        };
        return (
            factory,
            relationships,
            new RelationshipTrialService(factory, relationships, owners),
            new CustomerWorkspaceMembership(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                ["OWNER"]
            ),
            owners
        );
    }

    private static PlatformProfessionalApprovalService Approvals(
        InMemoryEmploymentRelationshipFactory factory,
        out InMemoryPlatformProfessionalApprovalStore store
    )
    {
        store = new InMemoryPlatformProfessionalApprovalStore();
        return new PlatformProfessionalApprovalService(
            Catalog(),
            store,
            factory,
            TimeProvider.System
        );
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

    private static FakePackageCatalogGateway DefaultPackages() =>
        new(
            HireQuoteFixtures.Package("GROWTH", 354000),
            HireQuoteFixtures.Package("STARTER", 118000)
        );

    private static CustomerWorkspaceMembership NewMembership() =>
        new(Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), ["OWNER"]);

    private static async Task<AcquisitionIntent> OnlyIntentAsync(
        InMemoryEmploymentRelationshipFactory factory
    )
    {
        await using var db = factory.CreateDbContext();
        return Assert.Single(await db.AcquisitionIntents.AsNoTracking().ToListAsync());
    }

    private static (
        InMemoryEmploymentRelationshipFactory Factory,
        EmploymentRelationshipService Relationships
    ) NewServices()
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        return (
            factory,
            new EmploymentRelationshipService(
                factory,
                new RecordingRelationshipConstitutionalGateway(),
                NullLogger<EmploymentRelationshipService>.Instance
            )
        );
    }

    [Fact]
    public async Task WC169_R013_AHireLocksTheLowestPricedPackageForSaleAndTheContractHashBindsIt()
    {
        var (factory, relationships) = NewServices();
        var membership = NewMembership();
        var controller = Controller(factory, Catalog(), relationships, membership);
        var key = Guid.NewGuid();

        var created = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(ValidRequest("HIRE"), key, CancellationToken.None)
        );

        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        var body = Assert.IsType<AcquisitionIntentResponse>(created.Value);
        Assert.Equal("STARTER", body.Quote!.PackageCode);
        Assert.Equal(118000, body.Quote.GrossAmountInrPaise);
        Assert.Equal(18000, body.Quote.GstAmountInrPaise);
        Assert.Equal("INR", body.Quote.Currency);
        Assert.Equal("MONTHLY", body.Quote.Cadence);
        var stored = await OnlyIntentAsync(factory);
        Assert.Equal(membership.TenantId, stored.TenantId);
        Assert.Equal(membership.AccountId, stored.ParticipantId);
        Assert.Equal(body.Quote.QuoteVersion, stored.QuoteVersion);
        Assert.Equal(118000, stored.QuoteGrossInrPaise);

        // Same disclosure, different package price: a different contract hash.
        var (otherFactory, otherRelationships) = NewServices();
        var dearer = Controller(
            otherFactory,
            Catalog(),
            otherRelationships,
            membership,
            packages: new FakePackageCatalogGateway(HireQuoteFixtures.Package("STARTER", 129800))
        );
        await dearer.CreateIntentAsync(ValidRequest("HIRE"), key, CancellationToken.None);
        Assert.NotEqual(stored.ContractHash, (await OnlyIntentAsync(otherFactory)).ContractHash);
    }

    [Fact]
    public async Task WC169_R013_AnExplicitPackageCodeIsLockedAndAnUnknownOneIsRefused()
    {
        var (factory, relationships) = NewServices();
        var controller = Controller(factory, Catalog(), relationships, NewMembership());

        var refused = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE") with
                {
                    PackageCode = "FORGED",
                },
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        var accepted = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE") with
                {
                    PackageCode = "GROWTH",
                },
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(StatusCodes.Status409Conflict, refused.StatusCode);
        Assert.Equal(
            354000,
            Assert.IsType<AcquisitionIntentResponse>(accepted.Value).Quote!.GrossAmountInrPaise
        );
        Assert.Equal("GROWTH", (await OnlyIntentAsync(factory)).QuotePackageCode);
    }

    [Fact]
    public async Task WC169_R013_AFounderChosenPackageCodeWithMixedCaseDashAndDotIsLocked()
    {
        var (factory, relationships) = NewServices();
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            NewMembership(),
            packages: new FakePackageCatalogGateway(
                HireQuoteFixtures.Package("Starter-Monthly.1", 118000)
            )
        );

        var accepted = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE") with
                {
                    PackageCode = "Starter-Monthly.1",
                },
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(
            "Starter-Monthly.1",
            Assert.IsType<AcquisitionIntentResponse>(accepted.Value).Quote!.PackageCode
        );
        Assert.Equal("Starter-Monthly.1", (await OnlyIntentAsync(factory)).QuotePackageCode);
    }

    [Fact]
    public async Task WC169_R013_WithNoPackageForSaleThereIsNoAmountAndNoHire()
    {
        var (factory, relationships) = NewServices();
        var membership = NewMembership();
        await SeedAdmissionAsync(factory, membership.TenantId);
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            membership,
            packages: new FakePackageCatalogGateway()
        );

        var intent = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE"),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        var continuation = Assert.IsType<ObjectResult>(
            await controller.ContinueAsync(
                ValidRequest("HIRE"),
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(StatusCodes.Status409Conflict, intent.StatusCode);
        Assert.Equal(StatusCodes.Status409Conflict, continuation.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.AcquisitionIntents);
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task WC169_R013_AnOwnerOutageIsUnavailableWithNoAmountNoHireAndNoDescriptorFallback()
    {
        var (factory, relationships) = NewServices();
        var membership = NewMembership();
        await SeedAdmissionAsync(factory, membership.TenantId);
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            membership,
            packages: new FakePackageCatalogGateway(HireQuoteFixtures.Package("STARTER", 118000))
            {
                Failure = new PackageCatalogUnavailableException("billing owner is down"),
            }
        );

        var intent = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE"),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        var continuation = Assert.IsType<ObjectResult>(
            await controller.ContinueAsync(
                ValidRequest("HIRE"),
                Guid.NewGuid(),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        var preview = Assert.IsType<ObjectResult>(
            await controller.PreviewHireQuoteAsync(
                new HireQuoteRequest(HireQuoteFixtures.AgentType, HireQuoteFixtures.AgentVersion),
                null,
                CancellationToken.None
            )
        );

        Assert.All(
            new[] { intent, continuation, preview },
            result => Assert.Equal(StatusCodes.Status503ServiceUnavailable, result.StatusCode)
        );
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.AcquisitionIntents);
        Assert.Empty(db.EmploymentRelationships);
    }

    [Fact]
    public async Task WC169_R013_AHireWithoutACustomerWorkspaceIsNeverPriced()
    {
        var (factory, relationships) = NewServices();
        var controller = Controller(factory, Catalog(), relationships, null);

        var result = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE"),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(StatusCodes.Status409Conflict, result.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.AcquisitionIntents);
    }

    [Fact]
    public async Task WC169_R013_APriceChangeBeforeChargingNeedsRenewedAcceptanceButAPaidHireKeepsItsLockedPrice()
    {
        var (factory, relationships) = NewServices();
        var membership = NewMembership();
        await SeedAdmissionAsync(factory, membership.TenantId);
        var packages = DefaultPackages();
        var controller = Controller(
            factory,
            Catalog(),
            relationships,
            membership,
            packages: packages
        );
        var key = Guid.NewGuid();
        await controller.CreateIntentAsync(ValidRequest("HIRE"), key, CancellationToken.None);
        var locked = await OnlyIntentAsync(factory);

        // The Founder changes the price after acceptance.
        packages.Packages.Clear();
        packages.Packages.Add(HireQuoteFixtures.Package("STARTER", 129800));

        var beforeCharging = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE") with
                {
                    ValidateQuoteBeforeCharge = true,
                },
                key,
                CancellationToken.None
            )
        );
        Assert.Equal(StatusCodes.Status409Conflict, beforeCharging.StatusCode);

        // Confirming a payment that was already taken replays the locked quote and completes at that price.
        var replay = Assert.IsType<OkObjectResult>(
            await controller.CreateIntentAsync(ValidRequest("HIRE"), key, CancellationToken.None)
        );
        Assert.Equal(
            118000,
            Assert.IsType<AcquisitionIntentResponse>(replay.Value).Quote!.GrossAmountInrPaise
        );
        var completed = Assert.IsType<ObjectResult>(
            await controller.ContinueAsync(ValidRequest("HIRE"), key, key, CancellationToken.None)
        );
        Assert.Equal(StatusCodes.Status201Created, completed.StatusCode);
        var after = await OnlyIntentAsync(factory);
        Assert.Equal(locked.QuoteVersion, after.QuoteVersion);
        Assert.Equal(118000, after.QuoteGrossInrPaise);
        Assert.Equal("COMPLETED", after.Status);
    }

    [Fact]
    public async Task WC169_R013_AnUnchangedQuotePassesTheBeforeChargingCheck()
    {
        var (factory, relationships) = NewServices();
        var controller = Controller(factory, Catalog(), relationships, NewMembership());
        var key = Guid.NewGuid();
        var request = ValidRequest("HIRE") with { ValidateQuoteBeforeCharge = true };
        await controller.CreateIntentAsync(request, key, CancellationToken.None);

        var replay = await controller.CreateIntentAsync(request, key, CancellationToken.None);

        Assert.True(
            Assert
                .IsType<AcquisitionIntentResponse>(Assert.IsType<OkObjectResult>(replay).Value)
                .Replayed
        );
    }

    [Fact]
    public async Task WC169_R013_AQuoteVersionTheCustomerDidNotSeeIsRefused()
    {
        var (factory, relationships) = NewServices();
        var controller = Controller(factory, Catalog(), relationships, NewMembership());

        var result = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("HIRE") with
                {
                    QuoteVersion = new string('0', 64),
                },
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Equal(StatusCodes.Status409Conflict, result.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.AcquisitionIntents);
    }

    [Fact]
    public async Task WC169_R013_AHireIntentWithoutALockedQuoteCannotComplete()
    {
        var (factory, relationships) = NewServices();
        var membership = NewMembership();
        await SeedAdmissionAsync(factory, membership.TenantId);
        var key = Guid.NewGuid();
        var request = ValidRequest("HIRE");
        var controller = Controller(factory, Catalog(), relationships, membership);
        await controller.CreateIntentAsync(request, key, CancellationToken.None);
        await using (var db = factory.CreateDbContext())
        {
            // A row from before quotes existed: same identity, no locked price.
            var original = await db.AcquisitionIntents.SingleAsync();
            db.AcquisitionIntents.Remove(original);
            db.AcquisitionIntents.Add(
                new AcquisitionIntent
                {
                    AcquisitionIntentId = original.AcquisitionIntentId,
                    ActorIdentityHash = original.ActorIdentityHash,
                    IdempotencyKey = original.IdempotencyKey,
                    TenantId = original.TenantId,
                    ParticipantId = original.ParticipantId,
                    ProfessionalType = original.ProfessionalType,
                    ProfessionalVersion = original.ProfessionalVersion,
                    Mode = original.Mode,
                    DisclosureRevision = original.DisclosureRevision,
                    ContractVersion = original.ContractVersion,
                    ContractHash = original.ContractHash,
                    MaterialRequestHash = original.MaterialRequestHash,
                    ContractAcceptedAt = original.ContractAcceptedAt,
                    ExpiresAt = original.ExpiresAt,
                }
            );
            await db.SaveChangesAsync();
        }

        var replay = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(request, key, CancellationToken.None)
        );
        var completion = Assert.IsType<ObjectResult>(
            await controller.ContinueAsync(request, key, key, CancellationToken.None)
        );

        Assert.Equal(StatusCodes.Status409Conflict, replay.StatusCode);
        Assert.Equal(StatusCodes.Status409Conflict, completion.StatusCode);
        await using var check = factory.CreateDbContext();
        Assert.Empty(check.EmploymentRelationships);
    }

    [Fact]
    public async Task WC169_R013_APreviewQuoteIsServerResolvedAndStoresNothing()
    {
        var (factory, relationships) = NewServices();
        var controller = Controller(factory, Catalog(), relationships, NewMembership());

        var ok = Assert.IsType<OkObjectResult>(
            await controller.PreviewHireQuoteAsync(
                new HireQuoteRequest(HireQuoteFixtures.AgentType, HireQuoteFixtures.AgentVersion),
                null,
                CancellationToken.None
            )
        );
        var stale = Assert.IsType<ObjectResult>(
            await controller.PreviewHireQuoteAsync(
                new HireQuoteRequest(HireQuoteFixtures.AgentType, "9.9.9"),
                null,
                CancellationToken.None
            )
        );

        Assert.Equal(118000, Assert.IsType<HireQuoteResponse>(ok.Value).GrossAmountInrPaise);
        Assert.Equal(StatusCodes.Status409Conflict, stale.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.AcquisitionIntents);
    }

    [Fact]
    public async Task WC169_R013_ATrialCarriesNoPrice()
    {
        var (factory, relationships) = NewServices();
        var controller = Controller(factory, Catalog(), relationships, null);

        var created = Assert.IsType<ObjectResult>(
            await controller.CreateIntentAsync(
                ValidRequest("TRIAL"),
                Guid.NewGuid(),
                CancellationToken.None
            )
        );

        Assert.Null(Assert.IsType<AcquisitionIntentResponse>(created.Value).Quote);
        Assert.Null((await OnlyIntentAsync(factory)).QuoteVersion);
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
        RelationshipTrialService? trials = null,
        FakePackageCatalogGateway? packages = null,
        PlatformProfessionalApprovalService? approvals = null
    )
    {
        var controller = new AcquisitionController(
            factory,
            catalog,
            relationships,
            NullLogger<AcquisitionController>.Instance,
            trials,
            new HireQuoteService(packages ?? DefaultPackages()),
            approvals
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
