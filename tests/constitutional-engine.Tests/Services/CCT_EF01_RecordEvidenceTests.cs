// Implements: architecture/reference/components/constitutional-engine.md §1 Evidence First Enforcer
// constitutional_basis: C-023 (Evidence First), C-007 (Append-only), C-059 (Traceability),
//                       C-073 (Annotated Obligations), C-076 (≥90% Unit Test Coverage),
//                       C-085 (Idempotency)

#nullable enable

using System;
using System.Threading;
using System.Threading.Tasks;
using Grpc.Core;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Data.Entities;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;   // FakeServerCallContext
using Xunit;

namespace Waooaw.ConstitutionalEngine.Tests.Services;

/// <summary>
/// CCT-EF-01: Evidence-First enforcement gate tests for RecordEvidence RPC.
/// All tests in this class must pass before WC012-03 may merge (C-076).
/// </summary>
public sealed class CCT_EF01_RecordEvidenceTests
{
    // ── helpers ────────────────────────────────────────────────────────────────

    private static ConstitutionalDbContext CreateDb(string dbName)
    {
        var options = new DbContextOptionsBuilder<ConstitutionalDbContext>()
            .UseInMemoryDatabase(dbName)
            .Options;
        return new ConstitutionalDbContext(options);
    }

    private static ConstitutionalEngineService CreateService(ConstitutionalDbContext db)
    {
        // EvaluatorRegistry with empty evaluator list is sufficient for RecordEvidence tests.
        var registry = new EvaluatorRegistry(
            Array.Empty<IClaimEvaluator>(),
            NullLogger<EvaluatorRegistry>.Instance);

        return new ConstitutionalEngineService(
            registry,
            db,
            NullLogger<ConstitutionalEngineService>.Instance);
    }

    private static RecordEvidenceRequest BuildRequest(
        string? actionInstanceId = null,
        string? contractId       = null,
        string? actionType       = null)
    {
        return new RecordEvidenceRequest
        {
            ActionInstanceId  = actionInstanceId ?? Guid.NewGuid().ToString(),
            ContractId        = contractId       ?? "contract-001",
            ProfessionalId    = "prof-001",
            ActionType        = actionType       ?? "MCP_TOOL_CALL",
            State             = EvidenceState.Proposed,
            ProposedContent   = "proposed",
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023"
        };
    }

    // ── CCT-EF-01-01: Happy path — record is persisted ─────────────────────────

    [Fact]
    public async Task RecordEvidence_ValidRequest_ReturnsNonEmptyEvidenceRecordId()
    {
        await using var db = CreateDb(nameof(RecordEvidence_ValidRequest_ReturnsNonEmptyEvidenceRecordId));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create(tenantId: Guid.NewGuid().ToString());

        var response = await svc.RecordEvidence(BuildRequest(), ctx);

        Assert.NotNull(response.EvidenceRecordId);
        Assert.NotEmpty(response.EvidenceRecordId);
        Assert.True(Guid.TryParse(response.EvidenceRecordId, out _));
    }

    // ── CCT-EF-01-02: C-023 Evidence First — record exists in DB before return ─

    [Fact]
    public async Task RecordEvidence_ValidRequest_PersistsRecordBeforeReturning()
    {
        await using var db = CreateDb(nameof(RecordEvidence_ValidRequest_PersistsRecordBeforeReturning));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();
        var request = BuildRequest();

        var response = await svc.RecordEvidence(request, ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstOrDefaultAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.NotNull(saved);
    }

    // ── CCT-EF-01-03: C-007 Append-only — exactly one record per call ──────────

    [Fact]
    public async Task RecordEvidence_SingleCall_ExactlyOneRecordInDb()
    {
        await using var db = CreateDb(nameof(RecordEvidence_SingleCall_ExactlyOneRecordInDb));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();

        await svc.RecordEvidence(BuildRequest(), ctx);

        var count = await db.EvidenceRecords.CountAsync();
        Assert.Equal(1, count);
    }

    // ── CCT-EF-01-04: C-085 Idempotency — same ActionInstanceId returns same ID ─

    [Fact]
    public async Task RecordEvidence_DuplicateActionInstanceId_ReturnsSameRecordId()
    {
        await using var db = CreateDb(nameof(RecordEvidence_DuplicateActionInstanceId_ReturnsSameRecordId));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();
        var request = BuildRequest(actionInstanceId: "idempotency-key-001");

        var first  = await svc.RecordEvidence(request, ctx);
        var second = await svc.RecordEvidence(request, ctx);

        Assert.Equal(first.EvidenceRecordId, second.EvidenceRecordId);
    }

    // ── CCT-EF-01-05: C-085 Idempotency — duplicate does NOT create extra row ───

    [Fact]
    public async Task RecordEvidence_DuplicateActionInstanceId_DoesNotInsertSecondRow()
    {
        await using var db = CreateDb(nameof(RecordEvidence_DuplicateActionInstanceId_DoesNotInsertSecondRow));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();
        var request = BuildRequest(actionInstanceId: "idempotency-key-002");

        await svc.RecordEvidence(request, ctx);
        await svc.RecordEvidence(request, ctx);

        var count = await db.EvidenceRecords.CountAsync();
        Assert.Equal(1, count);
    }

    // ── CCT-EF-01-06: TenantId propagated from gRPC header ────────────────────

    [Fact]
    public async Task RecordEvidence_TenantIdHeader_StoredOnRecord()
    {
        await using var db = CreateDb(nameof(RecordEvidence_TenantIdHeader_StoredOnRecord));
        var svc = CreateService(db);
        var tenantId = Guid.NewGuid();
        var ctx = FakeServerCallContext.Create(tenantId: tenantId.ToString());

        var response = await svc.RecordEvidence(BuildRequest(), ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.Equal(tenantId, saved.TenantId);
    }

    // ── CCT-EF-01-07: Missing/invalid TenantId header uses Guid.Empty ──────────

    [Fact]
    public async Task RecordEvidence_NoTenantIdHeader_TenantIdIsEmpty()
    {
        await using var db = CreateDb(nameof(RecordEvidence_NoTenantIdHeader_TenantIdIsEmpty));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create(tenantId: null);

        var response = await svc.RecordEvidence(BuildRequest(), ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.Equal(Guid.Empty, saved.TenantId);
    }

    // ── CCT-EF-01-08: IdempotencyKey set to ActionInstanceId ──────────────────

    [Fact]
    public async Task RecordEvidence_ActionInstanceId_StoredAsIdempotencyKey()
    {
        await using var db = CreateDb(nameof(RecordEvidence_ActionInstanceId_StoredAsIdempotencyKey));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();
        var actionInstanceId = Guid.NewGuid().ToString();

        var response = await svc.RecordEvidence(BuildRequest(actionInstanceId: actionInstanceId), ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.Equal(actionInstanceId, saved.IdempotencyKey);
    }

    // ── CCT-EF-01-09: EvidenceType set to ActionType ──────────────────────────

    [Fact]
    public async Task RecordEvidence_ActionType_StoredAsEvidenceType()
    {
        await using var db = CreateDb(nameof(RecordEvidence_ActionType_StoredAsEvidenceType));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();

        var response = await svc.RecordEvidence(BuildRequest(actionType: "AGENT_QUERY"), ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.Equal("AGENT_QUERY", saved.EvidenceType);
    }

    // ── CCT-EF-01-10: RecordedAt is populated ─────────────────────────────────

    [Fact]
    public async Task RecordEvidence_RecordedAt_IsRecentUtcTimestamp()
    {
        await using var db = CreateDb(nameof(RecordEvidence_RecordedAt_IsRecentUtcTimestamp));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();
        var before = DateTimeOffset.UtcNow.AddSeconds(-1);

        var response = await svc.RecordEvidence(BuildRequest(), ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.True(saved.RecordedAt >= before);
        Assert.True(saved.RecordedAt <= DateTimeOffset.UtcNow.AddSeconds(5));
    }

    // ── CCT-EF-01-11: PayloadJson is non-null and contains ContractId ──────────

    [Fact]
    public async Task RecordEvidence_PayloadJson_ContainsContractId()
    {
        await using var db = CreateDb(nameof(RecordEvidence_PayloadJson_ContainsContractId));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();

        var response = await svc.RecordEvidence(BuildRequest(contractId: "contract-XYZ"), ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.NotNull(saved.PayloadJson);
        Assert.Contains("contract-XYZ", saved.PayloadJson);
    }

    // ── CCT-EF-01-12: Multiple distinct ActionInstanceIds → multiple rows ───────

    [Fact]
    public async Task RecordEvidence_TwoDistinctRequests_CreatesTwoRows()
    {
        await using var db = CreateDb(nameof(RecordEvidence_TwoDistinctRequests_CreatesTwoRows));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();

        await svc.RecordEvidence(BuildRequest(actionInstanceId: "key-A"), ctx);
        await svc.RecordEvidence(BuildRequest(actionInstanceId: "key-B"), ctx);

        var count = await db.EvidenceRecords.CountAsync();
        Assert.Equal(2, count);
    }

    // ── CCT-EF-01-13: CancellationToken propagated (no throw on default token) ──

    [Fact]
    public async Task RecordEvidence_DefaultCancellationToken_CompletesNormally()
    {
        await using var db = CreateDb(nameof(RecordEvidence_DefaultCancellationToken_CompletesNormally));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();

        var ex = await Record.ExceptionAsync(() => svc.RecordEvidence(BuildRequest(), ctx));
        Assert.Null(ex);
    }

    // ── CCT-EF-01-14: Summary field is populated ──────────────────────────────

    [Fact]
    public async Task RecordEvidence_Summary_IsNonEmpty()
    {
        await using var db = CreateDb(nameof(RecordEvidence_Summary_IsNonEmpty));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();

        var response = await svc.RecordEvidence(BuildRequest(), ctx);

        var saved = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.Id == Guid.Parse(response.EvidenceRecordId));

        Assert.NotNull(saved.Summary);
        Assert.NotEmpty(saved.Summary);
    }

    // ── CCT-EF-01-15: Idempotency key collision returns original DB row Id ──────

    [Fact]
    public async Task RecordEvidence_Idempotent_ReturnedIdMatchesPersistedRow()
    {
        await using var db = CreateDb(nameof(RecordEvidence_Idempotent_ReturnedIdMatchesPersistedRow));
        var svc = CreateService(db);
        var ctx = FakeServerCallContext.Create();
        var request = BuildRequest(actionInstanceId: "idempotency-key-003");

        var first  = await svc.RecordEvidence(request, ctx);
        var second = await svc.RecordEvidence(request, ctx);

        var persisted = await db.EvidenceRecords
            .AsNoTracking()
            .FirstAsync(r => r.IdempotencyKey == "idempotency-key-003");

        Assert.Equal(persisted.Id.ToString(), first.EvidenceRecordId);
        Assert.Equal(persisted.Id.ToString(), second.EvidenceRecordId);
    }
}