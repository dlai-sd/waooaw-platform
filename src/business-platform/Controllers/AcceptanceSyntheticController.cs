// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.Filters;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

namespace Waooaw.BusinessPlatform.Controllers;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record RegisterSyntheticSubjectRequest(string? Subject);

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record RegisterSandboxRecipientRequest(string? Recipient);

/// <summary>
/// Runs before the body is bound, so a disabled route answers the same not-found for any request and a caller
/// without the acceptance-provisioner role learns nothing about the body contract.
/// </summary>
[AttributeUsage(AttributeTargets.Class)]
public sealed class AcceptanceRouteGuardAttribute : Attribute, IAsyncResourceFilter
{
    public const string ProvisionerItem = "waooaw:acceptance-provisioner";

    public async Task OnResourceExecutionAsync(
        ResourceExecutingContext context,
        ResourceExecutionDelegate next
    )
    {
        var http = context.HttpContext;
        var enabled = http
            .RequestServices.GetRequiredService<IOptions<AcceptanceSyntheticOptions>>()
            .Value.Enabled;
        if (!enabled)
        {
            context.Result = AcceptanceProblem.Create(
                StatusCodes.Status404NotFound,
                "ACCEPTANCE_SYNTHETIC_DISABLED"
            );
            return;
        }
        if (!AcceptanceProvisionerAuthority.TryResolve(http.User, out var provisioner))
        {
            context.Result = AcceptanceProblem.Create(
                StatusCodes.Status403Forbidden,
                "ACCEPTANCE_PROVISIONER_REQUIRED"
            );
            return;
        }
        http.Items[ProvisionerItem] = provisioner;
        await next();
    }
}

internal static class AcceptanceProblem
{
    public static ObjectResult Create(int status, string code, string? detail = null)
    {
        var problem = new ProblemDetails
        {
            Type =
                "https://waooaw.com/errors/acceptance/" + code.ToLowerInvariant().Replace('_', '-'),
            Title = code,
            Status = status,
            Detail = detail,
        };
        problem.Extensions["code"] = code;
        return new ObjectResult(problem)
        {
            StatusCode = status,
            ContentTypes = { "application/problem+json" },
        };
    }
}

/// <summary>
/// Internal registry route for the acceptance harness (ADR-055 decision 4). Default off through the feature setting
/// acceptance_synthetic_tenants_enabled. When on, only a verified Keycloak token with the realm role
/// acceptance-provisioner is accepted; a customer, another role or a token that names its own roles is refused. The
/// issuer of a registration is the verified issuer of the caller's token, never a body field, and a body member
/// that is not part of the contract is rejected.
/// </summary>
[ApiController]
[Authorize]
[AcceptanceProvisionerRoute]
[AcceptanceRouteGuard]
[RequestSizeLimit(2048)]
[Route("internal/v1/acceptance/runs/{runId}")]
public sealed partial class AcceptanceSyntheticController(ISyntheticAcceptanceRegistry registry)
    : ControllerBase
{
    [GeneratedRegex("^[A-Za-z0-9._-]{8,64}$")]
    private static partial Regex RunIdPattern();

    [GeneratedRegex("^[A-Za-z0-9._:@-]{8,128}$")]
    private static partial Regex SubjectPattern();

    [GeneratedRegex(@"^\+[1-9][0-9]{7,14}$")]
    private static partial Regex RecipientPattern();

    private AcceptanceProvisioner Provisioner =>
        (AcceptanceProvisioner)HttpContext.Items[AcceptanceRouteGuardAttribute.ProvisionerItem]!;

    [HttpPost("synthetic-subjects")]
    public async Task<IActionResult> RegisterSubjectAsync(
        string runId,
        [FromBody] RegisterSyntheticSubjectRequest request,
        CancellationToken ct
    )
    {
        if (!RunIdPattern().IsMatch(runId) || request.Subject is not { } subject)
            return Invalid("runId and subject are required.");
        if (!SubjectPattern().IsMatch(subject))
            return Invalid("subject must be a Keycloak subject of 8 to 128 safe characters.");
        var outcome = await registry.RegisterSubjectAsync(
            Provisioner.Issuer,
            subject,
            runId,
            Provisioner.Principal,
            ct
        );
        return outcome switch
        {
            SyntheticSubjectRegistration.Created => StatusCode(StatusCodes.Status201Created),
            SyntheticSubjectRegistration.AlreadyRegistered => NoContent(),
            SyntheticSubjectRegistration.RunConflict => AcceptanceProblem.Create(
                StatusCodes.Status409Conflict,
                "ACCEPTANCE_SUBJECT_REGISTERED_ELSEWHERE"
            ),
            _ => AcceptanceProblem.Create(
                StatusCodes.Status429TooManyRequests,
                "ACCEPTANCE_REGISTRY_LIMIT"
            ),
        };
    }

    [HttpPut("sandbox-recipients")]
    public async Task<IActionResult> RegisterSandboxRecipientAsync(
        string runId,
        [FromBody] RegisterSandboxRecipientRequest request,
        CancellationToken ct
    )
    {
        if (!RunIdPattern().IsMatch(runId) || request.Recipient is not { } recipient)
            return Invalid("runId and recipient are required.");
        if (!RecipientPattern().IsMatch(recipient))
            return Invalid("recipient must be an E.164 number.");
        var outcome = await registry.RegisterSandboxRecipientAsync(
            runId,
            recipient,
            Provisioner.Principal,
            ct
        );
        return outcome == SandboxRecipientRegistration.LimitReached
            ? AcceptanceProblem.Create(
                StatusCodes.Status429TooManyRequests,
                "ACCEPTANCE_REGISTRY_LIMIT"
            )
            : NoContent();
    }

    [HttpDelete]
    public async Task<IActionResult> DeactivateRunAsync(string runId, CancellationToken ct)
    {
        if (!RunIdPattern().IsMatch(runId))
            return Invalid("runId is required.");
        var result = await registry.DeactivateRunAsync(runId, ct);
        return Ok(
            new { deactivatedSubjects = result.Subjects, deactivatedRecipients = result.Recipients }
        );
    }

    private static IActionResult Invalid(string detail) =>
        AcceptanceProblem.Create(
            StatusCodes.Status400BadRequest,
            "ACCEPTANCE_REQUEST_INVALID",
            detail
        );
}
