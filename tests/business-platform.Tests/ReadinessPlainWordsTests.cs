// Implements: work-contracts/WC-176-customer-journeys-registration-trial-hire-and-pages.md WC176-R008
// Constitutional basis: C-042, C-049, C-059

using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class ReadinessPlainWordsTests
{
    [Theory]
    [InlineData("Required induction context must be confirmed.", "learn about your business", true)]
    [InlineData("Customer verification is required for every active goal.", "goal", true)]
    [InlineData("An accepted employment contract is required.", "employment agreement", true)]
    [InlineData(
        "Skill CUSTOMER_PROFILING lacks an exact active runtime binding.",
        "set up on our side",
        false
    )]
    [InlineData("Professional Runtime readiness is not current.", "workplace", false)]
    [InlineData("A reason nobody anticipated.", "still being set up", false)]
    public void EveryTechnicalReasonBecomesPlainWordsWithOneNextStep(
        string reason,
        string expected,
        bool customerCanAct
    )
    {
        var item = ReadinessPlainWords.Translate(reason);

        Assert.Contains(expected, item.Missing, StringComparison.OrdinalIgnoreCase);
        Assert.False(string.IsNullOrWhiteSpace(item.NextStep));
        Assert.Equal(customerCanAct, item.CustomerCanAct);
        Assert.DoesNotContain("Skill CUSTOMER_PROFILING", item.Missing, StringComparison.Ordinal);
    }

    [Fact]
    public void DuplicatesCollapseAndThingsTheCustomerCanDoComeFirst()
    {
        var items = ReadinessPlainWords.Translate([
            "The admitted artifact and runtime binding coordinates are unavailable.",
            "Required induction context must be confirmed.",
            "The current admission revision is unavailable.",
            "Customer verification is required for every active goal.",
            "At least one active goal must be customer-verified.",
        ]);

        Assert.True(items[0].CustomerCanAct);
        Assert.Equal(items.Count, items.Select(item => item.Missing).Distinct().Count());
        Assert.False(items[^1].CustomerCanAct);
    }
}
