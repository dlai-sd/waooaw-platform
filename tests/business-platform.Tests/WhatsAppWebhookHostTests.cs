// Implements: work-contracts/WC-133-whatsapp-first-registration-and-web-registration-repair.md R005
// constitutional_basis: C-059, C-063

using System.Collections.Concurrent;
using System.Net;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http.Extensions;
using Microsoft.AspNetCore.Http.Features;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Logging;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WhatsAppWebhookHostTests
{
    private const string PrivateToken = "synthetic-private-token-never-log";
    private const string PrivateChallenge = "synthetic-private-challenge-never-log";

    [Theory]
    [InlineData("valid", 200, "CHALLENGE_RETURNED", 3, 1, 1, 1)]
    [InlineData("extra", 401, "QUERY_SHAPE_INVALID", 4, 1, 1, 1)]
    [InlineData("missing", 401, "QUERY_SHAPE_INVALID", 2, 1, 0, 1)]
    [InlineData("duplicate-token", 401, "TOKEN_PARAMETER_INVALID", 3, 1, 2, 1)]
    [InlineData("duplicate-challenge", 401, "CHALLENGE_PARAMETER_INVALID", 3, 1, 1, 2)]
    [InlineData("duplicate-mode", 401, "MODE_PARAMETER_INVALID", 3, 2, 1, 1)]
    [InlineData("wrong-mode", 401, "MODE_MISMATCH", 3, 1, 1, 1)]
    [InlineData("wrong-token", 401, "TOKEN_MISMATCH", 3, 1, 1, 1)]
    [InlineData("empty-token", 401, "TOKEN_PARAMETER_INVALID", 3, 1, 1, 1)]
    [InlineData("large-token", 401, "TOKEN_PARAMETER_INVALID", 3, 1, 1, 1)]
    [InlineData("large-target", 401, "REQUEST_TARGET_TOO_LARGE", 4, 1, 1, 1)]
    [InlineData("wrong-host", 403, "CALLBACK_HOST_MISMATCH", 3, 1, 1, 1)]
    [InlineData("disabled", 503, "VERIFICATION_DISABLED", 3, 1, 1, 1)]
    [InlineData("credential-failure", 503, "CREDENTIAL_UNAVAILABLE", 3, 1, 1, 1)]
    [InlineData("missing-expected", 401, "EXPECTED_TOKEN_UNAVAILABLE", 3, 1, 1, 1)]
    public async Task VerificationDiagnosticsSimulateRequestVariationsWithoutLeakingValues(
        string scenario,
        int status,
        string reason,
        int queries,
        int modes,
        int tokens,
        int challenges
    )
    {
        var logs = new VerificationLogs();
        var credentials = new VerificationCredentials(scenario);
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Logging.AddProvider(logs);
        builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer();
        builder
            .Services.AddControllers()
            .AddApplicationPart(typeof(WhatsAppJourneyController).Assembly);
        builder.Services.Configure<WhatsAppJourneyOptions>(options =>
        {
            options.VerificationEnabled = scenario != "disabled";
            options.CallbackHost = "whatsapp-demo.example.test";
        });
        builder.Services.Configure<Wc120ConversationOptions>(_ => { });
        builder.Services.AddSingleton(new WhatsAppTestFactory().Service);
        builder.Services.AddSingleton<IWhatsAppWebhookCredentials>(credentials);
        await using var app = builder.Build();
        app.Use(
            async (context, next) =>
            {
                context.Features.Get<IHttpRequestFeature>()!.RawTarget =
                    context.Request.GetEncodedPathAndQuery();
                await next();
            }
        );
        app.MapControllers();
        await app.StartAsync();
        using var client = app.GetTestClient();
        client.BaseAddress = new Uri(
            scenario == "wrong-host"
                ? "https://private-unapproved-host.test"
                : "https://whatsapp-demo.example.test"
        );
        var token = scenario switch
        {
            "wrong-token" => "private-wrong-token-never-log",
            "empty-token" => "",
            "large-token" => new string('x', 1025),
            _ => PrivateToken,
        };
        var query =
            $"?hub.mode={(scenario == "wrong-mode" ? "private-wrong-mode" : "subscribe")}"
            + $"&hub.verify_token={token}&hub.challenge={PrivateChallenge}";
        query = scenario switch
        {
            "extra" => query + "&private-unknown-key=private-unknown-value",
            "large-target" => query + "&private-unknown-key=" + new string('x', 8192),
            "missing" => "?hub.mode=subscribe&hub.challenge=" + PrivateChallenge,
            "duplicate-token" => query + "&hub.verify_token=" + PrivateToken,
            "duplicate-mode" => query + "&hub.mode=subscribe",
            "duplicate-challenge" => query + "&hub.challenge=" + PrivateChallenge,
            _ => query,
        };
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            "/api/v1/channels/whatsapp/webhook" + query
        );
        request.Headers.Add("User-Agent", "facebookplatform/1.0");
        request.Headers.Add("Accept", "*/*");
        request.Headers.Add("X-Private-Probe", "private-header-never-log");
        using var response = await client.SendAsync(request);
        Assert.Equal(status, (int)response.StatusCode);
        if (status == 200)
        {
            Assert.Equal(PrivateChallenge, await response.Content.ReadAsStringAsync());
            Assert.Equal("text/plain", response.Content.Headers.ContentType?.MediaType);
        }
        var record = Assert.Single(logs.Records);
        Assert.Equal(status, record["StatusCode"]);
        Assert.Equal(reason, record["Reason"]);
        Assert.Equal(queries, record["QueryCount"]);
        Assert.Equal(modes, record["ModeCount"]);
        Assert.Equal(tokens, record["TokenCount"]);
        Assert.Equal(challenges, record["ChallengeCount"]);
        Assert.Equal(7, record.Count);
        Assert.DoesNotContain(
            "private",
            logs.Formatted.Single(),
            StringComparison.OrdinalIgnoreCase
        );
        if (token.Length > 0)
            Assert.DoesNotContain(token, logs.Formatted.Single(), StringComparison.Ordinal);
        Assert.Equal(
            status == 200
            || reason
                is "TOKEN_MISMATCH"
                    or "CREDENTIAL_UNAVAILABLE"
                    or "EXPECTED_TOKEN_UNAVAILABLE"
                ? 1
                : 0,
            credentials.Reads
        );
    }

    private sealed class VerificationCredentials(string scenario) : IWhatsAppWebhookCredentials
    {
        public int Reads { get; private set; }

        public Task<string> ReadVerifyTokenAsync(CancellationToken cancellationToken)
        {
            Reads++;
            if (scenario == "credential-failure")
                throw new WhatsAppCapabilityUnavailableException("private-exception-never-log");
            return Task.FromResult(scenario == "missing-expected" ? "" : PrivateToken);
        }

        public Task<string> ReadAppSecretAsync(CancellationToken cancellationToken) =>
            throw new InvalidOperationException("Verification must not read the app secret.");

        public Task<WhatsAppProviderBinding> ReadSenderBindingAsync(
            CancellationToken cancellationToken
        ) => throw new InvalidOperationException("Verification must not read the sender binding.");
    }

    private sealed class VerificationLogs : ILoggerProvider
    {
        public ConcurrentQueue<Dictionary<string, object?>> Records { get; } = new();
        public ConcurrentQueue<string> Formatted { get; } = new();

        public ILogger CreateLogger(string categoryName) => new Capture(this, categoryName);

        public void Dispose() { }

        private sealed class Capture(VerificationLogs owner, string category) : ILogger
        {
            public IDisposable? BeginScope<TState>(TState state)
                where TState : notnull => null;

            public bool IsEnabled(LogLevel logLevel) => true;

            public void Log<TState>(
                LogLevel logLevel,
                EventId eventId,
                TState state,
                Exception? exception,
                Func<TState, Exception?, string> formatter
            )
            {
                if (category != typeof(WhatsAppJourneyController).FullName)
                    return;
                Assert.Null(exception);
                var fields = Assert.IsAssignableFrom<IEnumerable<KeyValuePair<string, object?>>>(
                    state
                );
                owner.Records.Enqueue(fields.ToDictionary(pair => pair.Key, pair => pair.Value));
                owner.Formatted.Enqueue(formatter(state, exception));
            }
        }
    }

    [Theory]
    [InlineData(false, "", HttpStatusCode.ServiceUnavailable)]
    [InlineData(true, "", HttpStatusCode.Unauthorized)]
    [InlineData(true, "", HttpStatusCode.Forbidden)]
    [InlineData(
        true,
        "?hub.mode=subscribe&hub.verify_token=synthetic-token&hub.challenge=12345",
        HttpStatusCode.OK
    )]
    [InlineData(
        true,
        "?hub.mode=subscribe&hub.verify_token=wrong&hub.challenge=12345",
        HttpStatusCode.Unauthorized
    )]
    [InlineData(
        true,
        "?hub.mode=subscribe&hub.verify_token=synthetic-token&hub.challenge=1&hub.challenge=2",
        HttpStatusCode.Unauthorized
    )]
    public async Task ActualMvcActivationUsesProductionConstructorAndIndependentVerificationGate(
        bool verification,
        string query,
        HttpStatusCode expected
    )
    {
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseTestServer();
        builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer();
        builder
            .Services.AddControllers()
            .AddApplicationPart(typeof(WhatsAppJourneyController).Assembly);
        builder.Services.Configure<WhatsAppJourneyOptions>(options =>
        {
            options.VerificationEnabled = verification;
            options.CallbackHost = "whatsapp-demo.example.test";
            options.VerifyToken = "synthetic-token";
        });
        builder.Services.Configure<Wc120ConversationOptions>(_ => { });
        var factory = new WhatsAppTestFactory();
        builder.Services.AddSingleton(factory.Service);
        await using var app = builder.Build();
        app.MapControllers();
        await app.StartAsync();
        using var client = app.GetTestClient();
        client.BaseAddress = new Uri(
            expected == HttpStatusCode.Forbidden
                ? "https://unapproved.example.test"
                : "https://whatsapp-demo.example.test"
        );
        using var response = await client.GetAsync("/api/v1/channels/whatsapp/webhook" + query);
        Assert.Equal(expected, response.StatusCode);
        if (expected == HttpStatusCode.OK)
            Assert.Equal("12345", await response.Content.ReadAsStringAsync());
        using var content = new StringContent("{}");
        using var post = await client.PostAsync("/api/v1/channels/whatsapp/webhook", content);
        Assert.Equal(HttpStatusCode.ServiceUnavailable, post.StatusCode);
    }

    private sealed class WhatsAppTestFactory
    {
        public WhatsAppJourneyService Service { get; } =
            new(
                new UnusedEmploymentFactory(),
                new Evidence(),
                Microsoft.Extensions.Options.Options.Create(new WhatsAppJourneyOptions())
            );
    }

    private sealed class UnusedEmploymentFactory
        : IDbContextFactory<EmploymentRelationshipDbContext>
    {
        public EmploymentRelationshipDbContext CreateDbContext() =>
            throw new InvalidOperationException("Verification must not access the database.");
    }

    private sealed class Evidence : IWhatsAppRegistrationEvidenceGateway
    {
        public Task RecordAsync(
            Guid tenantId,
            string messageId,
            string phoneHmac,
            DateTimeOffset occurredAt,
            CancellationToken cancellationToken
        ) => throw new InvalidOperationException("Verification must not admit an identity.");
    }
}
