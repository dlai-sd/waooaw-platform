// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// Constitutional basis: C-023, C-059, C-063

namespace Waooaw.BusinessPlatform.Services.Spend;

public enum SpendAccountClass
{
    Acquisition,
    SetupGrant,
    Trial,
    Subscription,
    PlatformFloor,
    Simulation,
}

public static class SpendAccountClasses
{
    public static string ToStorage(this SpendAccountClass value) =>
        value switch
        {
            SpendAccountClass.Acquisition => "ACQUISITION",
            SpendAccountClass.SetupGrant => "SETUP_GRANT",
            SpendAccountClass.Trial => "TRIAL",
            SpendAccountClass.Subscription => "SUBSCRIPTION",
            SpendAccountClass.PlatformFloor => "PLATFORM_FLOOR",
            SpendAccountClass.Simulation => "SIMULATION",
            _ => throw new ArgumentOutOfRangeException(nameof(value)),
        };

    public static SpendAccountClass Parse(string value) =>
        value switch
        {
            "ACQUISITION" => SpendAccountClass.Acquisition,
            "SETUP_GRANT" => SpendAccountClass.SetupGrant,
            "TRIAL" => SpendAccountClass.Trial,
            "SUBSCRIPTION" => SpendAccountClass.Subscription,
            "PLATFORM_FLOOR" => SpendAccountClass.PlatformFloor,
            "SIMULATION" => SpendAccountClass.Simulation,
            _ => throw new ArgumentOutOfRangeException(nameof(value)),
        };

    public static SpendAccountClass? ParseOrNull(string? value) =>
        value is null ? null : Parse(value);
}

/// <summary>Account decision stored once at reserve; settle, release and reconcile read it back.</summary>
public sealed record SpendAccountPin(
    SpendAccountClass AccountClass,
    Guid? PinnedWalletAccountId = null
);
