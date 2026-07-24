// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), CCT-HO-01 (≤250ms P99), C-059 (Traceability), C-076 (≥90% coverage)
//
// CCT-HO-01: Emergency Stop end-to-end latency MUST be ≤250ms P99.
//            Target for this handler: ≤100ms (AD-001 allocates 250ms total;
//            150ms reserved for network + Temporal signal overhead).

using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.EmergencyStop;

/// <summary>
/// CCT-HO-01 — Constitutional Compliance Test: Emergency Stop Latency Budget.
///
/// Constitutional guarantee (C-001 / AD-001):
///   Emergency Stop MUST complete within 250ms P99 end-to-end.
///   This handler's target: ≤100ms (handler overhead only, excluding network).
///
/// Test approach: mock all I/O to eliminate network/DB latency.
///   If the handler itself exceeds 100ms with zero-latency dependencies,
///   there is a code-level latency violation that must be fixed before production.
/// </summary>
public sealed class CCT_HO01_EmergencyStopLatencyTests
{
    // CCT-HO-01 budget for this handler (AD-001: 250ms total; 150ms for network/Temporal)
    private const int HandlerLatencyBudgetMs = 100;

    // Warm-up run count to exclude JIT from measurement
    private const int WarmupRuns = 3;

    // Measurement runs for P99 estimate (true P99 needs production telemetry)
    private const int MeasurementRuns = 20;

    private static readonly Guid ContractId = Guid.NewGuid();
    private static readonly string[] SessionIds = ["session-001", "session-002"];

    [Fact]
    public async Task CCT_HO01_PASS_EmergencyStopHandlerCompletes_Within100ms()
    {
        // Arrange — zero-latency mocks to measure handler overhead only
        var (repo, signaller, handler) = BuildFastHandler();

        var request = new EmergencyStopRequest(ContractId, "user-1", SessionIds);

        // Warm up JIT
        for (var i = 0; i < WarmupRuns; i++)
        {
            SetupOneRun(repo, signaller);
            await handler.ExecuteAsync(request);
        }

        // Measure
        var elapsedMs = new long[MeasurementRuns];
        for (var i = 0; i < MeasurementRuns; i++)
        {
            SetupOneRun(repo, signaller);
            var sw = Stopwatch.StartNew();
            await handler.ExecuteAsync(request);
            sw.Stop();
            elapsedMs[i] = sw.ElapsedMilliseconds;
        }

        // P99 estimate from sample (worst observed value is a reasonable proxy for unit tests)
        var maxObservedMs = elapsedMs[^1]; // after sorting it would be max — use Max directly
        var p99Estimate = elapsedMs.Max();

        // Assert — CCT-HO-01: handler overhead must be within budget
        p99Estimate.Should().BeLessOrEqualTo(HandlerLatencyBudgetMs,
            because: $"CCT-HO-01: EmergencyStopHandler must complete within {HandlerLatencyBudgetMs}ms " +
                     $"(AD-001 reserves 250ms total; {HandlerLatencyBudgetMs}ms for handler overhead). " +
                     $"Observed max: {p99Estimate}ms over {MeasurementRuns} runs.");
    }

    [Fact]
    public async Task CCT_HO01_PASS_EmergencyStopHandler_ReturnsWithinBudget_WithSessionLookup()
    {
        // Variant: when ActiveSessionIds is empty, repository lookup path is also measured
        var (repo, signaller, handler) = BuildFastHandler();
        var requestWithNoSessions = new EmergencyStopRequest(ContractId, "user-1", ActiveSessionIds: Array.Empty<string>());

        SetupOneRun(repo, signaller);
        var sw = Stopwatch.StartNew();
        await handler.ExecuteAsync(requestWithNoSessions);
        sw.Stop();

        sw.ElapsedMilliseconds.Should().BeLessOrEqualTo(HandlerLatencyBudgetMs,
            because: "CCT-HO-01: session lookup path must also complete within handler budget");
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    private static (Mock<IEmergencyStopRepository> repo, Mock<ITemporalEmergencyStopSignaller> signaller, EmergencyStopHandler handler) BuildFastHandler()
    {
        var repo = new Mock<IEmergencyStopRepository>();
        var signaller = new Mock<ITemporalEmergencyStopSignaller>();

        var handler = new EmergencyStopHandler(
            repo.Object,
            signaller.Object,
            NullLogger<EmergencyStopHandler>.Instance);

        return (repo, signaller, handler);
    }

    private static void SetupOneRun(Mock<IEmergencyStopRepository> repo, Mock<ITemporalEmergencyStopSignaller> signaller)
    {
        var eventId = Guid.NewGuid();
        var persistedEvent = new EmergencyStopEvent
        {
            Id = eventId,
            ContractId = ContractId,
            InitiatedByUserId = "user-1",
            AffectedSessionIds = SessionIds,
            StopSource = "gRPC",
            Status = EmergencyStopStatus.Pending,
        };

        repo.Reset();
        signaller.Reset();

        repo.Setup(r => r.GetActiveSessionIdsForContractAsync(ContractId, It.IsAny<CancellationToken>()))
             .ReturnsAsync(SessionIds);

        repo.Setup(r => r.PersistEvidenceAsync(It.IsAny<EmergencyStopEvent>(), It.IsAny<CancellationToken>()))
             .ReturnsAsync(persistedEvent);

        repo.Setup(r => r.MarkTemporalSignalledAsync(eventId, It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()))
             .Returns(Task.CompletedTask);

        signaller.Setup(s => s.SignalWorkflowsAsync(It.IsAny<string[]>(), eventId, It.IsAny<CancellationToken>()))
                 .Returns(Task.CompletedTask);
    }
}
