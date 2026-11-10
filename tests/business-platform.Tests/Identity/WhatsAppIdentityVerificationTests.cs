using System.Net;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class WhatsAppIdentityVerificationTests
{
    private static readonly DateTimeOffset Now = DateTimeOffset.UtcNow;

    [Fact]
    public async Task DisabledTemplate_DoesNotReadCredentialsOrCallProvider()
    {
        var fixture = new Fixture();
        fixture.Options.Enabled = false;
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Verifier.VerifyAsync(CancellationToken.None)
        );
        Assert.Equal(0, fixture.Credentials.Reads);
        Assert.Equal(0, fixture.Handler.Requests);
    }

    [Fact]
    public async Task ApprovedCopyCodeTemplate_IsReadFromTheConfiguredBusinessAccount()
    {
        var fixture = new Fixture();
        var verified = await fixture.Verifier.VerifyAsync(CancellationToken.None);
        Assert.Equal("waooaw_registration_otp", verified.Name);
        Assert.Equal("en_US", verified.Locale);
        Assert.Equal(1, fixture.Handler.Requests);
        Assert.Equal(0, fixture.Handler.Sends);
    }

    [Theory]
    [InlineData("MARKETING", "APPROVED", "en_US", 15, "COPY_CODE")]
    [InlineData("AUTHENTICATION", "PENDING", "en_US", 15, "COPY_CODE")]
    [InlineData("AUTHENTICATION", "REJECTED", "en_US", 15, "COPY_CODE")]
    [InlineData("AUTHENTICATION", "APPROVED", "en", 15, "COPY_CODE")]
    [InlineData("AUTHENTICATION", "APPROVED", "en_US", 5, "COPY_CODE")]
    [InlineData("AUTHENTICATION", "APPROVED", "en_US", 15, "ONE_TAP")]
    public async Task UnapprovedOrMismatchedTemplate_FailsClosed(
        string category,
        string status,
        string locale,
        int expiry,
        string button
    )
    {
        var fixture = new Fixture();
        fixture.Handler.Metadata = Metadata(category, status, locale, expiry, button);
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Verifier.VerifyAsync(CancellationToken.None)
        );
        Assert.Equal(0, fixture.Handler.Sends);
    }

    [Theory]
    [InlineData("{{2}}")]
    [InlineData("{{3}}")]
    [InlineData("{{100}}")]
    public async Task TemplateWithAdditionalBodyParameter_IsRejected(string parameter)
    {
        var fixture = new Fixture();
        fixture.Handler.Metadata = Metadata(bodySuffix: parameter);
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Verifier.VerifyAsync(CancellationToken.None)
        );
        Assert.Equal(0, fixture.Handler.Sends);
    }

    [Fact]
    public async Task RegistrationDispatch_UsesOnlyTheVerifiedTemplateAndReservesBeforeSend()
    {
        var fixture = new Fixture();
        await fixture.Dispatcher.DispatchRegistrationMobileAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Now.AddMinutes(10),
            "+14155550100",
            "123456",
            CancellationToken.None
        );
        Assert.Equal(1, fixture.Budget.Reservations);
        Assert.Equal(1, fixture.Handler.Sends);
        Assert.Null(fixture.Scope.CurrentTenantId);
    }

    [Fact]
    public async Task GenericMobileDispatch_CannotInitiateATemplate()
    {
        var fixture = new Fixture();
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Dispatcher.DispatchAsync(
                IdentityVerificationPurpose.Mobile,
                "+14155550100",
                "123456",
                CancellationToken.None
            )
        );
        Assert.Equal(0, fixture.Handler.Requests);
        Assert.Equal(0, fixture.Budget.Reservations);
    }

    [Fact]
    public async Task MissingOtpAuthority_PreventsTemplateReadAndEgress()
    {
        var fixture = new Fixture();
        fixture.Gate.Authority = fixture.Gate.Authority with
        {
            AllowRegistrationVerification = false,
        };
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Dispatcher.DispatchRegistrationMobileAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Now.AddMinutes(10),
                "+14155550100",
                "123456",
                CancellationToken.None
            )
        );
        Assert.Equal(0, fixture.Handler.Requests);
        Assert.Equal(0, fixture.Budget.Reservations);
    }

    [Fact]
    public async Task PilotAuthority_CannotSendToAnotherNumber()
    {
        var fixture = new Fixture();
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Dispatcher.DispatchRegistrationMobileAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Now.AddMinutes(10),
                "+14155550101",
                "123456",
                CancellationToken.None
            )
        );
        Assert.Equal(0, fixture.Handler.Sends);
        Assert.Equal(0, fixture.Budget.Reservations);
    }

    [Fact]
    public async Task AuthorityChangeAfterReservation_PreventsProviderSend()
    {
        var fixture = new Fixture();
        fixture.Budget.BeforeReturn = () =>
            fixture.Gate.Authority = fixture.Gate.Authority with
            {
                ActivationReference = "changed",
            };
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Dispatcher.DispatchRegistrationMobileAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Now.AddMinutes(10),
                "+14155550100",
                "123456",
                CancellationToken.None
            )
        );
        Assert.Equal(1, fixture.Budget.Reservations);
        Assert.Equal(0, fixture.Handler.Sends);
        Assert.Null(fixture.Scope.CurrentTenantId);
    }

    [Fact]
    public async Task UnknownProviderOutcome_IsNotRetriedOrReportedAsSubmitted()
    {
        var fixture = new Fixture();
        fixture.Handler.SendResponse = "{}";
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Dispatcher.DispatchRegistrationMobileAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Now.AddMinutes(10),
                "+14155550100",
                "123456",
                CancellationToken.None
            )
        );
        Assert.Equal(1, fixture.Handler.Sends);
        Assert.Equal(1, fixture.Budget.Reservations);
    }

    [Theory]
    [InlineData("null")]
    [InlineData("[]")]
    [InlineData("""{"data":{}}""")]
    [InlineData("""{"data":[null]}""")]
    [InlineData("{")]
    public async Task MalformedTemplateReadback_IsAnExplicitDeliveryDenial(string metadata)
    {
        var fixture = new Fixture();
        fixture.Handler.Metadata = metadata;
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Verifier.VerifyAsync(CancellationToken.None)
        );
        Assert.Equal(0, fixture.Handler.Sends);
    }

    [Fact]
    public async Task ProtectedAccountChangeAfterReadback_PreventsReservationAndSend()
    {
        var fixture = new Fixture();
        fixture.Credentials.ChangeBindingOnSecondRead = true;
        await Assert.ThrowsAsync<IdentityDeliveryUnavailableException>(() =>
            fixture.Dispatcher.DispatchRegistrationMobileAsync(
                Guid.NewGuid(),
                Guid.NewGuid(),
                Now.AddMinutes(10),
                "+14155550100",
                "123456",
                CancellationToken.None
            )
        );
        Assert.Equal(0, fixture.Handler.Sends);
        Assert.Equal(0, fixture.Budget.Reservations);
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task FailedOrInterruptedDispatch_IsDurableAndCannotRedispatchOrConfirm(
        bool cancelled
    )
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var dispatcher = new InterruptedDispatcher(factory, cancelled);
        var controller = IdentityTestHelpers.CreateControllerWithDispatcher(
            factory,
            dispatcher,
            subject: "dispatch-owner",
            identityProvider: "google"
        );
        var registration = Assert.IsType<ObjectResult>(
            await controller.StartRegistrationAsync(new("en"), CancellationToken.None)
        );
        var registrationId = JsonSerializer
            .SerializeToElement(registration.Value)
            .GetProperty("RegistrationId")
            .GetGuid();
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        if (cancelled)
            await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
                controller.StartRegistrationMobileVerificationAsync(
                    registrationId,
                    new("+14155550100"),
                    CancellationToken.None
                )
            );
        else
            Assert.Equal(
                503,
                Assert
                    .IsType<ObjectResult>(
                        await controller.StartRegistrationMobileVerificationAsync(
                            registrationId,
                            new("+14155550100"),
                            CancellationToken.None
                        )
                    )
                    .StatusCode
            );
        var replay = Assert.IsType<ObjectResult>(
            await controller.StartRegistrationMobileVerificationAsync(
                registrationId,
                new("+14155550100"),
                CancellationToken.None
            )
        );
        Assert.Equal(503, replay.StatusCode);
        Assert.Equal(1, dispatcher.Attempts);
        await using var db = factory.CreateDbContext();
        var challenge = Assert.Single(db.VerificationChallenges);
        Assert.Equal(cancelled ? "DISPATCHING" : "UNAVAILABLE", challenge.DeliveryState);
        Assert.NotEqual(dispatcher.Code, challenge.CodeHmac);
        IdentityTestHelpers.RefreshIdempotencyKey(controller);
        var confirmation = Assert.IsType<ObjectResult>(
            await controller.ConfirmRegistrationMobileVerificationAsync(
                registrationId,
                new(challenge.ChallengeId, dispatcher.Code!),
                CancellationToken.None
            )
        );
        Assert.Equal(410, confirmation.StatusCode);
        Assert.False((await db.Registrations.FindAsync(registrationId))!.MobileVerified);
    }

    private static string Metadata(
        string category = "AUTHENTICATION",
        string status = "APPROVED",
        string locale = "en_US",
        int expiry = 15,
        string button = "COPY_CODE",
        string bodySuffix = ""
    ) =>
        JsonSerializer.Serialize(
            new
            {
                data = new[]
                {
                    new
                    {
                        id = "1476143084372706",
                        name = "waooaw_registration_otp",
                        language = locale,
                        category,
                        status,
                        components = new object[]
                        {
                            new
                            {
                                type = "BODY",
                                text = $"{{{{1}}}} is your verification code. For your security, do not share this code. {bodySuffix}",
                            },
                            new
                            {
                                type = "FOOTER",
                                text = $"This code expires in {expiry} minutes.",
                            },
                            new
                            {
                                type = "BUTTONS",
                                buttons = new[]
                                {
                                    new
                                    {
                                        type = "URL",
                                        text = "Copy code",
                                        url = $"https://www.whatsapp.com/otp/code/?otp_type={button}&code=otp{{{{1}}}}",
                                    },
                                },
                            },
                        },
                    },
                },
            }
        );

    private sealed class Fixture
    {
        public WhatsAppAuthenticationTemplateOptions Options { get; } =
            new()
            {
                Enabled = true,
                TemplateId = "1476143084372706",
                TemplateName = "waooaw_registration_otp",
                Locale = "en_US",
                ApprovalReference = "synthetic:approval",
            };
        public Credentials Credentials { get; } = new();
        public Handler Handler { get; } = new();
        public Gate Gate { get; } = new();
        public Budget Budget { get; }
        public WhatsAppTenantExecutionScope Scope { get; }
        public WhatsAppAuthenticationTemplateVerifier Verifier { get; }
        public WhatsAppIdentityVerificationDispatcher Dispatcher { get; }

        public Fixture()
        {
            var monitor = new Monitor(Options);
            var clients = new Clients(Handler);
            var clock = new Clock();
            Budget = new(Gate);
            Scope = new(Gate, clock);
            Verifier = new(clients, Credentials, monitor, clock);
            Dispatcher = new(clients, Credentials, Verifier, Budget, Gate, Scope, monitor, clock);
            Handler.BeforeSend = () => Assert.Equal(1, Budget.Reservations);
        }
    }

    private sealed class Clock : TimeProvider
    {
        public override DateTimeOffset GetUtcNow() => Now;
    }

    private sealed class Monitor(WhatsAppAuthenticationTemplateOptions value)
        : IOptionsMonitor<WhatsAppAuthenticationTemplateOptions>
    {
        public WhatsAppAuthenticationTemplateOptions CurrentValue => value;

        public WhatsAppAuthenticationTemplateOptions Get(string? name) => value;

        public IDisposable? OnChange(
            Action<WhatsAppAuthenticationTemplateOptions, string?> listener
        ) => null;
    }

    private sealed class Gate : IWhatsAppCapabilityGate
    {
        public WhatsAppActivationAuthority Authority { get; set; } =
            new()
            {
                TenantId = Guid.NewGuid(),
                Environment = "demo",
                RecipientBindingDigest = new string('a', 64),
                AllowRegistrationVerification = true,
            };

        public WhatsAppCapabilityState Evaluate(DateTimeOffset now) => new("ACTIVE", "AUTHORIZED");

        public WhatsAppActivationAuthority RequireActive(DateTimeOffset now) => Authority;

        public void RequireRecipient(
            Guid tenantId,
            string recipientBindingDigest,
            DateTimeOffset now
        )
        {
            Assert.Equal(Authority.TenantId, tenantId);
            Assert.Equal(Authority.RecipientBindingDigest, recipientBindingDigest);
        }
    }

    private sealed class Budget(Gate gate) : IWhatsAppRegistrationVerificationBudget
    {
        public int Reservations { get; private set; }
        public Action? BeforeReturn { get; set; }

        public Task<WhatsAppActivationAuthority> ReserveAsync(
            Guid challengeId,
            CancellationToken ct
        )
        {
            var reserved = gate.Authority;
            Reservations++;
            BeforeReturn?.Invoke();
            return Task.FromResult(reserved);
        }
    }

    private sealed class Credentials : IWhatsAppProviderCredentials
    {
        public int Reads { get; private set; }
        public bool ChangeBindingOnSecondRead { get; set; }

        public Task<WhatsAppProviderCredentials> ReadAsync(CancellationToken cancellationToken)
        {
            Reads++;
            return Task.FromResult(
                new WhatsAppProviderCredentials
                {
                    AccessToken = "synthetic-token",
                    ValidUntil = Now.AddMinutes(5),
                    Binding = new()
                    {
                        Environment = "demo",
                        BindingVersion =
                            ChangeBindingOnSecondRead && Reads > 1 ? "changed" : "synthetic",
                        AppId = "1001",
                        WabaId = "1002",
                        PhoneNumberId = "1003",
                        RecipientPhoneNumber = "+14155550100",
                        RecipientBindingDigest = new string('a', 64),
                        ApiVersion = "v23.0",
                        AuthorityReference = "synthetic:authority",
                        ValidFrom = Now.AddMinutes(-1),
                        ExpiresAt = Now.AddMinutes(30),
                    },
                }
            );
        }
    }

    private sealed class InterruptedDispatcher(
        InMemoryIdentityDbContextFactory factory,
        bool cancelled
    ) : IIdentityVerificationDispatcher
    {
        public int Attempts { get; private set; }
        public string? Code { get; private set; }

        public Task DispatchAsync(
            IdentityVerificationPurpose purpose,
            string destination,
            string code,
            CancellationToken ct
        ) => throw new InvalidOperationException("Registration-specific dispatch is required.");

        public async Task DispatchRegistrationMobileAsync(
            Guid registrationId,
            Guid challengeId,
            DateTimeOffset expiresAt,
            string destination,
            string code,
            CancellationToken ct
        )
        {
            Attempts++;
            Code = code;
            await using var db = factory.CreateDbContext();
            var challenge = await db.VerificationChallenges.FindAsync(challengeId);
            Assert.NotNull(challenge);
            Assert.Equal("DISPATCHING", challenge.DeliveryState);
            Assert.Equal(registrationId, challenge.RegistrationId);
            Assert.Single(
                db.IdempotencyLedger.Where(value =>
                    value.OperationFamily == "StartMobileVerification"
                )
            );
            if (cancelled)
                throw new OperationCanceledException();
            throw new IdentityDeliveryUnavailableException("synthetic:provider-unavailable");
        }
    }

    private sealed class Clients(Handler handler) : IHttpClientFactory
    {
        public HttpClient CreateClient(string name) => new(handler, disposeHandler: false);
    }

    private sealed class Handler : HttpMessageHandler
    {
        public int Requests { get; private set; }
        public int Sends { get; private set; }
        public string Metadata { get; set; } = WhatsAppIdentityVerificationTests.Metadata();
        public string SendResponse { get; set; } = """{"messages":[{"id":"wamid.synthetic"}]}""";
        public Action? BeforeSend { get; set; }

        protected override async Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken ct
        )
        {
            Requests++;
            Assert.Equal("graph.facebook.com", request.RequestUri!.Host);
            Assert.Equal("Bearer", request.Headers.Authorization!.Scheme);
            if (request.Method == HttpMethod.Get)
            {
                Assert.Equal("/v23.0/1002/message_templates", request.RequestUri.AbsolutePath);
                Assert.DoesNotContain("123456", request.RequestUri.Query);
                return new(HttpStatusCode.OK) { Content = new StringContent(Metadata) };
            }
            BeforeSend?.Invoke();
            Sends++;
            Assert.Equal("/v23.0/1003/messages", request.RequestUri.AbsolutePath);
            using var json = JsonDocument.Parse(await request.Content!.ReadAsStringAsync(ct));
            var root = json.RootElement;
            Assert.Equal("template", root.GetProperty("type").GetString());
            Assert.Equal("14155550100", root.GetProperty("to").GetString());
            var template = root.GetProperty("template");
            Assert.Equal("waooaw_registration_otp", template.GetProperty("name").GetString());
            Assert.Equal("en_US", template.GetProperty("language").GetProperty("code").GetString());
            var components = template.GetProperty("components");
            Assert.Equal(2, components.GetArrayLength());
            Assert.Equal("body", components[0].GetProperty("type").GetString());
            Assert.Equal("url", components[1].GetProperty("sub_type").GetString());
            foreach (var component in components.EnumerateArray())
                Assert.Equal(
                    "123456",
                    component.GetProperty("parameters")[0].GetProperty("text").GetString()
                );
            return new(HttpStatusCode.OK) { Content = new StringContent(SendResponse) };
        }
    }
}
