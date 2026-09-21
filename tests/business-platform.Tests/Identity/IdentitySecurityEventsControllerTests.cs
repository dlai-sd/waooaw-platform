// Implements: work-contracts/WC-103-multitenant-authentication-journeys.md §AUTH-S12
// Constitutional basis: C-002, C-005, C-007, C-027, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentitySecurityEventsControllerTests
{
    private const string SigningKey = "test-only-identity-event-ingest-key-32-bytes";

    [Fact]
    public async Task Receive_ValidSignedWebEventPersistsWithoutClientSelectedBoundary()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var controller = CreateController(factory, EventJson("CALLBACK_SUCCESS"), validSignature: true);

        var result = await controller.ReceiveAsync(CancellationToken.None);

        Assert.IsType<StatusCodeResult>(result);
        await using var db = factory.CreateDbContext();
        var record = Assert.Single(await db.SecurityEvents.ToListAsync());
        Assert.Equal("WEB_APPLICATION", record.SourceBoundary);
        Assert.Equal("CALLBACK_SUCCESS", record.EventType);
        Assert.Null(record.ActorRef);
        Assert.Null(record.SessionRef);
    }

    [Fact]
    public async Task Receive_InvalidSignatureOrNonWebEventFailsWithoutWrite()
    {
        var factory = new InMemoryIdentityDbContextFactory(Guid.NewGuid().ToString("N"));
        var invalidSignature = CreateController(factory, EventJson("CALLBACK_FAILURE"), validSignature: false);
        var forbiddenType = CreateController(factory, EventJson("SESSION_REVOCATION_ALL"), validSignature: true);

        Assert.Equal(403, Assert.IsType<ObjectResult>(
            await invalidSignature.ReceiveAsync(CancellationToken.None)).StatusCode);
        Assert.Equal(400, Assert.IsType<ObjectResult>(
            await forbiddenType.ReceiveAsync(CancellationToken.None)).StatusCode);
        await using var db = factory.CreateDbContext();
        Assert.Empty(await db.SecurityEvents.ToListAsync());
    }

    private static IdentitySecurityEventsController CreateController(
        InMemoryIdentityDbContextFactory factory,
        string body,
        bool validSignature
    )
    {
        var events = new IdentitySecurityEventService(
            factory,
            Options.Create(new IdentityHmacOptions { Key = "test-only-event-reference-key-32-bytes" }),
            Options.Create(new IdentityEnvironmentOptions { Environment = "local" })
        );
        var controller = new IdentitySecurityEventsController(
            events,
            Options.Create(new IdentitySecurityEventIngestOptions { SigningKey = SigningKey })
        );
        var context = new DefaultHttpContext();
        context.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body));
        context.Request.Headers["X-WAOOAW-Identity-Event-Signature"] = validSignature
            ? $"sha256={Convert.ToHexString(HMACSHA256.HashData(Encoding.UTF8.GetBytes(SigningKey), Encoding.UTF8.GetBytes(body)))}"
            : "sha256=00";
        controller.ControllerContext = new ControllerContext { HttpContext = context };
        return controller;
    }

    private static string EventJson(string eventType) => JsonSerializer.Serialize(new
    {
        correlationId = Guid.NewGuid(),
        sourceEventId = $"web:{Guid.NewGuid():N}",
        eventType,
        providerClass = "GOOGLE",
        outcome = "SUCCEEDED",
        reasonCode = "BROKER_CALLBACK_VALID",
        assuranceClass = "AAL2",
        occurredAt = DateTimeOffset.UtcNow,
    });
}