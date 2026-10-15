// Implements: architecture/reference/components/authentication-authorization-simplification-solution-contract.md §10.1
// constitutional_basis: C-023, C-026, C-059, C-063

using System.Net;
using System.Net.Http.Headers;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class IdentityLifecycleWriterOptions
{
    public const string SectionName = "IdentityLifecycleWriter";
    public bool Enabled { get; set; }
    public string PrivateOrigin { get; set; } = "";
    public string[] AllowedPrivateHosts { get; set; } = [];
    public string ClientId { get; set; } = "";
    public string ClientSecret { get; set; } = "";

    public bool IsConfigured =>
        Enabled
        && Uri.TryCreate(PrivateOrigin, UriKind.Absolute, out var origin)
        && origin.Scheme == "https"
        && origin.AbsolutePath == "/"
        && origin.UserInfo == ""
        && origin.Query == ""
        && origin.Fragment == ""
        && AllowedPrivateHosts.Contains(origin.Host, StringComparer.Ordinal)
        && ClientId == "waooaw-bp-identity-lifecycle-writer"
        && !string.IsNullOrWhiteSpace(ClientSecret);
}

public sealed record KeycloakFederatedBinding(
    string ProviderAlias,
    string ProviderUserId,
    string ProviderUsername
);

public sealed class KeycloakLifecycleUnknownOutcomeException()
    : Exception("The Keycloak lifecycle mutation outcome is unknown.");

public sealed class KeycloakLifecycleRejectedException()
    : Exception("The Keycloak lifecycle operation was rejected.");

public interface IKeycloakIdentityLifecycleWriter
{
    bool IsConfigured { get; }
    Task<bool> UserExistsAsync(string userId, CancellationToken ct);
    Task<IReadOnlyList<KeycloakFederatedBinding>> ReadBindingsAsync(
        string userId,
        CancellationToken ct
    );
    Task AddBindingAsync(string userId, KeycloakFederatedBinding binding, CancellationToken ct);
    Task RemoveBindingAsync(string userId, string providerAlias, CancellationToken ct);
}

public sealed class KeycloakIdentityLifecycleWriter(
    HttpClient client,
    IOptions<IdentityLifecycleWriterOptions> options
) : IKeycloakIdentityLifecycleWriter
{
    private static readonly Regex KeyPattern = new(
        "\\A[A-Za-z0-9._:@+-]{1,256}\\z",
        RegexOptions.CultureInvariant
    );
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);
    private readonly IdentityLifecycleWriterOptions _options = options.Value;

    public bool IsConfigured => _options.IsConfigured;

    public async Task<bool> UserExistsAsync(string userId, CancellationToken ct)
    {
        ValidateUserId(userId);
        using var request = await RequestAsync(
            HttpMethod.Get,
            $"admin/realms/waooaw/users/{Uri.EscapeDataString(userId)}",
            ct
        );
        using var response = await client.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            ct
        );
        return response.StatusCode switch
        {
            HttpStatusCode.OK => true,
            HttpStatusCode.NotFound => false,
            _ => throw new KeycloakLifecycleRejectedException(),
        };
    }

    public async Task<IReadOnlyList<KeycloakFederatedBinding>> ReadBindingsAsync(
        string userId,
        CancellationToken ct
    )
    {
        ValidateUserId(userId);
        using var request = await RequestAsync(
            HttpMethod.Get,
            $"admin/realms/waooaw/users/{Uri.EscapeDataString(userId)}/federated-identity",
            ct
        );
        using var response = await client.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            ct
        );
        if (response.StatusCode != HttpStatusCode.OK)
            throw new KeycloakLifecycleRejectedException();
        var payload = await response.Content.ReadFromJsonAsync<JsonElement>(JsonOptions, ct);
        if (payload.ValueKind != JsonValueKind.Array)
            throw new KeycloakLifecycleRejectedException();
        var bindings = new List<KeycloakFederatedBinding>();
        foreach (var item in payload.EnumerateArray())
        {
            var alias = RequiredString(item, "identityProvider");
            var providerUserId = RequiredString(item, "userId");
            var providerUsername = RequiredString(item, "userName");
            if (!AllowedProvider(alias))
                continue;
            bindings.Add(new(alias, providerUserId, providerUsername));
        }
        return bindings;
    }

    public Task AddBindingAsync(
        string userId,
        KeycloakFederatedBinding binding,
        CancellationToken ct
    ) => MutateBindingAsync(HttpMethod.Post, userId, binding, ct);

    public Task RemoveBindingAsync(string userId, string providerAlias, CancellationToken ct) =>
        MutateBindingAsync(
            HttpMethod.Delete,
            userId,
            new KeycloakFederatedBinding(providerAlias, "unused", "unused"),
            ct
        );

    private async Task MutateBindingAsync(
        HttpMethod method,
        string userId,
        KeycloakFederatedBinding binding,
        CancellationToken ct
    )
    {
        ValidateUserId(userId);
        if (
            !AllowedProvider(binding.ProviderAlias)
            || (
                method == HttpMethod.Post
                && (
                    !KeyPattern.IsMatch(binding.ProviderUserId)
                    || !KeyPattern.IsMatch(binding.ProviderUsername)
                )
            )
        )
            throw new ArgumentException("Invalid lifecycle binding.");

        using var request = await RequestAsync(
            method,
            $"admin/realms/waooaw/users/{Uri.EscapeDataString(userId)}/federated-identity/{binding.ProviderAlias}",
            ct
        );
        if (method == HttpMethod.Post)
            request.Content = JsonContent.Create(
                new
                {
                    identityProvider = binding.ProviderAlias,
                    userId = binding.ProviderUserId,
                    userName = binding.ProviderUsername,
                },
                options: JsonOptions
            );
        try
        {
            using var response = await client.SendAsync(
                request,
                HttpCompletionOption.ResponseHeadersRead,
                ct
            );
            var accepted =
                method == HttpMethod.Post
                    ? response.StatusCode == HttpStatusCode.OK
                    : response.StatusCode == HttpStatusCode.NoContent;
            if (!accepted)
                throw new KeycloakLifecycleRejectedException();
        }
        catch (OperationCanceledException) when (!ct.IsCancellationRequested)
        {
            throw new KeycloakLifecycleUnknownOutcomeException();
        }
        catch (HttpRequestException)
        {
            throw new KeycloakLifecycleUnknownOutcomeException();
        }
    }

    private async Task<HttpRequestMessage> RequestAsync(
        HttpMethod method,
        string relativePath,
        CancellationToken ct
    )
    {
        if (!_options.IsConfigured)
            throw new KeycloakLifecycleRejectedException();
        var token = await AccessTokenAsync(ct);
        var request = new HttpRequestMessage(
            method,
            new Uri(new Uri(_options.PrivateOrigin), relativePath)
        );
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return request;
    }

    private async Task<string> AccessTokenAsync(CancellationToken ct)
    {
        using var request = new HttpRequestMessage(
            HttpMethod.Post,
            new Uri(new Uri(_options.PrivateOrigin), "realms/waooaw/protocol/openid-connect/token")
        )
        {
            Content = new FormUrlEncodedContent(
                new Dictionary<string, string>
                {
                    ["grant_type"] = "client_credentials",
                    ["client_id"] = _options.ClientId,
                    ["client_secret"] = _options.ClientSecret,
                }
            ),
        };
        using var response = await client.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            ct
        );
        if (response.StatusCode != HttpStatusCode.OK)
            throw new KeycloakLifecycleRejectedException();
        var payload = await response.Content.ReadFromJsonAsync<JsonElement>(JsonOptions, ct);
        var token = RequiredString(payload, "access_token");
        if (
            !payload.TryGetProperty("expires_in", out var expires)
            || expires.ValueKind != JsonValueKind.Number
            || !expires.TryGetInt32(out var seconds)
            || seconds is < 1 or > 60
        )
            throw new KeycloakLifecycleRejectedException();
        return token;
    }

    private static string RequiredString(JsonElement payload, string property)
    {
        if (
            !payload.TryGetProperty(property, out var value)
            || value.ValueKind != JsonValueKind.String
            || value.GetString() is not { Length: > 0 } result
        )
            throw new KeycloakLifecycleRejectedException();
        return result;
    }

    private static bool AllowedProvider(string provider) =>
        provider is "google" or "facebook" or "apple";

    private static void ValidateUserId(string userId)
    {
        if (!KeyPattern.IsMatch(userId) || userId is "." or "..")
            throw new ArgumentException("Invalid Keycloak user reference.");
    }
}
