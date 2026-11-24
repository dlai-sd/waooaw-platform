// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004, WC137-R005
// constitutional_basis: C-009, C-023, C-059, C-063

using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services.PlatformAccess;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.PlatformAccess;

internal sealed class FakeAccessStore : IPlatformAccessStore
{
    public List<string> Roles { get; set; } = [];
    public bool Fail { get; set; }
    public int Resolutions { get; private set; }
    public IReadOnlyList<ConfiguredFounder>? Reconciled { get; private set; }
    public AccessRequestResult RequestResult { get; set; } = AccessRequestResult.Created;
    public AccessDecisionResult DecisionResult { get; set; } = AccessDecisionResult.Decided;
    public AccessRevocationResult RevocationResult { get; set; } = AccessRevocationResult.Revoked;
    public (string Role, string Justification)? Requested { get; private set; }
    public (bool Approve, string Decider)? Decided { get; private set; }

    public Task ReconcileFoundersAsync(IReadOnlyList<ConfiguredFounder> founders, DateTimeOffset now, CancellationToken ct)
    {
        Reconciled = founders;
        return Task.CompletedTask;
    }

    public Task<IReadOnlyList<string>> ResolveRolesAsync(string email, string subject, DateTimeOffset now, CancellationToken ct)
    {
        Resolutions++;
        return Fail ? throw new InvalidOperationException("store down") : Task.FromResult<IReadOnlyList<string>>(Roles);
    }

    public Task<(AccessRequestResult Result, Guid? RequestId)> CreateRequestAsync(string subject, string email, string role, string justification, DateTimeOffset now, CancellationToken ct)
    {
        Requested = (role, justification);
        return Task.FromResult((RequestResult, (Guid?)Guid.NewGuid()));
    }

    public Task<IReadOnlyList<PlatformAccessRequest>> ListRequestsAsync(string? status, string? subject, int limit, CancellationToken ct) =>
        Task.FromResult<IReadOnlyList<PlatformAccessRequest>>([
            new(Guid.NewGuid(), "admin@example.org", "pricing_admin", "Maintains prices", status ?? "PENDING", DateTimeOffset.UnixEpoch, null, null, null),
        ]);

    public Task<AccessDecisionResult> DecideAsync(Guid requestId, bool approve, string deciderEmail, string? reason, DateTimeOffset now, CancellationToken ct)
    {
        Decided = (approve, deciderEmail);
        return Task.FromResult(DecisionResult);
    }

    public Task<IReadOnlyList<PlatformRoleGrant>> ListGrantsAsync(DateTimeOffset now, CancellationToken ct) =>
        Task.FromResult<IReadOnlyList<PlatformRoleGrant>>([
            new(Guid.NewGuid(), "admin@example.org", "subject-admin-1", "pricing_admin", "APPROVAL", "owner@example.org", now, now.AddDays(90)),
        ]);

    public Task<AccessRevocationResult> RevokeAsync(Guid grantId, string revokedBy, string reason, DateTimeOffset now, CancellationToken ct) =>
        Task.FromResult(RevocationResult);
}

public sealed class PlatformRoleClaimsTransformationTests
{
    private static ClaimsPrincipal Principal(string? emailVerified = "true", string? email = "Owner@Example.org", string? sub = "subject-owner-1") =>
        new(new ClaimsIdentity(
            new[] { new Claim("azp", "waooaw-web") }
                .Concat(sub is null ? [] : [new Claim("sub", sub)])
                .Concat(email is null ? [] : [new Claim("email", email)])
                .Concat(emailVerified is null ? [] : [new Claim("email_verified", emailVerified)]),
            "Test"
        ));

    private static PlatformRoleClaimsTransformation Transformation(FakeAccessStore store, int cacheSeconds = 15) =>
        new(store, new MemoryCache(new MemoryCacheOptions()), Options.Create(new PlatformAccessOptions { ResolutionCacheSeconds = cacheSeconds }), TimeProvider.System, NullLogger<PlatformRoleClaimsTransformation>.Instance);

    [Fact]
    public async Task GrantedRolesBecomeRoleClaimsAndTheFounderIsAlsoAPricingAdministrator()
    {
        var result = await Transformation(new FakeAccessStore { Roles = ["founder"] }).TransformAsync(Principal());
        Assert.True(result.IsInRole("founder"));
        Assert.True(result.IsInRole("pricing_admin"));
        Assert.False(result.IsInRole("admission_approver"));
    }

    [Fact]
    public async Task ClaimsMappedByJwtBearerAreRecognisedToo()
    {
        var mapped = new ClaimsPrincipal(new ClaimsIdentity(
            [
                new Claim("azp", "waooaw-web"),
                new Claim(ClaimTypes.NameIdentifier, "subject-owner-1"),
                new Claim(ClaimTypes.Email, "Owner@Example.org"),
                new Claim("email_verified", "true"),
            ],
            "Test"
        ));
        var result = await Transformation(new FakeAccessStore { Roles = ["founder"] }).TransformAsync(mapped);
        Assert.True(result.IsInRole("founder"));
    }

    [Fact]
    public async Task AnUnverifiedEmailOrMissingSubjectNeverReachesTheStore()
    {
        var store = new FakeAccessStore { Roles = ["founder"] };
        var transformation = Transformation(store);
        Assert.False((await transformation.TransformAsync(Principal(emailVerified: "false"))).IsInRole("founder"));
        Assert.False((await transformation.TransformAsync(Principal(emailVerified: null))).IsInRole("founder"));
        Assert.False((await transformation.TransformAsync(Principal(email: "not an email"))).IsInRole("founder"));
        Assert.False((await transformation.TransformAsync(Principal(sub: null))).IsInRole("founder"));
        Assert.False((await transformation.TransformAsync(new ClaimsPrincipal(new ClaimsIdentity()))).IsInRole("founder"));
        Assert.Equal(0, store.Resolutions);
    }

    [Fact]
    public async Task APeopleWithoutGrantsGetNoRolesAndAStoreFailureGrantsNothing()
    {
        Assert.False((await Transformation(new FakeAccessStore()).TransformAsync(Principal())).IsInRole("founder"));
        Assert.False((await Transformation(new FakeAccessStore { Roles = ["founder"], Fail = true }).TransformAsync(Principal())).IsInRole("founder"));
    }

    [Fact]
    public async Task ResolutionIsCachedBrieflyAndTransformingTwiceDoesNotAddRolesTwice()
    {
        var store = new FakeAccessStore { Roles = ["pricing_admin"] };
        var transformation = Transformation(store);
        var first = await transformation.TransformAsync(Principal());
        var second = await transformation.TransformAsync(first);
        await transformation.TransformAsync(Principal());
        Assert.Equal(1, store.Resolutions);
        Assert.Single(second.FindAll(ClaimTypes.Role));

        var uncached = new FakeAccessStore { Roles = ["pricing_admin"] };
        await Transformation(uncached, 0).TransformAsync(Principal());
        await Transformation(uncached, 0).TransformAsync(Principal());
        Assert.Equal(2, uncached.Resolutions);
    }
}

public sealed class PlatformFounderBootstrapServiceTests
{
    private static async Task<FakeAccessStore> RunAsync(params ConfiguredFounder[] founders)
    {
        var store = new FakeAccessStore();
        var services = new ServiceCollection().AddSingleton<IPlatformAccessStore>(store).BuildServiceProvider();
        await new PlatformFounderBootstrapService(
            services.GetRequiredService<IServiceScopeFactory>(),
            Options.Create(new PlatformAccessOptions { Founders = [.. founders] }),
            TimeProvider.System,
            NullLogger<PlatformFounderBootstrapService>.Instance
        ).StartAsync(default);
        return store;
    }

    [Fact]
    public async Task ConfiguredFoundersAreReassertedAtStart()
    {
        var store = await RunAsync(new ConfiguredFounder { Email = "owner@example.org" });
        Assert.Equal("owner@example.org", Assert.Single(store.Reconciled!).Email);
    }

    [Fact]
    public async Task NoConfiguredFounderLeavesExistingGrantsAlone()
    {
        Assert.Null((await RunAsync()).Reconciled);
    }

    [Fact]
    public async Task StopIsANoOp() =>
        await new PlatformFounderBootstrapService(null!, Options.Create(new PlatformAccessOptions()), TimeProvider.System, NullLogger<PlatformFounderBootstrapService>.Instance).StopAsync(default);
}

public sealed class PlatformAccessOptionsValidatorTests
{
    private static bool Valid(PlatformAccessOptions options) =>
        new PlatformAccessOptionsValidator().Validate(null, options).Succeeded;

    [Fact]
    public void DefaultsAndTypicalFoundersAreValid()
    {
        Assert.True(Valid(new PlatformAccessOptions()));
        Assert.True(Valid(new PlatformAccessOptions { Founders = [new() { Email = "Owner@Example.org", Subject = "abcdefgh12" }] }));
    }

    [Fact]
    public void RebindOnStartIsValidAloneButNeverWithAConfiguredSubject()
    {
        Assert.True(Valid(new PlatformAccessOptions { Founders = [new() { Email = "owner@example.org", RebindOnStart = true }] }));
        Assert.False(Valid(new PlatformAccessOptions { Founders = [new() { Email = "owner@example.org", Subject = "abcdefgh12", RebindOnStart = true }] }));
    }

    [Theory]
    [InlineData("not an email", null)]
    [InlineData("", null)]
    [InlineData("owner@example.org", "short")]
    [InlineData("owner@example.org", "has space in it")]
    public void BadFoundersAreRejected(string email, string? subject) =>
        Assert.False(Valid(new PlatformAccessOptions { Founders = [new() { Email = email, Subject = subject }] }));

    [Fact]
    public void DuplicateFoundersAndOutOfRangeLimitsAreRejected()
    {
        Assert.False(Valid(new PlatformAccessOptions { Founders = [new() { Email = "a@example.org" }, new() { Email = "A@example.org" }] }));
        Assert.False(Valid(new PlatformAccessOptions { ApprovedGrantDays = 0 }));
        Assert.False(Valid(new PlatformAccessOptions { MaximumRequestsPerDay = 0 }));
        Assert.False(Valid(new PlatformAccessOptions { MaximumPendingRequests = 0 }));
        Assert.False(Valid(new PlatformAccessOptions { ResolutionCacheSeconds = 61 }));
    }
}

public sealed class PlatformRolesTests
{
    private static ClaimsPrincipal Strong(long authTime, string acr = "2", string amr = "otp") =>
        new(new ClaimsIdentity([new("auth_time", authTime.ToString()), new("acr", acr), new("amr", amr)], "Test"));

    [Fact]
    public void StepUpRecognisesTheClaimNamesJwtBearerMapsInbound()
    {
        var now = DateTimeOffset.UtcNow;
        var mapped = new ClaimsPrincipal(new ClaimsIdentity(
            [
                new("auth_time", now.ToUnixTimeSeconds().ToString()),
                new("http://schemas.microsoft.com/claims/authnclassreference", "2"),
                new("http://schemas.microsoft.com/claims/authnmethodsreferences", "pwd"),
                new("http://schemas.microsoft.com/claims/authnmethodsreferences", "otp"),
            ],
            "Test"
        ));
        Assert.True(PlatformRoles.HasStepUp(mapped, now));
        var passwordOnly = new ClaimsPrincipal(new ClaimsIdentity(
            [
                new("auth_time", now.ToUnixTimeSeconds().ToString()),
                new("http://schemas.microsoft.com/claims/authnclassreference", "2"),
                new("http://schemas.microsoft.com/claims/authnmethodsreferences", "pwd"),
            ],
            "Test"
        ));
        Assert.False(PlatformRoles.HasStepUp(passwordOnly, now));
    }

    [Fact]
    public void StepUpNeedsAFreshStrongSignIn()
    {
        var now = DateTimeOffset.UtcNow;
        Assert.True(PlatformRoles.HasStepUp(Strong(now.AddMinutes(-1).ToUnixTimeSeconds()), now));
        Assert.True(PlatformRoles.HasStepUp(Strong(now.ToUnixTimeSeconds(), "urn:waooaw:aal3", "pwd mfa"), now));
        Assert.False(PlatformRoles.HasStepUp(Strong(now.AddMinutes(-6).ToUnixTimeSeconds()), now));
        Assert.False(PlatformRoles.HasStepUp(Strong(now.AddMinutes(5).ToUnixTimeSeconds()), now));
        Assert.False(PlatformRoles.HasStepUp(Strong(now.ToUnixTimeSeconds(), "1"), now));
        Assert.False(PlatformRoles.HasStepUp(Strong(now.ToUnixTimeSeconds(), amr: "pwd"), now));
        Assert.False(PlatformRoles.HasStepUp(new ClaimsPrincipal(new ClaimsIdentity("Test")), now));
    }
}

public sealed class PlatformAccessControllerTests
{
    private static readonly DateTimeOffset Now = DateTimeOffset.UtcNow;

    private static (PlatformAccessController Controller, FakeAccessStore Store) Create(
        string[] roles, bool stepUp = false, bool verified = true, string? body = null)
    {
        var claims = new List<Claim>
        {
            new("sub", "subject-owner-1"),
            new("email", "owner@example.org"),
            new("email_verified", verified ? "true" : "false"),
        };
        claims.AddRange(roles.Select(role => new Claim(ClaimTypes.Role, role)));
        if (stepUp)
            claims.AddRange([new("auth_time", Now.ToUnixTimeSeconds().ToString()), new("acr", "2"), new("amr", "otp")]);
        var context = new DefaultHttpContext { User = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test", "name", ClaimTypes.Role)) };
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body ?? "{}"));
        var store = new FakeAccessStore();
        var controller = new PlatformAccessController(store, TimeProvider.System)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
        return (controller, store);
    }

    private static int Status(IActionResult result) =>
        result switch
        {
            ObjectResult { StatusCode: { } code } => code,
            OkObjectResult => 200,
            _ => throw new InvalidOperationException(result.GetType().Name),
        };

    [Fact]
    public async Task MyRolesReportsRolesAndOffersRequestableRolesOnlyToVerifiedEmails()
    {
        var (controller, _) = Create(["founder", "pricing_admin"]);
        var result = Assert.IsType<OkObjectResult>(await controller.MyRolesAsync(default));
        var json = System.Text.Json.JsonSerializer.Serialize(result.Value);
        Assert.Contains("\"founder\":true", json);
        Assert.Contains("\"emailVerified\":true", json);

        var (unverified, _) = Create([], verified: false);
        var other = System.Text.Json.JsonSerializer.Serialize(Assert.IsType<OkObjectResult>(await unverified.MyRolesAsync(default)).Value);
        Assert.Contains("\"emailVerified\":false", other);
        Assert.Contains("\"requestableRoles\":[]", other);
    }

    [Fact]
    public async Task AccessRequestsNeedAVerifiedEmailAValidRoleAndAReason()
    {
        Assert.Equal(403, Status(await Create([], verified: false, body: """{"role":"pricing_admin","justification":"I maintain prices."}""").Controller.RequestAsync(default)));
        Assert.Equal(400, Status(await Create([], body: """{"role":"founder","justification":"I maintain prices."}""").Controller.RequestAsync(default)));
        Assert.Equal(400, Status(await Create([], body: """{"role":"pricing_admin","justification":"short"}""").Controller.RequestAsync(default)));
        Assert.Equal(400, Status(await Create([], body: """{"role":"pricing_admin","extra":1}""").Controller.RequestAsync(default)));
        Assert.Equal(400, Status(await Create([], body: "not json").Controller.RequestAsync(default)));
        var (controller, store) = Create([], body: """{"role":" pricing_admin ","justification":" I maintain prices. "}""");
        Assert.Equal(202, Status(await controller.RequestAsync(default)));
        Assert.Equal(("pricing_admin", "I maintain prices."), store.Requested);
    }

    [Theory]
    [InlineData(AccessRequestResult.AlreadyGranted, 409)]
    [InlineData(AccessRequestResult.AlreadyPending, 409)]
    [InlineData(AccessRequestResult.RateLimited, 429)]
    [InlineData(AccessRequestResult.BacklogFull, 503)]
    public async Task AccessRequestRefusalsMapToStableStatuses(AccessRequestResult result, int status)
    {
        var (controller, store) = Create([], body: """{"role":"pricing_admin","justification":"I maintain prices."}""");
        store.RequestResult = result;
        Assert.Equal(status, Status(await controller.RequestAsync(default)));
    }

    [Fact]
    public async Task OnlyTheFounderCanListDecideOrRevoke()
    {
        var (admin, _) = Create(["pricing_admin"], stepUp: true, body: """{"decision":"APPROVE"}""");
        Assert.Equal(403, Status(await admin.ListRequestsAsync(null, default)));
        Assert.Equal(403, Status(await admin.DecideAsync(Guid.NewGuid(), default)));
        Assert.Equal(403, Status(await admin.ListGrantsAsync(default)));
        Assert.Equal(403, Status(await admin.RevokeAsync(Guid.NewGuid(), default)));

        var (founder, _) = Create(["founder"]);
        Assert.Equal(200, Status(await founder.ListRequestsAsync("pending", default)));
        Assert.Equal(400, Status(await founder.ListRequestsAsync("OTHER", default)));
        Assert.Equal(200, Status(await founder.ListGrantsAsync(default)));
    }

    [Fact]
    public async Task ApprovalNeedsAFreshStrongSignInButRejectionDoesNot()
    {
        var (noStepUp, store) = Create(["founder"], body: """{"decision":"approve","reason":"Known colleague"}""");
        Assert.Equal(403, Status(await noStepUp.DecideAsync(Guid.NewGuid(), default)));
        Assert.Null(store.Decided);

        var (reject, rejectStore) = Create(["founder"], body: """{"decision":"REJECT"}""");
        Assert.Equal(200, Status(await reject.DecideAsync(Guid.NewGuid(), default)));
        Assert.Equal((false, "owner@example.org"), rejectStore.Decided);

        var (approve, approveStore) = Create(["founder"], stepUp: true, body: """{"decision":"APPROVE"}""");
        Assert.Equal(200, Status(await approve.DecideAsync(Guid.NewGuid(), default)));
        Assert.Equal((true, "owner@example.org"), approveStore.Decided);
    }

    [Theory]
    [InlineData("""{"decision":"MAYBE"}""", 400)]
    [InlineData("""{}""", 400)]
    [InlineData("""{"decision":"REJECT","reason":""}""", 400)]
    public async Task InvalidDecisionsAreRefused(string body, int status) =>
        Assert.Equal(status, Status(await Create(["founder"], stepUp: true, body: body).Controller.DecideAsync(Guid.NewGuid(), default)));

    [Theory]
    [InlineData(AccessDecisionResult.NotFound, 404)]
    [InlineData(AccessDecisionResult.NotPending, 409)]
    [InlineData(AccessDecisionResult.SelfApproval, 403)]
    public async Task DecisionRefusalsMapToStableStatuses(AccessDecisionResult result, int status)
    {
        var (controller, store) = Create(["founder"], stepUp: true, body: """{"decision":"APPROVE"}""");
        store.DecisionResult = result;
        Assert.Equal(status, Status(await controller.DecideAsync(Guid.NewGuid(), default)));
    }

    [Fact]
    public async Task UnverifiedFounderTokensCannotDecideOrRevoke()
    {
        Assert.Equal(403, Status(await Create(["founder"], stepUp: true, verified: false, body: """{"decision":"APPROVE"}""").Controller.DecideAsync(Guid.NewGuid(), default)));
        Assert.Equal(403, Status(await Create(["founder"], verified: false, body: """{"reason":"left"}""").Controller.RevokeAsync(Guid.NewGuid(), default)));
    }

    [Theory]
    [InlineData(AccessRevocationResult.Revoked, 200)]
    [InlineData(AccessRevocationResult.NotFound, 404)]
    [InlineData(AccessRevocationResult.ProtectedFounder, 409)]
    public async Task RevocationMapsToStableStatuses(AccessRevocationResult result, int status)
    {
        var (controller, store) = Create(["founder"], body: """{"reason":"Left the team"}""");
        store.RevocationResult = result;
        Assert.Equal(status, Status(await controller.RevokeAsync(Guid.NewGuid(), default)));
        Assert.Equal(400, Status(await Create(["founder"], body: "{}").Controller.RevokeAsync(Guid.NewGuid(), default)));
    }
}
