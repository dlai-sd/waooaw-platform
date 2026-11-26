// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R005, R030, R032, R036
// Constitutional basis: C-005, C-023, C-026, C-059, C-063

using System.Text.Json;
using Npgsql;
using Waooaw.BusinessPlatform.Services.AgentOperation;
using Waooaw.BusinessPlatform.Tests.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AgentOperation;

/// <summary>
/// The Postgres store runs as the unprivileged <c>business_app</c> login on the shared WC-136 container, so grants,
/// row-level security and the append-only version history are the real ones.
/// </summary>
[Collection(Wc136PostgresFixture.CollectionName)]
public sealed class AgentOperationPostgresStoreTests(Wc136PostgresFixture fixture) : IAsyncLifetime
{
    private static readonly DateTimeOffset At = new(2026, 12, 1, 9, 0, 0, TimeSpan.Zero);

    private readonly PostgresAgentOperationStore _store = new(fixture.AppConversations);

    // The migration is idempotent, so applying it twice also proves a replay changes nothing.
    public async Task InitializeAsync()
    {
        var sql = await File.ReadAllTextAsync(
            RepositoryPaths.Resolve(
                "infrastructure/postgres/init/99zzzzzzzz-wc174-01-agent-operation.sql"
            )
        );
        await fixture.ExecuteAsync(sql);
        await fixture.ExecuteAsync(sql);
    }

    public Task DisposeAsync() => Task.CompletedTask;

    private static OperationItem Item(
        Guid tenant,
        Guid relationship,
        string title = "Festival post",
        int version = 1,
        string kind = "NOTE"
    ) =>
        new(
            tenant,
            relationship,
            Guid.NewGuid(),
            kind,
            null,
            null,
            null,
            title,
            "Body",
            new DateOnly(2026, 12, 10),
            null,
            "PROPOSED",
            "AGENT_PROPOSED",
            version,
            0,
            "AGENT",
            null,
            "Fits the business.",
            0.7,
            null,
            null,
            JsonSerializer.SerializeToElement(new { group = "Business" }),
            At,
            At,
            "agent"
        );

    [Fact]
    public async Task AnItemIsInsertedOnceVersionedAndListedOnlyForItsOwnTenant()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var item = Item(tenant, relationship);

        Assert.True(await _store.InsertAsync(item, default));
        Assert.False(await _store.InsertAsync(item, default));

        var read = await _store.GetAsync(tenant, relationship, item.ItemId, default);
        Assert.Equal("Festival post", read!.Title);
        Assert.Single(await _store.ListAsync(tenant, relationship, default));
        Assert.Empty(await _store.ListAsync(Guid.NewGuid(), relationship, default));
        Assert.Null(await _store.GetAsync(Guid.NewGuid(), relationship, item.ItemId, default));
    }

    [Fact]
    public async Task AnUpdateWritesTheNextVersionOnlyForTheExpectedOne_AndEveryVersionIsKept()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var item = Item(tenant, relationship, "First");
        await _store.InsertAsync(item, default);

        var second = item with { Title = "Second", VersionNo = 2, UpdatedAt = At.AddHours(1) };
        Assert.True(await _store.UpdateAsync(second, 1, default));
        Assert.False(await _store.UpdateAsync(second with { Title = "Lost" }, 1, default));

        var versions = await _store.VersionsAsync(tenant, relationship, item.ItemId, default);
        Assert.Equal(["First", "Second"], versions.Select(version => version.Title).ToArray());
        Assert.Equal(
            "Second",
            (await _store.GetAsync(tenant, relationship, item.ItemId, default))!.Title
        );
    }

    [Fact]
    public async Task TheVersionHistoryCannotBeRewritten()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var item = Item(tenant, relationship);
        await _store.InsertAsync(item, default);

        var failure = await Assert.ThrowsAsync<PostgresException>(() =>
            fixture.ExecuteAsync(
                $"UPDATE business.agent_operation_item_versions SET doc = '{{}}' WHERE item_id = '{item.ItemId}'"
            )
        );

        Assert.Contains("append-only", failure.MessageText);
    }

    [Fact]
    public async Task StateIsRememberedPerRelationshipAndStartsEmpty()
    {
        var tenant = Guid.NewGuid();
        var relationship = Guid.NewGuid();
        var empty = await _store.GetStateAsync(tenant, relationship, At, default);
        Assert.Null(empty.LastMode);
        Assert.Equal(0, empty.ChatsUsed);

        await _store.SaveStateAsync(
            empty with
            {
                LastMode = "GOALS",
                LastSurface = "kernel:calendar",
                Layers = new Dictionary<string, bool> { ["RELIGION"] = true },
                CustomLayers = [new CustomLayer("MY_LAYER", "My layer")],
                TourSeen = true,
                ChatsUsed = 7,
                PublishAuthority = true,
            },
            default
        );
        await _store.SaveStateAsync(
            (await _store.GetStateAsync(tenant, relationship, At, default)) with { ChatsUsed = 8 },
            default
        );

        var read = await _store.GetStateAsync(tenant, relationship, At, default);
        Assert.Equal("GOALS", read.LastMode);
        Assert.True(read.Layers["RELIGION"]);
        Assert.Equal("MY_LAYER", Assert.Single(read.CustomLayers).LayerId);
        Assert.True(read.TourSeen);
        Assert.True(read.PublishAuthority);
        Assert.Equal(8, read.ChatsUsed);
    }

    [Fact]
    public async Task SettingsDefaultTo1000ConversationsAndAreSavedByTheFounder()
    {
        await _store.SaveSettingsAsync(AgentOperationSettings.Default, "founder", default);
        Assert.Equal(1000, (await _store.GetSettingsAsync(default)).ChatAllowanceDefault);

        await _store.SaveSettingsAsync(
            new AgentOperationSettings(
                500,
                new Dictionary<string, int> { ["TYPE_A"] = 20 },
                InstagramConnectEnabled: true,
                PublishSandboxOnly: false,
                SandboxAccountIds: ["page-1"],
                RegistryReadsEnabled: true
            ),
            "founder",
            default
        );

        var read = await _store.GetSettingsAsync(default);
        Assert.Equal(500, read.ChatAllowanceDefault);
        Assert.Equal(20, read.AllowanceFor("TYPE_A"));
        Assert.True(read.InstagramConnectEnabled);
        Assert.False(read.PublishSandboxOnly);
        Assert.Equal(["page-1"], read.SandboxAccountIds);
        Assert.True(read.RegistryReadsEnabled);
    }

    [Fact]
    public async Task CountersAddUpPerDayAndHoldOnlyCounts()
    {
        var day = new DateOnly(2031, 3, 4);
        var reference = Convert.ToHexString(Guid.NewGuid().ToByteArray()).ToLowerInvariant();

        await _store.CountAsync(day, reference, "ROUTE_ASKED", 2, default);
        await _store.CountAsync(day, reference, "ROUTE_ASKED", 3, default);
        await _store.CountAsync(day, reference, "PUBLISHED", 1, default);

        var counters = await _store.CountersAsync(day, day, default);
        var mine = counters.Where(counter => counter.RelationshipRef == reference).ToArray();
        Assert.Equal(5, mine.Single(counter => counter.Metric == "ROUTE_ASKED").Count);
        Assert.Equal(1, mine.Single(counter => counter.Metric == "PUBLISHED").Count);
        Assert.Empty(await _store.CountersAsync(day.AddDays(1), day.AddDays(2), default));
    }
}
