// Implements: architecture/reference/components/conversation-engine-whatsapp-solution-work-component.md §25.2 WC120-P1
// Constitutional basis: C-001, C-005, C-023, C-026, C-049, C-059, C-063

using System.Security.Claims;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record RegisteredContextHintV1(string ContextKey, string? SubjectReference);

public sealed record ConversationContributionRequestV1(
    string SchemaVersion,
    string ContributionKind,
    string? Text,
    string? AcceptedVoiceContributionReference,
    RegisteredContextHintV1? ContextHint,
    string ContextVersion,
    string? ExpectedSourceVersion,
    string PayloadDigest
);

public sealed record CancellationRequestV1(
    Guid TargetOperationId,
    string ReasonCode,
    string ExpectedSourceVersion,
    string PayloadDigest
);

public sealed record HandoffPrepareRequestV1(
    string SourceChannel,
    string TargetChannel,
    long CurrentSequence,
    string ContextVersion,
    string PayloadDigest
);

public sealed record HandoffActivateRequestV1(
    string TargetAuthenticationReference,
    string CheckpointDigest,
    string PayloadDigest
);

public sealed record HandoffRevertRequestV1(
    string SourceChannel,
    string CheckpointDigest,
    string ExpectedHandoffState,
    string ReasonCode,
    string PayloadDigest
);

public sealed record HandoffReceiptV1(
    Guid HandoffId,
    string SourceChannel,
    string TargetChannel,
    string State,
    DateTimeOffset ExpiresAt
);

public sealed record CandidateConversationProblemV1(
    string Type,
    string Title,
    int Status,
    string Code,
    Guid CorrelationId,
    bool Retryable,
    string? Remediation
);

[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[Route("api/v1/employment/relationships/{relationshipId:guid}/conversation")]
public sealed class ChannelNeutralConversationController(
    ConversationService conversationService,
    ConversationContextProfileService contextService,
    VoiceContributionService voiceService,
    ConversationalEmploymentService employmentService,
    IEmploymentCommandCoordinator employmentCoordinator,
    ConversationStopFence stopFence,
    ChannelContinuityService continuityService,
    IOptions<Wc120ConversationOptions> options,
    IDbContextFactory<EmploymentRelationshipDbContext>? relationshipFactory = null
) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetCanonicalConversationAsync(
        Guid relationshipId,
        [FromQuery] long afterSequence = 0,
        [FromQuery] int pageSize = 50,
        CancellationToken cancellationToken = default
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!options.Value.Enabled)
            return DisabledProblem();
        try
        {
            return Ok(
                await contextService.GetCanonicalAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    afterSequence,
                    pageSize,
                    cancellationToken
                )
            );
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
    }

    [HttpGet("operations/{operationId:guid}")]
    public async Task<IActionResult> GetOperationAsync(
        Guid relationshipId,
        Guid operationId,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!options.Value.Enabled)
            return DisabledProblem();

        var command = employmentService.GetCommand(tenantId, relationshipId, operationId);
        if (command is not null)
            return Ok(
                new
                {
                    operationId,
                    operationType = "COMMAND",
                    state = MapEmploymentState(command.State),
                    canonicalMessageId = (Guid?)null,
                    canonicalSequence = (long?)null,
                    correlationId = operationId,
                    states = new
                    {
                        delivery = "NOT_APPLICABLE",
                        execution = command.State,
                        customerDecision = "RECORDED",
                        constitutionalEvidence = command.EvidenceRefs.Count > 0
                            ? "RECORDED"
                            : "PENDING",
                    },
                    problem = (object?)null,
                }
            );
        try
        {
            var execution = await conversationService.GetExecutionAsync(
                tenantId,
                participantId,
                relationshipId,
                operationId,
                cancellationToken
            );
            return execution is null
                ? NotFound(
                    ProblemBody(404, "CONVERSATION_NOT_ACCESSIBLE", "Operation is not accessible.")
                )
                : Ok(
                    new
                    {
                        operationId,
                        operationType = "CONTRIBUTION",
                        state = MapExecutionState(execution.State),
                        canonicalMessageId = (Guid?)null,
                        canonicalSequence = (long?)null,
                        correlationId = operationId,
                        states = new
                        {
                            delivery = "ACCEPTED",
                            execution = execution.State,
                            customerDecision = "NOT_REQUIRED",
                            constitutionalEvidence = "PENDING",
                        },
                        problem = (object?)null,
                    }
                );
        }
        catch (ConversationNotAccessibleException)
        {
            return NotFound(
                ProblemBody(404, "CONVERSATION_NOT_ACCESSIBLE", "Operation is not accessible.")
            );
        }
    }

    [HttpPost("cancellations")]
    public async Task<IActionResult> RequestCancellationAsync(
        Guid relationshipId,
        [FromBody] CancellationRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!TryGetIdempotencyKey(out var idempotencyKey))
            return BadRequest(
                ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Idempotency-Key is required.")
            );
        if (!options.Value.Enabled)
            return DisabledProblem();
        if (
            string.IsNullOrWhiteSpace(request.ReasonCode)
            || request.ReasonCode.Length > 64
            || string.IsNullOrWhiteSpace(request.ExpectedSourceVersion)
            || request.ExpectedSourceVersion.Length > 128
            || !IsDigest(request.PayloadDigest)
        )
            return BadRequest(
                ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Cancellation request is invalid.")
            );
        try
        {
            var result = await conversationService.CancelAsync(
                tenantId,
                participantId,
                relationshipId,
                request.TargetOperationId,
                idempotencyKey,
                cancellationToken,
                request
            );
            return result.Replayed
                ? Ok(
                    new
                    {
                        operationId = result.Value.ExecutionId,
                        operationType = "CANCELLATION",
                        state = result.Value.State == "CANCELLED" ? "CANCELLED" : "RECONCILING",
                        correlationId = result.Value.ExecutionId,
                        states = new
                        {
                            delivery = "NOT_APPLICABLE",
                            execution = result.Value.State,
                            customerDecision = "CANCELLED",
                            constitutionalEvidence = "RECORDED",
                        },
                        problem = (object?)null,
                    }
                )
                : Accepted(
                    new
                    {
                        operationId = result.Value.ExecutionId,
                        operationType = "CANCELLATION",
                        state = "ACCEPTED",
                        acceptedAt = result.Value.UpdatedAt,
                        correlationId = result.Value.ExecutionId,
                    }
                );
        }
        catch (ConversationNotAccessibleException)
        {
            return NotFound(
                ProblemBody(404, "CONVERSATION_NOT_ACCESSIBLE", "Operation is not accessible.")
            );
        }
        catch (ConversationIdempotencyConflictException)
        {
            return Conflict(
                ProblemBody(409, "CONVERSATION_IDEMPOTENCY_CONFLICT", "Cancellation conflicts.")
            );
        }
    }

    [HttpPost("commands")]
    public async Task<IActionResult> SubmitCommandAsync(
        Guid relationshipId,
        [FromBody] JsonElement command,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!TryGetIdempotencyKey(out var idempotencyKey))
            return BadRequest(
                ProblemBody(
                    StatusCodes.Status400BadRequest,
                    "CONVERSATION_REQUEST_INVALID",
                    "A UUID Idempotency-Key header is required."
                )
            );
        if (!options.Value.Enabled)
            return DisabledProblem();
        if (await stopFence.IsLatchedAsync(tenantId, relationshipId, cancellationToken))
            return StatusCode(
                423,
                ProblemBody(423, "CONVERSATION_STOPPED", "Conversation execution is stopped.")
            );
        if (!HasFreshAal3())
            return StatusCode(
                StatusCodes.Status403Forbidden,
                ProblemBody(
                    StatusCodes.Status403Forbidden,
                    "CONVERSATION_ASSURANCE_REQUIRED",
                    "Fresh AAL3 authentication is required."
                )
            );
        try
        {
            var result = employmentService.Submit(
                tenantId,
                relationshipId,
                participantId,
                idempotencyKey,
                command
            );
            if (!result.Replayed)
            {
                var workspace =
                    employmentService.GetWorkspace(tenantId, relationshipId)
                    ?? throw new EmploymentProtocolException("EMPLOYMENT_SOURCE_UNAVAILABLE");
                await employmentCoordinator.CoordinateAsync(
                    new EmploymentCommandCoordinationContext(
                        tenantId,
                        relationshipId,
                        participantId,
                        result.Receipt.CommandId,
                        command.GetProperty("kind").GetString()!,
                        command,
                        workspace
                    ),
                    cancellationToken
                );
                return Accepted(
                    new
                    {
                        operationId = result.Receipt.CommandId,
                        operationType = "COMMAND",
                        state = "ACCEPTED",
                        acceptedAt = result.Receipt.AcceptedAt,
                        correlationId = result.Receipt.CommandId,
                    }
                );
            }
            return Ok(
                new
                {
                    operationId = result.Outcome.CommandId,
                    operationType = "COMMAND",
                    state = MapEmploymentState(result.Outcome.State),
                    canonicalMessageId = (Guid?)null,
                    canonicalSequence = (long?)null,
                    correlationId = result.Outcome.CommandId,
                    states = new
                    {
                        delivery = "NOT_APPLICABLE",
                        execution = result.Outcome.State,
                        customerDecision = "RECORDED",
                        constitutionalEvidence = result.Outcome.EvidenceRefs.Count > 0
                            ? "RECORDED"
                            : "PENDING",
                    },
                    problem = (object?)null,
                }
            );
        }
        catch (EmploymentProtocolException exception)
        {
            return exception.Code switch
            {
                "EMPLOYMENT_INVALID_REQUEST" => BadRequest(
                    ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Command request is invalid.")
                ),
                "EMPLOYMENT_VERSION_CONFLICT" or "EMPLOYMENT_IDEMPOTENCY_CONFLICT" => Conflict(
                    ProblemBody(409, "CONVERSATION_STATE_CONFLICT", "Command state conflicts.")
                ),
                "EMPLOYMENT_BLOCKED" => StatusCode(
                    423,
                    ProblemBody(423, "CONVERSATION_STOPPED", "Command execution is blocked.")
                ),
                _ => DisabledProblem(),
            };
        }
    }

    [HttpPost("contributions")]
    public async Task<IActionResult> SubmitContributionAsync(
        Guid relationshipId,
        [FromBody] ConversationContributionRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!TryGetIdempotencyKey(out var idempotencyKey))
            return BadRequest(
                ProblemBody(
                    StatusCodes.Status400BadRequest,
                    "CONVERSATION_REQUEST_INVALID",
                    "A UUID Idempotency-Key header is required."
                )
            );
        if (!options.Value.Enabled)
            return DisabledProblem();
        if (await stopFence.IsLatchedAsync(tenantId, relationshipId, cancellationToken))
            return StatusCode(
                423,
                ProblemBody(423, "CONVERSATION_STOPPED", "Conversation execution is stopped.")
            );
        if (
            request.SchemaVersion != "1.0"
            || !IsDigest(request.PayloadDigest)
            || string.IsNullOrWhiteSpace(request.ContextVersion)
            || (
                request.ContributionKind == "TEXT"
                && (
                    string.IsNullOrWhiteSpace(request.Text)
                    || request.AcceptedVoiceContributionReference is not null
                )
            )
            || (
                request.ContributionKind == "REVIEWED_VOICE"
                && (
                    request.Text is not null
                    || !Guid.TryParse(request.AcceptedVoiceContributionReference, out _)
                )
            )
            || request.ContributionKind is not ("TEXT" or "REVIEWED_VOICE")
        )
            return BadRequest(
                ProblemBody(
                    StatusCodes.Status400BadRequest,
                    "CONVERSATION_REQUEST_INVALID",
                    "Exactly one discriminator-matched contribution payload is required."
                )
            );

        try
        {
            var contextCurrent = await contextService.IsCurrentContextVersionAsync(
                tenantId,
                participantId,
                relationshipId,
                request.ContextVersion,
                cancellationToken
            );
            if (!contextCurrent)
                return Conflict(
                    ProblemBody(
                        StatusCodes.Status409Conflict,
                        "CONVERSATION_CONTEXT_STALE",
                        "The interaction context must be refreshed."
                    )
                );

            string text;
            string locale;
            if (request.ContributionKind == "REVIEWED_VOICE")
            {
                var acceptedVoice = await voiceService.ResolveAcceptedContributionAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    Guid.Parse(request.AcceptedVoiceContributionReference!),
                    cancellationToken
                );
                if (acceptedVoice is null)
                    return NotFound(
                        ProblemBody(
                            StatusCodes.Status404NotFound,
                            "CONVERSATION_NOT_ACCESSIBLE",
                            "Reviewed voice contribution is not accessible."
                        )
                    );
                text = acceptedVoice.Text;
                locale = acceptedVoice.Locale;
            }
            else
            {
                text = request.Text!.Trim();
                locale = "und";
            }

            var result = await conversationService.SendAsync(
                tenantId,
                participantId,
                relationshipId,
                idempotencyKey,
                new SendConversationMessageRequestV1(
                    "1.0",
                    idempotencyKey,
                    request.ContextHint?.ContextKey ?? "CONVERSATION",
                    [new ConversationTextBlockV1("1.0", "TEXT", text, locale)],
                    locale,
                    ContextVersion: request.ContextVersion,
                    PayloadDigest: request.PayloadDigest
                ),
                cancellationToken
            );
            var operationId = result.Value.ExecutionId ?? result.Value.Message.MessageId;
            if (!result.Replayed)
                return Accepted(
                    new
                    {
                        operationId,
                        operationType = "CONTRIBUTION",
                        state = "ACCEPTED",
                        acceptedAt = result.Value.Message.AcceptedAt,
                        correlationId = operationId,
                    }
                );
            return Ok(
                new
                {
                    operationId,
                    operationType = "CONTRIBUTION",
                    state = "ACCEPTED",
                    canonicalMessageId = result.Value.Message.MessageId,
                    canonicalSequence = result.Value.Message.Sequence,
                    correlationId = operationId,
                    states = new
                    {
                        delivery = result.Value.Message.DeliveryState,
                        execution = result.Value.Message.ProcessingState,
                        customerDecision = "NOT_REQUIRED",
                        constitutionalEvidence = result.Value.Message.EvidenceState,
                    },
                    problem = (object?)null,
                }
            );
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
        catch (ConversationNotAccessibleException)
        {
            return NotFound(
                ProblemBody(
                    StatusCodes.Status404NotFound,
                    "CONVERSATION_NOT_ACCESSIBLE",
                    "Conversation is not accessible."
                )
            );
        }
        catch (ConversationIdempotencyConflictException)
        {
            return Conflict(
                ProblemBody(
                    StatusCodes.Status409Conflict,
                    "CONVERSATION_IDEMPOTENCY_CONFLICT",
                    "Idempotency identity conflicts with a prior contribution."
                )
            );
        }
    }

    [HttpGet("contexts")]
    public async Task<IActionResult> ListContextsAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!options.Value.Enabled)
            return DisabledProblem();
        try
        {
            return Ok(
                await contextService.ListAvailableContextsAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    cancellationToken
                )
            );
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
    }

    [HttpGet("profile")]
    public async Task<IActionResult> GetProfileAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!options.Value.Enabled)
            return DisabledProblem();
        try
        {
            return Ok(
                await contextService.GetProfileAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    cancellationToken
                )
            );
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
    }

    [HttpPost("profile/corrections")]
    public async Task<IActionResult> CorrectProfileAsync(
        Guid relationshipId,
        [FromBody] ContextCorrectionRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!options.Value.Enabled)
            return DisabledProblem();
        try
        {
            return Accepted(
                await contextService.CorrectAsync(
                    options.Value.Environment,
                    tenantId,
                    participantId,
                    relationshipId,
                    request,
                    cancellationToken
                )
            );
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
    }

    [HttpPost("handoffs")]
    public async Task<IActionResult> PrepareHandoffAsync(
        Guid relationshipId,
        [FromBody] HandoffPrepareRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (
            !TryGetIdempotencyKey(out var idempotencyKey)
            || !TryGetCorrelationId(out var correlationId)
            || !TryGetContinuityIdentity(out var identity)
            || identity.ParticipantId != participantId
        )
            return BadRequest(
                ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Handoff headers are invalid.")
            );
        if (!options.Value.Enabled)
            return DisabledProblem();
        if (
            !IsChannel(request.SourceChannel)
            || !IsChannel(request.TargetChannel)
            || request.SourceChannel == request.TargetChannel
            || !string.Equals(identity.Channel, request.SourceChannel, StringComparison.Ordinal)
            || request.CurrentSequence < 0
            || string.IsNullOrWhiteSpace(request.ContextVersion)
            || !IsDigest(request.PayloadDigest)
        )
            return BadRequest(
                ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Handoff request is invalid.")
            );
        if (await stopFence.IsLatchedAsync(tenantId, relationshipId, cancellationToken))
            return StatusCode(
                423,
                ProblemBody(423, "CONVERSATION_STOPPED", "Conversation handoff is stopped.")
            );
        try
        {
            var conversation = await contextService.GetCanonicalAsync(
                tenantId,
                participantId,
                relationshipId,
                request.CurrentSequence,
                1,
                cancellationToken
            );
            if (
                conversation.CurrentSequence != request.CurrentSequence
                || !await contextService.IsCurrentContextVersionAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    request.ContextVersion,
                    cancellationToken
                )
            )
                return Conflict(
                    ProblemBody(409, "CONVERSATION_CONTEXT_STALE", "Handoff context is stale.")
                );
            var handoff = await continuityService.PrepareAsync(
                tenantId,
                relationshipId,
                identity,
                new PrepareChannelHandoff(
                    request.TargetChannel,
                    $"pending:{idempotencyKey:D}",
                    "CONVERSATION_HANDOFF",
                    correlationId,
                    idempotencyKey,
                    request.PayloadDigest,
                    request.ContextVersion,
                    request.CurrentSequence
                ),
                cancellationToken
            );
            return StatusCode(201, ToHandoffReceipt(handoff));
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
        catch (ChannelContinuityConflictException)
        {
            return Conflict(
                ProblemBody(409, "CONVERSATION_HANDOFF_CONFLICT", "Handoff conflicts.")
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return StatusCode(
                403,
                ProblemBody(403, "CONVERSATION_AUTHORITY_DENIED", "Handoff is not authorized.")
            );
        }
    }

    [HttpPost("handoffs/{handoffId:guid}/activate")]
    public async Task<IActionResult> ActivateHandoffAsync(
        Guid relationshipId,
        Guid handoffId,
        [FromBody] HandoffActivateRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (
            !TryGetIdempotencyKey(out var idempotencyKey)
            || !TryGetCorrelationId(out var correlationId)
            || !TryGetContinuityIdentity(out var identity)
            || identity.ParticipantId != participantId
        )
            return BadRequest(
                ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Handoff headers are invalid.")
            );
        if (!options.Value.Enabled)
            return DisabledProblem();
        if (
            relationshipFactory is null
            || string.IsNullOrWhiteSpace(request.TargetAuthenticationReference)
            || request.TargetAuthenticationReference.Length > 256
            || !IsDigest(request.CheckpointDigest)
            || !IsDigest(request.PayloadDigest)
            || !FixedEquals(
                request.TargetAuthenticationReference,
                User.FindFirstValue("authentication_reference") ?? string.Empty
            )
        )
            return StatusCode(
                403,
                ProblemBody(
                    403,
                    "CONVERSATION_ASSURANCE_REQUIRED",
                    "Fresh target authentication is required."
                )
            );
        try
        {
            var envelope = await LoadContinuityEnvelopeAsync(
                tenantId,
                relationshipId,
                handoffId,
                cancellationToken
            );
            var handoff = await continuityService.ActivateAsync(
                tenantId,
                relationshipId,
                handoffId,
                identity,
                new ActivateChannelHandoff(
                    identity.ConversationId,
                    correlationId,
                    idempotencyKey,
                    envelope,
                    request.CheckpointDigest,
                    request.PayloadDigest
                ),
                cancellationToken
            );
            return Ok(ToHandoffReceipt(handoff));
        }
        catch (KeyNotFoundException)
        {
            return NotFound(
                ProblemBody(404, "CONVERSATION_NOT_ACCESSIBLE", "Handoff is not accessible.")
            );
        }
        catch (ChannelContinuityConflictException)
        {
            return Conflict(
                ProblemBody(409, "CONVERSATION_HANDOFF_CONFLICT", "Handoff conflicts.")
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return StatusCode(
                403,
                ProblemBody(403, "CONVERSATION_ASSURANCE_REQUIRED", "Handoff assurance failed.")
            );
        }
    }

    [HttpPost("handoffs/{handoffId:guid}/revert")]
    public async Task<IActionResult> RevertHandoffAsync(
        Guid relationshipId,
        Guid handoffId,
        [FromBody] HandoffRevertRequestV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (
            !TryGetIdempotencyKey(out var idempotencyKey)
            || !TryGetCorrelationId(out var correlationId)
        )
            return BadRequest(
                ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Handoff headers are invalid.")
            );
        if (!options.Value.Enabled)
            return DisabledProblem();
        if (
            relationshipFactory is null
            || !IsChannel(request.SourceChannel)
            || !IsDigest(request.CheckpointDigest)
            || request.ExpectedHandoffState is not ("PREPARED" or "UNKNOWN")
            || request.ReasonCode
                is not (
                    "TARGET_AUTHENTICATION_FAILED"
                    or "TARGET_UNAVAILABLE"
                    or "CUSTOMER_CANCELLED"
                    or "OUTCOME_UNKNOWN"
                )
            || !IsDigest(request.PayloadDigest)
        )
            return BadRequest(
                ProblemBody(400, "CONVERSATION_REQUEST_INVALID", "Handoff revert is invalid.")
            );
        try
        {
            await using var db = await relationshipFactory.CreateDbContextAsync(cancellationToken);
            var checkpoint =
                await db
                    .ContinuityCheckpoints.AsNoTracking()
                    .SingleOrDefaultAsync(
                        value =>
                            value.TenantId == tenantId
                            && value.RelationshipId == relationshipId
                            && value.CheckpointId == handoffId,
                        cancellationToken
                    )
                ?? throw new KeyNotFoundException();
            var sourceBinding = await db
                .ChannelBindings.AsNoTracking()
                .SingleAsync(
                    value =>
                        value.TenantId == tenantId && value.BindingId == checkpoint.SourceBindingId,
                    cancellationToken
                );
            if (
                !string.Equals(
                    sourceBinding.Channel,
                    request.SourceChannel,
                    StringComparison.Ordinal
                )
            )
                return Conflict(
                    ProblemBody(409, "CONVERSATION_HANDOFF_CONFLICT", "Source channel conflicts.")
                );
            return Ok(
                ToHandoffReceipt(
                    await continuityService.RevertAsync(
                        tenantId,
                        relationshipId,
                        handoffId,
                        participantId,
                        new RevertChannelHandoff(
                            checkpoint.SourceBindingId,
                            correlationId,
                            idempotencyKey,
                            request.CheckpointDigest,
                            request.ExpectedHandoffState,
                            request.ReasonCode,
                            request.PayloadDigest
                        ),
                        cancellationToken
                    )
                )
            );
        }
        catch (KeyNotFoundException)
        {
            return NotFound(
                ProblemBody(
                    StatusCodes.Status404NotFound,
                    "CONVERSATION_NOT_ACCESSIBLE",
                    "Conversation handoff is not accessible."
                )
            );
        }
        catch (ChannelContinuityConflictException)
        {
            return Conflict(
                ProblemBody(
                    StatusCodes.Status409Conflict,
                    "CONVERSATION_HANDOFF_CONFLICT",
                    "Conversation handoff state conflicts with this request."
                )
            );
        }
        catch (ConstitutionalActionDeniedException)
        {
            return StatusCode(
                StatusCodes.Status403Forbidden,
                ProblemBody(
                    StatusCodes.Status403Forbidden,
                    "CONVERSATION_AUTHORITY_DENIED",
                    "Conversation handoff is not authorized."
                )
            );
        }
    }

    [HttpGet("messages/{messageId:guid}/states")]
    public async Task<IActionResult> GetMessageStatesAsync(
        Guid relationshipId,
        Guid messageId,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!options.Value.Enabled)
            return DisabledProblem();
        try
        {
            return Ok(
                await contextService.GetMessageStatesAsync(
                    tenantId,
                    participantId,
                    relationshipId,
                    messageId,
                    cancellationToken
                )
            );
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
    }

    [HttpPost("data-rights")]
    public async Task<IActionResult> RequestDataRightAsync(
        Guid relationshipId,
        [FromBody] RequestConversationDataRightV1 request,
        CancellationToken cancellationToken
    )
    {
        if (!TryGetAuthority(out var tenantId, out var participantId))
            return UnauthorizedProblem();
        if (!TryGetIdempotencyKey(out var idempotencyKey))
            return BadRequest(
                ProblemBody(
                    StatusCodes.Status400BadRequest,
                    "CONVERSATION_REQUEST_INVALID",
                    "A UUID Idempotency-Key header is required."
                )
            );
        if (!options.Value.Enabled)
            return DisabledProblem();
        if (!HasFreshAal3())
            return StatusCode(
                403,
                ProblemBody(
                    403,
                    "CONVERSATION_ASSURANCE_REQUIRED",
                    "Fresh portal authentication is required."
                )
            );
        try
        {
            return Accepted(
                await contextService.RequestDataRightAsync(
                    options.Value.Environment,
                    tenantId,
                    participantId,
                    relationshipId,
                    idempotencyKey,
                    request,
                    cancellationToken
                )
            );
        }
        catch (ConversationContextConflictException exception)
        {
            return ContextProblem(exception);
        }
    }

    private bool TryGetAuthority(out Guid tenantId, out Guid participantId)
    {
        tenantId = default;
        participantId = default;
        var tenantValid =
            HttpContext.Items.TryGetValue(
                TenantIsolationMiddleware.TenantIdItemKey,
                out var tenantValue
            )
            && tenantValue is string tenantText
            && Guid.TryParse(tenantText, out tenantId);
        var participantValue =
            User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        return tenantValid && Guid.TryParse(participantValue, out participantId);
    }

    private bool TryGetIdempotencyKey(out Guid idempotencyKey) =>
        Guid.TryParse(Request.Headers["Idempotency-Key"].FirstOrDefault(), out idempotencyKey);

    private bool TryGetCorrelationId(out Guid correlationId) =>
        Guid.TryParse(Request.Headers["X-Correlation-ID"].FirstOrDefault(), out correlationId);

    private bool TryGetContinuityIdentity(out ChannelContinuityIdentity identity)
    {
        identity = default!;
        if (
            !Guid.TryParse(
                User.FindFirstValue("participant_id")
                    ?? User.FindFirstValue(ClaimTypes.NameIdentifier),
                out var participantId
            )
            || User.FindFirstValue("channel") is not { Length: > 0 } channel
            || User.FindFirstValue("conversation_id") is not { Length: > 0 } conversationId
            || User.FindFirstValue("external_subject_hash")
                is not { Length: 64 } externalSubjectHash
            || User.FindFirstValue("authentication_assurance") is not { Length: > 0 } assurance
            || !long.TryParse(User.FindFirstValue("auth_time"), out var authenticatedAt)
        )
            return false;
        identity = new(
            participantId,
            channel.ToUpperInvariant(),
            conversationId,
            externalSubjectHash,
            assurance.ToUpperInvariant(),
            DateTimeOffset.FromUnixTimeSeconds(authenticatedAt)
        );
        return true;
    }

    private async Task<NeutralContinuityEnvelope> LoadContinuityEnvelopeAsync(
        Guid tenantId,
        Guid relationshipId,
        Guid handoffId,
        CancellationToken cancellationToken
    )
    {
        await using var db = await relationshipFactory!.CreateDbContextAsync(cancellationToken);
        var envelopeJson = await db
            .ContinuityCheckpoints.AsNoTracking()
            .Where(value =>
                value.TenantId == tenantId
                && value.RelationshipId == relationshipId
                && value.CheckpointId == handoffId
            )
            .Select(value => value.ContinuityEnvelopeJson)
            .SingleOrDefaultAsync(cancellationToken);
        if (envelopeJson is null)
            throw new KeyNotFoundException();
        return JsonSerializer.Deserialize<NeutralContinuityEnvelope>(
                envelopeJson,
                new JsonSerializerOptions(JsonSerializerDefaults.Web)
            ) ?? throw new KeyNotFoundException();
    }

    private static HandoffReceiptV1 ToHandoffReceipt(ChannelHandoffResult handoff)
    {
        var expiresAt = handoff.ContinuityEnvelope.IssuedAt.AddMinutes(15);
        var state = handoff.Status switch
        {
            "COMMITTED" => "ACTIVE",
            "REVERTED" => "REVERTED",
            "PREPARED" when expiresAt <= DateTimeOffset.UtcNow => "EXPIRED",
            _ => "PREPARED",
        };
        return new(
            handoff.HandoffId,
            handoff.SourceBinding.Channel,
            handoff.TargetBinding.Channel,
            state,
            expiresAt
        );
    }

    private bool HasFreshAal3()
    {
        if (
            !string.Equals(
                User.FindFirstValue("authentication_assurance"),
                "AAL3_FRESH",
                StringComparison.Ordinal
            ) || !long.TryParse(User.FindFirstValue("auth_time"), out var unixTime)
        )
            return false;
        var age = DateTimeOffset.UtcNow - DateTimeOffset.FromUnixTimeSeconds(unixTime);
        return age >= TimeSpan.FromSeconds(-60) && age <= TimeSpan.FromMinutes(5);
    }

    private static string MapEmploymentState(string state) =>
        state switch
        {
            "COMPLETED" => "COMMITTED",
            "REJECTED" or "BLOCKED" => "DENIED",
            "CONFLICT" => "CONFLICTED",
            "FAILED" => "FAILED",
            _ => "RECONCILING",
        };

    private static string MapExecutionState(string state) =>
        state switch
        {
            "COMPLETED" => "COMMITTED",
            "CANCELLED" => "CANCELLED",
            "FAILED" => "FAILED",
            "STOPPED" => "DENIED",
            _ => "RECONCILING",
        };

    private IActionResult ContextProblem(ConversationContextConflictException exception) =>
        exception.Code switch
        {
            "CONVERSATION_NOT_ACCESSIBLE" or "CONVERSATION_MESSAGE_NOT_FOUND" => NotFound(
                ProblemBody(
                    StatusCodes.Status404NotFound,
                    "CONVERSATION_NOT_ACCESSIBLE",
                    "Conversation is not accessible."
                )
            ),
            var code when code.EndsWith("_INVALID", StringComparison.Ordinal) => BadRequest(
                ProblemBody(
                    StatusCodes.Status400BadRequest,
                    "CONVERSATION_REQUEST_INVALID",
                    "Conversation request is invalid."
                )
            ),
            "CONVERSATION_POLICY_UNAVAILABLE" or "CONVERSATION_CONTEXT_UNAVAILABLE" => StatusCode(
                StatusCodes.Status503ServiceUnavailable,
                ProblemBody(
                    StatusCodes.Status503ServiceUnavailable,
                    exception.Code,
                    "Required conversation policy is unavailable."
                )
            ),
            _ => Conflict(
                ProblemBody(
                    StatusCodes.Status409Conflict,
                    exception.Code,
                    "Authoritative conversation state must be reconciled."
                )
            ),
        };

    private IActionResult UnauthorizedProblem() =>
        Unauthorized(
            ProblemBody(
                StatusCodes.Status401Unauthorized,
                "CONVERSATION_SESSION_REQUIRED",
                "Authenticated conversation session required."
            )
        );

    private IActionResult DisabledProblem() =>
        StatusCode(
            StatusCodes.Status503ServiceUnavailable,
            ProblemBody(
                StatusCodes.Status503ServiceUnavailable,
                "CONVERSATION_UNAVAILABLE",
                "The channel-neutral conversation capability is unavailable."
            )
        );

    private static CandidateConversationProblemV1 ProblemBody(
        int status,
        string code,
        string title
    ) =>
        new(
            $"https://api.waooaw.com/problems/{MapProblemCode(code).Replace('_', '-')}",
            title,
            status,
            MapProblemCode(code),
            Guid.NewGuid(),
            status >= 500,
            null
        );

    private static string MapProblemCode(string code) =>
        code switch
        {
            "CONVERSATION_REQUEST_INVALID" => "invalid_request",
            "CONVERSATION_ASSURANCE_REQUIRED" => "assurance_required",
            "CONVERSATION_AUTHORITY_DENIED" => "assurance_required",
            "CONVERSATION_CONTEXT_STALE" => "context_stale",
            "CONVERSATION_CONTEXT_AMBIGUOUS" => "context_ambiguous",
            "CONVERSATION_IDEMPOTENCY_CONFLICT" => "idempotency_conflict",
            "CONVERSATION_STATE_CONFLICT" => "source_version_conflict",
            "CONVERSATION_HANDOFF_CONFLICT" => "source_version_conflict",
            "CONVERSATION_STOPPED" => "stop_active",
            "CONVERSATION_POLICY_UNAVAILABLE" => "policy_unavailable",
            "CONVERSATION_CONTEXT_UNAVAILABLE" => "policy_unavailable",
            "CONVERSATION_UNAVAILABLE" => "constitutional_governance_unavailable",
            _ => "not_accessible",
        };

    private static bool IsDigest(string value) =>
        value.Length == 64
        && value.All(character => character is >= '0' and <= '9' or >= 'a' and <= 'f');

    private static bool IsChannel(string value) => value is "WEB" or "WHATSAPP" or "MOBILE";

    private static bool FixedEquals(string left, string right) =>
        left.Length == right.Length
        && CryptographicOperations.FixedTimeEquals(
            System.Text.Encoding.UTF8.GetBytes(left),
            System.Text.Encoding.UTF8.GetBytes(right)
        );
}
