// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-023 (Evidence First), C-029 (scope-boundary record)

using Grpc.Core;
using Grpc.Core.Interceptors;

namespace Waooaw.ConstitutionalEngine.Interceptors;

/// <summary>
/// gRPC server interceptor that extracts and validates the x-tenant-id metadata header
/// on every inbound RPC call. If the header is absent or not a valid UUID, the call
/// is rejected with UNAUTHENTICATED (per the proto transport notes).
///
/// The validated tenant ID is stored in AsyncLocal state so downstream service
/// implementations can retrieve it without threading concerns.
/// </summary>
public sealed class TenantMetadataInterceptor : Interceptor
{
    // C-029: tenant isolation — every RPC must carry a valid tenant ID
    public const string TenantIdMetadataKey = "x-tenant-id";

    private static readonly AsyncLocal<Guid> _currentTenantId = new();

    /// <summary>Returns the tenant ID extracted from the current RPC call's metadata.</summary>
    public static Guid CurrentTenantId => _currentTenantId.Value;

    private readonly ILogger<TenantMetadataInterceptor> _logger;

    public TenantMetadataInterceptor(ILogger<TenantMetadataInterceptor> logger)
    {
        _logger = logger;
    }

    // C-029: enforce tenant boundary on every unary call
    public override async Task<TResponse> UnaryServerHandler<TRequest, TResponse>(
        TRequest request,
        ServerCallContext context,
        UnaryServerMethod<TRequest, TResponse> continuation)
    {
        ExtractAndValidateTenantId(context);
        return await continuation(request, context);
    }

    private void ExtractAndValidateTenantId(ServerCallContext context)
    {
        var tenantEntry = context.RequestHeaders.FirstOrDefault(
            h => h.Key.Equals(TenantIdMetadataKey, StringComparison.OrdinalIgnoreCase));

        if (tenantEntry is null || string.IsNullOrWhiteSpace(tenantEntry.Value))
        {
            _logger.LogWarning(
                "RPC {Method} rejected: missing {MetadataKey} metadata header",
                context.Method, TenantIdMetadataKey);

            throw new RpcException(new Status(
                StatusCode.Unauthenticated,
                $"Missing required metadata header: {TenantIdMetadataKey}"));
        }

        if (!Guid.TryParse(tenantEntry.Value, out var tenantId))
        {
            _logger.LogWarning(
                "RPC {Method} rejected: {MetadataKey} value '{Value}' is not a valid UUID",
                context.Method, TenantIdMetadataKey, tenantEntry.Value);

            throw new RpcException(new Status(
                StatusCode.Unauthenticated,
                $"Metadata header {TenantIdMetadataKey} must be a valid UUID"));
        }

        _currentTenantId.Value = tenantId;

        _logger.LogDebug(
            "RPC {Method}: tenant {TenantId} authenticated via metadata",
            context.Method, tenantId);
    }
}