// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-005, C-023, C-036, C-059, C-076
using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class EmploymentControllerCoverageTests
{
    private sealed class SkillFactory(DbContextOptions<SkillCatalogDbContext> options)
        : IDbContextFactory<SkillCatalogDbContext>
    {
        public SkillCatalogDbContext CreateDbContext() => new(options);
    }

    [Fact]
    public async Task RelationshipGetAndTimeline_ReturnCanonicalStateHistory()
    {
        var fixture = await CreateAsync();

        var get = Assert.IsType<OkObjectResult>(await fixture.Controller.GetAsync(
            fixture.RelationshipId, CancellationToken.None));
        var timeline = Assert.IsType<OkObjectResult>(await fixture.Controller.GetTimelineAsync(
            fixture.RelationshipId, CancellationToken.None));
        var missing = await fixture.Controller.GetAsync(Guid.NewGuid(), CancellationToken.None);
        var missingTimeline = await fixture.Controller.GetTimelineAsync(Guid.NewGuid(), CancellationToken.None);

        Assert.Equal("DISCOVERED", Assert.IsType<EmploymentRelationshipResponse>(get.Value).State);
        Assert.NotEmpty(Assert.IsAssignableFrom<IEnumerable<RelationshipTimelineEntryResponse>>(timeline.Value));
        Assert.IsType<NotFoundResult>(missing);
        Assert.IsType<NotFoundResult>(missingTimeline);
    }

    [Fact]
    public async Task RelationshipTransition_HandlesSuccessConflictAndMissingRelationship()
    {
        var fixture = await CreateAsync();
        var request = new TransitionEmploymentRelationshipRequest(
            EmploymentRelationshipState.Interviewing,
            fixture.ParticipantId,
            RelationshipParticipantRole.Evaluator,
            Guid.NewGuid());

        var transitioned = Assert.IsType<OkObjectResult>(await fixture.Controller.TransitionAsync(
            fixture.RelationshipId, request, CancellationToken.None));
        var conflict = await fixture.Controller.TransitionAsync(
            fixture.RelationshipId,
            request with { TargetState = EmploymentRelationshipState.Active, CorrelationId = Guid.NewGuid() },
            CancellationToken.None);
        var missing = await fixture.Controller.TransitionAsync(
            Guid.NewGuid(),
            request with { CorrelationId = Guid.NewGuid() },
            CancellationToken.None);

        Assert.Equal("INTERVIEWING", Assert.IsType<EmploymentRelationshipResponse>(transitioned.Value).State);
        Assert.IsType<ConflictObjectResult>(conflict);
        Assert.IsType<NotFoundResult>(missing);
    }

    [Fact]
    public async Task OptionalRelationshipOwners_ReturnServiceUnavailable()
    {
        var fixture = await CreateAsync(includeContinuityClaims: true);
        var commercialTerms = new EmploymentContractCommercialTerms(
            "INR", 100, 10, "monthly", "standard", "excluded", "non-refundable");

        var prepare = await fixture.Controller.PrepareHandoffAsync(
            fixture.RelationshipId,
            Guid.NewGuid().ToString(),
            new PrepareRelationshipHandoffRequest("WEB", "conversation", "continue"),
            CancellationToken.None);
        var activate = await fixture.Controller.ActivateHandoffAsync(
            fixture.RelationshipId,
            Guid.NewGuid(),
            Guid.NewGuid().ToString(),
            new ActivateRelationshipHandoffRequest("conversation"),
            CancellationToken.None);
        var stop = await fixture.Controller.StopAsync(
            fixture.RelationshipId, new StopEmploymentRelationshipRequest(), CancellationToken.None);
        var trial = await fixture.Controller.StartTrialAsync(
            fixture.RelationshipId, new StartRelationshipTrialRequest(), CancellationToken.None);
        var contract = await fixture.Controller.ProposeContractAsync(
            fixture.RelationshipId, new ProposeEmploymentContractRequest(commercialTerms), CancellationToken.None);
        var journey = await fixture.Controller.GetContractJourneyAsync(
            fixture.RelationshipId, CancellationToken.None);
        var acceptance = await fixture.Controller.AcceptContractAsync(
            fixture.RelationshipId,
            1,
            new AcceptEmploymentContractRequest("hash", "confirmed"),
            CancellationToken.None);
        var payment = await fixture.Controller.CreateOnboardingPaymentOrderAsync(
            fixture.RelationshipId,
            1,
            new PaymentProceedRequest("STARTER", 100, 10, "PROCEED"),
            CancellationToken.None);
        var activation = await fixture.Controller.StartPaidActivationAsync(
            fixture.RelationshipId,
            new StartPaidActivationRequest("payment", Guid.NewGuid()),
            CancellationToken.None);

        AssertStatus(prepare, 503);
        AssertStatus(activate, 503);
        AssertStatus(stop, 503);
        AssertStatus(trial, 503);
        AssertStatus(contract, 503);
        AssertStatus(journey, 503);
        AssertStatus(acceptance, 503);
        AssertStatus(payment, 503);
        AssertStatus(activation, 503);
    }

    [Fact]
    public async Task RelationshipEndpoints_RejectMissingTenantOrParticipantIdentity()
    {
        var fixture = await CreateAsync();
        fixture.Controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };

        Assert.IsType<ForbidResult>(await fixture.Controller.AdmitAsync(
            new AdmitEmploymentRelationshipRequest(Guid.NewGuid(), "DMA"), CancellationToken.None));
        Assert.IsType<ForbidResult>(await fixture.Controller.GetAsync(
            fixture.RelationshipId, CancellationToken.None));
        Assert.IsType<ForbidResult>(await fixture.Controller.GetTimelineAsync(
            fixture.RelationshipId, CancellationToken.None));
        Assert.IsType<ForbidResult>(await fixture.Controller.StartTrialAsync(
            fixture.RelationshipId, new StartRelationshipTrialRequest(), CancellationToken.None));
        Assert.IsType<ForbidResult>(await fixture.Controller.ReleaseStopAsync(
            fixture.RelationshipId,
            new ReleaseEmploymentRelationshipStopRequest(
                Guid.NewGuid(), Guid.NewGuid(), "release", "resolved", EmploymentRelationshipState.Active),
            CancellationToken.None));
    }

    [Fact]
    public async Task RelationshipIdentityGuards_RejectEachMalformedContinuityBoundary()
    {
        var fixture = await CreateAsync();
        var tenantValues = new object?[] { null, fixture.TenantId, "not-a-uuid" };
        foreach (var tenantValue in tenantValues)
        {
            var context = Context(fixture.TenantId, fixture.ParticipantId, includeContinuityClaims: true);
            if (tenantValue is null)
                context.HttpContext.Items.Remove(TenantIsolationMiddleware.TenantIdItemKey);
            else
                context.HttpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantValue;
            fixture.Controller.ControllerContext = context;
            Assert.IsType<ForbidResult>(await fixture.Controller.GetAsync(
                fixture.RelationshipId, CancellationToken.None));
        }

        var claimCases = new[]
        {
            "participant_id", "channel", "conversation_id", "external_subject_hash",
            "authentication_assurance", "auth_time",
        };
        foreach (var claimType in claimCases)
        {
            var context = Context(fixture.TenantId, fixture.ParticipantId, includeContinuityClaims: true);
            var identity = (ClaimsIdentity)context.HttpContext.User.Identity!;
            foreach (var claim in identity.FindAll(claimType).ToList()) identity.RemoveClaim(claim);
            fixture.Controller.ControllerContext = context;
            Assert.IsType<ForbidResult>(await fixture.Controller.PrepareHandoffAsync(
                fixture.RelationshipId,
                Guid.NewGuid().ToString(),
                new PrepareRelationshipHandoffRequest("WEB", "conversation", "continue"),
                CancellationToken.None));
        }

        foreach (var (claimType, replacement) in new[]
        {
            ("participant_id", "not-a-uuid"),
            ("external_subject_hash", "short"),
            ("auth_time", "not-a-number"),
        })
        {
            var context = Context(fixture.TenantId, fixture.ParticipantId, includeContinuityClaims: true);
            var identity = (ClaimsIdentity)context.HttpContext.User.Identity!;
            foreach (var claim in identity.FindAll(claimType).ToList()) identity.RemoveClaim(claim);
            identity.AddClaim(new Claim(claimType, replacement));
            fixture.Controller.ControllerContext = context;
            Assert.IsType<ForbidResult>(await fixture.Controller.PrepareHandoffAsync(
                fixture.RelationshipId,
                Guid.NewGuid().ToString(),
                new PrepareRelationshipHandoffRequest("WEB", "conversation", "continue"),
                CancellationToken.None));
        }
    }

    [Fact]
    public async Task RelationshipIdentityGuards_UseNameIdentifierAndRejectBadEnvelopes()
    {
        var fixture = await CreateAsync();
        var context = Context(fixture.TenantId, fixture.ParticipantId, includeContinuityClaims: true);
        var identity = (ClaimsIdentity)context.HttpContext.User.Identity!;
        foreach (var claim in identity.FindAll("participant_id").ToList()) identity.RemoveClaim(claim);
        identity.AddClaim(new Claim(ClaimTypes.NameIdentifier, fixture.ParticipantId.ToString()));
        fixture.Controller.ControllerContext = context;
        AssertStatus(await fixture.Controller.PrepareHandoffAsync(
            fixture.RelationshipId,
            "not-a-uuid",
            new PrepareRelationshipHandoffRequest("WEB", "conversation", "continue"),
            CancellationToken.None), 503);

        var continuity = new ChannelContinuityService(
            new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N")),
            new RecordingRelationshipConstitutionalGateway(),
            Options.Create(new ChannelContinuityOptions
            {
                EnvelopeHmacKey = Convert.ToBase64String(new byte[32]),
            }));
        var controller = new EmploymentRelationshipsController(fixture.Service, continuity: continuity);

        foreach (var envelope in new string?[] { null, " ", "{invalid", "null" })
        {
            context = Context(fixture.TenantId, fixture.ParticipantId, includeContinuityClaims: true);
            identity = (ClaimsIdentity)context.HttpContext.User.Identity!;
            if (envelope is not null) identity.AddClaim(new Claim("continuity_envelope", envelope));
            controller.ControllerContext = context;
            Assert.IsType<ForbidResult>(await controller.ActivateHandoffAsync(
                fixture.RelationshipId,
                Guid.NewGuid(),
                Guid.NewGuid().ToString(),
                new ActivateRelationshipHandoffRequest("conversation"),
                CancellationToken.None));
        }

        var validEnvelope = JsonSerializer.Serialize(new NeutralContinuityEnvelope(
            "1.0", fixture.TenantId, fixture.RelationshipId, fixture.ParticipantId, "EMPLOYER",
            "TIER_4_PORTAL_FRESH", Guid.NewGuid(), "WEB", "source", "WEB", "conversation",
            "continue", Guid.NewGuid(), Guid.NewGuid(), 1, Guid.NewGuid(), Guid.NewGuid(),
            Guid.NewGuid(), DateTimeOffset.UtcNow, new string('a', 64)));
        context = Context(fixture.TenantId, fixture.ParticipantId, includeContinuityClaims: true);
        ((ClaimsIdentity)context.HttpContext.User.Identity!).AddClaim(
            new Claim("continuity_envelope", validEnvelope));
        controller.ControllerContext = context;
        Assert.IsType<NotFoundResult>(await controller.ActivateHandoffAsync(
            fixture.RelationshipId, Guid.NewGuid(), Guid.NewGuid().ToString(),
            new ActivateRelationshipHandoffRequest("conversation"), CancellationToken.None));
    }

    [Fact]
    public async Task EmergencyReleaseAuthorization_CoversEveryOptionalBoundaryAndPortalPosture()
    {
        for (var boundary = 0; boundary < 6; boundary++)
        {
            var fixture = await CreateAsync();
            var request = new TransitionEmploymentRelationshipRequest(
                EmploymentRelationshipState.Interviewing,
                fixture.ParticipantId,
                RelationshipParticipantRole.Evaluator,
                Guid.NewGuid(),
                ExplicitEmergencyRelease: boundary > 0,
                OriginatingStopEvidenceId: boundary > 1 ? Guid.NewGuid() : null,
                OriginatingStopCorrelationId: boundary > 2 ? Guid.NewGuid() : null,
                ReleaseConfirmation: boundary > 3 ? "release" : null,
                ReleaseJustification: boundary > 4 ? "resolved" : null);

            Assert.IsType<OkObjectResult>(await fixture.Controller.TransitionAsync(
                fixture.RelationshipId, request, CancellationToken.None));
        }

        foreach (var (clientType, provider, authTime) in new[]
        {
            ("service", "keycloak", "not-a-number"),
            ("browser", "whatsapp", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString()),
            ("browser", "keycloak", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString()),
        })
        {
            var fixture = await CreateAsync();
            var identity = (ClaimsIdentity)fixture.Controller.User.Identity!;
            identity.AddClaim(new Claim("client_type", clientType));
            identity.AddClaim(new Claim("identity_provider", provider));
            foreach (var claim in identity.FindAll("auth_time").ToList()) identity.RemoveClaim(claim);
            identity.AddClaim(new Claim("auth_time", authTime));
            var request = new TransitionEmploymentRelationshipRequest(
                EmploymentRelationshipState.Interviewing,
                fixture.ParticipantId,
                RelationshipParticipantRole.Evaluator,
                Guid.NewGuid(),
                true,
                Guid.NewGuid(),
                Guid.NewGuid(),
                "release",
                "resolved");

            Assert.IsType<OkObjectResult>(await fixture.Controller.TransitionAsync(
                fixture.RelationshipId, request, CancellationToken.None));
        }
    }

    [Fact]
    public async Task LegacyCustomerContracts_FormReplayAndReadCanonicalRelationship()
    {
        var fixture = await CreateAsync();
        var skills = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var controller = CustomerController(fixture, skills);
        var request = new LegacyFormEmploymentContractRequest(
            Guid.NewGuid(), new LegacyDecisionSpaceInput("DMA"), Guid.NewGuid());

        var created = Assert.IsType<CreatedAtActionResult>(await controller.FormEmploymentContract(
            request, CancellationToken.None));
        var relationshipId = JsonSerializer.SerializeToElement(created.Value)
            .GetProperty("relationshipId")
            .GetGuid();
        var replay = await controller.FormEmploymentContract(request, CancellationToken.None);
        var read = await controller.GetEmploymentContract(relationshipId, CancellationToken.None);

        Assert.IsType<OkObjectResult>(replay);
        Assert.IsType<OkObjectResult>(read);
        Assert.Equal("true", controller.Response.Headers["Deprecation"]);
    }

    [Fact]
    public async Task LegacyHire_EnforcesSkillAndIdentityPreconditions()
    {
        var fixture = await CreateAsync();
        var skills = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var controller = CustomerController(fixture, skills);
        var request = new HireAgentRequest(
            "contract",
            "DMA",
            "publish",
            "1",
            100,
            "1",
            [new SkillAssignment("missing", "1")]);

        var missingSkill = await controller.HireAgentAsync(request, CancellationToken.None);
        Assert.IsType<UnprocessableEntityObjectResult>(missingSkill);

        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };
        var forbidden = await controller.HireAgentAsync(
            request with { Skills = null }, CancellationToken.None);
        Assert.IsType<ForbidResult>(forbidden);
    }

    [Fact]
    public async Task LegacyHire_WithPublishedSkillsCreatesAndReplaysRelationship()
    {
        var fixture = await CreateAsync();
        var skills = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        await using (var db = new SkillCatalogDbContext(skills))
        {
            db.Skills.Add(new SkillEntry
            {
                SkillId = "publish",
                Version = "1",
                DisplayName = "Publish",
                Definition = "{}",
                CctSuite = ["CCT-1"],
                Status = "PUBLISHED",
            });
            await db.SaveChangesAsync();
        }
        var controller = CustomerController(fixture, skills);
        var request = new HireAgentRequest(
            "contract", "DMA", "publish", "1", 100, "1",
            [new SkillAssignment("publish", "1")]);

        var created = await controller.HireAgentAsync(request, CancellationToken.None);
        var replay = await controller.HireAgentAsync(request, CancellationToken.None);

        Assert.IsType<CreatedAtActionResult>(created);
        Assert.IsType<OkObjectResult>(replay);
        Assert.Equal("true", controller.Response.Headers["Deprecation"]);
    }

    [Fact]
    public async Task LegacyCustomerMutations_ValidateBodiesSkillsAndCeAvailability()
    {
        var fixture = await CreateAsync();
        var skills = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        await using (var db = new SkillCatalogDbContext(skills))
        {
            db.Skills.Add(new SkillEntry
            {
                SkillId = "publish",
                Version = "1",
                DisplayName = "Publish",
                Definition = "{}",
                CctSuite = ["CCT-1"],
                Status = "PUBLISHED",
            });
            await db.SaveChangesAsync();
        }
        var controller = CustomerController(fixture, skills);

        Assert.IsType<BadRequestObjectResult>(await controller.RegisterCustomerAsync(null!, CancellationToken.None));
        AssertStatus(await controller.RegisterCustomerAsync(
            new RegisterCustomerRequest("Name", "customer@example.com", fixture.TenantId.ToString()),
            CancellationToken.None), 503);
        Assert.IsType<BadRequestObjectResult>(await controller.HireAgentAsync(null!, CancellationToken.None));
        Assert.IsType<BadRequestObjectResult>(await controller.AmendContractAsync(null!, CancellationToken.None));
        Assert.IsType<BadRequestObjectResult>(await controller.AmendContractAsync(
            new AmendContractRequest("contract", "publish", "1", "CHANGE"), CancellationToken.None));
        Assert.IsType<UnprocessableEntityObjectResult>(await controller.AmendContractAsync(
            new AmendContractRequest("contract", "missing", "1", "ADD"), CancellationToken.None));
        AssertStatus(await controller.AmendContractAsync(
            new AmendContractRequest("contract", "publish", "1", "ADD"), CancellationToken.None), 503);
        AssertStatus(await controller.AmendContractAsync(
            new AmendContractRequest("contract", "publish", "1", "REMOVE"), CancellationToken.None), 503);
    }

    [Fact]
    public void RelationshipCodecs_RoundTripEveryValueAndRejectUnknownValues()
    {
        foreach (var state in Enum.GetValues<EmploymentRelationshipState>())
        {
            var encoded = RelationshipStateCodec.ToDatabase(state);
            Assert.Equal(state, RelationshipStateCodec.FromDatabase(encoded));
            var json = JsonSerializer.Serialize(state, new JsonSerializerOptions
            {
                Converters = { new RelationshipStateJsonConverter() },
            });
            Assert.Equal(state, JsonSerializer.Deserialize<EmploymentRelationshipState>(json, new JsonSerializerOptions
            {
                Converters = { new RelationshipStateJsonConverter() },
            }));
        }
        foreach (var role in Enum.GetValues<RelationshipParticipantRole>())
        {
            var encoded = RelationshipRoleCodec.ToDatabase(role);
            Assert.Equal(role, RelationshipRoleCodec.FromDatabase(encoded));
            var json = JsonSerializer.Serialize(role, new JsonSerializerOptions
            {
                Converters = { new RelationshipRoleJsonConverter() },
            });
            Assert.Equal(role, JsonSerializer.Deserialize<RelationshipParticipantRole>(json, new JsonSerializerOptions
            {
                Converters = { new RelationshipRoleJsonConverter() },
            }));
        }

        Assert.Throws<ArgumentOutOfRangeException>(() =>
            RelationshipStateCodec.ToDatabase((EmploymentRelationshipState)int.MaxValue));
        Assert.Throws<InvalidOperationException>(() => RelationshipStateCodec.FromDatabase("UNKNOWN"));
        Assert.Throws<ArgumentOutOfRangeException>(() =>
            RelationshipRoleCodec.ToDatabase((RelationshipParticipantRole)int.MaxValue));
        Assert.Throws<InvalidOperationException>(() => RelationshipRoleCodec.FromDatabase("UNKNOWN"));
        Assert.Throws<JsonException>(() => JsonSerializer.Deserialize<EmploymentRelationshipState>(
            "null", new JsonSerializerOptions { Converters = { new RelationshipStateJsonConverter() } }));
        Assert.Throws<JsonException>(() => JsonSerializer.Deserialize<RelationshipParticipantRole>(
            "null", new JsonSerializerOptions { Converters = { new RelationshipRoleJsonConverter() } }));
    }

    [Fact]
    public async Task LegacyContracts_RejectMissingIdentityAndUnknownRelationship()
    {
        var fixture = await CreateAsync();
        var skills = new DbContextOptionsBuilder<SkillCatalogDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString("N"))
            .Options;
        var controller = CustomerController(fixture, skills);

        Assert.IsType<NotFoundResult>(await controller.GetEmploymentContract(
            Guid.NewGuid(), CancellationToken.None));
        controller.ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() };
        Assert.IsType<ForbidResult>(await controller.GetEmploymentContract(
            fixture.RelationshipId, CancellationToken.None));
        Assert.IsType<ForbidResult>(await controller.FormEmploymentContract(
            new LegacyFormEmploymentContractRequest(Guid.NewGuid(), new LegacyDecisionSpaceInput("DMA")),
            CancellationToken.None));
    }

    private static CustomersController CustomerController(
        Fixture fixture,
        DbContextOptions<SkillCatalogDbContext> skillOptions) => new(
            new ConfigurationBuilder().Build(),
            new SkillFactory(skillOptions),
            fixture.Service,
            NullLogger<CustomersController>.Instance)
        {
            ControllerContext = Context(fixture.TenantId, fixture.ParticipantId),
        };

    private static async Task<Fixture> CreateAsync(bool includeContinuityClaims = false)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var service = new EmploymentRelationshipService(
            factory,
            new RecordingRelationshipConstitutionalGateway(),
            NullLogger<EmploymentRelationshipService>.Instance);
        var tenantId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var admitted = await service.AdmitAsync(
            tenantId,
            participantId,
            Guid.NewGuid(),
            "DMA",
            Guid.NewGuid(),
            CancellationToken.None);
        var controller = new EmploymentRelationshipsController(service)
        {
            ControllerContext = Context(tenantId, participantId, includeContinuityClaims),
        };
        return new Fixture(
            service,
            controller,
            tenantId,
            participantId,
            admitted.Relationship.RelationshipId);
    }

    private static ControllerContext Context(
        Guid tenantId,
        Guid participantId,
        bool includeContinuityClaims = false)
    {
        var claims = new List<Claim>
        {
            new("tenant_id", tenantId.ToString()),
            new("participant_id", participantId.ToString()),
            new("identity_provider", "keycloak"),
            new("authentication_assurance", "TIER_4_PORTAL_FRESH"),
            new("auth_time", DateTimeOffset.UtcNow.ToUnixTimeSeconds().ToString()),
        };
        if (includeContinuityClaims)
        {
            claims.AddRange(
            [
                new Claim("channel", "web"),
                new Claim("conversation_id", "conversation"),
                new Claim("external_subject_hash", new string('a', 64)),
            ]);
        }
        var httpContext = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test")),
        };
        httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId.ToString();
        return new ControllerContext { HttpContext = httpContext };
    }

    private static void AssertStatus(IActionResult result, int expected) =>
        Assert.Equal(expected, Assert.IsType<ObjectResult>(result).StatusCode);

    private sealed record Fixture(
        EmploymentRelationshipService Service,
        EmploymentRelationshipsController Controller,
        Guid TenantId,
        Guid ParticipantId,
        Guid RelationshipId);
}
