// Implements: work-contracts/WC-033-goal005-bp-trial-lifecycle.md §WC033-03
// constitutional_basis: C-088 (trial billing mode lapse), C-090 (conversion), C-076 (≥90% coverage)
using System.Net;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Temporalio.Activities;
using Temporalio.Client;
using Temporalio.Testing;
using Temporalio.Worker;
using Waooaw.BusinessPlatform.Workflows;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

// ─── Activity stubs for workflow testing ──────────────────────────────────────

/// <summary>
/// In-memory activity stubs that record which activities were called.
/// Injected into the test Temporal worker instead of the real TrialExpiryActivities.
/// </summary>
internal sealed class TrackingActivities
{
    public List<(string CustomerId, string TrialId)> ReminderCalls { get; } = [];
    public List<(string CustomerId, string TrialId)> StatusChecks   { get; } = [];
    public List<(string TrialId, string CustomerId)> ExpiredCalls   { get; } = [];

    // Returned by CheckTrialStatusAsync to control the workflow lapse/convert path
    public string StatusToReturn { get; set; } = "ACTIVE";
    public string ExpiryStatusToReturn { get; set; } = "EXPIRED";

    [Activity]
    public Task SendReminderAsync(string customerId, string trialId)
    {
        ReminderCalls.Add((customerId, trialId));
        return Task.CompletedTask;
    }

    [Activity]
    public Task<string> CheckTrialStatusAsync(string customerId, string trialId)
    {
        StatusChecks.Add((customerId, trialId));
        return Task.FromResult(StatusToReturn);
    }

    [Activity]
    public Task<string> MarkExpiredAsync(string trialId, string customerId)
    {
        ExpiredCalls.Add((trialId, customerId));
        return Task.FromResult(ExpiryStatusToReturn);
    }
}

// ─── Workflow Tests ───────────────────────────────────────────────────────────

public sealed class TrialExpiryWorkflowTests
{
    private static readonly WorkflowOptions WorkflowOpts =
        new("trial-test", taskQueue: "test-q");

    private static TrialExpiryInput MakeInput(
        string? trialId = null,
        string? customerId = null,
        DateTimeOffset? expiresAt = null)
        => new(
            trialId    ?? Guid.NewGuid().ToString(),
            customerId ?? Guid.NewGuid().ToString(),
            expiresAt  ?? DateTimeOffset.UtcNow.AddDays(14));

    // ── Helper: run workflow with tracking activities ─────────────────────────

    private static async Task<(TrackingActivities Activities, TrialExpiryOutcome Outcome)> RunWorkflowAsync(
        TrialExpiryInput input,
        TrackingActivities? activities = null)
    {
        activities ??= new TrackingActivities();

        await using var env = await WorkflowEnvironment.StartTimeSkippingAsync();
        using var worker = new TemporalWorker(
            env.Client,
            new TemporalWorkerOptions("test-q")
                .AddWorkflow<TrialExpiryWorkflow>()
                .AddAllActivities(activities));

        var outcome = TrialExpiryOutcome.Unresolved;
        await worker.ExecuteAsync(async () =>
        {
            var handle = await env.Client.StartWorkflowAsync(
                (TrialExpiryWorkflow wf) => wf.RunAsync(input),
                WorkflowOpts);
            outcome = await handle.GetResultAsync();
        });

        return (activities, outcome);
    }

    // ── Test 1: 48h reminder fires before expiry ──────────────────────────────

    [Fact]
    public async Task Workflow_BeforeExpiry_SendsReminderActivity()
    {
        var trialId    = Guid.NewGuid().ToString();
        var customerId = Guid.NewGuid().ToString();
        var input      = MakeInput(trialId: trialId, customerId: customerId);

        var (activities, _) = await RunWorkflowAsync(input);

        activities.ReminderCalls.Should().ContainSingle(because: "48h reminder must fire once");
        activities.ReminderCalls[0].TrialId.Should().Be(trialId);
        activities.ReminderCalls[0].CustomerId.Should().Be(customerId);
    }

    // ── Test 2: Trial not converted at expiry → LAPSED ────────────────────────

    [Fact]
    public async Task Workflow_TrialNotConverted_MarksLapsed()
    {
        var trialId    = Guid.NewGuid().ToString();
        var customerId = Guid.NewGuid().ToString();
        var acts = new TrackingActivities { StatusToReturn = "ACTIVE" };

        var (_, outcome) = await RunWorkflowAsync(MakeInput(trialId: trialId, customerId: customerId), acts);

        acts.ExpiredCalls.Should().ContainSingle(because: "ACTIVE trial at expiry must be marked EXPIRED");
        acts.ExpiredCalls[0].TrialId.Should().Be(trialId);
        acts.ExpiredCalls[0].CustomerId.Should().Be(customerId);
        outcome.Should().Be(TrialExpiryOutcome.Expired);
    }

    // ── Test 3: Trial already converted → no LAPSED call ─────────────────────

    [Fact]
    public async Task Workflow_TrialAlreadyConverted_SkipsLapse()
    {
        var acts = new TrackingActivities { StatusToReturn = "CONVERTED" };

        var (_, outcome) = await RunWorkflowAsync(MakeInput(), acts);

        acts.ExpiredCalls.Should().BeEmpty(because: "CONVERTED is WBE billing truth, not an expiry command");
        outcome.Should().Be(TrialExpiryOutcome.BillingConverted);
    }

    // ── Test 4: Status check happens exactly once ─────────────────────────────

    [Fact]
    public async Task Workflow_ChecksStatusExactlyOnce()
    {
        var trialId = Guid.NewGuid().ToString();
        var acts    = new TrackingActivities { StatusToReturn = "ACTIVE" };

        var customerId = Guid.NewGuid().ToString();
        await RunWorkflowAsync(MakeInput(trialId: trialId, customerId: customerId), acts);

        acts.StatusChecks.Should().ContainSingle(because: "status must be checked once at expiry");
        acts.StatusChecks[0].Should().Be((customerId, trialId));
    }

    // ── Test 5: Already-expired input (expiresAt in the past) ────────────────
    // Workflow must still complete and mark LAPSED without hanging on DelayAsync.

    [Fact]
    public async Task Workflow_AlreadyExpiredTrial_CompletesAndMarksLapsed()
    {
        var input = MakeInput(expiresAt: DateTimeOffset.UtcNow.AddSeconds(-1));
        var acts  = new TrackingActivities { StatusToReturn = "ACTIVE" };

        await RunWorkflowAsync(input, acts);

        acts.ExpiredCalls.Should().ContainSingle(
            because: "already-expired input must immediately expire owner entitlement");
    }

    // ── Test 6: UNKNOWN status (WBE unreachable) → marks LAPSED ─────────────

    [Fact]
    public async Task Workflow_StatusUnknown_RemainsUnresolved()
    {
        var acts = new TrackingActivities { StatusToReturn = "UNKNOWN" };

        var (_, outcome) = await RunWorkflowAsync(MakeInput(), acts);

        acts.ExpiredCalls.Should().BeEmpty(
            because: "owner uncertainty must not be rewritten as a confirmed expiry");
        outcome.Should().Be(TrialExpiryOutcome.Unresolved);
    }

    [Fact]
    public async Task Workflow_ConversionRace_RemainsBillingOnly()
    {
        var acts = new TrackingActivities
        {
            StatusToReturn = "ACTIVE",
            ExpiryStatusToReturn = "CONVERTED",
        };

        var (_, outcome) = await RunWorkflowAsync(MakeInput(), acts);

        acts.ExpiredCalls.Should().ContainSingle();
        outcome.Should().Be(TrialExpiryOutcome.BillingConverted);
    }
}

// ─── TrialExpiryActivities Unit Tests (no Temporal server needed) ─────────────

public sealed class TrialExpiryActivitiesTests
{
    private static TrialExpiryActivities MakeActivities(StubHttpMessageHandler? wbeStub = null)
    {
        wbeStub ??= new StubHttpMessageHandler(HttpStatusCode.OK, "{}");
        var factory = new SingleClientHttpFactory("WBE",
            new HttpClient(wbeStub) { BaseAddress = new Uri("http://wbe-test") });
        return new TrialExpiryActivities(factory, NullLogger<TrialExpiryActivities>.Instance);
    }

    // ── SendReminderAsync: non-fatal on HTTP failure ──────────────────────────

    [Fact]
    public async Task SendReminder_WbeFailure_DoesNotThrow()
    {
        var wbeStub = new StubHttpMessageHandler(
            _ => throw new HttpRequestException("WBE down"));
        var acts = MakeActivities(wbeStub);

        // Must not throw — reminder failure is non-fatal
        await acts.SendReminderAsync("cust-001", "trial-001");
    }

    // ── CheckTrialStatusAsync: returns UNKNOWN on failure ────────────────────

    [Fact]
    public async Task CheckStatus_WbeFailure_ReturnsUnknown()
    {
        var wbeStub = new StubHttpMessageHandler(
            _ => throw new HttpRequestException("WBE down"));
        var acts   = MakeActivities(wbeStub);

        var status = await acts.CheckTrialStatusAsync("cust-001", "trial-001");

        status.Should().Be("UNKNOWN");
    }

    [Fact]
    public async Task CheckStatus_WbeReturns200_ReturnsStatus()
    {
        var body    = JsonSerializer.Serialize(new { trial_id = "trial-001", status = "ACTIVE" });
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.OK, body);
        var acts    = MakeActivities(wbeStub);

        var status = await acts.CheckTrialStatusAsync("cust-001", "trial-001");

        status.Should().Be("ACTIVE");
    }

    [Fact]
    public async Task CheckStatus_WbeReturnsNon200_ReturnsUnknown()
    {
        var wbeStub = new StubHttpMessageHandler(HttpStatusCode.ServiceUnavailable, "{}");
        var acts    = MakeActivities(wbeStub);

        var status = await acts.CheckTrialStatusAsync("cust-001", "trial-001");

        status.Should().Be("UNKNOWN");
    }

    // ── MarkLapsedAsync: throws on WBE HTTP failure (Temporal retries) ────────

    [Fact]
    public async Task MarkLapsed_WbeFailure_Throws()
    {
        var wbeStub = new StubHttpMessageHandler(
            _ => throw new HttpRequestException("WBE down"));
        var acts = MakeActivities(wbeStub);

        await Assert.ThrowsAsync<HttpRequestException>(
            () => acts.MarkExpiredAsync("trial-001", "cust-001"));
    }

    [Fact]
    public async Task MarkLapsed_WbeReturns200_Completes()
    {
        var callCount = 0;
        var wbeStub = new StubHttpMessageHandler(_ =>
        {
            callCount++;
            return new HttpResponseMessage(HttpStatusCode.OK)
            {
                Content = new StringContent(
                    JsonSerializer.Serialize(new { trial_id = "trial-001", status = "EXPIRED" }),
                    Encoding.UTF8,
                    "application/json"),
            };
        });
        var acts = MakeActivities(wbeStub);

        await acts.MarkExpiredAsync("trial-001", "cust-001");

        callCount.Should().BeGreaterOrEqualTo(1,
            because: "WBE /trial/convert and notification must be called");
    }
}

// ─── IHttpClientFactory stub for activity unit tests ─────────────────────────

internal sealed class SingleClientHttpFactory : IHttpClientFactory
{
    private readonly string     _name;
    private readonly HttpClient _client;

    public SingleClientHttpFactory(string name, HttpClient client)
    {
        _name   = name;
        _client = client;
    }

    public HttpClient CreateClient(string name)
        => name == _name ? _client : throw new InvalidOperationException($"Unknown client: {name}");
}
