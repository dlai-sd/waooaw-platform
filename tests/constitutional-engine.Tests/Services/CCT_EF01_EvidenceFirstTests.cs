// Implements: tests/QA-STRATEGY.md §5.1 Unit Tests
// constitutional_basis: C-023 (Evidence First), C-007 (Append-Only), C-076 (Test Coverage)
using FluentAssertions;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Logging.Abstractions;
using Waooaw.ConstitutionalEngine.Data;
using Waooaw.ConstitutionalEngine.Evaluators;
using Waooaw.ConstitutionalEngine.Grpc;
using Waooaw.ConstitutionalEngine.Services;
using Waooaw.ConstitutionalEngine.Tests.Evaluators;
using Xunit;

// Constitutional basis: C-023 (Evidence First — DB write BEFORE gRPC return)
// Constitutional basis: C-007 (Append-Only ledger — no UPDATE/DELETE)
// Constitutional basis: C-076 (≥90% coverage gate)
// Purpose: CCT-EF-01 — validates that RecordEvidence writes to constitutional.audit_records
//          before returning a gRPC response. Merge is blocked until this test passes.
// ADR reference: ADR-001 (gRPC), ADR-002 (Evidence First enforcement)

namespace Waooaw.ConstitutionalEngine.Services;

/// <summary>
/// CCT-EF-01 — Evidence First compliance tests for ConstitutionalEngineService.RecordEvidence.
/// C-023: the evidence record MUST be persisted before the RPC returns OK.
/// C-007: only INSERTs are ever issued — no UPDATE or DELETE.
/// </summary>
public sealed class CCT_EF01_EvidenceFirstTests
{
    // ─── helpers ─────────────────────────────────────────────────────────────

    private static ConstitutionalDbContext BuildDb()
    {
        var opts = new DbContextOptionsBuilder<ConstitutionalDbContext>()
            .UseInMemoryDatabase(Guid.NewGuid().ToString())
            .Options;
        return new ConstitutionalDbContext(opts);
    }

    private static EvaluatorRegistry BuildRegistry() =>
        new EvaluatorRegistry(
            new IClaimEvaluator[]
            {
                new C041ToolAuthorizationEvaluator(
                    NullLogger<C041ToolAuthorizationEvaluator>.Instance),
                new C043BudgetCeilingEvaluator(
                    NullLogger<C043BudgetCeilingEvaluator>.Instance),
                new C048NonExploitationEvaluator(
                    NullLogger<C048NonExploitationEvaluator>.Instance),
                new C049HonestLimitationEvaluator(
                    NullLogger<C049HonestLimitationEvaluator>.Instance),
                new C062AiSecurityEvaluator(
                    NullLogger<C062AiSecurityEvaluator>.Instance),
            },
            NullLogger<EvaluatorRegistry>.Instance);

    private static RecordEvidenceRequest BuildValidRequest() =>
        new RecordEvidenceRequest
        {
            ActionInstanceId     = Guid.NewGuid().ToString(),
            ContractId           = Guid.NewGuid().ToString(),
            ProfessionalId       = Guid.NewGuid().ToString(),
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Proposed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023; AD-002",
        };

    // ─── CCT-EF-01-A: happy path ─────────────────────────────────────────────

    /// <summary>
    /// C-023: RecordEvidence MUST write exactly one row to EvidenceRecords
    /// before the gRPC response is returned to the caller.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_WritesExactlyOneRow_BeforeReturningResponse()
    {
        // Arrange
        await using var db  = BuildDb();
        var registry        = BuildRegistry();
        var svc             = new ConstitutionalEngineService(
                                    registry,
                                    db,
                                    NullLogger<ConstitutionalEngineService>.Instance);

        var tenantId = Guid.NewGuid().ToString();
        var ctx      = FakeServerCallContext.Create(tenantId);
        var request  = BuildValidRequest();

        // Act
        var response = await svc.RecordEvidence(request, ctx);

        // Assert — evidence persisted BEFORE response returned (C-023)
        response.Should().NotBeNull();
        response.EvidenceRecordId.Should().NotBeNullOrWhiteSpace(
            because: "CE must assign a UUID to every evidence record");

        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(1,
            because: "C-023 requires exactly one record written before the RPC returns OK");
    }

    // ─── CCT-EF-01-B: record content integrity ───────────────────────────────

    /// <summary>
    /// C-007 / C-023: the persisted record must carry the correct tenant_id,
    /// action_type, and constitutional_basis from the request.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_PersistedRecord_CarriesCorrectFields()
    {
        // Arrange
        await using var db  = BuildDb();
        var registry        = BuildRegistry();
        var svc             = new ConstitutionalEngineService(
                                    registry,
                                    db,
                                    NullLogger<ConstitutionalEngineService>.Instance);

        var tenantId   = Guid.NewGuid().ToString();
        var ctx        = FakeServerCallContext.Create(tenantId);
        var request    = BuildValidRequest();

        // Act
        var response = await svc.RecordEvidence(request, ctx);

        // Assert — field-level integrity
        var record = await db.EvidenceRecords.SingleAsync();

        record.EvidenceType.Should().Be(request.ActionType,
            because: "action_type must be stored verbatim");

        record.IdempotencyKey.Should().NotBeNullOrWhiteSpace(
            because: "every record needs an idempotency key for deduplication");

        record.RecordedAt.Should().BeCloseTo(DateTimeOffset.UtcNow,
            precision: TimeSpan.FromSeconds(5),
            because: "recorded_at must reflect the server wall-clock time");

        response.EvidenceRecordId.Should().Be(record.Id.ToString(),
            because: "the returned evidence_record_id must match the DB primary key");
    }

    // ─── CCT-EF-01-C: append-only — no UPDATE/DELETE (C-007) ─────────────────

    /// <summary>
    /// C-007: calling RecordEvidence twice for the same action (state transitions)
    /// MUST produce two separate INSERT rows — never an UPDATE on the first row.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_CalledTwice_ProducesTwoRows_NeverUpdate()
    {
        // Arrange
        await using var db  = BuildDb();
        var registry        = BuildRegistry();
        var svc             = new ConstitutionalEngineService(
                                    registry,
                                    db,
                                    NullLogger<ConstitutionalEngineService>.Instance);

        var tenantId        = Guid.NewGuid().ToString();
        var sharedInstanceId = Guid.NewGuid().ToString();
        var contractId       = Guid.NewGuid().ToString();

        var proposedRequest = new RecordEvidenceRequest
        {
            ActionInstanceId     = sharedInstanceId,
            ContractId           = contractId,
            ProfessionalId       = Guid.NewGuid().ToString(),
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Proposed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023; AD-002",
        };

        var executedRequest = new RecordEvidenceRequest
        {
            ActionInstanceId     = sharedInstanceId,
            ContractId           = contractId,
            ProfessionalId       = proposedRequest.ProfessionalId,
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Executed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = "C-023; AD-002",
        };

        // Act
        var r1 = await svc.RecordEvidence(proposedRequest,  FakeServerCallContext.Create(tenantId));
        var r2 = await svc.RecordEvidence(executedRequest,  FakeServerCallContext.Create(tenantId));

        // Assert — two distinct rows, never an update (C-007)
        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(2,
            because: "C-007 mandates a new INSERT for every state transition; no row may be updated");

        r1.EvidenceRecordId.Should().NotBe(r2.EvidenceRecordId,
            because: "each evidence record must receive a unique UUID");
    }

    // ─── CCT-EF-01-D: missing constitutional_basis → INVALID_ARGUMENT ─────────

    /// <summary>
    /// C-023 / spec: constitutional_basis must not be empty.
    /// CE must return gRPC INVALID_ARGUMENT (not silently accept) when it is absent.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_EmptyConstitutionalBasis_ThrowsInvalidArgument()
    {
        // Arrange
        await using var db  = BuildDb();
        var registry        = BuildRegistry();
        var svc             = new ConstitutionalEngineService(
                                    registry,
                                    db,
                                    NullLogger<ConstitutionalEngineService>.Instance);

        var request = new RecordEvidenceRequest
        {
            ActionInstanceId     = Guid.NewGuid().ToString(),
            ContractId           = Guid.NewGuid().ToString(),
            ProfessionalId       = Guid.NewGuid().ToString(),
            ActionType           = "MARKETING_POST",
            State                = EvidenceState.Proposed,
            DecisionSpaceVersion = 1,
            ConstitutionalBasis  = string.Empty,   // ← violates C-023 requirement
        };

        var ctx = FakeServerCallContext.Create(Guid.NewGuid().ToString());

        // Act
        var act = async () => await svc.RecordEvidence(request, ctx);

        // Assert — service must not silently accept invalid payload
        await act.Should().ThrowAsync<Grpc.Core.RpcException>(
            because: "constitutional_basis must not be empty per constitutional-engine.md §RecordEvidence")
            .Where(ex => ex.StatusCode == Grpc.Core.StatusCode.InvalidArgument);

        // No row written (Evidence First must NOT write invalid records)
        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(0,
            because: "an invalid request must not produce a ledger entry");
    }

    // ─── CCT-EF-01-E: missing x-tenant-id → UNAUTHENTICATED ──────────────────

    /// <summary>
    /// Spec (constitutional_service.proto transport notes):
    /// If x-tenant-id metadata is absent → gRPC UNAUTHENTICATED.
    /// </summary>
    [Fact]
    public async Task RecordEvidence_MissingTenantMetadata_ThrowsUnauthenticated()
    {
        // Arrange
        await using var db  = BuildDb();
        var registry        = BuildRegistry();
        var svc             = new ConstitutionalEngineService(
                                    registry,
                                    db,
                                    NullLogger<ConstitutionalEngineService>.Instance);

        // FakeServerCallContext with no tenant header
        var ctx     = FakeServerCallContext.Create(tenantId: null);
        var request = BuildValidRequest();

        // Act
        var act = async () => await svc.RecordEvidence(request, ctx);

        // Assert
        await act.Should().ThrowAsync<Grpc.Core.RpcException>(
            because: "absent x-tenant-id must be rejected per proto transport notes")
            .Where(ex => ex.StatusCode == Grpc.Core.StatusCode.Unauthenticated);

        var count = await db.EvidenceRecords.CountAsync();
        count.Should().Be(0,
            because: "unauthenticated requests must not produce any ledger entries");
    }

    // ─── CCT-EF-01-F: response timestamp reflects persistence time ────────────

    /// <summary>
    /// C-023 / spec §RecordEvidenceResponse: recorded_at in the response MUST equal
    /// the timestamp stored in the ledger (same transaction).
    /// </summary>
    [Fact]
    public async Task RecordEvidence_ResponseTimestamp_MatchesLedgerTimestamp()
    {
        // Arrange
        await using var db  = BuildDb();
        var registry        = BuildRegistry();
        var svc             = new ConstitutionalEngineService(
                                    registry,
                                    db,
                                    NullLogger<ConstitutionalEngineService>.Instance);

        var ctx     = FakeServerCallContext.Create(Guid.NewGuid().ToString());
        var request = BuildValidRequest();

        // Act
        var response = await svc.RecordEvidence(request, ctx);

        // Assert
        var record          = await db.EvidenceRecords.SingleAsync();
        var responseInstant = DateTimeOffset.FromUnixTimeSeconds(
                                    response.RecordedAt.Seconds)
                                .AddTicks(response.RecordedAt.Nanos / 100);

        responseInstant.Should().BeCloseTo(record.RecordedAt,
            precision: TimeSpan.FromSeconds(1),
            because: "response.recorded_at must reflect the actual DB write timestamp (C-023)");
    }
}