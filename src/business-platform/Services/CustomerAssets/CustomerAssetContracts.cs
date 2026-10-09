// Implements: architecture/reference/components/dma-content-and-social-publication-solution-contract.md §3, §5, §7.1
// Constitutional basis: C-005, C-023, C-026, C-059, C-063, C-079

namespace Waooaw.BusinessPlatform.Services.CustomerAssets;

public sealed record CustomerAssetVersion(
    Guid TenantId,
    Guid RelationshipId,
    string AssetRef,
    string Version,
    string Digest,
    string OwnerRef,
    IReadOnlySet<string> PermittedChannels,
    IReadOnlySet<string> PermittedUses,
    string RightsBasis,
    string? LikenessAuthorityRef,
    string? VoiceAuthorityRef,
    string? Disclosure,
    DateTimeOffset? ExpiresAt,
    DateTimeOffset? WithdrawnAt,
    string RetentionClass,
    string DeliveryReference
);

public interface ICustomerAssetOwner
{
    CustomerAssetVersion? GetAuthorizedVersion(
        Guid tenantId,
        Guid relationshipId,
        string assetRef,
        string version
    );
}

public static class CustomerAssetPolicy
{
    public static bool IsAuthorized(
        CustomerAssetVersion asset,
        Guid tenantId,
        Guid relationshipId,
        string channel,
        string use,
        DateTimeOffset now
    )
    {
        return asset.TenantId == tenantId
            && asset.RelationshipId == relationshipId
            && asset.WithdrawnAt is null
            && (asset.ExpiresAt is null || asset.ExpiresAt > now)
            && asset.PermittedChannels.Contains(channel)
            && asset.PermittedUses.Contains(use)
            && asset.Digest.StartsWith("sha256:", StringComparison.Ordinal)
            && asset.Digest.Length == 71
            && !string.IsNullOrWhiteSpace(asset.OwnerRef)
            && !string.IsNullOrWhiteSpace(asset.RightsBasis)
            && IsTimeBoundedReference(asset.DeliveryReference);
    }

    private static bool IsTimeBoundedReference(string value)
    {
        return Uri.TryCreate(value, UriKind.Absolute, out var uri)
            && uri.Scheme == Uri.UriSchemeHttps
            && uri.Host.Length > 0
            && !uri.Host.EndsWith(".invalid", StringComparison.OrdinalIgnoreCase)
            && !value.Contains("CHANGEME", StringComparison.OrdinalIgnoreCase)
            && !value.Contains("PLACEHOLDER", StringComparison.OrdinalIgnoreCase)
            && !value.Contains("fixture", StringComparison.OrdinalIgnoreCase)
            && uri.Query.Contains("expires=", StringComparison.OrdinalIgnoreCase);
    }
}
