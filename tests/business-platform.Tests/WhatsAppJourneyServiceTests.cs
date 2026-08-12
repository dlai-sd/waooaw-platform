// Implements: ADR-023 and work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06
// constitutional_basis: C-023, C-026, C-042, C-059, C-063, C-076

using System.Security.Cryptography;
using System.Text;
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

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WhatsAppJourneyServiceTests
{
    private const string WebhookSecret = "webhook-secret-at-least-thirty-two-characters";
    private const string TokenKey = "tenant-token-key-at-least-thirty-two-characters";

    [Fact]
    public async Task ValidInboundCreatesOptInWithoutPersistingRawPhoneAndReplaysIdempotently()
    {
        var (service, factory, evidence) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body("wamid-1", now, "+919876543210", "I need local customers", "TIER_1_LOW_RISK");

        var first = await service.ReceiveAsync(body, Sign(body), now, CancellationToken.None);
        var replay = await service.ReceiveAsync(body, Sign(body), now.AddSeconds(1), CancellationToken.None);

        Assert.Equal("ACCEPTED", first.Status);
        Assert.False(string.IsNullOrWhiteSpace(first.InternalTenantToken));
        Assert.Equal(3, first.InternalTenantToken.Split('.').Length);
        Assert.Equal(now.AddMinutes(30).ToUnixTimeSeconds(), TokenExpiry(first.InternalTenantToken));
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
        Assert.DoesNotContain(first.InternalTenantToken, receipt.SessionTokenHash, StringComparison.Ordinal);
    }

    [Theory]
    [InlineData("+0123456789", 0)]
    [InlineData("919876543210", 0)]
    [InlineData("+919876543210", 6)]
    public async Task InvalidPhoneOrFutureTimestampIsRejected(string phone, int futureMinutes)
    {
        var (service, factory, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body("wamid-invalid", now.AddMinutes(futureMinutes), phone, "Hello", "TIER_1_LOW_RISK");

        await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(body, Sign(body), now, CancellationToken.None));

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
            service.ReceiveAsync(body, signature, now, CancellationToken.None));

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
        var request = Body("wamid-risk-1", now, "+919876543210", "Approve campaign brief", "TIER_2_MEDIUM_RISK");
        var confirm = Body("wamid-risk-2", now.AddSeconds(1), "+919876543210", "YES", "TIER_2_MEDIUM_RISK");

        var pending = await service.ReceiveAsync(request, Sign(request), now, CancellationToken.None);
        var accepted = await service.ReceiveAsync(confirm, Sign(confirm), now.AddSeconds(1), CancellationToken.None);

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
    [InlineData("STOP", "STOP", "delivery stays unresolved")]
    public async Task RelationshipContinuityCommandsPreserveAuthoritativeAndDeliveryMeaning(
        string text, string stage, string expectedReply)
    {
        var (service, _, _) = Create();
        var now = DateTimeOffset.UtcNow;
        var body = Body($"wamid-{text.ToLowerInvariant()}", now, "+919876543210", text, "TIER_1_LOW_RISK");

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
        Assert.Contains("cannot be accepted or initiated in WhatsApp", result.Reply, StringComparison.Ordinal);
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
            service.ReceiveAsync(body, Sign(body), now, CancellationToken.None));

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
            NullLogger<TenantIsolationMiddleware>.Instance);
        var context = new DefaultHttpContext();
        context.Request.Path = path;

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

        var response = Assert.IsType<OkObjectResult>(await controller.ReceiveAsync(CancellationToken.None));
        var responseJson = JsonSerializer.Serialize(response.Value, new JsonSerializerOptions(JsonSerializerDefaults.Web));

        Assert.DoesNotContain("tenantToken", responseJson, StringComparison.OrdinalIgnoreCase);
        Assert.DoesNotContain("waooaw-phone-identity", responseJson, StringComparison.Ordinal);
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
            Guid.NewGuid(), "TIER_4_PORTAL_FRESH", DateTimeOffset.UtcNow, Guid.NewGuid());
        await service.EnrolMpinAsync(tenantId, phone, "2468", proof, CancellationToken.None);

        Assert.False(await service.VerifyMpinAsync(tenantId, phone, "1111", now, CancellationToken.None));
        Assert.False(await service.VerifyMpinAsync(tenantId, phone, "2222", now, CancellationToken.None));
        Assert.False(await service.VerifyMpinAsync(tenantId, phone, "3333", now, CancellationToken.None));
        var locked = await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.VerifyMpinAsync(tenantId, phone, "2468", now.AddMinutes(1), CancellationToken.None));
        Assert.Equal(423, locked.StatusCode);
        Assert.True(await service.VerifyMpinAsync(
            tenantId, phone, "2468", now.AddMinutes(31), CancellationToken.None));
    }

    [Fact]
    public async Task CctAe01Takeover01_UnknownPhoneCannotAttachFromPortalPayloadHints()
    {
        var relationshipGateway = new RecordingRelationshipConstitutionalGateway();
        var (service, _, _) = Create(relationshipGateway: relationshipGateway);

        await Assert.ThrowsAsync<ConstitutionalActionDeniedException>(() => service.AttachPhoneAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            "+919876543210",
            "conversation",
            new PortalPhoneAttachProof(
                Guid.NewGuid(), "TIER_4_PORTAL_FRESH", DateTimeOffset.UtcNow, Guid.NewGuid()),
            CancellationToken.None));

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
        db.EmploymentRelationships.Add(new EmploymentRelationship
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ProfessionalType = "DMA",
            EvaluationIntentId = Guid.NewGuid(),
            InitiatingParticipantId = participantId,
        });
        db.RelationshipParticipants.Add(new RelationshipParticipant
        {
            TenantId = tenantId,
            RelationshipId = relationshipId,
            ParticipantId = participantId,
            Role = RelationshipParticipantRole.Evaluator,
            BoundEvidenceId = Guid.NewGuid(),
        });
        await db.SaveChangesAsync();

        var resolution = await service.AttachPhoneAsync(
            tenantId,
            relationshipId,
            phone,
            "conversation",
            new PortalPhoneAttachProof(
                participantId, "TIER_4_PORTAL_FRESH", DateTimeOffset.UtcNow, Guid.NewGuid()),
            CancellationToken.None);

        Assert.Equal("TIER_4_PORTAL_FRESH", resolution.AuthenticationAssurance);
        Assert.Equal(1, relationshipGateway.CallCount);
        var binding = await db.ChannelBindings.SingleAsync();
        Assert.Equal("ACTIVE", binding.Status);
        Assert.DoesNotContain(phone, binding.ExternalSubjectHash, StringComparison.Ordinal);
    }

    private static (WhatsAppJourneyService Service, InMemoryEmploymentRelationshipFactory Factory, RecordingEvidenceGateway Evidence) Create(
        bool evidenceFails = false,
        IRelationshipConstitutionalGateway? relationshipGateway = null)
    {
        var factory = new InMemoryEmploymentRelationshipFactory(Guid.NewGuid().ToString("N"));
        var evidence = new RecordingEvidenceGateway(evidenceFails);
        var options = Options.Create(new WhatsAppJourneyOptions
        {
            WebhookSecret = WebhookSecret,
            TenantTokenKey = TokenKey,
        });
        return (new WhatsAppJourneyService(factory, evidence, options, relationshipGateway), factory, evidence);
    }

    private static string Body(string messageId, DateTimeOffset sentAt, string from, string text, string riskTier) =>
        JsonSerializer.Serialize(new { messageId, timestamp = sentAt.ToUnixTimeSeconds(), from, text, riskTier },
            new JsonSerializerOptions(JsonSerializerDefaults.Web));

    private static string Sign(string body) => "sha256=" + Convert.ToHexStringLower(
        HMACSHA256.HashData(Encoding.UTF8.GetBytes(WebhookSecret), Encoding.UTF8.GetBytes(body)));

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

        public Task RecordAsync(Guid tenantId, string messageId, string phoneHmac, DateTimeOffset occurredAt,
            CancellationToken cancellationToken)
        {
            CallCount++;
            if (fails) throw new InvalidOperationException("Constitutional evidence unavailable.");
            return Task.CompletedTask;
        }
    }
}