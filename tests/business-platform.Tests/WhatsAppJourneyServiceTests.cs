// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-042, C-059, C-063, C-076

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Conversation;
using Waooaw.BusinessPlatform.Tests.Identity;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WhatsAppJourneyServiceTests
{
    private const string WebhookSecret = "webhook-secret-at-least-thirty-two-characters";
    private const string TokenKey = "tenant-token-key-at-least-thirty-two-characters";
    private const string ProofSigningKey = "proof-signing-key-at-least-thirty-two-characters";
    private const string ProofAudience = "waooaw-phone-identity-test";

    [Fact]
    public async Task ValidInboundCreatesOptInWithoutPersistingRawPhoneAndReplaysIdempotently()
    {
        var (service, factory, evidence) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body(
            "wamid-1",
            now,
            "+919876543210",
            "I need local customers",
            "TIER_1_LOW_RISK"
        );

        var first = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);
        var replay = await service.ReceiveAsync(
            body,
            Sign(body),
            now.AddSeconds(1),
            CancellationToken.None
        );

        Assert.Equal("ACCEPTED", first.Status);
        Assert.False(string.IsNullOrWhiteSpace(first.InternalTenantToken));
        Assert.Equal(3, first.InternalTenantToken.Split('.').Length);
        Assert.Equal(
            now.AddMinutes(30).ToUnixTimeSeconds(),
            TokenExpiry(first.InternalTenantToken)
        );
        Assert.True(replay.Replayed);
        Assert.Empty(replay.InternalTenantToken);
        Assert.Equal(1, evidence.CallCount);
        await using var db = factory.CreateDbContext();
        var contact = await db.WhatsAppJourneyContacts.SingleAsync();
        Assert.NotEqual(default, contact.OptedInAt);
        Assert.DoesNotContain("9876543210", contact.PhoneHmac, StringComparison.Ordinal);
        var receipt = await db.WhatsAppMessageReceipts.SingleAsync();
        Assert.Equal(now.AddMinutes(30), receipt.SessionExpiresAt);
        Assert.Equal(now.AddHours(24), receipt.ExpiresAt);
        Assert.DoesNotContain(
            first.InternalTenantToken,
            receipt.SessionTokenHash,
            StringComparison.Ordinal
        );
    }

    [Theory]
    [InlineData("+0123456789", 0)]
    [InlineData("919876543210", 0)]
    [InlineData("+919876543210", 6)]
    public async Task InvalidPhoneOrFutureTimestampIsRejected(string phone, int futureMinutes)
    {
        var (service, factory, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body(
            "wamid-invalid",
            now.AddMinutes(futureMinutes),
            phone,
            "Hello",
            "TIER_1_LOW_RISK"
        );

        await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(body, Sign(body), now, CancellationToken.None)
        );

        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
    }

    [Theory]
    [InlineData("bad-signature", 403)]
    [InlineData("stale", 409)]
    public async Task InvalidOrStaleInboundCreatesNoIdentity(string scenario, int statusCode)
    {
        var (service, factory, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var sentAt = scenario == "stale" ? now.AddMinutes(-6) : now;
        var body = Body("wamid-denied", sentAt, "+919876543210", "Hello", "TIER_1_LOW_RISK");
        var signature = scenario == "bad-signature" ? "sha256=00" : Sign(body);

        var exception = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(body, signature, now, CancellationToken.None)
        );

        Assert.Equal(statusCode, exception.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Empty(await db.WhatsAppMessageReceipts.ToListAsync());
    }

    [Fact]
    public async Task MediumRiskRequiresSeparateExplicitConfirmation()
    {
        var (service, _, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var request = Body(
            "wamid-risk-1",
            now,
            "+919876543210",
            "Approve campaign brief",
            "TIER_2_MEDIUM_RISK"
        );
        var confirm = Body(
            "wamid-risk-2",
            now.AddSeconds(1),
            "+919876543210",
            "YES",
            "TIER_2_MEDIUM_RISK"
        );

        var pending = await service.ReceiveAsync(
            request,
            Sign(request),
            now,
            CancellationToken.None
        );
        var accepted = await service.ReceiveAsync(
            confirm,
            Sign(confirm),
            now.AddSeconds(1),
            CancellationToken.None
        );

        Assert.Equal("CONFIRMATION_REQUIRED", pending.Status);
        Assert.Equal("ACCEPTED", accepted.Status);
    }

    [Fact]
    public async Task HighRiskAlwaysRequiresPortalStepUp()
    {
        var (service, _, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body("wamid-risk-3", now, "+919876543210", "YES", "TIER_3_HIGH_RISK");

        var result = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);

        Assert.Equal("PORTAL_STEP_UP_REQUIRED", result.Status);
        Assert.Contains("secure portal", result.Reply, StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData("STATUS", "CONTINUITY", "transport acceptance only")]
    [InlineData("TIMELINE", "CONTINUITY", "authority version")]
    [InlineData("EVIDENCE", "EVIDENCE", "time-limited canonical export")]
    [InlineData("EXPORT", "EVIDENCE", "current relationship role")]
    public async Task RelationshipContinuityCommandsPreserveAuthoritativeAndDeliveryMeaning(
        string text,
        string stage,
        string expectedReply
    )
    {
        var (service, _, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body(
            $"wamid-{text.ToLowerInvariant()}",
            now,
            "+919876543210",
            text,
            "TIER_1_LOW_RISK"
        );

        var result = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);

        Assert.Equal("ACCEPTED", result.Status);
        Assert.Equal(stage, result.JourneyStage);
        Assert.Contains(expectedReply, result.Reply, StringComparison.OrdinalIgnoreCase);
    }

    [Theory]
    [InlineData("YES")]
    [InlineData("CONFIRM")]
    [InlineData("PAY NOW")]
    public async Task TierFourContractAndPaymentActionsRemainPortalOnly(string text)
    {
        var (service, _, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body("wamid-tier-4", now, "+919876543210", text, "TIER_4_CONSEQUENTIAL");

        var result = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);

        Assert.Equal("SECURE_PORTAL_REQUIRED", result.Status);
        Assert.Contains(
            "cannot be accepted or initiated in WhatsApp",
            result.Reply,
            StringComparison.Ordinal
        );
        Assert.Contains("Hire, Not now, Cancel, or Exit", result.Reply, StringComparison.Ordinal);
        Assert.Contains("Razorpay", result.Reply, StringComparison.Ordinal);
        Assert.DoesNotContain("handoff", result.Reply, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task FirstContactFailsClosedWhenRegistrationEvidenceIsUnavailable()
    {
        var (service, factory, _) = Create(evidenceFails: true);
        var now = DateTimeOffset.UtcNow;
        var body = Body("wamid-evidence-failure", now, "+919876543210", "Hello", "TIER_1_LOW_RISK");

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.ReceiveAsync(body, Sign(body), now, CancellationToken.None)
        );

        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Empty(await db.WhatsAppMessageReceipts.ToListAsync());
    }

    [Theory]
    [InlineData("/api/v1/whatsapp/webhook", 204)]
    [InlineData("/api/v1/whatsapp/webhook/admin", 401)]
    public async Task TenantMiddlewareExemptsOnlyExactSignedWebhook(string path, int expectedStatus)
    {
        var reachedNext = false;
        var middleware = new TenantIsolationMiddleware(
            context =>
            {
                reachedNext = true;
                context.Response.StatusCode = StatusCodes.Status204NoContent;
                return Task.CompletedTask;
            },
            NullLogger<TenantIsolationMiddleware>.Instance
        );
        var context = new DefaultHttpContext();
        context.Request.Path = path;
        context.SetEndpoint(
            new Endpoint(
                _ => Task.CompletedTask,
                path == "/api/v1/whatsapp/webhook"
                    ? new EndpointMetadataCollection(new AllowAnonymousAttribute())
                    : new EndpointMetadataCollection(),
                path
            )
        );

        await middleware.InvokeAsync(context);

        Assert.Equal(expectedStatus, context.Response.StatusCode);
        Assert.Equal(expectedStatus == 204, reachedNext);
    }

    [Fact]
    public async Task ControllerDoesNotExposeInternalTenantToken()
    {
        var (service, _, _) = Create();
        var controller = new WhatsAppJourneyController(service);
        var now = DateTimeOffset.UtcNow;
        var body = Body("wamid-controller", now, "+919876543210", "Show skills", "TIER_1_LOW_RISK");
        var context = new DefaultHttpContext();
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
        context.Request.Headers["X-Hub-Signature-256"] = Sign(body);
        controller.ControllerContext = new ControllerContext { HttpContext = context };

        var response = Assert.IsType<OkObjectResult>(
            await controller.ReceiveAsync(CancellationToken.None)
        );
        var responseJson = JsonSerializer.Serialize(
            response.Value,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );

        Assert.DoesNotContain("tenantToken", responseJson, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("waooaw-phone-identity", responseJson, StringComparison.Ordinal);
    }

    [Fact]
    public async Task OptionsAwareControllerEnforcesVerificationHostAndMediaBoundary()
    {
        var (service, _, _) = Create();
        var journey = new WhatsAppJourneyOptions
        {
            VerificationEnabled = true,
            CallbackAcceptanceEnabled = true,
            CallbackHost = "callback.test",
            VerifyToken = "verify-token",
            MaxBodyBytes = 32,
        };
        var conversation = new Wc120ConversationOptions { Enabled = true };
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(journey),
            Options.Create(conversation)
        );
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString("wrong.test");
        controller.ControllerContext = new ControllerContext { HttpContext = context };
        Assert.IsType<ForbidResult>(controller.Verify());
        Assert.IsType<ForbidResult>(await controller.ReceiveAsync(CancellationToken.None));

        context.Request.Host = new HostString("callback.test");
        Assert.IsType<UnauthorizedResult>(controller.Verify());
        context.Request.QueryString = new QueryString(
            "?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=challenge"
        );
        Assert.IsType<ContentResult>(controller.Verify());

        Assert.IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None));
        context.Request.ContentType = "application/json";
        context.Request.Headers["Content-Encoding"] = "gzip";
        Assert.IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None));
        context.Request.Headers.Remove("Content-Encoding");
        context.Request.ContentLength = 33;
        Assert.IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None));
        context.Request.ContentLength = null;
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(new string('x', 33)));
        Assert.IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None));

        const string disabledBody = "{}";
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(disabledBody));
        context.Request.Headers["X-Hub-Signature-256"] = Sign(disabledBody);
        conversation.Enabled = false;
        Assert.IsType<ContentResult>(controller.Verify());
        Assert.IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None));
        journey.VerificationEnabled = false;
        Assert.Equal(
            StatusCodes.Status503ServiceUnavailable,
            Assert.IsType<StatusCodeResult>(controller.Verify()).StatusCode
        );
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.SetProviderClaimHoldAsync("WHATSAPP", "missing", true, CancellationToken.None)
        );
        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            service.PurgeExpiredProviderClaimsAsync(DateTimeOffset.UtcNow, CancellationToken.None)
        );
    }

    [Fact]
    public async Task VerificationCanRegisterCallbackWithoutEnablingConversationOrProviderEffects()
    {
        var (service, factory, _) = Create();
        var journey = new WhatsAppJourneyOptions
        {
            VerificationEnabled = true,
            CallbackHost = "callback.test",
            VerifyToken = "verify-token",
        };
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(journey),
            Options.Create(new Wc120ConversationOptions())
        );
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString("callback.test");
        context.Request.QueryString = new QueryString(
            "?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=challenge"
        );
        controller.ControllerContext = new ControllerContext { HttpContext = context };

        var response = Assert.IsType<ContentResult>(controller.Verify());
        Assert.Equal("challenge", response.Content);
        Assert.Equal("text/plain; charset=utf-8", response.ContentType);
        const string body = "{}";
        context.Request.ContentType = "application/json";
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
        context.Request.Headers["X-Hub-Signature-256"] = Sign(body);
        Assert.Equal(
            StatusCodes.Status503ServiceUnavailable,
            Assert
                .IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None))
                .StatusCode
        );
        Assert.False(journey.CallbackAcceptanceEnabled);
        Assert.False(journey.DispatchEnabled);
        await using var db = factory.CreateDbContext();
        Assert.Empty(db.WhatsAppJourneyContacts);
    }

    [Theory]
    [InlineData("?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=")]
    [InlineData(
        "?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=one&hub.challenge=two"
    )]
    [InlineData("?hub.mode=subscribe&hub.verify_token=wrong-token&hub.challenge=one")]
    [InlineData("?hub.mode=unsubscribe&hub.verify_token=verify-token&hub.challenge=one")]
    public void VerificationRejectsMissingDuplicateAndInvalidParameters(string query)
    {
        var (service, _, _) = Create();
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(
                new WhatsAppJourneyOptions
                {
                    VerificationEnabled = true,
                    CallbackHost = "callback.test",
                    VerifyToken = "verify-token",
                }
            ),
            Options.Create(new Wc120ConversationOptions())
        );
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString("callback.test");
        context.Request.QueryString = new QueryString(query);
        controller.ControllerContext = new ControllerContext { HttpContext = context };

        Assert.IsType<UnauthorizedResult>(controller.Verify());
    }

    [Theory]
    [InlineData("application/json-extra")]
    [InlineData("application/json; charset=\"")]
    [InlineData("text/json")]
    public async Task CallbackRejectsInvalidJsonMediaTypesBeforeReadingBody(string contentType)
    {
        var (service, _, _) = Create();
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(
                new WhatsAppJourneyOptions
                {
                    CallbackAcceptanceEnabled = true,
                    CallbackHost = "callback.test",
                }
            ),
            Options.Create(new Wc120ConversationOptions { Enabled = true })
        );
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString("callback.test");
        context.Request.ContentType = contentType;
        controller.ControllerContext = new ControllerContext { HttpContext = context };

        Assert.Equal(
            StatusCodes.Status415UnsupportedMediaType,
            Assert
                .IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None))
                .StatusCode
        );
    }

    [Theory]
    [InlineData(1024, true)]
    [InlineData(1025, false)]
    public void VerificationEnforcesExactParameterByteLimit(int length, bool accepted)
    {
        var (service, _, _) = Create();
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(
                new WhatsAppJourneyOptions
                {
                    VerificationEnabled = true,
                    CallbackHost = "callback.test",
                    VerifyToken = "verify-token",
                }
            ),
            Options.Create(new Wc120ConversationOptions())
        );
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString("callback.test");
        context.Request.QueryString = new QueryString(
            "?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge="
                + new string('x', length)
        );
        controller.ControllerContext = new ControllerContext { HttpContext = context };

        var result = controller.Verify();
        if (accepted)
            Assert.IsType<ContentResult>(result);
        else
            Assert.IsType<UnauthorizedResult>(result);
    }

    [Theory]
    [InlineData(512, true)]
    [InlineData(513, false)]
    public void VerificationLimitsDecodedUtf8BytesNotCharacters(int length, bool accepted)
    {
        var (service, _, _) = Create();
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(
                new WhatsAppJourneyOptions
                {
                    VerificationEnabled = true,
                    CallbackHost = "callback.test",
                    VerifyToken = "verify-token",
                }
            ),
            Options.Create(new Wc120ConversationOptions())
        );
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString("callback.test");
        context.Request.QueryString = new QueryString(
            "?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge="
                + Uri.EscapeDataString(new string('\u00e9', length))
        );
        controller.ControllerContext = new ControllerContext { HttpContext = context };

        var result = controller.Verify();
        if (accepted)
            Assert.IsType<ContentResult>(result);
        else
            Assert.IsType<UnauthorizedResult>(result);
    }

    [Theory]
    [InlineData(8192, true)]
    [InlineData(8193, false)]
    public void VerificationEnforcesCompleteRawTargetLimit(int length, bool accepted)
    {
        var (service, _, _) = Create();
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(
                new WhatsAppJourneyOptions
                {
                    VerificationEnabled = true,
                    CallbackHost = "callback.test",
                    VerifyToken = "verify-token",
                }
            ),
            Options.Create(new Wc120ConversationOptions())
        );
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString("callback.test");
        context.Request.QueryString = new QueryString(
            "?hub.mode=subscribe&hub.verify_token=verify-token&hub.challenge=challenge"
        );
        context.Features.Get<Microsoft.AspNetCore.Http.Features.IHttpRequestFeature>()!.RawTarget =
            new string('/', length - context.Request.QueryString.Value!.Length)
            + context.Request.QueryString.Value;
        controller.ControllerContext = new ControllerContext { HttpContext = context };

        var result = controller.Verify();
        if (accepted)
            Assert.IsType<ContentResult>(result);
        else
            Assert.IsType<UnauthorizedResult>(result);
    }

    [Theory]
    [InlineData("STOP", "STOP")]
    [InlineData("Show evidence", "EVIDENCE")]
    [InlineData("Timeline status", "CONTINUITY")]
    [InlineData("Trial", "TRIAL")]
    [InlineData("Configure budget", "CONFIGURE")]
    [InlineData("Name and location", "CONTEXT")]
    [InlineData("Interview?", "INTERVIEW")]
    [InlineData("Show skill limits", "DISCLOSURE")]
    public async Task InformationalPromptsMapToExplicitJourneyStages(
        string text,
        string expectedStage
    )
    {
        var (service, _, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body(
            $"wamid-stage-{expectedStage}",
            now,
            "+919876543210",
            text,
            "TIER_1_LOW_RISK"
        );

        var receipt = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);

        Assert.Equal(expectedStage, receipt.JourneyStage);
    }

    [Fact]
    public async Task SignatureJsonAndTimestampParsingFailClosed()
    {
        var (service, _, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body(
            "wamid-invalid-boundary",
            now,
            "+919876543210",
            "status",
            "TIER_1_LOW_RISK"
        );
        Assert.Equal(
            403,
            (
                await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                    service.ReceiveAsync(body, "invalid", now, CancellationToken.None)
                )
            ).StatusCode
        );
        Assert.Equal(
            403,
            (
                await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                    service.ReceiveAsync(body, "sha256=zz", now, CancellationToken.None)
                )
            ).StatusCode
        );
        const string invalidJson = "{";
        Assert.Equal(
            400,
            (
                await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
                    service.ReceiveAsync(
                        invalidJson,
                        Sign(invalidJson),
                        now,
                        CancellationToken.None
                    )
                )
            ).StatusCode
        );
    }

    [Fact]
    public async Task SignedPhoneIdentityProofIsAcceptedAndReplayedWithoutRawPhone()
    {
        var (service, factory, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var proof = Proof("wamid-proof-valid", now);
        var rawBody = JsonSerializer.Serialize(
            proof,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var controller = ProofController(service, rawBody, SignProof(rawBody));

        var first = Assert.IsType<OkObjectResult>(
            await controller.ReceiveAsync(CancellationToken.None)
        );
        controller = ProofController(service, rawBody, SignProof(rawBody));
        var replay = Assert.IsType<OkObjectResult>(
            await controller.ReceiveAsync(CancellationToken.None)
        );

        Assert.DoesNotContain(
            "+919876543210",
            JsonSerializer.Serialize(first.Value),
            StringComparison.Ordinal
        );
        Assert.True(
            JsonSerializer.SerializeToElement(replay.Value).GetProperty("replayed").GetBoolean()
        );
        await using var db = factory.CreateDbContext();
        Assert.Single(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Single(await db.WhatsAppMessageReceipts.ToListAsync());
    }

    [Theory]
    [InlineData("wrong-audience", "AAL1_CHANNEL")]
    [InlineData(ProofAudience, "AAL2_ACCOUNT")]
    public async Task WrongAudienceOrAssuranceRejectsProofBeforeMutation(
        string audience,
        string assurance
    )
    {
        var (service, factory, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var proof = Proof("wamid-proof-denied", now) with
        {
            Audience = audience,
            AuthenticationAssurance = assurance,
        };
        var rawBody = JsonSerializer.Serialize(
            proof,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var controller = ProofController(service, rawBody, SignProof(rawBody));

        var response = Assert.IsType<ObjectResult>(
            await controller.ReceiveAsync(CancellationToken.None)
        );

        Assert.Equal(403, response.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Empty(await db.WhatsAppMessageReceipts.ToListAsync());
    }

    [Fact]
    public async Task ExpiredPhoneIdentityProofRejectsBeforeMutation()
    {
        var (service, factory, _) = Create();
        var verifiedAt = DateTimeOffset.UtcNow.AddMinutes(-6);
        var proof = Proof("wamid-proof-expired", verifiedAt);
        var rawBody = JsonSerializer.Serialize(
            proof,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var controller = ProofController(service, rawBody, SignProof(rawBody));

        var response = Assert.IsType<ObjectResult>(
            await controller.ReceiveAsync(CancellationToken.None)
        );

        Assert.Equal(400, response.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Empty(await db.WhatsAppMessageReceipts.ToListAsync());
    }

    [Fact]
    public async Task TamperedPhoneIdentityProofRejectsBeforeMutation()
    {
        var (service, factory, _) = Create();
        var proof = Proof("wamid-proof-tampered", DateTimeOffset.UtcNow);
        var rawBody = JsonSerializer.Serialize(
            proof,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var controller = ProofController(service, rawBody, "sha256=00");

        var response = Assert.IsType<ObjectResult>(
            await controller.ReceiveAsync(CancellationToken.None)
        );

        Assert.Equal(403, response.StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Empty(await db.WhatsAppMessageReceipts.ToListAsync());
    }

    [Fact]
    public async Task CctAe01Auth01_MpinLocksOnThirdFailureAndRecoversAfterLockWindow()
    {
        var (service, factory, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var phone = "+919876543210";
        var body = Body("wamid-mpin", now, phone, "Show skills", "TIER_1_LOW_RISK");
        await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);
        await using var db = factory.CreateDbContext();
        var tenantId = (await db.WhatsAppJourneyContacts.SingleAsync()).TenantId;
        var proof = new PortalPhoneAttachProof(
            Guid.NewGuid(),
            "TIER_4_PORTAL_FRESH",
            DateTimeOffset.UtcNow,
            Guid.NewGuid()
        );
        await service.EnrolMpinAsync(tenantId, phone, "2468", proof, CancellationToken.None);

        Assert.False(
            await service.VerifyMpinAsync(tenantId, phone, "1111", now, CancellationToken.None)
        );
        Assert.False(
            await service.VerifyMpinAsync(tenantId, phone, "2222", now, CancellationToken.None)
        );
        Assert.False(
            await service.VerifyMpinAsync(tenantId, phone, "3333", now, CancellationToken.None)
        );
        var locked = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.VerifyMpinAsync(
                tenantId,
                phone,
                "2468",
                now.AddMinutes(1),
                CancellationToken.None
            )
        );
        Assert.Equal(423, locked.StatusCode);
        Assert.True(
            await service.VerifyMpinAsync(
                tenantId,
                phone,
                "2468",
                now.AddMinutes(31),
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData(-301, false)]
    [InlineData(-300, true)]
    [InlineData(30, true)]
    [InlineData(31, false)]
    public async Task LinkedPhoneProofUsesPortalFreshnessBoundaries(int secondsFromNow, bool valid)
    {
        var clock = new MutableClock { Now = DateTimeOffset.UtcNow };
        var (service, _, _) = Create(clock: clock);
        var attach = () =>
            service.AttachLinkedPhoneAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                new string('c', 64),
                true,
                new PortalPhoneAttachProof(
                    Guid.NewGuid(),
                    "TIER_4_PORTAL_FRESH",
                    clock.Now.AddSeconds(secondsFromNow),
                    Guid.NewGuid()
                ),
                CancellationToken.None
            );
        if (valid)
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(attach);
        else
            await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(attach);
    }

    [Fact]
    public async Task CctAe01Takeover01_UnknownPhoneCannotAttachFromPortalPayloadHints()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var (service, _, _) = Create(relationshipGateway: relationshipGateway);

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            service.AttachPhoneAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                "+919876543210",
                "conversation",
                new PortalPhoneAttachProof(
                    Guid.NewGuid(),
                    "TIER_4_PORTAL_FRESH",
                    DateTimeOffset.UtcNow,
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(0, relationshipGateway.CallCount);
    }

    [Fact]
    public async Task CctAe01Auth02_FreshTier4ProofAttachesKnownPhoneAfterEvidence()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var (service, factory, _) = Create(relationshipGateway: relationshipGateway);
        var now = DateTimeOffset.UtcNow;
        var phone = "+919876543210";
        var body = Body("wamid-attach", now, phone, "Show skills", "TIER_1_LOW_RISK");
        await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);
        await using var db = factory.CreateDbContext();
        var tenantId = (await db.WhatsAppJourneyContacts.SingleAsync()).TenantId;
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        db.EmploymentRelationships.Add(
            new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ProfessionalType = "DMA",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.TrialActive,
            }
        );
        db.RelationshipParticipants.Add(
            new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Evaluator,
                BoundEvidenceId = Guid.NewGuid(),
            }
        );
        await db.SaveChangesAsync();

        var resolution = await service.AttachPhoneAsync(
            tenantId,
            relationshipId,
            phone,
            "conversation",
            new PortalPhoneAttachProof(
                participantId,
                "TIER_4_PORTAL_FRESH",
                DateTimeOffset.UtcNow,
                Guid.NewGuid()
            ),
            CancellationToken.None
        );

        Assert.Equal("TIER_4_PORTAL_FRESH", resolution.AuthenticationAssurance);
        Assert.Equal(1, relationshipGateway.CallCount);
        var binding = await db.ChannelBindings.SingleAsync();
        Assert.Equal("ACTIVE", binding.Status);
        Assert.DoesNotContain(phone, binding.ExternalSubjectHash, StringComparison.Ordinal);
    }

    [Fact]
    public async Task ConfirmedIdentityAndExplicitConsentCreateCanonicalRelationshipBinding()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var (service, factory, _) = Create(
            relationshipGateway: relationshipGateway,
            enableConversationService: true
        );
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var phoneSubjectHash = new string('c', 64);
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await db.SaveChangesAsync();
        }

        var resolution = await service.AttachLinkedPhoneAsync(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            phoneSubjectHash,
            true,
            new PortalPhoneAttachProof(
                participantId,
                "TIER_4_PORTAL_FRESH",
                DateTimeOffset.UtcNow,
                Guid.NewGuid()
            ),
            CancellationToken.None
        );
        var replay = await service.AttachLinkedPhoneAsync(
            tenantId,
            relationshipId,
            Guid.NewGuid(),
            phoneSubjectHash,
            true,
            new PortalPhoneAttachProof(
                participantId,
                "TIER_4_PORTAL_FRESH",
                DateTimeOffset.UtcNow,
                Guid.NewGuid()
            ),
            CancellationToken.None
        );

        Assert.Equal(relationshipId, resolution.RelationshipId);
        Assert.Equal(resolution.BindingId, replay.BindingId);
        Assert.Equal(1, relationshipGateway.CallCount);
        await using var saved = factory.CreateDbContext();
        var contact = await saved.WhatsAppJourneyContacts.SingleAsync();
        Assert.Equal(tenantId, contact.TenantId);
        Assert.Equal(phoneSubjectHash, contact.PhoneHmac);
        Assert.Null(contact.OptedOutAt);
        var binding = await saved.ChannelBindings.SingleAsync();
        Assert.Equal(phoneSubjectHash, binding.ExternalSubjectHash);
        Assert.Equal("ACTIVE", binding.Status);
        Assert.True(Guid.TryParse(binding.ConversationId, out _));
    }

    [Theory]
    [InlineData("conversation")]
    [InlineData("activation")]
    [InlineData("revoked")]
    [InlineData("proof-expired")]
    public async Task LinkedPhoneReplayRechecksAuthorityAfterGuestLockWait(string change)
    {
        var interceptReplay = false;
        var contextCalls = 0;
        var capability = new ActiveWhatsAppCapabilityGate(Guid.NewGuid());
        var clock = new MutableClock { Now = DateTimeOffset.UtcNow };
        var authenticatedAt = clock.Now;
        InMemoryEmploymentRelationshipFactory? relationshipFactory = null;
        var (service, factory, _) = Create(
            relationshipGateway: new RecordingRelationshipConstitutionalGateway(),
            enableConversationService: true,
            capabilityGate: capability,
            clock: clock,
            beforeConversationContext: async () =>
            {
                if (!interceptReplay || ++contextCalls != 3)
                    return;
                if (change == "activation")
                {
                    capability.Changed = true;
                    return;
                }
                if (change == "revoked")
                {
                    capability.Revoked = true;
                    return;
                }
                if (change == "proof-expired")
                {
                    clock.Now = authenticatedAt.AddMinutes(6);
                    return;
                }
                await using var mutation = relationshipFactory!.CreateDbContext();
                (await mutation.ChannelBindings.SingleAsync()).ConversationId = Guid.NewGuid()
                    .ToString("D");
                await mutation.SaveChangesAsync();
            }
        );
        relationshipFactory = factory;
        var tenant = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var digest = new string('c', 64);
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenant,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await db.SaveChangesAsync();
        }
        var proof = new PortalPhoneAttachProof(
            participantId,
            "TIER_4_PORTAL_FRESH",
            authenticatedAt,
            Guid.NewGuid()
        );
        var linkId = Guid.NewGuid();
        await service.AttachLinkedPhoneAsync(
            tenant,
            relationshipId,
            linkId,
            digest,
            true,
            proof,
            CancellationToken.None
        );
        interceptReplay = true;
        var replay = () =>
            service.AttachLinkedPhoneAsync(
                tenant,
                relationshipId,
                linkId,
                digest,
                true,
                proof,
                CancellationToken.None
            );
        if (change is "conversation" or "proof-expired")
            await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(replay);
        else
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(replay);
        Assert.Equal(3, contextCalls);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LinkedPhoneRejectsAmbiguousSameTenantBindings(bool sameRelationship)
    {
        var gateway = new RecordingRelationshipConstitutionalGateway();
        var (service, factory, _) = Create(
            relationshipGateway: gateway,
            enableConversationService: true
        );
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var digest = new string('c', 64);
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            var count = sameRelationship ? 2 : 1;
            for (var index = 0; index < count; index++)
                db.ChannelBindings.Add(
                    new ChannelBinding
                    {
                        TenantId = tenantId,
                        RelationshipId = sameRelationship ? relationshipId : Guid.NewGuid(),
                        ParticipantId = Guid.NewGuid(),
                        ParticipantRole = "EVALUATOR",
                        Channel = "WHATSAPP",
                        ExternalSubjectHash = sameRelationship ? new string('d', 64) : digest,
                        ConversationId = Guid.NewGuid().ToString("D"),
                        AssuranceLevel = "TIER_4_PORTAL_FRESH",
                        Status = "ACTIVE",
                    }
                );
            await db.SaveChangesAsync();
        }

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            service.AttachLinkedPhoneAsync(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                digest,
                true,
                new PortalPhoneAttachProof(
                    participantId,
                    "TIER_4_PORTAL_FRESH",
                    DateTimeOffset.UtcNow,
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );
        Assert.Equal(0, gateway.CallCount);
        await using var saved = factory.CreateDbContext();
        Assert.Equal(sameRelationship ? 2 : 1, await saved.ChannelBindings.CountAsync());
        Assert.Empty(await saved.WhatsAppJourneyContacts.ToListAsync());
    }

    [Theory]
    [InlineData("relationship")]
    [InlineData("participant")]
    [InlineData("withdrawal")]
    [InlineData("activation")]
    [InlineData("competing-binding")]
    [InlineData("sender-reassigned")]
    [InlineData("proof-expired")]
    public async Task LinkedPhoneRechecksAuthorityAfterEvidence(string change)
    {
        var gateway = new ChangingRelationshipGateway();
        var capability = new ActiveWhatsAppCapabilityGate(Guid.NewGuid());
        var clock = new MutableClock { Now = DateTimeOffset.UtcNow };
        var authenticatedAt = clock.Now;
        var (service, factory, _) = Create(
            relationshipGateway: gateway,
            enableConversationService: true,
            capabilityGate: capability,
            clock: clock
        );
        var tenant = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var digest = new string('c', 64);
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenant,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenant,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            db.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = tenant,
                    PhoneHmac = digest,
                    OptedInAt = DateTimeOffset.UtcNow,
                    LastInboundAt = DateTimeOffset.UtcNow,
                }
            );
            await db.SaveChangesAsync();
        }
        gateway.BeforeReturn = async () =>
        {
            if (change == "activation")
            {
                capability.Changed = true;
                return;
            }
            if (change == "proof-expired")
            {
                clock.Now = authenticatedAt.AddMinutes(6);
                return;
            }
            await using var db = factory.CreateDbContext();
            if (change == "relationship")
                (await db.EmploymentRelationships.SingleAsync()).State =
                    EmploymentRelationshipState.StoppedEmergency;
            else if (change == "participant")
                (await db.RelationshipParticipants.SingleAsync()).Status = "REVOKED";
            else if (change == "sender-reassigned")
            {
                var otherRelationship = Guid.NewGuid();
                db.EmploymentRelationships.Add(
                    new EmploymentRelationship
                    {
                        TenantId = tenant,
                        RelationshipId = otherRelationship,
                        ProfessionalType = "DMA",
                        State = EmploymentRelationshipState.Active,
                    }
                );
                db.ChannelBindings.Add(
                    new ChannelBinding
                    {
                        TenantId = tenant,
                        RelationshipId = otherRelationship,
                        ParticipantId = Guid.NewGuid(),
                        ParticipantRole = "EVALUATOR",
                        Channel = "WHATSAPP",
                        ExternalSubjectHash = digest,
                        ConversationId = Guid.NewGuid().ToString("D"),
                        AssuranceLevel = "TIER_4_PORTAL_FRESH",
                        Status = "ACTIVE",
                    }
                );
            }
            else if (change == "competing-binding")
                db.ChannelBindings.Add(
                    new ChannelBinding
                    {
                        TenantId = tenant,
                        RelationshipId = relationshipId,
                        ParticipantId = Guid.NewGuid(),
                        ParticipantRole = "EVALUATOR",
                        Channel = "WHATSAPP",
                        ExternalSubjectHash = new string('d', 64),
                        ConversationId = Guid.NewGuid().ToString("D"),
                        AssuranceLevel = "TIER_4_PORTAL_FRESH",
                        Status = "ACTIVE",
                    }
                );
            else
                (await db.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt = DateTimeOffset.UtcNow;
            await db.SaveChangesAsync();
        };
        var attachment = () =>
            service.AttachLinkedPhoneAsync(
                tenant,
                relationshipId,
                Guid.NewGuid(),
                digest,
                true,
                new PortalPhoneAttachProof(
                    participantId,
                    "TIER_4_PORTAL_FRESH",
                    authenticatedAt,
                    Guid.NewGuid()
                ),
                CancellationToken.None
            );
        if (change == "activation")
            await Assert.ThrowsAsync<WhatsAppChannelBindingUnavailableException>(attachment);
        else
            await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(attachment);
        await using var verify = factory.CreateDbContext();
        Assert.Equal(
            change is "competing-binding" or "sender-reassigned" ? 1 : 0,
            await verify.ChannelBindings.CountAsync()
        );
    }

    private sealed class ChangingRelationshipGateway : IRelationshipConstitutionalGateway
    {
        public Func<Task>? BeforeReturn { get; set; }

        public async Task<Guid> AuthorizeAndRecordAsync(
            Guid tenantId,
            Guid relationshipId,
            string professionalType,
            string actionType,
            Guid correlationId,
            object actionParameters,
            CancellationToken cancellationToken
        )
        {
            if (BeforeReturn is not null)
                await BeforeReturn();
            return Guid.NewGuid();
        }
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LinkedPhoneRechecksIdentityLinkAfterEvidenceAndBeforeBindingReplay(
        bool replay
    )
    {
        var identityFactory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var identity = IdentityTestHelpers.CreateService(identityFactory);
        var actor = new VerifiedCustomerActor(
            "https://identity.test",
            Guid.NewGuid().ToString("D")
        );
        var membership = new CustomerWorkspaceMembership(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            ["OWNER"]
        );
        var registration = new IdentityRegistrationRecord
        {
            ActorIssuer = actor.Issuer,
            ActorSubject = actor.Subject,
            State = IdentityRegistrationState.Completed,
            AccountId = membership.AccountId,
            MobileVerified = true,
            MobileHmacDomain = "mobile",
            MobileHmacVersion = "v1",
            MobileHmacKey = new string('b', 64),
        };
        var mobileProof = new IdentityVerificationChallengeRecord
        {
            RegistrationId = registration.RegistrationId,
            ActorSubject = actor.Subject,
            Purpose = IdentityVerificationPurpose.Mobile,
            State = IdentityVerificationState.Consumed,
            VerifiedAt = DateTimeOffset.UtcNow.AddMinutes(-1),
            DeliveryState = "SUBMITTED",
            DestinationHmacDomain = "mobile",
            DestinationHmacVersion = "v1",
            DestinationHmacKey = registration.MobileHmacKey,
        };
        var digest = new string('c', 64);
        var link = new IdentityAccountLinkRecord
        {
            ActorSubject = actor.Subject,
            TenantId = membership.TenantId,
            State = IdentityAccountLinkState.Linked,
            VerifiedMobileProofId = mobileProof.ChallengeId,
            ConfirmedAt = DateTimeOffset.UtcNow.AddSeconds(-1),
            ConfirmationEvidenceId = Guid.NewGuid(),
            ConfirmedPhoneSubjectHash = digest,
        };
        await using (var seed = identityFactory.CreateDbContext())
        {
            seed.Add(registration);
            seed.Add(mobileProof);
            seed.Add(link);
            await seed.SaveChangesAsync();
        }
        async Task RevokeLink()
        {
            await using var mutation = identityFactory.CreateDbContext();
            (await mutation.AccountLinks.FindAsync(link.LinkId))!.State =
                IdentityAccountLinkState.Cancelled;
            await mutation.SaveChangesAsync();
        }
        var gateway = new ChangingRelationshipGateway();
        var (service, factory, _) = Create(
            relationshipGateway: gateway,
            enableConversationService: true,
            identity: identity
        );
        var participantId = Guid.Parse(actor.Subject);
        var relationshipId = Guid.NewGuid();
        await using (var seed = factory.CreateDbContext())
        {
            seed.EmploymentRelationships.Add(
                new()
                {
                    TenantId = membership.TenantId,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            seed.RelationshipParticipants.Add(
                new()
                {
                    TenantId = membership.TenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Employer,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await seed.SaveChangesAsync();
        }
        var proof = new PortalPhoneAttachProof(
            participantId,
            "TIER_4_PORTAL_FRESH",
            DateTimeOffset.UtcNow,
            Guid.NewGuid(),
            actor,
            membership
        );
        if (replay)
        {
            await service.AttachLinkedPhoneAsync(
                membership.TenantId,
                relationshipId,
                link.LinkId,
                digest,
                true,
                proof,
                CancellationToken.None
            );
            await RevokeLink();
        }
        else
            gateway.BeforeReturn = RevokeLink;
        await Assert.ThrowsAsync<IdentityResourceNotFoundException>(() =>
            service.AttachLinkedPhoneAsync(
                membership.TenantId,
                relationshipId,
                link.LinkId,
                digest,
                true,
                proof,
                CancellationToken.None
            )
        );
        await using var saved = factory.CreateDbContext();
        Assert.Equal(replay ? 1 : 0, await saved.ChannelBindings.CountAsync());
        Assert.Equal(replay ? 1 : 0, await saved.WhatsAppJourneyContacts.CountAsync());
        Assert.Equal(replay ? 1 : 0, await saved.Set<WhatsAppRelationshipRoute>().CountAsync());
    }

    private sealed class MutableClock : TimeProvider
    {
        public DateTimeOffset Now { get; set; }

        public override DateTimeOffset GetUtcNow() => Now;
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task LinkedPhoneRejectsCrossTenantOrWithdrawnSender(bool withdrawn)
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var (service, factory, _) = Create(
            relationshipGateway: relationshipGateway,
            enableConversationService: true
        );
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var phoneSubjectHash = new string('d', 64);
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            db.WhatsAppJourneyContacts.Add(
                new WhatsAppJourneyContact
                {
                    TenantId = withdrawn ? tenantId : Guid.NewGuid(),
                    PhoneHmac = phoneSubjectHash,
                    OptedInAt = DateTimeOffset.UtcNow,
                    OptedOutAt = withdrawn ? DateTimeOffset.UtcNow : null,
                }
            );
            await db.SaveChangesAsync();
        }

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            service.AttachLinkedPhoneAsync(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                phoneSubjectHash,
                true,
                new PortalPhoneAttachProof(
                    participantId,
                    "TIER_4_PORTAL_FRESH",
                    DateTimeOffset.UtcNow,
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(0, relationshipGateway.CallCount);
        await using var saved = factory.CreateDbContext();
        Assert.Empty(await saved.ChannelBindings.ToListAsync());
    }

    [Fact]
    public async Task StoppedGuestSessionCannotBeReenabledByRelationshipAttachment()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var phoneSubjectHash = new string('e', 64);
        var (service, factory, _) = Create(
            relationshipGateway: relationshipGateway,
            enableConversationService: true,
            stoppedGuestDigest: phoneSubjectHash
        );
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                    State = EmploymentRelationshipState.TrialActive,
                }
            );
            db.RelationshipParticipants.Add(
                new RelationshipParticipant
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ParticipantId = participantId,
                    Role = RelationshipParticipantRole.Evaluator,
                    BoundEvidenceId = Guid.NewGuid(),
                }
            );
            await db.SaveChangesAsync();
        }

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            service.AttachLinkedPhoneAsync(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                phoneSubjectHash,
                true,
                new PortalPhoneAttachProof(
                    participantId,
                    "TIER_4_PORTAL_FRESH",
                    DateTimeOffset.UtcNow,
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(0, relationshipGateway.CallCount);
        await using var saved = factory.CreateDbContext();
        Assert.Empty(await saved.WhatsAppJourneyContacts.ToListAsync());
        Assert.Empty(await saved.ChannelBindings.ToListAsync());
    }

    [Fact]
    public async Task LinkedPhoneCannotAttachToRelationshipOutsideEligibleLifecycleStates()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var (service, factory, _) = Create(
            relationshipGateway: relationshipGateway,
            enableConversationService: true
        );
        var tenantId = Guid.NewGuid();
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        await using (var db = factory.CreateDbContext())
        {
            db.EmploymentRelationships.Add(
                new EmploymentRelationship
                {
                    TenantId = tenantId,
                    RelationshipId = relationshipId,
                    ProfessionalType = "DMA",
                    EvaluationIntentId = Guid.NewGuid(),
                    InitiatingParticipantId = participantId,
                    State = EmploymentRelationshipState.Discovered,
                }
            );
            await db.SaveChangesAsync();
        }

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            service.AttachLinkedPhoneAsync(
                tenantId,
                relationshipId,
                Guid.NewGuid(),
                new string('f', 64),
                true,
                new PortalPhoneAttachProof(
                    participantId,
                    "TIER_4_PORTAL_FRESH",
                    DateTimeOffset.UtcNow,
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(0, relationshipGateway.CallCount);
        await using var saved = factory.CreateDbContext();
        Assert.Empty(await saved.ChannelBindings.ToListAsync());
    }

    [Fact]
    public async Task LinkedPhoneCannotAttachWithoutExplicitRelationshipChannelConsent()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var (service, factory, _) = Create(relationshipGateway: relationshipGateway);

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() =>
            service.AttachLinkedPhoneAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Guid.NewGuid(),
                new string('c', 64),
                false,
                new PortalPhoneAttachProof(
                    Guid.NewGuid(),
                    "TIER_4_PORTAL_FRESH",
                    DateTimeOffset.UtcNow,
                    Guid.NewGuid()
                ),
                CancellationToken.None
            )
        );

        Assert.Equal(0, relationshipGateway.CallCount);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Empty(await db.ChannelBindings.ToListAsync());
    }

    [Fact]
    public async Task RecipientStopOptsOutChannelWithoutStoppingRelationship()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var stopGateway = new RecordingEmergencyStopGateway();
        var (service, factory, _) = Create(
            relationshipGateway: relationshipGateway,
            stopGateway: stopGateway
        );
        var now = DateTimeOffset.UtcNow;
        var phone = "+919876543210";
        var first = Body("wamid-stop-register", now, phone, "Show skills", "TIER_1_LOW_RISK");
        await service.ReceiveAsync(first, Sign(first), now, CancellationToken.None);
        await using var db = factory.CreateDbContext();
        var tenantId = (await db.WhatsAppJourneyContacts.SingleAsync()).TenantId;
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        db.EmploymentRelationships.Add(
            new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ProfessionalType = "DMA",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.TrialActive,
            }
        );
        db.RelationshipParticipants.Add(
            new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Evaluator,
                BoundEvidenceId = Guid.NewGuid(),
            }
        );
        await db.SaveChangesAsync();
        await service.AttachPhoneAsync(
            tenantId,
            relationshipId,
            phone,
            "conversation",
            new PortalPhoneAttachProof(
                participantId,
                "TIER_4_PORTAL_FRESH",
                DateTimeOffset.UtcNow,
                Guid.NewGuid()
            ),
            CancellationToken.None
        );

        var incidentalStopBody = Body(
            "wamid-stop-in-question",
            now.AddSeconds(1),
            phone,
            "Please stop the trial.",
            "TIER_1_LOW_RISK"
        );
        var incidentalStop = await service.ReceiveAsync(
            incidentalStopBody,
            Sign(incidentalStopBody),
            now.AddSeconds(1),
            CancellationToken.None
        );
        Assert.Equal("ACCEPTED", incidentalStop.Status);
        Assert.Equal("TRIAL", incidentalStop.JourneyStage);
        await using var incidentalStopDb = factory.CreateDbContext();
        Assert.Null((await incidentalStopDb.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt);
        Assert.Equal(
            EmploymentRelationshipState.TrialActive,
            (await incidentalStopDb.EmploymentRelationships.FindAsync(relationshipId))!.State
        );

        var stopBody = Body("wamid-stop", now.AddSeconds(2), phone, "STOP", "TIER_1_LOW_RISK");
        var stopped = await service.ReceiveAsync(
            stopBody,
            Sign(stopBody),
            now.AddSeconds(2),
            CancellationToken.None
        );
        Assert.Equal("STOPPED", stopped.Status);
        Assert.Equal("STOP", stopped.JourneyStage);
        Assert.Empty(stopped.Reply);
        Assert.Empty(stopped.InternalTenantToken);

        await using var optedOutDb = factory.CreateDbContext();
        Assert.NotNull((await optedOutDb.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt);
        Assert.Equal(
            EmploymentRelationshipState.TrialActive,
            (await optedOutDb.EmploymentRelationships.FindAsync(relationshipId))!.State
        );
        var optedOutAt = (await optedOutDb.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt;

        var repeatedStopBody = Body(
            "wamid-stop-repeat",
            now.AddSeconds(3),
            phone,
            " stop ",
            "TIER_1_LOW_RISK"
        );
        var repeatedStop = await service.ReceiveAsync(
            repeatedStopBody,
            Sign(repeatedStopBody),
            now.AddSeconds(3),
            CancellationToken.None
        );
        Assert.Equal("STOPPED", repeatedStop.Status);
        Assert.Empty(repeatedStop.Reply);
        await using var repeatedStopDb = factory.CreateDbContext();
        Assert.Equal(
            optedOutAt,
            (await repeatedStopDb.WhatsAppJourneyContacts.SingleAsync()).OptedOutAt
        );

        var emergencyStopBody = Body(
            "wamid-emergency-stop",
            now.AddSeconds(4),
            phone,
            "EMERGENCY STOP",
            "TIER_1_LOW_RISK"
        );
        stopGateway.Failure = new Grpc.Core.RpcException(
            new Grpc.Core.Status(Grpc.Core.StatusCode.Unavailable, "sensitive gateway detail")
        );
        var controller = new WhatsAppJourneyController(service);
        var context = new DefaultHttpContext();
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(emergencyStopBody));
        context.Request.Headers["X-Hub-Signature-256"] = Sign(emergencyStopBody);
        controller.ControllerContext = new ControllerContext { HttpContext = context };
        var unavailable = Assert.IsType<ObjectResult>(
            await controller.ReceiveAsync(CancellationToken.None)
        );
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, unavailable.StatusCode);
        var problem = Assert.IsType<ProblemDetails>(unavailable.Value);
        Assert.Equal("EMERGENCY_STOP_RECONCILIATION_PENDING", problem.Title);
        Assert.DoesNotContain("sensitive gateway detail", JsonSerializer.Serialize(problem));
        var proofTime = DateTimeOffset.UtcNow;
        var signedProof = Proof("wamid-emergency-stop-proof", proofTime) with
        {
            PhoneSubjectHash = Convert.ToHexStringLower(
                HMACSHA256.HashData(
                    Encoding.UTF8.GetBytes(WebhookSecret),
                    Encoding.UTF8.GetBytes(phone)
                )
            ),
            Text = "EMERGENCY STOP",
        };
        var signedBody = JsonSerializer.Serialize(
            signedProof,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        var proofController = ProofController(service, signedBody, SignProof(signedBody));
        var proofUnavailable = Assert.IsType<ObjectResult>(
            await proofController.ReceiveAsync(CancellationToken.None)
        );
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, proofUnavailable.StatusCode);
        var proofProblem = Assert.IsType<ProblemDetails>(proofUnavailable.Value);
        Assert.Equal("EMERGENCY_STOP_RECONCILIATION_PENDING", proofProblem.Title);
        Assert.DoesNotContain("sensitive gateway detail", JsonSerializer.Serialize(proofProblem));
        stopGateway.Failure = null;
        var emergencyStopped = await service.ReceiveAsync(
            emergencyStopBody,
            Sign(emergencyStopBody),
            now.AddSeconds(4),
            CancellationToken.None
        );
        Assert.Equal("ACCEPTED", emergencyStopped.Status);
        Assert.Equal("STOP", emergencyStopped.JourneyStage);
        Assert.Contains("Session halt confirmation may still be pending.", emergencyStopped.Reply);
        Assert.DoesNotContain("were halted", emergencyStopped.Reply);

        var laterBody = Body(
            "wamid-after-stop",
            now.AddSeconds(5),
            phone,
            "CONFIGURE budget",
            "TIER_2_MEDIUM_RISK"
        );
        var later = await service.ReceiveAsync(
            laterBody,
            Sign(laterBody),
            now.AddSeconds(5),
            CancellationToken.None
        );

        Assert.Equal("STOPPED", later.Status);
        Assert.Empty(later.Reply);
        await using var verificationDb = factory.CreateDbContext();
        Assert.Equal(
            EmploymentRelationshipState.StoppedEmergency,
            (await verificationDb.EmploymentRelationships.FindAsync(relationshipId))!.State
        );
    }

    [Fact]
    public async Task Wc121_StatusUsesSharedTruthAndEndSessionLeavesRelationshipActive()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var employment = new ConversationalEmploymentService();
        var (service, factory, _) = Create(
            relationshipGateway: relationshipGateway,
            enableEngagementWorkspace: true,
            outboundEmployment: employment
        );
        var now = DateTimeOffset.UtcNow;
        var phone = "+919876543211";
        var register = Body("wamid-cew-register", now, phone, "Show skills", "TIER_1_LOW_RISK");
        await service.ReceiveAsync(register, Sign(register), now, CancellationToken.None);
        await using var db = factory.CreateDbContext();
        var tenantId = (await db.WhatsAppJourneyContacts.SingleAsync()).TenantId;
        var relationshipId = Guid.NewGuid();
        var participantId = Guid.NewGuid();
        var evidenceId = Guid.NewGuid();
        db.EmploymentRelationships.Add(
            new EmploymentRelationship
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                AgentInstanceId = Guid.NewGuid(),
                ProfessionalType = "DMA",
                ProfessionalVersion = "1.0.0",
                EvaluationIntentId = Guid.NewGuid(),
                InitiatingParticipantId = participantId,
                State = EmploymentRelationshipState.Active,
                StateVersion = 3,
            }
        );
        db.RelationshipParticipants.Add(
            new RelationshipParticipant
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                ParticipantId = participantId,
                Role = RelationshipParticipantRole.Employer,
                BoundEvidenceId = evidenceId,
            }
        );
        db.RelationshipStateHistory.Add(
            new RelationshipStateHistory
            {
                TenantId = tenantId,
                RelationshipId = relationshipId,
                StateVersion = 3,
                ToState = EmploymentRelationshipState.Active,
                ActorParticipantId = participantId,
                ActorRole = RelationshipParticipantRole.Employer,
                CorrelationId = Guid.NewGuid(),
                EvidenceId = evidenceId,
            }
        );
        await db.SaveChangesAsync();
        employment.RegisterWorkspace(
            ConversationWhatsAppFitness.Wc120FitnessContext.Workspace(
                tenantId,
                relationshipId,
                "workspace-1"
            )
        );
        await service.AttachPhoneAsync(
            tenantId,
            relationshipId,
            phone,
            "conversation",
            new PortalPhoneAttachProof(participantId, "TIER_4_PORTAL_FRESH", now, Guid.NewGuid()),
            CancellationToken.None
        );

        var statusBody = Body(
            "wamid-cew-status",
            now.AddSeconds(1),
            phone,
            "STATUS",
            "TIER_1_LOW_RISK"
        );
        var progress = await service.ReceiveAsync(
            statusBody,
            Sign(statusBody),
            now.AddSeconds(1),
            CancellationToken.None
        );
        Assert.Contains("DMA · Track work and customer outcomes", progress.Reply);
        Assert.Contains("Delivery: UNKNOWN", progress.Reply);
        Assert.Contains("Processing: WORKING", progress.Reply);
        Assert.Contains("Evidence: COMPLETED", progress.Reply);
        Assert.Contains("Commercial: UNKNOWN", progress.Reply);
        Assert.Contains("Outcome: UNKNOWN", progress.Reply);
        Assert.Contains("Next action: Review current work", progress.Reply);

        var endBody = Body(
            "wamid-cew-end-session",
            now.AddSeconds(2),
            phone,
            "END SESSION",
            "TIER_1_LOW_RISK"
        );
        var ended = await service.ReceiveAsync(
            endBody,
            Sign(endBody),
            now.AddSeconds(2),
            CancellationToken.None
        );
        Assert.Equal("END_SESSION", ended.JourneyStage);
        Assert.Contains("employment relationship", ended.Reply, StringComparison.OrdinalIgnoreCase);
        await using var verificationDb = factory.CreateDbContext();
        Assert.Equal("ENDED", (await verificationDb.ChannelBindings.SingleAsync()).Status);
        Assert.Equal(
            EmploymentRelationshipState.Active,
            (await verificationDb.EmploymentRelationships.SingleAsync()).State
        );
        Assert.Equal("END_CONVERSATION_CHANNEL_SESSION", relationshipGateway.LastActionType);
    }

    private static (
        WhatsAppJourneyService Service,
        InMemoryEmploymentRelationshipFactory Factory,
        RecordingEvidenceGateway Evidence
    ) Create(
        bool evidenceFails = false,
        IRelationshipConstitutionalGateway? relationshipGateway = null,
        IRelationshipEmergencyStopGateway? stopGateway = null,
        bool enableEngagementWorkspace = false,
        bool enableConversationService = false,
        string? stoppedGuestDigest = null,
        Func<Task>? beforeConversationContext = null,
        IWhatsAppCapabilityGate? capabilityGate = null,
        TimeProvider? clock = null,
        IdentityService? identity = null,
        ConversationalEmploymentService? outboundEmployment = null
    )
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var evidence = new RecordingEvidenceGateway(evidenceFails);
        var options = Options.Create(
            new WhatsAppJourneyOptions { WebhookSecret = WebhookSecret, TenantTokenKey = TokenKey }
        );
        RelationshipEmergencyStopService? emergencyStops = null;
        if (stopGateway is not null)
        {
            var relationships = new EmploymentRelationshipService(
                factory,
                relationshipGateway ?? new RecordingRelationshipConstitutionalGateway(),
                NullLogger<EmploymentRelationshipService>.Instance
            );
            emergencyStops = new RelationshipEmergencyStopService(
                new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N")),
                relationships,
                stopGateway
            );
        }
        var engagementWorkspace = enableEngagementWorkspace
            ? new CustomerEngagementWorkspaceService(
                factory,
                new EphemeralDataProtectionProvider(),
                relationshipGateway ?? new RecordingRelationshipConstitutionalGateway()
            )
            : null;
        ConversationService? conversationService = null;
        IDbContextFactory<ConversationStoreDbContext>? conversationDbFactory = null;
        WhatsAppTenantExecutionScope? tenantExecutionScope = null;
        ConversationOutboundContributionService? outboundContributions = null;
        if (enableConversationService || stoppedGuestDigest is not null)
        {
            var guestTenantId =
                capabilityGate?.RequireActive(DateTimeOffset.UtcNow).TenantId ?? Guid.NewGuid();
            var storeFactory = new InMemoryConversationStoreFactory(Guid.NewGuid().ToString("N"));
            var contextFactory = beforeConversationContext is null
                ? (IDbContextFactory<ConversationStoreDbContext>)storeFactory
                : new InterceptedConversationFactory(storeFactory, beforeConversationContext);
            conversationDbFactory = contextFactory;
            var capability = capabilityGate ?? new ActiveWhatsAppCapabilityGate(guestTenantId);
            tenantExecutionScope = new WhatsAppTenantExecutionScope(
                capability,
                TimeProvider.System
            );
            if (stoppedGuestDigest is not null)
            {
                using var guestDb = storeFactory.CreateDbContext();
                guestDb.Add(
                    new WhatsAppGuestSession
                    {
                        TenantId = guestTenantId,
                        BindingDigest = stoppedGuestDigest,
                        FirstObservedAt = DateTimeOffset.UtcNow,
                        LastInboundAt = DateTimeOffset.UtcNow,
                        StoppedAt = DateTimeOffset.UtcNow,
                    }
                );
                guestDb.SaveChanges();
            }
            if (enableConversationService)
            {
                conversationService = new ConversationService(
                    contextFactory,
                    factory,
                    new ConversationConstitutionalGatewayStub(),
                    new ConversationExecutionGatewayStub(),
                    new OperationalMandateResolverStub(),
                    new ConversationCursorCodec(
                        Options.Create(
                            new ConversationCursorOptions
                            {
                                HmacKey = "wc134-whatsapp-test-cursor-key-at-least-32-characters",
                            }
                        )
                    )
                );
            }
        }
        if (outboundEmployment is not null)
        {
            conversationDbFactory ??= new ConversationWhatsAppFitness.ConversationFitnessDbFactory(
                Guid.NewGuid().ToString("N")
            );
            var conversationOptions = Options.Create(
                new Wc120ConversationOptions
                {
                    Enabled = true,
                    Environment = "test",
                    PolicyVersion = "policy-1",
                    InstitutionalPolicyVersion = "constitution-1",
                    InteractionPolicyVersion = "interaction-1",
                    ChannelRenderingPolicyVersion = "rendering-1",
                }
            );
            outboundContributions = new ConversationOutboundContributionService(
                conversationDbFactory,
                new ConversationContextProfileService(
                    conversationDbFactory,
                    factory,
                    outboundEmployment,
                    conversationOptions
                ),
                new ConversationStopFence(conversationDbFactory, conversationOptions),
                conversationOptions
            );
        }
        return (
            new WhatsAppJourneyService(
                factory,
                evidence,
                options,
                relationshipGateway,
                emergencyStops,
                conversationDbFactory: conversationDbFactory,
                conversationService: conversationService,
                engagementWorkspace: engagementWorkspace,
                outboundContributions: outboundContributions,
                clock: clock,
                tenantExecutionScope: tenantExecutionScope,
                identity: identity
            ),
            factory,
            evidence
        );
    }

    private sealed class InterceptedConversationFactory(
        IDbContextFactory<ConversationStoreDbContext> inner,
        Func<Task> beforeCreate
    ) : IDbContextFactory<ConversationStoreDbContext>
    {
        public ConversationStoreDbContext CreateDbContext() => inner.CreateDbContext();

        public async Task<ConversationStoreDbContext> CreateDbContextAsync(
            CancellationToken cancellationToken = default
        )
        {
            await beforeCreate();
            return await inner.CreateDbContextAsync(cancellationToken);
        }
    }

    private sealed class ActiveWhatsAppCapabilityGate(Guid tenantId) : IWhatsAppCapabilityGate
    {
        private readonly DateTimeOffset _createdAt = DateTimeOffset.UtcNow;
        public bool Changed { get; set; }
        public bool Revoked { get; set; }

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) =>
            Revoked
                ? throw new WhatsAppCapabilityUnavailableException("AUTHORITY_DENIED")
                : new()
                {
                    TenantId = tenantId,
                    Environment = "demo",
                    StartsAt = _createdAt.AddMinutes(-1),
                    ExpiresAt = _createdAt.AddHours(1),
                    ActivationReference = Changed ? "changed" : "original",
                    AllowProvisionalOnboarding = true,
                    AllowPublicAdmission = true,
                    AllowRegistrationVerification = true,
                };

        public void RequireRecipient(
            Guid tenantId,
            string recipientBindingDigest,
            DateTimeOffset now
        ) { }
    }

    private static string Body(
        string messageId,
        DateTimeOffset sentAt,
        string from,
        string text,
        string riskTier
    ) =>
        JsonSerializer.Serialize(
            new
            {
                messageId,
                timestamp = sentAt.ToUnixTimeSeconds(),
                from,
                text,
                riskTier,
            },
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );

    private static string Sign(string body) =>
        "sha256="
        + Convert.ToHexStringLower(
            HMACSHA256.HashData(Encoding.UTF8.GetBytes(WebhookSecret), Encoding.UTF8.GetBytes(body))
        );

    private static VerifiedPhoneIdentityProof Proof(string messageId, DateTimeOffset now) =>
        new(
            messageId,
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "status",
            "TIER_1_LOW_RISK",
            ProofAudience,
            "AAL1_CHANNEL",
            now,
            now,
            now.AddMinutes(5),
            Guid.NewGuid()
        );

    private static PhoneIdentityProofController ProofController(
        WhatsAppJourneyService service,
        string body,
        string signature
    )
    {
        var controller = new PhoneIdentityProofController(
            service,
            Options.Create(
                new PhoneIdentityAdapterOptions
                {
                    SigningKey = ProofSigningKey,
                    Audience = ProofAudience,
                }
            )
        );
        var context = new DefaultHttpContext();
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
        context.Request.Headers["X-WAOOAW-Phone-Signature"] = signature;
        controller.ControllerContext = new ControllerContext { HttpContext = context };
        return controller;
    }

    private static string SignProof(string body) =>
        "sha256="
        + Convert.ToHexStringLower(
            HMACSHA256.HashData(
                Encoding.UTF8.GetBytes(ProofSigningKey),
                Encoding.UTF8.GetBytes(body)
            )
        );

    private static long TokenExpiry(string token)
    {
        var payload = token.Split('.')[1].Replace('-', '+').Replace('_', '/');
        payload = payload.PadRight(payload.Length + ((4 - payload.Length % 4) % 4), '=');
        using var document = JsonDocument.Parse(Convert.FromBase64String(payload));
        return document.RootElement.GetProperty("exp").GetInt64();
    }

    private sealed class RecordingEvidenceGateway(bool fails) : IWhatsAppRegistrationEvidenceGateway
    {
        public int CallCount { get; private set; }

        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken cancellationToken
        )
        {
            CallCount++;
            if (fails)
                throw new InvalidOperationException("Constitutional evidence unavailable.");
            return Task.CompletedTask;
        }
    }
}
