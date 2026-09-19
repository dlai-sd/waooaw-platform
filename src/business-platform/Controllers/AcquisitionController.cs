// Implements: WC-096 §4.3 Marketplace And Disclosure
// Constitutional basis: C-005, C-023, C-026, C-049, C-059, C-063

using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record ContinueAcquisitionRequest(
    string ProfessionalType,
    string ProfessionalVersion,
    string Intent,
    string DisclosureRevision,
    string TermsVersion,
    string Acceptance);

public sealed record AcquisitionContinuationResponse(
    Guid RelationshipId,
    string Intent,
    string Status,
    string ResumePath,
    bool Replayed);

[ApiController]
[Authorize]
[Route("api/v1/acquisition/continuations")]
public sealed class AcquisitionController(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory,
    IProfessionalCatalog catalog,
    EmploymentRelationshipService relationships) : ControllerBase
{
    [HttpPost]
    [CustomerIdentityRoute(requiresMembership: true)]
    public async Task<IActionResult> ContinueAsync(
        [FromBody] ContinueAcquisitionRequest request,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        [FromHeader(Name = "X-Correlation-ID")] Guid? correlationId,
        CancellationToken cancellationToken)
    {
        if (!TryGetMembership(out var tenantId, out var participantId)) return Forbid();
        if (!idempotencyKey.HasValue || idempotencyKey == Guid.Empty)
            return Problem(statusCode: StatusCodes.Status400BadRequest, title: "Idempotency key is required");

        var intent = request.Intent.Trim().ToUpperInvariant();
        var disclosure = catalog.GetDisclosure(request.ProfessionalType);
        if (request.Acceptance != "ACCEPT_DISCLOSURE"
            || intent is not ("TRIAL" or "HIRE")
            || disclosure is null
            || !disclosure.Eligibility.Eligible
            || !string.Equals(disclosure.ProjectionVersion, request.ProfessionalVersion, StringComparison.Ordinal)
            || !string.Equals(disclosure.DisclosureRevision, request.DisclosureRevision, StringComparison.Ordinal)
            || !string.Equals(disclosure.TermsVersion, request.TermsVersion, StringComparison.Ordinal)
            || (intent == "TRIAL" && !disclosure.Trial.Available))
            return Problem(statusCode: StatusCodes.Status409Conflict, title: "Acquisition disclosure is stale or invalid");

        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var admissionId = await db.AgentAdmissions.AsNoTracking()
            .Where(value => value.State == AgentAdmissionState.Active
                && value.ProfessionalTypeId == disclosure.ProfessionalType
                && value.ProfessionalVersion == disclosure.ProjectionVersion)
            .OrderByDescending(value => value.UpdatedAt)
            .Select(value => (Guid?)value.AdmissionId)
            .FirstOrDefaultAsync(cancellationToken);
        if (!admissionId.HasValue)
            return Problem(statusCode: StatusCodes.Status409Conflict, title: "Professional is not currently available");

        try
        {
            var result = await relationships.AdmitFromAcquisitionAsync(
                tenantId, participantId, idempotencyKey.Value, disclosure.ProfessionalType,
                admissionId.Value, disclosure.ProjectionVersion, correlationId ?? Guid.NewGuid(),
                new RelationshipAcquisitionEvidence(
                    intent, disclosure.DisclosureRevision, disclosure.TermsVersion, DateTimeOffset.UtcNow),
                cancellationToken);
            var response = new AcquisitionContinuationResponse(
                result.Relationship.RelationshipId, intent, "READY",
                $"/relationships/{result.Relationship.RelationshipId}", !result.Created);
            return result.Created ? StatusCode(StatusCodes.Status201Created, response) : Ok(response);
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: StatusCodes.Status403Forbidden, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: StatusCodes.Status503ServiceUnavailable, title: "Acquisition continuation unavailable");
        }
    }

    private bool TryGetMembership(out Guid tenantId, out Guid participantId)
    {
        tenantId = Guid.Empty;
        participantId = Guid.Empty;
        if (!HttpContext.Items.TryGetValue(CustomerMembershipMiddleware.MembershipItem, out var value)
            || value is not CustomerWorkspaceMembership membership)
            return false;
        tenantId = membership.TenantId;
        participantId = membership.AccountId;
        return tenantId != Guid.Empty && participantId != Guid.Empty;
    }
}