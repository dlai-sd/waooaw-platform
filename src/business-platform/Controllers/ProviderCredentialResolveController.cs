// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R003
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// The AI runtime asks which Key Vault secret version holds a provider's ACTIVE credential. The caller is an ADR-046
/// workload (mTLS, signed envelope bound to the request digest); the answer is a reference, never a secret value.
/// </summary>
[ApiController]
[AllowAnonymous]
[Route("internal/v1/provider-credentials")]
public sealed class ProviderCredentialResolveController(
    ProviderCredentialWorkloadAuthority authority,
    IProviderCredentialResolver resolver,
    ILogger<ProviderCredentialResolveController> logger
) : ControllerBase
{
    [HttpPost("resolve")]
    [RequestSizeLimit(4096)]
    public async Task<IActionResult> ResolveAsync([FromBody] JsonElement body, CancellationToken ct)
    {
        try
        {
            RuntimeEventStreamReader.ValidateUniqueProperties(body);
            var canonical = AgentAdmissionCanonicalizer.Canonicalize(body);
            var digest = Convert.ToHexStringLower(
                SHA256.HashData(Encoding.UTF8.GetBytes(canonical))
            );
            await authority.RequireAsync(HttpContext, digest, ct);
            var request = body.Deserialize<ResolveProviderCredentialRequest>(
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
                {
                    UnmappedMemberHandling = System
                        .Text
                        .Json
                        .Serialization
                        .JsonUnmappedMemberHandling
                        .Disallow,
                }
            );
            if (!ProviderSecretNames.IsValidProviderName(request?.ProviderName))
                return BadRequest(new { code = "PROVIDER_INVALID" });
            var resolved = await resolver.ResolveAsync(request!.ProviderName!, ct);
            Response.Headers.CacheControl = "no-store";
            return resolved is null
                ? NotFound(new { code = "PROVIDER_CREDENTIAL_NOT_FOUND" })
                : Ok(resolved);
        }
        catch (ProviderAuthorityDeniedException)
        {
            logger.LogWarning("Provider credential resolve was denied for the caller.");
            return StatusCode(403, new { code = "PROVIDER_AUTHORITY_DENIED" });
        }
        catch (JsonException)
        {
            return BadRequest(new { code = "PROVIDER_INVALID" });
        }
    }
}
