// Implements: work-contracts/WC-133-whatsapp-first-registration-and-web-registration-repair.md R005
// constitutional_basis: C-059, C-063

using System.Net;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.TestHost;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class WhatsAppWebhookHostTests
{
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
