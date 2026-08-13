// Implements: WC-065 WC065-03, FA-047
// constitutional_basis: C-002, C-023, C-059, C-089, C-091

using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class OfferabilityServiceTests
{
    private static readonly IReadOnlyDictionary<string, string> CurrentVersions =
        new Dictionary<string, string> { ["WBE"] = "wbe-4", ["LIFECYCLE"] = "professional-7" };

    [Fact]
    public void CurrentEvidenceAndNonNegativeDirectContributionAllows()
    {
        var decision = Evaluate(price: 100m, directCost: 100m);

        Assert.Equal(OfferabilityDisposition.Allow, decision.Disposition);
        Assert.True(decision.IsEligible);
        Assert.Equal(0m, decision.DirectContributionAmount);
        Assert.Empty(decision.Reasons);
    }

    [Fact]
    public void NegativeDirectContributionRequiresRevision()
    {
        var decision = Evaluate(price: 99m, directCost: 100m);

        Assert.Equal(OfferabilityDisposition.Revise, decision.Disposition);
        Assert.Contains("NEGATIVE_DIRECT_CONTRIBUTION", decision.Reasons);
    }

    [Fact]
    public void CalculatedRiskIsDisabledForLeanLaunch()
    {
        var decision = Evaluate(price: 100m, directCost: 90m, requestsCalculatedRisk: true);

        Assert.Equal(OfferabilityDisposition.Escalate, decision.Disposition);
        Assert.Contains("CALCULATED_RISK_DISABLED", decision.Reasons);
    }

    [Fact]
    public void MissingOrStaleOwnerEvidenceNeverAllows()
    {
        var decision = Evaluate(price: 100m, directCost: 90m, ownerEvidenceCurrent: false);

        Assert.Equal(OfferabilityDisposition.Revise, decision.Disposition);
        Assert.False(decision.IsEligible);
        Assert.Contains("OWNER_EVIDENCE_UNAVAILABLE_OR_STALE", decision.Reasons);
    }

    [Fact]
    public void CustomerOrConstitutionalFloorFailureBlocks()
    {
        var decision = Evaluate(
            price: 100m,
            directCost: 90m,
            customerProtectionSatisfied: false,
            constitutionalFloorSatisfied: false);

        Assert.Equal(OfferabilityDisposition.Block, decision.Disposition);
        Assert.Contains("CUSTOMER_PROTECTION_FAILED", decision.Reasons);
        Assert.Contains("CONSTITUTIONAL_FLOOR_FAILED", decision.Reasons);
    }

    private static OfferabilityDecision Evaluate(
        decimal price,
        decimal directCost,
        bool ownerEvidenceCurrent = true,
        bool customerProtectionSatisfied = true,
        bool constitutionalFloorSatisfied = true,
        bool requestsCalculatedRisk = false) => new OfferabilityService().Evaluate(new OfferabilityInput(
            "digital-marketing-local-service",
            "FA-047-v1",
            price,
            directCost,
            ownerEvidenceCurrent,
            false,
            customerProtectionSatisfied,
            constitutionalFloorSatisfied,
            requestsCalculatedRisk,
            CurrentVersions));
}