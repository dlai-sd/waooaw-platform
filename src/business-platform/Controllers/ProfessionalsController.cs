// Implements: architecture/reference/product/ae01-solution-contract.md §Canonical API and Compatibility
// Constitutional basis: C-009, C-048, C-059, C-063

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Security.Cryptography;
using System.Text;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/professionals")]
public sealed class ProfessionalsController : ControllerBase
{
    private readonly IProfessionalCatalog _catalog;

    public ProfessionalsController(IProfessionalCatalog catalog)
    {
        _catalog = catalog;
    }

    [HttpGet]
    [AllowAnonymous]
    public ActionResult<IReadOnlyList<ProfessionalDiscoveryResult>> Discover(
        [FromQuery] string outcome)
    {
        if (string.IsNullOrWhiteSpace(outcome) || outcome.Trim().Length < 3 || outcome.Length > 500)
        {
            return BadRequest(new ValidationProblemDetails(
                new Dictionary<string, string[]>
                {
                    [nameof(outcome)] = ["Outcome must contain between 3 and 500 characters."],
                }));
        }

        return Ok(_catalog.Discover(outcome));
    }

    [HttpGet("{professionalType}/disclosure")]
    [AllowAnonymous]
    public ActionResult<ProfessionalDisclosure> GetDisclosure(string professionalType)
    {
        var disclosure = _catalog.GetDisclosure(professionalType);
        return disclosure is null
            ? Problem(statusCode: StatusCodes.Status404NotFound, title: "Professional not found")
            : Ok(disclosure);
    }

    [HttpGet("marketplace")]
    public IActionResult BrowseMarketplace(
        [FromQuery] string? cursor,
        [FromQuery] int limit = 20,
        [FromQuery] string? professionalType = null,
        [FromQuery(Name = "q")] string? query = null)
    {
        if (limit is < 1 or > 100
            || professionalType is { Length: > 100 }
            || query is { Length: > 120 })
            return Problem(statusCode: StatusCodes.Status400BadRequest,
                title: "Invalid marketplace query");

        var filterHash = FilterHash(professionalType, query);
        var offset = 0;
        if (!string.IsNullOrWhiteSpace(cursor)
            && !TryParseCursor(cursor, filterHash, out offset))
            return Problem(statusCode: StatusCodes.Status400BadRequest,
                title: "Invalid marketplace cursor");

        var listings = _catalog.Browse(professionalType, query);
        var page = listings.Skip(offset).Take(limit + 1).ToArray();
        var items = page.Take(limit).Select(disclosure => new
        {
            professionalType = disclosure.ProfessionalType,
            version = disclosure.ProjectionVersion,
            displayName = disclosure.DisplayName,
            suitability = disclosure.Suitability,
            eligibility = disclosure.Eligibility,
            indicativePrice = disclosure.IndicativePrice,
            offerabilityState = disclosure.Eligibility.Eligible
                ? disclosure.Trial.Available ? "OFFERABLE" : "TRIAL_ONLY"
                : "NOT_OFFERABLE",
            trialTerms = disclosure.Trial.Available
                ? $"{disclosure.Trial.DurationDays}-day trial; no paid API calls or external actions."
                : null,
            nextAction = disclosure.Eligibility.Eligible ? "VIEW_DISCLOSURE" : "NONE",
        }).ToArray();
        var nextCursor = page.Length > limit ? Cursor(filterHash, offset + limit) : null;
        return Ok(new { schemaVersion = "1.0.0", producedAt = DateTimeOffset.UtcNow, nextCursor, items });
    }

    private static string FilterHash(string? professionalType, string? query) =>
        Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(
            $"{professionalType?.Trim().ToUpperInvariant()}\n{query?.Trim().ToUpperInvariant()}")))[..12];

    private static string Cursor(string filterHash, int offset) =>
        Convert.ToBase64String(Encoding.UTF8.GetBytes($"marketplace:{filterHash}:{offset:D8}"));

    private static bool TryParseCursor(string cursor, string expectedFilterHash, out int offset)
    {
        offset = 0;
        try
        {
            var value = Encoding.UTF8.GetString(Convert.FromBase64String(cursor));
            var parts = value.Split(':');
            return parts.Length == 3 && parts[0] == "marketplace"
                && parts[1] == expectedFilterHash && int.TryParse(parts[2], out offset) && offset >= 0;
        }
        catch (FormatException)
        {
            return false;
        }
    }
}