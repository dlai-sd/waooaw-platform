// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-023 (Evidence First), C-001 (Emergency Stop absolute), C-059 (Traceability), C-076 (≥90% coverage)
//
// CCT-EF-01: Evidence First — PersistEvidence MUST complete before TriggerTemporalSignal.
//            If persistence fails, Temporal MUST NOT be signalled. C-023 / AD-002.

using System;
using System.Threading;
using System.Threading.Tasks;
using FluentAssertions;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Moq.Language.Flow;
using Waooaw.ConstitutionalEngine.EmergencyStop;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.EmergencyStop;

/// <summary>
/// CCT-EF-01 — Constitutional Compliance Test: Evidence First Enforcer.
///
/// Constitutional guarantee (C-023 / AD-002):
///   Evidence record MUST be written and durable BEFORE any downstream action is taken.
///   If the write fails, the operation MUST NOT proceed.
///
/// For Emergency Stop specifically:
///   PersistEvidenceAsync MUST be called and complete before SignalWorkflowsAsync.
///   If PersistEvidenceAsync throws, SignalWorkflowsAsync MUST NOT be called.
/// </summary>
public sealed class CCT_EF01_EvidenceFirstTests
{
    private readonly Mock<IEmergencyStopRepository> _repo = new(MockBehavior.Strict);
    private readonly Mock<ITemporalEmergencyStopSignaller> _signaller = new(MockBehavior.Strict);
    private readonly EmergencyStopHandler _sut;

    private static readonly Guid ContractId = Guid.NewGuid();
    private static readonly string[] SessionIds = ["session-a", "session-b"];

    public CCT_EF01_EvidenceFirstTests()
    {
        _sut = new EmergencyStopHandler(
            _repo.Object,
            _signaller.Object,
            NullLogger<EmergencyStopHandler>.Instance);
    }

    // ─── CCT-EF-01-PASS: evidence is persisted before Temporal signal ─────────

    [Fact]
    public async Task CCT_EF01_PASS_EvidencePersisted_BeforeTemporalSignal()
    {
        // Arrange — strict call order verification: PersistEvidence then SignalWorkflows
        var callOrder = new System.Collections.Generic.List<string>();

        var persistedEvent = MakeEvent();

        _repo.Setup(r => r.GetActiveSessionIdsForContractAsync(ContractId, It.IsAny<CancellationToken>()))
             .ReturnsAsync(Array.Empty<string>());

        _repo.Setup(r => r.PersistEvidenceAsync(It.IsAny<EmergencyStopEvent>(), It.IsAny<CancellationToken>()))
             .Callback<EmergencyStopEvent, CancellationToken>((_, _) => callOrder.Add("persist"))
             .ReturnsAsync(persistedEvent);

        _repo.Setup(r => r.MarkTemporalSignalledAsync(persistedEvent.Id, It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()))
             .Returns(Task.CompletedTask);

        _signaller.Setup(s => s.SignalWorkflowsAsync(It.IsAny<string[]>(), persistedEvent.Id, It.IsAny<CancellationToken>()))
                  .Callback<string[], Guid, CancellationToken>((_, _, _) => callOrder.Add("signal"))
                  .Returns(Task.CompletedTask);

        var request = new EmergencyStopRequest(ContractId, "user-1", SessionIds);

        // Act
        var result = await _sut.ExecuteAsync(request);

        // Assert — Evidence First: persist MUST appear before signal in call order
        callOrder.Should().ContainInOrder(
            new[] { "persist", "signal" },
            because: "C-023 Evidence First: PersistEvidenceAsync must complete before SignalWorkflowsAsync");

        result.EmergencyStopRecordId.Should().Be(persistedEvent.Id);
        _repo.Verify(r => r.PersistEvidenceAsync(It.IsAny<EmergencyStopEvent>(), It.IsAny<CancellationToken>()), Times.Once);
        _signaller.Verify(s => s.SignalWorkflowsAsync(It.IsAny<string[]>(), persistedEvent.Id, It.IsAny<CancellationToken>()), Times.Once);
    }

    // ─── CCT-EF-01-FAIL: persistence failure MUST block Temporal signal ───────

    [Fact]
    public async Task CCT_EF01_FAIL_IfPersistenceFails_TemporalSignalNotSent()
    {
        // Arrange — persistence throws; signaller must NEVER be called
        _repo.Setup(r => r.GetActiveSessionIdsForContractAsync(ContractId, It.IsAny<CancellationToken>()))
             .ReturnsAsync(SessionIds);

        _repo.Setup(r => r.PersistEvidenceAsync(It.IsAny<EmergencyStopEvent>(), It.IsAny<CancellationToken>()))
             .ThrowsAsync(new InvalidOperationException("DB unavailable — simulated evidence persistence failure"));

        var request = new EmergencyStopRequest(ContractId, "user-1", SessionIds);

        // Act
        var act = async () => await _sut.ExecuteAsync(request);

        // Assert — exception propagates AND signaller was never called
        await act.Should().ThrowAsync<InvalidOperationException>(
            because: "C-023/AD-002: callers must not return success when evidence write fails");

        // C-001: Temporal signal must NOT have been sent — no unrecorded stop allowed
        _signaller.Verify(
            s => s.SignalWorkflowsAsync(It.IsAny<string[]>(), It.IsAny<Guid>(), It.IsAny<CancellationToken>()),
            Times.Never,
            "C-001: an unrecorded Emergency Stop is constitutionally prohibited");
    }

    // ─── Evidence record failure path — MarkFailed is called on signal failure ─

    [Fact]
    public async Task EvidenceRecordMarkedFailed_WhenTemporalSignalFails()
    {
        // Arrange
        var persistedEvent = MakeEvent();

        _repo.Setup(r => r.GetActiveSessionIdsForContractAsync(ContractId, It.IsAny<CancellationToken>()))
             .ReturnsAsync(SessionIds);

        _repo.Setup(r => r.PersistEvidenceAsync(It.IsAny<EmergencyStopEvent>(), It.IsAny<CancellationToken>()))
             .ReturnsAsync(persistedEvent);

        _signaller.Setup(s => s.SignalWorkflowsAsync(It.IsAny<string[]>(), persistedEvent.Id, It.IsAny<CancellationToken>()))
                  .ThrowsAsync(new TimeoutException("Temporal unavailable"));

        // MarkFailedAsync must be called even under signal failure (CancellationToken.None — non-cancellable)
        _repo.Setup(r => r.MarkFailedAsync(persistedEvent.Id, CancellationToken.None))
             .Returns(Task.CompletedTask);

        var request = new EmergencyStopRequest(ContractId, "user-1", SessionIds);

        // Act
        var act = async () => await _sut.ExecuteAsync(request);

        // Assert — exception propagates AND MarkFailed was called for audit trail
        await act.Should().ThrowAsync<TimeoutException>();

        _repo.Verify(r => r.MarkFailedAsync(persistedEvent.Id, CancellationToken.None), Times.Once,
            "C-023/C-027: audit trail must record the failure even when Temporal is unavailable");
    }

    // ─── Session ID fallback path ─────────────────────────────────────────────

    [Fact]
    public async Task WhenNoSessionsProvided_LooksUpActiveSessionsFromRepository()
    {
        // Arrange — empty ActiveSessionIds triggers repository lookup
        var persistedEvent = MakeEvent();
        var activeFromRepo = new[] { "session-from-repo-1", "session-from-repo-2" };

        _repo.Setup(r => r.GetActiveSessionIdsForContractAsync(ContractId, It.IsAny<CancellationToken>()))
             .ReturnsAsync(activeFromRepo);

        _repo.Setup(r => r.PersistEvidenceAsync(It.IsAny<EmergencyStopEvent>(), It.IsAny<CancellationToken>()))
             .ReturnsAsync(persistedEvent);

        _repo.Setup(r => r.MarkTemporalSignalledAsync(persistedEvent.Id, It.IsAny<DateTimeOffset>(), It.IsAny<CancellationToken>()))
             .Returns(Task.CompletedTask);

        _signaller.Setup(s => s.SignalWorkflowsAsync(activeFromRepo, persistedEvent.Id, It.IsAny<CancellationToken>()))
                  .Returns(Task.CompletedTask);

        var request = new EmergencyStopRequest(ContractId, "user-1", ActiveSessionIds: Array.Empty<string>());

        // Act
        var result = await _sut.ExecuteAsync(request);

        // Assert
        result.AffectedSessionIds.Should().BeEquivalentTo(activeFromRepo);
        _repo.Verify(r => r.GetActiveSessionIdsForContractAsync(ContractId, It.IsAny<CancellationToken>()), Times.Once);
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    private static EmergencyStopEvent MakeEvent() => new()
    {
        Id = Guid.NewGuid(),
        ContractId = ContractId,
        InitiatedByUserId = "user-1",
        AffectedSessionIds = SessionIds,
        StopSource = "gRPC",
        Status = EmergencyStopStatus.Pending
    };
}
