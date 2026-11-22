// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R004
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services;

public sealed class ProviderCredentialOptions
{
    public const string SectionName = "ProviderCredentials";

    public string VaultUrl { get; init; } = string.Empty;
    public string ManagedIdentityClientId { get; init; } = string.Empty;

    public static ProviderCredentialOptions From(IConfiguration configuration) =>
        new()
        {
            VaultUrl = configuration[$"{SectionName}:VaultUrl"]?.Trim() ?? string.Empty,
            ManagedIdentityClientId =
                (
                    configuration[$"{SectionName}:ManagedIdentityClientId"]
                    ?? configuration["WhatsAppProvider:ManagedIdentityClientId"]
                    ?? configuration["WAOOAW_WID_MANAGED_IDENTITY_CLIENT_ID"]
                )?.Trim() ?? string.Empty,
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
}

public static partial class ProviderSecretNames
{
    public const string Prefix = "provider-";

    [GeneratedRegex("^[a-z0-9-]{2,48}$")]
    private static partial Regex ProviderNamePattern();

    public static bool IsValidProviderName(string? providerName) =>
        providerName is not null && ProviderNamePattern().IsMatch(providerName);

    public static string For(string providerName) =>
        IsValidProviderName(providerName)
            ? Prefix + providerName
            : throw new ArgumentException("The provider name is not valid.", nameof(providerName));
}

/// <summary>The vault is unavailable or refused a write. The message never carries a secret value or a vault response body.</summary>
public sealed class ProviderSecretStoreException(string message) : Exception(message);

/// <summary>Writes provider credentials to Key Vault. Each write creates a new secret version; none is ever overwritten.</summary>
public interface IProviderSecretStore
{
    /// <summary>Stores the value as a new version of the named secret and returns that version's identifier.</summary>
    Task<string> SetSecretAsync(string secretName, string value, CancellationToken ct);
}

public sealed partial class KeyVaultProviderSecretStore(
    HttpClient client,
    IConfiguration configuration,
    ProviderCredentialOptions options
) : IProviderSecretStore
{
    private const int MaximumResponseBytes = 131_072;

    [GeneratedRegex("^[A-Za-z0-9]{1,64}$")]
    private static partial Regex VersionPattern();

    public async Task<string> SetSecretAsync(string secretName, string value, CancellationToken ct)
    {
        var vault =
            options.VaultUri
            ?? throw new ProviderSecretStoreException("Key Vault is not configured.");
        if (!secretName.StartsWith(ProviderSecretNames.Prefix, StringComparison.Ordinal))
            throw new ProviderSecretStoreException(
                "The secret name is outside the provider namespace."
            );
        try
        {
            var token = await ReadTokenAsync(ct);
            using var request = new HttpRequestMessage(
                HttpMethod.Put,
                new Uri(vault, $"/secrets/{Uri.EscapeDataString(secretName)}?api-version=7.4")
            );
            request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
            request.Content = new StringContent(
                JsonSerializer.Serialize(
                    new
                    {
                        value,
                        contentType = "text/plain",
                        attributes = new { enabled = true },
                    }
                ),
                Encoding.UTF8,
                "application/json"
            );
            using var response = await client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                ct
            );
            if (!response.IsSuccessStatusCode)
                throw new ProviderSecretStoreException(
                    $"Key Vault refused the write (HTTP {(int)response.StatusCode})."
                );
            using var document = await ReadBoundedJsonAsync(response, ct);
            return ParseVersion(document.RootElement, vault, secretName);
        }
        catch (Exception exception)
            when (exception
                    is HttpRequestException
                        or TaskCanceledException
                        or JsonException
                        or IOException
            )
        {
            if (ct.IsCancellationRequested)
                throw;
            throw new ProviderSecretStoreException("Key Vault could not be reached.");
        }
    }

    private static string ParseVersion(JsonElement root, Uri vault, string secretName)
    {
        if (
            root.ValueKind == JsonValueKind.Object
            && root.TryGetProperty("id", out var id)
            && id.ValueKind == JsonValueKind.String
            && Uri.TryCreate(id.GetString(), UriKind.Absolute, out var location)
            && location.Host.Equals(vault.Host, StringComparison.OrdinalIgnoreCase)
        )
        {
            var segments = location.AbsolutePath.Split('/', StringSplitOptions.RemoveEmptyEntries);
            if (
                segments.Length == 3
                && segments[0] == "secrets"
                && segments[1] == secretName
                && VersionPattern().IsMatch(segments[2])
            )
                return segments[2];
        }
        throw new ProviderSecretStoreException("Key Vault returned an unexpected response.");
    }

    private static async Task<JsonDocument> ReadBoundedJsonAsync(
        HttpResponseMessage response,
        CancellationToken ct
    )
    {
        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        var bytes = new byte[MaximumResponseBytes + 1];
        var length = 0;
        while (length < bytes.Length)
        {
            var count = await stream.ReadAsync(bytes.AsMemory(length), ct);
            if (count == 0)
                break;
            length += count;
        }
        if (length == bytes.Length)
            throw new ProviderSecretStoreException("Key Vault returned an unexpected response.");
        return JsonDocument.Parse(bytes.AsMemory(0, length));
    }

    private async Task<string> ReadTokenAsync(CancellationToken ct)
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
            throw new ProviderSecretStoreException("The workload identity is unavailable.");
        var query = "?api-version=2019-08-01&resource=https%3A%2F%2Fvault.azure.net";
        if (!string.IsNullOrEmpty(options.ManagedIdentityClientId))
            query += $"&client_id={Uri.EscapeDataString(options.ManagedIdentityClientId)}";
        using var request = new HttpRequestMessage(HttpMethod.Get, $"{endpoint}{query}");
        request.Headers.Add("X-IDENTITY-HEADER", header);
        using var response = await client.SendAsync(request, ct);
        if (!response.IsSuccessStatusCode)
            throw new ProviderSecretStoreException("The workload identity was refused.");
        using var document = await ReadBoundedJsonAsync(response, ct);
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
            throw new ProviderSecretStoreException("The workload identity was refused.");
        return token.GetString()!;
    }
}

/// <summary>Registered when ProviderCredentials:VaultUrl is not set; every write reports the vault unavailable.</summary>
public sealed class UnconfiguredProviderSecretStore : IProviderSecretStore
{
    public Task<string> SetSecretAsync(string secretName, string value, CancellationToken ct) =>
        Task.FromException<string>(
            new ProviderSecretStoreException("The provider credential vault is not configured.")
        );
}
