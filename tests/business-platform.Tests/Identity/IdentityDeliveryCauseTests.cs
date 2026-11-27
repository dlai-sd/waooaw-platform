// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R002, WC175-R003
// Constitutional basis: C-023, C-049, C-059

using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests.Identity;

public sealed class IdentityDeliveryCauseTests
{
    [Theory]
    [InlineData("REGISTRATION_VERIFICATION_DENIED")]
    [InlineData("REGISTRATION_RECIPIENT_DENIED")]
    [InlineData("REGISTRATION_PROVIDER_REJECTED")]
    [InlineData("AUTHENTICATION_TEMPLATE_APPROVAL_REQUIRED")]
    [InlineData("AUTHENTICATION_TEMPLATE_CONFIGURATION_REQUIRED")]
    [InlineData("CONFIGURATION_DENIED")]
    [InlineData("WINDOW_CLOSED")]
    public void RefusalBeforeTheProviderIsReached_IsReportedAsNotSent(string cause)
    {
        var exception = new IdentityDeliveryUnavailableException(
            "Verification delivery is unavailable.",
            cause
        );

        Assert.True(exception.NotSent);
        Assert.Equal(cause, exception.Cause);
    }

    [Theory]
    [InlineData("REGISTRATION_PROVIDER_OUTCOME_UNKNOWN")]
    [InlineData("DISPATCH_FAILED_TimeoutException")]
    [InlineData("")]
    [InlineData(null)]
    public void AnOutcomeThatMayHaveSentACode_IsNeverReportedAsNotSent(string? cause)
    {
        var exception = new IdentityDeliveryUnavailableException(
            "Verification delivery is unavailable.",
            cause
        );

        Assert.False(exception.NotSent);
    }

    [Fact]
    public void TheMessageStaysTheCustomerSafeSentence_NotTheInternalCause()
    {
        var exception = new IdentityDeliveryUnavailableException(
            "Verification delivery is unavailable.",
            "REGISTRATION_VERIFICATION_DENIED"
        );

        Assert.Equal("Verification delivery is unavailable.", exception.Message);
        Assert.DoesNotContain("REGISTRATION", exception.Message, StringComparison.Ordinal);
    }
}
