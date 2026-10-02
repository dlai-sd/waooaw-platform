// Implements: architecture/reference/product/ae01-solution-contract.md §Canonical API and Compatibility; WC-097 A03
// Constitutional basis: C-009, C-048, C-059, C-063

using System.Security.Cryptography;
using System.Text;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/professionals")]
public sealed class ProfessionalsController : ControllerBase
{
    private readonly IProfessionalCatalog _catalog;
    private readonly IRelationshipTrialOwnerGateway _trialOwners;

    public ProfessionalsController(
        IProfessionalCatalog catalog,
        IRelationshipTrialOwnerGateway trialOwners
    )
    {
        _catalog = catalog;
        _trialOwners = trialOwners;
    }

    [HttpGet]
    [AllowAnonymous]
    public ActionResult<IReadOnlyList<ProfessionalDiscoveryResult>> Discover(
        [FromQuery] string outcome
    )
    {
        var outcomeLength = outcome?.EnumerateRunes().Count() ?? 0;
        if (string.IsNullOrWhiteSpace(outcome) || outcomeLength is < 3 or > 500)
        {
            var problem = new ValidationProblemDetails(
                new Dictionary<string, string[]>
                {
                    [nameof(outcome)] = ["Outcome must contain between 3 and 500 characters."],
                }
            )
            {
                Type = "https://waooaw.com/problems/validation-error",
                Title = "The request is invalid",
                Status = StatusCodes.Status400BadRequest,
            };
            return BadRequest(problem);
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
    [CustomerIdentityRoute]
    public IActionResult BrowseMarketplace(
        [FromQuery] string? cursor,
        [FromQuery] int limit = 20,
        [FromQuery] string? professionalType = null,
        [FromQuery(Name = "q")] string? query = null
    )
    {
        if (
            limit is < 1 or > 100
            || Request.Query.Keys.Any(key =>
                key is not "cursor" and not "limit" and not "professionalType" and not "q"
            )
            || Request.Query.ContainsKey("cursor")
                && (string.IsNullOrWhiteSpace(cursor) || cursor.Length is < 16 or > 2048)
            || Request.Query.ContainsKey("professionalType")
                && (string.IsNullOrWhiteSpace(professionalType) || professionalType.Length > 100)
            || Request.Query.ContainsKey("q")
                && (string.IsNullOrWhiteSpace(query) || query.Length > 120)
        )
            return Problem(
                statusCode: StatusCodes.Status400BadRequest,
                title: "Invalid marketplace query"
            );

        var filterHash = FilterHash(professionalType, query);
        var offset = 0;
        if (!string.IsNullOrWhiteSpace(cursor) && !TryParseCursor(cursor, filterHash, out offset))
            return Problem(
                statusCode: StatusCodes.Status404NotFound,
                title: "Marketplace cursor is not accessible"
            );

        var listings = _catalog.Browse(professionalType, query);
        var page = listings.Skip(offset).Take(limit + 1).ToArray();
        var items = page.Take(limit)
            .Select(disclosure => new
            {
                professionalType = disclosure.ProfessionalType,
                version = disclosure.ProjectionVersion,
                displayName = disclosure.DisplayName,
                disclosurePath = $"/marketplace/{disclosure.CustomerRouteSlug}",
                availableIntents = disclosure.Eligibility.Eligible
                    ? disclosure.Trial.Available
                        ? new[] { "TRIAL", "HIRE" }
                        : ["HIRE"]
                    : [],
                disclosureRevision = disclosure.DisclosureRevision,
                termsVersion = disclosure.TermsVersion,
                suitability = disclosure.Suitability,
                capabilitySignals = disclosure.Skills.Take(3).Select(skill => skill.DisplayName),
                limitations = disclosure.Limitations,
                customerRights = disclosure.CustomerRights,
                eligibility = disclosure.Eligibility,
                indicativePrice = disclosure.IndicativePrice,
                trial = disclosure.Trial,
                evidencePosture = disclosure.EvidencePosture,
                offerabilityState = disclosure.Eligibility.Eligible
                    ? disclosure.Trial.Available
                        ? "OFFERABLE"
                        : "TRIAL_ONLY"
                    : "NOT_OFFERABLE",
                trialTerms = disclosure.Trial.Available
                    ? $"{disclosure.Trial.DurationDays}-day trial; no paid API calls or external actions."
                    : null,
                nextAction = disclosure.Eligibility.Eligible ? "VIEW_DISCLOSURE" : "NONE",
            })
            .ToArray();
        var nextCursor = page.Length > limit ? Cursor(filterHash, offset + limit) : null;
        return Ok(
            new
            {
                schemaVersion = "1.0.0",
                producedAt = DateTimeOffset.UtcNow,
                nextCursor,
                items,
            }
        );
    }

    private static string FilterHash(string? professionalType, string? query) =>
        Convert.ToHexStringLower(
            SHA256.HashData(
                Encoding.UTF8.GetBytes(
                    $"{professionalType?.Trim().ToUpperInvariant()}\n{query?.Trim().ToUpperInvariant()}"
                )
            )
        )[..12];

    private static string Cursor(string filterHash, int offset) =>
        Convert.ToBase64String(Encoding.UTF8.GetBytes($"marketplace:{filterHash}:{offset:D8}"));

    private static bool TryParseCursor(string cursor, string expectedFilterHash, out int offset)
    {
        offset = 0;
        try
        {
            var value = Encoding.UTF8.GetString(Convert.FromBase64String(cursor));
            var parts = value.Split(':');
            return parts.Length == 3
                && parts[0] == "marketplace"
                && parts[1] == expectedFilterHash
                && int.TryParse(parts[2], out offset)
                && offset >= 0;
        }
        catch (FormatException)
        {
            return false;
        }
    }
}
