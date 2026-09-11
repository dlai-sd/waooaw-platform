// Implements: architecture/reference/components/environment-readiness-and-data-continuity.md §7 Runtime Dependency Isolation
// Constitutional basis: C-023, C-026, C-059

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Route("api/v1/identity/providers")]
public sealed class IdentityProvidersController(
    IdentityProviderProjectionService providerProjectionService,
    IConfiguration configuration) : ControllerBase
{
    [AllowAnonymous]
    [HttpGet]
    public IActionResult GetProviders()
    {
        Response.Headers.CacheControl = "no-store";
        var brokerReadEnabled = configuration.GetValue<bool>("IdentityBrokerRead:Enabled");
        var providers = providerProjectionService.GetProviders()
            .Select(provider => provider.Id != "GOOGLE" || brokerReadEnabled
                ? provider
                : provider with { Availability = "UNAVAILABLE", UnavailableReason = "NOT_CONFIGURED" })
            .ToArray();
        return Ok(new IdentityProviderCollectionResponse(providers));
    }
}