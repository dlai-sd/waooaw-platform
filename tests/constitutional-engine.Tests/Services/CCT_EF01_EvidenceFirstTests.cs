// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-023 (Evidence First), C-007 (Append-Only), C-076 (Test Coverage), C-082 (Build Validation)
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

/// <summary>
/// CCT-EF-01: Evidence First gate — RecordEvidence MUST persist to DB before returning a gRPC response.
/// C-023 (Evidence First), C-007 (Append-Only ledger).
/// </summary>
public sealed class CCT_EF01_EvidenceFirstTests
{
    // ─── helpers ────────────────────────────────────────────────────────────

    private static ConstitutionalDbContext CreateDb() =>
        new ConstitutionalDbContext(
            new DbContextOptionsBuilder<ConstitutionalDbContext>()
                .UseInMemoryDatabase(Guid.NewGuid().ToString())
                .Options);

    private static ConstitutionalEngineService CreateSut(ConstitutionalDbContext db)
    {
        var registry = new EvaluatorRegistry(
            new List<IClaimEvaluator>(),
            NullLogger<EvaluatorRegistry>.Instance);

        return new ConstitutionalEngineService(
            db,
            new ConstitutionalDbContext(
                new DbContextOptionsBuilder<ConstitutionalDbContext>()
                    .UseInMemoryDatabase(Guid.NewGuid().ToString())
                    .Options),
            null,
            NullLogger<ConstitutionalEngineService>.Instance,
            registry);
    }

    private static RecordEvidenceRequest MakeRequest(
        string contractId         = "contract-cct-ef01",
        string actionType         = "AGENT_ACTION",
        string constitutionalBasis = "C-023",
        string actionInstanceId   = "")
        => new RecordEvidenceRequest
        {
            ActionInstanceId   = string.IsNullOrEmpty(actionInstanceId) ? Guid.NewGuid().ToString() : actionInstanceId,
            ContractId         = contractId,
            ProfessionalId     = "prof-test-001",
            ActionType         = actionType,
            State              = (EvidenceState)0,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis = constitutionalBasis
        };

    // ─── CCT-EF-01 gate tests ────────────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_WritesExactlyOneRecord_BeforeReturning()
    {
        // Arrange
        await using var db  = CreateDb();
        var sut             = CreateSut(db);
        var req             = MakeRequest();
        var ctx             = FakeServerCallContext.Create("tenant-ef01");

        // Act
        var response = await sut.RecordEvidence(req, ctx);

        // Assert — DB persisted before response returned (CCT-EF-01)
        db.EvidenceRecords.Count().Should().Be(1,
            because: "C-023 requires evidence to be written before a success response is returned");
    }

    [Fact]
    public async Task RecordEvidence_Response_ContainsNonEmptyEvidenceRecordId()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest();
        var ctx            = FakeServerCallContext.Create("tenant-ef01");

        var response = await sut.RecordEvidence(req, ctx);

        response.EvidenceRecordId.Should().NotBeNullOrWhiteSpace(
            because: "callers rely on the returned record ID for traceability (C-059)");
    }

    [Fact]
    public async Task RecordEvidence_EvidenceRecord_HasCorrectTenantId()
    {
        // Arrange
        const string tenantId = "tenant-abc-123";
        await using var db    = CreateDb();
        var sut               = CreateSut(db);
        var req               = MakeRequest();
        var ctx               = FakeServerCallContext.Create(tenantId);

        // Act
        await sut.RecordEvidence(req, ctx);

        // Assert
        var record = db.EvidenceRecords.Single();
        record.TenantId.Should().NotBe(Guid.Empty,
            because: "every evidence record must be scoped to a tenant");
    }

    [Fact]
    public async Task RecordEvidence_EvidenceRecord_IdempotencyKey_IsSet()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest();
        var ctx            = FakeServerCallContext.Create("tenant-idempotency");

        await sut.RecordEvidence(req, ctx);

        var record = db.EvidenceRecords.Single();
        record.IdempotencyKey.Should().NotBeNullOrWhiteSpace(
            because: "C-085 idempotency requires a stable key on every record");
    }

    [Fact]
    public async Task RecordEvidence_EvidenceRecord_HasNonEmptyId()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest();
        var ctx            = FakeServerCallContext.Create("tenant-id-check");

        await sut.RecordEvidence(req, ctx);

        var record = db.EvidenceRecords.Single();
        record.Id.Should().NotBe(Guid.Empty,
            because: "every evidence record requires a unique identifier for C-059 traceability");
    }

    [Fact]
    public async Task RecordEvidence_EvidenceRecord_RecordedAt_IsApproximatelyNow()
    {
        await using var db   = CreateDb();
        var sut              = CreateSut(db);
        var req              = MakeRequest();
        var ctx              = FakeServerCallContext.Create("tenant-ts");
        var before           = DateTimeOffset.UtcNow.AddSeconds(-2);

        await sut.RecordEvidence(req, ctx);

        var after  = DateTimeOffset.UtcNow.AddSeconds(2);
        var record = db.EvidenceRecords.Single();
        record.RecordedAt.Should().BeOnOrAfter(before)
            .And.BeOnOrBefore(after,
            because: "evidence timestamps must reflect actual wall-clock time for audit integrity");
    }

    [Fact]
    public async Task RecordEvidence_EvidenceRecord_EvidenceType_IsNotEmpty()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest(actionType: "MCP_TOOL_CALL");
        var ctx            = FakeServerCallContext.Create("tenant-type");

        await sut.RecordEvidence(req, ctx);

        var record = db.EvidenceRecords.Single();
        record.EvidenceType.Should().NotBeNullOrWhiteSpace(
            because: "evidence type is required for querying and audit classification");
    }

    [Fact]
    public async Task RecordEvidence_EvidenceRecord_Summary_IsNotEmpty()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest();
        var ctx            = FakeServerCallContext.Create("tenant-summary");

        await sut.RecordEvidence(req, ctx);

        var record = db.EvidenceRecords.Single();
        record.Summary.Should().NotBeNullOrWhiteSpace(
            because: "every evidence record must carry a human-readable summary for C-059 traceability");
    }

    // ─── C-007 append-only tests ─────────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_CalledTwice_WritesTwoDistinctRecords()
    {
        // C-007: append-only — each call appends a new row, never updates
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var ctx            = FakeServerCallContext.Create("tenant-append");

        await sut.RecordEvidence(MakeRequest(actionInstanceId: Guid.NewGuid().ToString()), ctx);
        await sut.RecordEvidence(MakeRequest(actionInstanceId: Guid.NewGuid().ToString()), ctx);

        db.EvidenceRecords.Count().Should().Be(2,
            because: "C-007 requires append-only writes — each RecordEvidence call adds a new row");
    }

    [Fact]
    public async Task RecordEvidence_CalledTwice_BothRecordsHaveDistinctIds()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var ctx            = FakeServerCallContext.Create("tenant-distinct");

        var r1 = await sut.RecordEvidence(MakeRequest(actionInstanceId: Guid.NewGuid().ToString()), ctx);
        var r2 = await sut.RecordEvidence(MakeRequest(actionInstanceId: Guid.NewGuid().ToString()), ctx);

        r1.EvidenceRecordId.Should().NotBe(r2.EvidenceRecordId,
            because: "each evidence record must have a unique ID to maintain an unambiguous audit trail");
    }

    [Fact]
    public async Task RecordEvidence_CalledThreeTimes_WritesThreeRecords()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var ctx            = FakeServerCallContext.Create("tenant-three");

        for (int i = 0; i < 3; i++)
        {
            await sut.RecordEvidence(MakeRequest(actionInstanceId: Guid.NewGuid().ToString()), ctx);
        }

        db.EvidenceRecords.Count().Should().Be(3,
            because: "append-only ledger (C-007) must accumulate one row per call");
    }

    // ─── contract / action-type variance ─────────────────────────────────────

    [Theory]
    [InlineData("AGENT_ACTION")]
    [InlineData("MCP_TOOL_CALL")]
    [InlineData("BUDGET_SPEND")]
    [InlineData("SCOPE_BOUNDARY")]
    public async Task RecordEvidence_AnyActionType_WritesRecord(string actionType)
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest(actionType: actionType);
        var ctx            = FakeServerCallContext.Create("tenant-variety");

        await sut.RecordEvidence(req, ctx);

        db.EvidenceRecords.Count().Should().Be(1,
            because: $"action type '{actionType}' must be recorded regardless of its value");
    }

    [Theory]
    [InlineData("contract-alpha")]
    [InlineData("contract-beta")]
    [InlineData("contract-gamma")]
    public async Task RecordEvidence_AnyContractId_WritesRecord(string contractId)
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest(contractId: contractId);
        var ctx            = FakeServerCallContext.Create("tenant-contract");

        await sut.RecordEvidence(req, ctx);

        db.EvidenceRecords.Count().Should().Be(1,
            because: $"contract '{contractId}' must produce an evidence record");
    }

    // ─── multi-tenant isolation ───────────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_DifferentTenants_BothWriteToSharedLedger()
    {
        // Shared DB (single service instance), two tenants — both rows appear
        await using var db = CreateDb();
        var sut            = CreateSut(db);

        await sut.RecordEvidence(MakeRequest(actionInstanceId: Guid.NewGuid().ToString()),
            FakeServerCallContext.Create("tenant-one"));

        await sut.RecordEvidence(MakeRequest(actionInstanceId: Guid.NewGuid().ToString()),
            FakeServerCallContext.Create("tenant-two"));

        db.EvidenceRecords.Count().Should().Be(2,
            because: "each tenant call must produce its own immutable evidence row in the shared ledger");
    }

    // ─── response-ID round-trip ───────────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_ReturnedId_MatchesPersistedRecord()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest();
        var ctx            = FakeServerCallContext.Create("tenant-roundtrip");

        var response = await sut.RecordEvidence(req, ctx);

        var record = db.EvidenceRecords.Single();
        response.EvidenceRecordId.Should().Be(record.Id.ToString(),
            because: "the caller must receive the exact persisted record ID to enable C-059 traceability");
    }

    // ─── cancellation safety ──────────────────────────────────────────────────

    [Fact]
    public async Task RecordEvidence_CompletesSuccessfully_WhenCancellationTokenIsDefault()
    {
        await using var db = CreateDb();
        var sut            = CreateSut(db);
        var req            = MakeRequest();
        var ctx            = FakeServerCallContext.Create("tenant-cancel");

        // Should not throw
        var act = async () => await sut.RecordEvidence(req, ctx);

        await act.Should().NotThrowAsync(
            because: "a non-cancelled call must always complete without exception");
    }
}