// Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §3, §5, §7.1
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, C-076, C-079

using Waooaw.BusinessPlatform.Services.CustomerAssets;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

public sealed class CustomerAssetPolicyTests
{
    private static readonly Guid Tenant = Guid.Parse("11111111-1111-1111-1111-111111111111");
    private static readonly Guid Relationship = Guid.Parse("22222222-2222-2222-2222-222222222222");

    [Fact]
    public void ExactTenantRightsAndTimeBoundedDeliveryReferenceAreRequired()
    {
        var asset = new CustomerAssetVersion(
            Tenant,
            Relationship,
            "asset-1",
            "1",
            $"sha256:{new string('a', 64)}",
            "customer",
            new HashSet<string> { "FACEBOOK" },
            new HashSet<string> { "ORGANIC_SOCIAL" },
            "CUSTOMER_OWNED",
            null,
            null,
            null,
            DateTimeOffset.UtcNow.AddDays(1),
            null,
            "CUSTOMER_ASSET",
            "https://assets.example.com/asset-1?expires=2026-10-10T00:00:00Z"
        );

        Assert.True(
            CustomerAssetPolicy.IsAuthorized(
                asset,
                Tenant,
                Relationship,
                "FACEBOOK",
                "ORGANIC_SOCIAL",
                DateTimeOffset.UtcNow
            )
        );
        Assert.False(
            CustomerAssetPolicy.IsAuthorized(
                asset,
                Guid.NewGuid(),
                Relationship,
                "FACEBOOK",
                "ORGANIC_SOCIAL",
                DateTimeOffset.UtcNow
            )
        );
    }

    [Fact]
    public void ExpiredOrNonTimeBoundedAssetsFailClosed()
    {
        var asset = new CustomerAssetVersion(
            Tenant,
            Relationship,
            "asset-1",
            "1",
            $"sha256:{new string('a', 64)}",
            "customer",
            new HashSet<string> { "FACEBOOK" },
            new HashSet<string> { "ORGANIC_SOCIAL" },
            "CUSTOMER_OWNED",
            null,
            null,
            null,
            DateTimeOffset.UtcNow.AddMinutes(-1),
            null,
            "CUSTOMER_ASSET",
            "https://assets.invalid/asset-1"
        );

        Assert.False(
            CustomerAssetPolicy.IsAuthorized(
                asset,
                Tenant,
                Relationship,
                "FACEBOOK",
                "ORGANIC_SOCIAL",
                DateTimeOffset.UtcNow
            )
        );
    }

    [Fact]
    public void InvalidPlaceholderHostFailsClosed()
    {
        var asset = new CustomerAssetVersion(
            Tenant,
            Relationship,
            "asset-1",
            "1",
            $"sha256:{new string('a', 64)}",
            "customer",
            new HashSet<string> { "FACEBOOK" },
            new HashSet<string> { "ORGANIC_SOCIAL" },
            "CUSTOMER_OWNED",
            null,
            null,
            null,
            DateTimeOffset.UtcNow.AddDays(1),
            null,
            "CUSTOMER_ASSET",
            "https://assets.invalid/asset-1?expires=2026-10-10T00:00:00Z"
        );

        Assert.False(
            CustomerAssetPolicy.IsAuthorized(
                asset,
                Tenant,
                Relationship,
                "FACEBOOK",
                "ORGANIC_SOCIAL",
                DateTimeOffset.UtcNow
            )
        );
    }
}
