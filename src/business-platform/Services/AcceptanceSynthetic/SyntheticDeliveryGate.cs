// Implements: architecture/reference/acceptance/customer-journey-acceptance-architecture.md §5 and adr/ADR-055-synthetic-acceptance-tenants-and-evidence.md decision 4
// Constitutional basis: C-059 (Implementation Traceability)

using Microsoft.Extensions.Options;

namespace Waooaw.BusinessPlatform.Services.AcceptanceSynthetic;

/// <summary>
/// Reduces a synthetic tenant's outbound side effects: delivery to any recipient other than a sandbox recipient
/// registered for the tenant's run is suppressed, counted and recorded. It runs after every authority, recipient,
/// stop and eligibility check of the dispatch, so it can only remove a send, never permit one.
/// </summary>
public interface ISyntheticDeliveryGate
{
    Task<bool> SuppressAsync(
        WhatsAppProviderDispatchRequest request,
        string recipient,
        CancellationToken ct
    );
}

public sealed class SyntheticDeliveryGate(
    ISyntheticAcceptanceRegistry registry,
    IOptions<AcceptanceSyntheticOptions> options,
    ILogger<SyntheticDeliveryGate> logger
) : ISyntheticDeliveryGate
{
    /// <summary>Blocked reason stored on the outbox row; it is not a delivery failure and raises no dead-letter signal.</summary>
    public const string SuppressedReason = "SYNTHETIC_RECIPIENT_SUPPRESSED";

    public async Task<bool> SuppressAsync(
        WhatsAppProviderDispatchRequest request,
        string recipient,
        CancellationToken ct
    )
    {
        if (!options.Value.Enabled)
            return false;
        var run = await registry.FindTenantRunAsync(request.TenantId, ct);
        if (run is null)
            return false;
        var digest = SyntheticRecipient.Digest(recipient);
        if (await registry.IsSandboxRecipientAsync(run, digest, ct))
            return false;
        await registry.RecordSuppressionAsync(
            request.TenantId,
            run,
            request.OutboxId,
            request.AttemptNumber,
            digest,
            ct
        );
        SyntheticAcceptanceTelemetry.DeliverySuppressed();
        logger.LogInformation(
            "Outbound delivery for synthetic tenant {TenantId} suppressed: recipient is not a registered sandbox recipient.",
            request.TenantId
        );
        return true;
    }
}
