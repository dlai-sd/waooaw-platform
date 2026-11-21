// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-04
// Constitutional basis: C-023, C-059, C-063, C-088
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

[Collection(Wc136PostgresFixture.CollectionName)]
public sealed class PricingEnvironmentCeilingStoreCoverageTests(Wc136PostgresFixture fixture)
{
    private const long Hard = 50_000;

    private readonly PostgresEnvironmentSpendCeilingStore _store = new(fixture.AppConversations);

    private Task<EnvironmentCeilingOutcome> ApplyAsync(
        string environment,
        long maximum,
        bool dryRun = false,
        Guid? evidence = null
    ) =>
        _store.ApplyAsync(
            environment,
            maximum,
            Hard,
            evidence ?? Guid.NewGuid(),
            DateTimeOffset.UtcNow,
            dryRun,
            CancellationToken.None
        );

    private Task<long> MaximumAsync(string environment) =>
        fixture.ScalarAsync<long>(
            $"SELECT maximum_paise FROM business.environment_spend_authorities WHERE environment='{environment}'"
        );

    [Fact]
    public async Task An_environment_without_an_authority_reports_authority_absent()
    {
        var outcome = await ApplyAsync($"absent{Guid.NewGuid():N}"[..13], 10_000);

        Assert.Equal(
            new EnvironmentCeilingOutcome(
                EnvironmentCeilingOutcomes.AuthorityAbsent,
                null,
                null,
                null
            ),
            outcome
        );
    }

    [Fact]
    public async Task A_ceiling_above_the_hard_maximum_is_refused_and_reports_the_maximum()
    {
        var environment = await fixture.NewEnvironmentAsync(20_000);

        var outcome = await ApplyAsync(environment, Hard + 1);

        Assert.Equal(
            new EnvironmentCeilingOutcome(
                EnvironmentCeilingOutcomes.AboveHardMaximum,
                20_000,
                null,
                Hard
            ),
            outcome
        );
        Assert.Equal(20_000, await MaximumAsync(environment));
    }

    [Fact]
    public async Task Lowering_below_the_open_exposure_is_refused_with_the_blocking_amount()
    {
        var environment = await fixture.NewEnvironmentAsync(40_000);
        await fixture.ExecuteAsync(
            $"""
            INSERT INTO business.environment_spend_attempts
                (environment,owner_kind,attempt_id,original_tenant_id,activation_digest,
                 request_digest,reservation_reference,reserved_paise,state,reserved_at)
            VALUES ('{environment}','MODEL',gen_random_uuid(),gen_random_uuid(),'activation',
                repeat('c',64),gen_random_uuid(),22000,'RECONCILIATION_REQUIRED',clock_timestamp())
            """
        );

        var outcome = await ApplyAsync(environment, 10_000);
        var allowed = await ApplyAsync(environment, 22_000, dryRun: true);

        Assert.Equal(
            new EnvironmentCeilingOutcome(
                EnvironmentCeilingOutcomes.BelowExposure,
                40_000,
                null,
                22_000
            ),
            outcome
        );
        Assert.Equal(EnvironmentCeilingOutcomes.DryRunOk, allowed.Outcome);
        Assert.Equal(40_000, await MaximumAsync(environment));
    }

    [Fact]
    public async Task Restating_the_current_ceiling_changes_nothing()
    {
        var environment = await fixture.NewEnvironmentAsync(30_000);

        var outcome = await ApplyAsync(environment, 30_000);

        Assert.Equal(
            new EnvironmentCeilingOutcome(
                EnvironmentCeilingOutcomes.Unchanged,
                30_000,
                30_000,
                null
            ),
            outcome
        );
        Assert.Equal(
            1,
            await fixture.ScalarAsync<int>(
                $"SELECT authority_version FROM business.environment_spend_authorities WHERE environment='{environment}'"
            )
        );
    }

    [Fact]
    public async Task A_dry_run_reports_the_change_without_writing_it()
    {
        var environment = await fixture.NewEnvironmentAsync(30_000);

        var outcome = await ApplyAsync(environment, 35_000, dryRun: true);

        Assert.Equal(
            new EnvironmentCeilingOutcome(
                EnvironmentCeilingOutcomes.DryRunOk,
                30_000,
                35_000,
                null
            ),
            outcome
        );
        Assert.Equal(30_000, await MaximumAsync(environment));
    }

    [Fact]
    public async Task An_applied_ceiling_is_stored_with_its_evidence_and_a_new_authority_version()
    {
        var environment = await fixture.NewEnvironmentAsync(30_000);
        var evidence = Guid.NewGuid();

        var outcome = await ApplyAsync(environment, 12_000, evidence: evidence);

        Assert.Equal(
            new EnvironmentCeilingOutcome(EnvironmentCeilingOutcomes.Applied, 30_000, 12_000, null),
            outcome
        );
        Assert.Equal(12_000, await MaximumAsync(environment));
        Assert.Equal(
            evidence,
            await fixture.ScalarAsync<Guid>(
                $"SELECT authority_evidence_id FROM business.environment_spend_authorities WHERE environment='{environment}'"
            )
        );
        Assert.Equal(
            2,
            await fixture.ScalarAsync<int>(
                $"SELECT authority_version FROM business.environment_spend_authorities WHERE environment='{environment}'"
            )
        );
    }

    [Fact]
    public async Task An_empty_evidence_id_is_refused_by_the_owner_function()
    {
        var environment = await fixture.NewEnvironmentAsync(30_000);

        var failure = await Assert.ThrowsAnyAsync<Exception>(() =>
            ApplyAsync(environment, 12_000, evidence: Guid.Empty)
        );

        Assert.Contains("SPEND_CEILING_ARGUMENT_INVALID", failure.ToString());
        Assert.Equal(30_000, await MaximumAsync(environment));
    }
}
