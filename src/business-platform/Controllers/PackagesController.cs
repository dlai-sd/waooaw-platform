// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[RequestSizeLimit(65536)]
[Route("api/v1/marketplace/agents/{agentType}/versions/{agentVersion}/packages")]
public sealed partial class PackagesController(
    PackageCatalogService catalog,
    ILogger<PackagesController> logger
) : ControllerBase
{
    public const string RequestInvalid = "PACKAGE_REQUEST_INVALID";
    public const string Unavailable = "PACKAGE_CATALOG_UNAVAILABLE";

    [GeneratedRegex(@"^[A-Za-z0-9_.\-]{1,100}$")]
    private static partial Regex Token();

    [HttpGet]
    public async Task<IActionResult> ListAsync(
        string agentType,
        string agentVersion,
        [FromQuery] string? cursor,
        [FromQuery] int? limit,
        CancellationToken ct
    )
    {
        var correlation = CorrelationOf(out var correlationInvalid);
        Response.Headers["X-Correlation-ID"] = correlation;
        if (correlationInvalid)
            return Problem(400, RequestInvalid, correlation, "X-Correlation-ID must be a UUID.");
        if (
            !Token().IsMatch(agentType)
            || agentVersion.Length > 64
            || !Token().IsMatch(agentVersion)
        )
            return Problem(
                400,
                RequestInvalid,
                correlation,
                "The agent type or version is not valid."
            );
        if (
            cursor is not null
            && cursor.Length is < 1 or > PackageCatalogService.MaximumCursorLength
        )
            return Problem(400, RequestInvalid, correlation, "cursor must be 1 to 256 characters.");
        if (limit is not null && (limit < 1 || limit > PackageCatalogService.MaximumLimit))
            return Problem(400, RequestInvalid, correlation, "limit must be 1 to 100.");
        if (
            !HttpContext.Items.TryGetValue(
                CustomerMembershipMiddleware.MembershipItem,
                out var value
            )
            || value is not CustomerWorkspaceMembership membership
            || membership.TenantId == Guid.Empty
            || membership.AccountId == Guid.Empty
        )
            return Problem(
                401,
                "PACKAGE_UNAUTHORIZED",
                correlation,
                "A customer membership is required."
            );
        try
        {
            var page = await catalog.ListAsync(
                membership.TenantId,
                membership.AccountId.ToString("D"),
                agentType,
                agentVersion,
                cursor,
                limit,
                correlation,
                ct
            );
            return Ok(page);
        }
        catch (PackageCatalogCursorException)
        {
            return Problem(400, RequestInvalid, correlation, "cursor is not valid.");
        }
        catch (PackageCatalogUnavailableException exception)
        {
            logger.LogWarning(
                exception,
                "package_catalog decision=unavailable correlation={Correlation}",
                correlation
            );
            return Problem(
                503,
                Unavailable,
                correlation,
                "Package prices are unavailable right now."
            );
        }
    }

    private string CorrelationOf(out bool invalid)
    {
        var header = Request.Headers["X-Correlation-ID"].FirstOrDefault();
        if (header is null)
        {
            invalid = false;
            return Guid.NewGuid().ToString("D");
        }
        invalid = !Guid.TryParse(header, out var parsed);
        return invalid ? Guid.NewGuid().ToString("D") : parsed.ToString("D");
    }

    private ObjectResult Problem(int status, string code, string correlation, string detail)
    {
        var response = StatusCode(
            status,
            new
            {
                type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                title = "The package request could not be completed",
                status,
                code,
                correlationId = correlation,
                detail,
            }
        );
        response.ContentTypes.Add("application/problem+json");
        return response;
    }
}
