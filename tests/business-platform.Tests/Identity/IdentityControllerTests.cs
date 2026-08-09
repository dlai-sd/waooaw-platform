// Implements: architecture/reference/components/identity-boundary.md §F2 Backend Tests
// constitutional_basis: C-023, C-026, C-059

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

// ── In-memory factory for IdentityDbContext (tests only) ─────────────────────

internal sealed class InMemoryIdentityDbContextFactory(string dbName)
    : IDbContextFactory<IdentityDbContext>
{
    public IdentityDbContext CreateDbContext() =>
        new(new DbContextOptionsBuilder<IdentityDbContext>()
            .UseInMemoryDatabase(dbName)
            .Options);
}

internal sealed class CapturingVerificationDispatcher : IIdentityVerificationDispatcher
{
    public string? LatestCode { get; private set; }

    public Task DispatchAsync(
        IdentityVerificationPurpose purpose,
        string destination,
        string code,
        CancellationToken ct)
    {
        LatestCode = code;
        return Task.CompletedTask;
    }
}

internal sealed class FailingVerificationDispatcher : IIdentityVerificationDispatcher
{
    public Task DispatchAsync(
        IdentityVerificationPurpose purpose,
        string destination,
        string code,
        CancellationToken ct) =>
        throw new InvalidOperationException("provider unavailable");
}

// ── Test helpers ─────────────────────────────────────────────────────────────

internal static class IdentityTestHelpers
{
    private const string TestHmacKey = "test-only-identity-hmac-key-32-bytes-minimum";

    public static IdentityController CreateController(
        IDbContextFactory<IdentityDbContext> factory,
        string subject = "test-subject",
        string? tenantId = null,
        string? identityProvider = null,
        string? providerIssuer = null,
        string? email = null,
        bool emailVerified = false,
        long? authTimestamp = null,
        CapturingVerificationDispatcher? dispatcher = null)
    {
        var service = CreateService(factory, dispatcher);

        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, subject),
        };
        if (email is not null) claims.Add(new Claim("email", email));
        if (emailVerified) claims.Add(new Claim("email_verified", "true"));
        if (identityProvider is not null) claims.Add(new Claim("identity_provider", identityProvider));
        if (providerIssuer is not null) claims.Add(new Claim("iss", providerIssuer));
        if (authTimestamp.HasValue) claims.Add(new Claim("auth_time", authTimestamp.Value.ToString()));

        var user = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test"));

        var httpContext = new DefaultHttpContext { User = user };
        httpContext.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        if (tenantId is not null)
            httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId;

        return new IdentityController(service, NullLogger<IdentityController>.Instance)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
    }

    public static IdentityService CreateService(
        IDbContextFactory<IdentityDbContext> factory,
        CapturingVerificationDispatcher? dispatcher = null) =>
        new(
            factory,
            Options.Create(new IdentityHmacOptions { Key = TestHmacKey }),
            dispatcher ?? new CapturingVerificationDispatcher());

    // Sets a fresh idempotency key for each call
    public static void RefreshIdempotencyKey(ControllerBase controller) =>
        controller.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();

    // Creates a controller with an arbitrary dispatcher (e.g. FailingVerificationDispatcher)
    public static IdentityController CreateControllerWithDispatcher(
        IDbContextFactory<IdentityDbContext> factory,
        IIdentityVerificationDispatcher dispatcher,
        string subject = "test-subject",
        string? tenantId = null,
        string? identityProvider = null,
        long? authTimestamp = null)
    {
        var service = new IdentityService(
            factory,
            Options.Create(new IdentityHmacOptions { Key = TestHmacKey }),
            dispatcher);

        var claims = new List<Claim> { new(ClaimTypes.NameIdentifier, subject) };
        if (identityProvider is not null) claims.Add(new Claim("identity_provider", identityProvider));
        if (authTimestamp.HasValue) claims.Add(new Claim("auth_time", authTimestamp.Value.ToString()));

        var user = new ClaimsPrincipal(new ClaimsIdentity(claims, "Test"));
        var httpContext = new DefaultHttpContext { User = user };
        httpContext.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        if (tenantId is not null)
            httpContext.Items[TenantIsolationMiddleware.TenantIdItemKey] = tenantId;

        return new IdentityController(service, NullLogger<IdentityController>.Instance)
        {
            ControllerContext = new ControllerContext { HttpContext = httpContext },
        };
    }
}

// ── Registration Tests ────────────────────────────────────────────────────────

public sealed class IdentityRegistrationTests
{
    [Fact]
    public async Task F2_StartRegistration_Google_Returns201WithRegistrationId()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory,
            identityProvider: "google", email: "test@example.com", emailVerified: true);

        var result = await ctrl.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None);

        var created = Assert.IsType<ObjectResult>(result);
        Assert.Equal(201, created.StatusCode);
        var json = JsonSerializer.Serialize(created.Value);
        Assert.Contains("RegistrationId", json);
        Assert.DoesNotContain("TenantId", json);
        Assert.DoesNotContain("EmailHmacKey", json);
    }

    [Fact]
    public async Task F2_StartRegistration_SameIdempotencyKey_Replays()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "google");

        var first = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var firstJson = JsonSerializer.SerializeToElement(first.Value);
        var regId = firstJson.GetProperty("RegistrationId").GetGuid();

        // Same Idempotency-Key → replay
        var replay = Assert.IsType<OkObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var replayJson = JsonSerializer.SerializeToElement(replay.Value);
        Assert.Equal(regId, replayJson.GetProperty("RegistrationId").GetGuid());
    }

    [Fact]
    public async Task F2_StartRegistration_Facebook_Returns403ActionDenied()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "facebook");

        var result = await ctrl.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_ACTION_DENIED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistration_Apple_Returns403ActionDenied()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "apple");

        var result = await ctrl.StartRegistrationAsync(
            new StartRegistrationRequest("en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_ACTION_DENIED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetRegistration_CrossTenant_Returns404NotAccessible()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "subject-a", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(created.Value);
        var regId = json.GetProperty("RegistrationId").GetGuid();

        // Different subject tries to read the registration
        var ctrl2 = IdentityTestHelpers.CreateController(factory, subject: "subject-b", identityProvider: "google");
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl2);

        var result = await ctrl2.GetRegistrationAsync(regId, CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        var errJson = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE", errJson.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetRegistration_SameSubject_Returns200()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "same-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(created.Value);
        var regId = json.GetProperty("RegistrationId").GetGuid();

        var result = await ctrl.GetRegistrationAsync(regId, CancellationToken.None);
        Assert.IsType<OkObjectResult>(result);
    }

    [Fact]
    public async Task F2_UpdateProfile_SetsMinimumFields_StateAdvances()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "profile-sub",
            identityProvider: "google", email: "p@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var update = await ctrl.UpdateProfileAsync(regId, new UpdateRegistrationProfileRequest(
            "Test User", "Acme", "Retail", "en"), CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(update);
        var updJson = JsonSerializer.SerializeToElement(ok.Value);
        Assert.Equal("READY_TO_COMPLETE", updJson.GetProperty("State").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_WithoutEmail_Returns422VerificationRequired()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // emailVerified = false
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "incomplete-sub",
            identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(422, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_VERIFICATION_REQUIRED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_WithEmail_Returns200AccountCreated()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "complete-sub",
            identityProvider: "google", email: "c@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(regId, new UpdateRegistrationProfileRequest(
            "Full Name", "Corp", "Consulting", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var json = JsonSerializer.SerializeToElement(ok.Value);
        Assert.Equal("ACCOUNT_CREATED", json.GetProperty("Outcome").GetString());
        Assert.Equal("AAL2_ACCOUNT", json.GetProperty("AssuranceLevel").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_Replay_ReturnsSameOutcome()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "replay-comp",
            identityProvider: "google", email: "r@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(regId, new UpdateRegistrationProfileRequest(
            "Name", "Co", "Domain", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var first = Assert.IsType<OkObjectResult>(
            await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None));
        var firstRef = JsonSerializer.SerializeToElement(first.Value).GetProperty("AccountReference").GetGuid();

        // Same idempotency key → replay
        var replay = Assert.IsType<OkObjectResult>(
            await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None));
        var replayRef = JsonSerializer.SerializeToElement(replay.Value).GetProperty("AccountReference").GetGuid();

        Assert.Equal(firstRef, replayRef);
    }
}

// ── Email Verification Tests ──────────────────────────────────────────────────

public sealed class IdentityEmailVerificationTests
{
    [Fact]
    public async Task F2_StartEmailVerification_Returns202Challenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.StartEmailVerificationAsync(regId,
            new StartEmailVerificationRequest("test@example.com"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(202, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Contains("ChallengeId", json.ToString());
        // Must never return raw email or match keys
        Assert.DoesNotContain("test@example.com", json.ToString());
    }

    [Fact]
    public async Task F2_StartEmailVerification_AntiEnumeration_SameResponseShape()
    {
        // Both known and unknown emails must return the same 202 shape
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ae-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var r1 = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("known@example.com"), CancellationToken.None));

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var r2 = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("unknown@example.com"), CancellationToken.None));

        // Both must be 202
        Assert.Equal(202, r1.StatusCode);
        Assert.Equal(202, r2.StatusCode);
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_ExpiredChallenge_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "exp-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var chResp = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("test@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(chResp.Value).GetProperty("ChallengeId").GetGuid();

        // Manually expire the challenge
        await using var db = factory.CreateDbContext();
        var ch = await db.VerificationChallenges.FindAsync(challengeId);
        ch!.State = IdentityVerificationState.Expired;
        await db.SaveChangesAsync();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_WrongCode_Returns403AndLeavesChallengePending()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "wrong-email-code", dispatcher: dispatcher);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("person@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var denied = Assert.IsType<ObjectResult>(await ctrl.ConfirmEmailVerificationAsync(
            regId, new(challengeId, "000000"), CancellationToken.None));
        Assert.Equal(403, denied.StatusCode);
        Assert.NotEqual("000000", dispatcher.LatestCode);

        await using var db = factory.CreateDbContext();
        var challenge = await db.VerificationChallenges.FindAsync(challengeId);
        Assert.Equal(IdentityVerificationState.Pending, challenge!.State);
        Assert.False((await db.Registrations.FindAsync(regId))!.EmailVerified);
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_ValidDispatchedCode_SucceedsWithoutPersistingRawCode()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "valid-email-code", dispatcher: dispatcher);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("person@example.com"), CancellationToken.None));
        var responseJson = JsonSerializer.Serialize(started.Value);
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();
        Assert.NotNull(dispatcher.LatestCode);
        Assert.DoesNotContain(dispatcher.LatestCode!, responseJson);

        await using (var db = factory.CreateDbContext())
        {
            var challenge = await db.VerificationChallenges.FindAsync(challengeId);
            Assert.NotEqual(dispatcher.LatestCode, challenge!.CodeHmac);
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var confirmed = Assert.IsType<OkObjectResult>(await ctrl.ConfirmEmailVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        Assert.True(JsonSerializer.SerializeToElement(confirmed.Value).GetProperty("EmailVerified").GetBoolean());
    }
}

// ── Idempotency Conflict Tests ────────────────────────────────────────────────

public sealed class IdentityIdempotencyTests
{
    [Fact]
    public async Task F2_DivergentIdempotencyKey_Returns409Conflict()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "idem-sub", identityProvider: "google");

        // First call
        await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None);

        // Same Idempotency-Key but different body (different canonical hash)
        var result = await ctrl.StartRegistrationAsync(new StartRegistrationRequest("fr"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(409, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_SameKeyAndHash_Replays_WithoutDoubleWrite()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "replay-sub", identityProvider: "google");

        var r1 = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        Assert.Equal(201, r1.StatusCode);

        var r2 = Assert.IsType<OkObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        Assert.Equal(200, r2.StatusCode);

        // Registration count must stay at 1
        await using var db = factory.CreateDbContext();
        Assert.Equal(1, await db.Registrations.CountAsync());
    }
}

// ── Account Link / WhatsApp Boundary Tests ────────────────────────────────────

public sealed class IdentityAccountLinkTests
{
    [Fact]
    public async Task F2_StartAccountLink_WithFreshAal3_Returns201()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var authTs = DateTimeOffset.UtcNow.AddMinutes(-1);  // within 5-minute window
        var ctrl = IdentityTestHelpers.CreateController(factory,
            subject: "link-sub",
            tenantId: Guid.NewGuid().ToString(),
            authTimestamp: authTs.ToUnixTimeSeconds());

        var result = await ctrl.StartAccountLinkAsync(
            new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(201, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Contains("LinkId", json.ToString());
        Assert.Equal("AAL3_FRESH", json.GetProperty("RequiredAssurance").GetString());
        Assert.Equal("PENDING_PORTAL_APPROVAL", json.GetProperty("State").GetString());
    }

    [Fact]
    public async Task F2_StartAccountLink_StaleSession_Returns403StepUpRequired()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var authTs = DateTimeOffset.UtcNow.AddMinutes(-10);  // outside 5-minute window
        var ctrl = IdentityTestHelpers.CreateController(factory,
            subject: "stale-sub",
            tenantId: Guid.NewGuid().ToString(),
            authTimestamp: authTs.ToUnixTimeSeconds());

        var result = await ctrl.StartAccountLinkAsync(
            new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_STEP_UP_REQUIRED", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetAccountLink_CrossTenant_Returns404NotAccessible()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantA = Guid.NewGuid().ToString();
        var tenantB = Guid.NewGuid().ToString();
        var authTs = DateTimeOffset.UtcNow.AddMinutes(-1);

        var ctrlA = IdentityTestHelpers.CreateController(factory,
            subject: "ct-sub-a", tenantId: tenantA,
            authTimestamp: authTs.ToUnixTimeSeconds());

        var created = Assert.IsType<ObjectResult>(
            await ctrlA.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Different tenant tries to read the link
        var ctrlB = IdentityTestHelpers.CreateController(factory,
            subject: "ct-sub-a", tenantId: tenantB);

        var result = await ctrlB.GetAccountLinkAsync(linkId, CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE", json.GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_GetAccountLink_WithoutTenant_Returns401SessionRequired()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No tenantId set in context
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "no-tenant-sub");

        var result = await ctrl.GetAccountLinkAsync(Guid.NewGuid(), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(401, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Equal("IDENTITY_SESSION_REQUIRED", json.GetProperty("code").GetString());
    }
}

// ── Progressive Mobile Verification Tests ────────────────────────────────────

public sealed class IdentityProgressiveMobileTests
{
    [Fact]
    public async Task F2_StartAccountMobileVerification_Returns202Challenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "mob-sub",
            tenantId: Guid.NewGuid().ToString());

        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(202, obj.StatusCode);
        var json = JsonSerializer.SerializeToElement(obj.Value);
        Assert.Contains("ChallengeId", json.ToString());
        // Never reveal actual mobile number
        Assert.DoesNotContain("+911234567890", json.ToString());
    }

    [Fact]
    public async Task F2_ProgressiveMobile_AntiEnumeration_SameResponseShape()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl1 = IdentityTestHelpers.CreateController(factory, subject: "mob-ae-1");
        var ctrl2 = IdentityTestHelpers.CreateController(factory, subject: "mob-ae-2");

        // Both existing and non-existing mobiles must return the same 202 shape
        var r1 = Assert.IsType<ObjectResult>(
            await ctrl1.StartAccountMobileVerificationAsync(
                new StartMobileVerificationRequest("+919999999999"), CancellationToken.None));
        var r2 = Assert.IsType<ObjectResult>(
            await ctrl2.StartAccountMobileVerificationAsync(
                new StartMobileVerificationRequest("+911111111111"), CancellationToken.None));

        Assert.Equal(202, r1.StatusCode);
        Assert.Equal(202, r2.StatusCode);
    }

    [Fact]
    public async Task F2_ProgressiveMobile_ValidCode_ReplaysStableOutcome()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "progressive-mobile", dispatcher: dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var key = ctrl.Request.Headers["Idempotency-Key"].ToString();

        var first = Assert.IsType<OkObjectResult>(await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var firstJson = JsonSerializer.SerializeToElement(first.Value);
        Assert.NotEqual("***", firstJson.GetProperty("MaskedMobile").GetString());

        ctrl.Request.Headers["Idempotency-Key"] = key;
        var replay = Assert.IsType<OkObjectResult>(await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var replayJson = JsonSerializer.SerializeToElement(replay.Value);
        Assert.Equal(firstJson.GetProperty("MaskedMobile").GetString(), replayJson.GetProperty("MaskedMobile").GetString());
        Assert.Equal(firstJson.GetProperty("VerifiedAt").GetDateTimeOffset(), replayJson.GetProperty("VerifiedAt").GetDateTimeOffset());
    }

    [Fact]
    public async Task F2_RegistrationMobile_StoresMatchKeyAndRejectsCrossRegistrationChallenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "mobile-registration", dispatcher: dispatcher);
        var first = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var reg1 = JsonSerializer.SerializeToElement(first.Value).GetProperty("RegistrationId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var second = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("fr"), CancellationToken.None));
        var reg2 = JsonSerializer.SerializeToElement(second.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            reg1, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        await using (var db = factory.CreateDbContext())
        {
            var registration = await db.Registrations.FindAsync(reg1);
            Assert.NotNull(registration!.MobileHmacKey);
            Assert.DoesNotContain("+911234567890", registration.MobileHmacKey!);
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var inaccessible = Assert.IsType<ObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            reg2, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        Assert.Equal(404, inaccessible.StatusCode);
    }

    [Fact]
    public async Task F2_ProgressiveMobile_WrongCode_Returns403AndLeavesChallengePending()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "wrong-mobile-code", dispatcher: dispatcher);
        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var denied = Assert.IsType<ObjectResult>(await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "000000"), CancellationToken.None));
        Assert.Equal(403, denied.StatusCode);

        await using var db = factory.CreateDbContext();
        Assert.Equal(IdentityVerificationState.Pending,
            (await db.VerificationChallenges.FindAsync(challengeId))!.State);
    }
}

// ── Provider-Subject Binding Tests ────────────────────────────────────────────

public sealed class IdentityProviderSubjectBindingTests
{
    [Fact]
    public async Task F2_GoogleRegistration_BindsProviderLabel()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory,
            subject: "google-sub", identityProvider: "google",
            email: "g@example.com", emailVerified: true);

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(result.Value);

        Assert.Equal("GOOGLE", json.GetProperty("AuthenticationPath").GetString());
        Assert.True(json.GetProperty("EmailVerified").GetBoolean());
    }

    [Fact]
    public async Task F2_CredentialRegistration_NoProviderLabel()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No identity_provider claim → CREDENTIAL path
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cred-sub");

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(result.Value);

        Assert.Equal("CREDENTIAL", json.GetProperty("AuthenticationPath").GetString());
    }

    [Fact]
    public async Task F2_TenantIdNeverAcceptedFromRequest_UsesJwtClaimOnly()
    {
        // The registration request body must not contain tenantId
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "tenant-sub", identityProvider: "google");

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = result.Value!.GetType().GetProperties();

        // Ensure no tenant_id property exists in the registration response
        Assert.DoesNotContain(json, p => p.Name.ToLowerInvariant().Contains("tenantid"));
    }

    [Fact]
    public async Task F2_SameSubjectFromDifferentIssuers_CreatesDistinctBindings()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var idempotencyKey = Guid.NewGuid().ToString();
        var first = IdentityTestHelpers.CreateController(factory, subject: "shared-subject", providerIssuer: "issuer-a");
        first.Request.Headers["Idempotency-Key"] = idempotencyKey;
        var second = IdentityTestHelpers.CreateController(factory, subject: "shared-subject", providerIssuer: "issuer-b");
        second.Request.Headers["Idempotency-Key"] = idempotencyKey;

        Assert.Equal(201, Assert.IsType<ObjectResult>(await first.StartRegistrationAsync(new("en"), CancellationToken.None)).StatusCode);
        Assert.Equal(201, Assert.IsType<ObjectResult>(await second.StartRegistrationAsync(new("en"), CancellationToken.None)).StatusCode);

        await using var db = factory.CreateDbContext();
        var registrations = await db.Registrations.OrderBy(value => value.ProviderIssuer).ToListAsync();
        Assert.Equal(["issuer-a", "issuer-b"], registrations.Select(value => value.ProviderIssuer));
        Assert.NotEqual(registrations[0].ActorSubject, registrations[1].ActorSubject);
    }

    [Fact]
    public async Task F2_GoogleVerifiedEmail_NextActionIsCompleteProfile()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, identityProvider: "google", emailVerified: true);
        var result = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        Assert.Equal("COMPLETE_PROFILE", JsonSerializer.SerializeToElement(result.Value).GetProperty("NextAction").GetString());
    }
}

// ── Email Masking / Privacy Tests ─────────────────────────────────────────────

public sealed class IdentityPrivacyTests
{
    [Theory]
    [InlineData("user@example.com", "u***@example.com")]
    [InlineData("ab@domain.org", "a***@domain.org")]
    public void F2_MaskEmail_MasksLocalPart(string email, string expected)
    {
        Assert.Equal(expected, IdentityService.MaskEmail(email));
    }

    [Fact]
    public void F2_MaskMobile_MasksMiddle()
    {
        var masked = IdentityService.MaskMobile("+911234567890");
        Assert.Contains("***", masked);
        Assert.DoesNotContain("12345678", masked);
    }

    [Fact]
    public async Task F2_StartEmailVerification_NeverExposesRawEmail()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "priv-sub", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.StartEmailVerificationAsync(regId,
            new StartEmailVerificationRequest("secret@example.com"), CancellationToken.None);

        var responseBody = JsonSerializer.Serialize(result);
        Assert.DoesNotContain("secret@example.com", responseBody);
        Assert.DoesNotContain("secret", responseBody.ToLowerInvariant().Replace("emailverified", ""));
    }

    [Fact]
    public async Task F2_Registration_ResponseNeverContainsHmacKeys()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "hmac-sub",
            identityProvider: "google", email: "h@example.com", emailVerified: true);

        var result = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var json = JsonSerializer.Serialize(result.Value);

        Assert.DoesNotContain("hmac", json.ToLowerInvariant());
        Assert.DoesNotContain("emailHmacKey", json);
        Assert.DoesNotContain("mobileHmacKey", json);
    }
}

// ── WhatsApp Boundary Tests ───────────────────────────────────────────────────

public sealed class IdentityWhatsAppBoundaryTests
{
    [Fact]
    public async Task F2_StartRegistration_WhatsApp_Returns403ActionDenied()
    {
        // WhatsApp registration must only come through internal server-to-server adapter,
        // never through the browser endpoint.
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // Simulate a WhatsApp "provider" claim (e.g. someone trying to inject it)
        // The service blocks it regardless of how authPath resolves in the controller.
        // Since the controller derives from identity_provider claim and none maps to WhatsApp,
        // we test the service directly with the WhatsApp path.
        var service = IdentityTestHelpers.CreateService(factory);
        var ex = await Assert.ThrowsAsync<IdentityActionDeniedException>(() =>
            service.StartRegistrationAsync(
                "wa-sub", Guid.NewGuid(), "hash", "en",
                IdentityAuthenticationPath.WhatsApp,
            null, null, false, null, null,
                CancellationToken.None));
        Assert.Contains("WhatsApp", ex.Message);
    }
}

public sealed class IdentityInputAndConfigurationTests
{
    [Fact]
    public async Task F2_InvalidLocaleEmailAndMobile_Return400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory);
        Assert.Equal(400, Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new("english"), CancellationToken.None)).StatusCode);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var created = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();
        Assert.Equal(400, Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("not-an-email"), CancellationToken.None)).StatusCode);
        Assert.Equal(400, Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("12345"), CancellationToken.None)).StatusCode);
    }

    [Fact]
    public void F2_MissingOrShortHmacSecret_FailsClosed()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        Assert.Throws<InvalidOperationException>(() => new IdentityService(
            factory,
            Options.Create(new IdentityHmacOptions { Key = "short" }),
            new CapturingVerificationDispatcher()));
    }

    [Fact]
    public async Task F2_UnconfiguredDelivery_Returns503WithoutSuccessfulIdempotencyRecord()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var service = new IdentityService(
            factory,
            Options.Create(new IdentityHmacOptions { Key = "test-only-identity-hmac-key-32-bytes-minimum" }),
            new FailingVerificationDispatcher());
        var user = new ClaimsPrincipal(new ClaimsIdentity(
            [new Claim(ClaimTypes.NameIdentifier, "delivery-failure")], "Test"));
        var context = new DefaultHttpContext { User = user };
        context.Request.Headers["Idempotency-Key"] = Guid.NewGuid().ToString();
        var ctrl = new IdentityController(service, NullLogger<IdentityController>.Instance)
        {
            ControllerContext = new ControllerContext { HttpContext = context },
        };
        var created = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationAsync(new("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = Assert.IsType<ObjectResult>(await ctrl.StartEmailVerificationAsync(
            regId, new("person@example.com"), CancellationToken.None));
        Assert.Equal(503, result.StatusCode);

        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.IdempotencyLedger.Where(value =>
            value.OperationFamily == "StartEmailVerification").ToListAsync());
        Assert.Equal(IdentityVerificationState.Expired,
            (await db.VerificationChallenges.SingleAsync()).State);
    }
}

// ── Update Profile Error Tests ────────────────────────────────────────────────

public sealed class IdentityUpdateProfileErrorTests
{
    [Fact]
    public async Task F2_UpdateProfile_NotFound_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "upd-notfound");

        var result = await ctrl.UpdateProfileAsync(Guid.NewGuid(),
            new UpdateRegistrationProfileRequest("N", "B", "D", "en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_UpdateProfile_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "upd-idem", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First call with BodyA
        await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("Alice", "AcmeA", "RetailA", "en"), CancellationToken.None);

        // Same idempotency key, different body → conflict
        var conflict = await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("Bob", "AcmeB", "RetailB", "fr"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_UpdateProfile_BadIdempotencyKey_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "upd-badkey", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        ctrl.Request.Headers["Idempotency-Key"] = "not-a-guid";
        var result = await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("N", "B", "D", "en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Email Verification Additional Error Tests ─────────────────────────────────

public sealed class IdentityEmailVerificationAdditionalTests
{
    [Fact]
    public async Task F2_StartEmailVerification_UnknownRegistration_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-notfound");

        var result = await ctrl.StartEmailVerificationAsync(Guid.NewGuid(),
            new StartEmailVerificationRequest("test@example.com"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartEmailVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-idem", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First call with one email
        await ctrl.StartEmailVerificationAsync(regId, new("first@example.com"), CancellationToken.None);

        // Same key, different email → conflict
        var conflict = await ctrl.StartEmailVerificationAsync(regId, new("second@example.com"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartEmailVerification_Replay_ReturnsSameChallenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-replay", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var first = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("replay@example.com"), CancellationToken.None));
        var firstId = JsonSerializer.SerializeToElement(first.Value).GetProperty("ChallengeId").GetGuid();

        // Same idempotency key + same email → replay (same challenge id)
        var replay = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("replay@example.com"), CancellationToken.None));
        var replayId = JsonSerializer.SerializeToElement(replay.Value).GetProperty("ChallengeId").GetGuid();

        Assert.Equal(firstId, replayId);
        Assert.Equal(202, replay.StatusCode);
    }

    [Fact]
    public async Task F2_StartEmailVerification_BadIdempotencyKey_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "ev-badkey", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        ctrl.Request.Headers["Idempotency-Key"] = "not-a-guid";
        var result = await ctrl.StartEmailVerificationAsync(regId, new("t@example.com"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_InvalidCodeFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-badcode", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        // 5-digit code fails the 6-digit regex check
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(Guid.NewGuid(), "12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_UnknownChallenge_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-nochal", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // Unknown challengeId (not in DB)
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(Guid.NewGuid(), "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-idem", identityProvider: "google",
            dispatcher: dispatcher);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("cev@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First confirm succeeds
        await ctrl.ConfirmEmailVerificationAsync(regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None);

        // Same idempotency key, different code → conflict
        var conflict = await ctrl.ConfirmEmailVerificationAsync(regId,
            new(challengeId, "999999"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmEmailVerification_TimeBasedExpiry_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "cev-texp", identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var started = Assert.IsType<ObjectResult>(
            await ctrl.StartEmailVerificationAsync(regId, new("texp@example.com"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // Set ExpiresAt to past while leaving State = Pending (different from the state-based expiry test)
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmEmailVerificationAsync(regId,
            new ConfirmVerificationRequest(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());

        // Challenge state must have been set to Expired by the time-check branch
        await using var db2 = factory.CreateDbContext();
        Assert.Equal(IdentityVerificationState.Expired,
            (await db2.VerificationChallenges.FindAsync(challengeId))!.State);
    }
}

// ── Registration Mobile Verification Tests ────────────────────────────────────

public sealed class IdentityRegistrationMobileVerificationTests
{
    private static async Task<(IdentityController ctrl, Guid regId)> CreateRegistrationAsync(
        InMemoryIdentityDbContextFactory factory,
        string subject,
        CapturingVerificationDispatcher? dispatcher = null)
    {
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: subject,
            identityProvider: "google", dispatcher: dispatcher);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        return (ctrl, regId);
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_UnknownRegistration_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "rmv-notfound");

        var result = await ctrl.StartRegistrationMobileVerificationAsync(Guid.NewGuid(),
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "rmv-idem");

        // First call with +91 number
        await ctrl.StartRegistrationMobileVerificationAsync(regId,
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        // Same key, different mobile → conflict
        var conflict = await ctrl.StartRegistrationMobileVerificationAsync(regId,
            new StartMobileVerificationRequest("+911234567891"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_Replay_ReturnsSameChallenge()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "rmv-replay");

        // First call
        var first = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var firstId = JsonSerializer.SerializeToElement(first.Value).GetProperty("ChallengeId").GetGuid();

        // Same key + same mobile → replay
        var replay = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        Assert.Equal(firstId, JsonSerializer.SerializeToElement(replay.Value).GetProperty("ChallengeId").GetGuid());
        Assert.Equal(202, replay.StatusCode);
    }

    [Fact]
    public async Task F2_StartRegistrationMobileVerification_DeliveryFailure_Returns503()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // Registration itself never dispatches, so FailingVerificationDispatcher is safe here
        var ctrl = IdentityTestHelpers.CreateControllerWithDispatcher(factory,
            new FailingVerificationDispatcher(), subject: "rmv-delivery", identityProvider: "google");
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.StartRegistrationMobileVerificationAsync(regId,
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(503, obj.StatusCode);
        Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_InvalidCodeFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "crmv-badcode");

        // 5-digit code is invalid
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(Guid.NewGuid(),
            new ConfirmVerificationRequest(Guid.NewGuid(), "12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_ValidCode_ReturnsRegistrationResponse()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-success", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var confirmed = Assert.IsType<OkObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));

        // The response must be IdentityRegistrationResponse shape (has RegistrationId, MobileVerified, etc.)
        var json = JsonSerializer.SerializeToElement(confirmed.Value);
        Assert.True(json.GetProperty("MobileVerified").GetBoolean());
        Assert.Equal(regId, json.GetProperty("RegistrationId").GetGuid());
        Assert.DoesNotContain("+911234567890", json.ToString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_Replay_ReturnsSameRegistration()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-replay", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var idemKey = ctrl.Request.Headers["Idempotency-Key"].ToString();

        // First confirm
        var first = Assert.IsType<OkObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var firstReg = JsonSerializer.SerializeToElement(first.Value).GetProperty("RegistrationId").GetGuid();

        // Replay with same idempotency key
        ctrl.Request.Headers["Idempotency-Key"] = idemKey;
        var replay = Assert.IsType<OkObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None));
        var replayReg = JsonSerializer.SerializeToElement(replay.Value).GetProperty("RegistrationId").GetGuid();

        Assert.Equal(firstReg, replayReg);
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-idem", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First confirm with correct code
        await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, dispatcher.LatestCode!), CancellationToken.None);

        // Same key, different code → hash differs → conflict
        var conflict = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "999999"), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_ExpiredByState_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-stateexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            ch!.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_TimeExpired_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-timeexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // Keep State = Pending but put ExpiresAt in the past
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_WrongCode_Returns403()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-wrongcode", dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartRegistrationMobileVerificationAsync(
            regId, new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var denied = Assert.IsType<ObjectResult>(await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(challengeId, "000000"), CancellationToken.None));

        Assert.Equal(403, denied.StatusCode);
        Assert.NotEqual("000000", dispatcher.LatestCode);
    }

    [Fact]
    public async Task F2_ConfirmRegistrationMobileVerification_UnknownChallenge_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var (ctrl, regId) = await CreateRegistrationAsync(factory, "crmv-nochal");

        // Unknown challengeId (not in DB)
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmRegistrationMobileVerificationAsync(
            regId, new(Guid.NewGuid(), "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Account Mobile Error Tests ────────────────────────────────────────────────

public sealed class IdentityAccountMobileErrorTests
{
    [Fact]
    public async Task F2_StartAccountMobileVerification_InvalidMobileFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "amv-badmob");

        // Missing + prefix → invalid E.164
        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "amv-idem");

        // First call
        await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        // Same key, different mobile → conflict
        var conflict = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567891"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountMobileVerification_DeliveryFailure_Returns503()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateControllerWithDispatcher(factory,
            new FailingVerificationDispatcher(), subject: "amv-delivery");

        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(503, obj.StatusCode);
        Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_InvalidCodeFormat_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-badcode");

        // 5-digit code is invalid format
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new ConfirmVerificationRequest(Guid.NewGuid(), "12345"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new CapturingVerificationDispatcher();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-idem", dispatcher: dispatcher);

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // First confirm succeeds
        await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, dispatcher.LatestCode!), CancellationToken.None);

        // Same key, different code → conflict
        var conflict = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "999999"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_ExpiredByState_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-stateexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            ch!.State = IdentityVerificationState.Expired;
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_TimeExpired_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-timeexp");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // State stays Pending, ExpiresAt set to past
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ConfirmAccountMobileVerification_UnknownChallenge_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "camv-nochal");

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        // Unknown challengeId (not in DB)
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(Guid.NewGuid(), "123456"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Complete Registration Error Tests ─────────────────────────────────────────

public sealed class IdentityCompleteRegistrationErrorTests
{
    [Fact]
    public async Task F2_CompleteRegistration_UnknownRegistration_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "comp-notfound");

        var result = await ctrl.CompleteRegistrationAsync(Guid.NewGuid(), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "comp-idem",
            identityProvider: "google", email: "comp@example.com", emailVerified: true);

        // Create two registrations for the same subject (different idempotency keys)
        var created1 = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var reg1Id = JsonSerializer.SerializeToElement(created1.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var created2 = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("fr"), CancellationToken.None));
        var reg2Id = JsonSerializer.SerializeToElement(created2.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(reg1Id,
            new UpdateRegistrationProfileRequest("Name", "Co", "Domain", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(reg2Id,
            new UpdateRegistrationProfileRequest("Name", "Co", "Domain", "en"), CancellationToken.None);

        // Complete reg1 with idempotency key K → records hash(reg1Id)
        var completeKey = Guid.NewGuid().ToString();
        ctrl.Request.Headers["Idempotency-Key"] = completeKey;
        await ctrl.CompleteRegistrationAsync(reg1Id, CancellationToken.None);

        // Same key K, different registrationId → hash(reg2Id) ≠ hash(reg1Id) → conflict
        ctrl.Request.Headers["Idempotency-Key"] = completeKey;
        var conflict = await ctrl.CompleteRegistrationAsync(reg2Id, CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_CompleteRegistration_WithEmailButMissingProfile_Returns422()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // Email is verified by claim but profile fields (DisplayName etc.) not set
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "comp-noprofile",
            identityProvider: "google", email: "np@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        // Skip UpdateProfile — DisplayName/BusinessName/BusinessDomain are null
        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(422, obj.StatusCode);
        Assert.Equal("IDENTITY_VERIFICATION_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}

// ── Account Link Full Flow Tests ──────────────────────────────────────────────

public sealed class IdentityAccountLinkFullFlowTests
{
    private static long FreshAuthTs => DateTimeOffset.UtcNow.AddMinutes(-1).ToUnixTimeSeconds();
    private static long StaleAuthTs => DateTimeOffset.UtcNow.AddMinutes(-10).ToUnixTimeSeconds();

    [Fact]
    public async Task F2_StartAccountLink_NoTenant_Returns401()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No tenantId in context
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "link-notenant",
            authTimestamp: FreshAuthTs);

        var result = await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(401, obj.StatusCode);
        Assert.Equal("IDENTITY_SESSION_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountLink_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "link-idem",
            tenantId: Guid.NewGuid().ToString(), authTimestamp: FreshAuthTs);

        // First call with proofId A
        await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);

        // Same key, different proofId → conflict
        var conflict = await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None);
        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartAccountLink_Replay_ReturnsSameLink()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "link-replay",
            tenantId: Guid.NewGuid().ToString(), authTimestamp: FreshAuthTs);

        var proofId = Guid.NewGuid();
        var first = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(proofId), CancellationToken.None));
        var firstLinkId = JsonSerializer.SerializeToElement(first.Value).GetProperty("LinkId").GetGuid();

        // Same key + same proofId → replay
        var replay = Assert.IsType<OkObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(proofId), CancellationToken.None));
        var replayLinkId = JsonSerializer.SerializeToElement(replay.Value).GetProperty("LinkId").GetGuid();

        Assert.Equal(firstLinkId, replayLinkId);
    }

    [Fact]
    public async Task F2_ApproveAccountLink_NoTenant_Returns401()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        // No tenantId
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-notenant",
            authTimestamp: FreshAuthTs);

        var result = await ctrl.ApproveAccountLinkAsync(Guid.NewGuid(), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(401, obj.StatusCode);
        Assert.Equal("IDENTITY_SESSION_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_FreshSession_Returns200WithPendingState()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-ok",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var approved = Assert.IsType<OkObjectResult>(
            await ctrl.ApproveAccountLinkAsync(linkId, CancellationToken.None));

        var json = JsonSerializer.SerializeToElement(approved.Value);
        Assert.Equal("PENDING_WHATSAPP_CONFIRMATION", json.GetProperty("State").GetString());
        Assert.Equal(linkId, json.GetProperty("LinkId").GetGuid());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_StaleSession_Returns403()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        // Create link with fresh session
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-stale",
            tenantId: tenantId, authTimestamp: FreshAuthTs);
        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Approve with stale session (different controller, same subject/tenant but stale auth_time)
        var staleCtrl = IdentityTestHelpers.CreateController(factory, subject: "approve-stale",
            tenantId: tenantId, authTimestamp: StaleAuthTs);

        var result = await staleCtrl.ApproveAccountLinkAsync(linkId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        Assert.Equal("IDENTITY_STEP_UP_REQUIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_IdempotencyConflict_Returns409()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-idem",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        // Create two links
        var link1 = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var link1Id = JsonSerializer.SerializeToElement(link1.Value).GetProperty("LinkId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var link2 = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var link2Id = JsonSerializer.SerializeToElement(link2.Value).GetProperty("LinkId").GetGuid();

        // Approve link1 with key K
        var approveKey = Guid.NewGuid().ToString();
        ctrl.Request.Headers["Idempotency-Key"] = approveKey;
        await ctrl.ApproveAccountLinkAsync(link1Id, CancellationToken.None);

        // Same key K, but different linkId → hash(link2Id) ≠ hash(link1Id) → conflict
        ctrl.Request.Headers["Idempotency-Key"] = approveKey;
        var conflict = await ctrl.ApproveAccountLinkAsync(link2Id, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(conflict);
        Assert.Equal(409, obj.StatusCode);
        Assert.Equal("IDENTITY_IDEMPOTENCY_CONFLICT",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_CrossTenant_Returns404()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantA = Guid.NewGuid().ToString();
        var tenantB = Guid.NewGuid().ToString();

        var ctrlA = IdentityTestHelpers.CreateController(factory, subject: "approve-ct",
            tenantId: tenantA, authTimestamp: FreshAuthTs);
        var created = Assert.IsType<ObjectResult>(
            await ctrlA.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Try to approve with tenantB context
        var ctrlB = IdentityTestHelpers.CreateController(factory, subject: "approve-ct",
            tenantId: tenantB, authTimestamp: FreshAuthTs);

        var result = await ctrlB.ApproveAccountLinkAsync(linkId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(404, obj.StatusCode);
        Assert.Equal("IDENTITY_RESOURCE_NOT_ACCESSIBLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_ApproveAccountLink_ExpiredLink_Returns410()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "approve-exp",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        // Expire the link directly
        await using (var db = factory.CreateDbContext())
        {
            var link = await db.AccountLinks.FindAsync(linkId);
            db.Entry(link!).Property(l => l.ExpiresAt).CurrentValue = DateTimeOffset.UtcNow.AddHours(-1);
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ApproveAccountLinkAsync(linkId, CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(410, obj.StatusCode);
        Assert.Equal("IDENTITY_CHALLENGE_EXPIRED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());

        // State must have been set to Expired
        await using var db2 = factory.CreateDbContext();
        Assert.Equal(IdentityAccountLinkState.Expired, (await db2.AccountLinks.FindAsync(linkId))!.State);
    }

    [Fact]
    public async Task F2_GetAccountLink_ExistingLink_Returns200()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var tenantId = Guid.NewGuid().ToString();
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "getlink-ok",
            tenantId: tenantId, authTimestamp: FreshAuthTs);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartAccountLinkAsync(new StartAccountLinkRequest(Guid.NewGuid()), CancellationToken.None));
        var linkId = JsonSerializer.SerializeToElement(created.Value).GetProperty("LinkId").GetGuid();

        var result = await ctrl.GetAccountLinkAsync(linkId, CancellationToken.None);

        var ok = Assert.IsType<OkObjectResult>(result);
        var json = JsonSerializer.SerializeToElement(ok.Value);
        Assert.Equal(linkId, json.GetProperty("LinkId").GetGuid());
        Assert.Equal("PENDING_PORTAL_APPROVAL", json.GetProperty("State").GetString());
    }
}

// ── Registration State Machine Coverage ──────────────────────────────────────

public sealed class IdentityRegistrationStateAdditionalTests
{
    [Fact]
    public async Task F2_CompletedRegistration_GetRegistration_NextActionIsContinueToDefaultTarget()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "state-comp",
            identityProvider: "google", email: "sc@example.com", emailVerified: true);

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.UpdateProfileAsync(regId,
            new UpdateRegistrationProfileRequest("Name", "Co", "Domain", "en"), CancellationToken.None);

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        await ctrl.CompleteRegistrationAsync(regId, CancellationToken.None);

        // GetRegistration should now show Completed state and CONTINUE_TO_DEFAULT_TARGET
        var reg = Assert.IsType<OkObjectResult>(await ctrl.GetRegistrationAsync(regId, CancellationToken.None));
        var json = JsonSerializer.SerializeToElement(reg.Value);
        Assert.Equal("COMPLETED", json.GetProperty("State").GetString());
        Assert.Equal("CONTINUE_TO_DEFAULT_TARGET", json.GetProperty("NextAction").GetString());
    }

    [Fact]
    public async Task F2_NonMappedRegistrationState_NextActionIsNone()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "state-none",
            identityProvider: "google");

        var created = Assert.IsType<ObjectResult>(
            await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None));
        var regId = JsonSerializer.SerializeToElement(created.Value).GetProperty("RegistrationId").GetGuid();

        // Directly set state to a value not covered by ComputeNextAction (e.g. Cancelled)
        await using (var db = factory.CreateDbContext())
        {
            var reg = await db.Registrations.FindAsync(regId);
            reg!.State = IdentityRegistrationState.Cancelled;
            await db.SaveChangesAsync();
        }

        var result = Assert.IsType<OkObjectResult>(await ctrl.GetRegistrationAsync(regId, CancellationToken.None));
        Assert.Equal("NONE", JsonSerializer.SerializeToElement(result.Value).GetProperty("NextAction").GetString());
    }
}

// ── Dispatcher and HMAC Edge Case Tests ──────────────────────────────────────

public sealed class IdentityEdgeCaseTests
{
    [Fact]
    public async Task F2_UnconfiguredDispatcher_MobileVerification_Returns503()
    {
        // UnconfiguredVerificationDispatcher is the fail-closed stand-in shipped with the service
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateControllerWithDispatcher(factory,
            new UnconfiguredVerificationDispatcher(), subject: "unconf-mob");

        var result = await ctrl.StartAccountMobileVerificationAsync(
            new StartMobileVerificationRequest("+911234567890"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(503, obj.StatusCode);
        Assert.Equal("IDENTITY_DEPENDENCY_UNAVAILABLE",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_MalformedCodeHmac_TreatedAsWrongCode_Returns403()
    {
        // If the stored HMAC is not valid hex, VerifyCode must safely return false (no exception)
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "malformed-hmac");

        var started = Assert.IsType<ObjectResult>(await ctrl.StartAccountMobileVerificationAsync(
            new("+911234567890"), CancellationToken.None));
        var challengeId = JsonSerializer.SerializeToElement(started.Value).GetProperty("ChallengeId").GetGuid();

        // Corrupt the stored HMAC to a non-hex string
        await using (var db = factory.CreateDbContext())
        {
            var ch = await db.VerificationChallenges.FindAsync(challengeId);
            db.Entry(ch!).Property(c => c.CodeHmac).CurrentValue = "not-valid-hex!@#";
            await db.SaveChangesAsync();
        }

        IdentityTestHelpers.RefreshIdempotencyKey(ctrl);
        var result = await ctrl.ConfirmAccountMobileVerificationAsync(
            new(challengeId, "123456"), CancellationToken.None);

        // Must return 403, NOT an unhandled exception
        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(403, obj.StatusCode);
        Assert.Equal("IDENTITY_ACTION_DENIED",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }

    [Fact]
    public async Task F2_StartRegistration_BadIdempotencyKey_Returns400()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var ctrl = IdentityTestHelpers.CreateController(factory, subject: "reg-badkey");

        ctrl.Request.Headers["Idempotency-Key"] = "not-a-guid";
        var result = await ctrl.StartRegistrationAsync(new StartRegistrationRequest("en"), CancellationToken.None);

        var obj = Assert.IsType<ObjectResult>(result);
        Assert.Equal(400, obj.StatusCode);
        Assert.Equal("IDENTITY_REQUEST_INVALID",
            JsonSerializer.SerializeToElement(obj.Value).GetProperty("code").GetString());
    }
}
