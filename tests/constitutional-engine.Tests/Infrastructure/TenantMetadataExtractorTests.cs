// Implements: architecture/reference/components/constitutional-engine.md
// constitutional_basis: C-076 (≥90% unit test coverage), C-029 (scope-boundary record), C-059 (Traceability)

using FluentAssertions;
using Grpc.Core;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Waooaw.ConstitutionalEngine.Infrastructure;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Infrastructure;

/// <summary>
/// Unit tests for <see cref="TenantMetadataExtractor"/>.
/// C-076: ≥90% coverage required.
/// C-029: Tenant extraction is the scope-boundary enforcement point — every path must be tested.
/// </summary>
public sealed class TenantMetadataExtractorTests
{
    private readonly TenantMetadataExtractor _sut;

    public TenantMetadataExtractorTests()
    {
        _sut = new TenantMetadataExtractor(NullLogger<TenantMetadataExtractor>.Instance);
    }

    // ─── Happy path ───────────────────────────────────────────────────────────

    [Fact]
    public void ExtractTenantId_ValidUuid_ReturnsTenantId()
    {
        // Arrange
        var tenantId = Guid.NewGuid().ToString();
        var context = BuildContextWithMetadata(TenantMetadataExtractor.TenantIdMetadataKey, tenantId);

        // Act
        var result = _sut.ExtractTenantId(context);

        // Assert
        result.Should().Be(tenantId);
    }

    [Fact]
    public void ExtractTenantId_MetadataKeyIsCaseInsensitive_ReturnsTenantId()
    {
        // Arrange — gRPC metadata keys are lowercase by convention but extractor must be tolerant
        var tenantId = Guid.NewGuid().ToString();
        var context = BuildContextWithMetadata("X-Tenant-Id", tenantId);

        // Act
        var result = _sut.ExtractTenantId(context);

        // Assert
        result.Should().Be(tenantId);
    }

    // ─── Missing metadata ─────────────────────────────────────────────────────

    [Fact]
    public void ExtractTenantId_MissingMetadata_ThrowsUnauthenticated()
    {
        // Arrange — no x-tenant-id header
        var context = BuildContextWithMetadata("some-other-key", "some-value");

        // Act
        var act = () => _sut.ExtractTenantId(context);

        // Assert
        act.Should().Throw<RpcException>()
            .Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    [Fact]
    public void ExtractTenantId_EmptyMetadataValue_ThrowsUnauthenticated()
    {
        // Arrange
        var context = BuildContextWithMetadata(TenantMetadataExtractor.TenantIdMetadataKey, "");

        // Act
        var act = () => _sut.ExtractTenantId(context);

        // Assert
        act.Should().Throw<RpcException>()
            .Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    [Fact]
    public void ExtractTenantId_WhitespaceMetadataValue_ThrowsUnauthenticated()
    {
        // Arrange
        var context = BuildContextWithMetadata(TenantMetadataExtractor.TenantIdMetadataKey, "   ");

        // Act
        var act = () => _sut.ExtractTenantId(context);

        // Assert
        act.Should().Throw<RpcException>()
            .Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    // ─── Malformed UUID ───────────────────────────────────────────────────────

    [Theory]
    [InlineData("not-a-uuid")]
    [InlineData("12345")]
    [InlineData("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")]
    [InlineData("00000000-0000-0000-0000-00000000000Z")]
    public void ExtractTenantId_MalformedUuid_ThrowsUnauthenticated(string malformedValue)
    {
        // Arrange
        var context = BuildContextWithMetadata(TenantMetadataExtractor.TenantIdMetadataKey, malformedValue);

        // Act
        var act = () => _sut.ExtractTenantId(context);

        // Assert
        act.Should().Throw<RpcException>()
            .Which.StatusCode.Should().Be(StatusCode.Unauthenticated);
    }

    [Fact]
    public void ExtractTenantId_MalformedUuid_ErrorMessageContainsTenantIdKey()
    {
        // Arrange
        var context = BuildContextWithMetadata(TenantMetadataExtractor.TenantIdMetadataKey, "not-a-uuid");

        // Act
        var act = () => _sut.ExtractTenantId(context);

        // Assert
        act.Should().Throw<RpcException>()
            .Which.Status.Detail.Should().Contain(TenantMetadataExtractor.TenantIdMetadataKey);
    }

    // ─── Constant ─────────────────────────────────────────────────────────────

    [Fact]
    public void TenantIdMetadataKey_IsCorrectValue()
    {
        // Ensures the metadata key matches the proto transport notes exactly.
        TenantMetadataExtractor.TenantIdMetadataKey.Should().Be("x-tenant-id");
    }

    // ─── Helpers ──────────────────────────────────────────────────────────────

    private static ServerCallContext BuildContextWithMetadata(string key, string value)
    {
        var metadata = new Metadata { { key, value } };
        var mockContext = new Mock<ServerCallContext>();
        mockContext.Setup(c => c.RequestHeaders).Returns(metadata);
        mockContext.Setup(c => c.Method).Returns("/constitutional.v1.ConstitutionalService/Test");
        return mockContext.Object;
    }
}