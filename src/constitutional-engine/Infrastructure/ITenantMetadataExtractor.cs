// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-029 (scope-boundary record), C-023 (Evidence First)

using Grpc.Core;

namespace Waooaw.ConstitutionalEngine.Infrastructure;

/// <summary>
/// Extracts and validates the tenant identifier from gRPC call metadata.
/// The tenant ID is carried in the "x-tenant-id" metadata key on every RPC call.
/// If the metadata is absent or not a valid UUID, throws RpcException with UNAUTHENTICATED.
///
/// C-029: Every evidence record is tenant-scoped — this extractor is the enforcement point.
/// </summary>
public interface ITenantMetadataExtractor
{
    /// <summary>
    /// Extracts the tenant ID from the gRPC call context metadata.
    /// </summary>
    /// <param name="context">The gRPC server call context.</param>
    /// <returns>The tenant ID as a string (canonical UUID format).</returns>
    /// <exception cref="RpcException">
    /// Thrown with StatusCode.Unauthenticated if "x-tenant-id" metadata is absent or invalid.
    /// </exception>
    string ExtractTenantId(ServerCallContext context);
}