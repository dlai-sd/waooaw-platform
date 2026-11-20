// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// constitutional_basis: C-023, C-059, C-063, C-088, C-089
using System.Net;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class PricingAdminGatewayTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    private static PricingGatewayRequest Request(
        bool stepUp,
        Guid? key,
        string method = "POST",
        string body = """{"a":1}"""
    ) =>
        new(
            "wbeAuthorizePricingDraft",
            method,
            "/internal/v1/pricing/drafts/{draftId}/authorize",
            "/internal/v1/pricing/drafts/7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11/authorize",
            null,
            Encoding.UTF8.GetBytes(body),
            "founder-1",
            "FOUNDER",
            stepUp,
            Guid.NewGuid(),
            "7d5e5d5e-6a16-4d35-9b44-7f3a1f0d1a11",
            Guid.NewGuid(),
            key
        );

    private static void Replace(
        AuthenticatedPricingAdminGateway gateway,
        Func<HttpRequestMessage, HttpResponseMessage> send
    )
    {
        var field = typeof(AuthenticatedPricingAdminGateway).GetField(
            "_client",
            BindingFlags.Instance | BindingFlags.NonPublic
        )!;
        var original = (HttpClient)field.GetValue(gateway)!;
        field.SetValue(
            gateway,
            new HttpClient(new Stub(send)) { BaseAddress = new Uri("https://billing.test") }
        );
        original.Dispose();
    }

    [Fact]
    public async Task The_call_carries_the_bearer_the_correlation_id_the_idempotency_key_and_the_etag_comes_back()
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedPricingAdminGateway(
            identity,
            new Uri("https://billing.test")
        );
        HttpRequestMessage? seen = null;
        string? sentBody = null;
        Replace(
            gateway,
            message =>
            {
                seen = message;
                sentBody = message.Content!.ReadAsStringAsync().Result;
                var response = new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent(
                        """{"state":"EFFECTIVE"}""",
                        Encoding.UTF8,
                        "application/json"
                    ),
                };
                response.Headers.ETag = new("\"2:EFFECTIVE:abcd\"");
                return response;
            }
        );
        var key = Guid.NewGuid();
        var request = Request(true, key);

        var response = await gateway.SendAsync(request, CancellationToken.None);

        Assert.Equal(200, response.Status);
        Assert.Equal("EFFECTIVE", response.Body!.Value.GetProperty("state").GetString());
        Assert.Equal("\"2:EFFECTIVE:abcd\"", response.ETag);
        Assert.Equal("Bearer", seen!.Headers.Authorization!.Scheme);
        Assert.Equal(
            request.CorrelationId.ToString("D"),
            seen.Headers.GetValues("X-Correlation-ID").Single()
        );
        Assert.Equal(key.ToString("D"), seen.Headers.GetValues("Idempotency-Key").Single());
        Assert.Equal("""{"a":1}""", sentBody);
    }

    [Fact]
    public async Task The_signed_context_binds_the_body_digest_the_nil_relationship_and_the_step_up_purpose()
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedPricingAdminGateway(
            identity,
            new Uri("https://billing.test")
        );
        var tokens = new List<string>();
        Replace(
            gateway,
            message =>
            {
                tokens.Add(message.Headers.Authorization!.Parameter!);
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent("{}"),
                };
            }
        );

        await gateway.SendAsync(Request(true, Guid.NewGuid()), CancellationToken.None);
        await gateway.SendAsync(Request(false, Guid.NewGuid()), CancellationToken.None);

        var stepUp = Decode(tokens[0]);
        var admin = Decode(tokens[1]);
        Assert.Contains(AuthenticatedPricingAdminGateway.StepUpPurpose, stepUp);
        Assert.Contains(AuthenticatedPricingAdminGateway.AdminPurpose, admin);
        Assert.DoesNotContain(AuthenticatedPricingAdminGateway.StepUpPurpose, admin);
        Assert.Contains(AuthenticatedPricingAdminGateway.NilRelationshipId, stepUp);
        Assert.Contains(
            Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes("""{"a":1}"""))),
            stepUp
        );
        Assert.Contains("wbeAuthorizePricingDraft", stepUp);
        Assert.Contains("/internal/v1/pricing/drafts/{draftId}/authorize", stepUp);
    }

    [Fact]
    public async Task A_read_sends_no_body_and_signs_the_digest_of_nothing()
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedPricingAdminGateway(
            identity,
            new Uri("https://billing.test")
        );
        HttpRequestMessage? seen = null;
        string? token = null;
        Replace(
            gateway,
            message =>
            {
                seen = message;
                token = message.Headers.Authorization!.Parameter;
                return new HttpResponseMessage(HttpStatusCode.OK)
                {
                    Content = new StringContent("{}"),
                };
            }
        );

        await gateway.SendAsync(Request(false, null, "GET", ""), CancellationToken.None);

        Assert.Null(seen!.Content);
        Assert.False(seen.Headers.Contains("Idempotency-Key"));
        Assert.Contains(Convert.ToHexStringLower(SHA256.HashData([])), Decode(token!));
    }

    [Fact]
    public async Task Transport_failures_surface_as_owner_unavailable_and_a_non_json_body_is_empty()
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedPricingAdminGateway(
            identity,
            new Uri("https://billing.test")
        );
        Replace(gateway, _ => throw new HttpRequestException("down"));
        await Assert.ThrowsAsync<PricingAdminOwnerUnavailableException>(() =>
            gateway.SendAsync(Request(false, Guid.NewGuid()), CancellationToken.None)
        );

        Replace(
            gateway,
            _ => new HttpResponseMessage(HttpStatusCode.BadGateway)
            {
                Content = new StringContent("<html>"),
            }
        );
        var response = await gateway.SendAsync(
            Request(false, Guid.NewGuid()),
            CancellationToken.None
        );

        Assert.Equal(502, response.Status);
        Assert.Null(response.Body);
    }

    [Fact]
    public async Task An_unconfigured_owner_is_unavailable()
    {
        await Assert.ThrowsAsync<PricingAdminOwnerUnavailableException>(() =>
            new UnconfiguredPricingAdminGateway().SendAsync(
                Request(false, null),
                CancellationToken.None
            )
        );
    }

    private static string Decode(string token) =>
        string.Concat(token.Split('.').Select(part => TryDecode(part) ?? part));

    private static string? TryDecode(string part)
    {
        try
        {
            var padded = part.Replace('-', '+').Replace('_', '/');
            padded = padded.PadRight(padded.Length + (4 - padded.Length % 4) % 4, '=');
            return Encoding.UTF8.GetString(Convert.FromBase64String(padded));
        }
        catch (FormatException)
        {
            return null;
        }
    }

    private sealed class Stub(Func<HttpRequestMessage, HttpResponseMessage> send)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(send(request));
    }
}
