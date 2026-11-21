// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02
// Constitutional basis: C-023, C-059, C-063, ADR-051

using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchCommandSupportTests
{
    private sealed class MutableClock(DateTimeOffset now) : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = now;

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private static readonly DateTimeOffset Start = new(2026, 6, 1, 9, 0, 0, TimeSpan.Zero);

    private static WorkbenchContext Context(Guid? participant = null, Guid? relationship = null) =>
        new(
            Guid.Parse("10000000-0000-0000-0000-000000000001"),
            relationship ?? Guid.Parse("20000000-0000-0000-0000-000000000002"),
            "customer-subject",
            participant ?? Guid.Parse("30000000-0000-0000-0000-000000000003"),
            RelationshipParticipantRole.Employer,
            WorkbenchAudiences.CustomerOwner,
            Guid.NewGuid().ToString("D")
        );

    private static WorkbenchCommandLedger NewLedger(TimeProvider? clock = null) =>
        new(new InMemoryWorkbenchLedgerStore(), clock ?? new MutableClock(Start));

    [Fact]
    public async Task Ledger_ReplaysTheStoredResultForTheSameKeyAndRequest()
    {
        var ledger = NewLedger();
        var key = Guid.NewGuid();
        var digest = WorkbenchCommandLedger.Digest("create_goal", "goals", new { title = "Grow" });
        var executions = 0;

        var first = await ledger.RunAsync(
            Context(),
            key,
            digest,
            () => Task.FromResult($"run-{++executions}"),
            CancellationToken.None
        );
        var second = await ledger.RunAsync(
            Context(),
            key,
            digest,
            () => Task.FromResult($"run-{++executions}"),
            CancellationToken.None
        );

        Assert.False(first.Replayed);
        Assert.True(second.Replayed);
        Assert.Equal("run-1", second.Result);
        Assert.Equal(1, executions);
    }

    [Fact]
    public async Task Ledger_ReplaysFromTheSharedStoreForAnotherReplica()
    {
        var store = new InMemoryWorkbenchLedgerStore();
        var key = Guid.NewGuid();
        var digest = WorkbenchCommandLedger.Digest("create_goal", "goals", new { title = "Grow" });
        var first = new WorkbenchCommandLedger(store, new MutableClock(Start));
        var otherReplica = new WorkbenchCommandLedger(store, new MutableClock(Start));

        await first.RunAsync(
            Context(),
            key,
            digest,
            () => Task.FromResult("done"),
            CancellationToken.None
        );
        var replay = await otherReplica.RunAsync(
            Context(),
            key,
            digest,
            () => Task.FromResult("again"),
            CancellationToken.None
        );

        Assert.True(replay.Replayed);
        Assert.Equal("done", replay.Result);
        Assert.Equal(1, store.Count);
    }

    [Fact]
    public async Task Ledger_RefusesAReusedKeyWithADifferentRequest()
    {
        var ledger = NewLedger();
        var key = Guid.NewGuid();
        await ledger.RunAsync(
            Context(),
            key,
            WorkbenchCommandLedger.Digest("create_goal", "goals", new { title = "Grow" }),
            () => Task.FromResult("done"),
            CancellationToken.None
        );

        var conflict = await Assert.ThrowsAsync<WorkbenchException>(() =>
            ledger.RunAsync(
                Context(),
                key,
                WorkbenchCommandLedger.Digest("create_goal", "goals", new { title = "Shrink" }),
                () => Task.FromResult("other"),
                CancellationToken.None
            )
        );

        Assert.Equal(409, conflict.Status);
        Assert.Equal(WorkbenchProblemCodes.IdempotencyConflict, conflict.Code);
    }

    [Fact]
    public async Task Ledger_KeepsKeysApartPerParticipantAndRelationship()
    {
        var ledger = NewLedger();
        var key = Guid.NewGuid();
        var digest = WorkbenchCommandLedger.Digest("pause", "controls", new { });
        var executions = 0;

        await ledger.RunAsync(
            Context(),
            key,
            digest,
            () => Task.FromResult($"run-{++executions}"),
            CancellationToken.None
        );
        var otherParticipant = await ledger.RunAsync(
            Context(Guid.NewGuid()),
            key,
            digest,
            () => Task.FromResult($"run-{++executions}"),
            CancellationToken.None
        );
        var otherRelationship = await ledger.RunAsync(
            Context(relationship: Guid.NewGuid()),
            key,
            digest,
            () => Task.FromResult($"run-{++executions}"),
            CancellationToken.None
        );

        Assert.False(otherParticipant.Replayed);
        Assert.False(otherRelationship.Replayed);
        Assert.Equal(3, executions);
    }

    [Fact]
    public async Task Ledger_DoesNotRecordAFailedExecution()
    {
        var ledger = NewLedger();
        var key = Guid.NewGuid();
        var digest = WorkbenchCommandLedger.Digest("pause", "controls", new { });

        await Assert.ThrowsAsync<WorkbenchException>(() =>
            ledger.RunAsync<string>(
                Context(),
                key,
                digest,
                () => throw new WorkbenchException(503, WorkbenchProblemCodes.Unavailable),
                CancellationToken.None
            )
        );
        var retry = await ledger.RunAsync(
            Context(),
            key,
            digest,
            () => Task.FromResult("ok"),
            CancellationToken.None
        );

        Assert.False(retry.Replayed);
        Assert.Equal("ok", retry.Result);
    }

    [Fact]
    public void Digest_DiffersByOperationResourceAndBody()
    {
        var baseline = WorkbenchCommandLedger.Digest("a", "r", new { x = 1 });

        Assert.Equal(baseline, WorkbenchCommandLedger.Digest("a", "r", new { x = 1 }));
        Assert.NotEqual(baseline, WorkbenchCommandLedger.Digest("b", "r", new { x = 1 }));
        Assert.NotEqual(baseline, WorkbenchCommandLedger.Digest("a", "s", new { x = 1 }));
        Assert.NotEqual(baseline, WorkbenchCommandLedger.Digest("a", "r", new { x = 2 }));
    }

    private static WorkbenchHandoffService Handoffs(
        TimeProvider clock,
        string baseUrl = "https://app.example.test/",
        int ttl = 900,
        InMemoryWorkbenchHandoffStore? store = null
    ) =>
        new(
            store ?? new InMemoryWorkbenchHandoffStore(),
            Options.Create(
                new WorkbenchOptions { HandoffBaseUrl = baseUrl, HandoffTtlSeconds = ttl }
            ),
            clock
        );

    [Fact]
    public async Task Handoff_IsSingleUseAndBoundToTheParticipantItWasIssuedTo()
    {
        var clock = new MutableClock(Start);
        var service = Handoffs(clock);
        var context = Context();
        var handoff = await service.CreateAsync(
            context,
            "WEB_WORKBENCH",
            null,
            CancellationToken.None
        );

        Assert.True(handoff.SingleUse);
        Assert.Null(
            await service.TryConsumeAsync(
                handoff.DestinationRef,
                context.TenantId,
                context.RelationshipId,
                Guid.NewGuid(),
                CancellationToken.None
            )
        );
        Assert.Null(
            await service.TryConsumeAsync(
                handoff.DestinationRef,
                context.TenantId,
                Guid.NewGuid(),
                context.ParticipantId,
                CancellationToken.None
            )
        );
        Assert.Null(
            await service.TryConsumeAsync(
                handoff.DestinationRef,
                Guid.NewGuid(),
                context.RelationshipId,
                context.ParticipantId,
                CancellationToken.None
            )
        );
        var redeemed = await service.TryConsumeAsync(
            handoff.DestinationRef,
            context.TenantId,
            context.RelationshipId,
            context.ParticipantId,
            CancellationToken.None
        );
        Assert.Equal("WEB_WORKBENCH", redeemed?.Purpose);
        Assert.Null(
            await service.TryConsumeAsync(
                handoff.DestinationRef,
                context.TenantId,
                context.RelationshipId,
                context.ParticipantId,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task Handoff_StoresOnlyTheHashOfTheTokenAndIsRedeemableByAnotherReplica()
    {
        var clock = new MutableClock(Start);
        var store = new InMemoryWorkbenchHandoffStore();
        var context = Context();
        var handoff = await Handoffs(clock, store: store)
            .CreateAsync(context, "APPROVAL", "decision-1", CancellationToken.None);

        var redeemed = await Handoffs(clock, store: store)
            .TryConsumeAsync(
                handoff.DestinationRef,
                context.TenantId,
                context.RelationshipId,
                context.ParticipantId,
                CancellationToken.None
            );

        Assert.False(store.Contains(handoff.DestinationRef));
        Assert.Equal(1, store.Count);
        Assert.Equal("APPROVAL", redeemed?.Purpose);
        Assert.Equal("decision-1", redeemed?.ContextRef);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task Handoff_RefusesABlankOrOversizedToken(string token)
    {
        var service = Handoffs(new MutableClock(Start));
        var context = Context();

        Assert.Null(
            await service.TryConsumeAsync(
                token,
                context.TenantId,
                context.RelationshipId,
                context.ParticipantId,
                CancellationToken.None
            )
        );
        Assert.Null(
            await service.TryConsumeAsync(
                new string('h', 129),
                context.TenantId,
                context.RelationshipId,
                context.ParticipantId,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task Handoff_ExpiresAfterItsTimeToLive()
    {
        var clock = new MutableClock(Start);
        var service = Handoffs(clock, ttl: 120);
        var context = Context();
        var handoff = await service.CreateAsync(
            context,
            "APPROVAL",
            "decision-1",
            CancellationToken.None
        );
        clock.Now = Start.AddSeconds(121);

        Assert.Equal(Start.AddSeconds(120), handoff.ExpiresAt);
        Assert.Null(
            await service.TryConsumeAsync(
                handoff.DestinationRef,
                context.TenantId,
                context.RelationshipId,
                context.ParticipantId,
                CancellationToken.None
            )
        );
    }

    [Fact]
    public async Task Handoff_ClampsTheTimeToLiveAndNeverReusesATokenOrAReference()
    {
        var clock = new MutableClock(Start);
        var short_ = await Handoffs(clock, ttl: 1)
            .CreateAsync(Context(), "PAYMENT", null, CancellationToken.None);
        var service = Handoffs(clock, ttl: 999999);
        var first = await service.CreateAsync(Context(), "EVIDENCE", null, CancellationToken.None);
        var second = await service.CreateAsync(Context(), "EVIDENCE", null, CancellationToken.None);

        Assert.Equal(Start.AddSeconds(60), short_.ExpiresAt);
        Assert.Equal(Start.AddSeconds(3600), first.ExpiresAt);
        Assert.NotEqual(first.DestinationRef, second.DestinationRef);
        Assert.NotEqual(first.HandoffRef, second.HandoffRef);
        Assert.StartsWith("h", first.DestinationRef);
    }

    [Theory]
    [InlineData("WEB_WORKBENCH", true)]
    [InlineData("APPROVAL", true)]
    [InlineData("PAYMENT", true)]
    [InlineData("EVIDENCE", true)]
    [InlineData("web_workbench", false)]
    [InlineData("ADMIN", false)]
    public void IsPurpose_AcceptsOnlyTheContractPurposes(string purpose, bool expected) =>
        Assert.Equal(expected, WorkbenchHandoffService.IsPurpose(purpose));

    [Fact]
    public async Task UrlFor_BuildsTheWebAddressFromTheConfiguredBase_AndIsNullWhenNoneIsConfigured()
    {
        var relationship = Guid.Parse("20000000-0000-0000-0000-000000000002");
        var configured = Handoffs(new MutableClock(Start));
        var handoff = await configured.CreateAsync(
            Context(),
            "WEB_WORKBENCH",
            null,
            CancellationToken.None
        );

        var url = configured.UrlFor(handoff, relationship);

        Assert.StartsWith($"https://app.example.test/relationships/{relationship:D}?handoff=", url);
        Assert.Contains(Uri.EscapeDataString(handoff.DestinationRef), url);
        Assert.Null(Handoffs(new MutableClock(Start), "").UrlFor(handoff, relationship));
        Assert.Null(
            Handoffs(new MutableClock(Start), "ftp://example.test").UrlFor(handoff, relationship)
        );
        Assert.Null(Handoffs(new MutableClock(Start), "not a url").UrlFor(handoff, relationship));
    }
}
