// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// Constitutional basis: C-023, C-059, C-063

namespace Waooaw.BusinessPlatform.Services.Spend;

public enum SpendPurpose
{
    AgentWork,
    Onboarding,
    PresalesOrMarketplace,
    PlatformSupport,
    SafetyFloor,
    Simulation,
}

public static class SpendAuthorityKinds
{
    public const string Trial = "TRIAL";
    public const string AcceptedOffering = "ACCEPTED_OFFERING";
    public const string None = "NONE";

    public static string FromEngagementMode(string? engagementMode) =>
        engagementMode switch
        {
            "TRIAL" => Trial,
            "LIVE" => AcceptedOffering,
            _ => None,
        };
}
