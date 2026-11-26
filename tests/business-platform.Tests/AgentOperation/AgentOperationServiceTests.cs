// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R005, R006, R007, R013, R015, R017, R018, R021, R028, R030, R032, R036
// Constitutional basis: C-001, C-005, C-023, C-059, C-061, C-063

using System.Text.Json;
using System.Text.Json.Nodes;
using Waooaw.BusinessPlatform.Services.AgentOperation;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.AgentOperation;

internal sealed class FixedClock(DateTimeOffset now) : TimeProvider
{
    public override DateTimeOffset GetUtcNow() => now;
}

internal sealed class FakeRelationships : IOperationRelationshipSource
{
    public OperationRelationship? Value { get; set; }

    public Task<OperationRelationship?> GetAsync(OperationCaller caller, CancellationToken ct) =>
        Task.FromResult(Value);
}

internal sealed class FakeLimits : IOperationPackageLimits
{
    public Dictionary<string, int>? Remaining { get; set; } = new() { ["SOCIAL_PUBLICATION"] = 2 };

    public Task<IReadOnlyDictionary<string, int>?> RemainingAsync(OperationCaller caller, CancellationToken ct) =>
        Task.FromResult<IReadOnlyDictionary<string, int>?>(Remaining);
}

internal sealed class FakeAlerts : IOperationAlertSink
{
    public List<string> Signals { get; } = [];

    public Task RaiseAsync(Guid tenantId, Guid relationshipId, string signal, string severity, string period, string meaning, CancellationToken ct)
    {
        Signals.Add(signal);
        return Task.CompletedTask;
    }
}

internal sealed class FakeConnections : ICustomerConnectionInterface
{
    public List<ConnectionFacts> Facts { get; } = [];
    public bool NeedsRepairOnPublish { get; set; }
    public bool Explode { get; set; }
    public List<string> Messages { get; } = [];

    public Task<IReadOnlyList<ConnectionFacts>> ListAsync(Guid tenantId, CancellationToken ct) =>
        Task.FromResult<IReadOnlyList<ConnectionFacts>>(Facts.ToArray());

    public Task<ConnectedPost> PublishAsync(Guid tenantId, Guid actorId, Guid connectionId, string message, string approvalNote, CancellationToken ct)
    {
        if (NeedsRepairOnPublish)
            throw new ConnectionNeedsRepairException();
        if (Explode)
            throw new InvalidOperationException("boom");
        Messages.Add(message);
        return Task.FromResult(new ConnectedPost($"post-{Messages.Count}", DateTimeOffset.UnixEpoch));
    }
}

internal sealed class Harness
{
    public static readonly Guid Tenant = Guid.Parse("11111111-1111-1111-1111-111111111111");
    public static readonly Guid Relationship = Guid.Parse("22222222-2222-2222-2222-222222222222");
    public static readonly DateTimeOffset Now = new(2026, 12, 1, 9, 0, 0, TimeSpan.Zero);

    public InMemoryAgentOperationStore Store { get; } = new();
    public FakeRelationships Relationships { get; } = new();
    public FakeLimits Limits { get; } = new();
    public FakeAlerts Alerts { get; } = new();
    public FakeConnections Connections { get; } = new();
    public AgentOperationService Service { get; }
    public OperationCaller Caller { get; } = new(Tenant, Relationship, Guid.NewGuid(), "customer", "customer_owner");
    public ExperienceDeclaration Declaration { get; }

    public Harness(bool legacy = false)
    {
        var manifest = JsonNode.Parse(File.ReadAllText(RepositoryPaths.Resolve("src/digital-marketing-agent/contracts/employment-interface-manifest.v1.json")))!;
        if (legacy)
            foreach (var name in new[] { "modes", "eventLayers", "planLevels", "platforms", "views" })
                manifest["experience"]!.AsObject().Remove(name);
        Declaration = ExperienceManifestScanner.Scan(JsonSerializer.SerializeToElement(manifest)).Declaration!;
        Relationships.Value = new OperationRelationship("TEST_PROFESSIONAL", false, Declaration);
        Service = new AgentOperationService(Store, Relationships, Limits, Connections, Alerts, new FixedClock(Now));
    }

    public static JsonElement Pay(object value) => JsonSerializer.SerializeToElement(value);

    public static OperationProposal Event(string key, string layer, string title = "A festival", int day = 10) =>
        new(key, "EVENT", layer, null, null, title, null, new DateOnly(2026, 12, day), null, "https://example.org/source", "Fits the business.", 0.8, null, null, null);

    public static OperationProposal Label(string key, string title) =>
        new(key, "PROFILE_LABEL", null, null, null, title, null, null, null, null, "Found on a public page.", 0.6, null, null, Pay(new { group = "Business" }));

    public static OperationProposal Content(string key, bool checksPass = true) =>
        new(key, "CONTENT", null, null, null, $"Festival post {key}", "Happy festival from the clinic.", null, null, null, null, null, "FACEBOOK", "SOCIAL_PUBLICATION",
            Pay(new { reviewChecks = new[] { new { checkId = "CLAIMS", passed = checksPass } } }));

    public static OperationProposal Node(string key, string level, string? parent) =>
        new(key, "PLAN_NODE", null, level, parent, $"{level} {key}", null, new DateOnly(2026, 12, 1), new DateOnly(2026, 12, 31), null, null, null, null, null, null);

    public Task<ProposalOutcome> ProposeAsync(params OperationProposal[] proposals) =>
        Service.ProposeAsync(Caller, proposals, CancellationToken.None);

    public async Task<ItemView> ProposeOneAsync(OperationProposal proposal)
    {
        var outcome = await ProposeAsync(proposal);
        Assert.Equal(1, outcome.Stored);
        return (await Service.ListAsync(Caller, proposal.Kind, CancellationToken.None)).Single(item => item.Title == proposal.Title);
    }

    public Task<ItemView> CreateAsync(string kind, string title, string? layer = null, string? level = null, Guid? parent = null, DateOnly? start = null, string? platform = null, string? component = null, Guid? key = null, string? route = null) =>
        Service.CreateItemAsync(Caller, key ?? Guid.NewGuid(), new CreateItemRequest(kind, layer, level, parent, title, null, start, null, platform, component, route), CancellationToken.None);

    /// <summary>Induct and Goals ready, a connected Facebook account, and an approved top-level theme.</summary>
    public async Task ReadyAsync(string connectedAccount = "page-1")
    {
        await Service.ProposeAsync(Caller, [Label("l1", "Dental clinic")], CancellationToken.None);
        var label = (await Service.ListAsync(Caller, "PROFILE_LABEL", CancellationToken.None)).Single();
        await Service.ConfirmLabelAsync(Caller, label.ItemId, null, null, CancellationToken.None);
        foreach (var platform in Declaration.Platforms)
            await Service.AnswerPlatformAsync(Caller, platform.PlatformId, platform.PlatformId == "FACEBOOK" ? "PRESENT" : "NOT_PRESENT", null, CancellationToken.None);
        foreach (var skill in Declaration.Cadence.Select(cadence => cadence.SkillId))
            await Service.SetGoalAsync(Caller, skill, new GoalRequest("None yet", "10 posts", "PLATFORM_OWNER_RECORD", "MONTHLY", "CUSTOMER_APPROVAL"), null, CancellationToken.None);
        var theme = await CreateAsync("PLAN_NODE", "December theme", level: "MASTER_THEME");
        await Service.ApproveAsync(Caller, theme.ItemId, theme.VersionNo, null, CancellationToken.None);
        Connections.Facts.Add(new ConnectionFacts(Guid.NewGuid(), "META_FACEBOOK", "CONNECTED", connectedAccount, "Test page"));
        await Service.SaveSettingsAsync("founder", AgentOperationSettings.Default with { SandboxAccountIds = [connectedAccount] }, CancellationToken.None);
    }

    public async Task<ItemView> ApprovedContentAsync(string key = "c1")
    {
        var content = await ProposeOneAsync(Content(key));
        return await Service.ApproveAsync(Caller, content.ItemId, content.VersionNo, null, CancellationToken.None);
    }

    public async Task<AgentOperationException> RefusedAsync(Func<Task> action)
    {
        var failure = await Assert.ThrowsAsync<AgentOperationException>(action);
        return failure;
    }
}

public sealed class AgentOperationServiceTests
{
    [Fact]
    public async Task ADeclarationWithoutModesShowsNoModesAndKeepsTheLegacyMenu()
    {
        var harness = new Harness(legacy: true);

        var frame = await harness.Service.GetFrameAsync(harness.Caller, null, CancellationToken.None);

        Assert.False(frame.ModesDeclared);
        Assert.Empty(frame.Modes);
        Assert.Empty(frame.Layers);
    }

    [Fact]
    public async Task InductionReadinessMovesFromNotStartedThroughConfirmationAndPlatformAnswersToReady()
    {
        var harness = new Harness();
        var frame = await harness.Service.GetFrameAsync(harness.Caller, "INDUCT", CancellationToken.None);
        Assert.Equal("NOT_STARTED", frame.Modes.Single(mode => mode.Mode.ModeId == "INDUCT").Readiness.State);
        Assert.Equal("OPEN_CONVERSATION", frame.Next!.Command);

        await harness.ProposeAsync(Harness.Label("l1", "Dental clinic"));
        frame = await harness.Service.GetFrameAsync(harness.Caller, "INDUCT", CancellationToken.None);
        Assert.Equal("CONFIRM_LABELS", frame.Next!.Command);

        var label = (await harness.Service.ListAsync(harness.Caller, "PROFILE_LABEL", CancellationToken.None)).Single();
        await harness.Service.ConfirmLabelAsync(harness.Caller, label.ItemId, null, null, CancellationToken.None);
        frame = await harness.Service.GetFrameAsync(harness.Caller, "INDUCT", CancellationToken.None);
        Assert.Equal("ANSWER_PLATFORM", frame.Next!.Command);
        Assert.Equal("FACEBOOK", frame.Next.Target);

        foreach (var platform in harness.Declaration.Platforms)
            await harness.Service.AnswerPlatformAsync(harness.Caller, platform.PlatformId, "NOT_PRESENT", null, CancellationToken.None);
        frame = await harness.Service.GetFrameAsync(harness.Caller, "INDUCT", CancellationToken.None);
        var induct = frame.Modes.Single(mode => mode.Mode.ModeId == "INDUCT").Readiness;
        Assert.Equal("READY", induct.State);
        Assert.Equal(induct.Total, induct.Done);
        Assert.Contains("of", induct.Line);
    }

    [Fact]
    public async Task EveryModeOpensAtAnyTimeAndAGateBlocksOnlyTheActionWithASideEffect()
    {
        var harness = new Harness();

        // Opening the Goals and Operations screens needs nothing; a plan can be read and a mode remembered.
        await harness.Service.SetModeAsync(harness.Caller, "GOALS", "plan_tree", CancellationToken.None);
        var tree = await harness.Service.GetPlanTreeAsync(harness.Caller, CancellationToken.None);
        var frame = await harness.Service.GetFrameAsync(harness.Caller, null, CancellationToken.None);
        Assert.Empty(tree.Nodes);
        Assert.Equal("GOALS", frame.LastMode);
        Assert.Equal("plan_tree", frame.LastSurface);

        // Scheduling is the side effect and explains which mode to finish.
        var content = await harness.ApprovedContentAsync();
        var refused = await harness.RefusedAsync(() => harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None));
        Assert.Equal(AgentOperationCodes.GateBlocked, refused.Code);
        Assert.Equal("INDUCT", refused.NextMode);
    }

    [Fact]
    public async Task ASensitiveLayerStartsOffAndNothingIsSuggestedOnALayerTheCustomerHasOff()
    {
        var harness = new Harness();
        var frame = await harness.Service.GetFrameAsync(harness.Caller, null, CancellationToken.None);
        Assert.True(frame.Layers.Single(layer => layer.LayerId == "FESTIVAL").On);
        Assert.False(frame.Layers.Single(layer => layer.LayerId == "RELIGION").On);
        Assert.False(frame.Layers.Single(layer => layer.LayerId == "POLITICS").On);

        var off = await harness.ProposeAsync(Harness.Event("e1", "RELIGION"));
        Assert.Equal(0, off.Stored);
        Assert.Equal(AgentOperationCodes.LayerOff, off.Refused.Single().Code);

        await harness.Service.SetLayerAsync(harness.Caller, "RELIGION", true, "TOOL", CancellationToken.None);
        Assert.Equal(1, (await harness.ProposeAsync(Harness.Event("e1", "RELIGION"))).Stored);

        await harness.Service.SetLayerAsync(harness.Caller, "RELIGION", false, "TOOL", CancellationToken.None);
        Assert.Equal(AgentOperationCodes.LayerOff, (await harness.ProposeAsync(Harness.Event("e2", "RELIGION"))).Refused.Single().Code);
        var calendar = await harness.Service.GetCalendarAsync(harness.Caller, new DateOnly(2026, 12, 1), new DateOnly(2026, 12, 31), false, CancellationToken.None);
        Assert.DoesNotContain(calendar.Entries, entry => entry.Layer == "RELIGION");
    }

    [Fact]
    public async Task TheCustomerChoosesLayersAndAddsOwnLayerAndOwnEventsThatAlwaysShow()
    {
        var harness = new Harness();
        var layer = await harness.Service.AddCustomLayerAsync(harness.Caller, "Family dates", Guid.NewGuid(), CancellationToken.None);
        var unknown = await harness.RefusedAsync(() => harness.Service.SetLayerAsync(harness.Caller, "NOT_A_LAYER", true, "TOOL", CancellationToken.None));
        await harness.Service.SetLayerAsync(harness.Caller, "FESTIVAL", false, "ASKED", CancellationToken.None);

        var own = await harness.CreateAsync("EVENT", "Clinic anniversary", layer: "FESTIVAL", start: new DateOnly(2026, 12, 12));
        var calendar = await harness.Service.GetCalendarAsync(harness.Caller, new DateOnly(2026, 12, 1), new DateOnly(2026, 12, 31), false, CancellationToken.None);

        Assert.StartsWith("CUSTOM_", layer.LayerId);
        Assert.Equal(AgentOperationCodes.UnknownLayer, unknown.Code);
        Assert.Equal("CUSTOMER_OWNED", own.AuthorState);
        Assert.Contains(calendar.Entries, entry => entry.ItemId == own.ItemId);
        Assert.Contains(calendar.Layers, value => value.LayerId == layer.LayerId && value.On && value.Custom);
    }

    [Fact]
    public async Task ASuggestionIsNotAppliedUntilAcceptedAndTheCustomersOwnItemIsNeverTouchedByTheAgent()
    {
        var harness = new Harness();
        await harness.ProposeAsync(Harness.Event("e1", "FESTIVAL", "Diwali"));
        var suggestion = (await harness.Service.ListAsync(harness.Caller, "EVENT", CancellationToken.None)).Single();
        Assert.True(suggestion.IsSuggestion);
        Assert.Equal("SUGGESTED", suggestion.State);

        await harness.Service.HandOverAsync(harness.Caller, suggestion.ItemId, null, CancellationToken.None);
        var again = await harness.ProposeAsync(Harness.Event("e1", "FESTIVAL", "Diwali"));
        Assert.Equal(AgentOperationCodes.CustomerOwned, again.Refused.Single().Code);

        await harness.Service.TakeBackAsync(harness.Caller, suggestion.ItemId, null, CancellationToken.None);
        var item = (await harness.Service.ListAsync(harness.Caller, "EVENT", CancellationToken.None)).Single();
        Assert.Equal("CUSTOMER_EDITED", item.AuthorState);
        Assert.False(item.IsSuggestion);
    }

    [Fact]
    public async Task AcceptHideRestoreEditAndUndoKeepEveryVersionAndDeleteNothing()
    {
        var harness = new Harness();
        await harness.ProposeAsync(Harness.Event("e1", "FESTIVAL", "Diwali"));
        var item = (await harness.Service.ListAsync(harness.Caller, "EVENT", CancellationToken.None)).Single();

        var accepted = await harness.Service.AcceptAsync(harness.Caller, item.ItemId, null, CancellationToken.None);
        var edited = await harness.Service.EditAsync(harness.Caller, item.ItemId, new EditItemRequest("Diwali week", null, null, null, accepted.VersionNo), null, CancellationToken.None);
        var undone = await harness.Service.UndoAsync(harness.Caller, item.ItemId, CancellationToken.None);
        var hidden = await harness.Service.HideAsync(harness.Caller, item.ItemId, null, CancellationToken.None);
        var calendar = await harness.Service.GetCalendarAsync(harness.Caller, new DateOnly(2026, 12, 1), new DateOnly(2026, 12, 31), false, CancellationToken.None);
        var restored = await harness.Service.RestoreAsync(harness.Caller, item.ItemId, CancellationToken.None);
        var versions = await harness.Service.VersionsAsync(harness.Caller, item.ItemId, CancellationToken.None);

        Assert.Equal("ACCEPTED", accepted.State);
        Assert.Equal("Diwali week", edited.Title);
        Assert.Equal("Diwali", undone.Title);
        Assert.Equal("HIDDEN", hidden.State);
        Assert.Empty(calendar.Entries);
        Assert.Equal("ACCEPTED", restored.State);
        Assert.Equal(6, versions.Count);
        var stale = await harness.RefusedAsync(() => harness.Service.EditAsync(harness.Caller, item.ItemId, new EditItemRequest("x", null, null, null, 1), null, CancellationToken.None));
        Assert.Equal(AgentOperationCodes.Conflict, stale.Code);
    }

    [Fact]
    public async Task ACreateIsIdempotentAndCountedOnce()
    {
        var harness = new Harness();
        var key = Guid.NewGuid();

        var first = await harness.CreateAsync("NOTE", "Remember the banner", key: key, route: "ASKED");
        var replay = await harness.CreateAsync("NOTE", "Remember the banner", key: key, route: "ASKED");

        Assert.Equal(first.ItemId, replay.ItemId);
        var share = await harness.Service.GetShareAsync(DateOnly.FromDateTime(Harness.Now.UtcDateTime), DateOnly.FromDateTime(Harness.Now.UtcDateTime), CancellationToken.None);
        Assert.Equal(1, share.Days.Single().Asked);
    }

    [Fact]
    public async Task EachPlanLevelIsBuiltOnlyUnderAnApprovedParent()
    {
        var harness = new Harness();
        await harness.ProposeAsync(Harness.Node("master", "MASTER_THEME", null));
        var master = (await harness.Service.ListAsync(harness.Caller, "PLAN_NODE", CancellationToken.None)).Single();

        var early = await harness.ProposeAsync(Harness.Node("week1", "WEEKLY_THEME", "master"));
        Assert.Equal(AgentOperationCodes.ParentNotApproved, early.Refused.Single().Code);

        await harness.Service.ApproveAsync(harness.Caller, master.ItemId, master.VersionNo, null, CancellationToken.None);
        var later = await harness.ProposeAsync(Harness.Node("week1", "WEEKLY_THEME", "master"));
        Assert.Equal(1, later.Stored);

        var skipped = await harness.ProposeAsync(Harness.Node("story1", "STORY", "master"));
        Assert.Equal(AgentOperationCodes.Invalid, skipped.Refused.Single().Code);
        var tree = await harness.Service.GetPlanTreeAsync(harness.Caller, CancellationToken.None);
        Assert.Equal(new[] { "MASTER_THEME", "WEEKLY_THEME" }, tree.Nodes.Select(node => node.LevelId));
        Assert.Equal(4, tree.Levels.Count);
    }

    [Fact]
    public async Task ACustomerBuildsTheirOwnPlanAndEveryNodeHasTheSameApprovalRules()
    {
        var harness = new Harness();
        var master = await harness.CreateAsync("PLAN_NODE", "Mine", level: "MASTER_THEME");
        var week = await harness.CreateAsync("PLAN_NODE", "Week one", level: "WEEKLY_THEME", parent: master.ItemId);
        var orphan = await harness.RefusedAsync(() => harness.CreateAsync("PLAN_NODE", "Lost", level: "WEEKLY_THEME"));
        var wrongLevel = await harness.RefusedAsync(() => harness.CreateAsync("PLAN_NODE", "Wrong", level: "STORY", parent: master.ItemId));

        Assert.Equal("CUSTOMER_OWNED", week.AuthorState);
        Assert.Equal("DRAFT", week.State);
        Assert.Equal(AgentOperationCodes.Invalid, orphan.Code);
        Assert.Equal(AgentOperationCodes.Invalid, wrongLevel.Code);
    }

    [Fact]
    public async Task ApprovalIsOfTheExactVersionAndAnyLaterChangeNeedsApprovalAgain()
    {
        var harness = new Harness();
        var content = await harness.ProposeOneAsync(Harness.Content("c1"));

        var stale = await harness.RefusedAsync(() => harness.Service.ApproveAsync(harness.Caller, content.ItemId, content.VersionNo + 3, null, CancellationToken.None));
        var approved = await harness.Service.ApproveAsync(harness.Caller, content.ItemId, content.VersionNo, null, CancellationToken.None);
        var replay = await harness.Service.ApproveAsync(harness.Caller, content.ItemId, approved.VersionNo, null, CancellationToken.None);
        var edited = await harness.Service.EditAsync(harness.Caller, content.ItemId, new EditItemRequest(null, "A new line.", null, null, approved.VersionNo), null, CancellationToken.None);

        Assert.Equal(AgentOperationCodes.Conflict, stale.Code);
        Assert.True(approved.IsApproved);
        Assert.Equal(approved.VersionNo, replay.VersionNo);
        Assert.False(edited.IsApproved);
        Assert.Equal("PROPOSED", edited.State);
    }

    [Fact]
    public async Task AnAgentDraftThatFailedItsReviewChecksIsNeverStored()
    {
        var harness = new Harness();

        var outcome = await harness.ProposeAsync(Harness.Content("c1", checksPass: false));

        Assert.Equal(0, outcome.Stored);
        Assert.Equal("OPERATION_REVIEW_CHECKS_FAILED", outcome.Refused.Single().Code);
    }

    [Fact]
    public async Task PublishingNeedsTheExactApprovedVersionASeparateAuthorityATestedAccountAndASandboxAccount()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        var content = await harness.ApprovedContentAsync();
        var slot = await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None);
        Assert.Equal("SCHEDULED", slot.State);

        var noAuthority = await harness.RefusedAsync(() => harness.Service.PublishAsync(harness.Caller, slot.ItemId, CancellationToken.None));
        Assert.Equal(AgentOperationCodes.PublishAuthorityMissing, noAuthority.Code);

        await harness.Service.SetPublishAuthorityAsync(harness.Caller, true, CancellationToken.None);
        await harness.Service.SaveSettingsAsync("founder", AgentOperationSettings.Default, CancellationToken.None);
        var notSandbox = await harness.RefusedAsync(() => harness.Service.PublishAsync(harness.Caller, slot.ItemId, CancellationToken.None));
        Assert.Equal(AgentOperationCodes.SandboxOnly, notSandbox.Code);
        Assert.Empty(harness.Connections.Messages);

        await harness.Service.SaveSettingsAsync("founder", AgentOperationSettings.Default with { SandboxAccountIds = ["page-1"] }, CancellationToken.None);
        var published = await harness.Service.PublishAsync(harness.Caller, slot.ItemId, CancellationToken.None);
        var again = await harness.Service.PublishAsync(harness.Caller, slot.ItemId, CancellationToken.None);

        Assert.Equal("PUBLISHED", published.State);
        Assert.Equal("PUBLISHED", again.State);
        Assert.Single(harness.Connections.Messages);
        Assert.Equal("Happy festival from the clinic.", harness.Connections.Messages[0]);
    }

    [Fact]
    public async Task APostChangedAfterApprovalIsNotPublished()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        await harness.Service.SetPublishAuthorityAsync(harness.Caller, true, CancellationToken.None);
        var content = await harness.ApprovedContentAsync();
        var slot = await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None);
        await harness.Service.EditAsync(harness.Caller, content.ItemId, new EditItemRequest(null, "Changed after approval.", null, null, content.VersionNo), null, CancellationToken.None);

        var refused = await harness.RefusedAsync(() => harness.Service.PublishAsync(harness.Caller, slot.ItemId, CancellationToken.None));

        Assert.Equal(AgentOperationCodes.NotApproved, refused.Code);
        Assert.Empty(harness.Connections.Messages);
    }

    [Fact]
    public async Task AnExpiredConnectionBecomesRepairRaisesAnAlertAndMarksTheFailedPublish()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        await harness.Service.SetPublishAuthorityAsync(harness.Caller, true, CancellationToken.None);
        var content = await harness.ApprovedContentAsync();
        var slot = await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None);
        harness.Connections.NeedsRepairOnPublish = true;

        var refused = await harness.RefusedAsync(() => harness.Service.PublishAsync(harness.Caller, slot.ItemId, CancellationToken.None));

        Assert.Equal(AgentOperationCodes.NotConnected, refused.Code);
        Assert.Contains("CONNECTION_NEEDS_REPAIR", harness.Alerts.Signals);
        var failed = (await harness.Service.ListAsync(harness.Caller, "SLOT", CancellationToken.None)).Single();
        Assert.Equal("PUBLISH_FAILED", failed.State);
        var attention = await harness.Service.GetAttentionAsync(new DateOnly(2026, 11, 25), new DateOnly(2026, 12, 2), CancellationToken.None);
        Assert.Contains(attention, row => row.Metric == "PUBLISH_FAILED");
        Assert.Contains(attention, row => row.Metric == "CONNECTION_REPAIR");
    }

    [Fact]
    public async Task AFailedProviderCallRaisesAnAlertAndNeverReportsPublished()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        await harness.Service.SetPublishAuthorityAsync(harness.Caller, true, CancellationToken.None);
        var content = await harness.ApprovedContentAsync();
        var slot = await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None);
        harness.Connections.Explode = true;

        var refused = await harness.RefusedAsync(() => harness.Service.PublishAsync(harness.Caller, slot.ItemId, CancellationToken.None));

        Assert.Equal(502, refused.Status);
        Assert.Contains("PUBLISH_FAILED", harness.Alerts.Signals);
    }

    [Fact]
    public async Task SchedulingStopsAtThePackageLimitAndAnUnreadableOwnerIsNeverGuessed()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        var first = await harness.ApprovedContentAsync("c1");
        var second = await harness.ApprovedContentAsync("c2");
        var third = await harness.ApprovedContentAsync("c3");
        await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), first.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None);
        await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), second.ItemId, "FACEBOOK", new DateOnly(2026, 12, 6), null, CancellationToken.None);

        var over = await harness.RefusedAsync(() => harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), third.ItemId, "FACEBOOK", new DateOnly(2026, 12, 7), null, CancellationToken.None));
        harness.Limits.Remaining = null;
        var unknown = await harness.RefusedAsync(() => harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), third.ItemId, "FACEBOOK", new DateOnly(2026, 12, 7), null, CancellationToken.None));
        harness.Limits.Remaining = new() { ["SOCIAL_PUBLICATION"] = 2 };
        var calendar = await harness.Service.GetCalendarAsync(harness.Caller, new DateOnly(2026, 12, 1), new DateOnly(2026, 12, 31), false, CancellationToken.None);

        Assert.Equal(AgentOperationCodes.LimitReached, over.Code);
        Assert.Equal(AgentOperationCodes.LimitReached, unknown.Code);
        var limit = calendar.Limits.Single(item => item.ComponentId == "SOCIAL_PUBLICATION");
        Assert.Equal(2, limit.Remaining);
        Assert.Equal(2, limit.Committed);
    }

    [Fact]
    public async Task ANothingIsScheduledOrPublishedOnAStoppedRelationship()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        var content = await harness.ApprovedContentAsync();
        harness.Relationships.Value = harness.Relationships.Value! with { Stopped = true };

        var schedule = await harness.RefusedAsync(() => harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None));
        var propose = await harness.RefusedAsync(() => harness.ProposeAsync(Harness.Event("e1", "FESTIVAL")));

        Assert.Equal(AgentOperationCodes.Stopped, schedule.Code);
        Assert.Equal(AgentOperationCodes.Stopped, propose.Code);
    }

    [Fact]
    public async Task MovingAnApprovedItemNeedsApprovalAgainButMovingAScheduledSlotDoesNot()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        var content = await harness.ApprovedContentAsync();
        var slot = await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None);
        var moved = await harness.Service.MoveAsync(harness.Caller, content.ItemId, new DateOnly(2026, 12, 20), null, null, CancellationToken.None);
        var stale = await harness.RefusedAsync(() => harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 6), null, CancellationToken.None));
        var slotMoved = await harness.Service.MoveAsync(harness.Caller, slot.ItemId, new DateOnly(2026, 12, 8), null, null, CancellationToken.None);

        Assert.False(moved.IsApproved);
        Assert.Equal(AgentOperationCodes.NotApproved, stale.Code);
        Assert.Equal("SCHEDULED", slotMoved.State);
    }

    [Fact]
    public async Task PlatformStatusIsPresentNotPresentConnectedNeedsRepairOrNotYetConnectableAndNothingTypedOrShownIsASecret()
    {
        var harness = new Harness();
        var facebook = await harness.Service.AnswerPlatformAsync(harness.Caller, "FACEBOOK", "PRESENT", null, CancellationToken.None);
        var instagram = await harness.Service.AnswerPlatformAsync(harness.Caller, "INSTAGRAM", "PRESENT", null, CancellationToken.None);
        var youtube = await harness.Service.AnswerPlatformAsync(harness.Caller, "YOUTUBE", "PRESENT", null, CancellationToken.None);
        var absent = await harness.Service.AnswerPlatformAsync(harness.Caller, "LINKEDIN", "NOT_PRESENT", null, CancellationToken.None);
        Assert.Equal("PRESENT", facebook.Presence);
        Assert.True(facebook.CanConnect);
        Assert.Equal("NOT_YET_CONNECTABLE", instagram.Presence);
        Assert.False(instagram.CanConnect);
        Assert.Equal("NOT_YET_CONNECTABLE", youtube.Presence);
        Assert.Equal("NOT_PRESENT", absent.Presence);

        await harness.Service.SaveSettingsAsync("founder", AgentOperationSettings.Default with { InstagramConnectEnabled = true }, CancellationToken.None);
        Assert.Equal("PRESENT", (await harness.Service.AnswerPlatformAsync(harness.Caller, "INSTAGRAM", "PRESENT", null, CancellationToken.None)).Presence);

        harness.Connections.Facts.Add(new ConnectionFacts(Guid.NewGuid(), "META_FACEBOOK", "CONNECTED", "page-1", "Test page"));
        Assert.Equal("CONNECTED_TESTED", (await harness.Service.TestPlatformAsync(harness.Caller, "FACEBOOK", CancellationToken.None)).Presence);
        harness.Connections.Facts[0] = harness.Connections.Facts[0] with { Status = "NEEDS_REPAIR" };
        var repair = await harness.Service.TestPlatformAsync(harness.Caller, "FACEBOOK", CancellationToken.None);
        Assert.Equal("NEEDS_REPAIR", repair.Presence);
        Assert.Contains("CONNECTION_NEEDS_REPAIR", harness.Alerts.Signals);
        Assert.DoesNotContain("token", JsonSerializer.Serialize(repair), StringComparison.OrdinalIgnoreCase);
        var badAnswer = await harness.RefusedAsync(() => harness.Service.AnswerPlatformAsync(harness.Caller, "FACEBOOK", "PASSWORD123", null, CancellationToken.None));
        Assert.Equal(AgentOperationCodes.Invalid, badAnswer.Code);
    }

    [Fact]
    public async Task GoalsAreSetSkillBySkillWithEveryRequiredFieldAndAMaterialRevisionWaitsForTheCustomer()
    {
        var harness = new Harness();
        var skill = harness.Declaration.Cadence[0].SkillId;
        var good = new GoalRequest("None yet", "10 posts", "PLATFORM_OWNER_RECORD", "MONTHLY", "CUSTOMER_APPROVAL");
        var unknownSkill = await harness.RefusedAsync(() => harness.Service.SetGoalAsync(harness.Caller, "NOT_A_SKILL", good, null, CancellationToken.None));
        var badCadence = await harness.RefusedAsync(() => harness.Service.SetGoalAsync(harness.Caller, skill, good with { Cadence = "WHENEVER" }, null, CancellationToken.None));
        var badAuthority = await harness.RefusedAsync(() => harness.Service.SetGoalAsync(harness.Caller, skill, good with { AuthorityState = "ANYTHING" }, null, CancellationToken.None));
        var markup = await harness.RefusedAsync(() => harness.Service.SetGoalAsync(harness.Caller, skill, good with { Target = "<script>" }, null, CancellationToken.None));
        var set = await harness.Service.SetGoalAsync(harness.Caller, skill, good, null, CancellationToken.None);

        var proposal = new OperationProposal("g", "GOAL", null, null, null, "Goal", null, null, null, "SOURCE", null, null, null, null,
            Harness.Pay(new { skillId = skill, baseline = "None yet", target = "20 posts", evidenceSource = "PLATFORM_OWNER_RECORD", cadence = "MONTHLY", authorityState = "CUSTOMER_APPROVAL" }));
        Assert.Equal(1, (await harness.ProposeAsync(proposal)).Stored);
        var pending = (await harness.Service.ListAsync(harness.Caller, "GOAL", CancellationToken.None)).Single();
        Assert.Equal("PENDING_CONFIRMATION", pending.State);
        Assert.Equal("10 posts", pending.Payload.GetProperty("target").GetString());

        var confirmed = await harness.Service.ConfirmGoalAsync(harness.Caller, skill, true, null, CancellationToken.None);

        Assert.All(new[] { unknownSkill, badCadence, badAuthority, markup }, failure => Assert.Equal(AgentOperationCodes.Invalid, failure.Code));
        Assert.Equal("CONFIRMED", set.State);
        Assert.Equal("CONFIRMED", confirmed.State);
        Assert.Equal("20 posts", confirmed.Payload.GetProperty("target").GetString());
        Assert.Equal(3, (await harness.Service.VersionsAsync(harness.Caller, set.ItemId, CancellationToken.None)).Count);
    }

    [Fact]
    public async Task DecliningARevisionKeepsTheConfirmedGoal()
    {
        var harness = new Harness();
        var skill = harness.Declaration.Cadence[0].SkillId;
        await harness.Service.SetGoalAsync(harness.Caller, skill, new GoalRequest("None yet", "10 posts", "PLATFORM_OWNER_RECORD", "MONTHLY", "CUSTOMER_APPROVAL"), null, CancellationToken.None);
        await harness.ProposeAsync(new OperationProposal("g", "GOAL", null, null, null, "Goal", null, null, null, "SOURCE", null, null, null, null,
            Harness.Pay(new { skillId = skill, baseline = "None yet", target = "99 posts", evidenceSource = "PLATFORM_OWNER_RECORD", cadence = "MONTHLY", authorityState = "CUSTOMER_APPROVAL" })));

        var declined = await harness.Service.ConfirmGoalAsync(harness.Caller, skill, false, null, CancellationToken.None);

        Assert.Equal("CONFIRMED", declined.State);
        Assert.Equal("10 posts", declined.Payload.GetProperty("target").GetString());
        Assert.False(declined.Payload.TryGetProperty("pending", out _));
    }

    [Fact]
    public async Task AcceptingADigestMakesItsGoalChangesTheNextGoalVersionsAndRaisesBehindPaceAlerts()
    {
        var harness = new Harness();
        var skill = harness.Declaration.Cadence[0].SkillId;
        await harness.Service.SetGoalAsync(harness.Caller, skill, new GoalRequest("None yet", "10 posts", "PLATFORM_OWNER_RECORD", "MONTHLY", "CUSTOMER_APPROVAL"), null, CancellationToken.None);
        await harness.ProposeAsync(new OperationProposal("d", "DIGEST", null, null, null, "2026-12 digest", "Do more of the festival posts.", null, null, null, null, null, null, null,
            Harness.Pay(new { goalChanges = new[] { new { skillId = skill, target = "12 posts" } }, behindPace = new[] { skill } })));
        var digest = (await harness.Service.ListAsync(harness.Caller, "DIGEST", CancellationToken.None)).Single();

        var accepted = await harness.Service.DecideDigestAsync(harness.Caller, digest.ItemId, true, CancellationToken.None);

        Assert.Equal("ACCEPTED", accepted.State);
        var goal = (await harness.Service.ListAsync(harness.Caller, "GOAL", CancellationToken.None)).Single();
        Assert.Equal("12 posts", goal.Payload.GetProperty("target").GetString());
        Assert.Contains("GOAL_BEHIND_PACE", harness.Alerts.Signals);
    }

    [Fact]
    public async Task PublicRegistryFindingsAreRefusedUntilTheFounderAllowsThem()
    {
        var harness = new Harness();
        var finding = new OperationProposal("f1", "FINDING", null, null, null, "GST number", "Registered", null, null, "https://example.org/registry", "Public registry.", 0.7, null, null,
            Harness.Pay(new { basis = "REGISTRY" }));

        var off = await harness.ProposeAsync(finding);
        await harness.Service.SaveSettingsAsync("founder", AgentOperationSettings.Default with { RegistryReadsEnabled = true }, CancellationToken.None);
        var on = await harness.ProposeAsync(finding);

        Assert.Equal(AgentOperationCodes.NotEnabled, off.Refused.Single().Code);
        Assert.Equal(1, on.Stored);
    }

    [Fact]
    public async Task TheChatAllowanceDefaultsTo1000IsSetByTheFounderAndExplainsItsLimitPlainly()
    {
        var harness = new Harness();
        var frame = await harness.Service.GetFrameAsync(harness.Caller, null, CancellationToken.None);
        Assert.Equal(1000, frame.Chats.Allowed);
        Assert.Equal(1000, frame.Chats.Remaining);

        await harness.Service.SaveSettingsAsync("founder", AgentOperationSettings.Default with { ChatAllowanceDefault = 2 }, CancellationToken.None);
        await harness.Service.RecordChatAsync(harness.Caller, CancellationToken.None);
        var last = await harness.Service.RecordChatAsync(harness.Caller, CancellationToken.None);
        var limit = await harness.RefusedAsync(() => harness.Service.RecordChatAsync(harness.Caller, CancellationToken.None));

        Assert.True(last.Reached);
        Assert.Equal(AgentOperationCodes.ChatLimitReached, limit.Code);
        Assert.Contains("still available", limit.Message);
        Assert.Contains("CHAT_ALLOWANCE_LOW", harness.Alerts.Signals);

        await harness.Service.SaveSettingsAsync("founder", AgentOperationSettings.Default with { ChatAllowanceByProfessionalType = new Dictionary<string, int> { ["TEST_PROFESSIONAL"] = 5 } }, CancellationToken.None);
        Assert.Equal(5, (await harness.Service.GetFrameAsync(harness.Caller, null, CancellationToken.None)).Chats.Allowed);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(-5)]
    [InlineData(1_000_001)]
    public async Task AnInvalidChatAllowanceIsRefused(int allowance)
    {
        var harness = new Harness();

        var failure = await harness.RefusedAsync(() => harness.Service.SaveSettingsAsync("founder", AgentOperationSettings.Default with { ChatAllowanceDefault = allowance }, CancellationToken.None));

        Assert.Equal(AgentOperationCodes.Invalid, failure.Code);
    }

    [Fact]
    public async Task TheShareByRouteCountsOnlyTheRouteAndNeverRevealsARelationshipOrContent()
    {
        var harness = new Harness();
        await harness.CreateAsync("NOTE", "Asked for", route: "ASKED");
        await harness.CreateAsync("NOTE", "By tool", route: "TOOL");
        await harness.ProposeAsync(Harness.Event("e1", "FESTIVAL"));
        var suggestion = (await harness.Service.ListAsync(harness.Caller, "EVENT", CancellationToken.None)).Single();
        await harness.Service.AcceptAsync(harness.Caller, suggestion.ItemId, null, CancellationToken.None);
        var day = DateOnly.FromDateTime(Harness.Now.UtcDateTime);

        var share = await harness.Service.GetShareAsync(day, day, CancellationToken.None);
        var counters = await harness.Store.CountersAsync(day, day, CancellationToken.None);

        var today = share.Days.Single();
        Assert.Equal((1, 1, 1), (today.Asked, today.Accepted, today.Tool));
        Assert.Equal(0.6667, share.AssistantShare);
        Assert.Equal(1, share.RelationshipsCounted);
        Assert.All(counters, counter => Assert.DoesNotContain(Harness.Relationship.ToString("N"), counter.RelationshipRef));
        Assert.DoesNotContain("Asked for", JsonSerializer.Serialize(share));
    }

    [Fact]
    public async Task ACustomerCanCreateEveryKindOfOwnItemAndTheConversationContextSeesThem()
    {
        var harness = new Harness();
        await harness.CreateAsync("PLACEHOLDER", "Something for spring", start: new DateOnly(2026, 12, 20));
        var note = await harness.CreateAsync("NOTE", "Ask about banners");
        await harness.CreateAsync("CONTENT", "My own post", platform: "FACEBOOK", component: "SOCIAL_PUBLICATION");
        await harness.ProposeAsync(Harness.Event("e1", "FESTIVAL"));

        var context = await harness.Service.GetContextAsync(harness.Caller, "GOALS", "MONTH", note.ItemId, CancellationToken.None);

        Assert.Equal(1, context.PendingSuggestions);
        Assert.Equal(3, context.CustomerOwned);
        Assert.Equal("Ask about banners", context.Selected!.Title);
        Assert.Equal("GOALS", context.Mode);
        Assert.Equal(1000, context.Chats.Allowed);
        var blocked = await harness.RefusedAsync(() => harness.CreateAsync("SLOT", "Direct slot"));
        var markup = await harness.RefusedAsync(() => harness.CreateAsync("NOTE", "<b>bold</b>"));
        Assert.Equal(AgentOperationCodes.Invalid, blocked.Code);
        Assert.Equal(AgentOperationCodes.Invalid, markup.Code);
    }

    [Fact]
    public async Task OperationsReadinessNamesTheOneNextStepForApprovalsThenSchedulingThenPublishing()
    {
        var harness = new Harness();
        await harness.ReadyAsync();
        var content = await harness.ProposeOneAsync(Harness.Content("c1"));
        var frame = await harness.Service.GetFrameAsync(harness.Caller, "OPERATIONS", CancellationToken.None);
        Assert.Equal("OPEN_APPROVALS", frame.Next!.Command);

        await harness.Service.ApproveAsync(harness.Caller, content.ItemId, content.VersionNo, null, CancellationToken.None);
        frame = await harness.Service.GetFrameAsync(harness.Caller, "OPERATIONS", CancellationToken.None);
        Assert.Equal("OPEN_SCHEDULE", frame.Next!.Command);

        await harness.Service.ScheduleAsync(harness.Caller, Guid.NewGuid(), content.ItemId, "FACEBOOK", new DateOnly(2026, 12, 5), null, CancellationToken.None);
        frame = await harness.Service.GetFrameAsync(harness.Caller, "OPERATIONS", CancellationToken.None);
        Assert.Equal("OPEN_PUBLISHED", frame.Next!.Command);
    }

    [Fact]
    public async Task TheRelationshipIsNotFoundWhenTheOwnerCannotReadIt()
    {
        var harness = new Harness();
        harness.Relationships.Value = null;

        var failure = await harness.RefusedAsync(() => harness.Service.GetFrameAsync(harness.Caller, null, CancellationToken.None));

        Assert.Equal(404, failure.Status);
    }
}
