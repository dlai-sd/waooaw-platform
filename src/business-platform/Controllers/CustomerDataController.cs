// Implements: adr/ADR-044-constitutional-audit-trail-sink.md §4
// constitutional_basis: C-078 (DPDPA Right-to-Erasure), ADR-044, C-059
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Grpc.Net.Client;
using Waooaw.BusinessPlatform.Infrastructure;
using Waooaw.ConstitutionalEngine.Grpc;

namespace Waooaw.BusinessPlatform.Controllers;

/// <summary>
/// DPDPA Right-to-Erasure endpoint.
/// DELETE /api/v1/customers/{tenantId}/data
/// Auth: Founder role only (C-078).
/// Sequence: wipe payload_store rows → call CE.RecordErasure → return certificate.
/// </summary>
[ApiController, Route("api/v1/customers")]
public sealed class CustomerDataController : ControllerBase
{
    private const string FounderRole = "founder";

    private readonly IDbContextFactory<PayloadStoreDbContext>      _payloadFactory;
    private readonly IConfiguration                                 _config;
    private readonly ILogger<CustomerDataController>                _logger;

    public CustomerDataController(
        IDbContextFactory<PayloadStoreDbContext> payloadFactory,
        IConfiguration config,
        ILogger<CustomerDataController> logger)
    {
        _payloadFactory = payloadFactory;
        _config         = config;
        _logger         = logger;
    }

    /// <summary>
    /// DELETE /api/v1/customers/{tenantId}/data
    /// C-078: Founder-only. Wipes payload_store rows; CE marks proof as PAYLOAD_PURGED.
    /// Returns DPDPA compliance certificate JSON.
    /// </summary>
    [HttpDelete("{tenantId}/data")]
    public async Task<IActionResult> EraseCustomerDataAsync(
        Guid              tenantId,
        [FromHeader(Name = "x-erasure-order-id")] string? erasureOrderId,
        CancellationToken cancellationToken)
    {
        // C-078: Founder role required — verified via claim.
        if (!User.IsInRole(FounderRole))
        {
            _logger.LogWarning(
                "EraseCustomerData rejected: caller lacks founder role. TenantId={TenantId}", tenantId);
            return Forbid();
        }

        if (string.IsNullOrWhiteSpace(erasureOrderId))
        {
            return BadRequest(new { error = "x-erasure-order-id header is required (C-078)." });
        }

        await using var db = await _payloadFactory.CreateDbContextAsync(cancellationToken);

        // Step 1: wipe payload_json + set erased_at for all tenant payloads.
        var payloads = await db.OperationalPayloads
            .Where(p => p.TenantId == tenantId && p.ErasedAt == null)
            .ToListAsync(cancellationToken);

        var erasureTs = DateTimeOffset.UtcNow;
        foreach (var payload in payloads)
        {
            payload.PayloadJson    = null;
            payload.PayloadBlobRef = null;
            payload.ErasedAt       = erasureTs;
        }

        await db.SaveChangesAsync(cancellationToken);

        _logger.LogInformation(
            "Payload wipe complete. TenantId={TenantId} ErasureOrderId={OrderId} Rows={Count}",
            tenantId, erasureOrderId, payloads.Count);

        // Step 2: call CE.RecordErasure to stamp audit_sink proof records.
        var ceRecordsUpdated = 0;
        var ceAddress = _config["ConstitutionalEngine:GrpcAddress"] ?? "http://constitutional-engine:7000";
        try
        {
            using var channel = GrpcChannel.ForAddress(ceAddress);
            var ceClient = new ConstitutionalService.ConstitutionalServiceClient(channel);
            var ceResp = await ceClient.RecordErasureAsync(
                new RecordErasureRequest
                {
                    TenantId       = tenantId.ToString(),
                    ErasureOrderId = erasureOrderId
                },
                cancellationToken: cancellationToken);

            ceRecordsUpdated = ceResp.RecordsUpdated;
            _logger.LogInformation(
                "CE.RecordErasure complete. TenantId={TenantId} RecordsMarked={Count}",
                tenantId, ceRecordsUpdated);
        }
        catch (Exception ex)
        {
            // C-059: log CE call failure; do not suppress.
            _logger.LogError(ex,
                "CE.RecordErasure failed. TenantId={TenantId} ErasureOrderId={OrderId}",
                tenantId, erasureOrderId);
            return StatusCode(502, new
            {
                error             = "CE_ERASURE_RECORD_FAILED",
                detail            = "Payload store wiped but CE proof-marking failed. Retry required.",
                erasure_order_id  = erasureOrderId,
                payloads_wiped    = payloads.Count,
                proof_retained    = true,
                timestamp         = erasureTs
            });
        }

        // Step 3: return DPDPA compliance certificate.
        return Ok(new
        {
            erasure_order_id  = erasureOrderId,
            tenant_id         = tenantId,
            records_wiped     = payloads.Count,
            ce_records_marked = ceRecordsUpdated,
            proof_retained    = true,
            timestamp         = erasureTs,
            statement         = $"Payload data purged per DPDPA erasure order {erasureOrderId}. " +
                                 "Constitutional audit proof records retained with erasure timestamp."
        });
    }
}
