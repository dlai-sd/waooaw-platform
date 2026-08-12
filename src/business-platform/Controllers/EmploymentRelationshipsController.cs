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
    bool ExplicitEmergencyRelease = false,
    Guid? OriginatingStopEvidenceId = null,
    Guid? OriginatingStopCorrelationId = null,
    string? ReleaseConfirmation = null,
    string? ReleaseJustification = null);

public sealed record StopEmploymentRelationshipRequest(Guid? CorrelationId = null);

public sealed record ReleaseEmploymentRelationshipStopRequest(
    Guid OriginatingStopEvidenceId,
    Guid OriginatingStopCorrelationId,
    string ReleaseConfirmation,
    string ReleaseJustification,
    [property: JsonConverter(typeof(RelationshipStateJsonConverter))] EmploymentRelationshipState TargetState,
    Guid? CorrelationId = null);

public sealed record StartRelationshipTrialRequest(Guid? CorrelationId = null);

public sealed record PrepareRelationshipHandoffRequest(
    string TargetChannel,
    string TargetConversationId,
    string CommandPurpose,
    Guid? CorrelationId = null);

public sealed record ActivateRelationshipHandoffRequest(
    string TargetConversationId,
    Guid? CorrelationId = null);

public sealed record RelationshipChannelBindingResponse(
    Guid BindingId,
    string Channel,
    string ConversationId,
    string Assurance,
    string Status);

public sealed record RelationshipHandoffResponse(
    Guid HandoffId,
    Guid RelationshipId,
    string Status,
    RelationshipChannelBindingResponse SourceBinding,
    RelationshipChannelBindingResponse TargetBinding,
    NeutralContinuityEnvelope ContinuityEnvelope,
    bool Replayed,
    Guid? ResolutionEvidenceId,
    DateTimeOffset? CommittedAt);

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

public sealed record ContractJourneyResponse(
    Guid ContractId,
    int Version,
    string ContractHash,
    EmploymentContractDocument Document,
    string RelationshipState,
    string AcceptanceState,
    string PaymentState,
    string ActivationState);

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
    private readonly RelationshipPaymentService? _payments;
    private readonly ActivationWorkflowDispatchService? _activationDispatch;
    private readonly ChannelContinuityService? _continuity;
    private readonly RelationshipEmergencyStopService? _emergencyStops;

    public EmploymentRelationshipsController(
        EmploymentRelationshipService service,
        RelationshipTrialService? trials = null,
        EmploymentContractService? contracts = null,
        EmploymentContractAcceptanceService? contractAcceptances = null,
        RelationshipPaymentService? payments = null,
        ActivationWorkflowDispatchService? activationDispatch = null,
        ChannelContinuityService? continuity = null,
        RelationshipEmergencyStopService? emergencyStops = null)
    {
        _service = service;
        _trials = trials;
        _contracts = contracts;
        _contractAcceptances = contractAcceptances;
        _payments = payments;
        _activationDispatch = activationDispatch;
        _continuity = continuity;
        _emergencyStops = emergencyStops;
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

    [HttpPost("{relationshipId:guid}/handoffs")]
    public async Task<IActionResult> PrepareHandoffAsync(
        Guid relationshipId,
        [FromHeader(Name = "Idempotency-Key")] string idempotencyKey,
        [FromBody] PrepareRelationshipHandoffRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetContinuityIdentity(out var identity)) return Forbid();
        if (_continuity is null) return Problem(statusCode: 503, title: "Channel continuity unavailable");
        if (!Guid.TryParse(idempotencyKey, out var parsedIdempotencyKey))
            return ValidationProblem("Idempotency-Key must be a UUID.");

        try
        {
            var handoff = await _continuity.PrepareAsync(
                tenantId,
                relationshipId,
                identity,
                new PrepareChannelHandoff(
                    request.TargetChannel,
                    request.TargetConversationId,
                    request.CommandPurpose,
                    request.CorrelationId ?? Guid.NewGuid(),
                    parsedIdempotencyKey),
                cancellationToken);
            return handoff.Replayed ? Ok(ToHandoffResponse(handoff)) : StatusCode(201, ToHandoffResponse(handoff));
        }
        catch (KeyNotFoundException) { return NotFound(); }
        catch (ArgumentException exception) { return ValidationProblem(exception.Message); }
        catch (ChannelContinuityLockedException exception) { return Problem(statusCode: 423, title: "Relationship is stopped", detail: exception.Message); }
        catch (ChannelContinuityConflictException exception) { return Conflict(new { error = "HANDOFF_CONFLICT", detail = exception.Message }); }
        catch (ConstitutionalActionDeniedException exception) { return Problem(statusCode: 403, title: "Constitutional authorization denied", detail: exception.Message); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Channel handoff remains unresolved");
        }
    }

    [HttpPost("{relationshipId:guid}/handoffs/{handoffId:guid}/activate")]
    public async Task<IActionResult> ActivateHandoffAsync(
        Guid relationshipId,
        Guid handoffId,
        [FromHeader(Name = "Idempotency-Key")] string idempotencyKey,
        [FromBody] ActivateRelationshipHandoffRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetContinuityIdentity(out var identity)) return Forbid();
        if (_continuity is null) return Problem(statusCode: 503, title: "Channel continuity unavailable");
        if (!Guid.TryParse(idempotencyKey, out var parsedIdempotencyKey))
            return ValidationProblem("Idempotency-Key must be a UUID.");
        if (!TryGetContinuityEnvelope(out var envelope)) return Forbid();

        try
        {
            var handoff = await _continuity.ActivateAsync(
                tenantId,
                relationshipId,
                handoffId,
                identity,
                new ActivateChannelHandoff(
                    request.TargetConversationId,
                    request.CorrelationId ?? Guid.NewGuid(),
                    parsedIdempotencyKey,
                    envelope),
                cancellationToken);
            return Ok(ToHandoffResponse(handoff));
        }
        catch (KeyNotFoundException) { return NotFound(); }
        catch (ChannelContinuityLockedException exception) { return Problem(statusCode: 423, title: "Relationship is stopped", detail: exception.Message); }
        catch (ChannelContinuityConflictException exception) { return Conflict(new { error = "HANDOFF_CONFLICT", detail = exception.Message }); }
        catch (ConstitutionalActionDeniedException exception) { return Problem(statusCode: 403, title: "Target authentication denied", detail: exception.Message); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Channel handoff remains unresolved");
        }
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
                cancellationToken,
                BuildEmergencyReleaseAuthorization(request));
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

    [HttpPost("{relationshipId:guid}/emergency-stop")]
    public async Task<IActionResult> StopAsync(
        Guid relationshipId,
        [FromBody] StopEmploymentRelationshipRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        if (_emergencyStops is null) return Problem(statusCode: 503, title: "Emergency Stop unavailable");
        var actorRole = await _service.GetActiveRoleAsync(tenantId, relationshipId, participantId, cancellationToken);
        if (actorRole is null) return NotFound();
        var current = await _service.GetAsync(tenantId, relationshipId, cancellationToken);
        if (current is null) return NotFound();
        if (current.State == EmploymentRelationshipState.StoppedEmergency) return Ok(ToResponse(current));
        try
        {
            var stopped = await _emergencyStops.StopAsync(
                tenantId, relationshipId, participantId, actorRole.Value,
                request.CorrelationId ?? Guid.NewGuid(), cancellationToken);
            return Ok(ToResponse(stopped!));
        }
        catch (IllegalRelationshipTransitionException exception)
        {
            return Conflict(new { error = "ILLEGAL_RELATIONSHIP_TRANSITION", detail = exception.Message });
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Emergency Stop remains unresolved");
        }
    }

    [HttpPost("{relationshipId:guid}/emergency-stop/release")]
    public async Task<IActionResult> ReleaseStopAsync(
        Guid relationshipId,
        [FromBody] ReleaseEmploymentRelationshipStopRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        try
        {
            var assurance = GetContractPortalAssurance();
            var released = await _service.TransitionAsync(
                tenantId, relationshipId, participantId, RelationshipParticipantRole.Employer,
                request.TargetState, request.CorrelationId ?? Guid.NewGuid(), true, cancellationToken,
                new EmergencyStopReleaseAuthorization(
                    assurance.IsKeycloakPortal,
                    User.FindFirstValue("authentication_assurance") ?? string.Empty,
                    assurance.AuthenticatedAt,
                    request.OriginatingStopEvidenceId,
                    request.OriginatingStopCorrelationId,
                    request.ReleaseConfirmation,
                    request.ReleaseJustification));
            return released is null ? NotFound() : Ok(ToResponse(released));
        }
        catch (IllegalRelationshipTransitionException exception)
        {
            return Conflict(new { error = "ILLEGAL_RELATIONSHIP_TRANSITION", detail = exception.Message });
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: 403, title: "Emergency Stop release denied", detail: exception.Message);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Emergency Stop remains active");
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

    [HttpGet("{relationshipId:guid}/contract-journey")]
    public async Task<IActionResult> GetContractJourneyAsync(
        Guid relationshipId, CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        if (_contracts is null) return Problem(statusCode: 503, title: "Contract projection unavailable");
        var relationship = await _service.GetAsync(tenantId, relationshipId, cancellationToken);
        if (relationship is null || !await _service.IsActiveParticipantAsync(
            tenantId, relationshipId, participantId, cancellationToken)) return NotFound();
        var contract = await _contracts.GetLatestAsync(tenantId, relationshipId, cancellationToken);
        if (contract is null) return NoContent();
        var accepted = relationship.AcceptedContractId == contract.Contract.ContractId;
        return Ok(new ContractJourneyResponse(
            contract.Contract.ContractId,
            contract.Contract.Version,
            contract.Contract.ContractHash,
            contract.Document,
            RelationshipStateCodec.ToDatabase(relationship.State),
            accepted ? "ACCEPTED" : "PENDING",
            relationship.State >= EmploymentRelationshipState.ActivationPending ? "CAPTURED" : "NOT_STARTED",
            relationship.State == EmploymentRelationshipState.Active ? "ACTIVE"
                : relationship.State == EmploymentRelationshipState.ActivationPending ? "PENDING" : "NOT_STARTED"));
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

    [HttpPost("{relationshipId:guid}/contracts/{version:int}/payments/onboarding-order")]
    public async Task<IActionResult> CreateOnboardingPaymentOrderAsync(
        Guid relationshipId,
        int version,
        [FromBody] PaymentProceedRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        if (_payments is null) return Problem(statusCode: 503, title: "Payment owner unavailable");

        try
        {
            return Ok(await _payments.CreateOnboardingOrderAsync(
                tenantId,
                relationshipId,
                participantId,
                version,
                request,
                GetContractPortalAssurance(),
                Guid.NewGuid(),
                cancellationToken));
        }
        catch (PaymentStepUpRequiredException exception)
        {
            return Problem(statusCode: 403, title: "IDENTITY_STEP_UP_REQUIRED", detail: exception.Message);
        }
        catch (PaymentConsentRequiredException exception)
        {
            return ValidationProblem(exception.Message);
        }
        catch (PaymentOrderingException)
        {
            return Conflict(new { error = "ACCEPTED_CONTRACT_REQUIRED" });
        }
        catch (PaymentItemizationMismatchException exception)
        {
            return Conflict(new { error = "CONTRACT_PAYMENT_ITEMIZATION_MISMATCH", detail = exception.Message });
        }
        catch (KeyNotFoundException)
        {
            return NotFound();
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: 403, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Payment owner outcome unresolved");
        }
    }

    [HttpPost("{relationshipId:guid}/activation")]
    public async Task<IActionResult> StartPaidActivationAsync(
        Guid relationshipId,
        [FromBody] StartPaidActivationRequest request,
        CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        if (_activationDispatch is null) return Problem(statusCode: 503, title: "Activation workflow unavailable");

        try
        {
            return Ok(await _activationDispatch.StartAsync(
                tenantId,
                relationshipId,
                participantId,
                request,
                GetContractPortalAssurance(),
                cancellationToken));
        }
        catch (PaymentStepUpRequiredException exception)
        {
            return Problem(statusCode: 403, title: "IDENTITY_STEP_UP_REQUIRED", detail: exception.Message);
        }
        catch (ConstitutionalActionDeniedException exception)
        {
            return Problem(statusCode: 403, title: "Constitutional authorization denied", detail: exception.Message);
        }
        catch (ActivationEligibilityException exception)
        {
            return Conflict(new { error = "ACTIVATION_NOT_ELIGIBLE", detail = exception.Message });
        }
        catch (ActivationConflictException exception)
        {
            return Conflict(new { error = "ACTIVATION_MATERIAL_CONFLICT", detail = exception.Message });
        }
        catch (ActivationOwnerUnavailableException exception)
        {
            return Problem(statusCode: 503, title: "Activation remains unresolved", detail: exception.Message);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "Activation remains unresolved");
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

    private bool TryGetContinuityIdentity(out ChannelContinuityIdentity identity)
    {
        identity = default!;
        if (!TryGetParticipantId(out var participantId)
            || User.FindFirstValue("channel") is not { Length: > 0 } channel
            || User.FindFirstValue("conversation_id") is not { Length: > 0 } conversationId
            || User.FindFirstValue("external_subject_hash") is not { Length: 64 } externalSubjectHash
            || User.FindFirstValue("authentication_assurance") is not { Length: > 0 } assurance
            || User.FindFirstValue("auth_time") is not string authTime
            || !long.TryParse(authTime, out var authenticatedAt))
        {
            return false;
        }

        identity = new ChannelContinuityIdentity(
            participantId,
            channel.ToUpperInvariant(),
            conversationId,
            externalSubjectHash,
            assurance.ToUpperInvariant(),
            DateTimeOffset.FromUnixTimeSeconds(authenticatedAt));
        return true;
    }

    private bool TryGetContinuityEnvelope(out NeutralContinuityEnvelope envelope)
    {
        envelope = default!;
        var value = User.FindFirstValue("continuity_envelope");
        if (string.IsNullOrWhiteSpace(value)) return false;
        try
        {
            envelope = JsonSerializer.Deserialize<NeutralContinuityEnvelope>(
                value, new JsonSerializerOptions(JsonSerializerDefaults.Web))!;
            return envelope is not null;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static RelationshipHandoffResponse ToHandoffResponse(ChannelHandoffResult handoff) => new(
        handoff.HandoffId,
        handoff.RelationshipId,
        handoff.Status,
        ToBindingResponse(handoff.SourceBinding),
        ToBindingResponse(handoff.TargetBinding),
        handoff.ContinuityEnvelope,
        handoff.Replayed,
        handoff.ResolutionEvidenceId,
        handoff.CommittedAt);

    private static RelationshipChannelBindingResponse ToBindingResponse(ChannelBinding binding) => new(
        binding.BindingId,
        binding.Channel,
        binding.ConversationId,
        binding.AssuranceLevel,
        binding.Status);

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

    private EmergencyStopReleaseAuthorization? BuildEmergencyReleaseAuthorization(
        TransitionEmploymentRelationshipRequest request)
    {
        if (!request.ExplicitEmergencyRelease
            || request.OriginatingStopEvidenceId is null
            || request.OriginatingStopCorrelationId is null
            || request.ReleaseConfirmation is null
            || request.ReleaseJustification is null)
        {
            return null;
        }
        var assurance = GetContractPortalAssurance();
        return new EmergencyStopReleaseAuthorization(
            assurance.IsKeycloakPortal,
            User.FindFirstValue("authentication_assurance") ?? string.Empty,
            assurance.AuthenticatedAt,
            request.OriginatingStopEvidenceId.Value,
            request.OriginatingStopCorrelationId.Value,
            request.ReleaseConfirmation,
            request.ReleaseJustification);
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