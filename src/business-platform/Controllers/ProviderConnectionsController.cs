// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R007, WC149-R008, WC149-R009
// Constitutional basis: C-023, C-059, C-063, C-083, C-084

using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// A customer's provider account connections. The tenant comes from the validated membership, never from the
/// request. Bodies that carry an authorization code are read here and handed to the service; nothing in a
/// response, problem or log carries a token or the app secret.
/// </summary>
[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[Route("api/v1/provider-connections")]
public sealed class ProviderConnectionsController(
    IProviderConnectionService connections,
    ILogger<ProviderConnectionsController> logger
) : ControllerBase
{
    private const int MaximumBodyBytes = 16_384;

    private static readonly JsonSerializerOptions BodyOptions = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    [HttpGet]
    public Task<IActionResult> ListAsync(CancellationToken ct) =>
        RunAsync(async (tenant, _) => Ok(await connections.ListAsync(tenant, ct)));

    [HttpPost("meta/start")]
    public Task<IActionResult> StartAsync(CancellationToken ct) =>
        RunAsync(async (tenant, actor) => Ok(await connections.StartMetaAsync(tenant, actor, ct)));

    [HttpPost("meta/callback")]
    public Task<IActionResult> CallbackAsync(CancellationToken ct) =>
        RunAsync(
            async (tenant, actor) =>
            {
                var request = await ReadBodyAsync<ProviderConnectionCallbackRequest>(ct);
                return Ok(await connections.CompleteMetaAsync(tenant, actor, request, ct));
            }
        );

    [HttpPost("{id:guid}/revoke")]
    public Task<IActionResult> RevokeAsync(Guid id, CancellationToken ct) =>
        RunAsync(
            async (tenant, actor) =>
            {
                await connections.RevokeAsync(tenant, actor, id, ct);
                return NoContent();
            }
        );

    [HttpPost("{id:guid}/publish")]
    public Task<IActionResult> PublishAsync(Guid id, CancellationToken ct) =>
        RunAsync(
            async (tenant, actor) =>
            {
                var request = await ReadBodyAsync<ProviderConnectionPublishRequest>(ct);
                return Ok(await connections.PublishAsync(tenant, actor, id, request, ct));
            }
        );

    private async Task<IActionResult> RunAsync(Func<Guid, Guid, Task<IActionResult>> operation)
    {
        Response.Headers.CacheControl = "no-store";
        try
        {
            if (
                !HttpContext.Items.TryGetValue(
                    TenantIsolationMiddleware.TenantIdItemKey,
                    out var tenantItem
                )
                || tenantItem is not string tenantText
                || !Guid.TryParse(tenantText, out var tenantId)
                || tenantId == Guid.Empty
                || !Guid.TryParse(
                    User.FindFirstValue("participant_id")
                        ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
                        ?? User.FindFirstValue("sub"),
                    out var actorId
                )
            )
                throw new ProviderConnectionException(
                    403,
                    "CONNECTION_FORBIDDEN",
                    "A signed-in customer account is required."
                );
            return await operation(tenantId, actorId);
        }
        catch (ProviderConnectionException problem)
        {
            return ProblemResult(problem);
        }
    }

    private async Task<T> ReadBodyAsync<T>(CancellationToken ct)
        where T : class
    {
        using var buffer = new MemoryStream();
        var chunk = new byte[4096];
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

    private static ProviderConnectionException Invalid(string detail) =>
        new(400, "CONNECTION_INVALID", detail);

    private IActionResult ProblemResult(ProviderConnectionException problem)
    {
        if (problem.Status >= 500)
            logger.LogWarning("Provider connection request failed: code={Code}", problem.Code);
        var words = problem.Code.ToLowerInvariant().Replace('_', ' ');
        var content = new SortedDictionary<string, object?>(StringComparer.Ordinal)
        {
            ["type"] =
                $"https://waooaw.com/problems/{problem.Code.ToLowerInvariant().Replace('_', '-')}",
            ["title"] = char.ToUpperInvariant(words[0]) + words[1..],
            ["status"] = problem.Status,
            ["code"] = problem.Code,
            ["correlationId"] = Guid.NewGuid().ToString("D"),
            ["detail"] = problem.Message,
        };
        return new ContentResult
        {
            StatusCode = problem.Status,
            ContentType = "application/problem+json",
            Content = JsonSerializer.Serialize(content),
        };
    }
}
