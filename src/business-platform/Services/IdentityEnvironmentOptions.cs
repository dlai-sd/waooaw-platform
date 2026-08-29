// Implements: architecture/reference/components/identity-boundary.md §7.3
// constitutional_basis: C-023, C-026, C-059

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services;

public sealed class IdentityEnvironmentOptions
{
    public const string SectionName = "IdentityEnvironment";

    public string SchemaVersion { get; set; } = string.Empty;
    public string Environment { get; set; } = string.Empty;
    public IdentityOriginsOptions Origins { get; set; } = new();
    public IdentityKeycloakOptions Keycloak { get; set; } = new();
    public List<IdentityClientOptions> Clients { get; set; } = [];
    public IdentityChannelOptions Channels { get; set; } = new();
    public IdentityCookieOptions Cookie { get; set; } = new();
    public IdentityEdgeOptions IdentityEdge { get; set; } = new();
    public PhoneIdentityOptions PhoneIdentity { get; set; } = new();
    public List<IdentityProviderOptions> Providers { get; set; } = [];
}

public sealed class IdentityOriginsOptions
{
    public string Web { get; set; } = string.Empty;
    public string Api { get; set; } = string.Empty;
    public string Identity { get; set; } = string.Empty;
}

public sealed class IdentityKeycloakOptions
{
    public string Issuer { get; set; } = string.Empty;
    public string Audience { get; set; } = string.Empty;
    public string JwksUri { get; set; } = string.Empty;
    public string Realm { get; set; } = string.Empty;
    public int AccessTokenMinutes { get; set; }
    public int RefreshSessionHours { get; set; }
    public int ClockSkewSeconds { get; set; }
}

public sealed class IdentityClientOptions
{
    public string Id { get; set; } = string.Empty;
    public string Channel { get; set; } = string.Empty;
    public bool PkceRequired { get; set; }
    public List<string> RedirectUris { get; set; } = [];
    public List<string> PostLogoutRedirectUris { get; set; } = [];
    public List<string> AllowedOrigins { get; set; } = [];
    public List<string> Scopes { get; set; } = [];
}

public sealed class IdentityChannelOptions
{
    public bool Web { get; set; }
    public bool Mobile { get; set; }
    public bool WhatsApp { get; set; }
}

public sealed class IdentityCookieOptions
{
    public string Name { get; set; } = string.Empty;
    public bool Secure { get; set; }
    public string SameSite { get; set; } = string.Empty;
}

public sealed class IdentityEdgeOptions
{
    public string Image { get; set; } = string.Empty;
    public string RoutePolicy { get; set; } = string.Empty;
}

public sealed class PhoneIdentityOptions
{
    public string InternalAudience { get; set; } = string.Empty;
}

public sealed class IdentityProviderOptions
{
    public string Id { get; set; } = string.Empty;
    public string DisplayName { get; set; } = string.Empty;
    public string AuthenticationPath { get; set; } = string.Empty;
    public bool Enabled { get; set; }
    public string? UnavailableReason { get; set; }
    public string? BrokerAlias { get; set; }
    public List<string> Scopes { get; set; } = [];
    public string? SecretReference { get; set; }
    public string? ReadinessEvidenceReference { get; set; }
}

public sealed class IdentityEnvironmentOptionsValidator : IValidateOptions<IdentityEnvironmentOptions>
{
    private static readonly string[] RequiredProviderIds = ["GOOGLE", "FACEBOOK", "APPLE", "EMAIL"];
    private static readonly HashSet<string> AuthenticationPaths =
        new(["GOOGLE", "META", "APPLE", "CREDENTIAL"], StringComparer.Ordinal);
    private static readonly HashSet<string> UnavailableReasons =
        new(["NOT_CONFIGURED", "TEMPORARILY_UNAVAILABLE"], StringComparer.Ordinal);

    public ValidateOptionsResult Validate(string? name, IdentityEnvironmentOptions options)
    {
        var errors = new List<string>();

        if (options.SchemaVersion != "1.0")
            errors.Add("IdentityEnvironment:SchemaVersion must be 1.0.");
        if (!new[] { "local", "demo", "uat", "prod" }.Contains(options.Environment, StringComparer.Ordinal))
            errors.Add("IdentityEnvironment:Environment must be local, demo, uat, or prod.");

        ValidateOrigins(options, errors);

        if (options.Keycloak.Audience != "waooaw-platform")
            errors.Add("IdentityEnvironment:Keycloak:Audience must be waooaw-platform.");
        if (options.Keycloak.Realm != "waooaw")
            errors.Add("IdentityEnvironment:Keycloak:Realm must be waooaw.");
        if (options.Keycloak.AccessTokenMinutes != 15 || options.Keycloak.RefreshSessionHours != 8)
            errors.Add("IdentityEnvironment Keycloak token lifetimes must be 15 minutes and 8 hours.");
        if (options.Keycloak.ClockSkewSeconds is < 0 or > 60)
            errors.Add("IdentityEnvironment Keycloak clock skew must be between 0 and 60 seconds.");
        if (!Uri.TryCreate(options.Keycloak.Issuer, UriKind.Absolute, out var issuer)
            || !Uri.TryCreate(options.Keycloak.JwksUri, UriKind.Absolute, out var jwks)
            || issuer.Scheme != jwks.Scheme || issuer.Host != jwks.Host
            || !options.Keycloak.JwksUri.StartsWith(options.Keycloak.Issuer + "/", StringComparison.Ordinal))
        {
            errors.Add("IdentityEnvironment Keycloak issuer and JWKS URI must share one exact origin and realm.");
        }

        if (options.Clients.Count != 2
            || !options.Clients.Select(client => client.Channel).Order(StringComparer.Ordinal)
                .SequenceEqual(["MOBILE", "WEB"], StringComparer.Ordinal))
            errors.Add("IdentityEnvironment clients must define exactly WEB and MOBILE.");
        foreach (var client in options.Clients)
            ValidateClient(options, client, errors);

        foreach (var value in new[] { options.Origins.Web, options.Origins.Api, options.Origins.Identity }
            .Concat(options.Clients.SelectMany(client => client.RedirectUris
                .Concat(client.PostLogoutRedirectUris)
                .Concat(client.AllowedOrigins))))
        {
            if (Uri.TryCreate(value, UriKind.Absolute, out var uri)
                && !BelongsToEnvironment(uri.Host, options.Environment))
                errors.Add($"IdentityEnvironment URI {value} does not belong to {options.Environment}.");
        }

        if (!options.Channels.Web || !options.Channels.WhatsApp)
            errors.Add("IdentityEnvironment web and WhatsApp channels must be explicitly enabled.");
        if (string.IsNullOrWhiteSpace(options.Cookie.Name)
            || options.Cookie.SameSite is not ("Lax" or "Strict"))
            errors.Add("IdentityEnvironment cookie name and SameSite policy are required.");
        if (options.Environment != "local" && !options.Cookie.Secure)
            errors.Add("IdentityEnvironment cookies must be secure outside local Docker.");
        if (string.IsNullOrWhiteSpace(options.IdentityEdge.Image)
            || string.IsNullOrWhiteSpace(options.IdentityEdge.RoutePolicy))
            errors.Add("IdentityEnvironment identity-edge image and route-policy references are required.");
        if (string.IsNullOrWhiteSpace(options.PhoneIdentity.InternalAudience))
            errors.Add("IdentityEnvironment Phone Identity internal audience is required.");

        var ids = options.Providers.Select(provider => provider.Id).ToArray();
        if (!ids.SequenceEqual(RequiredProviderIds, StringComparer.Ordinal))
            errors.Add("IdentityEnvironment:Providers must contain GOOGLE, FACEBOOK, APPLE, and EMAIL in that order.");
        var brokerAliases = options.Providers
            .Where(provider => !string.IsNullOrWhiteSpace(provider.BrokerAlias))
            .Select(provider => provider.BrokerAlias!);
        if (brokerAliases.Count() != brokerAliases.Distinct(StringComparer.Ordinal).Count())
            errors.Add("IdentityEnvironment provider broker aliases must be unique.");

        foreach (var provider in options.Providers)
        {
            var prefix = $"IdentityEnvironment provider {provider.Id}";
            if (string.IsNullOrWhiteSpace(provider.DisplayName) || provider.DisplayName.Length > 40)
                errors.Add($"{prefix} requires a display name no longer than 40 characters.");
            if (!AuthenticationPaths.Contains(provider.AuthenticationPath))
                errors.Add($"{prefix} has an unsupported authentication path.");
            if (provider.Scopes.Count != provider.Scopes.Distinct(StringComparer.Ordinal).Count())
                errors.Add($"{prefix} contains duplicate scopes.");
            if (provider.Id == "FACEBOOK"
                && !provider.Scopes.SequenceEqual(["email", "public_profile"], StringComparer.Ordinal))
                errors.Add($"{prefix} scopes must be exactly email and public_profile.");
            if (provider.Enabled)
            {
                if (!string.IsNullOrEmpty(provider.UnavailableReason))
                    errors.Add($"{prefix} cannot have an unavailable reason when enabled.");
                if (provider.Id != "EMAIL" && string.IsNullOrWhiteSpace(provider.BrokerAlias))
                    errors.Add($"{prefix} requires a broker alias when enabled.");
                if (provider.Id != "EMAIL" && string.IsNullOrWhiteSpace(provider.SecretReference))
                    errors.Add($"{prefix} requires a secret reference when enabled.");
                if (string.IsNullOrWhiteSpace(provider.ReadinessEvidenceReference))
                    errors.Add($"{prefix} requires accepted readiness evidence when enabled.");
            }
            else if (string.IsNullOrWhiteSpace(provider.UnavailableReason)
                || !UnavailableReasons.Contains(provider.UnavailableReason))
            {
                errors.Add($"{prefix} requires a generic unavailable reason when disabled.");
            }

            if (provider.SecretReference is { } secretReference
                && (!secretReference.StartsWith("kv://", StringComparison.Ordinal)
                    || secretReference.Contains('=')))
            {
                errors.Add($"{prefix} secret reference must be a Key Vault reference, not secret material.");
            }
        }

        return errors.Count == 0
            ? ValidateOptionsResult.Success
            : ValidateOptionsResult.Fail(errors);
    }

    private static void ValidateOrigins(IdentityEnvironmentOptions options, List<string> errors)
    {
        var values = new[] { options.Origins.Web, options.Origins.Api, options.Origins.Identity };
        foreach (var value in values)
        {
            if (!Uri.TryCreate(value, UriKind.Absolute, out var uri)
                || (options.Environment == "local" ? uri.Scheme is not ("http" or "https") : uri.Scheme != "https")
                || value.Contains('*'))
                errors.Add("IdentityEnvironment origins must be exact absolute URLs and HTTPS outside local Docker.");
        }
    }

    private static void ValidateClient(
        IdentityEnvironmentOptions options,
        IdentityClientOptions client,
        List<string> errors)
    {
        var prefix = $"IdentityEnvironment client {client.Id}";
        if (string.IsNullOrWhiteSpace(client.Id) || client.Channel is not ("WEB" or "MOBILE"))
            errors.Add($"{prefix} requires an ID and WEB or MOBILE channel.");
        if (!client.PkceRequired)
            errors.Add($"{prefix} must require PKCE.");
        if (!client.Scopes.Contains("openid", StringComparer.Ordinal))
            errors.Add($"{prefix} must request openid.");
        if (client.RedirectUris.Count == 0 || client.PostLogoutRedirectUris.Count == 0)
            errors.Add($"{prefix} requires redirect and post-logout URI allowlists.");

        foreach (var value in client.RedirectUris
            .Concat(client.PostLogoutRedirectUris)
            .Concat(client.AllowedOrigins))
        {
            if (!Uri.TryCreate(value, UriKind.Absolute, out var uri)
                || value.Contains('*')
                || (options.Environment != "local" && uri.Scheme != "https"))
                errors.Add($"{prefix} contains a wildcard, relative, or non-HTTPS URI.");
        }
    }

    private static bool BelongsToEnvironment(string host, string environment) => environment switch
    {
        "local" => host is "localhost" or "127.0.0.1" || host.Contains(".local.", StringComparison.Ordinal)
            || host.EndsWith(".local", StringComparison.Ordinal),
        "demo" => host.EndsWith(".demo.waooaw.com", StringComparison.Ordinal),
        "uat" => host.EndsWith(".uat.waooaw.com", StringComparison.Ordinal),
        "prod" => (host == "waooaw.com" || host.EndsWith(".waooaw.com", StringComparison.Ordinal))
            && !host.EndsWith(".demo.waooaw.com", StringComparison.Ordinal)
            && !host.EndsWith(".uat.waooaw.com", StringComparison.Ordinal),
        _ => false,
    };
}

public sealed record IdentityProviderProjection(
    string Id,
    string DisplayName,
    string AuthenticationPath,
    string Availability,
    string? UnavailableReason);

public sealed class IdentityProviderProjectionService(IOptions<IdentityEnvironmentOptions> options)
{
    private readonly IdentityEnvironmentOptions _options = options.Value;

    public bool IsAvailable(string providerId) =>
        _options.Providers.Any(provider => provider.Id == providerId && provider.Enabled);

    public IReadOnlyList<IdentityProviderProjection> GetProviders() =>
        _options.Providers
            .Select(provider => new IdentityProviderProjection(
                provider.Id,
                provider.DisplayName,
                provider.AuthenticationPath,
                provider.Enabled ? "AVAILABLE" : "UNAVAILABLE",
                provider.Enabled ? null : provider.UnavailableReason))
            .ToArray();
}
