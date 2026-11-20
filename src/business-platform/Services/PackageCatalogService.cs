// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C4-13
// Constitutional basis: C-023, C-026, C-059, C-063, ADR-051

using System.Globalization;
using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;
using Waooaw.BusinessPlatform.Infrastructure;

namespace Waooaw.BusinessPlatform.Services;

public sealed record MarketplacePackageComponent(
    string ComponentId,
    string Label,
    int Quantity,
    string Cadence,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] int? SelectableMaximum
);

public sealed record MarketplacePackage(
    Guid PackageId,
    string PackageCode,
    string DisplayName,
    string AgentType,
    string AgentVersion,
    int BillingPeriodDays,
    long PriceInclGstPaise,
    long BasePricePaise,
    long GstPaise,
    int GstRatePercent,
    string TaxTreatment,
    IReadOnlyList<MarketplacePackageComponent> Components
);

public sealed record MarketplacePackageList(
    string SchemaVersion,
    IReadOnlyList<MarketplacePackage> Items,
    [property: JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)] string? NextCursor
);

/// <summary>A for-sale package exactly as the billing owner publishes it: ids, prices and quantities, no costs or recipes.</summary>
public sealed record OwnerPackageComponent(
    string ComponentId,
    int Quantity,
    string Cadence,
    int? SelectableMaximum
);

public sealed record OwnerPackage(
    Guid PackageId,
    string PackageCode,
    string DisplayName,
    string AgentType,
    string AgentVersion,
    int BillingPeriodDays,
    long PriceInclGstPaise,
    long BasePricePaise,
    long GstPaise,
    int GstRatePercent,
    IReadOnlyList<OwnerPackageComponent> Components
);

public sealed record OwnerPackagePage(IReadOnlyList<OwnerPackage> Items, string? NextCursor);

public sealed class PackageCatalogUnavailableException(string message, Exception? inner = null)
    : Exception(message, inner);

public sealed class PackageCatalogCursorException() : Exception("The package cursor is not valid.");

public interface IPackageCatalogGateway
{
    Task<OwnerPackagePage> ListAsync(
        Guid tenantId,
        string actorSubject,
        string agentType,
        string agentVersion,
        string? cursor,
        int limit,
        string correlationId,
        CancellationToken ct
    );
}

public sealed class UnconfiguredPackageCatalogGateway : IPackageCatalogGateway
{
    public Task<OwnerPackagePage> ListAsync(
        Guid tenantId,
        string actorSubject,
        string agentType,
        string agentVersion,
        string? cursor,
        int limit,
        string correlationId,
        CancellationToken ct
    ) =>
        throw new PackageCatalogUnavailableException(
            "The package catalogue owner is not configured."
        );
}

/// <summary>The customer-facing words for a component; the default humanises the component id until the agent supplies its own vocabulary.</summary>
public interface IPackageComponentLabelSource
{
    string LabelFor(string agentType, string componentId);
}

public sealed class HumanizedComponentLabelSource : IPackageComponentLabelSource
{
    public string LabelFor(string agentType, string componentId)
    {
        var words = componentId
            .Replace('_', ' ')
            .Replace('-', ' ')
            .Replace('.', ' ')
            .Trim()
            .ToLowerInvariant();
        return words.Length == 0 ? componentId : char.ToUpperInvariant(words[0]) + words[1..];
    }
}

/// <summary>Turns the owner's for-sale catalogue into the customer-safe package list; prices are always GST inclusive.</summary>
public sealed class PackageCatalogService(
    IPackageCatalogGateway gateway,
    IPackageComponentLabelSource labels
)
{
    public const string GstInclusive = "GST_INCLUSIVE";
    public const string SchemaVersion = "1.0";
    public const int DefaultLimit = 25;
    public const int MaximumLimit = 100;
    public const int MaximumCursorLength = 256;

    public async Task<MarketplacePackageList> ListAsync(
        Guid tenantId,
        string actorSubject,
        string agentType,
        string agentVersion,
        string? cursor,
        int? limit,
        string correlationId,
        CancellationToken ct
    )
    {
        var page = await gateway.ListAsync(
            tenantId,
            actorSubject,
            agentType,
            agentVersion,
            cursor,
            limit ?? DefaultLimit,
            correlationId,
            ct
        );
        return new MarketplacePackageList(
            SchemaVersion,
            page.Items.Select(item => new MarketplacePackage(
                    item.PackageId,
                    item.PackageCode,
                    item.DisplayName,
                    item.AgentType,
                    item.AgentVersion,
                    item.BillingPeriodDays,
                    item.PriceInclGstPaise,
                    item.BasePricePaise,
                    item.GstPaise,
                    item.GstRatePercent,
                    GstInclusive,
                    item.Components.Select(component => new MarketplacePackageComponent(
                            component.ComponentId,
                            labels.LabelFor(item.AgentType, component.ComponentId),
                            component.Quantity,
                            component.Cadence,
                            component.SelectableMaximum
                        ))
                        .ToList()
                ))
                .ToList(),
            page.NextCursor
        );
    }
}

public sealed class AuthenticatedPackageCatalogGateway : IPackageCatalogGateway, IDisposable
{
    public const string Route =
        "/internal/v1/marketplace/agents/{agentType}/versions/{agentVersion}/packages";
    public const string Operation = "wbeListForSalePackages";
    public const string Purpose = "PACKAGE_CATALOG_READ";

    private const string EmptyDigest =
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

    private static readonly JsonSerializerOptions Json = new(JsonSerializerDefaults.Web);

    private readonly WorkloadIdentityClient _identity;
    private readonly HttpClient _client;

    public AuthenticatedPackageCatalogGateway(WorkloadIdentityClient identity, Uri endpoint)
    {
        _identity = identity;
        _client = identity.CreateClient(endpoint, "billing-engine");
    }

    public async Task<OwnerPackagePage> ListAsync(
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
        var envelope = _identity.Sign(
            new DelegatedRequestContext(
                actorSubject,
                "PROFESSIONAL",
                tenantId.ToString("D"),
                string.Empty,
                Purpose,
                $"{agentType}|{agentVersion}",
                correlationId,
                null,
                new Dictionary<string, string>(),
                correlationId
            ),
            _identity.GetAudience("billing-engine"),
            "GET",
            Route,
            Operation,
            1,
            EmptyDigest,
            DateTimeOffset.UtcNow
        );
        var path =
            $"/internal/v1/marketplace/agents/{Uri.EscapeDataString(agentType)}/versions/{Uri.EscapeDataString(agentVersion)}/packages?limit={limit.ToString(CultureInfo.InvariantCulture)}";
        if (!string.IsNullOrEmpty(cursor))
            path += $"&after={Uri.EscapeDataString(cursor)}";
        using var request = new HttpRequestMessage(HttpMethod.Get, path);
        request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", envelope);
        request.Headers.Add("X-Correlation-ID", correlationId);
        try
        {
            using var response = await _client.SendAsync(request, ct);
            if (response.StatusCode == HttpStatusCode.UnprocessableEntity)
                throw new PackageCatalogCursorException();
            if (!response.IsSuccessStatusCode)
                throw new PackageCatalogUnavailableException(
                    $"The package catalogue owner returned {(int)response.StatusCode}."
                );
            var page =
                await response.Content.ReadFromJsonAsync<OwnerPackagePage>(Json, ct)
                ?? throw new PackageCatalogUnavailableException(
                    "The package catalogue owner returned no page."
                );
            return page;
        }
        catch (Exception exception)
            when (exception is HttpRequestException or TaskCanceledException or JsonException)
        {
            throw new PackageCatalogUnavailableException(
                "The package catalogue owner did not answer.",
                exception
            );
        }
    }

    public void Dispose() => _client.Dispose();
}
