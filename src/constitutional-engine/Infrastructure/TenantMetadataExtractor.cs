// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-029 (scope-boundary record), C-023 (Evidence First)

using Grpc.Core;
using Microsoft.Extensions.Logging;

namespace Waooaw.ConstitutionalEngine.Infrastructure;

/// <summary>
/// Production implementation of <see cref="ITenantMetadataExtractor"/>.
/// Reads the "x-tenant-id" gRPC metadata key and validates it as a UUID.
/// Returns UNAUTHENTICATED if absent or malformed — per the proto transport notes.
/// </summary>
public sealed class TenantMetadataExtractor : ITenantMetadataExtractor
{
    /// <summary>
    /// The gRPC metadata key carrying the tenant UUID.
    /// Defined in constitutional_service.proto transport notes.
    /// </summary>
    public const string TenantIdMetadataKey = "x-tenant-id";

    private readonly ILogger<TenantMetadataExtractor> _logger;

    public TenantMetadataExtractor(ILogger<TenantMetadataExtractor> logger)
    {
        _logger = logger;
    }

    // C-073: Implements C-029 (scope-boundary record) — tenant ID extraction is the
    // enforcement point ensuring every operation is scoped to a valid tenant.
    /// <inheritdoc />
    public string ExtractTenantId(ServerCallContext context)
    {
        var entry = context.RequestHeaders.FirstOrDefault(
            h => string.Equals(h.Key, TenantIdMetadataKey, StringComparison.OrdinalIgnoreCase));

        if (entry is null || string.IsNullOrWhiteSpace(entry.Value))
        {
            _logger.LogWarning(
                "gRPC call missing required metadata key '{MetadataKey}'. Method={Method}",
                TenantIdMetadataKey, context.Method);

            throw new RpcException(new Status(
                StatusCode.Unauthenticated,
                $"Required metadata '{TenantIdMetadataKey}' is absent. " +
                "Callers must propagate the tenant UUID from the customer JWT."));
        }

        if (!Guid.TryParse(entry.Value, out _))
        {
            _logger.LogWarning(
                "gRPC call has malformed '{MetadataKey}' value '{Value}'. Method={Method}",
                TenantIdMetadataKey, entry.Value, context.Method);

            throw new RpcException(new Status(
                StatusCode.Unauthenticated,
                $"Metadata '{TenantIdMetadataKey}' value '{entry.Value}' is not a valid UUID."));
        }

        return entry.Value;
    }
}