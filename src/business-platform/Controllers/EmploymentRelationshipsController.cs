// Implements: architecture/reference/product/ae01-solution-contract.md § Canonical API and Compatibility
// constitutional_basis: C-005, C-023, C-026, C-059

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record AdmitEmploymentRelationshipRequest(
    Guid EvaluationIntentId,
    string ProfessionalType,
    Guid? CorrelationId = null);

public sealed record TransitionEmploymentRelationshipRequest(
    EmploymentRelationshipState TargetState,
    Guid ActorParticipantId,
    RelationshipParticipantRole ActorRole,
    Guid CorrelationId,
    bool ExplicitEmergencyRelease = false);

public sealed record EmploymentRelationshipResponse(
    Guid RelationshipId,
    string ProfessionalType,
    string State,
    int StateVersion,
    DateTimeOffset CreatedAt,
    DateTimeOffset UpdatedAt);

public sealed record RelationshipTimelineEntryResponse(
    int StateVersion,
    string? FromState,
    string ToState,
    Guid ActorParticipantId,
    string ActorRole,
    Guid CorrelationId,
    Guid EvidenceId,
    DateTimeOffset OccurredAt);

[ApiController]
[Authorize]
[Route("api/v1/employment/relationships")]
public sealed class EmploymentRelationshipsController : ControllerBase
{
    private readonly EmploymentRelationshipService _service;

    public EmploymentRelationshipsController(EmploymentRelationshipService service)
    {
        _service = service;
    }

    [HttpPost]
    public async Task<IActionResult> AdmitAsync(
        [FromBody] AdmitEmploymentRelationshipRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId))
        {
            return Forbid();
        }

        try
        {
            var result = await _service.AdmitAsync(
                tenantId,
                participantId,
                request.EvaluationIntentId,
                request.ProfessionalType,
                request.CorrelationId ?? Guid.NewGuid(),
                cancellationToken);
            var response = ToResponse(result.Relationship);
            return result.Created
                ? CreatedAtAction(nameof(GetAsync), new { relationshipId = response.RelationshipId }, response)
                : Ok(response);
        }
        catch (ArgumentException exception)
        {
            return ValidationProblem(exception.Message);
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: StatusCodes.Status403Forbidden, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: StatusCodes.Status503ServiceUnavailable, title: "Constitutional evidence unavailable");
        }
    }

    [HttpGet("{relationshipId:guid}")]
    public async Task<IActionResult> GetAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId))
        {
            return Forbid();
        }

        var relationship = await _service.GetAsync(tenantId, relationshipId, cancellationToken);
        return relationship is null ? NotFound() : Ok(ToResponse(relationship));
    }

    [HttpGet("{relationshipId:guid}/timeline")]
    public async Task<IActionResult> GetTimelineAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId))
        {
            return Forbid();
        }

        if (await _service.GetAsync(tenantId, relationshipId, cancellationToken) is null)
        {
            return NotFound();
        }

        var timeline = await _service.GetTimelineAsync(tenantId, relationshipId, cancellationToken);
        return Ok(timeline.Select(value => new RelationshipTimelineEntryResponse(
            value.StateVersion,
            value.FromState.HasValue ? RelationshipStateCodec.ToDatabase(value.FromState.Value) : null,
            RelationshipStateCodec.ToDatabase(value.ToState),
            value.ActorParticipantId,
            RelationshipRoleCodec.ToDatabase(value.ActorRole),
            value.CorrelationId,
            value.EvidenceId,
            value.OccurredAt)));
    }

    [Authorize(Policy = "InternalService")]
    [HttpPost("{relationshipId:guid}/transitions")]
    public async Task<IActionResult> TransitionAsync(
        Guid relationshipId,
        [FromBody] TransitionEmploymentRelationshipRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId))
        {
            return Forbid();
        }

        try
        {
            var relationship = await _service.TransitionAsync(
                tenantId,
                relationshipId,
                request.ActorParticipantId,
                request.ActorRole,
                request.TargetState,
                request.CorrelationId,
                request.ExplicitEmergencyRelease,
                cancellationToken);
            return relationship is null ? NotFound() : Ok(ToResponse(relationship));
        }
        catch (IllegalRelationshipTransitionException exception)
        {
            return Conflict(new { error = "ILLEGAL_RELATIONSHIP_TRANSITION", detail = exception.Message });
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: StatusCodes.Status403Forbidden, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (DbUpdateConcurrencyException)
        {
            return Conflict(new { error = "RELATIONSHIP_VERSION_CONFLICT" });
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: StatusCodes.Status503ServiceUnavailable, title: "Constitutional evidence unavailable");
        }
    }

    private bool TryGetTenantId(out Guid tenantId)
    {
        tenantId = default;
        return HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && value is string text
            && Guid.TryParse(text, out tenantId);
    }

    private bool TryGetParticipantId(out Guid participantId)
    {
        var value = User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier);
        return Guid.TryParse(value, out participantId);
    }

    private static EmploymentRelationshipResponse ToResponse(EmploymentRelationship relationship) =>
        new(
            relationship.RelationshipId,
            relationship.ProfessionalType,
            RelationshipStateCodec.ToDatabase(relationship.State),
            relationship.StateVersion,
            relationship.CreatedAt,
            relationship.UpdatedAt);
}