// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-05
// Constitutional basis: C-023, C-059, C-063

namespace Waooaw.BusinessPlatform.Services.Spend;

/// <summary>Fail-closed commercial reserve: an unreachable owner never becomes a metered dispatch.</summary>
public static class CommercialReservationGate
{
    public static async Task<OfferingUsageReceipt?> ReserveAsync(
        IAuthenticatedOfferingUsageGateway gateway,
        SpendAccountClass? accountClass,
        OfferingUsageIdentity identity,
        long maximumUnits,
        CancellationToken ct
    )
    {
        if (accountClass == SpendAccountClass.PlatformFloor)
            return null;
        try
        {
            return await gateway.ReserveAsync(identity, maximumUnits, ct);
        }
        catch (OfferingUsageOwnerUnavailableException failure)
        {
            throw new SpendRefusedException(SpendRefusalCodes.CommercialUnavailable, failure);
        }
    }
}
