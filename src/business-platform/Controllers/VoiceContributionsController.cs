// Implements: architecture/reference/components/wc062-voice-solution-contract.md § BP Public Operations
// constitutional_basis: C-001, C-005, C-023, C-026, C-042, C-049, C-059, C-063

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

[ApiController]
[Authorize]
[Route("api/v1/employment/relationships/{relationshipId:guid}/voice-contributions")]
public sealed class VoiceContributionsController(VoiceContributionService service) : ControllerBase
{
    [HttpPost("sessions")]
    public Task<IActionResult> CreateAsync(
        Guid relationshipId,
        [FromHeader(Name = "Idempotency-Key")] Guid idempotencyKey,
        [FromBody] CreateVoiceContributionSessionRequestV1 request,
        CancellationToken cancellationToken) => ExecuteAsync(async (tenantId, participantId) =>
    {
        var result = await service.CreateAsync(
            tenantId, participantId, relationshipId, idempotencyKey, request, cancellationToken);
        return result.Replayed ? Ok(result.Value) : StatusCode(StatusCodes.Status201Created, result.Value);
    });

    [HttpGet("sessions/{sessionId:guid}")]
    public Task<IActionResult> GetAsync(Guid relationshipId, Guid sessionId, CancellationToken cancellationToken) =>
        ExecuteAsync(async (tenantId, participantId) => Ok(await service.GetAsync(
            tenantId, participantId, relationshipId, sessionId, cancellationToken)));

    [HttpPost("sessions/{sessionId:guid}/audio")]
    [RequestSizeLimit(16 * 1024 * 1024)]
    public Task<IActionResult> UploadAsync(
        Guid relationshipId,
        Guid sessionId,
        [FromHeader(Name = "Idempotency-Key")] Guid idempotencyKey,
        IFormFile audio,
        CancellationToken cancellationToken) => ExecuteAsync(async (tenantId, participantId) =>
    {
        await using var stream = audio.OpenReadStream();
        var result = await service.UploadAsync(
            tenantId,
            participantId,
            relationshipId,
            sessionId,
            idempotencyKey,
            stream,
            audio.ContentType,
            cancellationToken);
        return result.Replayed ? Ok(result.Value) : Accepted(result.Value);
    });

    [HttpGet("sessions/{sessionId:guid}/transcript")]
    public Task<IActionResult> GetTranscriptAsync(
        Guid relationshipId,
        Guid sessionId,
        CancellationToken cancellationToken) => ExecuteAsync(async (tenantId, participantId) =>
            Ok(await service.GetTranscriptAsync(
                tenantId, participantId, relationshipId, sessionId, cancellationToken)));

    [HttpPut("sessions/{sessionId:guid}/correction")]
    public Task<IActionResult> CorrectAsync(
        Guid relationshipId,
        Guid sessionId,
        [FromHeader(Name = "Idempotency-Key")] Guid idempotencyKey,
        [FromBody] VoiceCorrectionRequestV1 request,
        CancellationToken cancellationToken) => ExecuteAsync(async (tenantId, participantId) =>
            Ok((await service.CorrectAsync(
                tenantId, participantId, relationshipId, sessionId, idempotencyKey, request, cancellationToken)).Value));

    [HttpPost("sessions/{sessionId:guid}/send")]
    public Task<IActionResult> SendAsync(
        Guid relationshipId,
        Guid sessionId,
        [FromHeader(Name = "Idempotency-Key")] Guid idempotencyKey,
        [FromBody] SendVoiceContributionRequestV1 request,
        CancellationToken cancellationToken) => ExecuteAsync(async (tenantId, participantId) =>
            Ok((await service.SendAsync(
                tenantId, participantId, relationshipId, sessionId, idempotencyKey, request, cancellationToken)).Value));

    [HttpPost("sessions/{sessionId:guid}/cancel")]
    public Task<IActionResult> CancelAsync(
        Guid relationshipId,
        Guid sessionId,
        [FromHeader(Name = "Idempotency-Key")] Guid idempotencyKey,
        [FromBody] CancelVoiceContributionRequestV1 request,
        CancellationToken cancellationToken) => ExecuteAsync(async (tenantId, participantId) =>
            Ok((await service.CancelAsync(
                tenantId, participantId, relationshipId, sessionId, idempotencyKey, request, cancellationToken)).Value));

    [HttpPost("{contributionId:guid}/erasure")]
    public Task<IActionResult> EraseAsync(
        Guid relationshipId,
        Guid contributionId,
        [FromHeader(Name = "Idempotency-Key")] Guid idempotencyKey,
        [FromBody] VoicePayloadErasureRequestV1 request,
        CancellationToken cancellationToken) => ExecuteAsync(async (tenantId, participantId) =>
    {
        var result = await service.EraseAsync(
            tenantId, participantId, relationshipId, contributionId, idempotencyKey, request, cancellationToken);
        return result.Replayed ? Ok(result.Value) : Accepted(result.Value);
    });

    private async Task<IActionResult> ExecuteAsync(Func<Guid, Guid, Task<IActionResult>> action)
    {
        if (!TryGetTenantId(out var tenantId) || !TryGetParticipantId(out var participantId)) return Forbid();
        try
        {
            return await action(tenantId, participantId);
        }
        catch (VoiceRequestException exception)
        {
            return Problem(statusCode: 400, title: "invalid_request", detail: exception.Message);
        }
        catch (VoiceInvalidMediaException)
        {
            return Problem(statusCode: 415, title: "invalid_media");
        }
        catch (VoiceLimitExceededException)
        {
            return Problem(statusCode: 413, title: "limit_exceeded");
        }
        catch (VoiceNotAccessibleException)
        {
            return Problem(statusCode: 404, title: "not_authorized");
        }
        catch (VoiceConflictException exception)
        {
            return Problem(statusCode: 409, title: "conflict", detail: exception.Message);
        }
        catch (VoiceBlockedException)
        {
            return Problem(statusCode: 423, title: "quarantined");
        }
        catch (VoiceUnavailableException)
        {
            return Problem(statusCode: 503, title: "temporarily_unavailable");
        }
        catch (ConstitutionalActionDeniedException)
        {
            return Problem(statusCode: 423, title: "stopped");
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(statusCode: 503, title: "unknown");
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
        var value = User.FindFirstValue("participant_id") ?? User.FindFirstValue(ClaimTypes.NameIdentifier);
        return Guid.TryParse(value, out participantId);
    }
}