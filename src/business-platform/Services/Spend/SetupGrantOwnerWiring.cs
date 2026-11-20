// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-09
// Constitutional basis: C-023, C-059, C-063

using System.Security.Cryptography;
using System.Text;

namespace Waooaw.BusinessPlatform.Services.Spend;

/// <summary>
/// How the conversation inference owner draws on, settles and releases the relationship's setup grant.
/// Kept apart from the owner so the wiring (identity mapping, keys, receipt shape, fail-closed rules) is
/// verified with fakes and no database.
/// </summary>
public static class SetupGrantOwnerWiring
{
    public static long PaiseCeiling(decimal paise) =>
        Math.Max(1L, checked((long)Math.Ceiling(paise)));

    /// <summary>The settle and the release of one reservation are different, stable operations.</summary>
    public static Guid IdempotencyKey(Guid reservationId, bool release) =>
        new(
            SHA256
                .HashData(
                    Encoding.UTF8.GetBytes(
                        $"setup-grant-{(release ? "release" : "settle")}:{reservationId:D}"
                    )
                )
                .AsSpan(0, 16)
        );

    /// <summary>Onboarding turns draw only on the relationship's setup grant; exhaustion is told, not hidden.</summary>
    public static async Task<OfferingUsageReceipt> ReserveAsync(
        IPlatformAccountGateway? gateway,
        InferenceCaller caller,
        OfferingUsageIdentity identity,
        decimal cost,
        CancellationToken ct
    )
    {
        var accounts =
            gateway ?? throw new SpendRefusedException(SpendRefusalCodes.CommercialUnavailable);
        var draw = await SetupGrantReservationGate.ReserveAsync(
            accounts,
            caller.TenantId,
            caller.ActorId,
            caller.RelationshipId,
            identity.ProfessionalType,
            identity.ProfessionalVersion,
            identity.ComponentId,
            PaiseCeiling(cost),
            identity.InvocationId,
            identity.OwnerEvidenceId,
            identity.IdempotencyKey,
            ct
        );
        if (draw.Exhausted || draw.ReservationId is not { } reservationId)
            throw new SpendRefusedException(SetupGrantReservationGate.ExhaustedCode);
        return new OfferingUsageReceipt(
            reservationId,
            "RESERVED",
            0,
            draw.ReservedPaise,
            draw.ReservedPaise,
            SpendAccountClass.SetupGrant.ToStorage(),
            Guid.Empty,
            SpendAccountClass.SetupGrant.ToStorage(),
            false
        );
    }

    public static Task SettleAsync(
        IPlatformAccountGateway? gateway,
        InferenceCaller caller,
        Guid reservationId,
        bool release,
        decimal actualPaise,
        Guid evidenceId,
        CancellationToken ct
    ) =>
        SetupGrantReservationGate.SettleOrReleaseAsync(
            gateway ?? throw new SpendRefusedException(SpendRefusalCodes.CommercialUnavailable),
            caller.TenantId,
            caller.ActorId,
            reservationId,
            release ? 0 : PaiseCeiling(actualPaise),
            evidenceId,
            IdempotencyKey(reservationId, release),
            ct
        );
}
