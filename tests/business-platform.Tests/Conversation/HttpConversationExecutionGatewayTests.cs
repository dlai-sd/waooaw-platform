// Implements: work-contracts/WC-095-agent-employment-lifecycle-and-dma-customer-activation.md §6.3
// constitutional_basis: C-005, C-023, C-026, C-059, C-063, C-076, C-079

using System.IdentityModel.Tokens.Jwt;
using System.Net;
using System.Text.Json;
using Microsoft.Extensions.Configuration;
using Moq;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Conversation;

public sealed class HttpConversationExecutionGatewayTests
{
    [Fact]
    public async Task SendsExactMandateContentAndScopedAssertion()
    {
        HttpRequestMessage? captured = null;
        string? capturedBody = null;
        var gateway = CreateGateway(request =>
        {
            captured = request;
            capturedBody = request.Content!.ReadAsStringAsync().GetAwaiter().GetResult();
            return new HttpResponseMessage(HttpStatusCode.Accepted);
        });
        var mandate = Mandate();
        var idempotencyKey = mandate.IdempotencyIdentity;

        await gateway.StartAsync(
            Guid.Parse("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
            Guid.Parse("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            Guid.Parse("cccccccc-cccc-4ccc-8ccc-cccccccccccc"),
            mandate.RelationshipId,
            "en-IN",
            [new ConversationTextBlockV1("1.0", "TEXT", "Prepare the profile", "en")],
            mandate,
            idempotencyKey,
            CancellationToken.None);

        Assert.NotNull(captured);
        Assert.Equal(idempotencyKey.ToString("D"), captured!.Headers.GetValues("Idempotency-Key").Single());
        var token = new JwtSecurityTokenHandler().ReadJwtToken(captured.Headers.Authorization!.Parameter);
        Assert.Equal("conversation:execute", token.Claims.Single(value => value.Type == "scope").Value);
        Assert.Equal(mandate.TenantId.ToString("D"), token.Claims.Single(value => value.Type == "tenant_id").Value);
        Assert.Equal(mandate.ActorId.ToString("D"), token.Claims.Single(value => value.Type == "delegated_actor_id").Value);
        using var document = JsonDocument.Parse(capturedBody!);
        var root = document.RootElement;
        Assert.Equal("CUSTOMER_PROFILING", root.GetProperty("operationalMandate").GetProperty("skillId").GetString());
        Assert.Equal(mandate.MandateDigest, root.GetProperty("operationalMandate").GetProperty("mandateDigest").GetString());
        Assert.Equal("Prepare the profile", root.GetProperty("content").GetProperty("text").GetString());
    }

    [Theory]
    [InlineData(HttpStatusCode.Conflict)]
    [InlineData(HttpStatusCode.Locked)]
    [InlineData(HttpStatusCode.ServiceUnavailable)]
    public async Task FailsClosedForAnyRejectedExecution(HttpStatusCode status)
    {
        var gateway = CreateGateway(_ => new HttpResponseMessage(status));
        var mandate = Mandate();
        await Assert.ThrowsAsync<ConversationExecutionUnavailableException>(() => gateway.StartAsync(
            Guid.NewGuid(), Guid.NewGuid(), Guid.NewGuid(), mandate.RelationshipId, "en-IN",
            [new ConversationTextBlockV1("1.0", "TEXT", "Prepare the profile", "en")],
            mandate, mandate.IdempotencyIdentity, CancellationToken.None));
    }

    private static OperationalMandateV1 Mandate() => new(
        "1.0", Guid.NewGuid(), "sha256:" + new string('1', 64),
        Guid.Parse("11111111-1111-4111-8111-111111111111"),
        Guid.Parse("22222222-2222-4222-8222-222222222222"),
        Guid.Parse("33333333-3333-4333-8333-333333333333"),
        Guid.Parse("44444444-4444-4444-8444-444444444444"),
        "EMPLOYER", "ACTIVE", "LIVE", "DIGITAL_MARKETING_LOCAL_SERVICE", 1, "1.0.0", "3.1",
        "sha256:" + new string('2', 64), 1, "sha256:" + new string('3', 64),
        "sha256:" + new string('4', 64), "1.0", "2.0", "1.0.0", "1.0.0",
        "sha256:" + new string('8', 64),
        "CUSTOMER_PROFILING", "1.0.0", "sha256:" + new string('5', 64),
        "sha256:" + new string('6', 64), "1.0.0", "sha256:" + new string('7', 64),
        1, 1, 1, 1, "allowance-a", 1, ["approval-a"], false, null, "Prepare the profile",
        ["PRESENT_PROFILE_PROPOSAL"], ["UNDECLARED_ACTION"],
        new DateTimeOffset(2027, 1, 1, 0, 0, 0, TimeSpan.Zero),
        Guid.Parse("55555555-5555-4555-8555-555555555555"), "decision-a", "evidence-a", null, null);

    private static HttpConversationExecutionGateway CreateGateway(Func<HttpRequestMessage, HttpResponseMessage> response)
    {
        var client = new HttpClient(new StubHandler(response)) { BaseAddress = new Uri("http://professional-runtime/") };
        var factory = new Mock<IHttpClientFactory>();
        factory.Setup(value => value.CreateClient("ConversationProfessionalRuntime")).Returns(client);
        var configuration = new ConfigurationBuilder().AddInMemoryCollection(new Dictionary<string, string?>
        {
            ["Conversation:ProfessionalRuntimeJwtSecret"] = "0123456789abcdef0123456789abcdef",
        }).Build();
        return new HttpConversationExecutionGateway(factory.Object, configuration);
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> response) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken cancellationToken) =>
            Task.FromResult(response(request));
    }
}
