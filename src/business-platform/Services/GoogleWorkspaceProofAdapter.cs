// Implements: adr/ADR-008-keycloak-identity-broker.md Amendment 3
// constitutional_basis: C-023, C-026, C-059

using System.IdentityModel.Tokens.Jwt;
using System.Net.Http.Headers;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed class IdentityBrokerReadOptions
{
    public const string SectionName = "IdentityBrokerRead";
    public bool Enabled { get; set; }
    public string ActorIssuer { get; set; } = "";
    public string PrivateOrigin { get; set; } = "";
    public string[] AllowedPrivateHosts { get; set; } = [];
    public string ClientId { get; set; } = "";
    public string ClientSecret { get; set; } = "";
    public Dictionary<string, IdentityBrokerProviderOptions> Providers { get; set; } =
        new(StringComparer.Ordinal);

    public bool IsConfigured =>
        Enabled
        && Uri.TryCreate(ActorIssuer, UriKind.Absolute, out var issuer)
        && issuer.Scheme == "https"
        && issuer.AbsolutePath == "/realms/waooaw"
        && issuer.Query == ""
        && issuer.Fragment == ""
        && issuer.UserInfo == ""
        && Uri.TryCreate(PrivateOrigin, UriKind.Absolute, out var origin)
        && origin.Scheme == "https"
        && origin.AbsolutePath == "/"
        && origin.UserInfo == ""
        && origin.Query == ""
        && origin.Fragment == ""
        && AllowedPrivateHosts.Contains(origin.Host, StringComparer.Ordinal)
        && ClientId == "waooaw-bp-identity-reader"
        && !string.IsNullOrWhiteSpace(ClientSecret)
        && Providers.Count > 0
        && Providers.All(provider =>
            provider.Key is "google" or "facebook"
            && GoogleWorkspaceProofAdapter.ValidKey(provider.Value.ProviderNamespace)
            && Regex.IsMatch(
                provider.Value.TrustConfigDigest,
                "\\A[0-9a-f]{64}\\z",
                RegexOptions.CultureInvariant
            )
        )
        && Providers
            .Values.Select(provider => provider.ProviderNamespace)
            .Distinct(StringComparer.Ordinal)
            .Count() == Providers.Count;
}

public sealed class IdentityBrokerProviderOptions
{
    public string ProviderNamespace { get; set; } = "";
    public string TrustConfigDigest { get; set; } = "";
}

public sealed class GoogleWorkspaceProofAdapter(
    HttpClient client,
    IOptions<IdentityBrokerReadOptions> options,
    ILogger<GoogleWorkspaceProofAdapter>? logger = null
)
{
    private readonly IdentityBrokerReadOptions _options = options.Value;

    public bool IsConfigured => _options.IsConfigured;

    public CustomerWorkspaceTrust TrustFor(ClaimsPrincipal principal)
    {
        var (alias, provider) = ConfiguredProvider(principal);
        return new(
            _options.ActorIssuer,
            provider.ProviderNamespace,
            alias,
            provider.TrustConfigDigest
        );
    }

    public IdentityAuthenticationPath AuthenticationPath(ClaimsPrincipal principal) =>
        ConfiguredProvider(principal).alias switch
        {
            "google" => IdentityAuthenticationPath.Google,
            "facebook" => IdentityAuthenticationPath.Meta,
            _ => Denied<IdentityAuthenticationPath>("unsupported_provider"),
        };

    public VerifiedCustomerActor ValidateActor(ClaimsPrincipal principal, bool requireFresh = false)
    {
        RequireConfiguration();
        ConfiguredProvider(principal);
        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        var subject = principal.HasClaim(claim => claim.Type == "sub")
            ? SingleClaim(principal, "sub")
            : SingleClaim(principal, ClaimTypes.NameIdentifier);
        var issuer = SingleClaim(principal, "iss");
        if (principal.Identity?.IsAuthenticated != true)
            return Denied<VerifiedCustomerActor>("actor_unauthenticated");
        if (issuer != _options.ActorIssuer)
            return Denied<VerifiedCustomerActor>("actor_issuer");
        if (
            !ValidKey(subject)
            || subject is "." or ".."
            || subject!.StartsWith("service-account-", StringComparison.Ordinal)
        )
            return Denied<VerifiedCustomerActor>("actor_subject");
        if (SingleClaim(principal, "azp") != "waooaw-web")
            return Denied<VerifiedCustomerActor>("actor_client");
        if (!principal.FindAll("aud").Any(claim => claim.Value == "waooaw-platform"))
            return Denied<VerifiedCustomerActor>("actor_audience");
        if (SingleClaim(principal, "email_verified") != "true")
            return Denied<VerifiedCustomerActor>("actor_email_verification");
        if (principal.HasClaim("client_type", "service"))
            return Denied<VerifiedCustomerActor>("actor_service_client");
        if (!CustomerRolesOnly(principal))
            return Denied<VerifiedCustomerActor>("actor_roles");
        if (!Timestamp(principal, "iat", out var issued) || issued > now + 30)
            return Denied<VerifiedCustomerActor>("actor_issued_at");
        if (!Timestamp(principal, "exp", out var expires) || expires <= now - 30)
            return Denied<VerifiedCustomerActor>("actor_expiry");
        if (expires <= issued || expires - issued > 900)
            return Denied<VerifiedCustomerActor>("actor_lifetime");
        if (!Timestamp(principal, "auth_time", out var authenticated) || authenticated > now + 30)
            return Denied<VerifiedCustomerActor>("actor_auth_time");
        if (authenticated > issued + 30)
            return Denied<VerifiedCustomerActor>("actor_auth_order");
        if (
            principal.HasClaim(claim => claim.Type == "nbf")
            && (!Timestamp(principal, "nbf", out var notBefore) || notBefore > now + 30)
        )
            return Denied<VerifiedCustomerActor>("actor_not_before");
        if (requireFresh && now - authenticated > 300)
            throw new CustomerWorkspaceException(
                CustomerWorkspaceError.FreshAuthenticationRequired
            );
        return new VerifiedCustomerActor(issuer!, subject!);
    }

    public async Task<VerifiedGoogleWorkspaceProof> ReadAsync(
        ClaimsPrincipal principal,
        CancellationToken ct
    )
    {
        var (brokerAlias, provider) = ConfiguredProvider(principal);
        var actor = ValidateActor(principal, requireFresh: true);
        using var timeout = CancellationTokenSource.CreateLinkedTokenSource(ct);
        timeout.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            using var tokenRequest = new HttpRequestMessage(
                HttpMethod.Post,
                new Uri(
                    new Uri(_options.PrivateOrigin),
                    "/realms/waooaw/protocol/openid-connect/token"
                )
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
            using var token = await SendAsync(tokenRequest, timeout.Token);
            if (
                token.RootElement.GetProperty("token_type").GetString() != "Bearer"
                || !token.RootElement.GetProperty("expires_in").TryGetInt32(out var lifetime)
                || lifetime is <= 0 or > 60
                || token.RootElement.TryGetProperty("refresh_token", out _)
            )
                throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
            var accessToken = token.RootElement.GetProperty("access_token").GetString();
            if (string.IsNullOrWhiteSpace(accessToken))
                throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
            var path = "/admin/realms/waooaw/users/" + Uri.EscapeDataString(actor.Subject);
            using var user = await ReadUserAsync(path, accessToken, timeout.Token);
            var root = user.RootElement;
            if (
                root.GetProperty("id").GetString() != actor.Subject
                || root.GetProperty("enabled").ValueKind != JsonValueKind.True
                || root.GetProperty("emailVerified").ValueKind != JsonValueKind.True
                || root.TryGetProperty("serviceAccountClientId", out var serviceAccount)
                    && serviceAccount.ValueKind != JsonValueKind.Null
                || root.TryGetProperty("username", out var username)
                    && username
                        .GetString()
                        ?.StartsWith("service-account-", StringComparison.Ordinal) == true
            )
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            using var bindings = await ReadUserAsync(
                path + "/federated-identity",
                accessToken,
                timeout.Token
            );
            if (
                bindings.RootElement.ValueKind != JsonValueKind.Array
                || bindings.RootElement.GetArrayLength() != 1
            )
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            var binding = bindings.RootElement[0];
            var providerSubject = binding.GetProperty("userId").GetString();
            if (
                binding.GetProperty("identityProvider").GetString() != brokerAlias
                || !ValidKey(providerSubject)
            )
                throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
            ValidateActor(principal, requireFresh: true);
            return new VerifiedGoogleWorkspaceProof(
                actor,
                provider.ProviderNamespace,
                brokerAlias,
                providerSubject!,
                DateTimeOffset.UtcNow,
                DateTimeOffset.FromUnixTimeSeconds(
                    long.Parse(SingleClaim(principal, "auth_time")!)
                ),
                provider.TrustConfigDigest,
                Guid.NewGuid()
            );
        }
        catch (Exception exception)
            when (exception
                    is HttpRequestException
                        or JsonException
                        or InvalidOperationException
                        or KeyNotFoundException
                        or FormatException
                || exception is OperationCanceledException && !ct.IsCancellationRequested
            )
        {
            throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
        }
    }

    private async Task<JsonDocument> ReadUserAsync(string path, string token, CancellationToken ct)
    {
        using var request = new HttpRequestMessage(
            HttpMethod.Get,
            new Uri(new Uri(_options.PrivateOrigin), path)
        );
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", token);
        return await SendAsync(request, ct);
    }

    private async Task<JsonDocument> SendAsync(HttpRequestMessage request, CancellationToken ct)
    {
        using var response = await client.SendAsync(
            request,
            HttpCompletionOption.ResponseHeadersRead,
            ct
        );
        if (!response.IsSuccessStatusCode)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
        await using var stream = await response.Content.ReadAsStreamAsync(ct);
        using var buffer = new MemoryStream();
        var chunk = new byte[4096];
        int count;
        while ((count = await stream.ReadAsync(chunk, ct)) != 0)
        {
            if (buffer.Length + count > 16384)
                throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
            buffer.Write(chunk, 0, count);
        }
        var document = JsonDocument.Parse(
            buffer.ToArray(),
            new JsonDocumentOptions { MaxDepth = 16 }
        );
        try
        {
            RejectDuplicateProperties(document.RootElement);
        }
        catch
        {
            document.Dispose();
            throw;
        }
        return document;
    }

    private static void RejectDuplicateProperties(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var property in element.EnumerateObject())
            {
                if (!names.Add(property.Name))
                    throw new JsonException();
                RejectDuplicateProperties(property.Value);
            }
        }
        else if (element.ValueKind == JsonValueKind.Array)
            foreach (var item in element.EnumerateArray())
                RejectDuplicateProperties(item);
    }

    private void RequireConfiguration()
    {
        if (!_options.IsConfigured)
            throw new CustomerWorkspaceException(CustomerWorkspaceError.DependencyUnavailable);
    }

    private (string alias, IdentityBrokerProviderOptions provider) ConfiguredProvider(
        ClaimsPrincipal principal
    )
    {
        RequireConfiguration();
        var alias = SingleClaim(principal, "idp");
        if (alias is null || !_options.Providers.TryGetValue(alias, out var provider))
            return Denied<(string, IdentityBrokerProviderOptions)>("actor_provider");
        return (alias, provider);
    }

    private T Denied<T>(string rule)
    {
        logger?.LogWarning("Customer identity actor denied by {Rule}", rule);
        throw new IdentityActionDeniedException("IDENTITY_ACTION_DENIED");
    }

    internal static bool ValidKey(string? value) =>
        !string.IsNullOrWhiteSpace(value)
        && Encoding.UTF8.GetByteCount(value) <= 256
        && !value.Any(char.IsControl)
        && !value.Any(char.IsSurrogate);

    internal static string? SingleClaim(ClaimsPrincipal principal, string type)
    {
        var claims = principal.FindAll(type).ToArray();
        if (
            claims.Length == 0
            && JwtSecurityTokenHandler.DefaultInboundClaimTypeMap.TryGetValue(type, out var mapped)
        )
            claims = principal.FindAll(mapped).ToArray();
        return claims.Length == 1 ? claims[0].Value : null;
    }

    private static bool Timestamp(ClaimsPrincipal principal, string type, out long value) =>
        long.TryParse(SingleClaim(principal, type), out value)
        && value > 0
        && value <= 253402300799;

    private static bool CustomerRolesOnly(ClaimsPrincipal principal)
    {
        try
        {
            using var realm = JsonDocument.Parse(SingleClaim(principal, "realm_access") ?? "{}");
            var roles = realm
                .RootElement.GetProperty("roles")
                .EnumerateArray()
                .Select(role => role.GetString())
                .ToArray();
            return roles.Contains("customer", StringComparer.Ordinal)
                && roles.All(role =>
                    role
                        is "customer"
                            or "offline_access"
                            or "uma_authorization"
                            or "default-roles-waooaw"
                )
                && !principal
                    .FindAll(ClaimTypes.Role)
                    .Concat(principal.FindAll("role"))
                    .Any(role =>
                        role.Value
                            is not (
                                "customer"
                                or "offline_access"
                                or "uma_authorization"
                                or "default-roles-waooaw"
                            )
                    );
        }
        catch (Exception exception)
            when (exception is JsonException or KeyNotFoundException or InvalidOperationException)
        {
            return false;
        }
    }
}
