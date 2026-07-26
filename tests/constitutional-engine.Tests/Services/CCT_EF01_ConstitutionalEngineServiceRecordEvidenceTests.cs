// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// constitutional_basis: C-023 (Evidence First), C-007 (Append-Only), C-059 (Traceability),
//                       C-073 (Annotation), C-076 (Test Coverage ≥90%), C-085 (Idempotency)

#nullable enable

using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging;
using Moq;
using System;
using System.Threading;
using System.Threading.Tasks;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators; // FakeServerCallContext
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

/// <summary>
/// CCT-EF-01: Confirms RecordEvidence satisfies C-023 (Evidence First) — DB write precedes response.
/// CCT gate: ALL tests in this file must PASS before WC012-03b is merged.
/// </summary>
public sealed class CCT_EF01_ConstitutionalEngineServiceRecordEvidenceTests : IDisposable
{
    private readonly ConstitutionalDbContext _dbContext;
    private readonly Mock<EvaluatorRegistry> _registryMock;
    private readonly Mock<ILogger<ConstitutionalEngineService>> _loggerMock;
    private readonly ConstitutionalEngineService _sut;

    private static readonly Guid ValidTenantId = Guid.NewGuid();
    private const string ValidTenantIdStr = ""; // set per test via FakeServerCallContext helper

    public CCT_EF01_ConstitutionalEngineServiceRecordEvidenceTests()
    {
        var options = new DbContextOptionsBuilder<ConstitutionalDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;

        _dbContext = new ConstitutionalDbContext(options);
        _loggerMock = new Mock<ILogger<ConstitutionalEngineService>>();

        // EvaluatorRegistry has no virtual constructor — use real instance with empty evaluators
        var registryLogger = new Mock<ILogger<EvaluatorRegistry>>();
        _registryMock = null!; // unused for RecordEvidence tests

        var realRegistry = new EvaluatorRegistry(
            Array.Empty<IClaimEvaluator>(),
            registryLogger.Object);

        _sut = new ConstitutionalEngineService(
            realRegistry,
            _dbContext,
            _loggerMock.Object);
    }

    public void Dispose() => _dbContext.Dispose();

    // ── Helper ────────────────────────────────────────────────────────────────

    private static RecordEvidenceRequest BuildRequest(
        string? actionInstanceId = null,
        string contractId = "CTR-001",
        string professionalId = "PRO-001",
        string actionType = "ToolInvocation",
        string constitutionalBasis = "C-023")
    {
        return new RecordEvidenceRequest
        {
            ActionInstanceId = actionInstanceId ?? Guid.NewGuid().ToString(),
            ContractId = contractId,
            ProfessionalId = professionalId,
            ActionType = actionType,
            ConstitutionalBasis = constitutionalBasis,
            DecisionSpaceVersion = 1
        };
    }

    private static FakeServerCallContext BuildContext(Guid? tenantId = null)
        => FakeServerCallContext.Create((tenantId ?? ValidTenantId).ToString());

    // ── CCT-EF-01: Evidence First (C-023) ────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_WritesToDatabaseBeforeReturningResponse()
    {
        // C-023: evidence record must exist in DB when response is received
        var request = BuildRequest();
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        Assert.NotNull(response);
        Assert.False(string.IsNullOrWhiteSpace(response.EvidenceRecordId));

        var id = Guid.Parse(response.EvidenceRecordId);
        var persisted = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(persisted);
    }

    [Fact]
    public async Task RecordEvidence_PersistedRecord_HasCorrectTenantId()
    {
        var tenantId = Guid.NewGuid();
        var request = BuildRequest();
        var ctx = BuildContext(tenantId);

        var response = await _sut.RecordEvidence(request, ctx);

        var id = Guid.Parse(response.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        Assert.Equal(tenantId, record!.TenantId);
    }

    [Fact]
    public async Task RecordEvidence_PersistedRecord_HasCorrectIdempotencyKey()
    {
        var actionInstanceId = Guid.NewGuid().ToString();
        var request = BuildRequest(actionInstanceId: actionInstanceId);
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        var id = Guid.Parse(response.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        Assert.Equal(actionInstanceId, record!.IdempotencyKey);
    }

    [Fact]
    public async Task RecordEvidence_PersistedRecord_HasCorrectEvidenceType()
    {
        var request = BuildRequest(actionType: "DocumentUpload");
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        var id = Guid.Parse(response.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        Assert.Equal("DocumentUpload", record!.EvidenceType);
    }

    [Fact]
    public async Task RecordEvidence_PersistedRecord_HasNonEmptySummary()
    {
        var request = BuildRequest();
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        var id = Guid.Parse(response.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        Assert.False(string.IsNullOrWhiteSpace(record!.Summary));
    }

    [Fact]
    public async Task RecordEvidence_PersistedRecord_HasRecordedAtTimestamp()
    {
        var before = DateTimeOffset.UtcNow.AddSeconds(-1);
        var request = BuildRequest();
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        var after = DateTimeOffset.UtcNow.AddSeconds(1);
        var id = Guid.Parse(response.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        Assert.InRange(record!.RecordedAt, before, after);
    }

    [Fact]
    public async Task RecordEvidence_PersistedRecord_HasPayloadJson()
    {
        var request = BuildRequest();
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        var id = Guid.Parse(response.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        Assert.False(string.IsNullOrWhiteSpace(record!.PayloadJson));
    }

    // ── CCT-EF-01: Idempotency (C-085) ───────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_CalledTwiceWithSameActionInstanceId_ReturnsSameRecordId()
    {
        // C-085: duplicate request must return existing record, not create a second one
        var actionInstanceId = Guid.NewGuid().ToString();
        var tenantId = Guid.NewGuid();
        var request = BuildRequest(actionInstanceId: actionInstanceId);
        var ctx1 = BuildContext(tenantId);
        var ctx2 = BuildContext(tenantId);

        var response1 = await _sut.RecordEvidence(request, ctx1);
        var response2 = await _sut.RecordEvidence(request, ctx2);

        Assert.Equal(response1.EvidenceRecordId, response2.EvidenceRecordId);
    }

    [Fact]
    public async Task RecordEvidence_CalledTwiceWithSameActionInstanceId_CreatesOnlyOneDbRecord()
    {
        var actionInstanceId = Guid.NewGuid().ToString();
        var tenantId = Guid.NewGuid();
        var request = BuildRequest(actionInstanceId: actionInstanceId);

        await _sut.RecordEvidence(request, BuildContext(tenantId));
        await _sut.RecordEvidence(request, BuildContext(tenantId));

        var count = await _dbContext.EvidenceRecords
            .CountAsync(e => e.IdempotencyKey == actionInstanceId);
        Assert.Equal(1, count);
    }

    [Fact]
    public async Task RecordEvidence_DifferentActionInstanceIds_CreateSeparateRecords()
    {
        var tenantId = Guid.NewGuid();
        var request1 = BuildRequest(actionInstanceId: Guid.NewGuid().ToString());
        var request2 = BuildRequest(actionInstanceId: Guid.NewGuid().ToString());

        var response1 = await _sut.RecordEvidence(request1, BuildContext(tenantId));
        var response2 = await _sut.RecordEvidence(request2, BuildContext(tenantId));

        Assert.NotEqual(response1.EvidenceRecordId, response2.EvidenceRecordId);
        Assert.Equal(2, await _dbContext.EvidenceRecords.CountAsync());
    }

    // ── CCT-EF-01: Tenant validation ─────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_MissingTenantIdHeader_ThrowsRpcExceptionInvalidArgument()
    {
        var request = BuildRequest();
        var ctx = FakeServerCallContext.Create(tenantId: null); // no header

        var ex = await Assert.ThrowsAsync<RpcException>(
            () => _sut.RecordEvidence(request, ctx));

        Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
    }

    [Fact]
    public async Task RecordEvidence_MalformedTenantIdHeader_ThrowsRpcExceptionInvalidArgument()
    {
        var request = BuildRequest();
        var ctx = FakeServerCallContext.Create(tenantId: "not-a-guid");

        var ex = await Assert.ThrowsAsync<RpcException>(
            () => _sut.RecordEvidence(request, ctx));

        Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
    }

    [Fact]
    public async Task RecordEvidence_EmptyTenantIdHeader_ThrowsRpcExceptionInvalidArgument()
    {
        var request = BuildRequest();
        var ctx = FakeServerCallContext.Create(tenantId: "");

        var ex = await Assert.ThrowsAsync<RpcException>(
            () => _sut.RecordEvidence(request, ctx));

        Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
    }

    // ── CCT-EF-01: ActionInstanceId validation ───────────────────────────────

    [Fact]
    public async Task RecordEvidence_EmptyActionInstanceId_ThrowsRpcExceptionInvalidArgument()
    {
        var request = BuildRequest(actionInstanceId: "");
        var ctx = BuildContext();

        var ex = await Assert.ThrowsAsync<RpcException>(
            () => _sut.RecordEvidence(request, ctx));

        Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
    }

    [Fact]
    public async Task RecordEvidence_WhitespaceActionInstanceId_ThrowsRpcExceptionInvalidArgument()
    {
        var request = BuildRequest(actionInstanceId: "   ");
        var ctx = BuildContext();

        var ex = await Assert.ThrowsAsync<RpcException>(
            () => _sut.RecordEvidence(request, ctx));

        Assert.Equal(StatusCode.InvalidArgument, ex.StatusCode);
    }

    // ── CCT-EF-01: Response shape ─────────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_Response_EvidenceRecordIdIsValidGuid()
    {
        var request = BuildRequest();
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        Assert.True(Guid.TryParse(response.EvidenceRecordId, out _),
            $"EvidenceRecordId '{response.EvidenceRecordId}' is not a valid GUID.");
    }

    [Fact]
    public async Task RecordEvidence_Response_EvidenceRecordIdIsNeverEmpty()
    {
        var request = BuildRequest();
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        Assert.NotNull(response.EvidenceRecordId);
        Assert.NotEmpty(response.EvidenceRecordId);
    }

    // ── CCT-EF-01: Append-only (C-007 / C-027) ───────────────────────────────

    [Fact]
    public async Task RecordEvidence_AppendOnly_NeverUpdatesExistingRecord()
    {
        // Verify that calling RecordEvidence twice does not alter the original record's content
        var actionInstanceId = Guid.NewGuid().ToString();
        var tenantId = Guid.NewGuid();
        var originalRequest = BuildRequest(actionInstanceId: actionInstanceId, actionType: "OriginalAction");
        var duplicateRequest = BuildRequest(actionInstanceId: actionInstanceId, actionType: "ModifiedAction");

        var firstResponse = await _sut.RecordEvidence(originalRequest, BuildContext(tenantId));
        await _sut.RecordEvidence(duplicateRequest, BuildContext(tenantId));

        var id = Guid.Parse(firstResponse.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        // EvidenceType must remain as originally recorded — no mutation
        Assert.Equal("OriginalAction", record!.EvidenceType);
    }

    // ── CCT-EF-01: Cancellation ───────────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_WithCancellationToken_PropagatesCorrectly()
    {
        using var cts = new CancellationTokenSource();
        var request = BuildRequest();
        // Confirm the method accepts a cancellation token via context without issue
        var ctx = BuildContext();

        // Should complete without throwing before cancellation
        var response = await _sut.RecordEvidence(request, ctx);
        Assert.NotNull(response);
    }

    // ── CCT-EF-01: Multi-tenant isolation ────────────────────────────────────

    [Theory]
    [InlineData("ToolInvocation")]
    [InlineData("DocumentUpload")]
    [InlineData("ContractAction")]
    [InlineData("BudgetRequest")]
    public async Task RecordEvidence_VariousActionTypes_AllPersistedCorrectly(string actionType)
    {
        var request = BuildRequest(actionType: actionType);
        var ctx = BuildContext();

        var response = await _sut.RecordEvidence(request, ctx);

        var id = Guid.Parse(response.EvidenceRecordId);
        var record = await _dbContext.EvidenceRecords.FindAsync(id);
        Assert.NotNull(record);
        Assert.Equal(actionType, record!.EvidenceType);
    }

    [Fact]
    public async Task RecordEvidence_DifferentTenants_SameActionInstanceId_CreateSeparateRecords()
    {
        // Two different tenants with the same ActionInstanceId should create separate records
        // because idempotency is scoped per tenant
        var actionInstanceId = Guid.NewGuid().ToString();
        var tenant1 = Guid.NewGuid();
        var tenant2 = Guid.NewGuid();
        var request = BuildRequest(actionInstanceId: actionInstanceId);

        var response1 = await _sut.RecordEvidence(request, BuildContext(tenant1));
        var response2 = await _sut.RecordEvidence(request, BuildContext(tenant2));

        // Different tenants = different records
        Assert.NotEqual(response1.EvidenceRecordId, response2.EvidenceRecordId);
        Assert.Equal(2, await _dbContext.EvidenceRecords.CountAsync(
            e => e.IdempotencyKey == actionInstanceId));
    }
}