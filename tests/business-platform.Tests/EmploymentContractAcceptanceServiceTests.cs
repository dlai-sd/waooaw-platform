// Implements: work-contracts/WC-059-goal005-ae01-contract-payment-activation.md §WC059-03
// constitutional_basis: C-009, C-010, C-011, C-023, C-026, C-059

using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using System.Security.Claims;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentContractAcceptanceServiceTests
{
    [Fact]
    public async Task ExactContractAndSeparateScopeConfirmationCommitEvidenceAndAcceptance()
    {
        var context = await CreateContextAsync(RelationshipParticipantRole.Employer);

        var result = await context.Service.AcceptAsync(
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            context.Contract.ContractId,
            context.Contract.Version,
            context.Contract.ContractHash,
            ContractScopeConfirmation.ExplicitStatement,
            new ContractPortalAssurance(true, DateTimeOffset.UtcNow),
            context.CorrelationId,
            CancellationToken.None);

        Assert.True(result.Created);
        Assert.Equal("AAL3_FRESH", result.Acceptance.AuthenticationAssurance);
        Assert.Equal(RelationshipParticipantRole.Employer, result.Acceptance.ParticipantRole);
        Assert.Equal(64, result.Acceptance.ScopeConfirmationHash.Length);
        Assert.Equal(1, context.Gateway.CallCount);

        await using var db = context.Factory.CreateDbContext();
        var relationship = await db.EmploymentRelationships.SingleAsync();
        Assert.Equal(EmploymentRelationshipState.ContractAcceptedPendingPayment, relationship.State);
        Assert.Equal(context.Contract.ContractId, relationship.AcceptedContractId);
        Assert.Single(await db.ContractAcceptances.ToListAsync());
        var history = await db.RelationshipStateHistory.SingleAsync();
        Assert.Equal(result.Acceptance.AcceptanceEvidenceId, history.EvidenceId);
    }

    [Fact]
    public async Task ExactReplayReturnsStoredAcceptanceWithoutSecondEvidence()
    {
        var context = await CreateContextAsync(RelationshipParticipantRole.Employer);
        var first = await AcceptAsync(context);
        var replay = await AcceptAsync(context);

        Assert.True(first.Created);
        Assert.False(replay.Created);
        Assert.Equal(first.Acceptance.AcceptanceId, replay.Acceptance.AcceptanceId);
        Assert.Equal(1, context.Gateway.CallCount);
    }

    [Theory]
    [InlineData(false, 0)]
    [InlineData(true, -6)]
    public async Task NonPortalOrStaleAuthenticationHasZeroMutation(bool isPortal, int authAgeMinutes)
    {
        var context = await CreateContextAsync(RelationshipParticipantRole.Employer);

        await Assert.ThrowsAsync<ContractStepUpRequiredException>(() => context.Service.AcceptAsync(
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            context.Contract.ContractId,
            context.Contract.Version,
            context.Contract.ContractHash,
            ContractScopeConfirmation.ExplicitStatement,
            new ContractPortalAssurance(isPortal, DateTimeOffset.UtcNow.AddMinutes(authAgeMinutes)),
            context.CorrelationId,
            CancellationToken.None));

        Assert.Equal(0, context.Gateway.CallCount);
        await AssertUnchangedAsync(context);
    }

    [Fact]
    public async Task NonEmployerOrMismatchedContractHasZeroMutation()
    {
        var context = await CreateContextAsync(RelationshipParticipantRole.Evaluator);

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => AcceptAsync(context));
        Assert.Equal(0, context.Gateway.CallCount);
        await AssertUnchangedAsync(context);

        var employerContext = await CreateContextAsync(RelationshipParticipantRole.Employer);
        await Assert.ThrowsAsync<ContractIdentityMismatchException>(() => employerContext.Service.AcceptAsync(
            employerContext.TenantId,
            employerContext.RelationshipId,
            employerContext.ParticipantId,
            employerContext.Contract.ContractId,
            employerContext.Contract.Version,
            new string('f', 64),
            ContractScopeConfirmation.ExplicitStatement,
            new ContractPortalAssurance(true, DateTimeOffset.UtcNow),
            employerContext.CorrelationId,
            CancellationToken.None));

        Assert.Equal(0, employerContext.Gateway.CallCount);
        await AssertUnchangedAsync(employerContext);
    }

    [Fact]
    public async Task MissingScopeOrEvidenceFailureHasZeroMutation()
    {
        var context = await CreateContextAsync(RelationshipParticipantRole.Employer);

        await Assert.ThrowsAsync<ContractScopeConfirmationRequiredException>(() => context.Service.AcceptAsync(
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            context.Contract.ContractId,
            context.Contract.Version,
            context.Contract.ContractHash,
            "",
            new ContractPortalAssurance(true, DateTimeOffset.UtcNow),
            context.CorrelationId,
            CancellationToken.None));
        context.Gateway.FailNext = true;
        await Assert.ThrowsAsync<InvalidOperationException>(() => AcceptAsync(context));

        Assert.Equal(1, context.Gateway.CallCount);
        await AssertUnchangedAsync(context);
    }

    [Theory]
    [InlineData(null, null)]
    [InlineData("whatsapp", 0)]
    [InlineData(null, -6)]
    public async Task EndpointRejectsNonPortalOrNonFreshSession(string? identityProvider, int? authAgeMinutes)
    {
        var context = await CreateContextAsync(RelationshipParticipantRole.Employer);
        var controller = CreateController(context, identityProvider, authAgeMinutes);

        var result = await controller.AcceptContractAsync(
            context.RelationshipId,
            context.Contract.Version,
            new AcceptEmploymentContractRequest(
                context.Contract.ContractHash,
                ContractScopeConfirmation.ExplicitStatement),
            CancellationToken.None);

        var denied = Assert.IsType<ObjectResult>(result);
        Assert.Equal(StatusCodes.Status403Forbidden, denied.StatusCode);
        Assert.Equal(0, context.Gateway.CallCount);
        await AssertUnchangedAsync(context);
    }

    [Fact]
    public async Task FreshPortalEndpointAcceptsExactPresentedVersion()
    {
        var context = await CreateContextAsync(RelationshipParticipantRole.Employer);
        var controller = CreateController(context, null, 0);

        var result = await controller.AcceptContractAsync(
            context.RelationshipId,
            context.Contract.Version,
            new AcceptEmploymentContractRequest(
                context.Contract.ContractHash,
                ContractScopeConfirmation.ExplicitStatement),
            CancellationToken.None);

        var created = Assert.IsType<ObjectResult>(result);
        Assert.Equal(StatusCodes.Status201Created, created.StatusCode);
        var response = Assert.IsType<ContractAcceptanceResponse>(created.Value);
        Assert.Equal(context.Contract.ContractHash, response.ContractHash);
        Assert.Equal("AAL3_FRESH", response.AuthenticationAssurance);
    }

    private static Task<ContractAcceptanceResult> AcceptAsync(AcceptanceTestContext context) =>
        context.Service.AcceptAsync(
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            context.Contract.ContractId,
            context.Contract.Version,
            context.Contract.ContractHash,
            ContractScopeConfirmation.ExplicitStatement,
            new ContractPortalAssurance(true, DateTimeOffset.UtcNow),
            context.CorrelationId,
            CancellationToken.None);

    private static async Task AssertUnchangedAsync(AcceptanceTestContext context)
    {
        await using var db = context.Factory.CreateDbContext();
        Assert.Empty(await db.ContractAcceptances.ToListAsync());
        var relationship = await db.EmploymentRelationships.SingleAsync();
        Assert.Equal(EmploymentRelationshipState.ContractPendingAcceptance, relationship.State);
        Assert.Null(relationship.AcceptedContractId);
    }

    private static EmploymentRelationshipsController CreateController(
        AcceptanceTestContext context,
        string? identityProvider,
        int? authAgeMinutes)
    {
        var claims = new List<Claim>
        {
            new("participant_id", context.ParticipantId.ToString("D")),
        };
        if (identityProvider is not null)
        {
            claims.Add(new Claim("identity_provider", identityProvider));
        }
        if (authAgeMinutes.HasValue)
        {
            claims.Add(new Claim(
                "auth_time",
                DateTimeOffset.UtcNow.AddMinutes(authAgeMinutes.Value).ToUnixTimeSeconds().ToString()));
        }

        var relationships = new EmploymentRelationshipService(
            context.Factory,
            context.Gateway,
            Microsoft.Extensions.Logging.Abstractions.NullLogger<EmploymentRelationshipService>.Instance);
        var contracts = new EmploymentContractService(context.Factory, new AcceptanceProfessionalCatalogStub());
        var controller = new EmploymentRelationshipsController(
            relationships,
            contracts: contracts,
            contractAcceptances: context.Service)
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test")),
                },
            },
        };
        controller.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = context.TenantId.ToString("D");
        return controller;
    }

    private static async Task<AcceptanceTestContext> CreateContextAsync(RelationshipParticipantRole role)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var contract = new EmploymentContractVersion
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Version = 1,
            ContractHash = new string('a', 64),
            AeecVersion = "1.0",
            DomainScheduleHash = new string('b', 64),
            ConfigurationSnapshotJson = "{}",
            PriceTaxSummaryJson = "{}",
            CreatedByParticipantId = participantId,
        };
        await using var db = factory.CreateDbContext();
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = participantId,
            State = EmploymentRelationshipState.ContractPendingAcceptance,
            StateVersion = 4,
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = role,
            BoundEvidenceId = Guid.NewGuid(),
        });
        db.DecisionSpaceSnapshots.Add(new DecisionSpaceSnapshot
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            Version = 1,
            BudgetCeilingInrPaise = 250000,
            AuthorityBoundariesJson = "[]",
            StopConditionsJson = "[]",
            AcceptedEvidenceJson = "[]",
            CreatedByParticipantId = participantId,
            EvidenceId = Guid.NewGuid(),
        });
        db.EmploymentContractVersions.Add(contract);
        await db.SaveChangesAsync();
        return new AcceptanceTestContext(
            new EmploymentContractAcceptanceService(factory, gateway),
            factory,
            gateway,
            tenantId,
            relationshipId,
            participantId,
            contract,
            Guid.NewGuid());
    }

    private sealed record AcceptanceTestContext(
        EmploymentContractAcceptanceService Service,
        InMemoryEmploymentRelationshipFactory Factory,
        RecordingRelationshipConstitutionalGateway Gateway,
        Guid TenantId,
        Guid RelationshipId,
        Guid ParticipantId,
        EmploymentContractVersion Contract,
        Guid CorrelationId);

    private sealed class AcceptanceProfessionalCatalogStub : IProfessionalCatalog
    {
        public IReadOnlyList<ProfessionalDiscoveryResult> Discover(string outcome) => [];

        public ProfessionalDisclosure? GetDisclosure(string professionalType) => null;
    }
}