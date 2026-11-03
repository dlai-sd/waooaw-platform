// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §10.2, §25.2 WC120-P2
// Implements: work-contracts/WC-121-demo-whatsapp-provider-enablement-work-component.md §10.17
// Constitutional basis: C-014, C-023, C-026, C-059, C-063

using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;
using OpenTelemetry;

namespace Waooaw.BusinessPlatform.Services;

public sealed class WhatsAppProviderOptions
{
    public bool Enabled { get; set; }
    public string Environment { get; set; } = string.Empty;
    public string VaultHost { get; set; } = string.Empty;
    public string ManagedIdentityClientId { get; set; } = string.Empty;
    public string BindingVersion { get; set; } = string.Empty;
    public string OutboundAuthorityVersion { get; set; } = string.Empty;
    public string VerifyTokenVersion { get; set; } = string.Empty;
    public string AppSecretVersion { get; set; } = string.Empty;
}

public sealed class WhatsAppProviderBinding
{
    public required string Environment { get; init; }
    public required string BindingVersion { get; init; }
    public required string AppId { get; init; }
    public required string WabaId { get; init; }
    public required string PhoneNumberId { get; init; }
    public required string RecipientPhoneNumber { get; init; }
    public required string RecipientBindingDigest { get; init; }
    public required string ApiVersion { get; init; }
    public required string AuthorityReference { get; init; }
    public required DateTimeOffset ValidFrom { get; init; }
    public required DateTimeOffset ExpiresAt { get; init; }

    public override string ToString() => nameof(WhatsAppProviderBinding);
}

public sealed class WhatsAppProviderCredentials
{
    public required WhatsAppProviderBinding Binding { get; init; }
    public required string AccessToken { get; init; }
    public required DateTimeOffset ValidUntil { get; init; }

    public override string ToString() => nameof(WhatsAppProviderCredentials);
}

public interface IWhatsAppProviderCredentials
{
    Task<WhatsAppProviderCredentials> ReadAsync(CancellationToken cancellationToken);
}

public interface IWhatsAppWebhookCredentials
{
    Task<string> ReadVerifyTokenAsync(CancellationToken cancellationToken);
    Task<string> ReadAppSecretAsync(CancellationToken cancellationToken);
    Task<WhatsAppProviderBinding> ReadSenderBindingAsync(CancellationToken cancellationToken);
}

public sealed partial class WhatsAppKeyVaultCredentials(
    IHttpClientFactory clients,
    IOptionsMonitor<WhatsAppProviderOptions> options,
    IConfiguration configuration,
    TimeProvider clock
) : IWhatsAppProviderCredentials, IWhatsAppWebhookCredentials
{
    private static readonly JsonSerializerOptions BindingJson = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        PropertyNameCaseInsensitive = false,
    };

    public async Task<WhatsAppProviderCredentials> ReadAsync(CancellationToken cancellationToken)
    {
        var current = options.CurrentValue;
        if (
            !current.Enabled
            || current.Environment != "demo"
            || current.VaultHost != "kv-waooaw-demo.vault.azure.net"
            || !Guid.TryParse(current.ManagedIdentityClientId, out _)
            || !Matches(Version(), current.BindingVersion)
            || !Matches(Version(), current.OutboundAuthorityVersion)
        )
            throw Denied("PROVIDER_CONFIGURATION_DENIED");

        using var suppression = SuppressInstrumentationScope.Begin();
        using var client = clients.CreateClient("WhatsAppProtected");
        try
        {
            var identityToken = await ReadIdentityAsync(client, current, cancellationToken);
            var now = clock.GetUtcNow();
            var bindingValue = await ReadSecretAsync(
                client,
                current,
                "whatsapp-provider-binding",
                current.BindingVersion,
                identityToken,
                now,
                cancellationToken
            );
            var binding = ParseBinding(bindingValue.Value, now);

            var outbound = await ReadSecretAsync(
                client,
                current,
                "whatsapp-outbound-authority",
                current.OutboundAuthorityVersion,
                identityToken,
                now,
                cancellationToken
            );
            if (
                outbound.Value.Length < 32
                || outbound.Value.Length > 8192
                || outbound.Value.Any(char.IsWhiteSpace)
            )
                throw Denied("PROVIDER_AUTHORITY_DENIED");
            return new()
            {
                Binding = binding,
                AccessToken = outbound.Value,
                ValidUntil = new[]
                {
                    now.AddMinutes(5),
                    binding.ExpiresAt,
                    bindingValue.ExpiresAt ?? throw Denied("PROVIDER_SECRET_DENIED"),
                    outbound.ExpiresAt ?? now.AddMinutes(5),
                }.Min(),
            };
        }
        catch (JsonException)
        {
            throw Denied("PROVIDER_AUTHORITY_INVALID");
        }
        catch (HttpRequestException)
        {
            throw Denied("PROVIDER_AUTHORITY_UNAVAILABLE");
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw Denied("PROVIDER_AUTHORITY_UNAVAILABLE");
        }
    }

    public Task<string> ReadVerifyTokenAsync(CancellationToken cancellationToken) =>
        ReadPurposeAsync("whatsapp-verify-token", cancellationToken);

    public Task<string> ReadAppSecretAsync(CancellationToken cancellationToken) =>
        ReadPurposeAsync("whatsapp-app-secret", cancellationToken);

    public async Task<WhatsAppProviderBinding> ReadSenderBindingAsync(
        CancellationToken cancellationToken
    )
    {
        var value = await ReadPurposeAsync("whatsapp-provider-binding", cancellationToken);
        return ParseBinding(value, clock.GetUtcNow());
    }

    private static WhatsAppProviderBinding ParseBinding(string value, DateTimeOffset now)
    {
        WhatsAppProviderBinding? binding;
        try
        {
            using var document = JsonDocument.Parse(value);
            RequireUniqueProperties(document.RootElement);
            binding = document.RootElement.Deserialize<WhatsAppProviderBinding>(BindingJson);
        }
        catch (JsonException)
        {
            throw Denied("PROVIDER_BINDING_DENIED");
        }
        if (
            binding is null
            || binding.Environment != "demo"
            || !Matches(Reference(), binding.BindingVersion)
            || !Matches(Identifier(), binding.AppId)
            || !Matches(Identifier(), binding.WabaId)
            || !Matches(Identifier(), binding.PhoneNumberId)
            || !Matches(Telephone(), binding.RecipientPhoneNumber)
            || !Matches(Digest(), binding.RecipientBindingDigest)
            || !Matches(ApiVersion(), binding.ApiVersion)
            || binding.ApiVersion.Length > 16
            || !Matches(Reference(), binding.AuthorityReference)
            || binding.ValidFrom > now
            || binding.ExpiresAt <= now
        )
            throw Denied("PROVIDER_BINDING_DENIED");
        return binding;
    }

    private async Task<string> ReadPurposeAsync(string name, CancellationToken cancellationToken)
    {
        var current = options.CurrentValue;
        var version = name switch
        {
            "whatsapp-verify-token" => current.VerifyTokenVersion,
            "whatsapp-app-secret" => current.AppSecretVersion,
            "whatsapp-provider-binding" => current.BindingVersion,
            _ => throw Denied("PROVIDER_SECRET_DENIED"),
        };
        if (
            !current.Enabled
            || current.Environment != "demo"
            || current.VaultHost != "kv-waooaw-demo.vault.azure.net"
            || !Guid.TryParse(current.ManagedIdentityClientId, out _)
            || !Matches(Version(), version)
        )
            throw Denied("PROVIDER_CONFIGURATION_DENIED");
        using var suppression = SuppressInstrumentationScope.Begin();
        using var client = clients.CreateClient("WhatsAppProtected");
        try
        {
            var identityToken = await ReadIdentityAsync(client, current, cancellationToken);
            var secret = await ReadSecretAsync(
                client,
                current,
                name,
                version,
                identityToken,
                clock.GetUtcNow(),
                cancellationToken
            );
            if (
                name != "whatsapp-provider-binding"
                && (
                    secret.Value.Length < 32
                    || secret.Value.Length > 1024
                    || secret.Value.Any(char.IsWhiteSpace)
                )
            )
                throw Denied("PROVIDER_SECRET_DENIED");
            return secret.Value;
        }
        catch (JsonException)
        {
            throw Denied("PROVIDER_AUTHORITY_INVALID");
        }
        catch (HttpRequestException)
        {
            throw Denied("PROVIDER_AUTHORITY_UNAVAILABLE");
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw Denied("PROVIDER_AUTHORITY_UNAVAILABLE");
        }
    }

    private async Task<string> ReadIdentityAsync(
        HttpClient client,
        WhatsAppProviderOptions current,
        CancellationToken cancellationToken
    )
    {
        var endpoint = configuration["IDENTITY_ENDPOINT"];
        var header = configuration["IDENTITY_HEADER"];
        if (
            !Uri.TryCreate(endpoint, UriKind.Absolute, out var identityEndpoint)
            || identityEndpoint.Scheme != "http"
            || !identityEndpoint.IsLoopback
            || !string.IsNullOrEmpty(identityEndpoint.UserInfo)
            || !string.IsNullOrEmpty(identityEndpoint.Query)
            || !string.IsNullOrEmpty(identityEndpoint.Fragment)
            || string.IsNullOrWhiteSpace(header)
        )
            throw Denied("WORKLOAD_IDENTITY_UNAVAILABLE");
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            $"{identityEndpoint}?api-version=2019-08-01&resource=https%3A%2F%2Fvault.azure.net"
                + $"&client_id={Uri.EscapeDataString(current.ManagedIdentityClientId)}"
        );
        request.Headers.Add("X-IDENTITY-HEADER", header);
        using var identity = await ReadJsonAsync(client, request, cancellationToken);
        var root = identity.RootElement;
        if (
            root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("access_token", out var token)
            || token.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(token.GetString())
            || !root.TryGetProperty("resource", out var resource)
            || resource.ValueKind != JsonValueKind.String
            || resource.GetString()?.TrimEnd('/') != "https://vault.azure.net"
        )
            throw Denied("WORKLOAD_IDENTITY_DENIED");
        return token.GetString()!;
    }

    private static async Task<(string Value, DateTimeOffset? ExpiresAt)> ReadSecretAsync(
        HttpClient client,
        WhatsAppProviderOptions options,
        string name,
        string version,
        string identityToken,
        DateTimeOffset now,
        CancellationToken cancellationToken
    )
    {
        var uri = $"https://{options.VaultHost}/secrets/{name}/{version}";
        using var request = new HttpRequestMessage(HttpMethod.Get, $"{uri}?api-version=7.4");
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", identityToken);
        using var document = await ReadJsonAsync(client, request, cancellationToken);
        var root = document.RootElement;
        DateTimeOffset? secretExpiry = null;
        if (
            root.ValueKind != JsonValueKind.Object
            || !root.TryGetProperty("id", out var id)
            || id.ValueKind != JsonValueKind.String
            || id.GetString() != uri
            || !root.TryGetProperty("attributes", out var attributes)
            || attributes.ValueKind != JsonValueKind.Object
            || !attributes.TryGetProperty("enabled", out var enabled)
            || enabled.ValueKind != JsonValueKind.True
            || (
                attributes.TryGetProperty("nbf", out var notBefore)
                && (
                    notBefore.ValueKind != JsonValueKind.Number
                    || !notBefore.TryGetInt64(out var startsAt)
                    || startsAt > now.ToUnixTimeSeconds()
                )
            )
            || !root.TryGetProperty("value", out var value)
            || value.ValueKind != JsonValueKind.String
            || string.IsNullOrWhiteSpace(value.GetString())
        )
            throw Denied("PROVIDER_SECRET_DENIED");
        if (attributes.TryGetProperty("exp", out var expiry))
        {
            if (
                expiry.ValueKind != JsonValueKind.Number
                || !expiry.TryGetInt64(out var expiresAt)
                || expiresAt <= now.ToUnixTimeSeconds()
                || expiresAt > 253402300799
            )
                throw Denied("PROVIDER_SECRET_DENIED");
            secretExpiry = DateTimeOffset.FromUnixTimeSeconds(expiresAt);
        }
        else if (name != "whatsapp-outbound-authority")
            throw Denied("PROVIDER_SECRET_DENIED");
        return (value.GetString()!, secretExpiry);
    }

    internal static async Task<JsonDocument> ReadJsonAsync(
        HttpClient client,
        HttpRequestMessage request,
        CancellationToken cancellationToken
    )
    {
        using var response = await client.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            cancellationToken
        );
        if (!response.IsSuccessStatusCode)
            throw Denied("PROVIDER_AUTHORITY_UNAVAILABLE");
        await using var stream = await response.Content.ReadAsStreamAsync(cancellationToken);
        var bytes = new byte[65_537];
        var length = 0;
        while (length < bytes.Length)
        {
            var count = await stream.ReadAsync(bytes.AsMemory(length), cancellationToken);
            if (count == 0)
                break;
            length += count;
        }
        if (length == bytes.Length)
            throw Denied("PROVIDER_AUTHORITY_INVALID");
        var document = JsonDocument.Parse(bytes.AsMemory(0, length));
        try
        {
            RequireUniqueProperties(document.RootElement);
            return document;
        }
        catch (WhatsAppCapabilityUnavailableException)
        {
            document.Dispose();
            throw;
        }
    }

    private static void RequireUniqueProperties(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name))
                    throw Denied("PROVIDER_AUTHORITY_INVALID");
                RequireUniqueProperties(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in element.EnumerateArray())
                RequireUniqueProperties(item);
        }
    }

    private static WhatsAppCapabilityUnavailableException Denied(string code) => new(code);

    [GeneratedRegex("\\A[a-f0-9]{32}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Version();

    [GeneratedRegex("\\A[0-9]{1,32}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Identifier();

    [GeneratedRegex("\\A\\+[1-9][0-9]{7,14}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Telephone();

    [GeneratedRegex("\\A[a-f0-9]{64}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Digest();

    [GeneratedRegex("\\Av[1-9][0-9]*\\.0\\z", RegexOptions.CultureInvariant)]
    private static partial Regex ApiVersion();

    [GeneratedRegex("\\A[A-Za-z0-9][A-Za-z0-9:._/-]{0,255}\\z", RegexOptions.CultureInvariant)]
    private static partial Regex Reference();

    private static bool Matches(Regex pattern, string? value) =>
        value is not null && pattern.IsMatch(value);
}
