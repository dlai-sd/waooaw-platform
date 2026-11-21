// Implements: work-contracts/WC-137-platform-access-and-environment-feature-settings.md WC137-R003, WC137-R004
// Constitutional basis: C-009, C-023, C-026, C-059, C-063

using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.PlatformAccess;

/// <summary>
/// Adds the staff roles a person holds to the validated token. Roles come only from stored grants matched by
/// verified email and identity-provider subject; a failure to read grants grants nothing.
/// </summary>
public sealed class PlatformRoleClaimsTransformation(
    IPlatformAccessStore store,
    IMemoryCache cache,
    IOptions<PlatformAccessOptions> options,
    TimeProvider clock,
    ILogger<PlatformRoleClaimsTransformation> logger
) : IClaimsTransformation
{
    public async Task<ClaimsPrincipal> TransformAsync(ClaimsPrincipal principal)
    {
        if (
            principal.Identities.Any(identity =>
                identity.AuthenticationType == PlatformRoles.ClaimSourceMarker
            ) || !PlatformRoles.TryIdentity(principal, out var email, out var subject)
        )
            return principal;
        IReadOnlyList<string> roles;
        try
        {
            var key = $"platform-roles:{subject}:{email}";
            var seconds = options.Value.ResolutionCacheSeconds;
            if (seconds == 0 || !cache.TryGetValue(key, out roles!))
            {
                roles = await store.ResolveRolesAsync(email, subject, clock.GetUtcNow(), default);
                if (seconds > 0)
                    cache.Set(key, roles, TimeSpan.FromSeconds(seconds));
            }
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogError(
                exception,
                "Platform role grants could not be read; no staff role added."
            );
            return principal;
        }
        if (roles.Count == 0)
            return principal;
        var identity = new ClaimsIdentity(PlatformRoles.ClaimSourceMarker, null, ClaimTypes.Role);
        foreach (var role in roles)
            identity.AddClaim(new Claim(ClaimTypes.Role, role));
        // The Founder is also a pricing administrator, as the web already treats it.
        if (roles.Contains(PlatformRoles.Founder) && !roles.Contains(PlatformRoles.PricingAdmin))
            identity.AddClaim(new Claim(ClaimTypes.Role, PlatformRoles.PricingAdmin));
        var transformed = new ClaimsPrincipal(principal.Identities);
        transformed.AddIdentity(identity);
        return transformed;
    }
}

/// <summary>Re-asserts the configured Founders at every start, before the first request is served.</summary>
public sealed class PlatformFounderBootstrapService(
    IServiceScopeFactory scopes,
    IOptions<PlatformAccessOptions> options,
    TimeProvider clock,
    ILogger<PlatformFounderBootstrapService> logger
) : IHostedService
{
    public async Task StartAsync(CancellationToken cancellationToken)
    {
        var founders = options.Value.Founders;
        if (founders.Count == 0)
        {
            logger.LogWarning(
                "No Founder is configured in PlatformAccess:Founders; existing Founder grants are unchanged."
            );
            return;
        }
        // A missing table fails the start on purpose: serving without the Founder root of trust is unsafe.
        await using var scope = scopes.CreateAsyncScope();
        var store = scope.ServiceProvider.GetRequiredService<IPlatformAccessStore>();
        await store.ReconcileFoundersAsync(founders, clock.GetUtcNow(), cancellationToken);
        logger.LogInformation(
            "Founder grants reconciled from configuration: count={Count}.",
            founders.Count
        );
    }

    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
