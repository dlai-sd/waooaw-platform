// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-02, C6-03
// Constitutional basis: C-023, C-059, C-063, ADR-051

using Microsoft.Extensions.Options;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.BusinessPlatform.Services.Workbench;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Workbench;

public sealed class WorkbenchCommandServiceLedgerTests
{
    private static readonly WorkbenchContext Context = new(
        Guid.NewGuid(),
        Guid.NewGuid(),
        "customer-subject",
        Guid.NewGuid(),
        RelationshipParticipantRole.Employer,
        WorkbenchAudiences.CustomerOwner,
        Guid.NewGuid().ToString("D")
    );

    private sealed class ScriptedLedgerStore(params WorkbenchLedgerClaim[] claims)
        : IWorkbenchLedgerStore
    {
        private readonly Queue<WorkbenchLedgerClaim> _claims = new(claims);

        public int Claims { get; private set; }
        public List<string> Completed { get; } = [];
        public int Abandoned { get; private set; }

        public Task<WorkbenchLedgerClaim> ClaimAsync(
            WorkbenchContext context,
            Guid idempotencyKey,
            string digest,
            DateTimeOffset now,
            DateTimeOffset leaseUntil,
            CancellationToken ct
        )
        {
            Claims += 1;
            Assert.True(leaseUntil > now);
            var next = _claims.Count > 1 ? _claims.Dequeue() : _claims.Peek();
            return Task.FromResult(next);
        }

        public Task CompleteAsync(
            WorkbenchContext context,
            Guid idempotencyKey,
            string resultJson,
            DateTimeOffset now,
            CancellationToken ct
        )
        {
            Completed.Add(resultJson);
            return Task.CompletedTask;
        }

        public Task AbandonAsync(
            WorkbenchContext context,
            Guid idempotencyKey,
            CancellationToken ct
        )
        {
            Abandoned += 1;
            return Task.CompletedTask;
        }
    }

    private static WorkbenchCommandLedger LedgerOver(IWorkbenchLedgerStore store) =>
        new(store, TimeProvider.System);

    private static readonly WorkbenchLedgerClaim Claimed = new(WorkbenchLedgerClaimKind.Claimed);

    private static Task<WorkbenchCommandReceipt> Receipt() =>
        Task.FromResult(
            new WorkbenchCommandReceipt(
                "1.0",
                Guid.NewGuid(),
                "COMPLETED",
                "resource",
                "version-1",
                false,
                Context.CorrelationId
            )
        );

    [Fact]
    public async Task Run_ExecutesAClaimedCommandOnceAndStoresItsReceipt()
    {
        var store = new ScriptedLedgerStore(Claimed);
        var executions = 0;

        var (result, replayed) = await LedgerOver(store)
            .RunAsync(
                Context,
                Guid.NewGuid(),
                "digest",
                () =>
                {
                    executions += 1;
                    return Receipt();
                },
                CancellationToken.None
            );

        Assert.False(replayed);
        Assert.Equal(1, executions);
        Assert.Equal(0, store.Abandoned);
        var stored = Assert.Single(store.Completed);
        Assert.Contains(result.OperationRef.ToString("D"), stored);
    }

    [Fact]
    public async Task Run_ReleasesTheClaimWhenTheCommandFailsSoARetryRunsAgain()
    {
        var store = new ScriptedLedgerStore(Claimed);

        await Assert.ThrowsAsync<InvalidOperationException>(() =>
            LedgerOver(store)
                .RunAsync<WorkbenchCommandReceipt>(
                    Context,
                    Guid.NewGuid(),
                    "digest",
                    () => throw new InvalidOperationException("boom"),
                    CancellationToken.None
                )
        );

        Assert.Equal(1, store.Abandoned);
        Assert.Empty(store.Completed);
    }

    [Fact]
    public async Task Run_AnswersAReplayFromTheStoredReceiptWithoutExecuting()
    {
        var original = await Receipt();
        var json = System.Text.Json.JsonSerializer.Serialize(
            original,
            new System.Text.Json.JsonSerializerOptions(System.Text.Json.JsonSerializerDefaults.Web)
        );
        var store = new ScriptedLedgerStore(
            new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.Replay, json)
        );

        var (result, replayed) = await LedgerOver(store)
            .RunAsync<WorkbenchCommandReceipt>(
                Context,
                Guid.NewGuid(),
                "digest",
                () => throw new InvalidOperationException("must not run"),
                CancellationToken.None
            );

        Assert.True(replayed);
        Assert.Equal(original, result);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("null")]
    public async Task Run_AReplayWithoutAReadableReceiptIsUnavailable(string? stored)
    {
        var store = new ScriptedLedgerStore(
            new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.Replay, stored)
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            LedgerOver(store)
                .RunAsync(Context, Guid.NewGuid(), "digest", Receipt, CancellationToken.None)
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.Unavailable, failure.Code);
    }

    [Fact]
    public async Task Run_AReusedKeyWithADifferentRequestIsAnIdempotencyConflict()
    {
        var store = new ScriptedLedgerStore(
            new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.Conflict)
        );

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            LedgerOver(store)
                .RunAsync(Context, Guid.NewGuid(), "digest", Receipt, CancellationToken.None)
        );

        Assert.Equal(409, failure.Status);
        Assert.Equal(WorkbenchProblemCodes.IdempotencyConflict, failure.Code);
        Assert.Equal(0, store.Abandoned);
    }

    [Fact]
    public async Task Run_WaitsForACommandRunningElsewhereThenRunsWhenTheClaimIsFree()
    {
        var store = new ScriptedLedgerStore(
            new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.InProgress),
            Claimed
        );

        var (_, replayed) = await LedgerOver(store)
            .RunAsync(Context, Guid.NewGuid(), "digest", Receipt, CancellationToken.None);

        Assert.False(replayed);
        Assert.Equal(2, store.Claims);
        Assert.Single(store.Completed);
    }

    [Fact]
    public async Task Run_AnInFlightCommandThatNeverFinishesIsReportedUnavailableAndNeverRunTwice()
    {
        var store = new ScriptedLedgerStore(
            new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.InProgress)
        );
        var executions = 0;

        var failure = await Assert.ThrowsAsync<WorkbenchException>(() =>
            LedgerOver(store)
                .RunAsync(
                    Context,
                    Guid.NewGuid(),
                    "digest",
                    () =>
                    {
                        executions += 1;
                        return Receipt();
                    },
                    CancellationToken.None
                )
        );

        Assert.Equal(503, failure.Status);
        Assert.Equal(0, executions);
        Assert.Equal(41, store.Claims);
    }

    [Fact]
    public async Task Run_StopsWaitingWhenTheCallerCancels()
    {
        var store = new ScriptedLedgerStore(
            new WorkbenchLedgerClaim(WorkbenchLedgerClaimKind.InProgress)
        );
        using var cancellation = new CancellationTokenSource(TimeSpan.FromMilliseconds(100));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            LedgerOver(store)
                .RunAsync(Context, Guid.NewGuid(), "digest", Receipt, cancellation.Token)
        );
    }

    [Fact]
    public void Digest_IsStableForTheSameRequestAndDiffersForAnyChange()
    {
        var request = new WorkbenchControlRequest("1.0", "v1", "reason");

        var first = WorkbenchCommandLedger.Digest("pause", "resource", request);

        Assert.Equal(first, WorkbenchCommandLedger.Digest("pause", "resource", request));
        Assert.NotEqual(first, WorkbenchCommandLedger.Digest("stop", "resource", request));
        Assert.NotEqual(first, WorkbenchCommandLedger.Digest("pause", "other", request));
        Assert.NotEqual(
            first,
            WorkbenchCommandLedger.Digest("pause", "resource", request with { Reason = "other" })
        );
    }
}

public sealed class WorkbenchCommandServiceHandoffLinkTests
{
    private sealed class FixedClock(DateTimeOffset now) : TimeProvider
    {
        public DateTimeOffset Now { get; set; } = now;

        public override DateTimeOffset GetUtcNow() => Now;
    }

    private static readonly WorkbenchContext Context = new(
        Guid.NewGuid(),
        Guid.NewGuid(),
        "customer-subject",
        Guid.NewGuid(),
        RelationshipParticipantRole.Employer,
        WorkbenchAudiences.CustomerOwner,
        Guid.NewGuid().ToString("D")
    );

    private static WorkbenchHandoffService Service(
        FixedClock clock,
        string baseUrl = "",
        int ttlSeconds = 900
    ) =>
        new(
            new InMemoryWorkbenchHandoffStore(),
            Options.Create(
                new WorkbenchOptions { HandoffBaseUrl = baseUrl, HandoffTtlSeconds = ttlSeconds }
            ),
            clock
        );

    [Theory]
    [InlineData(0, 60)]
    [InlineData(10, 60)]
    [InlineData(900, 900)]
    [InlineData(100000, 3600)]
    public async Task Create_KeepsTheLinkLifetimeBetweenOneAndSixtyMinutes(
        int configuredSeconds,
        int effectiveSeconds
    )
    {
        var clock = new FixedClock(new DateTimeOffset(2030, 1, 1, 0, 0, 0, TimeSpan.Zero));

        var handoff = await Service(clock, ttlSeconds: configuredSeconds)
            .CreateAsync(Context, "APPROVAL", "decision", CancellationToken.None);

        Assert.Equal(clock.Now.AddSeconds(effectiveSeconds), handoff.ExpiresAt);
        Assert.StartsWith("h", handoff.DestinationRef);
        Assert.True(handoff.SingleUse);
    }

    [Fact]
    public async Task TryConsume_ARedeemedLinkExpiresWithItsLifetime()
    {
        var clock = new FixedClock(new DateTimeOffset(2030, 1, 1, 0, 0, 0, TimeSpan.Zero));
        var service = Service(clock, ttlSeconds: 60);
        var handoff = await service.CreateAsync(Context, "EVIDENCE", null, CancellationToken.None);
        clock.Now = clock.Now.AddSeconds(61);

        var late = await service.TryConsumeAsync(
            handoff.DestinationRef,
            Context.TenantId,
            Context.RelationshipId,
            Context.ParticipantId,
            CancellationToken.None
        );

        Assert.Null(late);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    public async Task TryConsume_ABlankTokenIsNeverLookedUp(string token)
    {
        var service = Service(new FixedClock(DateTimeOffset.UtcNow));

        Assert.Null(
            await service.TryConsumeAsync(
                token,
                Context.TenantId,
                Context.RelationshipId,
                Context.ParticipantId,
                CancellationToken.None
            )
        );
        Assert.Null(
            await service.TryConsumeAsync(
                new string('t', 129),
                Context.TenantId,
                Context.RelationshipId,
                Context.ParticipantId,
                CancellationToken.None
            )
        );
    }

    [Theory]
    [InlineData("https://app.waooaw.test", "https://app.waooaw.test")]
    [InlineData("  https://app.waooaw.test///  ", "https://app.waooaw.test")]
    [InlineData("http://localhost:3000/", "http://localhost:3000")]
    public async Task UrlFor_BuildsTheAbsoluteWorkbenchAddressWithTheEscapedLinkToken(
        string configured,
        string expectedBase
    )
    {
        var service = Service(new FixedClock(DateTimeOffset.UtcNow), configured);
        var handoff = await service.CreateAsync(
            Context,
            "WEB_WORKBENCH",
            null,
            CancellationToken.None
        );

        var url = service.UrlFor(handoff, Context.RelationshipId);

        Assert.Equal(
            $"{expectedBase}/relationships/{Context.RelationshipId:D}?handoff={Uri.EscapeDataString(handoff.DestinationRef)}",
            url
        );
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("/relative/path")]
    [InlineData("ftp://files.waooaw.test")]
    public async Task UrlFor_IsNullWhenNoUsableWebAddressIsConfigured(string configured)
    {
        var service = Service(new FixedClock(DateTimeOffset.UtcNow), configured);
        var handoff = await service.CreateAsync(
            Context,
            "WEB_WORKBENCH",
            null,
            CancellationToken.None
        );

        Assert.Null(service.UrlFor(handoff, Context.RelationshipId));
    }
}
