// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-08
// constitutional_basis: C-023, C-059, C-063, C-076, ADR-051
using System.Net;
using System.Reflection;
using System.Text;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ComponentUnitGatewayCoverageTests(OwnerGatewayIdentityFixture fixture)
    : IClassFixture<OwnerGatewayIdentityFixture>
{
    private static readonly Guid Evidence = Guid.Parse("5d6c0f7e-9b1a-4c34-8f67-2a1e3b4c5d6e");

    private static ComponentUnitCompletion Completion() =>
        new(Guid.NewGuid(), Guid.NewGuid(), "lead_batch", Evidence, "bp-component-unit");

    private static HttpResponseMessage Json(HttpStatusCode status, string body) =>
        new(status) { Content = new StringContent(body, Encoding.UTF8, "application/json") };

    private AuthenticatedComponentUnitGateway Gateway(
        Func<HttpRequestMessage, HttpResponseMessage> send
    )
    {
        var identity = fixture.CreateIdentity();
        var gateway = new AuthenticatedComponentUnitGateway(
            identity,
            new Uri("https://billing.test")
        );
        var field = typeof(AuthenticatedComponentUnitGateway).GetField(
            "_client",
            BindingFlags.Instance | BindingFlags.NonPublic
        )!;
        ((HttpClient)field.GetValue(gateway)!).Dispose();
        field.SetValue(
            gateway,
            new HttpClient(new StubHandler(send)) { BaseAddress = new Uri("https://owner.test") }
        );
        return gateway;
    }

    [Fact]
    public void The_noop_sink_accepts_a_completion_and_keeps_nothing()
    {
        Assert.Null(
            Record.Exception(() => new NoopComponentUnitCompletionSink().Completed(Completion()))
        );
    }

    [Theory]
    [InlineData("not json")]
    [InlineData("{}")]
    [InlineData("""{"detail":7}""")]
    [InlineData("""{"detail":""}""")]
    public async Task A_refusal_without_a_readable_code_is_reported_as_a_generic_refusal(
        string body
    )
    {
        using var gateway = Gateway(_ => Json(HttpStatusCode.UnprocessableEntity, body));

        var refusal = await Assert.ThrowsAsync<ComponentUnitRefusedException>(() =>
            gateway.ConsumeAsync(Completion(), CancellationToken.None)
        );

        Assert.Equal("COMPONENT_UNIT_REFUSED", refusal.Code);
    }

    public static TheoryData<string> UnresolvedAnswers =>
        new()
        {
            "transport",
            "cancelled",
            "not json",
            "{}",
            """{"componentId":"lead_batch","quantity":"many","used":1,"remaining":2,"released":3,"replayed":false}""",
            """{"componentId":"lead_batch","quantity":1,"used":1,"remaining":2,"released":3,"replayed":"yes"}""",
        };

    [Theory]
    [MemberData(nameof(UnresolvedAnswers))]
    public async Task An_answer_that_cannot_be_read_leaves_the_outcome_unresolved(string answer)
    {
        using var gateway = Gateway(_ =>
            answer switch
            {
                "transport" => throw new HttpRequestException("connection reset"),
                "cancelled" => throw new TaskCanceledException("timeout"),
                _ => Json(HttpStatusCode.OK, answer),
            }
        );

        var failure = await Assert.ThrowsAsync<ComponentUnitOwnerUnavailableException>(() =>
            gateway.ConsumeAsync(Completion(), CancellationToken.None)
        );

        Assert.Equal("The component-unit outcome is unresolved.", failure.Message);
        Assert.NotNull(failure.InnerException);
    }

    [Fact]
    public async Task A_receipt_without_a_component_name_keeps_the_completions_component()
    {
        using var gateway = Gateway(_ =>
            Json(
                HttpStatusCode.OK,
                """{"componentId":null,"quantity":30,"used":1,"remaining":29,"released":10,"replayed":true}"""
            )
        );

        var receipt = await gateway.ConsumeAsync(Completion(), CancellationToken.None);

        Assert.Equal(new ComponentUnitReceipt("lead_batch", 30, 1, 29, 10, true), receipt);
    }

    [Fact]
    public async Task The_in_memory_outbox_ignores_marks_for_unknown_or_unleased_rows()
    {
        var clock = new FixedClock(PricingAdminFixtures.Now);
        var outbox = new InMemoryComponentUnitOutbox(clock);
        outbox.Completed(Completion());

        await outbox.DeliveredAsync(Guid.NewGuid(), CancellationToken.None);
        var work = Assert.Single(await outbox.ClaimAsync(5, TimeSpan.FromMinutes(1), default));
        await outbox.DeliveredAsync(work.OutboxId, CancellationToken.None);
        await outbox.RefusedAsync(work.OutboxId, "LATE", CancellationToken.None);
        await outbox.RetryAsync(work.OutboxId, TimeSpan.Zero, "LATE", CancellationToken.None);

        Assert.Equal(("DELIVERED", 0), (outbox.Snapshot()[0].State, outbox.Snapshot()[0].Attempt));
    }

    [Fact]
    public async Task The_in_memory_outbox_honours_the_retry_delay_and_reclaims_an_expired_lease()
    {
        var clock = new FixedClock(PricingAdminFixtures.Now);
        var outbox = new InMemoryComponentUnitOutbox(clock);
        outbox.Completed(Completion());
        var first = Assert.Single(await outbox.ClaimAsync(5, TimeSpan.FromMinutes(1), default));

        await outbox.RetryAsync(first.OutboxId, TimeSpan.FromMinutes(10), "SLOW", default);

        Assert.Empty(await outbox.ClaimAsync(5, TimeSpan.FromMinutes(1), default));
        clock.Now = clock.Now.AddMinutes(11);
        var second = Assert.Single(await outbox.ClaimAsync(5, TimeSpan.FromMinutes(1), default));
        Assert.Equal((first.OutboxId, 1), (second.OutboxId, second.Attempt));
        Assert.Empty(await outbox.ClaimAsync(5, TimeSpan.FromMinutes(1), default));
        clock.Now = clock.Now.AddMinutes(2);
        Assert.Single(await outbox.ClaimAsync(5, TimeSpan.FromMinutes(1), default));
    }

    [Fact]
    public async Task A_worker_without_configured_delays_retries_after_the_first_default_delay()
    {
        var clock = new FixedClock(PricingAdminFixtures.Now);
        var outbox = new InMemoryComponentUnitOutbox(clock);
        var gateway = new FailingGateway(new ComponentUnitOwnerUnavailableException("down"));
        var worker = new ComponentUnitCompletionWorker(
            outbox,
            gateway,
            NullLogger<ComponentUnitCompletionWorker>.Instance,
            clock
        );
        outbox.Completed(Completion());

        Assert.Equal(1, await worker.DrainOnceAsync(CancellationToken.None));
        Assert.Equal(0, await worker.DrainOnceAsync(CancellationToken.None));
        clock.Now += ComponentUnitCompletionWorker.DefaultRetryDelays[0];
        Assert.Equal(1, await worker.DrainOnceAsync(CancellationToken.None));

        Assert.Equal(("DELIVERED", 1), (outbox.Snapshot()[0].State, outbox.Snapshot()[0].Attempt));
    }

    [Fact]
    public async Task A_failing_outbox_does_not_stop_the_drain()
    {
        var outbox = new FlakyOutbox();
        var worker = new ComponentUnitCompletionWorker(
            outbox,
            new FailingGateway(),
            NullLogger<ComponentUnitCompletionWorker>.Instance,
            TimeProvider.System
        );

        Assert.Equal(0, await worker.DrainOnceAsync(CancellationToken.None));
        outbox.FailClaim = false;
        outbox.Pending.Add(new ComponentUnitWork(Guid.NewGuid(), Completion(), 0));
        Assert.Equal(1, await worker.DrainOnceAsync(CancellationToken.None));
        Assert.Equal(1, outbox.MarkAttempts);
    }

    [Fact]
    public async Task The_background_loop_delivers_work_and_stops_cleanly()
    {
        var outbox = new InMemoryComponentUnitOutbox();
        var gateway = new FailingGateway();
        using var worker = new ComponentUnitCompletionWorker(
            outbox,
            gateway,
            NullLogger<ComponentUnitCompletionWorker>.Instance,
            TimeProvider.System,
            null,
            TimeSpan.FromMilliseconds(20)
        );
        await worker.StartAsync(CancellationToken.None);
        outbox.Completed(Completion());

        var deadline = DateTime.UtcNow.AddSeconds(10);
        while (outbox.Snapshot().Any(row => row.State != "DELIVERED") && DateTime.UtcNow < deadline)
            await Task.Delay(20);
        await worker.StopAsync(CancellationToken.None);

        Assert.Equal("DELIVERED", Assert.Single(outbox.Snapshot()).State);
        Assert.Equal(1, gateway.Calls);
    }

    private sealed class FailingGateway(params Exception[] failures) : IComponentUnitGateway
    {
        public int Calls { get; private set; }

        public Task<ComponentUnitReceipt> ConsumeAsync(
            ComponentUnitCompletion completion,
            CancellationToken ct
        )
        {
            var index = Calls++;
            if (index < failures.Length)
                throw failures[index];
            return Task.FromResult(
                new ComponentUnitReceipt(completion.ComponentId, 30, 1, 29, 10, false)
            );
        }
    }

    private sealed class FlakyOutbox : IComponentUnitOutbox
    {
        public bool FailClaim { get; set; } = true;
        public List<ComponentUnitWork> Pending { get; } = [];
        public int MarkAttempts { get; private set; }

        public void Completed(ComponentUnitCompletion completion) { }

        public Task<IReadOnlyList<ComponentUnitWork>> ClaimAsync(
            int limit,
            TimeSpan lease,
            CancellationToken ct
        ) =>
            FailClaim
                ? throw new InvalidOperationException("storage down")
                : Task.FromResult<IReadOnlyList<ComponentUnitWork>>(Pending.ToList());

        public Task DeliveredAsync(Guid outboxId, CancellationToken ct)
        {
            MarkAttempts++;
            throw new InvalidOperationException("storage down");
        }

        public Task RefusedAsync(Guid outboxId, string code, CancellationToken ct) =>
            Task.CompletedTask;

        public Task RetryAsync(Guid outboxId, TimeSpan delay, string code, CancellationToken ct) =>
            Task.CompletedTask;

        public Task UnresolvedAsync(Guid outboxId, string code, CancellationToken ct) =>
            Task.CompletedTask;
    }

    private sealed class StubHandler(Func<HttpRequestMessage, HttpResponseMessage> send)
        : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken
        ) => Task.FromResult(send(request));
    }
}
