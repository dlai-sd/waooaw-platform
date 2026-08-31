// Implements: WC-079 AA-03, AA-04, AA-05, AA-08, AA-09
// constitutional_basis: C-003, C-005, C-007, C-023, C-026, C-059, C-063, C-065, C-079

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record CreateAgentAdmissionDraftRequest(Guid OwnerSubjectId);
public sealed record PutAgentAdmissionRevisionRequest(int ExpectedStateVersion, string AdmissionContentDigest, JsonElement AdmissionContent);
public sealed record ValidateAgentAdmissionRequest(int Revision, string AdmissionContentDigest, string ValidatorProfile);
public sealed record AgentAdmissionTransitionRequest(
    int ExpectedStateVersion,
    int Revision,
    string AdmissionContentDigest,
    string EvidenceSetDigest,
    string? ArtifactDigest,
    string PolicyVersion,
    string? ReasonCategory,
    string? SuccessorVersion);

[ApiController]
[Route("api/v1/professionals")]
public sealed class AgentAdmissionsController(AgentAdmissionService admissions) : ControllerBase
{
    [AllowAnonymous]
    [HttpGet("offerable-versions")]
    public async Task<IActionResult> GetOfferableAsync(
        [FromQuery] string environment,
        CancellationToken cancellationToken)
    {
        if (environment is not ("demo" or "uat" or "prod")) return AdmissionProblem(400, "ADMISSION_INVALID_REQUEST");
        return Ok(await admissions.GetOfferableAsync(environment, cancellationToken));
    }

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/drafts")]
    public async Task<IActionResult> CreateDraftAsync(
        string type,
        string version,
        [FromBody] CreateAgentAdmissionDraftRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        CancellationToken cancellationToken)
    {
        if (!TryContext(out var tenantId, out var actorId)) return AdmissionProblem(401, "ADMISSION_UNAUTHORIZED");
        if (idempotencyKey is null) return AdmissionProblem(400, "ADMISSION_INVALID_REQUEST");
        if (request.OwnerSubjectId != actorId && !IsRole("admission_operator")) return Forbid();
        return await ExecuteAsync(async () =>
        {
            var result = await admissions.CreateDraftAsync(
                tenantId, type, version, request.OwnerSubjectId, actorId, idempotencyKey.Value, cancellationToken);
            return StatusCode(result.Replayed ? 200 : 201, Projection(result.Admission));
        });
    }

    [Authorize]
    [HttpPut("{type}/versions/{version}/admission/drafts/{draftId:guid}/revisions/{revision:int}")]
    public async Task<IActionResult> PutRevisionAsync(
        string type,
        string version,
        Guid draftId,
        int revision,
        [FromBody] PutAgentAdmissionRevisionRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        CancellationToken cancellationToken)
    {
        if (!TryContext(out var tenantId, out var actorId)) return AdmissionProblem(401, "ADMISSION_UNAUTHORIZED");
        if (idempotencyKey is null) return AdmissionProblem(400, "ADMISSION_INVALID_REQUEST");
        return await ExecuteAsync(async () =>
        {
            var result = await admissions.PutRevisionAsync(
                tenantId, type, version, draftId, revision, request.ExpectedStateVersion,
                request.AdmissionContentDigest, request.AdmissionContent, actorId, idempotencyKey.Value, cancellationToken);
            return Ok(Projection(result.Admission));
        });
    }

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/drafts/{draftId:guid}/validations")]
    public async Task<IActionResult> ValidateAsync(
        string type,
        string version,
        Guid draftId,
        [FromBody] ValidateAgentAdmissionRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        CancellationToken cancellationToken)
    {
        if (!TryContext(out var tenantId, out var actorId)) return AdmissionProblem(401, "ADMISSION_UNAUTHORIZED");
        if (idempotencyKey is null) return AdmissionProblem(400, "ADMISSION_INVALID_REQUEST");
        return await ExecuteAsync(async () =>
        {
            var result = await admissions.ValidateAsync(
                tenantId, type, version, draftId, request.Revision, request.AdmissionContentDigest,
                request.ValidatorProfile, actorId, IsRole("validator_operator"), idempotencyKey.Value, cancellationToken);
            var response = new
            {
                result.Validation.ValidationId,
                result.Validation.Revision,
                profile = result.Validation.ValidatorProfile,
                result.Validation.Result,
                result.Validation.FindingCount,
            };
            return StatusCode(result.Replayed ? 200 : 202, response);
        });
    }

    [Authorize]
    [HttpGet("{type}/versions/{version}/admission/drafts/{draftId:guid}/validations/{validationId:guid}/findings")]
    public async Task<IActionResult> GetFindingsAsync(
        string type,
        string version,
        Guid draftId,
        Guid validationId,
        CancellationToken cancellationToken)
    {
        if (!TryContext(out var tenantId, out var actorId)) return AdmissionProblem(401, "ADMISSION_UNAUTHORIZED");
        return await ExecuteAsync(async () => Ok(await admissions.GetFindingsAsync(
            tenantId, type, version, draftId, validationId, actorId, IsRole("admission_reviewer"), cancellationToken)));
    }

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/submissions")]
    public Task<IActionResult> SubmitAsync(
        string type,
        string version,
        [FromBody] AgentAdmissionTransitionRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        CancellationToken cancellationToken) => TransitionAsync(
            type, version, "SUBMIT", request, idempotencyKey, ownerOperation: true, cancellationToken);

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/approvals")]
    public Task<IActionResult> ApproveAsync(string type, string version, [FromBody] AgentAdmissionTransitionRequest request, [FromHeader(Name = "Idempotency-Key")] Guid? key, CancellationToken token) =>
        TransitionAsync(type, version, "APPROVE", request, key, false, token);

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/rejections")]
    public Task<IActionResult> RejectAsync(string type, string version, [FromBody] AgentAdmissionTransitionRequest request, [FromHeader(Name = "Idempotency-Key")] Guid? key, CancellationToken token) =>
        TransitionAsync(type, version, "REJECT", request, key, false, token);

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/activations")]
    public Task<IActionResult> ActivateAsync(string type, string version, [FromBody] AgentAdmissionTransitionRequest request, [FromHeader(Name = "Idempotency-Key")] Guid? key, CancellationToken token) =>
        TransitionAsync(type, version, "ACTIVATE", request, key, false, token);

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/suspensions")]
    public Task<IActionResult> SuspendAsync(string type, string version, [FromBody] AgentAdmissionTransitionRequest request, [FromHeader(Name = "Idempotency-Key")] Guid? key, CancellationToken token) =>
        TransitionAsync(type, version, "SUSPEND", request, key, false, token);

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/supersessions")]
    public Task<IActionResult> SupersedeAsync(string type, string version, [FromBody] AgentAdmissionTransitionRequest request, [FromHeader(Name = "Idempotency-Key")] Guid? key, CancellationToken token) =>
        TransitionAsync(type, version, "SUPERSEDE", request, key, false, token);

    [Authorize]
    [HttpPost("{type}/versions/{version}/admission/retirements")]
    public Task<IActionResult> RetireAsync(string type, string version, [FromBody] AgentAdmissionTransitionRequest request, [FromHeader(Name = "Idempotency-Key")] Guid? key, CancellationToken token) =>
        TransitionAsync(type, version, "RETIRE", request, key, false, token);

    private async Task<IActionResult> TransitionAsync(
        string type,
        string version,
        string operation,
        AgentAdmissionTransitionRequest request,
        Guid? idempotencyKey,
        bool ownerOperation,
        CancellationToken cancellationToken)
    {
        if (!TryContext(out var tenantId, out var actorId)) return AdmissionProblem(401, "ADMISSION_UNAUTHORIZED");
        if (idempotencyKey is null) return AdmissionProblem(400, "ADMISSION_INVALID_REQUEST");
        if (!ownerOperation && (!AuthorizedFor(operation) || !HasStepUp()))
            return AdmissionProblem(403, "ADMISSION_FORBIDDEN");
        var correlationId = CorrelationId();
        return await ExecuteAsync(async () =>
        {
            var result = await admissions.TransitionAsync(
                tenantId,
                type,
                version,
                operation,
                new(
                    request.ExpectedStateVersion,
                    request.Revision,
                    request.AdmissionContentDigest,
                    request.EvidenceSetDigest,
                    request.ArtifactDigest,
                    request.PolicyVersion,
                    request.ReasonCategory,
                    request.SuccessorVersion),
                actorId,
                ownerOperation ? "OWNER_DELEGATE" : AuthorityFor(operation),
                idempotencyKey.Value,
                correlationId,
                EnvironmentName(),
                cancellationToken);
            return StatusCode(operation == "SUBMIT" && !result.Replayed ? 201 : 200, Projection(result.Admission));
        });
    }

    private async Task<IActionResult> ExecuteAsync(Func<Task<IActionResult>> action)
    {
        try { return await action(); }
        catch (AdmissionNotFoundException) { return NotFoundProblem(); }
        catch (AdmissionIdempotencyConflictException) { return AdmissionProblem(409, "ADMISSION_IDEMPOTENCY_CONFLICT"); }
        catch (AdmissionStateConflictException) { return AdmissionProblem(409, "ADMISSION_STATE_CONFLICT"); }
        catch (AdmissionTransitionBlockedException) { return AdmissionProblem(423, "ADMISSION_TRANSITION_BLOCKED"); }
        catch (ConstitutionalActionDeniedException) { return AdmissionProblem(423, "ADMISSION_TRANSITION_BLOCKED"); }
        catch (ArgumentException) { return AdmissionProblem(400, "ADMISSION_INVALID_REQUEST"); }
        catch (JsonException) { return AdmissionProblem(400, "ADMISSION_INVALID_REQUEST"); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return AdmissionProblem(503, "ADMISSION_UNAVAILABLE");
        }
    }

    private bool TryContext(out Guid tenantId, out Guid actorId)
    {
        tenantId = default;
        actorId = default;
        var actor = User.FindFirstValue("participant_id") ?? User.FindFirstValue(ClaimTypes.NameIdentifier);
        return HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && value is string tenant
            && Guid.TryParse(tenant, out tenantId)
            && Guid.TryParse(actor, out actorId);
    }

    private bool AuthorizedFor(string operation) => operation switch
    {
        "APPROVE" or "REJECT" => IsRole("founder") || IsRole("admission_approver"),
        "ACTIVATE" => IsRole("platform_activation_authority"),
        "SUSPEND" => IsRole("constitutional_authority") || IsRole("operations_authority"),
        "SUPERSEDE" or "RETIRE" => IsRole("lifecycle_authority"),
        _ => false,
    };

    private bool IsRole(string role) => User.IsInRole(role)
        || User.Claims.Where(claim => claim.Type is ClaimTypes.Role or "role" or "participant_role")
            .Any(claim => string.Equals(claim.Value, role, StringComparison.OrdinalIgnoreCase));

    private bool HasStepUp() => User.Claims.Any(claim => claim.Type is "amr" or "acr"
        && (claim.Value.Contains("mfa", StringComparison.OrdinalIgnoreCase) || claim.Value is "2" or "3"));

    private string AuthorityFor(string operation) => operation switch
    {
        "APPROVE" or "REJECT" => IsRole("founder") ? "FOUNDER" : "ADMISSION_APPROVER",
        "ACTIVATE" => "PLATFORM_ACTIVATION_AUTHORITY",
        "SUSPEND" => IsRole("constitutional_authority") ? "CONSTITUTIONAL_AUTHORITY" : "OPERATIONS_AUTHORITY",
        "SUPERSEDE" or "RETIRE" => "LIFECYCLE_AUTHORITY",
        _ => "UNKNOWN",
    };
    private string EnvironmentName() => HttpContext.RequestServices.GetRequiredService<IHostEnvironment>().EnvironmentName.ToLowerInvariant() switch
    {
        "production" => "prod",
        "uat" => "uat",
        _ => "demo",
    };
    private Guid CorrelationId() => Guid.TryParse(Request.Headers["X-Correlation-ID"].FirstOrDefault(), out var value) ? value : Guid.NewGuid();
    private ObjectResult NotFoundProblem() => AdmissionProblem(404, "ADMISSION_NOT_FOUND");
    private ObjectResult AdmissionProblem(int status, string code)
    {
        var problem = StatusCode(status, new
        {
            type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
            title = "The agent admission operation could not be completed",
            status,
            code,
            correlationId = User.FindFirstValue("correlation_id") ?? HttpContext.TraceIdentifier,
        });
        problem.ContentTypes.Add("application/problem+json");
        return problem;
    }

    private static object Projection(AgentAdmission admission) => new
    {
        admission.AdmissionId,
        admission.ProfessionalTypeId,
        admission.ProfessionalVersion,
        state = AgentAdmissionStateCodec.ToDatabase(admission.State),
        admission.StateVersion,
        admission.CurrentRevision,
        admission.AdmissionContentDigest,
        admission.CreatedAt,
        admission.UpdatedAt,
    };
}