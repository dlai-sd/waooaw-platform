// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-04
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C3-05
// Constitutional basis: C-023, C-059, C-063

namespace Waooaw.BusinessPlatform.Services.Spend;

public static class SpendRefusalCodes
{
    public const string PurposeUnmapped = "SPEND_PURPOSE_UNMAPPED";
    public const string AuthorityUnavailable = "SPEND_AUTHORITY_UNAVAILABLE";
    public const string CommercialUnavailable = "SPEND_COMMERCIAL_UNAVAILABLE";
}

/// <summary>Typed refusal: no metered call is dispatched for the refused request.</summary>
public sealed class SpendRefusedException(string code, Exception? inner = null)
    : Exception(code, inner)
{
    public string Code { get; } = code;

    public int StatusCode => Code == SpendRefusalCodes.CommercialUnavailable ? 503 : 403;
}

public sealed record RelationshipSpendInput(
    Guid? RelationshipId,
    string AuthorityKind,
    SpendPurpose Purpose,
    string Channel,
    bool IsSimulation,
    string? SkillId = null
);

public sealed record SpendAccountDecision(
    SpendAccountClass AccountClass,
    Guid? RelationshipId,
    string? SkillId = null
);

public interface ISpendAccountResolver
{
    SpendPurpose ResolvePurpose(string? contextKey, string? phase);

    SpendAccountDecision Resolve(RelationshipSpendInput input);
}

public sealed class SpendAccountResolver(SpendPurposeMap purposes) : ISpendAccountResolver
{
    public SpendPurpose ResolvePurpose(string? contextKey, string? phase) =>
        purposes.Find(contextKey, phase)
        ?? throw new SpendRefusedException(SpendRefusalCodes.PurposeUnmapped);

    public SpendAccountDecision Resolve(RelationshipSpendInput input)
    {
        Guid? relationship = input.RelationshipId is { } id && id != Guid.Empty ? id : null;
        if (input.Purpose == SpendPurpose.SafetyFloor)
            return new SpendAccountDecision(
                SpendAccountClass.PlatformFloor,
                relationship,
                input.SkillId
            );
        if (input.Purpose == SpendPurpose.Simulation || input.IsSimulation)
            return new SpendAccountDecision(
                SpendAccountClass.Simulation,
                relationship,
                input.SkillId
            );
        if (
            input.Purpose is SpendPurpose.PresalesOrMarketplace or SpendPurpose.PlatformSupport
            || relationship is null
        )
            return new SpendAccountDecision(SpendAccountClass.Acquisition, null, input.SkillId);
        if (input.Purpose == SpendPurpose.Onboarding)
            return new SpendAccountDecision(
                SpendAccountClass.SetupGrant,
                relationship,
                input.SkillId
            );
        if (input.Purpose != SpendPurpose.AgentWork)
            throw new SpendRefusedException(SpendRefusalCodes.PurposeUnmapped);
        return input.AuthorityKind switch
        {
            SpendAuthorityKinds.Trial => new SpendAccountDecision(
                SpendAccountClass.Trial,
                relationship,
                input.SkillId
            ),
            SpendAuthorityKinds.AcceptedOffering => new SpendAccountDecision(
                SpendAccountClass.Subscription,
                relationship,
                input.SkillId
            ),
            _ => throw new SpendRefusedException(SpendRefusalCodes.AuthorityUnavailable),
        };
    }
}
