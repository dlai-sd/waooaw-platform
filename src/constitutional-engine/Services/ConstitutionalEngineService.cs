// Implements: architecture/reference/components/constitutional-engine.md §4 Emergency Stop Handler
// constitutional_basis: C-001 (Emergency Stop absolute), ADR-001 (gRPC), CCT-HO-01 (≤250ms P99),
//                       C-059 (Traceability), C-073 (Annotated constitutional obligations)

using System;
using System.Diagnostics;
using System.Threading.Tasks;
using Grpc.Core;
using Microsoft.Extensions.Logging;
using Waooaw.ConstitutionalEngine.EmergencyStop;

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// gRPC service implementation for the Constitutional Engine.
/// TriggerEmergencyStop implements C-001 (Emergency Stop absolute guarantee).
/// CCT-HO-01: ≤250ms P99 end-to-end latency for Emergency Stop.
/// </summary>
public sealed class ConstitutionalEngineService : ConstitutionalService.ConstitutionalServiceBase
{
    private static readonly ActivitySource _activitySource =
        new("Waooaw.ConstitutionalEngine");

    private readonly EmergencyStopHandler _emergencyStopHandler;
    private readonly ILogger<ConstitutionalEngineService> _logger;

    public ConstitutionalEngineService(
        EmergencyStopHandler emergencyStopHandler,
        ILogger<ConstitutionalEngineService> logger)
    {
        _emergencyStopHandler = emergencyStopHandler;
        _logger = logger;
    }

    /// <summary>
    /// gRPC RPC: TriggerEmergencyStop
    /// Implements C-001 Emergency Stop absolute guarantee.
    /// CCT-HO-01: must complete ≤250ms P99 end-to-end.
    /// </summary>
    // C-073: Constitutional obligation — this method implements C-001 Emergency Stop
    public override async Task<TriggerEmergencyStopResponse> TriggerEmergencyStop(
        TriggerEmergencyStopRequest request,
        ServerCallContext context)
    {
        using var activity = _activitySource.StartActivity(
            "ConstitutionalEngine.TriggerEmergencyStop",
            ActivityKind.Server);

        var sw = Stopwatch.StartNew();

        // Extract authenticated user from JWT claims (Keycloak RS256 — security-architecture.md §2)
        var userId = context.GetHttpContext()?.User?.FindFirst("sub")?.Value
                     ?? context.GetHttpContext()?.User?.FindFirst("preferred_username")?.Value
                     ?? "unknown";

        _logger.LogInformation(
            "TriggerEmergencyStop gRPC call received. ContractId: {ContractId}, " +
            "UserId: {UserId}, SessionCount: {SessionCount}",
            request.ContractId,
            userId,
            request.ActiveSessionIds.Count);

        activity?.SetTag("contract.id", request.ContractId);
        activity?.SetTag("user.id", userId);

        if (!Guid.TryParse(request.ContractId, out var contractId))
        {
            _logger.LogWarning(
                "TriggerEmergencyStop: invalid ContractId format '{ContractId}'",
                request.ContractId);

            throw new RpcException(new Status(
                StatusCode.InvalidArgument,
                $"ContractId '{request.ContractId}' is not a valid UUID"));
        }

        var sessionIds = new string[request.ActiveSessionIds.Count];
        request.ActiveSessionIds.CopyTo(sessionIds, 0);

        EmergencyStopResult result;
        try
        {
            result = await _emergencyStopHandler.ExecuteAsync(
                new EmergencyStopRequest(
                    ContractId: contractId,
                    InitiatedByUserId: userId,
                    ActiveSessionIds: sessionIds,
                    StopSource: "gRPC"),
                context.CancellationToken);
        }
        catch (Exception ex) when (ex is not RpcException)
        {
            sw.Stop();
            _logger.LogCritical(
                ex,
                "TriggerEmergencyStop FAILED for contract {ContractId} after {ElapsedMs}ms — " +
                "C-001 Emergency Stop guarantee may be violated",
                request.ContractId,
                sw.ElapsedMilliseconds);

            activity?.SetStatus(ActivityStatusCode.Error, ex.Message);

            // C-073: Constitutional obligation — surface as gRPC Internal to caller
            throw new RpcException(new Status(
                StatusCode.Internal,
                "Emergency Stop failed — evidence may not have been recorded. " +
                "Contact platform support immediately."));
        }

        sw.Stop();

        _logger.LogInformation(
            "TriggerEmergencyStop completed. EventId: {EventId}, ElapsedMs: {ElapsedMs}ms, " +
            "Sessions: {SessionCount} (CCT-HO-01)",
            result.EmergencyStopRecordId,
            sw.ElapsedMilliseconds,
            result.AffectedSessionIds.Length);

        activity?.SetTag("stop.event.id", result.EmergencyStopRecordId.ToString());
        activity?.SetTag("elapsed_ms", sw.ElapsedMilliseconds);

        var response = new TriggerEmergencyStopResponse
        {
            EmergencyStopRecordId = result.EmergencyStopRecordId.ToString(),
            ConfirmedAt = Google.Protobuf.WellKnownTypes.Timestamp.FromDateTimeOffset(result.ConfirmedAt)
        };

        foreach (var sessionId in result.AffectedSessionIds)
        {
            response.AffectedSessionIds.Add(sessionId);
        }

        return response;
    }
}