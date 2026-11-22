// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R005
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Net.Http.Headers;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services;

public sealed record ProviderTestAnswerRequest(
    string? Model,
    IReadOnlyList<string>? FallbackProviders
);

public sealed record ProviderProbeTarget(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("model")] string? Model
);

public sealed record ProviderProbeAnswer(
    [property: JsonPropertyName("provider")] string Provider,
    [property: JsonPropertyName("model")] string? Model,
    [property: JsonPropertyName("reportedModel")] string? ReportedModel,
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("inputTokens")] long? InputTokens,
    [property: JsonPropertyName("outputTokens")] long? OutputTokens,
    [property: JsonPropertyName("latencyMs")] long? LatencyMs
);

public sealed record ProviderProbeAttempt(
    [property: JsonPropertyName("provider")] string Provider,
    [property: JsonPropertyName("outcome")] string Outcome,
    [property: JsonPropertyName("reason")] string? Reason
);

public sealed record ProviderProbeResult(
    [property: JsonPropertyName("answered")] ProviderProbeAnswer? Answered,
    [property: JsonPropertyName("attempts")] IReadOnlyList<ProviderProbeAttempt> Attempts
);

/// <summary>The AI runtime probe could not be reached, is not configured, or answered unusably.</summary>
public sealed class ProviderProbeUnavailableException(string message, Exception? inner = null)
    : Exception(message, inner);

public interface IProviderProbeGateway
{
    Task<ProviderProbeResult> ProbeAsync(
        IReadOnlyList<ProviderProbeTarget> providers,
        string actorSubject,
        CancellationToken ct
    );
}

public interface IProviderGenerationProbe
{
    Task<ProviderProbeResult> TestAnswerAsync(
        string providerName,
        ProviderTestAnswerRequest request,
        string actorSubject,
        CancellationToken ct
    );
}

public sealed partial class ProviderGenerationProbe(IProviderProbeGateway gateway)
    : IProviderGenerationProbe
{
    public const int MaximumTextLength = 2000;
    private const int MaximumFallbacks = 3;

    private static readonly HashSet<string> Outcomes = ["ANSWERED", "SKIPPED"];
    private static readonly HashSet<string> Reasons =
    [
        "KEY_MISSING",
        "KEY_REJECTED",
        "TIMEOUT",
        "PROVIDER_ERROR",
        "UNSUPPORTED",
    ];

    [GeneratedRegex("^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")]
    private static partial Regex ModelPattern();

    public async Task<ProviderProbeResult> TestAnswerAsync(
        string providerName,
        ProviderTestAnswerRequest request,
        string actorSubject,
        CancellationToken ct
    )
    {
        if (!ProviderSecretNames.IsValidProviderName(providerName))
            throw Invalid("The provider name is not valid.");
        var model = request.Model?.Trim();
        if (string.IsNullOrEmpty(model))
            model = null;
        else if (!ModelPattern().IsMatch(model))
            throw Invalid("The model name is not valid.");
        var fallbacks = request.FallbackProviders ?? [];
        if (
            fallbacks.Count > MaximumFallbacks
            || fallbacks.Any(name => !ProviderSecretNames.IsValidProviderName(name))
            || fallbacks.Append(providerName).Distinct(StringComparer.Ordinal).Count()
                != fallbacks.Count + 1
        )
            throw Invalid("The fallback providers are not valid.");

        ProviderProbeResult result;
        try
        {
            result = await gateway.ProbeAsync(
                [
                    new ProviderProbeTarget(providerName, model),
                    .. fallbacks.Select(name => new ProviderProbeTarget(name, null)),
                ],
                actorSubject,
                ct
            );
        }
        catch (ProviderProbeUnavailableException)
        {
            throw new ProviderAdminException(
                503,
                "PROVIDER_PROBE_UNAVAILABLE",
                "The AI runtime could not run the provider test right now."
            );
        }
        return Sanitize(result);
    }

    // Only fixed vocabularies and a bounded answer text leave this service, whatever the runtime returned.
    internal static ProviderProbeResult Sanitize(ProviderProbeResult result) =>
        new(
            result.Answered is { } answered
                ? answered with
                {
                    Provider = Clip(answered.Provider, 64) ?? string.Empty,
                    Model = Clip(answered.Model, 100),
                    ReportedModel = Clip(answered.ReportedModel, 100),
                    Text = Clip(answered.Text, MaximumTextLength) ?? string.Empty,
                }
                : null,
            (result.Attempts ?? [])
                .Take(MaximumFallbacks + 1)
                .Select(attempt => new ProviderProbeAttempt(
                    Clip(attempt.Provider, 64) ?? string.Empty,
                    Outcomes.Contains(attempt.Outcome) ? attempt.Outcome : "SKIPPED",
                    attempt.Outcome == "ANSWERED" ? null
                        : attempt.Reason is { } reason && Reasons.Contains(reason) ? reason
                        : "PROVIDER_ERROR"
                ))
                .ToList()
        );

    private static string? Clip(string? value, int length) =>
        value is null || value.Length <= length ? value : value[..length];

    private static ProviderAdminException Invalid(string detail) =>
        new(400, "PROVIDER_INVALID", detail);
}

/// <summary>
/// Signs the ADR-046 delegated context for the platform-level provider probe (no tenant or relationship) and
/// sends it to the AI runtime over mTLS. The body bytes signed are exactly the bytes sent.
/// </summary>
public sealed class AuthenticatedProviderProbeGateway : IProviderProbeGateway, IDisposable
{
    public const string Purpose = "PROVIDER_GENERATION_PROBE";
    public const string Route = "/internal/v1/provider-generations/probe";
    public const string Operation = "probeProviderGeneration";
    public const string FounderRole = "FOUNDER";
    private const string NilId = "00000000-0000-0000-0000-000000000000";
    private const int MaximumResponseBytes = 65_536;

    private static readonly JsonSerializerOptions Options = new(JsonSerializerDefaults.Web);

    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _client;

    public AuthenticatedProviderProbeGateway(WorkloadIdentityClient identity, Uri endpoint)
    {
        _identity = identity;
        _client = identity.CreateClient(endpoint, "ai-runtime");
    }

    public async Task<ProviderProbeResult> ProbeAsync(
        IReadOnlyList<ProviderProbeTarget> providers,
        string actorSubject,
        CancellationToken ct
    )
    {
        var body = JsonSerializer.SerializeToUtf8Bytes(new { providers }, Options);
        var correlation = Guid.NewGuid().ToString("D");
        string envelope;
        try
        {
            envelope = _identity.Sign(
                new DelegatedRequestContext(
                    actorSubject,
                    FounderRole,
                    NilId,
                    NilId,
                    Purpose,
                    providers[0].Name,
                    correlation,
                    null,
                    new Dictionary<string, string>(),
                    correlation
                ),
                _identity.GetAudience("ai-runtime"),
                "POST",
                Route,
                Operation,
                1,
                Convert.ToHexStringLower(SHA256.HashData(body)),
                DateTimeOffset.UtcNow
            );
        }
        catch (Exception exception)
            when (exception is WorkloadCredentialsUnavailableException or InvalidOperationException)
        {
            throw new ProviderProbeUnavailableException(
                "The AI runtime credentials are unavailable.",
                exception
            );
        }
        using var request = new HttpRequestMessage(HttpMethod.Post, Route)
        {
            Content = new ByteArrayContent(body),
        };
        request.Content.Headers.ContentType = new("application/json");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", correlation);
        try
        {
            using var response = await _client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                ct
            );
            if (!response.IsSuccessStatusCode)
                throw new ProviderProbeUnavailableException(
                    "The AI runtime refused the provider test."
                );
            await using var stream = await response.Content.ReadAsStreamAsync(ct);
            using var buffer = new MemoryStream();
            var chunk = new byte[8192];
            int read;
            while ((read = await stream.ReadAsync(chunk, ct)) > 0)
            {
                buffer.Write(chunk, 0, read);
                if (buffer.Length > MaximumResponseBytes)
                    throw new ProviderProbeUnavailableException(
                        "The AI runtime answered with an oversized response."
                    );
            }
            return JsonSerializer.Deserialize<ProviderProbeResult>(buffer.ToArray(), Options)
                ?? throw new ProviderProbeUnavailableException(
                    "The AI runtime answered without a usable body."
                );
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            throw new ProviderProbeUnavailableException(
                "The AI runtime could not be reached.",
                exception
            );
        }
    }

    public void Dispose() => _client.Dispose();
}

public sealed class UnconfiguredProviderProbeGateway : IProviderProbeGateway
{
    public Task<ProviderProbeResult> ProbeAsync(
        IReadOnlyList<ProviderProbeTarget> providers,
        string actorSubject,
        CancellationToken ct
    ) =>
        Task.FromException<ProviderProbeResult>(
            new ProviderProbeUnavailableException("The AI runtime probe is not configured.")
        );
}
