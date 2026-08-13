// Implements: business-platform.openapi.yaml WC-065 Founder offerability
// constitutional_basis: C-002, C-023, C-059, C-063, C-089

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record EvaluateOfferabilityRequest(
    string SchemaVersion,
    string OfferingId,
    string AgentType,
    string BundleTier,
    long ProposedPricePaise);

[ApiController]
[Authorize]
[Route("api/v1/employment/relationships/{relationshipId:guid}/offerability")]
public sealed class OfferabilityController(
    EmploymentRelationshipService relationships,
    OfferabilityOrchestrationService orchestration) : ControllerBase
{
    [HttpPost("evaluations")]
    public async Task<IActionResult> EvaluateAsync(
        Guid relationshipId,
        [FromBody] EvaluateOfferabilityRequest request,
        [FromHeader(Name = "X-Correlation-ID")] Guid? correlationId,
        [FromHeader(Name = "Idempotency-Key")] Guid? idempotencyKey,
        CancellationToken cancellationToken)
    {
        if (!IsFounder() || !TryContext(out var tenantId, out var participantId)) return Forbid();
        if (request.SchemaVersion != "1.0" || correlationId is null || idempotencyKey is null)
            return Problem(400, "OFFERABILITY_REQUEST_INVALID");
        var relationship = await relationships.GetAsync(tenantId, relationshipId, cancellationToken);
        if (relationship is null) return Problem(404, "OFFERABILITY_NOT_ACCESSIBLE");
        try
        {
            var decision = await orchestration.EvaluateAsync(new OfferabilityEvaluationRequest(
                tenantId,
                relationshipId,
                relationship.StateVersion,
                participantId,
                correlationId.Value,
                idempotencyKey.Value,
                request.OfferingId,
                request.AgentType,
                request.BundleTier,
                request.ProposedPricePaise), cancellationToken);
            return Ok(new
            {
                schemaVersion = "1.0",
                decisionId = decision.DecisionId,
                relationshipId,
                disposition = decision.Disposition,
                directContributionPaise = decision.DirectContributionAmount,
                policyVersion = decision.PolicyVersion,
                ownerVersions = JsonSerializer.Deserialize<JsonElement>(decision.OwnerVersionsJson),
                reasons = JsonSerializer.Deserialize<JsonElement>(decision.ReasonsJson),
                evidenceId = decision.EvidenceId,
                producedAt = decision.ProducedAt,
                expiresAt = decision.ExpiresAt,
            });
        }
        catch (OfferabilityIdempotencyConflictException) { return Problem(409, "OFFERABILITY_IDEMPOTENCY_CONFLICT"); }
        catch (ConstitutionalActionDeniedException) { return Problem(423, "OFFERABILITY_BLOCKED"); }
        catch (ArgumentException) { return Problem(400, "OFFERABILITY_REQUEST_INVALID"); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return Problem(503, "OFFERABILITY_UNAVAILABLE");
        }
    }

    private bool IsFounder() => User.IsInRole("founder")
        || string.Equals(User.FindFirstValue("participant_role"), "FOUNDER", StringComparison.OrdinalIgnoreCase);

    private bool TryContext(out Guid tenantId, out Guid participantId)
    {
        tenantId = default;
        participantId = default;
        var participant = User.FindFirstValue("participant_id") ?? User.FindFirstValue(ClaimTypes.NameIdentifier);
        return HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && value is string tenant
            && Guid.TryParse(tenant, out tenantId)
            && Guid.TryParse(participant, out participantId);
    }

    private ObjectResult Problem(int status, string code) => StatusCode(status, new
    {
        type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
        title = "The offerability evaluation could not be completed",
        status,
        code,
        correlationId = User.FindFirstValue("correlation_id") ?? HttpContext.TraceIdentifier,
    });
}