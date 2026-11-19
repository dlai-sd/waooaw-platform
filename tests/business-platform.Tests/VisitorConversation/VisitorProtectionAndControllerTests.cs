// Implements: work-contracts/WC-135-requirements.yaml WC135-R003, WC135-R007, WC135-R008, WC135-R011, WC135-R016
// Constitutional basis: C-023, C-026, C-048, C-059, C-063

using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services.Visitor;
using Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.VisitorConversation;

public sealed class VisitorProtectionTests
{
    private static VisitorFieldProtector Protector(VisitorConversationOptions options) =>
        new(
            new ConfigurationVisitorKeyRing(
                new StaticOptionsMonitor<VisitorConversationOptions>(options)
            )
        );

    private static VisitorConversationOptions Keys(string current = "k1") =>
        new()
        {
            LocalKeys = new() { ["k1"] = new string('a', 40), ["k2"] = new string('b', 40) },
            LocalCurrentKeyVersion = current,
        };

    private static readonly Guid Tenant = Guid.NewGuid();
    private static readonly Guid Row = Guid.NewGuid();

    [Fact]
    public async Task EnvelopeRoundTripsAndIsRandomised()
    {
        var protector = Protector(Keys());
        var one = await protector.ProtectAsync(
            "+919876543210",
            Tenant,
            "phone",
            Row,
            CancellationToken.None
        );
        var two = await protector.ProtectAsync(
            "+919876543210",
            Tenant,
            "phone",
            Row,
            CancellationToken.None
        );
        Assert.StartsWith("v2.k1.", one, StringComparison.Ordinal);
        Assert.NotEqual(one, two);
        Assert.DoesNotContain("9876543210", one, StringComparison.Ordinal);
        Assert.Equal(
            "+919876543210",
            await protector.UnprotectAsync(one, Tenant, "phone", Row, CancellationToken.None)
        );
    }

    [Theory]
    [InlineData("tenant")]
    [InlineData("field")]
    [InlineData("row")]
    public async Task CiphertextCannotBeMovedToAnotherTenantFieldOrRow(string moved)
    {
        var protector = Protector(Keys());
        var envelope = await protector.ProtectAsync(
            "secret value",
            Tenant,
            "email",
            Row,
            CancellationToken.None
        );
        var failure = await Assert.ThrowsAsync<VisitorProtectionException>(() =>
            protector.UnprotectAsync(
                envelope,
                moved == "tenant" ? Guid.NewGuid() : Tenant,
                moved == "field" ? "name" : "email",
                moved == "row" ? Guid.NewGuid() : Row,
                CancellationToken.None
            )
        );
        Assert.Equal("ENVELOPE_INVALID", failure.Reason);
    }

    [Fact]
    public async Task OldKeyVersionsStayReadableAfterRotationUntilTheyAreRewrapped()
    {
        var options = Keys("k1");
        var protector = Protector(options);
        var oldEnvelope = await protector.ProtectAsync(
            "kept across rotation",
            Tenant,
            "name",
            Row,
            CancellationToken.None
        );
        options.LocalCurrentKeyVersion = "k2";
        Assert.True(await protector.NeedsRewrapAsync(oldEnvelope, CancellationToken.None));
        Assert.Equal(
            "kept across rotation",
            await protector.UnprotectAsync(oldEnvelope, Tenant, "name", Row, CancellationToken.None)
        );
        var fresh = await protector.ProtectAsync(
            "kept across rotation",
            Tenant,
            "name",
            Row,
            CancellationToken.None
        );
        Assert.StartsWith("v2.k2.", fresh, StringComparison.Ordinal);
        Assert.False(await protector.NeedsRewrapAsync(fresh, CancellationToken.None));
    }

    [Fact]
    public async Task UnknownKeyVersionAndMalformedEnvelopesAreRefusedWithoutFallback()
    {
        var options = Keys();
        var protector = Protector(options);
        var envelope = await protector.ProtectAsync(
            "value",
            Tenant,
            "phone",
            Row,
            CancellationToken.None
        );
        var unknown = envelope.Replace("v2.k1.", "v2.k9.", StringComparison.Ordinal);
        var missing = await Assert.ThrowsAsync<VisitorProtectionException>(() =>
            protector.UnprotectAsync(unknown, Tenant, "phone", Row, CancellationToken.None)
        );
        Assert.Equal("KEY_VERSION_UNAVAILABLE", missing.Reason);
        foreach (
            var bad in new[]
            {
                "",
                "v1.a.b.c.d",
                "v2.k1.x",
                "v2.k1.!!.!!.!!",
                "v2.bad version.AA==.AA==.AA==",
            }
        )
            await Assert.ThrowsAsync<VisitorProtectionException>(() =>
                protector.UnprotectAsync(bad, Tenant, "phone", Row, CancellationToken.None)
            );
        await Assert.ThrowsAsync<VisitorProtectionException>(() =>
            Protector(new VisitorConversationOptions())
                .ProtectAsync("x", Tenant, "phone", Row, CancellationToken.None)
        );
    }

    [Fact]
    public void MaskNeverEchoesTheValue()
    {
        Assert.Equal("***", VisitorFieldProtector.Mask("rupali@example.com"));
        Assert.Equal(string.Empty, VisitorFieldProtector.Mask(null));
    }
}

public sealed class VisitorOptionsTests
{
    private static readonly VisitorLeadOptionsValidator Lead = new();
    private static readonly VisitorConversationOptionsValidator Conversation = new();

    [Theory]
    [InlineData(29, false)]
    [InlineData(30, true)]
    [InlineData(90, true)]
    [InlineData(365, true)]
    [InlineData(366, false)]
    public void RetentionIsBoundedBetweenThirtyAndThreeHundredSixtyFiveDays(int days, bool valid) =>
        Assert.Equal(
            valid,
            Lead.Validate(null, new VisitorLeadOptions { RetentionDays = days }).Succeeded
        );

    [Theory]
    [InlineData(0, false)]
    [InlineData(1, true)]
    [InlineData(30, true)]
    [InlineData(31, false)]
    public void SimulationRetentionIsBoundedBetweenOneAndThirtyDays(int days, bool valid) =>
        Assert.Equal(
            valid,
            Lead.Validate(null, new VisitorLeadOptions { SimulationRetentionDays = days }).Succeeded
        );

    [Fact]
    public void DefaultsFollowTheFounderDecisionAndTenantOverridesAreValidatedToo()
    {
        var defaults = new VisitorLeadOptions();
        Assert.Equal(90, defaults.RetentionDays);
        Assert.Equal(7, defaults.SimulationRetentionDays);
        Assert.True(Lead.Validate(null, defaults).Succeeded);
        var tenant = Guid.NewGuid();
        var overridden = new VisitorLeadOptions { TenantRetentionDays = { [tenant] = 5 } };
        Assert.False(Lead.Validate(null, overridden).Succeeded);
        Assert.Equal(
            120,
            new VisitorLeadOptions { TenantRetentionDays = { [tenant] = 120 } }.RetentionDaysFor(
                tenant
            )
        );
        Assert.Equal(90, defaults.RetentionDaysFor(tenant));
    }

    [Fact]
    public void ConversationOptionsFailClosedOnUnsafeCombinations()
    {
        Assert.True(Conversation.Validate(null, new VisitorConversationOptions()).Succeeded);
        Assert.False(
            Conversation.Validate(null, new VisitorConversationOptions { Mode = "BETA" }).Succeeded
        );
        Assert.False(
            Conversation
                .Validate(
                    null,
                    new VisitorConversationOptions
                    {
                        SimulatorEnabled = true,
                        SimulatorSecret = "short",
                    }
                )
                .Succeeded
        );
        Assert.False(
            Conversation
                .Validate(null, new VisitorConversationOptions { PublicEntryEnabled = true })
                .Succeeded
        );
        Assert.False(
            Conversation
                .Validate(
                    null,
                    new VisitorConversationOptions { HandoffBaseUrl = "http://insecure.example" }
                )
                .Succeeded
        );
        Assert.False(
            Conversation
                .Validate(null, new VisitorConversationOptions { MaxChoiceButtons = 4 })
                .Succeeded
        );
        Assert.Equal(VisitorMode.Legacy, new VisitorConversationOptions().Mode);
        Assert.False(new VisitorConversationOptions().PublicEntryEnabled);
        Assert.False(new VisitorConversationOptions().SimulatorEnabled);
    }
}

public sealed class VisitorSecurityPrimitivesTests
{
    [Fact]
    public void SimulatorSignatureEqualsTheValueTheSimulatorClientProduces()
    {
        // Produced by scripts/visitor_simulation/client.py sign_request with the same inputs.
        Assert.Equal(
            "ce1e6956879643facc747036b26a829dd56be54f83210d4152a3e09897bcebba",
            VisitorSimulatorSignature.Compute(
                new string('s', 40),
                1_795_000_000,
                "POST",
                "/api/v1/visitor/sessions",
                Encoding.UTF8.GetBytes("{\"a\":1}")
            )
        );
    }

    [Fact]
    public void SimulatorSignatureMatchesAFixedVectorAndBindsMethodPathBodyAndTime()
    {
        var secret = new string('k', 32);
        var body = Encoding.UTF8.GetBytes("{\"a\":1}");
        var signature = VisitorSimulatorSignature.Compute(
            secret,
            1_700_000_000,
            "post",
            "/api/v1/visitor/sessions",
            body
        );
        Assert.Equal(64, signature.Length);
        Assert.Equal(
            signature,
            VisitorSimulatorSignature.Compute(
                secret,
                1_700_000_000,
                "POST",
                "/api/v1/visitor/sessions",
                body
            )
        );
        var now = DateTimeOffset.FromUnixTimeSeconds(1_700_000_100);
        bool Verify(
            string method,
            string path,
            byte[] payload,
            string? sig = null,
            string? ts = null
        ) =>
            VisitorSimulatorSignature.Verify(
                secret,
                ts ?? "1700000000",
                sig ?? signature,
                method,
                path,
                payload,
                now
            );
        Assert.True(Verify("POST", "/api/v1/visitor/sessions", body));
        Assert.False(Verify("GET", "/api/v1/visitor/sessions", body));
        Assert.False(Verify("POST", "/api/v1/visitor/other", body));
        Assert.False(
            Verify("POST", "/api/v1/visitor/sessions", Encoding.UTF8.GetBytes("{\"a\":2}"))
        );
        Assert.False(Verify("POST", "/api/v1/visitor/sessions", body, ts: "1700000001"));
        Assert.False(Verify("POST", "/api/v1/visitor/sessions", body, sig: new string('0', 64)));
        Assert.False(Verify("POST", "/api/v1/visitor/sessions", body, sig: ""));
        Assert.False(
            VisitorSimulatorSignature.Verify(
                "",
                "1700000000",
                signature,
                "POST",
                "/api/v1/visitor/sessions",
                body,
                now
            )
        );
        Assert.False(
            VisitorSimulatorSignature.Verify(
                secret,
                "1700000000",
                signature,
                "POST",
                "/api/v1/visitor/sessions",
                body,
                now.AddMinutes(6)
            )
        );
    }

    [Fact]
    public void SessionTokensAreBoundToSessionTenantAndExpiry()
    {
        var key = new string('t', 40);
        var tenant = Guid.NewGuid();
        var session = Guid.NewGuid();
        var now = DateTimeOffset.UtcNow;
        var token = VisitorSessionTokens.Issue(key, session, tenant, now.AddMinutes(30));
        Assert.True(VisitorSessionTokens.TryValidate(key, token, tenant, now, out var parsed));
        Assert.Equal(session, parsed);
        Assert.False(VisitorSessionTokens.TryValidate(key, token, Guid.NewGuid(), now, out _));
        Assert.False(
            VisitorSessionTokens.TryValidate(key, token, tenant, now.AddMinutes(31), out _)
        );
        Assert.False(
            VisitorSessionTokens.TryValidate(new string('u', 40), token, tenant, now, out _)
        );
        Assert.False(VisitorSessionTokens.TryValidate(key, token + "0", tenant, now, out _));
        Assert.False(VisitorSessionTokens.TryValidate(key, "v1.x.y.z", tenant, now, out _));
        Assert.False(VisitorSessionTokens.TryValidate(key, string.Empty, tenant, now, out _));
    }
}

public sealed class VisitorControllerTests
{
    private static readonly string Secret = new('s', 40);

    private sealed class Fixture
    {
        public VisitorHarness Harness { get; }
        public VisitorConversationController Controller { get; }
        public VisitorConversationOptions Options => Harness.Options;

        public Fixture(Action<VisitorConversationOptions>? configure = null)
        {
            Harness = new VisitorHarness(configure: options =>
            {
                options.DefaultTenantId = VisitorHarness.Tenant;
                options.SessionTokenKey = new string('t', 40);
                options.SimulatorSecret = Secret;
                configure?.Invoke(options);
            });
            Controller = new VisitorConversationController(
                Harness.Service,
                new StaticOptionsMonitor<VisitorConversationOptions>(Harness.Options),
                Harness.Clock,
                NullLogger<VisitorConversationController>.Instance
            );
        }

        public void Request(
            string method,
            string path,
            string body,
            bool signed,
            string? idempotency = null,
            string? bearer = null,
            string? secret = null,
            long? timestamp = null
        )
        {
            var http = new DefaultHttpContext();
            var bytes = Encoding.UTF8.GetBytes(body);
            http.Request.Method = method;
            http.Request.Path = path;
            http.Request.Body = new MemoryStream(bytes);
            http.Request.ContentLength = bytes.Length;
            http.Request.ContentType = "application/json";
            if (signed)
            {
                var ts = timestamp ?? Harness.Clock.Now.ToUnixTimeSeconds();
                http.Request.Headers[VisitorSimulatorSignature.TimestampHeader] = ts.ToString();
                http.Request.Headers[VisitorSimulatorSignature.SignatureHeader] =
                    VisitorSimulatorSignature.Compute(secret ?? Secret, ts, method, path, bytes);
            }
            if (idempotency is not null)
                http.Request.Headers["Idempotency-Key"] = idempotency;
            if (bearer is not null)
                http.Request.Headers.Authorization = $"Bearer {bearer}";
            Controller.ControllerContext = new ControllerContext { HttpContext = http };
        }
    }

    private static (int Status, JsonElement Body) Read(IActionResult result)
    {
        var objectResult = Assert.IsAssignableFrom<ObjectResult>(result);
        var json = JsonSerializer.SerializeToElement(objectResult.Value);
        return (objectResult.StatusCode ?? 200, json);
    }

    private const string OpenBody =
        "{\"schemaVersion\":\"1.0\",\"channel\":\"SIMULATION\",\"subjectKey\":\"sim-ctrl-0001\"}";

    [Fact]
    public async Task SignedSimulatorOpensASessionAndTheReplyCarriesTheConsentPrompt()
    {
        var f = new Fixture();
        f.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        var (status, body) = Read(await f.Controller.OpenAsync(CancellationToken.None));
        Assert.Equal(201, status);
        Assert.Equal("CONSENT_PENDING", body.GetProperty("state").GetString());
        Assert.Equal("SIMULATION", body.GetProperty("channel").GetString());
        Assert.True(body.GetProperty("sessionToken").ValueKind is JsonValueKind.Null);
        Assert.Contains(
            body.GetProperty("reply").GetProperty("blocks").EnumerateArray(),
            block => block.GetProperty("type").GetString() == "CHOICES"
        );

        f.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        Assert.Equal(200, Read(await f.Controller.OpenAsync(CancellationToken.None)).Status);
    }

    [Theory]
    [InlineData("missing")]
    [InlineData("wrong-secret")]
    [InlineData("stale")]
    public async Task UnsignedWrongSecretOrStaleSimulatorRequestsAreRefused(string case_)
    {
        var f = new Fixture();
        f.Request(
            "POST",
            "/api/v1/visitor/sessions",
            OpenBody,
            signed: case_ != "missing",
            secret: case_ == "wrong-secret" ? new string('x', 40) : null,
            timestamp: case_ == "stale"
                ? f.Harness.Clock.Now.AddMinutes(-10).ToUnixTimeSeconds()
                : null
        );
        var (status, body) = Read(await f.Controller.OpenAsync(CancellationToken.None));
        Assert.Equal(401, status);
        Assert.Equal("VISITOR_SESSION_REQUIRED", body.GetProperty("code").GetString());
        Assert.True(Guid.TryParse(body.GetProperty("correlationId").GetString(), out _));
    }

    [Fact]
    public async Task SimulatorDisabledOrLegacyModeNeverServesTheEndpoint()
    {
        var disabled = new Fixture(options => options.SimulatorEnabled = false);
        disabled.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        Assert.Equal(401, Read(await disabled.Controller.OpenAsync(CancellationToken.None)).Status);

        var legacy = new Fixture(options => options.Mode = VisitorMode.Legacy);
        legacy.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        var (status, body) = Read(await legacy.Controller.OpenAsync(CancellationToken.None));
        Assert.Equal(503, status);
        Assert.Equal("VISITOR_DISABLED", body.GetProperty("code").GetString());
    }

    [Theory]
    [InlineData(
        "{\"schemaVersion\":\"1.0\",\"channel\":\"SIMULATION\",\"subjectKey\":\"sim-ctrl-0001\",\"tenantId\":\"x\"}"
    )]
    [InlineData(
        "{\"schemaVersion\":\"2.0\",\"channel\":\"SIMULATION\",\"subjectKey\":\"sim-ctrl-0001\"}"
    )]
    [InlineData(
        "{\"schemaVersion\":\"1.0\",\"channel\":\"WHATSAPP\",\"subjectKey\":\"sim-ctrl-0001\"}"
    )]
    [InlineData("{\"schemaVersion\":\"1.0\",\"channel\":\"SIMULATION\",\"subjectKey\":\"short\"}")]
    [InlineData("not json")]
    public async Task MalformedOrTenantSuppliedBodiesAreRejected(string body)
    {
        var f = new Fixture();
        f.Request("POST", "/api/v1/visitor/sessions", body, signed: true);
        Assert.Equal(400, Read(await f.Controller.OpenAsync(CancellationToken.None)).Status);
    }

    [Fact]
    public async Task OversizedBodiesAreRejectedBeforeParsing()
    {
        var f = new Fixture();
        f.Request("POST", "/api/v1/visitor/sessions", new string('x', 9_000), signed: true);
        Assert.Equal(400, Read(await f.Controller.OpenAsync(CancellationToken.None)).Status);
    }

    [Fact]
    public async Task SendingRequiresAnIdempotencyKeyAndReturnsTheStructuredTurn()
    {
        var f = new Fixture();
        f.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        var session = Read(await f.Controller.OpenAsync(CancellationToken.None))
            .Body.GetProperty("sessionId")
            .GetGuid();
        var path = $"/api/v1/visitor/sessions/{session}/messages";
        const string yes =
            "{\"schemaVersion\":\"1.0\",\"content\":{\"type\":\"CHOICE\",\"choiceId\":\"consent_yes\"}}";

        f.Request("POST", path, yes, signed: true);
        Assert.Equal(
            400,
            Read(await f.Controller.SendAsync(session, CancellationToken.None)).Status
        );

        var key = Guid.NewGuid().ToString();
        f.Request("POST", path, yes, signed: true, idempotency: key);
        var (status, body) = Read(await f.Controller.SendAsync(session, CancellationToken.None));
        Assert.Equal(200, status);
        Assert.Equal("DISCOVER", body.GetProperty("state").GetString());
        Assert.Equal("1.0", body.GetProperty("reply").GetProperty("schemaVersion").GetString());

        f.Request("POST", path, yes, signed: true, idempotency: key);
        var replay = Read(await f.Controller.SendAsync(session, CancellationToken.None));
        Assert.Equal(
            body.GetProperty("messageId").GetGuid(),
            replay.Body.GetProperty("messageId").GetGuid()
        );

        f.Request(
            "POST",
            path,
            "{\"schemaVersion\":\"1.0\",\"content\":{\"type\":\"TEXT\",\"text\":\"hello\"}}",
            signed: true,
            idempotency: key
        );
        var conflict = Read(await f.Controller.SendAsync(session, CancellationToken.None));
        Assert.Equal(409, conflict.Status);
        Assert.Equal("VISITOR_IDEMPOTENCY_CONFLICT", conflict.Body.GetProperty("code").GetString());

        foreach (
            var invalid in new[]
            {
                "{\"schemaVersion\":\"1.0\",\"content\":{\"type\":\"TEXT\"}}",
                "{\"schemaVersion\":\"1.0\",\"content\":{\"type\":\"CHOICE\",\"text\":\"x\",\"choiceId\":\"a\"}}",
                "{\"schemaVersion\":\"1.0\",\"content\":{\"type\":\"VOICE\",\"text\":\"x\"}}",
            }
        )
        {
            f.Request("POST", path, invalid, signed: true, idempotency: Guid.NewGuid().ToString());
            Assert.Equal(
                400,
                Read(await f.Controller.SendAsync(session, CancellationToken.None)).Status
            );
        }
    }

    [Fact]
    public async Task RateLimitedResponsesCarryRetryAfter()
    {
        var f = new Fixture(options => options.MessagesPerVisitorPerMinute = 1);
        f.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        var session = Read(await f.Controller.OpenAsync(CancellationToken.None))
            .Body.GetProperty("sessionId")
            .GetGuid();
        var path = $"/api/v1/visitor/sessions/{session}/messages";
        const string yes =
            "{\"schemaVersion\":\"1.0\",\"content\":{\"type\":\"CHOICE\",\"choiceId\":\"consent_yes\"}}";
        f.Request("POST", path, yes, signed: true, idempotency: Guid.NewGuid().ToString());
        Assert.Equal(
            200,
            Read(await f.Controller.SendAsync(session, CancellationToken.None)).Status
        );
        f.Request("POST", path, yes, signed: true, idempotency: Guid.NewGuid().ToString());
        var (status, body) = Read(await f.Controller.SendAsync(session, CancellationToken.None));
        Assert.Equal(429, status);
        Assert.Equal(30, body.GetProperty("retryAfterSeconds").GetInt32());
        Assert.Equal("30", f.Controller.Response.Headers.RetryAfter.ToString());
    }

    [Fact]
    public async Task PublicWebEntryIsClosedByDefaultAndTokenScopedWhenEnabled()
    {
        const string webOpen = "{\"schemaVersion\":\"1.0\",\"channel\":\"WEB\"}";
        var closed = new Fixture();
        closed.Request("POST", "/api/v1/visitor/sessions", webOpen, signed: false);
        Assert.Equal(401, Read(await closed.Controller.OpenAsync(CancellationToken.None)).Status);

        var open = new Fixture(options => options.PublicEntryEnabled = true);
        open.Request("POST", "/api/v1/visitor/sessions", webOpen, signed: false);
        var (status, body) = Read(await open.Controller.OpenAsync(CancellationToken.None));
        Assert.Equal(201, status);
        var session = body.GetProperty("sessionId").GetGuid();
        var token = body.GetProperty("sessionToken").GetString()!;

        open.Request(
            "GET",
            $"/api/v1/visitor/sessions/{session}",
            string.Empty,
            signed: false,
            bearer: token
        );
        Assert.Equal(
            200,
            Read(await open.Controller.GetAsync(session, CancellationToken.None)).Status
        );

        open.Request(
            "GET",
            $"/api/v1/visitor/sessions/{Guid.NewGuid()}",
            string.Empty,
            signed: false,
            bearer: token
        );
        Assert.Equal(
            401,
            Read(await open.Controller.GetAsync(Guid.NewGuid(), CancellationToken.None)).Status
        );

        open.Request("GET", $"/api/v1/visitor/sessions/{session}", string.Empty, signed: true);
        Assert.Equal(
            404,
            Read(await open.Controller.GetAsync(session, CancellationToken.None)).Status
        );

        open.Request("GET", $"/api/v1/visitor/sessions/{session}", string.Empty, signed: false);
        Assert.Equal(
            401,
            Read(await open.Controller.GetAsync(session, CancellationToken.None)).Status
        );
    }

    [Fact]
    public async Task TranscriptAndHandoffTapWorkThroughTheEndpoint()
    {
        var f = new Fixture();
        f.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        var session = Read(await f.Controller.OpenAsync(CancellationToken.None))
            .Body.GetProperty("sessionId")
            .GetGuid();
        var handoff = await f.Harness.JourneyToHandoffAsync(session);
        var url = handoff.Reply.Blocks.Single(block => block.Type == "LINK").Url!;
        var reference = url[(url.IndexOf("lead=", StringComparison.Ordinal) + 5)..];

        f.Request(
            "GET",
            $"/api/v1/visitor/sessions/{session}/messages",
            string.Empty,
            signed: true
        );
        var (status, body) = Read(
            await f.Controller.ListAsync(session, null, 40, CancellationToken.None)
        );
        Assert.Equal(200, status);
        Assert.True(body.GetProperty("items").GetArrayLength() >= 8);

        f.Request("POST", $"/api/v1/visitor/handoffs/{reference}/tap", string.Empty, signed: false);
        Assert.True(
            Read(await f.Controller.TapAsync(reference, CancellationToken.None))
                .Body.GetProperty("recorded")
                .GetBoolean()
        );
        f.Request("POST", $"/api/v1/visitor/handoffs/{reference}/tap", string.Empty, signed: false);
        Assert.False(
            Read(await f.Controller.TapAsync(reference, CancellationToken.None))
                .Body.GetProperty("recorded")
                .GetBoolean()
        );
    }

    [Fact]
    public async Task OpenEndpointRecordsTheTapAndRedirectsToThePortal()
    {
        var f = new Fixture();
        f.Harness.Options.HandoffOpenBaseUrl = "https://api.example.test/api/v1/visitor/handoffs/";
        f.Request("POST", "/api/v1/visitor/sessions", OpenBody, signed: true);
        var session = Read(await f.Controller.OpenAsync(CancellationToken.None))
            .Body.GetProperty("sessionId")
            .GetGuid();
        var handoff = await f.Harness.JourneyToHandoffAsync(session);
        var url = handoff.Reply.Blocks.Single(block => block.Type == "LINK").Url!;
        Assert.StartsWith("https://api.example.test/api/v1/visitor/handoffs/", url);
        Assert.EndsWith("/open", url);
        var reference = url[
            "https://api.example.test/api/v1/visitor/handoffs/".Length..^"/open".Length
        ];

        f.Request("GET", $"/api/v1/visitor/handoffs/{reference}/open", string.Empty, signed: false);
        var redirect = Assert.IsType<RedirectResult>(
            await f.Controller.OpenAsync(reference, CancellationToken.None)
        );
        Assert.StartsWith(f.Harness.Options.HandoffBaseUrl, redirect.Url);
        Assert.Contains($"lead={reference}", redirect.Url);
        f.Request("POST", $"/api/v1/visitor/handoffs/{reference}/tap", string.Empty, signed: false);
        Assert.False(
            Read(await f.Controller.TapAsync(reference, CancellationToken.None))
                .Body.GetProperty("recorded")
                .GetBoolean()
        );

        f.Request("GET", "/api/v1/visitor/handoffs/unknown/open", string.Empty, signed: false);
        Assert.IsType<RedirectResult>(
            await f.Controller.OpenAsync("unknown", CancellationToken.None)
        );
    }
}
