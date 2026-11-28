// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R023, R024
// Constitutional basis: C-023, C-059, C-063

using System.Security.Claims;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Hosting;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.PlatformApprovals;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.PlatformApprovals;

public sealed class PlatformProfessionalApprovalTests
{
    private const string Type = "DIGITAL_MARKETING_LOCAL_SERVICE";
    private static readonly DateTimeOffset Now = new(2026, 12, 1, 9, 0, 0, TimeSpan.Zero);

    private static (
        PlatformProfessionalApprovalService Service,
        InMemoryPlatformProfessionalApprovalStore Store
    ) Create()
    {
        var environment = new Mock<IHostEnvironment>();
        environment.SetupGet(value => value.ContentRootPath).Returns(FindBusinessPlatformRoot());
        var store = new InMemoryPlatformProfessionalApprovalStore();
        return (
            new PlatformProfessionalApprovalService(
                new ProfessionalCatalog(environment.Object),
                store,
                new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N")),
                new FixedClock(Now)
            ),
            store
        );
    }

    [Fact]
    public async Task ANewVersionIsNotApprovedAndOffersOnlyApprove()
    {
        var (service, _) = Create();

        var listed = Assert.Single(await service.ListAsync(default));

        Assert.Equal(Type, listed.ProfessionalType);
        Assert.Equal(PlatformApprovalStates.NotApproved, listed.State);
        Assert.Equal([PlatformApprovalActions.Approve], listed.Actions);
        Assert.Null(await service.GetEffectiveAsync(Type, "1.0.0", default));
    }

    [Fact]
    public async Task ApprovingRecordsWhoAndWhenAndOffersSuspendAndRetire()
    {
        var (service, store) = Create();

        var view = await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );

        Assert.Equal(PlatformApprovalStates.Approved, view.State);
        Assert.Equal("founder-1", view.DecidedBy);
        Assert.Equal(Now, view.DecidedAt);
        Assert.Equal(
            [PlatformApprovalActions.Suspend, PlatformApprovalActions.Retire],
            view.Actions
        );
        Assert.NotNull(await service.GetEffectiveAsync(Type, "1.0.0", default));
        Assert.Matches("^sha256:[0-9a-f]{64}$", Assert.Single(store.History).ContentDigest);
    }

    [Fact]
    public async Task SuspendingNeedsAReasonStopsNewCustomersAndCanBeUndoneByApprovingAgain()
    {
        var (service, store) = Create();
        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );

        var missing = await Assert.ThrowsAsync<PlatformApprovalException>(() =>
            service.DecideAsync(
                Type,
                "1.0.0",
                PlatformApprovalActions.Suspend,
                "founder-1",
                " ",
                default
            )
        );
        Assert.Equal("PROFESSIONAL_APPROVAL_REASON_REQUIRED", missing.Code);

        var suspended = await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Suspend,
            "founder-1",
            "Paused for a review",
            default
        );
        Assert.Equal(PlatformApprovalStates.Suspended, suspended.State);
        Assert.Equal("Paused for a review", suspended.Reason);
        Assert.Null(await service.GetEffectiveAsync(Type, "1.0.0", default));

        var reinstated = await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );
        Assert.Equal(PlatformApprovalStates.Approved, reinstated.State);
        Assert.Null(reinstated.Reason);
        Assert.Equal(3, store.History.Count);
    }

    [Fact]
    public async Task ARetiredVersionStaysRetired()
    {
        var (service, _) = Create();
        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );
        var retired = await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Retire,
            "founder-1",
            "Replaced by a new version",
            default
        );
        Assert.Empty(retired.Actions);

        var again = await Assert.ThrowsAsync<PlatformApprovalException>(() =>
            service.DecideAsync(
                Type,
                "1.0.0",
                PlatformApprovalActions.Approve,
                "founder-1",
                null,
                default
            )
        );

        Assert.Equal(409, again.Status);
        Assert.Null(await service.GetEffectiveAsync(Type, "1.0.0", default));
    }

    [Theory]
    [InlineData("UNKNOWN_TYPE", "1.0.0", "approve", "PROFESSIONAL_APPROVAL_UNKNOWN")]
    [InlineData(Type, "9.9.9", "approve", "PROFESSIONAL_APPROVAL_UNKNOWN")]
    [InlineData(Type, "1.0.0", "delete", "PROFESSIONAL_APPROVAL_UNKNOWN_ACTION")]
    [InlineData(Type, "1.0.0", "suspend", "PROFESSIONAL_APPROVAL_REASON_REQUIRED")]
    public async Task ADecisionThatCannotApplyIsRefusedWithAPlainCode(
        string type,
        string version,
        string action,
        string code
    )
    {
        var (service, _) = Create();

        var failure = await Assert.ThrowsAsync<PlatformApprovalException>(() =>
            service.DecideAsync(type, version, action, "founder-1", null, default)
        );

        Assert.Equal(code, failure.Code);
    }

    [Fact]
    public async Task ASuspendBeforeAnyApprovalIsNotAllowed()
    {
        var (service, _) = Create();

        var failure = await Assert.ThrowsAsync<PlatformApprovalException>(() =>
            service.DecideAsync(
                Type,
                "1.0.0",
                PlatformApprovalActions.Suspend,
                "founder-1",
                "Not ready yet",
                default
            )
        );

        Assert.Equal("PROFESSIONAL_APPROVAL_NOT_ALLOWED", failure.Code);
    }

    [Fact]
    public async Task ADecisionBuiltOnAStaleVersionIsNotSaved()
    {
        var (service, store) = Create();
        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );
        var stale = (await store.GetAsync(Type, "1.0.0", default))! with { StateVersion = 2 };

        Assert.False(await store.SaveAsync(stale, 0, default));
        Assert.Single(store.History);
    }

    [Fact]
    public async Task EachWorkspaceGetsOneActiveAdmissionFromTheApprovalAndReusesIt()
    {
        var (service, _) = Create();
        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );
        var tenant = Guid.NewGuid();
        var owner = Guid.NewGuid();

        var first = await service.EnsureWorkspaceAdmissionAsync(
            tenant,
            owner,
            Type,
            "1.0.0",
            default
        );
        var second = await service.EnsureWorkspaceAdmissionAsync(
            tenant,
            owner,
            Type,
            "1.0.0",
            default
        );
        var other = await service.EnsureWorkspaceAdmissionAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Type,
            "1.0.0",
            default
        );

        Assert.NotNull(first);
        Assert.Equal(first, second);
        Assert.NotEqual(first, other);
    }

    [Fact]
    public async Task ASuspendedVersionGivesNoAdmissionUntilTheFounderApprovesItAgain()
    {
        var (service, _) = Create();
        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );
        var tenant = Guid.NewGuid();
        var id = await service.EnsureWorkspaceAdmissionAsync(
            tenant,
            Guid.NewGuid(),
            Type,
            "1.0.0",
            default
        );
        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Suspend,
            "founder-1",
            "Paused for a review",
            default
        );
        Assert.Null(
            await service.EnsureWorkspaceAdmissionAsync(
                tenant,
                Guid.NewGuid(),
                Type,
                "1.0.0",
                default
            )
        );

        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );

        Assert.Equal(
            id,
            await service.EnsureWorkspaceAdmissionAsync(
                tenant,
                Guid.NewGuid(),
                Type,
                "1.0.0",
                default
            )
        );
    }

    private static PlatformProfessionalApprovalsController Controller(
        string? role,
        bool stepUp,
        PlatformProfessionalApprovalService service
    )
    {
        var claims = new List<Claim> { new("sub", "founder-1") };
        if (role is not null)
            claims.Add(new Claim("role", role));
        if (stepUp)
        {
            claims.Add(new Claim("auth_time", Now.AddMinutes(-1).ToUnixTimeSeconds().ToString()));
            claims.Add(new Claim("acr", "2"));
            claims.Add(new Claim("amr", "otp"));
        }
        return new PlatformProfessionalApprovalsController(service, new FixedClock(Now))
        {
            ControllerContext = new ControllerContext
            {
                HttpContext = new DefaultHttpContext
                {
                    User = new ClaimsPrincipal(new ClaimsIdentity(claims, "test")),
                },
            },
        };
    }

    [Fact]
    public async Task OnlyTheFounderSeesTheList()
    {
        var (service, _) = Create();

        Assert.Equal(
            403,
            Assert
                .IsType<ObjectResult>(
                    await Controller("customer", false, service).ListAsync(default)
                )
                .StatusCode
        );
        Assert.IsType<OkObjectResult>(
            await Controller("founder", false, service).ListAsync(default)
        );
    }

    [Fact]
    public async Task ADecisionNeedsTheFounderAndAFreshStrongSignIn()
    {
        var (service, store) = Create();
        var body = new PlatformProfessionalDecisionBody(null);

        var notFounder = await Controller("customer", true, service)
            .DecideAsync(Type, "1.0.0", "approve", body, default);
        var noStepUp = await Controller("founder", false, service)
            .DecideAsync(Type, "1.0.0", "approve", body, default);

        Assert.Equal(403, Assert.IsType<ObjectResult>(notFounder).StatusCode);
        Assert.Equal(403, Assert.IsType<ObjectResult>(noStepUp).StatusCode);
        Assert.Empty(store.History);

        var approved = await Controller("founder", true, service)
            .DecideAsync(Type, "1.0.0", "approve", body, default);
        Assert.Equal(
            PlatformApprovalStates.Approved,
            Assert
                .IsType<PlatformProfessionalView>(Assert.IsType<OkObjectResult>(approved).Value)
                .State
        );
    }

    [Fact]
    public async Task ARefusedDecisionReturnsItsStatus()
    {
        var (service, _) = Create();

        var result = await Controller("founder", true, service)
            .DecideAsync(
                Type,
                "1.0.0",
                "suspend",
                new PlatformProfessionalDecisionBody("no"),
                default
            );

        Assert.Equal(400, Assert.IsType<ObjectResult>(result).StatusCode);
    }

    [Fact]
    public async Task AWorkspaceAdmissionGetsOneRevisionAndOneBindingPerSkillExactlyOnce()
    {
        var environment = new Mock<IHostEnvironment>();
        environment.SetupGet(value => value.ContentRootPath).Returns(FindBusinessPlatformRoot());
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var packageDirectory = Path.GetDirectoryName(
            RepositoryPaths.Resolve(
                "src/digital-marketing-agent/tests/fixtures/agent-admission/digital-marketing-local-service-v1.0.0.json"
            )
        )!;
        var source = new FileAgentPackageSource(packageDirectory);
        var clock = new FixedClock(Now);
        var service = new PlatformProfessionalApprovalService(
            new ProfessionalCatalog(environment.Object),
            new InMemoryPlatformProfessionalApprovalStore(),
            factory,
            clock,
            new WorkspaceRuntimeBindingService(factory, source, clock)
        );
        await service.DecideAsync(
            Type,
            "1.0.0",
            PlatformApprovalActions.Approve,
            "founder-1",
            null,
            default
        );
        var tenant = Guid.NewGuid();

        var first = await service.EnsureWorkspaceAdmissionAsync(
            tenant,
            Guid.NewGuid(),
            Type,
            "1.0.0",
            default
        );
        var second = await service.EnsureWorkspaceAdmissionAsync(
            tenant,
            Guid.NewGuid(),
            Type,
            "1.0.0",
            default
        );

        Assert.Equal(first, second);
        await using var db = factory.CreateDbContext();
        var bindings = await db
            .AgentSkillRuntimeBindings.Where(value => value.TenantId == tenant)
            .ToListAsync();
        Assert.Equal(
            ["CONTENT_STRATEGY_AND_CALENDAR", "CUSTOMER_PROFILING", "MARKET_RESEARCH_AND_MATURITY"],
            bindings.Select(value => value.SkillId).Order(StringComparer.Ordinal).ToArray()
        );
        Assert.All(
            bindings,
            value =>
            {
                Assert.Equal(first, value.AdmissionId);
                Assert.Matches("^sha256:[0-9a-f]{64}$", value.PromptDigest);
                Assert.Matches("^sha256:[0-9a-f]{64}$", value.InputSchemaDigest);
                Assert.Equal("3.1", value.SpecificationRevision);
                Assert.Equal(1, value.ReleaseSequence);
            }
        );
        Assert.Single(
            await db.AgentAdmissionRevisions.Where(value => value.TenantId == tenant).ToListAsync()
        );
        Assert.Equal(
            1,
            (
                await db.AgentAdmissions.SingleAsync(value => value.TenantId == tenant)
            ).CurrentRevision
        );
    }

    private static string FindBusinessPlatformRoot() =>
        Path.GetDirectoryName(
            RepositoryPaths.Resolve("src/business-platform/business-platform.csproj")
        )!;
}
