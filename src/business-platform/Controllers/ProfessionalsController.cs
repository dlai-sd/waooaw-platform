// Implements: architecture/reference/product/ae01-solution-contract.md §Canonical API and Compatibility
// Constitutional basis: C-009, C-048, C-059, C-063

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
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
}