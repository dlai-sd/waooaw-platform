// Implements: architecture/reference/components/constitutional-engine.md §4
// constitutional_basis: C-001 (Emergency Stop ≤250ms), C-024 (architectural floor), C-076 (test coverage), C-082 (build validation)
using System.Diagnostics;
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Temporalio.Client;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.EmergencyStop;

public sealed class CCT_HO01_EmergencyStopLatencyTests
{
    // ── Factory helpers ──────────────────────────────────────────────────────

    private static EmergencyStopDbContext CreateEmergencyDb() =>
        new EmergencyStopDbContext(
            new DbContextOptionsBuilder<EmergencyStopDbContext>()
                .UseInMemoryDatabase(Guid.NewGuid().ToString())
                .Options);

    private static ConstitutionalDbContext CreateConstitutionalDb() =>
        new ConstitutionalDbContext(
            new DbContextOptionsBuilder<ConstitutionalDbContext>()
                .UseInMemoryDatabase(Guid.NewGuid().ToString())
                .Options);

    private static ITemporalClient MockedTemporalClient()
    {
    private static ConstitutionalEngineService CreateSut(
        EmergencyStopDbContext emergencyDb,
        ITemporalClient? temporalClient = null)
    {
        var registry = new EvaluatorRegistry(
            Array.Empty<IClaimEvaluator>(),
            NullLogger<EvaluatorRegistry>.Instance);

        return new ConstitutionalEngineService(
            CreateConstitutionalDb(),
            NullLogger<ConstitutionalEngineService>.Instance,
            registry,
            emergencyDb ?? new EmergencyStopDbContext(),
            temporalClient);
    }

    private static EmergencyStopRequest MakeRequest(
        string contractId = "contract-001",
        string stoppedBy = "user-admin",
        params string[] sessionIds)
    {
        var req = new EmergencyStopRequest
        {
            ContractId = contractId,
            StoppedBy = stoppedBy
        };


        req.ActiveSessionIds.AddRange(sessionIds);

        return req;
    }

    // ── CCT-HO-01: Latency gate (≤250ms P99) ────────────────────────────────

    [Fact]
    public async Task TriggerEmergencyStop_SingleSession_CompletesWithin250ms()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-abc", "operator-1", "session-A");
        var ctx = FakeServerCallContext.Create("tenant-001");

        var sw = Stopwatch.StartNew();
        await sut.TriggerEmergencyStop(req, ctx);
        sw.Stop();

        sw.Elapsed.TotalMilliseconds.Should().BeLessOrEqualTo(250,
            "C-001 mandates Emergency Stop completes within 250 ms P99");
    }

    [Fact]
    public async Task TriggerEmergencyStop_MultipleSessions_CompletesWithin250ms()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-multi", "operator-2",
            "sess-1", "sess-2", "sess-3", "sess-4", "sess-5");
        var ctx = FakeServerCallContext.Create("tenant-002");

        var sw = Stopwatch.StartNew();
        await sut.TriggerEmergencyStop(req, ctx);
        sw.Stop();

        sw.Elapsed.TotalMilliseconds.Should().BeLessOrEqualTo(250,
            "C-001 mandates Emergency Stop completes within 250 ms regardless of session count");
    }

    [Fact]
    public async Task TriggerEmergencyStop_NoSessions_CompletesWithin250ms()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-empty", "operator-3");
        var ctx = FakeServerCallContext.Create("tenant-003");

        var sw = Stopwatch.StartNew();
        await sut.TriggerEmergencyStop(req, ctx);
        sw.Stop();

        sw.Elapsed.TotalMilliseconds.Should().BeLessOrEqualTo(250,
            "C-001 mandates Emergency Stop completes within 250 ms even with zero sessions");
    }

    [Fact]
    public async Task TriggerEmergencyStop_NullTemporalClient_CompletesWithin250ms()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, temporalClient: null);
        var req = MakeRequest("contract-no-temporal", "operator-4", "sess-X");
        var ctx = FakeServerCallContext.Create("tenant-004");

        var sw = Stopwatch.StartNew();
        await sut.TriggerEmergencyStop(req, ctx);
        sw.Stop();

        sw.Elapsed.TotalMilliseconds.Should().BeLessOrEqualTo(250,
            "C-001 mandates ≤250ms even when Temporal client is absent");
    }

    [Fact]
    public async Task TriggerEmergencyStop_RepeatedCalls_EachCompletesWithin250ms()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var ctx = FakeServerCallContext.Create("tenant-005");

        for (var i = 0; i < 5; i++)
        {
            var req = MakeRequest($"contract-repeat-{i}", $"operator-{i}", $"sess-{i}");
            var sw = Stopwatch.StartNew();
            await sut.TriggerEmergencyStop(req, ctx);
            sw.Stop();

            sw.Elapsed.TotalMilliseconds.Should().BeLessOrEqualTo(250,
                $"C-001: call #{i + 1} must complete within 250 ms");
        }
    }

    // ── Response shape correctness ───────────────────────────────────────────

    [Fact]
    public async Task TriggerEmergencyStop_Response_HasNonEmptyEmergencyStopRecordId()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-id-check", "operator-5", "sess-Y");
        var ctx = FakeServerCallContext.Create("tenant-006");

        var response = await sut.TriggerEmergencyStop(req, ctx);

        response.EmergencyStopRecordId.Should().NotBeNullOrWhiteSpace(
            "the response must carry a traceable stop record ID (C-059)");
    }

    [Fact]
    public async Task TriggerEmergencyStop_Response_AffectedSessionsMatchesRequest()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var sessions = new[] { "sess-alpha", "sess-beta", "sess-gamma" };
        var req = MakeRequest("contract-sessions", "operator-6", sessions);
        var ctx = FakeServerCallContext.Create("tenant-007");

        var response = await sut.TriggerEmergencyStop(req, ctx);

        response.AffectedSessions.Should().BeEquivalentTo(sessions,
            "all active session IDs in the request must appear in AffectedSessions");
    }

    [Fact]
    public async Task TriggerEmergencyStop_NoSessions_Response_AffectedSessionsIsEmpty()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-zero-sess", "operator-7");
        var ctx = FakeServerCallContext.Create("tenant-008");

        var response = await sut.TriggerEmergencyStop(req, ctx);

        response.AffectedSessions.Should().BeEmpty(
            "no sessions in request means no affected sessions in response");
    }

    // ── Persistence assertions ───────────────────────────────────────────────

    [Fact]
    public async Task TriggerEmergencyStop_PersistsExactlyOneEvent()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-persist", "operator-8", "sess-P");
        var ctx = FakeServerCallContext.Create("tenant-009");

        await sut.TriggerEmergencyStop(req, ctx);

        var count = await emergencyDb.EmergencyStopEvents.CountAsync();
        count.Should().Be(1, "exactly one EmergencyStopEvent must be persisted per call");
    }

    [Fact]
    public async Task TriggerEmergencyStop_PersistedEvent_HasCorrectContractId()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var contractId = Guid.NewGuid().ToString();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest(contractId, "operator-9", "sess-Q");
        var ctx = FakeServerCallContext.Create("tenant-010");

        await sut.TriggerEmergencyStop(req, ctx);

        var evt = await emergencyDb.EmergencyStopEvents.SingleAsync();
        evt.ContractId.Should().Be(Guid.Parse(contractId),
            "the persisted event ContractId must match the request ContractId");
    }

    [Fact]
    public async Task TriggerEmergencyStop_PersistedEvent_HasNonDefaultId()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-id-default", "operator-10", "sess-R");
        var ctx = FakeServerCallContext.Create("tenant-011");

        await sut.TriggerEmergencyStop(req, ctx);

        var evt = await emergencyDb.EmergencyStopEvents.SingleAsync();
        evt.Id.Should().NotBe(Guid.Empty, "persisted event must have a generated non-empty ID");
    }

    [Fact]
    public async Task TriggerEmergencyStop_PersistedEvent_TriggeredAtIsApproximatelyNow()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-time", "operator-11", "sess-S");
        var ctx = FakeServerCallContext.Create("tenant-012");

        var before = DateTimeOffset.UtcNow.AddSeconds(-2);
        await sut.TriggerEmergencyStop(req, ctx);
        var after = DateTimeOffset.UtcNow.AddSeconds(2);

        var evt = await emergencyDb.EmergencyStopEvents.SingleAsync();
        evt.TriggeredAt.Should().BeAfter(before).And.BeBefore(after,
            "TriggeredAt must be set to approximately UtcNow at time of call");
    }

    [Fact]
    public async Task TriggerEmergencyStop_PersistedEvent_AffectedSessionIdsMatchRequest()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var sessions = new[] { "sess-X1", "sess-X2" };
        var req = MakeRequest("contract-aff-sess", "operator-12", sessions);
        var ctx = FakeServerCallContext.Create("tenant-013");

        await sut.TriggerEmergencyStop(req, ctx);

        var evt = await emergencyDb.EmergencyStopEvents.SingleAsync();
        evt.AffectedSessionIds.Should().BeEquivalentTo(sessions,
            "persisted AffectedSessionIds must mirror the request's ActiveSessionIds");
    }

    [Fact]
    public async Task TriggerEmergencyStop_CalledTwice_PersistsTwoDistinctEvents()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var ctx = FakeServerCallContext.Create("tenant-014");

        await sut.TriggerEmergencyStop(MakeRequest("c-tw-1", "op-a", "sess-1"), ctx);
        await sut.TriggerEmergencyStop(MakeRequest("c-tw-2", "op-b", "sess-2"), ctx);

        var events = await emergencyDb.EmergencyStopEvents.ToListAsync();
        events.Should().HaveCount(2, "two distinct stop requests must produce two persisted events");
        events.Select(e => e.Id).Distinct().Should().HaveCount(2,
            "each persisted event must have a unique ID");
    }

    // ── Latency: large payload ───────────────────────────────────────────────

    [Fact]
    public async Task TriggerEmergencyStop_LargeSessionList_CompletesWithin250ms()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var sessions = Enumerable.Range(1, 50).Select(i => $"session-{i:D4}").ToArray();
        var req = MakeRequest("contract-large", "operator-large", sessions);
        var ctx = FakeServerCallContext.Create("tenant-015");

        var sw = Stopwatch.StartNew();
        await sut.TriggerEmergencyStop(req, ctx);
        sw.Stop();

        sw.Elapsed.TotalMilliseconds.Should().BeLessOrEqualTo(250,
            "C-001 ≤250ms must hold even with 50 affected sessions");
    }

    // ── Cancellation safety ──────────────────────────────────────────────────

    [Fact]
    public async Task TriggerEmergencyStop_DefaultCancellationToken_CompletesSuccessfully()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-ct", "operator-ct", "sess-CT");
        var ctx = FakeServerCallContext.Create("tenant-016");

        var act = async () => await sut.TriggerEmergencyStop(req, ctx);

        await act.Should().NotThrowAsync(
            "TriggerEmergencyStop must complete without exception on a default CancellationToken");
    }

    // ── Response record ID traceability (C-059) ──────────────────────────────

    [Fact]
    public async Task TriggerEmergencyStop_ResponseRecordId_MatchesPersistedEventId()
    {
        await using var emergencyDb = CreateEmergencyDb();
        var sut = CreateSut(emergencyDb, MockedTemporalClient());
        var req = MakeRequest("contract-trace", "operator-trace", "sess-T1");
        var ctx = FakeServerCallContext.Create("tenant-017");

        var response = await sut.TriggerEmergencyStop(req, ctx);

        var evt = await emergencyDb.EmergencyStopEvents.SingleAsync();
        response.EmergencyStopRecordId.Should().Be(evt.Id.ToString(),
            "the response EmergencyStopRecordId must match the persisted event's Id for full traceability (C-059)");
    }
}