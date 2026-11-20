// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, ADR-051

using Npgsql;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

[Collection(Wc136PostgresFixture.CollectionName)]
public sealed class WorkbenchGoalHistoryPostgresTests(Wc136PostgresFixture fixture) : IAsyncLifetime
{
    private static readonly DateTimeOffset At = new(2030, 6, 1, 9, 30, 0, TimeSpan.Zero);

    private readonly PostgresWorkbenchGoalHistoryStore _store = new(fixture.AppConversations);

    // The migration is idempotent, so applying it here does not depend on the shared fixture's chain.
    public async Task InitializeAsync() =>
        await fixture.ExecuteAsync(
            await File.ReadAllTextAsync(
                RepositoryPaths.Resolve(
                    "infrastructure/postgres/init/99zzzzzzzz-wc136-14-workbench-goal-versions.sql"
                )
            )
        );

    public Task DisposeAsync() => Task.CompletedTask;

    private static WorkbenchGoalVersionEntry Entry(
        string title,
        string revisedBy = "Customer",
        string? reason = null,
        DateTimeOffset? at = null,
        IReadOnlyDictionary<string, string>? parameters = null
    ) => new(0, at ?? At, revisedBy, reason, title, parameters ?? new Dictionary<string, string>());

    [Fact]
    public async Task Append_NumbersEachGoalsVersionsFromOne_AndListsThemInOrder()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var goal = Guid.NewGuid();
        var other = Guid.NewGuid();

        await _store.AppendAsync(tenant, relationship, goal, Entry("First"), default);
        await _store.AppendAsync(tenant, relationship, other, Entry("Other first"), default);
        await _store.AppendAsync(
            tenant,
            relationship,
            goal,
            Entry(
                "Second",
                "Employer",
                "Wrong city",
                At.AddHours(2),
                new Dictionary<string, string> { ["PRIMARY_LOCATION"] = "Pune", ["A"] = "b" }
            ),
            default
        );

        var versions = await _store.ListAsync(tenant, relationship, goal, default);

        Assert.Equal([1, 2], versions.Select(entry => entry.VersionNo));
        Assert.Equal(["First", "Second"], versions.Select(entry => entry.Title));
        Assert.Null(versions[0].Reason);
        Assert.Empty(versions[0].Parameters);
        Assert.Equal("Employer", versions[1].RevisedBy);
        Assert.Equal("Wrong city", versions[1].Reason);
        Assert.Equal(At.AddHours(2), versions[1].RevisedAt);
        Assert.Equal(
            new Dictionary<string, string> { ["A"] = "b", ["PRIMARY_LOCATION"] = "Pune" },
            versions[1].Parameters
        );
        var otherVersions = await _store.ListAsync(tenant, relationship, other, default);
        Assert.Equal(1, Assert.Single(otherVersions).VersionNo);
    }

    [Fact]
    public async Task List_OfAGoalWithNoHistory_IsEmpty()
    {
        var versions = await _store.ListAsync(
            Guid.NewGuid(),
            Guid.NewGuid(),
            Guid.NewGuid(),
            default
        );

        Assert.Empty(versions);
    }

    [Fact]
    public async Task List_IsScopedToTheTenantAndTheRelationship()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var goal = Guid.NewGuid();
        await _store.AppendAsync(tenant, relationship, goal, Entry("Mine"), default);

        Assert.Empty(await _store.ListAsync(Guid.NewGuid(), relationship, goal, default));
        Assert.Empty(await _store.ListAsync(tenant, Guid.NewGuid(), goal, default));
        Assert.Single(await _store.ListAsync(tenant, relationship, goal, default));
    }

    [Fact]
    public async Task LatestVersions_ReportsTheHighestVersionOfEachGoalOfTheRelationship()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var twice = Guid.NewGuid();
        var once = Guid.NewGuid();
        var elsewhere = Guid.NewGuid();
        await _store.AppendAsync(tenant, relationship, twice, Entry("a"), default);
        await _store.AppendAsync(tenant, relationship, twice, Entry("b"), default);
        await _store.AppendAsync(tenant, relationship, once, Entry("c"), default);
        await _store.AppendAsync(tenant, Guid.NewGuid(), elsewhere, Entry("d"), default);

        var latest = await _store.LatestVersionsAsync(tenant, relationship, default);

        Assert.Equal(
            new Dictionary<Guid, int> { [twice] = 2, [once] = 1 },
            latest.ToDictionary(pair => pair.Key, pair => pair.Value)
        );
        Assert.Empty(await _store.LatestVersionsAsync(Guid.NewGuid(), relationship, default));
    }

    [Fact]
    public async Task Append_ByConcurrentWriters_NeverReusesAVersionNumber()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var goal = Guid.NewGuid();

        await Task.WhenAll(
            Enumerable
                .Range(0, 8)
                .Select(index =>
                    _store.AppendAsync(tenant, relationship, goal, Entry($"v{index}"), default)
                )
        );

        var versions = await _store.ListAsync(tenant, relationship, goal, default);
        Assert.Equal(Enumerable.Range(1, 8), versions.Select(entry => entry.VersionNo));
    }

    [Fact]
    public async Task Append_ForAnotherTenantThanTheOneItIsScopedTo_IsRefusedByRowLevelSecurity()
    {
        var tenant = Guid.NewGuid();
        await using var connection = new NpgsqlConnection(fixture.AppConnectionString);
        await connection.OpenAsync();
        await using var transaction = await connection.BeginTransactionAsync();
        await using var scope = new NpgsqlCommand(
            $"SELECT set_config('app.current_tenant_id','{tenant}',true)",
            connection,
            transaction
        );
        await scope.ExecuteNonQueryAsync();
        await using var insert = new NpgsqlCommand(
            $$"""
            INSERT INTO business.workbench_goal_versions
                (tenant_id,relationship_id,goal_id,version_no,revised_at,revised_by,title,parameters)
            VALUES ('{{Guid.NewGuid()}}','{{Guid.NewGuid()}}','{{Guid.NewGuid()}}',1,now(),'Customer','t','{}')
            """,
            connection,
            transaction
        );

        var failure = await Assert.ThrowsAsync<PostgresException>(() =>
            insert.ExecuteNonQueryAsync()
        );

        Assert.Equal(PostgresErrorCodes.InsufficientPrivilege, failure.SqlState);
    }

    [Fact]
    public async Task RecordedVersions_CannotBeChangedOrRemoved()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var goal = Guid.NewGuid();
        await _store.AppendAsync(tenant, relationship, goal, Entry("Kept"), default);

        var update = await Assert.ThrowsAsync<PostgresException>(() =>
            fixture.ExecuteAsync(
                $"UPDATE business.workbench_goal_versions SET title='Edited' WHERE goal_id='{goal}'"
            )
        );
        var delete = await Assert.ThrowsAsync<PostgresException>(() =>
            fixture.ExecuteAsync(
                $"DELETE FROM business.workbench_goal_versions WHERE goal_id='{goal}'"
            )
        );

        Assert.Contains("append-only", update.MessageText);
        Assert.Contains("append-only", delete.MessageText);
        Assert.Equal(
            "Kept",
            Assert.Single(await _store.ListAsync(tenant, relationship, goal, default)).Title
        );
    }
}
