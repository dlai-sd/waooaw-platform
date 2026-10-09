// Implements: architecture/reference/components/conversational-employment-solution-contract.md §4.8 Compatibility scan
// Constitutional basis: C-023, C-059, C-063, C-079, ADR-051
// IB: N/A - Founder-assigned WC-115

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize(Roles = "platform_admission")]
[Route("internal/v1/employment-interface/compatibility-scans")]
public sealed class EmploymentCompatibilityController(EmploymentCompatibilityService scans)
    : ControllerBase
{
    [HttpPost]
    public IActionResult StartEmploymentCompatibilityScan(
        [FromBody] EmploymentCompatibilityRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        [FromHeader(Name = "X-Correlation-Id")] Guid? correlationId
    )
    {
        if (idempotencyKey is null || correlationId is null)
            return ProblemResult(400, "COMPATIBILITY_INVALID", correlationId);
        var caller =
            User.FindFirstValue("client_id") ?? User.FindFirstValue("sub") ?? "unauthorized";
        try
        {
            var result = scans.Start(caller, idempotencyKey.Value, request);
            if (result.Replayed && result.Result.State is "PASS" or "FAIL")
                return Ok(result.Result);
            return StatusCode(StatusCodes.Status202Accepted, result.Receipt);
        }
        catch (EmploymentProtocolException error)
        {
            return error.Code switch
            {
                "COMPATIBILITY_CONFLICT" => ProblemResult(409, error.Code, correlationId),
                _ => ProblemResult(400, "COMPATIBILITY_INVALID", correlationId),
            };
        }
    }

    [HttpGet("{scanId:guid}")]
    public IActionResult GetEmploymentCompatibilityScan(
        Guid scanId,
        [FromHeader(Name = "X-Correlation-Id")] Guid? correlationId
    )
    {
        if (correlationId is null)
            return ProblemResult(400, "COMPATIBILITY_INVALID", correlationId);
        var result = scans.Get(scanId);
        return result is null
            ? ProblemResult(404, "COMPATIBILITY_NOT_FOUND", correlationId)
            : Ok(result);
    }

    private ObjectResult ProblemResult(int status, string code, Guid? correlationId)
    {
        var response = StatusCode(
            status,
            new
            {
                type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
                title = "The compatibility scan request could not be completed",
                status,
                code,
                correlationId = correlationId ?? Guid.Empty,
            }
        );
        response.ContentTypes.Add("application/problem+json");
        return response;
    }
}
