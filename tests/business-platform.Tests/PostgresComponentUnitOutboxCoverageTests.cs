// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051
using Npgsql;
using Waooaw.BusinessPlatform.Services;
using Waooaw.BusinessPlatform.Tests.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

[Collection(Wc136PostgresFixture.CollectionName)]
public sealed class PostgresComponentUnitOutboxCoverageTests(Wc136PostgresFixture fixture)
    : IAsyncLifetime
{
    private static readonly TimeSpan Lease = TimeSpan.FromMinutes(5);

    private PostgresComponentUnitOutbox Outbox => new(fixture.AppConnectionString);

    public Task InitializeAsync() =>
        fixture.ExecuteAsync("DELETE FROM business.component_unit_outbox");

    public Task DisposeAsync() => Task.CompletedTask;

    private static ComponentUnitCompletion Completion(
        string component = "lead_batch",
        Guid? tenant = null,
        Guid? evidence = null
    ) =>
        new(
            tenant ?? Guid.NewGuid(),
            Guid.NewGuid(),
            component,
            evidence ?? Guid.NewGuid(),
            "bp-component-unit"
        );

    private Task<string> RowAsync(Guid outboxId, string column) =>
        fixture.ScalarAsync<string>(
            $"SELECT COALESCE({column}::text,'<null>') FROM business.component_unit_outbox WHERE outbox_id='{outboxId}'"
        );

    [Fact]
    public async Task A_completion_is_stored_pending_and_claimed_with_its_identity()
    {
        var completion = Completion();
        Outbox.Completed(completion);

        var claimed = Assert.Single(await Outbox.ClaimAsync(10, Lease, CancellationToken.None));

        Assert.Equal(completion, claimed.Completion);
        Assert.Equal(0, claimed.Attempt);
        Assert.Equal("LEASED", await RowAsync(claimed.OutboxId, "state"));
    }

    [Fact]
    public async Task Recording_the_same_evidence_twice_keeps_one_row()
    {
        var completion = Completion();

        Outbox.Completed(completion);
        Outbox.Completed(completion with { ActorSubject = "someone-else" });

        Assert.Equal(
            1L,
            await fixture.ScalarAsync<long>("SELECT count(*) FROM business.component_unit_outbox")
        );
        Assert.Equal(
            "bp-component-unit",
            Assert
                .Single(await Outbox.ClaimAsync(10, Lease, CancellationToken.None))
                .Completion.ActorSubject
        );
    }

    [Fact]
    public async Task A_component_outside_the_allowed_alphabet_is_refused_and_nothing_is_stored()
    {
        Assert.Throws<PostgresException>(() => Outbox.Completed(Completion("bad component!")));

        Assert.Equal(
            0L,
            await fixture.ScalarAsync<long>("SELECT count(*) FROM business.component_unit_outbox")
        );
    }

    [Fact]
    public async Task A_claim_is_limited_leased_and_not_repeated_until_the_lease_lapses()
    {
        foreach (var _ in Enumerable.Range(0, 3))
            Outbox.Completed(Completion());

        var first = await Outbox.ClaimAsync(2, Lease, CancellationToken.None);
        var second = await Outbox.ClaimAsync(10, Lease, CancellationToken.None);
        var third = await Outbox.ClaimAsync(10, Lease, CancellationToken.None);

        Assert.Equal(2, first.Count);
        Assert.Single(second);
        Assert.Empty(third);
        Assert.Equal(3, first.Concat(second).Select(work => work.OutboxId).Distinct().Count());
    }

    [Fact]
    public async Task A_lease_is_rounded_up_to_whole_seconds()
    {
        Outbox.Completed(Completion());

        var work = Assert.Single(
            await Outbox.ClaimAsync(1, TimeSpan.FromSeconds(5.2), CancellationToken.None)
        );

        Assert.True(
            await fixture.ScalarAsync<bool>(
                $"""
                SELECT lease_expires_at - now() BETWEEN interval '5.5 seconds' AND interval '6 seconds'
                FROM business.component_unit_outbox WHERE outbox_id='{work.OutboxId}'
                """
            )
        );
    }

    [Theory]
    [InlineData(0, 60)]
    [InlineData(101, 60)]
    [InlineData(10, 4)]
    [InlineData(10, 901)]
    public async Task A_claim_outside_the_owner_bounds_is_refused(int limit, int leaseSeconds)
    {
        Outbox.Completed(Completion());

        await Assert.ThrowsAsync<PostgresException>(() =>
            Outbox.ClaimAsync(limit, TimeSpan.FromSeconds(leaseSeconds), CancellationToken.None)
        );
    }

    [Fact]
    public async Task A_lapsed_lease_is_claimed_again_by_another_worker()
    {
        Outbox.Completed(Completion());
        var first = Assert.Single(await Outbox.ClaimAsync(1, Lease, CancellationToken.None));
        await fixture.ExecuteAsync(
            $"UPDATE business.component_unit_outbox SET lease_expires_at=now()-interval '1 second' WHERE outbox_id='{first.OutboxId}'"
        );

        var again = Assert.Single(await Outbox.ClaimAsync(1, Lease, CancellationToken.None));

        Assert.Equal(first.OutboxId, again.OutboxId);
    }

    [Fact]
    public async Task Delivered_refused_and_unresolved_are_final_and_keep_their_code()
    {
        foreach (var _ in Enumerable.Range(0, 3))
            Outbox.Completed(Completion());
        var work = await Outbox.ClaimAsync(10, Lease, CancellationToken.None);

        await Outbox.DeliveredAsync(work[0].OutboxId, CancellationToken.None);
        await Outbox.RefusedAsync(
            work[1].OutboxId,
            "COMPONENT_NOT_YET_RELEASED",
            CancellationToken.None
        );
        await Outbox.UnresolvedAsync(work[2].OutboxId, "OWNER_UNAVAILABLE", CancellationToken.None);

        Assert.Equal("DELIVERED", await RowAsync(work[0].OutboxId, "state"));
        Assert.Equal("<null>", await RowAsync(work[0].OutboxId, "last_code"));
        Assert.Equal("REFUSED", await RowAsync(work[1].OutboxId, "state"));
        Assert.Equal("COMPONENT_NOT_YET_RELEASED", await RowAsync(work[1].OutboxId, "last_code"));
        Assert.Equal("UNRESOLVED", await RowAsync(work[2].OutboxId, "state"));
        Assert.Equal("OWNER_UNAVAILABLE", await RowAsync(work[2].OutboxId, "last_code"));
        foreach (var item in work)
            Assert.NotEqual("<null>", await RowAsync(item.OutboxId, "resolved_at"));
        Assert.Empty(await Outbox.ClaimAsync(10, Lease, CancellationToken.None));
    }

    [Fact]
    public async Task A_retry_returns_the_row_to_pending_after_its_delay_and_counts_the_attempt()
    {
        Outbox.Completed(Completion());
        var first = Assert.Single(await Outbox.ClaimAsync(1, Lease, CancellationToken.None));

        await Outbox.RetryAsync(
            first.OutboxId,
            TimeSpan.FromMinutes(10),
            "OWNER_UNAVAILABLE",
            CancellationToken.None
        );

        Assert.Equal("PENDING", await RowAsync(first.OutboxId, "state"));
        Assert.Equal("1", await RowAsync(first.OutboxId, "attempt_number"));
        Assert.Equal("<null>", await RowAsync(first.OutboxId, "lease_expires_at"));
        Assert.Empty(await Outbox.ClaimAsync(10, Lease, CancellationToken.None));

        await fixture.ExecuteAsync(
            $"UPDATE business.component_unit_outbox SET next_attempt_at=now() WHERE outbox_id='{first.OutboxId}'"
        );
        var again = Assert.Single(await Outbox.ClaimAsync(10, Lease, CancellationToken.None));
        Assert.Equal((first.OutboxId, 1), (again.OutboxId, again.Attempt));
    }

    [Fact]
    public async Task A_missing_or_over_long_code_is_bounded_before_it_is_stored()
    {
        foreach (var _ in Enumerable.Range(0, 2))
            Outbox.Completed(Completion());
        var work = await Outbox.ClaimAsync(10, Lease, CancellationToken.None);

        await Outbox.RefusedAsync(work[0].OutboxId, string.Empty, CancellationToken.None);
        await Outbox.UnresolvedAsync(
            work[1].OutboxId,
            new string('x', 150),
            CancellationToken.None
        );

        Assert.Equal("UNSPECIFIED", await RowAsync(work[0].OutboxId, "last_code"));
        Assert.Equal(new string('x', 100), await RowAsync(work[1].OutboxId, "last_code"));
    }

    [Fact]
    public async Task Marking_a_row_that_is_not_leased_changes_nothing()
    {
        Outbox.Completed(Completion());
        var work = Assert.Single(await Outbox.ClaimAsync(1, Lease, CancellationToken.None));
        await Outbox.DeliveredAsync(work.OutboxId, CancellationToken.None);

        await Outbox.RefusedAsync(work.OutboxId, "LATE", CancellationToken.None);
        await Outbox.DeliveredAsync(Guid.NewGuid(), CancellationToken.None);

        Assert.Equal("DELIVERED", await RowAsync(work.OutboxId, "state"));
        Assert.Equal("<null>", await RowAsync(work.OutboxId, "last_code"));
    }

    [Fact]
    public async Task A_retry_delay_beyond_a_day_is_refused_by_the_owner()
    {
        Outbox.Completed(Completion());
        var work = Assert.Single(await Outbox.ClaimAsync(1, Lease, CancellationToken.None));

        await Assert.ThrowsAsync<PostgresException>(() =>
            Outbox.RetryAsync(work.OutboxId, TimeSpan.FromDays(2), "SLOW", CancellationToken.None)
        );
    }

    [Fact]
    public async Task Racing_workers_never_claim_the_same_row_twice()
    {
        foreach (var _ in Enumerable.Range(0, 20))
            Outbox.Completed(Completion());

        var batches = await Task.WhenAll(
            Enumerable.Range(0, 6).Select(_ => Outbox.ClaimAsync(5, Lease, CancellationToken.None))
        );

        var ids = batches.SelectMany(batch => batch).Select(work => work.OutboxId).ToList();
        Assert.Equal(ids.Count, ids.Distinct().Count());
        ids.AddRange(
            (await Outbox.ClaimAsync(100, Lease, CancellationToken.None)).Select(work =>
                work.OutboxId
            )
        );
        Assert.Equal(20, ids.Distinct().Count());
        Assert.Equal(20, ids.Count);
    }

    [Fact]
    public void The_application_role_cannot_read_the_outbox_without_its_tenant_scope()
    {
        Outbox.Completed(Completion());

        using var connection = new NpgsqlConnection(fixture.AppConnectionString);
        connection.Open();
        using var count = new NpgsqlCommand(
            "SELECT count(*) FROM business.component_unit_outbox",
            connection
        );

        Assert.Equal(0L, (long)count.ExecuteScalar()!);
    }
}
