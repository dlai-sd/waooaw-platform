// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R002, WC148-R003, WC148-R004
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.PlatformAccess;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// Founder-only provider and credential registry. Every operation needs the founder role; creating a provider,
/// Test, Confirm and rollback also need a fresh step-up. Request bodies that carry a credential value are read here
/// and handed straight to the service: they are never logged, echoed or placed in an error. Failures are RFC 7807 problems.
/// </summary>
[ApiController]
[Authorize]
[StaffIdentityRoute]
[Route("api/v1/admin/providers")]
public sealed class ProviderCredentialAdminController(
    IProviderCredentialAdminService providers,
    IProviderGenerationProbe generationProbe,
    ILogger<ProviderCredentialAdminController> logger
) : ControllerBase
{
    private const int MaximumBodyBytes = 131_072;

    private static readonly JsonSerializerOptions BodyOptions = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    [HttpGet]
    public Task<IActionResult> ListAsync(CancellationToken ct) =>
        RunAsync(false, async () => Ok(await providers.ListAsync(ct)));

    [HttpPost]
    public Task<IActionResult> CreateAsync(CancellationToken ct) =>
        RunAsync(
            true,
            async () =>
            {
                var request = await ReadBodyAsync<CreateProviderRequest>(ct);
                return StatusCode(201, await providers.CreateAsync(request, ct));
            }
        );

    [HttpGet("{id:guid}/credentials")]
    public Task<IActionResult> ListVersionsAsync(Guid id, CancellationToken ct) =>
        RunAsync(false, async () => Ok(await providers.ListVersionsAsync(id, ct)));

    [HttpPost("{id:guid}/credentials/test")]
    public Task<IActionResult> TestAsync(Guid id, CancellationToken ct) =>
        RunAsync(
            true,
            async () =>
            {
                var request = await ReadBodyAsync<ProviderCredentialTestRequest>(ct);
                return Ok(await providers.TestAsync(id, request.Value, ct));
            }
        );

    [HttpPost("{providerName}/test-answer")]
    public Task<IActionResult> TestAnswerAsync(string providerName, CancellationToken ct) =>
        RunAsync(
            true,
            async () =>
            {
                var request = await ReadBodyAsync<ProviderTestAnswerRequest>(ct);
                return Ok(
                    await generationProbe.TestAnswerAsync(providerName, request, Subject()!, ct)
                );
            }
        );

    [HttpPost("{id:guid}/credentials")]
    public Task<IActionResult> ConfirmAsync(Guid id, CancellationToken ct) =>
        RunAsync(
            true,
            async () =>
            {
                var request = await ReadBodyAsync<ProviderCredentialConfirmRequest>(ct);
                var saved = await providers.ConfirmAsync(
                    id,
                    request.Value,
                    request.AcknowledgeUntested,
                    Subject()!,
                    ct
                );
                return StatusCode(201, saved);
            }
        );

    [HttpPost("{id:guid}/credentials/{versionId:guid}/activate")]
    public Task<IActionResult> ActivateAsync(Guid id, Guid versionId, CancellationToken ct) =>
        RunAsync(true, async () => Ok(await providers.ActivateAsync(id, versionId, ct)));

    private async Task<IActionResult> RunAsync(bool write, Func<Task<IActionResult>> operation)
    {
        Response.Headers.CacheControl = "no-store";
        try
        {
            Authorize(write);
            return await operation();
        }
        catch (ProviderAdminException problem)
        {
            return ProblemResult(problem);
        }
    }

    private void Authorize(bool write)
    {
        if (User.Identity?.IsAuthenticated != true || string.IsNullOrWhiteSpace(Subject()))
            throw new ProviderAdminException(
                401,
                "PROVIDER_FORBIDDEN",
                "A signed-in administrator is required."
            );
        if (!IsRole(PlatformRoles.Founder))
            throw new ProviderAdminException(
                403,
                "PROVIDER_FORBIDDEN",
                "Only the Founder may manage provider credentials."
            );
        if (write && !PlatformRoles.HasStepUp(User, DateTimeOffset.UtcNow))
            throw new ProviderAdminException(
                403,
                "PROVIDER_STEP_UP_REQUIRED",
                "This operation needs a fresh step-up authentication."
            );
    }

    private string? Subject() =>
        User.FindFirstValue("participant_id")
        ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? User.FindFirstValue("sub");

    private bool IsRole(string role) =>
        User.IsInRole(role)
        || User.Claims.Where(claim => claim.Type is ClaimTypes.Role or "role" or "participant_role")
            .Any(claim => string.Equals(claim.Value, role, StringComparison.OrdinalIgnoreCase));

    private async Task<T> ReadBodyAsync<T>(CancellationToken ct)
        where T : class
    {
        using var buffer = new MemoryStream();
        var chunk = new byte[8192];
        int read;
        while ((read = await Request.Body.ReadAsync(chunk, ct)) > 0)
        {
            buffer.Write(chunk, 0, read);
            if (buffer.Length > MaximumBodyBytes)
                throw Invalid("The request body is too large.");
        }
        try
        {
            return JsonSerializer.Deserialize<T>(buffer.ToArray(), BodyOptions)
                ?? throw Invalid("A JSON object body is required.");
        }
        catch (JsonException)
        {
            // The parser message can quote body fragments, so it is deliberately dropped.
            throw Invalid("The body is not valid JSON for this operation.");
        }
    }

    private static ProviderAdminException Invalid(string detail) =>
        new(400, "PROVIDER_INVALID", detail);

    private IActionResult ProblemResult(ProviderAdminException problem)
    {
        if (problem.Status >= 500)
            logger.LogWarning("Provider admin request failed: code={Code}", problem.Code);
        var content = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["type"] =
                $"https://waooaw.com/problems/{problem.Code.ToLowerInvariant().Replace('_', '-')}",
            ["title"] = Title(problem.Code),
            ["status"] = problem.Status,
            ["code"] = problem.Code,
            ["correlationId"] = Guid.NewGuid().ToString("D"),
            ["detail"] = problem.Message,
        };
        foreach (var (name, value) in problem.Extras)
            content[name] = value;
        return new ContentResult
        {
            StatusCode = problem.Status,
            ContentType = "application/problem+json",
            Content = JsonSerializer.Serialize(content),
        };
    }

    private static string Title(string code)
    {
        var words = code.ToLowerInvariant().Replace('_', ' ');
        return char.ToUpperInvariant(words[0]) + words[1..];
    }
}
