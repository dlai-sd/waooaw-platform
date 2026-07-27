// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// constitutional_basis: C-023 (Evidence First — record BEFORE returning), C-007 (Append-only),
//                       C-059 (Traceability), C-073 (Annotated Obligations), C-076 (≥90% Unit Test Coverage)
// CCT gate: CCT-EF-01 — RecordEvidence RPC writes to EvidenceRecords BEFORE returning gRPC response.
// DESIGN_QUESTION: FluentAssertions is spec-mandated (stack rules) — confirm PackageReference
//                  "FluentAssertions" (v6.x) is present in constitutional-engine.Tests.csproj.
//                  If absent, EA must add it before this file compiles.

#nullable enable

using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

/// <summary>
/// CCT-EF-01: Evidence-First gate tests.
/// These tests prove that <see cref="ConstitutionalEngineService.RecordEvidence"/> persists
/// a row to the append-only evidence ledger BEFORE returning a gRPC response,
/// satisfying C-023 (Evidence First) and C-007 (Append-only).
/// </summary>
public sealed class CCT_EF01_EvidenceFirstTests
{
    // ── Helpers ────────────────────────────────────────────────────────────────

    /// <summary>
    /// C-073: Creates an isolated in-memory ConstitutionalDbContext.
    /// Each test gets its own database name (Guid) to ensure full isolation.
    /// </summary>
    private static ConstitutionalDbContext CreateDb(string? dbName = null)
    {
        var opts = new DbContextOptionsBuilder<ConstitutionalDbContext>()
            .UseInMemoryDatabase(dbName ?? Guid.NewGuid().ToString())
            .Options;
        return new ConstitutionalDbContext(opts);
    }

    /// <summary>
    /// C-073: Constructs ConstitutionalEngineService with an empty evaluator registry
    /// and null loggers for deterministic unit tests.
    /// </summary>
    private static ConstitutionalEngineService CreateService(ConstitutionalDbContext db)
    {
        var registry = new EvaluatorRegistry(
            Array.Empty<IClaimEvaluator>(),
            NullLogger<EvaluatorRegistry>.Instance);

        return new ConstitutionalEngineService(
            registry,
            db,
            NullLogger<ConstitutionalEngineService>.Instance);
    }

    /// <summary>
    /// Builds a <see cref="RecordEvidenceRequest"/> with sensible defaults for CCT-EF-01 tests.
    /// </summary>
    private static RecordEvidenceRequest BuildRequest(
        string? actionInstanceId = null,
        string? actionType = null,
        string? contractId = null,
        string? constitutionalBasis = null)
    {
        return new RecordEvidenceRequest
        {
            ActionInstanceId    = actionInstanceId    ?? Guid.NewGuid().ToString(),
            ActionType          = actionType          ?? "MCP_TOOL_CALL",
            ContractId          = contractId          ?? Guid.NewGuid().ToString(),
            ProfessionalId      = Guid.NewGuid().ToString(),
            State               = EvidenceState.Unspecified,
            ConstitutionalBasis = constitutionalBasis ?? "C-023",
            DecisionSpaceVersion = 1,
        };
    }

    // ── CCT-EF-01 Core Gate Tests ───────────────────────────────────────────

    /// <summary>
    /// CCT-EF-01 CORE: After a single RecordEvidence call the ledger contains exactly one row.
    /// This is the primary gate assertion — proves "write BEFORE return".
    /// </summary>
    [Fact]
    public async Task RecordEvidence_SingleCall_ExactlyOneRowPersistedBeforeReturn()
    {
        // Arrange
        await using var db      = CreateDb();
        var service             = CreateService(db);
        var fakeCtx             = FakeServerCallContext.Create();
        var request             = BuildRequest();

        // Act — C-023: evidence must be persisted before this call returns
        var response = await service.RecordEvidence(request, fakeCtx);

        // Assert — row must exist immediately after method returns
        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(1, because: "C-023 requires the evidence row to be written before the RPC returns");
    }

    /// <summary>
    /// CCT-EF-01: The EvidenceRecordId in the response maps to the persisted row's Id.
    /// Proves the record is written before the response is constructed.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_ReturnedId_MatchesPersistedRowId()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var request         = BuildRequest();

        // Act
        var response = await service.RecordEvidence(request, fakeCtx);

        // Assert
        response.EvidenceRecordId.Should().NotBeNullOrEmpty(
            because: "C-059 requires a non-empty traceability identifier");

        var persistedId = await db.EvidenceRecords
            .Select(r => r.Id)
            .SingleAsync();

        response.EvidenceRecordId.Should().Be(persistedId.ToString(),
            because: "the response must reference the already-persisted row, proving Evidence-First ordering");
    }

    /// <summary>
    /// CCT-EF-01 / C-007: The ledger is append-only.
    /// Two distinct requests produce exactly two rows — no overwrites.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_TwoDistinctRequests_ProducesTwoRows()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var request1        = BuildRequest(actionInstanceId: Guid.NewGuid().ToString());
        var request2        = BuildRequest(actionInstanceId: Guid.NewGuid().ToString());

        // Act — C-007: each call must append, never overwrite
        await service.RecordEvidence(request1, fakeCtx);
        await service.RecordEvidence(request2, fakeCtx);

        // Assert
        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(2, because: "C-007 (append-only) requires both rows to be retained");
    }

    /// <summary>
    /// CCT-EF-01 / C-023: Database is empty before the call and non-empty after.
    /// Demonstrates the exact "before vs after" boundary that defines Evidence First.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_DbEmptyBeforeCall_NonEmptyAfterCall()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var request         = BuildRequest();

        // Assert precondition — ledger is empty before the RPC
        var countBefore = await db.EvidenceRecords.CountAsync();
        countBefore.Should().Be(0, because: "no evidence should exist before the first RPC call");

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert postcondition — evidence persisted before return
        var countAfter = await db.EvidenceRecords.CountAsync();
        countAfter.Should().Be(1, because: "C-023 demands the row is written before the RPC returns");
    }

    // ── Idempotency Tests (C-085) ───────────────────────────────────────────

    /// <summary>
    /// CCT-EF-01 / C-085: Replaying the same ActionInstanceId is idempotent —
    /// returns the same EvidenceRecordId and does NOT insert a second row.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_DuplicateActionInstanceId_IdempotentNoSecondRow()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var idempotencyKey  = Guid.NewGuid().ToString();
        var request         = BuildRequest(actionInstanceId: idempotencyKey);

        // Act
        var first  = await service.RecordEvidence(request, fakeCtx);
        var second = await service.RecordEvidence(request, fakeCtx);

        // Assert
        first.EvidenceRecordId.Should().Be(second.EvidenceRecordId,
            because: "idempotent calls must return the same EvidenceRecordId");

        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(1, because: "C-007 (append-only) must not create a duplicate row for the same idempotency key");
    }

    /// <summary>
    /// CCT-EF-01 / C-085: The IdempotencyKey on the persisted row equals the request's ActionInstanceId.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_ActionInstanceId_PersistedAsIdempotencyKey()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var actionInstanceId = Guid.NewGuid().ToString();
        var request         = BuildRequest(actionInstanceId: actionInstanceId);

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert
        var record = await db.EvidenceRecords.SingleAsync();
        record.IdempotencyKey.Should().Be(actionInstanceId,
            because: "C-059 requires ActionInstanceId to be stored as the idempotency key for traceability");
    }

    // ── Tenant Isolation Tests ──────────────────────────────────────────────

    /// <summary>
    /// CCT-EF-01 / C-059: TenantId from the x-tenant-id gRPC header is stored on the record.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_TenantIdHeader_StoredOnEvidenceRecord()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var tenantId        = Guid.NewGuid();
        var fakeCtx         = FakeServerCallContext.Create(tenantId.ToString());
        var request         = BuildRequest();

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert
        var record = await db.EvidenceRecords.SingleAsync();
        record.TenantId.Should().Be(tenantId,
            because: "C-059 requires the tenant context to be captured on every evidence record");
    }

    /// <summary>
    /// CCT-EF-01: When no x-tenant-id header is present, TenantId defaults to Guid.Empty.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_NoTenantIdHeader_TenantIdIsEmpty()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create(tenantId: null);
        var request         = BuildRequest();

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert
        var record = await db.EvidenceRecords.SingleAsync();
        record.TenantId.Should().Be(Guid.Empty,
            because: "a missing x-tenant-id header should yield Guid.Empty, not throw");
    }

    // ── Evidence Record Field Integrity Tests ────────────────────────────────

    /// <summary>
    /// CCT-EF-01 / C-059: ActionType is persisted as EvidenceType on the record.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_ActionType_PersistedAsEvidenceType()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var actionType      = "MCP_TOOL_CALL";
        var request         = BuildRequest(actionType: actionType);

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert
        var record = await db.EvidenceRecords.SingleAsync();
        record.EvidenceType.Should().Be(actionType,
            because: "C-059 requires the action type to be captured verbatim as EvidenceType");
    }

    /// <summary>
    /// CCT-EF-01 / C-059: RecordedAt is a recent UTC timestamp (within 10 seconds of now).
    /// </summary>
    [Fact]
    public async Task RecordEvidence_RecordedAt_IsRecentUtcTimestamp()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var beforeCall      = DateTimeOffset.UtcNow.AddSeconds(-1);
        var request         = BuildRequest();

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert
        var afterCall = DateTimeOffset.UtcNow.AddSeconds(1);
        var record    = await db.EvidenceRecords.SingleAsync();

        record.RecordedAt.Should().BeOnOrAfter(beforeCall,
            because: "RecordedAt must not predate the RPC call");
        record.RecordedAt.Should().BeOnOrBefore(afterCall,
            because: "RecordedAt must be close to UTC now at the time of the call");
        record.RecordedAt.Offset.Should().Be(TimeSpan.Zero,
            because: "RecordedAt must be expressed in UTC (offset = 0)");
    }

    /// <summary>
    /// CCT-EF-01 / C-059: Summary is non-empty on the persisted record.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_Summary_IsNonEmpty()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var request         = BuildRequest();

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert
        var record = await db.EvidenceRecords.SingleAsync();
        record.Summary.Should().NotBeNullOrWhiteSpace(
            because: "every evidence record must carry a human-readable summary for audit traceability (C-059)");
    }

    /// <summary>
    /// CCT-EF-01 / C-059: PayloadJson is stored and contains the ContractId from the request.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_PayloadJson_ContainsContractId()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var contractId      = Guid.NewGuid().ToString();
        var request         = BuildRequest(contractId: contractId);

        // Act
        await service.RecordEvidence(request, fakeCtx);

        // Assert
        var record = await db.EvidenceRecords.SingleAsync();
        record.PayloadJson.Should().Contain(contractId,
            because: "C-059 requires the full request context, including ContractId, to be traceable in PayloadJson");
    }

    /// <summary>
    /// CCT-EF-01: EvidenceRecordId in the response is a non-empty, parseable Guid string.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_Response_EvidenceRecordIdIsValidGuid()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var request         = BuildRequest();

        // Act
        var response = await service.RecordEvidence(request, fakeCtx);

        // Assert
        response.EvidenceRecordId.Should().NotBeNullOrEmpty(
            because: "C-059 requires a non-empty traceability id");

        Guid.TryParse(response.EvidenceRecordId, out var parsed)
            .Should().BeTrue(because: "EvidenceRecordId must be a valid Guid string");
        parsed.Should().NotBe(Guid.Empty, because: "an empty Guid is not a valid traceability identifier");
    }

    // ── Append-Only Invariant Tests (C-007) ─────────────────────────────────

    /// <summary>
    /// CCT-EF-01 / C-007: After N sequential calls, exactly N rows exist —
    /// no rows are ever updated or removed (append-only invariant).
    /// </summary>
    [Theory]
    [InlineData(1)]
    [InlineData(3)]
    [InlineData(5)]
    public async Task RecordEvidence_NDistinctCalls_ExactlyNRowsInLedger(int callCount)
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();

        // Act — C-007: each call appends; nothing is updated or deleted
        for (var i = 0; i < callCount; i++)
        {
            var request = BuildRequest(actionInstanceId: Guid.NewGuid().ToString());
            await service.RecordEvidence(request, fakeCtx);
        }

        // Assert
        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(callCount,
            because: $"C-007 (append-only) requires exactly {callCount} rows after {callCount} distinct calls");
    }

    /// <summary>
    /// CCT-EF-01 / C-007: Pre-existing rows are never mutated by a subsequent RecordEvidence call.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_SubsequentCall_DoesNotMutatePriorRow()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();

        var firstRequest = BuildRequest(actionType: "FIRST_ACTION");
        await service.RecordEvidence(firstRequest, fakeCtx);

        // Snapshot the original row state
        var originalRecord = await db.EvidenceRecords.AsNoTracking().SingleAsync();

        // Act — a second distinct call must not alter the first row
        var secondRequest = BuildRequest(actionType: "SECOND_ACTION");
        await service.RecordEvidence(secondRequest, fakeCtx);

        // Assert — first row is unchanged
        var reloadedFirst = await db.EvidenceRecords
            .AsNoTracking()
            .SingleAsync(r => r.Id == originalRecord.Id);

        reloadedFirst.EvidenceType.Should().Be(originalRecord.EvidenceType,
            because: "C-007 (append-only) forbids mutation of existing evidence records");
        reloadedFirst.IdempotencyKey.Should().Be(originalRecord.IdempotencyKey,
            because: "C-007 (append-only) forbids mutation of existing evidence records");
        reloadedFirst.RecordedAt.Should().Be(originalRecord.RecordedAt,
            because: "C-007 (append-only) forbids mutation of existing evidence records");
    }

    // ── Cancellation / Infrastructure Tests ─────────────────────────────────

    /// <summary>
    /// CCT-EF-01: RecordEvidence completes normally when supplied a default CancellationToken.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_DefaultCancellationToken_CompletesNormally()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();
        var request         = BuildRequest();

        // Act
        Func<Task> act = async () => await service.RecordEvidence(request, fakeCtx);

        // Assert
        await act.Should().NotThrowAsync(
            because: "a default CancellationToken must not cause the RPC to fail");
    }

    /// <summary>
    /// CCT-EF-01 / C-059: Even for a minimal request (only required fields set),
    /// the record is persisted with a non-empty EvidenceRecordId.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_MinimalRequest_StillPersistsRecord()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var fakeCtx         = FakeServerCallContext.Create();

        var minimalRequest = new RecordEvidenceRequest
        {
            ActionInstanceId     = Guid.NewGuid().ToString(),
            ActionType           = string.Empty,
            ContractId           = string.Empty,
            ProfessionalId       = string.Empty,
            ConstitutionalBasis  = string.Empty,
            State                = EvidenceState.Unspecified,
            DecisionSpaceVersion = 0,
        };

        // Act
        var response = await service.RecordEvidence(minimalRequest, fakeCtx);

        // Assert — C-023: evidence must ALWAYS be persisted regardless of payload completeness
        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(1, because: "C-023 requires evidence to be written for every RPC call, even minimal ones");
        response.EvidenceRecordId.Should().NotBeNullOrEmpty(
            because: "C-059 requires a non-empty traceability identifier even for minimal requests");
    }

    /// <summary>
    /// CCT-EF-01: Multiple tenants each produce isolated rows with correct TenantId values.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_MultipleTenants_EachRowHasCorrectTenantId()
    {
        // Arrange
        await using var db  = CreateDb();
        var service         = CreateService(db);
        var tenantA         = Guid.NewGuid();
        var tenantB         = Guid.NewGuid();

        // Act
        await service.RecordEvidence(
            BuildRequest(actionInstanceId: Guid.NewGuid().ToString()),
            FakeServerCallContext.Create(tenantA.ToString()));

        await service.RecordEvidence(
            BuildRequest(actionInstanceId: Guid.NewGuid().ToString()),
            FakeServerCallContext.Create(tenantB.ToString()));

        // Assert
        var records = await db.EvidenceRecords.AsNoTracking().ToListAsync();
        records.Should().HaveCount(2, because: "two distinct tenant calls must produce two distinct rows");

        records.Should().ContainSingle(r => r.TenantId == tenantA,
            because: "tenant A's row must carry tenant A's id");
        records.Should().ContainSingle(r => r.TenantId == tenantB,
            because: "tenant B's row must carry tenant B's id");
    }
}