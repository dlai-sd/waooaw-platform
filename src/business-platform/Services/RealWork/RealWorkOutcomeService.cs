// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-5 Outcome trace (WC170-R008)
// Constitutional basis: C-005, C-023, C-049, C-059, C-063
// IB: IB-170

using System.Text.Json;
using System.Text.RegularExpressions;

namespace Waooaw.BusinessPlatform.Services.RealWork;

public static class ClaimDerivations
{
    public const string Independent = "INDEPENDENT";
    public const string AgentStated = "AGENT_STATED";
}

public static class ClaimCategories
{
    public const string Activity = "ACTIVITY";
    public const string Outcome = "OUTCOME";
}

/// <summary>An agent-reported figure. It is always stored as AGENT_STATED: only the owner derives an INDEPENDENT claim.</summary>
public sealed record AgentClaimInput(
    string ClaimId,
    string MeasureId,
    string ClaimText,
    string Category,
    decimal? Value,
    string Unit,
    DateTimeOffset AsOf,
    IReadOnlyList<Guid> WorkItemIds,
    IReadOnlyList<string> EvidenceIds,
    IReadOnlyList<string>? Limitations = null
);

public sealed record OutcomeClaimView(
    string ClaimId,
    string MeasureId,
    string ClaimText,
    string Category,
    string Derivation,
    string? Label,
    decimal? Value,
    string Unit,
    DateTimeOffset AsOf,
    IReadOnlyList<Guid> WorkItemIds,
    IReadOnlyList<string> EvidenceIds,
    IReadOnlyList<string> Limitations
);

public sealed record NotMeasurableOutcome(string MeasureId, string Text);

public sealed record OutcomeView(
    Guid RelationshipId,
    IReadOnlyList<OutcomeClaimView> Activity,
    IReadOnlyList<OutcomeClaimView> Outcomes,
    IReadOnlyList<OutcomeClaimView> AgentStated,
    IReadOnlyList<NotMeasurableOutcome> NotMeasurableYet,
    int WithheldClaims
);

public sealed record OutcomeTrace(
    OutcomeClaimView Claim,
    IReadOnlyList<TimelineWorkItemView> WorkItems,
    IReadOnlyList<string> Evidence
);

public sealed partial class RealWorkOutcomeService(
    IRealWorkLedger ledger,
    RealWorkTimelineService timeline,
    TimeProvider clock
)
{
    public const string NotMeasurableText = "Not measurable yet";
    public const string AgentStatedLabel = "Stated by the agent. Not independently verified.";
    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    [GeneratedRegex(@"^[A-Za-z0-9_.:-]{1,128}$")]
    private static partial Regex IdPattern();

    public void RecordAgentClaim(Guid tenantId, Guid relationshipId, AgentClaimInput input)
    {
        if (
            !IdPattern().IsMatch(input.ClaimId)
            || !IdPattern().IsMatch(input.MeasureId)
            || string.IsNullOrWhiteSpace(input.ClaimText)
            || input.ClaimText.Length > 300
            || input.Category is not (ClaimCategories.Activity or ClaimCategories.Outcome)
            || input.WorkItemIds.Count > 100
            || input.EvidenceIds.Count > 100
            || input.EvidenceIds.Any(item => string.IsNullOrWhiteSpace(item) || item.Length > 200)
        )
            throw new RealWorkConflictException("REAL_WORK_INVALID_REQUEST");
        var view = new OutcomeClaimView(
            input.ClaimId,
            input.MeasureId,
            input.ClaimText.Trim(),
            input.Category,
            ClaimDerivations.AgentStated,
            AgentStatedLabel,
            input.Value,
            input.Unit,
            input.AsOf.ToUniversalTime(),
            input.WorkItemIds,
            input.EvidenceIds,
            input.Limitations ?? []
        );
        ledger.Append(
            tenantId,
            relationshipId,
            RealWorkKinds.Claim,
            $"{input.ClaimId}:{RealWorkDigest.Of(JsonSerializer.SerializeToElement(view, Json))}",
            JsonSerializer.SerializeToElement(view, Json),
            clock.GetUtcNow()
        );
    }

    public OutcomeView Read(Guid tenantId, Guid relationshipId)
    {
        var stream = timeline.Read(tenantId, relationshipId);
        var known = stream.WorkItems.ToDictionary(item => item.WorkItemId);
        var activity = ActivityClaims(stream);

        var stated = LatestAgentClaims(tenantId, relationshipId);
        var shownStated = new List<OutcomeClaimView>();
        var withheld = 0;
        foreach (var claim in stated)
        {
            var items = claim.WorkItemIds.Where(known.ContainsKey).ToArray();
            if (items.Length == 0 || claim.EvidenceIds.Count == 0)
            {
                withheld++;
                continue;
            }
            shownStated.Add(claim with { WorkItemIds = items });
        }
        // A business outcome needs an owner-computed source that does not exist yet, so it never reads as a number.
        var slots = stated
            .Where(claim => claim.Category == ClaimCategories.Outcome)
            .Select(claim => claim.MeasureId)
            .Distinct()
            .Select(measure => new NotMeasurableOutcome(measure, NotMeasurableText))
            .ToArray();
        return new OutcomeView(
            relationshipId,
            activity,
            [],
            shownStated
                .Select(claim =>
                    claim.Category == ClaimCategories.Outcome ? claim with { Value = null } : claim
                )
                .ToArray(),
            slots,
            withheld
        );
    }

    public OutcomeTrace? Trace(Guid tenantId, Guid relationshipId, string claimId)
    {
        var view = Read(tenantId, relationshipId);
        var claim = view
            .Activity.Concat(view.AgentStated)
            .FirstOrDefault(item => item.ClaimId == claimId);
        if (claim is null)
            return null;
        var stream = timeline.Read(tenantId, relationshipId);
        var items = stream
            .WorkItems.Where(item => claim.WorkItemIds.Contains(item.WorkItemId))
            .ToArray();
        return new OutcomeTrace(claim, items, claim.EvidenceIds);
    }

    private IReadOnlyList<OutcomeClaimView> LatestAgentClaims(Guid tenantId, Guid relationshipId) =>
        ledger
            .List(tenantId, relationshipId, RealWorkKinds.Claim)
            .Select(record => record.Payload.Deserialize<OutcomeClaimView>(Json)!)
            .GroupBy(claim => claim.ClaimId)
            .Select(group => group.OrderByDescending(claim => claim.AsOf).First())
            .ToArray();

    /// <summary>Activity counts are derived here from completed work items, never taken from the agent.</summary>
    private IReadOnlyList<OutcomeClaimView> ActivityClaims(TimelineView stream) =>
        stream
            .WorkItems.Where(item => item.State == TimelineStates.Completed)
            .GroupBy(item => item.WorkItemType)
            .Select(group =>
            {
                var evidence = group
                    .SelectMany(item => item.Events.SelectMany(e => e.EvidenceRefs))
                    .Distinct()
                    .ToArray();
                return (group, evidence);
            })
            .Where(item => item.evidence.Length > 0)
            .Select(item => new OutcomeClaimView(
                $"ACTIVITY:{item.group.Key}",
                item.group.Key,
                $"{item.group.Count()} {RealWorkTimelineService.Humanize(item.group.Key)} completed",
                ClaimCategories.Activity,
                ClaimDerivations.Independent,
                null,
                item.group.Count(),
                "ITEMS",
                clock.GetUtcNow(),
                item.group.Select(work => work.WorkItemId).ToArray(),
                item.evidence,
                ["Counts completed work. It is activity, not a business result."]
            ))
            .ToArray();
}
