// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-029 (scope-boundary record), C-076 (≥90% unit test coverage)

using FluentAssertions;
using Grpc.Core;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Interceptors;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Interceptors;

/// <summary>
/// Unit tests for TenantMetadataInterceptor.
/// Verifies that tenant isolation is enforced on every RPC call (C-029).
/// </summary>
public sealed class TenantMetadataInterceptorTests
{
    private readonly TenantMetadataInterceptor _sut;

    public TenantMetadataInterceptorTests()
    {
        _sut = new TenantMetadataInterceptor(NullLogger<TenantMetadataInterceptor>.Instance);
    }

    // ── UnaryServerHandler — missing header ───────────────────────────────────

    [Fact]
    public async Task UnaryServerHandler_MissingTenantHeader_ThrowsUnauthenticated()
    {
        // Arrange
        var context = CreateServerCallContext(metadata: new Metadata());
        var continuationCalled = false;

        Task<string> Continuation(string req, ServerCallContext ctx)
        {
            continuationCalled = true;
            return Task.FromResult("ok");
        }

        // Act
        var act = async () => await _sut.UnaryServerHandler(
            "request", context, (UnaryServerMethod<string, string>)Continuation);

        // Assert
        var ex = await act.Should().ThrowAsync<RpcException>();
        ex.Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
        ex.Which.Status.Detail.Should().Contain(TenantMetadataInterceptor.TenantIdMetadataKey);
        continuationCalled.Should().BeFalse("continuation must not be called when tenant header is missing");
    }

    [Fact]
    public async Task UnaryServerHandler_EmptyTenantHeader_ThrowsUnauthenticated()
    {
        // Arrange
        var metadata = new Metadata { { TenantMetadataInterceptor.TenantIdMetadataKey, "" } };
        var context = CreateServerCallContext(metadata);

        // Act
        var act = async () => await _sut.UnaryServerHandler(
            "request", context,
            (UnaryServerMethod<string, string>)((_, _) => Task.FromResult("ok")));

        // Assert
        var ex = await act.Should().ThrowAsync<RpcException>();
        ex.Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    [Fact]
    public async Task UnaryServerHandler_InvalidUuidTenantHeader_ThrowsUnauthenticated()
    {
        // Arrange
        var metadata = new Metadata { { TenantMetadataInterceptor.TenantIdMetadataKey, "not-a-uuid" } };
        var context = CreateServerCallContext(metadata);

        // Act
        var act = async () => await _sut.UnaryServerHandler(
            "request", context,
            (UnaryServerMethod<string, string>)((_, _) => Task.FromResult("ok")));

        // Assert
        var ex = await act.Should().ThrowAsync<RpcException>();
        ex.Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
        ex.Which.Status.Detail.Should().Contain("valid UUID");
    }

    // ── UnaryServerHandler — valid header ─────────────────────────────────────

    [Fact]
    public async Task UnaryServerHandler_ValidTenantHeader_CallsContinuation()
    {
        // Arrange
        var tenantId = Guid.NewGuid();
        var metadata = new Metadata
        {
            { TenantMetadataInterceptor.TenantIdMetadataKey, tenantId.ToString() }
        };
        var context = CreateServerCallContext(metadata);
        var continuationCalled = false;

        Task<string> Continuation(string req, ServerCallContext ctx)
        {
            continuationCalled = true;
            return Task.FromResult("ok");
        }

        // Act
        var result = await _sut.UnaryServerHandler(
            "request", context, (UnaryServerMethod<string, string>)Continuation);

        // Assert
        result.Should().Be("ok");
        continuationCalled.Should().BeTrue();
    }

    [Fact]
    public async Task UnaryServerHandler_ValidTenantHeader_SetsTenantIdOnAsyncLocal()
    {
        // Arrange
        var tenantId = Guid.NewGuid();
        var metadata = new Metadata
        {
            { TenantMetadataInterceptor.TenantIdMetadataKey, tenantId.ToString() }
        };
        var context = CreateServerCallContext(metadata);
        Guid capturedTenantId = Guid.Empty;

        Task<string> Continuation(string req, ServerCallContext ctx)
        {
            capturedTenantId = TenantMetadataInterceptor.CurrentTenantId;
            return Task.FromResult("ok");
        }

        // Act
        await _sut.UnaryServerHandler(
            "request", context, (UnaryServerMethod<string, string>)Continuation);

        // Assert
        capturedTenantId.Should().Be(tenantId);
    }

    [Fact]
    public async Task UnaryServerHandler_HeaderKeyIsCaseInsensitive()
    {
        // Arrange — use uppercase key
        var tenantId = Guid.NewGuid();
        var metadata = new Metadata
        {
            { TenantMetadataInterceptor.TenantIdMetadataKey.ToUpperInvariant(), tenantId.ToString() }
        };
        var context = CreateServerCallContext(metadata);
        var continuationCalled = false;

        Task<string> Continuation(string req, ServerCallContext ctx)
        {
            continuationCalled = true;
            return Task.FromResult("ok");
        }

        // Act
        var result = await _sut.UnaryServerHandler(
            "request", context, (UnaryServerMethod<string, string>)Continuation);

        // Assert
        result.Should().Be("ok");
        continuationCalled.Should().BeTrue();
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private static FakeServerCallContext CreateServerCallContext(Metadata metadata)
        => new(metadata);

    /// <summary>
    /// Minimal ServerCallContext fake sufficient for interceptor testing.
    /// Only RequestHeaders and Method are used by TenantMetadataInterceptor.
    /// </summary>
    private sealed class FakeServerCallContext : ServerCallContext
    {
        private readonly Metadata _requestHeaders;

        public FakeServerCallContext(Metadata requestHeaders)
        {
            _requestHeaders = requestHeaders;
        }

        protected override string MethodCore => "/constitutional.v1.ConstitutionalService/RecordEvidence";
        protected override string HostCore => "localhost";
        protected override string PeerCore => "127.0.0.1";
        protected override DateTime DeadlineCore => DateTime.MaxValue;
        protected override Metadata RequestHeadersCore => _requestHeaders;
        protected override CancellationToken CancellationTokenCore => CancellationToken.None;
        protected override Metadata ResponseTrailersCore => new();
        protected override Status StatusCore { get; set; }
        protected override WriteOptions? WriteOptionsCore { get; set; }
        protected override AuthContext AuthContextCore => new(null, new Dictionary<string, List<AuthProperty>>());

        protected override ContextPropagationToken CreatePropagationTokenCore(ContextPropagationOptions? options)
            => throw new NotSupportedException();

        protected override Task WriteResponseHeadersAsyncCore(Metadata responseHeaders)
            => Task.CompletedTask;
    }
}