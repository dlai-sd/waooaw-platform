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
public sealed record RelationshipOnboardRequest(
    string SchemaVersion,
    string? PreferredAgentDisplayName,
    string? ChatAppearance,
    string? TimestampVisibility,
    string? ThemePreference);

[ApiController]
[Authorize]
[Route("api/v1/employment/relationships/{relationshipId:guid}/workspace")]
public sealed class RelationshipWorkspaceController(
    EmploymentRelationshipService relationships,
    IRelationshipWorkspaceOwnerGateway owners,
    RelationshipEvidenceService? evidence = null,
    RelationshipConfigurationService? configuration = null) : ControllerBase
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

    [HttpGet("configuration")]
    public async Task<IActionResult> GetConfigurationAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        if (configuration is null) return WorkspaceProblem(503, "RELATIONSHIP_WORKSPACE_DEPENDENCY_UNAVAILABLE");
        var state = await configuration.GetPortalConfigurationAsync(
            relationship.TenantId, relationshipId, cancellationToken);
        return Ok(ConfigurationResponse(relationship, state));
    }

    [HttpPut("configuration/onboard")]
    public async Task<IActionResult> UpdateOnboardAsync(
        Guid relationshipId,
        [FromBody] RelationshipOnboardRequest request,
        [FromHeader(Name = "Idempotency-Key")] string? idempotencyKey,
        CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        if (configuration is null) return WorkspaceProblem(503, "RELATIONSHIP_WORKSPACE_DEPENDENCY_UNAVAILABLE");
        if (request.SchemaVersion != "1.0.0" || !Guid.TryParse(idempotencyKey, out var parsedKey)
            || request.PreferredAgentDisplayName is { Length: > 80 }
            || request.ChatAppearance is not (null or "CONSTITUTIONAL" or "COMPACT")
            || request.TimestampVisibility is not (null or "RELATIVE" or "ABSOLUTE")
            || request.ThemePreference is not (null or "SYSTEM" or "LIGHT" or "DARK"))
            return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID");
        var requestHash = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(request))));
        try
        {
            var state = await configuration.UpdateOnboardAsync(
                relationship.TenantId, relationshipId, parsedKey, requestHash,
                request.PreferredAgentDisplayName?.Trim(), request.ChatAppearance,
                request.TimestampVisibility, request.ThemePreference, cancellationToken);
            return Ok(ConfigurationResponse(relationship, state));
        }
        catch (RelationshipConfigurationConflictException)
        {
            return WorkspaceProblem(409, "RELATIONSHIP_IDEMPOTENCY_CONFLICT");
        }
        catch (ConstitutionalActionDeniedException)
        {
            return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED");
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            return WorkspaceProblem(503, "CONSTITUTIONAL_ENGINE_UNAVAILABLE");
        }
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

    [HttpGet("goals")]
    public async Task<IActionResult> GetGoalsAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        if (configuration is null) return WorkspaceProblem(503, "RELATIONSHIP_WORKSPACE_DEPENDENCY_UNAVAILABLE");
        var goals = await configuration.GetPortalGoalsAsync(relationship.TenantId, relationshipId, cancellationToken);
        var activeGoals = goals.Where(item => NormalizeGoalStatus(item.Goal.Status) == "ACTIVE")
            .Select(GoalResponse).ToArray();
        var history = goals.Where(item => NormalizeGoalStatus(item.Goal.Status) != "ACTIVE")
            .Select(item => new
            {
                goalId = item.Goal.GoalId,
                goalVersion = RelationshipConfigurationService.GetGoalVersion(item.Goal),
                skillId = item.SkillId,
                skillLabel = item.SkillLabel,
                measure = item.Goal.Measure,
                frequency = $"EVERY_{item.Goal.ReviewCadenceMonths}_MONTHS",
                baseline = item.Goal.Baseline,
                attributionBoundary = item.Goal.DecisionThreshold,
                verificationStatus = "PENDING_CUSTOMER",
                status = NormalizeGoalStatus(item.Goal.Status),
                evidenceState = "PENDING",
                changedAt = item.Goal.UpdatedAt,
                changeReason = "Goal state changed in the relationship configuration.",
            }).ToArray();
        return Ok(new
        {
            sectionType = "GOALS",
            currencyState = "CURRENT",
            provenance = Provenance("BP", $"relationship-{relationship.StateVersion}", DateTimeOffset.UtcNow),
            availableCommands = Array.Empty<object>(),
            activeGoals,
            history,
        });
    }

    [HttpGet("business-outcomes")]
    public async Task<IActionResult> GetBusinessOutcomesAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        return Ok(new
        {
            sectionType = "BUSINESS_OUTCOMES",
            currencyState = "UNAVAILABLE",
            provenance = Provenance("BP", $"relationship-{relationship.StateVersion}", DateTimeOffset.UtcNow),
            availableCommands = Array.Empty<object>(),
            items = Array.Empty<object>(),
        });
    }

    [HttpGet("operations")]
    public async Task<IActionResult> GetOperationsAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        if (configuration is null) return WorkspaceProblem(503, "RELATIONSHIP_WORKSPACE_DEPENDENCY_UNAVAILABLE");
        var goals = await configuration.GetPortalGoalsAsync(relationship.TenantId, relationshipId, cancellationToken);
        var requiredGoalIds = goals.Where(item => NormalizeGoalStatus(item.Goal.Status) == "ACTIVE")
            .Select(item => item.Goal.GoalId).ToArray();
        var activeGoals = goals.Where(item => NormalizeGoalStatus(item.Goal.Status) == "ACTIVE").ToArray();
        var verifiedGoalIds = activeGoals.Where(item => item.CurrentDecision?.Decision == "VERIFIED")
            .Select(item => item.Goal.GoalId).ToArray();
        var eligible = requiredGoalIds.Length > 0 && verifiedGoalIds.Length == requiredGoalIds.Length;
        var blockedReasons = eligible ? Array.Empty<string>() : requiredGoalIds.Length == 0
            ? new[] { "At least one active goal must be customer-verified before Operations is available." }
            : new[] { "Customer verification is required for every active goal before Operations is available." };
        return Ok(new
        {
            sectionType = "OPERATIONS",
            currencyState = "CURRENT",
            provenance = Provenance("BP", $"relationship-{relationship.StateVersion}", DateTimeOffset.UtcNow),
            availableCommands = Array.Empty<object>(),
            eligibilityState = eligible ? "ELIGIBLE" : "LOCKED",
            requiredGoalIds,
            verifiedGoalIds,
            blockedReasons,
            reassessmentRequired = activeGoals.Any(item => item.HasPriorDecision && item.CurrentDecision is null),
            dependentOutcomeIds = Array.Empty<Guid>(),
        });
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
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null) return NotFoundProblem();
        if (!Guid.TryParse(idempotencyKey, out var parsedKey))
            return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID");
        if (command.ValueKind == JsonValueKind.Object
            && command.TryGetProperty("type", out _)
            && !command.TryGetProperty("payload", out _))
            return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED");
        if (command.ValueKind != JsonValueKind.Object
            || !command.TryGetProperty("payload", out var payload)
            || payload.ValueKind != JsonValueKind.Object
            || !TryGetString(payload, "commandKind", out var commandKind))
            return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID");
        if (commandKind is "SELECT_SKILL" or "UPDATE_SKILL" or "ACCEPT_SKILL" or "DEFER_SKILL")
            return await SubmitSkillCommandAsync(
                relationship, command, payload, commandKind, parsedKey, cancellationToken);
        if (commandKind != "VERIFY_GOAL") return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED");
        if (configuration is null) return WorkspaceProblem(503, "RELATIONSHIP_WORKSPACE_DEPENDENCY_UNAVAILABLE");
        if (!TryGetString(command, "schemaVersion", out var schemaVersion) || schemaVersion != "1.0"
            || !TryGetString(command, "expectedWorkspaceVersion", out var expectedWorkspaceVersion)
            || !TryGetString(command, "expectedSubjectVersion", out var expectedSubjectVersion)
            || !TryGetGuid(payload, "goalId", out var goalId)
            || !TryGetString(payload, "goalVersion", out var goalVersion)
            || !TryGetString(payload, "verificationDecision", out var verificationDecision)
            || !TryGetOptionalString(payload, "correctionReason", out var correctionReason)
            || verificationDecision is not ("VERIFIED" or "CHANGES_REQUESTED")
            || correctionReason is { Length: > 500 }
            || (verificationDecision == "VERIFIED" && correctionReason is not null)
            || (verificationDecision == "CHANGES_REQUESTED" && string.IsNullOrWhiteSpace(correctionReason)))
            return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID");
        if (!TryGetParticipantId(out var actorParticipantId)) return NotFoundProblem();
        var actorRole = await relationships.GetActiveRoleAsync(
            relationship.TenantId, relationshipId, actorParticipantId, cancellationToken);
        if (actorRole is not (RelationshipParticipantRole.Evaluator or RelationshipParticipantRole.Employer))
            return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED");
        if (!HasFreshAal3()) return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_ASSURANCE_REQUIRED");

        var materialRequestHash = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new
            {
                schemaVersion,
                expectedWorkspaceVersion,
                expectedSubjectVersion,
                commandKind,
                goalId,
                goalVersion,
                verificationDecision,
                correctionReason = correctionReason?.Trim(),
            }))));
        try
        {
            var result = await configuration.VerifyGoalAsync(
                relationship.TenantId,
                relationshipId,
                actorParticipantId,
                parsedKey,
                materialRequestHash,
                expectedWorkspaceVersion,
                expectedSubjectVersion,
                goalId,
                goalVersion,
                verificationDecision,
                correctionReason,
                Guid.TryParse(User.FindFirstValue("correlation_id"), out var correlationId)
                    ? correlationId : Guid.NewGuid(),
                cancellationToken);
            var receipt = new
            {
                schemaVersion = "1.0",
                commandId = result.Decision.DecisionId,
                commandKind = "VERIFY_GOAL",
                status = "COMPLETED",
                acceptedAt = result.Decision.OccurredAt,
                replayed = result.Replayed,
            };
            return result.Replayed ? Ok(receipt) : StatusCode(202, receipt);
        }
        catch (ArgumentException) { return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID"); }
        catch (KeyNotFoundException) { return NotFoundProblem(); }
        catch (RelationshipConfigurationConflictException)
        {
            return WorkspaceProblem(409, "RELATIONSHIP_IDEMPOTENCY_CONFLICT");
        }
        catch (RelationshipGoalVersionConflictException)
        {
            return WorkspaceProblem(409, "RELATIONSHIP_STATE_CONFLICT");
        }
        catch (ConstitutionalActionDeniedException)
        {
            return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED");
        }
    }

    private async Task<IActionResult> SubmitSkillCommandAsync(
        EmploymentRelationship relationship, JsonElement command, JsonElement payload,
        string commandKind, Guid idempotencyKey, CancellationToken cancellationToken)
    {
        if (configuration is null) return WorkspaceProblem(503, "RELATIONSHIP_WORKSPACE_DEPENDENCY_UNAVAILABLE");
        if (!TryGetString(command, "schemaVersion", out var schemaVersion) || schemaVersion != "1.0"
            || !TryGetString(command, "expectedWorkspaceVersion", out var expectedWorkspaceVersion)
            || !TryGetString(command, "expectedSubjectVersion", out var expectedSubjectVersion)
            || !TryGetGuid(payload, "configurationId", out var configurationId)
            || !TryGetString(payload, "skillId", out var skillId)
            || !TryGetString(payload, "skillVersion", out var skillVersion))
            return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID");
        if (!TryGetParticipantId(out var actorParticipantId)) return NotFoundProblem();
        var actorRole = await relationships.GetActiveRoleAsync(
            relationship.TenantId, relationship.RelationshipId, actorParticipantId, cancellationToken);
        if (actorRole is not (RelationshipParticipantRole.Evaluator or RelationshipParticipantRole.Employer))
            return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED");
        if (!HasFreshAal3()) return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_ASSURANCE_REQUIRED");
        var requestHash = Convert.ToHexStringLower(System.Security.Cryptography.SHA256.HashData(
            System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new
            {
                schemaVersion, expectedWorkspaceVersion, expectedSubjectVersion, commandKind,
                configurationId, skillId, skillVersion,
            }))));
        try
        {
            var result = await configuration.DecideSkillAsync(
                relationship.TenantId, relationship.RelationshipId, actorParticipantId, idempotencyKey,
                requestHash, expectedWorkspaceVersion, expectedSubjectVersion, configurationId,
                skillId, skillVersion, commandKind,
                Guid.TryParse(User.FindFirstValue("correlation_id"), out var correlationId)
                    ? correlationId : Guid.NewGuid(), cancellationToken);
            var receipt = new { schemaVersion = "1.0", commandId = result.Decision.DecisionId,
                commandKind, status = "COMPLETED", acceptedAt = result.Decision.OccurredAt,
                replayed = result.Replayed };
            return result.Replayed ? Ok(receipt) : StatusCode(202, receipt);
        }
        catch (ArgumentException) { return WorkspaceProblem(400, "RELATIONSHIP_WORKSPACE_REQUEST_INVALID"); }
        catch (KeyNotFoundException) { return NotFoundProblem(); }
        catch (RelationshipConfigurationConflictException) { return WorkspaceProblem(409, "RELATIONSHIP_IDEMPOTENCY_CONFLICT"); }
        catch (RelationshipSkillVersionConflictException) { return WorkspaceProblem(409, "RELATIONSHIP_STATE_CONFLICT"); }
        catch (ConstitutionalActionDeniedException) { return WorkspaceProblem(423, "RELATIONSHIP_WORKSPACE_BLOCKED"); }
    }

    [HttpGet("commands/{commandId:guid}")]
    public async Task<IActionResult> GetCommandAsync(Guid relationshipId, Guid commandId, CancellationToken cancellationToken)
    {
        var relationship = await GetAuthorizedRelationshipAsync(relationshipId, cancellationToken);
        if (relationship is null || configuration is null) return NotFoundProblem();
        var skillDecision = await configuration.GetSkillDecisionAsync(
            relationship.TenantId, relationshipId, commandId, cancellationToken);
        if (skillDecision is not null) return Ok(new
        {
            schemaVersion = "1.0", commandId = skillDecision.DecisionId,
            commandKind = skillDecision.Decision, status = "COMPLETED", relationshipId,
            steps = new[] { new { owner = "BP", status = "COMPLETED" } },
            resolvedAt = skillDecision.OccurredAt,
        });
        var decision = await configuration.GetGoalDecisionAsync(
            relationship.TenantId, relationshipId, commandId, cancellationToken);
        return decision is null ? NotFoundProblem() : Ok(new
        {
            schemaVersion = "1.0",
            commandId = decision.DecisionId,
            commandKind = "VERIFY_GOAL",
            status = "COMPLETED",
            relationshipId,
            steps = new[] { new { owner = "BP", status = "COMPLETED" } },
            resolvedAt = decision.OccurredAt,
        });
    }

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
        var participant = User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        if (!Guid.TryParse(participant, out var participantId)
            || !await relationships.IsActiveParticipantAsync(tenantId, relationshipId, participantId, cancellationToken))
            return null;
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
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        return HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && value is string tenant
            && Guid.TryParse(tenant, out tenantId)
            && Guid.TryParse(participant, out participantId);
    }

    private bool TryGetParticipantId(out Guid participantId)
    {
        var participant = User.FindFirstValue("participant_id")
            ?? User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub");
        return Guid.TryParse(participant, out participantId);
    }

    private bool HasFreshAal3()
    {
        if (!string.Equals(User.FindFirstValue("authentication_assurance"), "AAL3_FRESH", StringComparison.Ordinal)
            || !long.TryParse(User.FindFirstValue("auth_time"), out var unixTime)) return false;
        var age = DateTimeOffset.UtcNow - DateTimeOffset.FromUnixTimeSeconds(unixTime);
        return age >= TimeSpan.FromSeconds(-30) && age <= TimeSpan.FromMinutes(5);
    }

    private static bool TryGetString(JsonElement value, string propertyName, out string result)
    {
        result = string.Empty;
        return value.TryGetProperty(propertyName, out var property)
            && property.ValueKind == JsonValueKind.String
            && !string.IsNullOrWhiteSpace(result = property.GetString()!);
    }

    private static bool TryGetOptionalString(JsonElement value, string propertyName, out string? result)
    {
        result = null;
        if (!value.TryGetProperty(propertyName, out var property)) return true;
        if (property.ValueKind != JsonValueKind.String) return false;
        result = property.GetString();
        return true;
    }

    private static bool TryGetGuid(JsonElement value, string propertyName, out Guid result)
    {
        result = default;
        return value.TryGetProperty(propertyName, out var property)
            && property.ValueKind == JsonValueKind.String
            && Guid.TryParse(property.GetString(), out result);
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

    private static object ConfigurationResponse(
        EmploymentRelationship relationship,
        RelationshipConfigurationState state)
    {
        var onboardState = state.Onboard is null ? "NOT_STARTED" : "VERIFIED";
        var inductState = state.InductComplete ? "VERIFIED"
            : state.ConfirmedContextCount > 0 ? "IN_PROGRESS" : "NOT_STARTED";
        var lifecyclePhase = state.InductComplete ? "GOAL_VERIFICATION"
            : state.Onboard is null ? "ONBOARD" : "INDUCT";
        return new
        {
            sectionType = "CONFIGURATION",
            currencyState = "CURRENT",
            provenance = Provenance("BP", $"relationship-{relationship.StateVersion}", state.ProducedAt),
            availableCommands = Array.Empty<object>(),
            lifecyclePhase,
            items = new object[]
            {
                new { stepKey = "ONBOARD", label = "Onboard", state = onboardState,
                    summary = state.Onboard is null ? "Choose relationship presentation preferences." : "Presentation preferences saved.",
                    continuationTarget = new { surface = "CONFIGURATION", relationshipId = relationship.RelationshipId } },
                new { stepKey = "INDUCT", label = "Induct", state = inductState,
                    summary = state.InductComplete ? "Required business context confirmed." : "Continue the consultative induction conversation.",
                    confirmedContextVersion = state.ConfirmedContextCount > 0 ? $"context-{state.ConfirmedContextCount}" : null,
                    continuationTarget = new { surface = "CONVERSATION", relationshipId = relationship.RelationshipId } },
            },
        };
    }

    private static object GoalResponse(RelationshipPortalGoal item) => new
    {
        goalId = item.Goal.GoalId,
        goalVersion = RelationshipConfigurationService.GetGoalVersion(item.Goal),
        skillId = item.SkillId,
        skillLabel = item.SkillLabel,
        measure = item.Goal.Measure,
        frequency = $"EVERY_{item.Goal.ReviewCadenceMonths}_MONTHS",
        baseline = item.Goal.Baseline,
        attributionBoundary = item.Goal.DecisionThreshold,
        verificationStatus = item.CurrentDecision?.Decision ?? "PENDING_CUSTOMER",
        customerVerifiedAt = item.CurrentDecision?.Decision == "VERIFIED"
            ? item.CurrentDecision.OccurredAt : (DateTimeOffset?)null,
        status = NormalizeGoalStatus(item.Goal.Status),
        evidenceState = item.CurrentDecision is null ? "PENDING" : "RECORDED",
    };

    private static string NormalizeGoalStatus(string status) => status.ToUpperInvariant() switch
    {
        "SUPERSEDED" => "SUPERSEDED",
        "RETIRED" => "RETIRED",
        "BLOCKED" => "BLOCKED",
        _ => "ACTIVE",
    };
}