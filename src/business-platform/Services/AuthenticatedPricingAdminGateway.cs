// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-03
// Constitutional basis: C-023, C-059, C-063, C-088, C-089
using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>One call to a WBE pricing admin route; the body bytes are exactly what is signed and sent.</summary>
public sealed record PricingGatewayRequest(
    string WbeOperation,
    string Method,
    string RouteTemplate,
    string Path,
    string? Query,
    byte[] Body,
    string ActorSubject,
    string EffectiveRole,
    bool StepUp,
    Guid TenantId,
    string SubjectReference,
    Guid CorrelationId,
    Guid? IdempotencyKey
);

public sealed record PricingGatewayResponse(int Status, JsonElement? Body, string? ETag);

public interface IPricingAdminGateway
{
    Task<PricingGatewayResponse> SendAsync(PricingGatewayRequest request, CancellationToken ct);
}

/// <summary>The WBE pricing owner could not be reached or answered without a usable body.</summary>
public sealed class PricingAdminOwnerUnavailableException(string message, Exception? inner = null)
    : Exception(message, inner);

/// <summary>
/// Signs the ADR-046 delegated context for a non-relationship admin call: the nil relationship id, the
/// pricing role in the effective role and the Founder step-up in the purpose (PRICING_ADMIN_STEP_UP).
/// </summary>
public sealed class AuthenticatedPricingAdminGateway : IPricingAdminGateway, IDisposable
{
    public const string AdminPurpose = "PRICING_ADMIN";
    public const string StepUpPurpose = "PRICING_ADMIN_STEP_UP";
    public const string NilRelationshipId = "00000000-0000-0000-0000-000000000000";

    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _client;

    public AuthenticatedPricingAdminGateway(WorkloadIdentityClient identity, Uri endpoint)
    {
        _identity = identity;
        _client = identity.CreateClient(endpoint, "billing-engine");
    }

    public async Task<PricingGatewayResponse> SendAsync(
        PricingGatewayRequest value,
        CancellationToken ct
    )
    {
        var digest = Convert.ToHexStringLower(SHA256.HashData(value.Body));
        var correlation = value.CorrelationId.ToString("D");
        var context = new DelegatedRequestContext(
            value.ActorSubject,
            value.EffectiveRole,
            value.TenantId.ToString("D"),
            NilRelationshipId,
            value.StepUp ? StepUpPurpose : AdminPurpose,
            value.SubjectReference,
            correlation,
            value.IdempotencyKey?.ToString("D"),
            new Dictionary<string, string>(),
            correlation
        );
        string envelope;
        try
        {
            envelope = _identity.Sign(
                context,
                _identity.GetAudience("billing-engine"),
                value.Method,
                value.RouteTemplate,
                value.WbeOperation,
                1,
                digest,
                DateTimeOffset.UtcNow
            );
        }
        catch (WorkloadCredentialsUnavailableException exception)
        {
            throw new PricingAdminOwnerUnavailableException(
                "The pricing owner credentials are unavailable.",
                exception
            );
        }
        var uri = string.IsNullOrEmpty(value.Query) ? value.Path : $"{value.Path}?{value.Query}";
        using var request = new HttpRequestMessage(new HttpMethod(value.Method), uri);
        if (value.Body.Length > 0)
        {
            request.Content = new ByteArrayContent(value.Body);
            request.Content.Headers.ContentType = new("application/json");
        }
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", correlation);
        if (value.IdempotencyKey is { } key)
            request.Headers.Add("Idempotency-Key", key.ToString("D"));
        try
        {
            using var response = await _client.SendAsync(request, ct);
            var text = await response.Content.ReadAsStringAsync(ct);
            JsonElement? body = null;
            if (!string.IsNullOrWhiteSpace(text))
            {
                try
                {
                    using var document = JsonDocument.Parse(text);
                    body = document.RootElement.Clone();
                }
                catch (JsonException)
                {
                    body = null;
                }
            }
            var etag = response.Headers.ETag?.Tag;
            return new PricingGatewayResponse((int)response.StatusCode, body, etag);
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException)
        {
            throw new PricingAdminOwnerUnavailableException(
                "The pricing owner could not be reached.",
                exception
            );
        }
    }

    public void Dispose() => _client.Dispose();
}

public sealed class UnconfiguredPricingAdminGateway : IPricingAdminGateway
{
    public Task<PricingGatewayResponse> SendAsync(
        PricingGatewayRequest request,
        CancellationToken ct
    ) =>
        Task.FromException<PricingGatewayResponse>(
            new PricingAdminOwnerUnavailableException(
                "The authenticated WBE pricing owner is not configured."
            )
        );
}
