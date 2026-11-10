using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.ConversationWhatsAppFitness;

public sealed class ConversationModelCostTests
{
    [Theory]
    [InlineData(0, 0, 8192, 2048, 0)]
    [InlineData(1, 1, 1, 1, 2)]
    [InlineData(1000000, 1000000, 8192, 2048, 10240)]
    [InlineData(1000000, 1000000, 8192, 2500, 10692)]
    public void CostRoundsEachCategoryUpAndDoesNotClampOverruns(long inputRate, long outputRate,
        long inputTokens, long outputTokens, long expected)
    {
        Assert.Equal((decimal)expected, ConversationInferenceOwner.Cost(inputRate, outputRate, inputTokens, outputTokens));
    }

    [Fact]
    public void CostDoesNotOverflowBeforeScalingLargeReportedUsage()
    {
        var cost = ConversationInferenceOwner.Cost(1000000000, 1000000000, long.MaxValue, long.MaxValue);
        Assert.True(cost > long.MaxValue);
    }

    [Fact]
    public void NegativeUsageIsExplicitlyDenied()
    {
        Assert.Throws<ConversationStateConflictException>(() => ConversationInferenceOwner.Cost(1, 1, -1, 0));
    }
}
