// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
// Constitutional basis: C-023, C-059, C-063

namespace Waooaw.BusinessPlatform.Services.Spend;

/// <summary>The outcome of an onboarding draw on the relationship's setup grant.</summary>
public sealed record SetupGrantDraw(
    Guid? ReservationId,
    long ReservedPaise,
    bool Exhausted,
    string? ConversationText
);

/// <summary>
/// Onboarding turns draw only on the setup grant. When it cannot cover the call the customer is told so,
/// and the work continues on the subscription scope only after that, never silently.
/// </summary>
public static class SetupGrantReservationGate
{
    public const string ExhaustedCode = "SETUP_GRANT_EXHAUSTED";

    public const string ExhaustedConversationText =
        "The free setup allowance for this agent has been used. I can keep helping, and from here "
        + "the work counts against your plan's allowance. Tell me if you would like to continue.";

    public static async Task<SetupGrantDraw> ReserveAsync(
        IPlatformAccountGateway gateway,
        Guid tenantId,
        Guid actorId,
        Guid relationshipId,
        string agentType,
        string agentVersion,
        string componentId,
        long maximumPaise,
        Guid invocationId,
        Guid ownerEvidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    )
    {
        try
        {
            var receipt = await gateway.ReserveSetupGrantAsync(
                tenantId,
                actorId,
                relationshipId,
                agentType,
                agentVersion,
                componentId,
                maximumPaise,
                invocationId,
                ownerEvidenceId,
                idempotencyKey,
                ct
            );
            return receipt.IsExhausted
                ? new SetupGrantDraw(null, 0, true, ExhaustedConversationText)
                : new SetupGrantDraw(receipt.ReservationId, receipt.ReservedPaise, false, null);
        }
        catch (OfferingUsageOwnerUnavailableException failure)
        {
            throw new SpendRefusedException(SpendRefusalCodes.CommercialUnavailable, failure);
        }
    }

    /// <summary>Settle the actual cost, or release the hold when nothing was dispatched.</summary>
    public static Task SettleOrReleaseAsync(
        IPlatformAccountGateway gateway,
        Guid tenantId,
        Guid actorId,
        Guid reservationId,
        long actualPaise,
        Guid evidenceId,
        Guid idempotencyKey,
        CancellationToken ct
    ) =>
        actualPaise > 0
            ? gateway.SettleAccountAsync(
                tenantId,
                actorId,
                reservationId,
                actualPaise,
                evidenceId,
                idempotencyKey,
                ct
            )
            : gateway.ReleaseAccountAsync(
                tenantId,
                actorId,
                reservationId,
                evidenceId,
                idempotencyKey,
                ct
            );
}
