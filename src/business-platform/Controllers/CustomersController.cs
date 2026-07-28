// Implements: architecture/reference/api-specs/business-platform.openapi.yaml
// constitutional_basis: ADR-002 (spec-first), C-023 (Evidence First), C-038 (pro-rata)

using Microsoft.AspNetCore.Mvc;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController, Route("api/v1")]
public sealed class CustomersController : ControllerBase
{
    [HttpPost("employment/contracts")]
    public IActionResult FormEmploymentContract() => Ok();

    [HttpGet("employment/contracts/{id}")]
    public IActionResult GetEmploymentContract(Guid id) => Ok();
}
