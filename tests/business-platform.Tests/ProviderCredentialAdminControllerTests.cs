// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R002, WC148-R003, WC148-R004
// constitutional_basis: C-023, C-059, C-063, C-083, C-084

using System.Reflection;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.BusinessPlatform.Controllers;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ProviderCredentialAdminControllerTests
{
    private const string Secret = "sk-test-SYNTHETIC-credential-value-0123456789";
    private static readonly Guid ProviderId = Guid.NewGuid();
    private readonly Mock<IProviderCredentialAdminService> _service = new(MockBehavior.Strict);
    private readonly Mock<IProviderGenerationProbe> _probe = new(MockBehavior.Strict);

    private ProviderCredentialAdminController Controller(
        string? role,
        bool stepUp,
        string? body = null,
        bool authenticated = true
    )
    {
        var claims = new List<Claim> { new("participant_id", "founder-1") };
        if (role is not null)
            claims.Add(new("participant_role", role));
        if (stepUp)
        {
            claims.Add(new("amr", "mfa"));
            claims.Add(new("acr", "2"));
            claims.Add(
                new(
                    "auth_time",
                    DateTimeOffset.UtcNow.AddMinutes(-1).ToUnixTimeSeconds().ToString()
                )
            );
        }
        var http = new DefaultHttpContext
        {
            User = new ClaimsPrincipal(
                authenticated ? new ClaimsIdentity(claims, "test") : new ClaimsIdentity()
            ),
        };
        http.Request.Body = new MemoryStream(Encoding.UTF8.GetBytes(body ?? "{}"));
        return new ProviderCredentialAdminController(
            _service.Object,
            _probe.Object,
            NullLogger<ProviderCredentialAdminController>.Instance
        )
        {
            ControllerContext = new ControllerContext { HttpContext = http },
        };
    }

    private static (int Status, JsonElement Body) Problem(IActionResult result)
    {
        var content = result.Should().BeOfType<ContentResult>().Subject;
        content.ContentType.Should().Be("application/problem+json");
        return (content.StatusCode!.Value, JsonDocument.Parse(content.Content!).RootElement);
    }

    private static readonly ProviderCredentialSaved Saved = new(Guid.NewGuid(), 3, "ACTIVE");

    [Fact]
    public void TheControllerIsAnAuthorizedStaffRouteAtTheAdminPath()
    {
        var type = typeof(ProviderCredentialAdminController);

        type.GetCustomAttribute<AuthorizeAttribute>().Should().NotBeNull();
        type.GetCustomAttribute<StaffIdentityRouteAttribute>().Should().NotBeNull();
        type.GetCustomAttribute<RouteAttribute>()!.Template.Should().Be("api/v1/admin/providers");
    }

    [Fact]
    public async Task FounderCanListWithoutStepUp()
    {
        _service
            .Setup(s => s.ListAsync(It.IsAny<CancellationToken>()))
            .ReturnsAsync([
                new ProviderSummary(
                    ProviderId,
                    "openai",
                    "OpenAI",
                    "PLATFORM_LLM",
                    null,
                    "API_KEY",
                    true,
                    true,
                    new("NOT_SET", null, null, null)
                ),
            ]);
        var controller = Controller("founder", stepUp: false);

        var result = await controller.ListAsync(CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
        controller.Response.Headers.CacheControl.ToString().Should().Be("no-store");
        var json = JsonSerializer.Serialize(
            ((OkObjectResult)result).Value,
            new JsonSerializerOptions(JsonSerializerDefaults.Web)
        );
        json.Should()
            .Contain("\"providerName\":\"openai\"")
            .And.Contain("\"hasTestEndpoint\":true");
    }

    [Fact]
    public async Task FounderCanListVersionsWithoutStepUp()
    {
        _service
            .Setup(s => s.ListVersionsAsync(ProviderId, It.IsAny<CancellationToken>()))
            .ReturnsAsync([]);

        var result = await Controller("founder", false)
            .ListVersionsAsync(ProviderId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>();
    }

    [Theory]
    [InlineData("pricing_admin")]
    [InlineData("platform_admin")]
    [InlineData(null)]
    public async Task EveryOperationIsFounderOnlyEvenWithStepUp(string? role)
    {
        var controller = () => Controller(role, stepUp: true, body: """{"value":"x"}""");

        var results = new[]
        {
            await controller().ListAsync(CancellationToken.None),
            await controller().CreateAsync(CancellationToken.None),
            await controller().ListVersionsAsync(ProviderId, CancellationToken.None),
            await controller().TestAsync(ProviderId, CancellationToken.None),
            await controller().TestAnswerAsync("openai", CancellationToken.None),
            await controller().ConfirmAsync(ProviderId, CancellationToken.None),
            await controller().ActivateAsync(ProviderId, Guid.NewGuid(), CancellationToken.None),
        };

        foreach (var result in results)
        {
            var (status, body) = Problem(result);
            status.Should().Be(403);
            body.GetProperty("code").GetString().Should().Be("PROVIDER_FORBIDDEN");
        }
        _service.VerifyNoOtherCalls();
        _probe.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task EveryWriteNeedsAFreshStepUp()
    {
        var controller = () =>
            Controller("founder", stepUp: false, body: $$"""{"value":"{{Secret}}"}""");

        var results = new[]
        {
            await controller().CreateAsync(CancellationToken.None),
            await controller().TestAsync(ProviderId, CancellationToken.None),
            await controller().TestAnswerAsync("openai", CancellationToken.None),
            await controller().ConfirmAsync(ProviderId, CancellationToken.None),
            await controller().ActivateAsync(ProviderId, Guid.NewGuid(), CancellationToken.None),
        };

        foreach (var result in results)
        {
            var (status, body) = Problem(result);
            status.Should().Be(403);
            body.GetProperty("code").GetString().Should().Be("PROVIDER_STEP_UP_REQUIRED");
            body.GetRawText().Should().NotContain(Secret);
        }
        _service.VerifyNoOtherCalls();
        _probe.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task TestAnswerPassesTheActorAndReturnsTheProbeResult()
    {
        var probeResult = new ProviderProbeResult(
            new ProviderProbeAnswer("openai", "gpt", "gpt-x", "ok", 3, 1, 120),
            [new ProviderProbeAttempt("openai", "ANSWERED", null)]
        );
        _probe
            .Setup(p =>
                p.TestAnswerAsync(
                    "openai",
                    It.Is<ProviderTestAnswerRequest>(r => r.Model == null),
                    "founder-1",
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(probeResult);

        var result = await Controller("founder", true, """{"model":null,"fallbackProviders":[]}""")
            .TestAnswerAsync("openai", CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>().Which.Value.Should().Be(probeResult);
    }

    [Fact]
    public async Task TestAnswerProbeUnavailabilityIsAProblem()
    {
        _probe
            .Setup(p =>
                p.TestAnswerAsync(
                    It.IsAny<string>(),
                    It.IsAny<ProviderTestAnswerRequest>(),
                    It.IsAny<string>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(new ProviderAdminException(503, "PROVIDER_PROBE_UNAVAILABLE", "down"));

        var result = await Controller("founder", true, "{}")
            .TestAnswerAsync("openai", CancellationToken.None);

        var (status, body) = Problem(result);
        status.Should().Be(503);
        body.GetProperty("code").GetString().Should().Be("PROVIDER_PROBE_UNAVAILABLE");
    }

    [Fact]
    public async Task AnUnauthenticatedCallerIsRefused()
    {
        var result = await Controller("founder", true, authenticated: false)
            .ListAsync(CancellationToken.None);

        Problem(result).Status.Should().Be(401);
    }

    [Fact]
    public async Task ConfirmReturns201WithTheRecordedVersionAndPassesTheActor()
    {
        _service
            .Setup(s =>
                s.ConfirmAsync(ProviderId, Secret, true, "founder-1", It.IsAny<CancellationToken>())
            )
            .ReturnsAsync(Saved);
        var controller = Controller(
            "founder",
            true,
            $$"""{"value":"{{Secret}}","acknowledgeUntested":true}"""
        );

        var result = await controller.ConfirmAsync(ProviderId, CancellationToken.None);

        var created = result.Should().BeOfType<ObjectResult>().Subject;
        created.StatusCode.Should().Be(201);
        created.Value.Should().Be(Saved);
    }

    [Fact]
    public async Task TestReturnsTheOutcomeAndNeverTheValue()
    {
        var outcome = new ProviderCredentialTestResult("FAILED", "HTTP 401", 401);
        _service
            .Setup(s => s.TestAsync(ProviderId, Secret, It.IsAny<CancellationToken>()))
            .ReturnsAsync(outcome);

        var result = await Controller("founder", true, $$"""{"value":"{{Secret}}"}""")
            .TestAsync(ProviderId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>().Which.Value.Should().Be(outcome);
    }

    [Fact]
    public async Task CreateReturns201()
    {
        var summary = new ProviderSummary(
            ProviderId,
            "agent-x",
            "Agent X",
            "AGENT_API",
            "a1",
            "API_KEY",
            false,
            true,
            new("NOT_SET", null, null, null)
        );
        _service
            .Setup(s =>
                s.CreateAsync(
                    It.Is<CreateProviderRequest>(r =>
                        r.ProviderName == "agent-x" && r.TestUrl == null
                    ),
                    It.IsAny<CancellationToken>()
                )
            )
            .ReturnsAsync(summary);

        var result = await Controller(
                "founder",
                true,
                """{"providerName":"agent-x","displayName":"Agent X","category":"AGENT_API","agentTypeId":"a1"}"""
            )
            .CreateAsync(CancellationToken.None);

        result.Should().BeOfType<ObjectResult>().Which.StatusCode.Should().Be(201);
    }

    [Fact]
    public async Task ActivateReturns200()
    {
        var versionId = Guid.NewGuid();
        _service
            .Setup(s => s.ActivateAsync(ProviderId, versionId, It.IsAny<CancellationToken>()))
            .ReturnsAsync(Saved);

        var result = await Controller("founder", true)
            .ActivateAsync(ProviderId, versionId, CancellationToken.None);

        result.Should().BeOfType<OkObjectResult>().Which.Value.Should().Be(Saved);
    }

    [Theory]
    [InlineData(404, "PROVIDER_NOT_FOUND")]
    [InlineData(409, "PROVIDER_CONFLICT")]
    [InlineData(422, "PROVIDER_INVALID")]
    [InlineData(503, "PROVIDER_VAULT_UNAVAILABLE")]
    public async Task ServiceFailuresBecomeRfc7807Problems(int status, string code)
    {
        _service
            .Setup(s =>
                s.ConfirmAsync(
                    It.IsAny<Guid>(),
                    It.IsAny<string?>(),
                    It.IsAny<bool>(),
                    It.IsAny<string>(),
                    It.IsAny<CancellationToken>()
                )
            )
            .ThrowsAsync(
                new ProviderAdminException(
                    status,
                    code,
                    "Reason.",
                    new Dictionary<string, object?> { ["testOutcome"] = "FAILED" }
                )
            );

        var result = await Controller("founder", true, $$"""{"value":"{{Secret}}"}""")
            .ConfirmAsync(ProviderId, CancellationToken.None);

        var (actual, body) = Problem(result);
        actual.Should().Be(status);
        body.GetProperty("code").GetString().Should().Be(code);
        body.GetProperty("testOutcome").GetString().Should().Be("FAILED");
        body.TryGetProperty("correlationId", out _).Should().BeTrue();
        body.GetRawText().Should().NotContain(Secret);
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("""{"value":"SYNTHETIC-body-fragment","extra":1}""")]
    [InlineData("null")]
    public async Task MalformedBodiesAreRejectedWithoutEchoingContent(string body)
    {
        var result = await Controller("founder", true, body)
            .ConfirmAsync(ProviderId, CancellationToken.None);

        var (status, problem) = Problem(result);
        status.Should().Be(400);
        problem.GetProperty("code").GetString().Should().Be("PROVIDER_INVALID");
        problem
            .GetRawText()
            .Should()
            .NotContain("SYNTHETIC-body-fragment")
            .And.NotContain("not json");
        _service.VerifyNoOtherCalls();
    }

    [Fact]
    public async Task OversizedBodiesAreRejected()
    {
        var result = await Controller("founder", true, new string('a', 140_000))
            .TestAsync(ProviderId, CancellationToken.None);

        Problem(result).Status.Should().Be(400);
    }

    [Fact]
    public void CredentialRequestsRedactTheValueInToString()
    {
        new ProviderCredentialTestRequest(Secret).ToString().Should().NotContain(Secret);
        new ProviderCredentialConfirmRequest(Secret, true).ToString().Should().NotContain(Secret);
    }
}
