using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class WhatsAppDemoProviderTests
{
    private static readonly DateTimeOffset Now = new(2026, 11, 2, 9, 0, 0, TimeSpan.Zero);
    private static readonly string Recipient = new('b', 64);
    private static readonly string TupleDigest = "sha256:" + new string('a', 64);

    [Theory]
    [InlineData(
        """[{"SchemaVersion":"1.0","BlockType":"MEDIA","Text":"not an admitted text projection"}]"""
    )]
    [InlineData("""[{"SchemaVersion":"2.0","BlockType":"TEXT","Text":"unsupported version"}]""")]
    [InlineData("""[{"SchemaVersion":"1.0","Text":"missing block type"}]""")]
    [InlineData(
        """[{"SchemaVersion":"1.0","BlockType":"TEXT","Text":"first","Text":"overridden"}]"""
    )]
    [InlineData(
        """[{"SchemaVersion":"1.0","BlockType":"TEXT","Text":"body","MediaUrl":"https://example.test"}]"""
    )]
    public async Task UnsupportedCanonicalBlocksCannotBecomeProviderText(string contentJson)
    {
        var fixture = await SeedAsync();
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            var message = await db.Messages.SingleAsync();
            message.ContentJson = contentJson;
            await db.SaveChangesAsync();
        }
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException(
                    "Unsupported canonical blocks must not leave the platform."
                );
            }
        );

        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );

        Assert.Equal("MESSAGE_PROJECTION_DENIED", failure.ReasonCode);
        Assert.Equal(0, calls);
        await using var saved = fixture.Context.Conversations.CreateDbContext();
        Assert.Empty(saved.Set<WhatsAppTrafficReservation>());
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public async Task ConsentAndServiceWindowAreRecheckedAfterProtectedReads(bool optOut)
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException(
                    "Ineligible recipient must not reach provider egress."
                );
            }
        );
        var credentials = new Credentials(async () =>
        {
            await using var db = fixture.Context.Relationships.CreateDbContext();
            var contact = await db.WhatsAppJourneyContacts.SingleAsync();
            if (optOut)
                contact.OptedOutAt = Now;
            else
                contact.LastInboundAt = Now.AddHours(-25);
            await db.SaveChangesAsync();
        });
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory, credentials: credentials)
                .DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal("RECIPIENT_ELIGIBILITY_REVOKED", failure.ReasonCode);
        Assert.Equal(0, calls);
    }

    [Theory]
    [InlineData("whatsapp-demo.example.com", "/", "GET", false)]
    [InlineData("whatsapp-demo.example.com", "/health/live", "GET", false)]
    [InlineData("whatsapp-demo.example.com", "/api/v1/channels/whatsapp/webhook", "PUT", false)]
    [InlineData("whatsapp-demo.example.com", "/api/v1/channels/whatsapp/webhook", "GET", true)]
    [InlineData("whatsapp-demo.example.com", "/api/v1/channels/whatsapp/webhook", "POST", true)]
    [InlineData("cp.demo.waooaw.com", "/api/v1/employment/relationships", "GET", true)]
    public async Task DedicatedCallbackHostExposesOnlyItsExactGetAndPostRoute(
        string host,
        string path,
        string method,
        bool expectedNext
    )
    {
        var invoked = false;
        var middleware = new WhatsAppCallbackHostMiddleware(_ =>
        {
            invoked = true;
            return Task.CompletedTask;
        });
        var context = new DefaultHttpContext();
        context.Request.Host = new HostString(host);
        context.Request.Path = path;
        context.Request.Method = method;
        await middleware.InvokeAsync(
            context,
            Options.Create(
                new WhatsAppJourneyOptions { CallbackHost = "whatsapp-demo.example.com" }
            )
        );
        Assert.Equal(expectedNext, invoked);
        if (!expectedNext)
            Assert.Equal(404, context.Response.StatusCode);
    }

    [Fact]
    public async Task KeyVaultReadsExactVersionsEveryTimeAndBoundsCredentialLifetime()
    {
        var calls = 0;
        using var factory = new ClientFactory(
            async (request, token) =>
            {
                calls++;
                await Task.CompletedTask;
                Assert.False(token.IsCancellationRequested);
                return SecretResponse(request);
            }
        );
        var reader = Reader(factory);
        var first = await reader.ReadAsync(CancellationToken.None);
        var second = await reader.ReadAsync(CancellationToken.None);
        Assert.Equal(6, calls);
        Assert.Equal(Now.AddMinutes(5), first.ValidUntil);
        Assert.Equal(first.ValidUntil, second.ValidUntil);
        Assert.Equal(nameof(WhatsAppProviderCredentials), first.ToString());
        Assert.Equal(nameof(WhatsAppProviderBinding), first.Binding.ToString());
    }

    [Theory]
    [InlineData("disabled")]
    [InlineData("expired")]
    [InlineData("wrong-version")]
    [InlineData("future")]
    [InlineData("wrong-resource")]
    [InlineData("oversized")]
    [InlineData("redirect")]
    [InlineData("wrong-shape")]
    public async Task SecretFailuresNeverReturnCredentialsOrFollowAnAlternateLocation(
        string failure
    )
    {
        var calls = 0;
        using var factory = new ClientFactory(
            (request, _) =>
            {
                calls++;
                return Task.FromResult(SecretResponse(request, failure));
            }
        );
        var error = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Reader(factory).ReadAsync(CancellationToken.None)
        );
        Assert.Matches("^[A-Z_]+$", error.ReasonCode);
        Assert.InRange(calls, 1, 2);
    }

    [Fact]
    public async Task InvalidVaultAndNonlocalIdentityEndpointAreDeniedBeforeAnyRequest()
    {
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException("Network must not be used.");
            }
        );
        var options = ProviderOptions();
        options.VaultHost = "kv-waooaw-uat.vault.azure.net";
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Reader(factory, options).ReadAsync(CancellationToken.None)
        );
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Reader(factory, endpoint: "https://example.invalid/token")
                .ReadAsync(CancellationToken.None)
        );
        Assert.Equal(0, calls);
    }

    [Fact]
    public async Task CallerCancellationIsNotConvertedToProviderSuccessOrDefaultCredentials()
    {
        using var cancellation = new CancellationTokenSource();
        using var factory = new ClientFactory(
            (_, token) =>
            {
                cancellation.Cancel();
                token.ThrowIfCancellationRequested();
                throw new InvalidOperationException("Cancellation was required.");
            }
        );
        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            Reader(factory).ReadAsync(cancellation.Token)
        );
    }

    [Fact]
    public async Task EachWebhookPurposeReadsOnlyItsOwnPinnedSecretAndNoOutboundToken()
    {
        var paths = new List<string>();
        using var factory = new ClientFactory(
            (request, _) =>
            {
                paths.Add(request.RequestUri!.AbsolutePath);
                return Task.FromResult(SecretResponse(request));
            }
        );
        var reader = Reader(factory);
        await reader.ReadVerifyTokenAsync(CancellationToken.None);
        await reader.ReadAppSecretAsync(CancellationToken.None);
        await reader.ReadSenderBindingAsync(CancellationToken.None);
        Assert.Equal(6, paths.Count);
        Assert.Single(
            paths,
            value => value.Contains("/whatsapp-verify-token/", StringComparison.Ordinal)
        );
        Assert.Single(
            paths,
            value => value.Contains("/whatsapp-app-secret/", StringComparison.Ordinal)
        );
        Assert.Single(
            paths,
            value => value.Contains("/whatsapp-provider-binding/", StringComparison.Ordinal)
        );
        Assert.DoesNotContain(
            paths,
            value =>
                value.Contains("outbound", StringComparison.Ordinal)
                || value.Contains("media", StringComparison.Ordinal)
        );
    }

    [Fact]
    public async Task ProtectedVerificationDoesNotRequireBusinessActivationOrLegacyIdentityKeys()
    {
        var context = await Wc120FitnessContext.CreateAsync();
        var options = new WhatsAppJourneyOptions
        {
            VerificationEnabled = true,
            CallbackHost = "whatsapp.demo.example",
        };
        var protectedSecrets = new WebhookCredentials();
        var service = new WhatsAppJourneyService(
            context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(options),
            webhookCredentials: protectedSecrets
        );
        var controller = new WhatsAppJourneyController(
            service,
            Options.Create(options),
            Options.Create(new Wc120ConversationOptions()),
            webhookCredentials: protectedSecrets
        )
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() },
        };
        controller.Request.Host = new HostString(options.CallbackHost);
        controller.Request.QueryString = new QueryString(
            "?hub.mode=subscribe&hub.verify_token="
                + new string('v', 32)
                + "&hub.challenge=challenge"
        );
        var response = await controller.VerifyAsync(CancellationToken.None);
        Assert.Equal("challenge", Assert.IsType<ContentResult>(response).Content);
        Assert.Equal(1, protectedSecrets.VerifyReads);
        Assert.Equal(0, protectedSecrets.AppReads);
        Assert.Equal(
            503,
            Assert
                .IsType<StatusCodeResult>(await controller.ReceiveAsync(CancellationToken.None))
                .StatusCode
        );
        await using var db = context.Relationships.CreateDbContext();
        Assert.Empty(await db.WhatsAppJourneyContacts.ToListAsync());
    }

    [Fact]
    public async Task AppSecretRotationUsesFreshSignatureAuthorityWithoutLegacyIdentityKey()
    {
        var fixture = await SeedAsync();
        var secrets = new WebhookCredentials();
        var service = new WhatsAppJourneyService(
            fixture.Context.Relationships,
            new ForbiddenEvidence(),
            Options.Create(new WhatsAppJourneyOptions()),
            conversationDbFactory: fixture.Context.Conversations,
            conversationOptions: Options.Create(fixture.Context.Options),
            outboxService: fixture.Context.Outbox(),
            webhookCredentials: secrets
        );
        var body = Encoding.UTF8.GetBytes(
            JsonSerializer.Serialize(
                new
                {
                    @object = "whatsapp_business_account",
                    entry = new[]
                    {
                        new
                        {
                            id = "1002",
                            changes = new[]
                            {
                                new
                                {
                                    value = new
                                    {
                                        metadata = new { phone_number_id = "1003" },
                                        statuses = new[]
                                        {
                                            new
                                            {
                                                id = "wamid.synthetic",
                                                status = "delivered",
                                                timestamp = Now.ToUnixTimeSeconds().ToString(),
                                            },
                                        },
                                    },
                                },
                            },
                        },
                    },
                }
            )
        );
        static string Sign(byte[] bytes, string key) =>
            "sha256="
            + Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.UTF8.GetBytes(key), bytes));
        var originalSignature = Sign(body, secrets.AppSecret);
        await service.ReceiveAsync(body, originalSignature, Now, CancellationToken.None);
        secrets.AppSecret = new string('r', 32);
        await Assert.ThrowsAsync<WhatsAppWebhookException>(() =>
            service.ReceiveAsync(body, originalSignature, Now, CancellationToken.None)
        );
        await service.ReceiveAsync(
            body,
            Sign(body, secrets.AppSecret),
            Now,
            CancellationToken.None
        );
        Assert.Equal(3, secrets.AppReads);
        await using var db = fixture.Context.Relationships.CreateDbContext();
        var unchanged = Assert.Single(await db.WhatsAppJourneyContacts.ToListAsync());
        Assert.Equal(Recipient, unchanged.PhoneHmac);
        Assert.Equal(Now, unchanged.LastInboundAt);
        Assert.Null(unchanged.OptedOutAt);
    }

    [Theory]
    [InlineData("Approved static body", "Approved static body", 0)]
    [InlineData("Report: {{1}}", "Report: ready", 1)]
    [InlineData("Report {{1}} for {{2}}.", "Report ready for review.", 2)]
    public void ApprovedTemplateProjectionPreservesExactCanonicalContent(
        string body,
        string canonical,
        int expected
    )
    {
        var projection = new WhatsAppTemplateProjection { Body = body };
        var parameters = projection.Project(canonical);
        Assert.Equal(expected, parameters.Length);
        for (var index = 0; index < parameters.Length; index++)
            body = body.Replace(
                "{{" + (index + 1) + "}}",
                parameters[index],
                StringComparison.Ordinal
            );
        Assert.Equal(canonical, body);
    }

    [Theory]
    [InlineData("Approved static body", "Different body")]
    [InlineData("Report: {{2}}", "Report: ready")]
    [InlineData("{{1}}{{2}}", "ambiguous")]
    [InlineData("Report: {{x}}", "Report: ready")]
    [InlineData("Report: {{1}}", "Report: line\nbreak")]
    public void InvalidTemplateProjectionCannotSilentlyRewriteOrDiscardCanonicalContent(
        string body,
        string canonical
    )
    {
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() =>
            new WhatsAppTemplateProjection { Body = body }.Project(canonical)
        );
    }

    [Fact]
    public async Task HttpAcceptanceIsNotDeliveryAndReservesBudgetDurably()
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            async (request, token) =>
            {
                calls++;
                Assert.Equal("graph.facebook.com", request.RequestUri!.Host);
                Assert.Equal("Bearer", request.Headers.Authorization?.Scheme);
                using var body = JsonDocument.Parse(
                    await request.Content!.ReadAsStringAsync(token)
                );
                Assert.Equal(
                    "whatsapp",
                    body.RootElement.GetProperty("messaging_product").GetString()
                );
                Assert.Equal(
                    "Canonical shared-API reply",
                    body.RootElement.GetProperty("text").GetProperty("body").GetString()
                );
                Assert.Equal(
                    fixture.Request.OutboxId.ToString("D"),
                    body.RootElement.GetProperty("biz_opaque_callback_data").GetString()
                );
                return Json(new { messages = new[] { new { id = "wamid.synthetic" } } });
            }
        );
        var adapter = Adapter(fixture, factory);
        var result = await adapter.DispatchAsync(fixture.Request, CancellationToken.None);
        Assert.Equal("PROVIDER_ACCEPTED", result.State);
        Assert.Equal(Hash("wamid.synthetic"), result.ProviderReferenceDigest);
        Assert.Equal(1, calls);
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Single(await db.Set<WhatsAppTrafficReservation>().ToListAsync());
        Assert.Equal("DISPATCHING", (await db.ConversationOutbox.SingleAsync()).State);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            adapter.DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal(1, calls);
    }

    [Fact]
    public async Task ProviderAcceptedOutboxWaitsForDeliveryAndNeverBecomesDeliveredFromHttpAlone()
    {
        var fixture = await SeedAsync();
        var outbox = fixture.Context.Outbox();
        await outbox.RecordResultAsync(
            fixture.Request.OutboxId,
            "fixture",
            new("PROVIDER_ACCEPTED", Hash("wamid.synthetic"), Hash("submission"), Now),
            CancellationToken.None
        );
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            Assert.Equal("UNRESOLVED", (await db.ConversationOutbox.SingleAsync()).State);
            Assert.Equal(
                "PROVIDER_ACCEPTED",
                (await db.DeliveryObservations.SingleAsync()).DeliveryState
            );
        }
        Assert.True(
            await outbox.RecordProviderStatusAsync(
                new(
                    "delivered-event",
                    "wamid.synthetic",
                    "delivered",
                    Now.AddSeconds(1),
                    Hash("callback")
                ),
                CancellationToken.None
            )
        );
        using var factory = new ClientFactory(
            (_, _) => throw new InvalidOperationException("Reconciliation must not send.")
        );
        Assert.Equal(
            "DELIVERED",
            (
                await Adapter(fixture, factory)
                    .ReconcileAsync(fixture.Request, CancellationToken.None)
            ).State
        );
    }

    [Fact]
    public async Task SignedOpaqueCorrelationRecoversLostSubmissionResponseWithoutResend()
    {
        var fixture = await SeedAsync();
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        await budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None);
        var outbox = fixture.Context.Outbox();
        await outbox.RecordResultAsync(
            fixture.Request.OutboxId,
            "fixture",
            new("UNKNOWN", Hash("unknown"), Hash("submission"), Now),
            CancellationToken.None
        );
        var status = new WhatsAppProviderStatusEvent(
            "delivered-event",
            "wamid.synthetic",
            "delivered",
            Now.AddSeconds(1),
            Hash("callback")
        )
        {
            OutboxId = fixture.Request.OutboxId,
        };
        Assert.True(await outbox.RecordProviderStatusAsync(status, CancellationToken.None));
        Assert.True(await outbox.RecordProviderStatusAsync(status, CancellationToken.None));
        await using var db = fixture.Context.Conversations.CreateDbContext();
        Assert.Single(
            await db
                .DeliveryObservations.Where(value => value.DeliveryState == "DELIVERED")
                .ToListAsync()
        );
        Assert.Equal("UNRESOLVED", (await db.ConversationOutbox.SingleAsync()).State);
        using var factory = new ClientFactory(
            (_, _) => throw new InvalidOperationException("Reconciliation must not send.")
        );
        Assert.Equal(
            "DELIVERED",
            (
                await Adapter(fixture, factory)
                    .ReconcileAsync(fixture.Request, CancellationToken.None)
            ).State
        );
    }

    [Fact]
    public async Task ApprovedBodyOnlyTemplateUsesExactVersionAndCanonicalParameterProjection()
    {
        var fixture = await SeedAsync("report");
        var channel = new WhatsAppJourneyOptions
        {
            DispatchEnabled = true,
            ApprovedTemplates = ["report:1:en_IN:UTILITY"],
            TemplateProjections =
            [
                new()
                {
                    Name = "report",
                    Version = "1",
                    Locale = "en_IN",
                    Category = "UTILITY",
                    Body = "{{1}}",
                },
            ],
        };
        var calls = 0;
        using var factory = new ClientFactory(
            async (request, token) =>
            {
                calls++;
                using var body = JsonDocument.Parse(
                    await request.Content!.ReadAsStringAsync(token)
                );
                Assert.Equal("template", body.RootElement.GetProperty("type").GetString());
                var template = body.RootElement.GetProperty("template");
                Assert.Equal("report", template.GetProperty("name").GetString());
                Assert.Equal(
                    "en_IN",
                    template.GetProperty("language").GetProperty("code").GetString()
                );
                Assert.Equal(
                    "Canonical shared-API reply",
                    template
                        .GetProperty("components")[0]
                        .GetProperty("parameters")[0]
                        .GetProperty("text")
                        .GetString()
                );
                return Json(new { messages = new[] { new { id = "wamid.synthetic" } } });
            }
        );
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal(0, calls);
        Assert.Equal(
            "PROVIDER_ACCEPTED",
            (
                await Adapter(fixture, factory, channel)
                    .DispatchAsync(fixture.Request, CancellationToken.None)
            ).State
        );
        Assert.Equal(1, calls);
    }

    [Fact]
    public async Task AmbiguousHttpOutcomeIsUnknownAndCannotBlindlyResubmit()
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new HttpRequestException("Synthetic network loss.");
            }
        );
        var adapter = Adapter(fixture, factory);
        var observation = await adapter.DispatchAsync(fixture.Request, CancellationToken.None);
        Assert.Equal("UNKNOWN", observation.State);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            adapter.DispatchAsync(fixture.Request, CancellationToken.None)
        );
        Assert.Equal(1, calls);
    }

    [Fact]
    public async Task BudgetAndRecipientBoundariesDenyBeforeProviderEgress()
    {
        var fixture = await SeedAsync();
        fixture.Options.Authority = fixture.Options.Authority! with
        {
            MaximumMessages = 1,
            MaximumMessagesPerMinute = 1,
        };
        var budget = new WhatsAppTrafficBudget(
            fixture.Context.Conversations,
            fixture.Gate,
            fixture.Clock
        );
        await budget.ReserveAsync(fixture.Request, Recipient, CancellationToken.None);
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            db.ConversationOutbox.Add(
                new()
                {
                    OutboxId = Guid.NewGuid(),
                    TenantId = fixture.Request.TenantId,
                    Environment = "demo",
                    State = "DISPATCHING",
                    AttemptNumber = 1,
                    LeaseExpiresAt = Now.AddMinutes(1),
                }
            );
            await db.SaveChangesAsync();
        }
        await using var check = fixture.Context.Conversations.CreateDbContext();
        var second = await check.ConversationOutbox.SingleAsync(value =>
            value.OutboxId != fixture.Request.OutboxId
        );
        var failure = await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveAsync(
                fixture.Request with
                {
                    OutboxId = second.OutboxId,
                },
                Recipient,
                CancellationToken.None
            )
        );
        Assert.Equal("TRAFFIC_BUDGET_EXHAUSTED", failure.ReasonCode);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            budget.ReserveAsync(
                fixture.Request with
                {
                    TenantId = Guid.NewGuid(),
                },
                Recipient,
                CancellationToken.None
            )
        );
        Assert.Single(await check.Set<WhatsAppTrafficReservation>().ToListAsync());
    }

    [Fact]
    public async Task ExpiryAndStopFencePreventEgressWithoutDiscardingTheCanonicalMessage()
    {
        var fixture = await SeedAsync();
        var calls = 0;
        using var factory = new ClientFactory(
            (_, _) =>
            {
                calls++;
                throw new InvalidOperationException("Network must not be used.");
            }
        );
        fixture.Clock.Now = Now.AddMinutes(1);
        await Assert.ThrowsAsync<WhatsAppCapabilityUnavailableException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );
        fixture.Clock.Now = Now;
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            db.EmergencyStopLatches.Add(
                new()
                {
                    Environment = "demo",
                    TenantId = fixture.Request.TenantId,
                    RelationshipId = fixture.Request.RelationshipId,
                    State = "LATCHED",
                }
            );
            await db.SaveChangesAsync();
        }
        await Assert.ThrowsAsync<ConversationStoppedException>(() =>
            Adapter(fixture, factory).DispatchAsync(fixture.Request, CancellationToken.None)
        );
        await using var check = fixture.Context.Conversations.CreateDbContext();
        Assert.Single(await check.Messages.ToListAsync());
        Assert.Empty(await check.Set<WhatsAppTrafficReservation>().ToListAsync());
        Assert.Equal(0, calls);
    }

    [Theory]
    [InlineData("PROVIDER_ACCEPTED", "UNKNOWN")]
    [InlineData("DELIVERED", "DELIVERED")]
    [InlineData("READ", "DELIVERED")]
    [InlineData("FAILED", "REJECTED")]
    public async Task ReconciliationUsesSharedDeliveryEvidenceAndNeverSendsAgain(
        string state,
        string expected
    )
    {
        var fixture = await SeedAsync();
        await using (var db = fixture.Context.Conversations.CreateDbContext())
        {
            var message = await db.Messages.SingleAsync();
            db.DeliveryObservations.Add(
                new()
                {
                    Environment = "demo",
                    TenantId = fixture.Request.TenantId,
                    RelationshipId = fixture.Request.RelationshipId,
                    MessageId = message.MessageId,
                    Provider = "WHATSAPP",
                    ProviderEventIdentity = Hash("status"),
                    ProviderReferenceDigest = Hash("provider"),
                    DeliveryState = state,
                    ObservationDigest = Hash("observation"),
                    ObservedAt = Now,
                    RetainUntil = Now.AddYears(7),
                }
            );
            await db.SaveChangesAsync();
        }
        using var factory = new ClientFactory(
            (_, _) => throw new InvalidOperationException("Reconciliation must not send.")
        );
        var observation = await Adapter(fixture, factory)
            .ReconcileAsync(fixture.Request, CancellationToken.None);
        Assert.Equal(expected, observation.State);
    }

    [Fact]
    public async Task TenantExecutionScopeDoesNotLeakAcrossAsyncFlowsAndCanOnlyUseAuthorityTenant()
    {
        var fixture = await SeedAsync();
        var scope = new WhatsAppTenantExecutionScope(fixture.Gate, fixture.Clock);
        Assert.Null(scope.CurrentTenantId);
        await Task.Run(async () =>
        {
            using var tenant = scope.Begin();
            Assert.Equal(fixture.Request.TenantId, scope.CurrentTenantId);
            Assert.Throws<InvalidOperationException>(() => scope.Begin());
            await Task.Yield();
            Assert.Equal(fixture.Request.TenantId, scope.CurrentTenantId);
        });
        Assert.Null(scope.CurrentTenantId);
        fixture.Options.Revoked = true;
        Assert.Throws<WhatsAppCapabilityUnavailableException>(() => scope.Begin());
        Assert.Null(scope.CurrentTenantId);
    }

    private sealed record Fixture(
        Wc120FitnessContext Context,
        WhatsAppCapabilityOptions Options,
        WhatsAppCapabilityGate Gate,
        Clock Clock,
        WhatsAppProviderDispatchRequest Request
    );

    private static async Task<Fixture> SeedAsync(string? template = null)
    {
        var context = await Wc120FitnessContext.CreateAsync();
        context.Options.Environment = "demo";
        context.Options.AppBindingDigest = Hash("1001");
        context.Options.WabaBindingDigest = Hash("1002");
        context.Options.RecipientBindingDigest = Hash("1003");
        await context.SeedWhatsAppEligibilityAsync(Recipient, Now);
        var options = new WhatsAppCapabilityOptions
        {
            Configured = true,
            ProviderAvailable = true,
            Environment = "demo",
            ReleaseDigest = TupleDigest,
            ConfigurationDigest = TupleDigest,
            CatalogDigest = TupleDigest,
            RollbackDigest = TupleDigest,
            Authority = new()
            {
                ActivationReference = "FA:demo",
                ExternalTrafficReference = "FA:traffic",
                ConsentReference = "consent:fixture",
                IncidentOwnerReference = "office:operations",
                AlertRouteReference = "alert:fixture",
                Environment = "demo",
                ReleaseDigest = TupleDigest,
                ConfigurationDigest = TupleDigest,
                CatalogDigest = TupleDigest,
                RollbackDigest = TupleDigest,
                TenantId = context.TenantId,
                RecipientBindingDigest = Recipient,
                StartsAt = Now,
                ExpiresAt = Now.AddMinutes(1),
                MaximumMessages = 10,
                MaximumMessagesPerMinute = 5,
                MaximumSpendInr = 100,
                MaximumCostPerMessageInr = 10,
            },
        };
        var gate = new WhatsAppCapabilityGate(
            new StaticOptionsMonitor<WhatsAppCapabilityOptions>(options)
        );
        var clock = new Clock { Now = Now };
        await using var db = context.Conversations.CreateDbContext();
        var message = new ConversationMessage
        {
            Environment = "demo",
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            ConversationId = Guid.NewGuid(),
            Sequence = 1,
            ContentJson = JsonSerializer.Serialize(
                new[] { new ConversationTextBlockV1("1.0", "TEXT", "Canonical shared-API reply") }
            ),
        };
        var outbox = new ConversationOutboxRecord
        {
            Environment = "demo",
            TenantId = context.TenantId,
            RelationshipId = context.RelationshipId,
            ConversationId = message.ConversationId,
            Sequence = 1,
            AggregateId = message.MessageId.ToString("D"),
            RecipientBindingDigest = Recipient,
            TemplateName = template,
            TemplateVersion = template is null ? null : "1",
            TemplateLocale = template is null ? null : "en_IN",
            TemplateCategory = template is null ? null : "UTILITY",
            PayloadReference = "payload:fixture",
            PayloadDigest = Hash("payload"),
            CreatedAt = Now,
            UpdatedAt = Now,
            State = "DISPATCHING",
            AttemptNumber = 1,
            LeaseOwner = "fixture",
            LeaseExpiresAt = Now.AddSeconds(60),
        };
        db.Messages.Add(message);
        db.ConversationOutbox.Add(outbox);
        await db.SaveChangesAsync();
        return new(
            context,
            options,
            gate,
            clock,
            new(
                outbox.OutboxId,
                "demo",
                context.TenantId,
                context.RelationshipId,
                message.ConversationId,
                1,
                outbox.PayloadReference,
                outbox.PayloadDigest,
                1
            )
        );
    }

    private static WhatsAppCloudProviderAdapter Adapter(
        Fixture fixture,
        ClientFactory factory,
        WhatsAppJourneyOptions? channel = null,
        IWhatsAppProviderCredentials? credentials = null
    ) =>
        new(
            factory,
            credentials ?? new Credentials(),
            fixture.Gate,
            fixture.Context.Conversations,
            fixture.Context.StopFence,
            fixture.Context.Outbox(channel),
            new WhatsAppTrafficBudget(fixture.Context.Conversations, fixture.Gate, fixture.Clock),
            fixture.Clock,
            new StaticOptionsMonitor<WhatsAppJourneyOptions>(
                channel ?? new WhatsAppJourneyOptions { DispatchEnabled = true }
            ),
            Options.Create(fixture.Context.Options)
        );

    private static WhatsAppKeyVaultCredentials Reader(
        ClientFactory factory,
        WhatsAppProviderOptions? options = null,
        string endpoint = "http://127.0.0.1:8080/msi/token"
    ) =>
        new(
            factory,
            new StaticOptionsMonitor<WhatsAppProviderOptions>(options ?? ProviderOptions()),
            new ConfigurationBuilder()
                .AddInMemoryCollection(
                    new Dictionary<string, string?>
                    {
                        ["IDENTITY_ENDPOINT"] = endpoint,
                        ["IDENTITY_HEADER"] = "synthetic-identity-header",
                    }
                )
                .Build(),
            new Clock { Now = Now }
        );

    private static WhatsAppProviderOptions ProviderOptions() =>
        new()
        {
            Enabled = true,
            Environment = "demo",
            VaultHost = "kv-waooaw-demo.vault.azure.net",
            ManagedIdentityClientId = Guid.NewGuid().ToString("D"),
            BindingVersion = new string('a', 32),
            OutboundAuthorityVersion = new string('b', 32),
            VerifyTokenVersion = new string('c', 32),
            AppSecretVersion = new string('d', 32),
        };

    private static HttpResponseMessage SecretResponse(
        HttpRequestMessage request,
        string? failure = null
    )
    {
        if (failure == "redirect")
        {
            var redirect = new HttpResponseMessage(HttpStatusCode.Redirect);
            redirect.Headers.Location = new Uri("https://example.invalid/denied");
            return redirect;
        }
        if (failure == "oversized")
            return new(HttpStatusCode.OK) { Content = new StringContent(new string('x', 65_537)) };
        if (failure == "wrong-shape")
            return Json(Array.Empty<string>());
        if (request.RequestUri!.IsLoopback)
            return Json(
                new
                {
                    access_token = new string('t', 40),
                    resource = failure == "wrong-resource"
                        ? "https://example.invalid"
                        : "https://vault.azure.net",
                }
            );
        var value = request.RequestUri.AbsolutePath.Contains(
            "whatsapp-provider-binding",
            StringComparison.Ordinal
        )
            ? JsonSerializer.Serialize(
                Binding(),
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            )
            : new string('p', 40);
        return Json(
            new
            {
                id = failure == "wrong-version"
                    ? "https://example.invalid/denied"
                    : request.RequestUri.GetLeftPart(UriPartial.Path),
                value,
                attributes = new
                {
                    enabled = failure != "disabled",
                    exp = (failure == "expired" ? Now : Now.AddHours(1)).ToUnixTimeSeconds(),
                    nbf = (failure == "future" ? Now.AddMinutes(1) : Now).ToUnixTimeSeconds(),
                },
            }
        );
    }

    private static WhatsAppProviderBinding Binding() =>
        new()
        {
            Environment = "demo",
            BindingVersion = "fixture-1",
            AppId = "1001",
            WabaId = "1002",
            PhoneNumberId = "1003",
            RecipientPhoneNumber = string.Concat("+", "44", new string('7', 10)),
            RecipientBindingDigest = Recipient,
            ApiVersion = "v25.0",
            AuthorityReference = "FA:provider",
            ValidFrom = Now,
            ExpiresAt = Now.AddHours(1),
        };

    private sealed class Credentials(Func<Task>? beforeReturn = null) : IWhatsAppProviderCredentials
    {
        public async Task<WhatsAppProviderCredentials> ReadAsync(
            CancellationToken cancellationToken
        )
        {
            if (beforeReturn is not null)
                await beforeReturn();
            return new WhatsAppProviderCredentials
            {
                Binding = Binding(),
                AccessToken = new string('p', 40),
                ValidUntil = Now.AddMinutes(5),
            };
        }
    }

    private sealed class WebhookCredentials : IWhatsAppWebhookCredentials
    {
        public int VerifyReads { get; private set; }
        public int AppReads { get; private set; }
        public string AppSecret { get; set; } = new('s', 32);

        public Task<string> ReadVerifyTokenAsync(CancellationToken cancellationToken)
        {
            VerifyReads++;
            return Task.FromResult(new string('v', 32));
        }

        public Task<string> ReadAppSecretAsync(CancellationToken cancellationToken)
        {
            AppReads++;
            return Task.FromResult(AppSecret);
        }

        public Task<WhatsAppProviderBinding> ReadSenderBindingAsync(
            CancellationToken cancellationToken
        ) => Task.FromResult(Binding());
    }

    private sealed class ForbiddenEvidence : IWhatsAppRegistrationEvidenceGateway
    {
        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken cancellationToken
        ) => throw new InvalidOperationException("No registration evidence effect is permitted.");
    }

    private sealed class Clock : TimeProvider
    {
        public DateTimeOffset Now { get; set; }

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private sealed class ClientFactory(
        Func<HttpRequestMessage, CancellationToken, Task<HttpResponseMessage>> send
    ) : HttpMessageHandler, IHttpClientFactory
    {
        public HttpClient CreateClient(string name) =>
            new(this, disposeHandler: false) { Timeout = TimeSpan.FromSeconds(15) };

        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => send(request, cancellationToken);
    }

    private static HttpResponseMessage Json<T>(T value) =>
        new(HttpStatusCode.OK)
        {
            Content = new StringContent(
                JsonSerializer.Serialize(value),
                Encoding.UTF8,
                "application/json"
            ),
        };

    private static string Hash(string value) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
