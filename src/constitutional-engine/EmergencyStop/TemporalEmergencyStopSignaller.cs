// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), ADR-018 (Temporal workflow IDs), ADR-001 (gRPC)

using System;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Logging;
using Temporalio.Client;

namespace Waooaw.ConstitutionalEngine.EmergencyStop;

/// <summary>
/// Signals Temporal PAAS session workflows to halt via the EmergencyStop signal.
/// Must complete within 100ms of being called (CCT-HO-01 budget allocation).
/// </summary>
public sealed class TemporalEmergencyStopSignaller : ITemporalEmergencyStopSignaller
{
    private static readonly ActivitySource _activitySource =
        new("Waooaw.ConstitutionalEngine.EmergencyStop");

    // C-073: Constitutional obligation — signal name must match Temporal workflow definition
    private const string EmergencyStopSignalName = "emergency-stop";

    private readonly ITemporalClient _temporalClient;
    private readonly ILogger<TemporalEmergencyStopSignaller> _logger;

    public TemporalEmergencyStopSignaller(
        ITemporalClient temporalClient,
        ILogger<TemporalEmergencyStopSignaller> logger)
    {
        _temporalClient = temporalClient;
        _logger = logger;
    }

    // C-073: Constitutional obligation — signal all affected workflows within 100ms budget
    public async Task SignalWorkflowsAsync(
        string[] workflowIds,
        Guid emergencyStopEventId,
        CancellationToken cancellationToken = default)
    {
        using var activity = _activitySource.StartActivity(
            "EmergencyStop.SignalWorkflows",
            ActivityKind.Client);

        activity?.SetTag("stop.event.id", emergencyStopEventId.ToString());
        activity?.SetTag("workflow.count", workflowIds.Length);

        if (workflowIds.Length == 0)
        {
            _logger.LogWarning(
                "EmergencyStop {EventId}: no workflow IDs to signal — " +
                "stop recorded but no active sessions found",
                emergencyStopEventId);
            return;
        }

        var sw = Stopwatch.StartNew();

        // Signal all workflows concurrently to minimise latency (CCT-HO-01 ≤250ms P99)
        var signalTasks = new Task[workflowIds.Length];
        for (int i = 0; i < workflowIds.Length; i++)
        {
            var workflowId = workflowIds[i];
            signalTasks[i] = SignalSingleWorkflowAsync(
                workflowId,
                emergencyStopEventId,
                cancellationToken);
        }

        await Task.WhenAll(signalTasks);

        sw.Stop();

        _logger.LogInformation(
            "EmergencyStop {EventId}: signalled {Count} Temporal workflow(s) in {ElapsedMs}ms",
            emergencyStopEventId,
            workflowIds.Length,
            sw.ElapsedMilliseconds);

        // C-073: Constitutional obligation — warn if approaching latency budget
        if (sw.ElapsedMilliseconds > 100)
        {
            _logger.LogWarning(
                "EmergencyStop {EventId}: Temporal signal took {ElapsedMs}ms — " +
                "exceeds 100ms internal budget (CCT-HO-01 total budget 250ms P99)",
                emergencyStopEventId,
                sw.ElapsedMilliseconds);
        }

        activity?.SetTag("elapsed_ms", sw.ElapsedMilliseconds);
    }

    private async Task SignalSingleWorkflowAsync(
        string workflowId,
        Guid emergencyStopEventId,
        CancellationToken cancellationToken)
    {
        using var activity = _activitySource.StartActivity(
            "EmergencyStop.SignalSingleWorkflow",
            ActivityKind.Client);

        activity?.SetTag("workflow.id", workflowId);

        try
        {
            var handle = _temporalClient.GetWorkflowHandle(workflowId);

            // C-073: Constitutional obligation — signal carries the evidence record ID for correlation
            await handle.SignalAsync(
                EmergencyStopSignalName,
                new[] { emergencyStopEventId.ToString() });

            _logger.LogInformation(
                "EmergencyStop {EventId}: signalled workflow {WorkflowId} successfully",
                emergencyStopEventId,
                workflowId);
        }
        catch (Exception ex)
        {
            // C-073: Constitutional obligation — log failure but do not swallow;
            // caller (EmergencyStopHandler) decides whether to mark event as Failed
            _logger.LogError(
                ex,
                "EmergencyStop {EventId}: failed to signal workflow {WorkflowId}",
                emergencyStopEventId,
                workflowId);

            throw;
        }
    }
}