// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R013
// constitutional_basis: C-023, C-059, C-063

using Waooaw.BusinessPlatform.Services;
using Xunit;

namespace Waooaw.BusinessPlatform.Tests;

internal sealed class FakePackageCatalogGateway(params OwnerPackage[] packages)
    : IPackageCatalogGateway
{
    public List<OwnerPackage> Packages { get; } = [.. packages];
    public Exception? Failure { get; set; }
    public int Calls { get; private set; }

    public Task<OwnerPackagePage> ListAsync(
        Guid tenantId,
        string actorSubject,
        string agentType,
        string agentVersion,
        string? cursor,
        int limit,
        string correlationId,
        CancellationToken ct
    )
    {
        Calls++;
        if (Failure is not null)
            throw Failure;
        var skip = cursor is null ? 0 : int.Parse(cursor);
        var page = Packages.Skip(skip).Take(limit).ToList();
        var next = skip + page.Count < Packages.Count ? (skip + page.Count).ToString() : null;
        return Task.FromResult(new OwnerPackagePage(page, next));
    }
}

internal static class HireQuoteFixtures
{
    public const string AgentType = "DIGITAL_MARKETING_LOCAL_SERVICE";
    public const string AgentVersion = "1.0.0";

    public static OwnerPackage Package(
        string code,
        long gross,
        long? gst = null,
        int days = 30,
        string agentVersion = AgentVersion,
        Guid? id = null
    )
    {
        var tax = gst ?? gross * 18 / 118;
        return new OwnerPackage(
            id ?? Guid.NewGuid(),
            code,
            code,
            AgentType,
            agentVersion,
            days,
            gross,
            gross - tax,
            tax,
            18,
            []
        );
    }
}

public sealed class HireQuoteServiceTests
{
    private static Task<HireQuote> ResolveAsync(
        FakePackageCatalogGateway gateway,
        string? packageCode = null
    ) =>
        new HireQuoteService(gateway).ResolveAsync(
            Guid.NewGuid(),
            Guid.NewGuid().ToString("D"),
            HireQuoteFixtures.AgentType,
            HireQuoteFixtures.AgentVersion,
            packageCode,
            Guid.NewGuid().ToString("D"),
            CancellationToken.None
        );

    [Fact]
    public async Task TheLowestPricedPackageForSaleIsTheDefault()
    {
        var gateway = new FakePackageCatalogGateway(
            HireQuoteFixtures.Package("PRO", 590000),
            HireQuoteFixtures.Package("STARTER", 118000, 18000),
            HireQuoteFixtures.Package("GROWTH", 354000)
        );

        var quote = await ResolveAsync(gateway);

        Assert.Equal("STARTER", quote.PackageCode);
        Assert.Equal(118000, quote.GrossAmountInrPaise);
        Assert.Equal(18000, quote.GstAmountInrPaise);
        Assert.Equal(100000, quote.BasePriceInrPaise);
        Assert.Equal("MONTHLY", quote.Cadence);
        Assert.Matches("^[0-9a-f]{64}$", quote.QuoteVersion);
    }

    [Fact]
    public async Task AnExplicitPackageCodeSelectsThatPackageAndNoOther()
    {
        var gateway = new FakePackageCatalogGateway(
            HireQuoteFixtures.Package("STARTER", 118000),
            HireQuoteFixtures.Package("PRO", 590000)
        );

        Assert.Equal("PRO", (await ResolveAsync(gateway, "PRO")).PackageCode);
        await Assert.ThrowsAsync<HireQuoteNotOfferedException>(() =>
            ResolveAsync(gateway, "ENTERPRISE")
        );
    }

    [Fact]
    public async Task WithNoPackageForSaleThereIsNoAmount()
    {
        await Assert.ThrowsAsync<HireQuoteNotOfferedException>(() =>
            ResolveAsync(new FakePackageCatalogGateway())
        );
    }

    [Fact]
    public async Task OnlyMonthlyPackagesOfTheRequestedVersionAreOffered()
    {
        var gateway = new FakePackageCatalogGateway(
            HireQuoteFixtures.Package("YEARLY", 100000, days: 365),
            HireQuoteFixtures.Package("OLDER", 100000, agentVersion: "0.9.0"),
            HireQuoteFixtures.Package("FREE", 0, 0),
            HireQuoteFixtures.Package("MONTHLY_ONE", 250000, days: 31)
        );

        Assert.Equal("MONTHLY_ONE", (await ResolveAsync(gateway)).PackageCode);
    }

    [Theory]
    [InlineData(typeof(PackageCatalogUnavailableException))]
    [InlineData(typeof(PackageCatalogCursorException))]
    public async Task AnOwnerFailureIsUnavailableAndNeverAFallbackAmount(Type failure)
    {
        var gateway = new FakePackageCatalogGateway(HireQuoteFixtures.Package("STARTER", 118000))
        {
            Failure =
                failure == typeof(PackageCatalogUnavailableException)
                    ? new PackageCatalogUnavailableException("down")
                    : new PackageCatalogCursorException(),
        };

        await Assert.ThrowsAsync<HireQuoteUnavailableException>(() => ResolveAsync(gateway));
    }

    [Fact]
    public async Task APriceChangeProducesANewQuoteVersion()
    {
        var id = Guid.NewGuid();
        var before = await ResolveAsync(
            new FakePackageCatalogGateway(HireQuoteFixtures.Package("STARTER", 118000, id: id))
        );
        var after = await ResolveAsync(
            new FakePackageCatalogGateway(HireQuoteFixtures.Package("STARTER", 129800, id: id))
        );
        var same = await ResolveAsync(
            new FakePackageCatalogGateway(HireQuoteFixtures.Package("STARTER", 118000, id: id))
        );

        Assert.NotEqual(before.QuoteVersion, after.QuoteVersion);
        Assert.Equal(before.QuoteVersion, same.QuoteVersion);
    }

    [Fact]
    public async Task ACatalogueLargerThanTheQuoteWindowIsRefusedNotTruncated()
    {
        var packages = Enumerable
            .Range(0, (HireQuoteService.PageSize * HireQuoteService.MaximumPages) + 1)
            .Select(index => HireQuoteFixtures.Package($"P{index}", 100000 + index))
            .ToArray();

        await Assert.ThrowsAsync<HireQuoteUnavailableException>(() =>
            ResolveAsync(new FakePackageCatalogGateway(packages))
        );
    }
}
