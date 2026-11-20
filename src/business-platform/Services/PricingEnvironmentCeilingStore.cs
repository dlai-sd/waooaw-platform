// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04
// Constitutional basis: C-023, C-059, C-063, C-088
using Microsoft.EntityFrameworkCore;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public static class EnvironmentCeilingOutcomes
{
    public const string AuthorityAbsent = "AUTHORITY_ABSENT";
    public const string AboveHardMaximum = "ABOVE_HARD_MAXIMUM";
    public const string BelowExposure = "BELOW_EXPOSURE";
    public const string Unchanged = "UNCHANGED";
    public const string DryRunOk = "DRY_RUN_OK";
    public const string Applied = "APPLIED";
}

public sealed record EnvironmentCeilingOutcome(
    string Outcome,
    long? PreviousPaise,
    long? AppliedPaise,
    long? BlockingPaise
);

/// <summary>Changes the environment spend authority only through the owner-defined function.</summary>
public interface IEnvironmentSpendCeilingStore
{
    Task<EnvironmentCeilingOutcome> ApplyAsync(
        string environment,
        long maximumPaise,
        long hardMaximumPaise,
        Guid authorityEvidenceId,
        DateTimeOffset asOf,
        bool dryRun,
        CancellationToken ct
    );
}

public sealed class PostgresEnvironmentSpendCeilingStore(
    IDbContextFactory<ConversationStoreDbContext> conversations
) : IEnvironmentSpendCeilingStore
{
    public async Task<EnvironmentCeilingOutcome> ApplyAsync(
        string environment,
        long maximumPaise,
        long hardMaximumPaise,
        Guid authorityEvidenceId,
        DateTimeOffset asOf,
        bool dryRun,
        CancellationToken ct
    )
    {
        await using var db = await conversations.CreateDbContextAsync(ct);
        var row = await db
            .Database.SqlQuery<CeilingRow>(
                $"""
                SELECT outcome AS "Outcome",previous_paise AS "PreviousPaise",
                    applied_paise AS "AppliedPaise",blocking_paise AS "BlockingPaise"
                FROM business.apply_environment_spend_ceiling(
                    {environment},{maximumPaise},{hardMaximumPaise},{authorityEvidenceId},{asOf},{dryRun})
                """
            )
            .SingleAsync(ct);
        return new(row.Outcome, row.PreviousPaise, row.AppliedPaise, row.BlockingPaise);
    }

    private sealed class CeilingRow
    {
        public string Outcome { get; init; } = "";
        public long? PreviousPaise { get; init; }
        public long? AppliedPaise { get; init; }
        public long? BlockingPaise { get; init; }
    }
}
