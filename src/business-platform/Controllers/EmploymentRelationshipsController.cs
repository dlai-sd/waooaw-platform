// Implements: architecture/reference/product/ae01-solution-contract.md § Canonical API and Compatibility
// constitutional_basis: C-005, C-023, C-026, C-059

using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Serialization;
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
    [property: JsonConverter(typeof(RelationshipStateJsonConverter))] EmploymentRelationshipState TargetState,
    Guid ActorParticipantId,
    [property: JsonConverter(typeof(RelationshipRoleJsonConverter))] RelationshipParticipantRole ActorRole,
    Guid CorrelationId,
    bool ExplicitEmergencyRelease = false);

public sealed record StartRelationshipTrialRequest(Guid? CorrelationId = null);

public sealed record ProposeEmploymentContractRequest(
    EmploymentContractCommercialTerms CommercialTerms,
    Guid? CorrelationId = null);

public sealed record AcceptEmploymentContractRequest(
    string ContractHash,
    string ScopeConfirmation,
    Guid? CorrelationId = null);

public sealed record EmploymentContractResponse(
    Guid ContractId,
    int Version,
    string ContractHash,
    string State,
    EmploymentContractDocument Document,
    DateTimeOffset CreatedAt);

public sealed record ContractAcceptanceResponse(
    Guid AcceptanceId,
    Guid ContractId,
    int ContractVersion,
    string ContractHash,
    string AuthenticationAssurance,
    Guid AcceptanceEvidenceId,
    DateTimeOffset AcceptedAt);

public sealed class RelationshipStateJsonConverter : JsonConverter<EmploymentRelationshipState>
{
    public override EmploymentRelationshipState Read(
        ref Utf8JsonReader reader,
        Type typeToConvert,
        JsonSerializerOptions options) =>
        RelationshipStateCodec.FromDatabase(
            reader.GetString() ?? throw new JsonException("Relationship state must be a string."));

    public override void Write(
        Utf8JsonWriter writer,
        EmploymentRelationshipState value,
        JsonSerializerOptions options) =>
        writer.WriteStringValue(RelationshipStateCodec.ToDatabase(value));
}

public sealed class RelationshipRoleJsonConverter : JsonConverter<RelationshipParticipantRole>
{
    public override RelationshipParticipantRole Read(
        ref Utf8JsonReader reader,
        Type typeToConvert,
        JsonSerializerOptions options) =>
        RelationshipRoleCodec.FromDatabase(
            reader.GetString() ?? throw new JsonException("Relationship role must be a string."));

    public override void Write(
        Utf8JsonWriter writer,
        RelationshipParticipantRole value,
        JsonSerializerOptions options) =>
        writer.WriteStringValue(RelationshipRoleCodec.ToDatabase(value));
}

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
    private readonly RelationshipTrialService? _trials;
    private readonly EmploymentContractService? _contracts;
    private readonly EmploymentContractAcceptanceService? _contractAcceptances;

    public EmploymentRelationshipsController(
        EmploymentRelationshipService service,
        RelationshipTrialService? trials = null,
        EmploymentContractService? contracts = null,
        EmploymentContractAcceptanceService? contractAcceptances = null)
    {
        _service = service;
        _trials = trials;
        _contracts = contracts;
        _contractAcceptances = contractAcceptances;
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

    [HttpPost("{relationshipId:guid}/trial")]
    public async Task<IActionResult> StartTrialAsync(
        Guid relationshipId,
        [FromBody] StartRelationshipTrialRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        if (_trials is null) return Problem(statusCode: 503, title: "Trial owners unavailable");
        try
        {
            return Ok(await _trials.StartAsync(
                tenantId, relationshipId, participantId, request.CorrelationId ?? Guid.NewGuid(), cancellationToken));
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
        catch (IllegalRelationshipTransitionException exception)
        {
            return Conflict(new { error = "ILLEGAL_RELATIONSHIP_TRANSITION", detail = exception.Message });
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Trial owner outcome unresolved", detail: exception.Message);
        }
    }

    [HttpPost("{relationshipId:guid}/contracts")]
    public async Task<IActionResult> ProposeContractAsync(
        Guid relationshipId,
        [FromBody] ProposeEmploymentContractRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        if (_contracts is null) return Problem(statusCode: 503, title: "Contract composition unavailable");

        try
        {
            var composition = await _contracts.ComposeAsync(
                tenantId,
                relationshipId,
                participantId,
                request.CommercialTerms,
                cancellationToken);
            var relationship = await _service.GetAsync(tenantId, relationshipId, cancellationToken);
            if (relationship is null) return NotFound();
            if (relationship.State == EmploymentRelationshipState.Configuring)
            {
                await _service.TransitionAsync(
                    tenantId,
                    relationshipId,
                    participantId,
                    RelationshipParticipantRole.Employer,
                    EmploymentRelationshipState.ContractPendingAcceptance,
                    request.CorrelationId ?? Guid.NewGuid(),
                    false,
                    cancellationToken);
            }
            else if (relationship.State != EmploymentRelationshipState.ContractPendingAcceptance)
            {
                return Conflict(new { error = "CONTRACT_PROPOSAL_STATE_CONFLICT" });
            }

            var response = ToContractResponse(composition);
            return composition.Created
                ? CreatedAtAction(nameof(ProposeContractAsync), new { relationshipId }, response)
                : Ok(response);
        }
        catch (ArgumentException exception)
        {
            return ValidationProblem(exception.Message);
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: 403, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (IllegalRelationshipTransitionException exception)
        {
            return Conflict(new { error = "ILLEGAL_RELATIONSHIP_TRANSITION", detail = exception.Message });
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Contract proposal unresolved");
        }
    }

    [HttpPost("{relationshipId:guid}/contracts/{version:int}/accept")]
    public async Task<IActionResult> AcceptContractAsync(
        Guid relationshipId,
        int version,
        [FromBody] AcceptEmploymentContractRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        if (_contractAcceptances is null || _contracts is null)
            return Problem(statusCode: 503, title: "Contract acceptance unavailable");

        try
        {
            var contract = await _contracts.GetByVersionAsync(tenantId, relationshipId, version, cancellationToken);
            if (contract is null) return NotFound();
            var result = await _contractAcceptances.AcceptAsync(
                tenantId,
                relationshipId,
                participantId,
                contract.ContractId,
                version,
                request.ContractHash,
                request.ScopeConfirmation,
                GetContractPortalAssurance(),
                request.CorrelationId ?? Guid.NewGuid(),
                cancellationToken);
            var response = ToAcceptanceResponse(result.Acceptance);
            return result.Created ? StatusCode(StatusCodes.Status201Created, response) : Ok(response);
        }
        catch (ContractStepUpRequiredException exception)
        {
            return Problem(statusCode: 403, title: "IDENTITY_STEP_UP_REQUIRED", detail: exception.Message);
        }
        catch (ContractScopeConfirmationRequiredException exception)
        {
            return ValidationProblem(exception.Message);
        }
        catch (ContractIdentityMismatchException)
        {
            return NotFound();
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: 403, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (IllegalRelationshipTransitionException exception)
        {
            return Conflict(new { error = "ILLEGAL_RELATIONSHIP_TRANSITION", detail = exception.Message });
        }
        catch (DbUpdateConcurrencyException)
        {
            return Conflict(new { error = "RELATIONSHIP_VERSION_CONFLICT" });
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Constitutional evidence unavailable");
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

    private ContractPortalAssurance GetContractPortalAssurance()
    {
        var hasPortalContext = !User.HasClaim("client_type", "service")
            && !string.Equals(User.FindFirstValue("identity_provider"), "whatsapp", StringComparison.OrdinalIgnoreCase);
        var authenticatedAt = User.FindFirstValue("auth_time") is string value
            && long.TryParse(value, out var timestamp)
            ? DateTimeOffset.FromUnixTimeSeconds(timestamp)
            : DateTimeOffset.MinValue;
        return new ContractPortalAssurance(hasPortalContext, authenticatedAt);
    }

    private static EmploymentContractResponse ToContractResponse(EmploymentContractComposition composition) => new(
        composition.Contract.ContractId,
        composition.Contract.Version,
        composition.Contract.ContractHash,
        composition.Contract.State,
        composition.Document,
        composition.Contract.CreatedAt);

    private static ContractAcceptanceResponse ToAcceptanceResponse(ContractAcceptance acceptance) => new(
        acceptance.AcceptanceId,
        acceptance.ContractId,
        acceptance.ContractVersion,
        acceptance.ContractHash,
        acceptance.AuthenticationAssurance,
        acceptance.AcceptanceEvidenceId,
        acceptance.AcceptedAt);

    private static EmploymentRelationshipResponse ToResponse(EmploymentRelationship relationship) =>
        new(
            relationship.RelationshipId,
            relationship.ProfessionalType,
            RelationshipStateCodec.ToDatabase(relationship.State),
            relationship.StateVersion,
            relationship.CreatedAt,
            relationship.UpdatedAt);
}