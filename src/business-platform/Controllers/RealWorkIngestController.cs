// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2, DC-4, DC-5 runtime ingestion (WC170-R005, WC170-R007, WC170-R008, WC170-R010)
// Constitutional basis: C-001, C-023, C-059, C-063
// IB: IB-170

using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.AgentOperation;
using Waooaw.BusinessPlatform.Services.RealWork;
using Waooaw.BusinessPlatform.Services.Workbench;
using Waooaw.WorkloadIdentity;

namespace Waooaw.BusinessPlatform.Controllers;

[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record RealWorkIngestRequest(
    string Type,
    Guid TenantId,
    Guid RelationshipId,
    TimelineEventInput? Event,
    ArtifactProposal? Artifact,
    AgentClaimInput? Claim,
    OperationProposalsInput? Proposals = null
);

/// <summary>WC174-R006: what an agent proposed for a relationship's calendar, plan, profile or goals. Suggestions only.</summary>
[JsonUnmappedMemberHandling(JsonUnmappedMemberHandling.Disallow)]
public sealed record OperationProposalsInput(IReadOnlyList<OperationProposal> Items);

/// <summary>
/// The Professional Runtime reports execution events, proposed artifacts and agent-stated claims here. The call is an
/// ADR-046 signed workload call (mTLS, route grant, signed envelope bound to the request digest); a shared token is not
/// accepted. The owner rules (artifact binding, stop fence, provider proof, blind-retry refusal) are applied on ingest.
/// </summary>
[ApiController]
[AllowAnonymous]
[Route("internal/v1/real-work/events")]
public sealed class RealWorkIngestController(
    InferenceWorkloadValidator validator,
    RealWorkArtifactService artifacts,
    RealWorkTimelineService timeline,
    RealWorkOutcomeService outcomes,
    ILogger<RealWorkIngestController> logger,
    AgentOperationService? operations = null
) : ControllerBase
{
    public const string Route = "internal/v1/real-work/events";
    public const string Purpose = "REAL_WORK_EVENTS";
    public const string Operation = "ingestRealWorkEvent";
    public const string ActorSource = "PR_RUNTIME";

    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web)
    {
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    };

    [HttpPost]
    [RequestSizeLimit(131072)]
    public async Task<IActionResult> IngestAsync(
        [FromBody] JsonElement body,
        CancellationToken cancellationToken
    )
    {
        PlatformWorkloadContext envelope;
        try
        {
            RuntimeEventStreamReader.ValidateUniqueProperties(body);
            var digest = Convert.ToHexStringLower(
                SHA256.HashData(
                    Encoding.UTF8.GetBytes(AgentAdmissionCanonicalizer.Canonicalize(body))
                )
            );
            envelope = await validator.RequirePlatformAsync(
                HttpContext,
                "professional-runtime",
                "business-platform",
                Purpose,
                "/" + Route,
                Operation,
                digest,
                cancellationToken,
                ActorSource
            );
        }
        catch (Exception error) when (error is InferenceWorkloadRejectedException or JsonException)
        {
            return StatusCode(403, new { code = "REAL_WORK_AUTHORITY_DENIED" });
        }

        try
        {
            var request =
                body.Deserialize<RealWorkIngestRequest>(Json)
                ?? throw new RealWorkConflictException("REAL_WORK_INVALID_REQUEST");
            // The signed envelope names the tenant and relationship the runtime is acting for. The body must name the
            // same ones, so a runtime fault can never write into another tenant's stream (WC171-R011, closes B6).
            if (
                !Guid.TryParse(envelope.TenantId, out var signedTenant)
                || !Guid.TryParse(envelope.RelationshipId, out var signedRelationship)
                || signedTenant != request.TenantId
                || signedRelationship != request.RelationshipId
            )
                return StatusCode(403, new { code = "REAL_WORK_AUTHORITY_DENIED" });
            switch (request.Type)
            {
                case "TIMELINE_EVENT" when request.Event is not null:
                    return Ok(
                        timeline.Ingest(request.TenantId, request.RelationshipId, request.Event)
                    );
                case "ARTIFACT_PROPOSAL" when request.Artifact is not null:
                    return StatusCode(
                        201,
                        artifacts.Propose(
                            request.TenantId,
                            request.RelationshipId,
                            request.Artifact
                        )
                    );
                case "AGENT_CLAIM" when request.Claim is not null:
                    outcomes.RecordAgentClaim(
                        request.TenantId,
                        request.RelationshipId,
                        request.Claim
                    );
                    return StatusCode(202, new { state = "RECORDED" });
                case "OPERATION_PROPOSALS"
                    when request.Proposals is not null && operations is not null:
                {
                    var context = new WorkbenchContext(
                        request.TenantId,
                        request.RelationshipId,
                        ActorSource,
                        Guid.Empty,
                        RelationshipParticipantRole.RelationshipManager,
                        WorkbenchAudiences.FromRole(
                            RelationshipParticipantRole.RelationshipManager
                        ),
                        HttpContext.TraceIdentifier
                    );
                    var outcome = await operations.ProposeAsync(
                        new OperationCaller(
                            request.TenantId,
                            request.RelationshipId,
                            Guid.Empty,
                            ActorSource,
                            context.Audience,
                            context
                        ),
                        request.Proposals.Items,
                        cancellationToken
                    );
                    return StatusCode(202, outcome);
                }
                default:
                    throw new RealWorkConflictException("REAL_WORK_INVALID_REQUEST");
            }
        }
        catch (Exception error) when (error is RealWorkConflictException or JsonException)
        {
            var code = (error as RealWorkConflictException)?.Code ?? "REAL_WORK_INVALID_REQUEST";
            logger.LogWarning("Real work ingestion refused: {Code}", code);
            return StatusCode(
                code switch
                {
                    "REAL_WORK_INVALID_REQUEST" or "REAL_WORK_SECRET_REJECTED" => 400,
                    "REAL_WORK_ARTIFACT_NOT_FOUND" => 404,
                    _ => 409,
                },
                new { code }
            );
        }
        catch (AgentOperationException error)
        {
            logger.LogWarning("Operation proposals refused: {Code}", error.Code);
            return StatusCode(error.Status, new { code = error.Code });
        }
    }
}
