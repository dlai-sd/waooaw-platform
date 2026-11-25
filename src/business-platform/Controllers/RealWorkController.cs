// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-2 to DC-5 customer projections (WC170-R005 to WC170-R008)
// Constitutional basis: C-001, C-005, C-023, C-059, C-063
// IB: IB-170

using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Services.RealWork;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// What the customer reads of real work: the locked artifacts that control execution with their two decisions, the
/// execution timeline, and traceable outcomes. Reads are tenant-scoped and answer one closed not-accessible code.
/// The decisions themselves are the closed employment commands, so the one command pipeline stays the only write path.
/// </summary>
[ApiController]
[Authorize]
[CustomerIdentityRoute(requiresMembership: true)]
[Route("api/v1/employment/relationships/{relationshipId:guid}/real-work")]
public sealed class RealWorkController(
    EmploymentRelationshipService relationships,
    IEmploymentProtocolGate gate,
    ConversationalEmploymentService employment,
    RealWorkArtifactService artifacts,
    RealWorkDecisionService decisions,
    RealWorkTimelineService timeline,
    RealWorkOutcomeService outcomes
) : ControllerBase
{
    [HttpGet("artifacts")]
    public async Task<IActionResult> ListArtifactsAsync(
        Guid relationshipId,
        [FromQuery] string? artifactType,
        CancellationToken cancellationToken
    )
    {
        if (await TenantAsync(relationshipId, cancellationToken) is not { } tenantId)
            return NotAccessible();
        var workspace = employment.GetWorkspace(tenantId, relationshipId);
        return Ok(
            new
            {
                // What the customer's decision commands must quote back to be accepted.
                commandContext = workspace is null
                    ? null
                    : new
                    {
                        workspaceVersion = workspace.WorkspaceVersion,
                        manifestVersion = workspace.ManifestVersion,
                        decisionSpaceVersion = workspace.DecisionSpaceVersion,
                    },
                items = artifacts
                    .List(tenantId, relationshipId, artifactType)
                    .Select(item => new
                    {
                        artifact = item,
                        decisions = decisions.Check(
                            tenantId,
                            relationshipId,
                            item.ArtifactId,
                            item.Digest
                        ),
                    }),
            }
        );
    }

    [HttpGet("artifacts/{artifactId:guid}")]
    public async Task<IActionResult> GetArtifactAsync(
        Guid relationshipId,
        Guid artifactId,
        CancellationToken cancellationToken
    )
    {
        if (await TenantAsync(relationshipId, cancellationToken) is not { } tenantId)
            return NotAccessible();
        var artifact = artifacts.Get(tenantId, relationshipId, artifactId);
        return artifact is null
            ? NotAccessible()
            : Ok(
                new
                {
                    artifact,
                    decisions = decisions.Check(
                        tenantId,
                        relationshipId,
                        artifactId,
                        artifact.Digest
                    ),
                }
            );
    }

    [HttpGet("timeline")]
    public async Task<IActionResult> GetTimelineAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    ) =>
        await TenantAsync(relationshipId, cancellationToken) is { } tenantId
            ? Ok(timeline.Read(tenantId, relationshipId))
            : NotAccessible();

    [HttpGet("outcomes")]
    public async Task<IActionResult> GetOutcomesAsync(
        Guid relationshipId,
        CancellationToken cancellationToken
    ) =>
        await TenantAsync(relationshipId, cancellationToken) is { } tenantId
            ? Ok(outcomes.Read(tenantId, relationshipId))
            : NotAccessible();

    [HttpGet("outcomes/{claimId}")]
    public async Task<IActionResult> GetOutcomeTraceAsync(
        Guid relationshipId,
        string claimId,
        CancellationToken cancellationToken
    )
    {
        if (await TenantAsync(relationshipId, cancellationToken) is not { } tenantId)
            return NotAccessible();
        var trace = outcomes.Trace(tenantId, relationshipId, claimId);
        return trace is null ? NotAccessible() : Ok(trace);
    }

    private async Task<Guid?> TenantAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        Response.Headers.CacheControl = "no-store";
        if (!gate.Snapshot().Enabled)
            return null;
        if (
            !HttpContext.Items.TryGetValue(
                TenantIsolationMiddleware.TenantIdItemKey,
                out var tenant
            )
            || tenant is not string tenantText
            || !Guid.TryParse(tenantText, out var tenantId)
        )
            return null;
        var actor =
            User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        return
            Guid.TryParse(actor, out var actorId)
            && await relationships.IsActiveParticipantAsync(
                tenantId,
                relationshipId,
                actorId,
                cancellationToken
            )
            ? tenantId
            : null;
    }

    private ObjectResult NotAccessible() =>
        StatusCode(404, new { code = "EMPLOYMENT_NOT_ACCESSIBLE" });
}
