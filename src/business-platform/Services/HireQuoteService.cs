// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R013
// Constitutional basis: C-023, C-059, C-063

using System.Security.Cryptography;
using System.Text;

namespace Waooaw.BusinessPlatform.Services;

/// <summary>One customer price for a Hire, resolved from the billing owner's for-sale package. Never built from client input or the agent descriptor.</summary>
public sealed record HireQuote(
    Guid PackageId,
    string PackageCode,
    int BillingPeriodDays,
    long GrossAmountInrPaise,
    long GstAmountInrPaise,
    long BasePriceInrPaise,
    string QuoteVersion
)
{
    public const string Currency = "INR";
    public const string MonthlyCadence = "MONTHLY";

    public string Cadence => MonthlyCadence;
}

/// <summary>No monthly package is on sale for the professional version, or the requested package code is not one of them.</summary>
public sealed class HireQuoteNotOfferedException(string message) : Exception(message);

/// <summary>The billing owner could not answer, so no amount exists; the caller must not fall back to any other price.</summary>
public sealed class HireQuoteUnavailableException(string message, Exception? inner = null)
    : Exception(message, inner);

public sealed class HireQuoteService(IPackageCatalogGateway gateway)
{
    public const int PageSize = 100;
    public const int MaximumPages = 5;
    private const int MonthlyMinimumDays = 28;
    private const int MonthlyMaximumDays = 31;

    public async Task<HireQuote> ResolveAsync(
        Guid tenantId,
        string actorSubject,
        string professionalType,
        string professionalVersion,
        string? packageCode,
        string correlationId,
        CancellationToken ct
    )
    {
        var candidates = new List<OwnerPackage>();
        string? cursor = null;
        try
        {
            for (var page = 0; page < MaximumPages; page++)
            {
                var result = await gateway.ListAsync(
                    tenantId,
                    actorSubject,
                    professionalType,
                    professionalVersion,
                    cursor,
                    PageSize,
                    correlationId,
                    ct
                );
                candidates.AddRange(result.Items);
                cursor = result.NextCursor;
                if (string.IsNullOrEmpty(cursor))
                    break;
            }
        }
        catch (Exception exception)
            when (exception is PackageCatalogUnavailableException or PackageCatalogCursorException)
        {
            throw new HireQuoteUnavailableException(
                "The package catalogue owner is unavailable.",
                exception
            );
        }
        if (!string.IsNullOrEmpty(cursor))
            throw new HireQuoteUnavailableException(
                "The package catalogue is larger than the supported quote window."
            );

        var offered = candidates
            .Where(item =>
                string.Equals(item.AgentType, professionalType, StringComparison.OrdinalIgnoreCase)
                && string.Equals(item.AgentVersion, professionalVersion, StringComparison.Ordinal)
                && item.BillingPeriodDays is >= MonthlyMinimumDays and <= MonthlyMaximumDays
                && item.PriceInclGstPaise > 0
                && item.GstPaise >= 0
                && item.GstPaise <= item.PriceInclGstPaise
            )
            .ToList();
        var selected = string.IsNullOrWhiteSpace(packageCode)
            ? offered
                .OrderBy(item => item.PriceInclGstPaise)
                .ThenBy(item => item.PackageCode, StringComparer.Ordinal)
                .FirstOrDefault()
            : offered.FirstOrDefault(item =>
                string.Equals(item.PackageCode, packageCode.Trim(), StringComparison.Ordinal)
            );
        if (selected is null)
            throw new HireQuoteNotOfferedException(
                string.IsNullOrWhiteSpace(packageCode)
                    ? "No monthly package is on sale for this professional."
                    : "The selected package is not on sale for this professional."
            );
        return new HireQuote(
            selected.PackageId,
            selected.PackageCode,
            selected.BillingPeriodDays,
            selected.PriceInclGstPaise,
            selected.GstPaise,
            selected.BasePricePaise,
            VersionOf(selected, professionalType, professionalVersion)
        );
    }

    private static string VersionOf(
        OwnerPackage package,
        string professionalType,
        string professionalVersion
    ) =>
        Convert
            .ToHexString(
                SHA256.HashData(
                    Encoding.UTF8.GetBytes(
                        string.Join(
                            '|',
                            "hire-quote-v1",
                            package.PackageId.ToString("D"),
                            package.PackageCode,
                            professionalType.ToUpperInvariant(),
                            professionalVersion,
                            package.BillingPeriodDays,
                            package.PriceInclGstPaise,
                            package.GstPaise,
                            package.BasePricePaise
                        )
                    )
                )
            )
            .ToLowerInvariant();
}
