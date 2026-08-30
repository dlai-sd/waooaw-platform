// Implements: WC-079 AA-03, AA-04, AA-05, AA-08, AA-09
// constitutional_basis: C-003, C-005, C-007, C-023, C-026, C-059, C-063, C-065, C-076, C-079

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class AgentAdmissionsControllerTests
{
    [Fact]
    public async Task OfferableProjectionRejectsUnknownEnvironment()
    {
        var fixture = Fixture.Create();

        AssertProblem(await fixture.Controller.GetOfferableAsync("staging", CancellationToken.None), 400, "ADMISSION_INVALID_REQUEST");
    }

    [Fact]
    public async Task DraftCreationEnforcesIdentityOwnerAndIdempotencyBoundaries()
    {
        var fixture = Fixture.Create();
        fixture.SetIdentity(includeTenant: false);
        AssertProblem(await fixture.Controller.CreateDraftAsync(
            fixture.Type, fixture.Version, new(fixture.ActorId), Guid.NewGuid(), CancellationToken.None),
            401, "ADMISSION_UNAUTHORIZED");

        fixture.SetIdentity();
        AssertProblem(await fixture.Controller.CreateDraftAsync(
            fixture.Type, fixture.Version, new(fixture.ActorId), null, CancellationToken.None),
            400, "ADMISSION_INVALID_REQUEST");
        Assert.IsType<ForbidResult>(await fixture.Controller.CreateDraftAsync(
            fixture.Type, fixture.Version, new(Guid.NewGuid()), Guid.NewGuid(), CancellationToken.None));

        fixture.SetIdentity("admission_operator");
        var key = Guid.NewGuid();
        var created = Assert.IsType<ObjectResult>(await fixture.Controller.CreateDraftAsync(
            fixture.Type, fixture.Version, new(fixture.ActorId), key, CancellationToken.None));
        var replayed = Assert.IsType<ObjectResult>(await fixture.Controller.CreateDraftAsync(
            fixture.Type, fixture.Version, new(fixture.ActorId), key, CancellationToken.None));

        Assert.Equal(201, created.StatusCode);
        Assert.Equal(200, replayed.StatusCode);
    }

    [Fact]
    public async Task RevisionValidationAndFindingsEndpointsExecuteBoundWorkflow()
    {
        var fixture = Fixture.Create();
        var admission = await fixture.CreateDraftAsync();
        using var contract = AgentAdmissionValidatorTests.ValidContract(fixture.Type, fixture.Version);
        var digest = AgentAdmissionCanonicalizer.Digest(contract.RootElement);

        AssertProblem(await fixture.Controller.PutRevisionAsync(
            fixture.Type, fixture.Version, admission.AdmissionId, 1,
            new(0, digest, contract.RootElement), null, CancellationToken.None),
            400, "ADMISSION_INVALID_REQUEST");
        var revision = Assert.IsType<OkObjectResult>(await fixture.Controller.PutRevisionAsync(
            fixture.Type, fixture.Version, admission.AdmissionId, 1,
            new(0, digest, contract.RootElement), Guid.NewGuid(), CancellationToken.None));
        Assert.Contains("\"CurrentRevision\":1", JsonSerializer.Serialize(revision.Value));

        var validation = Assert.IsType<ObjectResult>(await fixture.Controller.ValidateAsync(
            fixture.Type, fixture.Version, admission.AdmissionId,
            new(1, digest, AgentAdmissionValidator.Profile), Guid.NewGuid(), CancellationToken.None));
        Assert.Equal(202, validation.StatusCode);

        await using var db = fixture.Factory.CreateDbContext();
        var validationId = await db.AgentAdmissionValidations.Select(value => value.ValidationId).SingleAsync();
        var findings = Assert.IsType<OkObjectResult>(await fixture.Controller.GetFindingsAsync(
            fixture.Type, fixture.Version, admission.AdmissionId, validationId, CancellationToken.None));
        Assert.Empty(Assert.IsAssignableFrom<IReadOnlyList<global::Waooaw.BusinessPlatform.Infrastructure.AgentAdmissionFinding>>(findings.Value));
    }

    [Fact]
    public async Task TransitionEndpointsEnforceRoleStepUpAndIndependentApproval()
    {
        var fixture = Fixture.Create();
        var admission = await fixture.PrepareValidatedAsync();
        var request = Request(admission);

        AssertProblem(await fixture.Controller.SubmitAsync(
            fixture.Type, fixture.Version, request, null, CancellationToken.None),
            400, "ADMISSION_INVALID_REQUEST");
        var submitted = Assert.IsType<ObjectResult>(await fixture.Controller.SubmitAsync(
            fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None));
        Assert.Equal(201, submitted.StatusCode);

        admission = await fixture.ReloadAsync();
        request = Request(admission);
        AssertProblem(await fixture.Controller.ApproveAsync(
            fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None),
            403, "ADMISSION_FORBIDDEN");
        fixture.SetIdentity("admission_approver", stepUp: true, actorId: Guid.NewGuid());
        Assert.IsType<ObjectResult>(await fixture.Controller.ApproveAsync(
            fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None));

        admission = await fixture.ReloadAsync();
        request = Request(admission);
        fixture.SetIdentity("platform_activation_authority", stepUp: true, actorId: Guid.NewGuid());
        AssertProblem(await fixture.Controller.ActivateAsync(
            fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None),
            423, "ADMISSION_TRANSITION_BLOCKED");

        foreach (var (role, invoke) in new (string, Func<Task<IActionResult>>)[]
        {
            ("admission_approver", () => fixture.Controller.RejectAsync(fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None)),
            ("constitutional_authority", () => fixture.Controller.SuspendAsync(fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None)),
            ("lifecycle_authority", () => fixture.Controller.SupersedeAsync(fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None)),
            ("lifecycle_authority", () => fixture.Controller.RetireAsync(fixture.Type, fixture.Version, request, Guid.NewGuid(), CancellationToken.None)),
        })
        {
            fixture.SetIdentity(role, stepUp: true, actorId: Guid.NewGuid());
            Assert.IsType<ObjectResult>(await invoke());
        }
    }

    [Fact]
    public async Task ControllerMapsNotFoundConflictAndInvalidContentWithoutDisclosure()
    {
        var fixture = Fixture.Create();
        using var contract = AgentAdmissionValidatorTests.ValidContract(fixture.Type, fixture.Version);

        AssertProblem(await fixture.Controller.PutRevisionAsync(
            fixture.Type, fixture.Version, Guid.NewGuid(), 1,
            new(0, AgentAdmissionCanonicalizer.Digest(contract.RootElement), contract.RootElement),
            Guid.NewGuid(), CancellationToken.None),
            404, "ADMISSION_NOT_FOUND");

        var admission = await fixture.CreateDraftAsync();
        AssertProblem(await fixture.Controller.PutRevisionAsync(
            fixture.Type, fixture.Version, admission.AdmissionId, 1,
            new(0, "sha256:" + new string('0', 64), contract.RootElement),
            Guid.NewGuid(), CancellationToken.None),
            400, "ADMISSION_INVALID_REQUEST");

        AssertProblem(await fixture.Controller.CreateDraftAsync(
            fixture.Type, fixture.Version, new(fixture.ActorId), Guid.NewGuid(), CancellationToken.None),
            409, "ADMISSION_STATE_CONFLICT");
    }

    private static AgentAdmissionTransitionRequest Request(AgentAdmission admission) => new(
        admission.StateVersion,
        admission.CurrentRevision,
        admission.AdmissionContentDigest!,
        "sha256:" + new string('e', 64),
        "sha256:" + new string('a', 64),
        "WC-079-1.0",
        null,
        null);

    private static void AssertProblem(IActionResult result, int status, string code)
    {
        var problem = Assert.IsType<ObjectResult>(result);
        Assert.Equal(status, problem.StatusCode);
        Assert.Contains(code, JsonSerializer.Serialize(problem.Value));
        Assert.Contains("application/problem+json", problem.ContentTypes);
    }

    private sealed class Fixture
    {
        private Fixture(
            InMemoryEmploymentRelationshipFactory factory,
            AgentAdmissionsController controller,
            Guid tenantId,
            Guid actorId)
        {
            Factory = factory;
            Controller = controller;
            TenantId = tenantId;
            ActorId = actorId;
            SetIdentity();
        }

        public InMemoryEmploymentRelationshipFactory Factory { get; }
        public AgentAdmissionsController Controller { get; }
        public Guid TenantId { get; }
        public Guid ActorId { get; }
        public string Type => "DIGITAL_MARKETING_LOCAL_SERVICE";
        public string Version => "3.1.0";

        public static Fixture Create()
        {
            var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
            var service = new AgentAdmissionService(
                factory,
                new AgentAdmissionValidator(),
                new RecordingRelationshipConstitutionalGateway());
            return new(factory, new AgentAdmissionsController(service), Guid.NewGuid(), Guid.NewGuid());
        }

        public void SetIdentity(
            string? role = null,
            bool stepUp = false,
            Guid? actorId = null,
            bool includeTenant = true)
        {
            var claims = new List<Claim>
            {
                new("participant_id", (actorId ?? ActorId).ToString()),
                new("correlation_id", Guid.NewGuid().ToString()),
            };
            if (role is not null) claims.Add(new("participant_role", role));
            if (stepUp) claims.Add(new("amr", "mfa"));
            var context = new DefaultHttpContext
            {
                User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test")),
                RequestServices = Services("Development"),
            };
            if (includeTenant)
                context.Items[TenantIsolationMiddleware.TenantIdItemKey] = TenantId.ToString();
            Controller.ControllerContext = new ControllerContext { HttpContext = context };
        }

        public async Task<AgentAdmission> CreateDraftAsync()
        {
            await Controller.CreateDraftAsync(
                Type, Version, new(ActorId), Guid.NewGuid(), CancellationToken.None);
            return await ReloadAsync();
        }

        public async Task<AgentAdmission> PrepareValidatedAsync()
        {
            var admission = await CreateDraftAsync();
            using var contract = AgentAdmissionValidatorTests.ValidContract(Type, Version);
            var digest = AgentAdmissionCanonicalizer.Digest(contract.RootElement);
            await Controller.PutRevisionAsync(
                Type, Version, admission.AdmissionId, 1,
                new(0, digest, contract.RootElement), Guid.NewGuid(), CancellationToken.None);
            await Controller.ValidateAsync(
                Type, Version, admission.AdmissionId,
                new(1, digest, AgentAdmissionValidator.Profile), Guid.NewGuid(), CancellationToken.None);
            return await ReloadAsync();
        }

        public async Task<AgentAdmission> ReloadAsync()
        {
            await using var db = Factory.CreateDbContext();
            return await db.AgentAdmissions.SingleAsync();
        }

        private static IServiceProvider Services(string environment)
        {
            var host = new Mock<IHostEnvironment>();
            host.SetupGet(value => value.EnvironmentName).Returns(environment);
            return new ServiceCollection().AddSingleton(host.Object).BuildServiceProvider();
        }
    }
}