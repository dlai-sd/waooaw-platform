// Implements: business-platform.openapi.yaml 1.3.0 Relationship Workspace
// constitutional_basis: C-001, C-005, C-023, C-026, C-059, C-063, C-083, C-084, C-085

using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record RequestRelationshipEvidenceExport(string SchemaVersion, string Purpose);

[ApiController]
[Authorize]
[Route("api/v1/employment/relationships/{relationshipId:guid}/workspace")]
public sealed class RelationshipWorkspaceController(
    EmploymentRelationshipService relationships,
    IRelationshipWorkspaceOwnerGateway owners,
    RelationshipEvidenceService? evidence = null) : ControllerBase
{
    private static readonly string[] SectionTypes =
        ["PLAN", "ATTENTION", "WORK", "RESULTS", "USAGE_BUDGET", "RIGHTS_CONTROLS"];

    [HttpGet]
    public async Task<IActionResult> GetWorkspaceAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        var now = DateTimeOffset.UtcNow;
        var version = $"relationship-{relationship.StateVersion}";
        var ownerContext = OwnerContext(relationship);
        var executionTask = owners.GetExecutionAsync(ownerContext, cancellationToken);
        var commercialTask = owners.GetCommercialAsync(ownerContext, cancellationToken);
        await Task.WhenAll(executionTask, commercialTask);
        var execution = await executionTask;
        var commercial = await commercialTask;
        var sections = SectionTypes.Select(type => Section(type,
            type switch
            {
                "ATTENTION" or "RIGHTS_CONTROLS" => "CURRENT",
                "WORK" => execution?.State ?? "UNAVAILABLE",
                "USAGE_BUDGET" => commercial?.CurrencyState ?? "UNAVAILABLE",
                _ => "UNAVAILABLE",
            },
            type == "WORK" ? execution?.ProjectionVersion ?? version
                : type == "USAGE_BUDGET" ? commercial?.ProjectionVersion ?? version
                : version,
            type == "WORK" ? execution?.ProducedAt ?? now
                : type == "USAGE_BUDGET" ? commercial?.ProducedAt ?? now
                : now));
        return Ok(new
        {
            schemaVersion = "1.0", relationshipId, workspaceVersion = version,
            snapshotState = "PARTIAL", currencyState = "CURRENT",
            authoritativeCursor = Cursor(relationshipId, relationship.StateVersion), producedAt = now,
            context = new
            {
                relationshipId,
                lifecycleState = RelationshipStateCodec.ToDatabase(relationship.State),
                policySelection = new { f4Pol01 = "A", f4Pol02 = "A", f4Pol03 = "B", f4Pol04 = "A", f4Pol05 = "B", f4Pol06 = "A" },
            },
            sections,
        });
    }

    [HttpGet("changes")]
    public async Task<IActionResult> GetChangesAsync(Guid relationshipId, [FromQuery] string? afterCursor,
        CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        return Ok(new { schemaVersion = "1.0", relationshipId,
            authoritativeCursor = Cursor(relationshipId, relationship.StateVersion), items = Array.Empty<object>() });
    }

    [HttpGet("plan")]
    public async Task<IActionResult> GetPlanAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        var now = DateTimeOffset.UtcNow;
        return Ok(new { sectionType = "PLAN", currencyState = "UNAVAILABLE",
            provenance = Provenance("BP", $"relationship-{relationship.StateVersion}", now),
            availableCommands = Array.Empty<object>(), planId = relationshipId, goals = Array.Empty<string>() });
    }

    [HttpGet("attention")]
    public async Task<IActionResult> GetAttentionAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        return Ok(new { sectionType = "ATTENTION", currencyState = "CURRENT",
            provenance = Provenance("BP", $"relationship-{relationship.StateVersion}", DateTimeOffset.UtcNow),
            availableCommands = Array.Empty<object>(), items = Array.Empty<object>() });
    }

    [HttpGet("work")]
    public async Task<IActionResult> GetWorkAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        var projection = await owners.GetExecutionAsync(OwnerContext(relationship), cancellationToken);
        return Ok(new
        {
            sectionType = "WORK",
            currencyState = projection?.State ?? "UNAVAILABLE",
            provenance = Provenance("PR", projection?.ProjectionVersion ?? "unavailable-1",
                projection?.ProducedAt ?? DateTimeOffset.UtcNow),
            availableCommands = Array.Empty<object>(),
            items = Array.Empty<object>(),
        });
    }

    [HttpGet("results")]
    public Task<IActionResult> GetResultsAsync(Guid relationshipId, CancellationToken cancellationToken) =>
        UnavailableSectionAsync(relationshipId, "RESULTS", "outcomes", cancellationToken);

    [HttpGet("usage-budget")]
    public async Task<IActionResult> GetUsageBudgetAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        var projection = await owners.GetCommercialAsync(OwnerContext(relationship), cancellationToken);
        return Ok(new { sectionType = "USAGE_BUDGET", currencyState = projection?.CurrencyState ?? "UNAVAILABLE",
            provenance = Provenance("WBE", projection?.ProjectionVersion ?? "unavailable-1",
                projection?.ProducedAt ?? DateTimeOffset.UtcNow),
            availableCommands = Array.Empty<object>(), actualAmount = projection?.Actuals ?? "Unavailable",
            forecastRange = projection?.Forecast ?? "Unavailable",
            thresholdState = projection?.Thresholds ?? "UNAVAILABLE",
            wbeProjectionVersion = projection?.ProjectionVersion ?? "unavailable-1" });
    }

    [HttpGet("rights-controls")]
    public async Task<IActionResult> GetRightsControlsAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        var version = relationship.StateVersion.ToString(System.Globalization.CultureInfo.InvariantCulture);
        return Ok(new { sectionType = "RIGHTS_CONTROLS", currencyState = "CURRENT",
            provenance = Provenance("BP", $"relationship-{version}", DateTimeOffset.UtcNow),
            availableCommands = Array.Empty<object>(), scopeVersion = version, authorityVersion = version,
            lifecycleState = RelationshipStateCodec.ToDatabase(relationship.State), emergencyStopReachable = true });
    }

    [HttpPost("commands")]
    public async Task<IActionResult> SubmitCommandAsync(Guid relationshipId, [FromBody] JsonElement command,
        [FromHeader(Name = "Idempotency-Key")] string? idempotencyKey, CancellationToken cancellationToken)
    {
        if (await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken) is null) return NotFoundProblem();
        if (string.IsNullOrWhiteSpace(idempotencyKey)) return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID");
        return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED");
    }

    [HttpGet("commands/{commandId:guid}")]
    public async Task<IActionResult> GetCommandAsync(Guid relationshipId, Guid commandId, CancellationToken cancellationToken) =>
        await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken) is null
            ? NotFoundProblem() : WorkspaceProblem(404, "RELATIONSHIP_WORKSPACE_NOT_ACCESSIBLE");

    [HttpGet("evidence")]
    public async Task<IActionResult> ListEvidenceAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        if (evidence is null || !TryGetEvidenceContext(out var tenantId, out var participantId)) return NotFoundProblem();
        try
        {
            var items = await evidence.ListAsync(tenantId, relationshipId, participantId, cancellationToken);
            return Ok(new
            {
                schemaVersion = "1.0",
                relationshipId,
                items = items.Select(value => new { evidenceId = value.EvidenceId, subject = value.Subject, state = value.State }),
            });
        }
        catch (KeyNotFoundException) { return NotFoundProblem(); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return WorkspaceProblem(503, "CONSTITUTIONAL_ENGINE_UNAVAILABLE");
        }
    }

    [HttpGet("evidence/{evidenceId:guid}")]
    public async Task<IActionResult> GetEvidenceAsync(Guid relationshipId, Guid evidenceId, CancellationToken cancellationToken)
    {
        if (evidence is null || !TryGetEvidenceContext(out var tenantId, out var participantId)) return NotFoundProblem();
        try
        {
            var item = await evidence.GetAsync(
                tenantId, relationshipId, participantId, evidenceId, cancellationToken);
            return item is null ? NotFoundProblem() : Ok(new
            {
                schemaVersion = "1.0",
                evidenceId = item.EvidenceId,
                subject = item.Subject,
                state = item.State,
                completeness = "CONSTITUTIONAL_PROOF_RETAINED",
                payloadState = item.PayloadState,
                payloadReference = item.PayloadReference,
                erasedAt = item.ErasedAt,
            });
        }
        catch (KeyNotFoundException) { return NotFoundProblem(); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return WorkspaceProblem(503, "CONSTITUTIONAL_ENGINE_UNAVAILABLE");
        }
    }

    [HttpPost("evidence-exports")]
    public async Task<IActionResult> RequestEvidenceExportAsync(Guid relationshipId, [FromBody] RequestRelationshipEvidenceExport request,
        [FromHeader(Name = "Idempotency-Key")] string? idempotencyKey, CancellationToken cancellationToken)
    {
        if (evidence is null || !TryGetEvidenceContext(out var tenantId, out var participantId)) return NotFoundProblem();
        if (request.SchemaVersion != "1.0" || !Guid.TryParse(idempotencyKey, out var parsedIdempotencyKey))
            return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID");
        try
        {
            var result = await evidence.CreateExportAsync(
                tenantId, relationshipId, participantId, parsedIdempotencyKey, request.Purpose, cancellationToken);
            var response = new { schemaVersion = "1.0", exportId = result.ExportId, status = result.Status, acceptedAt = result.AcceptedAt };
            return result.Replayed ? Ok(response) : StatusCode(202, response);
        }
        catch (KeyNotFoundException) { return NotFoundProblem(); }
        catch (ArgumentException) { return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID"); }
        catch (ChannelContinuityConflictException) { return WorkspaceProblem(409, "RELATIONSHIP_IDEMPOTENCY_CONFLICT"); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return WorkspaceProblem(503, "CONSTITUTIONAL_ENGINE_UNAVAILABLE");
        }
    }

    [HttpGet("evidence-exports/{exportId:guid}")]
    public async Task<IActionResult> GetEvidenceExportAsync(Guid relationshipId, Guid exportId, CancellationToken cancellationToken)
    {
        if (evidence is null || !TryGetEvidenceContext(out var tenantId, out var participantId)) return NotFoundProblem();
        try
        {
            var result = await evidence.GetExportAsync(
                tenantId, relationshipId, participantId, exportId, cancellationToken);
            if (result is null) return NotFoundProblem();
            return Ok(new
            {
                schemaVersion = "1.0",
                exportId = result.ExportId,
                status = result.Status,
                downloadAvailableUntil = result.ExpiresAt,
                downloadUrl = result.DownloadUrl,
                mediaType = "application/vnd.waooaw.relationship-evidence+json;version=1.0",
                documentSha256 = result.DocumentSha256,
                document = JsonSerializer.Deserialize<JsonElement>(result.DocumentJson),
            });
        }
        catch (KeyNotFoundException) { return NotFoundProblem(); }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return WorkspaceProblem(503, "CONSTITUTIONAL_ENGINE_UNAVAILABLE");
        }
    }

    private async Task<IActionResult> UnavailableSectionAsync(Guid relationshipId, string sectionType,
        string itemsProperty, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        var common = new Dictionary<string, object?>
        {
            ["sectionType"] = sectionType, ["currencyState"] = "UNAVAILABLE",
            ["provenance"] = Provenance(sectionType == "WORK" ? "PR" : "DMA", "unavailable-1", DateTimeOffset.UtcNow),
            ["availableCommands"] = Array.Empty<object>(), [itemsProperty] = Array.Empty<object>(),
        };
        return Ok(common);
    }

    private async Task<EmploymentRelationship?> GetAuthorizedRelationshipAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        if (!HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            || value is not string text || !Guid.TryParse(text, out var tenantId)) return null;
        return await relationships.GetAsync(tenantId, relationshipId, cancellationToken);
    }

    private RelationshipOwnerContext OwnerContext(EmploymentRelationship relationship)
    {
        var actorSubject = User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")
            ?? "unknown";
        var effectiveRole = User.FindFirstValue("participant_role") ?? "EMPLOYER";
        var correlationId = User.FindFirstValue("correlation_id") ?? HttpContext.TraceIdentifier;
        return new RelationshipOwnerContext(
            actorSubject,
            effectiveRole,
            relationship.TenantId,
            relationship.RelationshipId,
            relationship.StateVersion,
            correlationId);
    }

    private bool TryGetEvidenceContext(out Guid tenantId, out Guid participantId)
    {
        tenantId = default;
        participantId = default;
        var participant = User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier);
        return HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && value is string tenant
            && Guid.TryParse(tenant, out tenantId)
            && Guid.TryParse(participant, out participantId);
    }

    private IActionResult NotFoundProblem() => WorkspaceProblem(404, "RELATIONSHIP_WORKSPACE_NOT_ACCESSIBLE");

    private ObjectResult WorkspaceProblem(int status, string code) => StatusCode(status, new
    {
        type = $"https://waooaw.com/problems/{code.ToLowerInvariant().Replace('_', '-')}",
        title = "The relationship workspace request could not be completed", status, code,
        correlationId = User.FindFirstValue("correlation_id") ?? Guid.NewGuid().ToString(),
    });

    private static object Section(string type, string state, string version, DateTimeOffset now) =>
        new { sectionType = type, currencyState = state,
            provenance = Provenance(type is "USAGE_BUDGET" ? "WBE" : type is "WORK" ? "PR" : type is "RESULTS" ? "DMA" : "BP", version, now),
            availableCommands = Array.Empty<object>() };

    private static object Provenance(string owner, string version, DateTimeOffset producedAt) =>
        new { owner, sourceProjectionVersion = version, producedAt };

    private static string Cursor(Guid relationshipId, int version) => $"workspace:{relationshipId:N}:{version:D8}";
}