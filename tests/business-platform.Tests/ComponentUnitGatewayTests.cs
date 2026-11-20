// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
// constitutional_basis: C-023, C-059, C-063, C-076, ADR-051
using System.Net;
using System.Reflection;
using System.Text;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ComponentUnitGatewayTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    private static readonly Guid Evidence = Guid.Parse("5d6c0f7e-9b1a-4c34-8f67-2a1e3b4c5d6e");

    private static ComponentUnitCompletion Completion(Guid? relationship = null) =>
        new(
            Guid.NewGuid(),
            relationship ?? Guid.NewGuid(),
            "lead_batch",
            Evidence,
            "bp-component-unit"
        );

    [Fact]
    public async Task ConsumePostsTheSortedBodyWithASignedEnvelopeAndADerivedKey()
    {
        var relationship = Guid.NewGuid();
        HttpRequestMessage? seen = null;
        string? body = null;
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedComponentUnitGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(
            gateway,
            (request, _) =>
            {
                seen = request;
                body = request.Content!.ReadAsStringAsync().GetAwaiter().GetResult();
                return Json(
                    HttpStatusCode.OK,
                    """
                    {"schemaVersion":"1.0","componentId":"lead_batch","kind":"COUNTED","entryId":"5d6c0f7e-9b1a-4c34-8f67-2a1e3b4c5d6e","quantity":30,"used":1,"remaining":29,"released":10,"replayed":false}
                    """
                );
            }
        );

        var receipt = await gateway.ConsumeAsync(Completion(relationship), CancellationToken.None);

        Assert.Equal(29, receipt.Remaining);
        Assert.False(receipt.Replayed);
        Assert.Equal(
            $"/internal/v1/relationships/{relationship:D}/component-units/consume",
            seen!.RequestUri!.AbsolutePath
        );
        Assert.StartsWith("Bearer ", seen.Headers.Authorization?.ToString());
        Assert.Equal(
            $$"""{"action":"CONSUME","completionEvidenceId":"{{Evidence:D}}","componentId":"lead_batch","outcome":"COMPLETED","schemaVersion":"1.0"}""",
            body
        );
        Assert.Equal(
            ComponentUnitEvidence
                .IdempotencyKey(relationship, "lead_batch", Evidence)
                .ToString("D"),
            seen.Headers.GetValues("Idempotency-Key").Single()
        );
    }

    [Theory]
    [InlineData(HttpStatusCode.Conflict, "COMPONENT_IDEMPOTENCY_CONFLICT")]
    [InlineData(HttpStatusCode.UnprocessableEntity, "COMPONENT_NOT_YET_RELEASED")]
    public async Task OwnerRefusalsKeepTheirCode(HttpStatusCode status, string code)
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedComponentUnitGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(gateway, (_, _) => Json(status, $$"""{"detail":"{{code}}"}"""));

        var refusal = await Assert.ThrowsAsync<ComponentUnitRefusedException>(() =>
            gateway.ConsumeAsync(Completion(), CancellationToken.None)
        );

        Assert.Equal(code, refusal.Code);
    }

    [Fact]
    public async Task AnUnavailableOwnerIsAnUnresolvedOutcome()
    {
        using var identity = fixture.CreateIdentity();
        using var gateway = new AuthenticatedComponentUnitGateway(
            identity,
            new Uri("https://billing.test")
        );
        ReplaceClient(gateway, (_, _) => Json(HttpStatusCode.BadGateway, "{}"));

        await Assert.ThrowsAsync<ComponentUnitOwnerUnavailableException>(() =>
            gateway.ConsumeAsync(Completion(), CancellationToken.None)
        );
    }

    [Theory]
    [InlineData("component-unit:lead_batch:5d6c0f7e-9b1a-4c34-8f67-2a1e3b4c5d6e", true)]
    [InlineData("component-unit::5d6c0f7e-9b1a-4c34-8f67-2a1e3b4c5d6e", false)]
    [InlineData("component-unit:lead_batch:not-a-guid", false)]
    [InlineData("component-unit:lead_batch:00000000-0000-0000-0000-000000000000", false)]
    [InlineData("evidence:CE", false)]
    [InlineData(null, false)]
    public void OnlyTheDeclaredEvidenceShapeNamesAComponent(string? evidenceRef, bool valid)
    {
        Assert.Equal(
            valid,
            ComponentUnitEvidence.TryParse(evidenceRef, out var component, out var id)
        );
        Assert.Equal(valid ? "lead_batch" : string.Empty, component);
        Assert.Equal(valid ? Evidence : Guid.Empty, id);
    }

    [Fact]
    public void TheIdempotencyKeyIsStableAndScopedToTheRelationship()
    {
        var relationship = Guid.NewGuid();

        Assert.Equal(
            ComponentUnitEvidence.IdempotencyKey(relationship, "lead_batch", Evidence),
            ComponentUnitEvidence.IdempotencyKey(relationship, "lead_batch", Evidence)
        );
        Assert.NotEqual(
            ComponentUnitEvidence.IdempotencyKey(relationship, "lead_batch", Evidence),
            ComponentUnitEvidence.IdempotencyKey(Guid.NewGuid(), "lead_batch", Evidence)
        );
    }

    private static ComponentUnitCompletionWorker Worker(
        IComponentUnitOutbox outbox,
        IComponentUnitGateway gateway,
        params TimeSpan[] delays
    ) =>
        new(
            outbox,
            gateway,
            NullLogger<ComponentUnitCompletionWorker>.Instance,
            TimeProvider.System,
            delays
        );

    [Fact]
    public async Task TheWorkerRetriesAnUnresolvedOutcomeAndThenSucceeds()
    {
        var outbox = new InMemoryComponentUnitOutbox();
        var gateway = new ScriptedGateway(
            new ComponentUnitOwnerUnavailableException("down"),
            new ComponentUnitOwnerUnavailableException("down")
        );
        var worker = Worker(outbox, gateway, TimeSpan.Zero, TimeSpan.Zero, TimeSpan.Zero);
        outbox.Completed(Completion());

        for (var drain = 0; drain < 3; drain++)
            Assert.Equal(1, await worker.DrainOnceAsync(CancellationToken.None));

        Assert.Equal(3, gateway.Attempts);
        var row = Assert.Single(outbox.Snapshot());
        Assert.Equal(("DELIVERED", 2), (row.State, row.Attempt));
        Assert.Equal(0, await worker.DrainOnceAsync(CancellationToken.None));
    }

    [Fact]
    public async Task TheWorkerMarksTheRowUnresolvedAfterTheLastRetryWithoutThrowing()
    {
        var outbox = new InMemoryComponentUnitOutbox();
        var gateway = new ScriptedGateway(
            Enumerable
                .Repeat<Exception>(new ComponentUnitOwnerUnavailableException("down"), 10)
                .ToArray()
        );
        var worker = Worker(outbox, gateway, TimeSpan.Zero, TimeSpan.Zero);
        outbox.Completed(Completion());

        for (var drain = 0; drain < 4; drain++)
            await worker.DrainOnceAsync(CancellationToken.None);

        Assert.Equal(3, gateway.Attempts);
        var row = Assert.Single(outbox.Snapshot());
        Assert.Equal(("UNRESOLVED", 2), (row.State, row.Attempt));
    }

    [Fact]
    public async Task ARefusalIsFinalAndIsNotRetried()
    {
        var outbox = new InMemoryComponentUnitOutbox();
        var gateway = new ScriptedGateway(
            new ComponentUnitRefusedException("COMPONENT_NOT_YET_RELEASED")
        );
        var worker = Worker(outbox, gateway, TimeSpan.Zero, TimeSpan.Zero);
        outbox.Completed(Completion());

        await worker.DrainOnceAsync(CancellationToken.None);
        await worker.DrainOnceAsync(CancellationToken.None);

        Assert.Equal(1, gateway.Attempts);
        Assert.Equal("REFUSED", Assert.Single(outbox.Snapshot()).State);
    }

    [Fact]
    public void TheSameCompletionIsRecordedOnceAndASecondEnqueueIsIgnored()
    {
        var outbox = new InMemoryComponentUnitOutbox();
        var completion = Completion();

        outbox.Completed(completion);
        outbox.Completed(completion);
        outbox.Completed(completion with { ActorSubject = "someone-else" });

        Assert.Single(outbox.Snapshot());
    }

    [Fact]
    public async Task AClaimedRowWhoseLeaseExpiresIsClaimedAgainAfterACrash()
    {
        var clock = new ManualClock();
        var outbox = new InMemoryComponentUnitOutbox(clock);
        outbox.Completed(Completion());
        var lease = TimeSpan.FromMinutes(5);

        var first = await outbox.ClaimAsync(10, lease, CancellationToken.None);
        var during = await outbox.ClaimAsync(10, lease, CancellationToken.None);
        clock.Advance(lease + TimeSpan.FromSeconds(1));
        var recovered = await outbox.ClaimAsync(10, lease, CancellationToken.None);

        Assert.Single(first);
        Assert.Empty(during);
        Assert.Equal(first[0].OutboxId, Assert.Single(recovered).OutboxId);
    }

    [Fact]
    public async Task ARetryIsNotClaimedBeforeItsDelayHasElapsed()
    {
        var clock = new ManualClock();
        var outbox = new InMemoryComponentUnitOutbox(clock);
        outbox.Completed(Completion());
        var claimed = Assert.Single(
            await outbox.ClaimAsync(10, TimeSpan.FromMinutes(5), CancellationToken.None)
        );

        await outbox.RetryAsync(
            claimed.OutboxId,
            TimeSpan.FromSeconds(10),
            "OWNER_UNAVAILABLE",
            CancellationToken.None
        );

        Assert.Empty(await outbox.ClaimAsync(10, TimeSpan.FromMinutes(5), CancellationToken.None));
        clock.Advance(TimeSpan.FromSeconds(11));
        var again = Assert.Single(
            await outbox.ClaimAsync(10, TimeSpan.FromMinutes(5), CancellationToken.None)
        );
        Assert.Equal(1, again.Attempt);
    }

    [Fact]
    public async Task AStorageFailureWhileClaimingIsLoggedAndTheWorkerKeepsRunning()
    {
        var worker = Worker(new FailingOutbox(), new ScriptedGateway(), TimeSpan.Zero);

        Assert.Equal(0, await worker.DrainOnceAsync(CancellationToken.None));
    }

    [Fact]
    public async Task AFailureMarkingADeliveredRowLeavesItLeasedForARedeliveryAndDoesNotStopTheBatch()
    {
        var outbox = new MarkFailingOutbox();
        outbox.Completed(Completion());
        outbox.Completed(Completion());
        var gateway = new ScriptedGateway();
        var worker = Worker(outbox, gateway, TimeSpan.Zero);

        Assert.Equal(2, await worker.DrainOnceAsync(CancellationToken.None));

        Assert.Equal(2, gateway.Attempts);
    }

    private sealed class ManualClock : TimeProvider
    {
        private DateTimeOffset _now = new(2026, 5, 1, 0, 0, 0, TimeSpan.Zero);

        public override DateTimeOffset GetUtcNow() => _now;

        public void Advance(TimeSpan by) => _now += by;
    }

    private sealed class FailingOutbox : IComponentUnitOutbox
    {
        public void Completed(ComponentUnitCompletion completion) { }

        public Task<IReadOnlyList<ComponentUnitWork>> ClaimAsync(
            int limit,
            TimeSpan lease,
            CancellationToken ct
        ) => throw new InvalidOperationException("database unavailable");

        public Task DeliveredAsync(Guid outboxId, CancellationToken ct) => Task.CompletedTask;

        public Task RefusedAsync(Guid outboxId, string code, CancellationToken ct) =>
            Task.CompletedTask;

        public Task RetryAsync(Guid outboxId, TimeSpan delay, string code, CancellationToken ct) =>
            Task.CompletedTask;

        public Task UnresolvedAsync(Guid outboxId, string code, CancellationToken ct) =>
            Task.CompletedTask;
    }

    private sealed class MarkFailingOutbox : IComponentUnitOutbox
    {
        private readonly InMemoryComponentUnitOutbox _inner = new();

        public void Completed(ComponentUnitCompletion completion) => _inner.Completed(completion);

        public Task<IReadOnlyList<ComponentUnitWork>> ClaimAsync(
            int limit,
            TimeSpan lease,
            CancellationToken ct
        ) => _inner.ClaimAsync(limit, lease, ct);

        public Task DeliveredAsync(Guid outboxId, CancellationToken ct) =>
            throw new InvalidOperationException("database unavailable");

        public Task RefusedAsync(Guid outboxId, string code, CancellationToken ct) =>
            Task.CompletedTask;

        public Task RetryAsync(Guid outboxId, TimeSpan delay, string code, CancellationToken ct) =>
            Task.CompletedTask;

        public Task UnresolvedAsync(Guid outboxId, string code, CancellationToken ct) =>
            Task.CompletedTask;
    }

    [Fact]
    public async Task TheUnconfiguredGatewayFailsClosed()
    {
        await Assert.ThrowsAsync<ComponentUnitOwnerUnavailableException>(() =>
            new UnconfiguredComponentUnitGateway().ConsumeAsync(
                Completion(),
                CancellationToken.None
            )
        );
    }

    private sealed class ScriptedGateway(params Exception[] failures) : IComponentUnitGateway
    {
        public int Attempts { get; private set; }

        public Task<ComponentUnitReceipt> ConsumeAsync(
            ComponentUnitCompletion completion,
            CancellationToken ct
        )
        {
            var index = Attempts++;
            if (index < failures.Length)
                throw failures[index];
            return Task.FromResult(
                new ComponentUnitReceipt(completion.ComponentId, 30, 1, 29, 10, false)
            );
        }
    }

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private static void ReplaceClient(
        object target,
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> send
    )
    {
        var field =
            target.GetType().GetField("_client", BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new InvalidOperationException("Missing field _client");
        var original = Assert.IsType<HttpClient>(field.GetValue(target));
        field.SetValue(
            target,
            new HttpClient(new StubHandler(send)) { BaseAddress = new Uri("https://owner.test") }
        );
        original.Dispose();
    }

    private sealed class StubHandler(
        Func<HttpRequestMessage, CancellationToken, HttpResponseMessage> send
    ) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(send(request, cancellationToken));
    }
}
