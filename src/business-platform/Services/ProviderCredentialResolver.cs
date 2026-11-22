// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R003
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.WorkloadIdentity;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>The ACTIVE Key Vault secret reference for a provider. Names the secret and version; never carries the value.</summary>
public sealed record ResolvedProviderCredential(
    string ProviderName,
    string SecretName,
    string SecretVersion,
    string AuthStyle
);

public sealed record ResolveProviderCredentialRequest(string? ProviderName);

public interface IProviderCredentialResolver
{
    /// <summary>Null when the provider has no active credential (not set, or the provider is disabled).</summary>
    Task<ResolvedProviderCredential?> ResolveAsync(string providerName, CancellationToken ct);
}

public sealed class ProviderCredentialResolver(
    IDbContextFactory<ProviderRegistryDbContext> dbFactory
) : IProviderCredentialResolver
{
    public async Task<ResolvedProviderCredential?> ResolveAsync(
        string providerName,
        CancellationToken ct
    )
    {
        if (!ProviderSecretNames.IsValidProviderName(providerName))
            return null;
        await using var db = await dbFactory.CreateDbContextAsync(ct);
        var provider = await db
            .ProviderConfigs.AsNoTracking()
            .SingleOrDefaultAsync(
                p =>
                    p.TenantId == null
                    && p.ProviderName == providerName
                    && p.Active
                    && p.ActiveCredentialVersionId != null
                    && (p.AuthMethod == "API_KEY" || p.TestAuthScheme == "META_APP"),
                ct
            );
        if (provider?.ActiveCredentialVersionId is not { } versionId)
            return null;
        var version = await db
            .ProviderCredentialVersions.AsNoTracking()
            .SingleOrDefaultAsync(
                v => v.Id == versionId && v.Status == ProviderCredentialStatuses.Active,
                ct
            );
        return version is null
            ? null
            : new ResolvedProviderCredential(
                provider.ProviderName,
                version.VaultSecretName,
                version.VaultSecretVersion,
                AuthStyleOf(provider)
            );
    }

    internal static string AuthStyleOf(ProviderConfig provider) =>
        provider.TestAuthScheme switch
        {
            ProviderAuthSchemes.XApiKey => "x-api-key",
            ProviderAuthSchemes.XGoogApiKey => "x-goog-api-key",
            ProviderAuthSchemes.SubscriptionKey => "api-subscription-key",
            ProviderAuthSchemes.MetaApp => "meta-app",
            ProviderAuthSchemes.Header when !string.IsNullOrEmpty(provider.TestAuthHeader) =>
                provider.TestAuthHeader,
            _ => "bearer",
        };
}

/// <summary>Authenticates the AI runtime workload for platform-level (tenant-free) calls to this service.</summary>
public sealed class ProviderCredentialWorkloadAuthority(InferenceWorkloadValidator validator)
{
    public const string Purpose = "PROVIDER_CREDENTIAL_RESOLVE";
    public const string Route = "/internal/v1/provider-credentials/resolve";
    public const string Operation = "resolveProviderCredential";

    public async Task RequireAsync(HttpContext http, string digest, CancellationToken ct)
    {
        try
        {
            await validator.RequirePlatformAsync(
                http,
                "ai-runtime",
                "business-platform",
                Purpose,
                Route,
                Operation,
                digest,
                ct,
                "WORKLOAD"
            );
        }
        catch (InferenceWorkloadRejectedException)
        {
            throw new ProviderAuthorityDeniedException();
        }
    }
}

public sealed class ProviderAuthorityDeniedException : Exception;
