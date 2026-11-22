// Implements: ADR-046 sections 4.2, 5.1 and 12.2 D4; workload-identity-cloud-issuance-contract.md section 8
// constitutional_basis: C-002, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Net.Http.Headers;
using System.Text.Json;

namespace Waooaw.BusinessPlatform.Services;

public sealed record WorkloadCredentialDocuments(string Bundle, string TrustBundle);

public interface IWorkloadCredentialReader
{
    Task<WorkloadCredentialDocuments> ReadAsync(CancellationToken cancellationToken);
}

public sealed class WorkloadCredentialReadException(string code, Exception? inner = null)
    : Exception(code, inner)
{
    public string Code { get; } = code;
}

public sealed class WorkloadCredentialOptions
{
    public const int DefaultRefreshSeconds = 300;
    public const int MinimumRefreshSeconds = 30;

    public string Source { get; init; } = "directory";
    public string VaultUrl { get; init; } = string.Empty;
    public string Workload { get; init; } = "business-platform";
    public string ManagedIdentityClientId { get; init; } = string.Empty;
    public int RefreshSeconds { get; init; } = DefaultRefreshSeconds;
    public string TrustDomain { get; init; } = string.Empty;

    public bool IsKeyVault => Source == "keyvault";

    public static WorkloadCredentialOptions From(IConfiguration configuration) =>
        new()
        {
            Source = (configuration["WAOOAW_WID_SOURCE"] ?? "directory").Trim().ToLowerInvariant(),
            VaultUrl = configuration["WAOOAW_WID_VAULT_URL"]?.Trim() ?? string.Empty,
            Workload = configuration["WAOOAW_WID_WORKLOAD"]?.Trim() is { Length: > 0 } workload
                ? workload
                : "business-platform",
            ManagedIdentityClientId =
                configuration["WAOOAW_WID_MANAGED_IDENTITY_CLIENT_ID"]?.Trim() ?? string.Empty,
            RefreshSeconds = int.TryParse(
                configuration["WAOOAW_WID_REFRESH_SECONDS"],
                out var seconds
            )
                ? Math.Max(MinimumRefreshSeconds, seconds)
                : DefaultRefreshSeconds,
            TrustDomain = configuration["WAOOAW_WID_TRUST_DOMAIN"]?.Trim() ?? string.Empty,
        };

    public Uri? VaultUri =>
        Uri.TryCreate(VaultUrl, UriKind.Absolute, out var uri)
        && uri.Scheme == Uri.UriSchemeHttps
        && uri.Host.EndsWith(".vault.azure.net", StringComparison.OrdinalIgnoreCase)
        && string.IsNullOrEmpty(uri.UserInfo)
        && uri.AbsolutePath == "/"
        && string.IsNullOrEmpty(uri.Query)
        && string.IsNullOrEmpty(uri.Fragment)
            ? uri
            : null;

    public string? Validate() =>
        !IsKeyVault ? null
        : Workload != "business-platform" ? "CONFIG_WORKLOAD"
        : string.IsNullOrWhiteSpace(TrustDomain) ? "CONFIG_TRUST_DOMAIN"
        : VaultUri is null ? "CONFIG_VAULT_URL"
        : null;
}

/// <summary>Reads the workload bundle and the trust bundle from Key Vault with the managed identity token.</summary>
public sealed class KeyVaultWorkloadCredentialReader(
    HttpClient client,
    IConfiguration configuration,
    WorkloadCredentialOptions options
) : IWorkloadCredentialReader
{
    public async Task<WorkloadCredentialDocuments> ReadAsync(CancellationToken cancellationToken)
    {
        var vault =
            options.VaultUri ?? throw new WorkloadCredentialReadException("CONFIG_VAULT_URL");
        if (options.Validate() is { } invalid)
            throw new WorkloadCredentialReadException(invalid);
        var token = await ReadTokenAsync(cancellationToken);
        var bundle = await ReadSecretAsync(
            vault,
            $"wid-bundle-{options.Workload}",
            token,
            cancellationToken
        );
        var trust = await ReadSecretAsync(vault, "wid-trust-bundle", token, cancellationToken);
        return new WorkloadCredentialDocuments(bundle, trust);
    }

    private async Task<string> ReadTokenAsync(CancellationToken cancellationToken)
    {
        var header = configuration["IDENTITY_HEADER"];
        if (
            !Uri.TryCreate(configuration["IDENTITY_ENDPOINT"], UriKind.Absolute, out var endpoint)
            || endpoint.Scheme != Uri.UriSchemeHttp
            || !endpoint.IsLoopback
            || !string.IsNullOrEmpty(endpoint.UserInfo)
            || !string.IsNullOrEmpty(endpoint.Query)
            || !string.IsNullOrEmpty(endpoint.Fragment)
            || string.IsNullOrWhiteSpace(header)
        )
            throw new WorkloadCredentialReadException("IDENTITY_ENDPOINT_UNAVAILABLE");
        var query = "?api-version=2019-08-01&resource=https%3A%2F%2Fvault.azure.net";
        if (!string.IsNullOrEmpty(options.ManagedIdentityClientId))
            query += $"&client_id={Uri.EscapeDataString(options.ManagedIdentityClientId)}";
        using var request = new HttpRequestMessage(HttpMethod.Get, $"{endpoint}{query}");
        request.Headers.Add("X-IDENTITY-HEADER", header);
        using var document = await SendAsync(request, "IDENTITY_TOKEN_DENIED", cancellationToken);
        var root = document.RootElement;
        if (
            root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("access_token", out var token)
            || token.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(token.GetString())
            || !root.TryGetProperty("resource", out var resource)
            || resource.ValueKind != JsonValueKind.String
            || resource.GetString()?.TrimEnd('/') != "https://vault.azure.net"
        )
            throw new WorkloadCredentialReadException("IDENTITY_TOKEN_DENIED");
        return token.GetString()!;
    }

    private async Task<string> ReadSecretAsync(
        Uri vault,
        string name,
        string token,
        CancellationToken cancellationToken
    )
    {
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            new Uri(vault, $"/secrets/{name}?api-version=7.4")
        );
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        using var document = await SendAsync(request, "SECRET_READ_DENIED", cancellationToken);
        var root = document.RootElement;
        if (
            root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("value", out var value)
            || value.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(value.GetString())
            || (
                root.TryGetProperty("attributes", out var attributes)
                && attributes.ValueKind == JsonValueKind.Object
                && attributes.TryGetProperty("enabled", out var enabled)
                && enabled.ValueKind == JsonValueKind.False
            )
        )
            throw new WorkloadCredentialReadException("SECRET_READ_DENIED");
        return value.GetString()!;
    }

    private async Task<JsonDocument> SendAsync(
        HttpRequestMessage request,
        string deniedCode,
        CancellationToken cancellationToken
    )
    {
        try
        {
            using var response = await client.SendAsync(request, cancellationToken);
            if (!response.IsSuccessStatusCode)
                throw new WorkloadCredentialReadException(deniedCode);
            return await JsonDocument.ParseAsync(
                await response.Content.ReadAsStreamAsync(cancellationToken),
                cancellationToken: cancellationToken
            );
        }
        catch (Exception exception)
            when (exception is HttpRequestException or JsonException or TaskCanceledException
                && !cancellationToken.IsCancellationRequested
            )
        {
            throw new WorkloadCredentialReadException("VAULT_UNREACHABLE", exception);
        }
    }
}
