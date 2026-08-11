// Implements: work-contracts/WC-058-goal005-ae01-discover-trial-configure.md §WC058-06 S03-S06
// constitutional_basis: C-023, C-026, C-049, C-059, C-063

using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Controllers;

public sealed record EvaluationContextItem(Guid PayloadReference, string FieldType, JsonElement Value, string Status);
public sealed record EvaluationGoalItem(Guid GoalId, string Goal, string Measure, string Status, int ReviewCadenceMonths);
public sealed record EvaluationSkillItem(Guid ConfigurationId, string SkillId, string Applicability, string? ApplicabilityReason, string AuthorityState, string Status);
public sealed record EvaluationDecisionSpace(int Version, long BudgetCeilingInrPaise, JsonElement AuthorityBoundaries, JsonElement StopConditions, int ReviewCadenceMonths);
public sealed record EvaluationTrial(Guid TrialId, DateTimeOffset StartsAt, DateTimeOffset ExpiresAt, string Status);
public sealed record RelationshipEvaluationProjection(
    Guid RelationshipId,
    string LifecycleState,
    string InterviewState,
    IReadOnlyList<EvaluationContextItem> Context,
    string? NextContextQuestion,
    EvaluationTrial? Trial,
    IReadOnlyList<EvaluationGoalItem> Goals,
    IReadOnlyList<EvaluationSkillItem> Skills,
    EvaluationDecisionSpace? DecisionSpace);

[ApiController]
[Authorize]
[Route("api/v1/employment/relationships/{relationshipId:guid}/evaluation")]
public sealed class RelationshipEvaluationController(
    IDbContextFactory<EmploymentRelationshipDbContext> dbFactory) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetAsync(Guid relationshipId, CancellationToken cancellationToken)
    {
        if (!TryGetTenantId(out var tenantId)) return Forbid();
        await using var db = await dbFactory.CreateDbContextAsync(cancellationToken);
        var relationship = await db.EmploymentRelationships.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken);
        if (relationship is null) return NotFound();

        var contextRows = await db.RelationshipContextPayloads.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId
                && item.InvalidatedAt == null && item.ErasedAt == null && item.ValueJson != null)
            .OrderBy(item => item.CreatedAt)
            .ToListAsync(cancellationToken);
        var context = contextRows.Select(item => new EvaluationContextItem(
            item.PayloadReference, item.FieldType, Parse(item.ValueJson!), item.ConfirmationStatus)).ToList();
        var fields = context.Select(item => item.FieldType).ToHashSet(StringComparer.Ordinal);
        var nextQuestion = !fields.Contains("NAME") ? "What name should this professional use for your business?"
            : !fields.Contains("LOCATION") ? "Where does your business serve customers?"
            : !fields.Contains("BUSINESS_NATURE") ? "What does your business provide?"
            : null;

        var trialRow = await db.RelationshipTrialBindings.AsNoTracking().SingleOrDefaultAsync(
            item => item.TenantId == tenantId && item.RelationshipId == relationshipId,
            cancellationToken);
        var trial = trialRow is { TrialId: not null, StartsAt: not null, ExpiresAt: not null }
            ? new EvaluationTrial(trialRow.TrialId.Value, trialRow.StartsAt.Value, trialRow.ExpiresAt.Value, trialRow.Status)
            : null;
        var goals = await db.RelationshipGoals.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderBy(item => item.CreatedAt)
            .Select(item => new EvaluationGoalItem(item.GoalId, item.Goal, item.Measure, item.Status, item.ReviewCadenceMonths))
            .ToListAsync(cancellationToken);
        var skills = await db.RelationshipSkillConfigurations.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderBy(item => item.CreatedAt)
            .Select(item => new EvaluationSkillItem(item.ConfigurationId, item.SkillId, item.Applicability, item.ApplicabilityReason, item.AuthorityState, item.Status))
            .ToListAsync(cancellationToken);
        var decisionRow = await db.DecisionSpaceSnapshots.AsNoTracking()
            .Where(item => item.TenantId == tenantId && item.RelationshipId == relationshipId)
            .OrderByDescending(item => item.Version)
            .FirstOrDefaultAsync(cancellationToken);
        var decision = decisionRow is null ? null : new EvaluationDecisionSpace(
            decisionRow.Version,
            decisionRow.BudgetCeilingInrPaise,
            Parse(decisionRow.AuthorityBoundariesJson),
            Parse(decisionRow.StopConditionsJson),
            decisionRow.ReviewCadenceMonths);

        return Ok(new RelationshipEvaluationProjection(
            relationshipId,
            RelationshipStateCodec.ToDatabase(relationship.State),
            relationship.State is EmploymentRelationshipState.Discovered ? "NOT_STARTED" : "AVAILABLE",
            context,
            nextQuestion,
            trial,
            goals,
            skills,
            decision));
    }

    private bool TryGetTenantId(out Guid tenantId)
    {
        tenantId = Guid.Empty;
        return HttpContext.Items.TryGetValue(TenantIsolationMiddleware.TenantIdItemKey, out var value)
            && Guid.TryParse(value?.ToString(), out tenantId);
    }

    private static JsonElement Parse(string value) => JsonSerializer.Deserialize<JsonElement>(value);
}